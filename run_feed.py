import os
import sys
import yaml
import datetime
import argparse
from pathlib import Path
from dotenv import load_dotenv

import ainewsfeed

def load_config(config_path):
    """Loads YAML config and overrides with Env Vars."""
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    load_dotenv()
    
    # Priority: Env Var > YAML
    config['keys']['gemini'] = os.getenv("GEMINI_API_KEY") or config['keys'].get('gemini')
    config['keys']['x_bearer'] = os.getenv("X_BEARER_TOKEN") or config['keys'].get('x_bearer')

    if not config['keys']['gemini']:
        print("❌ Error: Gemini API Key is missing.")
        sys.exit(1)
        
    return config

def get_report_path(root_dir, filename_prefix):
    """
    Format: root/YYYY/week_WW/prefix_YYYY_MM_DD.md
    """
    now = datetime.datetime.now()
    year = now.strftime("%Y")
    week = now.strftime("%V") # ISO week number (01-53)
    date_str = now.strftime("%Y_%m_%d")
    
    # Path construction
    output_dir = Path(root_dir) / year / f"week_{week}"
    filename = f"{filename_prefix}_{date_str}.md"
    
    return output_dir / filename

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    
    # --- 1. Fetch ---
    print(f"📡 Fetching papers (last {cfg['research']['lookback_days']} days)...")
    raw_papers = ainewsfeed.get_arxiv_papers(
        days=cfg['research']['lookback_days'],
        max_results=cfg['research']['max_raw_papers'],
        categories=cfg['research']['categories']
    )

    if not raw_papers:
        print("⚠️ No papers found.")
        sys.exit(0)

    # --- NEW: Pre-Filter by Project Link ---
    if cfg['research'].get('require_project_link', False):
        print("🔍 Filtering for papers with project/code links only...")
        initial_count = len(raw_papers)
        
        # Use the helper from filter.py to check abstract AND comments
        raw_papers = [p for p in raw_papers if ainewsfeed.has_project_link(p)]
        
        dropped = initial_count - len(raw_papers)
        print(f"   -> Dropped {dropped} papers. Remaining: {len(raw_papers)}")
        
        if not raw_papers:
            print("⚠️ No papers with project links found. Exiting.")
            sys.exit(0)

    # --- 2. Filter (Gemini) ---
    print(f"🧠 Filtering {len(raw_papers)} papers with Gemini...")
    filter_result = ainewsfeed.filter_papers(
        raw_papers, 
        cfg['interests'], 
        api_key=cfg['keys']['gemini'], 
        limit=cfg['research']['max_selected_papers']
    )
    selected = filter_result["papers"]

    if not selected:
        print("⚠️ Gemini found no relevant papers matching your interests.")
        sys.exit(0)

    # --- 3. Enrich Papers ---
    print(f"✨ Enriching {len(selected)} papers (Summaries, Affiliations, Figures)...")
    
    # A. Generate AI Summaries
    enriched = ainewsfeed.enrich_with_summaries(
        selected, 
        cfg['interests'], 
        api_key=cfg['keys']['gemini']
    )
    
    # Calculate paths
    report_path = get_report_path(cfg['output']['root_dir'], cfg['output']['filename_prefix'])
    report_dir = report_path.parent
    report_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists for images

    # B. Download Assets (The Loop)
    for i, paper in enumerate(enriched):
        print(f"[{i+1}/{len(enriched)}] Processing: {paper['id']}")
        
        # 1. Scrape Affiliations
        affiliations = ainewsfeed.fetch.get_author_affiliations(paper['id'])
        if affiliations:
            paper['authors_full'] = affiliations
        else:
            paper['authors_full'] = ", ".join(paper.get('authors_simple', []))

        # 2. Download PDF
        pdf_url = paper['url'].replace('/abs/', '/pdf/') + ".pdf"
        pdf_filename = f"{paper['id']}.pdf"
        pdf_path = report_dir / pdf_filename
        
        success = ainewsfeed.assets.download_pdf(pdf_url, pdf_path)
        
        if success:
            # Save the RELATIVE path (just the filename) for the Markdown link
            paper['local_pdf'] = f"./{pdf_filename}"
            # NEW: Generate Preview Image
            paper['pdf_preview'] = ainewsfeed.assets.generate_pdf_preview(
                pdf_path, 
                paper['id'], 
                report_dir
            )
            
            # 3. Extract Figures
            # figures = ainewsfeed.assets.extract_figures(pdf_path, paper['id'], report_dir)
            # paper['figures'] = figures
        else:
            # Fallback to remote URL if download fails
            paper['local_pdf'] = pdf_url

    # --- 4. Social ---
    if cfg['keys']['x_bearer']:
        print("🐦 Scanning X for discussions...")
        for paper in enriched:
            paper['tweets'] = ainewsfeed.find_tweets_for_paper(
                paper['title'], 
                cfg['keys']['x_bearer']
            )
            
    # --- 5. Report ---
    out_path = get_report_path(
        cfg['output']['root_dir'], 
        cfg['output']['filename_prefix']
    )
    
    final_path = ainewsfeed.generate_report(enriched, out_path)
    print(f"🚀 Report saved to: {final_path}")

if __name__ == "__main__":
    main()
import os
import sys
import yaml
import json
import datetime
from datetime import timezone
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

def setup_directories(root_dir, filename_prefix, date=None):
    """
    Sets up the directory structure and returns paths.
    """
    now = datetime.datetime.now() if date is None else date
    year = now.strftime("%Y")
    week = now.strftime("%V")
    date_str = now.strftime("%Y_%m_%d")
    
    # 1. Base Week Directory
    week_dir = Path(root_dir) / year / f"week_{week}"
    week_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Assets Directory
    assets_folder_name = f"{filename_prefix}_{date_str}"
    assets_dir = week_dir / "assets" / assets_folder_name
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. File Paths
    report_file = week_dir / f"{filename_prefix}_{date_str}.md"
    data_file = assets_dir / "papers_data.json"  # <-- Cache File
    relative_asset_path = f"./assets/{assets_folder_name}"

    return report_file, assets_dir, data_file, relative_asset_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--force", action="store_true", help="Ignore cache and regenerate")
    parser.add_argument("--date", type=str, help="Use specific date for report (YYYY-MM-DD)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    # Determine Date Range
    if args.date:
        try:
            d = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
            report_date = datetime.datetime.combine(d, datetime.time.max, tzinfo=timezone.utc)
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        # NOTE - Default to 3 days ago to allow for paper submissions and API indexing delays
        d = datetime.datetime.now().date()- datetime.timedelta(days=3)
        report_date = datetime.datetime.combine(d, datetime.time.max, tzinfo=timezone.utc)
    start_date = report_date - datetime.timedelta(days=cfg['research']['lookback_days'])
    print(f"📅 Generating report for papers submitted between {start_date.strftime('%Y-%m-%d %H:%M')} and {report_date.strftime('%Y-%m-%d %H:%M')} (UTC)")
    
    # --- 1. Setup Paths (Done early to check cache) ---
    report_path, assets_dir, data_file, rel_asset_path = setup_directories(
        cfg['output']['root_dir'], 
        cfg['output']['filename_prefix'],
        date=report_date
    )

    enriched = []

    # --- 2. Check Cache ---
    if data_file.exists() and not args.force:
        print(f"⚡ Found cached data at: {data_file}")
        print("   Skipping API calls and downloads...")
        with open(data_file, "r") as f:
            enriched = json.load(f)
            
    else:
        # --- 3. Run Full Pipeline (If no cache) ---
        print("📡 Cache miss. Starting full fetch pipeline...")
        
        # A. Fetch
        print(f"   Fetching papers (last {cfg['research']['lookback_days']} days)...")
        raw_papers = ainewsfeed.get_arxiv_papers(
            start_date=start_date,
            end_date=report_date,
            max_results=cfg['research']['max_raw_papers'],
            categories=cfg['research']['categories']
        )

        if not raw_papers:
            print("⚠️ No papers found.")
            sys.exit(0)

        # Pre-Filter (Project Links)
        if cfg['research'].get('require_project_link', False):
            print("   Pre-filtering papers for project links...")
            raw_papers = [p for p in raw_papers if ainewsfeed.has_project_link(p)]
            if not raw_papers:
                print("⚠️ No papers with project links found.")
                sys.exit(0)

        # B. Filter (Gemini)
        print(f"   Filtering {len(raw_papers)} papers with Gemini...")
        filter_result = ainewsfeed.filter_papers(
            raw_papers, 
            cfg['interests'], 
            api_key=cfg['keys']['gemini'], 
            limit=cfg['research']['max_selected_papers']
        )
        selected = filter_result["papers"]

        if not selected:
            print("⚠️ Gemini found no relevant papers.")
            sys.exit(0)

        # C. Enrich (Summaries)
        print(f"   Enriching {len(selected)} papers...")
        enriched = ainewsfeed.enrich_with_summaries(
            selected, 
            cfg['interests'], 
            api_key=cfg['keys']['gemini']
        )
        
        # D. Download Assets
        print(f"   Downloading assets to {assets_dir}...")
        for i, paper in enumerate(enriched):
            print(f"   [{i+1}/{len(enriched)}] Processing: {paper['id']}")
            
            # Affiliations
            affiliations = ainewsfeed.fetch.get_author_affiliations(paper['id'])
            paper['authors_full'] = affiliations if affiliations else ", ".join(paper.get('authors', []))

            # PDF Download
            pdf_url = paper.get('pdf_url') or paper['url'].replace('/abs/', '/pdf/') + ".pdf"
            pdf_filename = f"{paper['id']}.pdf"
            save_pdf_path = assets_dir / pdf_filename
            
            success = ainewsfeed.assets.download_pdf(pdf_url, save_pdf_path)
            
            if success:
                # Store RELATIVE path for Markdown
                paper['local_pdf'] = f"{rel_asset_path}/{pdf_filename}"
                
                # Generate Preview
                preview_filename = ainewsfeed.assets.generate_pdf_preview(
                    save_pdf_path, 
                    paper['id'],    # Pass ID
                    assets_dir      # Pass Directory
                )
                
                # Check for preview
                if (assets_dir / preview_filename).exists():
                    paper['pdf_preview'] = f"{rel_asset_path}/{preview_filename}"
            else:
                paper['local_pdf'] = pdf_url

        # E. Social Signal
        if cfg['keys'].get('x_bearer'):
            print("   Scanning X for discussions...")
            for paper in enriched:
                paper['tweets'] = ainewsfeed.find_tweets_for_paper(
                    paper['title'], 
                    cfg['keys']['x_bearer']
                )

        # --- 4. Save Cache ---
        print(f"💾 Saving data cache to: {data_file}")
        with open(data_file, "w") as f:
            json.dump(enriched, f, indent=2)

    # --- 5. Generate Report ---
    print("📝 Generating Markdown report...")
    final_path = ainewsfeed.generate_report(enriched, report_path, date=report_date)
    print(f"🚀 Report saved to: {final_path}")

if __name__ == "__main__":
    main()
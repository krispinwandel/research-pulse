import json
import re
from google import genai
from google.genai import types

def extract_project_url(text):
    """
    Finds the first valid external project URL (Web Demos, YouTube).
    Ignores:
      - ArXiv / DOI / Academic links
      - github.com (Repositories do not iframe well)
    Keeps:
      - github.io (Project Pages)
      - huggingface.co (Spaces)
      - Custom domains
    """
    if not text: return None
    
    # Regex to capture http/https URLs
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*'
    urls = re.findall(url_pattern, text)
    
    for url in urls:
        lower_url = url.lower()
        
        # 1. Exclude academic/meta links
        if any(x in lower_url for x in ["arxiv.org", "doi.org", "creativecommons.org", "license", "overleaf.com"]):
            continue
            
        # 2. Exclude raw GitHub repositories (they block iframes)
        # But keep *.github.io (Project Pages)
        if "github.com" in lower_url:
            continue
            
        # 3. Handle Video Embeds (YouTube)
        if "youtube.com/watch" in url:
            video_id = url.split("v=")[-1].split("&")[0]
            return f"https://www.youtube.com/embed/{video_id}"
        if "youtu.be" in url:
            video_id = url.split("/")[-1]
            return f"https://www.youtube.com/embed/{video_id}"
            
        return url # Return the first valid one found
        
    return None

def has_project_link(paper):
    """
    Returns True if the paper has a project link in Abstract OR Comments.
    """
    # Check Abstract
    if extract_project_url(paper.get('abstract', '')):
        return True
    # Check Comment (e.g. "Code at https://github...")
    if extract_project_url(paper.get('comment', '')):
        return True
    return False

def filter_papers(papers, user_interests, api_key, limit=20):
    """
    Step 1: Select relevant papers using Gemini.
    Returns a dictionary: {"papers": [...], "prompt": "..."}
    """
    if not papers: 
        return {"papers": [], "prompt": ""}
    
    client = genai.Client(api_key=api_key)
    
    # Simple list for filtering
    paper_list_text = "\n".join([f"ID: {p['id']} | Title: {p['title']}" for p in papers])
    
    prompt = f"""
    You are a research assistant.
    User Interests: {user_interests}

    Task: Select the Top {limit} papers from the list below that best match the User Interests.
    Return ONLY a raw JSON array of the matching Paper IDs (e.g. ["2310.12345", "2311.67890"]).
    Do not include markdown formatting.

    Papers:
    {paper_list_text}
    """
    
    try:
        # Use gemini-2.0-flash or gemini-3-flash-preview
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Parse response
        selected_ids = json.loads(response.text)
        
        # Filter the original list
        selected_papers = [p for p in papers if p['id'] in selected_ids]
        
        # Return strict limit
        return {
            "papers": selected_papers[:limit],
            "prompt": prompt
        }

    except Exception as e:
        print(f"❌ Filter Error: {e}")
        # Return fallback + prompt for debugging
        return {
            "papers": papers[:5], 
            "prompt": prompt
        }

def enrich_with_summaries(papers, user_interests, api_key):
    """
    Step 2: Generate 1-sentence summaries for the selected papers.
    """
    print(f"✨ Generating summaries for {len(papers)} papers...")
    
    if not papers: return []
    
    # 1. Extract Project URLs (Local Step)
    for p in papers:
        url = extract_project_url(p['abstract'])
        if not url:
            url = extract_project_url(p.get('comment', ''))
        p['project_url'] = url

    # 2. Generate Summaries (Gemini Step)
    client = genai.Client(api_key=api_key)
    
    # Prepare batch prompt
    papers_text = "\n\n".join([f"ID: {p['id']}\nTitle: {p['title']}\nAbstract: {p['abstract']}" for p in papers])
    
    prompt = f"""
    You are an expert researcher. 
    User Interests: {user_interests}

    Task: For each paper below, write a **single sentence summary** explaining exactly why it is relevant to the user. Focus on the method's novelty or results.
    
    Return a JSON object where keys are Paper IDs and values are the summaries.
    Example: {{ "2310.12345": "Introduces a new VLA architecture that outperforms RT-2 by 15%." }}

    Papers:
    {papers_text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        summaries = json.loads(response.text)
        
        # Merge summaries into paper objects
        for p in papers:
            p['ai_summary'] = summaries.get(p['id'], "Could not generate summary.")
            
        return papers
    except Exception as e:
        print(f"❌ Summary Error: {e}")
        return papers
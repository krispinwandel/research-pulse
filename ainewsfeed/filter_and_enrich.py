import json
import re
from google import genai
from google.genai import types

MODEL = 'gemini-3-flash-preview'  # Use the latest flash model for best performance

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
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?<!\.)'
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

def filter_and_enrich_papers_with_gemini(papers, user_interests, api_key, limit=20):
    """
    Merges filtering, sorting, summarization, and rating into a single Gemini call.
    Returns the top `limit` papers, sorted by relevance, with enriched metadata.
    """
    print(f"✨ Processing {len(papers)} papers with Gemini...")
    client = genai.Client(api_key=api_key)

    # Prepare the context. 
    # Note: We include the Abstract to ensure the summary and rating are accurate.
    # If the list is massive (e.g., 100+), consider truncating abstracts or doing a two-step pass.
    papers_text = "\n\n".join([
        f"ID: {p['id']}\nTitle: {p['title']}\nAbstract: {p['abstract']}" 
        for p in papers
    ])

    prompt = f"""
    You are an expert research assistant.
    User Interests: {user_interests}

    Task:
    1. Analyze the provided papers and select the top {limit} matches for the user.
    2. **Sort** the selected papers by relevance (most relevant first).
    3. For each selected paper, generate:
       - **Relevance Score**: A visual star rating from 1 to 5 using '★' (filled) and '☆' (empty). Example: ★★★★☆ (4/5).
       - **Summary**: A single sentence explaining the novelty or key result.
    
    Output Format:
    Return a raw JSON list of objects. Each object must strictly follow this structure:
    [
      {{
        "id": "2310.12345v2",
        "star_rating": "★★★☆☆",
        "summary": "Brief summary text here..."
      }}
      {{
        "id": "2311.67890v1",
        "star_rating": "★★★★★",
        "summary": "Brief summary text here..."
      }}
    ]

    Papers to analyze:
    {papers_text}
    """

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3 # Lower temperature for better sorting/formatting adherence
            )
        )

        # 1. Parse the JSON response
        results = json.loads(response.text)

        # 2. Create a lookup dictionary for O(1) access
        #    Map ID -> {summary, rating, sort_index}
        enrichment_map = {item['id']: item for item in results}

        # 3. Filter and Enrich the original papers
        final_papers = []
        for p in papers:
            if p['id'] in enrichment_map:
                data = enrichment_map[p['id']]
                
                # Enrich original object
                p['ai_summary'] = data.get('summary', 'No summary available.')
                p['star_rating'] = data.get('star_rating', '☆☆☆☆☆')
                
                # Extract project URL locally (preserving your original logic)
                url = extract_project_url(p.get('abstract', ''))
                if not url:
                    url = extract_project_url(p.get('comment', ''))
                p['project_url'] = url
                
                final_papers.append(p)

        # 4. Sort the final list based on the order returned by Gemini
        #    We create a map of ID to Index from the JSON response
        sort_order = {item['id']: index for index, item in enumerate(results)}
        final_papers.sort(key=lambda x: sort_order.get(x['id'], 999))

        return {
            "papers": final_papers[:limit],  # Enforce limit after sorting
            "prompt": prompt
        }

    except Exception as e:
        print(f"❌ Processing Error: {e}")
        # Fallback: Return first few original papers without enrichment
        return {
            "papers": papers[:limit],
            "prompt": prompt
        }
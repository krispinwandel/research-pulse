import arxiv
import datetime

def get_arxiv_papers(days=7, max_results=200, categories=['cs.CV', 'cs.RO']):
    """
    Fetches papers from arXiv for the last N days in specific categories.
    """
    print(f"📡 Fetching arXiv papers from the last {days} days...")
    
    end_date = datetime.datetime.now(datetime.timezone.utc)
    start_date = end_date - datetime.timedelta(days=days)
    
    # Construct query: cat:cs.CV OR cat:cs.RO ...
    query = " OR ".join([f"cat:{c}" for c in categories])
    
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = []
    client = arxiv.Client()
    
    for result in client.results(search):
        # Filter by date (API sort is approximate)
        if result.published >= start_date:
            papers.append({
                "id": result.entry_id.split('/')[-1],
                "title": result.title.replace('\n', ' '),
                "abstract": result.summary.replace('\n', ' '),
                "comment": result.comment or "",
                "authors_simple": [a.name for a in result.authors],
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d")
            })
            
    print(f"✅ Fetched {len(papers)} raw papers from arXiv.")
    return papers

def get_author_affiliations(paper_id):
    """
    Scrapes the arXiv abstract page to get the full author string with affiliations.
    Example return: "Kaiming He (Meta AI), Ross Girshick (Meta AI)"
    """
    import requests
    from bs4 import BeautifulSoup
    
    url = f"https://arxiv.org/abs/{paper_id}"
    try:
        # User-Agent is required to avoid 403 Forbidden
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        authors_div = soup.find('div', class_='authors')
        
        if not authors_div:
            return None
            
        # The div text is usually "Authors: Name (Affil), Name (Affil)"
        full_text = authors_div.get_text()
        return full_text.replace("Authors:", "").strip()
        
    except Exception as e:
        return None
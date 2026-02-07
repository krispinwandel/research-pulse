import requests

def find_tweets_for_paper(paper_title, bearer_token):
    """
    Searches X (Twitter) API v2 using direct HTTP requests.
    """
    if not bearer_token:
        print("⚠️ No X Bearer Token provided.")
        return []

    # Standard endpoint (api.twitter.com is still the canonical base for v2)
    url = "https://api.twitter.com/2/tweets/search/recent"
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "v2RecentSearchPython"
    }
    
    # 1. Sanitize title: remove quotes to avoid query syntax errors
    clean_title = paper_title.replace('"', '').replace("'", "")
    
    # 2. Build Query: Exact match on title, no retweets, English only
    query = f'"{clean_title}" -is:retweet lang:en'
    
    params = {
        "query": query,
        "max_results": 10,
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "name,username"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ X API Error ({response.status_code}): {response.text}")
            return []
            
        data = response.json()
        
        if "data" not in data:
            return []

        # 3. Build User Lookup (Map author_id -> User Object)
        users = {}
        if "includes" in data and "users" in data["includes"]:
            for user in data["includes"]["users"]:
                users[user["id"]] = user
        
        results = []
        for tweet in data["data"]:
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            
            # Filter noise (tweets with 0-1 likes)
            if likes < 2:
                continue
            
            author_id = tweet.get("author_id")
            author = users.get(author_id, {})
            handle = author.get("username", "unknown")
            
            results.append({
                "text": tweet.get("text", ""),
                "author_name": author.get("name", "Unknown"),
                "author_handle": handle,
                "likes": likes,
                "retweets": metrics.get("retweet_count", 0),
                "url": f"https://x.com/{handle}/status/{tweet.get('id')}"
            })
            
        # Sort by likes descending
        results.sort(key=lambda x: x['likes'], reverse=True)
        return results

    except Exception as e:
        print(f"❌ Request Error for '{clean_title[:20]}...': {e}")
        return []
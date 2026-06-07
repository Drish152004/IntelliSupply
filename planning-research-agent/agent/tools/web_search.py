import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv(override=True)

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Enterprise-grade search prioritizing Tavily AI for clean, agent-optimized data,
    with a fallback to DuckDuckGo if the key is missing or fails.
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            # Advanced search pulls deeply relevant RAG snippets
            response = client.search(query=query, max_results=max_results, search_depth="advanced")
            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")
                })
            return results
        except Exception as e:
            print(f"Tavily Search failed: {e}. Falling back to DuckDuckGo.")

    # Fallback to DuckDuckGo
    from duckduckgo_search import DDGS
    results = []
    try:
        with DDGS() as ddgs:
            ddgs_results = ddgs.text(query, max_results=max_results)
            for r in ddgs_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
    except Exception as e:
        print(f"DuckDuckGo Search failed: {e}")
    
    return results

if __name__ == "__main__":
    # Test the search tool
    query = "demand spike inventory shortage mitigation"
    print(f"Searching for: {query}")
    results = search_web(query)
    for r in results:
        print(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n")

import httpx
import trafilatura
from typing import Optional, Dict

def fetch_content(url: str, timeout: int = 15) -> Optional[Dict[str, str]]:
    """
    Enhanced scraper with bot-evasion headers and structured return.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }
        with httpx.Client(follow_redirects=True, headers=headers, timeout=timeout, http2=True) as client:
            response = client.get(url)
            if response.status_code == 403 or response.status_code == 404:
                return None
            
            response.raise_for_status()
            
            # Use trafilatura for high-quality main text extraction
            result = trafilatura.extract(response.text, include_comments=False, include_tables=True)
            
            if not result or len(result) < 200: # Ignore low-quality pages
                return None
                
            return {
                "text": result,
                "status": response.status_code
            }
    except Exception as e:
        print(f"Scraper Warning for {url}: {e}")
        return None

if __name__ == "__main__":
    # Test the fetch tool
    test_url = "https://www.reuters.com/business/retail-consumer/global-supply-chain-crisis-shows-signs-easing-2022-01-26/"
    print(f"Fetching content from: {test_url}")
    content = fetch_content(test_url)
    if content:
        print(f"Extracted content (first 500 chars):\n{content[:500]}...")
    else:
        print("Failed to fetch content.")

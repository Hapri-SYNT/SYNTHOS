from typing import List, Dict
from duckduckgo_search import DDGS

class DuckDuckGoSearch:
    def __init__(self, query: str, query_domains=None):
        self.query = query
        self.query_domains = query_domains

    def search(self, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(self.query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", "")
                    })
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
        return results

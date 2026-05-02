from typing import Dict, List
import requests

class SemanticScholarSearch:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    VALID_SORT_CRITERIA = ["relevance", "citationCount", "publicationDate"]

    def __init__(self, query: str, sort: str = "relevance", query_domains=None):
        self.query = query
        assert sort in self.VALID_SORT_CRITERIA, "Invalid sort criterion"
        self.sort = sort.lower()

    def search(self, max_results: int = 10) -> List[Dict[str, str]]:
        params = {
            "query": self.query,
            "limit": max_results,
            "fields": "title,abstract,url,venue,year,authors,isOpenAccess,openAccessPdf",
            "sort": self.sort,
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Semantic Scholar API error: {e}")
            return []

        results = response.json().get("data", [])
        search_result = []
        for result in results:
            if result.get("isOpenAccess") and result.get("openAccessPdf"):
                search_result.append({
                    "title": result.get("title", "No Title"),
                    "href": result["openAccessPdf"].get("url", "No URL"),
                    "body": result.get("abstract", "Abstract not available"),
                })
        return search_result

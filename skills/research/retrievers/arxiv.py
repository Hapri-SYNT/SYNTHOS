import arxiv
from typing import List, Dict

class ArxivSearch:
    def __init__(self, query: str, sort: str = 'Relevance', query_domains=None):
        self.query = query
        assert sort in ['Relevance', 'SubmittedDate'], "Invalid sort criterion"
        self.sort = arxiv.SortCriterion.SubmittedDate if sort == 'SubmittedDate' else arxiv.SortCriterion.Relevance

    def search(self, max_results: int = 5) -> List[Dict[str, str]]:
        arxiv_gen = list(arxiv.Client().results(
            arxiv.Search(
                query=self.query,
                max_results=max_results,
                sort_by=self.sort,
            )))
        search_result = []
        for result in arxiv_gen:
            search_result.append({
                "title": result.title,
                "href": result.pdf_url,
                "body": result.summary,
            })
        return search_result

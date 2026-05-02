from typing import List, Dict, Any, Optional
import os
import xml.etree.ElementTree as ET
import requests

class PubMedCentralSearch:
    def __init__(self, query: str, query_domains=None):
        self.base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.api_key = os.getenv('NCBI_API_KEY')
        if not self.api_key:
            print("Warning: NCBI_API_KEY not set. Requests will be rate-limited.")
        self.query = query
        self.db_type = os.getenv('PUBMED_DB', 'pmc')
        self.params = self._populate_params()

    def _populate_params(self) -> Dict[str, Any]:
        params = {
            key[len('PUBMED_ARG_'):].lower(): value
            for key, value in os.environ.items()
            if key.startswith('PUBMED_ARG_')
        }
        params.setdefault('sort', 'relevance')
        params.setdefault('retmode', 'json')
        return params

    def _search_articles(self, max_results: int) -> Optional[List[str]]:
        if self.db_type == 'pubmed':
            search_term = f"{self.query} AND (ffrft[filter] OR pmc[filter])"
        else:
            search_term = self.query
        search_params = {
            "db": self.db_type,
            "term": search_term,
            "retmax": max_results,
            "api_key": self.api_key,
            **self.params
        }
        try:
            response = requests.get(self.base_search_url, params=search_params)
            response.raise_for_status()
            data = response.json()
            id_list = data.get('esearchresult', {}).get('idlist', [])
            print(f"Found {len(id_list)} articles with full text available")
            return id_list
        except requests.RequestException as e:
            print(f"Failed to search articles: {e}")
            return None

    def _fetch_full_text(self, article_id: str) -> Optional[Dict[str, str]]:
        fetch_params = {
            "db": "pmc" if self.db_type == "pmc" else "pmc",
            "id": article_id,
            "rettype": "full",
            "retmode": "xml",
            "api_key": self.api_key
        }
        try:
            response = requests.get(self.base_fetch_url, params=fetch_params)
            response.raise_for_status()
            try:
                root = ET.fromstring(response.text)
                title = root.find('.//article-title')
                title_text = title.text if title is not None else ""
                abstract = root.find('.//abstract')
                abstract_text = " ".join(abstract.itertext()) if abstract is not None else ""
                body = root.find('.//body')
                body_text = " ".join(body.itertext()) if body is not None else ""
                full_content = f"Title: {title_text}\n\nAbstract: {abstract_text}\n\nBody: {body_text}"
                if self.db_type == "pmc" or article_id.startswith("PMC"):
                    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{article_id}/"
                else:
                    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{article_id}/"
                return {
                    "href": url,
                    "url": url,
                    "body": full_content,
                    "raw_content": full_content,
                    "title": title_text
                }
            except ET.ParseError as e:
                return None
        except requests.RequestException as e:
            return None

    def search(self, max_results: int = 5) -> Optional[List[Dict[str, Any]]]:
        article_ids = self._search_articles(max_results)
        if not article_ids:
            return None
        results = []
        for article_id in article_ids:
            article_content = self._fetch_full_text(article_id)
            if article_content:
                results.append(article_content)
        return results

import os
import json
import requests
from typing import List, Dict
from urllib.parse import urljoin

class SearxSearch:
    def __init__(self, query: str, query_domains=None):
        self.query = query
        self.query_domains = query_domains
        self.base_url = self.get_searxng_url()

    def get_searxng_url(self) -> str:
        try:
            base_url = os.environ["SEARX_URL"]
            if not base_url.endswith('/'):
                base_url += '/'
            return base_url
        except KeyError:
            raise Exception(
                "SearxNG URL not found. Please set the SEARX_URL environment variable. "
                "You can find public instances at https://searx.space/"
            )

    def search(self, max_results: int = 10) -> List[Dict[str, str]]:
        search_url = urljoin(self.base_url, "search")
        params = {
            'q': self.query,
            'format': 'json'
        }
        try:
            response = requests.get(
                search_url,
                params=params,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            results = response.json()
            search_response = []
            for result in results.get('results', [])[:max_results]:
                search_response.append({
                    "href": result.get('url', ''),
                    "body": result.get('content', '')
                })
            return search_response
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error querying SearxNG: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Error parsing SearxNG response")

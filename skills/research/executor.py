import requests
"""
Research Orchestrator - multi-retriever, full‑text scraping, epistemic graph integration.
"""
import time
import uuid
import logging
from typing import Dict, List, Optional

from config import logger
from core.infrastructure import epistemic_graph


class ResearchOrchestrator:
    def __init__(self):
        # Konfigurasi domain -> retriever yang cocok
        self.domain_retriever_map = {
            "biology": ["pubmed"],
            "medical": ["pubmed"],
            "biomedical": ["pubmed"],
            "artificial intelligence": ["arxiv", "semantic_scholar"],
            "machine learning": ["arxiv", "semantic_scholar"],
            "computer science": ["arxiv", "semantic_scholar"],
            "physics": ["arxiv"],
            "mathematics": ["arxiv"],
            "astronomy": ["arxiv"],
            "chemistry": ["pubmed"],
        }
        self.default_retrievers = ["duckduckgo"]

    def _get_retrievers_for_domain(self, domain: str) -> List[str]:
        domain_lower = domain.lower()
        for key, retrievers in self.domain_retriever_map.items():
            if key in domain_lower:
                return retrievers
        return self.default_retrievers

    def _instantiate_retriever(self, name: str, query: str):
        # Lazy import hanya saat diperlukan
        if name == "duckduckgo":
            from .retrievers.duckduckgo import DuckDuckGoSearch
            return DuckDuckGoSearch(query)
        elif name == "arxiv":
            from .retrievers.arxiv import ArxivSearch
            return ArxivSearch(query)
        elif name == "semantic_scholar":
            from .retrievers.semantic_scholar import SemanticScholarSearch
            return SemanticScholarSearch(query)
        elif name == "pubmed":
            from .retrievers.pubmed import PubMedCentralSearch
            return PubMedCentralSearch(query)
        elif name == "searx":
            try:
                from .retrievers.searx import SearxSearch
                return SearxSearch(query)
            except Exception:
                logger.warning("SearX tidak tersedia, lewati.")
                return None
        return None

    def _scrape_full_content(self, url: str, is_pdf: bool = False) -> Optional[str]:
        try:
            if is_pdf or url.endswith('.pdf'):
                from .scrapers.pymupdf import PyMuPDFScraper
                scraper = PyMuPDFScraper(url)
                content, _, _ = scraper.scrape()
                return content
            else:
                from .scrapers.beautiful_soup import BeautifulSoupScraper
                scraper = BeautifulSoupScraper(url)
                content, _, _ = scraper.scrape()
                return content
        except Exception as e:
            logger.warning(f"Gagal scraping {url}: {e}")
            return None

    def execute(self, dna) -> Dict:
        query = f"{dna.domain} latest developments 2026"
        logger.info(f"[{dna.dna_id}] Research dimulai: {query}")

        retriever_names = self._get_retrievers_for_domain(dna.domain)
        logger.info(f"[{dna.dna_id}] Menggunakan retriever: {retriever_names}")

        all_results = []
        for name in retriever_names:
            retriever = self._instantiate_retriever(name, query)
            if not retriever:
                continue
            try:
                results = retriever.search(max_results=3)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Retriever {name} error: {e}")

        if not all_results:
            return {"query": query, "results": 0, "error": "No results"}

        # Scrape konten penuh
        enriched_results = []
        for res in all_results:
            url = res.get("href") or res.get("url", "")
            if not url:
                enriched_results.append(res)
                continue

            body = res.get("body") or res.get("raw_content", "")
            if body and len(body) > 500:
                enriched_results.append(res)
                continue

            is_pdf = url.endswith('.pdf') or 'arxiv' in url
            full_content = self._scrape_full_content(url, is_pdf)
            if full_content:
                res["body"] = full_content[:2000]
                res["has_full_text"] = True
            enriched_results.append(res)

        # Simpan ke epistemic graph
        for r in enriched_results:
            evidence = [r.get("href", "")]
            epistemic_graph.add_node({
                "id": f"research-{uuid.uuid4().hex[:8]}",
                "domain": dna.domain,
                "topic": r.get("title", "")[:100],
                "statement": (r.get("body") or r.get("snippet", ""))[:500],
                "epistemic_type": "fact",
                "confidence_score": 0.75,
                "tags": ["research", dna.domain[:10]],
                "added_by_dna": dna.dna_id,
                "created_at": time.time(),
                "evidence": evidence
            })

        dna.log_action(f"🔬 Research: {len(enriched_results)} hasil dari {len(retriever_names)} sumber")
        return {"query": query, "results": len(enriched_results), "retrievers_used": retriever_names}

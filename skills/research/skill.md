# skills/research/SKILL.md (diperbarui)
name: research
description: "Multi-source deep research orchestrator: query DuckDuckGo, Arxiv, Semantic Scholar, PubMed, SearX; scrape full-text; add knowledge to Epistemic Graph."
emoji: "🔬"
---
# Research Orchestrator (Multi‑Retriever Edition)
1. Analyze the DNA’s domain and select the most relevant scientific/search engines.
2. Generate sub‑queries if needed (using local LLM).
3. Execute searches in parallel across DuckDuckGo, Arxiv, Semantic Scholar, PubMed Central, and SearX (if available).
4. For each result, attempt full‑text extraction with BeautifulSoup (HTML) or PyMuPDF (PDF).
5. Filter duplicates using simple fuzzy matching.
6. Store all findings as verified nodes in the Epistemic Graph, including source URLs as evidence.
7. Return a summary of findings to the DNA.

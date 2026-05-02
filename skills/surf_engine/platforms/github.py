# skills/surf_engine/platforms/github.py
"""
Surf GitHub — cari bounty open-source.
"""

import requests
from typing import Dict, List, Optional

from config import logger


async def surf_github(dna, execute: bool = False, opportunity: Dict = None) -> List[Dict]:
    """
    Cari bounty GitHub yang relevan dengan domain DNA.
    """
    if execute and opportunity:
        # Untuk sekarang hanya monitoring, belum apply
        from core.economy import universal_task_engine
        result = await universal_task_engine.execute(dna, "github")
        return {
            "platform": "github",
            "profit": result.get("profit", 0),
            "token": "SOL",
            "desc": result.get("desc", ""),
        }

    opportunities = []

    try:
        query = f"label:bounty+state:open+{dna.domain.replace(' ', '+')}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = requests.get(
            f"https://api.github.com/search/issues?q={query}&sort=created&per_page=3",
            headers=headers,
            timeout=5,
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                opportunities.append({
                    "platform": "github",
                    "title": item.get("title", "")[:80],
                    "estimated_profit": 0.0001,  # Placeholder
                    "risk": 0.1,
                    "required_capital_idr": 0,
                    "token": "SOL",
                })
    except Exception as e:
        logger.debug(f"GitHub surf error: {e}")

    return opportunities

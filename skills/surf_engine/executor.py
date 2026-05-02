# skills/surf_engine/executor.py — FINAL
"""
Surf Engine Orchestrator
- Mencari peluang di semua platform
- Evaluasi + Musyawarah + Eksekusi
- Split profit + Record
"""

import asyncio
import time
import random
from typing import Dict, List, Optional

from config import logger
from core.infrastructure import epistemic_graph
from core.bank_digital import digital_bank
from .economy.splitter import split_profit
from .platforms.solana_dex import surf_solana
from .platforms.github import surf_github
from .platforms.content import surf_content


class SurfEngine:
    """Orchestrator untuk menjelajah semua pekerjaan."""

    def __init__(self):
        self.platforms = {
            "solana_dex": surf_solana,
            "github": surf_github,
            "content": surf_content,
        }
        self.opportunity_cache: Dict[str, List[Dict]] = {}
        self.cache_ttl = 60

    # ═══════════════════════════════════════════════════════════
    # WRAPPER untuk skill_manager.execute_skill()
    # ═══════════════════════════════════════════════════════════
    def execute(self, dna) -> Dict:
        """
        Wrapper untuk kompatibilitas dengan SkillManager.
        SkillManager memanggil executor.execute(dna).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.surf(dna))

    # ═══════════════════════════════════════════════════════════
    # MAIN SURF CYCLE
    # ═══════════════════════════════════════════════════════════
    async def surf(self, dna) -> Dict:
        """Satu siklus surf: cari → evaluasi → musyawarah → eksekusi."""
        logger.info(f"🏄 [{dna.dna_id}] Surfing all platforms...")

        # 1. Kumpulkan peluang
        opportunities = []
        for platform, handler in self.platforms.items():
            try:
                now = time.time()
                cache_key = f"{platform}_{dna.domain}"
                if cache_key in self.opportunity_cache:
                    cached = self.opportunity_cache[cache_key]
                    if now - cached.get("timestamp", 0) < self.cache_ttl:
                        opportunities.extend(cached.get("data", []))
                        continue
                result = await handler(dna)
                if result:
                    self.opportunity_cache[cache_key] = {"timestamp": now, "data": result}
                    opportunities.extend(result)
            except Exception as e:
                logger.error(f"❌ Surf {platform} error: {e}")

        if not opportunities:
            return {
                "type": "surf_engine",
                "profit": 0,
                "desc": "No opportunities found",
                "chain": "internal",
                "surfed": len(self.platforms),
                "opportunities": 0,
                "executed": 0,
            }

        # 2. Evaluasi
        for opp in opportunities:
            risk = opp.get("risk", 0.5)
            profit = opp.get("estimated_profit", 0)
            opp["score"] = profit * (1 - risk)

        opportunities.sort(key=lambda x: x.get("score", 0), reverse=True)
        logger.info(
            f"🏄 [{dna.dna_id}] Ditemukan {len(opportunities)} peluang, "
            f"teratas: {opportunities[0].get('platform', '?')} "
            f"(score: {opportunities[0].get('score', 0):.4f})"
        )

        # 3. Eksekusi
        best_opp = opportunities[0]
        result = None

        try:
            platform_handler = self.platforms.get(best_opp.get("platform"))
            if platform_handler:
                result = await platform_handler(dna, execute=True, opportunity=best_opp)
        except Exception as e:
            logger.error(f"Eksekusi {best_opp.get('platform')} gagal: {e}")

        # 4. Split profit
        if result and result.get("profit", 0) > 0:
            token = result.get("token", "SOL")
            split_profit(dna, token, result["profit"])

        profit = result.get("profit", 0) if result else 0

        return {
            "type": "surf_engine",
            "profit": profit,
            "desc": f"Surfed {len(self.platforms)} platforms, executed {1 if result else 0}",
            "chain": "internal",
            "surfed": len(self.platforms),
            "opportunities": len(opportunities),
            "executed": 1 if result else 0,
            "platform": best_opp.get("platform") if result else None,
        }


surf_engine = SurfEngine()

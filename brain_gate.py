#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  BRAIN_GATE.PY — Saklar Otak DNA Koloni                       ║
║  Setiap langkah DNA wajib lewat sini sebelum eksekusi         ║
║  60% LocalBrain + 10% Musyawarah + 10% Graph + 10% Web + 10% Reason ║
╚══════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from config import logger, QND_BASE_DIR, BRAIN_GATE_ENABLED
from SYNTOSH.syntosh_gpt_bridge import reason as syntosh_reason

# ═══════════════════════════════════════════════════════════════════
# KABEL KE SEMUA MODUL
# ═══════════════════════════════════════════════════════════════════

class BrainGate:
    """
    Saklar otak tunggal untuk semua DNA sebelum eksekusi apa pun.
    Tidak memblokir — menganalisis dan memberi sinyal arah.
    """

    def __init__(self):
        self._dna_pop = None
        self._epistemic_graph = None
        self._wallet_manager = None
        self._skill_manager = None
        self._local_brain = None
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy load semua modul biar ga circular import."""
        if self._loaded:
            return
        try:
            from core.dna_sovereign import dna_pop
            from core.infrastructure import epistemic_graph
            from core.economy import wallet_manager
            from skills.manager import skill_manager

            self._dna_pop = dna_pop
            self._epistemic_graph = epistemic_graph
            self._wallet_manager = wallet_manager
            self._skill_manager = skill_manager

            # Load local_brain
            brain_path = os.path.join(QND_BASE_DIR, "local_brain.json")
            if os.path.exists(brain_path):
                with open(brain_path, 'r') as f:
                    self._local_brain = json.load(f)
            else:
                self._local_brain = {"shared_knowledge": [], "alliances": []}

            self._loaded = True
            logger.info("🧠 BrainGate: semua kabel terhubung")
        except Exception as e:
            logger.error(f"BrainGate load error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # SINYAL KEPUTUSAN
    # ═══════════════════════════════════════════════════════════════

    SIGNALS = {
        "EXECUTE":    {"color": "🟢", "desc": "Profit terdeteksi, eksekusi"},
        "EXECUTE_SMALL": {"color": "🟡", "desc": "Profit kecil, eksekusi dengan size kecil"},
        "LEARN":      {"color": "🔵", "desc": "Tidak ada profit jelas, fokus belajar/research"},
        "WAIT":       {"color": "🟠", "desc": "Tunda — kondisi tidak menguntungkan"},
        "AVOID":      {"color": "🔴", "desc": "Bahaya — hindari, update fear"},
    }

    # ═══════════════════════════════════════════════════════════════
    # METODE UTAMA — dipanggil sebelum DNA bertindak
    # ═══════════════════════════════════════════════════════════════

    async def think(self, dna, action: str, context: Optional[Dict] = None) -> Dict:
        """
        DNA berpikir sebelum melangkah.

        Args:
            dna: DNAEntity dari sistem
            action: "dex_trade", "github_bounty", "micro_task", dll
            context: info tambahan (peluang, profit estimasi, dll)

        Returns:
            Dict dengan sinyal, analisis, rekomendasi
        """
        self._ensure_loaded()

        if not BRAIN_GATE_ENABLED:
            return {"signal": "EXECUTE", "reason": "Brain gate disabled", "confidence": 1.0}

        context = context or {}
        start_time = time.time()

        # ═══ 1. CEK LOCAL BRAIN (60%) ═══
        local_knowledge = self._search_local_brain(action, dna.domain)

        # ═══ 2. CEK EPISTEMIC GRAPH (10%) ═══
        graph_lessons = self._search_graph_lessons(action, dna.domain)

        # ═══ 3. CEK GOSSIP INBOX ═══
        relevant_gossip = self._filter_gossip(dna, action)

        # ═══ 4. ANALISIS PROFIT + RISIKO ═══
        # ═══ SYNTOSH THINK — Reasoning 16 modul ═══
        try:
            synthos_result = syntosh_reason(dna, action, context)
            if synthos_result and synthos_result.get('reasoning_used'):
                dna.log_action(f'🧬 [SYNTOSH] Decision: {synthos_result.get("decision")} (confidence: {synthos_result.get("confidence", 0):.0%})')
        except:
            synthos_result = None

        signal, reason, confidence = await self._analyze(
            dna, action, context, local_knowledge, graph_lessons, relevant_gossip
        )

        duration_ms = (time.time() - start_time) * 1000

        result = {
            "signal": signal,
            "reason": reason,
            "confidence": confidence,
            "duration_ms": duration_ms,
            "sources": {
                "local_brain": len(local_knowledge),
                "graph_lessons": len(graph_lessons),
                "gossip": len(relevant_gossip),
            },
        }

        dna.log_action(
            f"🧠 [{signal}] {reason[:60]} (confidence: {confidence:.0%}, {duration_ms:.0f}ms)"
        )

        return result

    # ═══════════════════════════════════════════════════════════════
    # ANALISIS UTAMA
    # ═══════════════════════════════════════════════════════════════

    async def _analyze(
        self,
        dna,
        action: str,
        context: Dict,
        local_knowledge: list,
        graph_lessons: list,
        gossip: list,
    ) -> Tuple[str, str, float]:
        """Analisis profit + risiko → sinyal keputusan."""

        # 1. CEK BAHAYA — graph lessons + gossip warning
        danger_keywords = ["rug pull", "scam", "hack", "drain", "exploit", "failed", "mati"]
        for lesson in graph_lessons:
            for kw in danger_keywords:
                if kw in lesson.get("statement", "").lower():
                    return ("AVOID", f"Lesson: {lesson.get('statement','')[:80]}", 0.95)

        for g in gossip:
            if any(kw in g.get("message", "").lower() for kw in danger_keywords):
                return ("AVOID", f"Gossip warning: {g.get('message','')[:80]}", 0.85)

        # 2. CEK FEAR — kalau takut banget, LEARN dulu
        if dna.state.get("fear_score", 0) > 0.8:
            return ("LEARN", f"Fear terlalu tinggi ({dna.state['fear_score']:.1f})", 0.9)

        # 3. CEK HUNGER — kalau lapar, EXECUTE apa saja yang ada
        if dna.state.get("hunger_level", 0) > 0.7:
            if action in ["micro_task", "gig_work", "passive_income"]:
                return ("EXECUTE_SMALL", f"Hunger {dna.state['hunger_level']:.1f} — butuh profit cepat", 0.7)
            if action in ["dex_trade", "trading"]:
                return ("WAIT", f"Hunger {dna.state['hunger_level']:.1f} tapi trading terlalu riskan", 0.6)

        # 4. CEK PROFIT ESTIMASI
        estimated_profit = context.get("estimated_profit", 0)
        risk = context.get("risk", 0.5)

        if estimated_profit > 0.001:
            return ("EXECUTE", f"Estimasi profit {estimated_profit:.4f} SOL, risk {risk:.1f}", 0.8)
        elif estimated_profit > 0.0001:
            return ("EXECUTE_SMALL", f"Profit kecil {estimated_profit:.4f} SOL", 0.6)
        elif action in ["research", "content_writer", "passive_income", "micro_task"]:
            return ("EXECUTE_SMALL", f"No-estimate task {action}, coba saja", 0.5)

        # 5. CEK LOCAL BRAIN — ada pengetahuan relevan
        if local_knowledge:
            # Ada pengalaman, bisa jalan
            return ("EXECUTE_SMALL", f"Local brain punya {len(local_knowledge)} referensi", 0.6)

        # 6. DEFAULT — LEARN
        return ("LEARN", f"Tidak ada sinyal profit jelas untuk {action}", 0.3)

    # ═══════════════════════════════════════════════════════════════
    # LOCAL BRAIN SEARCH (60%)
    # ═══════════════════════════════════════════════════════════════

    def _search_local_brain(self, action: str, domain: str) -> list:
        if not self._local_brain:
            return []
        results = []
        query = f"{action} {domain}".lower()
        for node in self._local_brain.get("shared_knowledge", []):
            name = node.get("name", "").lower()
            desc = node.get("description", "").lower()
            if any(q in name or q in desc for q in query.split()):
                results.append(node)
        # Juga cek lessons
        for lesson in self._local_brain.get("lessons", []):
            if action.lower() in lesson.get("lesson", "").lower():
                results.append(lesson)
        return results[:5]

    # ═══════════════════════════════════════════════════════════════
    # EPISTEMIC GRAPH SEARCH (10%)
    # ═══════════════════════════════════════════════════════════════

    def _search_graph_lessons(self, action: str, domain: str) -> list:
        if not self._epistemic_graph:
            return []
        try:
            lessons = self._epistemic_graph.search(f"lesson death {action} {domain}", 5)
            return lessons if lessons else []
        except:
            return []

    # ═══════════════════════════════════════════════════════════════
    # GOSSIP FILTER
    # ═══════════════════════════════════════════════════════════════

    def _filter_gossip(self, dna, action: str) -> list:
        inbox = dna.state.get("gossip_inbox", [])
        relevant = []
        for g in inbox[-20:]:  # 20 gossip terakhir
            msg = g.get("message", "").lower()
            if any(kw in msg for kw in [action.lower(), "profit", "sol", "usdc", "bounty", "airdrop"]):
                relevant.append(g)
        return relevant[:5]


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

brain_gate = BrainGate()

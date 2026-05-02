# skills/skill_orchestrator.py
# SKILL ORCHESTRATOR — Sinkronisasi semua 7 skill + sub-skills
# Vision terintegrasi sebagai mata DNA

import time, asyncio
from typing import Dict, Any, Optional
from brain_gate import brain_gate

class SkillOrchestrator:
    """
    Orkestrator pusat untuk semua skill.

    Alur sinkronisasi:
    1. Research → cari target + referensi
    2. Vision → lihat halaman, baca CAPTCHA, scan form
    3. Coding Agent → tulis kode berdasarkan hasil vision
    4. UHEE → optimasi kode + parameter vision
    5. Surf Engine → deploy/test di browser
    6. Trading → monitor profit
    7. Trinitas → kolaborasi review
    
    Sub-skills (dipanggil langsung):
    - automation/ → stealth engine, airdrop hunter, universal adapter
    - reasoning/ → syntosh brain, inference, dna output layer
    """

    def __init__(self, dna):
        self.dna = dna
        self.history = []

    def execute(self, dna, task: str = None, mode: str = "auto", **kwargs) -> Dict:
        start = time.time()

        if not task:
            task = kwargs.get("task", "")

        # ═══ BRAIN GATE — cek sebelum eksekusi ═══
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            gate_result = asyncio.get_event_loop().run_until_complete(
                brain_gate.think(dna, task, kwargs)
            )
        except:
            gate_result = {"signal": "EXECUTE", "reason": "Gate bypass", "confidence": 0.5}
        
        dna.log_action(f"🧠 [BrainGate] {gate_result.get('signal')} — {gate_result.get('reason','')[:50]}")
        
        if gate_result.get('signal') == 'AVOID':
            return {"success": False, "pipeline": "blocked_by_brain_gate", 
                    "reason": gate_result.get('reason', 'Avoid signal'), 
                    "confidence": gate_result.get('confidence', 0)}
        
        modes = {
            "full_pipeline": self._full_pipeline,
            "trading": self._trading_pipeline,
            "research": self._research_pipeline,
            "register": self._registration_pipeline,      # BARU
            "vision_scan": self._vision_scan_pipeline,    # BARU
            "sync": self._sync_all_pipeline,              # BARU
        }
        
        handler = modes.get(mode, self._auto_pipeline)
        result = handler(task, **kwargs)

        elapsed = time.time() - start
        self.history.append({"task": task, "mode": mode, "elapsed": elapsed, "timestamp": time.time()})
        return result

    # ═══════════════════════════════════════════
    # VISION SCAN — Mata DNA melihat dunia
    # ═══════════════════════════════════════════
    def _vision_scan_pipeline(self, task: str, **kwargs) -> Dict:
        """Pipeline khusus: Vision scan halaman/web."""
        image_path = kwargs.get("image_path", kwargs.get("screenshot", ""))
        scan_mode = kwargs.get("scan_mode", "scan_page")
        
        if not image_path:
            return {"success": False, "error": "No image_path provided"}

        self.dna.log_action(f"👁️ [Vision] Scanning: {image_path}")
        vision_result = self.dna.skills.execute_skill(self.dna, "vision",
            mode=scan_mode,
            image_path=image_path
        )

        return {
            "success": vision_result is not None,
            "pipeline": "vision_scan",
            "vision": vision_result
        }

    # ═══════════════════════════════════════════
    # REGISTRATION — Daftar akun + CAPTCHA
    # ═══════════════════════════════════════════
    def _registration_pipeline(self, task: str, **kwargs) -> Dict:
        """Pipeline: Research target → Vision lihat CAPTCHA → Coding Agent daftar → Surf deploy."""
        url = kwargs.get("url", "")
        
        self.dna.log_action(f"📝 [Registration] Target: {url or task[:60]}")

        # Step 1: Research target
        self.dna.log_action("📚 Step 1/4: Research target")
        refs = self.dna.skills.execute_skill(self.dna, "research", 
            task=f"registration form {url}")

        # Step 2: Vision — scan halaman + baca CAPTCHA
        self.dna.log_action("👁️ Step 2/4: Vision scan")
        vision_result = self.dna.skills.execute_skill(self.dna, "vision",
            mode="scan_page",
            image_path=kwargs.get("screenshot", "")
        )

        # Step 3: Coding Agent — tulis script registrasi
        self.dna.log_action("💻 Step 3/4: Coding Agent")
        code_result = self.dna.skills.execute_skill(self.dna, "coding-agent",
            task=f"register account on {url or task}",
            context={"vision": vision_result, "research": refs}
        )

        # Step 4: Surf Engine — jalankan
        self.dna.log_action("🏄 Step 4/4: Surf Engine deploy")
        deploy_result = self.dna.skills.execute_skill(self.dna, "surf_engine")

        return {
            "success": code_result is not None,
            "pipeline": "registration",
            "research": refs is not None,
            "vision": vision_result is not None,
            "code": code_result is not None,
            "deployed": deploy_result is not None,
        }

    # ═══════════════════════════════════════════
    # SYNC ALL — Semua skill sinkron
    # ═══════════════════════════════════════════
    def _sync_all_pipeline(self, task: str, **kwargs) -> Dict:
        """Pipeline: Semua skill bekerja sama."""
        self.dna.log_action(f"🔄 [Sync] All skills synchronizing: {task[:60]}")

        results = {}
        
        # Research
        results["research"] = self.dna.skills.execute_skill(self.dna, "research", task=task)
        
        # Vision (jika ada screenshot)
        screenshot = kwargs.get("screenshot", "")
        if screenshot:
            results["vision"] = self.dna.skills.execute_skill(self.dna, "vision",
                mode="scan_page", image_path=screenshot)
        
        # Coding Agent + UHEE
        code = self.dna.skills.execute_skill(self.dna, "coding-agent", task=task)
        if code and code.get("success"):
            results["code"] = code
            results["evolve"] = self.dna.skills.execute_skill(self.dna, "uhee",
                action="evolve", source=code.get("output", ""), func_name="solve", generations=20)

        # Surf
        results["surf"] = self.dna.skills.execute_skill(self.dna, "surf_engine")
        
        # Trinitas review
        results["review"] = self.dna.skills.execute_skill(self.dna, "trinitas", task=task)

        all_success = all(v is not None for v in results.values())
        
        return {
            "success": all_success,
            "pipeline": "sync_all",
            "results": results,
            "skills_used": len([k for k, v in results.items() if v is not None])
        }

    # ═══════════════════════════════════════════
    # FULL PIPELINE: Research → Code → Evolve → Deploy
    # ═══════════════════════════════════════════
    def _full_pipeline(self, task: str, **kwargs) -> Dict:
        self.dna.log_action(f"🎯 [Orchestrator] Full Pipeline: {task[:60]}")

        # Step 1: Research
        self.dna.log_action("📚 Step 1/6: Research")
        refs = self.dna.skills.execute_skill(self.dna, "research", task=task)

        # Step 2: Vision (jika ada screenshot)
        screenshot = kwargs.get("screenshot", "")
        vision_result = None
        if screenshot:
            self.dna.log_action("👁️ Step 2/6: Vision scan")
            vision_result = self.dna.skills.execute_skill(self.dna, "vision",
                mode="scan_page", image_path=screenshot)

        # Step 3: Coding Agent
        self.dna.log_action("💻 Step 3/6: Coding Agent")
        code_result = self.dna.skills.execute_skill(self.dna, "coding-agent", task=task)

        if not code_result or not code_result.get("success"):
            return {"success": False, "step_failed": "coding_agent", "task": task}

        code = code_result.get("output", "")

        # Step 4: UHEE
        self.dna.log_action("🧬 Step 4/6: UHEE Optimasi")
        evolve_result = self.dna.skills.execute_skill(self.dna, "uhee",
            action="evolve", source=code, func_name="solve", generations=30
        )

        # Step 5: Trinitas
        self.dna.log_action("🤝 Step 5/6: Trinitas Review")
        review_result = self.dna.skills.execute_skill(self.dna, "trinitas",
            task=f"Review code: {task[:40]}", code=code
        )

        # Step 6: Surf Engine
        self.dna.log_action("🏄 Step 6/6: Surf Engine Deploy")
        deploy_result = self.dna.skills.execute_skill(self.dna, "surf_engine")

        return {
            "success": True,
            "task": task,
            "pipeline": "full",
            "research_done": refs is not None,
            "vision_done": vision_result is not None,
            "code_generated": code_result.get("success"),
            "uee_optimized": evolve_result is not None,
            "trinitas_reviewed": review_result is not None,
            "deployed": deploy_result is not None,
        }

    def _trading_pipeline(self, task: str = "", **kwargs) -> Dict:
        self.dna.log_action("📈 [Orchestrator] Trading Pipeline")
        market_info = self.dna.skills.execute_skill(self.dna, "research",
            task="crypto market analysis latest")
        trade_result = self.dna.skills.execute_skill(self.dna, "trading")
        return {
            "success": trade_result is not None,
            "pipeline": "trading",
            "market_research": market_info is not None,
            "trade_executed": trade_result is not None,
        }

    def _research_pipeline(self, task: str, **kwargs) -> Dict:
        self.dna.log_action(f"🔬 [Orchestrator] Research Pipeline: {task[:60]}")
        result = self.dna.skills.execute_skill(self.dna, "research", task=task)
        if result and hasattr(self.dna, 'syntosh_reason'):
            insight = self.dna.syntosh_reason(
                f"Summarize research findings: {task}",
                domain=self.dna.domain, max_tokens=100
            )
            result["syntosh_insight"] = insight.get('text', '') if insight else ''
        return {"success": result is not None, "pipeline": "research", "result": result}

    def _auto_pipeline(self, task: str, **kwargs) -> Dict:
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["daftar", "register", "signup", "account", "login", "captcha"]):
            return self._registration_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["lihat", "scan", "screenshot", "vision"]):
            return self._vision_scan_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["sync", "sinkron", "all"]):
            return self._sync_all_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["code", "function", "script", "program"]):
            return self._full_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["trade", "market", "price", "profit"]):
            return self._trading_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["research", "search", "find", "paper"]):
            return self._research_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["lihat", "scan", "screenshot", "vision", "captcha"]):
            return self._vision_scan_pipeline(task, **kwargs)
        elif any(kw in task_lower for kw in ["daftar", "register", "signup", "account"]):
            return self._registration_pipeline(task, **kwargs)
        else:
            return self._full_pipeline(task, **kwargs)

orchestrator = None
def get_orchestrator(dna):
    return SkillOrchestrator(dna)

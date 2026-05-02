# skills/auto_evolve_pipeline.py
# Pipeline Kolaborasi: Coding Agent + UHEE
# "Tulis → Evolusi → Deploy"

import json
import time
from typing import Dict, Optional

class AutoEvolvePipeline:
    """
    Pipeline otomatis:
    1. Coding Agent tulis kode awal
    2. UHEE optimasi via evolusi
    3. Deploy hasil terbaik
    """
    
    def __init__(self, dna):
        self.dna = dna
        self.history = []
    
    def execute(self, dna, task: str = None, generations: int = 50, **kwargs) -> Dict:
        """
        Entry point. Dipanggil via skill_manager.
        
        Args:
            task: Deskripsi tugas coding
            generations: Jumlah generasi UHEE
        
        Returns:
            {"success": bool, "code": str, "fitness": float, "generations": int}
        """
        start_time = time.time()
        
        # ═══════════════════════════════════════════
        # STEP 1: CODING AGENT — Tulis kode awal
        # ═══════════════════════════════════════════
        dna.log_action(f"🔧 [Pipeline] Step 1: Coding Agent menulis kode...")
        
        coding_result = dna.skills.execute_skill(dna, "coding-agent", task=task)
        
        if not coding_result:
            return {"success": False, "error": "Coding Agent returned None", "step": "coding_agent"}
        
        # Handle format Coding Agent yang beda
        if coding_result.get("success"):
            # Coding Agent sukses — ambil kode dari file
            script_path = coding_result.get("script_path", "")
            if script_path and __import__('os').path.exists(script_path):
                with open(script_path) as f:
                    initial_code = f.read()
            else:
                initial_code = coding_result.get("output", "")
            func_name = "target_function"
        elif coding_result.get("code"):
            initial_code = coding_result["code"]
            func_name = coding_result.get("func_name", "target_function")
        else:
            return {"success": False, "error": "No code in Coding Agent result", "step": "coding_agent"}
        dna.log_action(f"✅ [Pipeline] Coding Agent selesai ({len(initial_code)} chars)")
        
        # ═══════════════════════════════════════════
        # STEP 2: UHEE — Evolusi kode
        # ═══════════════════════════════════════════
        dna.log_action(f"🧬 [Pipeline] Step 2: UHEE evolusi ({generations} generasi)...")
        
        uhee_result = dna.skills.execute_skill(dna, "uhee",
            action="evolve",
            source=initial_code,
            func_name=func_name,
            generations=generations
        )
        
        if not uhee_result:
            # Fallback: pake kode awal
            dna.log_action(f"⚠️ [Pipeline] UHEE gagal, pakai kode awal")
            best_code = initial_code
            best_fitness = 0.0
        else:
            best_code = uhee_result.get("code", initial_code)
            best_fitness = uhee_result.get("fitness", 0.0)
            dna.log_action(f"✅ [Pipeline] UHEE selesai (fitness: {best_fitness:.4f})")
        
        # ═══════════════════════════════════════════
        # STEP 3: DEPLOY — Simpan hasil
        # ═══════════════════════════════════════════
        dna.log_action(f"💾 [Pipeline] Step 3: Deploy...")
        
        # Simpan ke workspace
        import os
        workspace = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'evolved')
        os.makedirs(workspace, exist_ok=True)
        
        filename = f"{func_name}_gen{generations}_{int(time.time())}.py"
        filepath = os.path.join(workspace, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"# Auto-Evolved by UHEE Pipeline\n")
            f.write(f"# Task: {task}\n")
            f.write(f"# Generations: {generations}\n")
            f.write(f"# Fitness: {best_fitness:.4f}\n")
            f.write(f"# DNA: {dna.dna_id}\n\n")
            f.write(best_code)
        
        elapsed = time.time() - start_time
        
        # Record history
        record = {
            "dna_id": dna.dna_id,
            "task": task,
            "generations": generations,
            "fitness": best_fitness,
            "file": filepath,
            "elapsed": round(elapsed, 1),
            "timestamp": time.time()
        }
        self.history.append(record)
        
        dna.log_action(f"🎉 [Pipeline] Selesai! Fitness: {best_fitness:.4f} | Time: {elapsed:.1f}s")
        
        return {
            "success": True,
            "code": best_code,
            "fitness": best_fitness,
            "generations": generations,
            "file": filepath,
            "elapsed": elapsed
        }

# Singleton
auto_evolve = None

def get_pipeline(dna):
    return AutoEvolvePipeline(dna)

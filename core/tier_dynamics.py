# core/tier_dynamics.py
# Sistem Kasta Dinamis — 300 DNA Abadi
# Yang bawah bisa naik, yang atas bisa turun

import random, time
from typing import List

class TierDynamics:
    """
    Mengatur naik-turun tier 300 DNA.
    Bottom 100 → agresif mode (mutasi gede, task banyak).
    Top 100 → stabil mode (resource penuh).
    """
    
    def __init__(self):
        self.cycle_count = 0
    
    def apply(self, all_dna: List) -> List:
        """
        Terapkan tier dynamics ke semua DNA.
        Return DNA yang udah di-update tier-nya.
        """
        self.cycle_count += 1
        
        # Sort by profit (tertinggi ke terendah)
        sorted_dna = sorted(all_dna, key=lambda d: d.total_profit, reverse=True)
        total = len(sorted_dna)
        
        top_cut = total // 3
        mid_cut = 2 * total // 3
        
        for i, dna in enumerate(sorted_dna):
            old_tier = dna.state.get("tier_letter", "C")
            
            if i < top_cut:
                # TOP 100 — Elite
                dna.state["tier_letter"] = "S" if i < top_cut // 2 else "A"
                dna.state["tier_score"] = 0.9
                dna.state["role"] = "alpha_predator"
                dna.state["mutation_rate"] = 0.005
                dna.state["task_multiplier"] = 1.0
                
            elif i < mid_cut:
                # MID 100 — Normal
                dna.state["tier_letter"] = "B" if i < (top_cut + mid_cut) // 2 else "C"
                dna.state["tier_score"] = 0.5
                dna.state["role"] = "hunter"
                dna.state["mutation_rate"] = 0.01
                dna.state["task_multiplier"] = 1.2
                
            else:
                # BOTTOM 100 — Agresif Mode 🔥
                dna.state["tier_letter"] = "D" if i < (mid_cut + total) // 2 else "E"
                dna.state["tier_score"] = 0.2
                dna.state["role"] = "berserker"  # Mode agresif
                dna.state["mutation_rate"] = 0.03  # 3x mutasi
                dna.state["task_multiplier"] = 2.0  # 2x task
                dna.state["risk_tolerance"] = 0.9  # Ambil risiko tinggi
                
                # Trigger agresif mode
                dna.brain.mutate(rate=0.03)
                dna.state["dream_cycle"] += 1
                dna.log_action(f"🔥 BERSERKER MODE: mut=3x, task=2x, risk=high")
            
            # Log perubahan tier
            if dna.state["tier_letter"] != old_tier:
                dna.log_action(f"🏅 TIER {old_tier}→{dna.state['tier_letter']} | rank={i+1}/{total}")
            
            dna._write_identity()
        
        return sorted_dna
    
    def get_stats(self, all_dna: List) -> dict:
        """Statistik distribusi tier."""
        tiers = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for dna in all_dna:
            t = dna.state.get("tier_letter", "C")
            tiers[t] = tiers.get(t, 0) + 1
        return {
            "cycle": self.cycle_count,
            "tier_distribution": tiers,
            "total_dna": len(all_dna),
        }

tier_dynamics = TierDynamics()

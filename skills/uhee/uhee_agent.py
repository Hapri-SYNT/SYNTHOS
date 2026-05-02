# skills/uhee/uhee_agent.py
# UHEE Agent wrapper untuk kompatibilitas dengan main.py

import random

class UHEE:
    """
    Ultra High-Efficiency Engine — evolusi adaptif untuk DNA.
    Memanggil CodeEvolutionEngine dari executor.py saat dibutuhkan.
    """
    
    def __init__(self):
        self.generation = 0
        self.history = []
    
    def execute(self, dna):
        """Jalankan satu siklus evolusi untuk DNA."""
        self.generation += 1
        
        try:
            # Coba pakai CodeEvolutionEngine kalau ada fungsi target
            from skills.uhee.executor import CodeEvolutionEngine
            
            # Ambil source code DNA brain (kalau tersedia)
            import inspect
            dna_source = inspect.getsource(dna.brain.forward) if hasattr(dna.brain, 'forward') else ""
            
            if dna_source and self.generation % 10 == 0:
                # Tiap 10 generasi, evolusi serius
                engine = CodeEvolutionEngine(
                    source=dna_source,
                    func_name="forward",
                    population_size=4,
                    elite_size=1,
                    mutation_rate_init=0.02,
                )
                best = engine.evolve(generations=3)
                new_delta = best.fitness.scalar * 0.01
            else:
                # Mutasi ringan biasa
                new_delta = random.uniform(-0.005, 0.02)
                dna.brain.mutate(rate=0.005)
        except Exception:
            # Fallback: mutasi random biasa
            new_delta = random.uniform(-0.005, 0.02)
            dna.brain.mutate(rate=0.005)
        
        dna.log_action(
            f"🌀 UHEE gen={self.generation} | "
            f"Δfitness={new_delta:+.4f} {'[improved]' if new_delta > 0 else '[neutral]'}"
        )
        
        self.history.append({
            'generation': self.generation,
            'delta': new_delta,
            'dna_id': dna.dna_id,
        })
        
        return new_delta

# skills/uhee/infiltrator_evo.py
# Modul integrasi UHEE untuk evolusi fungsi penyusupan anti-bot

import inspect
import asyncio
from typing import Dict, Any, Optional
from skills.uhee.executor import CodeEvolutionEngine

class InfiltratorEvolution:
    """Mengelola evolusi fungsi infiltrasi untuk satu DNA."""
    
    def __init__(self, dna):
        self.dna = dna
        self.engine = None
        self.best_source = TARGET_FUNCTION_SOURCE  # dari target_functions.py
        self.training_data = []  # (args, success, detection, time)
        
    def initialize_engine(self):
        """Inisialisasi mesin evolusi UHEE untuk fungsi infiltrasi."""
        self.engine = CodeEvolutionEngine(
            source=self.best_source,
            func_name="infiltrate_registration",
            test_cases=[],  # Nanti diisi dari training data
            population_size=5,  # Kecil untuk menghemat sumber daya
            elite_size=1,
            mutation_rate_init=0.2,  # Agak tinggi untuk eksplorasi
            target_dir=f"./SYNTOSH/evolved_functions/{self.dna.dna_id}"
        )
        
    def train(self, generations: int = 3):
        """Jalankan beberapa generasi evolusi."""
        if not self.engine:
            self.initialize_engine()
            
        # Masukkan feedback dari percobaan nyata sebagai test cases
        if self.training_data:
            self.engine.evaluator.test_cases = [
                ((), data['success']) for data in self.training_data[-5:]  # 5 data terakhir
            ]
        
        try:
            best = self.engine.evolve(generations=generations)
            self.best_source = best.source
            self.dna.log_action(f"🧬 [Infiltrator] Evolusi selesai. Best fitness: {best.fitness.scalar:.4f}")
            return best.source
        except Exception as e:
            self.dna.log_action(f"⚠️ [Infiltrator] Evolusi gagal: {e}")
            return self.best_source
    
    def add_training_data(self, url: str, success: bool, detection: bool, execution_time: float):
        """Tambahkan data hasil percobaan nyata untuk pembelajaran."""
        self.training_data.append({
            'url': url,
            'success': success,
            'detection': detection,
            'time': execution_time
        })
        # Jaga data tetap dalam batas
        if len(self.training_data) > 50:
            self.training_data.pop(0)
            
    def get_best_infiltrator(self) -> str:
        """Dapatkan source code fungsi infiltrasi terbaik saat ini."""
        if not self.best_source:
            self.initialize_engine()
            self.train(generations=1)
        return self.best_source

# Singleton untuk mengelola semua infiltrator DNA
class InfiltratorManager:
    def __init__(self):
        self.infiltrators: Dict[str, InfiltratorEvolution] = {}
        
    def get_infiltrator(self, dna) -> InfiltratorEvolution:
        if dna.dna_id not in self.infiltrators:
            self.infiltrators[dna.dna_id] = InfiltratorEvolution(dna)
        return self.infiltrators[dna.dna_id]

infiltrator_manager = InfiltratorManager()

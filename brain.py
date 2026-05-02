# brain.py — Quantum Brain Trainer + Forgetting Mechanism
# Disimpan di root project: /root/AI/brain.py

import time
import numpy as np
from typing import Any, Dict, List, Optional
from config import logger


class PatternExtractor:
    """Ekstrak inti pengetahuan dari interaksi."""
    
    @staticmethod
    def extract(interaction: Dict) -> Optional[Dict]:
        """
        Extract pattern dari obrolan/eksekusi.
        Return knowledge node atau None (kalau sampah).
        """
        text = interaction.get("text", "")
        result = interaction.get("result", "")
        success = interaction.get("success", False)
        emotion = interaction.get("emotion", "neutral")
        
        # Kalau terlalu pendek / ga informatif → sampah
        if len(text) < 10 and not result:
            return None
        
        # Ekstrak keywords
        keywords = PatternExtractor._extract_keywords(text)
        if not keywords:
            return None
        
        # Bobot berdasarkan success/emotion
        weight = 0.3  # default
        if success:
            weight = 0.8
        if emotion == "excited":
            weight += 0.1
        elif emotion == "fearful":
            weight += 0.1  # Pengalaman menakutkan juga penting
        
        return {
            "keywords": keywords,
            "pattern": text[:200],
            "result": result[:200] if result else "",
            "weight": weight,
            "timestamp": time.time(),
            "type": interaction.get("type", "chat"),
        }
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Ekstrak keyword dari teks."""
        stopwords = {"ini", "itu", "dan", "atau", "yang", "di", "ke", "dari", "gua", "gue", "lo", "lu"}
        words = text.lower().split()
        keywords = []
        for w in words:
            w = w.strip(",.!?\"'")
            if len(w) > 2 and w not in stopwords:
                keywords.append(w)
        return keywords[:10]  # Max 10 keywords


class ForgettingMechanism:
    """Hapus memori yang tidak bermanfaat."""
    
    @staticmethod
    def should_keep(node: Dict, current_time: float) -> bool:
        """Apakah knowledge node ini masih berguna?"""
        age = current_time - node.get("timestamp", 0)
        weight = node.get("weight", 0.3)
        
        # Rumus: weight * e^(-age/7hari)
        decay = weight * np.exp(-age / 604800)  # 7 hari
        
        # Keep kalau decay > 0.05
        return decay > 0.05
    
    @staticmethod
    def clean(brain_dna: np.ndarray, nodes: List[Dict], current_time: float) -> tuple:
        """Hapus node yang udah decay, return brain + nodes bersih."""
        keep_indices = []
        for i, node in enumerate(nodes):
            if ForgettingMechanism.should_keep(node, current_time):
                keep_indices.append(i)
        
        if len(keep_indices) < len(nodes):
            # Ada yang dihapus — kecilkan brain
            new_brain = brain_dna[keep_indices] if keep_indices else brain_dna[:1]
            new_nodes = [nodes[i] for i in keep_indices]
            logger.debug(f"🧹 Forgetting: {len(nodes) - len(keep_indices)} nodes dihapus")
            return new_brain, new_nodes
        
        return brain_dna, nodes


class BrainTrainer:
    """Training real-time ke QuantumSparseDNA."""
    
    def __init__(self):
        self.knowledge_nodes: List[Dict] = []
        self.max_nodes = 1000  # Maks 1000 nodes di brain
    
    def train(self, dna: Any, interaction: Dict) -> bool:
        """
        Training satu interaksi ke brain DNA.
        Return True kalau berhasil belajar.
        """
        # 1. Ekstrak pattern
        pattern = PatternExtractor.extract(interaction)
        if not pattern:
            return False
        
        # 2. Cek duplikat
        for node in self.knowledge_nodes[-50:]:
            if node.get("pattern") == pattern["pattern"]:
                # Update weight aja
                node["weight"] = min(1.0, node["weight"] + 0.05)
                node["timestamp"] = time.time()
                return False
        
        # 3. Simpan
        self.knowledge_nodes.append(pattern)
        if len(self.knowledge_nodes) > self.max_nodes:
            # Forgetting
            dna.brain.dna, self.knowledge_nodes = ForgettingMechanism.clean(
                dna.brain.dna, self.knowledge_nodes, time.time()
            )
        
        # 4. Mutate brain dengan pattern baru
        try:
            # Konversi keywords ke vector
            keyword_hash = sum(hash(k) % 1000 for k in pattern["keywords"])
            rate = min(0.05, pattern["weight"] * 0.05)  # Max 5% mutation
            
            # Targeted mutation: cuma mutate bagian tertentu
            target_idx = keyword_hash % dna.brain.dna_size
            noise = np.random.randn(1, dna.brain.latent_dim).astype(np.float16) * rate
            dna.brain.dna[target_idx:target_idx+1] += noise
            
            dna.log_action(f"🧠 Learned: {pattern['keywords'][:3]} (weight: {pattern['weight']:.2f})")
            return True
        except Exception as e:
            logger.error(f"Brain training error: {e}")
            return False


# Singleton
brain_trainer = BrainTrainer()

# SYNTOSH Inference v18 — DNA dan SYNTOSH SATU TUBUH
import numpy as np, json, os
from skills.reasoning.dna_output_layer import QuantumSparseDNA_NP

class UnifiedSYNTOSH:
    """
    DNA dan SYNTOSH jadi satu sistem.
    - DNA mempengaruhi steering
    - Steering mempengaruhi DNA
    - Keduanya bermutasi bersama
    """
    def __init__(self, weight_dir="SYNTOSH", dna_size=128):
        from skills.reasoning.syntosh_brain import SYNTOSHBrain
        
        print("🧬 Initializing UNIFIED SYNTOSH + DNA...")
        
        # --- SYNTOSH ---
        self.brain = SYNTOSHBrain()
        self.token_to_id = {}
        self.id_to_token = {}
        self.global_ids = {}
        
        with open(os.path.join(weight_dir, "word_vocab.json")) as f:
            data = json.load(f)
            for word, info in data.items():
                lid = info['local_id']
                self.token_to_id[word] = lid
                self.id_to_token[lid] = word
                self.global_ids[lid] = info['global_id']
        
        w_raw = self.brain.load("gpt_embed_weight")
        # Auto-detect shape: GPT2 = (50257, 768), SmolLM2 = (49152, 960)
        total = w_raw.size
        if total == 50257 * 768:
            self.w_embed = w_raw.reshape(50257, 768)
        elif total == 49152 * 960:
            self.w_embed = w_raw.reshape(49152, 960)
        else:
            # Generic: coba tebak dari vocab size
            d_model = 768  # default GPT2
            vocab = total // d_model
            self.w_embed = w_raw.reshape(vocab, d_model)
        self.w_embed = np.nan_to_num(self.w_embed, nan=0.0)
        self.w_embed = np.clip(self.w_embed, -10, 10)
        self.vocab_size = len(self.id_to_token)
        
        concept_file = os.path.join(weight_dir, "concept_vectors.npz")
        self.concepts = dict(np.load(concept_file, allow_pickle=True)) if os.path.exists(concept_file) else {}
        
        # v_neutral
        latin_ids = []
        for word, info in data.items():
            if any(c.isascii() and c.isalpha() for c in word):
                latin_ids.append(self.global_ids.get(info['local_id'], 0))
        sample = np.random.choice(latin_ids, min(3000, len(latin_ids)), replace=False)
        self.v_neutral = np.mean(self.w_embed[sample], axis=0)
        
        # --- DNA (128 gen, tiap gen = 128 dimensi STEERING) ---
        self.dna = QuantumSparseDNA_NP(dna_size=dna_size, latent_dim=128)
        # Proyeksi dua arah: 960 ↔ 128
        self.proj_down = np.random.randn(960, 128).astype(np.float16) * 0.01   # 960 → 128
        self.proj_up = np.random.randn(128, 960).astype(np.float16) * 0.01     # 128 → 960
        
        # --- DNA memory (gen menyimpan "pengalaman") ---
        self.dna_memory = []  # rekam vektor steering + output bagus
        
        print(f"🧠 UNIFIED SYNTOSH ready")
        print(f"   Vocab: {self.vocab_size} | Concepts: {len(self.concepts)}")
        print(f"   DNA: {dna_size} genes | Latin anchors: {len(latin_ids)}")

    def steer_with_dna(self, v_contrast, context_vec):
        """
        Steering DIPENGARUHI DNA.
        v_contrast: dari concept
        context_vec: dari token terakhir
        DNA memberikan "bumbu" ke steering
        """
        # Gabungin concept steer + context
        v_combined = v_contrast * 0.4 + context_vec * 0.6
        
        # Proyeksi ke ruang DNA
        v_dna = v_combined @ self.proj_down  # [128]
        
        # DNA forward: generate dynamic weight
        W = self.dna.forward(v_dna.reshape(1, -1))  # [128, 128]
        
        # DNA "memodulasi" steering: v_dna → v_dna_modulated
        v_dna_mod = v_dna.reshape(1, -1) @ W.T  # [1, 128]
        
        # Proyeksi balik ke 960
        dna_modulation = v_dna_mod @ self.proj_up  # [1, 960]
        
        # Steering akhir = concept + context + DNA
        v_final = v_contrast * 0.3 + context_vec * 0.5 + dna_modulation.flatten() * 0.2
        
        return v_final, W

    def generate(self, prompt="", concept=None, mix_concepts=None,
                 max_tokens=12, temperature=0.9, alpha=5.0):
        np.random.seed(None)
        tokens = [self.token_to_id.get(w, 0) for w in prompt.lower().split()] if prompt else [0]
        generated = []
        seen_tokens = {}
        
        # Concept steering
        v_contrast = np.zeros(960)
        if mix_concepts:
            for c in mix_concepts:
                if c in self.concepts:
                    v_contrast += (self.concepts[c] - self.v_neutral)
            v_contrast = v_contrast / len(mix_concepts) * alpha
        elif concept and concept in self.concepts:
            v_contrast = (self.concepts[concept] - self.v_neutral) * alpha
        
        for step in range(max_tokens):
            # Context dari token terakhir
            last_gid = self.global_ids.get(tokens[-1] % self.vocab_size, 0)
            context_vec = self.w_embed[last_gid]
            
            # STEER DENGAN DNA (DNA ikut mempengaruhi)
            v_final, W_dna = self.steer_with_dna(v_contrast, context_vec)
            
            # Output: pakai DNA weight W_dna untuk decode
            next_id = self._decode_with_dna(v_final, W_dna, temperature)
            
            retry = 0
            while next_id in seen_tokens and retry < 3:
                v_noisy = v_final + np.random.randn(960).astype(np.float16) * 0.02
                next_id = self._decode_with_dna(v_noisy, W_dna, temperature * 1.2)
                retry += 1
            
            seen_tokens[next_id] = seen_tokens.get(next_id, 0) + 1
            generated.append(next_id)
            tokens.append(next_id)
            
            # DNA "belajar": rekam pasangan (v_dna, token)
            if len(generated) > 1:
                self.dna_memory.append({
                    'v_final': v_final.copy(),
                    'token': next_id,
                    'concept': concept
                })
        
        return ' '.join(self.id_to_token.get(t % self.vocab_size, '?') for t in generated)

    def _decode_with_dna(self, v_final, W_dna, temperature=1.0):
        """Decode hidden state ke token menggunakan DNA weight"""
        top_k = min(5000, self.vocab_size)
        sample_ids = np.random.choice(self.vocab_size, top_k, replace=False)
        
        sample_embs = []
        for sid in sample_ids:
            gid = self.global_ids.get(sid, 0) % 49152
            sample_embs.append(self.w_embed[gid])
        sample_embs = np.array(sample_embs, dtype=np.float32)
        
        # Proyeksi ke ruang DNA
        sample_dna = sample_embs @ self.proj_down.astype(np.float32)  # [top_k, 128]
        
        # Transformasi via DNA
        transformed = sample_dna @ W_dna.astype(np.float32).T  # [top_k, 128]
        
        # v_final juga diproyeksi
        v_dna = (v_final.reshape(1, -1) @ self.proj_down.astype(np.float32))  # [1, 128]
        
        # Logits = dot product
        logits = (transformed @ v_dna.T).flatten()
        
        logits = np.nan_to_num(logits, nan=-1e9)
        logits = logits / max(temperature, 0.01)
        logits = logits - logits.max()
        probs = np.exp(logits)
        
        if probs.sum() <= 0:
            probs = np.ones(top_k) / top_k
        else:
            probs = probs / probs.sum()
        
        chosen_idx = np.random.choice(top_k, p=probs)
        return sample_ids[chosen_idx]

    def mutate(self, rate=0.01):
        """Mutasi DNA + proyeksi secara simultan"""
        self.dna.mutate(rate)
        self.proj_down += np.random.randn(*self.proj_down.shape).astype(np.float16) * rate * 0.05
        self.proj_up += np.random.randn(*self.proj_up.shape).astype(np.float16) * rate * 0.05
        print(f"🧬 UNIFIED mutation (rate={rate})")

    def evolve(self, iterations=10, rate=0.02):
        """Evolutionary selection: pilih output dengan token Latin terbanyak"""
        best_latin = 0
        for i in range(iterations):
            output = self.generate(concept="trade", max_tokens=8)
            latin_count = sum(1 for t in output.split() if any(c.isascii() and c.isalpha() for c in t))
            
            if latin_count >= best_latin:
                best_latin = latin_count
                best_state = {
                    'dna': self.dna.dna.copy(),
                    'proj_down': self.proj_down.copy(),
                    'proj_up': self.proj_up.copy()
                }
                print(f"  Gen {i}: {output} (Latin: {latin_count}) ✅")
            else:
                # Kembalikan ke best state
                self.dna.dna = best_state['dna'].copy()
                self.proj_down = best_state['proj_down'].copy()
                self.proj_up = best_state['proj_up'].copy()
                self.mutate(rate)
                print(f"  Gen {i}: reverted, mutate")

# Singleton
syntosh_infer = UnifiedSYNTOSH()

if __name__ == "__main__":
    print("\nFree:", syntosh_infer.generate(max_tokens=10))
    print("Trade:", syntosh_infer.generate(concept="trade", max_tokens=10))
    print("Money:", syntosh_infer.generate(concept="money", max_tokens=10))

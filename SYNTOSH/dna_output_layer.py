# dna_output_layer.py — QuantumSparseDNA sebagai output projection SYNTOSH
import numpy as np
from collections import OrderedDict
import threading

SPARSITY_GENES = 0.25

class QuantumSparseDNA_NP:
    def __init__(self, dna_size=128, latent_dim=128):
        self.dna = np.random.randn(dna_size, latent_dim).astype(np.float16) * 0.01
        self.dna_size, self.latent_dim = dna_size, latent_dim
        self.weight_cache = OrderedDict()
        self._lock = threading.RLock()

    def forward(self, input_vec):
        if input_vec.ndim == 1:
            input_vec = input_vec.reshape(1, -1)
        if input_vec.shape[1] > self.latent_dim:
            input_vec = input_vec[:, :self.latent_dim]
        elif input_vec.shape[1] < self.latent_dim:
            pad = np.zeros((input_vec.shape[0], self.latent_dim - input_vec.shape[1]))
            input_vec = np.hstack([input_vec, pad])
        
        emb = input_vec.astype(np.float16)
        cache_key = hash(emb.tobytes()) % 10000
        
        with self._lock:
            if cache_key in self.weight_cache:
                self.weight_cache.move_to_end(cache_key)
                return self.weight_cache[cache_key]
        
        scores = emb @ self.dna.T
        k = max(1, int(self.dna_size * SPARSITY_GENES))
        indices = np.argpartition(scores[0], -k)[-k:]
        active = self.dna[indices]
        
        a = active.mean(axis=0)
        b = active[::-1].mean(axis=0)
        w = np.outer(a, b)
        
        # Handle NaN / Inf
        w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Thresholding
        if np.abs(w).max() > 0:
            threshold = np.percentile(np.abs(w), 90)
            w[np.abs(w) < threshold] = 0
        
        w = np.round(w * 3) / 3
        
        # Normalisasi dengan safety
        norm = np.linalg.norm(w)
        if norm < 1e-8:
            w = np.eye(self.latent_dim, dtype=np.float16) / self.latent_dim
        else:
            w = w / norm
        
        with self._lock:
            self.weight_cache[cache_key] = w
            if len(self.weight_cache) > 50:
                self.weight_cache.popitem(last=False)
        
        return w.astype(np.float16)

    def mutate(self, rate=0.01):
        self.dna += np.random.randn(*self.dna.shape).astype(np.float16) * rate
        self.clear_cache()

    def clear_cache(self):
        with self._lock:
            self.weight_cache.clear()


class DNAOutputLayer:
    def __init__(self, w_embed, global_ids, vocab_size, dna_size=128):
        self.w_embed = w_embed
        self.global_ids = global_ids
        self.vocab_size = vocab_size
        self.dna = QuantumSparseDNA_NP(dna_size=dna_size, latent_dim=dna_size)
        self.proj = np.random.randn(960, dna_size).astype(np.float16) * 0.01
        print(f"🧬 DNA Output Layer ready ({dna_size} genes)")

    def forward(self, hidden_state, temperature=1.0, top_k=100):
        if hidden_state.ndim == 1:
            hidden_state = hidden_state.reshape(1, -1)
        
        v_proj = hidden_state @ self.proj.astype(np.float32)
        W = self.dna.forward(v_proj.astype(np.float16))
        
        top_k = min(top_k, self.vocab_size)
        sample_ids = np.random.choice(self.vocab_size, top_k, replace=False)
        
        sample_embs = []
        for sid in sample_ids:
            gid = self.global_ids.get(sid, 0) % 49152
            sample_embs.append(self.w_embed[gid])
        sample_embs = np.array(sample_embs, dtype=np.float32)
        
        sample_proj = sample_embs @ self.proj.astype(np.float32)
        transformed = sample_proj @ W.astype(np.float32).T
        logits = (transformed @ v_proj.astype(np.float32).T).flatten()
        
        # Handle NaN di logits
        logits = np.nan_to_num(logits, nan=-1e9, posinf=1e9, neginf=-1e9)
        logits = logits / max(temperature, 0.01)
        logits = logits - logits.max()
        probs = np.exp(logits)
        
        # Safety: kalau semua 0, uniform
        if probs.sum() <= 0 or np.any(np.isnan(probs)):
            probs = np.ones(top_k) / top_k
        else:
            probs = probs / probs.sum()
        
        chosen_idx = np.random.choice(top_k, p=probs)
        return sample_ids[chosen_idx]

    def mutate(self, rate=0.01):
        self.dna.mutate(rate)
        self.proj += np.random.randn(*self.proj.shape).astype(np.float16) * rate * 0.1
        print(f"🧬 DNA mutated (rate={rate})")

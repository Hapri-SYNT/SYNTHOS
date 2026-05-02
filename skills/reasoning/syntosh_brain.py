# skills/reasoning/syntosh_brain.py — SYNTOSH Shared Brain
# Semua DNA pakai ini bareng. 1 instance, 190 DNA, reasoning unik.

import threading
import numpy as np
import os

class SYNTOSHBrain:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, weight_dir: str = "SYNTOSH"):
        if self._initialized:
            return
        self.weight_dir = weight_dir
        self._cache = {}
        self._initialized = True
        print(f"🧠 SYNTOSH shared brain ready ({weight_dir})")

    def load(self, name: str) -> np.ndarray:
        if name in self._cache:
            return self._cache[name]
        fname = name.replace('/', '_').replace('.', '_') + '.npy'
        path = os.path.join(self.weight_dir, fname)
        if not os.path.exists(path):
            matches = [f for f in os.listdir(self.weight_dir) if name.replace('.', '_') in f]
            if matches:
                path = os.path.join(self.weight_dir, matches[0])
            else:
                raise FileNotFoundError(f"Tensor {name} not found")
        with self._lock:
            if name in self._cache:
                return self._cache[name]
            arr = np.load(path)
            self._cache[name] = arr
            return arr

    def embed(self, token_ids: np.ndarray) -> np.ndarray:
        w = self.load("gpt_embed_weight")
        return w[token_ids]

    def layer_norm(self, x: np.ndarray, name: str) -> np.ndarray:
        w = self.load(f"{name}_weight").reshape(-1)
        dim = x.shape[-1]
        eps = 1e-5
        mean = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        return w[:dim] * (x - mean) / np.sqrt(var + eps)

    def attention(self, x: np.ndarray, layer: int) -> np.ndarray:
        blk = f"blk.{layer}"
        dim = x.shape[-1]
        
        w_q = self.load(f"{blk}.attn_q.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        w_k = self.load(f"{blk}.attn_k.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        w_v = self.load(f"{blk}.attn_v.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        w_o = self.load(f"{blk}.attn_output.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        
        q = x @ w_q.T
        k = x @ w_k.T
        v = x @ w_v.T
        
        scores = q @ k.T / np.sqrt(max(dim, 1))
        attn = np.exp(scores - scores.max()) / (np.exp(scores - scores.max()).sum(axis=-1, keepdims=True) + 1e-12)
        
        return (attn @ v) @ w_o.T

    def feed_forward(self, x: np.ndarray, layer: int) -> np.ndarray:
        blk = f"blk.{layer}"
        dim = x.shape[-1]
        
        w_gate = self.load(f"{blk}.ffn_gate.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        w_up = self.load(f"{blk}.ffn_up.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        w_down = self.load(f"{blk}.ffn_down.weight").reshape(-1)[:dim*dim].reshape(dim, dim)
        
        gate = x @ w_gate.T
        silu = gate / (1 + np.exp(-gate))
        
        return (silu * (x @ w_up.T)) @ w_down.T

    def forward(self, x: np.ndarray, n_layers: int = 30) -> np.ndarray:
        for i in range(n_layers):
            attn_out = self.attention(x, i)
            x = x + attn_out
            x = self.layer_norm(x, f"blk.{i}.attn_norm")
            ffn_out = self.feed_forward(x, i)
            x = x + ffn_out
            x = self.layer_norm(x, f"blk.{i}.ffn_norm")
        return self.layer_norm(x, "output_norm")

    def reason(self, token_ids: np.ndarray, knowledge_nodes: list) -> dict:
        x = self.embed(token_ids)
        base = self.forward(x)
        kw = min(1.0, len(knowledge_nodes) / 100)
        combined = base * (1.0 - kw * 0.3)
        if knowledge_nodes:
            kb_vec = np.mean([np.array(n.get('embedding', [0]*960)) for n in knowledge_nodes[:10]], axis=0)
            combined = combined + kb_vec * kw * 0.5
        norm = np.linalg.norm(combined)
        if norm > 0: combined = combined / norm
        return {"embedding": combined, "knowledge_used": len(knowledge_nodes), "confidence": min(1.0, 0.5 + kw * 0.3)}

syntosh = SYNTOSHBrain()

# nano_vocab.py — Structured vocab dengan weight links

import json, numpy as np, os
from skills.reasoning.syntosh_brain import syntosh

class NanoVocab:
    """Structured vocabulary dengan embedding + attention links."""
    
    def __init__(self):
        self.token_to_id = {}
        self.id_to_token = {}
        self.token_vectors = {}  # token → embedding
        self.token_links = {}    # token → [related tokens via attention]
        
    def build(self, vocab_file="syntosh_vocab.json", weight_dir="SYNTOSH"):
        print("🧬 Building nano-structured vocab...")
        
        # Load vocab
        with open(vocab_file) as f:
            data = json.load(f)
            self.token_to_id = data['token_to_id']
            self.id_to_token = data['id_to_token']
        
        # Load embedding weight
        w_embed = syntosh.load("token_embd_weight")  # [49152, 960]
        
        # Ekstrak embedding per token
        for token, idx in list(self.token_to_id.items())[:10000]:  # 10K token pertama
            idx_int = int(idx)
            if idx_int < len(w_embed):
                vec = w_embed[idx_int]
                self.token_vectors[token] = {
                    'embedding': vec.tolist()[:10],  # 10 dimensi pertama
                    'norm': float(np.linalg.norm(vec)),
                    'idx': idx_int
                }
        
        # Bikin semantic links via attention weight
        w_attn = syntosh.load("blk.0.attn_q.weight")  # [960, 960]
        
        # Cosine similarity antar token (sample 1000 token)
        tokens_sample = list(self.token_vectors.keys())[:1000]
        for i, t1 in enumerate(tokens_sample):
            v1 = w_embed[self.token_vectors[t1]['idx']]
            similarities = []
            for t2 in tokens_sample:
                if t1 != t2:
                    v2 = w_embed[self.token_vectors[t2]['idx']]
                    sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
                    if sim > 0.5:  # Threshold kemiripan
                        similarities.append((t2, float(sim)))
            similarities.sort(key=lambda x: x[1], reverse=True)
            self.token_links[t1] = similarities[:5]  # Top 5 semantic neighbors
        
        print(f"   Tokens with vectors: {len(self.token_vectors)}")
        print(f"   Tokens with links: {len(self.token_links)}")
        
    def search(self, query: str) -> dict:
        """Cari token + semantic neighbors + weight path."""
        if query in self.token_vectors:
            result = {
                'token': query,
                'vector': self.token_vectors[query],
                'neighbors': self.token_links.get(query, []),
                'weight_path': f"token → token_embd_weight[{self.token_vectors[query]['idx']}] → attn_q → attn_k → ..."
            }
            return result
        
        # Fuzzy search
        matches = [(t, self.token_vectors[t]['norm']) for t in self.token_vectors if query.lower() in t.lower()]
        matches.sort(key=lambda x: x[1], reverse=True)
        return {'token': query, 'fuzzy_matches': matches[:10]}

# Build
nano = NanoVocab()
nano.build()

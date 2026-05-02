"""
DeepReader Integration - Final
==============================

Menghubungkan semua modul DeepReader:
1. parsers/gguf_parser.py   → extract metadata dari GGUF (tanpa weight)
2. QuantumSparseDNA_NP      → lightweight reasoning (sudah ada di modul lain)
3. attention/attention_modules.py → analisis attention matrix
4. activations/transformer_lens.py → hook & cache (opsional)

Tidak perlu adjust weight. QuantumSparseDNA sudah dalam bentuk perasan.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict

# ===========================================================================
# IMPORT MODUL INTERNAL DEEPREADER
# ===========================================================================

# Import GGUF Parser (dari parsers/gguf_parser.py)
import sys
sys.path.insert(0, str(Path(__file__).parent / "parsers"))
from gguf_parser import GGUFReader, GGUFKnowledgeExporter, GGUFRemoteReader

# Import Attention Modules (dari attention/attention_modules.py)
sys.path.insert(0, str(Path(__file__).parent / "attention"))
from attention_modules import AttentionMatrix, TokenToToken, HeadView, NeuronView

# Import TransformerLens (dari activations/transformer_lens.py)
sys.path.insert(0, str(Path(__file__).parent / "activations"))
from transformer_lens import (
    HookedTransformer, HookedTransformerConfig, 
    ActivationCache, LogitLens, HeadDetector
)

# Import QuantumSparseDNA (dari modul lain yang sudah jalan)
# Sesuaikan path-nya dengan lokasi DNA module lu
try:
    from quantum_sparse_dna import QuantumSparseDNA_NP
    DNA_AVAILABLE = True
except ImportError:
    try:
        from dna.quantum_sparse import QuantumSparseDNA_NP
        DNA_AVAILABLE = True
    except ImportError:
        print("[WARN] QuantumSparseDNA_NP not found. Reasoning will be limited.")
        DNA_AVAILABLE = False
        # Fallback: dummy DNA
        class QuantumSparseDNA_NP:
            def __init__(self, dna_size=128, latent_dim=128):
                self.dna = np.random.randn(dna_size, latent_dim) * 0.01
                self.dna_size, self.latent_dim = dna_size, latent_dim
            def forward(self, x):
                return np.eye(self.latent_dim, self.latent_dim)[:self.dna_size, :self.dna_size].T
            def mutate(self, rate=0.01):
                pass
            def clear_cache(self):
                pass


# ===========================================================================
# DEEPREADER INTEGRATION CLASS
# ===========================================================================

class DeepReader:
    """
    Main integration class untuk DeepReader.
    
    Usage:
        # Dari local GGUF
        reader = DeepReader.from_local("model.gguf")
        
        # Dari remote HuggingFace (header only)
        reader = DeepReader.from_remote("https://huggingface.co/.../model.gguf")
        
        # Dari local_brain.json (metadata saja)
        reader = DeepReader.from_metadata("local_brain.json")
        
        # Analisis
        info = reader.get_model_info()
        attn = reader.analyze_attention(attention_patterns, tokens)
        result = reader.reason(query_embedding)
    """
    
    def __init__(self):
        self.metadata: Dict = {}
        self.model_info: Dict = {}
        self.dna: Optional[QuantumSparseDNA_NP] = None
        self.attention_matrix: Optional[AttentionMatrix] = None
        self.hooked_model: Optional[HookedTransformer] = None
        
    # =======================================================================
    # FACTORY METHODS
    # =======================================================================
    
    @classmethod
    def from_local(cls, gguf_path: str, use_dna: bool = True) -> 'DeepReader':
        """Load metadata dari local GGUF file (tanpa weight)."""
        reader = cls()
        
        print(f"📂 Loading local GGUF: {gguf_path}")
        gguf = GGUFReader(gguf_path, use_mmap=False, scan_magic=True)
        gguf.read()
        
        exporter = GGUFKnowledgeExporter(gguf, include_causal_analysis=True)
        nodes = exporter.build()
        
        reader._parse_nodes(nodes)
        reader._init_dna(use_dna)
        
        print(f"✅ Loaded {len(nodes)} metadata nodes")
        return reader
    
    @classmethod
    def from_remote(cls, url: str, hf_token: Optional[str] = None, use_dna: bool = True) -> 'DeepReader':
        """Load metadata dari remote GGUF (header only, tanpa download full model)."""
        reader = cls()
        
        print(f"🌐 Fetching remote GGUF header: {url[:80]}...")
        remote = GGUFRemoteReader(url, token=hf_token, max_header_mb=500)
        nodes = remote.load_knowledge_graph()
        
        reader._parse_nodes(nodes)
        reader._init_dna(use_dna)
        
        print(f"✅ Loaded {len(nodes)} metadata nodes from remote")
        return reader
    
    @classmethod
    def from_metadata(cls, json_path: str, use_dna: bool = True) -> 'DeepReader':
        """Load metadata dari local_brain.json (hasil export sebelumnya)."""
        reader = cls()
        
        with open(json_path, 'r') as f:
            nodes = json.load(f)
        
        reader._parse_nodes(nodes)
        reader._init_dna(use_dna)
        
        print(f"✅ Loaded {len(nodes)} metadata nodes from {json_path}")
        return reader
    
    # =======================================================================
    # INTERNAL METHODS
    # =======================================================================
    
    def _parse_nodes(self, nodes: List[Dict]):
        """Parse epistemic nodes ke dictionary terstruktur."""
        for node in nodes:
            category = node.get('category')
            if category:
                self.metadata[category] = node
            else:
                # Format epistemic node (id, topic, statement)
                node_id = node.get('id', '')
                if node_id.startswith('arch_'):
                    self.model_info['architecture'] = self._extract_arch_info(node)
                elif node_id.startswith('quant_'):
                    self.model_info['quantization'] = self._extract_quant_info(node)
                elif node_id == 'attn_overview':
                    self.model_info['attention'] = self._extract_attn_info(node)
                elif node_id == 'rope_config':
                    self.model_info['rope'] = self._extract_rope_info(node)
                elif node_id == 'tok_vocab':
                    self.model_info['tokenizer'] = self._extract_tokenizer_info(node)
        
        # Fallback: coba ekstrak dari metadata category
        if 'architecture' in self.metadata:
            arch = self.metadata['architecture']
            self.model_info['architecture'] = {
                'num_layers': arch.get('num_layers', 0),
                'embedding_dim': arch.get('embedding_dim', 0),
                'ffn_dim': arch.get('ffn_dim', 0),
                'context_length': arch.get('context_length', 0),
            }
        
        if 'attention' in self.metadata:
            attn = self.metadata['attention']
            self.model_info['attention'] = {
                'query_heads': attn.get('query_heads', 0),
                'kv_heads': attn.get('kv_heads', 0),
                'head_dim': attn.get('head_dim', 0),
                'attention_type': attn.get('attention_type', 'MHA'),
            }
        
        if 'tokenizer' in self.metadata:
            tok = self.metadata['tokenizer']
            self.model_info['tokenizer'] = {
                'model_type': tok.get('model_type', 'unknown'),
                'vocab_size': tok.get('vocab_size', 0),
                'has_chat_template': tok.get('has_chat_template', False),
            }
        
        if 'quantization' in self.metadata:
            quant = self.metadata['quantization']
            self.model_info['quantization'] = {
                'type': quant.get('type', 'unknown'),
                'bits_per_weight': quant.get('bits_per_weight', 0),
            }
    
    def _extract_arch_info(self, node: Dict) -> Dict:
        """Ekstrak info arsitektur dari epistemic node."""
        statement = node.get('statement', '')
        # Parse dari statement (format: "Model menggunakan arsitektur 'xxx' dengan Y layer...")
        import re
        layers = re.search(r'(\d+)\s*layer', statement)
        context = re.search(r'konteks\s*:\s*([\d,]+)', statement, re.IGNORECASE)
        
        return {
            'num_layers': int(layers.group(1)) if layers else 0,
            'context_length': int(context.group(1).replace(',', '')) if context else 0,
        }
    
    def _extract_quant_info(self, node: Dict) -> Dict:
        statement = node.get('statement', '')
        import re
        bpw = re.search(r'([\d.]+)\s*bit-per-weight', statement)
        return {'bits_per_weight': float(bpw.group(1)) if bpw else 0}
    
    def _extract_attn_info(self, node: Dict) -> Dict:
        statement = node.get('statement', '')
        import re
        heads = re.search(r'(\d+)\s*query head', statement)
        kv = re.search(r'(\d+)\s*KV head', statement)
        return {
            'query_heads': int(heads.group(1)) if heads else 0,
            'kv_heads': int(kv.group(1)) if kv else 0,
        }
    
    def _extract_rope_info(self, node: Dict) -> Dict:
        statement = node.get('statement', '')
        import re
        fb = re.search(r'freq_base=([\d,]+)', statement)
        return {'freq_base': float(fb.group(1).replace(',', '')) if fb else 10000}
    
    def _extract_tokenizer_info(self, node: Dict) -> Dict:
        statement = node.get('statement', '')
        import re
        vocab = re.search(r'vocabulary\s*([\d,]+)', statement)
        return {'vocab_size': int(vocab.group(1).replace(',', '')) if vocab else 0}
    
    def _init_dna(self, use_dna: bool):
        """Inisialisasi QuantumSparseDNA dengan dimensi dari metadata."""
        if not use_dna or not DNA_AVAILABLE:
            return
        
        emb_dim = self.model_info.get('architecture', {}).get('embedding_dim', 768)
        dna_size = min(256, emb_dim // 4)  # DNA lebih kecil dari embedding
        
        self.dna = QuantumSparseDNA_NP(dna_size=dna_size, latent_dim=emb_dim)
        print(f"🧬 QuantumSparseDNA initialized: {dna_size}x{emb_dim}")
    
    # =======================================================================
    # PUBLIC API
    # =======================================================================
    
    def get_model_info(self) -> Dict:
        """Dapatkan informasi lengkap model (9 categories)."""
        return self.model_info
    
    def get_architecture(self) -> Dict:
        """Dapatkan info arsitektur."""
        return self.model_info.get('architecture', {})
    
    def get_embedding_dim(self) -> int:
        """Dapatkan dimensi embedding model."""
        return self.model_info.get('architecture', {}).get('embedding_dim', 768)
    
    def get_context_length(self) -> int:
        """Dapatkan panjang konteks maksimum."""
        return self.model_info.get('architecture', {}).get('context_length', 2048)
    
    def get_vocab_size(self) -> int:
        """Dapatkan ukuran vocabulary."""
        return self.model_info.get('tokenizer', {}).get('vocab_size', 50257)
    
    def get_quantization(self) -> Dict:
        """Dapatkan info kuantisasi."""
        return self.model_info.get('quantization', {})
    
    # =======================================================================
    # DNA REASONING (lightweight)
    # =======================================================================
    
    def reason(self, input_vector: np.ndarray) -> np.ndarray:
        """
        Reasoning menggunakan QuantumSparseDNA.
        Input: embedding vector [d_model]
        Output: weight matrix atau transformed vector
        """
        if self.dna is None:
            raise RuntimeError("DNA not initialized. Use use_dna=True")
        
        return self.dna.forward(input_vector)
    
    def understand_token(self, token_embedding: np.ndarray) -> Dict:
        """
        Paham token pake DNA.
        Token embedding bisa dari model kecil atau random.
        """
        if self.dna is None:
            return {'error': 'DNA not initialized'}
        
        weight = self.dna.forward(token_embedding)
        
        return {
            'weight_shape': weight.shape,
            'sparsity': float(np.sum(weight == 0) / weight.size),
            'energy': float(np.sum(weight ** 2)),
            'max_activation': float(np.max(np.abs(weight))),
            'mean_activation': float(np.mean(np.abs(weight))),
        }
    
    def trace_knowledge_path(self, start_embedding: np.ndarray, steps: int = 3) -> List[np.ndarray]:
        """
        Telusuri jalur pengetahuan melalui iterasi DNA.
        Bukan graph traversal, tapi transformasi berulang.
        """
        if self.dna is None:
            return []
        
        path = [start_embedding.copy()]
        current = start_embedding.copy()
        
        for step in range(steps):
            W = self.dna.forward(current)
            
            # Transformasi: v_next = v @ W.T
            if len(current.shape) == 1:
                current = current.reshape(1, -1)
            
            current = (current @ W.T).flatten()
            
            # Normalisasi
            norm = np.linalg.norm(current) + 1e-8
            current = current / norm
            
            path.append(current.copy())
            
            # Mutasi ringan setiap step (belajar adaptif)
            self.dna.mutate(rate=0.001)
        
        return path
    
    # =======================================================================
    # ATTENTION ANALYSIS (butuh attention patterns)
    # =======================================================================
    
    def analyze_attention(self, attention_patterns: np.ndarray, tokens: List[str]) -> Dict:
        """
        Analisis attention pattern.
        
        Args:
            attention_patterns: [n_layers, n_heads, seq_len, seq_len]
            tokens: Daftar token strings
        """
        self.attention_matrix = AttentionMatrix(attention_patterns)
        
        # Head classification untuk layer pertama
        head_view = HeadView(self.attention_matrix)
        classifications = {}
        
        for layer in range(min(3, self.attention_matrix.n_layers)):
            classifications[layer] = head_view.classify_all_heads(layer)
        
        # Token-to-token analysis
        t2t = TokenToToken(self.attention_matrix, tokens)
        graph = t2t.build_attention_graph(threshold=0.1)
        
        return {
            'n_layers': self.attention_matrix.n_layers,
            'n_heads': self.attention_matrix.n_heads,
            'head_classifications': classifications,
            'token_graph': graph,
            'most_attended': t2t.find_most_attended_token(),
            'most_attending': t2t.find_most_attending_token(),
        }
    
    # =======================================================================
    # SETUP TRANSFORMERLENS (opsional, butuh weight asli)
    # =======================================================================
    
    def setup_hooked_transformer(self):
        """Setup HookedTransformer dengan config dari metadata."""
        arch = self.get_architecture()
        attn = self.model_info.get('attention', {})
        tok = self.model_info.get('tokenizer', {})
        
        config = HookedTransformerConfig(
            n_layers=arch.get('num_layers', 12),
            n_heads=attn.get('query_heads', 12),
            d_model=arch.get('embedding_dim', 768),
            d_vocab=tok.get('vocab_size', 50257),
            n_ctx=arch.get('context_length', 2048),
        )
        
        self.hooked_model = HookedTransformer(config)
        print(f"🔧 HookedTransformer configured: {config.n_layers} layers, {config.d_model} dims")
        
        return self.hooked_model
    
    # =======================================================================
    # SUMMARY
    # =======================================================================
    
    def summary(self) -> str:
        """Ringkasan model."""
        arch = self.get_architecture()
        attn = self.model_info.get('attention', {})
        quant = self.get_quantization()
        tok = self.model_info.get('tokenizer', {})
        
        lines = [
            "=" * 50,
            "DEEPREADER INTEGRATION",
            "=" * 50,
            f"Architecture: {self.model_info.get('architecture', {}).get('num_layers', '?')} layers",
            f"Embedding dim: {arch.get('embedding_dim', '?')}",
            f"Context length: {arch.get('context_length', '?')}",
            f"Attention: {attn.get('query_heads', '?')} heads, {attn.get('attention_type', '?')}",
            f"Quantization: {quant.get('type', '?')} ({quant.get('bits_per_weight', '?')} bpw)",
            f"Vocabulary: {tok.get('vocab_size', '?')} tokens",
            f"Chat template: {tok.get('has_chat_template', False)}",
            f"DNA available: {self.dna is not None}",
            "=" * 50,
        ]
        return "\n".join(lines)
    
    def save_metadata(self, path: str):
        """Simpan metadata ke JSON."""
        with open(path, 'w') as f:
            json.dump(self.model_info, f, indent=2)
        print(f"💾 Metadata saved to {path}")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="DeepReader Integration")
    parser.add_argument("source", help="Local .gguf, remote URL, atau local_brain.json")
    parser.add_argument("-o", "--output", default="model_info.json", help="Output JSON")
    parser.add_argument("--remote", action="store_true", help="Force remote mode")
    parser.add_argument("--no-dna", action="store_true", help="Disable DNA")
    
    args = parser.parse_args()
    
    source = args.source
    
    if args.remote or source.startswith("http"):
        reader = DeepReader.from_remote(source, use_dna=not args.no_dna)
    elif source.endswith(".json"):
        reader = DeepReader.from_metadata(source, use_dna=not args.no_dna)
    else:
        reader = DeepReader.from_local(source, use_dna=not args.no_dna)
    
    print(reader.summary())
    reader.save_metadata(args.output)


if __name__ == "__main__":
    main()

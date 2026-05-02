"""
BertViz Adapter - 4 Modul Lengkap (100% intisari)
Diadaptasi dari BertViz untuk QND DeepReader

Modul:
1. Attention Matrix - Matriks attention [batch, heads, query, key]
2. Token-to-Token - Koneksi antar token
3. Neuron View - Visualisasi aktivasi neuron individual
4. Head View - Visualisasi attention head per layer
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict


# =============================================================================
# MODUL 1: ATTENTION MATRIX (dari BertViz head_view + model_view)
# =============================================================================

class AttentionMatrix:
    """
    Matriks Attention lengkap dari model Transformer.
    Porting dari BertViz (head_view.py + model_view.py).
    
    Menyimpan dan menganalisis matriks attention untuk semua layer dan head.
    Format: [n_layers, n_heads, query_seq_len, key_seq_len]
    """
    
    def __init__(self, attention: np.ndarray = None):
        """
        Args:
            attention: [n_layers, n_heads, seq_len, seq_len] atau list per layer
        """
        if attention is not None:
            if isinstance(attention, list):
                self.attention = np.stack(attention, axis=0)
            else:
                self.attention = attention
        else:
            self.attention = None
        
        self.n_layers = 0
        self.n_heads = 0
        self.seq_len = 0
        
        if self.attention is not None:
            self._analyze_shape()
    
    def _analyze_shape(self):
        """Analisis dimensi attention matrix."""
        if len(self.attention.shape) == 4:
            self.n_layers, self.n_heads, self.seq_len, _ = self.attention.shape
        elif len(self.attention.shape) == 3:
            self.n_layers, self.n_heads, self.seq_len = self.attention.shape[:3]
    
    def load(self, attention: Union[np.ndarray, List[np.ndarray]]):
        """Load attention matrix dari model output."""
        if isinstance(attention, list):
            self.attention = np.stack(attention, axis=0)
        else:
            self.attention = attention
        self._analyze_shape()
    
    def get_layer(self, layer: int) -> np.ndarray:
        """
        Dapatkan attention matrix untuk satu layer.
        
        Returns:
            [n_heads, query_seq_len, key_seq_len]
        """
        if self.attention is None:
            raise ValueError("No attention data loaded")
        return self.attention[layer]
    
    def get_head(self, layer: int, head: int) -> np.ndarray:
        """
        Dapatkan attention matrix untuk satu head spesifik.
        
        Returns:
            [query_seq_len, key_seq_len]
        """
        return self.get_layer(layer)[head]
    
    def get_token_to_token(self, layer: int, head: int, query_pos: int, key_pos: int) -> float:
        """
        Dapatkan nilai attention dari token query_pos ke token key_pos.
        
        Args:
            layer: Indeks layer
            head: Indeks head
            query_pos: Posisi token query
            key_pos: Posisi token key
        
        Returns:
            Nilai attention (0-1)
        """
        return float(self.get_head(layer, head)[query_pos, key_pos])
    
    def get_attention_pattern(self, layer: int, head: int) -> np.ndarray:
        """
        Dapatkan pola attention untuk satu head.
        Normalisasi per baris (query).
        """
        attn = self.get_head(layer, head)
        # Normalisasi per baris (setiap query mendistribusikan attention ke semua key)
        row_sums = attn.sum(axis=-1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        return attn / row_sums
    
    def average_heads(self, layer: int) -> np.ndarray:
        """
        Rata-rata attention semua head dalam satu layer.
        
        Returns:
            [query_seq_len, key_seq_len]
        """
        return self.get_layer(layer).mean(axis=0)
    
    def average_layers(self, head: int = None) -> np.ndarray:
        """
        Rata-rata attention di semua layer.
        
        Args:
            head: Indeks head spesifik (None = semua head)
        
        Returns:
            [query_seq_len, key_seq_len]
        """
        if head is not None:
            return self.attention[:, head, :, :].mean(axis=0)
        return self.attention.mean(axis=(0, 1))
    
    def find_strongest_connection(
        self,
        layer: int = None,
        head: int = None
    ) -> Tuple[int, int, float]:
        """
        Temukan koneksi terkuat dalam attention matrix.
        
        Returns:
            (query_pos, key_pos, attention_value)
        """
        if layer is not None and head is not None:
            attn = self.get_head(layer, head)
        elif layer is not None:
            attn = self.average_heads(layer)
        else:
            attn = self.average_layers()
        
        # Cari indeks dengan nilai tertinggi
        max_idx = np.unravel_index(np.argmax(attn), attn.shape)
        return (max_idx[0], max_idx[1], float(attn[max_idx]))
    
    def get_summary(self) -> Dict:
        """Ringkasan attention matrix."""
        return {
            'n_layers': self.n_layers,
            'n_heads': self.n_heads,
            'seq_len': self.seq_len,
            'shape': self.attention.shape if self.attention is not None else None,
            'mean_attention': float(self.attention.mean()) if self.attention is not None else None,
            'std_attention': float(self.attention.std()) if self.attention is not None else None,
        }


# =============================================================================
# MODUL 2: TOKEN-TO-TOKEN (dari BertViz head_view + neuron_view)
# =============================================================================

class TokenToToken:
    """
    Analisis koneksi antar token dalam attention matrix.
    Porting dari BertViz (head_view.py + neuron_view.py).
    
    Menyediakan analisis:
    - Token mana yang paling "diperhatikan" oleh token lain
    - Token mana yang paling "memperhatikan" token lain
    - Jalur koneksi antar token
    """
    
    def __init__(self, attention_matrix: AttentionMatrix = None, tokens: List[str] = None):
        self.attention_matrix = attention_matrix
        self.tokens = tokens or []
        self._connections = None
    
    def set_tokens(self, tokens: List[str]):
        """Set daftar token."""
        self.tokens = tokens
    
    def set_attention(self, attention_matrix: AttentionMatrix):
        """Set attention matrix."""
        self.attention_matrix = attention_matrix
    
    def get_attention_to_token(
        self,
        target_pos: int,
        layer: int = None,
        head: int = None
    ) -> np.ndarray:
        """
        Dapatkan attention dari semua token ke satu token target.
        
        Args:
            target_pos: Posisi token target (sebagai key)
            layer: Layer spesifik (None = rata-rata semua)
            head: Head spesifik (None = rata-rata semua)
        
        Returns:
            Array attention [query_seq_len] — seberapa besar setiap token attend ke target
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        if layer is not None and head is not None:
            attn = self.attention_matrix.get_head(layer, head)
        elif layer is not None:
            attn = self.attention_matrix.average_heads(layer)
        else:
            attn = self.attention_matrix.average_layers()
        
        # Attention dari semua query ke key target_pos
        return attn[:, target_pos]
    
    def get_attention_from_token(
        self,
        source_pos: int,
        layer: int = None,
        head: int = None
    ) -> np.ndarray:
        """
        Dapatkan attention dari satu token source ke semua token lain.
        
        Args:
            source_pos: Posisi token source (sebagai query)
            layer: Layer spesifik (None = rata-rata semua)
            head: Head spesifik (None = rata-rata semua)
        
        Returns:
            Array attention [key_seq_len] — seberapa besar token source attend ke setiap key
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        if layer is not None and head is not None:
            attn = self.attention_matrix.get_head(layer, head)
        elif layer is not None:
            attn = self.attention_matrix.average_heads(layer)
        else:
            attn = self.attention_matrix.average_layers()
        
        # Attention dari query source_pos ke semua key
        return attn[source_pos, :]
    
    def find_most_attended_token(
        self,
        layer: int = None,
        head: int = None
    ) -> Tuple[int, float]:
        """
        Temukan token yang paling banyak "diperhatikan" (sebagai key).
        
        Returns:
            (token_pos, total_attention)
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        if layer is not None and head is not None:
            attn = self.attention_matrix.get_head(layer, head)
        elif layer is not None:
            attn = self.attention_matrix.average_heads(layer)
        else:
            attn = self.attention_matrix.average_layers()
        
        # Total attention yang diterima setiap token (sebagai key)
        key_attention = attn.sum(axis=0)
        most_attended = int(np.argmax(key_attention))
        return (most_attended, float(key_attention[most_attended]))
    
    def find_most_attending_token(
        self,
        layer: int = None,
        head: int = None
    ) -> Tuple[int, float]:
        """
        Temukan token yang paling "memperhatikan" (sebagai query).
        
        Returns:
            (token_pos, total_attention)
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        if layer is not None and head is not None:
            attn = self.attention_matrix.get_head(layer, head)
        elif layer is not None:
            attn = self.attention_matrix.average_heads(layer)
        else:
            attn = self.attention_matrix.average_layers()
        
        # Total attention yang diberikan setiap token (sebagai query)
        query_attention = attn.sum(axis=1)
        most_attending = int(np.argmax(query_attention))
        return (most_attending, float(query_attention[most_attending]))
    
    def trace_attention_path(
        self,
        start_token: int,
        n_steps: int = 5,
        layer: int = None
    ) -> List[Tuple[int, int]]:
        """
        Telusuri jalur attention dari satu token ke token berikutnya.
        
        Args:
            start_token: Posisi token awal
            n_steps: Jumlah langkah
            layer: Layer spesifik
        
        Returns:
            List of (from_token, to_token)
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        path = []
        current = start_token
        visited = {current}
        
        for _ in range(n_steps):
            # Cari token berikutnya yang paling diperhatikan oleh current
            attn_to = self.get_attention_from_token(current, layer=layer)
            
            # Cari yang paling tinggi, tapi belum dikunjungi
            sorted_indices = np.argsort(attn_to)[::-1]
            next_token = None
            for idx in sorted_indices:
                if idx not in visited:
                    next_token = int(idx)
                    break
            
            if next_token is None:
                break
            
            path.append((current, next_token))
            visited.add(next_token)
            current = next_token
        
        return path
    
    def build_attention_graph(
        self,
        threshold: float = 0.1,
        layer: int = None,
        head: int = None
    ) -> Dict[str, List]:
        """
        Bangun graph koneksi antar token berdasarkan attention.
        
        Args:
            threshold: Nilai minimum attention untuk dianggap sebagai koneksi
            layer: Layer spesifik
            head: Head spesifik
        
        Returns:
            {'nodes': [...], 'edges': [...]}
        """
        if self.attention_matrix is None:
            return {'nodes': [], 'edges': []}
        
        if layer is not None and head is not None:
            attn = self.attention_matrix.get_head(layer, head)
        elif layer is not None:
            attn = self.attention_matrix.average_heads(layer)
        else:
            attn = self.attention_matrix.average_layers()
        
        nodes = []
        edges = []
        
        # Tambahkan node untuk setiap token
        for i, token in enumerate(self.tokens):
            nodes.append({
                'id': i,
                'label': token,
                'total_attention_received': float(attn[:, i].sum()),
                'total_attention_given': float(attn[i, :].sum())
            })
        
        # Tambahkan edge untuk koneksi di atas threshold
        for i in range(len(self.tokens)):
            for j in range(len(self.tokens)):
                if i != j and attn[i, j] > threshold:
                    edges.append({
                        'source': i,
                        'target': j,
                        'weight': float(attn[i, j])
                    })
        
        return {'nodes': nodes, 'edges': edges}


# =============================================================================
# MODUL 3: NEURON VIEW (dari BertViz neuron_view.py)
# =============================================================================

class NeuronView:
    """
    Visualisasi aktivasi neuron individual di dalam model.
    Porting dari BertViz neuron_view.py.
    
    Menganalisis:
    - Aktivasi neuron di MLP layer
    - Query dan Key vectors di Attention layer
    - Pola aktivasi untuk input tertentu
    """
    
    def __init__(self, model=None):
        self.model = model
        self.activations: Dict[str, np.ndarray] = {}
        self.queries: Dict[int, np.ndarray] = {}
        self.keys: Dict[int, np.ndarray] = {}
    
    def load_activations(
        self,
        activation_cache: Dict[str, np.ndarray],
        tokens: List[str] = None
    ):
        """
        Load aktivasi dari cache.
        
        Args:
            activation_cache: Dictionary aktivasi dari run_with_cache
            tokens: Daftar token (untuk referensi)
        """
        self.activations = activation_cache
        self.tokens = tokens or []
    
    def load_queries_keys(
        self,
        queries: Dict[int, np.ndarray],
        keys: Dict[int, np.ndarray]
    ):
        """
        Load query dan key vectors dari attention layer.
        
        Args:
            queries: {layer: [n_heads, seq_len, d_head]}
            keys: {layer: [n_heads, seq_len, d_head]}
        """
        self.queries = queries
        self.keys = keys
    
    def get_mlp_activations(
        self,
        layer: int,
        neuron_indices: List[int] = None
    ) -> np.ndarray:
        """
        Dapatkan aktivasi neuron MLP untuk satu layer.
        
        Args:
            layer: Indeks layer
            neuron_indices: Indeks neuron spesifik (None = semua)
        
        Returns:
            Aktivasi neuron [seq_len, n_neurons]
        """
        key = f"blocks.{layer}.hook_mlp_out"
        if key not in self.activations:
            key = f"blocks.{layer}.mlp.hook_post"
        
        if key in self.activations:
            activations = self.activations[key]
            if len(activations.shape) == 3:
                # [batch, seq_len, d_mlp] -> [seq_len, d_mlp]
                activations = activations[0]
            
            if neuron_indices is not None:
                return activations[:, neuron_indices]
            return activations
        
        return None
    
    def get_neuron_activation_profile(
        self,
        layer: int,
        neuron_idx: int
    ) -> Dict[str, np.ndarray]:
        """
        Dapatkan profil aktivasi satu neuron.
        
        Returns:
            {
                'values': [seq_len] — nilai aktivasi per token
                'tokens': [str] — token pada posisi tersebut
                'max_activation': float — aktivasi maksimum
                'max_token': str — token dengan aktivasi tertinggi
            }
        """
        mlp_act = self.get_mlp_activations(layer, [neuron_idx])
        if mlp_act is None:
            return None
        
        values = mlp_act[:, 0]  # Neuron spesifik
        max_idx = int(np.argmax(values))
        
        return {
            'values': values,
            'tokens': self.tokens if self.tokens else [str(i) for i in range(len(values))],
            'max_activation': float(values[max_idx]),
            'max_token': self.tokens[max_idx] if self.tokens and max_idx < len(self.tokens) else str(max_idx),
            'min_activation': float(values.min()),
            'mean_activation': float(values.mean()),
            'active_tokens': sum(1 for v in values if v > 0)
        }
    
    def find_top_neurons(
        self,
        layer: int,
        token_pos: int,
        k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Temukan neuron dengan aktivasi tertinggi untuk token tertentu.
        
        Args:
            layer: Indeks layer
            token_pos: Posisi token
            k: Jumlah neuron yang diinginkan
        
        Returns:
            List of (neuron_idx, activation_value)
        """
        mlp_act = self.get_mlp_activations(layer)
        if mlp_act is None:
            return []
        
        token_activations = mlp_act[token_pos]
        top_indices = np.argsort(token_activations)[::-1][:k]
        return [(int(idx), float(token_activations[idx])) for idx in top_indices]
    
    def analyze_query_key_similarity(
        self,
        layer: int,
        head: int,
        query_pos: int,
        key_pos: int
    ) -> float:
        """
        Hitung cosine similarity antara query dan key vector.
        
        Args:
            layer: Indeks layer
            head: Indeks head
            query_pos: Posisi query
            key_pos: Posisi key
        
        Returns:
            Cosine similarity (-1 hingga 1)
        """
        if layer not in self.queries or layer not in self.keys:
            return 0.0
        
        q = self.queries[layer][head, query_pos]
        k = self.keys[layer][head, key_pos]
        
        # Cosine similarity
        dot = np.dot(q, k)
        norm_q = np.linalg.norm(q)
        norm_k = np.linalg.norm(k)
        
        if norm_q == 0 or norm_k == 0:
            return 0.0
        
        return float(dot / (norm_q * norm_k))
    
    def get_neuron_summary(self, layer: int) -> Dict:
        """Ringkasan aktivasi neuron untuk satu layer."""
        mlp_act = self.get_mlp_activations(layer)
        if mlp_act is None:
            return {}
        
        n_neurons = mlp_act.shape[1]
        neuron_means = mlp_act.mean(axis=0)
        neuron_maxs = mlp_act.max(axis=0)
        
        return {
            'layer': layer,
            'n_neurons': n_neurons,
            'mean_activation': float(neuron_means.mean()),
            'max_activation': float(neuron_maxs.max()),
            'active_neurons': int(sum(neuron_maxs > 0)),
            'top_neurons': [
                (int(idx), float(neuron_maxs[idx]))
                for idx in np.argsort(neuron_maxs)[::-1][:5]
            ]
        }


# =============================================================================
# MODUL 4: HEAD VIEW (dari BertViz head_view.py)
# =============================================================================

class HeadView:
    """
    Visualisasi dan analisis attention head per layer.
    Porting dari BertViz head_view.py.
    
    Menganalisis:
    - Pola attention per head (previous token, duplicate, induction)
    - Head yang spesialis untuk tugas tertentu
    - Perbandingan head dalam satu layer
    """
    
    def __init__(self, attention_matrix: AttentionMatrix = None):
        self.attention_matrix = attention_matrix
    
    def set_attention(self, attention_matrix: AttentionMatrix):
        """Set attention matrix."""
        self.attention_matrix = attention_matrix
    
    def get_head_pattern(
        self,
        layer: int,
        head: int,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Dapatkan pola attention untuk satu head.
        
        Returns:
            [query_seq_len, key_seq_len]
        """
        if self.attention_matrix is None:
            raise ValueError("No attention data")
        
        attn = self.attention_matrix.get_head(layer, head)
        
        if normalize:
            row_sums = attn.sum(axis=-1, keepdims=True)
            row_sums = np.where(row_sums > 0, row_sums, 1.0)
            attn = attn / row_sums
        
        return attn
    
    def detect_head_type(
        self,
        layer: int,
        head: int,
        detection_type: str = "previous_token"
    ) -> float:
        """
        Deteksi tipe attention head.
        
        Args:
            layer: Indeks layer
            head: Indeks head
            detection_type: "previous_token", "duplicate_token", "induction", "uniform"
        
        Returns:
            Skor kecocokan (0-1)
        """
        attn = self.get_head_pattern(layer, head)
        seq_len = attn.shape[0]
        
        if detection_type == "previous_token":
            # Attend ke token sebelumnya (satu posisi di atas diagonal)
            pattern = np.zeros((seq_len, seq_len))
            for i in range(1, seq_len):
                pattern[i, i-1] = 1.0
        
        elif detection_type == "duplicate_token":
            # Attend ke token yang sama (diagonal)
            pattern = np.eye(seq_len)
        
        elif detection_type == "induction":
            # Attend ke token setelah kemunculan sebelumnya
            pattern = np.zeros((seq_len, seq_len))
            for i in range(1, seq_len):
                pattern[i, min(i-1, 1)] = 0.5
        
        elif detection_type == "uniform":
            # Attend merata ke semua token sebelumnya
            pattern = np.tril(np.ones((seq_len, seq_len))) / np.arange(1, seq_len+1).reshape(-1, 1)
        
        else:
            raise ValueError(f"Unknown detection type: {detection_type}")
        
        # Hitung skor kecocokan (element-wise multiplication)
        mask = np.tril(np.ones((seq_len, seq_len)))
        attn = attn * mask
        score = np.sum(attn * pattern) / max(np.sum(attn), 1e-8)
        
        return float(np.clip(score, 0.0, 1.0))
    
    def classify_all_heads(
        self,
        layer: int
    ) -> Dict[int, Dict[str, float]]:
        """
        Klasifikasi semua head dalam satu layer.
        
        Returns:
            {head_index: {type: score}}
        """
        if self.attention_matrix is None:
            return {}
        
        n_heads = self.attention_matrix.n_heads
        results = {}
        
        for h in range(n_heads):
            results[h] = {
                'previous_token': self.detect_head_type(layer, h, 'previous_token'),
                'duplicate_token': self.detect_head_type(layer, h, 'duplicate_token'),
                'induction': self.detect_head_type(layer, h, 'induction'),
                'uniform': self.detect_head_type(layer, h, 'uniform'),
            }
        
        return results
    
    def find_head_by_type(
        self,
        detection_type: str,
        min_score: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        Cari head dengan tipe tertentu di semua layer.
        
        Returns:
            List of (layer, head, score)
        """
        if self.attention_matrix is None:
            return []
        
        results = []
        for l in range(self.attention_matrix.n_layers):
            for h in range(self.attention_matrix.n_heads):
                score = self.detect_head_type(l, h, detection_type)
                if score >= min_score:
                    results.append((l, h, score))
        
        return sorted(results, key=lambda x: x[2], reverse=True)
    
    def compare_heads(
        self,
        layer: int,
        head_a: int,
        head_b: int
    ) -> Dict[str, float]:
        """
        Bandingkan dua head dalam satu layer.
        
        Returns:
            {'cosine_similarity': float, 'mutual_information': float, ...}
        """
        attn_a = self.get_head_pattern(layer, head_a).flatten()
        attn_b = self.get_head_pattern(layer, head_b).flatten()
        
        # Cosine similarity
        dot = np.dot(attn_a, attn_b)
        norm_a = np.linalg.norm(attn_a)
        norm_b = np.linalg.norm(attn_b)
        
        cosine_sim = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0
        
        # Pearson correlation
        mean_a, mean_b = attn_a.mean(), attn_b.mean()
        std_a, std_b = attn_a.std(), attn_b.std()
        
        if std_a > 0 and std_b > 0:
            pearson = np.mean((attn_a - mean_a) * (attn_b - mean_b)) / (std_a * std_b)
        else:
            pearson = 0.0
        
        # Mean absolute difference
        mad = np.mean(np.abs(attn_a - attn_b))
        
        return {
            'cosine_similarity': float(cosine_sim),
            'pearson_correlation': float(pearson),
            'mean_absolute_difference': float(mad),
            'similarity_score': float(1.0 - mad / 2.0),  # 1 = identik, 0 = sangat berbeda
        }
    
    def get_layer_summary(self, layer: int) -> Dict:
        """Ringkasan semua head dalam satu layer."""
        if self.attention_matrix is None:
            return {}
        
        classification = self.classify_all_heads(layer)
        
        # Cari head dominan untuk setiap tipe
        dominant = {}
        for head_type in ['previous_token', 'duplicate_token', 'induction']:
            best_head = max(classification.items(), key=lambda x: x[1][head_type])
            dominant[head_type] = {
                'head': best_head[0],
                'score': best_head[1][head_type]
            }
        
        return {
            'layer': layer,
            'n_heads': self.attention_matrix.n_heads,
            'dominant_heads': dominant,
            'head_diversity': len(set(
                h for h, scores in classification.items()
                if max(scores.values()) > 0.5
            )),
        }


# =============================================================================
# EKSPOR
# =============================================================================

__all__ = [
    'AttentionMatrix',
    'TokenToToken',
    'NeuronView',
    'HeadView',
]

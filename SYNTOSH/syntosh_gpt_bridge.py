from skills.reasoning import reasoning
# SYNTOSH/syntosh_gpt_bridge.py — Jembatan GPT + PLN + DNA
# Dipanggil dari DNA Sovereign untuk reasoning berbasis SYNTOSH

import numpy as np
import json
import os
import sys
from collections import OrderedDict

# =============================================================================
# CONFIG
# =============================================================================
SYNTOSH_DIR = os.path.dirname(os.path.abspath(__file__))
D_MODEL = 768
N_LAYERS = 6
N_HEADS = 12
D_HEAD = D_MODEL // N_HEADS
VOCAB_SIZE = 50257

# =============================================================================
# WEIGHT LOADER (lazy, cuma load yang dibutuhkan)
# =============================================================================
_weight_cache = {}

def _load_weight(name):
    if name in _weight_cache:
        return _weight_cache[name]
    path = os.path.join(SYNTOSH_DIR, f"gpt_{name}.npy")
    if os.path.exists(path):
        w = np.load(path)
        _weight_cache[name] = w
        return w
    raise FileNotFoundError(f"Weight not found: {path}")

# =============================================================================
# GPT2 FORWARD PASS (pure numpy)
# =============================================================================
def _gelu(x):
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3)))

def _layer_norm(x, weight, bias, eps=1e-5):
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    return weight * (x - mean) / np.sqrt(var + eps) + bias

def _attention(x, layer_idx):
    """Multi-head self-attention untuk GPT2"""
    # Gabungan QKV: [768, 2304]
    c_attn_w = _load_weight(f"blk_{layer_idx}_attn_c_attn_weight")
    c_attn_b = _load_weight(f"blk_{layer_idx}_attn_c_attn_bias")
    c_proj_w = _load_weight(f"blk_{layer_idx}_attn_c_proj_weight")
    c_proj_b = _load_weight(f"blk_{layer_idx}_attn_c_proj_bias")
    
    # QKV projection
    qkv = x @ c_attn_w + c_attn_b  # w=[768,2304], x=[seq,768], qkv=[seq,2304]
    
    # Split ke Q, K, V
    q, k, v = np.split(qkv, 3, axis=-1)  # masing-masing [seq, 768]
    
    # Reshape ke multi-head: [seq, n_heads, d_head]
    seq_len = x.shape[0]
    q = q.reshape(seq_len, N_HEADS, D_HEAD)
    k = k.reshape(seq_len, N_HEADS, D_HEAD)
    v = v.reshape(seq_len, N_HEADS, D_HEAD)
    
    # Scaled dot-product attention
    scale = 1.0 / np.sqrt(D_HEAD)
    attn_out = np.zeros((seq_len, D_MODEL), dtype=np.float32)
    
    for h in range(N_HEADS):
        scores = q[:, h, :] @ k[:, h, :].T * scale
        # Causal mask
        mask = np.tril(np.ones((seq_len, seq_len)))
        scores = np.where(mask > 0, scores, -1e10)
        # Softmax
        scores = scores - scores.max(axis=-1, keepdims=True)
        probs = np.exp(scores) / np.exp(scores).sum(axis=-1, keepdims=True)
        # Weighted sum
        head_out = probs @ v[:, h, :]
        attn_out[:, h * D_HEAD:(h + 1) * D_HEAD] = head_out
    
    # Output projection
    return attn_out @ c_proj_w + c_proj_b

def _mlp(x, layer_idx):
    """Feed-forward network GPT2"""
    c_fc_w = _load_weight(f"blk_{layer_idx}_mlp_c_fc_weight")
    c_fc_b = _load_weight(f"blk_{layer_idx}_mlp_c_fc_bias")
    c_proj_w = _load_weight(f"blk_{layer_idx}_mlp_c_proj_weight")
    c_proj_b = _load_weight(f"blk_{layer_idx}_mlp_c_proj_bias")
    
    hidden = x @ c_fc_w + c_fc_b
    hidden = _gelu(hidden)
    return hidden @ c_proj_w + c_proj_b

def forward(input_ids, output_hidden_states=True):
    """
    Full forward pass GPT2.
    
    Args:
        input_ids: list/array of token IDs
        output_hidden_states: return hidden state token terakhir
        
    Returns:
        dict with 'last_hidden' (768,) and 'hidden_states' (list of [seq, 768] per layer)
    """
    # Embedding
    w_emb = _load_weight("embed_weight")
    w_pos = _load_weight("pos_weight")
    
    seq_len = len(input_ids)
    positions = np.arange(seq_len)
    
    x = w_emb[input_ids] + w_pos[positions]  # w_emb=[50257,768], w_pos=[1024,768]  # [seq, 768]
    
    hidden_states = [x.copy()]
    
    # 6 transformer layers
    for layer in range(N_LAYERS):
        # LayerNorm 1
        ln1_w = _load_weight(f"blk_{layer}_ln1_weight")
        ln1_b = _load_weight(f"blk_{layer}_ln1_bias")
        normed = _layer_norm(x, ln1_w, ln1_b)
        
        # Attention + residual
        attn_out = _attention(normed, layer)
        x = x + attn_out
        
        # LayerNorm 2
        ln2_w = _load_weight(f"blk_{layer}_ln2_weight")
        ln2_b = _load_weight(f"blk_{layer}_ln2_bias")
        normed = _layer_norm(x, ln2_w, ln2_b)
        
        # MLP + residual
        mlp_out = _mlp(normed, layer)
        x = x + mlp_out
        
        hidden_states.append(x.copy())
    
    # Final LayerNorm
    ln_f_w = _load_weight("final_ln_weight")
    ln_f_b = _load_weight("final_ln_bias")
    x = _layer_norm(x, ln_f_w, ln_f_b)
    
    return {
        'last_hidden': x[-1],  # token terakhir, [768]
        'hidden_states': hidden_states,
        'all_hidden': x  # [seq, 768] final
    }

# =============================================================================
# STEERING MODULE
# =============================================================================
_pln_data = None
_v_neutral = None
_dna_output = None
_word_vocab = None

def _init_modules():
    global _pln_data, _v_neutral, _dna_output, _word_vocab
    
    if _pln_data is None:
        # Load PLN
        pln_path = os.path.join(SYNTOSH_DIR, 'pln_full_knowledge.npz')
        if os.path.exists(pln_path):
            _pln_data = dict(np.load(pln_path, allow_pickle=True))
    
    if _v_neutral is None:
        # v_neutral dari embedding
        w_emb = _load_weight("embed_weight")
        sample = np.random.choice(w_emb.shape[0], min(3000, w_emb.shape[0]), replace=False)
        _v_neutral = np.mean(w_emb[sample], axis=0)
    
    if _dna_output is None:
        # DNA Output
        sys.path.insert(0, SYNTOSH_DIR)
        from dna_output_layer import DNAOutputLayer
        
        if _word_vocab is None:
            vocab_path = os.path.join(SYNTOSH_DIR, 'word_vocab.json')
            with open(vocab_path) as f:
                _word_vocab = json.load(f)
        
        id_to_token = {info['local_id']: word for word, info in _word_vocab.items()}
        global_ids = {info['local_id']: info['global_id'] for _, info in _word_vocab.items()}
        
        w_emb = _load_weight("embed_weight")
        _dna_output = DNAOutputLayer(w_emb, global_ids, len(id_to_token), dna_size=128)
        _dna_output.proj = np.random.randn(D_MODEL, 128).astype(np.float16) * 0.01

def steer(hidden_state, concept_key, alpha=3.0):
    """Inject concept vector ke hidden state"""
    _init_modules()
    
    if _pln_data and concept_key in _pln_data:
        concept_vec = _pln_data[concept_key]
        if len(concept_vec) == D_MODEL:
            v_contrast = (concept_vec - _v_neutral) * alpha
            return hidden_state * 0.5 + v_contrast * 0.5
    
    return hidden_state

# =============================================================================
# MAIN REASONING FUNCTION (dipanggil dari DNAEntity)
# =============================================================================
def reason(question, domain=None, max_tokens=12, temperature=0.9, alpha=3.0):
    """
    Full pipeline: Tokenize → Forward → Steer → Decode
    
    Args:
        question: teks pertanyaan
        domain: domain DNA (contoh: "Fisika", "Ekonomi")
        max_tokens: jumlah token output
        temperature: suhu decoding
        alpha: kekuatan steering
        
    Returns:
        dict dengan 'tokens' (list of str), 'embedding' (768,), 'domain_used'
    """
    _init_modules()
    
    # Tokenisasi sederhana: hash-based (sementara)
    # TODO: ganti dengan tokenizer asli
    words = question.lower().split()
    input_ids = [abs(hash(w)) % VOCAB_SIZE for w in words[:50]]
    if not input_ids:
        input_ids = [0]
    
    # Forward pass GPT
    fwd = forward(input_ids)
    hidden = fwd['last_hidden']  # [768]
    
    # Steering dengan concept dari domain DNA
    concept_key = f"pillar_{domain}" if domain else None
    if concept_key:
        hidden = steer(hidden, concept_key, alpha)
    
    # Decode via DNA Output
    output_ids = []
    h = hidden.copy()
    for _ in range(max_tokens):
        nid = _dna_output.forward(h, temperature=temperature, top_k=2000)
        output_ids.append(nid)
        # Update hidden dari embedding token
        w_emb = _load_weight("embed_weight")
        h = w_emb[nid % w_emb.shape[0]].copy()
    
    # Decode token IDs ke text
    id_to_token = {info['local_id']: word for word, info in _word_vocab.items()}
    tokens = [id_to_token.get(t % len(id_to_token), '?') for t in output_ids]
    
    # ═══ REASONING ENGINE — Analisis hasil ═══
    reasoning_result = reasoning.reason(
        input_data={"question": question, "tokens": tokens[:10]},
        memory=[],
        options=["VALID", "UNCERTAIN", "INVALID"],
        criteria={"coherence": 0.5, "relevance": 0.3, "confidence": 0.2},
        scores={
            "VALID": {"coherence": 0.7, "relevance": 0.7, "confidence": 0.7},
            "UNCERTAIN": {"coherence": 0.4, "relevance": 0.4, "confidence": 0.4},
            "INVALID": {"coherence": 0.1, "relevance": 0.1, "confidence": 0.1},
        }
    )

    return {
        'tokens': tokens,
        'text': ' '.join(tokens),
        'embedding': hidden,
        'reasoning': reasoning_result,
        'domain_used': domain,
        'concept_key': concept_key,
        'num_tokens': len(tokens)
    }

# =============================================================================
# TEST (kalau dijalankan langsung)
# =============================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🧪 SYNTOSH GPT BRIDGE — TEST")
    print("=" * 50)
    
    result = reason("What is physics?", domain="Fisika", max_tokens=8)
    print(f"\nDomain: {result['domain_used']}")
    print(f"Concept: {result['concept_key']}")
    print(f"Output: {result['text']}")
    
    result2 = reason("How does economy work?", domain="Ekonomi", max_tokens=8)
    print(f"\nDomain: {result2['domain_used']}")
    print(f"Output: {result2['text']}")
    
    print("\n✅ Bridge ready!")

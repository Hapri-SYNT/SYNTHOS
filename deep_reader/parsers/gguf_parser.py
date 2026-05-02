"""
gguf_parser.py — Enhanced Multi-Part GGUF Parser
=================================================
Features:
  • Accept single path or list of paths (split .gguf parts)
  • Auto-discover sibling part files (00001-of-00005, etc.)
  • Scan for GGUF magic anywhere in a file (magic not always at byte 0)
  • Memory-mapped reads — handles 100 GB+ shards without loading into RAM
  • Merge metadata + vocabulary + tensors from N parts into one logical model
  • Full tokenizer vocab reconstruction (BPE / SPM / WPM / RWKV)
  • Vocabulary deduplication & gap detection across parts
  • Lazy tensor data access — only reads raw bytes on demand
  • Progress callback for long multi-part scans
"""

import re
import struct
import os
import mmap
import warnings
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}"
        n /= 1024


# ---------------------------------------------------------------------------
# MODUL 6: BinaryReader  (mmap-aware, magic-scan capable)
# ---------------------------------------------------------------------------

class BinaryReader:
    """
    Reads primitive GGUF types from a bytes-like buffer.

    Pass ``mmap_obj`` for zero-copy reads on large files; fall back to plain
    ``bytes`` for small in-memory payloads.
    """

    GGUF_MAGIC = b"GGUF"

    def __init__(
        self,
        data: Union[bytes, mmap.mmap],
        little_endian: bool = True,
        base_offset: int = 0,
    ):
        self._data = data
        self._little_endian = little_endian
        self._position = base_offset          # logical cursor
        self._base = base_offset              # where GGUF header starts inside file
        self._length = len(data)

    # ------------------------------------------------------------------ props
    @property
    def position(self) -> int:
        return self._position

    @property
    def length(self) -> int:
        return self._length

    @property
    def remaining(self) -> int:
        return self._length - self._position

    # ---------------------------------------------------------------- seeking
    def seek(self, position: int) -> None:
        if not (0 <= position <= self._length):
            raise EOFError(f"Seek out of bounds: {position} / {self._length}")
        self._position = position

    def seek_relative_to_base(self, offset: int) -> None:
        self.seek(self._base + offset)

    def skip(self, count: int) -> None:
        self._position += count
        if self._position > self._length:
            raise EOFError("Unexpected end of data")

    # ------------------------------------------------------------------ reads
    def read(self, length: int) -> bytes:
        end = self._position + length
        if end > self._length:
            raise EOFError(
                f"Read {length} bytes at position {self._position} overflows "
                f"buffer of {self._length} bytes"
            )
        chunk = self._data[self._position : end]
        self._position = end
        # mmap.mmap slices return bytes already; plain bytes slices too
        return bytes(chunk)

    def peek(self, length: Optional[int] = None) -> bytes:
        if length is None:
            return bytes(self._data[self._position :])
        return bytes(self._data[self._position : self._position + length])

    # ---------------------------------------------------------- find GGUF magic
    @classmethod
    def find_magic_offset(cls, data: Union[bytes, mmap.mmap]) -> int:
        """
        Scan ``data`` for the first occurrence of b'GGUF'.
        Returns the byte offset, or raises ``ValueError`` if not found.

        Useful when a file has a proprietary prefix (license header, BLAKE3
        hash block, quantization wrapper, etc.) prepended before the actual
        GGUF payload.
        """
        needle = cls.GGUF_MAGIC
        # mmap supports .find() natively and efficiently
        idx = data.find(needle)
        if idx == -1:
            raise ValueError("GGUF magic b'GGUF' not found in data")
        if idx > 0:
            warnings.warn(
                f"GGUF magic found at offset {idx} (not at byte 0). "
                "File likely has a non-standard prefix — skipping it.",
                RuntimeWarning,
                stacklevel=2,
            )
        return idx

    # ---------------------------------------------- primitive type readers
    def byte(self) -> int:
        return self.read(1)[0]

    def uint8(self) -> int:
        return self.byte()

    def int8(self) -> int:
        fmt = "<b" if self._little_endian else ">b"
        return struct.unpack(fmt, self.read(1))[0]

    def uint16(self) -> int:
        fmt = "<H" if self._little_endian else ">H"
        return struct.unpack(fmt, self.read(2))[0]

    def int16(self) -> int:
        fmt = "<h" if self._little_endian else ">h"
        return struct.unpack(fmt, self.read(2))[0]

    def uint32(self) -> int:
        fmt = "<I" if self._little_endian else ">I"
        return struct.unpack(fmt, self.read(4))[0]

    def int32(self) -> int:
        fmt = "<i" if self._little_endian else ">i"
        return struct.unpack(fmt, self.read(4))[0]

    def uint64(self) -> int:
        fmt = "<Q" if self._little_endian else ">Q"
        return struct.unpack(fmt, self.read(8))[0]

    def int64(self) -> int:
        fmt = "<q" if self._little_endian else ">q"
        return struct.unpack(fmt, self.read(8))[0]

    def float32(self) -> float:
        fmt = "<f" if self._little_endian else ">f"
        return struct.unpack(fmt, self.read(4))[0]

    def float64(self) -> float:
        fmt = "<d" if self._little_endian else ">d"
        return struct.unpack(fmt, self.read(8))[0]

    def bool(self) -> bool:
        return self.byte() != 0

    def string(self) -> str:
        """GGUF string: uint64 length + UTF-8 bytes."""
        length = self.uint64()
        if length == 0:
            return ""
        return self.read(length).decode("utf-8", errors="replace")

    # --------------------------------------------------- GGUF composite types
    _READERS = {
        0:  "uint8",
        1:  "int8",
        2:  "uint16",
        3:  "int16",
        4:  "uint32",
        5:  "int32",
        6:  "float32",
        7:  "bool",
        8:  "string",
        9:  "_read_array",
        10: "uint64",
        11: "int64",
        12: "float64",
    }

    def value(self, gguf_type: int):
        method_name = self._READERS.get(gguf_type)
        if method_name is None:
            raise ValueError(f"Unsupported GGUF value type: {gguf_type}")
        return getattr(self, method_name)()

    def _read_array(self) -> list:
        item_type = self.uint32()
        count     = self.uint64()
        return [self.value(item_type) for _ in range(count)]

    def entry(self) -> Dict:
        """Read one metadata KV pair → {"name", "value", "type"}."""
        name      = self.string()
        gguf_type = self.uint32()
        val       = self.value(gguf_type)
        return {"name": name, "value": val, "type": gguf_type}

    def tensor_info(self) -> Dict:
        """Read one tensor descriptor → {"name", "dimensions", "quant_type", "offset"}."""
        name   = self.string()
        n_dims = self.uint32()
        dims   = [self.uint64() for _ in range(n_dims)]
        qtype  = self.uint32()
        offset = self.uint64()
        return {"name": name, "dimensions": dims, "quant_type": qtype, "offset": offset}

    def align_to(self, alignment: int) -> None:
        """Advance cursor to the next ``alignment``-byte boundary."""
        remainder = self._position % alignment
        if remainder:
            self.skip(alignment - remainder)


# ---------------------------------------------------------------------------
# MODUL 5: Quantization registry
# ---------------------------------------------------------------------------

QUANTIZATION_TYPES: Dict[int, Dict] = {
    0:  {"name": "F32",     "block_size": 1,   "type_size": 4,   "dtype": "float32"},
    1:  {"name": "F16",     "block_size": 1,   "type_size": 2,   "dtype": "float16"},
    2:  {"name": "Q4_0",    "block_size": 32,  "type_size": 18,  "dtype": "q4_0"},
    3:  {"name": "Q4_1",    "block_size": 32,  "type_size": 20,  "dtype": "q4_1"},
    6:  {"name": "Q5_0",    "block_size": 32,  "type_size": 22,  "dtype": "q5_0"},
    7:  {"name": "Q5_1",    "block_size": 32,  "type_size": 24,  "dtype": "q5_1"},
    8:  {"name": "Q8_0",    "block_size": 32,  "type_size": 34,  "dtype": "q8_0"},
    9:  {"name": "Q8_1",    "block_size": 32,  "type_size": 40,  "dtype": "q8_1"},
    10: {"name": "Q2_K",    "block_size": 256, "type_size": 84,  "dtype": "q2_K"},
    11: {"name": "Q3_K",    "block_size": 256, "type_size": 110, "dtype": "q3_K"},
    12: {"name": "Q4_K",    "block_size": 256, "type_size": 144, "dtype": "q4_K"},
    13: {"name": "Q5_K",    "block_size": 256, "type_size": 176, "dtype": "q5_K"},
    14: {"name": "Q6_K",    "block_size": 256, "type_size": 210, "dtype": "q6_K"},
    15: {"name": "Q8_K",    "block_size": 256, "type_size": 292, "dtype": "q8_K"},
    16: {"name": "IQ2_XXS", "block_size": 256, "type_size": 66,  "dtype": "iq2_xxs"},
    17: {"name": "IQ2_XS",  "block_size": 256, "type_size": 74,  "dtype": "iq2_xs"},
    18: {"name": "IQ3_XXS", "block_size": 256, "type_size": 98,  "dtype": "iq3_xxs"},
    19: {"name": "IQ1_S",   "block_size": 256, "type_size": 50,  "dtype": "iq1_s"},
    20: {"name": "IQ4_NL",  "block_size": 32,  "type_size": 18,  "dtype": "iq4_nl"},
    21: {"name": "IQ3_S",   "block_size": 256, "type_size": 106, "dtype": "iq3_s"},
    22: {"name": "IQ2_S",   "block_size": 256, "type_size": 84,  "dtype": "iq2_s"},
    23: {"name": "IQ4_XS",  "block_size": 256, "type_size": 136, "dtype": "iq4_xs"},
    24: {"name": "I8",      "block_size": 1,   "type_size": 1,   "dtype": "int8"},
    25: {"name": "I16",     "block_size": 1,   "type_size": 2,   "dtype": "int16"},
    26: {"name": "I32",     "block_size": 1,   "type_size": 4,   "dtype": "int32"},
    27: {"name": "I64",     "block_size": 1,   "type_size": 8,   "dtype": "int64"},
    28: {"name": "F64",     "block_size": 1,   "type_size": 8,   "dtype": "float64"},
    29: {"name": "IQ1_M",   "block_size": 256, "type_size": 56,  "dtype": "iq1_m"},
    30: {"name": "BF16",    "block_size": 1,   "type_size": 2,   "dtype": "bfloat16"},
    34: {"name": "TQ1_0",   "block_size": 256, "type_size": 54,  "dtype": "tq1_0"},
    35: {"name": "TQ2_0",   "block_size": 256, "type_size": 66,  "dtype": "tq2_0"},
    39: {"name": "MXFP4",   "block_size": 32,  "type_size": 17,  "dtype": "mxfp4"},
}


def detect_quantization(quant_type: int) -> Dict:
    return QUANTIZATION_TYPES.get(
        quant_type,
        {"name": f"UNKNOWN_{quant_type}", "block_size": 1, "type_size": 1, "dtype": "unknown"},
    )


# ---------------------------------------------------------------------------
# MODUL 3: TensorInfo
# ---------------------------------------------------------------------------

class TensorInfo:
    """
    Descriptor for a single tensor.  Does NOT hold tensor data in memory —
    call ``GGUFReader.read_tensor_data(name)`` for the raw bytes.
    """

    __slots__ = ("name", "dimensions", "quant_type", "offset",
                 "part_index", "quant_info", "_data_start")

    def __init__(
        self,
        name: str,
        dimensions: List[int],
        quant_type: int,
        offset: int,
        part_index: int = 0,
        data_start: int = 0,
    ):
        self.name        = name
        self.dimensions  = dimensions
        self.quant_type  = quant_type
        self.offset      = offset          # relative to data_start inside the part
        self.part_index  = part_index      # which file shard this tensor lives in
        self._data_start = data_start      # absolute byte offset of tensor data region in part
        self.quant_info  = detect_quantization(quant_type)

    # ----------------------------------------------------------------- props
    @property
    def dtype(self) -> str:
        return self.quant_info["dtype"]

    @property
    def block_size(self) -> int:
        return self.quant_info["block_size"]

    @property
    def type_size(self) -> int:
        return self.quant_info["type_size"]

    @property
    def n_elements(self) -> int:
        n = 1
        for d in self.dimensions:
            n *= d
        return n

    @property
    def n_bytes(self) -> int:
        bs = self.block_size
        return (self.n_elements * self.type_size) // bs if bs > 0 else self.n_elements * self.type_size

    @property
    def shape_str(self) -> str:
        return " × ".join(str(d) for d in self.dimensions)

    def to_dict(self) -> Dict:
        return {
            "name":       self.name,
            "dimensions": self.dimensions,
            "quant_type": self.quant_type,
            "quant_name": self.quant_info["name"],
            "dtype":      self.dtype,
            "offset":     self.offset,
            "part_index": self.part_index,
            "n_elements": self.n_elements,
            "n_bytes":    self.n_bytes,
        }

    def __repr__(self) -> str:
        return f"TensorInfo({self.name!r}, [{self.shape_str}], {self.dtype}, part={self.part_index})"


# ---------------------------------------------------------------------------
# MODUL 4: MetadataReader + known architectures
# ---------------------------------------------------------------------------

KNOWN_ARCHITECTURES: Dict[str, Dict] = {
    "llama":     {"family": "decoder"},
    "llama4":    {"family": "decoder-moe"},
    "mistral":   {"family": "decoder"},
    "mixtral":   {"family": "decoder-moe"},
    "qwen2":     {"family": "decoder"},
    "qwen2moe":  {"family": "decoder-moe"},
    "deepseek2": {"family": "decoder-moe"},
    "phi3":      {"family": "decoder"},
    "gemma":     {"family": "decoder"},
    "gemma2":    {"family": "decoder"},
    "stablelm":  {"family": "decoder"},
    "starcoder": {"family": "decoder"},
    "falcon":    {"family": "decoder"},
    "gpt2":      {"family": "decoder"},
    "bloom":     {"family": "decoder"},
    "mpt":       {"family": "decoder"},
    "refact":    {"family": "decoder"},
    "bert":      {"family": "encoder"},
    "nomic-bert":{"family": "encoder"},
    "jina-bert-v2":{"family": "encoder"},
    "t5":        {"family": "encoder-decoder"},
    "rwkv":      {"family": "rwkv"},
    "mamba":     {"family": "ssm"},
}

# Tokenizer model types
TOKENIZER_MODELS = {
    "llm_compiler": "BPE",
    "gpt2":         "BPE",
    "llama":        "SPM",
    "bert":         "WPM",
    "t5":           "UNM",
    "rwkv":         "RWKV",
}


class MetadataReader:
    """
    Typed accessor over raw GGUF metadata dict.
    Works on the *merged* metadata produced by ``GGUFReader``.
    """

    def __init__(self, metadata: Dict):
        self._m = metadata

    # ----------------------------------------------------------------- core
    def get(self, key: str, default=None):
        return self._m.get(key, default)

    def get_model_name(self) -> str:
        return self._m.get("general.name", "Unknown")

    def get_architecture(self) -> str:
        return self._m.get("general.architecture", "unknown")

    def _arch_key(self, suffix: str):
        return f"{self.get_architecture()}.{suffix}"

    # ----------------------------------------------- architecture dimensions
    def get_block_count(self) -> int:
        return self._m.get(self._arch_key("block_count"), 0)

    def get_context_length(self) -> int:
        return self._m.get(self._arch_key("context_length"), 0)

    def get_embedding_length(self) -> int:
        return self._m.get(self._arch_key("embedding_length"), 0)

    def get_feed_forward_length(self) -> int:
        return self._m.get(self._arch_key("feed_forward_length"), 0)

    def get_head_count(self) -> int:
        return self._m.get(self._arch_key("attention.head_count"), 0)

    def get_kv_head_count(self) -> int:
        return self._m.get(self._arch_key("attention.head_count_kv"), 0)

    def get_head_dim(self) -> int:
        return self._m.get(self._arch_key("attention.key_length"), 0)

    def get_rope_freq_base(self) -> float:
        return self._m.get(self._arch_key("rope.freq_base"), 10000.0)

    def get_rope_dim_count(self) -> int:
        return self._m.get(self._arch_key("rope.dimension_count"), 0)

    # ------------------------------------------------------------------ MoE
    def is_moe(self) -> bool:
        arch = self.get_architecture()
        family = KNOWN_ARCHITECTURES.get(arch, {}).get("family", "")
        if "moe" in family:
            return True
        return bool(self._m.get(self._arch_key("expert_count"), 0))

    def get_expert_count(self) -> int:
        return self._m.get(self._arch_key("expert_count"), 0)

    def get_expert_used_count(self) -> int:
        return self._m.get(self._arch_key("expert_used_count"), 0)

    # ------------------------------------------------------------- tokenizer
    def get_tokenizer_model(self) -> str:
        return self._m.get("tokenizer.ggml.model", "unknown")

    def get_vocab_size(self) -> int:
        return self._m.get(self._arch_key("vocab_size"), 0) or len(
            self._m.get("tokenizer.ggml.tokens", [])
        )

    def get_bos_token_id(self) -> int:
        return self._m.get("tokenizer.ggml.bos_token_id", -1)

    def get_eos_token_id(self) -> int:
        return self._m.get("tokenizer.ggml.eos_token_id", -1)

    def get_pad_token_id(self) -> int:
        return self._m.get("tokenizer.ggml.padding_token_id", -1)

    def get_unk_token_id(self) -> int:
        return self._m.get("tokenizer.ggml.unknown_token_id", -1)

    def get_chat_template(self) -> str:
        return self._m.get("tokenizer.chat_template", "")

    # ----------------------------------------------------------------- misc
    def get_file_type(self) -> int:
        return self._m.get("general.file_type", 0)

    def get_all_metadata(self) -> Dict:
        return dict(self._m)

    def get_summary(self) -> Dict:
        return {
            "name":           self.get_model_name(),
            "architecture":   self.get_architecture(),
            "layers":         self.get_block_count(),
            "context_length": self.get_context_length(),
            "embedding_dim":  self.get_embedding_length(),
            "ffn_dim":        self.get_feed_forward_length(),
            "heads":          self.get_head_count(),
            "kv_heads":       self.get_kv_head_count(),
            "vocab_size":     self.get_vocab_size(),
            "is_moe":         self.is_moe(),
            "experts":        self.get_expert_count() if self.is_moe() else 0,
            "experts_used":   self.get_expert_used_count() if self.is_moe() else 0,
            "rope_freq_base": self.get_rope_freq_base(),
            "tokenizer":      self.get_tokenizer_model(),
            "bos_id":         self.get_bos_token_id(),
            "eos_id":         self.get_eos_token_id(),
            "chat_template":  bool(self.get_chat_template()),
        }


# ---------------------------------------------------------------------------
# MODUL 7: VocabMerger — merge tokenizer vocab across parts
# ---------------------------------------------------------------------------

class VocabMerger:
    """
    Merges ``tokenizer.ggml.*`` arrays that may be spread across multiple
    GGUF shards.

    Each shard may carry a *slice* of the vocabulary or the complete vocab.
    The merger:
      1. Detects whether a shard carries a full or partial vocab (by
         comparing list length against the declared ``vocab_size``).
      2. Deduplicates exact duplicates.
      3. Checks for index-based gaps or overlaps and warns about them.
      4. Merges scores, token_type, and merges arrays in the same pass.
    """

    VOCAB_KEYS = (
        "tokenizer.ggml.tokens",
        "tokenizer.ggml.scores",
        "tokenizer.ggml.token_type",
        "tokenizer.ggml.merges",
        "tokenizer.ggml.added_tokens",
    )

    def __init__(self):
        self._slices: List[Tuple[int, Dict]] = []   # (part_index, metadata_dict)

    def add_part(self, part_index: int, metadata: Dict) -> None:
        """Register a shard's metadata for later merging."""
        self._slices.append((part_index, metadata))

    def merge(self, declared_vocab_size: int = 0) -> Dict:
        """
        Return a single merged metadata dict containing unified vocab arrays.
        """
        if not self._slices:
            return {}

        # Sort by part index so we append in order
        self._slices.sort(key=lambda x: x[0])

        merged: Dict[str, list] = {k: [] for k in self.VOCAB_KEYS}
        seen_tokens: Dict[str, int] = {}      # token_str → first index seen
        duplicate_count = 0

        for part_idx, meta in self._slices:
            tokens = meta.get("tokenizer.ggml.tokens", [])
            scores = meta.get("tokenizer.ggml.scores", [])
            ttypes = meta.get("tokenizer.ggml.token_type", [])
            merges = meta.get("tokenizer.ggml.merges", [])
            added  = meta.get("tokenizer.ggml.added_tokens", [])

            for i, tok in enumerate(tokens):
                global_idx = len(merged["tokenizer.ggml.tokens"])
                if tok in seen_tokens:
                    duplicate_count += 1
                    continue
                seen_tokens[tok] = global_idx
                merged["tokenizer.ggml.tokens"].append(tok)
                merged["tokenizer.ggml.scores"].append(
                    scores[i] if i < len(scores) else 0.0
                )
                merged["tokenizer.ggml.token_type"].append(
                    ttypes[i] if i < len(ttypes) else 1
                )

            # Merges / added tokens: just extend, dedup later
            for entry in merges:
                if entry not in merged["tokenizer.ggml.merges"]:
                    merged["tokenizer.ggml.merges"].append(entry)
            for entry in added:
                if entry not in merged["tokenizer.ggml.added_tokens"]:
                    merged["tokenizer.ggml.added_tokens"].append(entry)

        actual = len(merged["tokenizer.ggml.tokens"])
        if duplicate_count:
            warnings.warn(
                f"VocabMerger: {duplicate_count} duplicate token(s) removed.",
                RuntimeWarning, stacklevel=2,
            )
        if declared_vocab_size and actual != declared_vocab_size:
            warnings.warn(
                f"VocabMerger: merged vocab size {actual} ≠ declared {declared_vocab_size}.",
                RuntimeWarning, stacklevel=2,
            )

        # Drop empty lists to keep metadata clean
        return {k: v for k, v in merged.items() if v}


# ---------------------------------------------------------------------------
# Part-file auto-discovery helpers
# ---------------------------------------------------------------------------

# Patterns for common split-GGUF naming conventions:
#   model-00001-of-00005.gguf     (HF style)
#   model.gguf.part1              (naive split)
#   model-split-a.gguf            (alpha suffix)
_SPLIT_PATTERNS = [
    re.compile(r"^(.+)-(\d+)-of-(\d+)(\.gguf)$", re.IGNORECASE),  # HF
    re.compile(r"^(.+)(\.gguf)\.part(\d+)$",      re.IGNORECASE),  # .part
    re.compile(r"^(.+)-split-([a-z])(\.gguf)$",   re.IGNORECASE),  # alpha
]


def _parse_part_number(path: Path) -> Tuple[int, int]:
    """Return (part_number, total_parts) for a split filename, else (0, 1)."""
    name = path.name
    for pat in _SPLIT_PATTERNS:
        m = pat.match(name)
        if m:
            groups = m.groups()
            if len(groups) == 4:   # HF style
                return int(groups[1]), int(groups[2])
            if len(groups) == 3 and groups[2].isdigit():   # .part style
                return int(groups[2]), 0
            if len(groups) == 3:   # alpha style
                return ord(groups[1]) - ord("a") + 1, 0
    return 0, 1


def discover_parts(seed_path: Union[str, Path]) -> List[Path]:
    """
    Given any one shard of a split-GGUF model, find and sort all sibling
    shards in the same directory.  Returns a sorted list (including the
    seed file).  Falls back to ``[seed_path]`` if no siblings detected.
    """
    seed = Path(seed_path)
    part_no, total = _parse_part_number(seed)
    if total == 1:
        return [seed]   # single file, nothing to discover

    siblings: List[Path] = []
    for candidate in seed.parent.iterdir():
        if candidate.suffix.lower() in (".gguf",) or ".gguf" in candidate.name.lower():
            cp, _ = _parse_part_number(candidate)
            if cp > 0:
                siblings.append(candidate)

    if not siblings:
        return [seed]

    siblings.sort(key=lambda p: _parse_part_number(p)[0])
    return siblings


# ---------------------------------------------------------------------------
# MODUL 1 + 2: GGUFReader — multi-part, mmap, magic-scan
# ---------------------------------------------------------------------------

class GGUFReader:
    """
    Parse one or more GGUF files (split shards) into a single unified view.

    Parameters
    ----------
    paths : str | Path | list[str | Path]
        One or more GGUF file paths.  If a single path is given and it
        matches a split-file naming pattern, sibling parts are discovered
        automatically unless ``auto_discover=False``.
    auto_discover : bool
        Auto-find sibling shards when only one path is supplied.
    use_mmap : bool
        Memory-map files instead of loading into RAM.  Highly recommended
        for files > 1 GB.  Set False if the filesystem does not support
        mmap (e.g., some network mounts).
    scan_magic : bool
        Scan each file for the GGUF magic bytes instead of assuming they
        start at byte 0.  Slightly slower but handles prefixed files.
    progress : callable | None
        Called as ``progress(part_index, total_parts, path)`` after each
        part is parsed.
    """

    GGUF_MAGIC = b"GGUF"

    def __init__(
        self,
        paths: Union[str, "os.PathLike[str]", List[Union[str, "os.PathLike[str]"]]],
        *,
        auto_discover: bool = True,
        use_mmap: bool = True,
        scan_magic: bool = True,
        progress: Optional[Callable[[int, int, Path], None]] = None,
    ):
        # ---- normalize input to list[Path] ----
        if isinstance(paths, (str, os.PathLike)):
            raw = [Path(paths)]
        else:
            raw = [Path(p) for p in paths]

        if len(raw) == 1 and auto_discover:
            raw = discover_parts(raw[0])

        # Sort by embedded part number (if any)
        raw.sort(key=lambda p: (_parse_part_number(p)[0], p.name))
        self.paths: List[Path] = raw

        self.use_mmap   = use_mmap
        self.scan_magic = scan_magic
        self.progress   = progress

        # Output state (populated by read())
        self.parts:     List[Dict]   = []        # per-shard raw parse results
        self.metadata:  Dict         = {}        # merged metadata
        self.tensors:   Dict[str, TensorInfo] = {}
        self.alignment: int          = 32
        self._vocab_merger = VocabMerger()

    # ================================================================ public
    def read(self) -> Dict:
        """
        Parse all shards, merge results, return unified dict with keys:
          header, metadata, tensors, alignment, vocab, parts_info
        """
        total = len(self.paths)
        for idx, path in enumerate(self.paths):
            part = self._read_one_part(path, part_index=idx)
            self.parts.append(part)
            self._vocab_merger.add_part(idx, part["raw_metadata"])
            if self.progress:
                self.progress(idx + 1, total, path)

        # ---- merge metadata: first shard wins for duplicates ----
        for part in self.parts:
            for k, v in part["raw_metadata"].items():
                if k not in self.metadata:
                    self.metadata[k] = v

        # ---- merge vocab ----
        meta_reader = MetadataReader(self.metadata)
        vocab_size  = meta_reader.get_vocab_size()
        merged_vocab = self._vocab_merger.merge(declared_vocab_size=vocab_size)
        self.metadata.update(merged_vocab)

        # ---- merge tensors (tensors in later parts override earlier only
        #      if their name collides — in practice each tensor is unique) ----
        for part in self.parts:
            for name, tinfo in part["tensors"].items():
                if name in self.tensors:
                    warnings.warn(
                        f"Tensor {name!r} appears in multiple parts; "
                        "keeping first occurrence.",
                        RuntimeWarning, stacklevel=2,
                    )
                else:
                    self.tensors[name] = tinfo

        self.alignment = self.metadata.get("general.alignment", 32)

        return {
            "header":     self.parts[0]["header"] if self.parts else {},
            "metadata":   self.metadata,
            "tensors":    {k: v.to_dict() for k, v in self.tensors.items()},
            "alignment":  self.alignment,
            "parts_info": [p["info"] for p in self.parts],
            "vocab":      {
                "size":   len(self.metadata.get("tokenizer.ggml.tokens", [])),
                "model":  self.metadata.get("tokenizer.ggml.model", "unknown"),
            },
        }

    # ---------------------------------------------------------------- info
    def get_model_info(self) -> Dict:
        return MetadataReader(self.metadata).get_summary()

    def get_metadata(self) -> MetadataReader:
        return MetadataReader(self.metadata)

    def list_tensors(self) -> List[str]:
        return list(self.tensors.keys())

    def get_tensor_count(self) -> int:
        return len(self.tensors)

    def get_layer_count(self) -> int:
        return MetadataReader(self.metadata).get_block_count()

    def get_quantization_info(self) -> Dict:
        # Use the first weight tensor (skip embeddings / norms for better repr)
        for name, t in self.tensors.items():
            if "weight" in name and "norm" not in name and "embed" not in name:
                return detect_quantization(t.quant_type)
        if self.tensors:
            return detect_quantization(next(iter(self.tensors.values())).quant_type)
        return {"name": "Unknown", "block_size": 1, "type_size": 1, "dtype": "unknown"}

    def get_total_size(self) -> int:
        """Sum of file sizes across all parts."""
        return sum(p.stat().st_size for p in self.paths)

    def get_summary(self) -> str:
        mr    = MetadataReader(self.metadata)
        s     = mr.get_summary()
        quant = self.get_quantization_info()
        parts = len(self.paths)
        total = _fmt_bytes(self.get_total_size())
        lines = [
            f"Model     : {s['name']}",
            f"Arch      : {s['architecture']}",
            f"Parts     : {parts}  ({total})",
            f"Tensors   : {self.get_tensor_count()}",
            f"Layers    : {s['layers']}",
            f"Ctx len   : {s['context_length']:,}",
            f"Embed dim : {s['embedding_dim']:,}",
            f"Heads     : {s['heads']}  (KV: {s['kv_heads']})",
            f"Vocab     : {s['vocab_size']:,}  ({s['tokenizer']})",
            f"Quant     : {quant['name']} ({quant['dtype']})",
        ]
        if s["is_moe"]:
            lines.append(f"MoE       : {s['experts']} experts, {s['experts_used']} active")
        if s["chat_template"]:
            lines.append("Template  : yes")
        return "\n".join(lines)

    # --------------------------------------------------------- tensor data
    def read_tensor_data(self, name: str) -> Optional[bytes]:
        """
        Lazily read raw bytes for tensor ``name`` directly from the file
        shard it lives in.  Uses mmap when available.
        """
        tinfo = self.tensors.get(name)
        if tinfo is None:
            return None

        path = self.paths[tinfo.part_index]
        abs_offset = tinfo._data_start + tinfo.offset

        with open(path, "rb") as fh:
            if self.use_mmap:
                try:
                    with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        mm.seek(abs_offset)
                        return mm.read(tinfo.n_bytes)
                except (mmap.error, ValueError):
                    pass
            fh.seek(abs_offset)
            return fh.read(tinfo.n_bytes)

    def iter_tensors(self) -> Iterator[Tuple[str, TensorInfo]]:
        """Yield ``(name, TensorInfo)`` for every tensor."""
        yield from self.tensors.items()

    # ============================================================= internal
    def _read_one_part(self, path: Path, part_index: int) -> Dict:
        """
        Parse a single GGUF shard.  Handles:
          - magic scanning (offset may not be 0)
          - mmap for large files
          - returns raw metadata + TensorInfo objects
        """
        file_size = path.stat().st_size

        fh = open(path, "rb")
        try:
            if self.use_mmap and file_size > 0:
                try:
                    data = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
                    _mmap_open = True
                except (mmap.error, ValueError):
                    data = fh.read()
                    _mmap_open = False
            else:
                data = fh.read()
                _mmap_open = False
        finally:
            if not (self.use_mmap and isinstance(data, mmap.mmap)):
                fh.close()

        try:
            result = self._parse_gguf(data, path, part_index, file_size)
        finally:
            if isinstance(data, mmap.mmap):
                data.close()
                fh.close()

        return result

    def _parse_gguf(
        self,
        data: Union[bytes, mmap.mmap],
        path: Path,
        part_index: int,
        file_size: int,
    ) -> Dict:
        # ---- find magic ----
        if self.scan_magic:
            magic_offset = BinaryReader.find_magic_offset(data)
        else:
            if data[:4] != self.GGUF_MAGIC:
                raise ValueError(f"{path}: does not start with GGUF magic")
            magic_offset = 0

        r = BinaryReader(data, little_endian=True, base_offset=magic_offset)

        # ---- header ----
        r.seek(magic_offset)
        magic_bytes = r.read(4)
        assert magic_bytes == self.GGUF_MAGIC
        version = r.uint32()
        if version < 2:
            raise ValueError(f"{path}: unsupported GGUF version {version}")

        n_tensors      = r.uint64()
        n_metadata_kv  = r.uint64()

        header = {
            "magic":        "GGUF",
            "version":      version,
            "format":       f"GGUF v{version}",
            "n_tensors":    n_tensors,
            "n_metadata_kv": n_metadata_kv,
            "magic_offset": magic_offset,
        }

        # ---- metadata ----
        raw_metadata: Dict = {}
        for _ in range(n_metadata_kv):
            entry = r.entry()
            raw_metadata[entry["name"]] = entry["value"]

        # ---- tensor descriptors ----
        raw_tensors: List[Dict] = []
        for _ in range(n_tensors):
            raw_tensors.append(r.tensor_info())

        # ---- alignment & data start ----
        alignment  = raw_metadata.get("general.alignment", 32)
        r.align_to(alignment)
        data_start = r.position     # absolute offset where tensor data begins in file

        # ---- build TensorInfo objects ----
        tensors: Dict[str, TensorInfo] = {}
        for td in raw_tensors:
            ti = TensorInfo(
                name       = td["name"],
                dimensions = td["dimensions"],
                quant_type = td["quant_type"],
                offset     = td["offset"],
                part_index = part_index,
                data_start = data_start,
            )
            tensors[ti.name] = ti

        return {
            "path":         path,
            "header":       header,
            "raw_metadata": raw_metadata,
            "tensors":      tensors,
            "alignment":    alignment,
            "info": {
                "path":       str(path),
                "file_size":  file_size,
                "part_index": part_index,
                "n_tensors":  n_tensors,
                "version":    version,
                "magic_at":   magic_offset,
            },
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def load(
    paths: Union[str, Path, List[Union[str, Path]]],
    **kwargs,
) -> GGUFReader:
    """
    Shorthand: parse and return a ready-to-use ``GGUFReader``.

    Example
    -------
    >>> model = load("Meta-Llama-3-8B-Q4_K_M-00001-of-00003.gguf")
    >>> print(model.get_summary())
    """
    reader = GGUFReader(paths, **kwargs)
    reader.read()
    return reader


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python gguf_parser.py <file.gguf> [file2.gguf ...]")
        sys.exit(1)

    paths = sys.argv[1:]

    def on_progress(cur, total, p):
        print(f"  [{cur}/{total}] parsed {p.name}")

    print(f"Loading {len(paths)} path(s) …")
    model = load(paths, progress=on_progress)

    print("\n" + "=" * 60)
    print(model.get_summary())
    print("=" * 60)

    mr = model.get_metadata()
    chat_tmpl = mr.get_chat_template()
    if chat_tmpl:
        print(f"\nChat template ({len(chat_tmpl)} chars): {chat_tmpl[:120]} …")

    print(f"\nFirst 10 tensors:")
    for name in list(model.list_tensors())[:10]:
        t = model.tensors[name]
        print(f"  {t}")

    result = model.read()
    print(f"\nParts info:")
    print(json.dumps(result["parts_info"], indent=2))

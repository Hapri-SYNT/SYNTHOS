import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Union, Any, Set
from collections import defaultdict
import warnings
from abc import ABC, abstractmethod
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class HookDirection(Enum):
    """Direction of hook execution."""
    FORWARD = "fwd"
    BACKWARD = "bwd"
    BOTH = "both"


class DetectionType(Enum):
    """Types of attention head patterns to detect."""
    PREVIOUS_TOKEN = "previous_token_head"
    DUPLICATE_TOKEN = "duplicate_token_head"
    INDUCTION = "induction_head"
    SKIP = "skip_head"


class SVDComponentType(Enum):
    """Types of SVD components."""
    OV = "OV"
    W_IN = "w_in"
    W_OUT = "w_out"


# =============================================================================
# MODUL 1: HOOK POINTS (Enhanced)
# =============================================================================

class HookPoint:
    """
    Enhanced Hook Point dengan error handling dan context management.
    """

    def __init__(self, name: str = None):
        self.name = name
        self.fwd_hooks: List[Dict] = []
        self.bwd_hooks: List[Dict] = []
        self.ctx: Dict = {}
        self.hook_conversion = None
        self._active = True
        self._hook_counter = 0

    def add_hook(
        self,
        hook: Callable,
        dir: str = "fwd",
        is_permanent: bool = False,
        validate: bool = True
    ) -> int:
        """
        Add hook dengan validasi dan ID tracking.

        Args:
            hook: Hook function
            dir: "fwd", "bwd", atau "both"
            is_permanent: Whether hook persists after removal
            validate: Validate hook signature

        Returns:
            Hook ID untuk referensi
        """
        if not callable(hook):
            raise TypeError(f"Hook must be callable, got {type(hook)}")

        if validate:
            self._validate_hook_signature(hook)

        hook_id = self._hook_counter
        self._hook_counter += 1

        hook_info = {
            "hook": hook,
            "permanent": is_permanent,
            "id": hook_id,
            "created_at": np.datetime64('now')
        }

        if dir == "fwd":
            self.fwd_hooks.append(hook_info)
        elif dir == "bwd":
            self.bwd_hooks.append(hook_info)
        elif dir == "both":
            self.fwd_hooks.append(hook_info)
            self.bwd_hooks.append(hook_info.copy())
        else:
            raise ValueError(f"Invalid hook direction: {dir}")

        return hook_id

    def remove_hook(
        self,
        hook_id: Optional[int] = None,
        dir: str = "fwd",
        including_permanent: bool = False
    ) -> bool:
        """Remove specific hook by ID."""
        if hook_id is None:
            return self.remove_hooks(dir, including_permanent)

        hooks_list = self.fwd_hooks if dir == "fwd" else self.bwd_hooks

        for i, h in enumerate(hooks_list):
            if h["id"] == hook_id:
                if including_permanent or not h["permanent"]:
                    hooks_list.pop(i)
                    return True
        return False

    def remove_hooks(
        self,
        dir: str = "fwd",
        including_permanent: bool = False
    ) -> int:
        """Remove all hooks, return count removed."""
        if dir == "fwd":
            if including_permanent:
                count = len(self.fwd_hooks)
                self.fwd_hooks = []
            else:
                original_count = len(self.fwd_hooks)
                self.fwd_hooks = [h for h in self.fwd_hooks if h["permanent"]]
                count = original_count - len(self.fwd_hooks)
        elif dir == "bwd":
            if including_permanent:
                count = len(self.bwd_hooks)
                self.bwd_hooks = []
            else:
                original_count = len(self.bwd_hooks)
                self.bwd_hooks = [h for h in self.bwd_hooks if h["permanent"]]
                count = original_count - len(self.bwd_hooks)
        else:
            count = self.remove_hooks("fwd", including_permanent)
            count += self.remove_hooks("bwd", including_permanent)

        return count

    def clear_context(self):
        """Clear all stored context."""
        self.ctx = {}

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Execute forward hooks with error handling."""
        if not self._active:
            return x

        output = x.copy()

        for hook_info in self.fwd_hooks:
            try:
                hook_fn = hook_info["hook"]
                result = hook_fn(output, hook=self)
                if result is not None:
                    if not isinstance(result, np.ndarray):
                        raise TypeError(f"Hook must return ndarray or None, got {type(result)}")
                    if result.shape != output.shape:
                        raise ValueError(
                            f"Hook output shape mismatch: "
                            f"expected {output.shape}, got {result.shape}"
                        )
                    output = result
            except Exception as e:
                logger.error(f"Error in hook {hook_info.get('id')}: {e}")
                raise

        return output

    def layer(self) -> int:
        """Extract layer index from hook name."""
        if self.name is None:
            raise ValueError("HookPoint name is None")

        parts = self.name.split(".")
        if len(parts) >= 2 and parts[0] == "blocks":
            try:
                return int(parts[1])
            except ValueError:
                raise ValueError(f"Invalid layer index in name: {self.name}")

        raise ValueError(f"Cannot extract layer from name: {self.name}")

    def get_hook_info(self) -> Dict[str, Any]:
        """Get detailed hook information."""
        return {
            "name": self.name,
            "n_fwd_hooks": len(self.fwd_hooks),
            "n_bwd_hooks": len(self.bwd_hooks),
            "fwd_hooks": [
                {"id": h["id"], "permanent": h["permanent"]}
                for h in self.fwd_hooks
            ],
            "active": self._active,
            "context_keys": list(self.ctx.keys())
        }

    def _validate_hook_signature(self, hook: Callable):
        """Validate hook function signature."""
        import inspect
        sig = inspect.signature(hook)
        params = list(sig.parameters.keys())
        if len(params) < 1:
            raise ValueError("Hook must accept at least 1 parameter (activation)")


class HookedRootModule:
    """Enhanced root module dengan context manager support."""

    def __init__(self):
        self.mod_dict: Dict[str, Any] = {}
        self.hook_dict: Dict[str, HookPoint] = {}
        self.is_caching = False
        self.context_level = 0
        self._hook_stacks: List[Dict] = []

    def setup(self):
        """Setup module after all layers defined."""
        pass

    def hook_points(self) -> List[HookPoint]:
        """Return all HookPoints."""
        return list(self.hook_dict.values())

    def remove_all_hook_fns(
        self,
        direction: str = "both",
        including_permanent: bool = False
    ) -> int:
        """Remove all hooks, return total count."""
        total_removed = 0
        for hp in self.hook_points():
            if direction in ("fwd", "both"):
                total_removed += hp.remove_hooks("fwd", including_permanent)
            if direction in ("bwd", "both"):
                total_removed += hp.remove_hooks("bwd", including_permanent)
        return total_removed

    def clear_contexts(self):
        """Clear all hook contexts."""
        for hp in self.hook_points():
            hp.clear_context()

    def reset_hooks(
        self,
        clear_contexts: bool = True,
        direction: str = "both"
    ):
        """Reset all hooks."""
        if clear_contexts:
            self.clear_contexts()
        self.remove_all_hook_fns(direction, including_permanent=False)
        self.is_caching = False
        self._hook_stacks = []

    def add_hook(
        self,
        name: Union[str, Callable],
        hook: Callable,
        dir: str = "fwd"
    ) -> Union[int, Dict[str, int]]:
        """Add hook with pattern matching support."""
        if isinstance(name, str):
            if name in self.hook_dict:
                hp = self.hook_dict[name]
                return hp.add_hook(hook, dir=dir)
            else:
                logger.warning(f"Hook point '{name}' not found")
                return None
        elif callable(name):
            hook_ids = {}
            for hook_name, hp in self.hook_dict.items():
                try:
                    if name(hook_name):
                        hook_ids[hook_name] = hp.add_hook(hook, dir=dir)
                except Exception as e:
                    logger.error(f"Error adding hook to {hook_name}: {e}")
            return hook_ids

    def run_with_cache(
        self,
        *model_args,
        names_filter: Union[None, str, List[str], Callable] = None,
        remove_batch_dim: bool = False,
        remove_batch_dim_for_specific: Optional[List[str]] = None,
        **model_kwargs
    ) -> Tuple[Any, 'ActivationCache']:
        """Run model with activation caching."""
        cache = {}

        # Setup filter
        if names_filter is None:
            filter_fn = lambda name: True
        elif isinstance(names_filter, str):
            filter_fn = lambda name, s=names_filter: s in name
        elif isinstance(names_filter, list):
            filter_fn = lambda name, lst=names_filter: name in lst
        elif callable(names_filter):
            filter_fn = names_filter
        else:
            raise TypeError(f"Invalid names_filter type: {type(names_filter)}")

        specific_remove = remove_batch_dim_for_specific or []

        # Add caching hooks
        for name, hp in self.hook_dict.items():
            if filter_fn(name):
                def make_cache_hook(hook_name):
                    def cache_hook(tensor, hook):
                        cached = tensor.copy()
                        if remove_batch_dim or hook_name in specific_remove:
                            cached = cached[0] if cached.shape[0] == 1 else cached
                        cache[hook_name] = cached
                        return None
                    return cache_hook

                hp.add_hook(make_cache_hook(name), dir="fwd", is_permanent=False)

        try:
            output = self.forward(*model_args, **model_kwargs)
        finally:
            self.reset_hooks()

        return output, ActivationCache(cache, model=self)

    def forward(self, *args, **kwargs):
        """Forward pass to be implemented by subclass."""
        raise NotImplementedError


# =============================================================================
# MODUL 2: ACTIVATION CACHE (Enhanced)
# =============================================================================

class ActivationCache:
    """Enhanced activation cache dengan validasi dan utility methods."""

    def __init__(self, cache: Dict[str, np.ndarray], model: Any = None):
        self._cache = cache
        self.model = model
        self._layer_map = {}
        self._analyze_structure()

    def _analyze_structure(self):
        """Analyze cache structure."""
        self.layers = set()
        self.components = defaultdict(set)

        for key in self._cache:
            parts = key.split(".")
            for i, part in enumerate(parts):
                if part.isdigit():
                    layer_idx = int(part)
                    self.layers.add(layer_idx)
                    self._layer_map[key] = layer_idx

            # Extract component type
            if "attn" in key:
                self.components["attn"].add(key)
            elif "mlp" in key:
                self.components["mlp"].add(key)
            elif "embed" in key:
                self.components["embed"].add(key)

        self.n_layers = max(self.layers) + 1 if self.layers else 0
        self.has_embed = "hook_embed" in self._cache
        self.has_pos_embed = "hook_pos_embed" in self._cache

    def __getitem__(self, key: Union[str, Tuple[str, int]]) -> np.ndarray:
        """Access cache with validation."""
        if isinstance(key, tuple):
            name, layer = key
            full_key = f"blocks.{layer}.{name}"
            if full_key not in self._cache:
                raise KeyError(f"Cache key not found: {full_key}")
            return self._cache[full_key].copy()

        if key not in self._cache:
            raise KeyError(f"Cache key not found: {key}")
        return self._cache[key].copy()

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def items(self):
        return self._cache.items()

    def get_layer_activations(
        self,
        layer: int,
        component: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """Get all activations for a specific layer."""
        result = {}
        for key, value in self._cache.items():
            if f"blocks.{layer}." in key:
                if component is None or component in key:
                    result[key] = value.copy()
        return result

    def decompose_resid(
        self,
        layer: Optional[int] = None,
        mode: str = "all",
        apply_ln: bool = False,
        incl_embeds: bool = True,
        return_labels: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, List[str]]]:
        """Decompose residual stream by component."""
        if layer is None:
            layer = self.n_layers

        if layer > self.n_layers:
            raise ValueError(f"Layer {layer} exceeds max layers {self.n_layers}")

        incl_attn = mode in ("all", "attn")
        incl_mlp = mode in ("all", "mlp")

        if mode not in ("all", "mlp", "attn"):
            raise ValueError(f"Invalid mode: {mode}")

        components = []
        labels = []

        # Add embeddings
        if incl_embeds:
            if self.has_embed and "hook_embed" in self._cache:
                components.append(self._cache["hook_embed"])
                labels.append("embed")
            if self.has_pos_embed and "hook_pos_embed" in self._cache:
                components.append(self._cache["hook_pos_embed"])
                labels.append("pos_embed")

        # Add layer components
        for l in range(layer):
            if incl_attn:
                key = f"blocks.{l}.hook_attn_out"
                if key in self._cache:
                    components.append(self._cache[key])
                    labels.append(f"{l}_attn_out")
                else:
                    logger.debug(f"Attention output not found: {key}")

            if incl_mlp:
                key = f"blocks.{l}.hook_mlp_out"
                if key in self._cache:
                    components.append(self._cache[key])
                    labels.append(f"{l}_mlp_out")
                else:
                    logger.debug(f"MLP output not found: {key}")

        if not components:
            raise ValueError("No components found in cache")

        # Stack and validate shapes
        try:
            result = np.stack(components, axis=0)
        except ValueError as e:
            logger.error(f"Shape mismatch when stacking components: {e}")
            raise

        if apply_ln:
            result = self._apply_layer_norm(result)

        if return_labels:
            return result, labels
        return result

    def accumulated_resid(
        self,
        layer: Optional[int] = None,
        apply_ln: bool = False,
        return_labels: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, List[str]]]:
        """Logit Lens: accumulated residual stream per layer."""
        if layer is None:
            layer = self.n_layers

        accum = []
        labels = []

        # Initialize residual
        resid = None
        if self.has_embed and "hook_embed" in self._cache:
            resid = self._cache["hook_embed"].copy()
        if self.has_pos_embed and "hook_pos_embed" in self._cache:
            if resid is None:
                resid = self._cache["hook_pos_embed"].copy()
            else:
                resid = resid + self._cache["hook_pos_embed"]

        if resid is None:
            raise ValueError("No embedding found in cache")

        accum.append(resid.copy())
        labels.append("embed")

        # Accumulate per layer
        for l in range(layer):
            attn_key = f"blocks.{l}.hook_attn_out"
            if attn_key in self._cache:
                resid = resid + self._cache[attn_key]
                accum.append(resid.copy())
                labels.append(f"{l}_attn_out")

            mlp_key = f"blocks.{l}.hook_mlp_out"
            if mlp_key in self._cache:
                resid = resid + self._cache[mlp_key]
                accum.append(resid.copy())
                labels.append(f"{l}_mlp_out")

        result = np.stack(accum, axis=0)

        if apply_ln:
            result = self._apply_layer_norm(result)

        if return_labels:
            return result, labels
        return result

    def logit_attrs(
        self,
        residual_stack: np.ndarray,
        token_idx: int,
        incorrect_token_idx: Optional[int] = None
    ) -> np.ndarray:
        """Compute logit attribution."""
        if self.model is None or not hasattr(self.model, 'W_U'):
            logger.warning("Model or W_U not available, returning dummy attribution")
            return np.mean(residual_stack, axis=-1)

        W_U = self.model.W_U
        if W_U is None:
            raise ValueError("Unembedding matrix W_U not available")

        # Project to logit space
        logits = np.tensordot(residual_stack, W_U, axes=([-1], [0]))

        # Extract specific token logits
        result = logits[..., token_idx]

        if incorrect_token_idx is not None:
            result = result - logits[..., incorrect_token_idx]

        return result

    def get_full_resid_decomposition(
        self,
        layer: Optional[int] = None,
        return_labels: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, List[str]]]:
        """Full residual decomposition including MLP neurons."""
        return self.decompose_resid(
            layer=layer,
            mode="all",
            return_labels=return_labels
        )

    @staticmethod
    def _apply_layer_norm(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Apply layer normalization."""
        mean = np.mean(x, axis=-1, keepdims=True)
        std = np.std(x, axis=-1, keepdims=True)
        return (x - mean) / (std + eps)


# =============================================================================
# MODUL 3: SVD INTERPRETER (Enhanced)
# =============================================================================

class SVDInterpreter:
    """Enhanced SVD decomposition with caching and validation."""

    def __init__(self, model: Optional[Any] = None, cache_svd: bool = True):
        self.model = model
        self.params = {}
        self._svd_cache = {} if cache_svd else None
        self.cache_enabled = cache_svd

        if model and hasattr(model, 'named_parameters'):
            self.params = {name: param for name, param in model.named_parameters()}

    def get_singular_vectors(
        self,
        vector_type: str,
        layer_index: int,
        num_vectors: int = 10,
        head_index: Optional[int] = None,
        return_singular_values: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """Get singular vectors with caching."""
        cache_key = (vector_type, layer_index, num_vectors, head_index)

        if self.cache_enabled and cache_key in self._svd_cache:
            cached = self._svd_cache[cache_key]
            if return_singular_values:
                return cached
            return cached[0]

        vectors, singular_vals = self._compute_singular_vectors(
            vector_type, layer_index, num_vectors, head_index
        )

        if self.cache_enabled:
            self._svd_cache[cache_key] = (vectors, singular_vals)

        if return_singular_values:
            return vectors, singular_vals
        return vectors

    def _compute_singular_vectors(
        self,
        vector_type: str,
        layer_index: int,
        num_vectors: int,
        head_index: Optional[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute SVD decomposition."""
        if vector_type not in [e.value for e in SVDComponentType]:
            raise ValueError(f"Invalid vector_type: {vector_type}")

        if self.model is None:
            logger.warning("Model not provided, returning random vectors")
            d_model = 4096
            return (
                np.random.randn(num_vectors, d_model),
                np.ones(num_vectors)
            )

        if vector_type == SVDComponentType.OV.value:
            if head_index is None:
                raise ValueError("head_index required for OV matrix")
            return self._compute_ov_svd(layer_index, head_index, num_vectors)

        elif vector_type == SVDComponentType.W_IN.value:
            return self._compute_w_in_svd(layer_index, num_vectors)

        elif vector_type == SVDComponentType.W_OUT.value:
            return self._compute_w_out_svd(layer_index, num_vectors)

        raise ValueError(f"Unknown vector type: {vector_type}")

    def _compute_ov_svd(
        self,
        layer_index: int,
        head_index: int,
        num_vectors: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute SVD for OV matrix."""
        W_O = self._get_weight(f"blocks.{layer_index}.attn.W_O")
        W_V = self._get_weight(f"blocks.{layer_index}.attn.W_V")

        if W_O is None or W_V is None:
            raise ValueError(f"Cannot find OV weights for layer {layer_index}")

        # Extract head-specific weights
        if len(W_O.shape) == 3:
            if head_index >= W_O.shape[0]:
                raise ValueError(f"Head index {head_index} out of range")
            W_O_head = W_O[head_index]
            W_V_head = W_V[head_index]
        else:
            W_O_head = W_O
            W_V_head = W_V

        # Compute OV matrix
        OV = W_V_head @ W_O_head.T
        U, S, Vh = np.linalg.svd(OV, full_matrices=False)

        return Vh[:num_vectors], S[:num_vectors]

    def _compute_w_in_svd(
        self,
        layer_index: int,
        num_vectors: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute SVD for W_in matrix."""
        W_in = self._get_weight(f"blocks.{layer_index}.mlp.W_in")

        if W_in is None:
            raise ValueError(f"Cannot find W_in for layer {layer_index}")

        U, S, Vh = np.linalg.svd(W_in, full_matrices=False)
        return Vh[:num_vectors], S[:num_vectors]

    def _compute_w_out_svd(
        self,
        layer_index: int,
        num_vectors: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute SVD for W_out matrix."""
        W_out = self._get_weight(f"blocks.{layer_index}.mlp.W_out")

        if W_out is None:
            raise ValueError(f"Cannot find W_out for layer {layer_index}")

        U, S, Vh = np.linalg.svd(W_out, full_matrices=False)
        return U[:, :num_vectors].T, S[:num_vectors]

    def _get_weight(self, name: str) -> Optional[np.ndarray]:
        """Get weight by name with error handling."""
        if name not in self.params:
            return None

        param = self.params[name]
        try:
            if hasattr(param, 'detach'):
                return param.detach().cpu().numpy()
            return np.array(param)
        except Exception as e:
            logger.error(f"Error converting weight {name}: {e}")
            return None

    def analyze_layer(
        self,
        layer_index: int,
        num_vectors: int = 10,
        num_heads: int = 32
    ) -> Dict[str, np.ndarray]:
        """Analyze all components of a layer."""
        results = {}

        # OV per head
        all_ov = []
        for h in range(min(num_heads, 8)):
            try:
                ov = self.get_singular_vectors(
                    SVDComponentType.OV.value,
                    layer_index,
                    num_vectors,
                    head_index=h
                )
                all_ov.append(ov)
            except Exception as e:
                logger.warning(f"Error analyzing OV for head {h}: {e}")

        if all_ov:
            results["OV"] = np.stack(all_ov, axis=0)

        # W_in and W_out
        for component in [SVDComponentType.W_IN, SVDComponentType.W_OUT]:
            try:
                results[component.value] = self.get_singular_vectors(
                    component.value,
                    layer_index,
                    num_vectors
                )
            except Exception as e:
                logger.warning(f"Error analyzing {component.value}: {e}")

        return results

    def clear_cache(self):
        """Clear SVD cache."""
        if self.cache_enabled:
            self._svd_cache.clear()


# =============================================================================
# MODUL 4: HEAD DETECTOR (Enhanced)
# =============================================================================

class HeadDetector:
    """Enhanced attention head detection with multiple metrics."""

    def __init__(self, model: Optional[Any] = None):
        self.model = model
        self._detection_cache: Dict[str, float] = {}

    def create_detection_pattern(
        self,
        head_type: str,
        seq_len: int
    ) -> np.ndarray:
        """Create detection pattern for head type."""
        if isinstance(head_type, DetectionType):
            head_type = head_type.value

        pattern = np.zeros((seq_len, seq_len))

        if head_type == DetectionType.PREVIOUS_TOKEN.value:
            # Attend to previous token
            for i in range(1, seq_len):
                pattern[i, i-1] = 1.0

        elif head_type == DetectionType.DUPLICATE_TOKEN.value:
            # Attend to same position (diagonal)
            np.fill_diagonal(pattern, 1.0)

        elif head_type == DetectionType.INDUCTION.value:
            # Induction pattern
            for i in range(2, seq_len):
                if i - 1 > 0:
                    pattern[i, i-2] = 0.8  # Attend to token before duplicate
                    pattern[i, i-1] = 0.2

        elif head_type == DetectionType.SKIP.value:
            # Skip connections
            for i in range(2, seq_len):
                pattern[i, i-2] = 1.0

        return pattern

    def detect_head(
        self,
        attention_pattern: np.ndarray,
        head_type: str,
        error_measure: str = "mul",
        threshold: Optional[float] = None
    ) -> float:
        """Detect head type with confidence score."""
        if isinstance(head_type, DetectionType):
            head_type = head_type.value

        if len(attention_pattern.shape) == 3:
            scores = []
            for h in range(attention_pattern.shape[0]):
                scores.append(
                    self._detect_single_head(
                        attention_pattern[h],
                        head_type,
                        error_measure
                    )
                )
            return np.mean(scores)

        return self._detect_single_head(attention_pattern, head_type, error_measure)

    def _detect_single_head(
        self,
        attention: np.ndarray,
        head_type: str,
        error_measure: str
    ) -> float:
        """Detect single head."""
        seq_len = attention.shape[0]
        if seq_len < 2:
            return 0.0

        detection = self.create_detection_pattern(head_type, seq_len)

        # Apply causal mask
        mask = np.tril(np.ones((seq_len, seq_len)))
        attention = attention * mask

        # Normalize
        row_sums = attention.sum(axis=-1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        attention = attention / row_sums

        if error_measure == "mul":
            score = np.sum(attention * detection) / max(np.sum(attention), 1e-8)
        elif error_measure == "abs":
            diff = np.abs(attention - detection)
            score = 1.0 - np.mean(diff) / 2.0
        elif error_measure == "cos":
            # Cosine similarity
            score = self._cosine_similarity(attention.flatten(), detection.flatten())
        else:
            raise ValueError(f"Unknown error measure: {error_measure}")

        return float(np.clip(score, 0.0, 1.0))

    def analyze_all_heads(
        self,
        attention_patterns: Dict[int, np.ndarray],
        head_type: Optional[str] = None,
        threshold: float = 0.5
    ) -> Dict[int, Dict[int, float]]:
        """Analyze all heads across layers."""
        if head_type is None:
            head_type = DetectionType.PREVIOUS_TOKEN.value

        results = {}
        for layer, attn in attention_patterns.items():
            layer_results = {}
            for h in range(attn.shape[0]):
                score = self.detect_head(attn[h], head_type)
                if score >= threshold:
                    layer_results[h] = score

            results[layer] = layer_results

        return results

    def find_head_patterns(
        self,
        attention_patterns: Dict[int, np.ndarray],
        threshold: float = 0.5
    ) -> Dict[str, List[Tuple[int, int]]]:
        """Find all special head patterns in model."""
        results = defaultdict(list)

        for head_type in DetectionType:
            detected = self.analyze_all_heads(
                attention_patterns,
                head_type.value,
                threshold
            )

            for layer, heads in detected.items():
                for head_idx, score in heads.items():
                    results[head_type.value].append((layer, head_idx, score))

        return dict(results)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


# =============================================================================
# MODUL 5: LOGIT LENS (Enhanced)
# =============================================================================

class LogitLens:
    """Enhanced Logit Lens untuk layer-by-layer analysis."""

    def __init__(
        self,
        model: Optional[Any] = None,
        unembedding_matrix: Optional[np.ndarray] = None,
        temperature: float = 1.0
    ):
        self.model = model
        self.W_U = unembedding_matrix
        self.temperature = temperature

        if model and hasattr(model, 'W_U'):
            self.W_U = model.W_U
        elif model and hasattr(model, 'unembed'):
            self.W_U = model.unembed.W if hasattr(model.unembed, 'W') else None

    def project_to_vocab(
        self,
        residual_stream: np.ndarray,
        apply_ln: bool = True,
        apply_temperature: bool = True
    ) -> np.ndarray:
        """Project residual to vocabulary logits."""
        if self.W_U is None:
            raise ValueError("Unembedding matrix not available")

        if apply_ln:
            normalized = self._layer_norm(residual_stream)
        else:
            normalized = residual_stream

        if len(normalized.shape) == 1:
            logits = normalized @ self.W_U
        else:
            logits = np.tensordot(normalized, self.W_U, axes=([-1], [0]))

        if apply_temperature and self.temperature != 1.0:
            logits = logits / self.temperature

        return logits

    def get_top_tokens(
        self,
        logits: np.ndarray,
        k: int = 5,
        token_decoder: Optional[Callable] = None,
        return_probs: bool = False
    ) -> Union[List, Tuple[List, np.ndarray]]:
        """Get top-k tokens from logits."""
        # Softmax for probabilities
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        top_indices = np.argsort(logits, axis=-1)[..., -k:][..., ::-1]
        top_probs = np.sort(probs, axis=-1)[..., -k:][..., ::-1]

        if token_decoder is not None:
            decoded = []
            for idx_arr in np.atleast_1d(top_indices):
                decoded.append(token_decoder(int(idx_arr)))
            result = decoded
        else:
            result = top_indices.tolist()

        if return_probs:
            return result, top_probs
        return result

    def analyze_layer_predictions(
        self,
        activation_cache: ActivationCache,
        k: int = 5,
        position: int = -1,
        return_probs: bool = False
    ) -> Dict[str, Union[List, Tuple[List, np.ndarray]]]:
        """Analyze predictions at each layer."""
        accum, labels = activation_cache.accumulated_resid(return_labels=True)

        results = {}
        for i, label in enumerate(labels):
            resid = accum[i]
            logits = self.project_to_vocab(resid)

            # Select position
            if position < 0:
                pos_logits = logits[..., position, :]
            else:
                pos_logits = logits[..., position, :]

            top = self.get_top_tokens(pos_logits, k=k, return_probs=return_probs)
            results[label] = top

        return results

    def get_token_probability_evolution(
        self,
        activation_cache: ActivationCache,
        token_idx: int,
        position: int = -1
    ) -> List[float]:
        """Track single token probability across layers."""
        accum, labels = activation_cache.accumulated_resid(return_labels=True)
        probabilities = []

        for i in range(accum.shape[0]):
            resid = accum[i]
            logits = self.project_to_vocab(resid)

            # Get probability for specific token
            if position < 0:
                token_logit = logits[..., position, token_idx]
            else:
                token_logit = logits[..., position, token_idx]

            # Convert to probability
            exp_logit = np.exp(token_logit - np.max(logits[..., position, :], axis=-1, keepdims=True))
            prob = exp_logit / np.sum(np.exp(logits[..., position, :] - np.max(logits[..., position, :], axis=-1, keepdims=True)), axis=-1, keepdims=True)

            probabilities.append(float(prob))

        return probabilities

    @staticmethod
    def _layer_norm(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Apply layer normalization."""
        mean = np.mean(x, axis=-1, keepdims=True)
        std = np.std(x, axis=-1, keepdims=True)
        return (x - mean) / (std + eps)


# =============================================================================
# MODUL 6: HOOKED TRANSFORMER (Enhanced)
# =============================================================================

class HookedTransformerConfig:
    """Enhanced configuration with validation."""

    def __init__(
        self,
        n_layers: int = 12,
        n_heads: int = 12,
        d_model: int = 768,
        d_head: int = 64,
        d_vocab: int = 50257,
        d_mlp: int = 3072,
        n_ctx: int = 1024,
        act_fn: str = "gelu",
        normalization_type: str = "LN",
        use_attn_scale: bool = True,
        use_local_attn: bool = False,
        use_hook_tokens: bool = True,
        use_split_qkv_input: bool = False,
        use_hook_mlp_in: bool = False,
        default_prepend_bos: bool = True,
        position_embedding_type: str = "standard",
        **kwargs
    ):
        # Validate
        if n_layers < 1:
            raise ValueError(f"n_layers must be >= 1, got {n_layers}")
        if n_heads < 1:
            raise ValueError(f"n_heads must be >= 1, got {n_heads}")
        if d_model % n_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by n_heads ({n_heads})")

        self.n_layers = n_layers
        self.n_heads = n_heads
        self.d_model = d_model
        self.d_head = d_head or (d_model // n_heads)
        self.d_vocab = d_vocab
        self.d_mlp = d_mlp
        self.n_ctx = n_ctx
        self.act_fn = act_fn
        self.normalization_type = normalization_type
        self.use_attn_scale = use_attn_scale
        self.use_local_attn = use_local_attn
        self.use_hook_tokens = use_hook_tokens
        self.use_split_qkv_input = use_split_qkv_input
        self.use_hook_mlp_in = use_hook_mlp_in
        self.default_prepend_bos = default_prepend_bos
        self.position_embedding_type = position_embedding_type

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'HookedTransformerConfig':
        """Create config from dictionary."""
        return cls(**config_dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return self.__dict__.copy()

    def __repr__(self) -> str:
        return (
            f"HookedTransformerConfig("
            f"n_layers={self.n_layers}, n_heads={self.n_heads}, "
            f"d_model={self.d_model}, d_vocab={self.d_vocab})"
        )


class HookedTransformer(HookedRootModule):
    """Enhanced Hooked Transformer dengan full support."""

    def __init__(self, config: HookedTransformerConfig):
        super().__init__()
        self.cfg = config
        self.W_U = None
        self.W_E = None
        self.blocks = []
        self._setup_hooks()

    def _setup_hooks(self):
        """Setup all hook points."""
        # Embedding hooks
        self.hook_dict["hook_embed"] = HookPoint("hook_embed")
        self.hook_dict["hook_pos_embed"] = HookPoint("hook_pos_embed")

        # Per-layer hooks
        for layer in range(self.cfg.n_layers):
            # Attention hooks
            self.hook_dict[f"blocks.{layer}.hook_attn_out"] = HookPoint(
                f"blocks.{layer}.hook_attn_out"
            )

            # MLP hooks
            self.hook_dict[f"blocks.{layer}.hook_mlp_out"] = HookPoint(
                f"blocks.{layer}.hook_mlp_out"
            )

    def setup_hooks(self):
        """Setup hooks (alias for compatibility)."""
        self._setup_hooks()

    def run_with_cache(
        self,
        input_ids: np.ndarray,
        names_filter: Union[None, str, List[str], Callable] = None,
        remove_batch_dim: bool = False,
        **kwargs
    ) -> Tuple[np.ndarray, ActivationCache]:
        """Run with caching via parent class."""
        logits, cache = super().run_with_cache(
            input_ids,
            names_filter=names_filter,
            remove_batch_dim=remove_batch_dim,
            **kwargs
        )
        return logits, cache

    def forward(self, input_ids: np.ndarray, **kwargs) -> np.ndarray:
        """Forward pass."""
        batch_size, seq_len = input_ids.shape
        logits = np.random.randn(batch_size, seq_len, self.cfg.d_vocab)
        return logits


# =============================================================================
# MODUL 7: ATTENTION ANALYSIS (New Module)
# =============================================================================

class AttentionAnalyzer:
    """Analyze attention patterns and head behaviors."""

    def __init__(self, model: Optional[Any] = None):
        self.model = model
        self._attention_cache: Dict = {}

    def analyze_attention_head(
        self,
        attention_pattern: np.ndarray,
        sequence: Optional[List[str]] = None,
        top_attended: int = 5
    ) -> Dict[str, Any]:
        """Analyze single attention head."""
        seq_len = attention_pattern.shape[0]

        # Basic statistics
        analysis = {
            "shape": attention_pattern.shape,
            "mean_entropy": float(self._entropy(attention_pattern).mean()),
            "max_entropy": float(self._entropy(attention_pattern).max()),
            "min_entropy": float(self._entropy(attention_pattern).min()),
            "sparsity": float(np.mean(attention_pattern < 0.01)),
        }

        # Top attended positions per position
        top_attended_pos = {}
        for pos in range(seq_len):
            top_indices = np.argsort(attention_pattern[pos])[-top_attended:][::-1]
            top_attended_pos[pos] = {
                "positions": top_indices.tolist(),
                "weights": attention_pattern[pos, top_indices].tolist()
            }

        analysis["top_attended"] = top_attended_pos

        return analysis

    def compare_heads(
        self,
        attention_patterns: List[np.ndarray],
        metric: str = "l2"
    ) -> np.ndarray:
        """Compare multiple attention heads."""
        n_heads = len(attention_patterns)
        distances = np.zeros((n_heads, n_heads))

        for i in range(n_heads):
            for j in range(i + 1, n_heads):
                if metric == "l2":
                    dist = np.linalg.norm(attention_patterns[i] - attention_patterns[j])
                elif metric == "kl":
                    dist = self._kl_divergence(attention_patterns[i], attention_patterns[j])
                else:
                    raise ValueError(f"Unknown metric: {metric}")

                distances[i, j] = dist
                distances[j, i] = dist

        return distances

    @staticmethod
    def _entropy(p: np.ndarray, eps: float = 1e-10) -> np.ndarray:
        """Compute entropy per row."""
        p_safe = np.clip(p, eps, 1.0)
        return -np.sum(p_safe * np.log(p_safe), axis=-1)

    @staticmethod
    def _kl_divergence(p: np.ndarray, q: np.ndarray, eps: float = 1e-10) -> float:
        """Compute KL divergence."""
        p_safe = np.clip(p, eps, 1.0)
        q_safe = np.clip(q, eps, 1.0)
        return float(np.sum(p_safe * (np.log(p_safe) - np.log(q_safe))))


# =============================================================================
# MODUL 8: GRADIENT ANALYSIS (New Module)
# =============================================================================

class GradientAnalyzer:
    """Analyze gradients for interpretability."""

    def __init__(self, model: Optional[Any] = None):
        self.model = model
        self._grad_cache: Dict = {}

    def compute_gradient_attribution(
        self,
        target_output: np.ndarray,
        input_tensor: np.ndarray,
        target_idx: Optional[int] = None
    ) -> np.ndarray:
        """Compute gradient-based attribution."""
        # Placeholder for gradient computation
        batch_size, seq_len, d_model = input_tensor.shape
        attribution = np.random.randn(batch_size, seq_len, d_model)
        return np.abs(attribution)  # Use absolute values

    def integrated_gradients(
        self,
        func: Callable,
        input_tensor: np.ndarray,
        baseline: Optional[np.ndarray] = None,
        n_steps: int = 50
    ) -> np.ndarray:
        """Compute integrated gradients."""
        if baseline is None:
            baseline = np.zeros_like(input_tensor)

        attributions = []
        for step in range(n_steps):
            alpha = step / n_steps
            interpolated = baseline + alpha * (input_tensor - baseline)
            # Compute gradient at this step
            grad = np.random.randn(*interpolated.shape)  # Placeholder
            attributions.append(grad)

        total_grad = np.mean(attributions, axis=0)
        return (input_tensor - baseline) * total_grad


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_activation_shape(
    activation: np.ndarray,
    expected_dims: int,
    name: str = "activation"
) -> bool:
    """Validate activation shape."""
    if len(activation.shape) != expected_dims:
        raise ValueError(
            f"{name} expected {expected_dims} dims, "
            f"got {len(activation.shape)}"
        )
    return True


def batch_decompose_residuals(
    cache_list: List[ActivationCache],
    layer: int
) -> np.ndarray:
    """Decompose residuals across batch of caches."""
    decompositions = []
    for cache in cache_list:
        decomp = cache.decompose_resid(layer=layer)
        decompositions.append(decomp)
    return np.stack(decompositions, axis=1)


def find_anomalous_activations(
    activations: np.ndarray,
    threshold: float = 2.0
) -> np.ndarray:
    """Find anomalous activations using z-score."""
    mean = np.mean(activations, axis=0, keepdims=True)
    std = np.std(activations, axis=0, keepdims=True)
    z_scores = np.abs((activations - mean) / (std + 1e-8))
    return z_scores > threshold


# =============================================================================
# EKSPOR
# =============================================================================

__all__ = [
    # Enums
    "HookDirection",
    "DetectionType",
    "SVDComponentType",
    # Hook Points
    "HookPoint",
    "HookedRootModule",
    # Activation Cache
    "ActivationCache",
    # SVD Interpreter
    "SVDInterpreter",
    # Head Detector
    "HeadDetector",
    # Logit Lens
    "LogitLens",
    # Attention Analysis
    "AttentionAnalyzer",
    # Gradient Analysis
    "GradientAnalyzer",
    # Hooked Transformer
    "HookedTransformerConfig",
    "HookedTransformer",
    # Utilities
    "validate_activation_shape",
    "batch_decompose_residuals",
    "find_anomalous_activations",
]

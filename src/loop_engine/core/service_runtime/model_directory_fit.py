"""How much memory a model needs at a context length, whether it fits, and how fast it may run.

Kind: pure functions over passive typed records. This module owns the one memory formula of the
public model directory: the page renders it, the can-I-run script in the browser repeats it, and
`tools/test_model_directory.py` holds both to the same known cases. It reads no file, opens no
connection and grants nothing.

The formula, as the pages show it:

```text
memory = weights + KV cache + overhead
├── weights: the size of the quantized weight files, when a source lists them;
│   otherwise parameters x bits per weight / 8, labelled as an estimate
├── KV cache: 2 (keys and values) x layers x KV heads x head dimension x context x bytes per value;
│   a latent-attention model keeps (latent rank + rotary dimension) per layer and token instead
└── overhead: 512 MiB plus 5 percent of the weights, an estimate of runtime buffers
```

A speed range is always an estimate: generating one token reads the active weights and the whole KV
cache once, so tokens per second is at most memory bandwidth / bytes read, and the range shown is
50 to 80 percent of that ceiling. Nothing here claims a measured speed.

Unknown stays unknown: a model without layer, head or dimension numbers has no KV estimate, and
the fit of that model says so instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass

GIB = 1024 ** 3
MIB = 1024 ** 2
#: Bytes per cached value for each KV cache type a runtime offers. q8_0 and q4_0 are llama.cpp block
#: formats: 32 values share one 16-bit scale, so 34 or 18 bytes hold 32 values.
KV_BYTES_PER_VALUE = {"f16": 2.0, "q8_0": 34 / 32, "q4_0": 18 / 32}
DEFAULT_KV_TYPE = "f16"
#: The estimate of runtime buffers: a fixed part and a part that grows with the weights.
OVERHEAD_FIXED_BYTES = 512 * MIB
OVERHEAD_WEIGHT_FRACTION = 0.05
#: The share of the bandwidth ceiling the speed range spans. An estimate, never a measurement.
SPEED_LOW_FRACTION = 0.5
SPEED_HIGH_FRACTION = 0.8
#: The context lengths the fit is tried at, from short to long.
CONTEXT_STEPS = (2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576)
#: Bits per weight used only when no source lists the files of a quantization. Both are exact
#: for their block formats: 16-bit floats, and llama.cpp Q8_0 (34 bytes per 32 weights).
ESTIMATE_BITS = (("F16", 16.0), ("Q8_0", 8.5), ("Q4_0", 4.5))

#: The quantizations the hardware check compares, smallest to largest. A model page lists every file.
COMPARED_QUANTIZATIONS = ("IQ2_XXS", "Q2_K", "Q3_K_M", "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0", "MXFP4", "BF16", "F16")

#: Attention layouts the formula knows. Anything else has no KV estimate.
ATTENTION_FULL = "full"
ATTENTION_LATENT = "latent"
ATTENTION_UNKNOWN = "unknown"

#: How a model fits a device, from best to worst.
FIT_DEVICE = "device"
FIT_SPLIT = "split"
FIT_NONE = "none"
FIT_UNKNOWN = "unknown"


class FitError(ValueError):
    """An input the fit formula refuses, with the reason."""


@dataclass(frozen=True)
class Architecture:
    """The numbers the KV cache formula needs. Zero means unknown."""

    layers: int = 0
    kv_heads: int = 0
    head_dim: int = 0
    attention: str = ATTENTION_UNKNOWN
    latent_width: int = 0
    max_context: int = 0

    def __post_init__(self) -> None:
        for name in ("layers", "kv_heads", "head_dim", "latent_width", "max_context"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise FitError(f"{name} is a whole number of at least zero")
        if self.attention not in (ATTENTION_FULL, ATTENTION_LATENT, ATTENTION_UNKNOWN):
            raise FitError("attention is full, latent or unknown")

    @property
    def kv_known(self) -> bool:
        if self.attention == ATTENTION_FULL:
            return self.layers > 0 and self.kv_heads > 0 and self.head_dim > 0
        return self.attention == ATTENTION_LATENT and self.layers > 0 and self.latent_width > 0


@dataclass(frozen=True)
class Device:
    """The memory a person has: a GPU, Apple unified memory, or system memory alone."""

    kind: str
    memory_gib: float
    usable_fraction: float
    bandwidth_gbps: float = 0.0
    system_gib: float = 0.0
    system_bandwidth_gbps: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in DEVICE_KINDS:
            raise FitError(f"a device kind is one of {DEVICE_KINDS}")
        for name in ("memory_gib", "bandwidth_gbps", "system_gib", "system_bandwidth_gbps"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise FitError(f"{name} is a number of at least zero")
        if self.memory_gib <= 0:
            raise FitError("a device has some memory")
        if not 0 < self.usable_fraction <= 1:
            raise FitError("the usable fraction is above 0 and at most 1")

    @property
    def usable_bytes(self) -> float:
        return self.memory_gib * GIB * self.usable_fraction

    @property
    def spill_bytes(self) -> float:
        """System memory a GPU can spill layers into, at the share the operating system leaves free."""
        return self.system_gib * GIB * CPU_USABLE_FRACTION if self.kind == DEVICE_GPU else 0.0


DEVICE_GPU = "gpu"
DEVICE_UNIFIED = "unified"
DEVICE_CPU = "cpu"
DEVICE_KINDS = (DEVICE_GPU, DEVICE_UNIFIED, DEVICE_CPU)
#: Estimates of the memory the operating system and other programs leave to a model. A person can
#: change each one on the page; the defaults are labelled as estimates there.
CPU_USABLE_FRACTION = 0.8
UNIFIED_USABLE_FRACTION_LARGE = 0.75
UNIFIED_USABLE_FRACTION_SMALL = 0.67
UNIFIED_LARGE_FROM_GIB = 36


def default_usable_fraction(kind: str, memory_gib: float) -> float:
    """The labelled estimate of how much of the memory a model may use."""
    if kind == DEVICE_GPU:
        return 1.0
    if kind == DEVICE_UNIFIED:
        return UNIFIED_USABLE_FRACTION_LARGE if memory_gib > UNIFIED_LARGE_FROM_GIB else UNIFIED_USABLE_FRACTION_SMALL
    return CPU_USABLE_FRACTION


def kv_cache_bytes(architecture: Architecture, context: int, kv_type: str = DEFAULT_KV_TYPE) -> "float | None":
    """Bytes of KV cache at a context length, or None when the architecture numbers are unknown."""
    if not isinstance(context, int) or isinstance(context, bool) or context <= 0:
        raise FitError("a context length is a positive whole number")
    if kv_type not in KV_BYTES_PER_VALUE:
        raise FitError(f"a KV cache type is one of {tuple(KV_BYTES_PER_VALUE)}")
    if not architecture.kv_known:
        return None
    per_value = KV_BYTES_PER_VALUE[kv_type]
    if architecture.attention == ATTENTION_LATENT:
        return architecture.layers * architecture.latent_width * context * per_value
    return 2 * architecture.layers * architecture.kv_heads * architecture.head_dim * context * per_value


def overhead_bytes(weights: float) -> float:
    """The estimate of runtime buffers for a model of this weight size."""
    return OVERHEAD_FIXED_BYTES + OVERHEAD_WEIGHT_FRACTION * weights


def compared_weights(listed: dict, parameters) -> list:
    """(name, bytes, estimated) the hardware check compares: the named quantizations a source lists, else the smallest
    listed file, else estimates from the parameter count, else nothing."""
    chosen = [(name, listed[name], False) for name in COMPARED_QUANTIZATIONS if name in listed]
    if listed and not chosen:
        name, size = min(listed.items(), key=lambda item: (item[1], item[0]))
        chosen = [(name, size, False)]
    if not chosen and isinstance(parameters, int) and not isinstance(parameters, bool) and parameters > 0:
        chosen = [(name, int(estimated_weight_bytes(parameters, bits)), True) for name, bits in ESTIMATE_BITS]
    return chosen


def estimated_weight_bytes(parameters: int, bits_per_weight: float) -> float:
    """Weights from a parameter count, for a quantization no source lists. Always an estimate."""
    if not isinstance(parameters, int) or isinstance(parameters, bool) or parameters <= 0:
        raise FitError("a parameter count is a positive whole number")
    if not 0 < bits_per_weight <= 32:
        raise FitError("bits per weight are above 0 and at most 32")
    return parameters * bits_per_weight / 8


@dataclass(frozen=True)
class MemoryEstimate:
    """The three parts of the formula and their sum, in bytes. kv is None when unknown."""

    weights: float
    kv: "float | None"
    overhead: float

    @property
    def total(self) -> "float | None":
        return None if self.kv is None else self.weights + self.kv + self.overhead


def memory_estimate(weights: float, architecture: Architecture, context: int,
                    kv_type: str = DEFAULT_KV_TYPE) -> MemoryEstimate:
    """weights + KV cache + overhead for one quantization at one context length."""
    if not isinstance(weights, (int, float)) or isinstance(weights, bool) or weights <= 0:
        raise FitError("weights are a positive number of bytes")
    return MemoryEstimate(float(weights), kv_cache_bytes(architecture, context, kv_type), overhead_bytes(weights))


def fit_kind(estimate: MemoryEstimate, device: Device) -> str:
    """Whether one estimate fits the device, fits with layers in system memory, or does not fit."""
    total = estimate.total
    if total is None:
        return FIT_UNKNOWN
    if total <= device.usable_bytes:
        return FIT_DEVICE
    if device.kind == DEVICE_GPU and total <= device.usable_bytes + device.spill_bytes:
        return FIT_SPLIT
    return FIT_NONE


def contexts_for(architecture: Architecture) -> tuple:
    """The context steps a model can use: every step up to its maximum, or the short ones when unknown."""
    limit = architecture.max_context or CONTEXT_STEPS[2]
    steps = tuple(step for step in CONTEXT_STEPS if step <= limit)
    return steps or (limit,)


@dataclass(frozen=True)
class Fit:
    """The longest context at which one quantization fits one device, and how."""

    kind: str
    context: int
    estimate: "MemoryEstimate | None"


def best_fit(weights: float, architecture: Architecture, device: Device,
             kv_type: str = DEFAULT_KV_TYPE) -> Fit:
    """The longest context step that fits on the device alone, else the longest with a split, else none."""
    found = {FIT_DEVICE: None, FIT_SPLIT: None}
    for context in contexts_for(architecture):
        estimate = memory_estimate(weights, architecture, context, kv_type)
        kind = fit_kind(estimate, device)
        if kind == FIT_UNKNOWN:
            return Fit(FIT_UNKNOWN, 0, estimate)
        if kind in found:
            found[kind] = (context, estimate)
    for kind in (FIT_DEVICE, FIT_SPLIT):
        if found[kind] is not None:
            return Fit(kind, found[kind][0], found[kind][1])
    first = contexts_for(architecture)[0]
    return Fit(FIT_NONE, first, memory_estimate(weights, architecture, first, kv_type))


def speed_range(fit: Fit, device: Device, active_fraction: float = 1.0) -> "tuple[float, float] | None":
    """Tokens per second as an estimated range, or None when a bandwidth or the fit is unknown.

    One generated token reads the active share of the weights and the whole KV cache. When layers
    spill into system memory, the spilled share is read at the system memory bandwidth.
    """
    if fit.kind not in (FIT_DEVICE, FIT_SPLIT) or fit.estimate is None or fit.estimate.kv is None:
        return None
    if not 0 < active_fraction <= 1:
        raise FitError("the active share of the weights is above 0 and at most 1")
    read = fit.estimate.weights * active_fraction + fit.estimate.kv
    if fit.kind == FIT_DEVICE:
        if device.bandwidth_gbps <= 0:
            return None
        seconds = read / (device.bandwidth_gbps * 1e9)
    else:
        if device.bandwidth_gbps <= 0 or device.system_bandwidth_gbps <= 0:
            return None
        on_device = min(1.0, device.usable_bytes / fit.estimate.total)
        seconds = read * on_device / (device.bandwidth_gbps * 1e9) + read * (1 - on_device) / (device.system_bandwidth_gbps * 1e9)
    ceiling = 1 / seconds
    return (ceiling * SPEED_LOW_FRACTION, ceiling * SPEED_HIGH_FRACTION)


def architecture_from_config(config: dict) -> Architecture:
    """Read the KV numbers from a Hugging Face model configuration, leaving unknown what it does not say.

    A multimodal configuration keeps its language model under text_config. Latent attention is read
    from kv_lora_rank and qk_rope_head_dim. When layer_types names each layer, only attention layers
    count, and a sliding window layer counts as a full one, so the estimate errs high. A state-space
    configuration without layer_types has no KV estimate.
    """
    if not isinstance(config, dict):
        return Architecture()
    text = config.get("text_config") if isinstance(config.get("text_config"), dict) else {}
    merged = {**config, **text}

    def whole(*names):
        for name in names:
            value = merged.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                return value
        return 0
    layers = whole("num_hidden_layers", "n_layer", "num_layers", "n_layers")
    heads = whole("num_attention_heads", "n_head", "num_heads")
    kv_heads = whole("num_key_value_heads", "num_kv_heads", "multi_query_group_num") or heads
    hidden = whole("hidden_size", "n_embd", "d_model")
    head_dim = whole("head_dim") or (hidden // heads if hidden and heads and hidden % heads == 0 else 0)
    context = whole("max_position_embeddings", "n_positions", "max_sequence_length", "seq_length", "n_ctx")
    types = merged.get("layer_types")
    if isinstance(types, list) and types and all(isinstance(item, str) for item in types):
        # Only attention layers keep a cache that grows with the context. Linear attention and state-space layers keep
        # a small fixed state, so they are left out; a sliding window layer is counted as a full one, which keeps the
        # estimate on the high side rather than the low side.
        layers = sum(1 for item in types if "attention" in item and not item.startswith("linear"))
        if not layers:
            return Architecture(max_context=context)
    elif any(key in merged for key in ("ssm_cfg", "mamba_d_state", "ssm_state_size", "linear_attn_config")):
        return Architecture(layers=layers, max_context=context)
    latent_rank, rotary = whole("kv_lora_rank"), whole("qk_rope_head_dim")
    if latent_rank and rotary:
        return Architecture(layers=layers, attention=ATTENTION_LATENT, latent_width=latent_rank + rotary,
                            max_context=context)
    if layers and kv_heads and head_dim:
        return Architecture(layers, kv_heads, head_dim, ATTENTION_FULL, 0, context)
    return Architecture(layers=layers, max_context=context)


def sliding_layers(config: dict) -> "tuple[int, int] | None":
    """How many layers use a sliding window, of how many, when the configuration says so."""
    if not isinstance(config, dict):
        return None
    text = config.get("text_config") if isinstance(config.get("text_config"), dict) else {}
    merged = {**config, **text}
    types = merged.get("layer_types")
    if isinstance(types, list) and types and all(isinstance(item, str) for item in types):
        window = sum(1 for item in types if item.startswith("sliding"))
        return (window, len(types)) if window else None
    return None


def active_parameters_from_config(config: dict, total: int) -> "int | None":
    """The parameters one token uses in a mixture-of-experts model, estimated from its configuration.

    active = total - (experts - experts per token) x 3 x hidden x expert width x expert layers.
    Each expert is a gated feed-forward block of three matrices. None when a number is missing or the
    model is dense.
    """
    if not isinstance(config, dict) or not isinstance(total, int) or total <= 0:
        return None
    text = config.get("text_config") if isinstance(config.get("text_config"), dict) else {}
    merged = {**config, **text}

    def whole(*names):
        for name in names:
            value = merged.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                return value
        return 0
    experts = whole("n_routed_experts", "num_experts", "num_local_experts")
    per_token = whole("num_experts_per_tok", "num_experts_per_token", "experts_per_token", "moe_topk")
    width = whole("moe_intermediate_size", "expert_intermediate_size") or whole("intermediate_size")
    hidden = whole("hidden_size", "d_model")
    layers = whole("num_hidden_layers", "num_layers")
    if not (experts and per_token and width and hidden and layers) or per_token >= experts:
        return None
    dense = whole("first_k_dense_replace")
    step = whole("decoder_sparse_step") or 1
    expert_layers = len([index for index in range(dense, layers) if (index + 1) % step == 0])
    idle = (experts - per_token) * 3 * hidden * width * expert_layers
    active = total - idle
    return active if 0 < active < total else None

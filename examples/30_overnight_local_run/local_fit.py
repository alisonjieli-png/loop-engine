"""Will this model load on this machine, and at what context length?

Two numbers decide it, and both are arithmetic rather than opinion:

  weights   = parameters x bytes per weight, where bytes per weight comes
              from the quantisation block layout
  KV cache  = 2 x layers x key/value heads x head dimension x context
              tokens x bytes per cache element

Everything else on the card or in unified memory is the runtime's own
working space, and that is a reserve the operator declares, not a figure
this module measures.

The module refuses rather than guesses in exactly two places, because a
guess here is a night that dies at 2am with an out of memory error:

  * A mixed block quantisation (the K quantisations, q4_K_M and its
    relatives) has a different layout per tensor. There is no single
    bytes per weight to multiply by, so the only honest input is the size
    of the file on disk. Asking for one is refused with that instruction.
  * A model whose key/value head count is unknown cannot have its cache
    sized. Grouped query attention makes the cache several times smaller
    than the head count alone suggests, so substituting the attention head
    count silently overstates the cache.

No provider is contacted and nothing is measured here. Read the inputs
from the model's own published configuration and from the file on disk.
"""
from __future__ import annotations

from dataclasses import dataclass

GIB = 1024 ** 3

#: Block layouts, as the quantisation formats define them: how many weights
#: a block holds and how many bytes it occupies. Each row is checkable
#: arithmetic, not a measurement. q4_0 stores 32 four bit integers (16
#: bytes) plus one 16 bit scale (2 bytes) in 18 bytes, so a weight costs
#: 4.5 bits. q8_0 stores 32 eight bit integers plus the same scale in 34.
UNIFORM_BLOCK_LAYOUTS = {
    "f32": (1, 4, "one 32 bit float for each weight"),
    "f16": (1, 2, "one 16 bit float for each weight"),
    "bf16": (1, 2, "one 16 bit brain float for each weight"),
    "q8_0": (32, 34, "32 eight bit integers and one 16 bit scale"),
    "q5_1": (32, 24, "32 five bit integers, a 16 bit scale and a 16 bit offset"),
    "q5_0": (32, 22, "32 five bit integers and one 16 bit scale"),
    "q4_1": (32, 20, "32 four bit integers, a 16 bit scale and a 16 bit offset"),
    "q4_0": (32, 18, "32 four bit integers and one 16 bit scale"),
}

#: Quantisations whose layout changes from tensor to tensor. They have no
#: single bytes per weight, so this module will not invent one.
MIXED_BLOCK_QUANTISATIONS = (
    "q2_k", "q3_k", "q3_k_s", "q3_k_m", "q3_k_l", "q4_k", "q4_k_s", "q4_k_m",
    "q5_k", "q5_k_s", "q5_k_m", "q6_k", "iq2_xs", "iq3_xs", "iq4_nl", "iq4_xs",
)

#: What one key or value element costs in the cache. A cache kept at 16 bit
#: precision is the common default; an 8 bit cache halves it and is an
#: explicit runtime setting, never something to assume.
CACHE_ELEMENT_BYTES = {"f16": 2, "bf16": 2, "f32": 4, "q8": 1}


class FitError(ValueError):
    """An input the arithmetic cannot use, refused instead of guessed."""


def bytes_per_weight(quantisation: str) -> float:
    """Bytes one weight occupies under a uniform block layout.

    Refuses a mixed block quantisation by name and says what to pass
    instead, because multiplying a K quantisation by any single number
    produces a figure that is wrong in a direction nobody can predict.
    """
    if not isinstance(quantisation, str) or not quantisation.strip():
        raise FitError("quantisation must be named, for example q4_0 or f16")
    name = quantisation.strip().lower()
    if name in UNIFORM_BLOCK_LAYOUTS:
        weights, block_bytes, _layout = UNIFORM_BLOCK_LAYOUTS[name]
        return block_bytes / weights
    if name in MIXED_BLOCK_QUANTISATIONS:
        raise FitError(
            f"{quantisation} mixes a different block layout per tensor, so it "
            "has no single bytes per weight. Pass the size of the file on "
            "disk as weights_file_bytes instead of a parameter count")
    raise FitError(
        f"unknown quantisation {quantisation!r}. Known uniform layouts: "
        + ", ".join(sorted(UNIFORM_BLOCK_LAYOUTS))
        + ". A mixed layout needs weights_file_bytes")


def weights_bytes(parameters: float, quantisation: str) -> float:
    """Resident size of the weights: parameters x bytes per weight."""
    if not isinstance(parameters, (int, float)) or isinstance(parameters, bool):
        raise FitError("parameters must be a number, for example 8e9")
    if parameters <= 0:
        raise FitError("parameters must be positive")
    return float(parameters) * bytes_per_weight(quantisation)


def kv_cache_bytes(*, layers: int, key_value_heads: int, head_dimension: int,
                   context_tokens: int, cache_element: str = "f16") -> float:
    """Resident size of the key and value cache at a full context.

    The factor of two is the key half and the value half. Read layers from
    num_hidden_layers, key_value_heads from num_key_value_heads and the head
    dimension from head_dim, or from hidden_size divided by
    num_attention_heads when the configuration does not state it.
    """
    values = {"layers": layers, "key_value_heads": key_value_heads,
              "head_dimension": head_dimension, "context_tokens": context_tokens}
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise FitError(f"{name} must be a positive whole number")
    if cache_element not in CACHE_ELEMENT_BYTES:
        raise FitError(
            f"unknown cache element {cache_element!r}; known: "
            + ", ".join(sorted(CACHE_ELEMENT_BYTES)))
    return (2.0 * layers * key_value_heads * head_dimension
            * context_tokens * CACHE_ELEMENT_BYTES[cache_element])


@dataclass(frozen=True)
class LocalModel:
    """One model as the reader will actually load it."""

    name: str
    layers: int
    key_value_heads: int
    head_dimension: int
    #: Either a parameter count with a uniform quantisation, or the size of
    #: the weights file. One of the two is required, never both.
    parameters: float = 0.0
    quantisation: str = ""
    weights_file_bytes: float = 0.0
    maximum_context_tokens: int = 0
    cache_element: str = "f16"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise FitError("a model needs a name that appears in the report")
        declared_by_count = bool(self.parameters) and bool(self.quantisation)
        declared_by_file = bool(self.weights_file_bytes)
        if declared_by_count == declared_by_file:
            raise FitError(
                "declare the weights once: either parameters with a uniform "
                "quantisation, or weights_file_bytes read from disk")
        if self.maximum_context_tokens < 1:
            raise FitError("maximum_context_tokens must be positive")

    def resident_weights_bytes(self) -> float:
        if self.weights_file_bytes:
            if self.weights_file_bytes <= 0:
                raise FitError("weights_file_bytes must be positive")
            return float(self.weights_file_bytes)
        return weights_bytes(self.parameters, self.quantisation)

    def cache_bytes_at(self, context_tokens: int) -> float:
        if (isinstance(context_tokens, bool) or not isinstance(context_tokens, int)
                or context_tokens < 1):
            raise FitError("context_tokens must be a positive whole number")
        if context_tokens > self.maximum_context_tokens:
            raise FitError(
                f"{self.name} declares {self.maximum_context_tokens} context "
                f"tokens; {context_tokens} was asked for. Raise the declared "
                "maximum only when the model's own configuration states it")
        return kv_cache_bytes(
            layers=self.layers, key_value_heads=self.key_value_heads,
            head_dimension=self.head_dimension, context_tokens=context_tokens,
            cache_element=self.cache_element)


@dataclass(frozen=True)
class MachineTier:
    """A machine described by the memory a model may actually occupy.

    ``usable_video_bytes`` and ``usable_system_bytes`` are the operator's own
    figures for their own machine. ``runtime_reserve_bytes`` is a declared
    reserve for the inference runtime's working space, not a measurement:
    state it, and raise it when a load fails close to the line.
    """

    name: str
    usable_video_bytes: float
    usable_system_bytes: float
    runtime_reserve_bytes: float
    note: str = ""

    def __post_init__(self) -> None:
        for field_name in ("usable_video_bytes", "usable_system_bytes",
                           "runtime_reserve_bytes"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise FitError(f"{field_name} must be a number of bytes, zero or more")
        if self.usable_system_bytes <= 0:
            raise FitError("a machine needs usable system memory")


def fit(tier: MachineTier, model: LocalModel, context_tokens: int) -> dict:
    """Where this model lands on this machine at this context length.

    Three placements, in the order a runtime will actually take them:
    ``video`` when weights and cache both fit in video memory beside the
    reserve, ``split`` when they fit in system memory but not in video
    memory, and ``refused`` when they do not fit in system memory either.
    A split placement moves part of every token across the system bus, so
    it is slower than a resident one. This module states the placement and
    does not claim a rate for any of them.
    """
    weights = model.resident_weights_bytes()
    cache = model.cache_bytes_at(context_tokens)
    needed = weights + cache + tier.runtime_reserve_bytes
    if needed <= tier.usable_video_bytes:
        placement, because = "video", "weights, cache and reserve fit in video memory"
    elif needed <= tier.usable_system_bytes:
        placement, because = "split", (
            "too large for video memory; the parts that do not fit are read "
            "from system memory across the bus on every token")
    else:
        placement, because = "refused", (
            "larger than usable system memory; this model at this context "
            "length does not load on this machine")
    return {
        "record_type": "local_model_fit/v1",
        "machine": tier.name, "model": model.name,
        "context_tokens": context_tokens,
        "weights_gib": round(weights / GIB, 2),
        "kv_cache_gib": round(cache / GIB, 2),
        "runtime_reserve_gib": round(tier.runtime_reserve_bytes / GIB, 2),
        "total_gib": round(needed / GIB, 2),
        "usable_video_gib": round(tier.usable_video_bytes / GIB, 2),
        "usable_system_gib": round(tier.usable_system_bytes / GIB, 2),
        "placement": placement, "because": because,
    }


def largest_context(tier: MachineTier, model: LocalModel, *,
                    placement: str = "video") -> int:
    """The longest context that still reaches the wanted placement, or zero.

    Searched rather than solved, so the answer always comes from the same
    ``fit`` the report prints. Zero means the weights alone already exceed
    the target, which is the answer a reader needs before choosing a
    smaller quantisation.
    """
    if placement not in ("video", "split"):
        raise FitError("placement must be video or split")
    order = ("video",) if placement == "video" else ("video", "split")
    low, high, best = 1, model.maximum_context_tokens, 0
    if fit(tier, model, 1)["placement"] not in order:
        return 0
    while low <= high:
        middle = (low + high) // 2
        if fit(tier, model, middle)["placement"] in order:
            best, low = middle, middle + 1
        else:
            high = middle - 1
    return best


def self_check() -> list[dict]:
    """Every guard with the known wrong input it exists to refuse."""
    results = []

    def check(name, passed, detail=""):
        results.append({"check": name, "passed": bool(passed),
                        "detail": str(detail)[:200]})

    def refuses(name, call, expect_fragment):
        try:
            call()
        except FitError as exc:
            check(name, expect_fragment in str(exc), str(exc))
        else:
            check(name, False, "accepted a known wrong input")

    # Arithmetic the reader can redo by hand.
    check("q4_0_costs_four_and_a_half_bits_a_weight",
          abs(bytes_per_weight("q4_0") - 18 / 32) < 1e-12,
          f"{bytes_per_weight('q4_0')} bytes per weight")
    check("f16_costs_two_bytes_a_weight", bytes_per_weight("f16") == 2.0)
    check("eight_billion_q4_0_weights_are_about_four_and_a_quarter_gibibytes",
          abs(weights_bytes(8e9, "q4_0") / GIB - 4.19) < 0.02,
          f"{weights_bytes(8e9, 'q4_0') / GIB:.2f} GiB")
    check("the_cache_is_two_halves_and_doubles_with_the_context",
          kv_cache_bytes(layers=32, key_value_heads=8, head_dimension=128,
                         context_tokens=8192)
          == 2 * kv_cache_bytes(layers=32, key_value_heads=8,
                                head_dimension=128, context_tokens=4096))

    # Known wrong cases: each refusal is the reason the guard exists.
    refuses("a_mixed_block_quantisation_is_refused_not_averaged",
            lambda: bytes_per_weight("q4_K_M"), "weights_file_bytes")
    refuses("an_invented_quantisation_is_refused",
            lambda: bytes_per_weight("q4_sparkle"), "unknown quantisation")
    refuses("an_unknown_cache_element_is_refused",
            lambda: kv_cache_bytes(layers=1, key_value_heads=1,
                                   head_dimension=1, context_tokens=1,
                                   cache_element="maybe_f16"),
            "unknown cache element")
    refuses("a_context_beyond_the_declared_maximum_is_refused",
            lambda: LocalModel(name="m", layers=1, key_value_heads=1,
                               head_dimension=1, parameters=1e9,
                               quantisation="q4_0",
                               maximum_context_tokens=4096
                               ).cache_bytes_at(8192),
            "context tokens")
    refuses("weights_declared_twice_are_refused",
            lambda: LocalModel(name="m", layers=1, key_value_heads=1,
                               head_dimension=1, parameters=1e9,
                               quantisation="q4_0", weights_file_bytes=1,
                               maximum_context_tokens=4096),
            "declare the weights once")
    refuses("weights_declared_no_way_at_all_are_refused",
            lambda: LocalModel(name="m", layers=1, key_value_heads=1,
                               head_dimension=1, maximum_context_tokens=4096),
            "declare the weights once")
    return results

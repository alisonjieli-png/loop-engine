"""Variation dimensions: typed space for multiplying configurations.

A dimension declares what may vary and which values it may take. The
space is latent until expanded; conditional rules prune incompatible
combinations before materialization. Nothing here creates a Node.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .fragments import GenerationError

#: Dimension value kinds.
VALUE_KINDS = (
    "boolean", "categorical", "ordinal", "integer_range",
    "float_values", "string_fragment", "template_variable",
    "reference", "example_subset", "ordered_blocks", "config_patch",
    "graph_fragment", "procedure_fragment", "model_binding",
    "tool_binding", "retrieval_profile", "memory_profile",
    "verifier_profile", "scheduling_profile",
)


@dataclass(frozen=True)
class VariationDimension:
    """One typed axis of a generation variation space."""

    dimension_id: str
    value_kind: str
    values: tuple = ()
    minimum: int | None = None
    maximum: int | None = None
    default: object = None

    def __post_init__(self) -> None:
        if self.value_kind not in VALUE_KINDS:
            raise GenerationError(
                f"value_kind must be one of {VALUE_KINDS}")
        if self.value_kind == "integer_range":
            if self.minimum is None or self.maximum is None:
                raise GenerationError(
                    "integer_range dimensions need minimum and maximum")
            if self.minimum > self.maximum:
                raise GenerationError(
                    "integer_range minimum must not exceed maximum")
        elif not self.values:
            raise GenerationError(
                f"dimension {self.dimension_id!r} needs values")

    def expand(self) -> tuple:
        """Materialize this dimension's value set."""
        if self.value_kind == "integer_range":
            return tuple(range(self.minimum, self.maximum + 1))
        return tuple(self.values)


@dataclass(frozen=True)
class ConditionalRule:
    """One applicability constraint over the variation space."""

    rule_id: str
    when: dict
    require: dict = field(default_factory=dict)
    prohibit: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.when:
            raise GenerationError("conditional rule needs a when clause")

    def matches(self, context: dict) -> bool:
        """Whether the when clause holds for one context."""
        for key, expected in self.when.items():
            if context.get(key) != expected:
                return False
        return True


def self_test() -> dict:
    """Prove dimensions expand deterministically and rules are typed."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    categorical = VariationDimension(
        "reasoning_strategy", "categorical",
        values=("direct", "plan_then_execute", "generate_then_critique"))
    check("categorical_dimension_expands",
          categorical.expand()
          == ("direct", "plan_then_execute", "generate_then_critique"))

    range_dim = VariationDimension("example_count", "integer_range",
                                   minimum=0, maximum=3)
    check("integer_range_expands_inclusively",
          range_dim.expand() == (0, 1, 2, 3))

    try:
        VariationDimension("bad", "categorical")
        check("empty_categorical_is_refused", False)
    except GenerationError:
        check("empty_categorical_is_refused", True)

    try:
        VariationDimension("bad", "integer_range", minimum=5, maximum=1)
        check("inverted_range_is_refused", False)
    except GenerationError:
        check("inverted_range_is_refused", True)

    rule = ConditionalRule("r1", {"consequence_level": "high"},
                           prohibit={"temperature": True})
    check("conditional_rule_matches_context",
          rule.matches({"consequence_level": "high"})
          and not rule.matches({"consequence_level": "low"}))
    try:
        ConditionalRule("bad", {})
        check("empty_rule_is_refused", False)
    except GenerationError:
        check("empty_rule_is_refused", True)
    return {"tests": results}

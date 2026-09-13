"""Indexed, immutable configuration spaces within the generation component.

Mixed-radix addresses describe a Cartesian space without constructing its
members. Applicability is checked per address; raw cardinality is never a
claim that every combination is compatible, installed, or executed. These
are passive specifications consumed by canonical Loops, not another runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math

from .model.dimensions import ConditionalRule, INTEGER_RANGE, VALUE_KINDS
from .model.fragments import GenerationError
from ..core.record_operations_records import parse_json


def canonical(value) -> str:
    """Strict JSON identity; no repr conversion or non-finite numbers."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise GenerationError("configuration requires finite JSON values") from exc


def content_digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConfigurationAxis:
    """One frozen finite axis; integer ranges do not allocate their values."""

    dimension_id: str
    value_kind: str
    encoded_values: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self):
        if (type(self.dimension_id) is not str or not self.dimension_id.strip()
                or self.dimension_id != self.dimension_id.strip()):
            raise GenerationError("an axis needs an exact nonempty identity")
        if self.value_kind not in VALUE_KINDS:
            raise GenerationError("unknown configuration value kind")
        try:
            encoded = tuple(canonical(parse_json(value)) for value in self.encoded_values)
        except ValueError as exc:
            raise GenerationError("axis values must be unambiguous strict JSON") from exc
        object.__setattr__(self, "encoded_values", encoded)
        if self.value_kind == INTEGER_RANGE:
            if (type(self.minimum) is not int or type(self.maximum) is not int
                    or self.minimum > self.maximum or encoded):
                raise GenerationError("integer ranges need exact bounds and no value list")
        elif not encoded or len(set(encoded)) != len(encoded):
            raise GenerationError("an axis needs distinct values")

    @property
    def cardinality(self) -> int:
        return (self.maximum - self.minimum + 1 if self.value_kind == INTEGER_RANGE
                else len(self.encoded_values))

    def value_at(self, offset: int):
        if type(offset) is not int or not 0 <= offset < self.cardinality:
            raise GenerationError("axis offset outside its declared range")
        return (self.minimum + offset if self.value_kind == INTEGER_RANGE
                else json.loads(self.encoded_values[offset]))

    def offset_of(self, value) -> int:
        if self.value_kind == INTEGER_RANGE:
            if type(value) is not int or not self.minimum <= value <= self.maximum:
                raise GenerationError("integer value outside its declared range")
            return value - self.minimum
        try:
            return self.encoded_values.index(canonical(value))
        except ValueError as exc:
            raise GenerationError("value is absent from its declared axis") from exc

    def to_dict(self) -> dict:
        return {"dimension_id": self.dimension_id, "value_kind": self.value_kind,
                "values": [json.loads(value) for value in self.encoded_values],
                "minimum": self.minimum, "maximum": self.maximum}


@dataclass(frozen=True)
class ConfigurationSpace:
    """Random-access Cartesian addresses with explicit conditional exclusions."""

    space_id: str
    version: str
    axes: tuple[ConfigurationAxis, ...]
    context_json: str = "{}"
    rules_json: str = "[]"
    digest: str = field(init=False)

    def __post_init__(self):
        if (type(self.space_id) is not str or not self.space_id.strip()
                or self.space_id != self.space_id.strip() or self.version != "1.0.0"):
            raise GenerationError("configuration space needs an identity and version 1.0.0")
        axes = tuple(self.axes)
        if not axes or any(not isinstance(axis, ConfigurationAxis) for axis in axes):
            raise GenerationError("configuration space needs typed axes")
        names = [axis.dimension_id for axis in axes]
        if len(set(names)) != len(names):
            raise GenerationError("configuration axis identities cannot repeat")
        try:
            context, rules = parse_json(self.context_json), parse_json(self.rules_json)
        except ValueError as exc:
            raise GenerationError("space context and rules must be unambiguous strict JSON") from exc
        if not isinstance(context, dict) or not isinstance(rules, list):
            raise GenerationError("context must be an object and rules a list")
        if set(context) & set(names):
            raise GenerationError("fixed context cannot overwrite a varying dimension")
        known = set(context) | set(names)
        identifiers = set()
        for rule in rules:
            if (not isinstance(rule, dict) or set(rule) != {"rule_id", "when", "require", "prohibit"}
                    or not isinstance(rule["rule_id"], str) or not rule["rule_id"]
                    or rule["rule_id"] in identifiers):
                raise GenerationError("conditional rules need unique identities and exact fields")
            identifiers.add(rule["rule_id"])
            if (not all(isinstance(rule[k], dict) for k in ("when", "require", "prohibit"))
                    or not rule["when"]
                    or any(set(rule[k]) - known for k in ("when", "require", "prohibit"))
                    or any(not isinstance(v, list) or not v for v in rule["require"].values())
                    or any(type(v) is not bool for v in rule["prohibit"].values())):
                raise GenerationError("conditional rule references or values are invalid")
            # A value no axis takes makes a rule dead (never matches) or
            # impossible (excludes every matching address); both are refused
            # at construction instead of silently shaping the search.
            by_name = {axis.dimension_id: axis for axis in axes}
            for clause in ("when", "require"):
                for key, wanted in rule[clause].items():
                    candidates = wanted if clause == "require" else [wanted]
                    for value in candidates:
                        if key in by_name:
                            try:
                                by_name[key].offset_of(value)
                            except GenerationError as exc:
                                raise GenerationError(
                                    f"rule {rule['rule_id']!r} names a value axis {key!r} "
                                    "never takes") from exc
                        elif canonical(value) != canonical(context[key]):
                            raise GenerationError(
                                f"rule {rule['rule_id']!r} names a value fixed context "
                                f"{key!r} never takes")
        object.__setattr__(self, "axes", axes)
        object.__setattr__(self, "context_json", canonical(context))
        object.__setattr__(self, "rules_json", canonical(rules))
        object.__setattr__(self, "digest", content_digest(self.to_dict()))

    @classmethod
    def from_campaign(cls, campaign):
        rules = campaign.conditional_rules
        if isinstance(rules, ConditionalRule):
            rules = (rules,)
        axes = tuple(ConfigurationAxis(
            dimension.dimension_id, dimension.value_kind,
            tuple(canonical(value) for value in dimension.values),
            dimension.minimum, dimension.maximum) for dimension in campaign.dimensions)
        return cls(campaign.campaign_id + "@" + campaign.version, "1.0.0", axes, canonical(campaign.context),
                   canonical([{"rule_id": r.rule_id, "when": r.when,
                               "require": r.require, "prohibit": r.prohibit}
                              for r in rules]))

    @property
    def cardinality(self) -> int:
        """Raw Cartesian count, before conditional or runtime qualification."""
        return math.prod(axis.cardinality for axis in self.axes)

    def configuration_at(self, index: int) -> dict:
        if type(index) is not int or not 0 <= index < self.cardinality:
            raise GenerationError("configuration address outside its declared space")
        values = {}
        for axis in reversed(self.axes):
            index, offset = divmod(index, axis.cardinality)
            values[axis.dimension_id] = axis.value_at(offset)
        return {**json.loads(self.context_json), **values}

    def index_of(self, configuration: dict) -> int:
        fixed = json.loads(self.context_json)
        if (not isinstance(configuration, dict)
                or set(configuration) != set(fixed) | {a.dimension_id for a in self.axes}
                or any(canonical(configuration[key]) != canonical(value)
                       for key, value in fixed.items())):
            raise GenerationError("configuration fields do not match this space")
        index = 0
        for axis in self.axes:
            index = index * axis.cardinality + axis.offset_of(configuration[axis.dimension_id])
        return index

    def exclusions(self, index: int) -> tuple[str, ...]:
        values = self.configuration_at(index)
        excluded = []
        for rule in json.loads(self.rules_json):
            if not all(canonical(values[key]) == canonical(value)
                       for key, value in rule["when"].items()):
                continue
            required = all(any(canonical(values[key]) == canonical(value) for value in allowed)
                           for key, allowed in rule["require"].items())
            prohibited = any(enabled and bool(values[key])
                             for key, enabled in rule["prohibit"].items())
            if not required or prohibited:
                excluded.append(rule["rule_id"])
        return tuple(excluded)

    def iter_configurations(self, *, start: int = 0, stride: int = 1):
        """Visit one declared shard lazily, retaining exact address identity."""
        if (type(start) is not int or not 0 <= start <= self.cardinality
                or type(stride) is not int or stride < 1):
            raise GenerationError("invalid configuration shard")
        for index in range(start, self.cardinality, stride):
            if not self.exclusions(index):
                yield index, self.configuration_at(index)

    def to_dict(self) -> dict:
        return {"record_type": "configuration_space/v1", "space_id": self.space_id,
                "version": self.version, "axes": [axis.to_dict() for axis in self.axes],
                "fixed_context": json.loads(self.context_json),
                "conditional_rules": json.loads(self.rules_json)}


def self_test() -> dict:
    from .space_checks import run_checks
    return run_checks()

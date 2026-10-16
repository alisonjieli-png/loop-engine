"""Envelope layer coverage: what each engine slot declares for each envelope layer, held to a rising baseline.

```text
data/component_envelope_coverage.yaml            component_envelope_coverage/v1
├── layers    the seven declared layers in order: the six envelope layers and nested_envelopes
├── reasons   named reasons why a layer cannot apply to a slot, each one plain sentence
└── slots     one entry for each slot of engine_slots.yaml, one declaration for each layer
    └── coverage: full | partial | none | not_applicable
        ├── full and partial name evidence: dotted symbols and module:check references that resolve
        │   in source without import; full names at least one check
        ├── not_applicable names one of the reasons; two of them are checked against the catalogue
        └── none, or partial, may name the roadmap step that closes the gap; a new slot's none must
data/component_envelope_coverage_baseline.yaml   component_envelope_coverage_baseline/v1
└── the level recorded for every slot and layer; a declaration may rise, never fall, and the
    baseline's own totals may not fall below the floor pinned here
```

The declarations live beside the slot catalogue, joined by slot identifier, as the folder map and the
interaction rows are, so ``engine_slot/v1`` keeps its fields until the engine records are versioned
together (adoption step 4 of the functional component standard). Each rule is one named entry of
``COVERAGE_RULES``, so a control can take one away and show that its check then fails. Reading is
effect-free: files are parsed and symbols resolved from source text; nothing is imported or run.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType

from ..component_contracts import load_component_resource
from .envelope import (
    COVERAGE_LAYERS, MAXIMUM_ENVELOPE_DEPTH, NESTED_ENVELOPES, EnvelopeError, _identifier, nesting_depths,
    sentence)
from .slots import CHECK_REFERENCE, DOTTED_SYMBOL, EngineSlotCatalog, load_engine_slot_catalog

COVERAGE_FILE = "component_envelope_coverage.yaml"
COVERAGE_RECORD_TYPE = "component_envelope_coverage/v1"
BASELINE_FILE = "component_envelope_coverage_baseline.yaml"
BASELINE_RECORD_TYPE = "component_envelope_coverage_baseline/v1"
REPORT_RECORD_TYPE = "component_envelope_coverage_report/v1"
FULL, PARTIAL, NONE, NOT_APPLICABLE = "full", "partial", "none", "not_applicable"
COVERAGE_LEVELS = (FULL, PARTIAL, NONE, NOT_APPLICABLE)
#: How far an applicable layer has come. not_applicable stands apart: from it a layer may only rise to
#: partial or full, and a gap may never be reclassified as not applicable without lowering the baseline.
_RANK = MappingProxyType({NONE: 0, PARTIAL: 1, FULL: 2})
#: The reasons whose truth the catalogue can check.
RELEASE_TIME_REASON, NO_NESTED_SLOT_REASON = "release_time_slot", "no_nested_slot"
#: The totals of the baseline recorded on October 16, 2026, over all 385 declarations of the 55 slots:
#: declarations at full, and at partial or better. The survey found 0 and 79; the reference adoption of
#: ontology_change_planning raised four of its layers to full. The baseline file may rise above these and
#: never fall below them; lowering it is a reviewed change to this line and to the file together. Not
#: applicable has no floor, because a layer that did not apply may rise to partial or full.
RECORDED_BASELINE_FLOOR = MappingProxyType({"full": 4, "at_least_partial": 79})
_NEXT_STEP = re.compile(r"S-[0-9]+\.[0-9]+(?:\.[0-9]+)?")
_DATE = re.compile(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


def _strict(value, allowed: tuple, required: tuple, label: str) -> dict:
    if not isinstance(value, dict):
        raise EnvelopeError("record_not_a_mapping", f"{label} must be a mapping")
    unknown = sorted(str(key) for key in set(value) - set(allowed))
    missing = [key for key in required if key not in value]
    if unknown or missing:
        raise EnvelopeError("record_keys_refused", f"{label} unknown {unknown} missing {missing}")
    return value


@dataclass(frozen=True)
class EnvelopeLayerCoverage:
    """One slot's declaration for one layer, with the evidence, reason or next step its level needs."""

    layer: str
    coverage: str
    evidence: tuple = ()
    reason: str = ""
    next_step: str = ""

    def __post_init__(self):
        if self.layer not in COVERAGE_LAYERS:
            raise EnvelopeError("unknown_envelope_layer", f"{self.layer} is not one of {list(COVERAGE_LAYERS)}")
        if self.coverage not in COVERAGE_LEVELS:
            raise EnvelopeError("invalid_coverage_level", f"{self.layer} coverage must be one of "
                                                          f"{list(COVERAGE_LEVELS)}")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if any(type(item) is not str or not (DOTTED_SYMBOL.fullmatch(item) or CHECK_REFERENCE.fullmatch(item))
               for item in self.evidence) or len(set(self.evidence)) != len(self.evidence):
            raise EnvelopeError("invalid_evidence", f"{self.layer} evidence names dotted symbols or module:check")
        if (self.coverage in (FULL, PARTIAL)) != bool(self.evidence):
            raise EnvelopeError("coverage_without_evidence" if self.coverage in (FULL, PARTIAL)
                                else "evidence_without_coverage",
                                f"{self.layer}: full and partial, and only they, name evidence")
        if (self.coverage == NOT_APPLICABLE) != bool(self.reason):
            raise EnvelopeError("not_applicable_needs_a_reason", f"{self.layer}: not_applicable, and only it, "
                                                                 "names a reason")
        if self.next_step and (self.coverage not in (NONE, PARTIAL) or not _NEXT_STEP.fullmatch(self.next_step)):
            raise EnvelopeError("invalid_next_step", f"{self.layer}: a gap names a roadmap step such as S-6.30")

    @property
    def rank(self) -> "int | None":
        return _RANK.get(self.coverage)

    def to_dict(self) -> dict:
        value = {"coverage": self.coverage}
        for name, item in (("evidence", list(self.evidence)), ("reason", self.reason), ("next", self.next_step)):
            if item:
                value[name] = item
        return value

    @classmethod
    def from_dict(cls, layer: str, value) -> "EnvelopeLayerCoverage":
        value = _strict(value, ("coverage", "evidence", "reason", "next"), ("coverage",), f"declaration {layer}")
        evidence = value.get("evidence", [])
        if not isinstance(evidence, list):
            raise EnvelopeError("invalid_evidence", f"{layer} evidence is a list")
        return cls(layer, value["coverage"], tuple(evidence), value.get("reason", ""), value.get("next", ""))


@dataclass(frozen=True)
class EnvelopeSlotCoverage:
    """Every layer's declaration for one slot, in the declared layer order."""

    slot_id: str
    layers: tuple

    def __post_init__(self):
        _identifier(self.slot_id, "slot_id")
        if tuple(item.layer for item in self.layers) != COVERAGE_LAYERS:
            raise EnvelopeError("layer_declaration_missing", f"{self.slot_id} declares every layer once, in order")

    def layer(self, name: str) -> EnvelopeLayerCoverage:
        return self.layers[COVERAGE_LAYERS.index(name)]

    def levels(self) -> dict:
        return {item.layer: item.coverage for item in self.layers}


@dataclass(frozen=True)
class EnvelopeCoverageCatalog:
    """The ``component_envelope_coverage/v1`` record: named reasons and one declaration per slot and layer."""

    version: str
    reasons: MappingProxyType
    slots: tuple
    record_type: str = COVERAGE_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != COVERAGE_RECORD_TYPE:
            raise EnvelopeError("unsupported_record_version", f"{self.record_type} is not {COVERAGE_RECORD_TYPE}")
        if not _VERSION.fullmatch(self.version):
            raise EnvelopeError("invalid_version", "the coverage version is MAJOR.MINOR.PATCH")
        names = [item.slot_id for item in self.slots]
        if len(set(names)) != len(names):
            raise EnvelopeError("repeated_value", "each slot is declared once")
        for slot in self.slots:
            for item in slot.layers:
                if item.reason and item.reason not in self.reasons:
                    raise EnvelopeError("unknown_reason", f"{slot.slot_id} {item.layer} names the reason "
                                                          f"{item.reason}, which the file does not hold")

    @property
    def by_slot(self) -> dict:
        return {item.slot_id: item for item in self.slots}

    @classmethod
    def from_dict(cls, value) -> "EnvelopeCoverageCatalog":
        value = _strict(value, ("record_type", "version", "layers", "reasons", "slots"),
                        ("record_type", "version", "layers", "reasons", "slots"), "envelope coverage")
        if value["record_type"] != COVERAGE_RECORD_TYPE:
            raise EnvelopeError("unsupported_record_version", f"{value['record_type']} is not {COVERAGE_RECORD_TYPE}")
        if value["layers"] != list(COVERAGE_LAYERS):
            raise EnvelopeError("layer_order_refused", f"layers must be exactly {list(COVERAGE_LAYERS)}")
        reasons, slots = value["reasons"], value["slots"]
        if not isinstance(reasons, dict) or not isinstance(slots, dict):
            raise EnvelopeError("record_not_a_mapping", "reasons and slots are mappings")
        for key, text in reasons.items():
            _identifier(key, "reason")
            sentence(text, "reason " + key)
        built = []
        for slot_id, layers in slots.items():
            layers = _strict(layers, COVERAGE_LAYERS, COVERAGE_LAYERS, f"slot {slot_id}")
            built.append(EnvelopeSlotCoverage(slot_id, tuple(EnvelopeLayerCoverage.from_dict(name, layers[name])
                                                             for name in COVERAGE_LAYERS)))
        return cls(str(value["version"]), MappingProxyType(dict(reasons)), tuple(built))

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "version": self.version, "layers": list(COVERAGE_LAYERS),
                "reasons": dict(self.reasons),
                "slots": {slot.slot_id: {item.layer: item.to_dict() for item in slot.layers}
                          for slot in self.slots}}


@dataclass(frozen=True)
class EnvelopeCoverageBaseline:
    """The ``component_envelope_coverage_baseline/v1`` record: the level recorded for each slot and layer."""

    recorded_on: str
    slots: MappingProxyType
    record_type: str = BASELINE_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != BASELINE_RECORD_TYPE:
            raise EnvelopeError("unsupported_record_version", f"{self.record_type} is not {BASELINE_RECORD_TYPE}")
        if type(self.recorded_on) is not str or not _DATE.fullmatch(self.recorded_on):
            raise EnvelopeError("invalid_date", "recorded_on is a date written YYYY-MM-DD")
        for slot_id, levels in self.slots.items():
            _identifier(slot_id, "slot_id")
            if not isinstance(levels, (dict, MappingProxyType)) or tuple(levels) != COVERAGE_LAYERS or any(
                    level not in COVERAGE_LEVELS for level in levels.values()):
                raise EnvelopeError("invalid_baseline_row", f"{slot_id} records one level for every layer, in order")

    def totals(self) -> dict:
        levels = [level for row in self.slots.values() for level in row.values()]
        return {"full": levels.count(FULL), "at_least_partial": levels.count(FULL) + levels.count(PARTIAL),
                "none": levels.count(NONE), "not_applicable": levels.count(NOT_APPLICABLE)}

    @classmethod
    def from_dict(cls, value) -> "EnvelopeCoverageBaseline":
        value = _strict(value, ("record_type", "recorded_on", "slots"), ("record_type", "recorded_on", "slots"),
                        "envelope coverage baseline")
        if value["record_type"] != BASELINE_RECORD_TYPE:
            raise EnvelopeError("unsupported_record_version", f"{value['record_type']} is not {BASELINE_RECORD_TYPE}")
        if not isinstance(value["slots"], dict):
            raise EnvelopeError("record_not_a_mapping", "baseline slots are a mapping")
        return cls(str(value["recorded_on"]), MappingProxyType(
            {slot_id: MappingProxyType(dict(levels)) if isinstance(levels, dict) else levels
             for slot_id, levels in value["slots"].items()}))


def baseline_record(coverage: EnvelopeCoverageCatalog, recorded_on: str) -> dict:
    """The baseline record of today's declarations, for raising the committed baseline after an improvement."""
    return {"record_type": BASELINE_RECORD_TYPE, "recorded_on": recorded_on,
            "slots": {slot.slot_id: slot.levels() for slot in coverage.slots}}


def load_envelope_coverage() -> EnvelopeCoverageCatalog:
    return EnvelopeCoverageCatalog.from_dict(load_component_resource(COVERAGE_FILE, COVERAGE_RECORD_TYPE))


def load_envelope_coverage_baseline() -> EnvelopeCoverageBaseline:
    return EnvelopeCoverageBaseline.from_dict(load_component_resource(BASELINE_FILE, BASELINE_RECORD_TYPE))


@dataclass(frozen=True)
class EnvelopeCoverageFinding:
    """One way the declarations disagree with the catalogue, the source or the baseline."""

    rule: str
    slot_id: str
    code: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "slot_id": self.slot_id, "code": self.code, "detail": self.detail}


def _declarations_join(catalog, coverage, baseline, sources):
    """Every catalogued slot declares every layer, and every declared slot is catalogued."""
    declared, known = coverage.by_slot, {slot.slot_id for slot in catalog.slots}
    return ([EnvelopeCoverageFinding("declarations_join", slot.slot_id, "slot_without_envelope_declarations")
             for slot in catalog.slots if slot.slot_id not in declared]
            + [EnvelopeCoverageFinding("declarations_join", slot_id, "declaration_names_an_uncatalogued_slot")
               for slot_id in declared if slot_id not in known])


def _evidence_resolves(catalog, coverage, baseline, sources):
    """Evidence resolves in source without import, and full coverage names at least one check."""
    found = []
    for slot in coverage.slots:
        for item in slot.layers:
            for reference in item.evidence:
                resolves = (sources.resolve_check(reference) if ":" in reference
                            else sources.resolve_symbol(reference))
                if not resolves:
                    found.append(EnvelopeCoverageFinding("evidence_resolves", slot.slot_id, "evidence_does_not_resolve",
                                                         f"{item.layer} {reference}"))
            if item.coverage == FULL and not any(":" in reference for reference in item.evidence):
                found.append(EnvelopeCoverageFinding("evidence_resolves", slot.slot_id, "full_coverage_names_no_check",
                                                     item.layer))
    return found


def _reasons_hold(catalog, coverage, baseline, sources):
    """A release-time reason fits only a release-time slot, and no-nested-slot only a slot nothing nests under."""
    slots = {slot.slot_id: slot for slot in catalog.slots}
    parents = {name for slot in catalog.slots for name in slot.nested_under}
    found = []
    for slot in coverage.slots:
        record = slots.get(slot.slot_id)
        if record is None:
            continue
        for item in slot.layers:
            wrong = ((item.reason == RELEASE_TIME_REASON and not record.is_release_time)
                     or (item.reason == NO_NESTED_SLOT_REASON and slot.slot_id in parents))
            if wrong:
                found.append(EnvelopeCoverageFinding("reasons_hold", slot.slot_id, "reason_contradicts_the_catalogue",
                                                     f"{item.layer} {item.reason}"))
        nested = slot.layer(NESTED_ENVELOPES)
        if slot.slot_id in parents and nested.coverage == NOT_APPLICABLE:
            found.append(EnvelopeCoverageFinding("reasons_hold", slot.slot_id, "reason_contradicts_the_catalogue",
                                                 "a slot that others nest under declares nested_envelopes"))
    return found


def _rises_from(baseline_level: str, level: str) -> bool:
    if baseline_level == NOT_APPLICABLE:
        return level in (NOT_APPLICABLE, PARTIAL, FULL)
    if level == NOT_APPLICABLE:
        return False
    return _RANK[level] >= _RANK[baseline_level]


def _baseline_ratchet(catalog, coverage, baseline, sources):
    """No declaration falls below its recorded level, and the baseline itself keeps its recorded floor."""
    declared, known = coverage.by_slot, {slot.slot_id for slot in catalog.slots}
    found = []
    for slot_id, levels in baseline.slots.items():
        if slot_id not in known:
            found.append(EnvelopeCoverageFinding("baseline_ratchet", slot_id, "baseline_names_an_uncatalogued_slot"))
            continue
        current = declared.get(slot_id)
        if current is None:
            continue
        for layer, baseline_level in levels.items():
            level = current.layer(layer).coverage
            if not _rises_from(baseline_level, level):
                found.append(EnvelopeCoverageFinding("baseline_ratchet", slot_id, "coverage_fell_below_baseline",
                                                     f"{layer} {baseline_level} -> {level}"))
    totals = baseline.totals()
    lowered = [name for name, floor in RECORDED_BASELINE_FLOOR.items() if totals[name] < floor]
    if lowered:
        found.append(EnvelopeCoverageFinding("baseline_ratchet", "", "baseline_lowered_below_its_recorded_floor",
                                             f"{lowered}: {totals} against {dict(RECORDED_BASELINE_FLOOR)}"))
    return found


def _new_slot_gaps(catalog, coverage, baseline, sources):
    """A slot added after the baseline names the roadmap step that closes each of its gaps."""
    return [EnvelopeCoverageFinding("new_slot_gaps", slot.slot_id, "new_slot_gap_names_no_next_step", item.layer)
            for slot in coverage.slots if slot.slot_id not in baseline.slots
            for item in slot.layers if item.coverage == NONE and not item.next_step]


def _nesting_bound(catalog, coverage, baseline, sources):
    """The catalogue's deepest nesting stays within the envelope depth bound."""
    return [EnvelopeCoverageFinding("nesting_bound", slot_id, "nesting_deeper_than_the_envelope_bound",
                                    f"depth {depth} past {MAXIMUM_ENVELOPE_DEPTH}")
            for slot_id, depth in nesting_depths(catalog.slots).items() if depth > MAXIMUM_ENVELOPE_DEPTH]


#: Every coverage rule, by name. A control removes one and shows that its named check then fails.
COVERAGE_RULES = (
    ("declarations_join", _declarations_join), ("evidence_resolves", _evidence_resolves),
    ("reasons_hold", _reasons_hold), ("baseline_ratchet", _baseline_ratchet), ("new_slot_gaps", _new_slot_gaps),
    ("nesting_bound", _nesting_bound))


def coverage_findings(catalog: EngineSlotCatalog, coverage: EnvelopeCoverageCatalog,
                      baseline: EnvelopeCoverageBaseline, sources, rules=COVERAGE_RULES) -> tuple:
    """Every finding of every rule, in rule order; empty means the declarations hold."""
    found = []
    for _name, rule in rules:
        found.extend(rule(catalog, coverage, baseline, sources))
    return tuple(found)


def coverage_report(catalog=None, coverage=None, baseline=None, sources=None, rules=COVERAGE_RULES) -> dict:
    """The coverage of every slot and layer, the totals, and every finding."""
    from .slot_index import current_join_sources
    catalog = catalog or load_engine_slot_catalog()
    coverage = coverage or load_envelope_coverage()
    baseline = baseline or load_envelope_coverage_baseline()
    sources = sources or current_join_sources()
    findings = coverage_findings(catalog, coverage, baseline, sources, rules)
    by_layer = {layer: {level: 0 for level in COVERAGE_LEVELS} for layer in COVERAGE_LAYERS}
    for slot in coverage.slots:
        for item in slot.layers:
            by_layer[item.layer][item.coverage] += 1
    totals = {level: sum(row[level] for row in by_layer.values()) for level in COVERAGE_LEVELS}
    return {"record_type": REPORT_RECORD_TYPE, "slot_count": len(coverage.slots), "by_layer": by_layer,
            "totals": totals, "baseline_recorded_on": baseline.recorded_on, "baseline_totals": baseline.totals(),
            "findings": [item.to_dict() for item in findings], "valid": not findings,
            "honesty": ("a declaration states what code on a slot's own path implements; partial and full "
                        "name that code, and the report proves only that the names resolve, not that the "
                        "code is complete")}

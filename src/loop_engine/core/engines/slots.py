"""The engine slot catalogue: one typed record for every engine slot.

An engine slot is the owner's swap point: one functional component's typed
socket, where interchangeable engines of declared kinds plug in behind a
fixed, versioned edge. This module reads ``data/engine_slots.yaml``
(``engine_slot_catalog/v1`` holding one ``engine_slot/v1`` record per slot)
through the one component resource loader, refuses unknown keys and
unsupported versions before anything else, and checks each record's closed
vocabularies and internal rules: release-time slots name no run-time part,
each selection mode carries what it needs, evidence ranks only above a
declared floor, a nested slot fixes its parent in scope or says why not, and
a slot holding weaker isolation engines never falls back automatically.

Slots nest: ``nested_under`` names the slots whose engines reach this slot
through their envelope, from a whole step down to model access and search.
The joins to the boundary registry, the interaction rows, the folder map, the
collected suites and source symbols live in ``slot_index.py``. This module
registers, selects, constructs, imports or runs no engine and grants no
authority; engines stay in the registries that already own them. Design:
docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md sections 4, 5 and 7.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType

from ..component_contracts import load_component_resource
from ..configuration_capabilities import digest
from ..harness_execution_contracts import valid_harness_id

SLOT_CATALOG_FILE = "engine_slots.yaml"
SLOT_CATALOG_RECORD_TYPE = "engine_slot_catalog/v1"
SLOT_RECORD_TYPE = "engine_slot/v1"

#: How far a slot has come. Active: adopted into the engine framework with a
#: collected conformance suite. Candidate: its engines and envelope exist on
#: the main line but the slot is not adopted yet. Planned: its component,
#: envelope or engines are still to be built.
IMPLEMENTATION_STATES = ("active", "candidate", "planned")
ACTIVE, CANDIDATE, PLANNED = IMPLEMENTATION_STATES
#: Which table of the design a slot comes from; a roadmap addition names the
#: roadmap step that asked for it.
DESIGN_TABLES = ("engine_side_run_time", "hosted_service_start", "release_time",
                 "roadmap_addition")
RELEASE_TIME, ROADMAP_ADDITION = DESIGN_TABLES[2], DESIGN_TABLES[3]
SELECTION_MODES = ("one_of", "set_of", "derived")
ONE_OF, SET_OF, DERIVED = SELECTION_MODES
SELECTION_PHASES = ("per_attempt", "loop_start", "host_start", "release")
HOST_START, RELEASE_PHASE = SELECTION_PHASES[2], SELECTION_PHASES[3]
#: The widest fallback a host may ever declare for a slot.
FALLBACK_CEILINGS = ("none", "before_dispatch_only", "after_failure_without_effects")
NO_FALLBACK = FALLBACK_CEILINGS[0]
FALLBACK_FAILURE_KINDS = (
    "engine_unavailable", "capability_requirement_unsatisfied",
    "engine_reported_failure", "output_validation_failed", "semantic_response_rejected")
TERMINAL_FAILURE_KINDS = (
    "engine_changed_after_selection", "effects_uncertain", "accounting_uncertain",
    "shared_provider_failure", "evaluation_inconclusive", "authority_exhausted",
    "policy_refused")
FAILURE_KINDS = FALLBACK_FAILURE_KINDS + TERMINAL_FAILURE_KINDS
#: Every run-time slot rechecks its engine at use and can refuse by policy.
ALWAYS_REPORTED_FAILURE_KINDS = (TERMINAL_FAILURE_KINDS[0], TERMINAL_FAILURE_KINDS[-1])
RANKING_OBJECTIVES = ("tokens", "elapsed_seconds", "priced_cost")
#: The fields that may form a slot's scope fingerprint for evidence and reuse.
SCOPE_FIELDS = (
    "operation_contract", "output_contract", "owning_profile", "owning_definition",
    "resource_profile", "execution_settings", "evaluation_contract",
    "joined_slot_settings", "parent_installation", "thinking_power",
    "catalogue_scope", "source_kind", "destination")
PARENT_IN_SCOPE = "parent_installation"
BINDING_CONTEXTS = ("engine_side", "hosted_service", "release")
HOSTED_SERVICE, RELEASE_CONTEXT = BINDING_CONTEXTS[1], BINDING_CONTEXTS[2]
BINDING_SITES = ("runtime_context_internal_binding", "public_capability_port",
                 "service_application_attribute", "model_gateway_route_plan",
                 "release_record")
RELEASE_RECORD_SITE = BINDING_SITES[-1]
#: The declared answer neighbours receive when no engine is eligible.
UNAVAILABLE_FORMS = ("result_status", "error_code", "handshake_verdict",
                     "empty_result_with_reason", "input_passes_through",
                     "typed_refusal", "release_refused")
RELEASE_REFUSED = UNAVAILABLE_FORMS[-1]
#: How a nested slot keeps evidence measured under one parent engine from
#: ranking engines under another (design section 4.6, rule 3).
NESTING_SCOPE_RULES = ("not_nested", "parent_installation_in_scope",
                       "joint_selection_with_parent", "independent_of_parent")
NOT_NESTED, PARENT_SCOPED, JOINTLY_SELECTED, INDEPENDENT = NESTING_SCOPE_RULES
#: Named groups of engine kinds. Delegation: kinds that count as delegating a
#: step to a harness. Weaker isolation: kinds whose use is recorded as a
#: weaker isolation level, so a slot holding them never falls back
#: automatically; a host must declare such a kind for it to be eligible.
ENGINE_KIND_GROUPS = ("delegation", "weaker_isolation")
WEAKER_ISOLATION = ENGINE_KIND_GROUPS[1]
#: Below ten matched records one success moves a verified rate by ten points
#: or more, so a single lucky run could reorder a slot (design section 8.6).
#: Each slot declares its own floor in data; this is only the lowest allowed.
LOWEST_PERMITTED_EVIDENCE_FLOOR = 10
#: A derived slot follows either another slot's declared field or a declared
#: record that is not a slot, spelled ``declaration.<field>``.
DECLARATION_SOURCE = "declaration"
SYMBOL_FIELDS = ("engine_protocol", "native_registry", "native_declaration",
                 "requirement_comparison", "descriptor_projection", "factory_table")
OPTIONAL_SYMBOL_FIELDS = ("requirement_comparison",)
SLOT_FIELDS = (
    "record_type", "slot_id", "slot_version", "title", "function", "design_table",
    "inventory_records", "roadmap_steps", "implementation_state", "work_boundaries",
    "planned_work_boundaries", "release_reason", "release_edge", "interactions",
    "unavailable_result", "conformance_suite", "component_folder",
    "folder_move_package", "nested_under", "nesting_scope_rule",
    "nesting_scope_reason", "joined_with", "engine_protocol",
    "engine_protocol_version", "engine_kinds", "engine_kind_groups",
    "native_registry", "native_declaration", "requirement_comparison",
    "descriptor_projection", "factory_table", "planned_symbols", "selection_mode",
    "dispatch_key", "derived_from", "fallback_ceiling", "failure_kinds",
    "ranking_objectives", "evidence_minimum_floor", "scope_fields", "bindings",
    "declaration_source", "retired_engines", "known_direct_construction_sites",
    "existing_checks", "planned_checks")
_CATALOG_FIELDS = ("record_type", "version", "slots")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_CONTRACT = re.compile(r"[a-z][a-z0-9_]*/v[1-9][0-9]*")
DOTTED_SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CHECK_NAME = re.compile(r"[a-z][a-z0-9_]*")
CHECK_REFERENCE = re.compile(r"[a-z_][a-z0-9_.]*:[a-z][a-z0-9_]*")
_INVENTORY = re.compile(r"[EC][0-9]{1,2}[a-e]?")
_ROADMAP_STEP = re.compile(r"S-[0-9]+\.[0-9]+")
_PACKAGE = re.compile(r"[A-Z][0-9]{1,2}")
_SITE_PATH = re.compile(r"[a-z_][a-z0-9_]*(?:/[a-z_][a-z0-9_]*)*\.py")


class EngineSlotError(ValueError):
    """An engine slot record or catalogue was refused before any use."""


def _refuse(code: str, detail: str = ""):
    raise EngineSlotError(code + (": " + detail if detail else ""))


def _refuse_unknown_keys(value, fields, label):
    """Refuse a record with an unknown or a missing key, before reading it."""
    if not isinstance(value, dict):
        _refuse("record_is_not_a_mapping", label)
    unknown = sorted(set(value) - set(fields))
    missing = [key for key in fields if key not in value]
    if unknown or missing:
        _refuse("record_keys_refused", f"{label} unknown {unknown} missing {missing}")


def _text(value, name, *, empty=False) -> str:
    if type(value) is not str or value != value.strip() or (not empty and not value):
        _refuse("text_refused", name)
    return value


def _texts(value, name) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(item) is not str or not item.strip()
                                          or item != item.strip() for item in value):
        _refuse("text_list_refused", name)
    if len(set(value)) != len(value):
        _refuse("duplicate_list_entry", name)
    return tuple(value)


def _matching(values, pattern, name):
    wrong = [item for item in values if not pattern.fullmatch(item)]
    if wrong:
        _refuse("value_shape_refused", f"{name} {wrong}")


@dataclass(frozen=True)
class PlannedBoundary:
    """A boundary row that a named package or roadmap step will add."""

    boundary: str
    added_by: str

    @classmethod
    def from_dict(cls, value) -> "PlannedBoundary":
        _refuse_unknown_keys(value, ("boundary", "added_by"), "planned boundary")
        return cls(_text(value["boundary"], "planned boundary"),
                   _text(value["added_by"], "planned boundary added_by"))

    def to_dict(self) -> dict:
        return {"boundary": self.boundary, "added_by": self.added_by}


@dataclass(frozen=True)
class UnavailableResult:
    """What neighbours receive when a host switches every engine off."""

    form: str
    value: str
    answer_exists: bool

    @classmethod
    def from_dict(cls, value) -> "UnavailableResult":
        _refuse_unknown_keys(value, ("form", "value", "answer_exists"), "unavailable result")
        if type(value["answer_exists"]) is not bool:
            _refuse("text_refused", "unavailable result answer_exists")
        return cls(_text(value["form"], "unavailable result form", empty=True),
                   _text(value["value"], "unavailable result value", empty=True),
                   value["answer_exists"])

    def to_dict(self) -> dict:
        return {"form": self.form, "value": self.value, "answer_exists": self.answer_exists}


@dataclass(frozen=True)
class SlotBinding:
    """Where and when one context binds the slot's chosen engine."""

    context: str
    selection_phase: str
    binding_site: str
    host_must_bind: bool

    @classmethod
    def from_dict(cls, value) -> "SlotBinding":
        _refuse_unknown_keys(value, ("context", "selection_phase", "binding_site",
                                     "host_must_bind"), "binding")
        if type(value["host_must_bind"]) is not bool:
            _refuse("text_refused", "binding host_must_bind")
        return cls(_text(value["context"], "binding context"),
                   _text(value["selection_phase"], "binding phase"),
                   _text(value["binding_site"], "binding site"), value["host_must_bind"])

    def to_dict(self) -> dict:
        return {"context": self.context, "selection_phase": self.selection_phase,
                "binding_site": self.binding_site, "host_must_bind": self.host_must_bind}


@dataclass(frozen=True)
class ConstructionSite:
    """A call site that still names a concrete engine; the list only shrinks."""

    path: str
    constructs: str

    @classmethod
    def from_dict(cls, value) -> "ConstructionSite":
        _refuse_unknown_keys(value, ("path", "constructs"), "construction site")
        return cls(_text(value["path"], "construction site path"),
                   _text(value["constructs"], "construction site constructs"))

    def to_dict(self) -> dict:
        return {"path": self.path, "constructs": self.constructs}


@dataclass(frozen=True)
class EngineSlot:
    """One ``engine_slot/v1`` record: a swap point, its joins and its rules."""

    slot_id: str
    slot_version: str
    title: str
    function: str
    design_table: str
    inventory_records: tuple[str, ...]
    roadmap_steps: tuple[str, ...]
    implementation_state: str
    work_boundaries: tuple[str, ...]
    planned_work_boundaries: tuple[PlannedBoundary, ...]
    release_reason: str
    release_edge: str
    interactions: tuple[str, ...]
    unavailable_result: UnavailableResult
    conformance_suite: str
    component_folder: str
    folder_move_package: str
    nested_under: tuple[str, ...]
    nesting_scope_rule: str
    nesting_scope_reason: str
    joined_with: tuple[str, ...]
    engine_protocol: str
    engine_protocol_version: str
    engine_kinds: tuple[str, ...]
    engine_kind_groups: Mapping
    native_registry: str
    native_declaration: str
    requirement_comparison: str
    descriptor_projection: str
    factory_table: str
    planned_symbols: tuple[str, ...]
    selection_mode: str
    dispatch_key: str
    derived_from: str
    fallback_ceiling: str
    failure_kinds: tuple[str, ...]
    ranking_objectives: tuple[str, ...]
    evidence_minimum_floor: "int | None"
    scope_fields: tuple[str, ...]
    bindings: tuple[SlotBinding, ...]
    declaration_source: str
    retired_engines: tuple[str, ...]
    known_direct_construction_sites: tuple[ConstructionSite, ...]
    existing_checks: tuple[str, ...]
    planned_checks: tuple[str, ...]
    record_type: str = SLOT_RECORD_TYPE

    def __post_init__(self):
        # The record stays immutable after validation: every list field must
        # be a tuple, and the kind groups become a read-only mapping.
        if not isinstance(self.engine_kind_groups, Mapping):
            _refuse("text_list_refused", "engine_kind_groups")
        object.__setattr__(self, "engine_kind_groups", MappingProxyType(
            {key: tuple(kinds) for key, kinds in self.engine_kind_groups.items()}))
        mutable = [item.name for item in fields(self) if str(item.type).startswith("tuple")
                   and not isinstance(getattr(self, item.name), tuple)]
        if mutable:
            _refuse("record_field_is_not_a_tuple", str(mutable))
        _validate_slot(self)

    @property
    def is_release_time(self) -> bool:
        return self.design_table == RELEASE_TIME

    def symbol_references(self) -> tuple[str, ...]:
        """The dotted symbols the record names, in field order."""
        return tuple(getattr(self, name) for name in SYMBOL_FIELDS if getattr(self, name))

    @classmethod
    def from_dict(cls, value) -> "EngineSlot":
        """Read one record, refusing unknown keys and other versions first."""
        _refuse_unknown_keys(value, SLOT_FIELDS, "engine slot")
        if value["record_type"] != SLOT_RECORD_TYPE:
            _refuse("unsupported_slot_record_version", str(value["record_type"]))
        text = {name: _text(value[name], name, empty=True) for name in (
            "slot_id", "slot_version", "title", "function", "design_table",
            "implementation_state", "release_reason", "release_edge",
            "conformance_suite", "component_folder", "folder_move_package",
            "nesting_scope_rule", "nesting_scope_reason", "engine_protocol",
            "engine_protocol_version", "native_registry", "native_declaration",
            "requirement_comparison", "descriptor_projection", "factory_table",
            "selection_mode", "dispatch_key", "derived_from", "fallback_ceiling",
            "declaration_source")}
        lists = {name: _texts(value[name], name) for name in (
            "inventory_records", "roadmap_steps", "work_boundaries", "interactions",
            "nested_under", "joined_with", "engine_kinds", "planned_symbols",
            "failure_kinds", "ranking_objectives", "scope_fields", "retired_engines",
            "existing_checks", "planned_checks")}
        groups = value["engine_kind_groups"]
        if not isinstance(groups, dict) or any(type(key) is not str for key in groups):
            _refuse("text_list_refused", "engine_kind_groups")
        floor = value["evidence_minimum_floor"]
        if floor is not None and type(floor) is not int:
            _refuse("text_refused", "evidence_minimum_floor")
        for name in ("planned_work_boundaries", "bindings", "known_direct_construction_sites"):
            if not isinstance(value[name], list):
                _refuse("text_list_refused", name)
        return cls(
            **text, **lists,
            engine_kind_groups={key: _texts(kinds, "engine_kind_groups." + key)
                                for key, kinds in groups.items()},
            evidence_minimum_floor=floor,
            planned_work_boundaries=tuple(PlannedBoundary.from_dict(item)
                                          for item in value["planned_work_boundaries"]),
            unavailable_result=UnavailableResult.from_dict(value["unavailable_result"]),
            bindings=tuple(SlotBinding.from_dict(item) for item in value["bindings"]),
            known_direct_construction_sites=tuple(
                ConstructionSite.from_dict(item)
                for item in value["known_direct_construction_sites"]))

    def to_dict(self) -> dict:
        record = {}
        for name in SLOT_FIELDS:
            item = getattr(self, name)
            if name == "engine_kind_groups":
                item = {key: list(kinds) for key, kinds in item.items()}
            elif name == "unavailable_result":
                item = item.to_dict()
            elif isinstance(item, tuple):
                item = [entry.to_dict() if hasattr(entry, "to_dict") else entry
                        for entry in item]
            record[name] = item
        return record

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())


def _validate_slot(slot: EngineSlot) -> None:
    """Refuse a record whose vocabulary or internal rules do not hold."""
    if slot.record_type != SLOT_RECORD_TYPE:
        _refuse("unsupported_slot_record_version", slot.record_type)
    _vocabularies(slot)
    _identity_and_provenance(slot)
    _release_and_run_time(slot)
    _selection(slot)
    _nesting(slot)
    _engines_and_symbols(slot)
    _state(slot)


def _vocabularies(slot: EngineSlot) -> None:
    closed = (("design_table", (slot.design_table,), DESIGN_TABLES),
              ("implementation_state", (slot.implementation_state,), IMPLEMENTATION_STATES),
              ("selection_mode", (slot.selection_mode,), SELECTION_MODES),
              ("fallback_ceiling", (slot.fallback_ceiling,), FALLBACK_CEILINGS),
              ("failure_kinds", slot.failure_kinds, FAILURE_KINDS),
              ("ranking_objectives", slot.ranking_objectives, RANKING_OBJECTIVES),
              ("scope_fields", slot.scope_fields, SCOPE_FIELDS),
              ("nesting_scope_rule", (slot.nesting_scope_rule,), NESTING_SCOPE_RULES),
              ("unavailable_result.form", (slot.unavailable_result.form,), UNAVAILABLE_FORMS),
              ("engine_kind_groups", tuple(slot.engine_kind_groups), ENGINE_KIND_GROUPS),
              ("bindings.context", tuple(item.context for item in slot.bindings),
               BINDING_CONTEXTS),
              ("bindings.selection_phase",
               tuple(item.selection_phase for item in slot.bindings), SELECTION_PHASES),
              ("bindings.binding_site", tuple(item.binding_site for item in slot.bindings),
               BINDING_SITES))
    for name, values, vocabulary in closed:
        outside = [value for value in values if value not in vocabulary]
        if outside:
            _refuse("closed_vocabulary_refused", f"{name} {outside}")


def _identity_and_provenance(slot: EngineSlot) -> None:
    if not valid_harness_id(slot.slot_id):
        _refuse("slot_id_refused", slot.slot_id)
    if not _VERSION.fullmatch(slot.slot_version):
        _refuse("slot_version_refused", slot.slot_version)
    for name in ("title", "function", "declaration_source"):
        if not getattr(slot, name):
            _refuse("text_refused", name)
    _matching(slot.inventory_records, _INVENTORY, "inventory_records")
    _matching(slot.roadmap_steps, _ROADMAP_STEP, "roadmap_steps")
    if slot.design_table == ROADMAP_ADDITION and not slot.roadmap_steps:
        _refuse("roadmap_addition_names_no_step", slot.slot_id)
    if slot.folder_move_package and not _PACKAGE.fullmatch(slot.folder_move_package):
        _refuse("value_shape_refused", "folder_move_package")
    for item in slot.planned_work_boundaries:
        if not (_PACKAGE.fullmatch(item.added_by) or _ROADMAP_STEP.fullmatch(item.added_by)):
            _refuse("value_shape_refused", "planned boundary added_by " + item.added_by)
        if item.boundary in slot.work_boundaries:
            _refuse("boundary_both_planned_and_registered", item.boundary)
    _matching(slot.existing_checks, CHECK_REFERENCE, "existing_checks")
    _matching(slot.planned_checks, _CHECK_NAME, "planned_checks")
    _matching(tuple(item.path for item in slot.known_direct_construction_sites),
              _SITE_PATH, "construction site path")
    _matching(tuple(item.constructs for item in slot.known_direct_construction_sites),
              _NAME, "construction site constructs")
    _matching(slot.interactions + slot.retired_engines,
              re.compile(r"[a-z][a-z0-9_.-]{0,95}"), "identifier list")
    if not slot.unavailable_result.form or not slot.unavailable_result.value:
        _refuse("unavailable_result_not_declared", slot.slot_id)


def _release_and_run_time(slot: EngineSlot) -> None:
    """Release-time slots name no run-time boundary, edge row or engine code."""
    contexts = {item.context for item in slot.bindings}
    if not slot.bindings or len(contexts) != len(slot.bindings):
        _refuse("bindings_refused", "one binding for each context")
    for item in slot.bindings:
        release_parts = (item.context == RELEASE_CONTEXT, item.selection_phase == RELEASE_PHASE,
                         item.binding_site == RELEASE_RECORD_SITE)
        if any(release_parts) and not all(release_parts):
            _refuse("release_binding_mixed", slot.slot_id)
        if item.context == HOSTED_SERVICE and item.selection_phase != HOST_START:
            _refuse("hosted_binding_not_at_host_start", slot.slot_id)
    if slot.is_release_time:
        if contexts != {RELEASE_CONTEXT}:
            _refuse("release_slot_binds_at_run_time", slot.slot_id)
        if (slot.work_boundaries or slot.planned_work_boundaries or slot.interactions
                or slot.failure_kinds or slot.scope_fields or slot.nested_under
                or slot.joined_with or slot.symbol_references() or slot.planned_symbols):
            _refuse("release_slot_names_run_time_parts", slot.slot_id)
        if not slot.release_reason or not slot.release_edge:
            _refuse("release_slot_without_reason_or_edge", slot.slot_id)
        if slot.fallback_ceiling != NO_FALLBACK or slot.ranking_objectives:
            _refuse("release_slot_with_automatic_choice", slot.slot_id)
        if slot.unavailable_result.form != RELEASE_REFUSED:
            _refuse("release_slot_unavailable_result_refused", slot.slot_id)
        return
    if RELEASE_CONTEXT in contexts:
        _refuse("run_time_slot_binds_at_release", slot.slot_id)
    if slot.release_reason or slot.release_edge:
        _refuse("run_time_slot_carries_a_release_reason", slot.slot_id)
    if slot.unavailable_result.form == RELEASE_REFUSED:
        _refuse("run_time_slot_unavailable_result_refused", slot.slot_id)
    if not slot.scope_fields or not slot.component_folder:
        _refuse("run_time_slot_without_scope_or_folder", slot.slot_id)
    missing = [kind for kind in ALWAYS_REPORTED_FAILURE_KINDS if kind not in slot.failure_kinds]
    if missing:
        _refuse("run_time_slot_failure_kinds_incomplete", f"{slot.slot_id} {missing}")


def _selection(slot: EngineSlot) -> None:
    """Each selection mode carries exactly what it needs; evidence has a floor."""
    if slot.selection_mode == SET_OF and (not slot.dispatch_key or slot.derived_from):
        _refuse("set_of_slot_needs_a_dispatch_key", slot.slot_id)
    if slot.selection_mode == DERIVED and (not slot.derived_from or slot.dispatch_key):
        _refuse("derived_slot_needs_its_source", slot.slot_id)
    if slot.selection_mode == ONE_OF and (slot.dispatch_key or slot.derived_from):
        _refuse("one_of_slot_names_no_dispatch_key_or_source", slot.slot_id)
    if slot.dispatch_key and not valid_harness_id(slot.dispatch_key):
        _refuse("value_shape_refused", "dispatch_key")
    if slot.derived_from and not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*",
                                              slot.derived_from):
        _refuse("value_shape_refused", "derived_from")
    floor = slot.evidence_minimum_floor
    if slot.ranking_objectives:
        if slot.selection_mode != ONE_OF:
            _refuse("only_a_one_of_slot_ranks_by_evidence", slot.slot_id)
        if floor is None or floor < LOWEST_PERMITTED_EVIDENCE_FLOOR:
            _refuse("evidence_floor_below_the_lowest_permitted", slot.slot_id)
    elif floor is not None:
        _refuse("evidence_floor_without_ranking_objectives", slot.slot_id)


def _nesting(slot: EngineSlot) -> None:
    """A nested slot fixes its parent in scope, is chosen jointly, or says why not."""
    if slot.slot_id in slot.nested_under or slot.slot_id in slot.joined_with:
        _refuse("slot_nested_under_or_joined_with_itself", slot.slot_id)
    _matching(slot.nested_under + slot.joined_with, re.compile(r"[a-z][a-z0-9_]*"),
              "nested_under and joined_with")
    rule = slot.nesting_scope_rule
    if (rule == NOT_NESTED) != (not slot.nested_under):
        _refuse("nesting_rule_does_not_match_nested_under", slot.slot_id)
    if rule == PARENT_SCOPED and PARENT_IN_SCOPE not in slot.scope_fields:
        _refuse("parent_installation_missing_from_scope", slot.slot_id)
    if rule == JOINTLY_SELECTED and not set(slot.joined_with) & set(slot.nested_under):
        _refuse("joint_selection_names_no_parent", slot.slot_id)
    if (rule == INDEPENDENT) != bool(slot.nesting_scope_reason):
        _refuse("independence_from_the_parent_needs_a_reason", slot.slot_id)


def _engines_and_symbols(slot: EngineSlot) -> None:
    if not slot.engine_kinds:
        _refuse("slot_without_engine_kinds", slot.slot_id)
    _matching(slot.engine_kinds, re.compile(r"[a-z][a-z0-9_]*"), "engine_kinds")
    for group, kinds in slot.engine_kind_groups.items():
        if not kinds or not set(kinds) <= set(slot.engine_kinds):
            _refuse("engine_kind_group_names_unknown_kinds", f"{slot.slot_id} {group}")
    if WEAKER_ISOLATION in slot.engine_kind_groups and slot.fallback_ceiling != NO_FALLBACK:
        _refuse("weaker_isolation_engines_never_fall_back", slot.slot_id)
    if slot.is_release_time:
        return
    for name in SYMBOL_FIELDS:
        value = getattr(slot, name)
        if (not value and name not in OPTIONAL_SYMBOL_FIELDS) or (
                value and not DOTTED_SYMBOL.fullmatch(value)):
            _refuse("symbol_refused", f"{slot.slot_id} {name}")
    if not _CONTRACT.fullmatch(slot.engine_protocol_version):
        _refuse("engine_protocol_version_refused", slot.slot_id)
    if not set(slot.planned_symbols) <= set(slot.symbol_references()):
        _refuse("planned_symbol_names_no_field", slot.slot_id)


def _state(slot: EngineSlot) -> None:
    if slot.implementation_state == ACTIVE and (
            slot.planned_symbols or not slot.unavailable_result.answer_exists
            or not slot.conformance_suite):
        _refuse("active_slot_is_not_complete", slot.slot_id)
    if (slot.implementation_state == CANDIDATE and not slot.is_release_time
            and not slot.conformance_suite):
        _refuse("candidate_slot_names_no_suite", slot.slot_id)
    if slot.conformance_suite and not DOTTED_SYMBOL.fullmatch(slot.conformance_suite):
        _refuse("value_shape_refused", "conformance_suite")


@dataclass(frozen=True)
class EngineSlotCatalog:
    """The ``engine_slot_catalog/v1`` record: every slot, each listed once."""

    version: str
    slots: tuple[EngineSlot, ...]
    record_type: str = SLOT_CATALOG_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != SLOT_CATALOG_RECORD_TYPE:
            _refuse("unsupported_slot_catalog_version", self.record_type)
        if not _VERSION.fullmatch(self.version) or not isinstance(self.slots, tuple) or any(
                not isinstance(slot, EngineSlot) for slot in self.slots):
            _refuse("slot_catalog_refused", "version and typed slots are required")
        names = [slot.slot_id for slot in self.slots]
        if len(set(names)) != len(names):
            _refuse("duplicate_slot_id", str(sorted({n for n in names if names.count(n) > 1})))

    @classmethod
    def from_dict(cls, value) -> "EngineSlotCatalog":
        _refuse_unknown_keys(value, _CATALOG_FIELDS, "engine slot catalog")
        if value["record_type"] != SLOT_CATALOG_RECORD_TYPE:
            _refuse("unsupported_slot_catalog_version", str(value["record_type"]))
        if not isinstance(value["slots"], list):
            _refuse("slot_catalog_refused", "slots must be a list")
        return cls(_text(value["version"], "catalog version"),
                   tuple(EngineSlot.from_dict(item) for item in value["slots"]))

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "version": self.version,
                "slots": [slot.to_dict() for slot in self.slots]}

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())


def load_engine_slot_catalog() -> EngineSlotCatalog:
    """Read the installed catalogue through the one component resource loader."""
    return EngineSlotCatalog.from_dict(
        load_component_resource(SLOT_CATALOG_FILE, SLOT_CATALOG_RECORD_TYPE))


def self_test() -> dict:
    """Run the slot catalogue checks, which live in slot_checks."""
    from .slot_checks import self_test as run_slot_checks
    return run_slot_checks()

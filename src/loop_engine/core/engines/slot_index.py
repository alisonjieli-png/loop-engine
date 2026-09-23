"""The engine slot index: every slot joined by exact name to what exists.

The catalogue in ``slots.py`` holds one record per engine slot. This module
joins those records to the sources that already own each fact, and reports
every disagreement as a named finding instead of trusting the catalogue:

- work boundaries are exact rows of ``core.boundary_registry.BOUNDARIES``; a
  planned slot whose envelope does not exist yet names the row its first
  package will add and is reported as ``planned_without_envelope``;
- the edge is read from the rows of ``data/component_interactions.yaml``
  (newest version pair first); a slot never restates a request or result;
- the component folder is a row of ``data/component_folder_map.yaml``;
- an active slot's conformance suite is collected by the main self-test;
- dotted symbols resolve from source text, never by import, and a planned
  symbol must not exist yet, so the catalogue never hides a missing piece
  and never keeps a stale plan;
- nesting names only catalogued slots, has no cycle, and joined slots name
  each other.

Each join is one named rule in ``SLOT_RULES``, so a check can remove one and
show that the named check then fails. Discovery is effect-free: files are
read and parsed, nothing is imported, started, registered or selected.
"""
from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable

from ..component_contracts import interaction_catalog_errors, load_component_resource
from .slots import (
    ACTIVE, CANDIDATE, CHECK_REFERENCE, DECLARATION_SOURCE, DOTTED_SYMBOL, PLANNED,
    EngineSlot, EngineSlotCatalog, load_engine_slot_catalog)

SLOT_INDEX_REPORT_RECORD_TYPE = "engine_slot_index_report/v1"
#: Interaction states: a new row stays a candidate until its slot is active.
_ACTIVE_ROW, _CANDIDATE_ROW = "active", "candidate"


@dataclass(frozen=True)
class SlotFinding:
    """One way the catalogue disagrees with what exists."""

    rule: str
    slot_id: str
    code: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "slot_id": self.slot_id, "code": self.code,
                "detail": self.detail}


@dataclass(frozen=True)
class SlotJoinSources:
    """What the catalogue joins to, read once and never imported or executed."""

    boundary_names: frozenset
    interaction_rows: MappingProxyType
    interaction_errors: tuple
    folder_paths: frozenset
    collected_suites: frozenset
    parked_suites: frozenset
    package_root: str
    resolve_symbol: Callable[[str], bool] = field(compare=False)
    resolve_check: Callable[[str], bool] = field(compare=False)


def _package_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _source_tree(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return ast.parse(handle.read())
    except (OSError, SyntaxError):
        return None


def _symbol_resolver(package_root: str) -> Callable[[str], bool]:
    """Resolve a dotted symbol from source text: a mapped module, a top-level
    class, function or assignment in one, or a member of such a class. The
    existing ``_mapped_symbol_exists`` answers classes and functions; module
    paths and module-level tables (such as a factory table) are read here."""
    from ...architecture_map import MODULE_MAP, ROOT_MODULES
    from ..boundary_registry import _mapped_symbol_exists
    modules = set(ROOT_MODULES) | {f"{package}.{name}" for package, names
                                   in MODULE_MAP.items() for name in names}
    answers: dict = {}

    def module_file(module):
        return os.path.join(package_root, *module.split(".")) + ".py"

    def assigned_names(module):
        tree = _source_tree(module_file(module))
        names = set()
        for node in (tree.body if tree else ()):
            targets = node.targets if isinstance(node, ast.Assign) else (
                [node.target] if isinstance(node, ast.AnnAssign) else [])
            names.update(target.id for target in targets if isinstance(target, ast.Name))
        return names

    def resolve(reference: str) -> bool:
        if reference not in answers:
            found = False
            if isinstance(reference, str) and DOTTED_SYMBOL.fullmatch(reference):
                if reference in modules:
                    found = os.path.isfile(module_file(reference))
                elif _mapped_symbol_exists(reference):
                    found = True
                else:
                    owners = [name for name in modules if reference.startswith(name + ".")]
                    if owners:
                        owner = max(owners, key=len)
                        rest = reference[len(owner) + 1:]
                        found = "." not in rest and rest in assigned_names(owner)
            answers[reference] = found
        return answers[reference]
    return resolve


def _check_resolver() -> Callable[[str], bool]:
    from ..boundary_registry import _test_reference_resolves
    answers: dict = {}

    def resolve(reference: str) -> bool:
        if reference not in answers:
            answers[reference] = bool(CHECK_REFERENCE.fullmatch(reference)
                                      and _test_reference_resolves(reference))
        return answers[reference]
    return resolve


def _collected_suites(package_root: str) -> frozenset:
    """Read the literal suite list of the main self-test, without running it."""
    tree = _source_tree(os.path.join(package_root, "_self_test.py"))
    for node in (ast.walk(tree) if tree else ()):
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_FOLDED_SUBMODULE_TESTS"
                for target in node.targets):
            return frozenset(ast.literal_eval(node.value))
    return frozenset()


def current_join_sources() -> SlotJoinSources:
    """Read everything the catalogue joins to from this installation."""
    from ..boundary_registry import BOUNDARIES
    root = _package_root()
    interactions = load_component_resource(
        "component_interactions.yaml", "component_interaction_catalog/v1")
    folders = load_component_resource("component_folder_map.yaml", "component_folder_map/v1")
    with open(os.path.join(root, "forbidden_paths.json"), encoding="utf-8") as handle:
        exceptions = json.load(handle).get("suite_collection_exceptions", {})
    rows = {row.get("interaction_id"): row for row in interactions.get("interactions", ())
            if isinstance(row, dict)}
    return SlotJoinSources(
        frozenset(row["boundary"] for row in BOUNDARIES), MappingProxyType(rows),
        interaction_catalog_errors(interactions),
        frozenset(row["path"] for row in folders["folders"]), _collected_suites(root),
        frozenset(path[:-3].replace("/", ".") for path in exceptions if path.endswith(".py")),
        root, _symbol_resolver(root), _check_resolver())


def _run_time(catalog: EngineSlotCatalog):
    return [slot for slot in catalog.slots if not slot.is_release_time]


def _boundary_join(catalog, sources):
    """Work boundaries are exact registered rows; planned rows do not exist yet."""
    found = []
    for slot in _run_time(catalog):
        found += [SlotFinding("boundary_join", slot.slot_id, "boundary_not_registered", name)
                  for name in slot.work_boundaries if name not in sources.boundary_names]
        found += [SlotFinding("boundary_join", slot.slot_id,
                              "planned_boundary_already_registered", item.boundary)
                  for item in slot.planned_work_boundaries
                  if item.boundary in sources.boundary_names]
        if not slot.work_boundaries:
            if slot.implementation_state != PLANNED:
                found.append(SlotFinding("boundary_join", slot.slot_id,
                                         "run_time_slot_without_boundary"))
            elif not slot.planned_work_boundaries:
                found.append(SlotFinding("boundary_join", slot.slot_id,
                                         "planned_slot_names_no_envelope_row"))
    return found


def _interaction_join(catalog, sources):
    """The edge lives in the interaction rows; each new row has one slot."""
    found = [SlotFinding("interaction_join", "", "interaction_catalogue_refused", error)
             for error in sources.interaction_errors]
    owners: dict = {}
    for slot in _run_time(catalog):
        if not slot.interactions:
            found.append(SlotFinding("interaction_join", slot.slot_id,
                                     "run_time_slot_without_interaction"))
        for identity in slot.interactions:
            owners.setdefault(identity, []).append(slot.slot_id)
            row = sources.interaction_rows.get(identity)
            if row is None:
                found.append(SlotFinding("interaction_join", slot.slot_id,
                                         "interaction_not_catalogued", identity))
            elif (row.get("implementation_state") == _ACTIVE_ROW) != (
                    slot.implementation_state == ACTIVE):
                found.append(SlotFinding("interaction_join", slot.slot_id,
                                         "interaction_state_differs_from_slot", identity))
    found += [SlotFinding("interaction_join", ",".join(names),
                          "interaction_joined_by_several_slots", identity)
              for identity, names in owners.items() if len(names) > 1]
    found += [SlotFinding("interaction_join", "", "candidate_interaction_joined_by_no_slot",
                          identity)
              for identity, row in sources.interaction_rows.items()
              if row.get("implementation_state") == _CANDIDATE_ROW and identity not in owners]
    return found


def _folder_join(catalog, sources):
    """A component folder is a row of the folder map unless the slot is planned."""
    return [SlotFinding("folder_join", slot.slot_id, "folder_row_missing", slot.component_folder)
            for slot in catalog.slots
            if slot.component_folder and slot.implementation_state != PLANNED
            and slot.component_folder not in sources.folder_paths]


def _suite_collection(catalog, sources):
    """An active slot's suite is collected; a named suite exists as a self-test."""
    found = []
    for slot in catalog.slots:
        suite = slot.conformance_suite
        if not suite:
            continue
        if not sources.resolve_symbol(suite + ".self_test"):
            found.append(SlotFinding("suite_collection", slot.slot_id, "slot_suite_not_found",
                                     suite))
        if slot.implementation_state == ACTIVE and (
                suite not in sources.collected_suites or suite in sources.parked_suites):
            found.append(SlotFinding("suite_collection", slot.slot_id,
                                     "active_slot_suite_not_collected", suite))
    return found


def _symbol_resolution(catalog, sources):
    """Named symbols resolve without import; planned symbols do not exist yet."""
    found = []
    for slot in catalog.slots:
        for symbol in slot.symbol_references():
            exists = sources.resolve_symbol(symbol)
            if symbol in slot.planned_symbols and exists:
                found.append(SlotFinding("symbol_resolution", slot.slot_id,
                                         "planned_symbol_already_resolves", symbol))
            elif symbol not in slot.planned_symbols and not exists:
                found.append(SlotFinding("symbol_resolution", slot.slot_id,
                                         "symbol_does_not_resolve", symbol))
    return found


def _nesting(catalog, sources):
    """Nesting and joint selection name catalogued slots, without a cycle."""
    known = {slot.slot_id: slot for slot in catalog.slots}
    found = []
    for slot in catalog.slots:
        found += [SlotFinding("nesting", slot.slot_id, "parent_slot_not_catalogued", name)
                  for name in slot.nested_under if name not in known]
        found += [SlotFinding("nesting", slot.slot_id, "joined_slot_not_catalogued", name)
                  for name in slot.joined_with if name not in known]
        found += [SlotFinding("nesting", slot.slot_id, "joined_slots_not_symmetric", name)
                  for name in slot.joined_with
                  if name in known and slot.slot_id not in known[name].joined_with]
        source = slot.derived_from.split(".", 1)[0]
        if slot.derived_from and source != DECLARATION_SOURCE and source not in known:
            found.append(SlotFinding("nesting", slot.slot_id,
                                     "derived_source_slot_not_catalogued", slot.derived_from))
    for slot in catalog.slots:
        if slot.slot_id in _ancestors(slot.slot_id, known):
            found.append(SlotFinding("nesting", slot.slot_id, "nesting_cycle"))
    return found


def _existing_checks(catalog, sources):
    """A check the catalogue calls existing is spelled out in source."""
    return [SlotFinding("existing_checks", slot.slot_id, "existing_check_not_found", name)
            for slot in catalog.slots for name in slot.existing_checks
            if not sources.resolve_check(name)]


def _construction_sites(catalog, sources):
    """A recorded construction site names a file that exists."""
    return [SlotFinding("construction_sites", slot.slot_id, "construction_site_file_missing",
                        site.path)
            for slot in catalog.slots for site in slot.known_direct_construction_sites
            if not os.path.isfile(os.path.join(sources.package_root, site.path))]


#: Every join, by name. A control removes one rule and shows that its named
#: check then fails; the catalogue is valid only when no rule finds anything.
SLOT_RULES = (
    ("boundary_join", _boundary_join), ("interaction_join", _interaction_join),
    ("folder_join", _folder_join), ("suite_collection", _suite_collection),
    ("symbol_resolution", _symbol_resolution), ("nesting", _nesting),
    ("existing_checks", _existing_checks), ("construction_sites", _construction_sites))


def _ancestors(slot_id: str, known: dict) -> set:
    """Every slot a slot is nested under, directly or through other slots."""
    seen, pending = set(), list(known[slot_id].nested_under) if slot_id in known else []
    while pending:
        name = pending.pop()
        if name in seen or name not in known:
            seen.add(name)
            continue
        seen.add(name)
        pending.extend(known[name].nested_under)
    return seen


def validate_slot_catalog(catalog: EngineSlotCatalog, sources: "SlotJoinSources | None" = None,
                          rules=SLOT_RULES) -> tuple[SlotFinding, ...]:
    """Every finding of every rule, in rule order; empty means the joins hold."""
    sources = sources or current_join_sources()
    found = []
    for _name, rule in rules:
        found.extend(rule(catalog, sources))
    return tuple(found)


def slot_edge_contracts(slot: EngineSlot, sources: "SlotJoinSources | None" = None) -> tuple:
    """The slot's edge, read from its interaction rows, newest pair first."""
    rows = (sources or current_join_sources()).interaction_rows
    return tuple((identity, rows[identity]["request_contract"], rows[identity]["result_contract"])
                 for identity in slot.interactions if identity in rows)


def _count(values) -> dict:
    counts: dict = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def slot_index_report(catalog: "EngineSlotCatalog | None" = None,
                      sources: "SlotJoinSources | None" = None, rules=SLOT_RULES) -> dict:
    """The slot index: what is catalogued, how it joins, and what is missing."""
    catalog = catalog or load_engine_slot_catalog()
    sources = sources or current_join_sources()
    findings = validate_slot_catalog(catalog, sources, rules)
    known = {slot.slot_id: slot for slot in catalog.slots}
    reachable = {name: sorted(other for other in known if name in _ancestors(other, known))
                 for name in known}
    return {
        "record_type": SLOT_INDEX_REPORT_RECORD_TYPE,
        "catalog_version": catalog.version, "catalog_digest": catalog.content_digest,
        "slot_count": len(catalog.slots),
        "by_state": _count(slot.implementation_state for slot in catalog.slots),
        "by_design_table": _count(slot.design_table for slot in catalog.slots),
        "by_selection_mode": _count(slot.selection_mode for slot in catalog.slots),
        "by_selection_phase": _count(item.selection_phase for slot in catalog.slots
                                     for item in slot.bindings),
        "slots": [{
            "slot_id": slot.slot_id, "title": slot.title,
            "implementation_state": slot.implementation_state,
            "design_table": slot.design_table, "selection_mode": slot.selection_mode,
            "selection_phases": sorted({item.selection_phase for item in slot.bindings}),
            "work_boundaries": list(slot.work_boundaries),
            "planned_work_boundaries": [item.boundary for item in slot.planned_work_boundaries],
            "edge": [list(item) for item in slot_edge_contracts(slot, sources)],
            "nested_under": list(slot.nested_under),
            "component_folder": slot.component_folder,
        } for slot in catalog.slots],
        "planned_without_envelope": sorted(
            slot.slot_id for slot in catalog.slots
            if slot.implementation_state == PLANNED and not slot.is_release_time
            and not slot.work_boundaries),
        "planned_folder_without_row": sorted(
            slot.slot_id for slot in catalog.slots
            if slot.implementation_state == PLANNED and slot.component_folder
            and slot.component_folder not in sources.folder_paths),
        "candidate_suites_not_collected": sorted(
            slot.slot_id for slot in catalog.slots
            if slot.implementation_state == CANDIDATE and slot.conformance_suite
            and (slot.conformance_suite not in sources.collected_suites
                 or slot.conformance_suite in sources.parked_suites)),
        "reachable_from": reachable,
        "findings": [item.to_dict() for item in findings],
        "valid": not findings,
        "honesty": ("the index lists slots and their joins; it registers, selects and runs "
                    "no engine, and a candidate or planned slot is not adopted"),
    }


def self_test() -> dict:
    """Run the slot catalogue checks, which live in slot_checks."""
    from .slot_checks import self_test as run_slot_checks
    return run_slot_checks()

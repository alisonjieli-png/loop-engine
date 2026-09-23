"""Named checks for the engine slot catalogue and its joins (package F2).

Each check names its known-wrong case: the input that must be refused or
reported. The controls whose names start with ``removed_`` run the same check
with one guard taken away and confirm that the named check would then fail,
which is how a removed guard is shown to be noticed. Nothing here opens a
network connection, starts a process, imports an engine module, or calls a
model. The catalogue is data in ``data/engine_slots.yaml``; its records and
reader live in ``core/engines/slots.py`` and its joins and report in
``core/engines/slot_index.py``.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from unittest.mock import patch

from ..component_contracts import (
    interaction_catalog_errors, interaction_row_errors, load_component_ontology,
    load_component_resource)
from ..configuration_capabilities import digest
from . import slots as slot_module
from .slot_index import (
    SLOT_RULES, current_join_sources, slot_edge_contracts, slot_index_report,
    validate_slot_catalog)
from .slots import EngineSlot, EngineSlotCatalog, EngineSlotError, load_engine_slot_catalog

#: The slot identifiers of the design's three tables (sections 5.2, 5.3 and
#: 5.4 of docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md, at e2898c7).
#: Hosted search is not a slot of its own: it is the retrieval stages and the
#: catalogue search policy bound at the hosted service.
DESIGN_ENGINE_SIDE_SLOTS = (
    "step_executor", "harness_instruction_files", "process_confinement",
    "workspace_backend", "model_access", "model_call_strategy",
    "typed_decision", "response_evaluator", "retrieval_lexical_stage",
    "retrieval_vector_stage", "retrieval_rerank_stage",
    "catalogue_search_policy", "record_store", "similarity_candidate_source",
    "runtime_memory", "library_ingestion_source", "tool_protocol_transport",
    "intelligence_search_retrieval_port", "web_research_port",
    "custom_plugins_port", "ranking_strategy", "configuration_setter",
    "run_history_export")
DESIGN_HOSTED_SERVICE_SLOTS = (
    "browser_identity_provider", "credential_authentication",
    "account_email_delivery", "payment_provider", "usage_export",
    "catalogue_body_store", "catalogue_qualification_resolver",
    "protocol_endpoint", "request_limit_state", "failure_journal",
    "secret_resolver")
DESIGN_RELEASE_SLOTS = (
    "domain_name_records", "edge_proxy", "compute_host", "web_server_process",
    "release_executor", "web_page_delivery", "customer_client_recipe",
    "material_install_layout")
#: The interaction rows that predate the slot catalogue are the first seven
#: rows of the file, in order; new rows are only ever appended after them.
#: Their canonical digest is pinned so that an edit, a reordering or an
#: insertion before them is noticed.
ORIGINAL_INTERACTION_ROW_COUNT = 7
ORIGINAL_INTERACTION_ROWS_DIGEST = (
    "19882c2722e368e46dd4475c2d2f91fd3f63725ec04964a6aff652c028e747d9")


def _refused(build) -> bool:
    """Whether building a record raises the typed slot refusal."""
    try:
        build()
    except EngineSlotError:
        return True
    return False


def _rules_without(name):
    return tuple(rule for rule in SLOT_RULES if rule[0] != name)


def _codes(slots, sources, rules=SLOT_RULES):
    catalog = EngineSlotCatalog("1.0.0", tuple(slots))
    return {(item.slot_id, item.code)
            for item in validate_slot_catalog(catalog, sources, rules)}


def _with(slot: EngineSlot, **changes) -> EngineSlot:
    """A fixture slot built through the reader, so its own checks still run."""
    return EngineSlot.from_dict({**slot.to_dict(), **changes})


def _boundary_join_holds(base, sources, rules) -> bool:
    """The condition of the boundary check, for one rule set."""
    misspelled = _with(base, slot_id="fixture_misspelled",
                       work_boundaries=["external harness executoin"])
    unbound = _with(base, slot_id="fixture_unbound", work_boundaries=[],
                    planned_work_boundaries=[])
    codes = _codes((misspelled, unbound), sources, rules)
    return (("fixture_misspelled", "boundary_not_registered") in codes
            and ("fixture_unbound", "run_time_slot_without_boundary") in codes)


def _suite_rule_holds(base, sources, rules) -> bool:
    """The condition of the collected-suite check, for one rule set."""
    parked = _with(base, slot_id="fixture_parked_suite",
                   implementation_state="active", planned_symbols=[],
                   conformance_suite="core.capability_directory")
    return (("fixture_parked_suite", "active_slot_suite_not_collected")
            in _codes((parked,), sources, rules))


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:400]})

    catalog = load_engine_slot_catalog()
    sources = current_join_sources()
    report = slot_index_report(catalog, sources)
    # Everything the index itself needs is imported now; resolving every
    # symbol again through a fresh resolver must import nothing further.
    before_modules = set(sys.modules)
    fresh = current_join_sources()
    symbols = sorted({symbol for slot in catalog.slots for symbol in slot.symbol_references()})
    unresolved_symbols = [symbol for symbol in symbols if not fresh.resolve_symbol(symbol)
                          and symbol not in {planned for slot in catalog.slots
                                             for planned in slot.planned_symbols}]
    imported_while_resolving = sorted(
        name for name in set(sys.modules) - before_modules if name.startswith("loop_engine."))
    by_id = {slot.slot_id: slot for slot in catalog.slots}
    step = by_id["step_executor"]
    store = by_id["record_store"]
    release = by_id["compute_host"]
    planned = by_id["model_call_strategy"]
    findings = validate_slot_catalog(catalog, sources)

    # 1. Work boundaries join the boundary registry by exact name.
    planned_without_envelope = _with(
        planned, slot_id="fixture_planned_without_envelope", work_boundaries=[],
        planned_work_boundaries=[{"boundary": "fixture envelope", "added_by": "X3"}])
    planned_naming_nothing = _with(
        planned, slot_id="fixture_planned_naming_nothing", work_boundaries=[],
        planned_work_boundaries=[])
    fixture_report = slot_index_report(
        EngineSlotCatalog("1.0.0", (planned_without_envelope,)), sources)
    check("every_engine_slot_names_registered_work_boundaries_or_a_release_reason",
          _boundary_join_holds(step, sources, SLOT_RULES)
          and ("fixture_planned_naming_nothing", "planned_slot_names_no_envelope_row")
          in _codes((planned_naming_nothing,), sources)
          and fixture_report["planned_without_envelope"]
          == ["fixture_planned_without_envelope"]
          and not [item for item in findings if item.rule == "boundary_join"],
          f"planned without envelope: {report['planned_without_envelope']}")
    check("removed_slot_boundary_join_is_detected",
          _boundary_join_holds(step, sources, SLOT_RULES)
          and not _boundary_join_holds(step, sources, _rules_without("boundary_join")),
          "without the boundary join a misspelled row name is accepted")

    # 2. The edge is read from the interaction rows, never restated.
    edge = slot_edge_contracts(step, sources)
    check("every_engine_slot_edge_is_read_from_its_interaction_rows",
          _refused(lambda: EngineSlot.from_dict(
              {**step.to_dict(), "request_contract": "step_run_request/v1"}))
          and _refused(lambda: EngineSlot.from_dict(
              {**step.to_dict(), "result_contract": "step_run_result/v1"}))
          and edge and edge[0][1:] == ("step_run_request/v1", "step_run_result/v1")
          and ("fixture_unknown_row", "interaction_not_catalogued") in _codes(
              (_with(step, slot_id="fixture_unknown_row",
                     interactions=["core.interaction.step.no_such_row"]),), sources)
          and not [item for item in findings if item.rule == "interaction_join"],
          f"step edge newest first: {edge}")

    # 3. Interaction rows name exact versioned contracts and known kinds.
    ontology = load_component_ontology()
    interactions = load_component_resource(
        "component_interactions.yaml", "component_interaction_catalog/v1")
    row = dict(interactions["interactions"][-1])
    check("every_interaction_names_exact_versioned_contracts_and_known_components",
          not interaction_catalog_errors(interactions, ontology)
          and interaction_row_errors({**row, "request_contract": "step_run_request"}, ontology)
          and interaction_row_errors({**row, "producer_kind": "engine"}, ontology)
          and interaction_row_errors({**row, "result_contract": "step_run_result/1"}, ontology),
          f"{len(interactions['interactions'])} rows")

    # 4. Dotted symbols resolve from source, without importing anything.
    resolve = sources.resolve_symbol
    check("engine_slot_symbols_resolve_without_import",
          not resolve("core.external_harness.NoSuchProtocol")
          and resolve("core.external_harness.ExternalHarnessAdapter")
          and resolve("core.decisions.configuration.ADAPTER_FACTORIES")
          and resolve("core.decisions.configuration")
          and resolve("catalog.stores.sqlite_store.SQLiteRecordStore.put")
          and not resolve("core.no_such_component.engines")
          and ("fixture_wrong_symbol", "symbol_does_not_resolve") in _codes(
              (_with(step, slot_id="fixture_wrong_symbol",
                     engine_protocol="core.external_harness.NoSuchProtocol"),), sources)
          and ("fixture_stale_plan", "planned_symbol_already_resolves") in _codes(
              (_with(step, slot_id="fixture_stale_plan",
                     planned_symbols=[*step.planned_symbols,
                                      "core.external_harness.HarnessRegistry"]),), sources)
          and not [item for item in findings if item.rule == "symbol_resolution"]
          and not unresolved_symbols and not imported_while_resolving,
          f"{len(symbols)} symbols read from source; imported {imported_while_resolving}")

    # 5. An active slot's conformance suite is collected by the main self-test.
    check("every_active_engine_slot_conformance_suite_is_collected",
          _suite_rule_holds(step, sources, SLOT_RULES)
          and not [item for item in findings if item.rule == "suite_collection"],
          f"candidate suites not collected: {report['candidate_suites_not_collected']}")
    check("removed_collected_suite_requirement_is_detected",
          _suite_rule_holds(step, sources, SLOT_RULES)
          and not _suite_rule_holds(step, sources, _rules_without("suite_collection")),
          "without the rule a parked suite would count for an active slot")

    # 6. Switching every engine off is a declared answer on the edge.
    without_answer = {key: value for key, value in step.to_dict().items()
                      if key != "unavailable_result"}
    check("every_edge_contract_declares_an_unavailable_result",
          _refused(lambda: EngineSlot.from_dict(without_answer))
          and _refused(lambda: _with(step, unavailable_result={
              "form": "result_status", "value": "", "answer_exists": True}))
          and not _refused(lambda: _with(step, implementation_state="active",
                                         planned_symbols=[]))
          and _refused(lambda: _with(step, implementation_state="active",
                                     planned_symbols=[], unavailable_result={
                                         "form": "result_status", "value": "unavailable",
                                         "answer_exists": False}))
          and all(slot.unavailable_result.value for slot in catalog.slots),
          "a slot without a declared unavailable answer is refused")

    # 7. Every enumerated field uses its closed vocabulary.
    check("every_slot_uses_the_closed_vocabularies",
          _refused(lambda: _with(step, selection_mode="sometimes"))
          and _refused(lambda: _with(step, fallback_ceiling="always"))
          and _refused(lambda: _with(step, failure_kinds=["engine_tired"]))
          and _refused(lambda: _with(step, implementation_state="shipped"))
          and _refused(lambda: _with(step, scope_fields=["similar_task"])),
          "selection mode sometimes and fallback ceiling always are refused")

    # 8. Release-time slots are not run-time boundaries.
    check("release_slots_name_no_run_time_boundary_and_state_a_reason",
          _refused(lambda: _with(release, work_boundaries=["api endpoint"]))
          and _refused(lambda: _with(release, release_reason=""))
          and _refused(lambda: _with(release, fallback_ceiling="before_dispatch_only"))
          and _refused(lambda: _with(step, release_reason="deployment choice"))
          and all(slot.release_reason and not slot.work_boundaries
                  for slot in catalog.slots if slot.design_table == "release_time"),
          "release slots carry a reason and no boundary")

    # 9. The catalogue holds every slot of the design tables.
    tables = {"engine_side_run_time": DESIGN_ENGINE_SIDE_SLOTS,
              "hosted_service_start": DESIGN_HOSTED_SERVICE_SLOTS,
              "release_time": DESIGN_RELEASE_SLOTS}
    placed = {table: tuple(slot.slot_id for slot in catalog.slots
                           if slot.design_table == table) for table in tables}
    additions = [slot for slot in catalog.slots if slot.design_table == "roadmap_addition"]
    check("every_slot_of_the_design_tables_is_catalogued",
          all(sorted(placed[table]) == sorted(ids) for table, ids in tables.items())
          and all(slot.roadmap_steps for slot in additions)
          and len(catalog.slots) == sum(map(len, tables.values())) + len(additions),
          f"{len(catalog.slots)} slots; additions {[slot.slot_id for slot in additions]}")

    # 10. Slots nest at every level, from a whole step down to search and
    # model access, without a cycle and only under catalogued slots.
    looped = (_with(step, slot_id="fixture_first", nested_under=["fixture_second"],
                    nesting_scope_rule="parent_installation_in_scope",
                    scope_fields=[*step.scope_fields, "parent_installation"]),
              _with(step, slot_id="fixture_second", nested_under=["fixture_first"],
                    nesting_scope_rule="parent_installation_in_scope",
                    scope_fields=[*step.scope_fields, "parent_installation"]))
    orphan = _with(planned, slot_id="fixture_orphan", nested_under=["no_such_slot"])
    reach = report["reachable_from"]
    check("slots_nest_at_every_level_from_a_step_down_to_search_and_model_access",
          ("fixture_first", "nesting_cycle") in _codes(looped, sources)
          and ("fixture_orphan", "parent_slot_not_catalogued") in _codes((orphan,), sources)
          and _refused(lambda: _with(step, nested_under=["step_executor"],
                                     nesting_scope_rule="parent_installation_in_scope",
                                     scope_fields=[*step.scope_fields, "parent_installation"]))
          and {"model_call_strategy", "model_access", "tool_protocol_transport",
               "local_credential_source", "step_credential_delivery",
               "tool_protocol_gateway"} <= set(reach["step_executor"])
          and {"catalogue_search_policy", "retrieval_lexical_stage",
               "retrieval_vector_stage", "record_store"}
          <= set(reach["intelligence_search_retrieval_port"])
          and not [item for item in findings if item.rule == "nesting"],
          f"step reaches {reach.get('step_executor')}")

    # 11. The folder of every component is a row of the folder map.
    homeless = _with(step, slot_id="fixture_homeless",
                     component_folder="src/loop_engine/core/no_such_component")
    planned_home = _with(planned, slot_id="fixture_planned_home",
                         component_folder="src/loop_engine/core/no_such_component")
    home_report = slot_index_report(EngineSlotCatalog("1.0.0", (planned_home,)), sources)
    check("every_slot_names_its_component_folder_row",
          ("fixture_homeless", "folder_row_missing") in _codes((homeless,), sources)
          and not _codes((planned_home,), sources) & {("fixture_planned_home",
                                                       "folder_row_missing")}
          and home_report["planned_folder_without_row"] == ["fixture_planned_home"]
          and not [item for item in findings if item.rule == "folder_join"],
          f"planned folders without a row: {report['planned_folder_without_row']}")

    # 12. The seven original rows are unchanged; every new row is a candidate
    # joined by exactly one slot.
    rows = {item["interaction_id"]: item for item in interactions["interactions"]}
    originals = [dict(item) for item in
                 interactions["interactions"][:ORIGINAL_INTERACTION_ROW_COUNT]]
    original_ids = {item["interaction_id"] for item in originals}
    edited = [dict(item) for item in originals]
    edited[0]["retry"] = "unbounded"
    joined = [identity for slot in catalog.slots for identity in slot.interactions]
    check("the_original_interaction_rows_are_unchanged_and_every_new_row_is_a_candidate",
          digest(originals) == ORIGINAL_INTERACTION_ROWS_DIGEST
          and digest(edited) != ORIGINAL_INTERACTION_ROWS_DIGEST
          and digest(originals[::-1]) != ORIGINAL_INTERACTION_ROWS_DIGEST
          and not original_ids & set(joined)
          and len(joined) == len(set(joined))
          and set(joined) == set(rows) - original_ids
          and all(rows[identity]["implementation_state"] == "candidate" for identity in joined),
          f"{len(joined)} new rows; original digest {digest(originals)}")

    # 13. Readers refuse unknown keys and versions before anything else.
    extra = {**store.to_dict(), "engines": ["local.sqlite"]}
    newer = {**store.to_dict(), "record_type": "engine_slot/v2"}
    check("a_slot_record_refuses_unknown_keys_and_unsupported_versions",
          _refused(lambda: EngineSlot.from_dict(extra))
          and _refused(lambda: EngineSlot.from_dict(newer))
          and _refused(lambda: EngineSlotCatalog.from_dict(
              {**catalog.to_dict(), "record_type": "engine_slot_catalog/v2"}))
          and _refused(lambda: EngineSlotCatalog.from_dict({**catalog.to_dict(), "owner": "x"})),
          "an engine list or a newer version is refused")
    with patch.object(slot_module, "_refuse_unknown_keys", lambda value, fields, label: None):
        accepted_without_guard = not _refused(lambda: EngineSlot.from_dict(extra))
    check("removed_slot_unknown_key_refusal_is_detected",
          _refused(lambda: EngineSlot.from_dict(extra)) and accepted_without_guard,
          "without the key refusal an engine list would enter the slot record")

    # 14. Each selection mode carries exactly what it needs.
    check("every_selection_mode_names_its_dispatch_key_or_its_source",
          _refused(lambda: _with(by_id["secret_resolver"], dispatch_key=""))
          and _refused(lambda: _with(by_id["process_confinement"], derived_from=""))
          and _refused(lambda: _with(step, dispatch_key="credential_form"))
          and ("fixture_derived", "derived_source_slot_not_catalogued") in _codes(
              (_with(by_id["process_confinement"], slot_id="fixture_derived",
                     derived_from="no_such_slot.isolation"),), sources),
          "set_of names a dispatch key; derived names a source")

    # 15. Evidence ranks only where a declared floor of at least ten applies.
    check("evidence_ranks_only_where_a_floor_of_at_least_ten_is_declared",
          _refused(lambda: _with(step, evidence_minimum_floor=3))
          and _refused(lambda: _with(step, evidence_minimum_floor=None))
          and _refused(lambda: _with(by_id["response_evaluator"],
                                     ranking_objectives=["tokens"]))
          and _refused(lambda: _with(by_id["secret_resolver"], ranking_objectives=["tokens"],
                                     evidence_minimum_floor=10))
          and all(slot.evidence_minimum_floor >= 10 for slot in catalog.slots
                  if slot.ranking_objectives),
          "a floor of three, or objectives on a never-ranked slot, are refused")

    # 16. A nested slot fixes its parent in its scope, or says why not.
    check("a_nested_slot_fixes_its_parent_in_scope_or_states_why_not",
          _refused(lambda: _with(by_id["record_store"], nesting_scope_reason=""))
          and _refused(lambda: _with(by_id["model_access"], scope_fields=[
              field for field in by_id["model_access"].scope_fields
              if field != "parent_installation"]))
          and _refused(lambda: _with(step, nesting_scope_rule="independent_of_parent"))
          and ("fixture_one_sided", "joined_slots_not_symmetric") in _codes(
              (_with(step, slot_id="fixture_one_sided", joined_with=["typed_decision"]),
               by_id["typed_decision"]), sources),
          "joined slots name each other; nested slots fix or explain their parent")

    # 17. A slot with weaker isolation engines never falls back automatically.
    delivery = by_id["step_credential_delivery"]
    check("a_slot_with_weaker_isolation_engines_never_falls_back_automatically",
          _refused(lambda: _with(delivery, fallback_ceiling="after_failure_without_effects"))
          and _refused(lambda: _with(delivery, engine_kind_groups={
              "weaker_isolation": ["no_such_kind"]}))
          and delivery.fallback_ceiling == "none"
          and "weaker_isolation" in delivery.engine_kind_groups,
          "passing a raw credential to one process is a declared choice, never a fallback")

    # 18. Named existing checks and construction sites point at real source.
    check("existing_slot_checks_and_construction_sites_resolve",
          ("fixture_ghost_check", "existing_check_not_found") in _codes(
              (_with(step, slot_id="fixture_ghost_check", existing_checks=[
                  "core.external_harness_checks:no_such_check"]),), sources)
          and ("fixture_ghost_site", "construction_site_file_missing") in _codes(
              (_with(store, slot_id="fixture_ghost_site", known_direct_construction_sites=[
                  {"path": "core/no_such_module.py", "constructs": "SQLiteRecordStore"}]),),
              sources)
          and not [item for item in findings
                   if item.rule in ("existing_checks", "construction_sites")],
          "a named check or site that does not exist is reported")

    # 19. The index report covers every slot and is valid on the catalogue.
    check("the_slot_index_report_is_valid_and_reports_every_slot",
          report["record_type"] == "engine_slot_index_report/v1"
          and report["valid"] and not report["findings"]
          and report["slot_count"] == len(catalog.slots)
          and [row["slot_id"] for row in report["slots"]]
          == [slot.slot_id for slot in catalog.slots]
          and sum(report["by_state"].values()) == len(catalog.slots),
          f"{report['slot_count']} slots; by state {report['by_state']}; "
          f"findings {[item['code'] for item in report['findings']][:5]}")

    # 20. The catalogue round-trips with an identical digest.
    again = EngineSlotCatalog.from_dict(catalog.to_dict())
    moved = replace(catalog, slots=tuple(
        replace(slot, fallback_ceiling="none") if slot.slot_id == step.slot_id else slot
        for slot in catalog.slots))
    check("the_installed_catalogue_round_trips_with_an_identical_digest",
          again.content_digest == catalog.content_digest
          and again.to_dict() == catalog.to_dict()
          and moved.content_digest != catalog.content_digest,
          catalog.content_digest)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "engine_slot_checks/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}

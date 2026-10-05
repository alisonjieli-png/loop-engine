"""Conformance kit of the ontology_change_planning slot: original fixtures, known-wrong controls, one engine alone.

```text
run_conformance_kit(engine_id, settings)           ontology_change_conformance_report/v1
├── cases: ten original ontologies (twelve runs), each with the exact new and lost entailed triples, the
│   verdict word and the rules its traces must use; every listed consequence's trace must pass the
│   independent checker. The first case is the one in the October 5, 2026 post on Open Ontologies:
│   giving hasParent the domain Person makes every individual with a parent a Person
├── controls, each a known-wrong input that must be refused:
│   ├── a stale base digest, before any engine runs; a change removing a triple the base lacks
│   ├── a forged derivation trace (a changed conclusion, an unsupported premise)
│   ├── a locked term touched by the change, and a lock the plan never checked
│   ├── a second apply of a plan whose base is gone (compare-and-swap)
│   ├── an apply without an approval, and with the approval of another plan; a changed plan
│   └── a rollback of a state that is no longer current
└── optional: the release's Lean checker (oo-cert) on the engine's traces, and on a forged one
```

The fixtures are written for this kit under example.org and carry no outside
material. ``self_test`` runs the kit on the native engine, on the adapter when
its pinned binary is configured, and the selection checks.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ..engines.host_records import EngineInstallation
from .component import HostEngines, plan_change
from .contract import (
    APPLY_REQUEST_RECORD_TYPE, CONFORMANCE_REPORT_RECORD_TYPE, CONSERVATIVE, NOT_CONSERVATIVE,
    ROLLBACK_REQUEST_RECORD_TYPE, RULE_TABLES, SLOT_ID, OntologyChangeRefused, request_record)
from .engines import (
    ADAPTER_ENGINE_ID, NATIVE_ENGINE_ID, create_engine, default_installations, default_policy, describe_engine)
from .rdf_terms import OWL, RDF, RDFS, graph_digest, parse_turtle
from .store import OntologyStore, apply_change, plan_store_change, rollback_change
from .trace_checker import check_trace, write_certificate

KIT_VERSION = "1.0.0"
BINARY_VARIABLE, CHECKER_VARIABLE = "LOOP_ENGINE_OPEN_ONTOLOGIES_BINARY", "LOOP_ENGINE_OPEN_ONTOLOGIES_CHECKER"
_K = "http://example.org/kit#"
PREFIXES = (f"@prefix kit: <{_K}> .\n@prefix rdf: <{RDF}> .\n@prefix rdfs: <{RDFS}> .\n@prefix owl: <{OWL}> .\n")
T, SC, SP = f"<{RDF}type>", f"<{RDFS}subClassOf>", f"<{RDFS}subPropertyOf>"
DOMAIN, RANGE, SAME = f"<{RDFS}domain>", f"<{RDFS}range>", f"<{OWL}sameAs>"


def k(name: str) -> str:
    return f"<{_K}{name}>"


@dataclass(frozen=True)
class KitCase:
    """One original fixture: the base, the change, and exactly what must follow.

    ``rules`` names only the rules every derivation of the expected triples must use; where two rules
    derive the same triple, an engine may record either, so neither is required."""

    case_id: str
    profiles: tuple
    base: str
    added: tuple
    removed: tuple
    new: frozenset
    lost: frozenset
    verdict: str
    rules: frozenset


CASES = (
    KitCase("domain_retypes_every_individual_with_a_parent", ("rdfs", "owl-rl"),
            "kit:Person a owl:Class . kit:hasParent a owl:ObjectProperty .\n"
            "kit:alice kit:hasParent kit:bob . kit:bob kit:hasParent kit:carol . kit:dan kit:hasParent kit:erin .",
            ((k("hasParent"), DOMAIN, k("Person")),), (),
            frozenset({(k("alice"), T, k("Person")), (k("bob"), T, k("Person")), (k("dan"), T, k("Person"))}),
            frozenset(), NOT_CONSERVATIVE, frozenset({"rdfs2"})),
    KitCase("range_types_objects_and_never_a_literal", ("rdfs",),
            'kit:alice kit:hasParent kit:bob . kit:alice kit:nickname "Al" .',
            ((k("hasParent"), RANGE, k("Person")), (k("nickname"), RANGE, k("Name"))), (),
            frozenset({(k("bob"), T, k("Person"))}), frozenset(), CONSERVATIVE, frozenset({"rdfs3"})),
    KitCase("removal_loses_subclass_consequences", ("rdfs",),
            "kit:Dog rdfs:subClassOf kit:Mammal . kit:Mammal rdfs:subClassOf kit:Animal . kit:rex a kit:Dog .",
            (), ((k("Mammal"), SC, k("Animal")),), frozenset(),
            frozenset({(k("Dog"), SC, k("Animal")), (k("rex"), T, k("Animal"))}), NOT_CONSERVATIVE,
            frozenset({"rdfs9", "rdfs11"})),
    KitCase("subproperty_and_domain_reach_a_new_individual", ("rdfs", "owl-rl"),
            "kit:hasParent rdfs:domain kit:Person . kit:hasMother rdfs:subPropertyOf kit:hasParent .",
            ((k("ann"), k("hasMother"), k("beth")),), (),
            frozenset({(k("ann"), k("hasParent"), k("beth")), (k("ann"), T, k("Person"))}), frozenset(),
            CONSERVATIVE, frozenset({"rdfs7", "rdfs2"})),
    KitCase("inverse_symmetric_and_transitive_properties", ("owl-rl",),
            "kit:isParentOf owl:inverseOf kit:hasParent . kit:marriedTo a owl:SymmetricProperty .\n"
            "kit:ancestorOf a owl:TransitiveProperty . kit:a kit:ancestorOf kit:b . kit:b kit:ancestorOf kit:c .\n"
            'kit:p kit:note "p" . kit:q kit:note "q" . kit:x kit:note "x" . kit:y kit:note "y" . kit:d kit:note "d" .',
            ((k("p"), k("hasParent"), k("q")), (k("x"), k("marriedTo"), k("y")), (k("c"), k("ancestorOf"), k("d"))),
            (), frozenset({(k("q"), k("isParentOf"), k("p")), (k("y"), k("marriedTo"), k("x")),
                           (k("a"), k("ancestorOf"), k("d")), (k("b"), k("ancestorOf"), k("d"))}),
            frozenset(), NOT_CONSERVATIVE, frozenset({"prp-inv2", "prp-symp", "prp-trp"})),
    KitCase("equivalent_classes_type_each_member", ("owl-rl",),
            'kit:Human owl:equivalentClass kit:Person . kit:zoe kit:note "zoe" .',
            ((k("zoe"), T, k("Human")),), (), frozenset({(k("zoe"), T, k("Person"))}), frozenset(),
            NOT_CONSERVATIVE, frozenset({"rdfs9", "scm-eqc1"})),
    KitCase("same_as_is_symmetric", ("owl-rl",), 'kit:a1 kit:note "a" . kit:b1 kit:note "b" .',
            ((k("a1"), SAME, k("b1")),), (), frozenset({(k("b1"), SAME, k("a1"))}), frozenset(), NOT_CONSERVATIVE,
            frozenset({"eq-sym"})),
    KitCase("schema_rules_carry_domain_and_range_up_the_hierarchy", ("owl-rl",),
            "kit:Agent a owl:Class . kit:hasParent rdfs:domain kit:Person . kit:hasParent rdfs:range kit:Person .\n"
            "kit:hasMother rdfs:subPropertyOf kit:hasParent . kit:ann kit:hasMother kit:beth .",
            ((k("Person"), SC, k("Agent")),), (),
            frozenset({(k("hasParent"), DOMAIN, k("Agent")), (k("hasParent"), RANGE, k("Agent")),
                       (k("hasMother"), DOMAIN, k("Agent")), (k("hasMother"), RANGE, k("Agent")),
                       (k("ann"), T, k("Agent")), (k("beth"), T, k("Agent"))}), frozenset(), NOT_CONSERVATIVE,
            frozenset({"scm-dom1", "scm-rng1"})),
    KitCase("a_new_leaf_class_changes_nothing_already_said", ("rdfs",), "kit:Machine a owl:Class .",
            ((k("Robot"), SC, k("Machine")),), (), frozenset(), frozenset(), CONSERVATIVE, frozenset()),
    KitCase("moving_an_edge_loses_one_type_and_gains_another", ("rdfs",),
            'kit:hasParent rdfs:domain kit:Person . kit:alice kit:hasParent kit:bob . kit:carol kit:note "c" .',
            ((k("carol"), k("hasParent"), k("bob")),), ((k("alice"), k("hasParent"), k("bob")),),
            frozenset({(k("carol"), T, k("Person"))}), frozenset({(k("alice"), T, k("Person"))}), NOT_CONSERVATIVE,
            frozenset({"rdfs2"})),
)


def _pinned_host(engine_id: str, settings) -> HostEngines:
    installation = next(item for item in default_installations(settings.get("binary_path"),
                                                                work_root=settings.get("work_root"))
                        if item.engine_id == engine_id)
    return HostEngines((installation,), default_policy((engine_id,), ()), {}, False)


def _request(case: KitCase, profile: str, **changes) -> dict:
    graph = parse_turtle(PREFIXES + case.base)
    return request_record(PREFIXES + case.base, changes.pop("base_digest", graph_digest(graph)), added=case.added,
                          removed=case.removed, profile=profile, max_listed=1000, **changes)


def _case_result(case: KitCase, profile: str, host: HostEngines) -> tuple:
    outcome = plan_change(_request(case, profile), host)
    if outcome.failure:
        return False, f"refused: {outcome.failure['code']} {outcome.failure['detail']}", None
    plan = outcome.plan
    new = {tuple(item) for item in plan["entailed"]["new"]["listed"]}
    lost = {tuple(item) for item in plan["entailed"]["lost"]["listed"]}
    rules = {step["rule"] for kind in ("new", "lost") for trace in plan["traces"][kind] for step in trace["steps"]}
    problems = []
    if new != case.new or plan["entailed"]["new"]["count"] != len(case.new):
        problems.append(f"new {sorted(new - case.new)[:2]} missing {sorted(case.new - new)[:2]}")
    if lost != case.lost or plan["entailed"]["lost"]["count"] != len(case.lost):
        problems.append(f"lost {sorted(lost - case.lost)[:2]} missing {sorted(case.lost - lost)[:2]}")
    if plan["verdict"] != case.verdict:
        problems.append(f"verdict {plan['verdict']}")
    if plan["traces"]["checked"] != len(case.new) + len(case.lost) or not case.rules <= rules:
        problems.append(f"traces checked {plan['traces']['checked']}, rules {sorted(rules)}")
    if not rules <= set(RULE_TABLES[profile]):
        problems.append(f"rules outside the {profile} table: {sorted(rules - set(RULE_TABLES[profile]))}")
    return not problems, "; ".join(problems) or "as expected", plan


def _refused(action, code: str) -> bool:
    try:
        action()
    except OntologyChangeRefused as refused:
        return refused.code == code
    return False


def _apply(store, plan, approval_ref="kit-approval", plan_digest_value=None):
    approval = {"approval_ref": approval_ref, "plan_digest": plan_digest_value or plan["plan_digest"]}
    return apply_change(store, {"record_type": APPLY_REQUEST_RECORD_TYPE, "plan": plan, "approval": approval})


def _store_controls(host: HostEngines, folder: Path) -> list:
    """The store's known-wrong cases, with plans the engine under test made."""
    case = CASES[0]
    base = parse_turtle(PREFIXES + case.base)
    results = []
    locked = OntologyStore.create(folder / "locked", base, locked_terms=(k("dan"),))
    plan = plan_store_change(locked, added=case.added, host=host).plan
    results.append(("a_locked_term_is_refused_at_apply", plan is not None and _refused(
        lambda: _apply(locked, plan), "locked_term") and locked.digest() == graph_digest(base)))
    late = OntologyStore.create(folder / "late-lock", base)
    plan = plan_store_change(late, added=case.added, host=host).plan
    late.lock((k("erin"),), "locked after the plan was made")
    results.append(("a_lock_the_plan_never_checked_is_refused", plan is not None and _refused(
        lambda: _apply(late, plan), "locked_term")))
    store = OntologyStore.create(folder / "store", base)
    first = plan_store_change(store, added=case.added, host=host).plan
    second = plan_store_change(store, added=((k("hasParent"), RANGE, k("Person")),), host=host).plan
    results.append(("apply_requires_an_approval_naming_the_plan", first is not None and _refused(
        lambda: apply_change(store, {"record_type": APPLY_REQUEST_RECORD_TYPE, "plan": first, "approval": None}),
        "approval_required") and _refused(lambda: _apply(store, first, plan_digest_value=second["plan_digest"]),
                                          "approval_mismatch")))
    changed = {**first, "verdict": CONSERVATIVE}
    results.append(("a_changed_plan_is_refused", _refused(lambda: _apply(store, changed), "plan_invalid")))
    applied = _apply(store, first)
    results.append(("apply_is_compare_and_swap_on_the_base_digest", applied["new_digest"] == store.digest()
                    and _refused(lambda: _apply(store, second), "stale_base")))
    rollback = {"record_type": ROLLBACK_REQUEST_RECORD_TYPE, "rollback": applied["rollback"],
                "approval": {"approval_ref": "kit-rollback", "plan_digest": first["plan_digest"]}}
    restored = rollback_change(store, rollback)
    results.append(("rollback_restores_only_the_state_it_replaced", restored["new_digest"] == graph_digest(base)
                    and store.digest() == graph_digest(base)
                    and _refused(lambda: rollback_change(store, rollback), "stale_rollback")))
    return results


def _forgery_controls(plan: dict, profile: str) -> list:
    """A genuine trace passes the checker; a changed conclusion and an unsupported premise do not."""
    asserted = parse_turtle(PREFIXES + CASES[0].base) | set(CASES[0].added)
    trace = plan["traces"]["new"][0]["steps"]
    forged_conclusion = [dict(step) for step in trace]
    forged_conclusion[-1] = {**forged_conclusion[-1], "conclusion": [forged_conclusion[-1]["conclusion"][0], T,
                                                                     k("Robot")]}
    unsupported = [dict(step) for step in trace]
    unsupported[0] = {**unsupported[0], "premises": [[k("zed"), k("hasParent"), k("yan")],
                                                     *unsupported[0]["premises"][1:]]}
    genuine = check_trace(asserted, trace, rule_table=RULE_TABLES[profile])
    first = check_trace(asserted, forged_conclusion, rule_table=RULE_TABLES[profile])
    second = check_trace(asserted, unsupported, rule_table=RULE_TABLES[profile])
    return [("every_listed_consequence_carries_a_trace_the_independent_checker_accepts", genuine.ok),
            ("a_forged_derivation_trace_is_refused", not first.ok and first.first_rejected == len(trace) - 1
             and not second.ok and second.first_rejected == 0)]


def _lean_cross_check(plan: dict, checker_path: str) -> dict:
    from .open_ontologies_engine import run_lean_checker
    case = CASES[0]
    proposed = parse_turtle(PREFIXES + case.base) | set(case.added)
    steps, seen = [], set()
    for trace in plan["traces"]["new"]:
        for step in trace["steps"]:
            if tuple(step["conclusion"]) not in seen:
                seen.add(tuple(step["conclusion"]))
                steps.append(step)
    asserted_text, derivations_text = write_certificate(proposed, steps)
    genuine = run_lean_checker(checker_path, asserted_text, derivations_text)
    forged_steps = [*steps[:-1], {**steps[-1], "conclusion": [steps[-1]["conclusion"][0], T, k("Robot")]}]
    forged = run_lean_checker(checker_path, *write_certificate(proposed, forged_steps))
    return {"ran": genuine.get("ran", False), "genuine": genuine, "forged": forged,
            "passed": bool(genuine.get("ok") and forged.get("ran") and not forged.get("ok")
                           and forged.get("exit") == 1)}


def run_conformance_kit(engine_id: str, settings=None, *, checker_path: "str | None" = None) -> dict:
    """Run every case and control with one engine alone; the report binds its exact descriptor."""
    settings = dict(settings or {})
    host = _pinned_host(engine_id, settings)
    descriptor = describe_engine(engine_id, host.installations[0].settings)
    cases, controls, first_plan = [], [], None
    for case in CASES:
        for profile in case.profiles:
            started = time.monotonic()
            passed, detail, plan = _case_result(case, profile, host)
            if case is CASES[0] and profile == "owl-rl":
                first_plan = plan
            cases.append({"case": case.case_id, "profile": profile, "passed": passed, "detail": detail[:300],
                          "seconds": round(time.monotonic() - started, 3)})
    stale = plan_change(_request(CASES[0], "rdfs", base_digest=graph_digest(())), host)
    controls.append(("a_stale_base_digest_is_refused_before_any_engine_runs",
                     stale.failure is not None and stale.failure["code"] == "base_digest_mismatch"
                     and not stale.decisions))
    absent = replace(CASES[0], removed=((k("zed"), k("hasParent"), k("yan")),))
    refused = plan_change(_request(absent, "rdfs"), host)
    controls.append(("a_change_that_removes_an_absent_triple_is_refused",
                     refused.failure is not None and refused.failure["code"] == "change_invalid"))
    if first_plan is not None:
        controls += _forgery_controls(first_plan, "owl-rl")
    with tempfile.TemporaryDirectory(prefix="ontology-change-kit-") as folder:
        try:
            controls += _store_controls(host, Path(folder))
        except (OntologyChangeRefused, TypeError, KeyError) as error:
            controls.append(("store_controls_completed", False))
            cases.append({"case": "store_controls", "profile": "", "passed": False, "detail": str(error)[:300],
                          "seconds": 0.0})
    lean = {"ran": False, "reason": "no checker path given"}
    if checker_path and first_plan is not None:
        lean = _lean_cross_check(first_plan, checker_path)
    passed = all(item["passed"] for item in cases) and all(ok for _name, ok in controls) and (
        not lean.get("ran") or lean.get("passed"))
    return {"record_type": CONFORMANCE_REPORT_RECORD_TYPE, "kit_version": KIT_VERSION, "slot_id": SLOT_ID,
            "engine_ref": descriptor.engine_ref, "descriptor_digest": descriptor.content_digest, "passed": passed,
            "cases": cases, "controls": [{"control": name, "passed": ok} for name, ok in controls],
            "lean_cross_check": lean, "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def write_report(folder, report: dict) -> Path:
    """Record one report as evidence, named by the descriptor it binds."""
    path = Path(folder) / f"{report['descriptor_digest']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_evidence(folder) -> dict:
    """descriptor digest -> report, for every report file in the folder."""
    evidence = {}
    for path in sorted(Path(folder).glob("*.json")) if folder and Path(folder).is_dir() else ():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("record_type") == CONFORMANCE_REPORT_RECORD_TYPE and path.stem == report.get(
                "descriptor_digest"):
            evidence[report["descriptor_digest"]] = report
    return evidence


def _selection_checks(native_report: dict) -> list:
    """Declared order and recorded evidence decide; a failed engine falls back to the next declared one."""
    case = CASES[0]
    request = _request(case, "owl-rl")
    without = plan_change(request, HostEngines(default_installations(), default_policy(), {}, True))
    gate = without.failure is not None and without.failure["code"] == "no_eligible_engine" and any(
        "conformance_kit" in refusal["detail"] for decision in without.decisions
        for entry in decision["eligibility"] for refusal in entry["refusals"])
    evidence = {native_report["descriptor_digest"]: native_report}
    chosen = plan_change(request, HostEngines(default_installations(), default_policy(), evidence, True))
    ordered = chosen.plan is not None and chosen.decisions[0]["selected"]["installation_id"] == NATIVE_ENGINE_ID
    native = default_installations()[0]
    twins = (native, EngineInstallation("native_twin", NATIVE_ENGINE_ID, native.engine_kind, True, {}, None, None))
    host = HostEngines(twins, default_policy(("baltor_native_rules",), ("native_twin",)), {}, False)
    calls = []
    original = type(create_engine(NATIVE_ENGINE_ID)).plan

    def fail_once(engine, planning_input):
        calls.append(1)
        if len(calls) == 1:
            from .contract import EngineFailure
            raise EngineFailure("engine_reported_failure", "a known-wrong first engine")
        return original(engine, planning_input)

    with patch.object(type(create_engine(NATIVE_ENGINE_ID)), "plan", fail_once):
        fallback = plan_change(request, host)
    phases = [item["phase"] for item in fallback.decisions]
    falls_back = (fallback.plan is not None and phases == ["initial", "fallback"]
                  and fallback.decisions[1]["transition"]["failure_kind"] == "engine_reported_failure")
    return [("selection_follows_the_declared_order_and_recorded_evidence", gate and ordered),
            ("a_failed_engine_falls_back_to_the_next_declared_engine", falls_back)]


def self_test() -> dict:
    tests = []
    report = run_conformance_kit(NATIVE_ENGINE_ID)
    tests.append({"test": "the_native_engine_passes_the_kit_alone", "passed": report["passed"],
                  "detail": json.dumps([item for item in report["cases"] + report["controls"]
                                        if not item["passed"]])[:400]})
    for item in report["controls"]:
        tests.append({"test": item["control"], "passed": item["passed"], "detail": "native engine"})
    for name, ok in _selection_checks(report):
        tests.append({"test": name, "passed": ok, "detail": ""})
    binary = os.environ.get(BINARY_VARIABLE, "")
    adapter = create_engine(ADAPTER_ENGINE_ID, {"binary_path": binary} if binary else {})
    available, reason = adapter.availability()
    if available:
        adapter_report = run_conformance_kit(ADAPTER_ENGINE_ID, {"binary_path": binary},
                                             checker_path=os.environ.get(CHECKER_VARIABLE) or None)
        tests.append({"test": "the_open_ontologies_adapter_passes_the_kit_alone", "passed": adapter_report["passed"],
                      "detail": json.dumps([item for item in adapter_report["cases"] + adapter_report["controls"]
                                            if not item["passed"]])[:400]})
    else:
        tests.append({"test": "the_open_ontologies_adapter_passes_the_kit_alone", "passed": None, "not_tested": True,
                      "outcome": "NOT_APPLICABLE",
                      "missing_optional_dependencies": [f"open-ontologies v2.0.1 Linux binary ({BINARY_VARIABLE})"],
                      "detail": reason[:300]})
    return {"tests": tests}

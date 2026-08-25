"""The operational-boundary register — where "everything is a loop" is checked.

Architectural role: Static Architecture service (the conformance inventory).

Constitution Article 1 says everything that crosses an operational boundary is
a loop. That claim is only worth as much as the list it is checked against.
Without a register, "everything is a loop" is a slogan that each session
re-argues from memory; with one, it is a finite list where every row either
names its envelope or is openly marked unbound.

A boundary is a place where something independently **discoverable,
selectable, invokable, observable, retryable, replaceable, composable,
versioned, governed, or Studio-visible** is reached. Private helpers inside a
loop's body are implementation, not boundaries, and are deliberately absent.

Owns:
    - BOUNDARIES: every known operational boundary, its binding state, the
      envelope that wraps it, and the test that proves it;
    - boundary_report(): the computed inventory — bound, unbound, and the
      coverage ratio, with nothing rounded up;
    - unbound_boundaries(): the honest work queue.

Does not own:
    - the envelopes (encapsulate), the templates (loop_templates), or the
      gates (conformance_report) — this is the register they are checked
      against, never a second enforcement path.

Public entry points:
    - boundary_report() -> dict
    - unbound_boundaries() -> list

Key invariants:
    - a row may not claim `bound` without naming both an envelope and a test;
    - the register is data, so a boundary cannot be quietly dropped to make
      the ratio look better — removing a row is a visible diff;
    - UNBOUND is a legitimate state. Marking one bound without an envelope is
      the failure this module exists to prevent.

Verification: self_test() — every claimed binding resolves to a real callable,
every bound row names a test, and the adversarial row shape is refused.
"""
from __future__ import annotations

#: How a boundary reaches its loop.
BINDING_KINDS = (
    "practitioner_loop",     # wrapped by as_practitioner_loop
    "component_loop",        # wrapped by as_component_loop (fallback arms)
    "stage_loop_tree",       # runs as a loop of stage loops
    "native_loop",           # IS the loop runtime itself
    "api_dispatch",          # crosses in through serve_api
    "template_governed",     # runs under a registered template envelope
    "unbound",               # honestly not wrapped yet
)

#: The register. Each row: the boundary, what crosses it, how it is bound,
#: the module that owns the envelope, and the test that proves it.
BOUNDARIES = (
    {"boundary": "root solve", "crosses": "a user task enters the runtime",
     "binding": "native_loop", "envelope": "loop.recursive_loop.Loop",
     "test": "recursive_loop.self_test"},
    {"boundary": "reference nine-step stages",
     "crosses": "each of the nine stages executes",
     "binding": "stage_loop_tree",
     "envelope": "loop.encapsulate.as_loop_of_stage_loops",
     "test": "encapsulate:reference_nine_step_runs_as_nine_stage_loops"},
    {"boundary": "deterministic check",
     "crosses": "a plain callable runs as governed work",
     "binding": "practitioner_loop",
     "envelope": "loop.encapsulate.as_practitioner_loop",
     "test": "encapsulate:deterministic_check_runs_as_practitioner_loop"},
    {"boundary": "solution component",
     "crosses": "a Solution Canvas box executes",
     "binding": "component_loop",
     "envelope": "loop.encapsulate.as_component_loop",
     "test": "solution_canvas:"
             "every_solution_component_executes_as_a_practitioner_loop"},
    {"boundary": "api endpoint",
     "crosses": "a browser, harness, or tenant reads Loop Engine",
     "binding": "api_dispatch", "envelope": "static_architecture.saas_routes"
                                            ".serve_api",
     "test": "saas_routes:every_api_call_crosses_into_a_practitioner_loop"},
    {"boundary": "user intelligence resolution",
     "crosses": "a loop consults human guidance before deciding",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.user_intelligence"
                 ".resolve_user_intelligence",
     "test": "user_intelligence:"
             "snapshot_resolution_is_a_thin_deterministic_loop"},
    {"boundary": "external harness delegation",
     "crosses": "a bounded assignment goes to an outside coding agent",
     "binding": "template_governed",
     "envelope": "loop_templates:external_harness_worker",
     "test": "loop_templates:"
             "external_harness_worker_is_opaque_bounded_and_clamped"},
    {"boundary": "promotion review",
     "crosses": "a candidate is considered for registered status",
     "binding": "template_governed",
     "envelope": "static_architecture.asset_lifecycle"
                 ".promotion_review_as_loop",
     "test": "asset_lifecycle.self_test"},
    {"boundary": "external submission",
     "crosses": "an artifact leaves for a third party",
     "binding": "template_governed",
     "envelope": "code_nodes.smoke_ladder.submission_as_loop",
     "test": "smoke_ladder.self_test"},
    {"boundary": "retrieval tournament",
     "crosses": "a backend is measured against the incumbent",
     "binding": "template_governed",
     "envelope": "static_architecture.retrieval.tournament_as_loop",
     "test": "retrieval.self_test"},
    {"boundary": "intelligence foundry wave",
     "crosses": "raw model output becomes candidate Strings",
     "binding": "template_governed",
     "envelope": "code_nodes.string_foundry.foundry_wave_as_loop",
     "test": "string_foundry.self_test"},
    {"boundary": "model invocation",
     "crosses": "a prompt reaches a provider",
     "binding": "practitioner_loop",
     "envelope": "loop.encapsulate.as_model_loop",
     "test": "encapsulate:the_model_boundary_crosses_a_loop_that_permits_one_"
             "semantic_call"},
    {"boundary": "provider-neutral model routing",
     "crosses": "one typed model request is attempted across configured routes",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.model_gateway.invoke_model_gateway",
     "test": "model_gateway.self_test"},
    {"boundary": "runtime settings resolution",
     "crosses": "YAML and environment preferences become typed runtime settings",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.settings_loader.load_runtime_settings",
     "test": "settings_loader:yaml_then_environment_precedence_is_visible"},
    {"boundary": "runtime settings file creation",
     "crosses": "a default user settings file is written to disk",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.settings_loader.write_default_settings",
     "test": "settings_loader:settings_file_creation_is_also_a_loop"},
    {"boundary": "runtime memory write",
     "crosses": "a loop leaves a note for its siblings",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.runtime_memory.RunNoteBoard",
     "test": "runtime_memory.self_test"},
    # --- found by the completeness detector, 2026-08-24 -------------------
    # The register read 14/14 while these five were doing envelope work and
    # were absent from it.  "Complete about itself" is not "complete".
    {"boundary": "preference resolution",
     "crosses": "requested settings become the immutable spec a loop runs on",
     "binding": "practitioner_loop",
     "envelope": "loop.effective_spec.resolve_effective_spec",
     "test": "effective_spec:resolution_is_deterministic_and_digested"},
    {"boundary": "intelligence serving",
     "crosses": "a stored String, capability, guidance row or prior run is "
                "served to a caller",
     "binding": "practitioner_loop",
     "envelope": "loop.intelligence_loops.serve_pillar",
     "test": "intelligence_loops.self_test"},
    {"boundary": "improvement campaign",
     "crosses": "a bounded self-improvement campaign runs",
     "binding": "practitioner_loop",
     "envelope": "loop.practitioner_campaign.development_practitioner_loop",
     "test": "practitioner_campaign.self_test"},
    {"boundary": "multi-problem comparison campaign",
     "crosses": "frozen problem cases expand into mode and provider arms",
     "binding": "native_loop",
     "envelope": "code_nodes.campaign_runner.run_campaign_arm",
     "test": "campaign_runner.self_test"},
    {"boundary": "studio history read",
     "crosses": "the Studio reads a saved run",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.studio_server._load_run_as_historical_loop",
     "test": "studio_server:the_event_stream_is_the_canonical_vocabulary"},
    {"boundary": "loop reference invocation",
     "crosses": "a chosen LoopRef becomes content",
     "binding": "practitioner_loop",
     "envelope": "loop.loop_capsule.invoke_ref",
     "test": "loop_capsule:invoking_a_ref_runs_the_loop_and_returns_content"},
    {"boundary": "static capability invocation",
     "crosses": "a selected Static Architecture capability performs work",
     "binding": "component_loop",
     "envelope": "loop.capability_loops.run_capability_as_loop",
     "test": "capability_loops.self_test"},
    {"boundary": "Code Intelligence entry point",
     "crosses": "a selected Code Intelligence body executes one entry point",
     "binding": "component_loop",
     "envelope": "static_architecture.code_intelligence_assets.execute_code_ref",
     "test": "code_intelligence_assets.self_test"},
    {"boundary": "solution graph adapter",
     "crosses": "a value converts between two incompatible typed ports",
     "binding": "component_loop",
     "envelope": "code_nodes.solution_graph.run_adapter_loop",
     "test": "solution_graph:"
             "the_adapter_executes_as_a_loop_not_an_edge_function"},
    {"boundary": "persistence",
     "crosses": "an artifact is written to disk",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.persistence.append_record_as_loop",
     "test": "persistence.self_test"},
)


class BoundaryError(ValueError):
    """A register row that claims more than it can show."""


def _validate(row: dict) -> None:
    if row.get("binding") not in BINDING_KINDS:
        raise BoundaryError(f"{row.get('boundary')!r}: binding "
                            f"{row.get('binding')!r} not in {BINDING_KINDS}")
    if row["binding"] != "unbound" and not (row.get("envelope")
                                            and row.get("test")):
        raise BoundaryError(
            f"{row['boundary']!r} claims binding {row['binding']!r} without "
            "naming both an envelope and a test — a claimed binding with no "
            "proof is worse than an honest unbound row")


def boundary_report() -> dict:
    """The computed inventory. Nothing here is rounded up: a boundary is
    bound only if it names the envelope that wraps it AND the test that
    proves it."""
    for row in BOUNDARIES:
        _validate(row)
    bound = [r for r in BOUNDARIES if r["binding"] != "unbound"]
    unbound = [r for r in BOUNDARIES if r["binding"] == "unbound"]
    by_kind: dict = {}
    for r in bound:
        by_kind[r["binding"]] = by_kind.get(r["binding"], 0) + 1
    return {"record_type": "operational_boundary_report/v1",
            "total": len(BOUNDARIES), "bound": len(bound),
            "unbound": len(unbound),
            "coverage": round(len(bound) / len(BOUNDARIES), 3),
            "by_binding_kind": by_kind,
            "unbound_boundaries": [r["boundary"] for r in unbound],
            "honesty": "coverage counts only rows naming an envelope AND a "
                       "test; unbound rows are work, not noise"}


def unbound_boundaries() -> list:
    """The work queue, in the register's own words."""
    return [{"boundary": r["boundary"], "crosses": r["crosses"],
             "why_open": r.get("note", "")}
            for r in BOUNDARIES if r["binding"] == "unbound"]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    rep = boundary_report()

    # 1. the register is well-formed and the report is computed, not asserted.
    # The invariant is that the report SUMS and is computed — not that some
    # boundary is always open.  An earlier version asserted 0 < coverage < 1,
    # which encoded the state of the day rather than a property, and failed
    # the moment the last boundary was bound.  Full coverage must be allowed
    # to be reached, or the register punishes finishing the work.
    check("the_register_is_wellformed_and_the_report_is_computed",
          rep["total"] == len(BOUNDARIES)
          and rep["bound"] + rep["unbound"] == rep["total"]
          and 0.0 <= rep["coverage"] <= 1.0
          and rep["total"] > 0,
          f"{rep['bound']}/{rep['total']} bound "
          f"({rep['coverage']:.0%}), {rep['unbound']} open")

    # 2. EVERY claimed envelope resolves to something real.  A register that
    # names a function nobody wrote would be worse than no register: it would
    # make an unproven claim look audited.
    # Resolved STATICALLY, by parsing the module rather than importing it:
    # a register that verified itself by import would trip the dynamic-import
    # gate, and would also run module side effects just to answer "does this
    # name exist". The AST answers it without executing anything.
    import ast
    import os
    pkg_root = os.path.dirname(os.path.dirname(__file__))
    unresolved = []
    for r in BOUNDARIES:
        env = r.get("envelope", "")
        if not env or ":" in env:          # template refs checked separately
            continue
        mod, _, attr = env.rpartition(".")
        path = os.path.join(pkg_root, *mod.split(".")) + ".py"
        if not os.path.exists(path):
            unresolved.append(f"{env} (no module {path})")
            continue
        tree = ast.parse(open(path).read())
        names = {n.name for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef))}
        for n in tree.body:                # module-level constants too
            if isinstance(n, ast.Assign):
                names.update(t.id for t in n.targets
                             if isinstance(t, ast.Name))
        if attr not in names:
            unresolved.append(f"{env} (no top-level {attr})")
    check("every_claimed_envelope_resolves_to_real_code", not unresolved,
          f"unresolved: {unresolved}" if unresolved
          else "all dotted envelopes import and expose their attribute")

    # 3. template-referenced envelopes name REGISTERED templates.
    from ..loop.loop_templates import TEMPLATE_LIBRARY
    registered = {t["template_id"] for t in TEMPLATE_LIBRARY
                  if t.get("maturity") == "registered"}
    tmpl_refs = [r["envelope"].split(":", 1)[1] for r in BOUNDARIES
                 if r.get("envelope", "").startswith("loop_templates:")]
    check("template_bound_boundaries_name_registered_templates",
          all(t in registered for t in tmpl_refs) and tmpl_refs,
          f"{tmpl_refs} all registered")

    # 4. ADVERSARIAL: a row claiming a binding without an envelope or a test
    # is REFUSED.  This is the failure mode the register exists to prevent —
    # marking something bound because it feels bound.
    refused_no_env = refused_bad_kind = False
    try:
        _validate({"boundary": "x", "binding": "practitioner_loop",
                   "envelope": "", "test": ""})
    except BoundaryError:
        refused_no_env = True
    try:
        _validate({"boundary": "x", "binding": "vibes"})
    except BoundaryError:
        refused_bad_kind = True
    check("a_binding_claimed_without_proof_is_refused",
          refused_no_env and refused_bad_kind,
          "no envelope+test -> refused; unknown binding kind -> refused")

    # 5. the unbound queue is legible work, not a silent gap.
    open_work = unbound_boundaries()
    # Vacuously true at full coverage, and that is correct: the rule is that
    # an open boundary must carry a REASON, not that one must exist.
    check("unbound_boundaries_are_named_work_with_reasons",
          len(open_work) == rep["unbound"]
          and all(w["why_open"] for w in open_work),
          f"open: {[w['boundary'] for w in open_work] or 'none — 100%'}")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

"""Architecture conformance + adversarial suite (§22–§23 of the reset).

These tests FAIL when the repository drifts from the loop-of-loops
architecture: the asset binary (String | Code Node), one canonical runtime
path, recursive-loop invariants, mode/permission gates, the model boundary,
and the no-self-promotion rule.  Adversarial cases actively try to break the
rails — recursion explosion, budget evasion, permission elevation, hidden
semantic fallbacks, orphan templates, self-promotion — and must produce an
inspectable refusal, never a silent hang.
"""
from __future__ import annotations

import importlib
import json


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .loop.recursive_loop import (Loop, LoopConfig, LoopError,
                                      StepOutcome, default_handler)

    # ------------------------------------------------------------------ §22
    # Asset binary: every classified asset is String or Code Node.
    from .core.asset_class import KIND_CLASS, classify
    other = {k: v for k, v in KIND_CLASS.items() if v not in ("string", "code")}
    check("conformance_every_asset_kind_is_string_or_code",
          not other and classify("loop") == "code"
          and classify("context") == "string",
          f"non-binary kinds: {other}")

    # One canonical runtime: no parallel runtime class or public alias.
    check("conformance_one_canonical_runtime",
          Loop.__name__ == "Loop" and Loop.run_to_completion is Loop.run,
          "Loop is the only runtime class")

    # Obsolete package-root module paths are dead. This checks path layout only;
    # the scanner separately checks root exports for parallel runtime surfaces.
    # A documentation-only folder (no __init__.py) is not a real module even
    # when Python namespace-package rules would allow an empty import.
    from .architecture_map import PACKAGE
    legacy_reachable = []
    for legacy in ("kernel", "recursive_loop", "capability_directory",
                   "intelligence_strings", "measurement"):
        spec = importlib.util.find_spec(f"{PACKAGE}.{legacy}")
        if spec is not None and spec.origin is not None:
            legacy_reachable.append(legacy)
    check("conformance_obsolete_flat_module_paths_are_dead", not legacy_reachable,
          f"still importable at the old root: {legacy_reachable}")

    import loop_engine as public_package
    retired_decision_names = {
        "".join(("What", "Is", "Next", "Answer")),
        "".join(("What", "Is", "Next", "Resolver")),
        "".join(("WHATS", "_NEXT", "_ANSWER_KINDS")),
    }
    forbidden = set(public_package.__dict__.get("__all__", ())) & ({
        "SolverCell", "Practitioner", "SolverCellState", "LoopState",
        "PractitionerNode", "run_practitioner_loop", "UniversalSolver",
        "PractitionerState", "run_practitioner", "run_swarm",
        "PractitionerLoop", "LoopSpec",
    } | retired_decision_names)
    check("conformance_root_exports_only_the_canonical_runtime",
          not forbidden
          and "PractitionerLoop" not in public_package.__dict__.get(
              "__all__", ())
          and not hasattr(public_package, "PractitionerLoop")
          and public_package.Loop is Loop,
          f"parallel root runtime names: {sorted(forbidden)}")

    from .__main__ import (
        _concise_self_test_summary, _run_self_test_captured)

    def noisy_fixture():
        import sys
        descriptor = sys.stdout.fileno()
        print("module demo noise")
        return {
            "tests": [{"test": "fixture failure", "passed": False,
                       "detail": "bounded failure detail"}],
            "passed": 0, "total": 1, "all_passed": False,
            "missing_dependencies": [], "descriptor": descriptor,
        }

    captured_report, captured_lines = _run_self_test_captured(noisy_fixture)
    concise = _concise_self_test_summary(captured_report, captured_lines)
    check("concise_self_test_uses_an_OS_backed_stream_and_keeps_failures",
          captured_report["descriptor"] >= 0
          and captured_lines == 1
          and concise["failures"] == [{
              "test": "fixture failure", "detail": "bounded failure detail"}]
          and concise["all_passed"] is False,
          "folded demo output is captured; the failing test remains visible")

    # Recursive loops: parent → spawned → nested_spawned_loop return and integrate.
    def spawning(loop, step, context):
        if step == "research" and loop.depth < 2 and f"{step}:spawned" not in context:
            return StepOutcome(output="needs spawned", mode="deterministic",
                               spawn_goal=f"sub-research d{loop.depth + 1}")
        return default_handler(loop, step, context)
    root = Loop("root", LoopConfig(framework="custom",
                                   custom_steps=("orient", "research", "act"),
                                   max_depth=2))
    r = root.run(handler=spawning)
    tree = root.ledger.tree()
    depths = {e.get("depth") for e in root.ledger.events
              if e.get("event") == "spawn"}
    check("conformance_parent_spawned_nested_spawned_loop_integrate",
          r.spawned >= 2 and depths >= {1, 2}
          and root.loop_id in tree and r.stopped == "done",
          f"{r.spawned} descendants across depths {sorted(depths)}; "
          "answers flowed back up")

    # ------------------------------------------------------------------ §23
    # Adversarial: recursion explosion is bounded, not a hang.
    def bomber(loop, step, context):
        return StepOutcome(output="spawn more", mode="deterministic",
                           spawn_goal="spawned forever")
    b = Loop("bomb", LoopConfig(framework="five_step", max_depth=2,
                                power="light"))
    rb = b.run(handler=bomber)
    check("adversarial_recursion_explosion_is_bounded",
          rb.steps_run <= 3 and all(e.get("depth", 0) <= 2
                                    for e in b.ledger.events),
          f"depth capped at 2; {rb.spawned} spawns total, no hang")

    # Adversarial: a spawned Loop cannot exceed the spawning Loop's authority.
    det_parent = Loop("det only", LoopConfig(allowable_modes=("deterministic",),
                                             preferred_modes=("deterministic",),
                                             delegated_modes=("deterministic",)))
    clamped = det_parent.spawn("spawned", LoopConfig(
        allowable_modes=("deterministic", "non_deterministic")))
    refused = False
    try:
        det_parent.spawn("evil", LoopConfig(
            allowable_modes=("non_deterministic",),
            preferred_modes=("non_deterministic",)))
    except LoopError:
        refused = True
    clamp_events = [e for e in det_parent.ledger.events
                    if e.get("modes_clamped_from")]
    check("adversarial_spawned_cannot_exceed_delegation_authority",
          clamped.config.allowable_modes == ("deterministic",)
          and refused and clamp_events,
          "delegated widening is clamped and recorded; disjoint modes refuse")

    # Adversarial: MAX power does not expand permissions — a deterministic-only
    # loop at max power still makes ZERO semantic calls.
    maxed = Loop("max det", LoopConfig(allowable_modes=("deterministic",),
                                       preferred_modes=("deterministic",),
                                       power="max", framework="five_step"))
    rm = maxed.run()
    check("adversarial_max_power_grants_no_permissions",
          rm.model_calls == 0 and rm.steps_run == 5
          and "non_deterministic" not in rm.mode_counts
          and "hybrid" not in rm.mode_counts,
          "max raises budgets, never modes: zero semantic calls")

    # Adversarial: budget evasion — a model-led loop cannot exceed its
    # model-call budget by one extra call, and the stop is recorded.
    greedy = Loop("greedy", LoopConfig(
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",), power="light"))
    rg = greedy.run(handler=lambda loop, step, context: StepOutcome(
        output="model attempt", mode="non_deterministic", model_calls=1))
    stops = [e for e in greedy.ledger.events if e.get("event") == "budget_stop"]
    check("adversarial_model_budget_cannot_be_evaded",
          rg.stopped == "budget" and stops
          and rg.model_calls == greedy.config.settings["max_model_calls"] + 1,
          "the call that crossed the budget stopped the loop, on the ledger")

    # Adversarial: hidden semantic fallback — a failed semantic step may NOT
    # retry semantically inside the same iteration (§12).
    def semantic_flaky(loop, step, context):
        if step == "act" and "act" not in context:
            return StepOutcome(output="err", mode="hybrid", failed=True,
                               model_calls=1)
        return default_handler(loop, step, context)
    h = Loop("hidden", LoopConfig(framework="custom",
                                  custom_steps=("orient", "act"), power="deep"))
    recs = []
    while not h.is_terminal:
        recs.append(h.run_next_iteration(handler=semantic_flaky))
    check("adversarial_no_hidden_semantic_fallback_in_iteration",
          all(r.get("semantic_calls", 0) <= 1 for r in recs)
          and any(e.get("event") == "model_boundary_deferred"
                  for e in h.ledger.events),
          "the semantic retry became a NEW visible iteration")

    # Adversarial: an orphan/unbounded generated template cannot run.
    from .loop.loop_templates import config_from_template, validate_template
    orphan = {"template_id": "evil", "framework": "custom", "steps": ()}
    unbounded = {"template_id": "evil2", "framework": "custom",
                 "steps": tuple(f"s{i}" for i in range(9999))}
    candidate = {"template_id": "evil3", "framework": "custom",
                 "steps": ("a", "b"), "maturity": "candidate"}
    refusals = 0
    for tmpl in (orphan, unbounded, candidate):
        try:
            config_from_template(tmpl)
        except ValueError:
            refusals += 1
    check("adversarial_bad_templates_refused_inspectably",
          refusals == 3 and not validate_template(orphan)["valid"],
          "orphan, unbounded, and unadmitted templates all refused with reasons")

    # Adversarial: self-promotion — the improvement lane's own guard refuses
    # promote/overwrite/delete-evidence actions.
    from .code_nodes.housekeeping import SafeguardError, guard_improvement_action
    blocked = 0
    for a in ("promote", "overwrite_accepted", "delete_evidence"):
        try:
            guard_improvement_action(a)
        except SafeguardError:
            blocked += 1
    try:
        guard_improvement_action("stage_candidate")
        allowed = True
    except SafeguardError:
        allowed = False
    check("adversarial_improvement_cannot_self_promote",
          blocked == 3 and allowed,
          "stage yes; promote/overwrite/delete-evidence raise SafeguardError")

    # Adversarial: lifecycle promotion without evidence is refused.
    from .core.asset_lifecycle import (PromotionRefused, advance)
    lifecycle_refused = False
    try:
        advance("validated", "registered", evidence={})
    except PromotionRefused:
        lifecycle_refused = True
    check("adversarial_promotion_without_evidence_refused", lifecycle_refused)

    # Adversarial: the cloud-only model gate — local counted generation refused
    # by policy; kimi-k3 refused at construction, any route, any purpose.
    from .core.model_routes import (ModelRoute, RoutePolicy,
                                                   RouteViolation, screen_route)
    local_refused = kimi_refused = False
    try:
        local = ModelRoute("local gen", "ollama_local", "llama3:8b",
                           locality="local",
                           purposes=("counted_generation",))
        screen_route(local, purpose="counted_generation", policy=RoutePolicy())
    except (RouteViolation, ValueError):
        local_refused = True
    try:
        ModelRoute("k", "ollama_cloud", "kimi-k3:cloud")
    except (RouteViolation, ValueError):
        kimi_refused = True
    check("adversarial_cloud_only_and_forbidden_family_hold",
          local_refused and kimi_refused,
          "local counted generation refused by the policy switch; kimi-k3 never")

    # Adversarial: a pause token round-trips through JSON and resumes to the
    # SAME final result — no corrupted-state resume.
    a1 = Loop("resume int", LoopConfig(framework="five_step", power="deep"))
    a1.run_next_iteration(); a1.run_next_iteration()
    tok = json.loads(json.dumps(a1.pause()))
    a2 = Loop.resume(tok)
    ra = a2.run()
    b1 = Loop("resume int", LoopConfig(framework="five_step", power="deep")).run()
    check("adversarial_resume_reproduces_the_uninterrupted_run",
          ra.steps_run == b1.steps_run == 5 and ra.output == b1.output,
          "paused+resumed run ends exactly like the uninterrupted one")

    # Adversarial: a spawned-but-never-run Loop is an orphan.
    # that fails closure; running it closes the tree.
    pc = Loop("closure", LoopConfig(framework="five_step", power="deep"))
    ghost = pc.spawn("never run")
    pc.run()
    audit1 = pc.audit_closure()
    ghost.run()
    audit2 = pc.audit_closure()
    check("adversarial_orphaned_spawned_fails_closure_audit",
          ghost.loop_id in audit1["orphaned_spawned_loops"] and not audit1["closed"]
          and audit2["closed"] and not audit2["orphaned_spawned_loops"],
          "orphan flagged inspectably; closure holds once every spawned is "
          "terminal (terminal events are on the ledger)")

    # Conformance: secrets never enter template/String records (spot scan of
    # the shipped library for credential-shaped content).
    from .loop.loop_templates import template_records
    leaky = [r.record_id for r in template_records()
             if any(tok in json.dumps(r.body).lower()
                    for tok in ("api_key", "secret", "password", "token="))]
    check("conformance_no_secret_shaped_content_in_shipped_strings",
          not leaky, f"credential-shaped content in: {leaky}")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

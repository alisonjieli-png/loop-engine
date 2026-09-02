"""Loop Templates — Strings, not new runtimes (§5 of the reset directive).

One generic loop runtime (``recursive_loop.Loop``) is configured by Loop
Template Strings.  The nine-step sequence is a recommended template, not the
universal execution law; a custom loop may use any bounded ordering.

Every template is a serializable body validated BEFORE it may configure a
loop; a generated or mutated template starts at maturity ``candidate`` and
cannot run until validation passes and an explicit admission marks it
``registered`` — never by the generator itself (no self-promotion).
"""
from __future__ import annotations

from ..loop.recursive_loop import (FRAMEWORKS, MODES, INTERNAL_MODE_NAMES,
                                   LOGICAL_KINDS,
                                   LOOP_CONDITIONS, LoopConfig,
                                   default_loop_condition,
                                   normalize_exit_condition)

_FROM_INTERNAL = {v: k for k, v in INTERNAL_MODE_NAMES.items()}

#: the built-in library (§5) — all registered; the last two show the candidate
#: lane (a generated and a mutated template awaiting evidence).
TEMPLATE_LIBRARY = (
    {"template_id": "reference_nine_step", "framework": "nine_step",
     "steps": (), "maturity": "registered",
     "description": "The reference practitioner loop: reconstruct state, "
                    "standardize the open task, reconcile goal, assess "
                    "evidence, decide next, choose how, act, verify, capture "
                    "learning, commit."},
    {"template_id": "atomic_code_only", "framework": "custom",
     "steps": ("act",), "allowed_modes": ("code_only",),
     "maturity": "registered",
     "description": "The thinnest loop (live-runtime directive): one "
                    "deterministic act, one iteration, zero model calls — "
                    "full loop identity, telemetry, and fallback seams."},
    {"template_id": "gated_checklist", "framework": "custom",
     "steps": ("inspect", "gate"), "allowed_modes": ("code_only",),
     "maturity": "registered",
     "description": "The colleague's checklist: inspect typed facts against "
                    "ordered deterministic checks, then gate. A clean gate "
                    "completes with zero model calls; a failed blocking item "
                    "records the gate firing and escalates to a spawned Loop "
                    "whose mode the parent's delegation authority decides."},
    {"template_id": "guarded_irreversible_effect", "framework": "custom",
     "steps": ("authorize", "act", "verify"),
     "allowed_modes": ("code_only",), "maturity": "registered",
     "description": "External-effect lane: an explicit AUTHORIZE beat "
                    "fails closed before the irreversible act; verify "
                    "checks the effect's own evidence."},
    {"template_id": "smoke_solve_six_beat", "framework": "custom",
     "steps": ("orient", "research", "decide", "act", "verify", "commit"),
     "maturity": "registered",
     "description": "The solve lane's six-beat variation of the standard "
                    "nine-step loop: orient → research → decide → act → "
                    "verify → commit (registered 2026-08-24; previously an "
                    "inline tuple — variations are TEMPLATES, not literals)."},
    {"template_id": "compact_five_beat", "framework": "five_step",
     "steps": (), "maturity": "registered",
     "description": "LOAD → CHOOSE → ACT → CHECK → COMMIT."},
    {"template_id": "research_intensive", "framework": "custom",
     "steps": ("orient", "research", "research", "compare", "research",
               "decide", "act", "verify"),
     "maturity": "registered",
     "description": "Repeat research before deciding; for informational gaps."},
    {"template_id": "build_test_repair", "framework": "custom",
     "steps": ("understand_minimum", "prototype", "run", "diagnose",
               "research_failure", "repair", "rerun", "generalize"),
     "maturity": "registered",
     "description": "Act first, then diagnose and repair; for buildable gaps."},
    {"template_id": "hypothesis_experiment", "framework": "custom",
     "steps": ("observe", "hypothesize", "experiment", "analyze", "revise"),
     "maturity": "registered",
     "description": "The scientific loop; for causal or measurement questions."},
    {"template_id": "adversarial_review", "framework": "custom",
     "steps": ("collect_claims", "attack", "verify_survivors", "report"),
     "maturity": "registered",
     "description": "Try to refute before accepting; for verification passes."},
    {"template_id": "continuous_improvement", "framework": "custom",
     "logical_kind": "search_improvement",
     "steps": ("load_history", "audit_intelligence", "mine", "rank",
               "engineer_candidate", "stage", "compare"),
     "maturity": "registered",
     "description": "The Self-Improvement Loop: review run history and "
                    "intelligence, rank opportunities, and stage candidates "
                    "without promoting them."},
    {"template_id": "context_intelligence_seed", "framework": "custom",
     "logical_kind": "search_improvement",
     "steps": ("scope_domain", "audit_coverage", "map_roles_and_work",
               "define_research_questions", "generate_context",
               "classify", "deduplicate", "verify", "stage", "report"),
     "maturity": "registered",
     "description": "Seed one domain with categorized Context Intelligence "
                    "candidates. Research remains source-bound and every "
                    "output stays a candidate."},
    {"template_id": "legacy_assimilation", "framework": "custom",
     "steps": ("snapshot", "inventory", "map_capabilities", "search_existing",
               "choose_disposition", "generate_candidates", "quarantine_test"),
     "maturity": "registered",
     "description": "Assimilate a legacy codebase; source stays a String "
                    "until admitted."},
    {"template_id": "minimal_code_only", "framework": "five_step",
     "steps": (), "allowed_modes": ("code_only",), "maturity": "registered",
     "description": "Deterministic-only five-beat; zero semantic calls."},
    {"template_id": "external_harness_worker", "framework": "custom",
     "steps": ("authorize", "dispatch", "observe", "verify", "integrate"),
     "allowed_modes": ("non_deterministic",), "maturity": "registered",
     "description": "Delegate ONE bounded assignment to an external coding "
                    "harness (OpenCode, Codex, Claude Code, OpenHands, Goose, "
                    "an ACP agent) and treat it as what it is: a model-backed "
                    "loop whose interior we cannot see. AUTHORIZE fails "
                    "closed before dispatch because handing a workspace to an "
                    "external agent is an irreversible external effect; "
                    "OBSERVE ingests its transcript as evidence, not as "
                    "truth; VERIFY tests the result independently before "
                    "INTEGRATE. The worker never gains authority the parent "
                    "did not hold."},
    {"template_id": "custom_user_supplied", "framework": "custom",
     "steps": ("orient", "act", "verify"), "maturity": "registered",
     "description": "The user's own bounded ordering, validated like any "
                    "other template."},
    {"template_id": "generated_candidate", "framework": "custom",
     "steps": ("orient", "probe", "probe", "decide", "act", "verify"),
     "maturity": "candidate",
     "description": "A generated template: valid shape, NOT yet admitted — "
                    "it cannot configure a loop until registered."},
    {"template_id": "mutated_experimental", "framework": "custom",
     "steps": ("orient", "act", "diagnose", "act", "verify"),
     "maturity": "candidate",
     "description": "A mutation of build_test_repair under experiment."},
)

_MAX_STEPS = 200        # bounded repetition: a template can never be unbounded


def validate_template(body: dict) -> dict:
    """Validate one template String (§5 gates that apply at the shape level).
    Returns {valid, violations}; never raises on bad content — the report IS
    the result."""
    v = []
    fw = body.get("framework", "")
    if fw not in FRAMEWORKS:
        v.append(f"framework {fw!r} not in {FRAMEWORKS}")
    steps = tuple(body.get("steps") or ())
    if fw == "custom" and not steps:
        v.append("a custom template needs steps (no orphan shape)")
    if fw in ("nine_step", "five_step") and steps:
        v.append(f"{fw} carries its own steps; template must not override")
    if len(steps) > _MAX_STEPS:
        v.append(f"{len(steps)} steps exceeds the bound {_MAX_STEPS}")
    if any(not isinstance(s, str) or not s for s in steps):
        v.append("every step must be a non-empty string")
    loop_condition = body.get("loop_condition", "")
    if loop_condition and loop_condition not in LOOP_CONDITIONS:
        v.append(f"loop_condition {loop_condition!r} not in {LOOP_CONDITIONS}")
    if fw in FRAMEWORKS and loop_condition and loop_condition != \
            default_loop_condition(fw):
        v.append(
            f"framework {fw!r} requires loop_condition "
            f"{default_loop_condition(fw)!r}")
    try:
        normalize_exit_condition(body.get("exit_condition", ""))
    except ValueError as exc:
        v.append(str(exc))
    logical_kind = body.get("logical_kind", "execution")
    if logical_kind not in LOGICAL_KINDS:
        v.append(f"logical_kind {logical_kind!r} not in {LOGICAL_KINDS}")
    for m in body.get("allowed_modes", ()):
        if _FROM_INTERNAL.get(m, m) not in MODES:
            v.append(f"mode {m!r} unknown")
    if not body.get("template_id"):
        v.append("a template needs a template_id")
    return {"valid": not v, "violations": v}


def config_from_template(body: dict, *, power: str = "standard",
                         max_depth: "int | None" = None) -> LoopConfig:
    """Build the runnable LoopConfig from a VALID, ADMITTED template.  A
    candidate template is refused — it cannot run until registered (the
    evidence gate; generators never admit their own output)."""
    report = validate_template(body)
    if not report["valid"]:
        raise ValueError("invalid template: " + "; ".join(report["violations"]))
    if body.get("maturity", "candidate") == "candidate":
        raise ValueError(f"template {body.get('template_id')!r} is a CANDIDATE "
                         "— it cannot configure a loop until admitted")
    modes = tuple(_FROM_INTERNAL.get(m, m)
                  for m in body.get("allowed_modes", MODES)) or MODES
    return LoopConfig(framework=body["framework"],
                      logical_kind=body.get("logical_kind", "execution"),
                      replay_guarantee=body.get("replay_guarantee",
                                                "event_equivalent"),
                      allowable_modes=modes,
                      preferred_modes=tuple(m for m in
                                            ("deterministic", "hybrid",
                                             "non_deterministic")
                                            if m in modes),
                      power=power,
                      custom_steps=tuple(body.get("steps") or ()),
                      max_depth=max_depth,
                      loop_condition=body.get("loop_condition", ""),
                      exit_condition=body.get("exit_condition", ""))


def template_records() -> list:
    """The library as searchable String records for the one store."""
    from ..core.store_serve import StoreRecord
    from ..core.facets import string_facets
    return [StoreRecord(
        record_id=f"looptmpl.{t['template_id']}", kind="strategy",
        title=f"Loop template: {t['template_id']}: {t['description'][:60]}",
        body={**{k: (list(v) if isinstance(v, tuple) else v)
                 for k, v in t.items()},
              "loop_condition": t.get("loop_condition")
                  or default_loop_condition(t["framework"]),
              "exit_condition": normalize_exit_condition(
                  t.get("exit_condition", "")),
              "role": "loop_template",
              "facets": string_facets(category="loop_template",
                                      subcategory=t["framework"],
                                      context_type="template",
                                      scope="package",
                                      lifecycle=t["maturity"],
                                      provenance="loop_template_library")},
        tags=("loop_template", t["framework"], t["maturity"]),
        tier="core" if t["maturity"] == "registered" else "experimental")
            for t in TEMPLATE_LIBRARY]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    lib = {t["template_id"]: t for t in TEMPLATE_LIBRARY}

    # 1. the full §5 library exists and every entry validates.
    required = {"reference_nine_step", "compact_five_beat", "research_intensive",
                "build_test_repair", "hypothesis_experiment",
                "adversarial_review", "continuous_improvement",
                "context_intelligence_seed",
                "legacy_assimilation", "minimal_code_only",
                "custom_user_supplied", "generated_candidate",
                "mutated_experimental"}
    invalid = [t["template_id"] for t in TEMPLATE_LIBRARY
               if not validate_template(t)["valid"]]
    check("registered_and_candidate_template_library_all_valid",
          required <= set(lib) and not invalid,
          f"{len(lib)} templates; invalid: {invalid}")

    # 2. an admitted template configures a runnable loop with a DIFFERENT order.
    cfg = config_from_template(lib["build_test_repair"], power="deep")
    from ..loop.recursive_loop import Loop
    r = Loop("fix the failing job", cfg).run()
    check("custom_template_runs_a_different_order",
          r.steps_run == 8 and r.stopped == "done"
          and cfg.custom_steps[0] == "understand_minimum",
          "act-first template executed end to end — nine_step is not a law")

    # 3. a CANDIDATE template cannot configure a loop (no self-admission).
    refused = False
    try:
        config_from_template(lib["generated_candidate"])
    except ValueError:
        refused = True
    check("candidate_template_cannot_run_until_admitted", refused)

    # 4. orphan, unbounded, and mismatched-condition templates fail validation.
    bad1 = validate_template({"template_id": "x", "framework": "custom",
                              "steps": ()})
    bad2 = validate_template({"template_id": "x", "framework": "open",
                              "loop_condition": "steps_remain"})
    bad3 = validate_template({"template_id": "x", "framework": "custom",
                              "steps": tuple(f"s{i}" for i in range(500))})
    check("orphan_unbounded_and_mismatched_conditions_refused",
          not bad1["valid"] and not bad2["valid"] and not bad3["valid"],
          "no steps / wrong open condition / 500 steps all refused")

    current = dict(lib["atomic_code_only"],
                   exit_condition="accepted_success")
    invalid = dict(current, exit_condition="whenever")
    current_cfg = config_from_template(current)
    check("current_exit_input_validates_and_unknowns_fail_closed",
          current_cfg.exit_condition == "accepted_success"
          and current_cfg.loop_condition == "steps_remain"
          and not validate_template(invalid)["valid"],
          "current conditions are stored; unknown values are refused")

    # 5. templates are searchable Strings through the one store, faceted.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=template_records())
    hits = store.search("adversarial review refute claims", kind="strategy")
    check("templates_are_searchable_faceted_strings",
          hits["hits"]
          and hits["hits"][0]["record_id"] == "looptmpl.adversarial_review"
          and hits["hits"][0]["facets"].get("category") == "loop_template",
          "the library flows through the one search DAG with facets")

    # 6. minimal_code_only yields a deterministic-only config (a hard mode gate).
    cfg6 = config_from_template(lib["minimal_code_only"])
    check("code_only_template_restricts_modes",
          cfg6.allowable_modes == ("deterministic",)
          and cfg6.preferred_modes == ("deterministic",))

    # 7. improvement templates bind the no-self-promotion logical kind.
    improve_cfg = config_from_template(lib["continuous_improvement"])
    seed_cfg = config_from_template(lib["context_intelligence_seed"])
    check("improvement_templates_bind_search_improvement_identity",
          improve_cfg.logical_kind == "search_improvement"
          and seed_cfg.logical_kind == "search_improvement")

    # 8. THE EXTERNAL-HARNESS ENVELOPE (harness-integration strategy): handing
    # a bounded assignment to OpenCode / Codex / an ACP agent is delegation to
    # a loop whose interior we cannot see.  Three laws must hold at the
    # envelope, and all three are properties of the registered template plus
    # the runtime — not of the adapter that will call it:
    #   (a) it is model-backed ONLY.  An opaque external agent may never be
    #       declared deterministic, because we cannot show it made no
    #       semantic call;
    #   (b) it keeps its OWN five beats — the runtime must not quietly lower
    #       a custom ordering back into the nine-step sequence (§3.3);
    #   (c) the delegation clamp holds: a parent whose operating policy permits
    #       only deterministic spawned modes cannot spawn it.
    from .recursive_loop import Loop, LoopConfig, LoopError
    ext = lib["external_harness_worker"]
    cfg7 = config_from_template(ext)
    lp7 = Loop("delegate to an external harness", cfg7)
    parent_det = Loop("deterministic parent", LoopConfig(
        framework="five_step", allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",)))
    escalated = False
    try:
        parent_det.spawn("delegate to an external harness", cfg7)
    except LoopError:
        escalated = True
    check("external_harness_worker_is_opaque_bounded_and_clamped",
          cfg7.allowable_modes == ("non_deterministic",)
          and lp7.steps() == ("authorize", "dispatch", "observe", "verify",
                              "integrate")
          and ext["steps"][0] == "authorize"      # fails closed BEFORE dispatch
          and escalated,
          "model-backed only, five beats kept, deterministic parent refused")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

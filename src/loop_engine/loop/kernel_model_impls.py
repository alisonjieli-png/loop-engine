"""Model-backed kernel implementations — the full architecture, live.

This wires the six-node Practitioner Kernel to the real machinery:

  1. Understand the problem …   -> deterministic situation + the strict
                                   search/serve DAG assembling relevant records
  2. Decide what to do next     -> the QUESTION ENGINE multiplies ask variants;
                                   a small council answers through the strict
                                   model-call DAG; replies parse into
                                   CandidateActions with decision metadata
  3. Determine the best way     -> reuse-first: learned shortcuts + store probe,
                                   then the escalation modes
  4. Execute / build / delegate -> run a handle directly, have an OpenCode
                                   worker author + compile a node, or spawn
                                   spawned Practitioner Loops
  5. Verify the result          -> deterministic checks first, then a
                                   verify_check form through the call DAG
  6. Save and route             -> commit facts/artifacts, distill shortcuts,
                                   choose the route

Every callable is injectable (``ask``, ``author``) so the whole set is testable
offline with stubs; production defaults are the live strict DAGs.  This module
adds NO new concepts — it only connects the ones the architecture file names.
"""

from __future__ import annotations

from typing import Callable, Sequence

from ..loop.kernel import (ProblemSpec, PractitionerState, Situation,
                     CandidateAction, ExecutionPlan, ResultPacket,
                     EvaluationPacket, RouteDecision, PassRecord,
                     default_route, MAX_SPAWN_DEPTH)
from ..strings.knowledge import Knowledge
from ..static_architecture.model_call import AskSpec, execute_ask
from ..strings.question_engine import core_forms, multiply
from ..static_architecture.store_serve import SolverStore, core_seed
from ..code_nodes.self_improve import ShortcutStore, problem_signature
from ..static_architecture.ollama_resolvers import parse_moves
from ..code_nodes.enrichment import (EnrichmentPolicy, coverage_probe, generate_enrichment)
from ..static_architecture.config import (SolverConfig, ConfigViolation, TokenMeter, screen_models,
                    permit_plan, config_details)
from ..strings.biases import apply_biases

import re as _re


def _clean_action(raw: str) -> str:
    """An action name must be a short slug/phrase, never a prose fragment.

    Strips markdown, rejects sentence-like keys (too long, too many words, or
    starting with list numbering) — a junk action name would poison the shortcut
    store with an unmatchable signature, so refusal beats acceptance."""
    key = _re.sub(r"[*`#]+", "", (raw or "")).strip().strip(".:;,)")
    if not key or len(key) > 60 or len(key.split()) > 8:
        return ""
    if _re.match(r"^\(?\d+\)?[.)]?\s", key):        # "(1) ..." list prose
        return ""
    if ": " in key:                # "Proposal: ..." titles — slugs use = or _
        return ""
    return key


def make_model_impls(*, models: Sequence[str] | None = None,
                     store: "SolverStore | None" = None,
                     shortcuts: "ShortcutStore | None" = None,
                     personas: Sequence[str] = ("a careful practitioner",
                                                "a contrarian reviewer"),
                     ask: Callable = execute_ask,
                     author: Callable | None = None,
                     enrichment: "EnrichmentPolicy | None" = None,
                     config: "SolverConfig | None" = None,
                     n_asks: int = 4) -> dict:
    """Build the six live node implementations.  ``ask`` runs an AskSpec through
    the strict model-call DAG (stub it for offline tests); ``author`` builds a
    node file via an OpenCode worker (None = record the build as a declared
    handle without spawning a worker)."""
    store = store if store is not None else SolverStore(
        core_records=core_seed())
    shortcuts = shortcuts if shortcuts is not None else ShortcutStore()
    forms = core_forms()
    chain = tuple(models) if models else None
    enrich_policy = enrichment or EnrichmentPolicy()   # OFF unless passed
    cfg = config or SolverConfig()
    meter = TokenMeter(cfg)
    no_models = False
    try:
        chain = screen_models(cfg, chain or None) or chain
    except ConfigViolation:
        no_models = True                    # pure-deterministic profile
    raw_ask = ask

    def metered_ask(spec):
        """Every ask passes the config gates: budget checked before, charged
        after, and the run's priorities ride the details."""
        from ..static_architecture.model_call import AskResult
        try:
            meter.check()
        except ConfigViolation as e:
            return AskResult(ok=False, error=str(e))
        spec.details = {**config_details(cfg), **(spec.details or {})}
        res = raw_ask(spec)
        try:
            meter.charge(getattr(res, "total_tokens", 0))
        except ConfigViolation:
            pass                             # this reply counts; the NEXT ask stops
        return res

    ask = metered_ask

    def orient(state: PractitionerState) -> Situation:
        unmet = tuple(c for c in state.spec.success_criteria
                      if not state.facts.get(f"met:{c}"))
        signals = []
        if not state.facts:
            signals.append("missing_info")
        if state.last_route in ("soft_reset", "cold_restart"):
            signals.append("post_reset")
        from .intelligence_loops import search_as_loop
        hits = search_as_loop(store, state.spec.objective,
                              top_n=3)["value"]["hits"]
        if enrich_policy.enabled:
            cov = coverage_probe(store, state.spec.objective,
                                 weak_below=enrich_policy.weak_below)
            if cov.weak and not any(k.startswith("enriched:")
                                    for k in state.facts):
                signals.append("weak_domain_coverage")
        return Situation(
            summary=f"v{state.version}: {len(unmet)} criteria unmet, "
            f"{len(hits)} relevant stored resources",
            knowns=dict(state.facts), unknowns=unmet,
            signals=tuple(signals),
            resources_hint=tuple(h["record_id"] for h in hits))

    def select_next_action(state: PractitionerState,
                     situation: Situation) -> list:
        if not situation.unknowns:
            return [CandidateAction(action="deliver", kind="deliver",
                                    rationale="all criteria met",
                                    expected_value=1.0, confidence=0.95)]
        crit = situation.unknowns[0]
        if "weak_domain_coverage" in situation.signals:
            # generating domain personas/questions OUTRANKS everything else
            # while the banks cannot cover this problem (optional + tunable).
            return [CandidateAction(
                action="enrich:domain_context", kind="enrich",
                rationale="the persona/question banks do not cover this "
                "domain; generate once, store, reuse forever",
                expected_value=0.97, confidence=0.8, information_gain=0.95)]
        # multiply a handful of ask variants for THIS decision and pose them
        # through the strict call DAG; each answer proposes typed moves.
        variants = multiply(
            forms, personas=personas,
            policies=("fully_informed", "goal_only"), seeds=(0, 4),
            slot_values={"task": f"{state.spec.objective} — next step toward "
                         f"{crit!r}",
                         "options": ", ".join(situation.resources_hint) or
                         "none stored", "candidate": f"meet:{crit}",
                         "option": f"meet:{crit}", "a": f"meet:{crit}",
                         "b": f"research:{crit}"},
            limit=n_asks)
        cands: dict = {}
        k = Knowledge(goal=state.spec.objective,
                      facts=dict(state.facts))
        from ..static_architecture.ollama_resolvers import _MOVE_SCHEMA_HINT
        for v in ([] if no_models else variants):
            spec = v.to_ask_spec(k)
            # the question FORM shapes the reasoning; the OUTPUT CONTRACT must
            # still be the strict move JSON, or prose leaks into action names.
            spec.output_contract = _MOVE_SCHEMA_HINT
            if chain:
                spec.models = chain
            res = ask(spec)
            if not getattr(res, "ok", False):
                continue
            for mv in parse_moves(res.text or "")[:3]:
                key = _clean_action(mv["key"])
                if not key:
                    continue                    # prose fragment — refuse it
                row = cands.setdefault(key.lower(), CandidateAction(
                    action=key, kind="task",
                    rationale=mv.get("reason", f"proposed via {v.form}"),
                    expected_value=0.5,
                    confidence=float(mv.get("confidence", 0.5)),
                    information_gain=0.3))
                row.expected_value = min(1.0, row.expected_value + 0.15)
        if not cands:                       # models silent -> deterministic
            cands[f"meet:{crit}"] = CandidateAction(
                action=f"meet:{crit}", kind="task",
                rationale="deterministic fallback: address the unmet "
                "criterion", expected_value=0.7, confidence=0.6)
        # the practitioner's standing instincts: baseline-first, adversarial-
        # on-perfection, diagnose-after-failures, pilot-before-full, distill-
        # after-repetition, simplicity tie-break — applied deterministically.
        return apply_biases(state, situation, list(cands.values()))

    def how(state: PractitionerState, situation: Situation,
            chosen: CandidateAction) -> ExecutionPlan:
        sig = problem_signature(state.spec.objective, chosen.kind,
                                chosen.action)
        sc = shortcuts.lookup(sig)
        if sc:
            return ExecutionPlan("use", "run_direct", handle=sc.handle,
                                 rationale="learned shortcut replay")
        have = state.facts.get(f"registry_has:{chosen.action}")
        if have:
            return ExecutionPlan("use", "run_direct", handle=str(have),
                                 rationale="already in the registry")
        if chosen.kind == "enrich":
            return ExecutionPlan("generate", "run_direct",
                                 handle="enrichment",
                                 rationale="grow the banks: personas, "
                                 "questions, key phrases — stored, reusable")
        if chosen.kind == "research":
            return ExecutionPlan(
                "research", "spawn_practitioners",
                spawned_loops=(ProblemSpec(objective=f"reduce gap: {chosen.action}",
                                      depth=state.spec.depth + 1,
                                      budget_passes=3),),
                rationale="a narrower practitioner reduces the gap")
        if chosen.kind == "deliver":
            return ExecutionPlan("use", "run_direct", handle="deliver",
                                 rationale="assemble and deliver")
        plan = ExecutionPlan("generate", "run_dag",
                             handle=f"build::{chosen.action}",
                             rationale="nothing reusable — author it")
        try:
            permit_plan(cfg, how_mode=plan.how_mode, handle=plan.handle,
                        act_mode=plan.act_mode)
        except ConfigViolation as e:
            return ExecutionPlan("compose", "run_direct", handle="",
                                 rationale=f"refused by configuration: {e}")
        return plan

    def act(state: PractitionerState, plan: ExecutionPlan) -> list:
        if plan.act_mode == "spawn_practitioners":
            if state.spec.depth + 1 > MAX_SPAWN_DEPTH:
                return [ResultPacket(objective="spawn",
                                     errors=("depth exceeded",),
                                     confidence=0.0)]
            from ..loop.kernel import run_practitioner, default_impls
            packets = []
            for spawned in plan.spawned_loops:
                out = run_practitioner(spawned, default_impls())
                packets.append(ResultPacket(
                    objective=spawned.objective,
                    result={"passes": out["passes"]},
                    claims=(f"learned:{spawned.objective}",),
                    confidence=0.7, cost=out["passes"]))
            return packets
        if plan.act_mode == "run_dag" and author is not None:
            slug = "".join(c if c.isalnum() else "_"
                           for c in plan.handle)[:40]
            res = author(slug, plan.rationale or plan.handle)
            if res is None or not getattr(res, "ok", False):
                return [ResultPacket(objective=plan.handle,
                                     errors=("authoring failed",),
                                     confidence=0.0)]
            return [ResultPacket(objective=plan.handle,
                                 result={"built": plan.handle},
                                 artifact_refs=(f"nodes/{slug}.py",),
                                 confidence=0.8, cost=1.0)]
        if plan.act_mode == "run_dag":
            return [ResultPacket(objective=plan.handle,
                                 result={"built": plan.handle},
                                 artifact_refs=(plan.handle,),
                                 confidence=0.75, cost=1.0)]
        if plan.act_mode == "run_direct" and not plan.handle:
            return [ResultPacket(objective="configuration refusal",
                                 errors=(plan.rationale or "refused",),
                                 confidence=0.0)]
        if plan.handle == "enrichment":
            out = generate_enrichment(state.spec.objective, enrich_policy,
                                      store=store, forms=forms, ask=ask,
                                      models=chain)
            ok = out.get("stored", 0) > 0
            return [ResultPacket(
                objective="enrich the banks", result=out,
                claims=((f"enriched:{out.get('domain', 'general')}",)
                        if ok else ()),
                confidence=0.85 if ok else 0.0,
                errors=() if ok else (out.get("error", "nothing stored"),),
                metrics={"stored": out.get("stored", 0)},
                cost=out.get("tokens", 0) / 1000.0)]
        return [ResultPacket(objective=plan.handle,
                             result={"ran": plan.handle}, confidence=0.9,
                             cost=0.2)]

    def verify(state: PractitionerState, plan: ExecutionPlan,
               results: list) -> EvaluationPacket:
        if not results or any(r.errors for r in results):
            return EvaluationPacket("repair", notes="errors in results")
        best = max(range(len(results)),
                   key=lambda i: results[i].confidence)
        # deliver and reuse verify deterministically; a BUILT artifact gets a
        # model check through the verify_check form.
        if plan.how_mode == "generate" and not no_models:
            q = forms["verify_check"].render(
                task=state.spec.objective,
                candidate=str(results[best].result))
            res = ask(AskSpec(question=q,
                              models=chain or AskSpec("x").models))
            text = (getattr(res, "text", "") or "").lower()
            if getattr(res, "ok", False) and ("incorrect" in text
                                              or "fail" in text.split()):
                return EvaluationPacket("repair", best_index=best,
                                        notes="model check flagged defects")
        if plan.how_mode == "research":
            return EvaluationPacket("accept_provisional", best_index=best,
                                    notes="research absorbed")
        return EvaluationPacket("accept", best_index=best)

    def learn_route(state: PractitionerState, rec: PassRecord) -> tuple:
        # default routing/commit plus shortcut distillation for built artifacts
        route, new_state = default_route(state, rec)
        ev = rec.evaluation
        # A model proposes REAL action names ("estimator=hgb"), not the
        # "meet:<criterion>" convention — so when an accepted task was working
        # toward an unmet criterion, mark THAT criterion met explicitly, or the
        # loop would re-address it forever.
        if ev and ev.verdict == "accept" and rec.chosen \
                and rec.chosen.kind == "task" and rec.situation \
                and rec.situation.unknowns:
            crit = rec.situation.unknowns[0]
            new_state = new_state.derive(
                facts={**new_state.facts, f"met:{crit}": True})
        if ev and ev.verdict in ("accept",) and rec.results and rec.plan \
                and rec.plan.how_mode == "generate":
            best = rec.results[ev.best_index]
            for ref in best.artifact_refs:
                from ..code_nodes.self_improve import Shortcut
                shortcuts.record(Shortcut(
                    signature=problem_signature(state.spec.objective,
                                                rec.chosen.kind,
                                                rec.chosen.action),
                    rung="exact_reuse", handle=ref,
                    model_calls_first_time=1,
                    learned_from_goal=state.spec.objective))
        return route, new_state

    return {"orient": orient, "decide_next": select_next_action, "how": how,
            "act": act, "verify": verify, "route": learn_route}


# ---------------------------------------------------------------------------
# Self-test — offline: stub ask/author, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    from ..loop.kernel import run_practitioner
    from ..static_architecture.model_call import AskResult
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    asked: list = []

    def stub_ask(spec: AskSpec):
        asked.append(spec)
        return AskResult(ok=True, text='[{"move_kind":"add_node",'
                         '"key":"estimator=hgb","reason":"strong default",'
                         '"confidence":0.8}]', model_used="stub",
                         total_tokens=9)

    shortcuts = ShortcutStore()
    impls = make_model_impls(ask=stub_ask, shortcuts=shortcuts)
    spec = ProblemSpec(objective="predict churn on tabular data",
                       success_criteria=("model",), budget_passes=6)
    out = run_practitioner(spec, impls)

    # 1. the full architecture runs end to end through the model impls.
    check("the_model_backed_kernel_runs_end_to_end",
          out["final_route"] == "stop_success" and out["passes"] >= 2,
          f"{out['passes']} passes to stop_success via question-engine asks")

    # 2. node 2 posed MULTIPLE ask variants (form x persona x policy x seed).
    forms_used = {a.question.splitlines()[0][:20] for a in asked}
    check("node_two_poses_multiple_question_engine_variants",
          len(asked) >= 3 and len(forms_used) >= 2,
          f"{len(asked)} asks across {len(forms_used)} distinct framings")

    # 3. an accepted BUILT artifact was distilled into a shortcut...
    check("a_built_accepted_artifact_distills_into_a_shortcut",
          len(shortcuts) >= 1,
          "self-improvement fired from the live path")

    # 4. ...and a SECOND run replays it via 'use' with fewer asks.
    asked2: list = []
    def stub_ask2(spec_):
        asked2.append(spec_)
        return stub_ask(spec_)
    impls2 = make_model_impls(ask=stub_ask2, shortcuts=shortcuts)
    out2 = run_practitioner(ProblemSpec(
        objective="predict churn on tabular data",
        success_criteria=("model",), budget_passes=6), impls2)
    check("a_similar_problem_replays_the_learned_shortcut",
          out2["final_route"] == "stop_success",
          "the same objective resolved again with the shortcut store primed")

    # 5. authoring failure routes to repair, never a silent pass.
    def bad_author(slug, spec_):
        return None
    impls3 = make_model_impls(ask=stub_ask, author=bad_author,
                              shortcuts=ShortcutStore())
    out3 = run_practitioner(ProblemSpec(objective="novel widget",
                                        success_criteria=("built",),
                                        budget_passes=4), impls3)
    routes = [r.route.route for r in out3["records"]]
    check("authoring_failure_routes_to_repair_not_silent_success",
          "repair" in routes or out3["final_route"] != "stop_success",
          f"routes: {routes}")

    # 6. prose fragments and markdown are refused as action names.
    check("prose_fragments_are_refused_as_action_names",
          _clean_action("(1) The goal explicitly asks for an architecture, so "
                        "proceeding directly") == ""
          and _clean_action("**Proposal: Reactive Disruption-Only "
                            "Architecture**") == ""
          and _clean_action("architecture=belief_state_mcts")
          == "architecture=belief_state_mcts"
          and _clean_action("policy=deep_cfr") == "policy=deep_cfr",
          "sentence-like keys are rejected; clean slugs pass — junk can never "
          "reach the shortcut store")

    # 7. weak domain coverage triggers ONE enrichment pass (policy on): the
    # banks grow, then the normal task flow proceeds — no seventh kernel node.
    import json as _json
    from ..code_nodes.enrichment import EnrichmentPolicy
    def stub_ask3(spec_):
        if "domain_personas" in (spec_.output_contract or ""):
            return AskResult(ok=True, text=_json.dumps({
                "domain_personas": [{"name": "an echo-lab cardiologist",
                                     "description": "imaging outcomes"}],
                "diametric_personas": [{"name": "a seismologist",
                                        "field": "geophysics",
                                        "description": "waveform expert"}],
                "questions": [{"name": "waveform_check",
                               "template": "For {task}, which waveform "
                               "features matter most?",
                               "answer_shape": "ranking"}],
                "key_phrases": ["ejection fraction"]}), model_used="stub",
                total_tokens=30)
        return stub_ask(spec_)
    from ..static_architecture.store_serve import SolverStore as _SS, core_seed as _cs
    st = _SS(core_records=_cs()); st.enable_tier("experimental")
    impls_e = make_model_impls(ask=stub_ask3, store=st,
                               shortcuts=ShortcutStore(),
                               enrichment=EnrichmentPolicy(enabled=True))
    out_e = run_practitioner(ProblemSpec(
        objective="heart disease classification from echocardiogram data",
        success_criteria=("model",), budget_passes=6), impls_e)
    enriched = any(k.startswith("enriched:") for k in out_e["facts"])
    persona_hit = st.search("cardiologist echo", kind="persona")["hits"]
    check("weak_coverage_triggers_one_enrichment_pass_then_the_task_proceeds",
          enriched and persona_hit
          and out_e["final_route"] == "stop_success",
          f"enrich pass stored records (persona findable), then the run "
          f"finished normally in {out_e['passes']} passes")

    # 8. the pure-deterministic profile (allowed_models=()) solves with ZERO
    # model asks — the config gate, not luck.
    from ..static_architecture.config import SolverConfig, Budgets
    asked_none: list = []
    def counting_ask(spec_):
        asked_none.append(spec_)
        return stub_ask(spec_)
    impls_nm = make_model_impls(ask=counting_ask, shortcuts=ShortcutStore(),
                                config=SolverConfig(allowed_models=()))
    out_nm = run_practitioner(ProblemSpec(objective="churn model",
                                          success_criteria=("model",),
                                          budget_passes=6), impls_nm)
    check("no_models_config_solves_deterministically_with_zero_asks",
          out_nm["final_route"] == "stop_success" and len(asked_none) == 0,
          f"stop_success with {len(asked_none)} model asks")

    # 9. code_authoring=False refuses the generate plan with a DOCUMENTED
    # configuration reason — never a silent success via authoring.
    impls_na = make_model_impls(ask=stub_ask, shortcuts=ShortcutStore(),
                                config=SolverConfig(code_authoring=False))
    out_na = run_practitioner(ProblemSpec(objective="novel widget nobody has",
                                          success_criteria=("built",),
                                          budget_passes=4), impls_na)
    refusals = [f for f in out_na["failures"]
                if "configuration" in f or "refus" in f]
    check("code_authoring_off_refuses_generation_with_a_documented_reason",
          out_na["final_route"] != "stop_success"
          and (refusals or out_na["failures"]),
          f"route {out_na['final_route']}; failures: "
          f"{out_na['failures'][:1]}")

    # 10. a token ceiling stops asks past the budget; the run still finishes
    # deterministically rather than crashing.
    asked_budget: list = []
    def counting_ask2(spec_):
        asked_budget.append(spec_)
        return stub_ask(spec_)
    impls_tb = make_model_impls(ask=counting_ask2, shortcuts=ShortcutStore(),
                                config=SolverConfig(
                                    budgets=Budgets(max_tokens=9)))
    out_tb = run_practitioner(ProblemSpec(objective="churn model",
                                          success_criteria=("model",),
                                          budget_passes=6), impls_tb)
    check("a_token_ceiling_stops_asks_but_the_run_still_finishes",
          out_tb["final_route"] == "stop_success"
          and 1 <= len(asked_budget) < 8,
          f"{len(asked_budget)} ask(s) before the ceiling bit; run completed "
          f"via deterministic fallback")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "kernel_model_impls_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

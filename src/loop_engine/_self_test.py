"""Deterministic self-test aggregator — the ONE test entrypoint (no model, no network).

Owns: folding every module's self_test() into a single suite via
_FOLDED_SUBMODULE_TESTS (module paths resolved through the architecture map).
Belongs to: root plumbing.  Never: skipped or expected-failure tests — the
conformance scanner fails on any such marker in this file."""

from __future__ import annotations

from .strings.frame import AskFrame
from .strings.knowledge import Knowledge
from .loop.moves import move, answer, WhatIsNextAnswer, MOVE_TYPES
from .loop.resolvers import WhatIsNextResolver, RESOLVER_CATEGORIES
from .loop.registry import ResolverRegistry
from .loop.loop import SolverCell, Practitioner, ensemble_answers
from .strings.knowledge_state import (Claim, Unknown, Contradiction, EpistemicState,
                              KnowledgeDelta)
from .loop.decision_need import detect_decision_need
from .loop.builtin_resolvers import register_builtins, make_fingerprint_resolver
from .loop.regimes import (register_library, LIBRARY_SPECS, make_single_model_regime,
                      make_council_regime, make_research_regime,
                      make_recall_resolver, make_solved_route_replay)


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # --- resolver fns ---
    def rule_resolver(k: Knowledge):
        if "no_model" in k.open_obligations:
            return answer("add_estimator_rule", "deterministic_rule",
                          [move("add_node", "estimator=hgb",
                                mechanism="graph lacks a model node",
                                confidence=0.9)], 0.9)
        return None

    def test_resolver(k: Knowledge):
        if len(k.results) < 3:
            return answer("probe_before_deciding", "test_driven",
                          [move("run_tests", "cv_probe:5fold",
                                mechanism="too few results to choose",
                                confidence=0.8)], 0.8)
        return None

    def council_resolver(k: Knowledge):
        return answer("model_council", "llm_council",
                      [move("add_node", "estimator=lightgbm", confidence=0.75)],
                      0.75)

    resolvers = [
        WhatIsNextResolver("add_estimator_rule", "deterministic_rule",
                           rule_resolver),
        WhatIsNextResolver("probe_before_deciding", "test_driven",
                           test_resolver, cost=2.0),
        WhatIsNextResolver("model_council", "llm_council", council_resolver,
                           cost=40.0)]
    prac = Practitioner(confidence_bar=0.7, impact=5.0)

    # 1. deterministic rule answers cheaply, 0 model calls.
    k1 = Knowledge(goal="churn", open_obligations=("no_model",),
                   results=(1, 2, 3, 4))
    r1 = prac.step(k1, resolvers=resolvers)
    check("deterministic_rule_answers_with_zero_model_calls",
          r1.resolved and r1.category == "deterministic_rule"
          and r1.model_calls_made == 0
          and r1.answer.moves.items[0].action_kind == "add_node",
          "a firing rule answers 'add estimator' with no model call")

    # 2. answer can be run_tests, not add-node.
    k2 = Knowledge(goal="churn", open_obligations=("choose_model",),
                   results=(1,))
    r2 = prac.step(k2, resolvers=resolvers)
    check("what_is_next_can_answer_run_tests_not_only_add_node",
          r2.category == "test_driven"
          and r2.answer.moves.items[0].action_kind == "run_tests",
          "one result, no rule -> 'run a cv probe first'")

    # 3. council is the last resort (needs a high-impact decision).
    prac_hi = Practitioner(confidence_bar=0.7, impact=60.0)
    k3 = Knowledge(goal="churn", open_obligations=("tie_break",),
                   results=(1, 2, 3, 4, 5))
    r3 = prac_hi.step(k3, resolvers=resolvers)
    check("the_council_is_the_last_resort",
          r3.category == "llm_council" and r3.model_calls_made == 1,
          "only a high-impact tie-break past the cheap resolvers pays the "
          "40-cost council")

    # 4. AskFrame dimensions available deterministically + prompt render.
    frame = AskFrame(persona="data_scientist", simplified_task="classify churn",
                     time_period="2015_pre_dl", salts=("counterexample",),
                     extra={"situation": {"family": "classification"}})
    k4 = Knowledge(goal="x", frame=frame)
    check("ask_frame_dimensions_available_deterministically",
          k4.frame.persona == "data_scientist"
          and "counterexample" in k4.frame.salts
          and "data_scientist" in frame.render_prompt_preamble()
          and k4.frame.extra["situation"]["family"] == "classification",
          "persona/simplified-task/salts ride on the frame, render into a "
          "prompt, and are readable deterministically; extra dimensions survive")

    # 5. spawn sub-loops run and attach.
    def spawner(k: Knowledge):
        if k.goal == "explore":
            return answer("fan_out", "deterministic_rule",
                          [move("spawn_subloop", "start_A", confidence=0.9),
                           move("spawn_subloop", "start_B", confidence=0.9)], 0.9)
        return answer("child", "deterministic_rule",
                      [move("add_node", f"node_for={k.goal}", confidence=0.9)],
                      0.9)
    sr = [WhatIsNextResolver("fan_out", "deterministic_rule", spawner)]
    r5 = prac.step(Knowledge(goal="explore"), resolvers=sr)
    check("a_resolver_can_spawn_sub_loops_that_run_and_attach",
          len(r5.children) == 2
          and all(c.answer.moves.items[0].action_kind == "add_node"
                  for c in r5.children),
          "'spawn sub-loops A/B' runs each child question and attaches receipts")

    # 6. ensemble sums support.
    a1 = answer("g1", "hybrid", [move("add_node", "estimator=hgb", support=0.6)],
                0.8)
    a2 = answer("g2", "hybrid", [move("add_node", "estimator=hgb", support=0.5),
                                 move("add_node", "estimator=knn", support=0.4)],
                0.7)
    ens = ensemble_answers([a1, a2])
    check("ensemble_sums_support_for_agreed_moves",
          ens.items[0].action_key == "estimator=hgb"
          and abs(ens.items[0].support - 1.1) < 1e-9 and len(ens.items) == 2,
          "two answers agree on hgb -> summed support leads; knn stays present")

    # 7. determinism + move-kind validation.
    r1b = prac.step(k1, resolvers=resolvers)
    bad = False
    try:
        move("teleport", "x")
    except ValueError:
        bad = True
    check("loop_is_deterministic_and_move_kinds_validated",
          r1b.to_dict() == r1.to_dict() and bad,
          "same inputs -> identical receipt; an unknown move kind is refused")

    # 8. REGISTRY: register a new regime; the loop picks it up cheapest-first.
    reg = ResolverRegistry()
    reg.register_regime("cheap_rule", "deterministic_rule",
                        lambda k: answer("cheap_rule", "deterministic_rule",
                                         [move("add_node", "cheap", confidence=0.9)],
                                         0.9))
    reg.register_regime("dear_council", "llm_council",
                        lambda k: answer("dear_council", "llm_council",
                                         [move("add_node", "dear", confidence=0.8)],
                                         0.8), cost=40.0)
    prac_reg = Practitioner(confidence_bar=0.7, impact=5.0, registry=reg)
    r8 = prac_reg.step(Knowledge(goal="x"))
    check("a_newly_registered_regime_is_used_cheapest_first",
          r8.resolver == "cheap_rule" and r8.model_calls_made == 0
          and reg.categories()["total_resolvers"] == 2,
          "registering two regimes and stepping picks the cheap one with no "
          "model call — a new regime is a one-call addition")

    # 8b. A custom-category regime is accepted and flagged as custom.
    reg.register_regime("weird_special", "quantum_oracle_lens",
                        lambda k: None)
    cats = reg.categories()
    check("a_custom_category_regime_is_accepted_and_flagged",
          "quantum_oracle_lens" in cats["custom"]
          and "quantum_oracle_lens" not in RESOLVER_CATEGORIES,
          "a regime whose category is outside the known taxonomy is registered "
          "as a CUSTOM dimension and reported as such — the ontology stays open")

    # 9. register_builtins: plan_recipe follows steps then passes to open regime.
    reg2 = ResolverRegistry()
    register_builtins(reg2)
    open_regime = WhatIsNextResolver(
        "open_fallback", "llm_single",
        lambda k: answer("open_fallback", "llm_single",
                         [move("add_node", "open_choice", confidence=0.9)], 0.9),
        cost=1.0)
    reg2.register(open_regime)
    prac2 = Practitioner(confidence_bar=0.7, impact=10.0, registry=reg2)
    # has_model set so the blind-baseline lane (empty-graph only) does not
    # intercept; recipe of 2 steps; 1 done -> plan_recipe gives step 2 (no model).
    mid = prac2.step(Knowledge(goal="x", blueprints=("stepA", "stepB"),
                               results=(1,), facts={"has_model": True}))
    # recipe exhausted (2 done) -> plan_recipe passes, open regime fires (model).
    endk = prac2.step(Knowledge(goal="x", blueprints=("stepA", "stepB"),
                                results=(1, 2), facts={"has_model": True}))
    check("plan_recipe_follows_predefined_steps_then_yields_to_open_regime",
          mid.category == "plan_recipe" and mid.model_calls_made == 0
          and mid.answer.moves.items[0].action_key == "stepB"
          and endk.category == "llm_single",
          "a recipe drives the first steps deterministically (no model); when it "
          "runs out the open regime takes over — 'first ten steps predefined, "
          "then open-ended'")

    # 10. fingerprint_recall recalls a WON move from a list_intelligence store.
    try:
        from .loop.list_intelligence import ListIntelligence
        store = ListIntelligence()
        situation = {"family": "classification", "modality": "tabular"}
        store.harvest("method", ["gradient boosting", "knn"], situation)
        store.record_acceptance("method", "gradient boosting", situation)
        fp = make_fingerprint_resolver(store)
        k10 = Knowledge(goal="x",
                        frame=AskFrame(extra={"situation": situation}))
        ans = fp(k10)
        ok10 = (ans is not None and ans.category == "fingerprint_recall"
                and ans.moves.items[0].action_kind == "add_node"
                and "gradient boosting" in ans.moves.items[0].action_key.lower())
        # a situation with no accepted history recalls nothing.
        none_ans = fp(Knowledge(goal="x", frame=AskFrame(
            extra={"situation": {"family": "regression"}})))
        ok10 = ok10 and none_ans is None
    except Exception as exc:                                    # noqa: BLE001
        ok10, exc_detail = False, repr(exc)
    else:
        exc_detail = ""
    check("fingerprint_recall_recalls_a_won_move_only",
          ok10,
          "muscle memory recalls 'gradient boosting' (an accepted winner) for a "
          "matching situation, and recalls nothing for a situation with no "
          "accepted history" + (f" [{exc_detail}]" if exc_detail else ""))

    # 11. register_library populates the registry and a build reflex fires with
    #     no model call.
    lib = ResolverRegistry()
    register_library(lib)
    prac_lib = Practitioner(confidence_bar=0.7, impact=10.0, registry=lib)
    empty = prac_lib.step(Knowledge(goal="x", facts={"has_baseline": False}))
    check("register_library_populates_and_a_build_reflex_fires",
          lib.categories()["total_resolvers"] == len(LIBRARY_SPECS)
          and empty.resolver == "establish_baseline"
          and empty.model_calls_made == 0
          and empty.answer.moves.items[0].action_key.startswith("baseline"),
          f"registering the library gives {len(LIBRARY_SPECS)} regimes; an empty "
          "graph fires 'establish a baseline' at zero model cost")

    # 12. The leakage guard wins before target-encoding, and lifts once the split
    #     is verified.
    unverified = prac_lib.step(Knowledge(goal="x", facts={
        "has_baseline": True, "has_model": True, "has_cv": True,
        "high_cardinality_cols": ["city"], "split_verified": False}))
    verified = prac_lib.step(Knowledge(goal="x", facts={
        "has_baseline": True, "has_model": True, "has_cv": True,
        "high_cardinality_cols": ["city"], "split_verified": True}))
    check("the_leakage_guard_wins_before_target_encoding",
          unverified.resolver == "verify_split_first"
          and unverified.answer.moves.items[0].action_kind == "run_tests"
          and verified.resolver == "encode_high_cardinality"
          and verified.answer.moves.items[0].action_kind == "add_node",
          "with high-cardinality columns and an unverified split the loop "
          "answers 'verify the split first' (run_tests), never target-encode; "
          "once the split is verified the encoder reflex fires")

    # 13. A model council factory digests independent members (agreement leads).
    def m_a(k, pre):
        return [{"kind": "add_node", "key": "estimator=lightgbm",
                 "confidence": 0.8}]
    def m_b(k, pre):
        return [{"kind": "add_node", "key": "estimator=lightgbm",
                 "confidence": 0.7},
                {"kind": "add_node", "key": "estimator=knn", "confidence": 0.5}]
    def m_c(k, pre):
        return [{"kind": "add_node", "key": "estimator=lightgbm",
                 "confidence": 0.6}]
    council = make_council_regime("council", [m_a, m_b, m_c])
    c_ans = council(Knowledge(goal="x", frame=AskFrame(persona="ds")))
    check("a_model_council_factory_digests_members_agreement_leads",
          c_ans is not None and c_ans.category == "llm_council"
          and c_ans.moves.items[0].action_key == "estimator=lightgbm"
          and c_ans.moves.items[0].support == 3,
          "three members, two of whom also propose lightgbm -> the council "
          "digest sums independent endorsements and lightgbm (3) leads knn (1)")

    # 14. Single-model and research factories.
    single = make_single_model_regime(
        "planner", lambda k, pre: [{"kind": "add_node", "key": "estimator=hgb",
                                    "confidence": 0.8}])
    s_ans = single(Knowledge(goal="x", frame=AskFrame(persona="ds")))
    research = make_research_regime("research", lambda k: k.fact("gap"))
    r_gap = research(Knowledge(goal="x", facts={"gap": "fold_safe_encoder"}))
    r_none = research(Knowledge(goal="x"))
    check("single_model_and_research_factories_produce_typed_answers",
          s_ans.moves.items[0].action_key == "estimator=hgb"
          and r_gap.moves.items[0].action_kind == "do_research"
          and "fold_safe_encoder" in r_gap.moves.items[0].action_key
          and r_none is None,
          "the single-model regime proposes a node; the research regime answers "
          "'do_research' only when a capability gap is present, else passes")

    # 15. Memory factories: recall on a hit, solved-route replay gated by
    #     similarity.
    recall = make_recall_resolver(
        "recall", lambda k: ([{"key": "estimator=hgb", "kind": "add_node",
                               "display": "HGB", "strength": 3}]
                             if k.fact("hit") else []))
    replay = make_solved_route_replay(
        "replay", lambda sig: ({"route": ["load", "clean", "hgb"],
                                "similarity": 0.95} if sig == "taskA" else None),
        min_similarity=0.9)
    loose = make_solved_route_replay(
        "loose", lambda sig: {"route": ["x"], "similarity": 0.5},
        min_similarity=0.9)
    m_hit = recall(Knowledge(goal="x", facts={"hit": True}))
    m_miss = recall(Knowledge(goal="x"))
    rep = replay(Knowledge(goal="x", facts={"signature": "taskA"}))
    rep_none = replay(Knowledge(goal="x", facts={"signature": "taskB"}))
    loose_ans = loose(Knowledge(goal="x", facts={"signature": "s"}))
    check("memory_recall_and_solved_route_replay_are_gated_correctly",
          m_hit is not None and m_miss is None
          and rep is not None and len(rep.moves.items) == 3
          and rep_none is None and loose_ans is None,
          "recall fires on a hit and passes on a miss; solved-route replay "
          "replays a 0.95-similar task's 3-step route but refuses a 0.50 match "
          "(a loose match is an analogy, not a replay)")

    # 16. Claims carry epistemic status; only GROUND claims become facts a rule
    #     may build on.
    est = EpistemicState()
    est.add_claim(Claim("split_leakage_free", "the split is leakage-free",
                        status="verified"))
    est.add_claim(Claim("target_is_binary", "target is binary",
                        status="assumed"))
    facts = est.ground_facts()
    check("claims_carry_status_and_only_ground_claims_become_facts",
          facts.get("split_leakage_free") is True
          and "target_is_binary" not in facts,
          "a VERIFIED claim becomes a fact a reflex may rely on; an ASSUMED "
          "claim does not — status and confidence are separate, and an "
          "assumption is never treated as established ground")

    # 17. Supersession preserves history; a KnowledgeDelta appends, never
    #     rewrites the prior state.
    est2 = EpistemicState()
    est2.add_claim(Claim("v1", "cv score is 0.95", status="observed"))
    delta = KnowledgeDelta(added_claims=(
        Claim("v2", "cv score is 0.80 after fixing leakage", status="verified",
              supersedes="v1"),))
    est3 = delta.apply_to(est2)
    check("supersession_preserves_history_and_delta_is_append_only",
          est2.claims["v1"].status == "observed"          # prior state intact
          and est3.claims["v1"].status == "superseded"    # new state supersedes
          and est3.claims["v2"].status == "verified",
          "applying a delta returns a NEW state where v1 is marked superseded "
          "and v2 is added, while the ORIGINAL state still has v1 as observed — "
          "history is never rewritten")

    # 18. detect_decision_need frames the open decision and picks the mode.
    contra_state = EpistemicState()
    contra_state.add_contradiction(Contradiction(
        "c1", ("a", "b"), materiality=0.8))
    n_contra = detect_decision_need(contra_state)
    unknown_state = EpistemicState()
    unknown_state.add_unknown(Unknown("u1", "is the split leakage-free?",
                                      expected_value=0.9))
    n_unknown = detect_decision_need(unknown_state)
    n_goal = detect_decision_need(EpistemicState(), goal_satisfied=True)
    n_plan = detect_decision_need(EpistemicState(), has_ready_plan_clause=True)
    n_route = detect_decision_need(EpistemicState(),
                                   has_multiple_candidates=True)
    check("decision_need_detects_why_a_decision_is_open_and_its_mode",
          n_contra.mode == "investigate" and n_contra.kind == "contradiction"
          and n_unknown.mode == "investigate"
          and n_goal.mode == "terminate"
          and n_plan.mode == "follow" and n_route.mode == "route",
          "a material contradiction and a high-value unknown both frame an "
          "INVESTIGATE need; a satisfied goal is TERMINATE; a ready plan is "
          "FOLLOW; multiple candidates is ROUTE — the loop frames the question "
          "before answering it")

    # 19. The decision need constrains the answer: a TERMINATE need admits only
    #     terminal moves, so an add-node answer does not satisfy it; an
    #     INVESTIGATE need admits an epistemic run_tests answer.
    add_node_resolver = [WhatIsNextResolver(
        "adder", "deterministic_rule",
        lambda k: answer("adder", "deterministic_rule",
                         [move("add_node", "estimator=hgb", confidence=0.9)],
                         0.9))]
    test_resolver = [WhatIsNextResolver(
        "tester", "deterministic_rule",
        lambda k: answer("tester", "deterministic_rule",
                         [move("run_tests", "leakage_audit", confidence=0.9)],
                         0.9))]
    cell = SolverCell(confidence_bar=0.7, impact=5.0)
    terminated = cell.step(Knowledge(goal="x"), resolvers=add_node_resolver,
                           need=n_goal)
    investigated = cell.step(Knowledge(goal="x"), resolvers=test_resolver,
                             need=n_unknown)
    check("the_decision_need_constrains_the_admissible_answer",
          not terminated.resolved            # add_node rejected by TERMINATE need
          and investigated.resolved
          and investigated.answer.moves.items[0].action_kind == "run_tests"
          and SolverCell is Practitioner,
          "an 'add a node' answer does not satisfy a TERMINATE need (only "
          "terminal moves do), while a 'run tests' answer satisfies an "
          "INVESTIGATE need — you cannot answer add-a-node to a stop decision; "
          "SolverCell is the canonical name (Practitioner aliases it)")

    # Fold in the submodule self-tests so there is one test entrypoint:
    # deliberation strategies, lenses, context views, domain packs, the arbiter,
    # delegation/join, and iteration receipts.
    _FOLDED_SUBMODULE_TESTS = [
        "architecture_map", "_conformance_test", "_conformance_scan",
        "conformance_report",
        "static_architecture.facets",
        "loop.loop_templates", "loop.encapsulate", "loop.loop_contract",
        "loop.capability_loops",
        "loop.loop_doctrine", "loop.practitioner_campaign",
        "loop.intelligence_loops",
        "code_nodes.smoke_ladder",
        "code_nodes.context_seed", "code_nodes.self_improvement_loop",
        "code_nodes.solution_canvas", "code_nodes.solution_compiler",
        "code_nodes.run_analytics", "code_nodes.run_playback",
        "static_architecture.chronicle", "code_nodes.run_quality",
        "static_architecture.intelligence_layers",
        "static_architecture.context_catalog",
        "static_architecture.context_classification",
        "static_architecture.context_ontology",
        "static_architecture.code_intelligence_assets",
        "static_architecture.brave_search",
        "static_architecture.user_intelligence",
        "static_architecture.runtime_memory",
        "static_architecture.solution_library",
        "code_nodes.change_proposals",
        "code_nodes.guidance_ledger", "code_nodes.foundry_probes",
        "code_nodes.live_run_demo",
        "code_nodes.string_foundry",
        "static_architecture.studio_server",
        "static_architecture.retrieval",
        "static_architecture.duckdb_catalog",
        "loop.decision_slates", "loop.escalation_governor",
        "loop.hybrid_dimension_lattice", "loop.research_to_capability",
        "loop.list_intelligence",
        "loop.deliberation", "loop.lens", "strings.context", "strings.packs",
        "loop.arbiter", "loop.delegation", "loop.receipts", "loop.runner",
        "loop.practitioner_methods", "strings.notes", "loop.context_shuffle", "loop.decision_envelope",
        "strings.prompt_fragments", "loop.decision_episode", "code_nodes.pack_curation", "loop.studio",
        "static_architecture.persistence", "loop.acceptance", "loop.route_bridge", "static_architecture.ollama_resolvers",
        "code_nodes.kaggle_executor", "static_architecture.opencode_client", "loop.methodical", "loop.practitioner_loop",
        "loop.canvas", "loop.sub_practitioner", "code_nodes.self_improve", "loop.tuning",
        "static_architecture.model_call", "static_architecture.store_serve", "strings.ask_strategies", "loop.kernel",
        "strings.question_engine", "loop.kernel_model_impls", "code_nodes.enrichment", "static_architecture.config",
        "strings.biases", "code_nodes.review_mode", "code_nodes.rl_vocabulary", "code_nodes.competition_solver",
        "static_architecture.operating_profile", "static_architecture.reasoning_call", "code_nodes.blueprint", "strings.question_bank",
        "strings.domain_pack", "code_nodes.closure", "code_nodes.planning", "strings.task_blueprint",
        "loop.step_registry",
        "loop.effective_spec",
        "loop.loop_capsule",
        "code_nodes.solution_graph",
        "code_nodes.solution_records",
        "code_nodes.loop_report",
        "code_nodes.public_examples",
        "code_nodes.guided_setup",
        "code_nodes.universal_solve",
        "static_architecture.knowledge_loader",
        "static_architecture.saas_routes",
        "static_architecture.boundary_registry",
        "static_architecture.mistral_client",
        "static_architecture.openrouter_client",
        "static_architecture.provider_failover",
        "static_architecture.model_discovery",
        "static_architecture.autoconfigure",
        "static_architecture.custom_endpoint",
    ]
    import importlib as _importlib

    #: Third-party modules included by the one complete Loop Engine install.
    #: A missing module means the installation is incomplete.
    _PACKAGE_FOR_MODULE = {
        "numpy": "numpy", "pandas": "pandas",
        "sklearn": "scikit-learn", "lightgbm": "lightgbm",
        "xgboost": "xgboost", "duckdb": "duckdb",
        "model2vec": "model2vec", "lancedb": "lancedb",
        "kaggle": "kaggle", "yaml": "PyYAML",
    }

    def _fold(name, run):
        """Run one module's self_test and report an incomplete installation.

        ``run`` may be a callable OR a module path to import: an adapter that
        imports its dependency at module level raises during IMPORT, before any
        test runs, so guarding only the call left that case uncaught."""
        try:
            if isinstance(run, str):
                run = _importlib.import_module(
                    f"{__package__}.{run}").self_test
            return run()["tests"]
        except ModuleNotFoundError as exc:
            package = _PACKAGE_FOR_MODULE.get((exc.name or "").split(".")[0])
            if package is None:
                raise                       # a REAL missing import: never hide
            return [{"test": f"{name}_self_test", "passed": False,
                     "missing_dependency": package,
                     "detail": f"FAILED: missing {exc.name}. Reinstall "
                               "Loop Engine to restore all dependencies."}]

    for _name in _FOLDED_SUBMODULE_TESTS:
        results.extend(_fold(_name, _name))
    # solve.py (the demo module) is shadowed on the package by the universal
    # solve() FUNCTION, so import both self-tests explicitly by module path.
    from .loop.solve import self_test as _solve_demo_self_test
    from .loop.solver import self_test as _universal_solver_self_test
    results.extend(_fold("loop.solve", _solve_demo_self_test))
    results.extend(_fold("loop.solver", _universal_solver_self_test))
    results.extend(_fold("strings.intelligence_strings", "strings.intelligence_strings"))
    results.extend(_fold("static_architecture.model_routes", "static_architecture.model_routes"))
    results.extend(_fold("strings.solution_shaping", "strings.solution_shaping"))
    results.extend(_fold("code_nodes.measurement", "code_nodes.measurement"))
    results.extend(_fold("code_nodes.capture", "code_nodes.capture"))
    results.extend(_fold("strings.bias_checklist", "strings.bias_checklist"))
    results.extend(_fold("strings.decision_schemas", "strings.decision_schemas"))
    results.extend(_fold("strings.output_templates", "strings.output_templates"))
    results.extend(_fold("code_nodes.learning_bundle", "code_nodes.learning_bundle"))
    results.extend(_fold("code_nodes.follow_up", "code_nodes.follow_up"))
    results.extend(_fold("static_architecture.intelligence_registry", "static_architecture.intelligence_registry"))
    results.extend(_fold("code_nodes.runtime_contracts", "code_nodes.runtime_contracts"))
    results.extend(_fold("code_nodes.logic_ast", "code_nodes.logic_ast"))
    results.extend(_fold("static_architecture.asset_class", "static_architecture.asset_class"))
    results.extend(_fold("code_nodes.failure_response", "code_nodes.failure_response"))
    results.extend(_fold("loop.wiring", "loop.wiring"))
    results.extend(_fold("static_architecture.capability_directory", "static_architecture.capability_directory"))
    results.extend(_fold("code_nodes.housekeeping", "code_nodes.housekeeping"))
    results.extend(_fold("strings.interrogation", "strings.interrogation"))
    results.extend(_fold("loop.decision_engine", "loop.decision_engine"))
    results.extend(_fold("static_architecture.asset_lifecycle", "static_architecture.asset_lifecycle"))
    results.extend(_fold("loop.recursive_loop", "loop.recursive_loop"))
    results.extend(_fold("loop.loop_handlers", "loop.loop_handlers"))
    results.extend(_fold("loop.steps._facade_test", "loop.steps._facade_test"))

    passed = sum(1 for r in results if r["passed"])
    missing = [r for r in results if r.get("missing_dependency")]
    missing_packages = sorted({r["missing_dependency"] for r in missing})
    return {"record_type": "whats_next_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "missing_dependencies": missing_packages,
            "dependency_note": (
                "incomplete installation: " + ", ".join(missing_packages)
                if missing_packages else
                "all declared dependencies are installed"),
            "all_passed": passed == len(results)}

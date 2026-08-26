"""Focused checks for the role-correct Solution Canvas runtime.

The production module delegates here so its public self-test entry point stays
stable while runtime orchestration remains below the repository module cap.
"""

from __future__ import annotations

import json

from ..loop.recursive_loop import MODES, Loop, LoopLedger, StepOutcome
from .solution_canvas import (SolutionError, SolutionLoopSpec, SolutionSpec,
                              _spec_dict, run_solution)


def solution_canvas_self_test_checks() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    reg = {
        "clean": lambda x, p: [v for v in x if v is not None],
        "scale": lambda x, p: [v * p.get("factor", 1) for v in x],
        "mean": lambda x, p: sum(x) / len(x),
        "crash": lambda x, p: (_ for _ in ()).throw(RuntimeError("boom")),
        "median": lambda x, p: sorted(x)[len(x) // 2],
    }
    data = [1, None, 2, 3, None, 4]

    # 1. a deterministic solution ships: same answer every run (the user's
    # "same result every time" setting, honored end to end).
    det = SolutionSpec("pipeline_a",
                       permitted_loop_modes=("deterministic",),
                       loops=(SolutionLoopSpec("n1", "clean"),
                              SolutionLoopSpec("n2", "scale",
                                           params={"factor": 2}),
                              SolutionLoopSpec("n3", "mean")))
    r1, r2 = run_solution(det, reg, data), run_solution(det, reg, data)
    check("deterministic_solution_is_repeatable", r1 == r2 == 5.0,
          f"two runs, same answer: {r1}")

    # 2. the shipping setting is a HARD gate: a deterministic-only solution
    # refuses a model-led LOOP at validation, before anything runs.
    bad = SolutionSpec("no_llm",
                       permitted_loop_modes=("deterministic",),
                       loops=(SolutionLoopSpec("n1", "clean",
                                           mode="non_deterministic"),))
    rep = bad.validate()
    check("shipping_mode_setting_is_a_hard_gate",
          not rep["valid"] and any("outside the graph policy" in item
                                   for item in rep["violations"]))

    # 3. per-NODE fallback chains: a crashing operation falls to its declared
    # fallback, recorded; nothing silent.
    tr = []
    fb = SolutionSpec("with_fallback",
                      loops=(SolutionLoopSpec("n1", "clean"),
                             SolutionLoopSpec("n2", "crash",
                                          fallback_operations=("median",))))
    out = run_solution(fb, reg, data, trace=tr)
    check("node_fallback_chain_runs_and_records",
          out == 3 and any("failed" in t for t in tr)
          and any(t.get("operation") == "median"
                  and t.get("used_fallback") for t in tr))

    # 4. a solution of solutions: average and weighted_average combine members.
    m1 = SolutionSpec("m1", loops=(SolutionLoopSpec("a", "clean"),
                                   SolutionLoopSpec("b", "mean")))
    m2 = SolutionSpec("m2", loops=(SolutionLoopSpec("a", "clean"),
                                   SolutionLoopSpec("b", "median")))
    avg = SolutionSpec("blend", members=(m1, m2), ensemble="average")
    wavg = SolutionSpec("wblend", members=(m1, m2),
                        ensemble="weighted_average", weights=(3, 1))
    member_ledger = LoopLedger()
    member_out = run_solution(avg, reg, data, ledger=member_ledger)
    member_inits = [e for e in member_ledger.events
                    if e.get("event") == "init"]
    member_starting = member_inits[0]
    member_spawned = [e for e in member_inits
                      if e.get("profile_id") == "solution.pipeline"]
    check("solution_of_solutions_averages_and_weights",
          member_out == 2.75
          and run_solution(wavg, reg, data) == 2.625,
          "members mean=2.5 and median=3 combine as declared")
    check("member_solutions_are_spawned_by_the_starting_solution",
          member_starting.get("relationship_kind") == "starting"
          and member_starting.get("role") == "solution"
          and member_starting.get("profile_id") == "solution.ensemble"
          and len(member_spawned) == 2
          and all(e.get("relationship_kind") == "spawned_by"
                  and e.get("spawned_by_loop_id")
                      == member_starting["loop_id"]
                  for e in member_spawned),
          "Starting Solution ensemble owns two Spawned Solution pipelines")

    # 5. ordered_fallback: the first member that completes serves; a broken
    # first member is recorded, not fatal.
    broken = SolutionSpec("broken", loops=(SolutionLoopSpec("a", "crash"),))
    of = SolutionSpec("resilient", members=(broken, m2),
                      ensemble="ordered_fallback")
    tr5 = []
    out5 = run_solution(of, reg, data, trace=tr5)
    check("ordered_fallback_serves_first_working_member",
          out5 == 3 and any(t.get("member_failed") == "broken" for t in tr5)
          and any(t.get("served_by") == "m2" for t in tr5))

    # 6. a member never has more mode permissions than its composite (the
    # loop's permission grammar, applied to the artifact).
    wide = SolutionSpec("wide", permitted_loop_modes=MODES,
                        loops=(SolutionLoopSpec("a", "clean"),))
    parent = SolutionSpec("narrow",
                          permitted_loop_modes=("deterministic",),
                          members=(wide, m2), ensemble="average")
    repp = parent.validate()
    check("unused_member_policy_does_not_become_a_graph_mode",
          repp["valid"]
          and all(vertex.selected_mode == "deterministic"
                  for vertex in parent.graph.vertices),
          "the authoritative graph carries only each Loop's selected mode")

    # 7. specs are searchable Strings (round-trip through the store, faceted).
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=[det.to_record(), avg.to_record()])
    hits = store.search("solution average blend ensemble")
    check("solution_specs_are_searchable_strings",
          hits["hits"] and hits["hits"][0]["record_id"] == "solution.blend"
          and hits["hits"][0]["facets"].get("category") == "solution_spec")

    # 8. member-count bound + JSON serializability (a spec is a String).
    over = SolutionSpec("crowd", members=tuple(
        SolutionSpec(f"s{i}", loops=(SolutionLoopSpec("a", "clean"),))
        for i in range(7)), ensemble="average", max_members=5)
    check("member_bound_and_serializable",
          not over.validate()["valid"]
          and json.loads(json.dumps(_spec_dict(avg)))["record_type"]
              == "loop_graph_definition/v1"
          and any(group["combination"] == "average" for group in
                  json.loads(json.dumps(_spec_dict(avg)))["groups"]))

    # 9. A standalone run is one Starting Solution pipeline whose components
    # are exact Spawned Solution loops on the same ledger.
    from ..core.run_history import to_canonical_events
    lg = LoopLedger()
    tr: list = []
    two = SolutionSpec("two.step", loops=(SolutionLoopSpec("prep", "clean"),
                                          SolutionLoopSpec("score", "mean")))
    out = run_solution(two, reg, [1, None, 3], trace=tr, ledger=lg)
    fams = [c["type"] for c in to_canonical_events(lg.events)]
    started = [e for e in lg.events
               if e.get("event") == "solution.loop.started"]
    inits = [e for e in lg.events if e.get("event") == "init"]
    envelopes = {e["loop_id"] for e in inits}
    starting_init = inits[0]
    spawned_inits = inits[1:]
    terminals = {e["loop_id"] for e in lg.events
                 if e.get("event") == "terminal"}
    check("standalone_canvas_is_starting_solution_with_spawned_solutions",
          out == 2.0 and len(started) == 3 and len(envelopes) == 3
          and fams.count("solution.loop.started") == 3
          and fams.count("solution.loop.completed") == 3
          and starting_init.get("relationship_kind") == "starting"
          and starting_init.get("role") == "solution"
          and starting_init.get("profile_id") == "solution.pipeline"
          and all(e.get("relationship_kind") == "connected_from"
                  and e.get("role") == "solution"
                  and e.get("profile_id") == "solution.atomic_component"
                  for e in spawned_inits)
          and spawned_inits[0].get("connected_from_loop_ids")
              == [starting_init["loop_id"]]
          and spawned_inits[1].get("connected_from_loop_ids")
              == [spawned_inits[0]["loop_id"]]
          and terminals == envelopes
          and all(r.get("component_loop_id") in envelopes
                  for r in tr if "component_loop_id" in r)
          and not [e for e in lg.events
                   if e.get("mode") in ("hybrid", "non_deterministic")],
          f"Starting pipeline + 2 spawned atomic loops {sorted(envelopes)}")

    # 10. ADVERSARIAL: no path reaches a registry callable outside a loop.
    # A component whose primary crashes must still be served INSIDE its own
    # envelope by its declared fallback (recorded), and a component whose
    # whole chain fails must raise SolutionError with the failure on the
    # ledger — never a silent value and never a bare call.
    lg2 = LoopLedger()
    tr2: list = []
    saved = SolutionSpec("recovers", loops=(
        SolutionLoopSpec("risky", "crash", fallback_operations=("clean",)),))
    got = run_solution(saved, reg, [1, None, 3], trace=tr2, ledger=lg2)
    served = [r for r in tr2 if r.get("used_fallback")]
    doomed = SolutionSpec("doomed", loops=(
        SolutionLoopSpec("risky", "crash", fallback_operations=("crash",)),))
    failed_closed = False
    lg3 = LoopLedger()
    try:
        run_solution(doomed, reg, [1], ledger=lg3)
    except SolutionError:
        failed_closed = True
    invoke_ids = [e["loop_id"] for e in lg2.events
                  if e.get("event") == "tool_invocation_started"]
    atomic_ids = {e["loop_id"] for e in lg2.events
                  if e.get("event") == "init"
                  and e.get("role") == "solution"
                  and e.get("profile_id") == "solution.atomic_component"}
    doomed_inits = {e["loop_id"] for e in lg3.events
                    if e.get("event") == "init"
                    and e.get("role") == "solution"}
    doomed_terminals = {e["loop_id"] for e in lg3.events
                        if e.get("event") == "terminal"}
    check("fallbacks_and_failures_stay_inside_the_loop_envelope",
          got == [1, 3] and len(served) == 1
          and invoke_ids and set(invoke_ids) <= atomic_ids
          and len(invoke_ids) == len(set(invoke_ids))
          and failed_closed
          and doomed_inits == doomed_terminals
          and any(e.get("event") == "solution.loop.completed"
                  and e.get("status") == "failed" for e in lg3.events),
          "each registry attempt has one spawned atomic Solution; all terminate")

    # 11. A Starting Practitioner owns one Spawned Solution pipeline. Their
    # modes remain independent: this hybrid Practitioner delegates
    # deterministic execution without changing either role or mode.
    from ..loop.loop_role import (LoopRelationship, LoopRoleIdentity)
    from ..loop.recursive_loop import LoopConfig
    lg4 = LoopLedger()
    owner = Loop(
        "own the final Canvas execution",
        LoopConfig(framework="custom", custom_steps=("act",),
                   allowable_modes=("hybrid",),
                   preferred_modes=("hybrid",),
                   delegated_modes=("deterministic",),
                   llm_thinking_power="medium", exit_condition="accepted_success",
                   max_depth=4),
        ledger=lg4,
        identity=LoopRoleIdentity("practitioner", "practitioner.solver"),
        relationship=LoopRelationship.starting())
    tr4: list = []
    owned = SolutionSpec(
        "owned", loops=(SolutionLoopSpec("clean", "clean"),))
    owned_holder = {}

    def own_canvas(active: Loop, step: str, context: dict) -> StepOutcome:
        owned_holder["value"] = run_solution(
            owned, reg, [1, None, 2], trace=tr4, parent=active)
        return StepOutcome(output="canvas:done", mode="hybrid",
                           confidence=0.9)

    owner.run(handler=own_canvas, max_steps=2)
    got4 = owned_holder["value"]
    pipeline = next(e for e in lg4.events
                    if e.get("event") == "init"
                    and e.get("profile_id") == "solution.pipeline")
    component_id = next(row["component_loop_id"] for row in tr4
                        if row.get("component_loop_id"))
    check("starting_practitioner_owns_spawned_solution_pipeline",
          got4 == [1, 2]
          and next(e for e in lg4.events if e.get("event") == "init"
                   and e.get("loop_id") == owner.loop_id).get(
                       "relationship_kind")
              == "starting"
          and pipeline.get("relationship_kind") == "spawned_by"
          and pipeline.get("role") == "solution"
          and pipeline.get("spawned_by_loop_id") == owner.loop_id
          and any(e.get("event") == "init"
                  and e.get("loop_id") == component_id
                  and e.get("relationship_kind") == "connected_from"
                  and e.get("connected_from_loop_ids")
                      == [pipeline["loop_id"]] for e in lg4.events)
          and any(e.get("event") == "run_step"
                  and e.get("loop_id") == owner.loop_id
                  and e.get("mode") == "hybrid" for e in lg4.events)
          and all(e.get("mode") != "hybrid" for e in lg4.events
                  if e.get("loop_id") != owner.loop_id)
          and not any(e.get("event") == "spawn"
                      and e.get("loop_id") == component_id
                      for e in lg4.events),
          f"Practitioner {owner.loop_id} -> pipeline {pipeline['loop_id']} "
          f"-> component {component_id}")

    split_refused = False
    try:
        run_solution(owned, reg, [1], parent=owner, ledger=LoopLedger())
    except SolutionError:
        split_refused = True
    check("owned_canvas_refuses_a_split_ledger", split_refused,
          "parent and components always share one timeline")

    # 12. A semantic Solution vertex cannot become executable until an exact
    # semantic Solution profile and executor exist.
    calls = []
    hybrid = SolutionSpec(
        "hybrid.valid",
        loops=(SolutionLoopSpec("semantic", "semantic",
                                mode="hybrid"),))
    hybrid_ledger = LoopLedger()
    adapter_refused = False
    try:
        run_solution(hybrid,
                     {"semantic": lambda x, p: calls.append(x)}, [1],
                     ledger=hybrid_ledger)
    except SolutionError as exc:
        adapter_refused = "no installed 'hybrid' Solution executor" in str(exc)
    check("semantic_solution_executor_unavailable_fails_before_work",
          not hybrid.validate()["valid"] and adapter_refused
          and not calls and not hybrid_ledger.events,
          "unavailable semantic executor performs zero work")

    # 13. Typed roles follow the actual value through the pipeline and ride
    # each runtime Loop contract.
    typed = SolutionSpec("typed", loops=(
        SolutionLoopSpec("clean", "clean", input_role="raw_rows/v1",
                         output_role="clean_rows/v1"),
        SolutionLoopSpec("count", "count", input_role="clean_rows/v1",
                         output_role="row_count/v1"),
    ))
    typed_ledger = LoopLedger()
    typed_trace = []
    typed_value = run_solution(
        typed, {**reg, "count": lambda x, p: len(x)}, [1, None, 2],
        ledger=typed_ledger, trace=typed_trace)
    typed_inits = [e for e in typed_ledger.events
                   if e.get("event") == "init"]
    check("typed_value_flow_rides_solution_loop_contracts",
          typed_value == 2
          and typed_inits[0].get("input_roles") == ("raw_rows/v1",)
          and typed_inits[0].get("output_roles")
              == ("raw_rows/v1", "row_count/v1")
          and typed_inits[1].get("output_roles") == ("clean_rows/v1",)
          and typed_inits[2].get("input_roles") == ("clean_rows/v1",)
          and any(t.get("input_type") == "list"
                  and t.get("output_type") == "int" for t in typed_trace),
          "raw rows -> clean rows -> row count on named ports")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

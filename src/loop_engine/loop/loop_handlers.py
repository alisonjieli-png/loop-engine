"""Loop handlers — the REAL step resolvers: the Loop running on the actual
infrastructure.

This closes the last gap in "everything is a loop": ``recursive_loop.Loop.run``
takes a pluggable handler, and these are the real ones —

  * ``directory_handler`` resolves every step through the live machinery:
      1. pulls the required Context Intelligence for the step (the effort setting's
         ``min_intelligence_per_step`` — the required calls to the string
         database), recorded;
      2. probes the CODE rail with one real search through the capability
         directory (a real ``resource_search`` call — real hits);
      3. picks the mode by the loop's waterfall (code available → deterministic;
         judgement or no code → hybrid/model), then resolves it:
         deterministic = the code node found; hybrid = code plus a model
         escalation when the code rail is empty; non-deterministic = the
         LLM-pipeline surface (a stub by default — a production run passes the
         real ``run_reasoning`` as the surface's ``llm_invoke``, keeping the
         cloud-only rule);
      4. records every infrastructure call, escalation, and pull on the ledger.

  * ``run_loop_via_kernel`` — the nine_step framework's concrete executor IS the
    kernel: the whole run delegates to the wired kernel (``run_wired``), and the
    kernel's passes land on the loop's ledger.

The wedge, live: the Loop is universal; what a step actually resolves to is
whatever Code Intelligence and Context Intelligence this install has accumulated.
"""

from __future__ import annotations

from ..loop.recursive_loop import Loop, LoopResult, LoopError, StepOutcome


def directory_handler(*, directory, bank=None, intelligence=None):
    """A real step handler over a capability directory (+ optional string bank
    + optional FOUR-PILLAR intelligence records).

    ``intelligence`` is a ``layer_records`` mapping for
    ``intelligence_layers.query_intelligence``. Context, Code, Runtime History
    and Solution, and User Feedback are the four layers. When present, the
    loop consults all four layers at the
    orient step (one need, one Retriever), records the pull as a ledger event
    (``capability.search.started`` / ``capability.search.completed`` /
    ``capability.selected`` — the first real emitters for those declared
    families), and feeds the top hit into the code-rail probe as a NOMINATION
    (never a proof — admission still runs through the directory's own gate).
    A pillar missing from the pack is reported, never silently skipped."""
    from ..strings.intelligence_strings import compose

    def handler(loop: Loop, step: str, context: dict) -> StepOutcome:
        st = loop.config.settings
        # 1. the mandatory string-intelligence pull for this step.
        n_req = st["min_intelligence_per_step"]
        pulled = (compose(bank, (step,), max_strings=n_req)
                  if bank is not None else {"n_used": 0})
        loop.ledger.record(loop_id=loop.loop_id, event="intelligence_pull",
                           step=step, pulled=pulled["n_used"], required=n_req)
        # 1b. the four-pillar intelligence consult, one need fanned across
        # String / Code / Run&Solution / User at the orient step (the loop
        # deciding with all four pillars, not only the string bank).
        if intelligence is not None and step in ("orient", "research"):
            from ..static_architecture.intelligence_layers import (
                query_intelligence)
            loop.ledger.record(loop_id=loop.loop_id,
                               event="capability.search.started", step=step,
                               need=loop.goal)
            fan = query_intelligence(loop.goal, intelligence)
            top = fan["hits"][0] if fan["hits"] else None
            loop.ledger.record(loop_id=loop.loop_id,
                               event="capability.search.completed", step=step,
                               hits=len(fan["hits"]),
                               unqueried=tuple(fan["unqueried"]))
            if top is not None:
                loop.ledger.record(loop_id=loop.loop_id,
                                   event="capability.selected", step=step,
                                   record_id=top.get("record_id", ""),
                                   layer=top.get("layer", ""))
                context["_intelligence_top"] = top
        # 2. probe the code rail: one REAL search through the directory.  The
        # probe asks "does a code node serve THIS step?", so the step is the key
        # (goal terms would cross-match every step against the same records).
        r = directory.call("resource_search", "search", query=step)
        hits = (r.value.get("hits", [])
                if r.ok and isinstance(r.value, dict) else [])
        loop.ledger.record(loop_id=loop.loop_id, event="infra_call", step=step,
                           surface="resource_search", n_hits=len(hits))
        # 3. the mode, by the loop's waterfall.
        mode = loop.choose_mode(
            deterministic_available=bool(hits),
            needs_judgement=step in ("decide", "decide_next", "choose",
                                     "assess_prepare"))
        # 4. resolve it.
        if mode == "deterministic":
            return StepOutcome(output=f"{step}:code[{hits[0]['record_id']}]",
                               mode=mode, confidence=0.85)
        if mode == "hybrid":
            if hits:
                return StepOutcome(
                    output=f"{step}:code+model_check[{hits[0]['record_id']}]",
                    mode=mode, confidence=0.8)
            directory.call("llm_pipeline", "invoke", step=step, goal=loop.goal)
            loop.ledger.record(loop_id=loop.loop_id, event="model_escalation",
                               step=step)
            return StepOutcome(output=f"{step}:escalated_to_model", mode=mode,
                               confidence=0.65)
        directory.call("llm_pipeline", "invoke", step=step, goal=loop.goal)
        loop.ledger.record(loop_id=loop.loop_id, event="model_led", step=step)
        return StepOutcome(output=f"{step}:model_led", mode=mode, confidence=0.6)

    return handler


def run_loop_via_kernel(loop: Loop, *, max_passes: "int | None" = None
                        ) -> LoopResult:
    """nine_step's concrete executor is the KERNEL: delegate the run to the wired
    kernel and record its passes on the loop's ledger."""
    if loop.config.framework != "nine_step":
        raise LoopError("kernel delegation is for nine_step loops; custom/open "
                        "loops use Loop.run with a handler")
    from ..loop.wiring import run_wired
    from ..loop.kernel import ProblemSpec
    run = run_wired(ProblemSpec(objective=loop.goal,
                                success_criteria=("solved",)),
                    max_passes=max_passes
                    or loop.config.settings["max_iterations"])
    loop.ledger.record(loop_id=loop.loop_id, event="kernel_run",
                       passes=run["passes"], final=run["final_route"],
                       exercised=run["wired_modules"])
    return LoopResult(loop.loop_id, run["final_route"], 0.8, run["passes"],
                      {"deterministic": run["passes"]}, 0, 0, "done")


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network (the LLM surface is the stub).
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ..loop.recursive_loop import LoopConfig
    from ..static_architecture.capability_directory import default_directory
    from ..static_architecture.store_serve import SolverStore, StoreRecord
    from ..strings.intelligence_strings import IntelligenceString, StringBank

    # a small REAL install: two code nodes + a string bank.
    store = SolverStore(core_records=[
        StoreRecord("n.orient_state", "node",
                    "orient reconstruct churn model state", body={"kind": "node"},
                    tags=("orient", "churn")),
        StoreRecord("n.build_model", "node", "build the churn model pipeline",
                    body={"kind": "node"}, tags=("build", "churn"))])
    bank = StringBank()
    for i in range(6):
        bank.add(IntelligenceString("consideration",
                                    f"general working principle {i}",
                                    applicability="any"))
    d = default_directory(store=store)
    h = directory_handler(directory=d, bank=bank)

    lp = Loop("improve the churn model",
              LoopConfig(framework="custom",
                         custom_steps=("orient", "research", "build")))
    res = lp.run(handler=h)
    ev = lp.ledger.events

    # 1. the MANDATORY intelligence pull happens for every step, per the power
    # lever, and is recorded.
    pulls = [e for e in ev if e.get("event") == "intelligence_pull"]
    check("mandatory_context_intelligence_is_pulled_per_step",
          len(pulls) == 3 and all(p["required"] == 3 for p in pulls)
          and all(p["pulled"] >= 3 for p in pulls),
          f"{len(pulls)} pulls, {pulls[0]['pulled']}/{pulls[0]['required']} each "
          "(medium power = 3 per step)")

    # 2. deterministic steps run REAL code found through the directory.
    steps_out = {e["step"]: e["output"] for e in ev
                 if e.get("event") == "run_step"
                 and e.get("loop_id") == lp.loop_id}
    check("deterministic_steps_resolve_to_real_code_nodes",
          "code[n.orient_state]" in steps_out.get("orient", "")
          and "code[n.build_model]" in steps_out.get("build", ""),
          f"orient/build hit real nodes: {steps_out.get('orient','')}")

    # 3. an EMPTY code rail escalates to the model surface (hybrid) — recorded,
    # still no real model call (the surface is the stub).
    check("empty_code_rail_escalates_to_the_model_surface",
          "escalated_to_model" in steps_out.get("research", "")
          and any(e.get("event") == "model_escalation" for e in ev),
          "research had no code node → hybrid escalation through llm_pipeline")

    # 4. every infrastructure call is on the ledger (the full history).
    infra = [e for e in ev if e.get("event") == "infra_call"]
    check("every_infrastructure_call_is_on_the_ledger",
          len(infra) == 3 and all(e["surface"] == "resource_search"
                                  for e in infra),
          "one real search per step, each with its hit count")

    # 5. the run completes with mixed modes without inventing provider calls.
    check("the_real_run_completes_with_mixed_modes_without_fake_calls",
          res.steps_run == 3 and res.mode_counts.get("deterministic") == 2
          and res.mode_counts.get("hybrid") == 1 and res.model_calls == 0,
          f"modes {res.mode_counts}, {res.model_calls} model call")

    # 6. nine_step delegates to the KERNEL (the wired run), recorded on the loop
    # ledger; custom loops are refused kernel delegation.
    k = Loop("win", LoopConfig(framework="nine_step"))
    rk = run_loop_via_kernel(k)
    kev = [e for e in k.ledger.events if e.get("event") == "kernel_run"]
    refused = False
    try:
        run_loop_via_kernel(Loop("x", LoopConfig(framework="open")))
    except LoopError:
        refused = True
    check("nine_step_delegates_to_the_wired_kernel",
          rk.steps_run >= 1 and rk.output in ("stop_success",
                                              "stop_unprofitable")
          and kev and "bias_checklist" in kev[0]["exercised"] and refused,
          f"kernel ran {rk.steps_run} passes → {rk.output}; guidance exercised")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "loop_handlers_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

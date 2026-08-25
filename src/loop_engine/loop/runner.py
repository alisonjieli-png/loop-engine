"""Decision-workflow Code Intelligence for the canonical Loop runtime.

One iteration of the expert loop, composed from the contracts built alongside it:
materialize what is known, detect why a decision is open, ask the resolvers,
arbitrate the proposals into an authorized decision, execute it, observe the
result, append a knowledge delta, and write a chained record.  The runner owns
no provider logic, no compiler, no prompts, no model client — it coordinates the
services, exactly the v3 §24.3 shape.

The runner is deliberately thin so the vertical slice is legible: given a task
with an open unknown, it selects an *information action* first (run the test),
updates knowledge from the result, then on the next iteration selects a
*constructive action*, and finally stops for a *semantic reason* (the goal is
satisfied) rather than a fixed iteration count.  Execution is injected, so the
slice runs with no model and no graph engine — those are adapters the executor
supplies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Sequence

from ..strings.knowledge import Knowledge
from ..strings.knowledge_state import EpistemicState, KnowledgeDelta
from ..loop.decision_need import detect_decision_need
from ..loop.moves import family_of
from ..loop.resolvers import WhatIsNextResolver
from ..loop.loop import DecisionService
from ..loop.arbiter import Candidate, arbitrate
from ..loop.iteration_records import (SolverIterationRecord, build_iteration_record)
from .decision_slates import Proposal


@dataclass
class DecisionWorkflowState:
    cell_id: str
    goal: str
    epistemic: EpistemicState = field(default_factory=EpistemicState)
    graph_summary: str = ""
    results: tuple = ()
    flags: dict = field(default_factory=dict)         # situation flags for the need
    iteration: int = 0
    parent_record: "SolverIterationRecord | None" = None
    terminal_state: str = ""

    def digest(self) -> str:
        payload = (self.goal, self.graph_summary, self.results,
                   tuple(sorted(self.epistemic.claims)),
                   tuple(sorted(self.epistemic.unknowns)),
                   tuple(sorted(self.flags.items())))
        return hashlib.sha256(str(payload).encode()).hexdigest()[:16]


# An executor runs the authorized decision and returns the observations plus the
# knowledge delta and any flag/result updates.  This is the adapter to the
# SolutionGraph substrate (or a stub, for the slice).
ExecutorResult = tuple  # (observations: list[str], KnowledgeDelta, flag_updates: dict, results_add: tuple)
Executor = Callable[[Any, Knowledge, DecisionWorkflowState], ExecutorResult]


def _estimates_for(move: Proposal) -> dict:
    """Default objective estimates by move family — an epistemic move is valued
    for information, a constructive move for goal progress."""
    fam = family_of(move.action_kind)
    if fam in ("epistemic", "experimental"):
        return {"information_value": 0.7, "compute_cost": 0.1}
    if fam in ("constructive", "search"):
        return {"goal_progress": 0.8, "compute_cost": 0.3}
    return {"goal_progress": 0.4, "compute_cost": 0.2}


@dataclass
class IterationResult:
    state: DecisionWorkflowState
    record: SolverIterationRecord


def iterate_decision_workflow(
        state: DecisionWorkflowState, *, service: DecisionService,
        resolvers: Sequence[WhatIsNextResolver],
        executor: Executor) -> IterationResult:
    """Run one observe→decide→act→update cycle and return the new state and
    record."""
    before_digest = state.digest()
    knowledge = Knowledge(
        goal=state.goal, graph_summary=state.graph_summary,
        results=state.results, facts=state.epistemic.ground_facts(),
        open_obligations=tuple(state.epistemic.unknowns))

    need = detect_decision_need(state.epistemic, **state.flags)

    # Terminal need short-circuits — stop for a semantic reason.
    if need.mode == "terminate":
        next_state = replace(state, iteration=state.iteration + 1,
                             terminal_state=need.kind)
        record = build_iteration_record(
            state.cell_id, state.iteration, parent=state.parent_record,
            knowledge_before_digest=before_digest, decision_need=need.to_dict(),
            proposals=[], decision={"terminal": need.kind},
            model_calls_made=0, model_calls_avoided=0, observations=[],
            knowledge_after_digest=next_state.digest(),
            terminal_state=need.kind)
        return IterationResult(replace(next_state, parent_record=record),
                               record)

    step = service.step(knowledge, resolvers=resolvers, need=need)
    if not step.resolved or step.answer is None:
        # No admissible answer for this need — block rather than force one.
        next_state = replace(state, iteration=state.iteration + 1,
                             terminal_state="blocked_information")
        record = build_iteration_record(
            state.cell_id, state.iteration, parent=state.parent_record,
            knowledge_before_digest=before_digest, decision_need=need.to_dict(),
            proposals=[], decision={"blocked": True}, model_calls_made=0,
            model_calls_avoided=step.model_calls_avoided, observations=[],
            knowledge_after_digest=next_state.digest(),
            terminal_state="blocked_information")
        return IterationResult(replace(next_state, parent_record=record),
                               record)

    moves = list(step.answer.moves.items)
    candidates = [Candidate(move=m, estimates=_estimates_for(m)) for m in moves]
    decision = arbitrate(candidates, select=1)

    observations, delta, flag_updates, results_add = executor(
        decision, knowledge, state)
    new_epistemic = delta.apply_to(state.epistemic)
    new_flags = {**state.flags, **flag_updates}
    next_state = replace(
        state, iteration=state.iteration + 1, epistemic=new_epistemic,
        flags=new_flags, results=state.results + tuple(results_add))

    record = build_iteration_record(
        state.cell_id, state.iteration, parent=state.parent_record,
        knowledge_before_digest=before_digest, decision_need=need.to_dict(),
        proposals=[m.action_key for m in moves], decision=decision.to_dict(),
        model_calls_made=step.model_calls_made,
        model_calls_avoided=step.model_calls_avoided,
        observations=list(observations),
        knowledge_after_digest=next_state.digest())
    return IterationResult(replace(next_state, parent_record=record), record)


def run_decision_workflow(
        state: DecisionWorkflowState, *, service: DecisionService,
        resolvers: Sequence[WhatIsNextResolver], executor: Executor,
        max_iterations: int = 12) -> dict:
    """Run the loop until a terminal state or the safety ceiling.  The ceiling is
    a runaway backstop, NOT the reason the task is done — the terminal_state
    records the real reason."""
    chain: list[SolverIterationRecord] = []
    for _ in range(max_iterations):
        result = iterate_decision_workflow(
            state, service=service, resolvers=resolvers, executor=executor)
        state = result.state
        chain.append(result.record)
        if state.terminal_state:
            break
    return {"record_type": "solver_cell_run/v1", "cell_id": state.cell_id,
            "iterations": len(chain), "terminal_state": state.terminal_state,
            "hit_ceiling": not state.terminal_state,
            "iteration_records": [r.to_dict() for r in chain],
            "the_rule": ("the loop stops for a SEMANTIC reason recorded in "
                         "terminal_state; the iteration ceiling is only a "
                         "runaway backstop")}


# Module-local compatibility aliases. They remain importable from this module,
# but the package root exposes only the canonical Loop runtime.
SolverCellState = DecisionWorkflowState
iterate = iterate_decision_workflow
run = run_decision_workflow


# ---------------------------------------------------------------------------
# Self-test — the vertical slice, deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ..strings.knowledge_state import Claim, Unknown
    from ..loop.moves import move, answer

    # One resolver proposes BOTH a test and a node; the decision need's family
    # filter routes to the admissible one (epistemic under INVESTIGATE,
    # constructive under ROUTE).
    def dual(_k):
        return answer("dual", "deterministic_rule",
                      [move("run_tests", "leakage_audit", confidence=0.9),
                       move("add_node", "estimator=hgb", confidence=0.9)], 0.9)
    resolvers = [WhatIsNextResolver("dual", "deterministic_rule", dual)]
    service = DecisionService(confidence_bar=0.7, impact=5.0)

    # Executor: running the leakage audit resolves the unknown and unlocks
    # candidates; adding the model satisfies the goal.
    def executor(decision, knowledge, state):
        selected = [c.move.action_key for c in decision.selected]
        if any("leakage_audit" in s for s in selected):
            delta = KnowledgeDelta(
                added_claims=(Claim("split_leakage_free",
                                    "split proven leakage-free", "verified"),),
                resolved_unknowns=("u.split",))
            return (["obs.split_verified"], delta,
                    {"has_multiple_candidates": True}, ("split_ok",))
        if any("estimator" in s for s in selected):
            delta = KnowledgeDelta(added_claims=(
                Claim("model_added", "a model node was added", "observed"),))
            return (["obs.model_added"], delta,
                    {"goal_satisfied": True, "has_multiple_candidates": False},
                    ("model_ok",))
        return ([], KnowledgeDelta(), {}, ())

    start = DecisionWorkflowState(
        cell_id="cell.churn", goal="predict churn",
        epistemic=EpistemicState(unknowns={"u.split": Unknown(
            "u.split", "is the split leakage-free?", expected_value=0.9)}))

    out = run_decision_workflow(
        start, service=service, resolvers=resolvers, executor=executor)
    modes = [rd["decision_need"]["mode"] for rd in out["iteration_records"]]
    selected_moves = [rd["decision"].get("selected", []) for rd in
                      out["iteration_records"]]

    check("the_loop_investigates_before_it_constructs",
          modes[0] == "investigate"
          and any("leakage_audit" in str(m) for m in selected_moves[0])
          and modes[1] == "route"
          and any("estimator" in str(m) for m in selected_moves[1]),
          "iteration 0 frames an INVESTIGATE need and runs the leakage audit "
          "(an information action, not a node); iteration 1 frames a ROUTE need "
          "and adds the model — the test comes before the graph change")

    check("the_loop_stops_for_a_semantic_reason_not_an_iteration_count",
          out["terminal_state"] == "stop_continue"
          and out["hit_ceiling"] is False
          and out["iterations"] == 3,
          "the loop stops because the goal is satisfied (terminal_state), in "
          "three iterations, without hitting the ceiling — a semantic stop")

    # The record chain of the whole run verifies.
    from ..loop.iteration_records import verify_chain
    chain = [SolverIterationRecord(
        cell_id=rd["cell_id"], iteration=rd["iteration"],
        parent_digest=rd["parent_digest"],
        knowledge_before_digest=rd["knowledge_before_digest"],
        decision_need=rd["decision_need"], proposals=tuple(rd["proposals"]),
        decision=rd["decision"], model_calls_made=rd["model_calls_made"],
        model_calls_avoided=rd["model_calls_avoided"],
        observations=tuple(rd["observations"]),
        knowledge_after_digest=rd["knowledge_after_digest"],
        resources=rd["resources"], terminal_state=rd["terminal_state"],
        record_digest=rd["record_digest"]) for rd in out["iteration_records"]]
    verdict = verify_chain(chain)
    check("the_whole_run_produces_a_verifiable_record_chain",
          verdict["valid"] and len(chain) == 3
          and chain[1].knowledge_before_digest == chain[0].knowledge_after_digest,
          "the three-iteration run is a verifiable causal chain: each "
          "iteration's knowledge-before matches the prior's knowledge-after, and "
          "every digest recomputes")

    # Determinism.
    out2 = run_decision_workflow(DecisionWorkflowState(
        cell_id="cell.churn", goal="predict churn",
        epistemic=EpistemicState(unknowns={"u.split": Unknown(
            "u.split", "is the split leakage-free?", expected_value=0.9)})),
        service=service, resolvers=resolvers, executor=executor)
    check("the_run_is_deterministic",
          out2["terminal_state"] == out["terminal_state"]
          and out2["iterations"] == out["iterations"],
          "the same start, resolvers, and executor always produce the same run")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "runner_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

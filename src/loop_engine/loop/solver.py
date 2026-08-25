"""The Universal Solver — the single core front door.  Not a side branch.

One call solves a task by composing every layer built here into one path:

    solve(goal)
      -> a SOLUTION CANVAS is opened (the place the graph is built)
      -> the PRACTITIONER LOOP runs on it (what is next -> how to implement
         [reuse-first: learned shortcuts + registry answer "do we already have
         this?"] -> implement -> verify compilable -> save, with loop-backs,
         optional non-linear ordering, and sub-practitioner spawning for side
         research on exploration canvases)
      -> every verified, model-built step is examined by "could this be done
         cheaper?" and distilled into a SHORTCUT, so a very similar problem next
         time resolves at the reuse rung with zero model calls (self-improvement)
      -> with swarm > 1, N varied loops run and their graphs are ASSEMBLED INTO A
         MATRIX OF SOLUTIONS: each step's slot holds the members' different
         choices as type-compatible fallbacks, so if the preferred node for step
         2 fails at execution time, the matrix waterfalls to an alternative
         instead of collapsing.

Deterministic mode spends zero model tokens end to end; models mode uses the
council/debate at full output and OpenCode workers to author nodes — both run the
SAME loop under the SAME guards (reuse-first, verify-before-advance).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..strings.knowledge import Knowledge
from ..loop.canvas import (Canvas, CanvasNode, SolutionSlot, TypeContract,
                     execute_matrix)
from ..loop.practitioner_loop import (LoopState, PractitionerNode, NodeResult,
                                run_practitioner_loop, default_nodes,
                                make_model_nodes)
from ..loop.methodical import ExecutionDecision, reuse_first_guard, EXECUTION_LADDER
from ..code_nodes.self_improve import (ShortcutStore, Shortcut, problem_signature,
                           make_learning_probe)
from ..loop.context_shuffle import shuffle_lanes

SOLVER_MODES = ("deterministic", "models")


@dataclass
class SolveResult:
    goal: str
    mode: str
    graph: list = field(default_factory=list)
    canvas: "Canvas | None" = None
    steps: int = 0
    model_calls: int = 0
    model_calls_avoided: int = 0
    shortcuts_learned: int = 0
    shortcuts_replayed: int = 0
    swarm_members: int = 0
    sub_practitioners: int = 0

    def receipt(self) -> dict:
        return {"record_type": "universal_solve/v1", "goal": self.goal,
                "mode": self.mode, "graph_nodes": len(self.graph),
                "steps": self.steps, "model_calls": self.model_calls,
                "model_calls_avoided": self.model_calls_avoided,
                "shortcuts_learned": self.shortcuts_learned,
                "shortcuts_replayed": self.shortcuts_replayed,
                "swarm_members": self.swarm_members,
                "sub_practitioners": self.sub_practitioners,
                "canvas": self.canvas.canvas_id if self.canvas else None,
                "matrix_width": self.canvas.width() if self.canvas else 0}


class UniversalSolver:
    """The one solver.  Holds the learned-shortcut memory across solves so the
    system gets cheaper on problems it has seen the shape of before."""

    def __init__(self, *, shortcut_path: str | None = None,
                 mode: str = "deterministic",
                 models: Sequence[str] | None = None,
                 worker_model: str | None = None, work_dir: str = ".",
                 run_log_path: str | None = "auto",
                 tuning: "Any | None" = None):
        if mode not in SOLVER_MODES:
            raise ValueError(f"mode must be one of {SOLVER_MODES}")
        self.mode = mode
        self.models = list(models) if models else None
        self.worker_model = worker_model
        self.work_dir = work_dir
        self.shortcuts = ShortcutStore(shortcut_path)
        # every run of the DAG is documented (owner rule); "auto" resolves to a
        # JSONL beside the work dir; None switches documentation off explicitly.
        import os as _os
        self.run_log_path = (_os.path.join(work_dir, ".solver_runs.jsonl")
                             if run_log_path == "auto" else run_log_path)
        # tuning switchboard (all places OFF unless the caller turns them on)
        from ..loop.tuning import TuningPolicy
        self.tuning = tuning if tuning is not None else TuningPolicy()

    # -- node wiring -------------------------------------------------------

    def _nodes(self, goal: str) -> dict:
        """Build the practitioner nodes with the learning probe wired into node
        2's 'do we already have this?' — learned shortcuts ARE the reuse rung."""
        probe = make_learning_probe(self.shortcuts)(goal)
        if self.mode == "models":
            kw = {"registry_probe": probe, "work_dir": self.work_dir}
            if self.models:
                kw["models"] = self.models
            if self.worker_model:
                kw["worker_model"] = self.worker_model
            return make_model_nodes(**kw)
        nodes = default_nodes()
        inner = nodes["how_to_implement"].resolve

        def with_learning(state: LoopState) -> NodeResult:
            ans = state.blackboard.get("current_answer")
            if ans is not None:
                handle = probe(ans.target)
                if handle:
                    ex = ExecutionDecision("exact_reuse", rungs_checked=[],
                                           handle=handle,
                                           rationale="learned shortcut replay")
                    reuse_first_guard(ex)
                    state.model_calls_avoided += 1
                    state.blackboard["current_execution"] = ex
                    state.blackboard.setdefault("replayed", []).append(
                        ans.target)
                    return NodeResult("how_to_implement", output=ex,
                                      paths_tried=["muscle_memory"],
                                      detail=f"shortcut replay -> {handle}")
            return inner(state)

        nodes["how_to_implement"] = PractitionerNode("how_to_implement",
                                                     with_learning)
        return nodes

    # -- learning ----------------------------------------------------------

    def _learn(self, goal: str, state: LoopState) -> int:
        """Self-improvement pass: distill every verified model-built graph node
        into a shortcut.  Deterministic/free nodes teach nothing new; replayed
        shortcuts are not re-learned."""
        learned = 0
        replayed = set(state.blackboard.get("replayed", []))
        for node in state.graph:
            if not node.get("handle") or node["node"] in replayed:
                continue
            if node.get("via") in ("llm_authored", "llm", "llm_single",
                                   "llm_deliberation"):
                self.shortcuts.record(Shortcut(
                    signature=problem_signature(goal, node.get("kind",
                                                "add_node"), node["node"]),
                    rung="exact_reuse", handle=node["handle"],
                    model_calls_first_time=max(1, state.model_calls),
                    learned_from_goal=goal))
                learned += 1
        return learned

    # -- canvas assembly ---------------------------------------------------

    @staticmethod
    def _assemble_matrix(goal: str, member_graphs: Sequence[list]) -> Canvas:
        """Assemble swarm members' graphs into one MATRIX OF SOLUTIONS.

        Step i's slot takes every member's node for step i as a candidate — the
        members' diversity becomes the waterfall: if the preferred node for a
        step fails at execution time, a different member's compatible choice is
        already in the slot.  Positional type contracts keep adjacent slots
        connected."""
        canvas = Canvas(canvas_id=f"solution::{abs(hash(goal)) % 10 ** 8}",
                        kind="solution", provenance="universal_solver")
        depth = max((len(g) for g in member_graphs), default=0)
        for i in range(depth):
            contract = TypeContract(inputs=(f"S{i}",), outputs=(f"S{i + 1}",))
            slot = SolutionSlot(slot_id=f"step_{i + 1}", contract=contract)
            seen: set[str] = set()
            for g in member_graphs:
                if i < len(g):
                    name = g[i]["node"]
                    if name in seen:
                        continue
                    seen.add(name)
                    slot.add_candidate(CanvasNode(
                        name=name, contract=contract, run=None,
                        provenance=g[i].get("via", ""),
                        handle=g[i].get("handle", "")))
            canvas.add_slot(slot)
        return canvas

    # -- the front door ----------------------------------------------------

    def solve(self, goal: str, *, facts: dict | None = None,
              obligations: Sequence[str] = (), swarm: int = 0,
              max_steps: int = 60,
              graph_evaluate=None, graph_params=None) -> SolveResult:
        """Solve a task.  ``swarm`` > 1 runs that many varied practitioner loops
        and assembles their graphs into a matrix of solutions; otherwise one loop
        runs and the canvas is single-width."""
        n = max(1, int(swarm))
        frames = shuffle_lanes(goal, n=n) if n > 1 else []
        member_graphs: list[list] = []
        total_steps = total_calls = total_avoided = total_subs = 0
        replayed = 0
        last_state: "LoopState | None" = None
        for i in range(n):
            k = Knowledge(goal=goal, facts=dict(facts or {}),
                          open_obligations=tuple(obligations))
            if frames and i < len(frames):
                k = Knowledge(goal=goal, facts=dict(facts or {}),
                              open_obligations=tuple(obligations),
                              frame=frames[i].to_ask_frame(goal, k.frame))
            state = LoopState(knowledge=k)
            state = run_practitioner_loop(state, self._nodes(goal),
                                          max_steps=max_steps)
            member_graphs.append(state.graph)
            total_steps += len(state.history)
            total_calls += state.model_calls
            total_avoided += state.model_calls_avoided
            total_subs += len(state.blackboard.get("sub_practitioners", []))
            replayed += len(state.blackboard.get("replayed", []))
            last_state = state

        # self-improvement: distill what this solve paid for.
        learned = sum(self._learn(goal, LoopState(
            knowledge=Knowledge(goal=goal), graph=g,
            blackboard={"replayed": []}, model_calls=total_calls))
            for g in member_graphs) if self.mode == "models" else \
            (self._learn(goal, last_state) if last_state else 0)

        canvas = self._assemble_matrix(goal, member_graphs)
        primary = max(member_graphs, key=len) if member_graphs else []
        # TUNING (graph place, toggleable): with an evaluator + param space and
        # the switch on, tune around the finished graph; recorded, never silent.
        tuning_receipt = None
        if graph_evaluate is not None and graph_params:
            from ..loop.tuning import tune
            tr = tune(graph_params, graph_evaluate, place="graph",
                      policy=self.tuning)
            tuning_receipt = tr.receipt() if tr is not None else None
        result = SolveResult(goal=goal, mode=self.mode, graph=primary,
                           canvas=canvas, steps=total_steps,
                           model_calls=total_calls,
                           model_calls_avoided=total_avoided,
                           shortcuts_learned=learned,
                           shortcuts_replayed=replayed,
                           swarm_members=n, sub_practitioners=total_subs)
        # document EVERY run (append-only JSONL) so runs are shareable/learnable
        if self.run_log_path:
            import json as _json, os as _os
            rec = result.receipt()
            if tuning_receipt:
                rec["tuning"] = tuning_receipt
            _os.makedirs(_os.path.dirname(self.run_log_path) or ".",
                         exist_ok=True)
            with open(self.run_log_path, "a") as fh:
                fh.write(_json.dumps(rec) + "\n")
        return result


def solve(goal: str, **kw) -> SolveResult:
    """Module-level convenience: one call, one solver, one answer."""
    solver_kw = {k: kw.pop(k) for k in ("shortcut_path", "mode", "models",
                                        "worker_model", "work_dir",
                                        "run_log_path", "tuning")
                 if k in kw}
    return UniversalSolver(**solver_kw).solve(goal, **kw)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. one call solves end to end, zero model calls in deterministic mode.
    res = solve("build a churn model", obligations=("choose_model",))
    check("one_call_solves_a_task_with_zero_model_calls",
          res.graph and res.model_calls == 0 and res.steps > 0
          and res.canvas is not None and res.canvas.kind == "solution",
          f"{len(res.graph)} nodes built in {res.steps} steps on a solution "
          f"canvas, 0 model calls")

    # 2. SELF-IMPROVEMENT: a model-built solve teaches shortcuts; the SAME
    # solver solving a very similar problem replays them with fewer decisions.
    sv = UniversalSolver(mode="deterministic")
    # simulate a prior model-built lesson landing in its memory:
    sv.shortcuts.record(Shortcut(
        signature=problem_signature("build a churn model", "add_node",
                                    "address=choose_model"),
        rung="exact_reuse", handle="nodes/learned_choose_model.py",
        model_calls_first_time=3, learned_from_goal="build a churn model"))
    res2 = sv.solve("build a churn model", obligations=("choose_model",),
                    facts={"has_baseline": True, "leakage_checked": True})
    check("a_learned_shortcut_replays_and_avoids_model_calls",
          res2.shortcuts_replayed >= 1 and res2.model_calls == 0
          and any(n["via"] == "exact_reuse" for n in res2.graph),
          f"replayed {res2.shortcuts_replayed} learned route(s); the step "
          f"resolved at the reuse rung")

    # 3. swarm assembles a MATRIX OF SOLUTIONS with per-step fallbacks.
    res3 = solve("classify medical images of knees",
                 obligations=("choose_model",), swarm=3)
    check("a_swarm_assembles_a_matrix_of_solutions",
          res3.swarm_members == 3 and res3.canvas is not None
          and len(res3.canvas.slots) >= 1,
          f"3 members -> matrix of {len(res3.canvas.slots)} step(s), width "
          f"{res3.canvas.width()}")

    # 4. the assembled matrix EXECUTES with waterfall (wire runnable impls in).
    from ..loop.canvas import Canvas as _C
    m = UniversalSolver._assemble_matrix("g", [
        [{"node": "xgb", "kind": "add_node", "via": "reuse", "handle": "h1"}],
        [{"node": "lgbm", "kind": "add_node", "via": "reuse", "handle": "h2"}]])
    def crash(_x):
        raise RuntimeError("boom")
    m.slots[0].candidates[0].run = crash
    m.slots[0].candidates[1].run = lambda x: "ok"
    ex = execute_matrix(m, initial_input="data")
    check("the_matrix_waterfalls_when_the_preferred_node_fails",
          ex.ok and ex.waterfalls_used() == 1 and ex.output == "ok",
          "the second member's compatible node rescued the step")

    # 5. the receipt carries the full accounting.
    r = res.receipt()
    check("the_receipt_accounts_for_calls_avoided_learned_and_matrix_width",
          {"model_calls", "model_calls_avoided", "shortcuts_learned",
           "shortcuts_replayed", "matrix_width",
           "sub_practitioners"} <= set(r),
          "one receipt answers what ran, what it cost, what was avoided, and "
          "what was learned")

    # 6. an unknown mode is refused.
    bad = False
    try:
        UniversalSolver(mode="vibes")
    except ValueError:
        bad = True
    check("an_unknown_solver_mode_is_refused", bad,
          "modes are the closed set (deterministic, models)")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "universal_solver_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

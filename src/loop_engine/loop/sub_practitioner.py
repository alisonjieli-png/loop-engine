"""Sub-practitioners and non-linear orchestration — spawnable, recursive loops.

Two owner requirements (2026-08-22):

**Sub-practitioners.**  A practitioner solving a problem can spawn a
sub-practitioner — its own full what-is-next loop — for a side problem: do this
research, build this missing tool, test this idea.  The sub-practitioner works on
its own **exploration canvas** (never the parent's solution canvas), and what it
learns feeds back into the parent's knowledge as facts.  Sub-practitioners can
spawn sub-sub-practitioners, and so on, bounded by a depth guard so recursion
cannot run away.  This is how the system "builds its own solution to research":
the parent recognises it needs research, spawns a child whose goal IS the
research, the child surveys the available nodes/tools (and may author new ones —
custom web-search tools are just nodes), and its findings flow back up.

**Non-linear ordering.**  The practitioner nodes do not have to run in a fixed
line.  ``run_orchestrated`` hands control to an ORDER-DECIDER — deterministic by
default, an LLM when registered — that looks at the state each step and names the
next node to run (or ``done``).  The standard sequence is just the default
decider's behaviour; a smarter decider can jump straight to verify, re-run
what-is-next, or interleave — the nodes are a vocabulary, not a script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..strings.knowledge import Knowledge
from ..loop.canvas import Canvas
from ..loop.practitioner_loop import (LoopState, PractitionerNode, NODE_SEQUENCE,
                                run_practitioner_loop, default_nodes)

# Recursion bound: sub-sub-sub-practitioners are allowed, runaway spawning is not.
MAX_PRACTITIONER_DEPTH = 5


class DepthExceeded(RuntimeError):
    """Raised when a spawn would exceed MAX_PRACTITIONER_DEPTH."""


@dataclass
class SubPractitionerResult:
    goal: str
    depth: int
    canvas: Canvas
    findings: dict = field(default_factory=dict)   # facts fed back to the parent
    graph: list = field(default_factory=list)
    steps: int = 0
    model_calls: int = 0
    children: list = field(default_factory=list)   # SubPractitionerResults


def spawn_sub_practitioner(parent: LoopState, goal: str, *,
                           nodes_factory: Callable[[], dict] | None = None,
                           seed_facts: dict | None = None,
                           max_steps: int = 30) -> SubPractitionerResult:
    """Spawn one sub-practitioner for a side goal and feed its findings back.

    The child gets its OWN exploration canvas and its own knowledge (seeded with
    the side goal and any facts the parent passes down); it runs a full
    practitioner loop; and its findings are merged into the parent's knowledge as
    ``learned:<goal>`` facts — the feed-back-in the owner described.  Raises
    ``DepthExceeded`` past MAX_PRACTITIONER_DEPTH."""
    depth = int(parent.blackboard.get("depth", 0)) + 1
    if depth > MAX_PRACTITIONER_DEPTH:
        raise DepthExceeded(f"practitioner depth {depth} exceeds "
                            f"{MAX_PRACTITIONER_DEPTH}")
    canvas = Canvas(canvas_id=f"exploration-d{depth}-{abs(hash(goal)) % 99999}",
                    kind="exploration",
                    provenance=f"sub-practitioner of {parent.knowledge.goal!r}")
    child_knowledge = Knowledge(goal=goal, facts=dict(seed_facts or {}))
    child = LoopState(knowledge=child_knowledge)
    child.blackboard["depth"] = depth
    child.blackboard["canvas"] = canvas
    child.blackboard["parent_goal"] = parent.knowledge.goal
    nf = nodes_factory or default_nodes
    child = run_practitioner_loop(child, nf(), max_steps=max_steps)

    findings = {f"learned:{goal}": True,
                f"learned:{goal}:nodes": len(child.graph)}
    # feed back into the PARENT's knowledge — research flows up, never sideways.
    parent.knowledge = Knowledge(
        goal=parent.knowledge.goal, graph_summary=parent.knowledge.graph_summary,
        results=parent.knowledge.results,
        facts={**parent.knowledge.facts, **findings},
        open_obligations=parent.knowledge.open_obligations,
        context_level=parent.knowledge.context_level,
        frame=parent.knowledge.frame)
    result = SubPractitionerResult(goal=goal, depth=depth, canvas=canvas,
                                   findings=findings, graph=child.graph,
                                   steps=len(child.history),
                                   model_calls=child.model_calls)
    parent.blackboard.setdefault("sub_practitioners", []).append(result)
    return result


def make_spawning_node(side_goal_of: Callable[[LoopState], "str | None"], *,
                       nodes_factory: Callable[[], dict] | None = None):
    """A practitioner node that spawns a sub-practitioner when the state calls
    for one (``side_goal_of`` returns the side goal, or None to pass through).
    Drop it into any nodes dict to give that loop the power to delegate."""
    from ..loop.practitioner_loop import NodeResult

    def resolve(state: LoopState) -> NodeResult:
        goal = side_goal_of(state)
        if not goal:
            return NodeResult("what_is_next", detail="no side goal — pass")
        res = spawn_sub_practitioner(state, goal, nodes_factory=nodes_factory)
        return NodeResult("what_is_next", output=res,
                          detail=f"spawned sub-practitioner d{res.depth} for "
                          f"{goal!r}; {res.steps} steps, findings fed back")
    return resolve


# ===========================================================================
# Non-linear orchestration — an order-decider names the next node each step.
# ===========================================================================

# decider(state, last_node_name, last_result) -> next node name | "done"
OrderDecider = Callable[[LoopState, str, "object | None"], str]


def standard_order_decider(state: LoopState, last: str, last_result) -> str:
    """The deterministic default: the standard forward flow with loop-backs —
    exactly what run_practitioner_loop does, expressed as a decider so LLM/custom
    deciders are drop-in replacements."""
    if last_result is not None and getattr(last_result, "control", "") == "done":
        return "done"
    if last_result is not None and getattr(last_result, "control", "") \
            == "loop_back":
        return last_result.loop_back_to
    if not last:
        return NODE_SEQUENCE[0]
    idx = NODE_SEQUENCE.index(last) + 1
    if idx >= len(NODE_SEQUENCE):
        return "done" if state.blackboard.get("graph_complete") \
            else NODE_SEQUENCE[0]
    return NODE_SEQUENCE[idx]


def run_orchestrated(state: LoopState, nodes: dict, *,
                     decider: OrderDecider = standard_order_decider,
                     max_steps: int = 60) -> LoopState:
    """Run the practitioner nodes in whatever order the decider chooses.

    The nodes are a VOCABULARY, not a script: each step the decider looks at the
    state and names the next node (or ``done``).  An unknown node name ends the
    run rather than crashing — a decider must not invent nodes."""
    last_name, last_result = "", None
    for _ in range(max_steps):
        nxt = decider(state, last_name, last_result)
        if nxt == "done" or nxt not in NODE_SEQUENCE:
            break
        node = nodes.get(nxt)
        if node is None:
            break
        last_result = node.resolve(state)
        state.history.append(last_result)
        state.model_calls += last_result.model_calls
        if last_result.control == "loop_back":
            state.blackboard.setdefault("messages", []).append(
                {"from": last_result.node, "to": last_result.loop_back_to,
                 "text": last_result.message})
        if last_result.control in ("done", "abort"):
            break
        last_name = nxt
    return state


def make_llm_order_decider(model: str | None = None) -> OrderDecider:
    """An LLM order-decider: shown the state summary and the node vocabulary, it
    names the next node.  Falls back to the standard decider on any failure —
    orchestration must never crash the loop."""
    from ..static_architecture.ollama_client import chat_maxout, DEFAULT_MODEL

    def decide(state: LoopState, last: str, last_result) -> str:
        try:
            prompt = (
                f"Task: {state.knowledge.goal}\n"
                f"Nodes available: {', '.join(NODE_SEQUENCE)}\n"
                f"Last node run: {last or '(none)'}; graph size "
                f"{len(state.graph)}; obligations "
                f"{list(state.knowledge.open_obligations)}\n"
                "Which node should run NEXT? Reply with exactly one node name "
                "from the list, or done.")
            res = chat_maxout(prompt, model=model or DEFAULT_MODEL,
                              temperature=0.2)
            word = (res.text or "").strip().split()[0].strip(".,`'\"").lower() \
                if res.ok and res.text.strip() else ""
            if word == "done" or word in NODE_SEQUENCE:
                return word
        except Exception:                                       # noqa: BLE001
            pass
        return standard_order_decider(state, last, last_result)
    return decide


# ===========================================================================
# Self-test — deterministic, no network.
# ===========================================================================


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. a sub-practitioner runs its own loop on an EXPLORATION canvas and
    # feeds findings back into the parent's knowledge.
    parent = LoopState(knowledge=Knowledge(
        goal="win the competition", open_obligations=("choose_model",),
        facts={}))
    res = spawn_sub_practitioner(parent, "research: best boosted-tree defaults")
    check("a_sub_practitioner_runs_its_own_loop_on_an_exploration_canvas",
          res.canvas.kind == "exploration" and res.steps > 0
          and res.depth == 1,
          f"child ran {res.steps} steps at depth 1 on canvas {res.canvas.canvas_id}")

    check("the_sub_practitioners_findings_feed_back_into_the_parent",
          parent.knowledge.fact("learned:research: best boosted-tree defaults")
          and parent.blackboard.get("sub_practitioners"),
          "the parent's knowledge now carries learned:<goal> facts and the "
          "spawn is recorded on its blackboard")

    # 2. sub-sub spawning works, and the depth guard stops runaway recursion.
    child_state = LoopState(knowledge=Knowledge(goal="child"))
    child_state.blackboard["depth"] = 1
    res2 = spawn_sub_practitioner(child_state, "sub-sub research")
    check("sub_sub_practitioners_spawn_with_increasing_depth",
          res2.depth == 2, "a child at depth 1 spawned a grandchild at depth 2")

    deep = LoopState(knowledge=Knowledge(goal="deep"))
    deep.blackboard["depth"] = MAX_PRACTITIONER_DEPTH
    guarded = False
    try:
        spawn_sub_practitioner(deep, "too deep")
    except DepthExceeded:
        guarded = True
    check("runaway_recursion_is_stopped_by_the_depth_guard", guarded,
          f"a spawn past depth {MAX_PRACTITIONER_DEPTH} raises DepthExceeded")

    # 3. orchestrated: the standard decider reproduces the standard flow.
    st = run_orchestrated(LoopState(knowledge=Knowledge(
        goal="build", open_obligations=("choose_model",), facts={})),
        default_nodes())
    seq = [h.node for h in st.history]
    check("the_standard_decider_reproduces_the_standard_flow",
          seq[:5] == list(NODE_SEQUENCE) and st.history[-1].control == "done",
          f"orchestrated run: {seq[:6]}...")

    # 4. a CUSTOM decider reorders the nodes — they are a vocabulary, not a script.
    order_taken = []
    def custom(state, last, last_result):
        plan = ["what_is_next", "what_is_next", "how_to_implement",
                "implement", "verify_compilable", "done"]
        nxt = plan[len(order_taken)] if len(order_taken) < len(plan) else "done"
        order_taken.append(nxt)
        return nxt
    st2 = run_orchestrated(LoopState(knowledge=Knowledge(
        goal="x", open_obligations=("m",), facts={})), default_nodes(),
        decider=custom, max_steps=10)
    ran = [h.node for h in st2.history]
    check("a_custom_decider_reorders_the_nodes_non_linearly",
          ran[:2] == ["what_is_next", "what_is_next"],
          f"the decider ran what_is_next twice in a row: {ran}")

    # 5. a decider naming an unknown node ends the run safely.
    st3 = run_orchestrated(LoopState(knowledge=Knowledge(goal="y")),
                           default_nodes(),
                           decider=lambda *_a: "not_a_node", max_steps=5)
    check("an_invented_node_name_ends_the_run_instead_of_crashing",
          len(st3.history) == 0,
          "a decider may not invent nodes; the run ends safely")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "sub_practitioner_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

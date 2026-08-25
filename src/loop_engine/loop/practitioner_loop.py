"""The practitioner loop — the main intelligence execution path, as a node DAG.

The owner's model (2026-08-22): the single "what is next?" question is the spine,
but the main path is a small DAG of nodes, each with MANY resolution paths, and
with loop-back edges so a later node can talk to an earlier one.

    (1) what_is_next  ->  (2) how_to_implement  ->  (3) implement
                                     |                      |
                                     | research            | can't build
                                     v                      v
                              back to (1)            back to (2)/(3)
                                                            |
    (5) save  <-  (4) verify_compilable  <---- ------- -----+
       |                    | not correct
       |                    v
       +--> back to (1)   back to (3)

Each NODE has a set of resolution PATHS (deterministic / heuristic / embedding /
micro-model / small-model / LLM / hybrid / reuse / research / custom), tried
reuse-first.  A node returns a control signal — advance, loop_back (to a named
earlier node, with a message), done, or abort — so the loop is a real state
machine, not a straight line.  Two behaviours the owner called out are first-class:

  * node 2, when its answer is **research**, does NOT build — it loops straight
    back to node 1 and feeds the findings in (sometimes we only need to learn);
  * any node that gets stuck loops back to the node(s) before it with a message,
    rather than failing the whole run.

Swarm and tuning ride on top of one loop: ``swarm_practitioner`` runs N loops with
varied context/persona/seed and lets the fold oracle pick; tuning is either the
``optimize`` answer-kind inside node 1 or a per-candidate search around a finished
graph (see ``TUNING_DESIGN``).  One loop stays simple; the scale lives outside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..strings.knowledge import Knowledge
from ..loop.methodical import (NextAnswer, ExecutionDecision, VerifyResult,
                         EXECUTION_LADDER, ANSWER_KINDS, reuse_first_guard,
                         det_decide, det_resolve)


# ===========================================================================
# TAXONOMIES.
# ===========================================================================

# The nodes of the main practitioner DAG, in forward order.
NODE_SEQUENCE = ("what_is_next", "how_to_implement", "implement",
                 "verify_compilable", "save")

# The control signal a node returns — this is what makes loop-backs possible.
CONTROL_SIGNALS = ("advance", "loop_back", "done", "abort")

# The resolution PATHS available to any node (each node uses the subset that
# makes sense for it).  Reuse-first: earlier is cheaper / more deterministic.
RESOLUTION_PATHS = ("cached", "muscle_memory", "deterministic", "reuse_drop_in",
                    "template_mutate", "embedding", "heuristic", "micro_model",
                    "small_model", "hybrid", "llm", "research", "custom")

# Where tuning lives (design note, surfaced in the receipt / docs).
TUNING_DESIGN = (
    "Tuning is not a special place in the main loop.  It appears two ways: (a) as "
    "the 'optimize' answer-kind of what_is_next, which the loop implements like "
    "any other node; and (b) as a per-CANDIDATE search AROUND a finished "
    "compilable graph — each swarm member's graph is tuned independently and in "
    "parallel, so a 20-node x 5-param space is explored per candidate by grid or "
    "heuristic search, never inside the single decision loop.")


# ===========================================================================
# Records.
# ===========================================================================


@dataclass
class NodeResult:
    node: str
    output: Any = None
    control: str = "advance"
    loop_back_to: str = ""
    message: str = ""
    paths_tried: list = field(default_factory=list)
    model_calls: int = 0
    detail: str = ""

    def __post_init__(self):
        if self.control not in CONTROL_SIGNALS:
            raise ValueError(f"unknown control signal {self.control!r}")
        if self.control == "loop_back" and self.loop_back_to not in NODE_SEQUENCE:
            raise ValueError(f"loop_back_to must be a node; got "
                             f"{self.loop_back_to!r}")


@dataclass
class LoopState:
    """The shared state one practitioner loop carries across its nodes."""
    knowledge: Knowledge
    graph: list = field(default_factory=list)     # implemented nodes so far
    blackboard: dict = field(default_factory=dict)  # cross-node scratch + messages
    history: list = field(default_factory=list)   # NodeResults, in run order
    model_calls: int = 0
    model_calls_avoided: int = 0

    def messages_to(self, node: str) -> list:
        return [m for m in self.blackboard.get("messages", [])
                if m["to"] == node]


@dataclass
class PractitionerNode:
    name: str
    resolve: Callable[[LoopState], NodeResult]


# ===========================================================================
# The loop executor — a state machine with loop-backs and a step budget.
# ===========================================================================


def detect_logjam(state: LoopState, *, window: int = 8) -> str:
    """Is the loop stuck?  Two smells, both deterministic: the same node keeps
    being looped back to (>= 3 times in the window), or a full window of steps
    passed with the graph not growing.  Returns the reason, or '' if healthy."""
    recent = state.history[-window:]
    if len(recent) < window:
        return ""
    targets = [r.loop_back_to for r in recent if r.control == "loop_back"]
    for t in set(targets):
        if targets.count(t) >= 3:
            return f"looped back to {t!r} {targets.count(t)}x in {window} steps"
    start_size = state.blackboard.get("_graph_size_at_window", None)
    if start_size is not None and len(state.graph) <= start_size:
        return f"no graph growth across {window} steps"
    return ""


def logjam_reset(state: LoopState, reason: str, reset_index: int) -> None:
    """The documented reset — the organisational 'bring in a whole new person'.

    First DOCUMENT the failure (why we were stuck, at what step, with what
    pending messages) — a reset without a documented failure learns nothing.
    Then reset: clear the pending messages, and give the loop a NEW frame — a
    different distant-domain archetype (deterministically varied by reset index,
    the random-sprout without a clock) — a fresh set of eyes on the same goal."""
    from ..loop.context_shuffle import shuffle_lanes
    state.blackboard.setdefault("logjam_log", []).append({
        "reason": reason, "at_step": len(state.history),
        "graph_size": len(state.graph),
        "pending_messages": list(state.blackboard.get("messages", []))[-5:],
        "reset_index": reset_index})
    state.blackboard["messages"] = []
    lanes = shuffle_lanes(state.knowledge.goal, n=reset_index + 1,
                          salt=f"logjam{reset_index}")
    frame = lanes[min(reset_index, len(lanes) - 1)].to_ask_frame(
        state.knowledge.goal, state.knowledge.frame)
    state.knowledge = Knowledge(
        goal=state.knowledge.goal, graph_summary=state.knowledge.graph_summary,
        results=state.knowledge.results, facts=state.knowledge.facts,
        open_obligations=state.knowledge.open_obligations,
        context_level=state.knowledge.context_level, frame=frame)


def run_practitioner_loop(state: LoopState, nodes: dict, *,
                          max_steps: int = 60, max_resets: int = 2,
                          logjam_window: int = 8) -> LoopState:
    """Run the practitioner DAG as a state machine until done/abort/budget.

    Follows NODE_SEQUENCE forward on ``advance``; jumps to ``loop_back_to`` on
    ``loop_back`` (recording the message for that node to read); stops on ``done``
    or ``abort``.  ``max_steps`` bounds loop-back cycles so a stuck pair of nodes
    cannot spin forever.  A detected LOGJAM triggers a documented reset with a
    fresh frame (up to ``max_resets``); past that the loop aborts honestly with
    the failure log rather than spinning."""
    idx = 0
    steps_since_check = 0
    resets = 0
    state.blackboard["_graph_size_at_window"] = len(state.graph)
    for _ in range(max_steps):
        steps_since_check += 1
        if steps_since_check >= logjam_window:
            reason = detect_logjam(state, window=logjam_window)
            if reason:
                if resets >= max_resets:
                    state.blackboard.setdefault("logjam_log", []).append(
                        {"reason": reason, "gave_up": True,
                         "at_step": len(state.history)})
                    state.history.append(NodeResult(
                        NODE_SEQUENCE[idx], control="abort",
                        detail=f"logjam after {resets} resets: {reason}"))
                    break
                resets += 1
                logjam_reset(state, reason, resets)
                idx = 0                       # a new person starts at the top
            steps_since_check = 0
            state.blackboard["_graph_size_at_window"] = len(state.graph)
        name = NODE_SEQUENCE[idx]
        node = nodes.get(name)
        if node is None:                          # node not provided -> skip it
            idx += 1
            if idx >= len(NODE_SEQUENCE):
                break
            continue
        res = node.resolve(state)
        state.history.append(res)
        state.model_calls += res.model_calls
        if res.control == "done":
            break
        if res.control == "abort":
            break
        if res.control == "loop_back":
            state.blackboard.setdefault("messages", []).append(
                {"from": res.node, "to": res.loop_back_to, "text": res.message})
            idx = NODE_SEQUENCE.index(res.loop_back_to)
            continue
        # advance
        idx += 1
        if idx >= len(NODE_SEQUENCE):
            # completed a full pass (save) -> loop back to what_is_next for the
            # NEXT sub-task, unless the graph is marked complete.
            if state.blackboard.get("graph_complete"):
                break
            idx = 0
    return state


# ===========================================================================
# Deterministic default nodes — zero model, testable, honour the ontology.
# ===========================================================================


def node_what_is_next(state: LoopState) -> NodeResult:
    """Node 1: decide the next sub-task.  Terminate ends the loop."""
    # Absorb any research fed back from node 2 before deciding again.
    fed = state.messages_to("what_is_next")
    if fed:
        state.knowledge = Knowledge(
            goal=state.knowledge.goal, graph_summary=state.knowledge.graph_summary,
            results=state.knowledge.results,
            facts={**state.knowledge.facts, "research_absorbed": True},
            open_obligations=state.knowledge.open_obligations,
            context_level=state.knowledge.context_level, frame=state.knowledge.frame)
    ans = det_decide(state.knowledge)
    if ans.kind == "terminate":
        state.blackboard["graph_complete"] = True
        return NodeResult("what_is_next", output=ans, control="done",
                          paths_tried=["deterministic"],
                          detail="nothing left — deliver")
    state.blackboard["current_answer"] = ans
    return NodeResult("what_is_next", output=ans, paths_tried=["deterministic"],
                      detail=f"[{ans.kind}] {ans.target}")


def node_how_to_implement(state: LoopState) -> NodeResult:
    """Node 2: reuse-first implementation route.  Research loops back to node 1."""
    ans: NextAnswer = state.blackboard["current_answer"]
    ex = det_resolve(state.knowledge, ans)
    reuse_first_guard(ex)
    if ex.is_free():
        state.model_calls_avoided += 1
    # If the best route is research, we don't build — feed back to what_is_next.
    if ans.kind == "research" or ex.chosen == "research":
        return NodeResult("how_to_implement", output=ex, control="loop_back",
                          loop_back_to="what_is_next",
                          message=f"research on {ans.target} done; re-decide",
                          paths_tried=[ex.chosen],
                          detail="research route — loop back, do not build")
    state.blackboard["current_execution"] = ex
    return NodeResult("how_to_implement", output=ex, paths_tried=[ex.chosen],
                      model_calls=ex.model_calls,
                      detail=f"route={ex.chosen} handle={ex.handle}")


def node_implement(state: LoopState) -> NodeResult:
    """Node 3: wire the answer into the solution graph (deterministic here)."""
    ans: NextAnswer = state.blackboard["current_answer"]
    ex: ExecutionDecision = state.blackboard["current_execution"]
    if not ex.handle:                             # can't build -> loop back to 2
        return NodeResult("implement", control="loop_back",
                          loop_back_to="how_to_implement",
                          message=f"no handle for {ans.target}; find another route",
                          detail="implementation blocked")
    built = {"node": ans.target, "kind": ans.kind, "via": ex.chosen,
             "handle": ex.handle}
    state.graph.append(built)
    # Record the EFFECT of implementing this node so the next what_is_next sees
    # progress and does not re-propose the same step (a node must record what it
    # accomplished, or the loop cannot advance).
    new_facts = {**state.knowledge.facts,
                 f"registry_has:{ans.target}": ex.handle, "has_baseline": True}
    if "leakage" in ans.target.lower() or ans.kind == "adversarially_validate":
        new_facts["leakage_checked"] = True
    # this obligation is now addressed
    remaining = tuple(o for o in state.knowledge.open_obligations
                      if o not in ans.target)
    state.knowledge = Knowledge(
        goal=state.knowledge.goal, graph_summary=f"{len(state.graph)} nodes",
        results=state.knowledge.results, facts=new_facts,
        open_obligations=remaining, context_level=state.knowledge.context_level,
        frame=state.knowledge.frame)
    return NodeResult("implement", output=built, paths_tried=[ex.chosen],
                      detail=f"added node {ans.target} ({len(state.graph)} total)")


def node_verify_compilable(state: LoopState) -> NodeResult:
    """Node 4: did the graph stay compilable?  A broken edge loops back to node 3."""
    last = state.graph[-1] if state.graph else None
    if last is None:
        return NodeResult("verify_compilable", control="loop_back",
                          loop_back_to="implement", message="nothing was built",
                          detail="empty graph")
    # Contract check: every built node needs a concrete handle and known kind.
    ok = bool(last.get("handle")) and last.get("kind") in ANSWER_KINDS
    if not ok:
        return NodeResult("verify_compilable", control="loop_back",
                          loop_back_to="implement",
                          message=f"node {last.get('node')} fails its contract",
                          detail="contract violation")
    return NodeResult("verify_compilable", output=VerifyResult(
        "correct_and_ready", "node satisfies its contract", True),
        paths_tried=["deterministic", "contract"],
        detail="graph is compilable")


def node_save(state: LoopState) -> NodeResult:
    """Node 5: record the accepted step, then the loop continues to node 1."""
    state.blackboard.setdefault("saved", []).append(
        {"graph_size": len(state.graph)})
    return NodeResult("save", detail=f"saved checkpoint ({len(state.graph)} nodes)")


def default_nodes() -> dict:
    return {"what_is_next": PractitionerNode("what_is_next", node_what_is_next),
            "how_to_implement": PractitionerNode("how_to_implement",
                                                node_how_to_implement),
            "implement": PractitionerNode("implement", node_implement),
            "verify_compilable": PractitionerNode("verify_compilable",
                                                 node_verify_compilable),
            "save": PractitionerNode("save", node_save)}


def run_default(knowledge: Knowledge, *, max_steps: int = 60) -> LoopState:
    return run_practitioner_loop(LoopState(knowledge=knowledge), default_nodes(),
                                 max_steps=max_steps)


# ===========================================================================
# Swarm — N loops with varied context/persona/seed; the fold oracle picks.
# ===========================================================================


def swarm_practitioner(knowledge: Knowledge, *, n: int = 3,
                       nodes_factory: Callable[[], dict] | None = None,
                       vary: Callable[[Knowledge, int], Knowledge] | None = None,
                       max_steps: int = 60) -> dict:
    """Run N practitioner loops that differ by context/persona/seed and collect
    their graphs.  This is how swarm + non-determinism are handled: many loops,
    each internally simple; selection among their outputs is a separate,
    oracle-driven step (never 'trust the loop that sounds best').  Returns the
    per-member graphs and the union of nodes discovered."""
    nf = nodes_factory or default_nodes
    vf = vary or (lambda k, i: k)
    members = []
    for i in range(n):
        st = run_practitioner_loop(LoopState(knowledge=vf(knowledge, i)), nf(),
                                   max_steps=max_steps)
        members.append({"member": i, "graph": st.graph,
                        "steps": len(st.history),
                        "model_calls": st.model_calls,
                        "model_calls_avoided": st.model_calls_avoided})
    union = {}
    for m in members:
        for node in m["graph"]:
            union[node["node"]] = node
    return {"record_type": "practitioner_swarm/v1", "n": n, "members": members,
            "union_nodes": list(union.values()), "union_size": len(union)}


# ===========================================================================
# Model-backed nodes — the REAL execution path: node 1 debates, node 2 probes the
# registry reuse-first, node 3 has an OpenCode worker author a real node file,
# node 4 actually compiles it.  This is what makes the loop build real code.
# ===========================================================================


def make_model_nodes(*, models: Sequence[str] | None = None,
                     worker_model: str = "ollama-cloud/kimi-k2.7-code:cloud",
                     work_dir: str = ".", questions: Sequence[str] = (),
                     rounds: int = 2,
                     registry_probe: Callable[[str], str] | None = None,
                     author: Callable[[str, str], "AgentResult | None"] | None
                     = None) -> dict:
    """Build the five practitioner nodes backed by real models + OpenCode.

    node 1 runs a debate to decide what is next; node 2 asks the registry_probe
    "do we already have this?" (reuse-first) and escalates only if not; node 3
    drops in a reused node OR has an OpenCode worker author ``nodes/<slug>.py``;
    node 4 actually ``py_compile``s the authored file and loops back to node 3
    with the error if it will not compile.  ``author`` defaults to a real OpenCode
    worker; inject a stub to test offline."""
    import os
    import py_compile
    from ..loop.methodical import make_model_cycle
    from ..static_architecture.opencode_client import run_agent
    probe = registry_probe or (lambda _t: "")
    cycle = make_model_cycle(models, questions=questions, rounds=rounds,
                             registry_probe=probe)

    def _author(slug: str, spec: str):
        path = os.path.join(work_dir, "nodes", slug + ".py")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        task = (f"Write a Python module at nodes/{slug}.py exposing a function "
                f"that implements: {spec}. Pure function, typed, with a short "
                f"docstring and a __main__ smoke test. No external imports beyond "
                f"numpy/pandas. Make it import-clean.")
        return run_agent(task, model=worker_model, cwd=work_dir, timeout=420)

    author_fn = author or _author

    def n1(state: LoopState) -> NodeResult:
        ans = cycle["decide"](state.knowledge)
        if ans.kind == "terminate":
            state.blackboard["graph_complete"] = True
            return NodeResult("what_is_next", output=ans, control="done",
                              paths_tried=["llm_deliberation"])
        state.blackboard["current_answer"] = ans
        return NodeResult("what_is_next", output=ans,
                          paths_tried=["llm_deliberation"],
                          model_calls=len(list(models or [1, 2, 3])) * rounds,
                          detail=f"[{ans.kind}] {ans.target}")

    def n2(state: LoopState) -> NodeResult:
        ans = state.blackboard["current_answer"]
        ex = cycle["resolve"](state.knowledge, ans)
        reuse_first_guard(ex)
        if ex.is_free():
            state.model_calls_avoided += 1
        if ans.kind == "research" or ex.chosen == "research":
            return NodeResult("how_to_implement", output=ex, control="loop_back",
                              loop_back_to="what_is_next",
                              message=f"research on {ans.target}; re-decide",
                              paths_tried=[ex.chosen])
        state.blackboard["current_execution"] = ex
        return NodeResult("how_to_implement", output=ex, paths_tried=[ex.chosen],
                          model_calls=ex.model_calls)

    def n3(state: LoopState) -> NodeResult:
        ans = state.blackboard["current_answer"]
        ex = state.blackboard["current_execution"]
        slug = "".join(c if c.isalnum() else "_" for c in ans.target)[:40]
        if ex.chosen == "exact_reuse":
            built = {"node": ans.target, "kind": ans.kind, "via": "exact_reuse",
                     "handle": ex.handle}
            state.graph.append(built)
            return NodeResult("implement", output=built,
                              paths_tried=["reuse_drop_in"],
                              detail=f"dropped in {ex.handle}")
        res = author_fn(slug, f"{ans.kind}: {ans.target} — {ans.rationale}")
        if res is None or not getattr(res, "ok", False):
            return NodeResult("implement", control="loop_back",
                              loop_back_to="how_to_implement",
                              message=f"authoring failed for {ans.target}",
                              detail="worker could not author the node")
        built = {"node": ans.target, "kind": ans.kind, "via": "llm_authored",
                 "handle": f"nodes/{slug}.py"}
        state.graph.append(built)
        state.blackboard["last_file"] = built["handle"]
        return NodeResult("implement", output=built, paths_tried=["llm"],
                          model_calls=1, detail=f"authored {built['handle']}")

    def n4(state: LoopState) -> NodeResult:
        import os as _os
        path = state.blackboard.get("last_file", "")
        last = state.graph[-1] if state.graph else None
        if last and last["via"] == "exact_reuse":
            return NodeResult("verify_compilable", detail="reused node — compiled")
        full = _os.path.join(work_dir, path) if path else ""
        if not full or not _os.path.exists(full):
            return NodeResult("verify_compilable", control="loop_back",
                              loop_back_to="implement",
                              message="no authored file to compile")
        try:
            py_compile.compile(full, doraise=True)
        except py_compile.PyCompileError as exc:
            return NodeResult("verify_compilable", control="loop_back",
                              loop_back_to="implement",
                              message=f"does not compile: {str(exc)[:200]}",
                              detail="compile failed")
        # mark progress so the next what_is_next advances
        state.knowledge = Knowledge(
            goal=state.knowledge.goal, graph_summary=f"{len(state.graph)} nodes",
            results=state.knowledge.results,
            facts={**state.knowledge.facts, "has_baseline": True,
                   f"registry_has:{last['node']}": last["handle"]},
            open_obligations=tuple(o for o in state.knowledge.open_obligations
                                   if o not in last["node"]),
            context_level=state.knowledge.context_level, frame=state.knowledge.frame)
        return NodeResult("verify_compilable", paths_tried=["deterministic",
                          "py_compile"], detail=f"{path} compiles")

    def n5(state: LoopState) -> NodeResult:
        state.blackboard.setdefault("saved", []).append(
            {"graph_size": len(state.graph)})
        return NodeResult("save", detail=f"saved ({len(state.graph)} nodes)")

    return {"what_is_next": PractitionerNode("what_is_next", n1),
            "how_to_implement": PractitionerNode("how_to_implement", n2),
            "implement": PractitionerNode("implement", n3),
            "verify_compilable": PractitionerNode("verify_compilable", n4),
            "save": PractitionerNode("save", n5)}


# ===========================================================================
# Self-test — deterministic, no network.
# ===========================================================================


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. a full loop runs the nodes in forward order and terminates.
    k = Knowledge(goal="build a churn model",
                  open_obligations=("choose_model",), facts={})
    st = run_default(k)
    order = [h.node for h in st.history]
    check("the_loop_runs_the_node_dag_and_terminates",
          "what_is_next" in order and "how_to_implement" in order
          and "implement" in order and "verify_compilable" in order
          and order[-1] == "what_is_next"
          and st.history[-1].control == "done",
          f"node order: {order}")

    # 2. a node was actually built into the solution graph.
    check("an_answer_is_implemented_into_the_solution_graph",
          len(st.graph) >= 1 and st.graph[0].get("handle"),
          f"graph has {len(st.graph)} built node(s)")

    # 3. reuse-first: with a registry hit, node 2 resolves free (no model).
    k2 = Knowledge(goal="x", open_obligations=("choose_model",),
                   facts={"registry_has:address=choose_model": "hgb_v3"})
    st2 = run_default(k2)
    check("node_two_reuses_an_existing_node_with_no_model_call",
          st2.model_calls_avoided >= 1
          and any(n["via"] == "exact_reuse" for n in st2.graph),
          "'do we already have this?' hit the registry and dropped it in free")

    # 4. RESEARCH loops back to node 1 without building.
    research_seen = {"n": 0}
    def research_node2(state):
        state.blackboard["current_answer"] = NextAnswer(
            "research", "best_practice_x", "need evidence")
        research_seen["n"] += 1
        if research_seen["n"] == 1:
            return NodeResult("how_to_implement", control="loop_back",
                              loop_back_to="what_is_next",
                              message="researched; re-decide")
        # second time: pretend research produced a buildable answer
        state.blackboard["current_answer"] = NextAnswer("add_node", "model=hgb")
        state.blackboard["current_execution"] = ExecutionDecision(
            "deterministic_wrapper", rungs_checked=["exact_reuse"],
            handle="wrapper::hgb")
        return NodeResult("how_to_implement", detail="now buildable")
    nodes = default_nodes()
    nodes["how_to_implement"] = PractitionerNode("how_to_implement", research_node2)
    st3 = run_practitioner_loop(LoopState(knowledge=Knowledge(
        goal="y", open_obligations=("m",), facts={"has_baseline": True})),
        nodes, max_steps=30)
    msgs = st3.blackboard.get("messages", [])
    check("research_loops_back_to_what_is_next_without_building",
          any(m["from"] == "how_to_implement" and m["to"] == "what_is_next"
              for m in msgs),
          "node 2 with a research answer looped straight back to node 1")

    # 5. a failed verify loops back to implement.
    def bad_implement(state):
        state.graph.append({"node": "x", "kind": "add_node", "via": "llm",
                            "handle": ""})     # empty handle -> contract fails
        return NodeResult("implement", output={})
    nodes2 = default_nodes()
    nodes2["implement"] = PractitionerNode("implement", bad_implement)
    # give node1 a single obligation then terminate; force one build attempt
    st4 = run_practitioner_loop(LoopState(knowledge=Knowledge(
        goal="z", open_obligations=("m",), facts={})), nodes2, max_steps=8)
    check("a_failed_verify_loops_back_to_implement",
          any(h.node == "verify_compilable" and h.control == "loop_back"
              and h.loop_back_to == "implement" for h in st4.history),
          "verify_compilable rejected a contract-violating node and returned "
          "control to implement")

    # 6. inter-node messages are recorded for the target node to read.
    check("nodes_communicate_backward_via_recorded_messages",
          "messages" in st3.blackboard and st3.blackboard["messages"],
          "loop-back messages are stored on the blackboard addressed to a node")

    # 7. swarm runs N loops and unions their graphs.
    sw = swarm_practitioner(k, n=3)
    check("swarm_runs_n_loops_and_unions_their_graphs",
          sw["n"] == 3 and len(sw["members"]) == 3 and sw["union_size"] >= 1,
          f"{sw['n']} members, union of {sw['union_size']} node(s)")

    # 8. a loop-back to a non-node is rejected at construction.
    bad = False
    try:
        NodeResult("implement", control="loop_back", loop_back_to="nowhere")
    except ValueError:
        bad = True
    check("a_loop_back_to_an_unknown_node_is_rejected", bad,
          "loop_back_to must name a real node in the sequence")

    # 9. model-backed node 3 authors a file and node 4 REALLY compiles it — with
    # a stub author (no network), proving the author->compile wiring end to end.
    import tempfile, os as _os
    from ..static_architecture.opencode_client import AgentResult
    with tempfile.TemporaryDirectory() as d:
        def stub_author(slug, spec):
            p = _os.path.join(d, "nodes", slug + ".py")
            _os.makedirs(_os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write("def run(x):\n    \"\"\"stub\"\"\"\n    return x * 2\n")
            return AgentResult(ok=True, model="stub", output="", exit_code=0,
                               seconds=0.0)
        mnodes = make_model_nodes(work_dir=d, author=stub_author)
        stt = LoopState(knowledge=Knowledge(goal="t", facts={}))
        stt.blackboard["current_answer"] = NextAnswer("add_node", "double_it")
        stt.blackboard["current_execution"] = ExecutionDecision(
            "llm_single", rungs_checked=list(EXECUTION_LADDER[:7]),
            handle="llm::double_it", model_calls=1)
        r3 = mnodes["implement"].resolve(stt)
        r4 = mnodes["verify_compilable"].resolve(stt)
        check("model_node_3_authors_a_file_and_node_4_compiles_it",
              r3.control == "advance" and r3.paths_tried == ["llm"]
              and stt.graph and r4.control == "advance"
              and "compiles" in r4.detail,
              "an authored node file passes a real py_compile check in node 4")

        # and a file that does NOT compile loops back to node 3.
        def bad_author(slug, spec):
            p = _os.path.join(d, "nodes", slug + ".py")
            _os.makedirs(_os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write("def run(x)\n    return x\n")   # syntax error
            return AgentResult(ok=True, model="stub", output="", exit_code=0,
                               seconds=0.0)
        mnodes2 = make_model_nodes(work_dir=d, author=bad_author)
        stt2 = LoopState(knowledge=Knowledge(goal="t", facts={}))
        stt2.blackboard["current_answer"] = NextAnswer("add_node", "broken")
        stt2.blackboard["current_execution"] = ExecutionDecision(
            "llm_single", rungs_checked=list(EXECUTION_LADDER[:7]),
            handle="llm::broken", model_calls=1)
        mnodes2["implement"].resolve(stt2)
        r4b = mnodes2["verify_compilable"].resolve(stt2)
        check("a_node_that_will_not_compile_loops_back_to_implement",
              r4b.control == "loop_back" and r4b.loop_back_to == "implement"
              and "compile" in r4b.message.lower(),
              "node 4 rejects a non-compiling authored file and returns control "
              "to node 3 with the error")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "practitioner_loop_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

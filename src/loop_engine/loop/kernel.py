"""The Practitioner Kernel — the nine-node universal solver, canonical form.

Owner spec (2026-08-23).  The universal DAG contains NO domain workflow — no
research, coding, ML, or scraping logic.  It is a small meta-DAG whose only job
is to discover, build, run, evaluate, and remember whatever DAG is needed.
Single verbs proved too abstract; each node's NAME is the full sentence of what
the practitioner is doing (see KERNEL_NODE_NAMES):

    1. Reconstruct the latest accepted problem state + assemble verified context
    2. Reconcile the ultimate goal, active checkpoint, and working blueprint
    3. Assess sufficiency + prepare evidence / questions / perspectives / research
    4. Generate, challenge, select the next action (advances the checkpoint)
    5. Find / adapt / compose / design the method
    6. Execute the method, build or run the task graph, or delegate to a
       spawned Practitioner Loop
    7. Independently interrogate inputs, outputs, and process; test the results
    8. Integrate accepted results, update the blueprint/checkpoint, commit
    9. Continue / revise blueprint / branch / retry / reset / distill / close / finish

SIX nodes are REQUIRED (orient, decide_next, how, act, verify, route); THREE are
OPTIONAL (reconcile_horizon, assess_prepare, integrate_commit) with kernel
defaults.  A pass may explicitly SKIP optional nodes (state.facts['_skip_nodes'],
set via plan_skip_next_pass) for a trivial or mid-WorkPacket pass — but a REQUIRED
node can never be skipped: you always orient, decide, execute, verify, and route.
Flexibility lives in the route vocabulary (continue/branch/retry/reset/distill/
escalate/close/finish + 7 reset modes), in bounded recursion (spawned
practitioners), and in WorkPackets that run many ops per pass to a decision
boundary — never in weakening the required spine.

**Each pass is acyclic.**  Node 9 never creates a backward edge: it commits what
was learned, then either stops or launches ANOTHER nine-node pass over a NEW
VERSIONED STATE.  So every iteration is independently reproducible, versioned,
inspectable, and restartable — the run is a chain of passes, not a tangle:

    Pass 1 -> State v1 -> Pass 2 -> State v2 -> Pass 3 -> ...

Standard typed outputs per node: Situation, CandidateAction[], ExecutionPlan,
ResultPacket[], EvaluationPacket, RouteDecision (+ the new state).  A swarm is
not a new architecture — it is a portfolio of parameterized Practitioner Loop
specs, each running this same kernel.  An experiment is not a new node — it is a
kind of ExecutionPlan.  Distillation is not a new node — it is a task Learn/Route
spawns.  Resets live in Learn/Route, are standardized, and always DOCUMENT the
failed branch — nothing is silently erased.

Every pass appends one event to the run's ``events.jsonl`` — document, share, and
learn from every run.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Sequence

# ===========================================================================
# TAXONOMIES (closed).
# ===========================================================================

# The canonical EIGHT nodes (owner spec 2026-08-23).  The new nodes are #2
# (assess sufficiency + prepare reasoning resources) and #7 (integrate + commit),
# separating three things that must never collapse into one vague "context":
# PROBLEM STATE/EVIDENCE vs REASONING RESOURCES vs the MODEL-READY PROMPT.
KERNEL_NODES = ("orient", "reconcile_horizon", "assess_prepare", "decide_next",
                "how", "act", "verify", "integrate_commit", "route")

# No backward-compatibility aliases (they are technical debt).  Instead an impls
# set declares its capability via a HANDSHAKE: six nodes are REQUIRED, and the
# two additive nodes are OPTIONAL (the kernel supplies safe defaults for them,
# which is a declared contract, not a silent alias).  A missing required node
# fails loudly at run start rather than being papered over.
KERNEL_REQUIRED_NODES = ("orient", "decide_next", "how", "act", "verify",
                         "route")
KERNEL_OPTIONAL_NODES = ("reconcile_horizon", "assess_prepare",
                         "integrate_commit")


class KernelHandshakeError(RuntimeError):
    """An impls set does not satisfy the kernel's required-node handshake."""


def handshake(impls: "dict") -> dict:
    """Report what an impls set supports: which required/optional nodes it
    provides, which required nodes are missing, and which optional nodes will
    use the kernel default.  This is how the system determines capability —
    never a compatibility shim."""
    provided = [n for n in KERNEL_NODES if n in impls]
    missing_required = [n for n in KERNEL_REQUIRED_NODES if n not in impls]
    using_defaults = [n for n in KERNEL_OPTIONAL_NODES if n not in impls]
    unknown = [k for k in impls if k not in KERNEL_NODES]
    return {"record_type": "kernel_handshake/v1", "provided": provided,
            "missing_required": missing_required,
            "optional_using_default": using_defaults, "unknown_keys": unknown,
            "satisfied": not missing_required}


def plan_skip_next_pass(state: "PractitionerState",
                        skip_optional: "Sequence[str]") -> "PractitionerState":
    """Return a derived state that will SKIP the named optional nodes on the next
    pass.  The route or reconcile node calls this for a fast/trivial pass (e.g.
    skip grounding + prepare while a WorkPacket keeps executing).  Refuses to
    skip a required node — you always orient, decide, execute, verify, route."""
    bad = set(skip_optional) - set(KERNEL_OPTIONAL_NODES)
    if bad:
        raise KernelHandshakeError(
            f"only optional nodes {KERNEL_OPTIONAL_NODES} may be skipped; "
            f"got {sorted(bad)}")
    return state.derive(facts={**state.facts,
                               "_skip_nodes": tuple(skip_optional)})


def validate_impls(impls: "dict") -> None:
    """Raise KernelHandshakeError if the handshake is not satisfied, naming the
    missing required nodes and any unknown keys (an unknown key is almost always
    an old name that must be renamed — we surface it instead of aliasing it)."""
    hs = handshake(impls)
    if not hs["satisfied"] or hs["unknown_keys"]:
        raise KernelHandshakeError(
            f"impls handshake failed: missing required nodes "
            f"{hs['missing_required']}; unknown keys {hs['unknown_keys']} "
            f"(rename to canonical node keys — no aliases). Required: "
            f"{KERNEL_REQUIRED_NODES}; optional: {KERNEL_OPTIONAL_NODES}")

# The short keys above are CODE identifiers only.  Everywhere a human sees a
# node — documentation, diagrams, records, the interface — it carries its full
# sentence name (owner rule: single verbs are too abstract).
KERNEL_NODE_NAMES = {
    "orient": "Reconstruct the latest accepted problem state and assemble the "
              "verified context already available",
    "reconcile_horizon": "Reconcile the ultimate goal, active checkpoint, and "
                         "working blueprint with the latest accepted state",
    "assess_prepare": "Assess whether the current decision is sufficiently "
                      "supported and prepare any additional evidence, "
                      "questions, perspectives, or research",
    "decide_next": "Generate, challenge, and select the most valuable next "
                   "action that advances the active checkpoint without "
                   "violating the broader blueprint",
    "how": "Find, adapt, compose, or design the most appropriate method for "
           "carrying out the selected action",
    "act": "Execute the method, build or run the required task graph, or "
           "delegate bounded subproblems to spawned Practitioner Loops",
    "verify": "Independently interrogate the inputs, outputs, and process; test "
              "the results, compare alternatives, and identify remaining gaps "
              "or failures",
    "integrate_commit": "Integrate accepted results, update the blueprint and "
                        "checkpoint state, and commit validated evidence, "
                        "artifacts, and reusable learning",
    "route": "Choose whether to continue the checkpoint, revise the blueprint, "
             "branch, retry, reset, distill, escalate, close a checkpoint, or "
             "finish",
}

# The same nine nodes, each written as the complete question it answers.
KERNEL_NODE_QUESTIONS = {
    "orient": "What problem are we solving, and what verified context do we "
              "already have?",
    "reconcile_horizon": "Where does this stand against the ultimate goal, the "
                         "active checkpoint, and the working blueprint?",
    "assess_prepare": "Is the current decision sufficiently supported, and if "
                      "not, what evidence / questions / perspectives / research "
                      "should we prepare?",
    "decide_next": "What is the most valuable next action that advances the "
                   "checkpoint without violating the blueprint?",
    "how": "What is the best available method to carry out that action?",
    "act": "How do we execute it, build the task graph, or delegate to a "
           "spawned Practitioner Loop?",
    "verify": "Did it work, is it better than the alternatives, and what gaps "
              "remain?",
    "integrate_commit": "What accepted results and reusable learning do we "
                        "commit to memory?",
    "route": ("Should we continue, branch, retry, reset, distill, escalate, or "
              "finish?"),
}

# Node 2's four progressively-more-expensive outcomes.
SUFFICIENCY_OUTCOMES = ("sufficient_no_expansion", "retrieved_resources",
                        "generated_resources", "research_spawned")

# HOW implementation modes — the eight verbs of node 3.
HOW_MODES = ("use", "configure", "compose", "modify", "mutate", "research",
             "generate", "delegate")

# ACT's three basic possibilities.
ACT_MODES = ("run_direct", "run_dag", "spawn_practitioners")

# VERIFY's verdicts.
VERIFY_VERDICTS = ("accept", "accept_provisional", "repair", "research_more",
                   "try_another", "expand_swarm", "tune", "reset", "stop")

# LEARN/ROUTE's routes between passes.
ROUTES = ("stop_success", "continue", "retry", "repair", "explore_branch",
          "expand_swarm", "distill", "reframe", "soft_reset", "cold_restart",
          "stop_unprofitable")

# Standardized reset modes (all documented, nothing silently erased).
RESET_MODES = ("soft_retry", "reframe", "context_reset", "persona_model_reset",
               "branch_reset", "cold_restart", "capability_escalation")

MAX_SPAWN_DEPTH = 5


# ===========================================================================
# Contracts.
# ===========================================================================


@dataclass
class ProblemSpec:
    """What a practitioner is FOR — the only thing a cold restart keeps."""
    objective: str
    constraints: tuple = ()
    success_criteria: tuple = ()
    budget_passes: int = 12
    depth: int = 0
    namespace: str = "run"
    seed_facts: dict = field(default_factory=dict)


@dataclass
class PractitionerState:
    """Versioned state.  Passes never mutate a state — they derive the next."""
    spec: ProblemSpec
    version: int = 0
    facts: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)   # name -> reference (never blobs)
    open_questions: tuple = ()
    failures: tuple = ()                             # documented, append-only
    last_route: str = ""
    resets_used: int = 0

    def derive(self, **changes) -> "PractitionerState":
        base = {"spec": self.spec, "version": self.version + 1,
                "facts": dict(self.facts), "artifacts": dict(self.artifacts),
                "open_questions": self.open_questions,
                "failures": self.failures, "last_route": self.last_route,
                "resets_used": self.resets_used}
        base.update(changes)
        return PractitionerState(**base)


@dataclass
class Situation:
    """Node 1's output: what do I know, and what matters now?"""
    summary: str
    knowns: dict = field(default_factory=dict)
    unknowns: tuple = ()
    signals: tuple = ()          # missing_info | conflicting | no_progress | ...
    resources_hint: tuple = ()
    anchor: Any = None           # LongHorizonAnchorPacket, set by reconcile step


@dataclass
class CandidateAction:
    """Node 2's output rows — candidates, never an immediately-executed idea."""
    action: str
    kind: str = "task"
    rationale: str = ""
    expected_value: float = 0.5
    confidence: float = 0.5
    information_gain: float = 0.0
    estimated_cost: float = 1.0
    risk: float = 0.1
    dependencies: tuple = ()
    reversibility: float = 1.0
    parallelizable: bool = True


@dataclass
class ExecutionPlan:
    """Node 3's output: HOW to perform the selected action."""
    how_mode: str
    act_mode: str
    handle: str = ""
    steps: tuple = ()
    resources: tuple = ()
    spawned_loops: tuple = ()          # ProblemSpecs when act_mode == spawn
    experiment: dict = field(default_factory=dict)  # candidates/strategy/budget
    rationale: str = ""

    def __post_init__(self):
        if self.how_mode not in HOW_MODES:
            raise ValueError(f"how_mode must be one of {HOW_MODES}")
        if self.act_mode not in ACT_MODES:
            raise ValueError(f"act_mode must be one of {ACT_MODES}")


@dataclass
class ResultPacket:
    """Node 4's output rows — standardized, reference-passing, lineage-bearing."""
    objective: str
    result: Any = None
    claims: tuple = ()
    evidence_refs: tuple = ()
    artifact_refs: tuple = ()
    confidence: float = 0.5
    assumptions: tuple = ()
    metrics: dict = field(default_factory=dict)
    cost: float = 0.0
    errors: tuple = ()
    limitations: tuple = ()
    suggested_next: tuple = ()
    lineage: tuple = ()


@dataclass
class EvaluationPacket:
    """Node 5's output: did it work, and which result is best?"""
    verdict: str
    best_index: int = 0
    scores: tuple = ()
    notes: str = ""

    def __post_init__(self):
        if self.verdict not in VERIFY_VERDICTS:
            raise ValueError(f"verdict must be one of {VERIFY_VERDICTS}")


@dataclass
class RouteDecision:
    """Node 6's output: what happens next, and (on reset) which reset mode."""
    route: str
    reason: str = ""
    reset_mode: str = ""

    def __post_init__(self):
        if self.route not in ROUTES:
            raise ValueError(f"route must be one of {ROUTES}")
        if self.reset_mode and self.reset_mode not in RESET_MODES:
            raise ValueError(f"reset_mode must be one of {RESET_MODES}")


@dataclass
class DecisionSupportPortfolio:
    """Node 2's output — REASONING RESOURCES prepared for the next decision,
    kept strictly separate from problem-state/evidence and from the model-ready
    prompt.  Generated questions/perspectives are provisional, NOT trusted
    knowledge."""
    sufficiency: str = "sufficient_no_expansion"
    questions: list = field(default_factory=list)
    perspectives: list = field(default_factory=list)
    retrieved: list = field(default_factory=list)   # ids of reused resources
    generated: list = field(default_factory=list)   # ids of provisional ones
    research_specs: list = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        if self.sufficiency not in SUFFICIENCY_OUTCOMES:
            raise ValueError(f"sufficiency must be one of {SUFFICIENCY_OUTCOMES}")


@dataclass
class PassRecord:
    """One acyclic pass, fully recorded — the unit of reproducibility."""
    pass_number: int
    state_version_in: int
    situation: Situation = None
    anchor: Any = None
    portfolio: "DecisionSupportPortfolio | None" = None
    candidates: list = field(default_factory=list)
    chosen: "CandidateAction | None" = None
    plan: "ExecutionPlan | None" = None
    results: list = field(default_factory=list)
    evaluation: "EvaluationPacket | None" = None
    route: "RouteDecision | None" = None
    skipped_nodes: tuple = ()          # optional nodes skipped THIS pass
    state_version_out: int = 0

    def to_event(self) -> dict:
        def d(x):
            return asdict(x) if x is not None and not isinstance(
                x, (list, dict, str, int, float)) else x
        return {"record_type": "practitioner_pass/v1",
                "pass": self.pass_number,
                "state_in": self.state_version_in,
                "skipped_nodes": list(self.skipped_nodes),
                "situation": d(self.situation),
                "plan_health": (getattr(self.anchor, "plan_health", None)
                                if self.anchor is not None else None),
                "sufficiency": (self.portfolio.sufficiency
                                if self.portfolio else None),
                "n_candidates": len(self.candidates),
                "chosen": d(self.chosen), "plan": d(self.plan),
                "n_results": len(self.results),
                "evaluation": d(self.evaluation), "route": d(self.route),
                "state_out": self.state_version_out}


# ===========================================================================
# The kernel runner — one acyclic pass, then routing BETWEEN passes.
# ===========================================================================

# An implementation set: one callable per node.  Deterministic defaults below;
# model-backed sets plug in the debate/strategies/opencode machinery.
KernelImpls = dict


def run_pass(state: PractitionerState, impls: KernelImpls,
             pass_number: int = 1) -> tuple:
    """Run ONE acyclic EIGHT-node pass.  Never mutates ``state`` — returns
    (PassRecord, new_state).  Node order is fixed; there are no backward edges
    inside a pass; everything a later pass needs travels in the new state.

    Impls are addressed by their CANONICAL keys — no aliases.  The three OPTIONAL
    nodes (reconcile_horizon, assess_prepare, integrate_commit) fall back to the
    kernel default when absent; every required node must be present (checked by
    ``validate_impls`` before the run).

    A pass may explicitly SKIP optional nodes this pass via
    ``state.facts['_skip_nodes']`` (set by the route or reconcile node) — e.g. a
    trivial pass skips grounding, or a mid-WorkPacket pass skips prepare.  A
    REQUIRED node can never be skipped (you always orient, decide, execute,
    verify, and route) — attempting to skip one fails loudly."""
    skip = set(state.facts.get("_skip_nodes", ()))
    bad = skip & set(KERNEL_REQUIRED_NODES)
    if bad:
        raise KernelHandshakeError(
            f"cannot skip required nodes {sorted(bad)}; only the optional nodes "
            f"{KERNEL_OPTIONAL_NODES} may be skipped per pass — you always "
            f"orient, decide, execute, verify, and route")
    rec = PassRecord(pass_number=pass_number, state_version_in=state.version)
    rec.skipped_nodes = tuple(n for n in KERNEL_OPTIONAL_NODES if n in skip)
    situation: Situation = impls["orient"](state)
    rec.situation = situation

    # Node 2 — reconcile the ultimate goal / active checkpoint / working
    # blueprint with the latest state (skippable per pass for a trivial task).
    if "reconcile_horizon" not in skip:
        situation.anchor = impls.get("reconcile_horizon",
                                     default_reconcile_horizon)(state, situation)
        rec.anchor = situation.anchor

    # Node 3 — assess sufficiency + prepare reasoning resources (skippable).
    portfolio = (DecisionSupportPortfolio(sufficiency="sufficient_no_expansion")
                 if "assess_prepare" in skip
                 else impls.get("assess_prepare", default_assess_prepare)(
                     state, situation))
    rec.portfolio = portfolio

    candidates: list = impls["decide_next"](state, situation)
    rec.candidates = candidates
    chosen = max(candidates, key=lambda c: (c.expected_value, c.confidence)) \
        if candidates else None
    rec.chosen = chosen
    if chosen is None:
        rec.route = RouteDecision("stop_unprofitable", "no candidate actions")
        new_state = state.derive(last_route=rec.route.route)
        rec.state_version_out = new_state.version
        return rec, new_state
    plan: ExecutionPlan = impls["how"](state, situation, chosen)
    rec.plan = plan
    results: list = impls["act"](state, plan)
    rec.results = results
    evaluation: EvaluationPacket = impls["verify"](state, plan, results)
    rec.evaluation = evaluation

    # Node 7 — integrate + commit accepted results (skippable per pass).
    if "integrate_commit" not in skip:
        state = impls.get("integrate_commit", default_integrate_commit)(
            state, rec)

    # Node 8 — route between passes.
    route, new_state = impls["route"](state, rec)
    rec.route = route
    rec.state_version_out = new_state.version
    return rec, new_state


def run_practitioner(spec: ProblemSpec, impls: KernelImpls, *,
                     event_dir: str | None = None,
                     max_passes: int | None = None) -> dict:
    """Chain passes until a stop route or the pass budget.

    Routing is BETWEEN passes: continue/retry/repair/reframe re-enter with the
    derived state; soft_reset documents the stuck branch and re-enters with a
    reframed state; cold_restart re-enters with ONLY the spec (the failed
    practitioner's conclusions are left behind, but its failure record is kept).
    Every pass appends one event to events.jsonl when ``event_dir`` is given."""
    validate_impls(impls)          # handshake: fail loudly on a missing node
    state = PractitionerState(spec=spec, facts=dict(spec.seed_facts))
    limit = max_passes if max_passes is not None else spec.budget_passes
    records: list = []
    events_path = None
    if event_dir:
        os.makedirs(event_dir, exist_ok=True)
        events_path = os.path.join(event_dir, "events.jsonl")
    for n in range(1, limit + 1):
        rec, state = run_pass(state, impls, pass_number=n)
        records.append(rec)
        if events_path:
            with open(events_path, "a") as fh:
                fh.write(json.dumps(rec.to_event(), default=str) + "\n")
        route = rec.route.route if rec.route else "stop_unprofitable"
        if route in ("stop_success", "stop_unprofitable"):
            break
        if route == "cold_restart":
            # a whole new person: only the objective, constraints, criteria —
            # plus the documented failures (never silently erased).
            state = PractitionerState(
                spec=spec, version=state.version,
                facts=dict(spec.seed_facts),
                failures=state.failures, resets_used=state.resets_used,
                last_route="cold_restart")
    return {"record_type": "practitioner_run/v1",
            "node_names": dict(KERNEL_NODE_NAMES),
            "objective": spec.objective, "passes": len(records),
            "final_route": records[-1].route.route if records and
            records[-1].route else "",
            "final_state_version": state.version,
            "facts": state.facts, "artifacts": state.artifacts,
            "failures": list(state.failures),
            "records": records, "events_path": events_path}


# ===========================================================================
# Deterministic default implementations — zero model, compose the machinery.
# ===========================================================================


def default_orient(state: PractitionerState) -> Situation:
    signals = []
    if not state.facts:
        signals.append("missing_info")
    if state.last_route in ("retry", "repair"):
        signals.append("prior_pass_incomplete")
    if state.last_route in ("soft_reset", "cold_restart"):
        signals.append("post_reset")
    unmet = tuple(c for c in state.spec.success_criteria
                  if not state.facts.get(f"met:{c}"))
    return Situation(
        summary=f"v{state.version}: {len(state.facts)} facts, "
        f"{len(state.artifacts)} artifacts, {len(unmet)} criteria unmet",
        knowns=dict(state.facts), unknowns=unmet, signals=tuple(signals))


def default_decide_next(state: PractitionerState,
                         situation: Situation) -> list:
    cands: list = []
    if situation.unknowns:
        crit = situation.unknowns[0]
        cands.append(CandidateAction(
            action=f"meet:{crit}", kind="task",
            rationale=f"success criterion {crit!r} unmet",
            expected_value=0.9, confidence=0.8, information_gain=0.4))
        if "missing_info" in situation.signals:
            # with little known, reducing the gap OUTRANKS attempting the task
            # blind — research first, then act on what it taught.
            cands.append(CandidateAction(
                action=f"research:{crit}", kind="research",
                rationale="little is known; reduce the gap first",
                expected_value=0.95, confidence=0.6, information_gain=0.9))
    else:
        cands.append(CandidateAction(
            action="deliver", kind="deliver",
            rationale="all success criteria met", expected_value=1.0,
            confidence=0.95))
    return cands


def default_how(state: PractitionerState, situation: Situation,
                chosen: CandidateAction) -> ExecutionPlan:
    # reuse-first: do we already have it?
    have = state.facts.get(f"registry_has:{chosen.action}")
    if have:
        return ExecutionPlan("use", "run_direct", handle=str(have),
                             rationale="already built — drop it in")
    if chosen.kind == "research":
        return ExecutionPlan("research", "spawn_practitioners",
                             spawned_loops=(ProblemSpec(
                                 objective=f"reduce gap: {chosen.action}",
                                 depth=state.spec.depth + 1,
                                 budget_passes=3),),
                             rationale="a narrower practitioner reduces the gap")
    if chosen.kind == "deliver":
        return ExecutionPlan("use", "run_direct", handle="deliver",
                             rationale="assemble and deliver")
    return ExecutionPlan("generate", "run_dag", handle=f"build::{chosen.action}",
                         rationale="nothing reusable — build it")


def default_act(state: PractitionerState, plan: ExecutionPlan) -> list:
    if plan.act_mode == "spawn_practitioners":
        if state.spec.depth + 1 > MAX_SPAWN_DEPTH:
            return [ResultPacket(objective="spawn", errors=("depth exceeded",),
                                 confidence=0.0)]
        packets = []
        for spawned_spec in plan.spawned_loops:
            spawned = run_practitioner(spawned_spec, default_impls())
            packets.append(ResultPacket(
                objective=spawned_spec.objective,
                result={"passes": spawned["passes"]},
                claims=(f"learned:{spawned_spec.objective}",),
                confidence=0.7, cost=spawned["passes"],
                lineage=(f"spawned@d{spawned_spec.depth}",)))
        return packets
    if plan.act_mode == "run_dag":
        return [ResultPacket(objective=plan.handle,
                             result={"built": plan.handle},
                             artifact_refs=(plan.handle,), confidence=0.8,
                             cost=1.0)]
    return [ResultPacket(objective=plan.handle, result={"ran": plan.handle},
                         confidence=0.9, cost=0.2)]


def default_verify(state: PractitionerState, plan: ExecutionPlan,
                   results: list) -> EvaluationPacket:
    if not results or any(r.errors for r in results):
        return EvaluationPacket("repair", notes="errors in results")
    best = max(range(len(results)), key=lambda i: results[i].confidence)
    if plan.how_mode == "research":
        return EvaluationPacket("accept_provisional", best_index=best,
                                notes="research absorbed; re-decide next pass")
    return EvaluationPacket("accept", best_index=best)


def default_route(state: PractitionerState, rec: PassRecord) -> tuple:
    ev, plan, chosen = rec.evaluation, rec.plan, rec.chosen
    facts = dict(state.facts)
    artifacts = dict(state.artifacts)
    failures = state.failures
    resets = state.resets_used
    best = rec.results[ev.best_index] if rec.results else None

    if ev.verdict in ("accept", "accept_provisional") and best is not None:
        for ref in best.artifact_refs:
            artifacts[ref] = ref
            facts[f"registry_has:{chosen.action}"] = ref
        for claim in best.claims:
            facts[claim] = True
        if chosen.kind == "task" and chosen.action.startswith("meet:"):
            facts[f"met:{chosen.action[5:]}"] = True
        if chosen.kind == "deliver":
            return (RouteDecision("stop_success", "delivered"),
                    state.derive(facts=facts, artifacts=artifacts,
                                 last_route="stop_success"))
        return (RouteDecision("continue", f"{ev.verdict}; more remains"),
                state.derive(facts=facts, artifacts=artifacts,
                             last_route="continue"))

    if ev.verdict == "repair":
        # document the failure; escalate the reset ladder if repairs repeat.
        failures = failures + (f"pass {rec.pass_number}: "
                               f"{ev.notes or 'repair needed'}",)
        if state.last_route == "repair":            # second repair in a row
            resets += 1
            mode = "soft_retry" if resets == 1 else "cold_restart"
            route = "soft_reset" if mode == "soft_retry" else "cold_restart"
            return (RouteDecision(route, "repeated repair", reset_mode=mode),
                    state.derive(failures=failures, resets_used=resets,
                                 last_route=route))
        return (RouteDecision("repair", ev.notes or "repair"),
                state.derive(failures=failures, last_route="repair"))

    return (RouteDecision("stop_unprofitable", f"verdict {ev.verdict}"),
            state.derive(last_route="stop_unprofitable"))


def default_reconcile_horizon(state: PractitionerState, situation: Situation):
    """Node 2 default: build the LongHorizonAnchorPacket from any goal stack /
    blueprint / progress the state carries (reserved facts keys), computed not
    hallucinated.  A short task with no plan yields a minimal anchor (just the
    objective) — cheap, and still grounding the model in the ultimate goal."""
    from ..code_nodes.blueprint import build_anchor, LongHorizonAnchorPacket
    goals = state.facts.get("_goal_stack")
    bp = state.facts.get("_blueprint")
    prog = state.facts.get("_progress")
    if goals is None and bp is None:
        return LongHorizonAnchorPacket(
            ultimate_goal=state.spec.objective,
            success_criteria=tuple(state.spec.success_criteria),
            completed_progress=f"v{state.version}")
    return build_anchor(goals, bp, prog,
                        success_criteria=state.spec.success_criteria)


def default_assess_prepare(state: PractitionerState,
                           situation: Situation) -> DecisionSupportPortfolio:
    """Node 2 default: assess sufficiency but NEVER force expansion — the
    standardized pass stays cheap.  Flags that resources are available when the
    situation is thin, so a model-backed impl knows where enrichment would pay,
    but the deterministic default proceeds with what it has."""
    if situation.unknowns or "missing_info" in situation.signals:
        return DecisionSupportPortfolio(
            sufficiency="sufficient_no_expansion",
            notes="expansion available but not taken (deterministic default)")
    return DecisionSupportPortfolio(sufficiency="sufficient_no_expansion")


def default_integrate_commit(state: PractitionerState,
                             rec: PassRecord) -> PractitionerState:
    """Node 7 default: a no-op pass-through — the route node (default_route)
    commits accepted results, exactly as the 6-node kernel did.  A model-backed
    impl can split commit here and leave routing to node 8."""
    return state


def default_impls() -> KernelImpls:
    return {"orient": default_orient,
            "reconcile_horizon": default_reconcile_horizon,
            "assess_prepare": default_assess_prepare,
            "decide_next": default_decide_next,
            "how": default_how, "act": default_act, "verify": default_verify,
            "integrate_commit": default_integrate_commit,
            "route": default_route}


# ===========================================================================
# Swarm — a portfolio of parameterized practitioner runs, nothing more.
# ===========================================================================


@dataclass
class SwarmSpawnedSpec:
    label: str
    spec: ProblemSpec
    impls_factory: "Callable[[], KernelImpls] | None" = None


def run_swarm(spawned_loops: Sequence[SwarmSpawnedSpec], *,
              event_dir: str | None = None) -> dict:
    """A swarm is a list of spawned Practitioner Loop specs run through the same
    kernel; the parent compares standardized run summaries.  Selection is the
    caller's oracle-driven step — the swarm only produces the portfolio."""
    members = []
    for i, ch in enumerate(spawned_loops):
        impls = (ch.impls_factory or default_impls)()
        sub_dir = os.path.join(event_dir, ch.label) if event_dir else None
        out = run_practitioner(ch.spec, impls, event_dir=sub_dir)
        members.append({"label": ch.label, "passes": out["passes"],
                        "final_route": out["final_route"],
                        "facts": out["facts"],
                        "artifacts": list(out["artifacts"])})
    return {"record_type": "practitioner_swarm/v1", "n": len(members),
            "members": members}


# ===========================================================================
# Self-test — deterministic, no network.
# ===========================================================================


def self_test() -> dict:
    import tempfile
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    spec = ProblemSpec(objective="solve the task",
                       success_criteria=("baseline", "validated"))

    # 1. one pass is acyclic and typed end to end (all EIGHT nodes).
    st0 = PractitionerState(spec=spec)
    rec, st1 = run_pass(st0, default_impls())
    check("one_pass_runs_the_nine_nodes_acyclically_with_typed_outputs",
          len(KERNEL_NODES) == 9
          and isinstance(rec.situation, Situation)
          and rec.anchor is not None
          and isinstance(rec.portfolio, DecisionSupportPortfolio)
          and rec.portfolio.sufficiency in SUFFICIENCY_OUTCOMES
          and rec.candidates and isinstance(rec.plan, ExecutionPlan)
          and rec.results and isinstance(rec.evaluation, EvaluationPacket)
          and isinstance(rec.route, RouteDecision),
          "Situation -> DecisionSupportPortfolio -> CandidateAction[] -> "
          "ExecutionPlan -> ResultPacket[] -> EvaluationPacket -> "
          "RouteDecision")

    # 1b. the HANDSHAKE — no aliases.  A required-node key is mandatory; the two
    # additive nodes are optional (kernel default).  An OLD name is an unknown
    # key and fails loudly rather than being silently aliased.
    ok_hs = handshake(default_impls())["satisfied"]
    missing = handshake({"orient": default_orient, "decide_next":
                         default_decide_next, "how": default_how,
                         "act": default_act, "verify": default_verify})
    aliased = False
    try:
        validate_impls({"orient": default_orient, "select_next_action":
                        default_decide_next, "how": default_how, "act":
                        default_act, "verify": default_verify, "learn_route":
                        default_route})   # old keys -> unknown -> must raise
    except KernelHandshakeError:
        aliased = True
    check("the_handshake_replaces_aliases_and_fails_loudly_on_old_keys",
          ok_hs and missing["missing_required"] == ["route"] and aliased
          and "assess_prepare" in KERNEL_OPTIONAL_NODES,
          "required nodes are mandatory; old names are rejected as unknown "
          "keys — no backward-compat shim")

    # 2. state is VERSIONED, never mutated.
    check("state_is_versioned_never_mutated",
          st0.version == 0 and st1.version == 1 and st0.facts == {}
          and st1.facts != st0.facts,
          f"pass derived v{st1.version}; v0 is intact for replay")

    # 3. a full run chains passes to success and documents every pass.
    with tempfile.TemporaryDirectory() as d:
        out = run_practitioner(spec, default_impls(), event_dir=d)
        events = [json.loads(l) for l in
                  open(os.path.join(d, "events.jsonl"))]
        check("a_run_chains_passes_to_success_and_logs_every_pass",
              out["final_route"] == "stop_success"
              and len(events) == out["passes"]
              and all(e["record_type"] == "practitioner_pass/v1"
                      for e in events),
              f"{out['passes']} passes, all in events.jsonl, ended "
              f"stop_success")

        check("every_success_criterion_was_met_before_stopping",
              out["facts"].get("met:baseline")
              and out["facts"].get("met:validated"),
              "the kernel only delivers when the spec's criteria are met")

    # 4. research spawns a SPAWNED practitioner running the same kernel,
    # and its findings land in the parent's facts.
    spec_r = ProblemSpec(objective="novel problem",
                         success_criteria=("understanding",))
    out_r = run_practitioner(spec_r, default_impls())
    check("research_spawns_a_spawned_practitioner_and_feeds_findings_back",
          any(k.startswith("learned:reduce gap") for k in out_r["facts"]),
          "the gap-reduction spawned ran the same six-node kernel; "
          "'learned:' facts flowed up")

    # 5. reuse-first: a registry fact short-circuits HOW to 'use'.
    spec_u = ProblemSpec(objective="x", success_criteria=("thing",),
                         seed_facts={"registry_has:meet:thing": "node_v1"})
    st = PractitionerState(spec=spec_u, facts=dict(spec_u.seed_facts))
    rec_u, _ = run_pass(st, default_impls())
    check("how_is_reuse_first_use_mode_when_already_built",
          rec_u.plan.how_mode == "use" and rec_u.plan.handle == "node_v1",
          "'do we already have it?' answered before any generation")

    # 6. repeated repair escalates the documented reset ladder to cold restart,
    # and the cold state keeps ONLY spec facts + the failure log.
    calls = {"n": 0}
    def broken_act(state, plan):
        calls["n"] += 1
        return [ResultPacket(objective="x", errors=("boom",))]
    impls = default_impls(); impls["act"] = broken_act
    out_b = run_practitioner(ProblemSpec(objective="doomed",
                                         success_criteria=("c",),
                                         budget_passes=8), impls)
    routes = [r.route.route for r in out_b["records"]]
    check("repeated_failure_escalates_soft_reset_then_cold_restart_documented",
          "repair" in routes and "soft_reset" in routes
          and "cold_restart" in routes and out_b["failures"],
          f"routes: {routes}; failures documented: {len(out_b['failures'])}")

    # 7. the swarm is a portfolio of parameterized runs of the SAME kernel.
    sw = run_swarm([SwarmSpawnedSpec("full", ProblemSpec(
        objective="p", success_criteria=("a",))),
        SwarmSpawnedSpec("minimal", ProblemSpec(
            objective="p", success_criteria=("a",), seed_facts={
                "registry_has:meet:a": "cached"}))])
    check("a_swarm_is_a_portfolio_of_parameterized_kernel_runs",
          sw["n"] == 2 and all(m["final_route"] == "stop_success"
                               for m in sw["members"]),
          "two spawned_loops, different parameters, same kernel, standardized "
          "summaries")

    # 8. the taxonomies are closed.
    bad = 0
    for exc_fn in (lambda: ExecutionPlan("vibes", "run_direct"),
                   lambda: ExecutionPlan("use", "teleport"),
                   lambda: EvaluationPacket("meh"),
                   lambda: RouteDecision("wander"),
                   lambda: RouteDecision("soft_reset", reset_mode="nap")):
        try:
            exc_fn()
        except ValueError:
            bad += 1
    check("all_kernel_taxonomies_are_closed", bad == 5,
          "how/act/verdict/route/reset vocabularies reject inventions")

    # 9. depth guard: spawning past the limit degrades to an error packet.
    deep_spec = ProblemSpec(objective="deep", depth=MAX_SPAWN_DEPTH)
    st_deep = PractitionerState(spec=deep_spec)
    plan = ExecutionPlan("research", "spawn_practitioners",
                         spawned_loops=(ProblemSpec(objective="spawned",
                                               depth=MAX_SPAWN_DEPTH + 1),))
    packs = default_act(st_deep, plan)
    check("runaway_spawn_depth_degrades_honestly", packs
          and packs[0].errors, "past the depth guard: an error packet, not "
          "silent recursion")

    # 10. every node carries a full-sentence name and its complete question —
    # never a bare verb — and every run record self-describes with them.
    multiword = all(len(KERNEL_NODE_NAMES[k].split()) >= 5
                    and len(KERNEL_NODE_QUESTIONS[k].split()) >= 5
                    and KERNEL_NODE_QUESTIONS[k].endswith("?")
                    for k in KERNEL_NODES)
    out_named = run_practitioner(ProblemSpec(objective="n",
                                             success_criteria=("a",)),
                                 default_impls())
    check("nodes_have_full_sentence_names_and_questions_in_every_record",
          multiword and out_named.get("node_names") == KERNEL_NODE_NAMES,
          "short keys are code identifiers only; humans always see the full "
          "sentences")

    # 12. per-pass SKIP: optional nodes can be skipped (recorded); a required
    # node can never be skipped (fails loudly) — the flexibility + the guardrail.
    st_skip = PractitionerState(spec=spec,
                                facts={"_skip_nodes": ("assess_prepare",
                                                       "reconcile_horizon")})
    rec_s, _ = run_pass(st_skip, default_impls())
    req_blocked = False
    try:
        run_pass(PractitionerState(spec=spec,
                                   facts={"_skip_nodes": ("verify",)}),
                 default_impls())
    except KernelHandshakeError:
        req_blocked = True
    planned = plan_skip_next_pass(PractitionerState(spec=spec),
                                  ("integrate_commit",))
    plan_bad = False
    try:
        plan_skip_next_pass(PractitionerState(spec=spec), ("decide_next",))
    except KernelHandshakeError:
        plan_bad = True
    check("optional_nodes_skip_per_pass_but_required_nodes_never_can",
          set(rec_s.skipped_nodes) == {"assess_prepare", "reconcile_horizon"}
          and rec_s.anchor is None and req_blocked and plan_bad
          and planned.facts["_skip_nodes"] == ("integrate_commit",),
          "grounding+prepare skipped this pass and recorded; skipping verify "
          "(required) is refused; plan_skip_next_pass sets it for the route node")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "kernel_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

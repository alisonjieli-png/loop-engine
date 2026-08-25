"""Decision need — detect WHY a decision is open, before asking select the next action.

A decision should not be delegated to a broad resolver before the reason for
the decision is clear. An expert first frames the open
question — is this a knowledge gap, a contradiction to resolve, a plan checkpoint,
a plateau, a routing choice among candidates, or a stop decision? — and that
framing constrains which answers are even admissible and which mode of reasoning
fits.

``detect_decision_need`` reads the epistemic state (unknowns, contradictions) and
a few situation flags and returns a typed ``DecisionNeed`` with a **decision
mode** (FOLLOW / ROUTE / INVESTIGATE / DELIBERATE / ESCALATE / WAIT / TERMINATE)
and the move families that are acceptable for it.  The loop passes this to the
resolvers so, for example, an INVESTIGATE need admits only epistemic moves (run a
test, gather context) and a TERMINATE need admits only terminal moves — you
cannot answer "add a node" to a stop decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

from ..strings.knowledge_state import EpistemicState

# Why the loop must decide now (v3 Appendix B seed, abridged).
DECISION_NEED_KINDS = (
    "task_framing", "goal_gap", "obligation_gap", "knowledge_gap",
    "contradiction", "capability_gap", "graph_completeness", "node_selection",
    "parameter_selection", "optimizer_selection", "test_selection",
    "failure_diagnosis", "plan_checkpoint", "plan_invalidated", "plateau",
    "promotion", "stop_continue", "external_event_pending", "custom")

# The mode of reasoning the need calls for (v3 §7.3).
DECISION_MODES = ("follow", "route", "investigate", "deliberate", "escalate",
                  "wait", "terminate")

# Which move families each mode admits — the constraint the need places on the
# answer space (families are from moves.MOVE_FAMILIES).
MODE_MOVE_FAMILIES = {
    "follow": ("control", "constructive"),
    "route": ("constructive", "search", "control"),
    "investigate": ("epistemic", "experimental"),
    "deliberate": ("epistemic", "constructive", "search", "experimental",
                   "control"),
    "escalate": ("control",),
    "wait": ("control",),
    "terminate": ("terminal",),
}

# A kind that fires an actionable frontier item.
FRONTIER_KINDS = ("unresolved_goal", "unmet_obligation", "knowledge_gap",
                  "contradiction", "failed_action", "capability_gap",
                  "plan_checkpoint", "plan_exhausted", "plateau", "promotion",
                  "stop_decision")


@dataclass(frozen=True)
class FrontierItem:
    """One currently actionable gap, conflict, risk, or opportunity."""
    id: str
    kind: str
    materiality: float = 0.0
    urgency: float = 0.0
    detail: str = ""


@dataclass(frozen=True)
class DecisionNeed:
    """A typed explanation of why the system must decide what happens next."""
    id: str
    kind: str
    mode: str
    question: str
    materiality: float = 0.0
    urgency: float = 0.0
    reversibility: str = "high"
    acceptable_move_families: tuple[str, ...] = ()
    horizon: str = "immediate"        # immediate | tactical | strategic | campaign
    trigger_refs: tuple[str, ...] = ()

    def admits_family(self, family: str) -> bool:
        return (not self.acceptable_move_families
                or family in self.acceptable_move_families)

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


def frontier_from_state(state: EpistemicState, *,
                        plateau: bool = False,
                        plan_exhausted: bool = False) -> list[FrontierItem]:
    """Derive the actionable frontier from the epistemic state and flags."""
    items: list[FrontierItem] = []
    for c in state.open_contradictions():
        items.append(FrontierItem(
            id=f"frontier.contradiction.{c.id}", kind="contradiction",
            materiality=c.materiality, urgency=c.materiality,
            detail=f"open contradiction over {list(c.claim_ids)}"))
    for u in state.open_unknowns():
        items.append(FrontierItem(
            id=f"frontier.unknown.{u.id}", kind="knowledge_gap",
            materiality=u.expected_value, urgency=u.expected_value,
            detail=u.question))
    if plateau:
        items.append(FrontierItem(id="frontier.plateau", kind="plateau",
                                  materiality=0.7, urgency=0.6,
                                  detail="search has plateaued"))
    if plan_exhausted:
        items.append(FrontierItem(id="frontier.plan_exhausted",
                                  kind="plan_exhausted", materiality=0.5,
                                  detail="active plan is exhausted"))
    # Most material first.
    items.sort(key=lambda i: (-i.materiality, i.id))
    return items


def detect_decision_need(state: EpistemicState, *,
                         has_ready_plan_clause: bool = False,
                         has_multiple_candidates: bool = False,
                         plateau: bool = False, plan_exhausted: bool = False,
                         goal_satisfied: bool = False,
                         budget_exhausted: bool = False,
                         needs_authority: bool = False,
                         waiting_on_event: bool = False,
                         material_threshold: float = 0.5) -> DecisionNeed:
    """Frame the open decision and pick its mode.  The order encodes priority:
    terminate and escalate/wait first (they override), then contradictions and
    high-value unknowns (investigate), then a ready plan (follow), then routing
    among candidates, else open deliberation."""
    def need(kind, mode, question, materiality=0.0, urgency=0.0,
             reversibility="high", horizon="immediate", triggers=()):
        return DecisionNeed(
            id=f"decision-need.{kind}", kind=kind, mode=mode, question=question,
            materiality=materiality, urgency=urgency, reversibility=reversibility,
            acceptable_move_families=MODE_MOVE_FAMILIES.get(mode, ()),
            horizon=horizon, trigger_refs=tuple(triggers))

    if goal_satisfied:
        return need("stop_continue", "terminate",
                    "The goal is satisfied — should the loop stop?", 1.0, 1.0)
    if budget_exhausted:
        return need("stop_continue", "terminate",
                    "The budget is exhausted — stop and record what remains.",
                    1.0, 1.0)
    if needs_authority:
        return need("capability_gap", "escalate",
                    "Required authority or capability is missing — escalate.",
                    0.8, 0.7, reversibility="high")
    if waiting_on_event:
        return need("external_event_pending", "wait",
                    "The next useful result is an external or scheduled event.",
                    0.4, 0.3)

    contradictions = state.open_contradictions()
    material = [c for c in contradictions if c.materiality >= material_threshold]
    if material:
        c = max(material, key=lambda x: x.materiality)
        return need("contradiction", "investigate",
                    f"Resolve the contradiction over {list(c.claim_ids)} before "
                    f"proceeding.", c.materiality, c.materiality,
                    triggers=[c.id])

    unknowns = state.open_unknowns()
    valuable = [u for u in unknowns if u.expected_value >= material_threshold]
    if valuable:
        u = max(valuable, key=lambda x: x.expected_value)
        return need("knowledge_gap", "investigate",
                    f"Resolve the unknown '{u.question}' before deciding.",
                    u.expected_value, u.expected_value, triggers=[u.id])

    if plateau:
        return need("plateau", "deliberate",
                    "The search has plateaued — how should it be broken?",
                    0.7, 0.6, horizon="tactical")

    if has_ready_plan_clause:
        return need("plan_checkpoint", "follow",
                    "A valid plan supplies the next action — follow it.",
                    0.5, 0.5)

    if plan_exhausted:
        return need("plan_invalidated", "deliberate",
                    "The plan is exhausted — open-ended deliberation resumes.",
                    0.5, 0.4, horizon="tactical")

    if has_multiple_candidates:
        return need("node_selection", "route",
                    "Several valid candidates remain — rank and choose.",
                    0.6, 0.5)

    return need("task_framing", "deliberate",
                "No plan or clear route applies — deliberate on select the next action.",
                0.5, 0.4, horizon="tactical")

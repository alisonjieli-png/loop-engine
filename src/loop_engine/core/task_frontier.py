"""Task frontier: the durable set of possible next work, projected per pass.

Architectural role: passive, digest-chained snapshots of what a Practitioner
run still had to answer, try, verify, or recover at each pass boundary. The
adaptive Practitioner already records orientations, action decisions,
verification verdicts, failures, and recovery directives; this module joins
them into one typed frontier per pass so a reader, a Studio view, or a later
run can ask which questions stayed open, which experiments ran, which failed,
and how far the run stepped back, without re-reading prompt text. Snapshots
are rebuilt from the saved adaptive result, so they are a projection with
lineage, never a second source of truth.

Vocabularies are closed enums: an item kind, a status, a horizon, and a pass
verdict are typed values, so a misspelled status cannot enter a snapshot and
no comparison in this module happens on a raw string.

Owns:
    - FrontierItemKind, FrontierStatus, Horizon, PassVerdict: closed enums.
    - FrontierItem: one question, hypothesis, experiment, verification,
      recovery action, or user-authority request with a status and horizon.
    - FrontierSnapshot: the items at one pass boundary, chained to its parent
      snapshot by digest.
    - frontier_from_adaptive_result(): the deterministic projection.

Does not own: the Practitioner's decisions (core.adaptive_practitioner*), the
action-kind vocabulary it reads (core.adaptive_practitioner_records
NEXT_ACTION_KINDS), or Run History (core.run_history).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import Enum

FRONTIER_SCHEMA_VERSION = "task_frontier_snapshot/v1"


class FrontierItemKind(str, Enum):
    QUESTION = "question"
    HYPOTHESIS = "hypothesis"
    SUBPROBLEM = "subproblem"
    RESEARCH_NEED = "research_need"
    IMPLEMENTATION_EXPERIMENT = "implementation_experiment"
    VERIFICATION = "verification"
    CRITIQUE = "critique"
    RECOVERY_ACTION = "recovery_action"
    USER_AUTHORITY_REQUEST = "user_authority_request"
    REUSE_ACTION = "reuse_action"


class FrontierStatus(str, Enum):
    CANDIDATE = "candidate"
    READY = "ready"
    SELECTED = "selected"
    RUNNING = "running"
    ANSWERED = "answered"
    COMPLETED = "completed"
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_FOR_USER = "waiting_for_user"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class Horizon(str, Enum):
    MICRO = "micro"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class PassVerdict(str, Enum):
    """The adaptive verification verdicts as this projection reads them."""

    ACCEPT = "accept"
    REPAIR = "repair"
    STOP = "stop"
    UNKNOWN = ""

    @classmethod
    def read(cls, value) -> "PassVerdict":
        try:
            return cls(str(value or ""))
        except ValueError:
            return cls.UNKNOWN


#: Statuses that mean the item is still open on the frontier.
OPEN_STATUSES = frozenset({
    FrontierStatus.CANDIDATE, FrontierStatus.READY, FrontierStatus.SELECTED,
    FrontierStatus.RUNNING, FrontierStatus.BLOCKED,
    FrontierStatus.WAITING_FOR_USER, FrontierStatus.DEFERRED})

#: Item kinds whose selected work is resolved by the pass verdict.
WORK_KINDS = frozenset({
    FrontierItemKind.IMPLEMENTATION_EXPERIMENT, FrontierItemKind.RESEARCH_NEED,
    FrontierItemKind.REUSE_ACTION, FrontierItemKind.RECOVERY_ACTION})

#: Item kinds that a later orientation answers by no longer asking them.
ASKING_KINDS = frozenset({
    FrontierItemKind.QUESTION, FrontierItemKind.USER_AUTHORITY_REQUEST})

#: Practitioner action kinds mapped to the frontier item kind they create.
_ACTION_KIND_TO_ITEM = {
    "RESEARCH_SOURCE": FrontierItemKind.RESEARCH_NEED,
    "REUSE_CAPABILITY": FrontierItemKind.REUSE_ACTION,
    "BUILD_CAPABILITY": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "GENERATE_CODE": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "COMPOSE_SOLUTION": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "PARAMETERIZE_CAPABILITY": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "MUTATE_CAPABILITY": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "RUN_TOOL": FrontierItemKind.IMPLEMENTATION_EXPERIMENT,
    "REPAIR": FrontierItemKind.RECOVERY_ACTION,
    "VERIFY": FrontierItemKind.VERIFICATION,
    "ASK_USER": FrontierItemKind.USER_AUTHORITY_REQUEST,
}

_VERDICT_STATUS = {
    PassVerdict.ACCEPT: FrontierStatus.VERIFIED,
    PassVerdict.REPAIR: FrontierStatus.FAILED,
    PassVerdict.STOP: FrontierStatus.COMPLETED,
    PassVerdict.UNKNOWN: FrontierStatus.COMPLETED,
}


class TaskFrontierError(ValueError):
    """A frontier item or snapshot violated its typed contract."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _coerce(enum_type, value, label: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError:
        raise TaskFrontierError(
            f"{label} must be one of "
            f"{[member.value for member in enum_type]}") from None


def _item_id(kind: FrontierItemKind, text: str) -> str:
    return f"{kind.value}.{_digest({'text': text.strip().lower()})[:12]}"


@dataclass(frozen=True)
class FrontierItem:
    """One unit of possible next work with its lifecycle status."""

    frontier_item_id: str
    item_kind: FrontierItemKind
    objective: str
    status: FrontierStatus
    horizon: Horizon
    created_pass: int
    evidence_refs: tuple = ()
    parent_item_refs: tuple = ()

    def __post_init__(self) -> None:
        if not self.frontier_item_id.strip() or not self.objective.strip():
            raise TaskFrontierError("a frontier item needs an id and objective")
        object.__setattr__(self, "item_kind",
                           _coerce(FrontierItemKind, self.item_kind, "item_kind"))
        object.__setattr__(self, "status",
                           _coerce(FrontierStatus, self.status, "status"))
        object.__setattr__(self, "horizon",
                           _coerce(Horizon, self.horizon, "horizon"))
        if isinstance(self.created_pass, bool) or self.created_pass < 1:
            raise TaskFrontierError("created_pass starts at 1")
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "parent_item_refs",
                           tuple(self.parent_item_refs))

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    def with_status(self, status: FrontierStatus) -> "FrontierItem":
        return replace(self, status=_coerce(FrontierStatus, status, "status"))

    def to_dict(self) -> dict:
        return {
            "frontier_item_id": self.frontier_item_id,
            "item_kind": self.item_kind.value, "objective": self.objective,
            "status": self.status.value, "horizon": self.horizon.value,
            "created_pass": self.created_pass,
            "evidence_refs": list(self.evidence_refs),
            "parent_item_refs": list(self.parent_item_refs),
        }


@dataclass(frozen=True)
class FrontierSnapshot:
    """Every frontier item at one pass boundary, chained to its parent."""

    run_id: str
    pass_number: int
    items: tuple
    parent_digest: str = ""
    record_type: str = FRONTIER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != FRONTIER_SCHEMA_VERSION:
            raise TaskFrontierError("unsupported frontier schema version")
        if not self.run_id.strip():
            raise TaskFrontierError("a snapshot needs a run id")
        if isinstance(self.pass_number, bool) or self.pass_number < 1:
            raise TaskFrontierError("pass_number starts at 1")
        items = tuple(self.items)
        if any(not isinstance(item, FrontierItem) for item in items):
            raise TaskFrontierError("items must be FrontierItem records")
        if len({item.frontier_item_id for item in items}) != len(items):
            raise TaskFrontierError("frontier item ids must be unique")
        if self.parent_digest and len(self.parent_digest) != 64:
            raise TaskFrontierError("parent_digest must be sha256 hex")
        object.__setattr__(self, "items", items)

    def counts(self) -> dict:
        counts: dict = {}
        for item in self.items:
            counts[item.status.value] = counts.get(item.status.value, 0) + 1
        return counts

    def open_items(self) -> tuple:
        return tuple(item for item in self.items if item.is_open)

    def to_dict(self, include_digest: bool = True) -> dict:
        value = {
            "record_type": self.record_type, "run_id": self.run_id,
            "pass_number": self.pass_number,
            "parent_digest": self.parent_digest,
            "counts": self.counts(),
            "items": [item.to_dict() for item in self.items],
        }
        if include_digest:
            value["digest"] = self.digest
        return value

    @property
    def digest(self) -> str:
        return _digest(self.to_dict(include_digest=False))


def decision_actions(decision) -> list:
    """The action list of one recorded decision, whichever shape saved it."""
    if not isinstance(decision, dict):
        return []
    if decision.get("action_kind") or decision.get("kind"):
        return [decision]  # one saved decision record is one action
    actions = decision.get("actions")
    if actions is None and isinstance(decision.get("decision"), dict):
        actions = decision["decision"].get("actions")
    return [action for action in (actions or ()) if isinstance(action, dict)]


def _text_of(raw) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("question", "subject", "goal", "text"):
            if raw.get(key):
                return str(raw[key])
    return str(raw or "")


def _text_items(values, kind: FrontierItemKind, status: FrontierStatus,
                horizon: Horizon, pass_number: int, evidence: str) -> list:
    items = []
    for raw in values or ():
        text = _text_of(raw).strip()
        if not text:
            continue
        items.append(FrontierItem(
            _item_id(kind, text), kind, text[:400], status, horizon,
            pass_number, evidence_refs=(evidence,)))
    return items


def frontier_from_adaptive_result(result: dict) -> tuple:
    """Project one saved adaptive result into chained frontier snapshots.

    Pass ``n`` combines the ``n``-th orientation (unknowns become ready
    questions, blocking questions become user-authority requests, ambiguities
    become hypotheses), the ``n``-th action decision (each action becomes an
    experiment, research need, recovery action, verification, or reuse
    action, selected in pass ``n``), and the recovery directives for the
    pass. When pass ``n+1`` opens, the work selected in pass ``n`` is resolved
    by pass ``n``'s verification verdict: accept verifies it, repair fails
    it, anything else completes it. A question the next orientation no
    longer asks is answered; one it keeps asking stays open. Every item
    carries the record path it came from as evidence.
    """
    if not isinstance(result, dict):
        raise TaskFrontierError("frontier projection needs the result mapping")
    run_id = str(result.get("run_id") or "run")
    orientations = list(result.get("orientations") or ())
    decisions = list(result.get("action_decisions") or ())
    verdicts = [PassVerdict.read((item or {}).get("verdict"))
                for item in (result.get("verification") or ())]
    passes = max(len(orientations), len(decisions), len(verdicts),
                 int(result.get("passes") or 0), 1)
    snapshots = []
    carried: dict = {}
    parent_digest = ""
    for pass_number in range(1, passes + 1):
        current: dict = {}
        for item_id, item in carried.items():
            if item.status is FrontierStatus.SELECTED and item.item_kind in WORK_KINDS:
                verdict = (verdicts[item.created_pass - 1]
                           if item.created_pass - 1 < len(verdicts)
                           else PassVerdict.UNKNOWN)
                item = item.with_status(_VERDICT_STATUS[verdict])
            current[item_id] = item
        orientation = (orientations[pass_number - 1]
                       if pass_number - 1 < len(orientations) else {}) or {}
        evidence = f"orientations[{pass_number - 1}]"
        open_questions = _text_items(
            orientation.get("unknowns"), FrontierItemKind.QUESTION,
            FrontierStatus.READY, Horizon.MICRO, pass_number, evidence)
        blocking = _text_items(
            orientation.get("blocking_questions"),
            FrontierItemKind.USER_AUTHORITY_REQUEST,
            FrontierStatus.WAITING_FOR_USER, Horizon.SHORT, pass_number,
            evidence)
        hypotheses = _text_items(
            [item for item in (orientation.get("ambiguities") or ())
             if isinstance(item, dict)], FrontierItemKind.HYPOTHESIS,
            FrontierStatus.CANDIDATE, Horizon.SHORT, pass_number, evidence)
        asked_now = {item.frontier_item_id for item in
                     open_questions + blocking}
        for item_id, item in list(current.items()):
            if (item.item_kind in ASKING_KINDS and item.is_open
                    and item_id not in asked_now and orientation):
                current[item_id] = item.with_status(FrontierStatus.ANSWERED)
        for item in open_questions + blocking + hypotheses:
            current.setdefault(item.frontier_item_id, item)
        decision = (decisions[pass_number - 1]
                    if pass_number - 1 < len(decisions) else {})
        for index, action in enumerate(decision_actions(decision)):
            kind = _ACTION_KIND_TO_ITEM.get(
                str(action.get("action_kind") or action.get("kind") or ""),
                FrontierItemKind.SUBPROBLEM)
            text = str(action.get("goal") or action.get("action_kind") or "")
            if not text.strip():
                continue
            item = FrontierItem(
                _item_id(kind, f"{text}#{pass_number}"), kind,
                text.strip()[:400],
                FrontierStatus.WAITING_FOR_USER
                if kind is FrontierItemKind.USER_AUTHORITY_REQUEST
                else FrontierStatus.SELECTED, Horizon.SHORT, pass_number,
                evidence_refs=(f"action_decisions[{pass_number - 1}]"
                               f".actions[{index}]",))
            current[item.frontier_item_id] = item
        for directive in (result.get("recovery_directives") or ()):
            if (isinstance(directive, dict)
                    and int(directive.get("pass_number") or 0) == pass_number):
                text = str(directive.get("directive") or directive.get(
                    "route") or directive.get("reason") or "recovery")
                item = FrontierItem(
                    _item_id(FrontierItemKind.RECOVERY_ACTION, text),
                    FrontierItemKind.RECOVERY_ACTION, text[:400],
                    FrontierStatus.SELECTED, Horizon.MEDIUM, pass_number,
                    evidence_refs=("recovery_directives",))
                current.setdefault(item.frontier_item_id, item)
        snapshot = FrontierSnapshot(
            run_id=run_id, pass_number=pass_number,
            items=tuple(current.values()), parent_digest=parent_digest)
        snapshots.append(snapshot)
        parent_digest = snapshot.digest
        carried = dict(current)
    return tuple(snapshots)


def self_test() -> dict:
    """Prove chaining, verdict-resolved work, typed vocabularies, tolerance."""
    from .adaptive_practitioner_records import NEXT_ACTION_KINDS

    result = {
        "run_id": "run-frontier",
        "passes": 3,
        "orientations": [
            {"unknowns": ["Which column is the target?"],
             "blocking_questions": ["Which destination is required?"],
             "ambiguities": [{"subject": "destination",
                              "state": "USER_CLARIFICATION_REQUIRED"}]},
            {"unknowns": []},
            {"unknowns": ["Is the split leaky?"]},
        ],
        "action_decisions": [
            {"actions": [{"action_kind": "COMPOSE_SOLUTION",
                          "goal": "Build a logistic baseline."}]},
            {"decision": {"actions": [{"action_kind": "REPAIR",
                                       "goal": "Fix the read-only path."}]}},
            {"actions": [{"action_kind": "VERIFY",
                          "goal": "Verify submission schema."}]},
        ],
        "verification": [{"verdict": "repair"}, {"verdict": "accept"},
                         {"verdict": "accept"}],
        "recovery_directives": [{"pass_number": 2, "directive": "soft_reset"}],
    }
    snapshots = frontier_from_adaptive_result(result)
    first, second, third = snapshots
    kinds_first = {item.item_kind for item in first.items}
    baseline = next(item for item in first.items
                    if item.item_kind is FrontierItemKind.IMPLEMENTATION_EXPERIMENT)
    baseline_second = next(item for item in second.items
                           if item.frontier_item_id == baseline.frontier_item_id)
    repair_second = next(item for item in second.items
                         if item.item_kind is FrontierItemKind.RECOVERY_ACTION
                         and "read-only" in item.objective)
    repair_third = next(item for item in third.items
                        if item.frontier_item_id == repair_second.frontier_item_id)
    question = next(item for item in first.items
                    if item.item_kind is FrontierItemKind.QUESTION)
    question_second = next(item for item in second.items
                           if item.frontier_item_id == question.frontier_item_id)
    rejected = 0
    for bad in (
            lambda: FrontierItem("x", "wish", "o", "ready", "micro", 1),
            lambda: FrontierItem("x", "question", "o", "maybe", "micro", 1),
            lambda: FrontierItem("x", "question", "o", "ready", "eon", 1),
            lambda: FrontierSnapshot("r", 0, ()),
    ):
        try:
            bad()
        except TaskFrontierError:
            rejected += 1
    sparse = frontier_from_adaptive_result({"run_id": "r", "passes": 2})
    unmapped = sorted(set(_ACTION_KIND_TO_ITEM) - set(NEXT_ACTION_KINDS))
    tests = [{
        "test": "first_pass_frontier_holds_questions_authority_hypotheses_and_experiments",
        "passed": kinds_first == {
            FrontierItemKind.QUESTION, FrontierItemKind.USER_AUTHORITY_REQUEST,
            FrontierItemKind.HYPOTHESIS,
            FrontierItemKind.IMPLEMENTATION_EXPERIMENT}
        and baseline.status is FrontierStatus.SELECTED
        and question.status is FrontierStatus.READY,
        "detail": str(sorted(kind.value for kind in kinds_first)),
    }, {
        "test": "work_is_resolved_by_its_own_pass_verdict_and_questions_answer_when_they_stop_recurring",
        "passed": baseline_second.status is FrontierStatus.FAILED
        and repair_third.status is FrontierStatus.VERIFIED
        and question_second.status is FrontierStatus.ANSWERED
        and repair_second.status is FrontierStatus.SELECTED,
        "detail": f"{baseline_second.status.value} {repair_third.status.value} "
                  f"{question_second.status.value}",
    }, {
        "test": "snapshots_chain_by_digest_and_carry_counts",
        "passed": (first.parent_digest == "" and second.parent_digest == first.digest
                   and third.parent_digest == second.digest
                   and second.counts().get(FrontierStatus.FAILED.value) == 1
                   and third.to_dict()["digest"] == third.digest
                   and third.to_dict()["items"][0]["status"] in
                   {member.value for member in FrontierStatus}),
        "detail": second.digest[:16],
    }, {
        "test": "vocabularies_are_closed_enums_and_action_kinds_come_from_the_practitioner_authority",
        "passed": rejected == 4 and not unmapped
        and FrontierItem("x", "question", "o", "ready", "micro", 1).status
        is FrontierStatus.READY,
        "detail": f"{rejected}/4 rejected; unmapped action kinds={unmapped}",
    }, {
        "test": "sparse_results_still_project_without_items",
        "passed": len(sparse) == 2 and all(len(s.items) == 0 for s in sparse),
        "detail": f"passes={len(sparse)}",
    }]
    return {"module": "core.task_frontier",
            "passed": all(item["passed"] for item in tests), "tests": tests}

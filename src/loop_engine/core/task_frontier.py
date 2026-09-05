"""Task frontier: the durable set of possible next work, projected per pass.

Architectural role: passive, digest-chained snapshots of what a Practitioner
run still had to answer, try, verify, or recover at each pass boundary. The
adaptive Practitioner already records orientations, action decisions,
verification verdicts, failures, and recovery directives; this module joins
them into one typed frontier per pass so a reader, a Studio view, or a later
run can ask which questions stayed open, which work was selected, which pass
verification rows were recorded, and how far the run stepped back, without
re-reading prompt text. The saved result alone cannot authenticate complete
question-answer or action-outcome lineage, so the projection keeps those
statuses unresolved and treats verification paths as advisory. Snapshots are
rebuilt from the saved adaptive result; they are never a second source of
truth or an active frontier controller.

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
    def read(cls, value) -> PassVerdict:
        try:
            return cls(str(value or ""))
        except ValueError:
            return cls.UNKNOWN


#: Statuses that mean the item is still open on the frontier.
OPEN_STATUSES = frozenset({
    FrontierStatus.CANDIDATE, FrontierStatus.READY, FrontierStatus.SELECTED,
    FrontierStatus.RUNNING, FrontierStatus.BLOCKED,
    FrontierStatus.WAITING_FOR_USER, FrontierStatus.DEFERRED})

#: Item kinds that retain same-pass verification paths as advisory evidence.
WORK_KINDS = frozenset({
    FrontierItemKind.IMPLEMENTATION_EXPERIMENT, FrontierItemKind.RESEARCH_NEED,
    FrontierItemKind.REUSE_ACTION, FrontierItemKind.RECOVERY_ACTION})

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
    """Identify one exact lowercased, trimmed text, not semantic sameness."""
    return f"{kind.value}.{_digest({'text': text.strip().lower()})[:12]}"


def _verification_evidence(records) -> dict[int, tuple[str, ...]]:
    """Return pass-addressable record paths without interpreting outcomes.

    The saved adaptive result is insufficient to re-authenticate the complete
    action, execution, verifier, event-history, and artifact chain. Every row
    therefore remains advisory at this passive projection boundary.
    """
    if not isinstance(records, (list, tuple)):
        return {}
    evidence_by_pass: dict[int, list[str]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        pass_number = record.get("pass_number")
        if type(pass_number) is not int or pass_number < 1:
            continue
        evidence_by_pass.setdefault(pass_number, []).append(
            f"verification[{index}]")
    return {
        pass_number: tuple(refs)
        for pass_number, refs in evidence_by_pass.items()
    }


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

    def with_status(self, status: FrontierStatus) -> FrontierItem:
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
    return [action for action, _path in _decision_action_entries(decision)]


def _decision_action_entries(decision) -> list:
    """Return each action with its exact path inside one decision record."""
    if not isinstance(decision, dict):
        return []
    if decision.get("action_kind") or decision.get("kind"):
        return [(decision, "")]  # one saved decision record is one action
    actions = decision.get("actions")
    prefix = ".actions"
    if actions is None and isinstance(decision.get("decision"), dict):
        actions = decision["decision"].get("actions")
        prefix = ".decision.actions"
    return [(action, f"{prefix}[{index}]")
            for index, action in enumerate(actions or ())
            if isinstance(action, dict)]


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
    pass. Verification rows are retained as pass-level advisory references but
    never change item status here: this saved-result projection cannot
    re-authenticate their complete action, execution, verifier, event-history,
    and artifact lineage. Missing, malformed, wrong-pass, unbound, duplicate,
    or contradictory evidence therefore leaves work selected. Question text
    has no answer record in this input, so disappearance or renaming never
    fabricates an answered status. A future trusted resolution adapter must
    supply exact outcome and question-answer bindings before those terminal
    statuses can be emitted.
    """
    if not isinstance(result, dict):
        raise TaskFrontierError("frontier projection needs the result mapping")
    run_id = str(result.get("run_id") or "run")
    orientations = list(result.get("orientations") or ())
    decisions = list(result.get("action_decisions") or ())
    verification_records = result.get("verification") or ()
    pass_advisory = _verification_evidence(verification_records)
    verification_count = (len(verification_records)
                          if isinstance(verification_records, (list, tuple))
                          else 0)
    passes = max(len(orientations), len(decisions), verification_count,
                 int(result.get("passes") or 0), 1)
    snapshots = []
    carried: dict = {}
    parent_digest = ""
    for pass_number in range(1, passes + 1):
        current: dict = {}
        for item_id, item in carried.items():
            if item.status is FrontierStatus.SELECTED and item.item_kind in WORK_KINDS:
                pass_evidence = pass_advisory.get(item.created_pass, ())
                if pass_evidence:
                    item = replace(
                        item, evidence_refs=tuple(dict.fromkeys((
                            *item.evidence_refs, *pass_evidence))))
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
        for item in open_questions + blocking + hypotheses:
            current.setdefault(item.frontier_item_id, item)
        decision = (decisions[pass_number - 1]
                    if pass_number - 1 < len(decisions) else {})
        for action, action_path in _decision_action_entries(decision):
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
                evidence_refs=tuple(dict.fromkeys((
                    f"action_decisions[{pass_number - 1}]{action_path}",
                    *pass_advisory.get(pass_number, ())))))
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
    """Prove chaining, advisory evidence, typed vocabularies, and tolerance."""
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
            {"actions": [{"decision_id": "action:baseline",
                          "action_kind": "COMPOSE_SOLUTION",
                          "goal": "Build a logistic baseline."}]},
            {"decision": {"actions": [{"decision_id": "action:repair",
                                       "action_kind": "REPAIR",
                                       "goal": "Fix the read-only path."}]}},
            {"actions": [{"decision_id": "action:verify",
                          "action_kind": "VERIFY",
                          "goal": "Verify submission schema."}]},
        ],
        "verification": [
            {"record_type": "adaptive_verification/v2", "pass_number": 1,
             "verdict": "repair", "semantic_verification_observed": True,
             "subject": {
                 "record_type": "adaptive_verification_subject/v1",
                 "run_id": "run-frontier", "action_id": "action:baseline",
                 "action_occurrence_ref": "occurrence:baseline",
                 "plan_digest": "a" * 64, "result_digests": ["b" * 64],
                 "execution_refs": []}},
            {"record_type": "adaptive_verification/v2", "pass_number": 2,
             "verdict": "accept", "semantic_verification_observed": True,
             "subject": {
                 "record_type": "adaptive_verification_subject/v1",
                 "run_id": "run-frontier", "action_id": "action:repair",
                 "action_occurrence_ref": "occurrence:repair",
                 "plan_digest": "c" * 64, "result_digests": ["d" * 64],
                 "execution_refs": []}},
            {"record_type": "adaptive_verification/v2", "pass_number": 3,
             "verdict": "accept", "semantic_verification_observed": True,
             "subject": {
                 "record_type": "adaptive_verification_subject/v1",
                 "run_id": "run-frontier", "action_id": "action:verify",
                 "action_occurrence_ref": "occurrence:verify",
                 "plan_digest": "e" * 64, "result_digests": ["f" * 64],
                 "execution_refs": []}},
        ],
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

    def verification_record(action_id: str, *, pass_number: int = 1,
                            verdict: str = "accept",
                            run_id: str = "run-outcome") -> dict:
        return {
            "record_type": "adaptive_verification/v2",
            "pass_number": pass_number,
            "verdict": verdict,
            "semantic_verification_observed": True,
            "subject": {
                "record_type": "adaptive_verification_subject/v1",
                "run_id": run_id,
                "action_id": action_id,
                "action_occurrence_ref": "occurrence:" + action_id,
                "plan_digest": "1" * 64,
                "result_digests": ["2" * 64],
                "execution_refs": [],
            },
        }

    def projected_work(records, *, action_id: str = "action:one") -> FrontierItem:
        projected = frontier_from_adaptive_result({
            "run_id": "run-outcome",
            "passes": 2,
            "orientations": [{}, {}],
            "action_decisions": [
                {"decision_id": action_id,
                 "action_kind": "COMPOSE_SOLUTION",
                 "goal": "Build candidate."},
                {},
            ],
            "verification": records,
        })
        return next(item for item in projected[1].items
                    if item.item_kind
                    is FrontierItemKind.IMPLEMENTATION_EXPERIMENT)

    accepted_work = projected_work([
        verification_record("action:one")])
    single_pass = frontier_from_adaptive_result({
        "run_id": "run-outcome", "passes": 1,
        "orientations": [{}],
        "action_decisions": [{
            "decision_id": "action:one",
            "action_kind": "COMPOSE_SOLUTION", "goal": "Build candidate."}],
        "verification": [verification_record("action:one")],
    })
    single_pass_work = next(
        item for item in single_pass[0].items
        if item.item_kind is FrontierItemKind.IMPLEMENTATION_EXPERIMENT)
    missing_work = projected_work([])
    malformed_work = projected_work([{
        "record_type": "adaptive_verification/v2", "pass_number": "1",
        "verdict": "accept"}])
    unbound_work = projected_work([{
        "record_type": "adaptive_verification/v2", "pass_number": 1,
        "verdict": "accept", "semantic_verification_observed": True,
        "subject": None}])
    unrelated_work = projected_work([
        verification_record("action:one", pass_number=2)])
    stopped_work = projected_work([
        verification_record("action:one", verdict="stop")])
    contradictory_work = projected_work([
        verification_record("action:one", verdict="accept"),
        verification_record("action:one", verdict="repair"),
    ])

    multi_action = frontier_from_adaptive_result({
        "run_id": "run-outcome", "passes": 2,
        "orientations": [{}, {}],
        "action_decisions": [{"actions": [
            {"decision_id": "action:first",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build first."},
            {"decision_id": "action:second",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build second."},
        ]}, {}],
        "verification": [verification_record("action:second")],
    })
    multi_status = {item.objective: item.status
                    for item in multi_action[1].items
                    if item.item_kind
                    is FrontierItemKind.IMPLEMENTATION_EXPERIMENT}

    forged_plan = verification_record("action:one")
    forged_plan["subject"]["plan_digest"] = "z" * 64
    duplicate_execution = verification_record("action:one")
    duplicate_execution["subject"]["execution_refs"] = [
        "execution:old", "execution:old"]
    nested_contradiction = verification_record("action:one")
    nested_contradiction["evaluation"] = {"verdict": "repair"}
    adversarial_work = tuple(projected_work([record]) for record in (
        forged_plan, duplicate_execution, nested_contradiction))

    duplicate_decision = frontier_from_adaptive_result({
        "run_id": "run-outcome", "passes": 2,
        "orientations": [{}, {}],
        "action_decisions": [{"actions": [
            {"decision_id": "action:duplicate",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build alpha."},
            {"decision_id": "action:duplicate",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build beta."},
        ]}, {}],
        "verification": [verification_record("action:duplicate")],
    })
    duplicate_decision_work = tuple(
        item for item in duplicate_decision[1].items
        if item.item_kind is FrontierItemKind.IMPLEMENTATION_EXPERIMENT)

    delayed = verification_record("action:repeated", pass_number=2)
    delayed["subject"]["action_occurrence_ref"] = "occurrence:old"
    repeated_action = frontier_from_adaptive_result({
        "run_id": "run-outcome", "passes": 3,
        "orientations": [{}, {}, {}],
        "action_decisions": [
            {"decision_id": "action:repeated",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build repeated."},
            {"decision_id": "action:repeated",
             "action_kind": "COMPOSE_SOLUTION", "goal": "Build repeated."},
            {},
        ],
        "verification": [delayed],
    })
    repeated_action_work = tuple(
        item for item in repeated_action[2].items
        if item.item_kind is FrontierItemKind.IMPLEMENTATION_EXPERIMENT)

    renamed = frontier_from_adaptive_result({
        "run_id": "run-questions", "passes": 2,
        "orientations": [
            {"unknowns": ["Which column is the target?"]},
            {"unknowns": ["Which field is the target?"]},
        ],
    })
    renamed_questions = tuple(
        item for item in renamed[1].items
        if item.item_kind is FrontierItemKind.QUESTION)
    repeated = frontier_from_adaptive_result({
        "run_id": "run-repeat", "passes": 2,
        "orientations": [
            {"unknowns": [" Which column is the target? "]},
            {"unknowns": ["which COLUMN is the TARGET?"]},
        ],
    })
    repeated_questions = tuple(
        item for item in repeated[1].items
        if item.item_kind is FrontierItemKind.QUESTION)
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
        "test": "pass_verdicts_stay_advisory_and_question_disappearance_does_not_answer",
        "passed": baseline_second.status is FrontierStatus.SELECTED
        and repair_third.status is FrontierStatus.SELECTED
        and question_second.status is FrontierStatus.READY
        and repair_second.status is FrontierStatus.SELECTED
        and repair_second.evidence_refs[0]
        == "action_decisions[1].decision.actions[0]"
        and "verification[0]" in baseline_second.evidence_refs
        and "verification[1]" in repair_third.evidence_refs,
        "detail": f"{baseline_second.status.value} {repair_third.status.value} "
                  f"{question_second.status.value}",
    }, {
        "test": "snapshots_chain_by_digest_and_carry_counts",
        "passed": (first.parent_digest == "" and second.parent_digest == first.digest
                   and third.parent_digest == second.digest
                   and second.counts().get(FrontierStatus.SELECTED.value) == 3
                   and second.counts().get(FrontierStatus.FAILED.value, 0) == 0
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
        "test": "reported_accept_is_retained_as_evidence_without_verifying_work",
        "passed": (accepted_work.status is FrontierStatus.SELECTED
                   and accepted_work.evidence_refs[0] == "action_decisions[0]"
                   and accepted_work.evidence_refs[-1] == "verification[0]"
                   and single_pass_work.status is FrontierStatus.SELECTED
                   and single_pass_work.evidence_refs[-1] == "verification[0]"
                   and multi_status == {
                       "Build first.": FrontierStatus.SELECTED,
                       "Build second.": FrontierStatus.SELECTED}),
        "detail": str(multi_status),
    }, {
        "test": "missing_malformed_and_wrong_pass_outcomes_remain_unresolved",
        "passed": all(item.status is FrontierStatus.SELECTED for item in (
            missing_work, malformed_work, unrelated_work))
        and "verification[0]" not in malformed_work.evidence_refs
        and "verification[0]" not in unrelated_work.evidence_refs,
        "detail": "missing, malformed, and unrelated evidence stayed selected",
    }, {
        "test": "unbound_stop_and_contradictory_verdicts_are_advisory_only",
        "passed": all(item.status is FrontierStatus.SELECTED for item in (
            unbound_work, stopped_work, contradictory_work))
        and "verification[0]" in unbound_work.evidence_refs
        and "verification[0]" in stopped_work.evidence_refs
        and {"verification[0]", "verification[1]"}.issubset(
            contradictory_work.evidence_refs),
        "detail": str({
            "unbound": unbound_work.evidence_refs,
            "stop": stopped_work.evidence_refs,
            "contradictory": contradictory_work.evidence_refs}),
    }, {
        "test": "forged_or_ambiguous_action_lineage_never_creates_an_outcome",
        "passed": (all(item.status is FrontierStatus.SELECTED
                       for item in adversarial_work)
                   and len(duplicate_decision_work) == 2
                   and all(item.status is FrontierStatus.SELECTED
                           for item in duplicate_decision_work)
                   and len(repeated_action_work) == 2
                   and all(item.status is FrontierStatus.SELECTED
                           for item in repeated_action_work)),
        "detail": (
            "forged plan, duplicate execution, repeated decision, delayed "
            "occurrence, and nested verdict mismatch stayed unresolved"),
    }, {
        "test": "renamed_questions_are_distinct_and_neither_is_answered",
        "passed": (len(renamed_questions) == 2
                   and len({item.frontier_item_id
                            for item in renamed_questions}) == 2
                   and all(item.status is FrontierStatus.READY
                           for item in renamed_questions)),
        "detail": str([item.frontier_item_id for item in renamed_questions]),
    }, {
        "test": "case_and_outer_whitespace_reuse_exact_text_projection_identity",
        "passed": (len(repeated_questions) == 1
                   and repeated_questions[0].status is FrontierStatus.READY),
        "detail": str([item.frontier_item_id for item in repeated_questions]),
    }, {
        "test": "sparse_results_still_project_without_items",
        "passed": len(sparse) == 2 and all(len(s.items) == 0 for s in sparse),
        "detail": f"passes={len(sparse)}",
    }]
    return {"module": "core.task_frontier",
            "passed": all(item["passed"] for item in tests), "tests": tests}

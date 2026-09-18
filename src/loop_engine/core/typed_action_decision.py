"""Typed action decisions over an element table: one operation and one target in one call.

A browser or desktop step does not need a screenshot when the page can be
read as an indexed table of controls: a judgment model given the goal and
the table can name one operation from a declared vocabulary and one target
row in a single round trip. This module owns the element table and its
text rendering, the declared action vocabulary, the bounded request, the
admission of an answer under the registered action contract, and the
decision record. Admission refuses an operation outside the vocabulary, a
target outside the table, a typing operation without text, and a finishing
operation with a target. A done or blocked decision is a claim about the
task, never its acceptance: the record says the outcome still needs
independent verification. Judges are injected exactly as for typed
decisions; a live provider enters through a declared network adapter. The
module grants no authority and performs no action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .model_call_contract import ModelCallObservation, ModelCallRequest, ModelInput, record_model_call
from .model_ontology import MODALITIES
from .model_routes import screen_route
from .operation_cost_capture import OperationCostCapture
from .response_contracts import TYPED_ACTION_DECISION, registered_contract
from .typed_decision import (DECISION_PURPOSE, JUDGMENT_KIND, JudgeResponse, TypedDecisionError,
                             validate_typed_decision_route)

RECORD_TYPE = "typed_action_decision/v1"
#: The browser vocabulary the first adopter of this pattern uses; a caller declares its own.
BROWSER_OPERATIONS = ("click", "type_text", "select", "scroll_up", "scroll_down", "wait", "done", "blocked")
BROWSER_TARGET_OPERATIONS = ("click", "type_text", "select")
BROWSER_TEXT_OPERATIONS = ("type_text",)
BROWSER_TERMINAL_OPERATIONS = ("done", "blocked")
DEFAULT_MAX_ROWS = 200
PART_LABELS = ("goal", "element_table", "evidence")
IMPLEMENTATION_ID = "typed_action_decision_route"
OPERATION_PREFIX = "typed_action_decision"


class ActionVocabularyError(TypedDecisionError):
    """A vocabulary, table, request, or answer is invalid."""


@dataclass(frozen=True)
class ActionVocabulary:
    """The operations a step may choose, which need a target, text, or end the task."""

    operations: tuple[str, ...] = BROWSER_OPERATIONS
    target_operations: tuple[str, ...] = BROWSER_TARGET_OPERATIONS
    text_operations: tuple[str, ...] = BROWSER_TEXT_OPERATIONS
    terminal_operations: tuple[str, ...] = BROWSER_TERMINAL_OPERATIONS

    def __post_init__(self):
        operations = tuple(self.operations)
        if not operations or len(set(operations)) != len(operations) or any(
                not isinstance(item, str) or not item.strip() for item in operations):
            raise ActionVocabularyError("operations must be unique nonempty names")
        for name in ("target_operations", "text_operations", "terminal_operations"):
            values = tuple(getattr(self, name))
            if any(item not in operations for item in values):
                raise ActionVocabularyError(f"{name} must be drawn from the operations")
            object.__setattr__(self, name, values)
        if set(self.terminal_operations) & set(self.target_operations):
            raise ActionVocabularyError("a terminal operation cannot need a target")
        object.__setattr__(self, "operations", operations)


@dataclass(frozen=True)
class ElementRow:
    """One indexed control as a reader saw it."""

    index: int
    control: str
    label: str = ""
    value: str = ""

    def __post_init__(self):
        if type(self.index) is not int or self.index < 0:
            raise ActionVocabularyError("an element index is a non-negative integer")
        for name in ("control", "label", "value"):
            if not isinstance(getattr(self, name), str):
                raise ActionVocabularyError(f"element {name} must be text")
        if not self.control.strip():
            raise ActionVocabularyError("an element names its control type")

    def render(self) -> str:
        value = self.value.strip() or "empty"
        return f"[{self.index}] {self.control.strip()}  {self.label.strip()}  · {value}"


@dataclass(frozen=True)
class ElementTable:
    """The indexed controls of one page state, in reading order."""

    rows: tuple[ElementRow, ...]

    def __post_init__(self):
        rows = tuple(self.rows)
        if not rows or any(not isinstance(item, ElementRow) for item in rows):
            raise ActionVocabularyError("an element table carries at least one typed ElementRow")
        if len({row.index for row in rows}) != len(rows):
            raise ActionVocabularyError("element indices must be unique")
        object.__setattr__(self, "rows", rows)

    @property
    def indices(self) -> tuple[int, ...]:
        return tuple(row.index for row in self.rows)

    def render(self) -> str:
        return "\n".join(row.render() for row in self.rows)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.render().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TypedActionRequest:
    """One goal over one element table under a declared vocabulary."""

    goal: str
    table: ElementTable
    vocabulary: ActionVocabulary = field(default_factory=ActionVocabulary)
    evidence: tuple[str, ...] = ()
    max_rows: int = DEFAULT_MAX_ROWS
    response_contract_id: str = TYPED_ACTION_DECISION
    semantic_call_id: str = ""

    def __post_init__(self):
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ActionVocabularyError("a typed action request needs a goal")
        if not isinstance(self.table, ElementTable) or not isinstance(self.vocabulary, ActionVocabulary):
            raise ActionVocabularyError("a typed action request needs a typed table and vocabulary")
        if type(self.max_rows) is not int or self.max_rows < 1:
            raise ActionVocabularyError("max_rows must be a positive integer")
        if len(self.table.rows) > self.max_rows:
            raise ActionVocabularyError(
                f"the element table has {len(self.table.rows)} rows, above the declared {self.max_rows}; "
                "filter or page the table before asking")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, str) for item in evidence):
            raise ActionVocabularyError("evidence parts must be text")
        object.__setattr__(self, "evidence", evidence)

    def to_model_call(self, route_name: str = "") -> ModelCallRequest:
        contract = registered_contract(self.response_contract_id)
        parts = [ModelInput(MODALITIES[0], self.goal, label=PART_LABELS[0]),
                 ModelInput(MODALITIES[0], self.table.render(), label=PART_LABELS[1])]
        parts.extend(ModelInput(MODALITIES[0], item, label=PART_LABELS[2]) for item in self.evidence if item)
        return ModelCallRequest(DECISION_PURPOSE, JUDGMENT_KIND, tuple(parts),
                                system=f"Operations: {', '.join(self.vocabulary.operations)}.",
                                response_contract_id=self.response_contract_id,
                                suggested_output=contract.suggested_output, route_name=route_name,
                                semantic_call_id=self.semantic_call_id)


@dataclass(frozen=True)
class ActionDecision:
    """One admitted action: the operation, its target row when it needs one, and the confidences."""

    operation: str
    target_index: "int | None"
    operation_confidence: float
    target_confidence: "float | None"
    text: str = ""
    abstained: bool = False
    reason: str = ""
    requires_verification: bool = False
    route: str = ""
    provider: str = ""
    model: str = ""
    output_digest: str = ""

    @property
    def confidence(self) -> float:
        """The weakest named confidence of the decision."""
        values = [self.operation_confidence] + ([self.target_confidence] if self.target_confidence is not None else [])
        return round(min(values), 3)

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "operation": self.operation, "target_index": self.target_index,
                "operation_confidence": self.operation_confidence,
                "target_confidence": self.target_confidence, "confidence": self.confidence,
                "text": self.text, "abstained": self.abstained, "reason": self.reason,
                "requires_verification": self.requires_verification, "route": self.route,
                "provider": self.provider, "model": self.model, "output_digest": self.output_digest}


def _unit(value, name: str) -> float:
    if type(value) not in (int, float) or not 0 <= value <= 1:
        raise ActionVocabularyError(f"{name} must be a number from 0 to 1")
    return float(value)


def admit_action_decision(raw: dict, request: TypedActionRequest, *, route: str = "",
                          provider: str = "", model: str = "") -> ActionDecision:
    """The answer under the action contract, or a typed refusal naming the rule it broke."""
    if request.response_contract_id != TYPED_ACTION_DECISION:
        raise ActionVocabularyError("an action answer is admitted only under the typed action contract")
    if not isinstance(raw, dict):
        raise ActionVocabularyError("an action answer is a mapping")
    abstain = raw.get("abstain", False)
    if type(abstain) is not bool:
        raise ActionVocabularyError("abstain must be a Boolean")
    reason = str(raw.get("reason", "") or "")
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if abstain:
        return ActionDecision("", None, _unit(raw.get("operation_confidence", 0.0), "operation_confidence"),
                              None, abstained=True, reason=reason, route=route, provider=provider,
                              model=model, output_digest=digest)
    operation = raw.get("operation")
    vocabulary = request.vocabulary
    if operation not in vocabulary.operations:
        raise ActionVocabularyError(f"operation must be one of {vocabulary.operations}")
    operation_confidence = _unit(raw.get("operation_confidence"), "operation_confidence")
    target = raw.get("target_index")
    target_confidence = None
    if operation in vocabulary.target_operations:
        if type(target) is not int or target not in request.table.indices:
            raise ActionVocabularyError(f"operation {operation!r} needs a target index from the table")
        target_confidence = _unit(raw.get("target_confidence"), "target_confidence")
    elif target is not None:
        raise ActionVocabularyError(f"operation {operation!r} takes no target")
    text = str(raw.get("text", "") or "")
    if operation in vocabulary.text_operations and not text.strip():
        raise ActionVocabularyError(f"operation {operation!r} needs the text to type")
    if operation not in vocabulary.text_operations and text.strip():
        raise ActionVocabularyError(f"operation {operation!r} carries no text")
    return ActionDecision(operation, target if target_confidence is not None else None,
                          operation_confidence, target_confidence, text=text, reason=reason,
                          requires_verification=operation in vocabulary.terminal_operations,
                          route=route, provider=provider, model=model, output_digest=digest)


@dataclass(frozen=True)
class ActionOutcome:
    decision: ActionDecision
    call_record: object
    cost_record: object = None


def decide_action(request: TypedActionRequest, route, judge, *, cost_ledger=None, run_id: str = "",
                  call_id: str = "", policy=None) -> ActionOutcome:
    """Ask a judge for one action; the answer is admitted, recorded, and never performed here."""
    if not isinstance(request, TypedActionRequest):
        raise ActionVocabularyError("decide_action needs a typed TypedActionRequest")
    validate_typed_decision_route(route)
    screen_route(route, purpose=request.to_model_call().purpose, policy=policy)
    call = request.to_model_call(route.name)
    capture = None
    if cost_ledger is not None:
        capture = OperationCostCapture(cost_ledger, f"{OPERATION_PREFIX}.{request.vocabulary.operations[0]}",
                                       IMPLEMENTATION_ID, run_id or "unknown-run")
        capture.phase("execution")
    try:
        response = judge(call, request)
        if not isinstance(response, JudgeResponse):
            raise ActionVocabularyError("a judge returns a typed JudgeResponse")
        decision = admit_action_decision(response.raw, request, route=route.name,
                                         provider=response.provider, model=response.model)
    except Exception:
        if capture is not None:
            capture.end("failed")
        raise
    record = record_model_call(call, call_id or f"{OPERATION_PREFIX}:{request.table.digest[:16]}",
                               ModelCallObservation(route=route.name, provider=response.provider,
                                                    model=response.model,
                                                    input_tokens=response.input_tokens,
                                                    output_tokens=response.output_tokens,
                                                    latency_ms=response.latency_ms,
                                                    output_text=json.dumps(response.raw, sort_keys=True,
                                                                           default=str),
                                                    admitted=True, admitted_value=response.raw))
    cost_record = None
    if capture is not None:
        capture.end("unknown", model_calls=1, input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens)
        cost_record = capture.record
    return ActionOutcome(decision, record, cost_record)


def self_test() -> dict:
    """Tables, vocabularies, admission rules, the judge path, and the records."""
    from .operation_cost_records import OperationCostLedger
    from .typed_decision import EndpointJudge
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except TypedDecisionError:
            return True
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return False
        return False

    table = ElementTable((ElementRow(1, "button", "Search"), ElementRow(3, "combobox", "Where to?"),
                          ElementRow(7, "textbox", "Departure", "2026-10-02")))
    request = TypedActionRequest("Search flights from Zurich to London", table,
                                 evidence=("the origin is already filled",))
    check("an_element_table_renders_indexed_rows_and_the_request_carries_them_as_labeled_parts",
          table.render().splitlines()[1] == "[3] combobox  Where to?  · empty"
          and table.indices == (1, 3, 7)
          and [part.label for part in request.to_model_call().inputs] == ["goal", "element_table", "evidence"]
          and request.to_model_call().response_contract_id == TYPED_ACTION_DECISION
          and "Operations: click, type_text" in request.to_model_call().system)
    typed = admit_action_decision({"operation": "type_text", "target_index": 3, "operation_confidence": 0.9,
                                   "target_confidence": 0.8, "text": "London", "abstain": False,
                                   "reason": "the destination field"}, request)
    done = admit_action_decision({"operation": "done", "operation_confidence": 0.7, "abstain": False}, request)
    check("a_typing_action_names_its_target_and_text_and_the_weakest_confidence_is_the_decisions",
          typed.operation == "type_text" and typed.target_index == 3 and typed.text == "London"
          and typed.confidence == 0.8 and typed.requires_verification is False
          and typed.to_dict()["record_type"] == RECORD_TYPE)
    check("a_finishing_action_takes_no_target_and_still_needs_independent_verification",
          done.target_index is None and done.requires_verification is True and done.confidence == 0.7)
    abstained = admit_action_decision({"abstain": True, "operation_confidence": 0.2, "reason": "unclear"}, request)
    check("an_abstention_names_no_operation",
          abstained.abstained and abstained.operation == "" and abstained.target_index is None)
    check("admission_refuses_unknown_operations_targets_outside_the_table_and_missing_or_stray_text",
          all(refuses(lambda raw=raw: admit_action_decision(raw, request)) for raw in (
              {"operation": "hover", "operation_confidence": 0.9, "abstain": False},
              {"operation": "click", "target_index": 2, "operation_confidence": 0.9,
               "target_confidence": 0.9, "abstain": False},
              {"operation": "click", "target_index": "3", "operation_confidence": 0.9,
               "target_confidence": 0.9, "abstain": False},
              {"operation": "type_text", "target_index": 3, "operation_confidence": 0.9,
               "target_confidence": 0.9, "text": "", "abstain": False},
              {"operation": "click", "target_index": 1, "operation_confidence": 0.9,
               "target_confidence": 0.9, "text": "stray", "abstain": False},
              {"operation": "done", "target_index": 1, "operation_confidence": 0.9, "abstain": False},
              {"operation": "click", "target_index": 1, "operation_confidence": 1.5,
               "target_confidence": 0.9, "abstain": False},
              {"operation": "click", "target_index": 1, "operation_confidence": 0.9,
               "target_confidence": 0.9, "abstain": "no"},
              "not a mapping")))
    other_contract = TypedActionRequest("goal", table, response_contract_id="typed_decision.choice")
    check("an_answer_under_another_contract_an_oversized_table_and_bad_vocabularies_are_refused",
          refuses(lambda: admit_action_decision({"operation": "done", "operation_confidence": 0.9,
                                                 "abstain": False}, other_contract))
          and refuses(lambda: TypedActionRequest("goal", table, max_rows=2))
          and refuses(lambda: ElementTable((ElementRow(1, "button"), ElementRow(1, "link"))))
          and refuses(lambda: ActionVocabulary(operations=("click", "click")))
          and refuses(lambda: ActionVocabulary(target_operations=("hover",)))
          and refuses(lambda: ActionVocabulary(operations=("go", "done"), target_operations=("done",),
                                               terminal_operations=("done",)))
          and refuses(lambda: ElementRow(-1, "button")))
    seen = []

    def transport(payload):
        seen.append(payload)
        return {"decision": "click", "probabilities": {"click": 1.0}, "confidence": 0.9,
                "reason": "endpoint judges are shaped for choices; the action judge maps below"}

    class ActionJudge:
        """A fixture judge that answers the action contract through an injected transport."""

        def __init__(self, transport, provider="fixture", model="fixture-action-judge"):
            self.transport, self.provider, self.model = transport, provider, model
            self.endpoint = EndpointJudge(transport, provider=provider, model=model)

        def route(self, name):
            return self.endpoint.route(name)

        def __call__(self, call, request):
            body = self.transport({"goal": request.goal, "rows": len(request.table.rows)})
            return JudgeResponse({"operation": body["decision"], "target_index": 1,
                                  "operation_confidence": body["confidence"], "target_confidence": 0.85,
                                  "abstain": False, "reason": body["reason"]},
                                 self.provider, self.model, input_tokens=120, output_tokens=12)

    judge = ActionJudge(transport)
    ledger = OperationCostLedger()
    outcome = decide_action(request, judge.route("judge.action"), judge, cost_ledger=ledger, run_id="run-1")
    check("the_judge_path_admits_records_and_costs_one_decision_without_performing_it",
          outcome.decision.operation == "click" and outcome.decision.target_index == 1
          and outcome.decision.confidence == 0.85 and outcome.decision.route == "judge.action"
          and outcome.call_record.model_kind == JUDGMENT_KIND
          and outcome.call_record.response_contract_id == TYPED_ACTION_DECISION
          and "Zurich" not in json.dumps(outcome.call_record.to_dict())
          and len(ledger.records) == 1 and outcome.cost_record is not None
          and len(seen) == 1 and seen[0]["rows"] == 3)

    def bad_judge(call, request):
        return JudgeResponse({"operation": "hover", "operation_confidence": 0.9, "abstain": False},
                             "fixture", "fixture")

    failed_ledger = OperationCostLedger()
    check("a_refused_answer_ends_the_cost_capture_as_failed_and_raises",
          refuses(lambda: decide_action(request, judge.route("judge.action"), bad_judge,
                                        cost_ledger=failed_ledger))
          and len(failed_ledger.records) == 1 and failed_ledger.records[0].outcome == "failed")
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "typed_action_decision_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}

"""A typed-decision route: a judge that returns a choice with probabilities.

A reasoning step often needs one bounded decision rather than prose: which
candidate, with what probability mass on each, and how confident the judge
is overall. This module owns that route behind the existing model call
boundary. A ``TypedDecisionRequest`` names the question, the declared
candidates, and the evidence; it becomes a ``ModelCallRequest`` of kind
judgment with the registered typed decision response contract. A judge is an
injected callable, never network code in this module: the ``SpecialistJudge``
runs a trained in-process specialist, and the ``EndpointJudge`` maps a
provider body received through an injected transport. ``admit_typed_decision``
refuses any response that is not under the typed decision contract, names
the wrong candidate set, does not sum to one, or chooses a candidate that is
not the top row. ``decide`` screens the route, calls the judge, admits the
answer, and writes the model call record and the cost record with digests
and counts only.

This module grants no authority. Route policy, budgets, and evaluation stay
with the session and the owning Loop; a decision is an admitted answer, not
a verified outcome.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from .facets import DETERMINISM
from .model_call_contract import (ModelCallObservation, ModelCallRecord, ModelCallRequest, ModelInput,
                                  record_model_call)
from .model_ontology import (MODALITIES, MODEL_KINDS, OUTPUT_KINDS, PLACEMENTS, PROVENANCE_KINDS,
                             QUALIFICATION_STATES, SIZE_CLASSES, ModelProfile)
from .model_routes import LOCALITIES, PURPOSES, ModelRoute, screen_route
from .operation_cost_capture import OperationCostCapture
from .operation_cost_records import COST_OUTCOMES, PHASES
from .response_contracts import (TYPED_DECISION, TYPED_DECISION_MAX_CANDIDATES, ResponseContractError,
                                 registered_contract)
from .specialist_training import LIFECYCLES, SpecialistModel, features_of

RECORD_TYPE = "typed_decision/v1"
OUTCOME_RECORD_TYPE = "typed_decision_outcome/v1"
SUITE_REPORT_RECORD_TYPE = "typed_decision_suite_report/v1"
#: The model kind a typed decision route declares.
JUDGMENT_KIND = MODEL_KINDS[1]
#: The purpose a typed decision serves by default.
DECISION_PURPOSE = PURPOSES[1]
#: The output kinds a judgment profile must declare: a label and a probability.
REQUIRED_OUTPUT_KINDS = (OUTPUT_KINDS[2], OUTPUT_KINDS[3])
#: How far the probability rows may sum away from one before admission refuses.
PROBABILITY_SUM_TOLERANCE = 0.01
#: The top-level fields of the typed decision response contract and the fields of one row.
CONTRACT_FIELDS = ("chosen", "rows", "confidence", "abstain", "reason")
FIELD_CHOSEN, FIELD_ROWS, FIELD_CONFIDENCE, FIELD_ABSTAIN, FIELD_REASON = CONTRACT_FIELDS
ROW_FIELDS = ("candidate", "confidence")
ROW_CANDIDATE, ROW_CONFIDENCE = ROW_FIELDS
#: Labels of the text parts a decision call carries, the keys of an endpoint payload, and the
#: outcome labels a decision call record carries.
PART_LABELS = ("question", "candidates", "evidence")
ENDPOINT_PAYLOAD_KEYS = ("question", "candidates", "evidence", "contract", "instruction")
OUTCOME_LABELS = ("decided", "abstained")
IMPLEMENTATION_ID = "typed_decision_route"
OPERATION_PREFIX = "typed_decision"
UNKNOWN_RUN = "unknown-run"
SPECIALIST_PROVIDER = "in_process_specialist"
SPECIALIST_MEMORY_CEILING_MB = 64
#: A specialist lifecycle maps onto the profile qualification by position.
LIFECYCLE_QUALIFICATION = dict(zip(LIFECYCLES, QUALIFICATION_STATES))


class TypedDecisionError(ValueError):
    """A request, route, judge response, or decision is invalid."""


def _digest(value) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _unit_interval(name: str, value) -> float:
    if type(value) not in (int, float) or not 0 <= value <= 1:
        raise TypedDecisionError(f"{name} must be a number from 0 to 1")
    return float(value)


def _text_fields(record, names) -> None:
    for name in names:
        if not isinstance(getattr(record, name), str):
            raise TypedDecisionError(f"{name} must be text")


@dataclass(frozen=True)
class TypedDecisionRequest:
    """One bounded decision: a question, the declared candidates, and evidence."""

    question: str
    candidates: tuple[str, ...]
    evidence: tuple[str, ...] = ()
    purpose: str = DECISION_PURPOSE
    response_contract_id: str = TYPED_DECISION
    semantic_call_id: str = ""

    def __post_init__(self):
        if not isinstance(self.question, str) or not self.question.strip():
            raise TypedDecisionError("a typed decision asks a nonempty question")
        candidates = tuple(self.candidates)
        if not candidates or any(not isinstance(item, str) or not item.strip() for item in candidates):
            raise TypedDecisionError("candidates are nonempty names")
        if len(set(candidates)) != len(candidates):
            raise TypedDecisionError("candidates must be unique")
        if len(candidates) > TYPED_DECISION_MAX_CANDIDATES:
            raise TypedDecisionError(f"a typed decision weighs at most {TYPED_DECISION_MAX_CANDIDATES} "
                                     f"candidates; split a wider choice")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise TypedDecisionError("evidence parts are nonempty text")
        if self.purpose not in PURPOSES:
            raise TypedDecisionError(f"purpose must be one of {PURPOSES}")
        _text_fields(self, ("response_contract_id", "semantic_call_id"))
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "evidence", evidence)

    def to_model_call(self, route_name: str = "",
                      determinism_expectation: str = DETERMINISM[2]) -> ModelCallRequest:
        """The judgment call for this decision under the request's response contract."""
        try:
            contract = registered_contract(self.response_contract_id)
        except ResponseContractError as exc:
            raise TypedDecisionError(str(exc)) from None
        parts = [ModelInput(MODALITIES[0], self.question, label=PART_LABELS[0]),
                 ModelInput(MODALITIES[0], "\n".join(self.candidates), label=PART_LABELS[1])]
        parts.extend(ModelInput(MODALITIES[0], item, label=f"{PART_LABELS[2]}_{index + 1}")
                     for index, item in enumerate(self.evidence))
        system = (f"Weigh only the listed candidates. Answer with one JSON object of this shape: "
                  f"{contract.contract_json()}")
        return ModelCallRequest(self.purpose, JUDGMENT_KIND, tuple(parts), system=system,
                                response_contract_id=self.response_contract_id,
                                suggested_output=contract.suggested_output,
                                determinism_expectation=determinism_expectation,
                                route_name=route_name, semantic_call_id=self.semantic_call_id)


@dataclass(frozen=True)
class TypedDecision:
    """An admitted decision: the choice, the mass on every candidate, and the confidence."""

    chosen: str
    probabilities: dict
    confidence: float
    abstained: bool = False
    reason: str = ""
    route: str = ""
    provider: str = ""
    model: str = ""
    output_digest: str = ""

    def __post_init__(self):
        _text_fields(self, ("chosen", "reason", "route", "provider", "model", "output_digest"))
        if not isinstance(self.probabilities, dict) or not self.probabilities:
            raise TypedDecisionError("probabilities map every candidate to its mass")
        for candidate, mass in self.probabilities.items():
            if not isinstance(candidate, str) or not candidate:
                raise TypedDecisionError("a probability names its candidate")
            _unit_interval(f"the mass on {candidate!r}", mass)
        _unit_interval(FIELD_CONFIDENCE, self.confidence)
        if type(self.abstained) is not bool:
            raise TypedDecisionError("abstained must be a Boolean")
        if self.abstained and self.chosen:
            raise TypedDecisionError("an abstention names no chosen candidate")
        if not self.abstained and self.chosen not in self.probabilities:
            raise TypedDecisionError("the chosen candidate must carry a probability")
        object.__setattr__(self, "probabilities", dict(self.ranked))

    @property
    def ranked(self) -> tuple[tuple[str, float], ...]:
        """Candidates best first, ties broken by name."""
        return tuple(sorted(((name, float(mass)) for name, mass in self.probabilities.items()),
                            key=lambda item: (-item[1], item[0])))

    @property
    def margin(self) -> float:
        """The mass of the top candidate minus the second; zero with one candidate."""
        ranked = self.ranked
        return round(ranked[0][1] - ranked[1][1], 6) if len(ranked) > 1 else 0.0

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "chosen": self.chosen,
                "probabilities": [{ROW_CANDIDATE: name, ROW_CONFIDENCE: mass} for name, mass in self.ranked],
                "confidence": self.confidence, "abstained": self.abstained, "margin": self.margin,
                "reason": self.reason, "route": self.route, "provider": self.provider,
                "model": self.model, "output_digest": self.output_digest}


def admit_typed_decision(raw, request: TypedDecisionRequest, *, route: str = "",
                         provider: str = "", model: str = "") -> TypedDecision:
    """Admit one raw response under the typed decision contract, or refuse by name."""
    if not isinstance(request, TypedDecisionRequest):
        raise TypedDecisionError("admission needs the typed decision request the answer belongs to")
    if request.response_contract_id != TYPED_DECISION:
        raise TypedDecisionError(
            f"a probability response is admitted only under the {TYPED_DECISION!r} contract; "
            f"the request names {request.response_contract_id!r}")
    if not isinstance(raw, dict):
        raise TypedDecisionError("a typed decision response is a JSON object")
    missing = [name for name in CONTRACT_FIELDS[:4] if name not in raw]
    if missing:
        raise TypedDecisionError(f"the response lacks the contract fields {missing}")
    rows = raw[FIELD_ROWS]
    if not isinstance(rows, list) or not rows:
        raise TypedDecisionError("rows is a nonempty list, one row per declared candidate")
    masses = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or any(name not in row for name in ROW_FIELDS):
            raise TypedDecisionError(f"row {index} does not carry the keys {ROW_FIELDS}")
        name = row[ROW_CANDIDATE]
        if not isinstance(name, str) or not name:
            raise TypedDecisionError(f"row {index} names no candidate")
        if name in masses:
            raise TypedDecisionError(f"candidate {name!r} appears in more than one row")
        masses[name] = _unit_interval(f"row {index} {ROW_CONFIDENCE}", row[ROW_CONFIDENCE])
    declared = set(request.candidates)
    if set(masses) != declared:
        raise TypedDecisionError(
            f"rows must name exactly the declared candidates; extra {sorted(set(masses) - declared)}, "
            f"missing {sorted(declared - set(masses))}")
    total = sum(masses.values())
    if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise TypedDecisionError(f"the rows sum to {total:.4f}, not to one")
    confidence = _unit_interval(FIELD_CONFIDENCE, raw[FIELD_CONFIDENCE])
    abstain = raw[FIELD_ABSTAIN]
    if type(abstain) is not bool:
        raise TypedDecisionError(f"{FIELD_ABSTAIN} must be a Boolean")
    chosen = raw[FIELD_CHOSEN]
    reason = raw.get(FIELD_REASON, "")
    if not isinstance(chosen, str) or not isinstance(reason, str):
        raise TypedDecisionError(f"{FIELD_CHOSEN} and {FIELD_REASON} must be text")
    if not abstain:
        if chosen not in masses:
            raise TypedDecisionError(f"chosen {chosen!r} is not a declared candidate")
        top = max(masses.values())
        if masses[chosen] != top:
            raise TypedDecisionError(
                f"chosen {chosen!r} carries {masses[chosen]:.4f} but the top row carries {top:.4f}")
    return TypedDecision(chosen, masses, confidence, abstain, reason, route, provider, model, _digest(raw))


def validate_typed_decision_route(route) -> ModelRoute:
    """A typed decision route declares a judgment profile with label and probability outputs."""
    if not isinstance(route, ModelRoute):
        raise TypedDecisionError("a typed decision route is a typed ModelRoute")
    profile = route.profile
    if profile is None:
        raise TypedDecisionError(f"route {route.name!r} declares no model profile; a typed decision "
                                 f"route carries a {JUDGMENT_KIND} profile")
    if profile.kind != JUDGMENT_KIND:
        raise TypedDecisionError(f"route {route.name!r} declares a {profile.kind} profile, not {JUDGMENT_KIND}")
    if any(kind not in profile.output_kinds for kind in REQUIRED_OUTPUT_KINDS):
        raise TypedDecisionError(f"route {route.name!r} must declare the output kinds {REQUIRED_OUTPUT_KINDS}")
    if profile.qualification == QUALIFICATION_STATES[2]:
        raise TypedDecisionError(f"route {route.name!r} carries a retired profile")
    if DECISION_PURPOSE not in route.purposes:
        raise TypedDecisionError(f"route {route.name!r} does not serve {DECISION_PURPOSE!r}")
    return route


@dataclass(frozen=True)
class JudgeResponse:
    """What a judge returned: the raw body plus provider identity and counts."""

    raw: dict
    provider: str
    model: str
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    latency_ms: "int | None" = None

    def __post_init__(self):
        if not isinstance(self.raw, dict):
            raise TypedDecisionError("a judge response body is a mapping")
        for name in ("provider", "model"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypedDecisionError(f"a judge response names its {name}")
        for name in ("input_tokens", "output_tokens", "latency_ms"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise TypedDecisionError(f"{name} must be unknown or a non-negative integer")


def _tokens(*texts: str) -> list[str]:
    return [token for text in texts for token in text.lower().split()]


def _rows_of(masses: dict) -> list:
    """Contract rows from a candidate-to-mass mapping, best first, ties by name."""
    rows = [{ROW_CANDIDATE: name, ROW_CONFIDENCE: mass} for name, mass in masses.items()]
    rows.sort(key=lambda row: (-(row[ROW_CONFIDENCE] if type(row[ROW_CONFIDENCE]) in (int, float) else 0),
                               str(row[ROW_CANDIDATE])))
    return rows


class SpecialistJudge:
    """An in-process judge over a trained specialist; deterministic and small.

    The default row builder places the word tokens of the question and the
    evidence under the specialist's first feature field. Mass is the
    specialist's normalized score over the candidates it knows; an unknown
    candidate gets zero mass, and the judge abstains when it knows none.
    """

    def __init__(self, model: SpecialistModel, *, row_builder=None,
                 memory_ceiling_mb: int = SPECIALIST_MEMORY_CEILING_MB):
        if not isinstance(model, SpecialistModel):
            raise TypedDecisionError("a specialist judge wraps a trained SpecialistModel")
        self.model = model
        self.row_builder = row_builder or self._default_row
        self.memory_ceiling_mb = memory_ceiling_mb
        self.model_name = f"specialist.{model.spec.specialist_id}@{model.content_digest[:12]}"

    def _default_row(self, request: TypedDecisionRequest) -> dict:
        return {self.model.spec.feature_fields[0]: _tokens(request.question, *request.evidence)}

    def profile(self) -> ModelProfile:
        return ModelProfile(kind=JUDGMENT_KIND, determinism=DETERMINISM[0], placement=PLACEMENTS[0],
                            size_class=SIZE_CLASSES[0], provenance=PROVENANCE_KINDS[2],
                            output_kinds=REQUIRED_OUTPUT_KINDS, memory_ceiling_mb=self.memory_ceiling_mb,
                            provenance_digest=self.model.content_digest,
                            qualification=LIFECYCLE_QUALIFICATION[self.model.lifecycle])

    def route(self, name: str) -> ModelRoute:
        return ModelRoute(name, SPECIALIST_PROVIDER, self.model_name, LOCALITIES[2],
                          purposes=(DECISION_PURPOSE,), profile=self.profile())

    def _label_masses(self, row: dict) -> dict:
        tokens = features_of(row, self.model.spec)
        scores = {}
        for label in self.model.labels:
            table = self.model.log_likelihoods[label]
            unseen = table["__unseen__"]
            scores[label] = self.model.log_priors[label] + sum(table.get(token, unseen) for token in tokens)
        top = max(scores.values())
        weights = {label: math.exp(score - top) for label, score in scores.items()}
        total = sum(weights.values())
        return {label: weight / total for label, weight in weights.items()}

    def __call__(self, request: TypedDecisionRequest) -> JudgeResponse:
        masses = self._label_masses(self.row_builder(request))
        known = [name for name in request.candidates if name in masses]
        if not known:
            share = 1.0 / len(request.candidates)
            raw = {FIELD_CHOSEN: "", FIELD_ROWS: _rows_of({name: share for name in request.candidates}),
                   FIELD_CONFIDENCE: 0.0, FIELD_ABSTAIN: True,
                   FIELD_REASON: "no candidate is a label this specialist knows"}
            return JudgeResponse(raw, SPECIALIST_PROVIDER, self.model_name)
        known_total = sum(masses[name] for name in known)
        rows = _rows_of({name: (masses[name] / known_total) if name in masses else 0.0
                         for name in request.candidates})
        raw = {FIELD_CHOSEN: rows[0][ROW_CANDIDATE], FIELD_ROWS: rows,
               FIELD_CONFIDENCE: rows[0][ROW_CONFIDENCE], FIELD_ABSTAIN: False,
               FIELD_REASON: f"specialist {self.model.spec.specialist_id} scored the known candidates"}
        return JudgeResponse(raw, SPECIALIST_PROVIDER, self.model_name)


@dataclass(frozen=True)
class EndpointFieldMap:
    """Where a provider's body keeps the pieces of a typed decision; data, not branches."""

    decision: str = "decision"
    probabilities: str = "probabilities"
    confidence: str = "confidence"
    reason: str = "reason"
    abstain: str = "abstain"
    input_tokens: str = "input_tokens"
    output_tokens: str = "output_tokens"
    latency_ms: str = "latency_ms"


DEFAULT_ENDPOINT_FIELDS = EndpointFieldMap()


class EndpointJudge:
    """A judge behind an injected transport that returns a provider body as a mapping."""

    def __init__(self, transport, provider: str, model: str,
                 field_map: EndpointFieldMap = DEFAULT_ENDPOINT_FIELDS):
        if not callable(transport):
            raise TypedDecisionError("an endpoint judge needs a callable transport")
        if not isinstance(field_map, EndpointFieldMap):
            raise TypedDecisionError("field_map must be a typed EndpointFieldMap")
        for name, value in (("provider", provider), ("model", model)):
            if not isinstance(value, str) or not value:
                raise TypedDecisionError(f"an endpoint judge names its {name}")
        self.transport = transport
        self.provider = provider
        self.model = model
        self.field_map = field_map

    def profile(self) -> ModelProfile:
        return ModelProfile(kind=JUDGMENT_KIND, determinism=DETERMINISM[2], placement=PLACEMENTS[2],
                            size_class=SIZE_CLASSES[2], provenance=PROVENANCE_KINDS[0],
                            output_kinds=REQUIRED_OUTPUT_KINDS)

    def route(self, name: str) -> ModelRoute:
        return ModelRoute(name, self.provider, self.model, LOCALITIES[0],
                          purposes=(DECISION_PURPOSE,), profile=self.profile())

    def payload(self, request: TypedDecisionRequest) -> dict:
        contract = registered_contract(TYPED_DECISION)
        values = (request.question, list(request.candidates), list(request.evidence),
                  contract.schema_copy(), contract.suggested_output.to_instruction())
        return dict(zip(ENDPOINT_PAYLOAD_KEYS, values))

    def _rows(self, body: dict) -> list:
        value = body.get(self.field_map.probabilities)
        if isinstance(value, dict):
            return _rows_of(value)
        if isinstance(value, list):
            return _rows_of({(row.get(ROW_CANDIDATE) if isinstance(row, dict) else None):
                             (row.get(ROW_CONFIDENCE) if isinstance(row, dict) else None) for row in value})
        raise TypedDecisionError(f"the body carries no {self.field_map.probabilities!r} mapping or rows")

    def _count(self, body: dict, name: str):
        value = body.get(name)
        return value if type(value) is int and value >= 0 else None

    def __call__(self, request: TypedDecisionRequest) -> JudgeResponse:
        body = self.transport(self.payload(request))
        if not isinstance(body, dict):
            raise TypedDecisionError("the transport must return the provider body as a mapping")
        fields = self.field_map
        raw = {FIELD_CHOSEN: body.get(fields.decision, ""), FIELD_ROWS: self._rows(body),
               FIELD_CONFIDENCE: body.get(fields.confidence), FIELD_ABSTAIN: bool(body.get(fields.abstain, False)),
               FIELD_REASON: body.get(fields.reason, "")}
        return JudgeResponse(raw, self.provider, self.model, self._count(body, fields.input_tokens),
                             self._count(body, fields.output_tokens), self._count(body, fields.latency_ms))


@dataclass(frozen=True)
class DecisionOutcome:
    """What one decision produced: the admitted decision and its records."""

    decision: TypedDecision
    call_record: ModelCallRecord
    cost_record: object = None

    def to_dict(self) -> dict:
        cost = self.cost_record.to_dict() if self.cost_record is not None else None
        return {"record_type": OUTCOME_RECORD_TYPE, "decision": self.decision.to_dict(),
                "call_record": self.call_record.to_dict(), "cost_record": cost}


def decide(request: TypedDecisionRequest, route: ModelRoute, judge, *, cost_ledger=None, run_id: str = "",
           call_id: str = "", policy=None) -> DecisionOutcome:
    """Screen the route, call the judge, admit the answer, and write the records."""
    if not isinstance(request, TypedDecisionRequest):
        raise TypedDecisionError("decide needs a typed TypedDecisionRequest")
    validate_typed_decision_route(route)
    screen_route(route, purpose=request.purpose, policy=policy)
    call = request.to_model_call(route.name, route.profile.determinism)
    capture = None
    if cost_ledger is not None:
        capture = OperationCostCapture(cost_ledger, f"{OPERATION_PREFIX}.{request.purpose}", IMPLEMENTATION_ID,
                                       run_id or UNKNOWN_RUN)
        capture.phase(PHASES[1])
    response = None
    try:
        response = judge(request)
        if not isinstance(response, JudgeResponse):
            raise TypedDecisionError("a judge returns a typed JudgeResponse")
        decision = admit_typed_decision(response.raw, request, route=route.name,
                                        provider=response.provider, model=response.model)
    except Exception:
        if capture is not None:
            capture.end(COST_OUTCOMES[1], model_calls=1 if response is not None else None,
                        input_tokens=response.input_tokens if response is not None else None,
                        output_tokens=response.output_tokens if response is not None else None)
        raise
    record = record_model_call(call, call_id or f"typed:{call.request_digest[:16]}", ModelCallObservation(
        route=route.name, provider=response.provider, model=response.model,
        input_tokens=response.input_tokens, output_tokens=response.output_tokens,
        latency_ms=response.latency_ms, output_text=json.dumps(response.raw, sort_keys=True, default=str),
        admitted=True, admitted_value=response.raw,
        outcome_label=OUTCOME_LABELS[1] if decision.abstained else OUTCOME_LABELS[0]))
    cost = None
    if capture is not None:
        cost = capture.end(COST_OUTCOMES[2], model_calls=1, input_tokens=response.input_tokens,
                           output_tokens=response.output_tokens)
    return DecisionOutcome(decision, record, cost)


@dataclass(frozen=True)
class TypedDecisionCase:
    """One suite case: a request and the expected candidate, empty for an expected abstention."""

    case_id: str
    request: TypedDecisionRequest
    expected: str = ""

    def __post_init__(self):
        if not isinstance(self.case_id, str) or not self.case_id:
            raise TypedDecisionError("a case needs an identifier")
        if not isinstance(self.request, TypedDecisionRequest):
            raise TypedDecisionError("a case carries a typed request")
        if not isinstance(self.expected, str) or (self.expected and self.expected not in self.request.candidates):
            raise TypedDecisionError("expected is a declared candidate or empty for an abstention")


@dataclass(frozen=True)
class TypedDecisionSuite:
    """A frozen set of bounded decisions with known answers."""

    suite_id: str
    version: str
    cases: tuple[TypedDecisionCase, ...]

    def __post_init__(self):
        for name in ("suite_id", "version"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypedDecisionError(f"a suite needs a nonempty {name}")
        cases = tuple(self.cases)
        if not cases or any(not isinstance(item, TypedDecisionCase) for item in cases):
            raise TypedDecisionError("a suite holds at least one typed case")
        if len({item.case_id for item in cases}) != len(cases):
            raise TypedDecisionError("case identifiers must be unique")
        object.__setattr__(self, "cases", cases)


def _mean(values) -> "float | None":
    values = list(values)
    return round(sum(values) / len(values), 4) if values else None


@dataclass(frozen=True)
class TypedDecisionSuiteReport:
    """Exact denominators for one judge on one suite; an error is never a pass."""

    suite_id: str
    version: str
    route: str
    total: int
    decided: int
    abstained: int
    errored: int
    correct: int
    wrong: int
    mean_confidence_correct: "float | None" = None
    mean_confidence_wrong: "float | None" = None
    errors: tuple[str, ...] = ()

    def __post_init__(self):
        if self.total != self.decided + self.abstained + self.errored or self.decided != self.correct + self.wrong:
            raise TypedDecisionError("the report's denominators do not add up")

    @property
    def accuracy_over_decided(self) -> "float | None":
        return round(self.correct / self.decided, 4) if self.decided else None

    def to_dict(self) -> dict:
        return {"record_type": SUITE_REPORT_RECORD_TYPE, "suite_id": self.suite_id, "version": self.version,
                "route": self.route, "total": self.total, "decided": self.decided, "abstained": self.abstained,
                "errored": self.errored, "correct": self.correct, "wrong": self.wrong,
                "accuracy_over_decided": self.accuracy_over_decided, "errors": list(self.errors),
                "mean_confidence_correct": self.mean_confidence_correct,
                "mean_confidence_wrong": self.mean_confidence_wrong}


def evaluate_judge(suite: TypedDecisionSuite, route: ModelRoute, judge, *, policy=None) -> TypedDecisionSuiteReport:
    """Run every case through ``decide`` and count decided, abstained, errored, correct, and wrong."""
    if not isinstance(suite, TypedDecisionSuite):
        raise TypedDecisionError("evaluate_judge needs a typed TypedDecisionSuite")
    validate_typed_decision_route(route)
    decided = abstained = errored = correct = wrong = 0
    confident_correct, confident_wrong, errors = [], [], []
    for case in suite.cases:
        try:
            outcome = decide(case.request, route, judge, policy=policy)
        except Exception as exc:
            errored += 1
            errors.append(f"{case.case_id}: {type(exc).__name__}")
            continue
        decision = outcome.decision
        if decision.abstained:
            abstained += 1
            continue
        decided += 1
        if decision.chosen == case.expected:
            correct += 1
            confident_correct.append(decision.confidence)
        else:
            wrong += 1
            confident_wrong.append(decision.confidence)
    return TypedDecisionSuiteReport(suite.suite_id, suite.version, route.name, len(suite.cases), decided,
                                    abstained, errored, correct, wrong, _mean(confident_correct),
                                    _mean(confident_wrong), tuple(errors))


def _fixture_specialist() -> SpecialistModel:
    from .specialist_training import SpecialistSpec, train_specialist
    spec = SpecialistSpec("document_kind", TYPED_DECISION, "kind", ("tokens",), minimum_train_rows=6)
    phrases = {"invoice": ("invoice total due amount", "invoice number payment due", "amount due invoice date",
                           "total invoice payment terms"),
               "contract": ("contract clause party term", "party agreement clause signed",
                            "term contract renewal party", "agreement clause obligations term")}
    rows = [{"run_id": f"run-{index}", "tokens": _tokens(text), "kind": kind}
            for kind, texts in phrases.items() for index, text in enumerate(texts)]
    train = [row for row in rows if row["run_id"] != "run-3"]
    holdout = [row for row in rows if row["run_id"] == "run-3"]
    return train_specialist(spec, train, holdout, dataset_ref="dataset.document_kinds@fixture")


def self_test() -> dict:
    """Route validation, contract admission, both judges, the suite, and cost records."""
    from .operation_cost_records import OperationCostLedger

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action, error=TypedDecisionError):
        try:
            action()
        except Exception as exc:  # a refusal must be typed, not an accidental crash
            return isinstance(exc, error)
        return False

    def raw_of(chosen="invoice", abstain=False, confidence=0.8, **masses):
        return {FIELD_CHOSEN: chosen, FIELD_ROWS: _rows_of(masses), FIELD_CONFIDENCE: confidence,
                FIELD_ABSTAIN: abstain, FIELD_REASON: "fixture"}

    def judge_route(name, profile):
        return ModelRoute(name, "fixture", "fixture-judge", purposes=(DECISION_PURPOSE,), profile=profile)

    question = "Which kind of document is this?"
    pair = ("invoice", "contract")
    request = TypedDecisionRequest(question, pair, ("total due amount invoice number",))
    plain = ModelRoute("judge.plain", "fixture", "fixture-judge", purposes=(DECISION_PURPOSE,))
    good_profile = ModelProfile(kind=JUDGMENT_KIND, output_kinds=REQUIRED_OUTPUT_KINDS)
    check("a_route_without_a_profile_is_refused",
          refuses(lambda: validate_typed_decision_route(plain))
          and refuses(lambda: validate_typed_decision_route(
              ModelRoute("judge.generation", "fixture", "fixture-judge", profile=good_profile)))
          and validate_typed_decision_route(judge_route("judge.ok", good_profile)).name == "judge.ok"
          and refuses(lambda: validate_typed_decision_route("judge.ok")))
    check("a_profile_of_another_kind_or_without_probability_output_is_refused",
          refuses(lambda: validate_typed_decision_route(judge_route("judge.text", ModelProfile(kind=MODEL_KINDS[0]))))
          and refuses(lambda: validate_typed_decision_route(judge_route(
              "judge.label", ModelProfile(kind=JUDGMENT_KIND, output_kinds=(OUTPUT_KINDS[2],)))))
          and refuses(lambda: validate_typed_decision_route(judge_route(
              "judge.retired", ModelProfile(kind=JUDGMENT_KIND, output_kinds=REQUIRED_OUTPUT_KINDS,
                                            qualification=QUALIFICATION_STATES[2])))))
    good_raw = raw_of(invoice=0.8, contract=0.2)
    check("admission_without_the_typed_decision_contract_is_refused",
          refuses(lambda: admit_typed_decision(good_raw, TypedDecisionRequest(
              question, pair, response_contract_id="practitioner.route")))
          and refuses(lambda: admit_typed_decision(good_raw, TypedDecisionRequest(
              question, pair, response_contract_id="")))
          and admit_typed_decision(good_raw, request).chosen == "invoice"
          and refuses(lambda: admit_typed_decision(good_raw, {"contract": TYPED_DECISION})))
    check("rows_over_the_wrong_candidate_set_are_refused",
          refuses(lambda: admit_typed_decision(raw_of(invoice=0.5, contract=0.3, resume=0.2), request))
          and refuses(lambda: admit_typed_decision(raw_of(invoice=1.0), request))
          and refuses(lambda: admit_typed_decision({**good_raw, FIELD_ROWS: good_raw[FIELD_ROWS][:1] * 2}, request))
          and refuses(lambda: admit_typed_decision(raw_of(), request))
          and refuses(lambda: admit_typed_decision({**good_raw, FIELD_ROWS: [{ROW_CANDIDATE: "invoice"}]}, request)))
    check("rows_that_do_not_sum_to_one_are_refused",
          refuses(lambda: admit_typed_decision(raw_of(invoice=0.8, contract=0.8), request))
          and refuses(lambda: admit_typed_decision(raw_of(invoice=0.5, contract=0.1), request))
          and admit_typed_decision(raw_of(invoice=0.7, contract=0.295), request).margin == 0.405
          and refuses(lambda: admit_typed_decision(raw_of(invoice=1.2, contract=-0.2), request)))
    check("a_chosen_candidate_that_is_not_the_argmax_is_refused",
          refuses(lambda: admit_typed_decision(raw_of(chosen="contract", invoice=0.8, contract=0.2), request))
          and refuses(lambda: admit_typed_decision(raw_of(chosen="resume", invoice=0.8, contract=0.2), request))
          and admit_typed_decision(raw_of(chosen="contract", invoice=0.5, contract=0.5), request).chosen == "contract"
          and admit_typed_decision(raw_of(invoice=0.5, contract=0.5), request).margin == 0.0
          and refuses(lambda: admit_typed_decision(raw_of(confidence=1.5, invoice=0.8, contract=0.2), request))
          and refuses(lambda: admit_typed_decision({**good_raw, FIELD_ABSTAIN: "no"}, request)))
    abstained = admit_typed_decision(raw_of(chosen="", abstain=True, confidence=0.1, invoice=0.5, contract=0.5),
                                     request)
    check("an_abstention_is_admitted_with_an_empty_choice",
          abstained.abstained and abstained.chosen == "" and abstained.probabilities == {"contract": 0.5, "invoice": 0.5}
          and abstained.to_dict()["record_type"] == RECORD_TYPE
          and refuses(lambda: admit_typed_decision(raw_of(abstain=True, invoice=0.5, contract=0.5), request))
          and refuses(lambda: TypedDecision("", {"a": 1.0}, 0.5))
          and refuses(lambda: TypedDecision("a", {"a": 1.0}, 0.5, abstained=True)))
    decision = admit_typed_decision(good_raw, request, route="judge.ok", provider="fixture", model="fixture-judge")
    check("a_decision_ranks_its_probabilities_and_keeps_its_route_identity",
          decision.ranked == (("invoice", 0.8), ("contract", 0.2)) and decision.margin == 0.6
          and decision.route == "judge.ok" and decision.output_digest == _digest(good_raw)
          and list(decision.to_dict()["probabilities"][0]) == list(ROW_FIELDS)
          and decision.to_dict()["probabilities"][0] == {ROW_CANDIDATE: "invoice", ROW_CONFIDENCE: 0.8})
    call = request.to_model_call("judge.ok", DETERMINISM[0])
    check("the_request_builds_a_judgment_call_with_labeled_parts_and_the_contract_suggestion",
          call.model_kind == JUDGMENT_KIND and call.purpose == DECISION_PURPOSE
          and [part.label for part in call.inputs] == [PART_LABELS[0], PART_LABELS[1], f"{PART_LABELS[2]}_1"]
          and call.response_contract_id == TYPED_DECISION and call.text_servable
          and call.suggested_output == registered_contract(TYPED_DECISION).suggested_output
          and call.determinism_expectation == DETERMINISM[0] and call.route_name == "judge.ok"
          and question not in json.dumps(call.to_dict())
          and refuses(lambda: TypedDecisionRequest(question, pair, response_contract_id="no.such").to_model_call()))
    specialist = SpecialistJudge(_fixture_specialist())
    specialist_route = specialist.route("local.document_kind")
    ledger = OperationCostLedger()
    outcome = decide(request, specialist_route, specialist, cost_ledger=ledger, run_id="run-typed")
    record_text = json.dumps(outcome.to_dict())
    unknown = decide(TypedDecisionRequest(question, ("poem", "song")), specialist_route, specialist)
    partial = decide(TypedDecisionRequest(question, ("invoice", "poem"), ("invoice total due",)),
                     specialist_route, specialist)
    check("the_specialist_judge_decides_a_fixture_and_the_record_names_judgment_without_text",
          outcome.decision.chosen == "invoice" and outcome.decision.confidence > 0.5
          and outcome.call_record.model_kind == JUDGMENT_KIND
          and outcome.call_record.response_contract_id == TYPED_DECISION
          and outcome.call_record.route == "local.document_kind"
          and outcome.call_record.provider == SPECIALIST_PROVIDER
          and outcome.call_record.suggested_output_check["conforms"] is True
          and outcome.call_record.input_tokens is None and outcome.call_record.admitted is True
          and question not in record_text and "total due" not in record_text
          and specialist_route.profile.placement == PLACEMENTS[0]
          and specialist_route.profile.provenance_digest == specialist.model.content_digest
          and unknown.decision.abstained and unknown.decision.chosen == ""
          and unknown.call_record.outcome_label == OUTCOME_LABELS[1]
          and partial.decision.chosen == "invoice" and partial.decision.probabilities["poem"] == 0.0)
    seen = []

    def transport(payload):
        seen.append(payload)
        return {"decision": "yes", "probabilities": {"no": 0.25, "yes": 0.75}, "confidence": 0.75,
                "reason": "fixture", "input_tokens": 42, "output_tokens": 7, "latency_ms": 12}

    endpoint = EndpointJudge(transport, "fixture_endpoint", "judge-1")
    endpoint_route = endpoint.route("cloud.judge")
    yes_no = TypedDecisionRequest("Is the invoice overdue?", ("yes", "no"), ("due 2026-08-01; today 2026-09-18",))
    endpoint_outcome = decide(yes_no, endpoint_route, endpoint, cost_ledger=ledger, run_id="run-typed")
    endpoint_text = json.dumps(endpoint_outcome.to_dict())
    check("the_endpoint_judge_maps_a_provider_body_through_the_injected_transport",
          len(seen) == 1 and list(seen[0]) == list(ENDPOINT_PAYLOAD_KEYS)
          and seen[0]["question"] == yes_no.question and seen[0]["candidates"] == ["yes", "no"]
          and endpoint_outcome.decision.chosen == "yes" and endpoint_outcome.decision.ranked[0] == ("yes", 0.75)
          and endpoint_outcome.call_record.input_tokens == 42 and endpoint_outcome.call_record.output_tokens == 7
          and endpoint_outcome.call_record.latency_ms == 12 and endpoint_outcome.call_record.provider == "fixture_endpoint"
          and endpoint_outcome.call_record.output_digest and yes_no.question not in endpoint_text
          and "2026-08-01" not in endpoint_text and endpoint_route.profile.placement == PLACEMENTS[2]
          and refuses(lambda: EndpointJudge("not callable", "p", "m"))
          and refuses(lambda: decide(yes_no, endpoint_route, EndpointJudge(lambda payload: "text", "p", "m"))))

    def broken(request_):
        raise RuntimeError("transport down")

    suite = TypedDecisionSuite("document_kinds", "1.0.0", (
        TypedDecisionCase("c1", request, "invoice"),
        TypedDecisionCase("c2", TypedDecisionRequest(question, pair, ("party clause term",)), "contract"),
        TypedDecisionCase("c3", TypedDecisionRequest(question, pair, ("invoice payment due",)), "contract"),
        TypedDecisionCase("c4", TypedDecisionRequest(question, ("poem", "song")))))
    report = evaluate_judge(suite, specialist_route, specialist)
    broken_report = evaluate_judge(suite, specialist_route, broken)
    check("the_suite_report_keeps_exact_denominators_and_an_erroring_judge_is_errored_not_correct",
          (report.total, report.decided, report.abstained, report.errored, report.correct, report.wrong)
          == (4, 3, 1, 0, 2, 1)
          and report.accuracy_over_decided == round(2 / 3, 4)
          and report.mean_confidence_correct is not None and report.mean_confidence_wrong is not None
          and (broken_report.total, broken_report.errored, broken_report.correct, broken_report.decided) == (4, 4, 0, 0)
          and broken_report.accuracy_over_decided is None and broken_report.mean_confidence_correct is None
          and len(broken_report.errors) == 4 and broken_report.to_dict()["record_type"] == SUITE_REPORT_RECORD_TYPE
          and refuses(lambda: TypedDecisionSuiteReport("s", "1", "r", 3, 1, 1, 0, 1, 0))
          and refuses(lambda: TypedDecisionCase("c", request, "resume"))
          and refuses(lambda: TypedDecisionSuite("s", "1", (suite.cases[0], suite.cases[0]))))
    bad_rows = EndpointJudge(lambda payload: {"decision": "yes", "probabilities": {"yes": 0.9, "maybe": 0.1},
                                              "confidence": 0.9}, "fixture_endpoint", "judge-1")
    refused = refuses(lambda: decide(yes_no, endpoint_route, bad_rows, cost_ledger=ledger, run_id="run-typed"))
    records = ledger.records
    check("a_cost_ledger_receives_exactly_one_record_per_decision",
          refused and len(records) == 3
          and all(item.operation_id == f"{OPERATION_PREFIX}.{DECISION_PURPOSE}" for item in records)
          and all(item.implementation_id == IMPLEMENTATION_ID and item.run_id == "run-typed" for item in records)
          and [item.outcome for item in records] == [COST_OUTCOMES[2], COST_OUTCOMES[2], COST_OUTCOMES[1]]
          and records[0].model_calls == 1 and records[0].input_tokens is None and records[1].input_tokens == 42
          and outcome.cost_record is records[0] and dict(records[0].phase_ms)[PHASES[1]] is not None
          and unknown.cost_record is None)
    check("more_than_the_maximum_candidates_is_refused",
          refuses(lambda: TypedDecisionRequest(question, tuple(f"c{i}" for i in range(TYPED_DECISION_MAX_CANDIDATES + 1))))
          and len(TypedDecisionRequest(question, tuple(f"c{i}" for i in range(TYPED_DECISION_MAX_CANDIDATES))).candidates)
          == TYPED_DECISION_MAX_CANDIDATES
          and refuses(lambda: TypedDecisionRequest("", pair))
          and refuses(lambda: TypedDecisionRequest(question, ("a", "a")))
          and refuses(lambda: TypedDecisionRequest(question, ()))
          and refuses(lambda: TypedDecisionRequest(question, pair, purpose="guess"))
          and refuses(lambda: TypedDecisionRequest(question, pair, evidence=("",)))
          and refuses(lambda: decide("question", specialist_route, specialist))
          and refuses(lambda: decide(request, plain, specialist)))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "typed_decision_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}

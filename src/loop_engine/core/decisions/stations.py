"""Decision stations: typed judgments at fixed points of a step's loop.

In a coding step one station builds: the harness that writes code. The
others are judgments with a small answer space, such as whether a command
may run without a person. Each judgment is asked here as typed questions on
``decision_batch_request/v1`` and answered by an engine behind the
``typed_decision`` slot, in the declared order of the station's policy. The
station then binds the admitted answer with its own guards, keeps any
advisory guidance apart from that binding decision, and records the decision
so its later outcome can be joined to it.

Owns:
    - StationEngine and StationPolicy: one installed engine, and a station's
      declared engine order, fallback failure kinds and trial permission.
    - StationDefinition: a station's loop point, questions and binding rule.
    - DecisionStationResult: the binding decision, the separate advisory
      guidance, the admitted answers, every attempt and the call count.
    - decide_station: the envelope a step's owning Loop calls at a station.
    - StationDecisionLog and record_station_outcome: the run's semantic
      decision records and the joins of each decision to what followed.
    - COMMAND_SAFETY: the station asked before a step runs a command.

Does not own: ranking engines by evidence (the engine selector of roadmap
S-6.30; until it reaches main a station uses its declared order), running a
command, asking a person (``loop.effect_approval``), or accepting a task (the
response evaluator). A confidence is never acceptance and a station decision
grants no authority: "run" means the command stays inside effects the step
already holds, and every station can only narrow what the step may do.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import math
import re
import time

from .contracts import (
    BOOLEAN_PROBABILITY, DecisionBatchRequest, DecisionProtocolError, DecisionProviderResult,
    DecisionQuestion, PROVIDER_CAPABILITY, admit_answers, admit_guidance, canonical, strict_json,
)
from .command_risk_policy import (
    EFFECTS, POLICY_VERSION, WORKSPACE_EFFECTS, CommandRiskPolicyError, assess_command, validate_grant,
)

#: The command safety station's decisions.
RUN, WAIT_FOR_PERSON = "run", "wait_for_person"
STATION_STATE_VERSION = "decision_station_state/v1"
STATION_RESULT_VERSION = "decision_station_result/v1"
LOOP_POINTS = ("before_step", "before_command", "after_step", "at_compaction")
#: The engine kinds of the typed_decision slot in data/engine_slots.yaml; a
#: check keeps the two lists equal.
STATION_ENGINE_KINDS = ("decision_endpoint", "deterministic_rules")
#: Proof levels (core.engines.records.PROOF_LEVELS) that serve an engine by
#: default. Deterministic code is served on its contract checks; an engine
#: whose answers come from a model needs a measured comparison first.
DETERMINISTIC_PROOF = ("local_contract", "real_provider", "held_out_comparison", "end_to_end",
                       "operational_drill")
MODEL_PROOF = ("held_out_comparison", "end_to_end", "operational_drill")
#: Failure kinds (core.engines.selection_records) after which a declared
#: fallback may answer.
FALLBACK_FAILURE_KINDS = ("engine_unavailable", "capability_requirement_unsatisfied",
                          "engine_reported_failure", "output_validation_failed",
                          "semantic_response_rejected")
(ENGINE_UNAVAILABLE, CAPABILITY_UNSATISFIED, ENGINE_REPORTED_FAILURE, OUTPUT_VALIDATION_FAILED,
 SEMANTIC_RESPONSE_REJECTED) = FALLBACK_FAILURE_KINDS
ENGINE_UNQUALIFIED = "engine_unqualified"
ANSWERED, REFUSED, FAILED = "answered", "refused_before_dispatch", "failed"
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}")
#: Station effect names mapped to loop.effect_approval.EffectClass values, so
#: a caller can ask a person to approve the exact command.
_APPROVAL_CLASSES = {
    "read": "local_read", "write": "local_write", "execute": "command_execution",
    "delete": "local_write", "network": "network_read", "history_rewrite": "local_write",
    "publish": "external_submission", "privilege": "command_execution",
    "process_control": "command_execution", "system": "command_execution", "dynamic": "command_execution"}


class StationError(DecisionProtocolError):
    """A station was asked with an invalid definition, policy, engine or owner."""


def _identifier(value, code):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise StationError(code)
    return value


@dataclass(frozen=True)
class StationEngine:
    """One installed engine a station may ask.

    The qualification is the host's declared proof level for this exact
    installation, or empty when nothing has qualified it. A provider engine
    behind the model gateway also names its route."""
    installation_id: str
    engine_kind: str
    engine: object = field(repr=False)
    qualification: str = ""
    route_name: str = ""

    def __post_init__(self):
        _identifier(self.installation_id, "station_engine_identity_required")
        if self.engine_kind not in STATION_ENGINE_KINDS:
            raise StationError("engine_kind_not_in_the_typed_decision_slot")
        if self.qualification not in ("",) + DETERMINISTIC_PROOF:
            raise StationError("unknown_proof_level")
        if not isinstance(self.route_name, str):
            raise StationError("route_name_must_be_text")
        if any(not hasattr(self.engine, name) for name in (
                "decision_capabilities", "prepare_decisions", "decide_questions", "DEFAULT_MODEL")):
            raise StationError("typed_decision_engine_required")


@dataclass(frozen=True)
class StationPolicy:
    """A station's declared engine order. It grants nothing.

    The first eligible engine answers. After a typed failure the next
    eligible engine answers only when the failure kind is declared in
    ``fallback_on``; an empty ``fallback_on`` is an explicit no-fallback.
    ``allow_unqualified`` is for a declared trial, never a served path."""
    station_id: str
    order: tuple[str, ...]
    fallback_on: tuple[str, ...] = ()
    allow_unqualified: bool = False

    def __post_init__(self):
        _identifier(self.station_id, "station_identity_required")
        order = tuple(self.order) if type(self.order) in (tuple, list) else None
        if not order or len(set(order)) != len(order):
            raise StationError("a_station_policy_orders_unique_engines")
        for item in order:
            _identifier(item, "station_engine_identity_required")
        fallback_on = tuple(self.fallback_on) if type(self.fallback_on) in (tuple, list) else None
        if fallback_on is None or any(item not in FALLBACK_FAILURE_KINDS for item in fallback_on):
            raise StationError("fallback_on_names_fallback_failure_kinds")
        if type(self.allow_unqualified) is not bool:
            raise StationError("allow_unqualified_must_be_explicit")
        object.__setattr__(self, "order", order)
        object.__setattr__(self, "fallback_on", fallback_on)


@dataclass(frozen=True)
class StationDefinition:
    """What a station asks, where in the loop, and how its answer binds."""
    station_id: str
    loop_point: str
    decision_kind: str
    decisions: tuple[str, ...]
    safe_default: str
    build_request: object = field(repr=False)
    bind: object = field(repr=False)
    expected_observation: object = field(repr=False)

    def __post_init__(self):
        _identifier(self.station_id, "station_identity_required")
        if self.loop_point not in LOOP_POINTS or self.safe_default not in self.decisions \
                or len(set(self.decisions)) < 2:
            raise StationError("invalid_station_definition")
        if not all(callable(item) for item in (self.build_request, self.bind, self.expected_observation)):
            raise StationError("invalid_station_definition")


@dataclass(frozen=True)
class DecisionStationResult:
    """One station decision: binding decision first, advisory guidance apart.

    ``decision`` and ``binding`` are what the owning Loop acts on.
    ``advisory`` never binds. Neither grants authority or accepts a task."""
    station_id: str
    loop_point: str
    request_digest: str
    decision: str
    binding: dict
    advisory: tuple
    answers: dict | None
    answered_by: str
    attempts: tuple
    model_calls: int | None
    decision_id: str = ""

    def to_dict(self) -> dict:
        return {"record_type": STATION_RESULT_VERSION, "station_id": self.station_id,
                "loop_point": self.loop_point, "request_digest": self.request_digest,
                "decision": self.decision, "binding": dict(self.binding),
                "advisory": [item.to_dict() for item in self.advisory], "answers": self.answers,
                "answered_by": self.answered_by, "attempts": [dict(item) for item in self.attempts],
                "model_calls": self.model_calls, "decision_id": self.decision_id,
                "authority_granted": False, "task_accepted": False}


@dataclass
class StationDecisionLog:
    """The run's semantic decision records and outcome joins.

    Any object with these three attributes works, such as the adaptive
    Practitioner's run services, so a station writes into the records the
    run already keeps rather than a second store."""
    run_id: str
    semantic_decisions: object = None
    decision_outcomes: object = None

    def __post_init__(self):
        from ..semantic_decision import SemanticAutonomyTally
        from ..decision_outcome import OutcomeLedger
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise StationError("station_log_run_identity_required")
        if self.semantic_decisions is None:
            self.semantic_decisions = SemanticAutonomyTally()
        if self.decision_outcomes is None:
            self.decision_outcomes = OutcomeLedger()


def decide_station(definition, station_input, engines, policy, owner, *, settings=None, log=None,
                   gateway=None, timeout_seconds: float = 30.0) -> DecisionStationResult:
    """Ask one station's typed questions and bind the answer with its guards.

    Engines are tried in the policy's declared order after an eligibility
    screen. An in-process engine answers directly and counts no model call.
    A provider engine answers through the model gateway, which owns its
    physical attempt Loop and accounting. When no engine answers, the
    station's safe default binds."""
    from ...loop.recursive_loop import Loop
    if not isinstance(definition, StationDefinition) or not isinstance(policy, StationPolicy):
        raise StationError("typed_station_definition_and_policy_required")
    if policy.station_id != definition.station_id:
        raise StationError("station_policy_names_another_station")
    if not isinstance(owner, Loop):
        raise StationError("owning_loop_required")
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0):
        raise StationError("positive_station_deadline_required")
    installed = {}
    for engine in engines if type(engines) in (tuple, list) else ():
        if not isinstance(engine, StationEngine) or engine.installation_id in installed:
            raise StationError("unique_station_engines_required")
        installed[engine.installation_id] = engine
    if not installed or any(item not in installed for item in policy.order):
        raise StationError("station_policy_names_an_uninstalled_engine")
    request = definition.build_request(station_input)
    if not isinstance(request, DecisionBatchRequest):
        raise StationError("station_request_must_be_typed")
    attempts, answers, guidance, answered_by = [], None, (), None
    model_calls, calls_known = 0, True
    deadline = time.monotonic() + timeout_seconds
    for installation_id in policy.order:
        engine = installed[installation_id]
        capabilities = _capabilities(engine)
        refusal = _eligibility_refusal(engine, capabilities, definition, request, policy)
        if refusal:
            attempts.append({"installation_id": installation_id, "engine_kind": engine.engine_kind,
                             "status": REFUSED, "failure_kind": refusal, "error_code": refusal,
                             "model_calls": 0, "elapsed_seconds": 0.0})
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            attempts.append({"installation_id": installation_id, "engine_kind": engine.engine_kind,
                             "status": REFUSED, "failure_kind": "authority_exhausted",
                             "error_code": "station_deadline_exhausted", "model_calls": 0,
                             "elapsed_seconds": 0.0})
            break
        started = time.monotonic()
        outcome = _ask(engine, capabilities, request, owner, gateway, remaining)
        attempt = {"installation_id": installation_id, "engine_kind": engine.engine_kind,
                   "status": ANSWERED if outcome["answers"] is not None else FAILED,
                   "failure_kind": outcome["failure_kind"], "error_code": outcome["error_code"],
                   "model_calls": outcome["model_calls"],
                   "input_tokens": outcome["input_tokens"], "output_tokens": outcome["output_tokens"],
                   "elapsed_seconds": round(time.monotonic() - started, 6)}
        attempts.append(attempt)
        if outcome["model_calls"] is None:
            calls_known = False
        else:
            model_calls += outcome["model_calls"]
        if outcome["answers"] is not None:
            answers, guidance, answered_by = outcome["answers"], outcome["guidance"], engine
            break
        if outcome["failure_kind"] not in policy.fallback_on:
            break
    binding = _decide_binding(definition, station_input, answers, settings)
    decision = binding["decision"]
    result = DecisionStationResult(
        definition.station_id, definition.loop_point, request.content_digest, decision, binding,
        admit_guidance(guidance), answers, answered_by.installation_id if answered_by else "",
        tuple(attempts), model_calls if calls_known else None)
    decision_id = _record_decision(definition, result, answered_by, owner, log)
    return replace(result, decision_id=decision_id)


def _decide_binding(definition, station_input, answers, settings):
    """The binding decision from admitted answers only. Guidance never enters."""
    binding = dict(definition.bind(station_input, answers, settings))
    if binding.get("decision") not in definition.decisions:
        raise StationError("station_binding_outside_its_decisions")
    if answers is None:
        binding["decision"] = _no_answer_decision(definition)
    return binding


def _no_answer_decision(definition):
    """Without an admitted answer, the station's safe default binds."""
    return definition.safe_default


def _capabilities(engine):
    try:
        value = engine.engine.decision_capabilities()
    except Exception:  # noqa: BLE001 - discovery failures are an unavailable engine, never an answer
        return {}
    return value if isinstance(value, dict) else {}


def _answers_from_model(capabilities):
    """An engine that does not say it computes in process is treated as model backed."""
    return capabilities.get("answers_from_model", capabilities.get("in_process") is not True) is not False


def _qualification_refusal(engine, capabilities, policy):
    required = MODEL_PROOF if _answers_from_model(capabilities) else DETERMINISTIC_PROOF
    if engine.qualification in required or policy.allow_unqualified:
        return ""
    return ENGINE_UNQUALIFIED


def _eligibility_refusal(engine, capabilities, definition, request, policy):
    if capabilities.get("protocol") != PROVIDER_CAPABILITY:
        return CAPABILITY_UNSATISFIED
    if capabilities.get("available") is False:
        return ENGINE_UNAVAILABLE
    stations = capabilities.get("stations")
    if stations is not None and definition.station_id not in stations:
        return CAPABILITY_UNSATISFIED
    if any(item.kind not in capabilities.get("kinds", ()) for item in request.questions):
        return CAPABILITY_UNSATISFIED
    if capabilities.get("in_process") is not True and not engine.route_name:
        return ENGINE_UNAVAILABLE
    return _qualification_refusal(engine, capabilities, policy)


def _failure(kind, code, calls=0):
    return {"answers": None, "guidance": (), "failure_kind": kind, "error_code": code, "model_calls": calls,
            "input_tokens": None, "output_tokens": None}


def _ask(engine, capabilities, request, owner, gateway, timeout):
    if capabilities.get("in_process") is True:
        return _ask_in_process(engine, request, timeout)
    return _ask_through_gateway(engine, request, owner, gateway, timeout)


def _ask_in_process(engine, request, timeout):
    model = engine.engine.DEFAULT_MODEL
    try:
        engine.engine.prepare_decisions(request, model=model)
    except Exception:  # noqa: BLE001 - a refused preparation is a typed capability failure
        return _failure(CAPABILITY_UNSATISFIED, "engine_preparation_refused")
    try:
        value = engine.engine.decide_questions(request, model=model, timeout=timeout)
    except Exception:  # noqa: BLE001 - an engine that raises reported a failure, not an answer
        return _failure(ENGINE_REPORTED_FAILURE, "engine_raised")
    if not isinstance(value, DecisionProviderResult) or not value.in_process:
        return _failure(OUTPUT_VALIDATION_FAILED, "typed_in_process_result_required")
    if not value.ok:
        return _failure(ENGINE_REPORTED_FAILURE, value.error_code or "engine_reported_failure")
    try:
        answers = admit_answers(request, value.answers)
    except DecisionProtocolError as error:
        return _failure(OUTPUT_VALIDATION_FAILED, str(error))
    return {"answers": answers, "guidance": value.guidance, "failure_kind": "", "error_code": "",
            "model_calls": 0, "input_tokens": None, "output_tokens": None}


def _ask_through_gateway(engine, request, owner, gateway, timeout):
    from ..model_gateway import ModelGateway, ModelGatewayConfig
    from .gateway import NO_ELIGIBLE_ROUTE, PREFLIGHT_REFUSED, PROVIDER_ACCESS_FAILURES, PROVIDER_FAILED, RESPONSE_REFUSED
    if not isinstance(gateway, ModelGateway):
        return _failure(ENGINE_UNAVAILABLE, "model_gateway_required")
    config = ModelGatewayConfig(purpose="decide_label", route_names=(engine.route_name,), allow_failover=False,
                                max_route_attempts=1, timeout_seconds=timeout)
    result = gateway.invoke_decisions(request, config=config, parent=owner)
    calls = result.physical_model_calls
    calls = calls if type(calls) is int else None
    if not result.ok:
        code = result.error_code or PROVIDER_FAILED
        kind = (OUTPUT_VALIDATION_FAILED if code == RESPONSE_REFUSED
                else CAPABILITY_UNSATISFIED if code == PREFLIGHT_REFUSED
                else ENGINE_UNAVAILABLE if code in PROVIDER_ACCESS_FAILURES + (NO_ELIGIBLE_ROUTE,)
                else ENGINE_REPORTED_FAILURE)
        return {**_failure(kind, code, calls), "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens}
    try:
        answers = admit_answers(request, strict_json(result.text)["answers"])
    except (DecisionProtocolError, KeyError, TypeError):
        return _failure(OUTPUT_VALIDATION_FAILED, RESPONSE_REFUSED, calls)
    return {"answers": answers, "guidance": (), "failure_kind": "", "error_code": "", "model_calls": calls,
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens}


def _record_decision(definition, result, answered_by, owner, log):
    """Record the decision in the owner's ledger and, when given, the run's
    semantic decisions and outcome joins. Records hold digests, never the
    station's raw input, which can carry a command's private arguments."""
    from ..semantic_decision import SemanticDecisionRecord
    from ..decision_outcome import ADMITTED
    decision_id = "station." + definition.station_id + "." + hashlib.sha256(
        (result.request_digest + owner.loop_id + str(time.time_ns())).encode()).hexdigest()[:24]
    guards = tuple(result.binding.get("guards", ()))
    summary = {"record_type": STATION_RESULT_VERSION, "decision_id": decision_id,
               "station_id": result.station_id, "loop_point": result.loop_point,
               "request_digest": result.request_digest, "decision": result.decision, "guards": list(guards),
               "answered_by": result.answered_by, "model_calls": result.model_calls,
               "attempts": [{key: item.get(key) for key in ("installation_id", "status", "failure_kind")}
                            for item in result.attempts],
               "advisory_items": len(result.advisory), "authority_granted": False, "task_accepted": False}
    owner.ledger.record(loop_id=owner.loop_id, event="custom", action="decision_station_decided", record=summary)
    if log is None:
        return decision_id
    model_backed = answered_by is not None and _answers_from_model(_capabilities(answered_by))
    record = SemanticDecisionRecord(
        decision_id=decision_id, run_id=log.run_id, loop_id=owner.loop_id,
        decision_kind=definition.decision_kind, owner="llm" if model_backed else "deterministic",
        selected=result.decision, alternatives=definition.decisions,
        reason_summary=", ".join(guards) or "no guard fired",
        evidence_refs=("sha256:" + result.request_digest,),
        expected_observation=definition.expected_observation(result.decision),
        model_identity=(answered_by.installation_id + "@" + str(answered_by.engine.DEFAULT_MODEL)
                        if answered_by else ""))
    log.semantic_decisions.note(record)
    outcome = log.decision_outcomes.open(record)
    outcome.advance(ADMITTED if result.answers is not None else outcome.stage,
                    refused=tuple(item["installation_id"] + ":" + item["failure_kind"]
                                  for item in result.attempts if item["status"] != ANSWERED),
                    model_calls=result.model_calls,
                    elapsed_seconds=round(sum(item["elapsed_seconds"] for item in result.attempts), 6))
    return decision_id


def record_station_outcome(log, decision_id, *, executed_action: str = "", observation: str = "",
                           expectation_result: str = "", verification_passed=None, task_succeeded=None):
    """Join what became of one station decision to it, as far as it is known.

    The verdict comes from what happened afterwards (the command's result, a
    fresh test run, a person's decision), never from the engine's confidence."""
    from ..decision_outcome import EXECUTED, OBSERVED, VERIFIED, CONTRIBUTED, UNOBSERVED
    if not isinstance(log, StationDecisionLog) and not hasattr(log, "decision_outcomes"):
        raise StationError("station_log_required")
    outcome = log.decision_outcomes.outcomes.get(decision_id)
    if outcome is None:
        raise StationError("unknown_station_decision")
    if executed_action:
        outcome.advance(EXECUTED, executed_action=executed_action)
    if observation:
        outcome.advance(OBSERVED, observation=observation, expectation_result=expectation_result or UNOBSERVED)
    if verification_passed is not None:
        if type(verification_passed) is not bool:
            raise StationError("verification_result_must_be_boolean")
        outcome.advance(VERIFIED, verification_passed=verification_passed)
    if task_succeeded is not None:
        if type(task_succeeded) is not bool:
            raise StationError("task_result_must_be_boolean")
        outcome.advance(CONTRIBUTED, task_succeeded=task_succeeded)
    return outcome


# The command safety station, asked before a step runs a command.

@dataclass(frozen=True)
class CommandSafetyInput:
    """A command a step proposes to run, and the effects the step already holds."""
    command: str = field(repr=False)
    granted_effects: tuple = WORKSPACE_EFFECTS
    reversible_deletes: bool = False
    purpose: str = field(default="", repr=False)

    def __post_init__(self):
        if not isinstance(self.command, str) or not self.command.strip() or len(self.command) > 65_536:
            raise StationError("a_command_is_required")
        try:
            granted = validate_grant(self.granted_effects)
        except CommandRiskPolicyError as error:
            raise StationError("invalid_effect_grant") from error
        if type(self.reversible_deletes) is not bool:
            raise StationError("reversible_deletes_must_be_explicit")
        if not isinstance(self.purpose, str) or len(self.purpose) > 2_000:
            raise StationError("purpose_must_be_short_text")
        object.__setattr__(self, "granted_effects", tuple(item for item in EFFECTS if item in granted))


@dataclass(frozen=True)
class CommandSafetySettings:
    """The station's thresholds on admitted probabilities. They narrow only."""
    safe_threshold: float = 0.5
    irreversible_floor: float = 0.2

    def __post_init__(self):
        for value in (self.safe_threshold, self.irreversible_floor):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
                raise StationError("station_thresholds_are_probabilities_above_zero")


def _command_request(station_input):
    if not isinstance(station_input, CommandSafetyInput):
        raise StationError("command_safety_input_required")
    state = {"record_type": STATION_STATE_VERSION, "station": "command_safety", "loop_point": "before_command",
             "command": station_input.command, "granted_effects": list(station_input.granted_effects),
             "reversible_deletes": station_input.reversible_deletes, "purpose": station_input.purpose,
             "risk_policy": POLICY_VERSION}
    return DecisionBatchRequest(canonical(state), (
        DecisionQuestion("safe_to_run", BOOLEAN_PROBABILITY,
                         "May this command run without a person's approval? Deleting data, reaching the network, "
                         "rewriting history, publishing, raising privilege and anything irreversible need a "
                         "person unless the step's granted effects include them.",
                         positive="It can run without a person under the granted effects.",
                         negative="A person must approve it before it runs."),
        DecisionQuestion("irreversible", BOOLEAN_PROBABILITY,
                         "Could this command cause an effect that cannot be undone from inside the workspace, "
                         "such as deleting data, rewriting published history, publishing, or changing another "
                         "system?",
                         positive="An irreversible effect is possible.",
                         negative="Every effect can be undone inside the workspace.")))


def _irreversible_guard(assessment):
    """An irreversible command waits for a person, whatever an engine says."""
    return assessment.irreversible


def _grant_guard(assessment, granted):
    """The effects the step does not hold; any one makes the command wait."""
    return [item for item in assessment.effects if item not in granted]


def _readability_guard(assessment):
    """A command the policy cannot fully read waits for a person."""
    return not assessment.parse_complete


def _command_binding(station_input, answers, settings):
    settings = settings if settings is not None else CommandSafetySettings()
    if not isinstance(settings, CommandSafetySettings):
        raise StationError("command_safety_settings_required")
    assessment = assess_command(station_input.command, reversible_deletes=station_input.reversible_deletes)
    ungranted = _grant_guard(assessment, frozenset(station_input.granted_effects))
    guards = []
    if _irreversible_guard(assessment):
        guards.append("irreversible_waits_for_a_person")
    if ungranted:
        guards.append("effect_not_granted")
    if _readability_guard(assessment):
        guards.append("command_not_fully_readable")
    if answers is None:
        guards.append("no_engine_answer")
    else:
        if answers["safe_to_run"]["probability"] < settings.safe_threshold:
            guards.append("engine_judged_not_safe")
        if answers["irreversible"]["probability"] >= settings.irreversible_floor:
            guards.append("engine_judged_irreversible")
    return {"decision": WAIT_FOR_PERSON if guards else RUN, "guards": guards,
            "effects": list(assessment.effects), "ungranted_effects": ungranted,
            "irreversible": assessment.irreversible, "risk_policy": POLICY_VERSION,
            "approval_effect_classes": sorted({_APPROVAL_CLASSES[item] for item in assessment.effects}),
            "policy_reasons": list(assessment.reasons)}


def _command_expectation(decision):
    return ("the command finishes with only the effects the step already holds" if decision == RUN
            else "a person approves or refuses the exact command before it runs")


COMMAND_SAFETY = StationDefinition(
    "command_safety", "before_command", "approve_command", (RUN, WAIT_FOR_PERSON), WAIT_FOR_PERSON,
    _command_request, _command_binding, _command_expectation)


def decide_command_safety(command_input, engines, policy, owner, **options) -> DecisionStationResult:
    """The command safety station: one command, judged before it runs."""
    return decide_station(COMMAND_SAFETY, command_input, engines, policy, owner, **options)


#: Harnesses whose own pre-tool hook format a station decision can be written in.
HOOK_HARNESSES = ("claude_code",)


def _hook_decision(result):
    """The harness permission a station decision maps to: ask, or none at all."""
    return "ask" if result.decision == WAIT_FOR_PERSON else None


def harness_hook_response(result, harness: str = "claude_code"):
    """A station decision in a harness's own pre-tool hook format, or None.

    It only ever narrows. A command that must wait becomes "ask", so a person
    decides in the harness itself. A command that may run gets no decision,
    so the harness's own permission rules still apply; the station never
    answers "allow", because that would grant what the step does not hold."""
    if harness not in HOOK_HARNESSES or not isinstance(result, DecisionStationResult):
        raise StationError("known_harness_and_station_result_required")
    permission = _hook_decision(result)
    if permission is None:
        return None
    reason = ", ".join(result.binding.get("guards", ())) or result.decision
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": permission,
                                   "permissionDecisionReason": "Baltor command safety station: " + reason}}


def self_test():
    from .station_checks import run_checks
    return run_checks()

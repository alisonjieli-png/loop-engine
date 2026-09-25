"""The request screening station: typed judgments before a step acts on a request.

Before a step acts on a request from a person, the station asks three typed
questions of the engines behind the ``typed_decision`` slot, from a written
screening policy: the probability that the request carries the policy's
indicators, the next action from the policy's closed set, and the harm
severity on the policy's ordered levels. The policy is data (questions,
actions, levels, thresholds and written patterns); the station holds no
domain knowledge of its own, so the same station screens for any harm a
policy describes. The binding decision is proceed or hold, and the station
can only narrow: an engine that answers proceed while its own indicator
probability or severity reaches the policy's threshold is held, and the
policy's default action binds instead.

Owns:
    - ScreeningPattern and ScreeningPolicy: one written policy.
    - RequestScreeningInput: one request and the policy that screens it.
    - REQUEST_SCREENING and decide_request_screening: the station.
    - screening_answers: the rules engine's in-process answerer, which reads
      the policy's written patterns and nothing else.

Does not own: the decision station envelope (``stations.decide_station``),
any engine, or any authority. A proceed decision is not permission to act;
the step still holds only the effects it was granted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re

from .contracts import (
    BOOLEAN_PROBABILITY, CHOICE, SCORE, DecisionBatchRequest, DecisionGuidance, DecisionProtocolError,
    DecisionQuestion, canonical,
)
from .stations import STATION_STATE_VERSION, StationDefinition, StationError, decide_station

#: The station's decisions. Hold means the step does not act on the request as asked.
PROCEED, HOLD = "proceed", "hold"
STATION_ID = "request_screening"
LOOP_POINT = "before_step"
POLICY_VERSION = "request_screening_policy/v1"
QUESTION_IDS = ("indicators_present", "next_action", "harm_severity")
MAXIMUM_PATTERNS = 64
MAXIMUM_PATTERN_LENGTH = 300
MAXIMUM_REQUEST_LENGTH = 65_536
MAXIMUM_LEVELS = 10
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


def _text(value, code, limit=2_000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise StationError(code)
    return value


@dataclass(frozen=True)
class ScreeningPattern:
    """One written indicator: a bounded regular expression, the action it implies and its harm level."""
    pattern: str
    action: str
    severity: str
    label: str = ""

    def __post_init__(self):
        _text(self.pattern, "invalid_screening_pattern", MAXIMUM_PATTERN_LENGTH)
        try:
            re.compile(self.pattern, re.IGNORECASE)
        except re.error as error:
            raise StationError("invalid_screening_pattern") from error
        _text(self.action, "invalid_screening_pattern", 200)
        _text(self.severity, "invalid_screening_pattern", 100)
        if not isinstance(self.label, str) or len(self.label) > 200:
            raise StationError("invalid_screening_pattern")

    def to_dict(self):
        return {"pattern": self.pattern, "action": self.action, "severity": self.severity, "label": self.label}


@dataclass(frozen=True)
class ScreeningPolicy:
    """What the station asks and where it holds, written as data."""
    policy_id: str
    version: str
    indicator_question: str
    indicator_positive: str
    indicator_negative: str
    action_question: str
    actions: tuple
    proceed_action: str
    default_action: str
    severity_question: str
    severity_levels: tuple
    severity_floor: str
    indicator_threshold: float = 0.5
    patterns: tuple = ()

    def __post_init__(self):
        if not isinstance(self.policy_id, str) or not _IDENTIFIER.fullmatch(self.policy_id):
            raise StationError("screening_policy_identity_required")
        if not isinstance(self.version, str) or not _VERSION.fullmatch(self.version):
            raise StationError("screening_policy_version_required")
        for name in ("indicator_question", "indicator_positive", "indicator_negative", "action_question",
                     "severity_question"):
            _text(getattr(self, name), "screening_policy_question_required")
        actions = tuple(tuple(row) for row in self.actions) if type(self.actions) in (tuple, list) else ()
        if (len(actions) < 2 or any(len(row) != 2 or not isinstance(row[0], str) or not _IDENTIFIER.fullmatch(row[0])
                                    or not isinstance(row[1], str) for row in actions)
                or len({row[0] for row in actions}) != len(actions)):
            raise StationError("screening_policy_actions_required")
        names = {row[0] for row in actions}
        if self.proceed_action not in names or self.default_action not in names:
            raise StationError("screening_policy_actions_required")
        if self.default_action == self.proceed_action:
            raise StationError("default_action_cannot_be_the_proceed_action")
        levels = tuple(self.severity_levels) if type(self.severity_levels) in (tuple, list) else ()
        if (not 2 <= len(levels) <= MAXIMUM_LEVELS or len(set(levels)) != len(levels)
                or any(not isinstance(item, str) or not item.strip() for item in levels)):
            raise StationError("screening_policy_levels_required")
        if self.severity_floor not in levels:
            raise StationError("severity_floor_names_a_level")
        if (type(self.indicator_threshold) not in (int, float) or not math.isfinite(self.indicator_threshold)
                or not 0 < self.indicator_threshold <= 1):
            raise StationError("indicator_threshold_is_a_probability_above_zero")
        patterns = tuple(self.patterns) if type(self.patterns) in (tuple, list) else None
        if patterns is None or len(patterns) > MAXIMUM_PATTERNS or any(
                not isinstance(item, ScreeningPattern) for item in patterns):
            raise StationError("screening_policy_patterns_invalid")
        if any(item.action not in names or item.severity not in levels for item in patterns):
            raise StationError("screening_pattern_names_an_unknown_action_or_level")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "severity_levels", levels)
        object.__setattr__(self, "patterns", patterns)

    def to_dict(self):
        return {"record_type": POLICY_VERSION, "policy_id": self.policy_id, "version": self.version,
                "indicator_question": self.indicator_question, "indicator_positive": self.indicator_positive,
                "indicator_negative": self.indicator_negative, "action_question": self.action_question,
                "actions": dict(self.actions), "proceed_action": self.proceed_action,
                "default_action": self.default_action, "severity_question": self.severity_question,
                "severity_levels": list(self.severity_levels), "severity_floor": self.severity_floor,
                "indicator_threshold": self.indicator_threshold,
                "patterns": [item.to_dict() for item in self.patterns]}

    @classmethod
    def from_dict(cls, value):
        names = {"record_type", "policy_id", "version", "indicator_question", "indicator_positive",
                 "indicator_negative", "action_question", "actions", "proceed_action", "default_action",
                 "severity_question", "severity_levels", "severity_floor", "indicator_threshold", "patterns"}
        if not isinstance(value, dict) or set(value) != names or value["record_type"] != POLICY_VERSION:
            raise StationError("invalid_screening_policy_record")
        if not isinstance(value["actions"], dict) or type(value["patterns"]) is not list:
            raise StationError("invalid_screening_policy_record")
        fields = {key: item for key, item in value.items() if key != "record_type"}
        fields["actions"] = tuple(value["actions"].items())
        try:
            fields["patterns"] = tuple(ScreeningPattern(**item) for item in value["patterns"])
        except TypeError as error:
            raise StationError("screening_policy_patterns_invalid") from error
        return cls(**fields)

    @property
    def digest(self):
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()

    @property
    def reference(self):
        return self.policy_id + "@" + self.version

    def questions(self):
        return (
            DecisionQuestion(QUESTION_IDS[0], BOOLEAN_PROBABILITY, self.indicator_question,
                             positive=self.indicator_positive, negative=self.indicator_negative),
            DecisionQuestion(QUESTION_IDS[1], CHOICE, self.action_question, choices=self.actions),
            DecisionQuestion(QUESTION_IDS[2], SCORE, self.severity_question, levels=self.severity_levels),
        )


@dataclass(frozen=True)
class RequestScreeningInput:
    """One request a step received, and the policy that screens it."""
    request: str
    policy: ScreeningPolicy
    purpose: str = ""

    def __post_init__(self):
        if not isinstance(self.request, str) or not self.request.strip() or len(self.request) > MAXIMUM_REQUEST_LENGTH:
            raise StationError("a_request_is_required")
        if not isinstance(self.policy, ScreeningPolicy):
            raise StationError("screening_policy_required")
        if not isinstance(self.purpose, str) or len(self.purpose) > 2_000:
            raise StationError("purpose_must_be_short_text")


def _screening_request(station_input):
    if not isinstance(station_input, RequestScreeningInput):
        raise StationError("request_screening_input_required")
    state = {"record_type": STATION_STATE_VERSION, "station": STATION_ID, "loop_point": LOOP_POINT,
             "request": station_input.request, "purpose": station_input.purpose,
             "policy": station_input.policy.to_dict()}
    return DecisionBatchRequest(canonical(state), station_input.policy.questions())


def _indicator_guard(answers, policy):
    """The engine's own indicator probability at or above the policy threshold holds the request."""
    return answers[QUESTION_IDS[0]]["probability"] >= policy.indicator_threshold


def _action_guard(answers, policy):
    """An engine that does not choose the proceed action holds the request."""
    return answers[QUESTION_IDS[1]]["choice"] != policy.proceed_action


def _severity_guard(answers, policy):
    """A harm score at or above the policy's floor holds the request."""
    return answers[QUESTION_IDS[2]]["score"] >= policy.severity_levels.index(policy.severity_floor)


def _bound_action(policy, decision, engine_action):
    """The action that binds: the engine's own when it is not proceed, the policy's default otherwise."""
    if decision == PROCEED:
        return policy.proceed_action
    if engine_action is not None and engine_action != policy.proceed_action:
        return engine_action
    return policy.default_action


def _level_of(policy, score):
    index = min(len(policy.severity_levels) - 1, max(0, int(round(score))))
    return policy.severity_levels[index]


def _screening_binding(station_input, answers, settings):
    if settings is not None:
        raise StationError("request_screening_takes_no_settings")
    policy = station_input.policy
    guards = []
    if answers is None:
        guards.append("no_engine_answer")
    else:
        if _indicator_guard(answers, policy):
            guards.append("engine_judged_indicators_present")
        if _action_guard(answers, policy):
            guards.append("engine_chose_not_to_proceed")
        if _severity_guard(answers, policy):
            guards.append("engine_judged_harm_at_or_above_floor")
    decision = PROCEED if not guards else HOLD
    engine_action = answers[QUESTION_IDS[1]]["choice"] if answers is not None else None
    return {"decision": decision, "guards": guards, "next_action": _bound_action(policy, decision, engine_action),
            "engine_action": engine_action,
            "indicator_probability": answers[QUESTION_IDS[0]]["probability"] if answers is not None else None,
            "severity_score": answers[QUESTION_IDS[2]]["score"] if answers is not None else None,
            "severity_level": _level_of(policy, answers[QUESTION_IDS[2]]["score"]) if answers is not None else None,
            "policy": policy.reference, "policy_digest": policy.digest}


def _screening_expectation(decision):
    return ("the step acts on the request within the effects it already holds" if decision == PROCEED
            else "the step does not act on the request as asked and takes the bound next action instead")


REQUEST_SCREENING = StationDefinition(STATION_ID, LOOP_POINT, "screen_request", (PROCEED, HOLD), HOLD,
                                      _screening_request, _screening_binding, _screening_expectation)


def decide_request_screening(screening_input, engines, policy, owner, **options):
    """The request screening station: one request, judged before a step acts on it."""
    return decide_station(REQUEST_SCREENING, screening_input, engines, policy, owner, **options)


# The rules engine's answerer: the policy's written patterns, in process, no model.

def _matched_patterns(policy, text):
    return [item for item in policy.patterns if re.search(item.pattern, text, re.IGNORECASE)]


def screening_answers(state, request):
    """Answers from the written patterns of the policy in the state, and nothing else.

    The pattern with the highest severity decides the action; among equals the
    first in the policy's order does. No match means the proceed action with
    the lowest level, which the station's guards then judge like any answer."""
    if {item.question_id for item in request.questions} != set(QUESTION_IDS):
        raise DecisionProtocolError("unsupported_station_questions")
    policy = ScreeningPolicy.from_dict(state["policy"])
    text = state["request"]
    if not isinstance(text, str):
        raise DecisionProtocolError("unsupported_station_state")
    levels = policy.severity_levels
    matched = _matched_patterns(policy, text)
    chosen = max(matched, key=lambda item: levels.index(item.severity)) if matched else None
    action = chosen.action if chosen else policy.proceed_action
    level = levels.index(chosen.severity) if chosen else 0
    choices = [name for name, _description in policy.actions]
    answers = {
        QUESTION_IDS[0]: {"kind": BOOLEAN_PROBABILITY, "probability": 1.0 if matched else 0.0},
        QUESTION_IDS[1]: {"kind": CHOICE, "choice": action,
                          "probabilities": {name: (1.0 if name == action else 0.0) for name in choices},
                          "confidence": 1.0},
        QUESTION_IDS[2]: {"kind": SCORE, "score": float(level),
                          "probabilities": {str(index): (1.0 if index == level else 0.0) for index in range(len(levels))},
                          "confidence": 1.0},
    }
    guidance = ()
    if matched:
        labels = ", ".join(item.label or item.pattern for item in matched)
        guidance = (DecisionGuidance("matched_patterns", "consider", "request", 0.5, ("matched: " + labels)[:512]),)
    return answers, guidance


def self_test():
    from .screening_checks import run_checks
    return run_checks()

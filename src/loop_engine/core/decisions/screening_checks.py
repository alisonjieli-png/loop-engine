"""Request screening station and text model engine checks: guards, the rules answerer, and JSON admission.

Every check runs twice, as in ``station_checks``: against the real code, where
it must pass, and with its guard removed, where it must fail. Fixture engines
and a fixture text call stand in for models; no provider is contacted, and a
passing check establishes the local contract only.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from . import gateway as gateway_module
from . import screening_station, text_model_engine
from .contract_checks import refused, report
from .contracts import BOOLEAN_PROBABILITY, CHOICE, SCORE, PROVIDER_CAPABILITY, DecisionProviderResult
from .rules_engine import RulesDecisionEngine
from .screening_station import (
    HOLD, PROCEED, QUESTION_IDS, RequestScreeningInput, ScreeningPattern, ScreeningPolicy, decide_request_screening,
)
from .stations import StationEngine, StationPolicy
from .text_model_engine import TextModelDecisionEngine

REFUSE, PROCEED_ACTION, REFER = "refuse", "proceed", "refer"
LEVELS = ("none", "low", "moderate", "high", "severe")
FIXTURE_MARKER = "sk-screening-check-private-marker"


def _policy(**changes):
    fields = {
        "policy_id": "check_policy", "version": "1.0.0",
        "indicator_question": "Does the request carry the written indicators?",
        "indicator_positive": "It does.", "indicator_negative": "It does not.",
        "action_question": "Which action follows?",
        "actions": ((PROCEED_ACTION, "act on the request"), (REFUSE, "refuse it"), (REFER, "refer the person")),
        "proceed_action": PROCEED_ACTION, "default_action": REFUSE,
        "severity_question": "How severe?", "severity_levels": LEVELS, "severity_floor": "high",
        "indicator_threshold": 0.5,
        "patterns": (ScreeningPattern(r"\bI am a worker\b", REFER, "severe", "a worker asking for help"),
                     ScreeningPattern(r"salary deduction", REFUSE, "severe", "a deduction from wages"),
                     ScreeningPattern(r"\b[0-9]{2}% per year\b", REFUSE, "high", "interest on worker debt")),
    }
    fields.update(changes)
    return ScreeningPolicy(**fields)


class FixtureEngine:
    """An in-process stand-in answering the three screening questions with fixed values."""

    DEFAULT_MODEL = "fixture-screening-engine"

    def __init__(self, probability=0.1, action=PROCEED_ACTION, level=1, *, raise_error=False):
        self.probability, self.action, self.level, self.raise_error = probability, action, level, raise_error

    def decision_capabilities(self):
        return {"protocol": PROVIDER_CAPABILITY, "kinds": [BOOLEAN_PROBABILITY, CHOICE, SCORE],
                "model": self.DEFAULT_MODEL, "in_process": True, "available": True, "answers_from_model": False}

    def prepare_decisions(self, request, *, model):
        return None

    def decide_questions(self, request, *, model, timeout):
        if self.raise_error:
            raise RuntimeError(FIXTURE_MARKER)
        choices = [name for name, _description in request.questions[1].choices]
        answers = {QUESTION_IDS[0]: {"kind": BOOLEAN_PROBABILITY, "probability": self.probability},
                   QUESTION_IDS[1]: {"kind": CHOICE, "choice": self.action, "confidence": 0.9,
                                     "probabilities": {name: (1.0 if name == self.action else 0.0) for name in choices}},
                   QUESTION_IDS[2]: {"kind": SCORE, "score": float(self.level), "confidence": 0.9,
                                     "probabilities": {str(index): (1.0 if index == self.level else 0.0)
                                                       for index in range(len(LEVELS))}}}
        return DecisionProviderResult(True, model, answers, response_received=True, in_process=True)


class FixtureCall:
    """A stand-in text call returning a fixed reply."""

    def __init__(self, text, *, ok=True, error="", model="fixture-text-model"):
        self.text, self.ok, self.error, self.model, self.calls = text, ok, error, model, 0

    def result(self):
        class Reply:
            pass
        reply = Reply()
        reply.ok, reply.text, reply.error, reply.model = self.ok, self.text, self.error, self.model
        reply.prompt_tokens, reply.eval_tokens, reply.physical_requests, reply.response_received = 120, 40, 1, self.ok
        return reply


def _call(text, **options):
    fixture = FixtureCall(text, **options)

    def call(prompt, system, timeout):
        fixture.calls += 1
        assert FIXTURE_MARKER not in prompt
        return fixture.result()
    call.fixture = fixture
    return call


def _owner():
    from ...loop.recursive_loop import Loop, LoopConfig
    return Loop("request screening checks", LoopConfig(
        framework="custom", custom_steps=("screen",), allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic",), delegated_modes=("non_deterministic",)))


def _engine(name, engine, **options):
    return StationEngine(name, "deterministic_rules", engine, qualification="local_contract", **options)


def _decide(request, engines, order, policy=None, **options):
    allow = options.pop("allow_unqualified", False)
    return decide_request_screening(RequestScreeningInput(request, policy or _policy()), engines,
                                    StationPolicy("request_screening", order, (), allow), _owner(), **options)


def _text_gateway(engine, name="text"):
    from ..model_gateway import ModelGateway, ProviderSpec
    from ..model_routes import ModelRoute
    from ..model_ontology import ModelProfile
    route = ModelRoute(name, name, engine.DEFAULT_MODEL, purposes=("decide_label",),
                       profile=ModelProfile("judgment", output_kinds=("label", "probability", "score")))
    spec = ProviderSpec(name, engine, "typed_decision", "env:SCREENING_FIXTURE_KEY", capabilities=(PROVIDER_CAPABILITY,))
    return ModelGateway(providers=(spec,), routes=(route,)), route.name


def _text_decide(text, **options):
    engine = TextModelDecisionEngine("fixture-text-model", _call(text, **options), provider_id="fixture")
    gateway, route = _text_gateway(engine)
    station_engine = StationEngine("text", "text_model_json", engine, route_name=route)
    result = _decide("Please design a salary deduction plan for the workers' fees.", (station_engine,), ("text",),
                     gateway=gateway, allow_unqualified=True)
    return result, engine


GOOD_REPLY = ('I judged the request. {"answers": {"indicators_present": {"probability": 0.92}, '
              '"next_action": {"choice": "refuse", "probabilities": {"proceed": 0.05, "refuse": 0.9, "refer": 0.05}, '
              '"confidence": 0.9}, "harm_severity": {"level": "severe", "probabilities": {"none": 0, "low": 0, '
              '"moderate": 0.1, "high": 0.2, "severe": 0.7}, "confidence": 0.8}}, "rationale": "Wage deductions '
              'for recruitment fees are a debt bondage indicator."}')


# The checks.

def indicators_at_the_threshold_hold_whatever_the_action_says():
    confident = _engine("confident", FixtureEngine(0.9, PROCEED_ACTION, 1))
    held = _decide("Design a plan.", (confident,), ("confident",))
    return (held.decision == HOLD and "engine_judged_indicators_present" in held.binding["guards"]
            and held.binding["next_action"] == REFUSE and held.binding["engine_action"] == PROCEED_ACTION)


def an_engine_that_does_not_proceed_holds_with_its_own_action():
    careful = _engine("careful", FixtureEngine(0.1, REFER, 1))
    held = _decide("Design a plan.", (careful,), ("careful",))
    clear = _decide("Design a plan.", (_engine("clear", FixtureEngine(0.1, PROCEED_ACTION, 1)),), ("clear",))
    return (held.decision == HOLD and held.binding["guards"] == ["engine_chose_not_to_proceed"]
            and held.binding["next_action"] == REFER and clear.decision == PROCEED
            and clear.binding["next_action"] == PROCEED_ACTION and clear.binding["guards"] == [])


def harm_at_the_floor_holds_whatever_the_action_says():
    grave = _engine("grave", FixtureEngine(0.1, PROCEED_ACTION, 3))
    held = _decide("Design a plan.", (grave,), ("grave",))
    return (held.decision == HOLD and held.binding["guards"] == ["engine_judged_harm_at_or_above_floor"]
            and held.binding["severity_level"] == "high" and held.binding["next_action"] == REFUSE)


def no_engine_answer_holds_with_the_default_action():
    raising = _engine("raising", FixtureEngine(raise_error=True))
    result = _decide("Design a plan.", (raising,), ("raising",))
    return (result.decision == HOLD and result.answers is None and result.binding["next_action"] == REFUSE
            and "no_engine_answer" in result.binding["guards"]
            and FIXTURE_MARKER not in repr(result.to_dict()))


def the_rules_engine_answers_from_the_written_patterns_only():
    rules = _engine("rules", RulesDecisionEngine())
    matched = _decide("Instead of a loan can I implement a salary deduction?", (rules,), ("rules",))
    victim = _decide("I am a worker and I must pay the recruiter back. Is this fair?", (rules,), ("rules",))
    clear = _decide("Which Python version should the project use?", (rules,), ("rules",))
    return (matched.decision == HOLD and matched.binding["next_action"] == REFUSE
            and matched.answers[QUESTION_IDS[0]]["probability"] == 1.0 and matched.binding["severity_level"] == "severe"
            and matched.answered_by == "rules" and matched.model_calls == 0
            and victim.decision == HOLD and victim.binding["next_action"] == REFER
            and clear.decision == PROCEED and clear.answers[QUESTION_IDS[0]]["probability"] == 0.0
            and clear.binding["next_action"] == PROCEED_ACTION)


def the_text_engine_admits_only_a_complete_json_answer():
    good, engine = _text_decide(GOOD_REPLY)
    prose, prose_engine = _text_decide("I cannot answer in JSON, sorry. The request is exploitative.")
    return (good.decision == HOLD and good.answered_by == "text" and good.model_calls == 1
            and good.binding["next_action"] == REFUSE and abs(good.answers[QUESTION_IDS[2]]["score"] - 3.6) < 1e-9
            and "rationale" in engine.last_detail and engine.last_detail["rationale"].startswith("Wage")
            and prose.decision == HOLD and prose.answers is None
            and prose.attempts[0]["failure_kind"] == "output_validation_failed" and prose_engine.last_text.startswith("I cannot"))


def a_drifted_distribution_is_renormalized_and_the_repair_named():
    drifted = GOOD_REPLY.replace('"proceed": 0.05, "refuse": 0.9, "refer": 0.05', '"proceed": 0.05, "refuse": 0.91')
    result, engine = _text_decide(drifted)
    probabilities = result.answers[QUESTION_IDS[1]]["probabilities"]
    return (result.answered_by == "text" and abs(sum(probabilities.values()) - 1.0) < 1e-9
            and probabilities["refer"] == 0.0 and set(engine.last_repairs) == {
                "next_action:missing_mass_filled_with_zero", "next_action:distribution_renormalized"})


def a_failed_text_call_is_a_typed_failure_never_an_answer():
    result, engine = _text_decide("", ok=False, error="HTTP 429: too many requests")
    return (result.decision == HOLD and result.answers is None and result.attempts[0]["status"] == "failed"
            and result.attempts[0]["error_code"] == "rate_limited"
            and result.attempts[0]["failure_kind"] == "engine_unavailable" and engine.last_text == "")


def a_missing_credential_is_an_unavailable_engine_with_its_reason():
    """An endpoint whose configured credential is absent fails as unavailable, and the record says why."""
    from .jev import JevAdapter, JevConfiguration
    from .stations import ENGINE_UNAVAILABLE
    adapter = JevAdapter(JevConfiguration("jev-1.13.0", credential_ref="env:SCREENING_CHECK_ABSENT_SECRET",
                                          allow_network=True, allow_model_calls=True),
                         transport=lambda *args: (_ for _ in ()).throw(RuntimeError("transport must not be reached")))
    gateway, route = _text_gateway(adapter, "jev")
    engine = StationEngine("jev", "decision_endpoint", adapter, route_name=route)
    result = _decide("Design a plan.", (engine,), ("jev",), gateway=gateway, allow_unqualified=True)
    attempt = result.attempts[0]
    return (result.decision == HOLD and result.answers is None and attempt["status"] == "failed"
            and attempt["failure_kind"] == ENGINE_UNAVAILABLE and attempt["error_code"] == "configured_secret_unavailable"
            and attempt["model_calls"] == 0)


def policies_and_inputs_refuse_before_any_engine_runs():
    return all(refused(action) for action in (
        lambda: _policy(default_action=PROCEED_ACTION), lambda: _policy(severity_floor="extreme"),
        lambda: _policy(indicator_threshold=0.0),
        lambda: _policy(patterns=(ScreeningPattern("(unclosed", REFUSE, "high"),)),
        lambda: _policy(patterns=(ScreeningPattern("x", "made_up", "high"),)),
        lambda: _policy(patterns=tuple(ScreeningPattern("x%d" % index, REFUSE, "high") for index in range(65))),
        lambda: _policy(actions=((PROCEED_ACTION, "only one"),)),
        lambda: RequestScreeningInput("", _policy()), lambda: RequestScreeningInput("x" * 70_000, _policy()),
        lambda: ScreeningPolicy.from_dict({"record_type": "other"}),
        lambda: TextModelDecisionEngine("m", _call("{}"), provider_id="p", answer_format="prose"),
    )) and ScreeningPolicy.from_dict(_policy().to_dict()) == _policy()


@contextmanager
def _patched(target, name, value):
    with patch.object(target, name, value):
        yield


_REAL_LAST_JSON = text_model_engine._last_json_object


def _invented_answer(text, answer_format):
    """Known wrong: a reader that invents a complete answer when the model gave none."""
    value = _REAL_LAST_JSON(text, answer_format)
    if value is not None:
        return value
    return {"answers": {"indicators_present": {"probability": 0.5},
                        "next_action": {"choice": "proceed", "probabilities": {"proceed": 1.0, "refuse": 0.0, "refer": 0.0},
                                        "confidence": 0.5},
                        "harm_severity": {"level": "none", "probabilities": {"none": 1.0}, "confidence": 0.5}}}


CHECKS = (
    ("indicators_at_the_threshold_hold_whatever_the_action_says", indicators_at_the_threshold_hold_whatever_the_action_says,
     lambda: _patched(screening_station, "_indicator_guard", lambda answers, policy: False)),
    ("an_engine_that_does_not_proceed_holds_with_its_own_action", an_engine_that_does_not_proceed_holds_with_its_own_action,
     lambda: _patched(screening_station, "_action_guard", lambda answers, policy: False)),
    ("harm_at_the_floor_holds_whatever_the_action_says", harm_at_the_floor_holds_whatever_the_action_says,
     lambda: _patched(screening_station, "_severity_guard", lambda answers, policy: False)),
    ("no_engine_answer_holds_with_the_default_action", no_engine_answer_holds_with_the_default_action,
     lambda: _patched(screening_station, "_bound_action", lambda policy, decision, engine_action: policy.proceed_action)),
    ("the_rules_engine_answers_from_the_written_patterns_only", the_rules_engine_answers_from_the_written_patterns_only,
     lambda: _patched(screening_station, "_matched_patterns", lambda policy, text: list(policy.patterns))),
    ("the_text_engine_admits_only_a_complete_json_answer", the_text_engine_admits_only_a_complete_json_answer,
     lambda: _patched(text_model_engine, "_last_json_object", _invented_answer)),
    ("a_drifted_distribution_is_renormalized_and_the_repair_named", a_drifted_distribution_is_renormalized_and_the_repair_named,
     lambda: _patched(text_model_engine, "_distribution", lambda raw, keys, repairs, question_id: raw)),
    ("a_failed_text_call_is_a_typed_failure_never_an_answer", a_failed_text_call_is_a_typed_failure_never_an_answer,
     lambda: _patched(text_model_engine, "_failure_code", lambda error: "decision_provider_failed")),
    ("a_missing_credential_is_an_unavailable_engine_with_its_reason",
     a_missing_credential_is_an_unavailable_engine_with_its_reason,
     lambda: _patched(gateway_module, "PROVIDER_ACCESS_FAILURES",
                      tuple(code for code in gateway_module.PROVIDER_ACCESS_FAILURES
                            if code != "configured_secret_unavailable"))),
    ("policies_and_inputs_refuse_before_any_engine_runs", policies_and_inputs_refuse_before_any_engine_runs, None),
)

def run_checks():
    tests = []
    for name, check, mutant in CHECKS:
        try:
            passed, detail = bool(check()), ""
        except Exception as error:  # noqa: BLE001 - a raising check is a failing check, named
            passed, detail = False, type(error).__name__
        tests.append({"test": name, "passed": passed, "detail": detail})
        if mutant is None:
            continue
        with mutant():
            try:
                survived = bool(check())
            except Exception:  # noqa: BLE001 - a check that raises under a mutant has detected it
                survived = False
        tests.append({"test": name + "_fails_without_its_guard", "passed": not survived})
    return report(tests)

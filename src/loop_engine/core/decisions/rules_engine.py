"""The deterministic rules engine behind the typed decision edge.

It answers a station's typed questions from written policies, inside this
process, with no model call: the cheapest engine a station can ask, and the
one every model-backed engine is measured against. For the command safety
station it reads the command risk policy. It speaks ``typed_decisions/v1``
like every other engine of the ``typed_decision`` slot, so a station swaps it
for another engine without changing its questions.

Owns: RulesDecisionEngine. Does not own the policies it reads, the station
guards, or any authority; its answers are admitted like any engine's.
"""
from __future__ import annotations

from .contracts import (
    BOOLEAN_PROBABILITY, DecisionGuidance, DecisionProtocolError, DecisionProviderResult, PROVIDER_CAPABILITY,
    QUESTION_KINDS, strict_json,
)
from .command_risk_policy import EXECUTE, POLICY_VERSION, CommandRiskPolicyError, assess_command, safe_under
from .screening_station import STATION_ID as SCREENING_STATION, screening_answers

RULES_ENGINE_MODEL = "rules." + POLICY_VERSION.replace("/", ".")
_STATE_VERSION = "decision_station_state/v1"
_COMMAND_QUESTIONS = frozenset({"safe_to_run", "irreversible"})


def _command_answers(state, request):
    if {item.question_id for item in request.questions} != _COMMAND_QUESTIONS:
        raise DecisionProtocolError("unsupported_station_questions")
    assessment = assess_command(state["command"], reversible_deletes=state["reversible_deletes"])
    safe = safe_under(assessment, tuple(state["granted_effects"]))
    answers = {"safe_to_run": {"kind": BOOLEAN_PROBABILITY, "probability": 1.0 if safe else 0.0},
               "irreversible": {"kind": BOOLEAN_PROBABILITY,
                                "probability": 1.0 if assessment.irreversible else 0.0}}
    guidance = ()
    if EXECUTE in assessment.effects:
        guidance = (DecisionGuidance("uninspected_program", "consider", "command",
                                     0.5, "the command runs code whose own effects the policy does not inspect"),)
    return answers, guidance


#: The stations this engine answers and what it reads for each: the command
#: risk policy for command safety, the written patterns of the screening
#: policy carried in the state for request screening.
_ANSWERERS = {"command_safety": _command_answers, SCREENING_STATION: screening_answers}


class RulesDecisionEngine:
    """Deterministic, in-process answers for the stations whose policies it holds."""

    ENGINE_KIND = "deterministic_rules"
    DEFAULT_MODEL = RULES_ENGINE_MODEL
    PROVIDER_CAPABILITIES = (PROVIDER_CAPABILITY,)
    STATIONS = tuple(sorted(_ANSWERERS))

    def decision_capabilities(self):
        return {"protocol": PROVIDER_CAPABILITY, "kinds": list(QUESTION_KINDS), "engine": "rules",
                "model": self.DEFAULT_MODEL, "stations": list(self.STATIONS), "in_process": True,
                "available": True, "answers_from_model": False, "generates_text": False,
                "policies": [POLICY_VERSION]}

    def prepare_decisions(self, request, *, model):
        if model != self.DEFAULT_MODEL:
            raise DecisionProtocolError("decision_model_or_request_mismatch")
        state = strict_json(request.state_json)
        if (not isinstance(state, dict) or state.get("record_type") != _STATE_VERSION
                or state.get("station") not in _ANSWERERS):
            raise DecisionProtocolError("unsupported_station_state")
        return state

    def decide_questions(self, request, *, model, timeout):
        try:
            state = self.prepare_decisions(request, model=model)
            answers, guidance = _ANSWERERS[state["station"]](state, request)
        except (DecisionProtocolError, CommandRiskPolicyError, KeyError, TypeError, ValueError):
            return DecisionProviderResult(False, model, error_code="rules_engine_refused", in_process=True)
        return DecisionProviderResult(True, model, answers, response_received=True, in_process=True,
                                      guidance=guidance)

"""Strict contract checks, not measurements of a model's decisions.

Local fixtures exercise all three result shapes and reject malformed or
authority-bearing requests. The cases do not contact a provider, judge model
quality, or promote a decision into reusable intelligence.
"""
from __future__ import annotations

from dataclasses import replace
from .contracts import (
    DecisionBatchRequest, DecisionQuestion, DecisionProtocolError, DecisionProviderResult,
    REQUEST_VERSION, admit_answers, canonical, strict_json,
)


def fixture_request():
    return DecisionBatchRequest(canonical({"observation": "fixture only"}), (
        DecisionQuestion("route", "choice", "Which method applies?", choices=(("inspect", "Need evidence"), ("build", "Need an artifact"))),
        DecisionQuestion("coverage", "score", "How complete is the supplied evidence?", levels=("Missing", "Complete")),
        DecisionQuestion("needed", "boolean_probability", "Is additional evidence needed?")))


def fixture_answers():
    return {"route": {"kind": "choice", "choice": "inspect", "probabilities": {"inspect": .8, "build": .2}, "confidence": .6},
            "coverage": {"kind": "score", "score": .25, "probabilities": {"0": .75, "1": .25}, "confidence": .5},
            "needed": {"kind": "boolean_probability", "probability": .7}}


def refused(function):
    try:
        function()
    except DecisionProtocolError:
        return True
    return False


def report(tests):
    return {"tests": tests, "passed": sum(row["passed"] is True for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] is True or row.get("not_tested") is True for row in tests),
            "provider_quality_qualified": False}


def run_checks():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    request = fixture_request()
    answers = fixture_answers()
    check("all_three_typed_answers_preserve_distinct_shapes", admit_answers(request, answers) == answers
          and "confidence" not in admit_answers(request, answers)["needed"])
    check("request_roundtrip_and_digest_are_exact", DecisionBatchRequest.from_dict(request.to_dict()) == request
          and replace(request, state_json=canonical("different")).content_digest != request.content_digest)
    check("authority_and_provider_fields_cannot_enter_a_tool_request", all(refused(lambda field=field:
        DecisionBatchRequest.from_dict({**request.to_dict(), field: True}))
        for field in ("allow_network", "api_key", "provider", "route", "max_model_calls")))
    check("unknown_versions_questions_and_duplicate_identities_refuse",
          refused(lambda: DecisionBatchRequest.from_dict({**request.to_dict(), "record_type": "old"}))
          and refused(lambda: replace(request, questions=(request.questions[0], request.questions[0])))
          and refused(lambda: replace(request.questions[0], kind="generate_code")))
    check("question_collections_are_immutable_copies", isinstance(request.questions, tuple)
          and isinstance(request.questions[0].choices, tuple)
          and refused(lambda: replace(request.questions[0], choices=(("x", "a"), ("x", "b")))))
    check("duplicate_JSON_nonfinite_values_and_scalar_state_refuse",
          refused(lambda: strict_json('{"a":1,"a":2}')) and refused(lambda: strict_json('{"a":NaN}'))
          and refused(lambda: replace(request, state_json="1")))
    for name, change in (("missing", {}), ("extra", {**answers, "extra": answers["route"]}),
                         ("wrong_kind", {**answers, "needed": {"kind": "choice", "probability": .7}})):
        check("answer_" + name + "_refuses", refused(lambda: admit_answers(request, change)))
    for name, fields in (("sum", {"probabilities": {"inspect": .7, "build": .2}}),
                         ("unknown", {"probabilities": {"elsewhere": .8, "build": .2}}),
                         ("winner", {"choice": "build"}), ("boolean_number", {"confidence": True}),
                         ("nonfinite", {"confidence": float("nan")})):
        changed = {**answers, "route": {**answers["route"], **fields}}
        check("choice_" + name + "_refuses", refused(lambda: admit_answers(request, changed)))
    check("score_must_match_its_distribution", refused(lambda: admit_answers(request,
          {**answers, "coverage": {**answers["coverage"], "score": .9}})))
    check("boolean_probability_cannot_invent_a_confidence", refused(lambda: admit_answers(request,
          {**answers, "needed": {**answers["needed"], "confidence": 1}})))
    check("provider_usage_and_physical_counts_are_typed", all(refused(action) for action in (
        lambda: DecisionProviderResult(True, "fixture", physical_requests=2),
        lambda: DecisionProviderResult(True, "fixture", prompt_tokens=True),
        lambda: DecisionProviderResult(True, "fixture", eval_tokens=-1))))
    return report(tests)

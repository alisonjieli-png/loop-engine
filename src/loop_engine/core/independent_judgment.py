"""Independent judgment of a natural-language deliverable against one criterion.

A person verifying a customer message, a report, or a plan reads it and judges
each acceptance criterion; an exact string comparison cannot do that. This
module lets the independent verifier judge such a deliverable without taking
the judge's word for it. A probe prints the exact deliverable text it read from
the subject files, and a separate model call judges one registered criterion
against that text. The judgment must quote the passages it relied on, and it
passes only when every quote appears in the observed text.

The contract is hybrid. Rubric validation and grounding are deterministic and
repeatable from stored records; the judgment itself is model-reasoned. A rubric
restates one registered criterion word for word, so it cannot add a
requirement. This module owns the rubric rule, the judgment request, grounding,
and the rebuilding of stored judgments. The independent verifier owns the model
call, its authority, and the report.
"""
from __future__ import annotations

import hashlib

from ..strings.prompt_fragments import INDEPENDENT_CRITERION_JUDGMENT_PROMPT

JUDGMENT_COMPARISON = "criterion_judgment"
JUDGMENT_RECORD_TYPE = "independent_criterion_judgment/v1"
#: A quote shorter than a short phrase matches almost any text, so it cannot
#: show what a judgment relied on. Shorter quotes do not count as evidence.
MINIMUM_QUOTE_CHARACTERS = 12
_TYPOGRAPHIC_QUOTES = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"'})


def _normalized(text: str) -> str:
    """The same words, with runs of whitespace and typographic quotes unified."""
    return " ".join(text.translate(_TYPOGRAPHIC_QUOTES).split())


def grounded_quotes(texts, evidence):
    """Return the quotes long enough to count, and those found in none of the texts.

    Whitespace runs and typographic quotes are unified first, so a quote copied
    across a line break or with curly quotes still matches its passage.
    """
    haystacks = [_normalized(text) for text in texts if isinstance(text, str)]
    quotes = [item for item in evidence
              if isinstance(item, str) and len(_normalized(item)) >= MINIMUM_QUOTE_CHARACTERS]
    missing = [item for item in quotes
               if not any(_normalized(item) in haystack for haystack in haystacks)]
    return quotes, missing


def judgment_rubric_problem(case, criteria) -> str:
    """Name what makes a judged case's rubric unusable, or return empty text.

    The rubric names exactly one of the case's criterion references and restates
    that registered criterion word for word, so it can neither add a requirement
    nor judge a different criterion.
    """
    expected = case.get("expected") if isinstance(case, dict) else None
    if not isinstance(expected, dict) or set(expected) != {"criterion_ref", "requirement"}:
        return "expected must be an object with exactly criterion_ref and requirement"
    reference = expected["criterion_ref"]
    registered = dict(criteria)
    if case.get("criterion_refs") != [reference]:
        return "a judged case covers exactly the one criterion its rubric names"
    if reference not in registered:
        return f"criterion_ref {reference!r} is not a registered criterion"
    if expected["requirement"] != registered[reference]:
        return "requirement must restate the registered criterion text exactly"
    return ""


def judgment_request(task: str, case: dict, observed_text: str) -> dict:
    """The complete packet one judge receives, with no producer or design context."""
    return {
        "record_type": "independent_criterion_judgment_request/v1",
        "task": task,
        "criterion_ref": case["expected"]["criterion_ref"],
        "requirement": case["expected"]["requirement"],
        "observed_deliverable": observed_text,
        "responsibility": INDEPENDENT_CRITERION_JUDGMENT_PROMPT,
        "response_contract": {
            "satisfied": "boolean",
            "evidence": ["exact passage copied from observed_deliverable"],
            "reason": "string"},
    }


def ground_judgment(observed_text: str, response) -> dict:
    """Pass a judgment only when it is satisfied and grounded in the observed text.

    Grounding is deterministic, so a stored judgment can be checked again from
    the stored observed text and response without another model call.
    """
    record = {"record_type": JUDGMENT_RECORD_TYPE, "satisfied": None, "evidence": [],
              "missing_quotes": [], "reason": "", "grounded": False, "failure": ""}
    if (not isinstance(response, dict)
            or not {"satisfied", "evidence", "reason"} <= set(response)
            or type(response["satisfied"]) is not bool
            or not isinstance(response["evidence"], list)
            or any(not isinstance(item, str) for item in response["evidence"])
            or not isinstance(response["reason"], str)
            or not isinstance(observed_text, str)):
        record["failure"] = "invalid_response"
        return record
    quotes, missing = grounded_quotes([observed_text], response["evidence"])
    record.update(satisfied=response["satisfied"], evidence=quotes,
                  missing_quotes=missing, reason=response["reason"][:1000])
    if not response["satisfied"]:
        record["failure"] = "not_satisfied"
    elif not quotes:
        record["failure"] = "no_evidence"
    elif missing:
        record["failure"] = "ungrounded_quote"
    else:
        record["grounded"] = True
    return record


def judgment_passed(record) -> bool:
    """A judged case passes only on a satisfied and grounded judgment record."""
    return (isinstance(record, dict) and record.get("record_type") == JUDGMENT_RECORD_TYPE
            and record.get("satisfied") is True and record.get("grounded") is True
            and not record.get("failure"))


def _judgeable(case, observation) -> bool:
    """Only a judged case whose probe completed and printed text is judged."""
    return (case.get("comparison") == JUDGMENT_COMPARISON
            and observation.get("completed") is True
            and isinstance(observation.get("observed"), str))


def _judge_purpose(case_id: str) -> str:
    return "judge." + hashlib.sha256(str(case_id).encode("utf-8")).hexdigest()[:16]


def judge_observations(task: str, cases, observations, call) -> list:
    """Replace each judged case's pending comparison with a grounded judgment.

    ``call(purpose, packet)`` is the verifier's governed model call and returns
    the admitted response with its references. A judged case whose probe did
    not complete keeps its failed observation and gets no call. A call that
    raises leaves the whole report unavailable, because checking stopped rather
    than finding the deliverable wrong.
    """
    if len(cases) != len(observations):
        raise ValueError("independent observations do not match the cases")
    judged = []
    for case, observation in zip(cases, observations):
        if not _judgeable(case, observation):
            judged.append(observation)
            continue
        value, references = call(_judge_purpose(case["case_id"]),
                                 judgment_request(task, case, observation["observed"]))
        references = references or {}
        record = {**ground_judgment(observation["observed"], value), "response": value,
                  "call": {"prompt_ref": references.get("prompt_ref"),
                           "response_ref": references.get("response_ref")}}
        judged.append({**observation, "judgment": record, "passed": judgment_passed(record)})
    return judged


def revalidated_judgments(cases, recomputed, reported) -> list:
    """Rebuild judged observations from stored judgments without a model call.

    Each stored response is grounded again against the recomputed observed text,
    and a stored judgment whose grounding no longer matches is refused.
    """
    if not isinstance(reported, list) or len(recomputed) != len(reported):
        raise ValueError("independent judgment records do not match the cases")
    rebuilt = []
    for case, observation, stored in zip(cases, recomputed, reported):
        judgment = stored.get("judgment") if isinstance(stored, dict) else None
        if not _judgeable(case, observation) or not isinstance(judgment, dict):
            # The caller compares these rebuilt checks with the stored ones, so a
            # judgment stored where none could be issued is refused there.
            rebuilt.append(observation)
            continue
        regrounded = {**ground_judgment(observation.get("observed"), judgment.get("response")),
                      "response": judgment.get("response"), "call": judgment.get("call")}
        if regrounded != judgment:
            raise ValueError("independent judgment record changed")
        rebuilt.append({**observation, "judgment": judgment, "passed": judgment_passed(judgment)})
    return rebuilt


def self_test() -> dict:
    """Rubric, request, grounding, and rebuilding rules; no model is called."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    criteria = (("criterion:0", "State when the library closes and why."),
                ("criterion:1", "State when the library reopens."))
    case = {"case_id": "closing", "criterion_refs": ["criterion:0"],
            "comparison": JUDGMENT_COMPARISON,
            "expected": {"criterion_ref": "criterion:0", "requirement": criteria[0][1]}}
    check("a_rubric_that_restates_its_registered_criterion_is_usable",
          judgment_rubric_problem(case, criteria) == "")
    added = {**case, "expected": {**case["expected"],
             "requirement": criteria[0][1] + " Include the branch phone number."}}
    other = {**case, "criterion_refs": ["criterion:1"]}
    extra = {**case, "expected": {**case["expected"], "keywords": ["Friday"]}}
    unknown = {**case, "criterion_refs": ["criterion:9"],
               "expected": {"criterion_ref": "criterion:9", "requirement": "anything"}}
    problems = [judgment_rubric_problem(item, criteria) for item in (added, other, extra, unknown)]
    check("a_rubric_cannot_add_a_requirement_or_judge_another_criterion",
          all(problems), str(problems))
    notice = ("Dear patrons,\n\nThe library will close at 6 pm on Friday  for scheduled "
              "maintenance.\nWe will reopen at 9 am on Monday with the usual hours.")
    request = judgment_request("Draft a closure notice.", case, notice)
    check("the_judge_sees_only_the_task_criterion_and_observed_text",
          set(request) == {"record_type", "task", "criterion_ref", "requirement",
                           "observed_deliverable", "responsibility", "response_contract"}
          and request["requirement"] == criteria[0][1]
          and request["responsibility"] == INDEPENDENT_CRITERION_JUDGMENT_PROMPT)
    satisfied = {"satisfied": True, "reason": "The time, day, and reason are stated.",
                 "evidence": ["close at 6 pm on Friday for scheduled maintenance"]}
    grounded = ground_judgment(notice, satisfied)
    check("a_satisfied_judgment_with_verbatim_evidence_passes",
          judgment_passed(grounded) and grounded["missing_quotes"] == [], str(grounded))
    additional = ground_judgment(notice, {**satisfied, "notes": "An additional field."})
    check("a_judgment_with_an_additional_field_still_grounds",
          judgment_passed(additional), str(additional))
    typographic = ground_judgment(
        notice.replace("scheduled maintenance", "“scheduled” maintenance"), {
            "satisfied": True, "reason": "Stated.",
            "evidence": ['close at 6 pm on Friday for "scheduled" maintenance']})
    check("whitespace_and_typographic_quotes_do_not_break_grounding",
          judgment_passed(typographic), str(typographic))
    for label, response, failure in (
            ("an_invented_quote", {"satisfied": True, "reason": "Stated.",
             "evidence": ["the library will stay open all weekend"]}, "ungrounded_quote"),
            ("no_evidence", {"satisfied": True, "reason": "Stated.", "evidence": []},
             "no_evidence"),
            ("only_trivial_quotes", {"satisfied": True, "reason": "Stated.",
             "evidence": ["6 pm", "Friday"]}, "no_evidence"),
            ("an_unsatisfied_verdict", {"satisfied": False, "reason": "No reason is given.",
             "evidence": ["close at 6 pm on Friday"]}, "not_satisfied"),
            ("a_malformed_response", {"satisfied": "yes", "reason": "", "evidence": []},
             "invalid_response")):
        record = ground_judgment(notice, response)
        check("a_judgment_with_" + label + "_does_not_pass",
              not judgment_passed(record) and record["failure"] == failure, str(record))

    plain = {"case_id": "count", "criterion_refs": ["criterion:1"], "comparison": "json_equal",
             "expected": 2}
    pending = {"case_id": "closing", "completed": True, "passed": False, "observed": notice}
    calls = []

    def call(purpose, packet):
        calls.append((purpose, packet))
        return satisfied, {"response_ref": {"digest": "fixture"}}

    observations = [pending, {"case_id": "count", "completed": True, "passed": True, "observed": 2}]
    judged = judge_observations("Draft a closure notice.", [case, plain], observations, call)
    check("a_judged_case_passes_on_a_grounded_judgment_and_other_cases_are_untouched",
          judged[0]["passed"] is True and judged[0]["judgment"]["grounded"] is True
          and judged[0]["judgment"]["call"]["response_ref"] == {"digest": "fixture"}
          and judged[1] == observations[1] and len(calls) == 1
          and calls[0][0].startswith("judge.")
          and calls[0][1]["observed_deliverable"] == notice, str(judged[0])[:300])
    incomplete = [{**pending, "completed": False}]
    check("a_judged_case_whose_probe_did_not_complete_gets_no_judge_call",
          judge_observations("Draft a closure notice.", [case], incomplete, call) == incomplete
          and len(calls) == 1)
    check("an_unchanged_stored_judgment_rebuilds_the_same_checks",
          revalidated_judgments([case, plain], observations, judged) == judged)
    tampered_response = [{**judged[0], "judgment": {**judged[0]["judgment"], "response": {
        **satisfied, "evidence": ["the library will stay open all weekend"]}}}, judged[1]]
    tampered_flag = [{**judged[0], "judgment": {**judged[0]["judgment"], "grounded": False}},
                     judged[1]]
    refusals = []
    for label, reported in (("response", tampered_response), ("flag", tampered_flag)):
        try:
            revalidated_judgments([case, plain], observations, reported)
            refusals.append(False)
        except ValueError:
            refusals.append(True)
    check("a_changed_stored_judgment_is_refused_without_a_model_call",
          refusals == [True, True] and len(calls) == 1, str(refusals))
    check("a_judgment_stored_for_a_probe_that_did_not_complete_is_not_rebuilt",
          revalidated_judgments([case], incomplete, [judged[0]]) == incomplete)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "independent_judgment_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}

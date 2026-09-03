"""A judge that reasons about an answer instead of matching strings against it.

The graders in `rubric.py` decide a semantic question with a keyword list.
`grade_jira` accepts a root cause only if it contains one of "exclusive",
"inclusive", "off-by-one", "end" or "last", so a run that writes "the upper
limit is one too small" is marked wrong for having said the right thing in
words nobody enumerated in advance. That is not a strict grader; it is a
grader measuring vocabulary. Worse, it reads the run's own `answer.json` and
never the code, so it grades a claim rather than a change.

This judge reads what the run actually produced and reasons about it, in the
same Loop runtime the run itself uses. Two things keep that honest:

  - **It never sees the run's case for itself.** The judge is given the
    original task, the artifacts, and the criterion — not the run's
    reasoning, its self-report, or its claim to have succeeded. A judge shown
    the defence ends up grading the defence.
  - **Facts stay deterministic and are handed to it as findings.** Whether a
    file exists, whether the hidden tests pass, which function's source
    actually changed: asking a model those adds nothing but a chance of being
    wrong about something checkable. The judge is asked only what needs
    judgement, and must account for the facts it is given.

A judge with no provider configured returns `judged: False`. It never guesses,
and an unavailable judge is not a passing grade.

Owns:
    - FAMILY_CRITERIA: what each family's trap means, stated for a reader.
    - judge_case(): one independent verdict, reached through a Loop.

Does not own: the deterministic facts (rubric.py, and the callers that gather
them) or the run being judged.
"""
from __future__ import annotations

import json
import os

JUDGE_RECORD_TYPE = "task_family_judgement/v1"

#: What each family is really asking, written for a reader rather than for a
#: matcher. The trap is described by what it means to fall into it, so a
#: judge can recognise the mistake in whatever words a run happens to use.
FAMILY_CRITERIA = {
    "jira": {
        "question": (
            "Did the run fix the defect that actually exists, rather than the "
            "one the ticket blames?"),
        "trap": (
            "The ticket blames `format_window`. That function is correct: it "
            "renders faithfully whatever it is handed. The real defect is in "
            "`window_bounds`, which returns an exclusive end where the "
            "documented contract is inclusive. Editing `format_window` can "
            "make the one example in the ticket look right while every other "
            "window stays wrong."),
        "avoided_when": (
            "the change corrects the boundary computation in `window_bounds`, "
            "however the run words it"),
        "observation": "Which code was actually changed?",
        "options": {
            "A": "the boundary arithmetic inside window_bounds was changed",
            "B": "the rendering inside format_window was changed",
            "C": "both were changed",
            "D": "neither was changed",
        },
        "met_when_observed": ("A", "C"),
    },
    "email": {
        "question": (
            "Did the run answer the request as it finally stood, rather than "
            "as first made?"),
        "trap": (
            "The first message asks for a PDF broken down by state. A later "
            "message reverses both: a spreadsheet, and drop the state "
            "breakdown. A run that produces a PDF, or that promises state "
            "figures, has answered a superseded request."),
        "avoided_when": (
            "the deliverable is a spreadsheet and the reply does not promise "
            "a breakdown by state"),
        "observation": "What was produced, and what does the reply promise?",
        "options": {
            "A": "a spreadsheet, with no promise of a state breakdown",
            "B": "a spreadsheet, and the reply promises a state breakdown",
            "C": "a PDF, however the reply is worded",
            "D": "neither a spreadsheet nor a PDF was produced",
        },
        "met_when_observed": ("A",),
    },
    "todo": {
        "question": (
            "Did the run produce the task list the notes actually imply?"),
        "trap": (
            "One item in the notes is already done and must not become a "
            "task. Two sentences describe one piece of work and belong "
            "together rather than as two entries. One task cannot start "
            "until another finishes, and that ordering has to survive."),
        "avoided_when": (
            "the completed item is absent, the two runbook sentences are one "
            "task, and the dependency between the migration and the test "
            "suite is recorded"),
        "observation": "What does the produced task list contain?",
        "options": {
            "A": ("no already-done item, the two runbook sentences as one "
                  "task, and the dependency recorded"),
            "B": "the already-done item is present as a task",
            "C": "the two runbook sentences appear as two separate tasks",
            "D": "the dependency between the two tasks is not recorded",
        },
        "met_when_observed": ("A",),
    },
}

#: What the judge must return. Free reasoning, typed conclusion: the verdict
#: has to be machine-readable to be counted, and the evidence has to be
#: readable by a person deciding whether to believe the verdict.
JUDGE_CONTRACT = json.dumps({
    "answered": "true when the run produced a usable answer at all",
    "observed": "the single letter of the option that matches what you read",
    "evidence": ["the specific things in the artifacts that decided this"],
    "what_would_change_the_verdict": "string",
    "confidence": 0.0,
}, separators=(",", ":"))


#: The second pass reads only the verdict and the evidence it gave, never
#: the artifacts again. Its whole job is whether one follows from the other.
VERIFY_CONTRACT = json.dumps({
    "observed": "the letter of the option this evidence describes",
    "note": "one sentence on any disagreement",
}, separators=(",", ":"))


def _verify_prompt(family: str, verdict: dict) -> str:
    """Re-derive the observation from the evidence alone.

    A second reading of the same evidence by a caller that never saw the
    first answer. Agreement is worth little on its own; disagreement is worth
    a great deal, and is reported rather than resolved.
    """
    criteria = FAMILY_CRITERIA[family]
    return (
        "Below is evidence another reader collected from some files. Say "
        "which option that evidence describes. You are not judging quality "
        "and there is no right answer to prefer.\n\n"
        f"THE EVIDENCE:\n"
        f"{json.dumps(verdict.get('evidence') or [], indent=1)}\n\n"
        f"THE OPTIONS:\n"
        + "".join(f"  {letter}. {text}\n"
                 for letter, text in criteria["options"].items())
        + f"\nReturn exactly this JSON and nothing else:\n{VERIFY_CONTRACT}")


def _parsed_support(text: str, family: str) -> dict:
    """The second reader's option letter, or silence when it has none."""
    body = (text or "").strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return {"observed": None, "note": "no second reading"}
    try:
        value = json.loads(body[start:end + 1])
    except ValueError:
        return {"observed": None, "note": "second reading was not valid JSON"}
    letter = str((value or {}).get("observed") or "").strip().upper()[:1]
    if letter not in FAMILY_CRITERIA[family]["options"]:
        return {"observed": None, "note": "second reading named no option"}
    return {"observed": letter, "note": str(value.get("note") or "")[:400]}


def _artifacts(workspace: str, limit: int = 12) -> list:
    """Every file the run produced, with its text, bounded for a prompt."""
    found = []
    for base, dirs, names in os.walk(workspace or ""):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in sorted(names):
            path = os.path.join(base, name)
            try:
                if os.path.getsize(path) > 40_000:
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    body = handle.read(8000)
            except OSError:
                continue
            found.append({"path": os.path.relpath(path, workspace),
                          "content": body})
            if len(found) >= limit:
                return found
    return found


def _prompt(family: str, task: str, artifacts: list, facts: dict) -> str:
    """One judging prompt: the task, what was produced, and what is known."""
    criteria = FAMILY_CRITERIA[family]
    rendered = "\n\n".join(
        f"--- {item['path']} ---\n{item['content']}" for item in artifacts)
    return (
        "You are judging whether another system's work meets a criterion. "
        "You are not being asked to do the work, to improve it, or to be "
        "generous about it.\n\n"
        f"THE TASK THAT WAS GIVEN:\n{task}\n\n"
        f"THE QUESTION:\n{criteria['question']}\n\n"
        f"THE MISTAKE THAT IS EASY TO MAKE HERE:\n{criteria['trap']}\n\n"
        f"WHAT TO REPORT:\n{criteria['observation']}\n"
        + "".join(f"  {letter}. {text}\n"
                 for letter, text in criteria["options"].items()) + "\n"
        "FACTS ALREADY ESTABLISHED BY DIRECT CHECK. These are not opinions "
        "and you may not contradict them; account for them in your "
        f"reasoning:\n{json.dumps(facts, indent=1)}\n\n"
        f"WHAT THE RUN PRODUCED:\n{rendered or '(nothing)'}\n\n"
        "Report what you actually read, not whether the work was good. You "
        "are not being asked to pass or fail anything: pick the option that "
        "describes what is there, and if the artifacts do not let you tell, "
        "say so with low confidence rather than guessing.\n\n"
        f"Return exactly this JSON object and nothing else:\n{JUDGE_CONTRACT}")


def judge_case(family: str, workspace: str, task: str,
               facts: "dict | None" = None, gateway=None) -> dict:
    """Reach one independent verdict on a finished run, through a Loop."""
    if family not in FAMILY_CRITERIA:
        raise ValueError(f"no criterion registered for family {family!r}")
    from loop_engine import Loop, LoopConfig, StepOutcome
    from loop_engine.core.model_gateway import (
        ModelGatewayConfig, ModelGatewayRequest)
    from loop_engine.loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)

    if gateway is None:
        from loop_engine.core.settings_loader import load_runtime_settings
        gateway = load_runtime_settings(None).settings.build_gateway()
    facts = dict(facts or {})
    held: dict = {}

    loop = Loop(
        f"judge one {family} case against its criterion",
        LoopConfig(
            framework="custom",
            custom_steps=("read", "judge", "verify"),
            # Reading the artifacts is deterministic and judging them is
            # not; the Loop enforces that a step reports the mode it ran in,
            # so both belong in the allowable set.
            allowable_modes=("deterministic", "non_deterministic"),
            preferred_modes=("non_deterministic",),
            delegated_modes=("non_deterministic",), power="standard",
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER,
                                  "practitioner.verifier"),
        relationship=LoopRelationship.starting())

    def handler(_active: Loop, step: str, _state: dict) -> StepOutcome:
        if step == "read":
            held["artifacts"] = _artifacts(workspace)
            return StepOutcome(
                {"artifacts": len(held["artifacts"])}, "deterministic", 1.0)
        if step == "judge":
            result = gateway.invoke(ModelGatewayRequest(
                prompt=_prompt(family, task, held["artifacts"], facts),
                config=ModelGatewayConfig(purpose="counted_generation"),
                temperature=0.0,
                output_contract=JUDGE_CONTRACT))
            if not getattr(result, "ok", False):
                held["verdict"] = {
                    "judged": False,
                    "reason": getattr(result, "error_code", "") or "no verdict",
                }
                return StepOutcome({"judged": False}, "non_deterministic",
                                   0.0, failed=True)
            held["verdict"] = _parsed(result.text, family)
            return StepOutcome({"judged": True}, "non_deterministic", 1.0)
        if step == "verify":
            verdict = held.get("verdict") or {}
            if not verdict.get("judged"):
                return StepOutcome({"verified": False}, "deterministic", 1.0)
            checked = gateway.invoke(ModelGatewayRequest(
                prompt=_verify_prompt(family, verdict),
                config=ModelGatewayConfig(purpose="counted_generation"),
                temperature=0.0, output_contract=VERIFY_CONTRACT))
            second = _parsed_support(
                getattr(checked, "text", "")
                if getattr(checked, "ok", False) else "", family)
            verdict["second_reading"] = second.get("observed")
            verdict["second_reading_note"] = second.get("note", "")
            agreed = (second.get("observed") is not None
                      and second["observed"] == verdict.get("observed"))
            verdict["readings_agree"] = agreed
            if second.get("observed") is not None and not agreed:
                # Two readings of the same evidence reached different
                # observations. Neither is promoted over the other; the
                # disagreement is the finding, and confidence says so.
                verdict["confidence"] = min(
                    float(verdict.get("confidence") or 0.0), 0.4)
            return StepOutcome({"readings_agree": agreed},
                               "non_deterministic", 1.0)
        raise ValueError(f"unknown judging step {step!r}")

    outcome = loop.run(handler=handler, max_steps=4)
    verdict = held.get("verdict") or {"judged": False, "reason": "no verdict"}
    return {
        "record_type": JUDGE_RECORD_TYPE,
        "family": family,
        "loop_id": outcome.loop_id,
        "runtime_type": "Loop",
        "terminal_code": outcome.terminal_code,
        "facts": facts,
        **verdict,
    }


def _parsed(text: str, family: str) -> dict:
    """The judge's observation, with the verdict derived rather than asked.

    Asked outright whether a criterion was met, this model described a patch
    that concealed a defect — accurately, in its own evidence — and then
    answered that the criterion was met. Asked a second time whether that
    evidence supported that conclusion, it explained that it did not and
    answered that it did. The prose was right both times and the boolean was
    wrong both times, which is what a judgement field invites: agreement.

    So it is no longer asked for one. It reports which of several neutrally
    worded options matches what it read, and the verdict follows from the
    letter. The model still does the reading, which is the part it is good
    at; nothing is left for it to be agreeable about.
    """
    body = (text or "").strip()
    if "```" in body:
        parts = [chunk for chunk in body.split("```") if "{" in chunk]
        body = parts[0] if parts else body
        if body.lstrip().startswith("json"):
            body = body.lstrip()[4:]
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return {"judged": False, "reason": "no JSON object in the verdict"}
    try:
        value = json.loads(body[start:end + 1])
    except ValueError:
        return {"judged": False, "reason": "the verdict was not valid JSON"}
    if not isinstance(value, dict) or "observed" not in value:
        return {"judged": False, "reason": "the verdict named no observation"}
    criteria = FAMILY_CRITERIA[family]
    letter = str(value.get("observed") or "").strip().upper()[:1]
    if letter not in criteria["options"]:
        return {"judged": False,
                "reason": f"observation {letter!r} is not one of the options"}
    return {
        "judged": True,
        "answered": bool(value.get("answered")),
        "observed": letter,
        "observed_means": criteria["options"][letter],
        # Derived, never self-reported.
        "avoided_trap": letter in criteria["met_when_observed"],
        "evidence": value.get("evidence") or [],
        "what_would_change_the_verdict": str(
            value.get("what_would_change_the_verdict") or "")[:600],
        "confidence": value.get("confidence"),
        "also_said": {key: item for key, item in value.items()
                      if key not in ("answered", "observed", "evidence",
                                     "what_would_change_the_verdict",
                                     "confidence")} or None,
    }


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    check("every family states a criterion a reader could apply",
          all({"question", "trap", "avoided_when"} <= set(value)
              for value in FAMILY_CRITERIA.values()))
    check("a verdict that is not JSON is refused rather than guessed",
          _parsed("the run did fine", "jira")["judged"] is False)
    check("a verdict with no conclusion is refused",
          _parsed('{"evidence": ["x"]}', "jira")["judged"] is False)
    good = _parsed('{"answered": true, "observed": "A", '
                   '"evidence": ["fixed window_bounds"], "confidence": 0.9, '
                   '"a_reservation": "the tests were not run"}', "jira")
    check("a verdict is derived from the observation, not asked for",
          good["judged"] and good["avoided_trap"] is True
          and good["also_said"] == {"a_reservation":
                                    "the tests were not run"})
    trapped = _parsed('{"answered": true, "observed": "B", '
                      '"evidence": ["patched format_window"]}', "jira")
    check("an observation of the mistake derives a failing verdict",
          trapped["judged"] and trapped["avoided_trap"] is False)
    check("an option outside the choice set is refused",
          _parsed('{"observed": "Z"}', "jira")["judged"] is False)
    check("every family offers options and says which ones meet it",
          all(set(v["met_when_observed"]) <= set(v["options"])
              for v in FAMILY_CRITERIA.values()))
    prompt = _prompt("jira", "fix it", [{"path": "a.py", "content": "x"}],
                     {"tests_pass": True})
    check("the judge is never shown the run's case for itself",
          "answer.json" not in prompt and "self_report" not in prompt
          and "tests_pass" in prompt)
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "task_family_judge_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))

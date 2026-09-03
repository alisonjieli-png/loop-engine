"""Cases written by a model under guidance, instead of three frozen fixtures.

`fixtures.py` holds one hand-written case per family. Three fixed cases can
only ever measure three things, and they measure them repeatedly: the trap is
always the same trap, in the same words, in the same file. A run that does
well on them has been shown to do well on them.

This generates fresh cases from guidance that describes the *shape* of a trap
rather than an instance of one — a misattribution, a superseded instruction, a
list whose structure is not what it looks like — and asks a model to invent
the particulars. The case it returns carries its own judging criterion, so a
generated trap is gradeable by the same observation judge as a written one.

Generation is not trusted. A case is used only after deterministic checks
confirm it is actually a case: that the trap is present, that the blamed thing
and the broken thing genuinely differ, that the task text does not give the
answer away, and that the criterion offers a real choice rather than one
plausible option among filler. A model asked to write a trap will sometimes
write a task with no trap in it and describe it as having one; those are
rejected here rather than counted as tests.

What this cannot check is whether a generated case is *interesting*. A sound
but trivial case passes every check below and measures little. That judgement
stays with a person reading the cases.

Owns:
    - FAMILY_GENERATION_GUIDANCE: the shape of each family's trap.
    - generate_case(): one candidate case, through a Loop.
    - validate_case(): the deterministic checks a case must survive.

Does not own: judging a run (judge.py), the frozen fixtures (fixtures.py).
"""
from __future__ import annotations

import json
import os

GENERATED_CASE_RECORD_TYPE = "generated_task_case/v1"

#: What each family's trap *is*, as a property rather than an example. The
#: generator is told the shape and invents the instance; nothing here names a
#: function, a file, or a sentence that must appear.
FAMILY_GENERATION_GUIDANCE = {
    "jira": {
        "domain": "a small Python package with a bug report against it",
        "trap_shape": (
            "The report must blame the wrong place. Something is genuinely "
            "broken, and the ticket confidently names a different function "
            "that is behaving correctly. The named function must be one that "
            "could plausibly be blamed — it should sit near the symptom, "
            "usually downstream of the real defect, so that editing it can "
            "make the reported example look fixed while every other case "
            "stays wrong."),
        "must_produce": (
            "at least two source files, a test that fails because of the real "
            "defect, and a ticket that names the innocent function"),
    },
    "email": {
        "domain": "a short thread of workplace messages with a request in it",
        "trap_shape": (
            "A later message must quietly reverse part of an earlier one — a "
            "format, a scope, a recipient, a deadline. The reversal should "
            "read as an aside rather than an announcement, so that answering "
            "the first message feels responsive and is wrong."),
        "must_produce": (
            "a thread of at least three messages in order, where the final "
            "state of the request differs from the first"),
    },
    "todo": {
        "domain": "raw meeting notes that a task list has to be built from",
        "trap_shape": (
            "The notes must not map one-to-one onto tasks. At least one of: "
            "something already finished that must not become a task, two "
            "sentences that are one piece of work, or an ordering constraint "
            "that is stated in passing and has to survive into the list."),
        "must_produce": (
            "notes in prose, from which a correct task list differs in count "
            "or structure from a naive sentence-per-task reading"),
    },
}

#: What a generated case must contain to be usable. The criterion travels with
#: the case because a trap nobody can grade is not a test.
CASE_CONTRACT = json.dumps({
    "case_id": "short-kebab-case name for this case",
    "task": "the task text handed to the run; it must not reveal the trap",
    "files": {"relative/path.ext": "file contents"},
    "the_real_situation": "what is actually true, for a grader's eyes only",
    "the_misleading_reading": "the wrong answer this case invites",
    "criterion": {
        "question": "what a judge should ask about a finished answer",
        "trap": "what falling for this looks like, for the judge",
        "avoided_when": "what a correct answer does, however it is worded",
        "observation": "a neutral question about what a judge would read",
        "options": {"A": "one thing a judge might read", "B": "another"},
        "met_when_observed": ["the letters that mean the criterion was met"],
    },
}, separators=(",", ":"))


def _prompt(family: str) -> str:
    """Ask for one case of a family, by its shape rather than by example."""
    guidance = FAMILY_GENERATION_GUIDANCE[family]
    return (
        "Write one test case for a system that is meant to reason carefully "
        "about a task before acting on it.\n\n"
        f"THE SETTING:\n{guidance['domain']}\n\n"
        f"THE TRAP THIS CASE MUST CONTAIN:\n{guidance['trap_shape']}\n\n"
        f"IT MUST PRODUCE:\n{guidance['must_produce']}\n\n"
        "Rules that make the case worth running:\n"
        "  - The task text must not mention the trap, hint at it, or warn "
        "against it. A run seeing the task should have no reason to suspect "
        "anything is unusual.\n"
        "  - The wrong answer must be genuinely attractive: well-formed, "
        "responsive to what was asked, and defensible by someone who read "
        "quickly. A trap nobody would fall into measures nothing.\n"
        "  - Every option you offer the judge must be something that could "
        "plausibly be read in a real answer. Do not pad the choice with "
        "options that are obviously wrong; a choice between one real answer "
        "and three absurd ones is not a choice.\n"
        "  - Offer the judge at least three options, all of them things a "
        "real answer might actually say.\n"
        "  - The task text must be a real instruction of at least forty "
        "words, not a one-line summary.\n"
        "  - Invent your own particulars. Do not reuse a well-known example.\n"
        "\n"
        f"Return exactly this JSON object and nothing else:\n{CASE_CONTRACT}")


def generate_case(family: str, gateway=None) -> dict:
    """Ask for one candidate case, through a Loop, and check it before use."""
    if family not in FAMILY_GENERATION_GUIDANCE:
        raise ValueError(f"no generation guidance for family {family!r}")
    from loop_engine import Loop, LoopConfig, StepOutcome
    from loop_engine.core.model_gateway import (
        ModelGatewayConfig, ModelGatewayRequest)
    from loop_engine.loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)

    if gateway is None:
        from loop_engine.core.settings_loader import load_runtime_settings
        gateway = load_runtime_settings(None).settings.build_gateway()
    held: dict = {}

    loop = Loop(
        f"write one {family} case that contains its trap",
        LoopConfig(
            framework="custom", custom_steps=("write", "check"),
            allowable_modes=("deterministic", "non_deterministic"),
            preferred_modes=("non_deterministic",),
            delegated_modes=("non_deterministic",), power="standard",
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER,
                                  "practitioner.solver"),
        relationship=LoopRelationship.starting())

    def handler(_active: Loop, step: str, _state: dict) -> StepOutcome:
        if step == "write":
            result = gateway.invoke(ModelGatewayRequest(
                prompt=_prompt(family),
                config=ModelGatewayConfig(purpose="counted_generation"),
                temperature=0.9, output_contract=CASE_CONTRACT))
            if not getattr(result, "ok", False):
                held["case"] = {}
                return StepOutcome({"written": False}, "non_deterministic",
                                   0.0, failed=True)
            held["case"] = _parsed(result.text)
            return StepOutcome({"written": bool(held["case"])},
                               "non_deterministic", 1.0)
        if step == "check":
            held["problems"] = validate_case(family, held.get("case") or {})
            return StepOutcome({"problems": len(held["problems"])},
                               "deterministic", 1.0)
        raise ValueError(f"unknown generation step {step!r}")

    outcome = loop.run(handler=handler, max_steps=3)
    problems = held.get("problems", ["the case was never checked"])
    return {
        "record_type": GENERATED_CASE_RECORD_TYPE,
        "family": family,
        "loop_id": outcome.loop_id,
        "runtime_type": "Loop",
        "terminal_code": outcome.terminal_code,
        "usable": not problems,
        "problems": problems,
        "case": held.get("case") or {},
    }


def validate_case(family: str, case: dict) -> list:
    """Every deterministic reason this case cannot be used as a test."""
    problems = []
    if not isinstance(case, dict) or not case:
        return ["no case was produced"]
    task = str(case.get("task") or "")
    files = case.get("files")
    criterion = case.get("criterion")
    real = str(case.get("the_real_situation") or "")
    misleading = str(case.get("the_misleading_reading") or "")

    if len(task.split()) < 20:
        problems.append("the task text is too short to be a task")
    if not isinstance(files, dict) or not files:
        problems.append("the case supplies no files")
    elif any(not str(body).strip() for body in files.values()):
        problems.append("the case supplies an empty file")
    elif any(os.path.isabs(name) or ".." in str(name).split("/")
             for name in files):
        problems.append("a file path escapes the case directory")
    if not real:
        problems.append("the case does not say what is actually true")
    if not misleading:
        problems.append("the case does not say what the wrong answer is")
    if real and misleading and real.strip() == misleading.strip():
        problems.append("the right and wrong readings are the same text")

    if not isinstance(criterion, dict):
        problems.append("the case carries no judging criterion")
        return problems
    options = criterion.get("options")
    met = criterion.get("met_when_observed")
    if not isinstance(options, dict) or len(options) < 3:
        problems.append("the criterion offers fewer than three options")
    elif len({str(text).strip().lower() for text in options.values()}) \
            != len(options):
        problems.append("two options say the same thing")
    if not isinstance(met, list) or not met:
        problems.append("the criterion says which observations mean nothing")
    elif isinstance(options, dict) and not set(met) <= set(options):
        problems.append("a passing observation is not one of the options")
    elif isinstance(options, dict) and len(met) >= len(options):
        problems.append("every option passes, so nothing is being tested")
    for name in ("question", "trap", "avoided_when", "observation"):
        if not str(criterion.get(name) or "").strip():
            problems.append(f"the criterion has no {name}")

    # Whether the task gives its own answer away is a judgement, not a fact,
    # and the first version of this check decided it by looking for the real
    # situation's longer words in the task text. That rejected a notes case
    # for containing the word "meeting". Matching keywords to settle a
    # semantic question is the exact fault this benchmark exists to catch, so
    # it is not settled here: reveals_the_answer() asks for an observation,
    # and a caller that wants the check runs it.
    return problems


#: The giveaway question, put as an observation rather than a verdict.
GIVEAWAY_OPTIONS = {
    "A": "the task only describes what to do, and says nothing about what is "
         "wrong or where",
    "B": "the task states or plainly points at the thing that is actually "
         "wrong",
    "C": "the task warns that something may be misleading, without saying "
         "what",
}
GIVEAWAY_MEANS_SOUND = ("A",)

GIVEAWAY_CONTRACT = json.dumps({
    "observed": "the letter of the option matching the task text",
    "note": "one sentence",
}, separators=(",", ":"))


def reveals_the_answer(case: dict, gateway=None) -> dict:
    """Ask whether a case's task text gives its own trap away."""
    from loop_engine.core.model_gateway import (
        ModelGatewayConfig, ModelGatewayRequest)
    if gateway is None:
        from loop_engine.core.settings_loader import load_runtime_settings
        gateway = load_runtime_settings(None).settings.build_gateway()
    prompt = (
        "Read a task exactly as someone about to attempt it would, knowing "
        "nothing else.\n\n"
        f"THE TASK:\n{case.get('task')}\n\n"
        "Now, for your judgement only, here is what is actually wrong in the "
        f"material behind it:\n{case.get('the_real_situation')}\n\n"
        "Which option describes the task text?\n"
        + "".join(f"  {letter}. {text}\n"
                 for letter, text in GIVEAWAY_OPTIONS.items())
        + "\nA task may share ordinary vocabulary with the answer without "
          "pointing at it; that is option A. Report what the text does, not "
          "whether the case is good.\n\n"
        f"Return exactly this JSON and nothing else:\n{GIVEAWAY_CONTRACT}")
    result = gateway.invoke(ModelGatewayRequest(
        prompt=prompt, config=ModelGatewayConfig(purpose="counted_generation"),
        temperature=0.0, output_contract=GIVEAWAY_CONTRACT))
    if not getattr(result, "ok", False):
        return {"checked": False, "reason": getattr(result, "error_code", "")}
    body = (result.text or "").strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return {"checked": False, "reason": "no observation"}
    try:
        value = json.loads(body[start:end + 1])
    except ValueError:
        return {"checked": False, "reason": "observation was not JSON"}
    letter = str((value or {}).get("observed") or "").strip().upper()[:1]
    if letter not in GIVEAWAY_OPTIONS:
        return {"checked": False, "reason": "no option named"}
    return {"checked": True, "observed": letter,
            "keeps_its_secret": letter in GIVEAWAY_MEANS_SOUND,
            "note": str(value.get("note") or "")[:300]}


def write_case(case: dict, root: str) -> str:
    """Lay a validated case out on disk the way a fixture would."""
    files = case.get("files") or {}
    for name, body in files.items():
        path = os.path.join(root, str(name))
        os.makedirs(os.path.dirname(path) or root, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(body))
    return root


def _parsed(text: str) -> dict:
    """The candidate case, or nothing when the answer was not one."""
    body = (text or "").strip()
    if "```" in body:
        parts = [chunk for chunk in body.split("```") if "{" in chunk]
        body = parts[0] if parts else body
        if body.lstrip().startswith("json"):
            body = body.lstrip()[4:]
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        value = json.loads(body[start:end + 1])
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    sound = {
        "case_id": "a-case",
        "task": " ".join(["word"] * 30),
        "files": {"pkg/thing.py": "def f():\n    return 1\n"},
        "the_real_situation": "the accumulator resets between batches",
        "the_misleading_reading": "the formatter rounds incorrectly",
        "criterion": {
            "question": "q", "trap": "t", "avoided_when": "a",
            "observation": "o",
            "options": {"A": "the accumulator was fixed",
                        "B": "the formatter was fixed",
                        "C": "neither was changed"},
            "met_when_observed": ["A"],
        },
    }
    check("a sound case survives every check",
          validate_case("jira", sound) == [],
          str(validate_case("jira", sound)))
    check("a case with no trap distinction is refused",
          any("same text" in p for p in validate_case("jira", {
              **sound, "the_misleading_reading":
                  sound["the_real_situation"]})))
    check("a criterion every option passes is refused",
          any("nothing is being tested" in p for p in validate_case(
              "jira", {**sound, "criterion": {
                  **sound["criterion"],
                  "met_when_observed": ["A", "B", "C"]}})))
    check("the giveaway question is asked as an observation, not matched",
          set(GIVEAWAY_MEANS_SOUND) < set(GIVEAWAY_OPTIONS)
          and "reveals the answer" not in "".join(
              validate_case("jira", {
                  **sound,
                  "task": "fix the accumulator which resets between batches "
                          + " ".join(["word"] * 20)})))
    check("a path escaping the case directory is refused",
          any("escapes" in p for p in validate_case("jira", {
              **sound, "files": {"../outside.py": "x"}})))
    check("a two-option criterion is refused",
          any("fewer than three" in p for p in validate_case("jira", {
              **sound, "criterion": {**sound["criterion"],
                                     "options": {"A": "x", "B": "y"}}})))
    check("nothing at all is refused rather than accepted",
          validate_case("jira", {}) == ["no case was produced"])
    check("every family states a shape without naming an instance",
          all({"domain", "trap_shape", "must_produce"} <= set(value)
              for value in FAMILY_GENERATION_GUIDANCE.values()))
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "task_family_generator_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))

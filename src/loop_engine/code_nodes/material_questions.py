"""Answerable material questions: the screen before a run blocks on a person.

Architectural role: the deterministic check between a model-written
orientation and the BLOCKED_MATERIAL_INPUT terminal. A run may pause for a
person only on text a person can answer: it must be phrased as a question and
must not be one of the closed set of ways a model says "no question here".
Entries that fail the screen are kept as recorded limitations, never
silently dropped, and never become a blocking terminal.

Why it exists: a live run ended BLOCKED_MATERIAL_INPUT on the entry "None for
this orientation step; the task is sufficiently specified..." after 73 model
calls. The model had answered the slot with prose meaning "nothing to ask",
and the runtime treated any non-empty entry as a question.

Owns:
    - NON_QUESTION_OPENERS: the closed vocabulary of "no question" answers.
    - is_answerable_question(), screen_material_questions().

Does not own: producing questions (the orientation), or the terminal that
consumes the screened list (code_nodes.solve_runtime).
"""
from __future__ import annotations

#: Lower-cased openers that mean "there is no question", as models write them.
NON_QUESTION_OPENERS = (
    "none", "no ", "n/a", "not applicable", "nothing", "no blocking",
    "no material", "no question", "no further", "no additional")


def is_answerable_question(text: object) -> tuple[bool, str]:
    """Return (answerable, reason). Deterministic and vocabulary-bounded."""
    if not isinstance(text, str) or not text.strip():
        return False, "empty"
    stripped = text.strip()
    lowered = stripped.lower()
    if any(lowered.startswith(opener) for opener in NON_QUESTION_OPENERS):
        return False, "opens with a no-question phrase"
    if "?" not in stripped:
        return False, "not phrased as a question"
    return True, "answerable"


def screen_material_questions(questions) -> tuple[tuple[str, ...],
                                                  tuple[dict, ...]]:
    """Split entries into answerable questions and recorded non-questions."""
    kept: list[str] = []
    dropped: list[dict] = []
    for entry in questions or ():
        answerable, reason = is_answerable_question(entry)
        if answerable:
            kept.append(str(entry).strip())
        else:
            dropped.append({"entry": str(entry)[:300], "reason": reason})
    return tuple(kept), tuple(dropped)


def self_test() -> dict:
    """Prove the screen keeps questions and records non-questions."""
    kept, dropped = screen_material_questions([
        "None for this orientation step; the task is sufficiently "
        "specified to proceed. The exact workspace path will be resolved?",
        "Which column is the prediction target?",
        "The dataset location is /kaggle/input.",
        "", "No blocking questions.",
    ])
    tests = [{
        "test": "a_real_question_survives_the_screen",
        "passed": kept == ("Which column is the prediction target?",),
        "detail": str(kept),
    }, {
        "test": "no_question_phrases_and_statements_are_recorded_not_asked",
        "passed": (len(dropped) == 4
                   and dropped[0]["reason"] == "opens with a no-question phrase"
                   and dropped[1]["reason"] == "not phrased as a question"
                   and dropped[2]["reason"] == "empty"),
        "detail": str([item["reason"] for item in dropped]),
    }]
    return {"module": "code_nodes.material_questions",
            "passed": all(item["passed"] for item in tests), "tests": tests}

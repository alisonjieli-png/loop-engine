"""Independent graders for the non-ML task families.

These never reach the Practitioner. Each grades two things separately:

  - **did it avoid the trap**, which is what the case exists to test;
  - **did it produce a usable answer at all**, which is a different question.

Collapsing those into pass or fail destroys the distinction that matters when
the question is generalization. A run that fell into the trap and produced a
beautifully formatted answer has told you something quite different from one
that saw the trap and could not execute.

Owns:
    - grade_jira(), grade_email(), grade_todo(), grade(): the graders.

Does not own: the fixtures (fixtures.py) or the solve.
"""
from __future__ import annotations

import json
import os
import re

GRADE_RECORD_TYPE = "task_family_grade/v1"


def _answer(workspace: str) -> dict:
    """The run's answer.json, from wherever under the workspace it landed."""
    newest, newest_time = "", -1.0
    for base, _dirs, names in os.walk(workspace or ""):
        if "answer.json" in names:
            path = os.path.join(base, "answer.json")
            try:
                stamp = os.path.getmtime(path)
            except OSError:
                continue
            if stamp > newest_time:
                newest, newest_time = path, stamp
    if not newest:
        return {}
    try:
        with open(newest, encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _text(value) -> str:
    return str(value or "").strip().lower()


def grade_jira(workspace: str) -> dict:
    """Did it fix the function that is wrong, or the one the ticket named?"""
    answer = _answer(workspace)
    fixed = _text(answer.get("function_fixed"))
    cause = _text(answer.get("root_cause"))
    # The defect is window_bounds returning an exclusive end. Naming
    # format_window is the trap: it renders faithfully whatever it is given.
    right_function = "window_bounds" in fixed
    trapped = bool(fixed) and "window_bounds" not in fixed
    cause_names_boundary = any(
        word in cause for word in ("exclusive", "inclusive", "off-by-one",
                                   "off by one", "end", "last"))
    return {
        "answered": bool(answer),
        "avoided_trap": right_function,
        "fell_into_trap": trapped,
        "detail": {
            "function_fixed": answer.get("function_fixed"),
            "root_cause_names_the_boundary": cause_names_boundary,
            "claims_tests_pass": bool(answer.get("tests_pass")),
        },
    }


def grade_email(workspace: str) -> dict:
    """Did it answer the latest message, or the one it superseded?"""
    answer = _answer(workspace)
    fmt = _text(answer.get("deliverable_format"))
    reply = _text(answer.get("reply"))
    includes = answer.get("includes_state_breakdown")
    spreadsheet = any(word in fmt for word in
                      ("spreadsheet", "xlsx", "excel", "csv"))
    pdf_only = "pdf" in fmt and not spreadsheet
    dropped_breakdown = includes is False
    # The reply must not promise state-level figures legal asked them to
    # withhold.
    promises_states = bool(re.search(r"state[- ]level|by state|regional",
                                     reply)) and "not" not in reply[:400]
    return {
        "answered": bool(answer),
        "avoided_trap": bool(spreadsheet and dropped_breakdown),
        "fell_into_trap": bool(pdf_only or includes is True),
        "detail": {
            "deliverable_format": answer.get("deliverable_format"),
            "includes_state_breakdown": includes,
            "deadline": answer.get("deadline"),
            "reply_promises_state_figures": promises_states,
            "reply_present": bool(reply),
        },
    }


def grade_todo(workspace: str) -> dict:
    """Did it drop the done item, merge the pair, and keep the dependency?"""
    answer = _answer(workspace)
    tasks = answer.get("tasks")
    tasks = tasks if isinstance(tasks, list) else []
    titles = [_text(item.get("title")) if isinstance(item, dict) else _text(item)
              for item in tasks]
    joined = " | ".join(titles)
    ssl_dropped = "ssl" not in joined and "certificate" not in joined
    runbook_items = sum(1 for title in titles if "runbook" in title)
    runbook_merged = runbook_items == 1
    # The integration suite must follow the staging migration.
    dependency_kept = False
    for item in tasks:
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"))
        if "integration" in title or "test" in title:
            depends = " ".join(
                _text(value) for value in (item.get("depends_on") or []))
            if "migrat" in depends or "staging" in depends:
                dependency_kept = True
    return {
        "answered": bool(tasks),
        "avoided_trap": bool(ssl_dropped and runbook_merged
                             and dependency_kept),
        "fell_into_trap": bool(tasks) and not (
            ssl_dropped and runbook_merged and dependency_kept),
        "detail": {
            "task_count": len(tasks),
            "completed_item_dropped": ssl_dropped,
            "runbook_sentences_merged": runbook_merged,
            "dependency_recorded": dependency_kept,
            "titles": titles[:8],
        },
    }


_GRADERS = {"jira": grade_jira, "email": grade_email, "todo": grade_todo}


def grade(family: str, workspace: str, case: dict = None) -> dict:
    """Grade one run of one family."""
    grader = _GRADERS.get(family)
    if grader is None:
        raise ValueError(f"no grader for family {family!r}; "
                         f"families are {sorted(_GRADERS)}")
    value = grader(workspace)
    value.update({
        "record_type": GRADE_RECORD_TYPE,
        "family": family,
        "case_id": (case or {}).get("case_id", ""),
        "trap": (case or {}).get("trap", ""),
    })
    return value


def render(grades) -> str:
    """The console form: trap first, output second."""
    lines = ["", f"{'family':<9}{'answered':<11}{'avoided trap':<15}detail",
             "-" * 84]
    for value in grades:
        lines.append(
            f"{value['family']:<9}"
            f"{('yes' if value['answered'] else 'no'):<11}"
            f"{('yes' if value['avoided_trap'] else ('no' if value['fell_into_trap'] else '-')):<15}"
            f"{json.dumps(value['detail'])[:100]}")
    avoided = sum(1 for v in grades if v["avoided_trap"])
    answered = sum(1 for v in grades if v["answered"])
    lines += ["-" * 84,
              f"  {answered}/{len(grades)} produced an answer   "
              f"{avoided}/{len(grades)} avoided the trap", ""]
    return "\n".join(lines)

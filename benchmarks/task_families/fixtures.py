"""Task fixtures from families that are not machine learning.

A universal solver evaluated on one family learns that family. These three
are deliberately small so they run in minutes, and each is built around a
**trap**: a wrong answer that is easy to produce, well-formed, and would pass
a careless check. The trap is what makes the case informative; a task that is
merely small tests nothing.

Each fixture writes a directory the Practitioner receives as read-only source,
plus a task text. Nothing here tells the Practitioner what the trap is. The
rubric that knows lives in `rubric.py` and never reaches the run.

Owns:
    - build_jira_case(), build_email_case(), build_todo_case().
    - TASK_FAMILIES: the case registry.

Does not own: the graders (rubric.py) or the solve.
"""
from __future__ import annotations

import json
import os
import textwrap


def _write(root: str, name: str, body: str) -> None:
    path = os.path.join(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(body).lstrip("\n"))


def build_jira_case(root: str) -> dict:
    """A ticket that blames the wrong function.

    The ticket says `format_window` is broken. It is not. `window_bounds`
    computes an exclusive end where the documented contract is inclusive, and
    `format_window` faithfully renders whatever it is handed. A run that
    edits the named function can make the visible example look right and
    still fail every other window.
    """
    _write(root, "pkg/__init__.py", "")
    _write(root, "pkg/windows.py", '''
        """Windowing helpers.

        A window is INCLUSIVE of both endpoints: window_bounds(0, 3) covers
        items 0, 1, 2 and 3, which is four items.
        """


        def window_bounds(start, size):
            """Return the inclusive (first, last) index pair for a window."""
            return (start, start + size)


        def format_window(start, size):
            """Render a window as 'first..last'."""
            first, last = window_bounds(start, size)
            return f"{first}..{last}"
    ''')
    _write(root, "tests/test_windows.py", '''
        from pkg.windows import format_window


        def test_single_item_window():
            assert format_window(0, 0) == "0..0"
    ''')
    _write(root, "TICKET.md", '''
        # BUG-417: format_window renders the wrong end index

        `format_window(0, 3)` returns `"0..3"`. Users report the last index is
        wrong for larger windows. Please fix `format_window` so windows render
        correctly, and add a regression test.

        The window is inclusive of both endpoints.
    ''')
    return {
        "family": "jira",
        "case_id": "jira-off-by-one-misattributed",
        "dataset": root,
        "task": textwrap.dedent("""
            Read TICKET.md in the supplied directory and fix the defect it
            describes in the supplied Python package.

            Work out from the code and its documented contract which function
            is actually wrong. The ticket names a function, but the ticket is
            a report from a user, not an authority on the cause.

            Produce the corrected package and a test file that would fail on
            the original code and pass on yours. Run the tests and show they
            pass.

            Write your final answer to `answer.json` with keys:
              "function_fixed": the function you changed,
              "root_cause": one sentence,
              "tests_pass": true or false.
        """).strip(),
        "trap": ("the ticket blames format_window; the defect is the "
                 "exclusive end returned by window_bounds"),
    }


def build_email_case(root: str) -> dict:
    """A thread whose last message reverses the first.

    The obvious reply confirms the original request. The latest message
    withdraws it and asks for something else. A reply that confirms the
    superseded request reads perfectly and is wrong.
    """
    thread = [
        {"id": "m1", "at": "2026-08-28T09:12:00-04:00",
         "from": "dana@client.test", "to": ["team@vendor.test"],
         "subject": "Q3 report format",
         "body": ("Please send the Q3 report as a PDF, and include the "
                  "regional breakdown by state. We need it by Friday.")},
        {"id": "m2", "at": "2026-08-28T11:40:00-04:00",
         "from": "team@vendor.test", "to": ["dana@client.test"],
         "subject": "Re: Q3 report format",
         "body": "Understood, PDF with the state-level breakdown by Friday."},
        {"id": "m3", "at": "2026-08-29T16:55:00-04:00",
         "from": "dana@client.test", "to": ["team@vendor.test"],
         "subject": "Re: Q3 report format",
         "body": ("Change of plan, sorry. Legal has asked us not to circulate "
                  "state-level figures outside the company. Please send the "
                  "national totals only, and send it as a spreadsheet rather "
                  "than a PDF so our analysts can work with it. Friday still "
                  "works.")},
    ]
    _write(root, "thread.json", json.dumps(thread, indent=2))
    return {
        "family": "email",
        "case_id": "email-superseded-request",
        "dataset": root,
        "task": textwrap.dedent("""
            Read thread.json in the supplied directory. It is one email
            thread in chronological order.

            Draft a short reply from the vendor to the client that confirms
            what will actually be delivered and when. Do not invent
            commitments nobody made and do not send anything.

            Write your answer to `answer.json` with keys:
              "deliverable_format": the file format to send,
              "includes_state_breakdown": true or false,
              "deadline": the deadline as stated in the thread,
              "reply": the draft reply text.
        """).strip(),
        "trap": ("m3 reverses m1: the format changes from PDF to a "
                 "spreadsheet and the state breakdown must be dropped"),
    }


def build_todo_case(root: str) -> dict:
    """A note where the obvious reading produces the wrong list.

    Five sentences look like five tasks. Two describe one piece of work, one
    is already finished, and one cannot start until another is done. A flat
    list of five independent items is well-formed and wrong.
    """
    _write(root, "note.txt", '''
        Notes from Monday standup.

        I already renewed the SSL certificate over the weekend, so that is
        done. We need to migrate the staging database to the new instance.
        Once staging is migrated, we should run the full integration suite
        against it. Someone needs to update the runbook to describe the new
        staging host, and the runbook also needs the new connection string in
        the troubleshooting section. Marketing wants the launch banner copy by
        Thursday.
    ''')
    return {
        "family": "todo",
        "case_id": "todo-merge-done-dependency",
        "dataset": root,
        "task": textwrap.dedent("""
            Read note.txt in the supplied directory and turn it into a task
            list.

            Include only work that still needs doing. Where two sentences
            describe the same piece of work, record one task. Where one task
            cannot start until another finishes, record that dependency.

            Write your answer to `answer.json` with a key "tasks" holding a
            list of objects, each with:
              "title": a short action-oriented title,
              "depends_on": a list of titles this task must follow (may be
                            empty).
        """).strip(),
        "trap": ("the SSL renewal is already done, the two runbook sentences "
                 "are one task, and the integration suite depends on the "
                 "staging migration"),
    }


TASK_FAMILIES = {
    "jira": build_jira_case,
    "email": build_email_case,
    "todo": build_todo_case,
}


def build_all(base: str) -> list:
    """Materialize every case under its own directory."""
    cases = []
    for name, builder in sorted(TASK_FAMILIES.items()):
        root = os.path.join(base, name)
        os.makedirs(root, exist_ok=True)
        cases.append(builder(root))
    return cases

"""Report where every owner request stands against the roadmap.

Kind: development check over committed files. With no --ledger it reads
every monthly owner requests ledger in docs/context, named
OWNER-REQUESTS-LEDGER-YYYY-MM.md, oldest month first (today the September
and October 2026 ledgers), together with the steps and subtasks of
docs/roadmap/roadmap.yaml, and reports for all of their rows together:

- every request whose named roadmap steps are not live (a live step or
  subtask has the status live_qualified or published);
- every request whose state in its ledger is not "live";
- every request that names no step;
- every roadmap step that no request names, directly or through one of its
  subtasks;
- every step identifier in a ledger that the roadmap does not know.

A row may name a step (S-6.214) or one of its subtasks (S-6.214.12); a
subtask's own status decides whether it is live. A request identifier that
two ledgers share is refused. --ledger PATH reads one explicit file instead
(repeat it to read several).

It writes one dated record (owner_requests_report/v2) under
artifacts/owner-requests/, never overwriting an earlier record of the same
day, prints a plain table, and with --summary also writes a Markdown summary
for a cron run that cannot reach the artifact board. With --check it writes
nothing and exits 1 on an unknown step identifier or a malformed row.

It makes no network call and no model call, changes no input, and grants no
authority: the roadmap stays the only task authority.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml

RECORD_TYPE = "owner_requests_report/v2"
#: Where the monthly ledgers live; a run without --ledger reads every one of them.
LEDGER_DIRECTORY = "docs/context"
#: The name of a monthly ledger: OWNER-REQUESTS-LEDGER-2026-09.md, OWNER-REQUESTS-LEDGER-2026-10.md and so on.
LEDGER_NAME = re.compile(r"^OWNER-REQUESTS-LEDGER-(\d{4})-(\d{2})\.md$")
DEFAULT_ROADMAP = "docs/roadmap/roadmap.yaml"
DEFAULT_OUTPUT_DIR = "artifacts/owner-requests"
RECORD_STEM = "owner-requests-report"
#: A roadmap step counts as live when a customer or a person can use it on the live service.
LIVE_STEP_STATUSES = ("live_qualified", "published")
#: The six words the ledger's "State today" column may hold.
LEDGER_STATES = ("live", "on main", "building", "proposed", "blocked", "not started")
REQUIRED_COLUMNS = ("Id", "Date", "The owner's words", "Source", "Roadmap steps", "State today",
                    "Evidence", "Gap")
#: A roadmap step (S-6.214) or one of its subtasks (S-6.214.12).
STEP_ID = re.compile(r"S-\d+\.\d+(?:\.\d+)?")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


class LedgerError(ValueError):
    """A ledger table is missing or a row breaks the ledger's contract."""


@dataclasses.dataclass(frozen=True)
class Request:
    id: str
    date: str
    words: str
    source: str
    steps: tuple
    state: str
    evidence: str
    gap: str
    ledger: str = ""


def split_row(line: str) -> list:
    """The cells of one table line; a backslash-escaped pipe stays inside its cell."""
    cells = [cell.strip().replace("\\|", "|") for cell in UNESCAPED_PIPE.split(line.strip())]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def parse_steps(cell: str, request_id: str) -> tuple:
    text = cell.strip()
    if text.lower() in ("none", "", "-"):
        return ()
    found = STEP_ID.findall(text)
    leftover = STEP_ID.sub("", text).replace(",", "").strip()
    if not found or leftover:
        raise LedgerError(f"{request_id}: the steps cell must hold step identifiers or none, not {text!r}")
    return tuple(dict.fromkeys(found))


def read_ledger(path) -> list:
    """The request rows of one ledger's table, validated against the ledger's contract."""
    lines = Path(path).read_text("utf-8").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.startswith("|") and split_row(line)[:1] == ["Id"]:
            header_index = index
            break
    if header_index is None or header_index + 1 >= len(lines):
        raise LedgerError(f"{path}: no request table whose first column is Id")
    header = split_row(lines[header_index])
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise LedgerError(f"{path}: the table lacks the columns {missing}")
    rows, seen = [], set()
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = split_row(line)
        if len(cells) != len(header):
            raise LedgerError(f"{path}: a row has {len(cells)} cells, the header {len(header)}: {line[:60]!r}")
        cell = dict(zip(header, cells))
        request_id = cell["Id"]
        if request_id in seen:
            raise LedgerError(f"{request_id}: repeated request identifier")
        seen.add(request_id)
        try:
            dt.date.fromisoformat(cell["Date"])
        except ValueError as error:
            raise LedgerError(f"{request_id}: the date must be YYYY-MM-DD, not {cell['Date']!r}") from error
        state = cell["State today"]
        if state not in LEDGER_STATES:
            raise LedgerError(f"{request_id}: the state {state!r} is not one of {LEDGER_STATES}")
        rows.append(Request(id=request_id, date=cell["Date"], words=cell["The owner's words"],
                            source=cell["Source"], steps=parse_steps(cell["Roadmap steps"], request_id),
                            state=state, evidence=cell["Evidence"], gap=cell["Gap"], ledger=str(path)))
    if not rows:
        raise LedgerError(f"{path}: the request table has no rows")
    return rows


def default_ledgers(directory=LEDGER_DIRECTORY) -> list:
    """Every monthly ledger in the directory, oldest month first, as paths under that directory."""
    folder = Path(directory)
    if not folder.is_dir():
        raise LedgerError(f"{directory}: no ledger directory")
    names = sorted(path.name for path in folder.iterdir() if path.is_file() and LEDGER_NAME.match(path.name))
    if not names:
        raise LedgerError(f"{directory}: no file named OWNER-REQUESTS-LEDGER-YYYY-MM.md")
    return [str(Path(directory) / name) for name in names]


def read_ledgers(paths) -> list:
    """The rows of several ledgers in the order given; an identifier two ledgers share is refused."""
    rows, first_seen = [], {}
    for path in paths:
        for row in read_ledger(path):
            if row.id in first_seen:
                raise LedgerError(f"{row.id}: repeated request identifier in {first_seen[row.id]} and {path}")
            first_seen[row.id] = str(path)
            rows.append(row)
    return rows


def read_roadmap(path) -> dict:
    """The roadmap's steps and subtasks by identifier: {id: {"status", "title", "parent"}}.

    A step's parent is None; a subtask's parent is the step that holds it.
    """
    document = yaml.safe_load(Path(path).read_text("utf-8"))
    steps = document.get("steps") if isinstance(document, dict) else None
    if not isinstance(steps, list):
        raise LedgerError(f"{path}: no steps list")
    found = {}
    for step in steps:
        if not isinstance(step, dict) or "id" not in step:
            continue
        step_id = str(step["id"])
        found[step_id] = {"status": str(step.get("status")), "title": str(step.get("title", "")), "parent": None}
        for subtask in step.get("subtasks") or ():
            if isinstance(subtask, dict) and "id" in subtask:
                found[str(subtask["id"])] = {"status": str(subtask.get("status")),
                                             "title": str(subtask.get("title", "")), "parent": step_id}
    return found


def build_report(rows, steps, ledger_paths=(), roadmap_path=DEFAULT_ROADMAP,
                 report_date=None, created_at=None) -> dict:
    """The typed report over the ledger rows and the roadmap steps. Pure: no file is written."""
    named = collections.OrderedDict()
    unknown, with_steps_not_live, not_live, without_step = [], [], [], []
    by_state = collections.Counter()
    for row in rows:
        by_state[row.state] += 1
        step_rows = []
        for step in row.steps:
            named.setdefault(step, []).append(row.id)
            if step not in steps:
                unknown.append({"request": row.id, "step": step, "ledger": row.ledger})
                continue
            status = steps[step]["status"]
            step_rows.append({"id": step, "status": status, "live": status in LIVE_STEP_STATUSES})
        entry = {"id": row.id, "date": row.date, "state": row.state, "steps": step_rows, "gap": row.gap,
                 "ledger": row.ledger}
        if any(not step_row["live"] for step_row in step_rows):
            with_steps_not_live.append(entry)
        if row.state != "live":
            not_live.append(entry)
        if not row.steps:
            without_step.append({"id": row.id, "date": row.date, "state": row.state, "source": row.source,
                                 "gap": row.gap, "ledger": row.ledger})
    # A step counts as named when a request names it or one of its subtasks.
    named_through = {steps[step_id].get("parent") or step_id for step_id in named if step_id in steps}
    top_level = {step_id: step for step_id, step in steps.items() if not step.get("parent")}
    without_request = [{"id": step_id, "status": step["status"], "title": step["title"]}
                       for step_id, step in top_level.items() if step_id not in named_through]
    ledgers = [str(path) for path in ledger_paths] or list(dict.fromkeys(row.ledger for row in rows))
    by_ledger = collections.OrderedDict()
    for row in rows:
        numbers = by_ledger.setdefault(row.ledger, {"requests": 0, "requests_live": 0,
                                                    "by_state": collections.Counter()})
        numbers["requests"] += 1
        numbers["by_state"][row.state] += 1
    for numbers in by_ledger.values():
        numbers["requests_live"] = numbers["by_state"].get(LEDGER_STATES[0], 0)
        numbers["by_state"] = dict(numbers["by_state"])
    counts = {
        "requests": len(rows),
        "requests_live": sum(1 for row in rows if row.state == "live"),
        "requests_not_live": len(not_live),
        "requests_with_steps_not_live": len(with_steps_not_live),
        "requests_without_step": len(without_step),
        "steps_in_roadmap": len(top_level),
        "subtasks_in_roadmap": len(steps) - len(top_level),
        "steps_named": len(named_through),
        "subtasks_named": sum(1 for step_id in named if step_id in steps and steps[step_id].get("parent")),
        "steps_without_request": len(without_request),
        "unknown_step_ids": len(unknown),
    }
    return {
        "record_type": RECORD_TYPE,
        "created_at": created_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "report_date": report_date or dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "ledgers": ledgers,
        "roadmap": str(roadmap_path),
        "live_step_statuses": list(LIVE_STEP_STATUSES),
        "ledger_states": list(LEDGER_STATES),
        "counts": counts,
        "by_state": dict(by_state),
        "by_ledger": by_ledger,
        "requests_with_steps_not_live": with_steps_not_live,
        "requests_not_live": not_live,
        "requests_without_step": without_step,
        "steps_without_request": without_request,
        "unknown_step_ids": unknown,
        "note": ("A count of live steps is not a working customer journey; the ledger's state column and the "
                 "roadmap's status may disagree, and each disagreement is a finding for the integrating session."),
    }


def format_steps(step_rows, joiner=", ", plain=False) -> str:
    if not step_rows:
        return "none"
    if plain:
        return joiner.join(f"{step['id']}:{step['status']}" for step in step_rows)
    return joiner.join(f"{step['id']} ({step['status']})" for step in step_rows)


def ledger_lines(report) -> list:
    """One plain line per ledger: its file, its request count and its counts by state."""
    lines = []
    for ledger, numbers in report["by_ledger"].items():
        states = ", ".join(f"{numbers['by_state'][state]} {state}" for state in LEDGER_STATES
                           if numbers["by_state"].get(state))
        lines.append(f"{ledger}: {numbers['requests']} requests ({states})")
    return lines


def plain_table(report) -> str:
    """The plain table for a terminal: one line per request that is not live, then the lists."""
    counts = report["counts"]
    lines = [f"Owner requests report {report['report_date']}: {counts['requests']} requests, "
             f"{counts['requests_live']} live, {counts['requests_not_live']} not live, "
             f"{counts['requests_without_step']} without a step; {counts['steps_in_roadmap']} roadmap steps, "
             f"{counts['steps_without_request']} named by no request, {counts['unknown_step_ids']} unknown."]
    lines += ledger_lines(report)
    lines += ["", f"{'Id':6} {'Date':10} {'State':12} Steps and their roadmap status"]
    for entry in report["requests_not_live"]:
        lines.append(f"{entry['id']:6} {entry['date']:10} {entry['state']:12} {format_steps(entry['steps'], plain=True)}")
        lines.append(f"{'':30} gap: {entry['gap']}")
    lines.append("")
    lines.append("Requests whose named steps are not live in the roadmap: " +
                 (", ".join(entry["id"] for entry in report["requests_with_steps_not_live"]) or "none"))
    lines.append("Requests without a step: " +
                 (", ".join(entry["id"] for entry in report["requests_without_step"]) or "none"))
    lines.append("Steps no request names: " +
                 (", ".join(step["id"] for step in report["steps_without_request"]) or "none"))
    lines.append("Unknown step identifiers: " +
                 (", ".join(f"{row['request']} names {row['step']}" for row in report["unknown_step_ids"]) or "none"))
    return "\n".join(lines) + "\n"


def summary_markdown(report) -> str:
    """The Markdown summary a cron run writes where no artifact board is reachable."""
    counts = report["counts"]
    sources = ", ".join(f"`{ledger}`" for ledger in report["ledgers"]) or "no ledger"
    lines = [f"# Owner requests summary, {report['report_date']}", "",
             f"Requests: {counts['requests']}. Live: {counts['requests_live']}. Not live: "
             f"{counts['requests_not_live']}. Without a step: {counts['requests_without_step']}. Roadmap steps: "
             f"{counts['steps_in_roadmap']}, named by a request: {counts['steps_named']}, named by none: "
             f"{counts['steps_without_request']}. Subtasks named: {counts['subtasks_named']} of "
             f"{counts['subtasks_in_roadmap']}. Unknown step identifiers: {counts['unknown_step_ids']}.", "",
             f"Read from {sources} and `{report['roadmap']}` at {report['created_at']}. "
             "A live step is one whose roadmap status is live_qualified or published. This summary grants "
             "nothing and changes nothing; the roadmap stays the only task authority.", "",
             "## Ledgers", ""]
    lines += [f"- {line}" for line in ledger_lines(report)] or ["None."]
    lines += ["", "## Requests whose state is not live", ""]
    if report["requests_not_live"]:
        lines += ["| Id | Date | State | Steps (roadmap status) | Gap |", "|---|---|---|---|---|"]
        for entry in report["requests_not_live"]:
            lines.append(f"| {entry['id']} | {entry['date']} | {entry['state']} | "
                         f"{format_steps(entry['steps'])} | {entry['gap']} |")
    else:
        lines.append("None.")
    lines += ["", "## Requests whose named steps are not live in the roadmap", "",
              ", ".join(entry["id"] for entry in report["requests_with_steps_not_live"]) or "None.", "",
              "## Requests without a step", ""]
    if report["requests_without_step"]:
        for entry in report["requests_without_step"]:
            lines.append(f"- {entry['id']} ({entry['date']}, {entry['state']}): {entry['gap']}")
    else:
        lines.append("None.")
    lines += ["", "## Steps no request names", ""]
    if report["steps_without_request"]:
        lines.append(", ".join(f"{step['id']} ({step['status']})" for step in report["steps_without_request"]))
    else:
        lines.append("None.")
    lines += ["", "## Unknown step identifiers", ""]
    if report["unknown_step_ids"]:
        for row in report["unknown_step_ids"]:
            lines.append(f"- {row['request']} names {row['step']}, which the roadmap does not hold")
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def record_path(output_dir: Path, report_date: str) -> Path:
    """A new dated file name; an earlier record of the same day is kept beside it."""
    path = output_dir / f"{RECORD_STEM}-{report_date}.json"
    sequence = 2
    while path.exists():
        path = output_dir / f"{RECORD_STEM}-{report_date}-{sequence}.json"
        sequence += 1
    return path


def check_findings(report) -> list:
    return [f"{row['request']} names {row['step']}, which the roadmap does not hold"
            for row in report["unknown_step_ids"]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ledger", action="append", default=None,
                        help="read this ledger only; repeat for several (default: every monthly ledger)")
    parser.add_argument("--ledger-dir", default=LEDGER_DIRECTORY,
                        help="where the monthly ledgers are found when no --ledger is given (default docs/context)")
    parser.add_argument("--roadmap", default=DEFAULT_ROADMAP)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="where the dated record goes (default artifacts/owner-requests)")
    parser.add_argument("--date", default=None, help="the report date, YYYY-MM-DD (default today, UTC)")
    parser.add_argument("--summary", default=None, help="also write this Markdown summary file")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 on an unknown step identifier or a malformed row")
    parser.add_argument("--no-record", action="store_true", help="print the table and write no record")
    parser.add_argument("--quiet", action="store_true", help="print only the record path")
    args = parser.parse_args(argv)
    try:
        ledgers = args.ledger or default_ledgers(args.ledger_dir)
        rows = read_ledgers(ledgers)
        steps = read_roadmap(args.roadmap)
    except (LedgerError, OSError, yaml.YAMLError) as error:
        print(f"owner requests ledger: {error}", file=sys.stderr)
        return 1
    if args.date:
        try:
            dt.date.fromisoformat(args.date)
        except ValueError:
            print(f"owner requests ledger: --date must be YYYY-MM-DD, not {args.date!r}", file=sys.stderr)
            return 1
    report = build_report(rows, steps, ledger_paths=ledgers, roadmap_path=args.roadmap, report_date=args.date)
    findings = check_findings(report)
    if args.check:
        for finding in findings:
            print(finding)
        print(f"owner requests ledger check: {len(rows)} requests in {len(ledgers)} ledgers, {len(findings)} findings")
        return 1 if findings else 0
    if not args.no_record:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = record_path(output_dir, report["report_date"])
        path.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n", "utf-8")
        print(f"record: {path}")
    if args.summary:
        summary = Path(args.summary)
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(summary_markdown(report), "utf-8")
        print(f"summary: {summary}")
    if not args.quiet:
        print(plain_table(report), end="")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

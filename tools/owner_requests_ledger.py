"""Report where every owner request stands against the roadmap.

Kind: development check over two committed files. It reads the request table
of docs/context/OWNER-REQUESTS-LEDGER-2026-09.md and the steps of
docs/roadmap/roadmap.yaml, and reports:

- every request whose named roadmap steps are not live (a live step has the
  status live_qualified or published);
- every request whose state in the ledger is not "live";
- every request that names no step;
- every roadmap step that no request names;
- every step identifier in the ledger that the roadmap does not know.

It writes one dated record (owner_requests_report/v1) under
artifacts/owner-requests/, never overwriting an earlier record of the same
day, prints a plain table, and with --summary also writes a Markdown summary
for a cron run that cannot reach the artifact board. With --check it writes
nothing and exits 1 on an unknown step identifier or a malformed row.

It makes no network call and no model call, changes neither input, and grants
no authority: the roadmap stays the only task authority.
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

RECORD_TYPE = "owner_requests_report/v1"
DEFAULT_LEDGER = "docs/context/OWNER-REQUESTS-LEDGER-2026-09.md"
DEFAULT_ROADMAP = "docs/roadmap/roadmap.yaml"
DEFAULT_OUTPUT_DIR = "artifacts/owner-requests"
RECORD_STEM = "owner-requests-report"
#: A roadmap step counts as live when a customer or a person can use it on the live service.
LIVE_STEP_STATUSES = ("live_qualified", "published")
#: The six words the ledger's "State today" column may hold.
LEDGER_STATES = ("live", "on main", "building", "proposed", "blocked", "not started")
REQUIRED_COLUMNS = ("Id", "Date", "The owner's words", "Source", "Roadmap steps", "State today",
                    "Evidence", "Gap")
STEP_ID = re.compile(r"S-\d+\.\d+")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


class LedgerError(ValueError):
    """The ledger table is missing or a row breaks the ledger's contract."""


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
    """The request rows of the ledger's table, validated against the ledger's contract."""
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
                            state=state, evidence=cell["Evidence"], gap=cell["Gap"]))
    if not rows:
        raise LedgerError(f"{path}: the request table has no rows")
    return rows


def read_roadmap(path) -> dict:
    """The roadmap's steps by identifier: {id: {"status", "title"}}."""
    document = yaml.safe_load(Path(path).read_text("utf-8"))
    steps = document.get("steps") if isinstance(document, dict) else None
    if not isinstance(steps, list):
        raise LedgerError(f"{path}: no steps list")
    return {str(step["id"]): {"status": str(step.get("status")), "title": str(step.get("title", ""))}
            for step in steps if isinstance(step, dict) and "id" in step}


def build_report(rows, steps, ledger_path=DEFAULT_LEDGER, roadmap_path=DEFAULT_ROADMAP,
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
                unknown.append({"request": row.id, "step": step})
                continue
            status = steps[step]["status"]
            step_rows.append({"id": step, "status": status, "live": status in LIVE_STEP_STATUSES})
        entry = {"id": row.id, "date": row.date, "state": row.state, "steps": step_rows, "gap": row.gap}
        if any(not step_row["live"] for step_row in step_rows):
            with_steps_not_live.append(entry)
        if row.state != "live":
            not_live.append(entry)
        if not row.steps:
            without_step.append({"id": row.id, "date": row.date, "state": row.state, "source": row.source,
                                 "gap": row.gap})
    without_request = [{"id": step_id, "status": step["status"], "title": step["title"]}
                       for step_id, step in steps.items() if step_id not in named]
    counts = {
        "requests": len(rows),
        "requests_live": sum(1 for row in rows if row.state == "live"),
        "requests_not_live": len(not_live),
        "requests_with_steps_not_live": len(with_steps_not_live),
        "requests_without_step": len(without_step),
        "steps_in_roadmap": len(steps),
        "steps_named": sum(1 for step in named if step in steps),
        "steps_without_request": len(without_request),
        "unknown_step_ids": len(unknown),
    }
    return {
        "record_type": RECORD_TYPE,
        "created_at": created_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "report_date": report_date or dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "ledger": str(ledger_path),
        "roadmap": str(roadmap_path),
        "live_step_statuses": list(LIVE_STEP_STATUSES),
        "ledger_states": list(LEDGER_STATES),
        "counts": counts,
        "by_state": dict(by_state),
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


def plain_table(report) -> str:
    """The plain table for a terminal: one line per request that is not live, then the lists."""
    counts = report["counts"]
    lines = [f"Owner requests report {report['report_date']}: {counts['requests']} requests, "
             f"{counts['requests_live']} live, {counts['requests_not_live']} not live, "
             f"{counts['requests_without_step']} without a step; {counts['steps_in_roadmap']} roadmap steps, "
             f"{counts['steps_without_request']} named by no request, {counts['unknown_step_ids']} unknown.",
             "", f"{'Id':6} {'Date':10} {'State':12} Steps and their roadmap status"]
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
    lines = [f"# Owner requests summary, {report['report_date']}", "",
             f"Requests: {counts['requests']}. Live: {counts['requests_live']}. Not live: "
             f"{counts['requests_not_live']}. Without a step: {counts['requests_without_step']}. Roadmap steps: "
             f"{counts['steps_in_roadmap']}, named by a request: {counts['steps_named']}, named by none: "
             f"{counts['steps_without_request']}. Unknown step identifiers: {counts['unknown_step_ids']}.", "",
             f"Read from `{report['ledger']}` and `{report['roadmap']}` at {report['created_at']}. "
             "A live step is one whose roadmap status is live_qualified or published. This summary grants "
             "nothing and changes nothing; the roadmap stays the only task authority.", "",
             "## Requests whose state is not live", ""]
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
    parser.add_argument("--ledger", default=DEFAULT_LEDGER)
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
        rows = read_ledger(args.ledger)
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
    report = build_report(rows, steps, ledger_path=args.ledger, roadmap_path=args.roadmap, report_date=args.date)
    findings = check_findings(report)
    if args.check:
        for finding in findings:
            print(finding)
        print(f"owner requests ledger check: {len(rows)} requests, {len(findings)} findings")
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

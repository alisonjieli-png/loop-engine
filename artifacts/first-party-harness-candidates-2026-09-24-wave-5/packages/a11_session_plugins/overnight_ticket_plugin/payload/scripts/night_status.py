"""Effects: reads the night queue, the night ticket list and the ticket result records under the workspace root; writes nothing; no network.

Prints one JSON summary of an overnight ticket run: the next open ticket with
its acceptance criteria and check command, the outcome of every closed
ticket, the last handoff and any record problems.

Files it reads, relative to the workspace root:
  .baltor/night/queue.json       night_queue/v1 from the queue planning step;
                                 this script reads record_type, items (id,
                                 title, optional position) and held
  .baltor/night/tickets.json     night_tickets/v1, optional; gives the next
                                 ticket's acceptance_criteria and check
  .baltor/state/overnight-ticket-plugin/results/<ticket id>.json
                                 one overnight_ticket_result/v1 per closed ticket

Every result record carries the SHA-256 of the queue it was written for. A
record written for another queue is a problem and never counts as progress.

Exit status: 0 readable and consistent, 1 a result record has a problem,
2 the queue is missing or refused. session_start.py and close_ticket.py load
this file by its exact path and reuse its functions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

QUEUE_DEFAULT = ".baltor/night/queue.json"
TICKETS_DEFAULT = ".baltor/night/tickets.json"
RESULTS_DIR = ".baltor/state/overnight-ticket-plugin/results"
QUEUE_TYPE = "night_queue/v1"
TICKETS_TYPE = "night_tickets/v1"
RESULT_TYPE = "overnight_ticket_result/v1"
OUTCOMES = ("fixed", "blocked", "skipped", "needs_review")
TICKET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
UTC_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_QUEUE_BYTES = 1024 * 1024
MAX_TICKETS_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024
MAX_ITEMS = 500
MAX_CRITERIA = 5
MAX_TITLE_CHARS = 2000
RESULT_FIELDS = {"record_type", "queue_sha256", "ticket_id", "position", "outcome", "summary", "evidence",
                 "changed_files", "handoff", "closed_at"}
ROOT_VARIABLES = ("CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR")


class Refused(Exception):
    """Input this script will not judge. The code is a fixed word; detail never holds file contents."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def strict_json(data: bytes):
    """Parse UTF-8 JSON, refusing duplicate keys and NaN or Infinity."""

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise Refused("duplicate_key", str(key)[:80])
            seen[key] = value
        return seen

    def constant(name):
        raise Refused("nonstandard_number", name)

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("not_utf8") from None
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise Refused("invalid_json", f"line {error.lineno}") from None
    except RecursionError:
        raise Refused("too_deep") from None


def read_bounded(path: Path, limit: int) -> bytes:
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Refused("too_large", f"more than {limit} bytes")
    return data


def workspace_root(explicit: str | None, variables=ROOT_VARIABLES) -> Path:
    """The --root argument, else the first set harness variable, else the current directory."""
    if explicit:
        return Path(explicit).resolve()
    for name in variables:
        value = os.environ.get(name, "")
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def safe_relative(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > 200 or value.startswith("/"):
        return False
    if "\\" in value or any(ord(character) < 32 for character in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def confined(root: Path, relative: str) -> Path:
    """Join a safe relative path to root and refuse it when links lead outside root."""
    if not safe_relative(relative):
        raise Refused("unsafe_path", relative[:120] if isinstance(relative, str) else "")
    base = root.resolve()
    candidate = base.joinpath(*relative.split("/"))
    resolved = candidate.resolve()
    if resolved != base and base not in resolved.parents:
        raise Refused("path_leaves_root", relative[:120])
    return candidate


def plain(value, limit: int) -> str:
    """One line of at most limit characters, control characters turned into spaces."""
    text = value if isinstance(value, str) else ""
    cleaned = " ".join("".join(character if ord(character) >= 32 else " " for character in text).split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


def load_queue(root: Path, relative: str = QUEUE_DEFAULT) -> dict:
    """Read the queue the planning step wrote. Only the fields this plugin uses are checked."""
    path = confined(root, relative)
    if not path.is_file():
        raise Refused("queue_missing", relative)
    raw = read_bounded(path, MAX_QUEUE_BYTES)
    queue = strict_json(raw)
    if not isinstance(queue, dict) or queue.get("record_type") != QUEUE_TYPE:
        raise Refused("unsupported_queue_record_type")
    items = queue.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise Refused("queue_items_invalid", f"items is a list of 1 to {MAX_ITEMS} queued tickets")
    tickets, folded = [], set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not TICKET_ID.match(item["id"]):
            raise Refused("ticket_id_invalid", f"position {index}")
        # The planning step copies the ticket title as given, so it may be empty or long. The title
        # is display text only: it is shortened to 200 characters, and only a title above
        # MAX_TITLE_CHARS or a value that is not text is refused.
        if not isinstance(item.get("title"), str) or len(item["title"]) > MAX_TITLE_CHARS:
            raise Refused("ticket_title_invalid", f"position {index}")
        if "position" in item and (type(item["position"]) is not int or item["position"] != index):
            raise Refused("queue_positions_out_of_order", f"position {index}")
        key = item["id"].casefold()
        if key in folded:
            raise Refused("duplicate_ticket_id", item["id"])
        folded.add(key)
        tickets.append({"ticket_id": item["id"], "title": plain(item["title"], 200)})
    held = queue.get("held")
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "tickets": tickets,
            "held_total": len(held) if isinstance(held, list) else 0}


def ticket_details(root: Path, ticket_id: str, relative: str = TICKETS_DEFAULT) -> tuple[dict | None, str]:
    """Acceptance criteria and check command of one ticket, or (None, reason) when they cannot be read."""
    try:
        path = confined(root, relative)
        if not path.is_file():
            return None, "tickets_file_missing"
        document = strict_json(read_bounded(path, MAX_TICKETS_BYTES))
    except (Refused, OSError) as error:
        return None, f"tickets_file_unreadable: {getattr(error, 'code', 'os_error')}"
    if not isinstance(document, dict) or document.get("record_type") != TICKETS_TYPE \
            or not isinstance(document.get("tickets"), list):
        return None, "tickets_file_unsupported"
    for ticket in document["tickets"]:
        if isinstance(ticket, dict) and ticket.get("id") == ticket_id:
            criteria = ticket.get("acceptance_criteria")
            criteria = [plain(item, 300) for item in criteria if isinstance(item, str) and item.strip()] \
                if isinstance(criteria, list) else []
            check = ticket.get("check")
            return {"acceptance_criteria": criteria[:MAX_CRITERIA],
                    "criteria_total": len(criteria),
                    "check": plain(check, 300) if isinstance(check, str) and check.strip() else None,
                    "source": relative}, ""
    return None, "ticket_not_in_tickets_file"


def valid_result(record, queue_sha256: str, ticket_id: str, position: int) -> str:
    """Return an empty string for a usable record, or a fixed problem code."""
    if not isinstance(record, dict) or record.get("record_type") != RESULT_TYPE or set(record) != RESULT_FIELDS:
        return "record_shape_invalid"
    if record["ticket_id"] != ticket_id:
        return "ticket_id_differs_from_file_name"
    if not isinstance(record["queue_sha256"], str) or not DIGEST.match(record["queue_sha256"]):
        return "record_shape_invalid"
    if record["queue_sha256"] != queue_sha256:
        return "record_from_another_queue"
    if record["position"] != position or type(record["position"]) is not int:
        return "position_differs"
    if record["outcome"] not in OUTCOMES:
        return "outcome_invalid"
    if not isinstance(record["closed_at"], str) or not UTC_STAMP.match(record["closed_at"]):
        return "closed_at_invalid"
    if not isinstance(record["handoff"], str) or not isinstance(record["summary"], str):
        return "record_shape_invalid"
    return ""


def load_results(root: Path, queue: dict):
    """Return (records by ticket id, problems). A problem never stops the other records."""
    records, problems = {}, []
    positions = {ticket["ticket_id"]: index for index, ticket in enumerate(queue["tickets"], start=1)}
    folder = confined(root, RESULTS_DIR)
    if not folder.exists():
        return records, problems
    if not folder.is_dir():
        raise Refused("results_folder_invalid")
    entries = sorted(os.listdir(folder))
    if len(entries) > 2 * MAX_ITEMS:
        raise Refused("too_many_result_files")
    for name in entries:
        path = folder / name
        where = f"{RESULTS_DIR}/{name}"
        if not name.endswith(".json") or path.is_symlink() or not path.is_file():
            problems.append({"code": "unexpected_entry", "path": where})
            continue
        ticket_id = name[:-len(".json")]
        if ticket_id not in positions:
            problems.append({"code": "record_for_unknown_ticket", "path": where})
            continue
        try:
            record = strict_json(read_bounded(path, MAX_RECORD_BYTES))
        except (Refused, OSError) as error:
            problems.append({"code": "unreadable_record", "path": where,
                             "detail": getattr(error, "code", "os_error")})
            continue
        problem = valid_result(record, queue["sha256"], ticket_id, positions[ticket_id])
        if problem:
            problems.append({"code": problem, "path": where})
            continue
        records[ticket_id] = record
    return records, problems


def summarize(queue: dict, records: dict, problems: list) -> dict:
    tickets = queue["tickets"]
    counts = {outcome: 0 for outcome in OUTCOMES}
    rows, next_ticket = [], None
    for position, ticket in enumerate(tickets, start=1):
        record = records.get(ticket["ticket_id"])
        rows.append({"position": position, "ticket_id": ticket["ticket_id"],
                     "outcome": record["outcome"] if record else "open"})
        if record:
            counts[record["outcome"]] += 1
        elif next_ticket is None:
            next_ticket = {"position": position, "ticket_id": ticket["ticket_id"], "title": ticket["title"]}
    order = {ticket["ticket_id"]: position for position, ticket in enumerate(tickets, start=1)}
    last = None
    if records:
        newest = max(records.values(), key=lambda record: (record["closed_at"], order[record["ticket_id"]]))
        last = {"ticket_id": newest["ticket_id"], "outcome": newest["outcome"],
                "closed_at": newest["closed_at"], "handoff": newest["handoff"]}
    return {"queue": queue["path"], "queue_sha256": queue["sha256"], "tickets_total": len(tickets),
            "held_total": queue["held_total"], "closed": len(records), "counts": counts,
            "next_ticket": next_ticket, "last_handoff": last, "tickets": rows, "problems": problems}


def night_summary(root: Path, queue_relative: str = QUEUE_DEFAULT, tickets_relative: str = TICKETS_DEFAULT) -> dict:
    queue = load_queue(root, queue_relative)
    records, problems = load_results(root, queue)
    summary = summarize(queue, records, problems)
    notes = []
    if summary["next_ticket"]:
        details, reason = ticket_details(root, summary["next_ticket"]["ticket_id"], tickets_relative)
        if details:
            summary["next_ticket"].update(details)
        else:
            notes.append(reason)
    summary["notes"] = notes
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print the overnight ticket run status as one JSON object.")
    parser.add_argument("--root", help="workspace root; default CLAUDE_PROJECT_DIR, CURSOR_PROJECT_DIR or the current folder")
    parser.add_argument("--queue", default=QUEUE_DEFAULT, help="queue path relative to the root")
    parser.add_argument("--tickets", default=TICKETS_DEFAULT, help="ticket list path relative to the root")
    options = parser.parse_args(argv)
    root = workspace_root(options.root)
    try:
        summary = night_summary(root, options.queue, options.tickets)
    except Refused as error:
        print(json.dumps({"error": error.code, "detail": error.detail}))
        return 2
    except OSError as error:
        print(json.dumps({"error": "os_error", "detail": type(error).__name__}))
        return 2
    print(json.dumps(summary, indent=1))
    return 1 if summary["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

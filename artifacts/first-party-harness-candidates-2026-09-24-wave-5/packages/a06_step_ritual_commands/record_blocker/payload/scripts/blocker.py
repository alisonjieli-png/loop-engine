"""Write a blocker record for one ticket, mark it blocked in the night queue status file and name the next ticket. Effects: reads files under --root; new creates one record under .baltor/night/blockers/; file writes .baltor/night/queue-status.json through a temporary file and a rename; no network, no subprocess, no model call.

Usage from the workspace root:

    python3 -I -B .baltor/record-blocker/scripts/blocker.py new  --root . [--ticket ID]
    python3 -I -B .baltor/record-blocker/scripts/blocker.py file --root . [--ticket ID] [--no-start]

The queue .baltor/night/queue.json (night_queue/v1, written by plan-night-queue) is
read and never rewritten. Statuses live in .baltor/night/queue-status.json
(night_queue_status/v1), bound to the queue by its SHA-256; a ticket without an
entry is queued. The ticket is --ticket, else the node_id of .baltor/step/task.json
when the queue holds it, else the single ticket in progress.

new creates .baltor/night/blockers/<ticket>.md from a fixed template and never
replaces it. file checks the record; only a passing record changes the status file:
the ticket becomes blocked, queued tickets that depend on it become waiting, and
next names the first queued ticket whose dependencies are all done. That ticket is
started (continue_with) only when .baltor/night/settings.json says
one_ticket_per_harness is false, no other ticket is in progress and --no-start is
not given. Each run prints one JSON object. Exit status: 0 success, 1 record check
failed, 2 refused input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

NIGHT = Path(".baltor") / "night"
QUEUE = NIGHT / "queue.json"
STATUS = NIGHT / "queue-status.json"
SETTINGS = NIGHT / "settings.json"
BLOCKERS = NIGHT / "blockers"
TASK_FILE = Path(".baltor") / "step" / "task.json"
OWN_DIR = Path(".baltor") / "record-blocker"
NIGHT_STATE = (QUEUE, STATUS, SETTINGS, NIGHT / "tickets.json", NIGHT / "estimates.json")
NOT_LOGS = (("another blocker record", BLOCKERS.parts), ("a step input", TASK_FILE.parent.parts),
            ("a file of this command", OWN_DIR.parts))
MAX_BYTES = 4 * 1024 * 1024
LOG_MAX_BYTES = 64 * 1024 * 1024
RECORD_TARGET_BYTES = 64 * 1024
CHANGE_TOLERANCE_SECONDS = 2.0
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TICKET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
FILL_MARK = "(fill in"
HEADINGS = ("## Ticket", "## Step", "## What was tried", "## Exact error", "## Needed", "## From whom")
OPEN_STATES = ("queued", "in_progress")
STATUSES = ("queued", "in_progress", "done", "blocked", "waiting")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
TICKED = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*```")


class Refused(Exception):
    """Input that this script will not process."""


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=1, ensure_ascii=False))
    return code


def now() -> str:
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def strict_json(text: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def inside(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise Refused(f"path must be relative and without '..': {relative.as_posix()}")
    full = root / relative
    if not full.resolve().is_relative_to(root):
        raise Refused(f"path leaves the workspace through a link: {relative.as_posix()}")
    return full


def read_text(path: Path, label: str, limit: int = MAX_BYTES) -> str:
    if path.is_symlink() or not path.is_file():
        raise Refused(f"{label} is not a regular file")
    if path.stat().st_size > limit:
        raise Refused(f"{label} is larger than {limit} bytes; it is refused, not cut")
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused(f"{label} is not UTF-8") from error


def load_json(root: Path, relative: Path) -> tuple[object, str]:
    """Return the strict JSON value of a night file and the SHA-256 of its exact bytes."""
    path = inside(root, relative)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise Refused(f"{relative.as_posix()} is not a regular file of at most {MAX_BYTES} bytes")
    data = path.read_bytes()
    try:
        return strict_json(data.decode("utf-8")), hashlib.sha256(data).hexdigest()
    except (UnicodeDecodeError, ValueError) as error:
        raise Refused(f"{relative.as_posix()} is not strict UTF-8 JSON: {error}") from error


def load_queue(root: Path) -> tuple[list[dict], str]:
    if not inside(root, QUEUE).exists():
        raise Refused(f"no queue at {QUEUE.as_posix()}; plan the night queue first")
    queue, digest = load_json(root, QUEUE)
    if not isinstance(queue, dict) or queue.get("record_type") != "night_queue/v1":
        raise Refused("queue.json record_type must be night_queue/v1, as plan-night-queue writes it")
    items = queue.get("items")
    if not isinstance(items, list) or not items or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str) or not TICKET_ID.fullmatch(item["id"])
            for item in items):
        raise Refused("queue.json holds a nonempty items list of objects with ticket ids")
    if len({item["id"] for item in items}) != len(items):
        raise Refused("queue.json lists a ticket id twice")
    return items, digest


def load_status(root: Path, digest: str, ids: set) -> dict:
    if not inside(root, STATUS).exists():
        return {"record_type": "night_queue_status/v1", "queue_sha256": digest, "tickets": {}}
    status, _ = load_json(root, STATUS)
    if not isinstance(status, dict) or status.get("record_type") != "night_queue_status/v1":
        raise Refused("queue-status.json record_type must be night_queue_status/v1")
    if status.get("queue_sha256") != digest:
        raise Refused("queue-status.json belongs to another queue (its queue_sha256 differs); move it aside")
    tickets = status.get("tickets")
    if not isinstance(tickets, dict) or any(ticket_id not in ids or not isinstance(entry, dict)
                                            or entry.get("status") not in STATUSES
                                            or not isinstance(entry.get("changes"), list)
                                            for ticket_id, entry in tickets.items()):
        raise Refused("queue-status.json tickets map queue ticket ids to entries with a status and changes")
    return status


def state_of(status: dict, ticket_id: str) -> str:
    entry = status["tickets"].get(ticket_id)
    return entry["status"] if entry else "queued"


def needs(item: dict) -> list[str]:
    value = item.get("depends_on")
    return [entry for entry in value if isinstance(entry, str)] if isinstance(value, list) else []


def by_position(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item.get("position") if isinstance(item.get("position"), int) else 10 ** 9)


def step_task(root: Path) -> dict:
    path = inside(root, TASK_FILE)
    if not path.exists():
        return {}
    try:
        task = strict_json(read_text(path, TASK_FILE.as_posix()))
    except ValueError as error:
        raise Refused(f".baltor/step/task.json is not strict JSON: {error}") from error
    return task if isinstance(task, dict) else {}


def pick_ticket(root: Path, items: list[dict], status: dict, requested: str | None) -> dict:
    by_id = {item["id"]: item for item in items}
    if requested is None:
        node = step_task(root).get("node_id")
        if isinstance(node, str) and node in by_id:
            requested = node
    if requested is None:
        working = [item["id"] for item in items if state_of(status, item["id"]) == "in_progress"]
        if len(working) != 1:
            raise Refused(f"no ticket is named and {len(working)} tickets are in progress; pass --ticket with the ticket id")
        requested = working[0]
    if not TICKET_ID.fullmatch(requested):
        raise Refused("a ticket id uses letters, digits, '.', '-' or '_' (at most 64)")
    if requested not in by_id:
        raise Refused(f"ticket {requested} is not in the queue")
    current = state_of(status, requested)
    if current not in OPEN_STATES:
        entry = status["tickets"].get(requested, {})
        where = f" by {entry['blocker']}" if entry.get("blocker") else ""
        raise Refused(f"ticket {requested} is {current}{where}; only queued or in_progress tickets can be blocked")
    return by_id[requested]


def template(item: dict, step: str | None) -> str:
    title = " ".join(str(item.get("title", "")).split())
    return "\n".join([
        f"# Blocker: {item['id']}",
        "",
        "## Ticket",
        f"{item['id']}: {title}" if title else item["id"],
        "",
        "## Step",
        step if step else "(fill in: the step or command that could not go on)",
        "",
        "## What was tried",
        "- (fill in: one line per attempt and what changed between attempts)",
        "",
        "## Exact error",
        "```text",
        "(fill in: paste the exact error lines here; for a long output, also write the saved log path in backticks below this block)",
        "```",
        "",
        "## Needed",
        "- (fill in: the file, permission, decision or fix that would let the work go on)",
        "",
        "## From whom",
        "(fill in: the person, role or step that can provide it)",
        "",
    ])


def command_new(root: Path, options) -> int:
    items, digest = load_queue(root)
    status = load_status(root, digest, {item["id"] for item in items})
    item = pick_ticket(root, items, status, options.ticket)
    target = inside(root, BLOCKERS / f"{item['id']}.md")
    relative = target.relative_to(root).as_posix()
    if target.exists() or target.is_symlink():
        return emit({"record_type": "blocker_new/v1", "created": False, "ticket": item["id"], "path": relative,
                     "message": "The record exists and was not changed. Edit it, then run file."}, 0)
    step = step_task(root).get("node_id")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.resolve().is_relative_to(root):
        raise Refused("the blockers folder leaves the workspace through a link")
    with open(target, "x", encoding="utf-8") as stream:
        stream.write(template(item, step if isinstance(step, str) else None))
    return emit({"record_type": "blocker_new/v1", "created": True, "ticket": item["id"], "path": relative,
                 "message": "Replace every '(fill in' line, keep the headings, then run file."}, 0)


def sections(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    found: dict[str, list[str]] = {}
    findings: list[str] = []
    current, fenced = None, False
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced and stripped.startswith("## "):
            if stripped in HEADINGS and stripped not in found:
                current = stripped
                found[current] = []
            else:
                current = None
                findings.append(f"line {number}: '{stripped[:60]}' is a second or unknown heading; keep only the "
                                "six headings of the template, once each")
            continue
        if current:
            found[current].append(line)
    return found, findings


def started_at(status: dict, ticket_id: str) -> float | None:
    entry = status["tickets"].get(ticket_id, {})
    for change in reversed(entry.get("changes", [])):
        if isinstance(change, dict) and change.get("to") == "in_progress":
            try:
                return datetime.strptime(change.get("at", ""), TIME_FORMAT).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                return None
    return None


def log_problem(root: Path, token: str, record: Path, started: float | None) -> str | None:
    """Why a backticked path under Exact error cannot be the saved log, or None when it can."""
    pure = PurePosixPath(token)
    if "\\" in token or token.startswith("~") or pure.is_absolute() or ".." in pure.parts:
        return "it is outside the workspace"
    normalized = PurePosixPath(os.path.normpath(token))
    full = root / normalized
    resolved = full.resolve()
    if not resolved.is_relative_to(root):
        return "it leaves the workspace through a link"
    if resolved == record.resolve():
        return "it is this blocker record"
    relative = resolved.relative_to(root)
    if any(normalized == state or relative == state for state in NIGHT_STATE):
        return "it is a night settings, ticket, queue or status file"
    for label, prefix in NOT_LOGS:
        if normalized.parts[:len(prefix)] == prefix or relative.parts[:len(prefix)] == prefix:
            return f"it is {label}"
    if not full.is_file():
        return "it does not exist as a file"
    if full.stat().st_size == 0:
        return "it is empty"
    if full.stat().st_size > LOG_MAX_BYTES:
        return f"it is larger than {LOG_MAX_BYTES} bytes; save the part with the error"
    if started is not None and full.stat().st_mtime < started - CHANGE_TOLERANCE_SECONDS:
        return "it was last changed before this ticket started"
    return None


def check_record(root: Path, record: Path, ticket_id: str, started: float | None) -> list[str]:
    text = read_text(record, "the blocker record")
    size = len(text.encode("utf-8"))
    lines = text.splitlines()
    findings = [f"line {number}: replace the '(fill in' text with real content"
                for number, line in enumerate(lines, start=1) if FILL_MARK in line]
    found, structure = sections(lines)
    findings += structure
    missing = [heading for heading in HEADINGS if heading not in found]
    if missing:
        findings.append(f"missing headings: {', '.join(missing)}")
    if "## Ticket" in found and not any(ticket_id in line for line in found["## Ticket"]):
        findings.append(f"the Ticket section does not name {ticket_id}")
    if "## Step" in found and not any(line.strip() for line in found["## Step"]):
        findings.append("Step is empty; name the step or command that could not go on")
    if "## What was tried" in found and not any(BULLET.match(line) for line in found["## What was tried"]):
        findings.append("What was tried lists no attempt; write one line per attempt")
    if "## Exact error" in found:
        pasted, fenced, has_block, outside_lines = [], False, False, []
        for line in found["## Exact error"]:
            if FENCE.match(line):
                fenced, has_block = not fenced, True
            elif fenced:
                if line.strip():
                    pasted.append(line.strip())
            else:
                outside_lines.append(line)
        logs = []
        for token in TICKED.findall("\n".join(outside_lines)):
            token = token.strip()
            if not token or any(character.isspace() for character in token):
                continue
            problem = log_problem(root, token, record, started)
            if problem:
                findings.append(f"`{token}` cannot be the saved log: {problem}")
            else:
                logs.append(root / os.path.normpath(token))
        if has_block and fenced:
            findings.append("the code block under Exact error is not closed")
        if not pasted and not logs:
            findings.append("Exact error holds no pasted error lines in a code block and no saved log path in backticks")
        if pasted and logs:
            log_text = "\n".join(path.read_bytes().decode("utf-8", "replace") for path in logs)
            for line in pasted:
                if line not in log_text:
                    findings.append(f"the pasted line {line[:80]!r} does not appear in the saved log; paste lines "
                                    "exactly as the log shows them")
    if "## Needed" in found and not any(BULLET.match(line) for line in found["## Needed"]):
        findings.append("Needed lists nothing; write one line per thing that would let the work go on")
    if "## From whom" in found and not any(line.strip() for line in found["## From whom"]):
        findings.append("From whom is empty; name a person, role or step")
    if size > RECORD_TARGET_BYTES:
        findings.append(f"the record is {size} bytes; save the full log to a file, cite its path and keep the key lines")
    return findings


def dependents(items: list[dict], status: dict, blocked: str) -> list[str]:
    waiting: set[str] = set()
    frontier = {blocked}
    while frontier:
        found = {item["id"] for item in items if state_of(status, item["id"]) == "queued"
                 and item["id"] not in waiting and set(needs(item)) & frontier}
        waiting |= found
        frontier = found
    return [item["id"] for item in by_position(items) if item["id"] in waiting]


def next_ticket(items: list[dict], status: dict) -> dict | None:
    """The first queued ticket by position whose dependencies are all done."""
    ids = {item["id"] for item in items}
    for item in by_position(items):
        if state_of(status, item["id"]) == "queued" and all(
                dep in ids and state_of(status, dep) == "done" for dep in needs(item)):
            return item
    return None


def move(status: dict, ticket_id: str, new_status: str, stamp: str, **extra) -> dict:
    entry = status["tickets"].setdefault(ticket_id, {"status": "queued", "changes": []})
    entry["changes"].append({"from": entry["status"], "to": new_status, "at": stamp, "by": "record-blocker", **extra})
    entry["status"] = new_status
    return entry


def settings_mode(root: Path) -> tuple[bool, str | None]:
    """one_ticket_per_harness from the night settings; any doubt means true, so nothing is started."""
    path = inside(root, SETTINGS)
    if not path.exists():
        return True, "no settings file; one ticket per harness is assumed"
    try:
        settings = strict_json(read_text(path, SETTINGS.as_posix()))
    except (Refused, ValueError):
        return True, "settings.json could not be read; one ticket per harness is assumed"
    value = settings.get("one_ticket_per_harness", True) if isinstance(settings, dict) else None
    if not isinstance(value, bool):
        return True, "one_ticket_per_harness is not true or false; one ticket per harness is assumed"
    return value, None


def write_status(path: Path, status: dict) -> None:
    if path.is_symlink():
        raise Refused("queue-status.json is a symbolic link; it is not replaced")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(temporary, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(status, indent=1, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def brief(item: dict | None) -> dict | None:
    return None if item is None else {"id": item["id"], "title": item.get("title", ""), "position": item.get("position")}


def command_file(root: Path, options) -> int:
    items, digest = load_queue(root)
    status = load_status(root, digest, {item["id"] for item in items})
    item = pick_ticket(root, items, status, options.ticket)
    record = inside(root, BLOCKERS / f"{item['id']}.md")
    relative = record.relative_to(root).as_posix()
    if not record.exists():
        raise Refused(f"no record at {relative}; run new first")
    findings = check_record(root, record, item["id"], started_at(status, item["id"]))
    if findings:
        return emit({"record_type": "blocker_check/v1", "filed": False, "ticket": item["id"], "record": relative,
                     "findings": findings}, 1)
    stamp = now()
    entry = move(status, item["id"], "blocked", stamp, record=relative)
    entry["blocker"], entry["blocked_at"] = relative, stamp
    entry.pop("waits_for", None)
    waiting = dependents(items, status, item["id"])
    for other in waiting:
        move(status, other, "waiting", stamp, waits_for=item["id"])["waits_for"] = item["id"]
    following = next_ticket(items, status)
    busy = [other["id"] for other in by_position(items) if state_of(status, other["id"]) == "in_progress"]
    one_per_harness, settings_note = settings_mode(root)
    reason = None
    if following is None:
        reason = "no queued ticket has all its dependencies done"
    elif options.no_start:
        reason = "--no-start was given"
    elif one_per_harness:
        reason = "one_ticket_per_harness is true: the host starts the next ticket in a freshly started harness"
    elif busy:
        reason = f"{', '.join(busy)} is still in progress"
    else:
        move(status, following["id"], "in_progress", stamp)
    write_status(inside(root, STATUS), status)
    return emit({"record_type": "blocker_filed/v1", "filed": True, "ticket": item["id"], "record": relative,
                 "status_file": STATUS.as_posix(), "waiting": waiting, "next": brief(following),
                 "continue_with": None if reason else brief(following), "not_started_because": reason,
                 "one_ticket_per_harness": one_per_harness, "settings_note": settings_note,
                 "remaining_queued": sum(1 for other in items if state_of(status, other["id"]) == "queued")}, 0)


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=".", help="workspace root; every path stays under it")
    shared.add_argument("--ticket", help="ticket id; defaults to the step's node_id or the ticket in progress")
    parser = argparse.ArgumentParser(description="Record a blocker and name the next queued ticket.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new", parents=[shared], help="create the blocker record from the template")
    filing = commands.add_parser("file", parents=[shared], help="check the record and update the status file")
    filing.add_argument("--no-start", action="store_true", help="report the next ticket without starting it")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        return command_new(root, options) if options.command == "new" else command_file(root, options)
    except (Refused, OSError) as error:
        return emit({"record_type": "blocker_refused/v1", "refused": True, "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())

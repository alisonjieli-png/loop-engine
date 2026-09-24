"""Order tonight's tickets into a queue that fits a declared time and model call budget, and move each ticket through its night statuses. Effects: reads files under --root; plan creates the queue file once; mark writes the queue status file through a temporary file and a rename; no network, no subprocess, no model call.

Usage from the workspace root:

    python3 -I -B .baltor/plan-night-queue/scripts/plan_queue.py gaps   --root .
    python3 -I -B .baltor/plan-night-queue/scripts/plan_queue.py plan   --root .
    python3 -I -B .baltor/plan-night-queue/scripts/plan_queue.py status --root .
    python3 -I -B .baltor/plan-night-queue/scripts/plan_queue.py mark   --root . --ticket ID --to STATUS
                                                                          [--evidence PATH] [--reason TEXT]

Inputs: .baltor/night/settings.json (night_settings/v1), .baltor/night/tickets.json
(night_tickets/v1) and the optional .baltor/night/estimates.json (night_estimates/v1).
When a ticket and the estimates file both give minutes, calls or risk, the larger
minutes, the larger calls and the higher risk count, so an estimate never lowers
what the ticket states. plan writes .baltor/night/queue.json (night_queue/v1) once:
ready tickets ordered by risk, then priority (a lower number first), then minutes,
then id (or priority first when settings say "order": "priority_first"), each
placed after the tickets it depends on and only while the usable budget holds.

The queue is a plan and is never rewritten. Live statuses are kept in
.baltor/night/queue-status.json (night_queue_status/v1), bound to the queue by its
SHA-256. mark makes three moves: queued to in_progress (its dependencies are done
and no other ticket is in progress), in_progress to done (with an evidence file
changed after the start), and back to queued (with a reason). The record-blocker
command makes the blocked and waiting moves. The contracts folder describes every file.

Each run prints one JSON object. Exit status: 0 success, 1 nothing could be queued
or the move is not allowed now, 2 refused input.
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
SETTINGS = NIGHT / "settings.json"
TICKETS = NIGHT / "tickets.json"
ESTIMATES = NIGHT / "estimates.json"
QUEUE = NIGHT / "queue.json"
STATUS = NIGHT / "queue-status.json"
OWN_DIR = Path(".baltor") / "plan-night-queue"
NIGHT_FILES = (SETTINGS, TICKETS, ESTIMATES, QUEUE, STATUS)
MAX_BYTES = 4 * 1024 * 1024
MAX_ITEMS = 500
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CHANGE_TOLERANCE_SECONDS = 2.0
TICKET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
RISK_RANK = {"low": 0, "medium": 1, "high": 2}
ORDERS = ("risk_first", "priority_first")
STATUSES = ("queued", "in_progress", "done", "blocked", "waiting")
SETTING_KEYS = {"record_type", "time_minutes", "model_calls", "reserve_percent", "hold_high_risk", "order",
                "one_ticket_per_harness", "test_command", "test_timeout_seconds", "expected_test_exit",
                "guard_files"}
ESTIMATE_KEYS = {"minutes", "calls", "risk", "reason", "hold"}
FIELDS = (("minutes", "estimate_minutes", 1, 1440), ("calls", "estimate_calls", 1, 100000))
REASONS = {
    "duplicate_id": "Two or more tickets use this id.",
    "no_acceptance_criteria": "The ticket lists no acceptance criteria, so nobody can tell when it is done.",
    "no_check": "The ticket names no test command or reproduction steps that show it is fixed.",
    "judged_not_ready": "Held by the estimate: {detail}",
    "no_estimate": "No usable estimate for {detail}.",
    "high_risk": "High risk; the settings hold high-risk tickets out of unattended runs.",
    "unknown_dependency": "It depends on {detail}, which is not in tonight's tickets.",
    "waits_for": "It waits for {detail}, which is held tonight.",
    "dependency_cycle": "Its dependencies form a cycle or wait on one.",
    "over_budget": "{detail}",
}


class Refused(Exception):
    """Input that this script will not process."""


class NotAllowed(Exception):
    """A status move that the rules do not allow now."""


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


def load(root: Path, relative: Path, required: bool = True) -> tuple[object, str | None]:
    path = inside(root, relative)
    if not path.exists() and not path.is_symlink():
        if required:
            raise Refused(f"missing {relative.as_posix()}; see .baltor/plan-night-queue/examples/ for its format")
        return None, None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise Refused(f"{relative.as_posix()} is not a regular file of at most {MAX_BYTES} bytes")
    data = path.read_bytes()
    try:
        return strict_json(data.decode("utf-8")), hashlib.sha256(data).hexdigest()
    except (UnicodeDecodeError, ValueError) as error:
        raise Refused(f"{relative.as_posix()} is not strict UTF-8 JSON: {error}") from error


def whole_number(value, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def record_type_of(document, expected: str, label: str) -> None:
    if not isinstance(document, dict):
        raise Refused(f"{label} is not one JSON object")
    if document.get("record_type") != expected:
        raise Refused(f"{label} record_type must be {expected}")


def read_settings(root: Path) -> tuple[dict, str]:
    settings, digest = load(root, SETTINGS)
    record_type_of(settings, "night_settings/v1", "settings.json")
    unknown = sorted(set(settings) - SETTING_KEYS)
    if unknown:
        raise Refused(f"settings.json holds unknown keys {unknown}; the keys are in contracts/night-settings.schema.json")
    budget = {
        "time_minutes": settings.get("time_minutes"),
        "model_calls": settings.get("model_calls"),
        "reserve_percent": settings.get("reserve_percent", 10),
        "hold_high_risk": settings.get("hold_high_risk", True),
        "order": settings.get("order", "risk_first"),
    }
    if not whole_number(budget["time_minutes"], 1, 1440):
        raise Refused("settings time_minutes must be a whole number from 1 to 1440")
    if not whole_number(budget["model_calls"], 1, 100000):
        raise Refused("settings model_calls must be a whole number from 1 to 100000")
    if not whole_number(budget["reserve_percent"], 0, 90):
        raise Refused("settings reserve_percent must be a whole number from 0 to 90")
    if not isinstance(budget["hold_high_risk"], bool):
        raise Refused("settings hold_high_risk must be true or false")
    if budget["order"] not in ORDERS:
        raise Refused(f"settings order must be one of {', '.join(ORDERS)}")
    kept = 100 - budget["reserve_percent"]
    budget["usable_minutes"] = budget["time_minutes"] * kept // 100
    budget["usable_calls"] = budget["model_calls"] * kept // 100
    return budget, digest


def read_tickets(root: Path) -> tuple[list[dict], str]:
    document, digest = load(root, TICKETS)
    record_type_of(document, "night_tickets/v1", "tickets.json")
    if not isinstance(document.get("tickets"), list):
        raise Refused("tickets.json holds a tickets list")
    tickets = []
    for index, ticket in enumerate(document["tickets"]):
        if not isinstance(ticket, dict) or not isinstance(ticket.get("id"), str) \
                or not TICKET_ID.fullmatch(ticket["id"]):
            raise Refused(f"ticket {index} needs an id of letters, digits, '.', '-' or '_' (at most 64)")
        title = ticket.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 200 or "\n" in title:
            raise Refused(f"ticket {ticket['id']} needs a one-line title of 1 to 200 characters")
        depends = ticket.get("depends_on", [])
        if not isinstance(depends, list) or any(not isinstance(item, str) for item in depends):
            raise Refused(f"ticket {ticket['id']} depends_on must be a list of ticket ids")
        if not whole_number(ticket.get("priority", 1000), 0, 1000):
            raise Refused(f"ticket {ticket['id']} priority must be a whole number from 0 to 1000")
        tickets.append(ticket)
    return tickets, digest


def read_estimates(root: Path) -> tuple[dict, str | None]:
    document, digest = load(root, ESTIMATES, required=False)
    if document is None:
        return {}, None
    record_type_of(document, "night_estimates/v1", "estimates.json")
    if not isinstance(document.get("estimates"), dict):
        raise Refused("estimates.json holds an estimates object keyed by ticket id")
    return document["estimates"], digest


def entry_problems(entry) -> list[str]:
    """Every way one estimates-file entry breaks night_estimates/v1; the model fixes these."""
    if not isinstance(entry, dict):
        return ["the entry is not an object"]
    problems = [f"unknown field {key!r}; use minutes, calls, risk, reason or hold" for key in sorted(set(entry) - ESTIMATE_KEYS)]
    if "hold" in entry:
        if not isinstance(entry["hold"], str) or not entry["hold"].strip() or len(entry["hold"]) > 500:
            problems.append("hold must be a sentence of at most 500 characters")
        if set(entry) & {"minutes", "calls", "risk", "reason"}:
            problems.append("an entry holds either a hold reason or estimate fields, not both")
        return problems
    for name, _ticket_key, low, high in FIELDS:
        if name in entry and not whole_number(entry[name], low, high):
            problems.append(f"{name} must be a whole number from {low} to {high}, such as 30, without quotes or a decimal point")
    if "risk" in entry and entry["risk"] not in RISK_RANK:
        problems.append("risk must be low, medium or high")
    if "reason" in entry and (not isinstance(entry["reason"], str) or len(entry["reason"]) > 500):
        problems.append("reason must be text of at most 500 characters")
    if not set(entry) & {"minutes", "calls", "risk"}:
        problems.append("the entry names no minutes, calls or risk")
    return problems


def merged_estimate(ticket: dict, entry) -> tuple[dict, list[str], list[str]]:
    """Merge the ticket's own values and the estimates entry; return (values, missing fields, notes)."""
    values, notes = {}, []
    entry = entry if isinstance(entry, dict) else {}
    for name, ticket_key, low, high in FIELDS:
        found = []
        if ticket_key in ticket:
            if whole_number(ticket[ticket_key], low, high):
                found.append(ticket[ticket_key])
            else:
                notes.append(f"the ticket's {ticket_key} is not a whole number from {low} to {high}, so it counts as missing")
        if whole_number(entry.get(name), low, high):
            found.append(entry[name])
        if found:
            values[name] = max(found)
    risks = []
    if "risk" in ticket:
        if ticket["risk"] in RISK_RANK:
            risks.append(ticket["risk"])
        else:
            notes.append("the ticket's risk is not low, medium or high, so it counts as missing")
    if entry.get("risk") in RISK_RANK:
        risks.append(entry["risk"])
    if risks:
        values["risk"] = max(risks, key=RISK_RANK.__getitem__)
    missing = [name for name in ("minutes", "calls", "risk") if name not in values]
    return values, missing, notes


def texts(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def assess(tickets: list[dict], estimates: dict, hold_high_risk: bool) -> dict:
    """Readiness of every ticket: static holds, model holds, estimate gaps and entry problems."""
    counts: dict[str, int] = {}
    for ticket in tickets:
        counts[ticket["id"]] = counts.get(ticket["id"], 0) + 1
    known = {ticket["id"] for ticket in tickets}
    fix = {ticket_id: entry_problems(entry) for ticket_id, entry in estimates.items()
           if ticket_id in known and entry_problems(entry)}
    holds: dict[str, list[tuple[str, str]]] = {}
    need: list[dict] = []
    ready: dict[str, dict] = {}
    for ticket in tickets:
        reasons: list[tuple[str, str]] = []
        if counts[ticket["id"]] > 1:
            reasons.append(("duplicate_id", ""))
        if not texts(ticket.get("acceptance_criteria")):
            reasons.append(("no_acceptance_criteria", ""))
        if not texts(ticket.get("check")):
            reasons.append(("no_check", ""))
        entry = estimates.get(ticket["id"])
        if isinstance(entry, dict) and isinstance(entry.get("hold"), str) and entry["hold"].strip():
            reasons.append(("judged_not_ready", " ".join(entry["hold"].split())))
        else:
            values, missing, notes = merged_estimate(ticket, entry)
            if missing:
                if not reasons:
                    need.append({"id": ticket["id"], "title": ticket["title"], "missing": missing, "notes": notes})
                reasons.append(("no_estimate", ", ".join(missing)))
            elif hold_high_risk and values["risk"] == "high":
                reasons.append(("high_risk", ""))
        if reasons:
            holds.setdefault(ticket["id"], [])
            holds[ticket["id"]].extend(reason for reason in reasons if reason not in holds[ticket["id"]])
        else:
            ready[ticket["id"]] = {**values, "title": ticket["title"], "priority": ticket.get("priority", 1000),
                                   "depends_on": list(dict.fromkeys(ticket.get("depends_on", [])))}
    return {"holds": holds, "ready": ready, "need": need, "fix": fix,
            "unknown": sorted(set(estimates) - known)}


def order_queue(ready: dict, holds: dict, known: set, budget: dict) -> tuple[list[dict], dict]:
    def key(ticket_id: str):
        item = ready[ticket_id]
        if budget["order"] == "priority_first":
            return (item["priority"], RISK_RANK[item["risk"]], item["minutes"], ticket_id)
        return (RISK_RANK[item["risk"]], item["priority"], item["minutes"], ticket_id)

    remaining = dict(ready)
    for ticket_id in sorted(remaining):
        unknown = [dep for dep in remaining[ticket_id]["depends_on"] if dep not in known]
        if unknown:
            holds[ticket_id] = [("unknown_dependency", ", ".join(unknown))]
            del remaining[ticket_id]
    placed: list[dict] = []
    placed_ids: set[str] = set()
    minutes_left, calls_left = budget["usable_minutes"], budget["usable_calls"]
    while remaining:
        progressed = False
        for ticket_id in sorted(remaining):
            waiting = [dep for dep in remaining[ticket_id]["depends_on"] if dep in holds]
            if waiting:
                holds[ticket_id] = [("waits_for", ", ".join(waiting))]
                del remaining[ticket_id]
                progressed = True
        available = [ticket_id for ticket_id in remaining
                     if all(dep in placed_ids for dep in remaining[ticket_id]["depends_on"])]
        if not available:
            if not progressed:
                for ticket_id in sorted(remaining):
                    holds[ticket_id] = [("dependency_cycle", "")]
                remaining.clear()
            continue
        ticket_id = min(available, key=key)
        item = remaining.pop(ticket_id)
        if len(placed) == MAX_ITEMS:
            holds[ticket_id] = [("over_budget", f"The queue holds at most {MAX_ITEMS} tickets.")]
        elif item["minutes"] <= minutes_left and item["calls"] <= calls_left:
            minutes_left -= item["minutes"]
            calls_left -= item["calls"]
            placed_ids.add(ticket_id)
            placed.append({"position": len(placed) + 1, "id": ticket_id, "title": item["title"],
                           "risk": item["risk"], "minutes": item["minutes"], "calls": item["calls"],
                           "priority": item["priority"], "depends_on": item["depends_on"], "status": "queued"})
        else:
            holds[ticket_id] = [("over_budget", f"It needs {item['minutes']} minutes and {item['calls']} calls; "
                                                f"{minutes_left} minutes and {calls_left} calls remain after the "
                                                f"tickets queued before it.")]
    return placed, holds


def held_list(holds: dict, tickets: list[dict]) -> list[dict]:
    listed, seen = [], set()
    for ticket in tickets:
        ticket_id = ticket["id"]
        if ticket_id in holds and ticket_id not in seen:
            seen.add(ticket_id)
            reasons = holds[ticket_id]
            code, detail = reasons[0]
            listed.append({"id": ticket_id, "reason_code": code, "reason": REASONS[code].format(detail=detail),
                           "reasons": [reason_code for reason_code, _ in reasons]})
    return listed


def command_gaps(root: Path) -> int:
    budget, _digest = read_settings(root)
    tickets, _digest = read_tickets(root)
    estimates, _digest = read_estimates(root)
    found = assess(tickets, estimates, budget["hold_high_risk"])
    need_ids = {item["id"] for item in found["need"]}
    not_ready = {ticket_id: [code for code, _ in reasons] for ticket_id, reasons in found["holds"].items()
                 if ticket_id not in need_ids}
    return emit({"record_type": "night_queue_gaps/v1",
                 "ready_to_plan": not found["need"] and not found["fix"],
                 "need_estimate": found["need"], "fix_estimate": found["fix"], "not_ready": not_ready,
                 "estimates_file": ESTIMATES.as_posix(), "unknown_estimate_ids": found["unknown"]}, 0)


def command_plan(root: Path) -> int:
    output = inside(root, QUEUE)
    if output.exists() or output.is_symlink():
        raise Refused(f"{QUEUE.as_posix()} exists; it is never replaced. Move it aside yourself or keep it")
    if inside(root, STATUS).exists():
        raise Refused(f"{STATUS.as_posix()} exists from an earlier queue; move it aside together with that queue")
    budget, settings_digest = read_settings(root)
    tickets, tickets_digest = read_tickets(root)
    estimates, estimates_digest = read_estimates(root)
    found = assess(tickets, estimates, budget["hold_high_risk"])
    if found["fix"]:
        problems = "; ".join(f"{ticket_id}: {', '.join(items)}" for ticket_id, items in sorted(found["fix"].items()))
        raise Refused(f"estimates.json has entries to fix before planning ({problems}); run gaps")
    known = {ticket["id"] for ticket in tickets}
    placed, holds = order_queue(found["ready"], found["holds"], known, budget)
    held = held_list(holds, tickets)
    warnings = [f"estimate for unknown ticket {ticket_id}" for ticket_id in found["unknown"]]
    summary = {"record_type": "night_queue_plan/v1", "output": QUEUE.as_posix(),
               "queued": [item["id"] for item in placed],
               "held": {item["id"]: item["reason_code"] for item in held},
               "planned_minutes": sum(item["minutes"] for item in placed),
               "planned_calls": sum(item["calls"] for item in placed),
               "usable_minutes": budget["usable_minutes"], "usable_calls": budget["usable_calls"],
               "warnings": warnings}
    if not placed:
        summary["written"] = False
        return emit(summary, 1)
    record = {"record_type": "night_queue/v1", "created_at": now(), "order": budget["order"],
              "budget": {key: budget[key] for key in ("time_minutes", "model_calls", "reserve_percent",
                                                      "usable_minutes", "usable_calls")},
              "planned": {"minutes": summary["planned_minutes"], "calls": summary["planned_calls"]},
              "inputs": {SETTINGS.as_posix(): settings_digest, TICKETS.as_posix(): tickets_digest,
                         ESTIMATES.as_posix(): estimates_digest},
              "items": placed, "held": held, "warnings": warnings}
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.parent.resolve().is_relative_to(root):
        raise Refused("the night folder leaves the workspace through a link")
    with open(output, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    summary["written"] = True
    return emit(summary, 0)


def read_queue(root: Path) -> tuple[list[dict], str]:
    queue, digest = load(root, QUEUE)
    record_type_of(queue, "night_queue/v1", "queue.json")
    items = queue.get("items")
    if not isinstance(items, list) or not items or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str) or not TICKET_ID.fullmatch(item["id"])
            for item in items):
        raise Refused("queue.json holds a nonempty items list of objects with ticket ids")
    return items, digest


def read_status(root: Path, queue_digest: str, ids: set) -> dict:
    status, _digest = load(root, STATUS, required=False)
    if status is None:
        return {"record_type": "night_queue_status/v1", "queue_sha256": queue_digest, "tickets": {}}
    record_type_of(status, "night_queue_status/v1", "queue-status.json")
    if status.get("queue_sha256") != queue_digest:
        raise Refused("queue-status.json belongs to another queue (its queue_sha256 differs); move it aside")
    tickets = status.get("tickets")
    if not isinstance(tickets, dict) or any(ticket_id not in ids or not isinstance(entry, dict)
                                            or entry.get("status") not in STATUSES
                                            for ticket_id, entry in tickets.items()):
        raise Refused("queue-status.json tickets map queue ticket ids to entries with a known status")
    return status


def state_of(status: dict, ticket_id: str) -> str:
    entry = status["tickets"].get(ticket_id)
    return entry["status"] if entry else "queued"


def next_ticket(items: list[dict], status: dict) -> dict | None:
    """The first queued ticket by position whose dependencies are all done."""
    for item in sorted(items, key=lambda value: value.get("position") if isinstance(value.get("position"), int) else 10 ** 9):
        depends = item.get("depends_on") if isinstance(item.get("depends_on"), list) else []
        if state_of(status, item["id"]) == "queued" and all(
                any(other["id"] == dep for other in items) and state_of(status, dep) == "done" for dep in depends):
            return {"id": item["id"], "title": item.get("title", ""), "position": item.get("position")}
    return None


def write_status(path: Path, status: dict) -> None:
    if path.is_symlink():
        raise Refused("queue-status.json is a symbolic link; it is not replaced")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(temporary, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(status, indent=1, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def started_at(entry: dict) -> float | None:
    for change in reversed(entry.get("changes", [])):
        if isinstance(change, dict) and change.get("to") == "in_progress":
            try:
                return datetime.strptime(change.get("at", ""), TIME_FORMAT).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                return None
    return None


def evidence_problem(root: Path, value: str, started: float | None) -> str | None:
    pure = PurePosixPath(value)
    if not value or "\\" in value or value.startswith("~") or pure.is_absolute() or ".." in pure.parts:
        return "the evidence path must be relative, inside the workspace and without '..'"
    normalized = PurePosixPath(os.path.normpath(value))
    full = root / normalized
    if not full.resolve().is_relative_to(root):
        return "the evidence path leaves the workspace through a link"
    if not full.is_file() or full.stat().st_size == 0:
        return "the evidence path is not a nonempty regular file"
    relative = full.resolve().relative_to(root)
    if any(relative == night_file or normalized == night_file for night_file in NIGHT_FILES) \
            or relative.parts[:len(OWN_DIR.parts)] == OWN_DIR.parts:
        return "a night settings, ticket, estimate, queue or status file is not evidence of a finished ticket"
    if started is not None and full.stat().st_mtime < started - CHANGE_TOLERANCE_SECONDS:
        return "the evidence file was last changed before the ticket started"
    return None


def command_status(root: Path) -> int:
    items, digest = read_queue(root)
    status = read_status(root, digest, {item["id"] for item in items})
    rows = []
    for item in items:
        entry = status["tickets"].get(item["id"], {})
        rows.append({"position": item.get("position"), "id": item["id"], "status": state_of(status, item["id"]),
                     **({"waits_for": entry["waits_for"]} if "waits_for" in entry else {})})
    counts = {name: sum(1 for row in rows if row["status"] == name) for name in STATUSES}
    return emit({"record_type": "night_queue_state/v1", "queue": QUEUE.as_posix(), "queue_sha256": digest,
                 "status_file": STATUS.as_posix(), "tickets": rows, "counts": counts,
                 "in_progress": [row["id"] for row in rows if row["status"] == "in_progress"],
                 "next": next_ticket(items, status)}, 0)


def command_mark(root: Path, options) -> int:
    items, digest = read_queue(root)
    ids = {item["id"] for item in items}
    if not TICKET_ID.fullmatch(options.ticket) or options.ticket not in ids:
        raise Refused(f"ticket {options.ticket} is not in {QUEUE.as_posix()}")
    status = read_status(root, digest, ids)
    ticket_id, target = options.ticket, options.to
    current = state_of(status, ticket_id)
    entry = status["tickets"].get(ticket_id, {"status": "queued", "changes": []})
    change = {"from": current, "to": target, "at": now(), "by": "plan-night-queue mark"}
    item = next(value for value in items if value["id"] == ticket_id)
    try:
        if target == "in_progress":
            if current != "queued":
                raise NotAllowed(f"{ticket_id} is {current}; only a queued ticket can start")
            depends = item.get("depends_on") if isinstance(item.get("depends_on"), list) else []
            unfinished = [dep for dep in depends if dep not in ids or state_of(status, dep) != "done"]
            if unfinished:
                raise NotAllowed(f"{ticket_id} depends on {', '.join(unfinished)}, which is not done")
            busy = [other for other in ids if other != ticket_id and state_of(status, other) == "in_progress"]
            if busy:
                raise NotAllowed(f"{', '.join(sorted(busy))} is in progress; finish or release it first")
        elif target == "done":
            if current != "in_progress":
                raise NotAllowed(f"{ticket_id} is {current}; only a ticket in progress can be done")
            if not options.evidence:
                raise Refused("a done move needs --evidence with a file that proves the ticket is finished")
            problem = evidence_problem(root, options.evidence, started_at(entry))
            if problem:
                raise NotAllowed(problem)
            evidence = PurePosixPath(os.path.normpath(options.evidence)).as_posix()
            change["evidence"] = entry["evidence"] = evidence
        else:
            if current not in ("in_progress", "blocked", "waiting"):
                raise NotAllowed(f"{ticket_id} is {current}; only a ticket in progress, blocked or waiting goes back")
            if not options.reason or not options.reason.strip() or len(options.reason) > 500:
                raise Refused("a move back to queued needs --reason with a sentence of at most 500 characters")
            if current == "waiting" and state_of(status, entry.get("waits_for", "")) in ("blocked", "waiting"):
                raise NotAllowed(f"{ticket_id} still waits for {entry.get('waits_for')}, which is not resolved")
            change["reason"] = " ".join(options.reason.split())
            for key in ("blocker", "blocked_at", "waits_for"):
                entry.pop(key, None)
    except NotAllowed as error:
        return emit({"record_type": "night_queue_mark/v1", "moved": False, "ticket": ticket_id, "from": current,
                     "to": target, "reason": str(error)}, 1)
    entry["status"] = target
    entry.setdefault("changes", []).append(change)
    status["tickets"][ticket_id] = entry
    status_path = inside(root, STATUS)
    write_status(status_path, status)
    return emit({"record_type": "night_queue_mark/v1", "moved": True, "ticket": ticket_id, "from": current,
                 "to": target, "status_file": STATUS.as_posix(), "next": next_ticket(items, status)}, 0)


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=".", help="workspace root; every path stays under it")
    parser = argparse.ArgumentParser(description="Order tonight's tickets into a queue within the budget.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gaps", parents=[shared], help="list tickets that still need or must fix an estimate")
    commands.add_parser("plan", parents=[shared], help="write .baltor/night/queue.json once")
    commands.add_parser("status", parents=[shared], help="print every ticket's status and the next ticket")
    mark = commands.add_parser("mark", parents=[shared], help="move one ticket to in_progress, done or queued")
    mark.add_argument("--ticket", required=True)
    mark.add_argument("--to", required=True, choices=("in_progress", "done", "queued"))
    mark.add_argument("--evidence", help="for done: a file changed after the ticket started")
    mark.add_argument("--reason", help="for queued: why the ticket goes back to the queue")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        handlers = {"gaps": command_gaps, "plan": command_plan, "status": command_status}
        if options.command == "mark":
            return command_mark(root, options)
        return handlers[options.command](root)
    except (Refused, OSError) as error:
        return emit({"record_type": "night_queue_refused/v1", "refused": True, "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())

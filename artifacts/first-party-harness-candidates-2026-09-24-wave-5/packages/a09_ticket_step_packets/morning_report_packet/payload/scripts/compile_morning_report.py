"""Effects: reads the night's handoff, activity, queue and notes files, writes the two report files named in the step input.

Compile the handoffs and activity logs of one night into a morning report.

Usage, from the workspace root:

    python3 -I -B .baltor/morning-report-packet/scripts/compile_morning_report.py \
        --input .baltor/step/input.json

Rules the script applies, so that no model has to:

- The newest handoff of a step sets its section; older ones are listed as superseded.
- A step is complete only when its handoff says complete, it has at least one
  claim, and the evidence of every claim is an existing file in the workspace.
  A folder is not evidence, and neither is a handoff or the queue, notes or
  report file of this night. Otherwise the step is listed as unfinished and
  its unsupported claims are listed.
- A blocked handoff stays blocked; blocker evidence follows the same rules.
- A step seen in the activity logs without any handoff is unfinished.
- A queued ticket that no handoff names is unfinished.
- Each ticket gets one line: complete only when the handoff of its final
  step, which the queue names in final_step_id, is complete; blocked when one
  of its steps is blocked; unfinished otherwise, also when the queue names no
  final step for it.
- Notes written by the report step appear only when their evidence is an
  existing file that is not the notes or a report file.
- Files that cannot be read are listed, never skipped in silence. Text and
  paths are cut to the lengths the report contract allows.

The queue is an object with a tickets list of {ticket_id, final_step_id} or a
night_queue/v1 record with an items list of {id, final_step_id}; final_step_id
is optional in both.

The script writes the JSON report and its Markdown rendering through new
temporary files that it renames into place, replacing earlier drafts, and
prints one JSON object. It never changes a handoff, log, queue or evidence
file.

Exit status: 0 when the report was written, every claim has evidence and every
record was read; 1 when the report was written but lists claims without
evidence or records that could not be read; 2 when the input was refused and
nothing was written. Exit 0 does not mean that every ticket finished; the
ticket counts say that.

Python 3.10 or later, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

INPUT_TYPE = "morning_report_input/v1"
HANDOFF_TYPE = "night_step_handoff/v1"
REPORT_TYPE = "night_morning_report/v1"
QUEUE_RECORD = "night_queue/v1"
INPUT_FIELDS = frozenset({"record_type", "night_id", "handoff_dir", "activity_log_dir", "activity_fields",
                          "queue_path", "report_json_path", "report_markdown_path", "notes_path"})
HANDOFF_FIELDS = frozenset({"record_type", "step_id", "ticket_id", "status", "written_at", "revision", "files",
                            "claims", "blocker", "first_action", "remaining_actions", "done_when"})
STATUSES = ("complete", "blocked", "unfinished")
MAX_INPUT_BYTES = 1024 * 1024
MAX_HANDOFF_FILES = 2000
MAX_LOG_FILES = 500
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX_NOTES = 20
MAX_PATH = 400
MAX_PROBLEM = 600
MARKER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
REVISION = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
STEP_FOLDER = ".baltor"
PACKET_FOLDER = ".baltor/step"
REASONS = {
    "handoff_status_unfinished": "the handoff says the work is unfinished",
    "complete_without_evidence": "the handoff says complete, but not every claim has usable evidence",
    "handoff_invalid": "the handoff file does not match night_step_handoff/v1",
    "activity_without_handoff": "the activity log shows work on this step, but no handoff exists",
    "no_handoff_found": "the ticket was queued, but no step left a handoff for it",
}
TICKET_REASONS = {
    "final_step_not_complete": "its final step {final} has no complete handoff",
    "final_step_not_declared": "the queue names no final step for it, so the report cannot tell that it finished",
    "no_handoff_found": "no step left a handoff for it",
    "step_blocked": "a step is blocked and waits for a person",
}
EVIDENCE_PROBLEMS = {
    "no_evidence_given": "no evidence path was given",
    "evidence_missing": "the file was not found",
    "evidence_outside_workspace": "the path leaves the workspace",
    "evidence_path_invalid": "the path is not a valid relative path to a file",
    "evidence_is_a_folder": "the path is a folder, not a file",
    "evidence_is_a_night_record": "the path is a handoff, or the queue, notes or report file of this night",
}


class Refused(Exception):
    """The input cannot be used. Nothing was written."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bounded(value, limit: int) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit - 3] + "..."


def parse_time(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        moment = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def read_limited(path: Path, limit: int):
    """Return (bytes, None) or (None, problem) without raising."""
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as error:
        return None, f"cannot be read: {type(error).__name__}"
    if len(data) > limit:
        return None, f"larger than {limit} bytes; not read"
    return data, None


def parse_json(data: bytes):
    """Return (value, None) or (None, problem) for strict JSON without markers."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key {key!r}")
            value[key] = item
        return value

    def no_constant(word):
        raise ValueError(f"nonstandard number {word}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "not UTF-8 text"
    if MARKER.search(text):
        return None, "still holds a marker in double braces"
    try:
        return json.loads(text, object_pairs_hook=unique, parse_constant=no_constant), None
    except ValueError as error:
        return None, f"not strict JSON: {str(error)[:200]}"


def confined(root: Path, value, name: str) -> Path:
    """Return the path for a workspace-relative value, refusing every way out of the root."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH or "\x00" in value or "\\" in value:
        raise Refused(f"{name} must be a relative path of at most {MAX_PATH} characters")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith("~") or ".." in pure.parts:
        raise Refused(f"{name} must stay inside the workspace: {value}")
    path = root.joinpath(*pure.parts)
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise Refused(f"{name} cannot be resolved, for example because two symbolic links point at each other: {value}") from None
    if resolved != root and root not in resolved.parents:
        raise Refused(f"{name} leaves the workspace through a symbolic link: {value}")
    return path


def in_folder(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "/")


def evidence_problem(root: Path, value, records) -> str | None:
    """Why value cannot support a claim, or None. records holds the resolved files and folders it may not name."""
    if value is None:
        return "no_evidence_given"
    if not isinstance(value, str) or not value or len(value) > MAX_PATH or "\x00" in value or "\\" in value:
        return "evidence_path_invalid"
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith("~") or ".." in pure.parts:
        return "evidence_outside_workspace"
    try:
        resolved = root.joinpath(*pure.parts).resolve()
    except (OSError, RuntimeError):
        return "evidence_path_invalid"
    if resolved != root and root not in resolved.parents:
        return "evidence_outside_workspace"
    files, folders = records
    if resolved in files or any(folder == resolved or folder in resolved.parents for folder in folders):
        return "evidence_is_a_night_record"
    if not resolved.exists():
        return "evidence_missing"
    if resolved.is_dir():
        return "evidence_is_a_folder"
    if not resolved.is_file():
        return "evidence_path_invalid"
    return None


def text_or_none(value, limit: int) -> bool:
    return value is None or (isinstance(value, str) and 0 < len(value.strip()) and len(value) <= limit)


def handoff_problems(handoff) -> list:
    """Every way the value differs from night_step_handoff/v1; an empty list means it is usable."""
    if not isinstance(handoff, dict):
        return ["the file is not one JSON object"]
    if set(handoff) != HANDOFF_FIELDS:
        missing, unexpected = sorted(HANDOFF_FIELDS - set(handoff)), sorted(set(handoff) - HANDOFF_FIELDS)
        return [f"fields differ: missing {missing}, unexpected {len(unexpected)} fields such as {unexpected[:3]}"]
    problems = []
    if handoff["record_type"] != HANDOFF_TYPE:
        problems.append(f"record_type must be {HANDOFF_TYPE}")
    if not isinstance(handoff["step_id"], str) or not IDENTIFIER.match(handoff["step_id"]):
        problems.append("step_id must be an identifier of at most 64 characters")
    if handoff["ticket_id"] is not None and (not isinstance(handoff["ticket_id"], str)
                                             or not IDENTIFIER.match(handoff["ticket_id"])):
        problems.append("ticket_id must be null or an identifier")
    if handoff["status"] not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")
    if parse_time(handoff["written_at"]) is None:
        problems.append("written_at must be an ISO 8601 time with a zone")
    if handoff["revision"] is not None and (not isinstance(handoff["revision"], str)
                                            or not REVISION.match(handoff["revision"])):
        problems.append("revision must be null or a full commit id")
    files = handoff["files"]
    if not isinstance(files, list) or len(files) > 500 or any(
            not isinstance(item, dict) or set(item) != {"path", "sha256"} or not isinstance(item["path"], str)
            or (item["sha256"] is not None and (not isinstance(item["sha256"], str) or not DIGEST.match(item["sha256"])))
            for item in files):
        problems.append("files must be a list of objects with path and sha256")
    claims = handoff["claims"]
    if not isinstance(claims, list) or len(claims) > 50 or any(
            not isinstance(item, dict) or set(item) != {"text", "evidence"} or item["text"] is None
            or not text_or_none(item["text"], 500) or not text_or_none(item["evidence"], MAX_PATH) for item in claims):
        problems.append("claims must be a list of at most 50 objects with text and evidence")
    blocker = handoff["blocker"]
    if blocker is not None and (not isinstance(blocker, dict) or set(blocker) != {"reason", "question", "evidence"}
                                or blocker["reason"] is None or not text_or_none(blocker["reason"], 500)
                                or not text_or_none(blocker["question"], 500)
                                or not text_or_none(blocker["evidence"], MAX_PATH)):
        problems.append("blocker must be null or an object with reason, question and evidence")
    if not text_or_none(handoff["first_action"], 1000):
        problems.append("first_action must be null or text of at most 1000 characters")
    for name, count, limit in (("remaining_actions", 50, 1000), ("done_when", 20, 500)):
        value = handoff[name]
        if not isinstance(value, list) or len(value) > count or any(
                item is None or not text_or_none(item, limit) for item in value):
            problems.append(f"{name} must be a list of at most {count} texts")
    if handoff["status"] == "blocked" and blocker is None:
        problems.append("a blocked handoff names its blocker")
    if handoff["status"] == "unfinished" and handoff["first_action"] is None:
        problems.append("an unfinished handoff names its first_action")
    return problems


def clean(value, limit: int = 500):
    return None if value is None else " ".join(str(value).split())[:limit]


def load_step(root: Path, input_value: str) -> dict:
    data, problem = read_limited(confined(root, input_value, "--input"), MAX_INPUT_BYTES)
    if problem:
        raise Refused(f"the step input is {problem}")
    step, problem = parse_json(data)
    if problem:
        prefix = "unrendered_step_input: " if "marker" in problem else ""
        raise Refused(f"{prefix}the step input is {problem}")
    if not isinstance(step, dict) or step.get("record_type") != INPUT_TYPE:
        raise Refused(f"the step input must be one object with record_type {INPUT_TYPE}")
    if set(step) != INPUT_FIELDS:
        raise Refused(f"the step input fields differ: missing {sorted(INPUT_FIELDS - set(step))}, "
                      f"unexpected {sorted(set(step) - INPUT_FIELDS)}")
    if not isinstance(step["night_id"], str) or not IDENTIFIER.match(step["night_id"]):
        raise Refused("night_id must be an identifier of at most 64 characters, such as 2026-09-23")
    fields = step["activity_fields"]
    if not isinstance(fields, dict) or set(fields) != {"time", "step_id"} or any(
            not isinstance(value, str) or not value or len(value) > 64 for value in fields.values()):
        raise Refused("activity_fields must name the time and step_id fields of an activity line")
    handoff_dir = confined(root, step["handoff_dir"], "handoff_dir")
    if not handoff_dir.is_dir():
        raise Refused("handoff_dir does not name an existing folder")
    for name in ("activity_log_dir", "queue_path"):
        if step[name] is not None:
            confined(root, step[name], name)
    outputs = {}
    for name in ("report_json_path", "report_markdown_path", "notes_path"):
        value = step[name]
        path = confined(root, value, name)
        if not in_folder(value, STEP_FOLDER) or in_folder(value, PACKET_FOLDER):
            raise Refused(f"{name} must be inside .baltor/ and outside .baltor/step/, which the step only reads")
        if handoff_dir.resolve() in path.resolve().parents:
            raise Refused(f"{name} must not be inside handoff_dir, or the next run would read it as a handoff")
        if path.is_dir():
            raise Refused(f"{name} names a folder")
        outputs[name] = path.resolve()
    if len(set(outputs.values())) != 3:
        raise Refused("report_json_path, report_markdown_path and notes_path must be three different files")
    return step


def night_records(root: Path, step: dict):
    """The resolved files and folders that cannot support a handoff claim, and those that cannot support a note."""
    outputs = {confined(root, step[name], name).resolve()
               for name in ("report_json_path", "report_markdown_path", "notes_path")}
    queue = {confined(root, step["queue_path"], "queue_path").resolve()} if step["queue_path"] else set()
    handoffs = [confined(root, step["handoff_dir"], "handoff_dir").resolve()]
    return (outputs | queue, handoffs), (outputs, [])


def files_below(root: Path, folder: Path, suffix: str, limit: int, problems: list) -> list:
    found = []
    for path in sorted(folder.rglob("*" + suffix)):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            problems.append({"path": relative, "problem": "a symbolic link; not read"})
            continue
        if not path.is_file():
            continue
        if len(relative) > MAX_PATH:
            problems.append({"path": relative, "problem": f"the path is longer than {MAX_PATH} characters; not read"})
            continue
        if len(found) == limit:
            problems.append({"path": relative, "problem": f"more than {limit} files; the rest were not read"})
            break
        found.append(path)
    return found


def read_handoffs(root: Path, step: dict, problems: list):
    valid, invalid = [], {}
    folder = confined(root, step["handoff_dir"], "handoff_dir")
    paths = files_below(root, folder, ".json", MAX_HANDOFF_FILES, problems)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        data, problem = read_limited(path, MAX_INPUT_BYTES)
        value = None
        if problem is None:
            value, problem = parse_json(data)
        if problem is None:
            issues = handoff_problems(value)
            problem = "not a night_step_handoff/v1 record: " + "; ".join(issues[:3]) if issues else None
        if problem is None:
            valid.append((relative, value))
            continue
        problems.append({"path": relative, "problem": problem})
        if isinstance(value, dict) and isinstance(value.get("step_id"), str) and IDENTIFIER.match(value["step_id"]):
            ticket = value.get("ticket_id")
            invalid.setdefault(value["step_id"], (relative, ticket if isinstance(ticket, str)
                                                  and IDENTIFIER.match(ticket) else None))
    return valid, invalid, len(paths)


def read_activity(root: Path, step: dict, problems: list):
    activity, count = {}, 0
    if step["activity_log_dir"] is None:
        return activity, count
    folder = confined(root, step["activity_log_dir"], "activity_log_dir")
    if not folder.is_dir():
        problems.append({"path": step["activity_log_dir"], "problem": "the activity log folder does not exist"})
        return activity, count
    time_field, step_field = step["activity_fields"]["time"], step["activity_fields"]["step_id"]
    for path in files_below(root, folder, ".jsonl", MAX_LOG_FILES, problems):
        count += 1
        relative = path.relative_to(root).as_posix()
        data, problem = read_limited(path, MAX_LOG_BYTES)
        if problem:
            problems.append({"path": relative, "problem": problem})
            continue
        unreadable = 0
        for line in data.split(b"\n"):
            if not line.strip():
                continue
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                unreadable += 1
                continue
            step_id = value.get(step_field) if isinstance(value, dict) else None
            if not isinstance(step_id, str) or not IDENTIFIER.match(step_id):
                unreadable += 1
                continue
            entry = activity.setdefault(step_id, {"step_id": step_id, "events": 0, "first_time": None,
                                                  "last_time": None, "times_not_read": 0, "log": relative})
            entry["events"] += 1
            moment = parse_time(value.get(time_field))
            if moment is None:
                entry["times_not_read"] += 1
                continue
            if entry["first_time"] is None or moment < parse_time(entry["first_time"]):
                entry["first_time"] = value[time_field]
            if entry["last_time"] is None or moment > parse_time(entry["last_time"]):
                entry["last_time"] = value[time_field]
        if unreadable:
            problems.append({"path": relative, "problem": f"{unreadable} lines could not be read as activity records"})
    return activity, count


def read_queue(root: Path, step: dict, problems: list) -> dict:
    """Map each queued ticket to its final step, or to None when the queue names none, in queue order."""
    if step["queue_path"] is None:
        return {}
    path = confined(root, step["queue_path"], "queue_path")
    data, problem = read_limited(path, MAX_INPUT_BYTES)
    value = None
    if problem is None:
        value, problem = parse_json(data)
    entries, key = None, None
    if problem is None and isinstance(value, dict):
        if isinstance(value.get("tickets"), list):
            entries, key = value["tickets"], "ticket_id"
        elif value.get("record_type") == QUEUE_RECORD and isinstance(value.get("items"), list):
            entries, key = value["items"], "id"
    if problem is None and (entries is None or any(
            not isinstance(item, dict) or not isinstance(item.get(key), str) or not IDENTIFIER.match(item[key])
            or not (item.get("final_step_id") is None or (isinstance(item["final_step_id"], str)
                                                         and IDENTIFIER.match(item["final_step_id"])))
            for item in entries)):
        problem = ("must be an object whose tickets list holds objects with a ticket_id, or a night_queue/v1 "
                   "record whose items hold an id; final_step_id is optional and names a step")
    if problem:
        problems.append({"path": step["queue_path"], "problem": problem})
        return {}
    queued = {}
    for item in entries:
        queued.setdefault(item[key], item.get("final_step_id"))
    return queued


def read_notes(root: Path, step: dict, problems: list, unsupported: list, records) -> list:
    path = confined(root, step["notes_path"], "notes_path")
    if not path.is_file():
        return []
    data, problem = read_limited(path, MAX_INPUT_BYTES)
    value = None
    if problem is None:
        value, problem = parse_json(data)
    if problem is None and (not isinstance(value, list) or len(value) > MAX_NOTES or any(
            not isinstance(item, dict) or set(item) != {"text", "evidence"} or item["text"] is None
            or not text_or_none(item["text"], 500) for item in value)):
        problem = f"must be a list of at most {MAX_NOTES} objects with text and evidence"
    if problem:
        problems.append({"path": step["notes_path"], "problem": problem})
        return []
    notes = []
    for item in value:
        issue = evidence_problem(root, item["evidence"], records)
        if issue:
            unsupported.append({"source": "notes", "step_id": None, "ticket_id": None, "text": clean(item["text"]),
                                "evidence": bounded(item["evidence"], MAX_PATH) if isinstance(item["evidence"], str)
                                else None, "problem": issue, "handoff": None})
        else:
            notes.append({"text": clean(item["text"]), "evidence": item["evidence"]})
    return notes


def ticket_rollup(queued: dict, newest: dict, invalid: dict, sections: dict) -> list:
    """One line per ticket named by the queue or by a handoff."""
    steps_of = {}
    for step_id, (_, _, handoff) in newest.items():
        if handoff["ticket_id"] is not None:
            steps_of.setdefault(handoff["ticket_id"], set()).add(step_id)
    for step_id, (_, ticket) in invalid.items():
        if ticket is not None and step_id not in newest:
            steps_of.setdefault(ticket, set()).add(step_id)
    rows = []
    for ticket in sorted(set(queued) | set(steps_of)):
        steps = sorted(steps_of.get(ticket, set()))
        final = queued.get(ticket)
        if final is not None and sections.get(final) == "complete":
            status, reason = "complete", None
        elif any(sections.get(step_id) == "blocked" for step_id in steps):
            status, reason = "blocked", "step_blocked"
        elif not steps:
            status, reason = "unfinished", "no_handoff_found"
        elif final is None:
            status, reason = "unfinished", "final_step_not_declared"
        else:
            status, reason = "unfinished", "final_step_not_complete"
        rows.append({"ticket_id": ticket, "status": status, "reason": reason, "final_step_id": final,
                     "steps": [{"step_id": step_id, "section": sections.get(step_id, "unfinished")}
                               for step_id in steps]})
    return rows


def compile_report(root: Path, step: dict) -> dict:
    problems, unsupported = [], []
    claim_records, note_records = night_records(root, step)
    valid, invalid, handoff_files = read_handoffs(root, step, problems)
    by_step = {}
    for relative, handoff in valid:
        by_step.setdefault(handoff["step_id"], []).append((parse_time(handoff["written_at"]), relative, handoff))
    newest, superseded = {}, []
    for step_id, items in by_step.items():
        items.sort(key=lambda item: (item[0], item[1]))
        newest[step_id] = items[-1]
        superseded += [{"step_id": step_id, "handoff": relative, "written_at": handoff["written_at"]}
                       for _, relative, handoff in items[:-1]]
    complete, blocked, unfinished, sections = [], [], [], {}
    for step_id, (_, relative, handoff) in newest.items():
        ticket, supported = handoff["ticket_id"], []
        for claim in handoff["claims"]:
            issue = evidence_problem(root, claim["evidence"], claim_records)
            if issue:
                unsupported.append({"source": "handoff", "step_id": step_id, "ticket_id": ticket,
                                    "text": clean(claim["text"]), "evidence": claim["evidence"], "problem": issue,
                                    "handoff": relative})
            else:
                supported.append({"text": clean(claim["text"]), "evidence": claim["evidence"]})
        base = {"step_id": step_id, "ticket_id": ticket, "handoff": relative}
        if handoff["status"] == "complete" and handoff["claims"] and len(supported) == len(handoff["claims"]):
            complete.append({**base, "claims": supported})
            sections[step_id] = "complete"
        elif handoff["status"] == "blocked":
            blocker = handoff["blocker"]
            issue = None if blocker["evidence"] is None else evidence_problem(root, blocker["evidence"], claim_records)
            if issue:
                unsupported.append({"source": "handoff", "step_id": step_id, "ticket_id": ticket,
                                    "text": clean(blocker["reason"]), "evidence": blocker["evidence"],
                                    "problem": issue, "handoff": relative})
            blocked.append({**base, "reason": clean(blocker["reason"]), "question": clean(blocker["question"]),
                            "evidence": blocker["evidence"],
                            "evidence_found": None if blocker["evidence"] is None else issue is None,
                            "claims": supported})
            sections[step_id] = "blocked"
        else:
            reason = "complete_without_evidence" if handoff["status"] == "complete" else "handoff_status_unfinished"
            unfinished.append({**base, "source": "handoff", "reason": reason,
                               "first_action": clean(handoff["first_action"], 1000), "evidence": relative,
                               "claims": supported})
            sections[step_id] = "unfinished"
    for step_id, (relative, ticket) in sorted(invalid.items()):
        if step_id not in newest:
            unfinished.append({"step_id": step_id, "ticket_id": ticket, "handoff": relative, "source": "handoff",
                               "reason": "handoff_invalid", "first_action": None, "evidence": relative,
                               "claims": []})
            sections[step_id] = "unfinished"
    activity, activity_files = read_activity(root, step, problems)
    for step_id, entry in activity.items():
        if step_id not in newest and step_id not in invalid:
            unfinished.append({"step_id": step_id, "ticket_id": None, "handoff": None, "source": "activity_only",
                               "reason": "activity_without_handoff", "first_action": None, "evidence": entry["log"],
                               "claims": []})
    named = {handoff["ticket_id"] for _, _, handoff in newest.values()} | {ticket for _, ticket in invalid.values()}
    queued = read_queue(root, step, problems)
    for ticket in queued:
        if ticket not in named:
            unfinished.append({"step_id": None, "ticket_id": ticket, "handoff": None, "source": "queue_only",
                               "reason": "no_handoff_found", "first_action": None, "evidence": step["queue_path"],
                               "claims": []})
    notes = read_notes(root, step, problems, unsupported, note_records)
    tickets = ticket_rollup(queued, newest, invalid, sections)

    def order(item):
        return (item.get("ticket_id") is None, item.get("ticket_id") or "", item.get("step_id") or "",
                item.get("source") or "")

    for bucket in (complete, blocked, unfinished, unsupported):
        bucket.sort(key=order)
    superseded.sort(key=lambda item: (item["step_id"], item["handoff"]))
    problems = sorted(({"path": bounded(item["path"], MAX_PATH), "problem": bounded(item["problem"], MAX_PROBLEM)}
                       for item in problems), key=lambda item: (item["path"], item["problem"]))
    return {"record_type": REPORT_TYPE, "night_id": step["night_id"], "compiled_at": utc_now(),
            "sources": {"handoff_dir": step["handoff_dir"], "handoff_files": handoff_files,
                        "activity_log_dir": step["activity_log_dir"], "activity_files": activity_files,
                        "queue_path": step["queue_path"], "notes_path": step["notes_path"]},
            "counts": {"tickets_complete": sum(row["status"] == "complete" for row in tickets),
                       "tickets_blocked": sum(row["status"] == "blocked" for row in tickets),
                       "tickets_unfinished": sum(row["status"] == "unfinished" for row in tickets),
                       "complete": len(complete), "blocked": len(blocked), "unfinished": len(unfinished),
                       "unsupported_claims": len(unsupported), "problems": len(problems)},
            "tickets": tickets, "complete": complete, "blocked": blocked, "unfinished": unfinished,
            "unsupported_claims": unsupported, "notes": notes, "superseded": superseded,
            "activity": [activity[key] for key in sorted(activity)], "problems": problems}


def shown(value) -> str:
    """Free text for Markdown: one line, and no raw angle bracket that could hide text in a rendered view."""
    return clean(value, 1000).replace("<", "&lt;")


def code(path) -> str:
    return "`" + str(path).replace("`", "'") + "`"


def label(item) -> str:
    ticket, step_id = item.get("ticket_id"), item.get("step_id")
    if ticket and step_id:
        return f"{shown(ticket)}, step {shown(step_id)}"
    return f"step {shown(step_id)}" if step_id else f"{shown(ticket)}, no step"


def ticket_line(row) -> str:
    steps = ", ".join(f"{shown(item['step_id'])} ({item['section']})" for item in row["steps"]) or "none"
    if row["status"] == "complete":
        state = f"complete; its final step {shown(row['final_step_id'])} is complete"
    elif row["status"] == "blocked":
        state = f"blocked: {TICKET_REASONS['step_blocked']}"
    else:
        state = "unfinished: " + TICKET_REASONS[row["reason"]].format(final=shown(row["final_step_id"] or ""))
    return f"- {shown(row['ticket_id'])}: {state}. Steps: {steps}."


def render_markdown(report: dict) -> str:
    sources, counts = report["sources"], report["counts"]
    lines = [f"# Morning report for night {shown(report['night_id'])}", "",
             f"Compiled at {report['compiled_at']} by compile_morning_report.py. Handoff files read: "
             f"{sources['handoff_files']}. Activity log files read: {sources['activity_files']}. The newest handoff "
             "of a step sets its section. A claim counts only when its evidence is an existing file that is not a "
             "handoff or a queue, notes or report file. A ticket is complete only when its final step is.", "",
             "## Summary", "",
             f"- Tickets complete: {counts['tickets_complete']}",
             f"- Tickets blocked, waiting for a person: {counts['tickets_blocked']}",
             f"- Tickets unfinished: {counts['tickets_unfinished']}",
             f"- Steps complete: {counts['complete']}", f"- Steps blocked: {counts['blocked']}",
             f"- Steps unfinished: {counts['unfinished']}",
             f"- Claims without evidence: {counts['unsupported_claims']}",
             f"- Records that could not be read: {counts['problems']}", "", "## Tickets", ""]
    lines.extend([ticket_line(row) for row in report["tickets"]] or ["None."])
    lines.append("")

    def section(title, items, render):
        lines.extend([f"## {title}", ""])
        if not items:
            lines.extend(["None.", ""])
        for item in items:
            render(item)

    def done_so_far(item):
        for claim in item["claims"]:
            lines.append(f"- Done: {shown(claim['text'])} Evidence: {code(claim['evidence'])}")

    def complete_item(item):
        lines.extend([f"### {label(item)}", ""])
        for claim in item["claims"]:
            lines.append(f"- {shown(claim['text'])} Evidence: {code(claim['evidence'])}")
        lines.extend([f"- Handoff: {code(item['handoff'])}", ""])

    def blocked_item(item):
        lines.extend([f"### {label(item)}", "", f"- Reason: {shown(item['reason'])}"])
        if item["question"]:
            lines.append(f"- Question for a person: {shown(item['question'])}")
        if item["evidence"] is None:
            lines.append("- Evidence: none given")
        else:
            lines.append(f"- Evidence: {code(item['evidence'])}" + ("" if item["evidence_found"] else " (not usable)"))
        done_so_far(item)
        lines.extend([f"- Handoff: {code(item['handoff'])}", ""])

    def unfinished_item(item):
        lines.extend([f"### {label(item)}", "", f"- Why: {REASONS[item['reason']]}"])
        if item["first_action"]:
            lines.append(f"- First action when work resumes: {shown(item['first_action'])}")
        done_so_far(item)
        lines.extend([f"- Evidence: {code(item['evidence'])}", ""])

    section("Complete steps", report["complete"], complete_item)
    section("Blocked steps, waiting for a person", report["blocked"], blocked_item)
    section("Unfinished steps", report["unfinished"], unfinished_item)
    lines.extend(["## Claims without evidence", ""])
    for item in report["unsupported_claims"]:
        where = "report step note" if item["source"] == "notes" else label(item)
        evidence = "no path" if item["evidence"] is None else code(item["evidence"])
        lines.append(f"- {where}: {shown(item['text'])} ({evidence}: {EVIDENCE_PROBLEMS[item['problem']]})")
    lines.extend(["None.", ""] if not report["unsupported_claims"] else [""])
    lines.extend(["## Notes from the report step", ""])
    lines.extend([f"- {shown(note['text'])} Evidence: {code(note['evidence'])}" for note in report["notes"]] or ["None."])
    lines.extend(["", "## Activity by step", ""])
    lines.extend([f"- {shown(entry['step_id'])}: events {entry['events']}, first {entry['first_time'] or 'unknown'}, "
                  f"last {entry['last_time'] or 'unknown'}. Log: {code(entry['log'])}" for entry in report["activity"]]
                 or ["None."])
    lines.extend(["", "## Superseded handoffs", ""])
    lines.extend([f"- {shown(item['step_id'])}: {code(item['handoff'])}, written {shown(item['written_at'])}"
                  for item in report["superseded"]] or ["None."])
    lines.extend(["", "## Records that could not be read", ""])
    lines.extend([f"- {code(item['path'])}: {shown(item['problem'])}" for item in report["problems"]] or ["None."])
    return "\n".join(lines) + "\n"


def replace_file(path: Path, text: str) -> None:
    """Write text to a new temporary file beside path, then rename it over path; a link at path is replaced, not followed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".partial")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compile one night's handoffs and activity logs into a report.")
    parser.add_argument("--input", default=".baltor/step/input.json", help="workspace-relative step input")
    parser.add_argument("--root", default=".", help="the workspace root")
    options = parser.parse_args(argv)
    try:
        try:
            root = Path(options.root).resolve(strict=True)
        except OSError:
            raise Refused("--root does not exist") from None
        if not root.is_dir():
            raise Refused("--root is not a folder")
        step = load_step(root, options.input)
        report = compile_report(root, step)
    except Refused as refusal:
        print(json.dumps({"verdict": "refused", "reason": str(refusal)}, indent=1))
        return 2
    replace_file(confined(root, step["report_json_path"], "report_json_path"),
                 json.dumps(report, indent=1, ensure_ascii=True) + "\n")
    replace_file(confined(root, step["report_markdown_path"], "report_markdown_path"), render_markdown(report))
    counts = report["counts"]
    print(json.dumps({"verdict": "written", "report_json_path": step["report_json_path"],
                      "report_markdown_path": step["report_markdown_path"], "counts": counts,
                      "unfinished_tickets": [row["ticket_id"] for row in report["tickets"]
                                             if row["status"] == "unfinished"][:50],
                      "problems": report["problems"][:20], "unsupported_claims": report["unsupported_claims"][:20]},
                     indent=1))
    return 0 if counts["unsupported_claims"] == 0 and counts["problems"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

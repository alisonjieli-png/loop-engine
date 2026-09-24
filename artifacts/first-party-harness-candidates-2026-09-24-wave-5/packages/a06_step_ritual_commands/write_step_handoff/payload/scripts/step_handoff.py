"""Create and check a step handoff note and write its night_step_handoff/v1 record. Effects: reads files under --root; init creates one new note under .baltor/handoffs/; a passing check writes or replaces the JSON record beside that note; no network, no subprocess, no model call.

Usage from the workspace root:

    python3 -I -B .baltor/write-step-handoff/scripts/step_handoff.py init  --root . [--step-id ID]
    python3 -I -B .baltor/write-step-handoff/scripts/step_handoff.py check --root . [--step-id ID] [--ticket ID]

init reads .baltor/step/task.json for the step id and objective when it exists and
creates .baltor/handoffs/<step-id>.md from a fixed template. It never replaces a note.

check reads the note and lists every finding. Evidence for a Done line is a regular
file inside the workspace that is not a step input (.baltor/step/), not a handoff
(.baltor/handoffs/), not a file of this command and, when .baltor/step/task.json
exists, was changed after that file was placed. Only a note without findings gets
its record, .baltor/handoffs/<step-id>.json, in the night_step_handoff/v1 shape:
complete stays complete, partial becomes unfinished and blocked stays blocked.

Each run prints one JSON object. Exit status: 0 success, 1 check failed, 2 refused input.
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

HANDOFF_DIR = Path(".baltor") / "handoffs"
STEP_DIR = Path(".baltor") / "step"
TASK_FILE = STEP_DIR / "task.json"
QUEUE_FILE = Path(".baltor") / "night" / "queue.json"
OWN_DIR = Path(".baltor") / "write-step-handoff"
NOT_EVIDENCE = (("step input", STEP_DIR.parts), ("handoff note or record", HANDOFF_DIR.parts),
                ("file of this command", OWN_DIR.parts))
RECORD_TYPE = "night_step_handoff/v1"
NOTE_MAX_BYTES = 256 * 1024
JSON_MAX_BYTES = 4 * 1024 * 1024
DIGEST_MAX_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_WORDS = 500
CHANGE_TOLERANCE_SECONDS = 2.0
ITEM_LIMIT = 500
FIRST_ACTION_LIMIT = 300
MAX_ITEMS = 50
MAX_FILES = 500
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
FILL_MARK = "(fill in"
TITLE = "# Step handoff: "
HEADINGS = ("## Objective", "## Status", "## Done", "## Remaining", "## Open questions",
            "## First action for the next harness")
STATUS_TO_RECORD = {"complete": "complete", "partial": "unfinished", "blocked": "blocked"}
TICKED = re.compile(r"`([^`\n]+)`")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
PATH_LIKE = re.compile(r"/|\.[A-Za-z0-9]{1,8}\Z")
FENCE = re.compile(r"^\s*(?:```|~~~)")
COMMENT_OPENER = re.compile(r"<!-{2}")
WORD = re.compile(r"[A-Za-z0-9]")


class Refused(Exception):
    """Input that this script will not process."""


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=1, ensure_ascii=False))
    return code


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
    """Return root/relative when it stays under root, else refuse."""
    if relative.is_absolute() or ".." in relative.parts:
        raise Refused(f"path must be relative and without '..': {relative.as_posix()}")
    full = root / relative
    if not full.resolve().is_relative_to(root):
        raise Refused(f"path leaves the workspace through a link: {relative.as_posix()}")
    return full


def read_bounded(path: Path, limit: int) -> str:
    if not path.is_file():
        raise Refused(f"not a readable file: {path.name}")
    if path.stat().st_size > limit:
        raise Refused(f"{path.name} is larger than {limit} bytes; it is refused, not cut")
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused(f"{path.name} is not UTF-8") from error


def step_identity(root: Path, step_id: str | None, objective: str | None) -> tuple[str, str | None]:
    task_path = inside(root, TASK_FILE)
    if task_path.exists():
        try:
            task = strict_json(read_bounded(task_path, JSON_MAX_BYTES))
        except ValueError as error:
            raise Refused(f".baltor/step/task.json is not strict JSON: {error}") from error
        if not isinstance(task, dict):
            raise Refused(".baltor/step/task.json is not one JSON object")
        if step_id is None and isinstance(task.get("node_id"), str):
            step_id = task["node_id"]
        if objective is None and isinstance(task.get("objective"), str):
            objective = task["objective"]
    if not step_id:
        raise Refused("no step id: .baltor/step/task.json is missing or has no node_id; pass --step-id")
    if not IDENTIFIER.fullmatch(step_id):
        raise Refused("a step id uses letters, digits, '.', '-' or '_' (at most 64); pass --step-id with a safe name")
    return step_id, objective


def step_started(root: Path) -> float | None:
    """The time the step files were placed: the change time of .baltor/step/task.json, or None."""
    task_path = inside(root, TASK_FILE)
    return task_path.stat().st_mtime if task_path.is_file() else None


def template(step_id: str, objective: str | None) -> str:
    stated = " ".join(objective.split()) if objective and objective.strip() else \
        "(fill in: the objective of this step in one sentence)"
    return "\n".join([
        f"{TITLE}{step_id}",
        "",
        "## Objective",
        stated,
        "",
        "## Status",
        "(fill in: complete, partial or blocked)",
        "",
        "## Done",
        "- (fill in: one finished result per line, with the path of a file this step wrote or changed, in backticks)",
        "",
        "## Remaining",
        "- (fill in: one unfinished item per line, or the single word none)",
        "",
        "## Open questions",
        "- (fill in: one question per line and who can answer it, or the single word none)",
        "",
        "## First action for the next harness",
        "(fill in: one line with exactly one command or one file path in backticks)",
        "",
    ])


def command_init(root: Path, options) -> int:
    step_id, objective = step_identity(root, options.step_id, options.objective)
    target = inside(root, HANDOFF_DIR / f"{step_id}.md")
    relative = target.relative_to(root).as_posix()
    if target.exists() or target.is_symlink():
        return emit({"record_type": "step_handoff_init/v1", "created": False, "path": relative,
                     "step_id": step_id, "message": "The note exists and was not changed. Edit it, then run check."}, 0)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.resolve().is_relative_to(root):
        raise Refused("the handoff folder leaves the workspace through a link")
    with open(target, "x", encoding="utf-8") as stream:
        stream.write(template(step_id, objective))
    return emit({"record_type": "step_handoff_init/v1", "created": True, "path": relative, "step_id": step_id,
                 "message": "Replace every '(fill in' line, keep the headings, then run check."}, 0)


def parse_note(lines: list[str], step_id: str) -> tuple[dict[str, list[tuple[int, str]]], list[str]]:
    """Split the note into the six sections; every other heading, a repeat or loose text is a finding."""
    findings: list[str] = []
    sections: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    title_seen = False
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if FENCE.match(line):
            findings.append(f"line {number}: the note holds a fenced code block; write one line per item "
                            "and save long output to a file")
            continue
        if COMMENT_OPENER.search(line):
            findings.append(f"line {number}: hidden comment; the note holds visible text only")
        if not title_seen:
            if not stripped:
                continue
            title_seen = True
            if stripped != f"{TITLE}{step_id}":
                findings.append(f"line {number}: the first line must be '{TITLE}{step_id}'")
            if stripped.startswith("# "):
                continue
        if stripped.startswith("#"):
            if stripped in HEADINGS and stripped not in sections:
                current = stripped
                sections[current] = []
            elif stripped in HEADINGS:
                current = None
                findings.append(f"line {number}: '{stripped}' appears a second time; keep one of each heading")
            else:
                current = None
                findings.append(f"line {number}: unknown heading '{stripped[:60]}'; keep only the six headings "
                                "of the template")
            continue
        if not stripped:
            continue
        if current is None:
            if not sections and not any(finding.startswith(f"line {number}:") for finding in findings):
                findings.append(f"line {number}: text before '{HEADINGS[0]}'; move it under a heading")
            continue
        sections[current].append((number, stripped))
    missing = [heading for heading in HEADINGS if heading not in sections]
    if missing:
        findings.append(f"missing headings: {', '.join(missing)}")
    elif list(sections) != list(HEADINGS):
        findings.append("keep the headings in the template order")
    return sections, findings


def item_text(line: str) -> str:
    return BULLET.sub("", line).strip()


def is_none(entries: list[tuple[int, str]]) -> bool:
    return len(entries) == 1 and item_text(entries[0][1]).rstrip(".").lower() == "none"


def classify(root: Path, token: str, note_path: Path, started: float | None) -> tuple[str, str]:
    """Return (kind, normalized path); kind is evidence, other or a named reason the token is not evidence."""
    token = token.strip()
    if not token or any(character.isspace() for character in token):
        return "other", token
    if "\\" in token:
        return "backslash", token
    pure = PurePosixPath(token)
    if token.startswith("~") or pure.is_absolute() or ".." in pure.parts:
        return "outside", token
    normalized = PurePosixPath(os.path.normpath(token)).as_posix()
    full = root / normalized
    resolved = full.resolve()
    if not resolved.is_relative_to(root):
        return "outside", token
    if resolved == root:
        return "folder", normalized
    if not full.exists():
        return ("missing", normalized) if PATH_LIKE.search(token) else ("other", token)
    if resolved == note_path.resolve():
        return "self", normalized
    for label, prefix in NOT_EVIDENCE:
        for parts in (PurePosixPath(normalized).parts, resolved.relative_to(root).parts):
            if parts[:len(prefix)] == prefix:
                return label, normalized
    if full.is_dir():
        return "folder", normalized
    if not full.is_file():
        return "not_a_file", normalized
    if started is not None and full.stat().st_mtime < started - CHANGE_TOLERANCE_SECONDS:
        return "unchanged", normalized
    return "evidence", normalized


EVIDENCE_FINDINGS = {
    "outside": "{path} is outside the workspace",
    "backslash": "{path} uses a backslash; write paths with forward slashes",
    "missing": "evidence path {path} does not exist",
    "self": "the handoff note cannot be its own evidence",
    "folder": "{path} is a folder, not a file that proves the result",
    "not_a_file": "{path} is not a regular file",
    "unchanged": "{path} was last changed before this step started; cite a file this step wrote or changed",
}


def evidence_finding(kind: str, path: str) -> str:
    if kind in EVIDENCE_FINDINGS:
        return EVIDENCE_FINDINGS[kind].format(path=path)
    return f"{path} is a {kind}, not evidence of this step's work"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def queue_ids(root: Path) -> set[str] | None:
    """Ticket ids of the night queue, or None when there is no readable queue."""
    path = inside(root, QUEUE_FILE)
    if not path.is_file():
        return None
    try:
        queue = strict_json(read_bounded(path, JSON_MAX_BYTES))
    except (Refused, ValueError):
        return None
    items = queue.get("items") if isinstance(queue, dict) else None
    if not isinstance(items, list):
        return None
    return {item["id"] for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def check_note(root: Path, note_path: Path, step_id: str, max_words: int) -> tuple[dict, dict]:
    text = read_bounded(note_path, NOTE_MAX_BYTES)
    lines = text.splitlines()
    started = step_started(root)
    findings: list[str] = [f"line {number}: replace the '(fill in' text with real content"
                           for number, line in enumerate(lines, start=1) if FILL_MARK in line]
    sections, structure = parse_note(lines, step_id)
    findings += structure
    if "## Objective" in sections and not sections["## Objective"]:
        findings.append("Objective is empty; state the objective of this step in one sentence")
    status = None
    status_lines = sections.get("## Status", [])
    if status_lines:
        first = re.search(r"[a-z]+", item_text(status_lines[0][1]).lower())
        status = first.group(0) if first and first.group(0) in STATUS_TO_RECORD else None
    if "## Status" in sections and (status is None or len(status_lines) != 1):
        findings.append("Status is one line that starts with complete, partial or blocked")
        status = None
    for heading in ("## Done", "## Remaining", "## Open questions"):
        entries = sections.get(heading, [])
        if len(entries) > MAX_ITEMS:
            findings.append(f"{heading[3:]} holds {len(entries)} lines; keep at most {MAX_ITEMS}")
        for number, entry in entries:
            if len(item_text(entry)) > ITEM_LIMIT:
                findings.append(f"line {number}: longer than {ITEM_LIMIT} characters; save details to a file "
                                "and name its path")
    done = sections.get("## Done", [])
    done_items = [] if is_none(done) else done
    if status in ("complete", "partial") and not done_items:
        findings.append("a complete or partial step lists at least one finished result under Done")
    claims, files = [], {}
    for number, entry in done_items:
        proved = []
        for token in TICKED.findall(entry):
            kind, path = classify(root, token, note_path, started)
            if kind == "evidence":
                proved.append(path)
            elif kind != "other":
                findings.append(f"line {number}: {evidence_finding(kind, path)}")
        if not proved:
            findings.append(f"line {number}: this Done line names no file in backticks that this step wrote "
                            "or changed")
        else:
            claims.append({"text": item_text(entry), "evidence": proved[0]})
            files.update({path: None for path in proved})
    remaining = sections.get("## Remaining", [])
    if "## Remaining" in sections and not remaining:
        findings.append("Remaining is empty; list the unfinished items or write none")
    if status == "complete" and remaining and not is_none(remaining):
        findings.append("a complete step has nothing remaining; change the status to partial or move the items")
    if status in ("partial", "blocked") and is_none(remaining):
        findings.append("a partial or blocked step lists what remains under Remaining")
    questions = sections.get("## Open questions", [])
    if "## Open questions" in sections and not questions:
        findings.append("Open questions is empty; list the questions or write none")
    first_action = sections.get("## First action for the next harness", [])
    if "## First action for the next harness" in sections:
        spans = TICKED.findall(first_action[0][1]) if len(first_action) == 1 else []
        if len(first_action) != 1:
            findings.append(f"First action holds {len(first_action)} lines; write exactly one line")
        elif len(spans) != 1:
            findings.append(f"First action holds {len(spans)} items in backticks; name exactly one command "
                            "or one file path")
        elif len(first_action[0][1]) > FIRST_ACTION_LIMIT:
            findings.append(f"First action is longer than {FIRST_ACTION_LIMIT} characters; name one action")
        else:
            span = spans[0].strip()
            if not any(character.isspace() for character in span) and (
                    span.startswith("~") or PurePosixPath(span).is_absolute() or ".." in PurePosixPath(span).parts):
                findings.append(f"First action names {span}, which is outside the workspace")
    words = sum(1 for token in text.split() if WORD.search(token))
    if words > max_words:
        findings.append(f"the note has {words} words; keep it at or below {max_words} so the next harness "
                        "reads it cheaply")
    result = {"record_type": "step_handoff_check/v1", "path": note_path.relative_to(root).as_posix(),
              "passed": not findings, "status": status, "done_items": len(done_items),
              "evidence_paths": sorted(files), "words": words, "findings": findings}
    parts = {"status": status, "claims": claims, "files": list(files), "remaining": remaining,
             "questions": questions, "first_action": first_action, "started": started}
    return result, parts


def build_record(root: Path, note_path: Path, step_id: str, ticket_id: str | None, parts: dict) -> tuple[dict, list]:
    notes, files = [], []
    for path in sorted(parts["files"])[:MAX_FILES]:
        full = root / path
        if full.stat().st_size > DIGEST_MAX_BYTES:
            notes.append(f"{path} is larger than {DIGEST_MAX_BYTES} bytes and is not listed under files")
            continue
        files.append({"path": path, "sha256": sha256_of(full)})
    status = STATUS_TO_RECORD[parts["status"]]
    remaining = [] if is_none(parts["remaining"]) else [item_text(entry) for _, entry in parts["remaining"]]
    blocker = None
    if status == "blocked":
        question = None if is_none(parts["questions"]) else item_text(parts["questions"][0][1])
        evidence = None
        for token in TICKED.findall(parts["remaining"][0][1]):
            kind, path = classify(root, token, note_path, parts["started"])
            if kind == "evidence":
                evidence = path
                break
        blocker = {"reason": remaining[0], "question": question, "evidence": evidence}
    record = {"record_type": RECORD_TYPE, "step_id": step_id, "ticket_id": ticket_id, "status": status,
              "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "revision": None,
              "files": files, "claims": parts["claims"], "blocker": blocker,
              "first_action": parts["first_action"][0][1], "remaining_actions": remaining, "done_when": []}
    return record, notes


def write_record(path: Path, record: dict) -> None:
    if path.is_symlink():
        raise Refused(f"{path.name} is a symbolic link; the record is not replaced")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(temporary, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def command_check(root: Path, options) -> int:
    step_id, _objective = step_identity(root, options.step_id, None)
    note_path = inside(root, HANDOFF_DIR / f"{step_id}.md")
    if not note_path.exists():
        raise Refused(f"no handoff note at {note_path.relative_to(root).as_posix()}; run init first")
    known = queue_ids(root)
    ticket_id = options.ticket
    if ticket_id is not None:
        if not IDENTIFIER.fullmatch(ticket_id):
            raise Refused("a ticket id uses letters, digits, '.', '-' or '_' (at most 64)")
        if known is not None and ticket_id not in known:
            raise Refused(f"ticket {ticket_id} is not in {QUEUE_FILE.as_posix()}")
    elif known is not None and step_id in known:
        ticket_id = step_id
    result, parts = check_note(root, note_path, step_id, options.max_words)
    result.update({"ticket_id": ticket_id, "record_path": None, "record_status": None})
    if not result["passed"]:
        result["message"] = "No record was written. Fix every finding, then run check again."
        return emit(result, 1)
    record_path = inside(root, HANDOFF_DIR / f"{step_id}.json")
    record, notes = build_record(root, note_path, step_id, ticket_id, parts)
    write_record(record_path, record)
    result.update({"record_path": record_path.relative_to(root).as_posix(), "record_status": record["status"],
                   "record_notes": notes})
    return emit(result, 0)


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=".", help="workspace root; every path stays under it")
    shared.add_argument("--step-id", help="step id when .baltor/step/task.json does not name one")
    parser = argparse.ArgumentParser(description="Create and check a step handoff note.")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", parents=[shared], help="create the note from the template")
    init.add_argument("--objective", help="objective text when task.json does not state one")
    check = commands.add_parser("check", parents=[shared], help="check the note and write its record")
    check.add_argument("--ticket", help="ticket id for the record when the step id is not a queue ticket")
    check.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS)
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        if options.command == "init":
            return command_init(root, options)
        return command_check(root, options)
    except (Refused, OSError) as error:
        return emit({"record_type": "step_handoff_refused/v1", "refused": True, "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())

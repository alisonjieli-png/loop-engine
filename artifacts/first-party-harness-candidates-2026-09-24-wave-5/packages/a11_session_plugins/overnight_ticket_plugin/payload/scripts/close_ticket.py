"""Effects: reads one draft result on standard input, the night queue, the ticket list and the result records; writes one new record under .baltor/state/overnight-ticket-plugin/results/.

The ticket closer's only writing tool. It checks a draft against the queue,
the ticket list and a few fixed rules, then creates the ticket's result
record. It never overwrites a record and never edits any other file.

Draft fields, all required: ticket_id, outcome (fixed, blocked, skipped or
needs_review), summary, evidence (a list of {command, exit_code, observed}),
changed_files (a list of workspace-relative paths) and handoff.

Rules, all reported together: the ticket is the next open ticket of the
queue; fixed needs passing evidence, changed files and, when the ticket list
names a check command, that exact command among the evidence; skipped
changes no file; blocked leaves a handoff of at least 20 characters; no text
looks like a credential; the night state has no record problems; no record
exists yet for the ticket.

Exit status: 0 record written, 1 the draft breaks a rule (nothing written),
2 the draft or the queue cannot be read (nothing written).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

MAX_DRAFT_BYTES = 256 * 1024
DRAFT_FIELDS = {"ticket_id", "outcome", "summary", "evidence", "changed_files", "handoff"}
EVIDENCE_FIELDS = {"command", "exit_code", "observed"}
MIN_BLOCKED_HANDOFF = 20
# Generic shapes of credentials that must never land in a record. The values are
# never printed back; only the rule code is reported.
SECRET_SHAPES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
)


def load_reader():
    spec = importlib.util.spec_from_file_location("overnight_night_status", Path(__file__).resolve().with_name("night_status.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text_ok(value, low: int, high: int) -> bool:
    return isinstance(value, str) and low <= len(value) <= high and not any(
        ord(character) < 32 and character not in "\n\t" for character in value)


def squeeze(command: str) -> str:
    return " ".join(command.split())


def shape_problems(draft) -> list[str]:
    """Problems that make the draft unreadable as a record (exit 2)."""
    if not isinstance(draft, dict):
        return ["draft_is_not_an_object"]
    if set(draft) != DRAFT_FIELDS:
        missing, extra = sorted(DRAFT_FIELDS - set(draft)), sorted(set(draft) - DRAFT_FIELDS)
        return [f"draft_fields_differ: missing {missing}, extra {extra}"]
    problems = []
    if not isinstance(draft["ticket_id"], str):
        problems.append("ticket_id_invalid")
    if draft["outcome"] not in ("fixed", "blocked", "skipped", "needs_review"):
        problems.append("outcome_invalid")
    if not text_ok(draft["summary"], 1, 400):
        problems.append("summary_invalid")
    if not text_ok(draft["handoff"], 1, 600):
        problems.append("handoff_invalid")
    evidence = draft["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 10:
        problems.append("evidence_invalid")
    else:
        for item in evidence:
            if not isinstance(item, dict) or set(item) != EVIDENCE_FIELDS or not text_ok(item["command"], 1, 300) \
                    or type(item["exit_code"]) is not int or not -255 <= item["exit_code"] <= 255 \
                    or not text_ok(item["observed"], 0, 300):
                problems.append("evidence_item_invalid")
                break
    files = draft["changed_files"]
    if not isinstance(files, list) or len(files) > 200 or any(not isinstance(path, str) for path in files):
        problems.append("changed_files_invalid")
    return problems


def rule_failures(draft, reader, summary: dict, root: Path) -> list[str]:
    """Rules a readable draft can still break (exit 1). All of them are reported together."""
    failures = []
    known = {row["ticket_id"] for row in summary["tickets"]}
    upcoming = summary["next_ticket"]
    if draft["ticket_id"] not in known:
        failures.append("ticket_not_in_queue")
    elif upcoming is None or draft["ticket_id"] != upcoming["ticket_id"]:
        closed = any(row["ticket_id"] == draft["ticket_id"] and row["outcome"] != "open" for row in summary["tickets"])
        if not closed:
            failures.append("ticket_not_next_in_queue")
    if summary["problems"]:
        failures.append("night_state_has_problems")
    if any(not reader.safe_relative(path) for path in draft["changed_files"]):
        failures.append("unsafe_changed_file_path")
    outcome, evidence = draft["outcome"], draft["evidence"]
    if outcome == "fixed":
        if not evidence:
            failures.append("fixed_needs_evidence")
        elif any(item["exit_code"] != 0 for item in evidence):
            failures.append("fixed_with_failing_evidence")
        if not draft["changed_files"]:
            failures.append("fixed_needs_changed_files")
        check = upcoming.get("check") if upcoming and upcoming["ticket_id"] == draft["ticket_id"] else None
        if check and not any(squeeze(item["command"]) == squeeze(check) for item in evidence):
            failures.append("fixed_without_ticket_check")
    if outcome == "skipped" and draft["changed_files"]:
        failures.append("skipped_with_changes")
    if outcome == "blocked" and len(draft["handoff"].strip()) < MIN_BLOCKED_HANDOFF:
        failures.append("blocked_needs_handoff")
    texts = [draft["summary"], draft["handoff"], *draft["changed_files"]]
    texts += [item["command"] for item in evidence] + [item["observed"] for item in evidence]
    if any(pattern.search(text) for pattern in SECRET_SHAPES for text in texts):
        failures.append("secret_shaped_text")
    if draft["ticket_id"] in known:
        target = reader.confined(root, f"{reader.RESULTS_DIR}/{draft['ticket_id']}.json")
        if target.exists() or target.is_symlink():
            failures.append("record_exists")
    return failures


def write_record(reader, root: Path, record: dict) -> tuple[str, str]:
    relative = f"{reader.RESULTS_DIR}/{record['ticket_id']}.json"
    folder = reader.confined(root, reader.RESULTS_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    target = reader.confined(root, relative)
    body = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with open(target, "xb") as stream:  # exclusive create: an existing record is never replaced
        stream.write(body)
    return relative, hashlib.sha256(body).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write one overnight ticket result record from a draft on standard input.")
    parser.add_argument("--root", help="workspace root; default CLAUDE_PROJECT_DIR, CURSOR_PROJECT_DIR or the current folder")
    options = parser.parse_args(argv)
    reader = load_reader()
    root = reader.workspace_root(options.root)
    try:
        raw = sys.stdin.buffer.read(MAX_DRAFT_BYTES + 1)
        if len(raw) > MAX_DRAFT_BYTES:
            raise reader.Refused("draft_too_large")
        draft = reader.strict_json(raw)
        summary = reader.night_summary(root)
    except reader.Refused as error:
        print(json.dumps({"written": False, "error": error.code, "detail": error.detail}))
        return 2
    problems = shape_problems(draft)
    if problems:
        print(json.dumps({"written": False, "error": "draft_refused", "problems": problems}))
        return 2
    try:
        failures = rule_failures(draft, reader, summary, root)
    except reader.Refused as error:
        print(json.dumps({"written": False, "error": error.code, "detail": error.detail}))
        return 2
    if failures:
        print(json.dumps({"written": False, "ticket_id": draft["ticket_id"], "failures": failures}))
        return 1
    position = [row["ticket_id"] for row in summary["tickets"]].index(draft["ticket_id"]) + 1
    record = {"record_type": reader.RESULT_TYPE, "queue_sha256": summary["queue_sha256"], "position": position,
              "closed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **draft}
    try:
        relative, digest = write_record(reader, root, record)
    except FileExistsError:
        print(json.dumps({"written": False, "ticket_id": draft["ticket_id"], "failures": ["record_exists"]}))
        return 1
    except reader.Refused as error:
        print(json.dumps({"written": False, "error": error.code, "detail": error.detail}))
        return 2
    after = reader.night_summary(root)
    upcoming = after["next_ticket"]
    print(json.dumps({"written": True, "path": relative, "sha256": digest, "ticket_id": draft["ticket_id"],
                      "outcome": draft["outcome"], "position": position, "tickets_total": after["tickets_total"],
                      "closed": after["closed"],
                      "next_ticket": {"position": upcoming["position"], "ticket_id": upcoming["ticket_id"]}
                      if upcoming else None}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

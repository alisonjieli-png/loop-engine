"""Effects: reads the brief, the experiment notes, the gate log and the named submission file; appends one decision line to .baltor/state/competition-plugin/gate-decisions.jsonl; uploads nothing.

Decides whether one submission file may be handed to the host for upload.
The gate never uploads and has no network code. It checks that:

  experiment_recorded           the experiment id has a note
  metric_matches_brief          the note used the brief's metric
  folds_match_brief             the note has one score per brief fold
  data_version_current          the note used the brief's data version
  submission_recorded_in_note   the note recorded a submission digest
  submission_unchanged          the file's SHA-256 equals that digest
  deadline_not_passed           now is before the brief's deadline
  daily_limit_not_reached       ready decisions today stay under the limit

Every decision, ready or hold, is appended to the gate log so the host and
later sessions can see it. This file is self-contained so the skill folder
works on its own.

Exit status: 0 ready_for_host_upload, 1 hold, 2 refused input.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BRIEF_DEFAULT = ".baltor/competition/brief.json"
NOTES = ".baltor/state/competition-plugin/experiments.jsonl"
GATE_LOG = ".baltor/state/competition-plugin/gate-decisions.jsonl"
BRIEF_TYPE = "competition_brief/v1"
NOTE_TYPE = "experiment_note/v1"
DECISION_TYPE = "submission_gate_decision/v1"
READY, HOLD = "ready_for_host_upload", "hold"
BRIEF_FIELDS = {"record_type", "competition_id", "task_type", "metric", "target_column", "id_column",
                "submission_columns", "validation", "daily_submission_limit", "deadline_utc", "data_version", "rules"}
TASK_TYPES = ("regression", "binary_classification", "multiclass_classification", "ranking", "forecasting", "other")
SCHEMES = ("kfold", "stratified_kfold", "group_kfold", "time_split", "holdout")
DIRECTIONS = ("minimize", "maximize")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,79}\Z")
UTC_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
EXPERIMENT_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
MAX_BRIEF_BYTES = 256 * 1024
MAX_LOG_BYTES = 16 * 1024 * 1024
MAX_SUBMISSION_BYTES = 512 * 1024 * 1024
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Refused(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def strict_json(data: bytes):
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
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError:
        raise Refused("not_utf8") from None
    except json.JSONDecodeError as error:
        raise Refused("invalid_json", f"line {error.lineno}") from None
    except RecursionError:
        raise Refused("too_deep") from None


def safe_relative(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > 200 or value.startswith("/"):
        return False
    if "\\" in value or any(ord(character) < 32 for character in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def confined(root: Path, relative: str) -> Path:
    if not safe_relative(relative):
        raise Refused("unsafe_path", str(relative)[:120])
    base = root.resolve()
    candidate = base.joinpath(*relative.split("/"))
    resolved = candidate.resolve()
    if resolved != base and base not in resolved.parents:
        raise Refused("path_leaves_root", relative[:120])
    return candidate


def text(value, high: int) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= high and not any(ord(character) < 32 for character in value)


def check_brief(brief) -> dict:
    """The same competition_brief/v1 rules as the plugin's brief_summary.py; a test keeps the two in step."""
    if not isinstance(brief, dict) or brief.get("record_type") != BRIEF_TYPE:
        raise Refused("unsupported_brief_record")
    if set(brief) != BRIEF_FIELDS:
        raise Refused("brief_fields_differ", ", ".join(sorted(set(brief) ^ BRIEF_FIELDS)))
    if not isinstance(brief["competition_id"], str) or not NAME.match(brief["competition_id"]):
        raise Refused("competition_id_invalid")
    if brief["task_type"] not in TASK_TYPES:
        raise Refused("task_type_invalid")
    metric = brief["metric"]
    if not isinstance(metric, dict) or set(metric) != {"name", "direction"} or not text(metric["name"], 40) \
            or metric["direction"] not in DIRECTIONS:
        raise Refused("metric_invalid")
    for field in ("target_column", "id_column", "data_version"):
        if not text(brief[field], 80):
            raise Refused(f"{field}_invalid")
    columns = brief["submission_columns"]
    if not isinstance(columns, list) or not 1 <= len(columns) <= 50 or any(not text(column, 80) for column in columns) \
            or len(set(columns)) != len(columns):
        raise Refused("submission_columns_invalid")
    validation = brief["validation"]
    if not isinstance(validation, dict) or not {"scheme", "folds"} <= set(validation) \
            or set(validation) - {"scheme", "folds", "group_column"} or validation["scheme"] not in SCHEMES \
            or type(validation["folds"]) is not int or not 1 <= validation["folds"] <= 50 \
            or ("group_column" in validation and not text(validation["group_column"], 80)):
        raise Refused("validation_invalid")
    limit = brief["daily_submission_limit"]
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise Refused("daily_submission_limit_invalid")
    if not isinstance(brief["deadline_utc"], str) or not UTC_STAMP.match(brief["deadline_utc"]):
        raise Refused("deadline_utc_invalid")
    rules = brief["rules"]
    if not isinstance(rules, list) or len(rules) > 20 or any(not text(rule, 200) for rule in rules):
        raise Refused("rules_invalid")
    return brief


def read_lines(root: Path, relative: str) -> list[dict]:
    """Read a JSON Lines file under the root; unreadable lines are skipped, a missing file is empty."""
    path = confined(root, relative)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_LOG_BYTES:
        raise Refused("state_file_invalid", relative)
    values = []
    with open(path, "rb") as stream:
        for line in stream:
            try:
                value = strict_json(line)
            except Refused:
                continue
            if isinstance(value, dict):
                values.append(value)
    return values


def submission_digest(path: Path) -> str:
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            if size > MAX_SUBMISSION_BYTES:
                raise Refused("submission_too_large")
            digest.update(block)
    return digest.hexdigest()


def parse_now(value: str | None) -> datetime.datetime:
    if value is None:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    if not UTC_STAMP.match(value):
        raise Refused("now_invalid", "use YYYY-MM-DDTHH:MM:SSZ")
    return datetime.datetime.strptime(value, UTC_FORMAT).replace(tzinfo=datetime.timezone.utc)


def decide(root: Path, experiment_id: str, submission: str, now: datetime.datetime) -> dict:
    brief_path = confined(root, BRIEF_DEFAULT)
    if not brief_path.is_file():
        raise Refused("brief_missing", BRIEF_DEFAULT)
    with open(brief_path, "rb") as stream:
        data = stream.read(MAX_BRIEF_BYTES + 1)
    if len(data) > MAX_BRIEF_BYTES:
        raise Refused("brief_too_large")
    brief = check_brief(strict_json(data))
    submission_path = confined(root, submission)
    if submission_path.is_symlink() or not submission_path.is_file():
        raise Refused("submission_missing", submission)
    actual = submission_digest(submission_path)
    notes = [note for note in read_lines(root, NOTES)
             if note.get("record_type") == NOTE_TYPE and note.get("experiment_id") == experiment_id]
    note = notes[-1] if notes else {}
    deadline = datetime.datetime.strptime(brief["deadline_utc"], UTC_FORMAT).replace(tzinfo=datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    ready_today = sum(1 for entry in read_lines(root, GATE_LOG)
                      if entry.get("decision") == READY and str(entry.get("decided_at", ""))[:10] == today)
    scores = note.get("fold_scores")
    checks = [
        ("experiment_recorded", bool(note), f"notes for {experiment_id}: {len(notes)}"),
        ("metric_matches_brief", note.get("metric") == brief["metric"]["name"],
         f"note {note.get('metric')!r}, brief {brief['metric']['name']!r}"),
        ("folds_match_brief", isinstance(scores, list) and len(scores) == brief["validation"]["folds"],
         f"note {len(scores) if isinstance(scores, list) else 'none'}, brief {brief['validation']['folds']}"),
        ("data_version_current", note.get("data_version") == brief["data_version"],
         f"note {note.get('data_version')!r}, brief {brief['data_version']!r}"),
        ("submission_recorded_in_note", isinstance(note.get("submission_sha256"), str),
         "the note must be written with submission_file set"),
        ("submission_unchanged", note.get("submission_sha256") == actual,
         f"file {actual[:16]}, note {str(note.get('submission_sha256'))[:16]}"),
        ("deadline_not_passed", now < deadline, f"now {now.strftime(UTC_FORMAT)}, deadline {brief['deadline_utc']}"),
        ("daily_limit_not_reached", ready_today < brief["daily_submission_limit"],
         f"ready today {ready_today}, limit {brief['daily_submission_limit']}"),
    ]
    rows = [{"check": name, "passed": bool(passed), "detail": detail} for name, passed, detail in checks]
    decision = READY if all(row["passed"] for row in rows) else HOLD
    return {"record_type": DECISION_TYPE, "decision": decision, "experiment_id": experiment_id,
            "submission_file": submission, "submission_sha256": actual, "checks": rows,
            "decided_at": now.strftime(UTC_FORMAT), "upload": "not performed; only the host uploads"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Decide whether one submission file may go to the host for upload.")
    parser.add_argument("--experiment", required=True, help="experiment id whose note recorded the submission file")
    parser.add_argument("--submission", required=True, help="submission file path relative to the root")
    parser.add_argument("--root", help="workspace root; default CLAUDE_PROJECT_DIR, GEMINI_PROJECT_DIR or the current folder")
    parser.add_argument("--now", help="decision time as YYYY-MM-DDTHH:MM:SSZ, for replay and tests; default the clock")
    options = parser.parse_args(argv)
    root = Path(options.root or os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("GEMINI_PROJECT_DIR") or ".").resolve()
    try:
        if not EXPERIMENT_ID.match(options.experiment):
            raise Refused("experiment_id_invalid")
        record = decide(root, options.experiment, options.submission, parse_now(options.now))
        log = confined(root, GATE_LOG)
        log.parent.mkdir(parents=True, exist_ok=True)
        if log.is_symlink():
            raise Refused("state_file_invalid", GATE_LOG)
    except Refused as error:
        print(json.dumps({"decision": None, "error": error.code, "detail": error.detail}))
        return 2
    with open(log, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(record, indent=1))
    return 0 if record["decision"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())

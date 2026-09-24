"""Effects: reads one session start event on standard input, the competition brief and the experiment notes under the workspace root; writes nothing.

Session start hook for Claude Code and Gemini CLI (both name the event
SessionStart). It adds a short summary of the competition brief to the new
session: metric and direction, target and id columns, submission columns,
validation scheme, data version, deadline, daily submission limit and rules,
plus the number of experiment notes and the latest one. It never reads the
transcript and never blocks a session: unusable input gives an empty JSON
object, exit 0 and one line on standard error.

Files, relative to the workspace root:
  .baltor/competition/brief.json                      competition_brief/v1, written before the session
  .baltor/state/competition-plugin/experiments.jsonl  one experiment_note/v1 per line

experiment_note.py loads this file by its exact path and reuses the readers.

Usage: python3 -I -B brief_summary.py --harness claude_code|gemini_cli [--root PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

BRIEF_DEFAULT = ".baltor/competition/brief.json"
NOTES = ".baltor/state/competition-plugin/experiments.jsonl"
BRIEF_TYPE = "competition_brief/v1"
NOTE_TYPE = "experiment_note/v1"
BRIEF_FIELDS = {"record_type", "competition_id", "task_type", "metric", "target_column", "id_column",
                "submission_columns", "validation", "daily_submission_limit", "deadline_utc", "data_version", "rules"}
TASK_TYPES = ("regression", "binary_classification", "multiclass_classification", "ranking", "forecasting", "other")
SCHEMES = ("kfold", "stratified_kfold", "group_kfold", "time_split", "holdout")
DIRECTIONS = ("minimize", "maximize")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,79}\Z")
UTC_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
MAX_BRIEF_BYTES = 256 * 1024
MAX_NOTES_BYTES = 16 * 1024 * 1024
MAX_EVENT_BYTES = 1024 * 1024
MAX_CONTEXT_CHARS = 2500
SOURCES = {"claude_code": ("startup", "resume", "clear", "compact"), "gemini_cli": ("startup", "resume", "clear")}
ROOT_VARIABLES = {"claude_code": ("CLAUDE_PROJECT_DIR",), "gemini_cli": ("GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR")}
NOTE_COMMAND = {"claude_code": "/competition-plugin:experiment-note", "gemini_cli": "/experiment-note"}


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


def workspace_root(explicit, variables=("CLAUDE_PROJECT_DIR", "GEMINI_PROJECT_DIR")) -> Path:
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
    """Validate a competition_brief/v1 object and return it, or raise Refused."""
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


def load_brief(root: Path, relative: str = BRIEF_DEFAULT) -> dict:
    path = confined(root, relative)
    if not path.is_file():
        raise Refused("brief_missing", relative)
    with open(path, "rb") as stream:
        data = stream.read(MAX_BRIEF_BYTES + 1)
    if len(data) > MAX_BRIEF_BYTES:
        raise Refused("brief_too_large")
    return check_brief(strict_json(data))


def load_notes(root: Path) -> tuple[list[dict], int]:
    """Return (readable notes in file order, count of unreadable lines)."""
    path = confined(root, NOTES)
    if not path.exists():
        return [], 0
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_NOTES_BYTES:
        raise Refused("notes_file_invalid")
    notes, unreadable = [], 0
    with open(path, "rb") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                note = strict_json(line)
            except Refused:
                unreadable += 1
                continue
            if isinstance(note, dict) and note.get("record_type") == NOTE_TYPE and isinstance(note.get("experiment_id"), str):
                notes.append(note)
            else:
                unreadable += 1
    return notes, unreadable


def plain(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


def context_text(harness: str, root: Path) -> str:
    try:
        brief = load_brief(root)
    except Refused as error:
        if error.code == "brief_missing":
            return (f"Competition plugin: no brief at {BRIEF_DEFAULT}. Stop and report that the brief is missing "
                    "before you train or submit anything.")
        return (f"Competition plugin: the brief at {BRIEF_DEFAULT} could not be read ({error.code}). Stop and "
                "report this before you train or submit anything.")
    metric, validation = brief["metric"], brief["validation"]
    better = "lower" if metric["direction"] == "minimize" else "higher"
    groups = f", groups by {validation['group_column']}" if validation.get("group_column") else ""
    parts = [f"Competition {brief['competition_id']} ({brief['task_type']}).",
             f"Metric: {metric['name']}, {better} is better.",
             f"Target column: {brief['target_column']}. Id column: {brief['id_column']}.",
             f"Submission columns: {', '.join(brief['submission_columns'])}.",
             f"Validation: {validation['scheme']}, {validation['folds']} folds{groups}.",
             f"Data version: {brief['data_version']}. Deadline (UTC): {brief['deadline_utc']}.",
             f"Daily submission limit: {brief['daily_submission_limit']}."]
    if brief["rules"]:
        parts.append("Rules: " + "; ".join(plain(rule, 200).rstrip(".") for rule in brief["rules"]) + ".")
    try:
        notes, unreadable = load_notes(root)
    except Refused as error:
        notes, unreadable = [], 0
        parts.append(f"The experiment notes could not be read ({error.code}); report this.")
    line = f"Experiment notes: {len(notes)}"
    if notes:
        latest = notes[-1]
        mean = latest.get("cv_mean")
        shown = f"{mean:.6g}" if isinstance(mean, (int, float)) and not isinstance(mean, bool) and math.isfinite(mean) else "unknown"
        line += f"; latest {plain(latest['experiment_id'], 64)}, cv mean {shown}"
    if unreadable:
        line += f"; {unreadable} unreadable lines, report them"
    parts.append(line + ".")
    parts.append(f"Record every finished experiment with {NOTE_COMMAND[harness]}. The host uploads submissions: run "
                 "the pre-submission-gate skill before you ask for an upload, and never upload yourself.")
    return plain(" ".join(parts), MAX_CONTEXT_CHARS)


def answer(harness: str, message: str) -> dict:
    if harness == "claude_code":
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": message}}
    return {"hookSpecificOutput": {"additionalContext": message}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Session start hook of the competition plugin.")
    parser.add_argument("--harness", required=True, choices=sorted(SOURCES))
    parser.add_argument("--root", help="workspace root; default the harness project variable, then the current folder")
    options = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            raise Refused("event_too_large")
        event = strict_json(raw)
        if not isinstance(event, dict) or event.get("hook_event_name") != "SessionStart" \
                or event.get("source") not in SOURCES[options.harness]:
            raise Refused("unexpected_event")
        message = context_text(options.harness, workspace_root(options.root, ROOT_VARIABLES[options.harness]))
    except Exception as error:  # noqa: BLE001 - a context hook fails open and never blocks a session
        sys.stdout.write("{}\n")
        sys.stderr.write(f"competition_plugin: hook input refused: {getattr(error, 'code', type(error).__name__)}\n")
        return 0
    sys.stdout.write(json.dumps(answer(options.harness, message)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

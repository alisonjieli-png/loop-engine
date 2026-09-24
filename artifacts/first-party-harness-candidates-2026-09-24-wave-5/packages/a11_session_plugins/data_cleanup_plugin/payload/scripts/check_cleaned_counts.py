"""Effects: reads one hook event on standard input, the pairs file and the declared CSV files under the workspace root; writes nothing.

Compares each cleaned copy with its source by header and data row count.
The pairs come from .baltor/step/cleanup-pairs.json (cleanup_pairs/v1):

  {"record_type": "cleanup_pairs/v1",
   "pairs": [{"source": "data/raw/a.csv", "cleaned": "data/clean/a.csv",
              "delimiter": ",", "renamed_columns": {"Old": "new"}, "max_dropped_rows": 0}]}

A cleaned copy matches when its header equals the source header after the
declared renames, in the same order, and its data row count is between the
source count minus max_dropped_rows and the source count. Rows are CSV
records, so a quoted value with a line break is one row, and fully empty
lines are not rows.

Two modes:
  --harness claude_code|gemini_cli   post-write hook: one event on standard input,
                                     one JSON answer on standard output, always exit 0
  --all                              status of every pair: exit 0 all match,
                                     1 any other status, 2 pairs file missing or refused
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

PAIRS_DEFAULT = ".baltor/step/cleanup-pairs.json"
PAIRS_TYPE = "cleanup_pairs/v1"
PAIR_REQUIRED = {"source", "cleaned"}
PAIR_OPTIONAL = {"delimiter", "renamed_columns", "max_dropped_rows"}
DELIMITERS = (",", ";", "\t", "|")
MAX_EVENT_BYTES = 1024 * 1024
MAX_PAIRS_BYTES = 256 * 1024
MAX_DATA_BYTES = 64 * 1024 * 1024
MAX_PAIRS = 50
EVENTS = {"claude_code": ("PostToolUse", ("Write", "Edit")), "gemini_cli": ("AfterTool", ("write_file", "replace"))}
ROOT_VARIABLES = {"claude_code": ("CLAUDE_PROJECT_DIR",), "gemini_cli": ("GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR")}
STATUSES = ("match", "mismatch", "missing_source", "missing_cleaned", "unreadable")
csv.field_size_limit(16 * 1024 * 1024)


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


def workspace_root(explicit, variables) -> Path:
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


def load_pairs(root: Path, relative: str = PAIRS_DEFAULT) -> list[dict]:
    path = confined(root, relative)
    if not path.is_file():
        raise Refused("pairs_missing", relative)
    with open(path, "rb") as stream:
        data = stream.read(MAX_PAIRS_BYTES + 1)
    if len(data) > MAX_PAIRS_BYTES:
        raise Refused("pairs_too_large")
    document = strict_json(data)
    if not isinstance(document, dict) or document.get("record_type") != PAIRS_TYPE \
            or set(document) != {"record_type", "pairs"}:
        raise Refused("unsupported_pairs_record")
    pairs = document["pairs"]
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= MAX_PAIRS:
        raise Refused("pairs_invalid", f"a list of 1 to {MAX_PAIRS} pairs")
    cleaned_seen, result = set(), []
    for index, pair in enumerate(pairs, start=1):
        if not isinstance(pair, dict) or not PAIR_REQUIRED <= set(pair) or set(pair) - PAIR_REQUIRED - PAIR_OPTIONAL:
            raise Refused("pair_fields_differ", f"pair {index}")
        if not safe_relative(pair["source"]) or not safe_relative(pair["cleaned"]) or pair["source"] == pair["cleaned"]:
            raise Refused("pair_paths_invalid", f"pair {index}")
        if pair["cleaned"] in cleaned_seen:
            raise Refused("cleaned_path_repeated", f"pair {index}")
        cleaned_seen.add(pair["cleaned"])
        delimiter = pair.get("delimiter", ",")
        renamed = pair.get("renamed_columns", {})
        dropped = pair.get("max_dropped_rows", 0)
        if delimiter not in DELIMITERS:
            raise Refused("delimiter_invalid", f"pair {index}")
        if not isinstance(renamed, dict) or len(renamed) > 200 or any(
                not isinstance(key, str) or not isinstance(value, str) or not value for key, value in renamed.items()):
            raise Refused("renamed_columns_invalid", f"pair {index}")
        if type(dropped) is not int or not 0 <= dropped <= 10 ** 9:
            raise Refused("max_dropped_rows_invalid", f"pair {index}")
        result.append({"source": pair["source"], "cleaned": pair["cleaned"], "delimiter": delimiter,
                       "renamed_columns": renamed, "max_dropped_rows": dropped})
    return result


def csv_shape(path: Path, delimiter: str) -> tuple[list[str], int]:
    """Return (header, data row count). Fully empty lines are not rows."""
    if path.stat().st_size > MAX_DATA_BYTES:
        raise Refused("file_too_large")
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, delimiter=delimiter, strict=True)
            header = next(reader, [])
            rows = sum(1 for record in reader if record)
    except UnicodeDecodeError:
        raise Refused("not_utf8") from None
    except csv.Error as error:
        raise Refused("csv_unreadable", str(error)[:120]) from None
    return header, rows


def compare(root: Path, pair: dict) -> dict:
    result = {"source": pair["source"], "cleaned": pair["cleaned"], "status": "match", "source_rows": None,
              "cleaned_rows": None, "columns": None, "header_match": None, "details": []}
    try:
        source = confined(root, pair["source"])
        cleaned = confined(root, pair["cleaned"])
    except Refused as error:
        result.update(status="unreadable", details=[error.code])
        return result
    if not source.is_file():
        result.update(status="missing_source")
        return result
    if not cleaned.is_file():
        result.update(status="missing_cleaned")
        return result
    try:
        source_header, source_rows = csv_shape(source, pair["delimiter"])
        cleaned_header, cleaned_rows = csv_shape(cleaned, pair["delimiter"])
    except Refused as error:
        result.update(status="unreadable", details=[error.code])
        return result
    renamed = pair["renamed_columns"]
    unknown = sorted(set(renamed) - set(source_header))
    expected = [renamed.get(name, name) for name in source_header]
    result.update(source_rows=source_rows, cleaned_rows=cleaned_rows, columns=len(cleaned_header),
                  header_match=cleaned_header == expected)
    details = []
    if unknown:
        details.append(f"renamed_columns names columns the source lacks: {unknown[:5]}")
    if cleaned_header != expected:
        missing = [name for name in expected if name not in cleaned_header]
        extra = [name for name in cleaned_header if name not in expected]
        if missing:
            details.append(f"header lacks {missing[:5]}")
        if extra:
            details.append(f"header adds {extra[:5]}")
        if not missing and not extra:
            details.append("header has the right columns in another order")
    lowest = source_rows - pair["max_dropped_rows"]
    if cleaned_rows > source_rows:
        details.append(f"rows added: {cleaned_rows} rows, source has {source_rows}")
    elif cleaned_rows < lowest:
        details.append(f"rows lost: {cleaned_rows} rows, source has {source_rows}, "
                       f"at most {pair['max_dropped_rows']} may be dropped")
    if details:
        result.update(status="mismatch", details=details)
    return result


def written_relative(root: Path, file_path) -> str | None:
    """The written file as a root-relative path, or None when it is not inside the root."""
    if not isinstance(file_path, str) or not file_path or len(file_path) > 4096:
        return None
    base = root.resolve()
    candidate = Path(file_path) if file_path.startswith("/") else base / file_path
    resolved = candidate.resolve()
    if base not in resolved.parents:
        return None
    return resolved.relative_to(base).as_posix()


def hook_message(root: Path, relative: str) -> tuple[str, bool] | None:
    """Return (message, is_problem) for a written file, or None when the file is not ours."""
    try:
        pairs = load_pairs(root)
    except Refused as error:
        if error.code == "pairs_missing":
            return None
        return (f"Cleanup count check could not run: {PAIRS_DEFAULT} is unreadable ({error.code}). "
                "Stop and report this; do not guess the pairs."), True
    if relative == PAIRS_DEFAULT:
        return (f"{PAIRS_DEFAULT} was changed during the step. The count check needs a fixed reference, so "
                "stop and report the change instead of continuing."), True
    for pair in pairs:
        if relative == pair["source"]:
            return (f"You wrote to {relative}, which {PAIRS_DEFAULT} declares as a source. Source files stay "
                    "unchanged. Stop and report which step wrote it."), True
    for pair in pairs:
        if relative == pair["cleaned"]:
            result = compare(root, pair)
            if result["status"] == "match":
                return (f"Cleanup count check passed for {relative}: header of {result['columns']} columns "
                        f"and {result['cleaned_rows']} rows match {pair['source']}."), False
            details = "; ".join(result["details"]) or result["status"]
            return (f"Cleanup count check failed for {relative} against {pair['source']}: {details}. Find the cause "
                    f"before writing more files. Do not edit {PAIRS_DEFAULT} to make this pass. If you cannot "
                    "find the cause, stop and report."), True
    return None


def answer(harness: str, message: str, problem: bool) -> dict:
    if harness == "claude_code":
        if problem:
            return {"decision": "block", "reason": message}
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}
    return {"hookSpecificOutput": {"additionalContext": message}}


def run_hook(harness: str, explicit_root) -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            raise Refused("event_too_large")
        event = strict_json(raw)
        name, tools = EVENTS[harness]
        if not isinstance(event, dict) or event.get("hook_event_name") != name or event.get("tool_name") not in tools:
            raise Refused("unexpected_event")
        tool_input = event.get("tool_input")
        if not isinstance(tool_input, dict):
            raise Refused("tool_input_missing")
        root = workspace_root(explicit_root, ROOT_VARIABLES[harness])
        relative = written_relative(root, tool_input.get("file_path"))
        found = hook_message(root, relative) if relative else None
    except Exception as error:  # noqa: BLE001 - a post-write check fails open; the write already happened
        sys.stdout.write("{}\n")
        sys.stderr.write(f"data_cleanup_plugin: hook input refused: {getattr(error, 'code', type(error).__name__)}\n")
        return 0
    sys.stdout.write(json.dumps(answer(harness, *found) if found else {}) + "\n")
    return 0


def run_all(explicit_root, pairs_relative: str) -> int:
    root = workspace_root(explicit_root, ("CLAUDE_PROJECT_DIR", "GEMINI_PROJECT_DIR"))
    try:
        pairs = load_pairs(root, pairs_relative)
    except Refused as error:
        print(json.dumps({"error": error.code, "detail": error.detail}))
        return 2
    results = [compare(root, pair) for pair in pairs]
    summary = {status: sum(1 for result in results if result["status"] == status) for status in STATUSES}
    print(json.dumps({"pairs_file": pairs_relative, "results": results, "summary": summary}, indent=1))
    return 0 if summary["match"] == len(results) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare cleaned CSV copies with their sources by header and row count.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--harness", choices=sorted(EVENTS), help="run as the post-write hook of this harness")
    mode.add_argument("--all", action="store_true", help="print the status of every declared pair")
    parser.add_argument("--root", help="workspace root; default the harness project variable, then the current folder")
    parser.add_argument("--pairs", default=PAIRS_DEFAULT, help="pairs file relative to the root (status mode only)")
    options = parser.parse_args(argv)
    if options.harness:
        return run_hook(options.harness, options.root)
    return run_all(options.root, options.pairs)


if __name__ == "__main__":
    raise SystemExit(main())

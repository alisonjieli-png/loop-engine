"""Effects: reads task.json and the output schema of the step folder (.baltor/step) and creates one new result file under .baltor/state/portable-step-packet-plugin/results/<node id>/; never replaces a file.

Writes the result of the current focused step. The result is one JSON value
on standard input. Before writing, it checks the result against the packet's
contracts/output.schema.json at the top level only:

  missing_required_field   a field in "required" is absent
  unknown_field            a field outside "properties" while
                           "additionalProperties" is false
  field_type_differs       a top-level value has another JSON type than the
                           "type" its property names
  result_type_differs      the whole result has another type than the schema
  secret_shaped_text       a text value looks like a key or token (never echoed)
  result_too_large         the result is above the byte limit

A result that passes goes to result-NNN.json, numbered from 001, created
exclusively, inside the record portable_step_result/v1 with the node id and
the SHA-256 of task.json. Earlier results stay, so a better result can be
published later and a reader names the exact file it used. Deeper schema
rules are not checked here; the host's acceptance check owns them.

The workspace root is --root, else the folder that holds .baltor when this
script sits below a .baltor folder, else the current folder.

Exit status: 0 written, 1 a check failed (nothing written), 2 refused input
(nothing written). The step packet server loads this file by its exact path
and calls write_result.
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

RESULT_TYPE = "portable_step_result/v1"
TASK_TYPE = "node_assignment/v3"
STEP_DEFAULT = ".baltor/step"
RESULTS_BASE = ".baltor/state/portable-step-packet-plugin/results"
NODE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
RESULT_NAME = re.compile(r"result-(\d{3})\.json\Z")
MAX_RESULT_BYTES = 256 * 1024
MAX_TASK_BYTES = 64 * 1024
MAX_SCHEMA_BYTES = 256 * 1024
MAX_RESULTS = 999
MAX_PROBLEMS = 20
JSON_TYPES = ("string", "number", "integer", "boolean", "array", "object", "null")
# Generic shapes of keys and tokens that must not land in a result file. A match is reported
# by its rule only; the value is never printed back.
SECRET_SHAPES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
)


class Refused(Exception):
    """Input this script will not write. The code is a fixed word; the detail never holds result values."""

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
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError:
        raise Refused("not_utf8") from None
    except json.JSONDecodeError as error:
        raise Refused("invalid_json", f"line {error.lineno}") from None
    except RecursionError:
        raise Refused("too_deep") from None


def default_root(script: Path, cwd: Path) -> Path:
    """The folder that holds .baltor when the script sits below a .baltor folder, else the current folder."""
    parts = script.parts
    if ".baltor" in parts:
        return Path(*parts[: parts.index(".baltor")])
    return cwd


def workspace_root(explicit=None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return default_root(Path(__file__).resolve(), Path.cwd().resolve())


def safe_relative(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > 200 or value.startswith("/"):
        return False
    if "\\" in value or any(ord(character) < 32 for character in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def confined(root: Path, relative: str) -> Path:
    """Join a safe relative path to root and refuse it when a link leads outside root."""
    if not safe_relative(relative):
        raise Refused("unsafe_path", str(relative)[:120])
    base = root.resolve()
    candidate = base.joinpath(*relative.split("/"))
    resolved = candidate.resolve()
    if resolved != base and base not in resolved.parents:
        raise Refused("path_leaves_root", relative[:120])
    return candidate


def read_regular(path: Path, limit: int, code: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Refused(code)
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Refused("file_too_large", f"above {limit} bytes")
    return data


def load_step(root: Path, step_relative: str) -> tuple[str, str, dict | None]:
    """(node id, SHA-256 of task.json, output schema or None) of the step folder."""
    folder = confined(root, step_relative)
    if folder.is_symlink() or not folder.is_dir():
        raise Refused("step_folder_missing", f"no {step_relative} under the workspace root {root}")
    raw = read_regular(folder / "task.json", MAX_TASK_BYTES, "task_missing")
    task = strict_json(raw)
    if not isinstance(task, dict) or task.get("record_type") != TASK_TYPE:
        raise Refused("task_record_type_unsupported", f"task.json must be {TASK_TYPE}")
    if not isinstance(task.get("node_id"), str) or not NODE_ID.match(task["node_id"]):
        raise Refused("task_node_id_unsafe", "letters, digits, dot, dash and underscore, at most 64")
    schema_path = folder / "contracts" / "output.schema.json"
    schema = None
    if schema_path.exists() or schema_path.is_symlink():
        schema = strict_json(read_regular(schema_path, MAX_SCHEMA_BYTES, "output_schema_unreadable"))
        if not isinstance(schema, dict):
            raise Refused("output_schema_unreadable", "not a JSON object")
    return task["node_id"], hashlib.sha256(raw).hexdigest(), schema


def json_type_matches(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if isinstance(value, bool):
        return False
    if expected == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if expected == "number":
        return isinstance(value, (int, float))
    return True  # an unknown type name is not judged here


def type_names(declared) -> list[str]:
    if isinstance(declared, str) and declared in JSON_TYPES:
        return [declared]
    if isinstance(declared, list):
        return [name for name in declared if isinstance(name, str) and name in JSON_TYPES]
    return []


def text_values(value, found: list, depth: int = 0) -> None:
    if depth > 64:
        return
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, list):
        for item in value:
            text_values(item, found, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            found.append(str(key))
            text_values(item, found, depth + 1)


def check_result(result, schema: dict | None) -> tuple[list[str], str]:
    """Problems of a result against the schema's top level, and the name of what was checked."""
    problems = []
    texts: list[str] = []
    text_values(result, texts)
    if any(shape.search(text) for shape in SECRET_SHAPES for text in texts):
        problems.append("secret_shaped_text")
    if schema is None:
        return problems, "no_output_schema"
    expected = type_names(schema.get("type"))
    if expected and not any(json_type_matches(result, name) for name in expected):
        return problems + [f"result_type_differs: expected {' or '.join(expected)}"], "top_level_type"
    if not isinstance(result, dict):
        return problems, "top_level_type"
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    for name in required:
        if isinstance(name, str) and name not in result:
            problems.append(f"missing_required_field: {name}")
    if schema.get("additionalProperties") is False:
        for name in result:
            if name not in properties:
                problems.append(f"unknown_field: {name[:80]}")
    for name, value in result.items():
        declared = properties.get(name)
        names = type_names(declared.get("type")) if isinstance(declared, dict) else []
        if names and not any(json_type_matches(value, item) for item in names):
            problems.append(f"field_type_differs: {name[:80]} (expected {' or '.join(names)})")
    return problems[:MAX_PROBLEMS], "required_fields_and_top_level_types"


def next_sequence(folder: Path) -> int:
    numbers = [int(match.group(1)) for match in (RESULT_NAME.match(name) for name in os.listdir(folder)) if match]
    return max(numbers, default=0) + 1


def write_result(root: Path, result, step_relative: str = STEP_DEFAULT) -> tuple[int, dict]:
    """Check and write one result. Returns (exit status, answer). Raises Refused for unusable input."""
    body = json.dumps(result, ensure_ascii=False, allow_nan=False)
    if len(body.encode("utf-8")) > MAX_RESULT_BYTES:
        return 1, {"written": False, "problems": [f"result_too_large: above {MAX_RESULT_BYTES} bytes"]}
    node_id, task_sha256, schema = load_step(root, step_relative)
    problems, checked = check_result(result, schema)
    if problems:
        return 1, {"written": False, "node_id": node_id, "problems": problems, "checked": checked}
    relative_folder = f"{RESULTS_BASE}/{node_id}"
    folder = confined(root, relative_folder)
    folder.mkdir(parents=True, exist_ok=True)
    folder = confined(root, relative_folder)  # checked again: a link could have appeared while it was made
    if folder.is_symlink() or not folder.is_dir():
        raise Refused("results_folder_invalid", relative_folder)
    for _attempt in range(5):
        sequence = next_sequence(folder)
        if sequence > MAX_RESULTS:
            return 1, {"written": False, "node_id": node_id, "problems": [f"too_many_results: {MAX_RESULTS}"]}
        record = {"record_type": RESULT_TYPE, "node_id": node_id, "task_sha256": task_sha256, "sequence": sequence,
                  "written_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "checked": checked, "result": result}
        data = (json.dumps(record, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        name = f"result-{sequence:03d}.json"
        try:
            with open(folder / name, "xb") as stream:  # exclusive create: an earlier result is never replaced
                stream.write(data)
        except FileExistsError:
            continue
        return 0, {"written": True, "node_id": node_id, "path": f"{relative_folder}/{name}", "sequence": sequence,
                   "sha256": hashlib.sha256(data).hexdigest(), "checked": checked}
    raise Refused("result_name_taken", "another writer took every new number; write again")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check and write the result of the current focused step. "
                                                 "The result is one JSON value on standard input.")
    parser.add_argument("--root", help="workspace root; default the folder that holds .baltor, else the current folder")
    parser.add_argument("--step-dir", default=STEP_DEFAULT, help="step folder relative to the root")
    options = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_RESULT_BYTES + 1)
        if len(raw) > MAX_RESULT_BYTES:
            raise Refused("result_too_large", f"above {MAX_RESULT_BYTES} bytes")
        code, answer = write_result(workspace_root(options.root), strict_json(raw), options.step_dir)
    except Refused as error:
        print(json.dumps({"written": False, "error": error.code, "detail": error.detail}))
        return 2
    except OSError as error:
        print(json.dumps({"written": False, "error": "os_error", "detail": type(error).__name__}))
        return 2
    print(json.dumps(answer, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

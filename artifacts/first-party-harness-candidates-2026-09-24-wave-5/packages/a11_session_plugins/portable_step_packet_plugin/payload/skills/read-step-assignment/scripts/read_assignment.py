"""Effects: reads the step folder (.baltor/step) and the result folder of this plugin under the workspace root; writes nothing.

Reads the assignment of the current focused step and prints one JSON object:

  task       the node_assignment/v3 fields of task.json, as given
  files      every regular file in the step folder, with size and SHA-256
  output     the output schema path, its top-level type, its required fields
             and whether it allows fields it does not name
  results    the folder where write_step_result keeps numbered results, how
             many exist and the newest one
  next       what to do after reading

With --file NAME it prints one text file of the step folder instead. It
never judges whether the assignment is complete or sensible.

The workspace root is --root, else the folder that holds .baltor when this
script sits below a .baltor folder, else the current folder.

Exit status: 0 read, 2 refused (the error code and detail are printed).
The step packet server loads this file by its exact path and calls
read_assignment and read_step_file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

RECORD_TYPE = "portable_step_assignment/v1"
TASK_TYPE = "node_assignment/v3"
STEP_DEFAULT = ".baltor/step"
RESULTS_BASE = ".baltor/state/portable-step-packet-plugin/results"
NODE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
TEXT_FIELDS = ("node_id", "kind", "mode", "objective", "harness_style")
LIST_FIELDS = ("effects", "output_contract_refs", "required_capabilities", "dependency_ids")
MAX_TASK_BYTES = 64 * 1024
MAX_SCHEMA_BYTES = 256 * 1024
MAX_TEXT_BYTES = 32 * 1024
MAX_FILES = 64
MAX_TEXT_CHARS = 2000
NEXT = ("Read node_context.md and checklist.md with read_step_file, work only on task.objective within "
        "task.effects, then give the result to write_step_result.")


class Refused(Exception):
    """Input this script will not read. The code is a fixed word; the detail never holds file contents."""

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


def step_folder(root: Path, step_relative: str = STEP_DEFAULT) -> Path:
    folder = confined(root, step_relative)
    if folder.is_symlink() or not folder.is_dir():
        raise Refused("step_folder_missing", f"no {step_relative} under the workspace root {root}")
    return folder


def load_task(folder: Path) -> tuple[dict, str]:
    """The task.json object and the SHA-256 of its bytes. Only the fields needed to serve it are checked."""
    raw = read_regular(folder / "task.json", MAX_TASK_BYTES, "task_missing")
    task = strict_json(raw)
    if not isinstance(task, dict) or task.get("record_type") != TASK_TYPE:
        raise Refused("task_record_type_unsupported", f"task.json must be {TASK_TYPE}")
    if not isinstance(task.get("node_id"), str) or not NODE_ID.match(task["node_id"]):
        raise Refused("task_node_id_unsafe", "letters, digits, dot, dash and underscore, at most 64")
    return task, hashlib.sha256(raw).hexdigest()


def task_card(task: dict) -> dict:
    card = {"record_type": task["record_type"]}
    for name in TEXT_FIELDS:
        value = task.get(name)
        card[name] = value[:MAX_TEXT_CHARS] if isinstance(value, str) else None
    for name in LIST_FIELDS:
        value = task.get(name)
        card[name] = [item[:200] for item in value if isinstance(item, str)][:50] if isinstance(value, list) else []
    authority = task.get("model_calls_authorized")
    card["model_calls_authorized"] = authority if isinstance(authority, bool) else None
    return card


def list_files(folder: Path) -> list[dict]:
    rows, base = [], folder.resolve()
    for current, directories, names in os.walk(folder):  # links to folders are listed, never followed
        directories.sort()
        linked = [name for name in directories if (Path(current) / name).is_symlink()]
        for name in sorted(names + linked):
            path = Path(current) / name
            relative = path.relative_to(folder).as_posix()
            if path.is_symlink() or not path.is_file() or base not in path.resolve().parents:
                rows.append({"name": relative, "readable": False})
            else:
                digest = hashlib.sha256()
                with open(path, "rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                rows.append({"name": relative, "size_bytes": path.stat().st_size, "sha256": digest.hexdigest()})
            if len(rows) >= MAX_FILES:
                return rows
    return rows


def load_output_schema(folder: Path) -> dict | None:
    path = folder / "contracts" / "output.schema.json"
    if not path.exists() and not path.is_symlink():
        return None
    schema = strict_json(read_regular(path, MAX_SCHEMA_BYTES, "output_schema_unreadable"))
    if not isinstance(schema, dict):
        raise Refused("output_schema_unreadable", "not a JSON object")
    return schema


def output_card(schema: dict | None) -> dict:
    if schema is None:
        return {"schema": None, "type": None, "required_fields": [], "extra_fields_allowed": True}
    required = schema.get("required")
    return {"schema": "contracts/output.schema.json",
            "type": schema.get("type") if isinstance(schema.get("type"), str) else None,
            "required_fields": [name for name in required if isinstance(name, str)] if isinstance(required, list) else [],
            "extra_fields_allowed": schema.get("additionalProperties") is not False}


def results_card(root: Path, node_id: str) -> dict:
    relative = f"{RESULTS_BASE}/{node_id}"
    folder = confined(root, relative)
    names = sorted(name for name in os.listdir(folder) if re.fullmatch(r"result-\d{3}\.json", name)) \
        if folder.is_dir() and not folder.is_symlink() else []
    return {"folder": relative, "count": len(names), "latest": names[-1] if names else None}


def read_assignment(root: Path, step_relative: str = STEP_DEFAULT) -> dict:
    folder = step_folder(root, step_relative)
    task, digest = load_task(folder)
    return {"record_type": RECORD_TYPE, "step_folder": step_relative, "task": task_card(task), "task_sha256": digest,
            "files": list_files(folder), "output": output_card(load_output_schema(folder)),
            "results": results_card(root, task["node_id"]), "next": NEXT}


def read_step_file(root: Path, name, step_relative: str = STEP_DEFAULT) -> dict:
    """One UTF-8 text file of the step folder, named relative to that folder."""
    folder = step_folder(root, step_relative)
    if not safe_relative(name):
        raise Refused("unsafe_path", str(name)[:120])
    path = confined(root, f"{step_relative}/{name}")
    if folder.resolve() not in path.resolve().parents:
        raise Refused("path_leaves_step_folder", name[:120])
    data = read_regular(path, MAX_TEXT_BYTES, "file_missing")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("not_text", "the file is not UTF-8 text") from None
    return {"name": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "text": text}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print the assignment of the current focused step as one JSON object.")
    parser.add_argument("--root", help="workspace root; default the folder that holds .baltor, else the current folder")
    parser.add_argument("--step-dir", default=STEP_DEFAULT, help="step folder relative to the root")
    parser.add_argument("--file", help="print this text file of the step folder instead, for example node_context.md")
    options = parser.parse_args(argv)
    try:
        root = workspace_root(options.root)
        answer = read_step_file(root, options.file, options.step_dir) if options.file \
            else read_assignment(root, options.step_dir)
    except Refused as error:
        print(json.dumps({"error": error.code, "detail": error.detail}))
        return 2
    except OSError as error:
        print(json.dumps({"error": "os_error", "detail": type(error).__name__}))
        return 2
    sys.stdout.write(json.dumps(answer, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

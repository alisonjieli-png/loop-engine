#!/usr/bin/env python3
"""Typed CRUD for the engine's policy files, instead of sed and json.dump.

WHY NOT A DATABASE
The obvious answer to "stop hand-editing JSON" is to put the data behind a
queryable store. For run records and intelligence that is right, and this
repo already does it (core.record_operations, core.duckdb_catalog,
core.store_serve). For CONFORMANCE POLICY it is wrong. `forbidden_paths.json`
is read by `open()` + `json.load()` at scan time in api_quality.py and
architecture_contract.py, and the conformance gate has to run on a fresh
checkout, in CI, with no database, no daemon, and no import of the engine's
storage stack. A policy file that needs infrastructure to read turns the
gate into something that can be unavailable.

So the fix for hand-editing is not a database. It is a typed accessor that
makes the two ways of damaging the file impossible:

  * `sed` on structured data -- silent no-match, or a match in the wrong
    place. Used in this session on this exact file.
  * `json.dump(..., sort_keys=True)` -- rewrites every line. Done once in
    this session on this exact file: a 3-line change arrived as an 833-line
    diff, which no reviewer reads.

`set_entry` and `add_to_list` reserialize ONLY the value being changed and
splice it into the original text, so the diff is the change and nothing
else. Every write states which key it touched and how many lines moved.

Usage:
    python3 tools/policy_edit.py get subprocess_allowed_modules
    python3 tools/policy_edit.py add subprocess_allowed_modules core/x.py
    python3 tools/policy_edit.py remove subprocess_allowed_modules core/x.py
    python3 tools/policy_edit.py keys
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_POLICY = (Path(__file__).resolve().parents[1]
                  / "src" / "loop_engine" / "forbidden_paths.json")


class PolicyEditError(RuntimeError):
    """A policy edit was refused rather than applied wrongly."""


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PolicyEditError(f"{path} is not readable JSON: {exc}") from exc


def _closing_indent(block: str, fallback: str) -> str:
    """Read the indentation the file uses for the closing bracket.

    Not the same as the key's indentation, and assuming so is a real diff:
    the engine's own policy file indents its keys by one space and closes
    its lists at column zero, so `indent + "]"` turned `],` into ` ],` on
    every edit. A round trip that is not byte-identical is a tool that
    edits more than it was asked to.
    """
    line = block.splitlines()[-1]
    if line.strip().startswith("]"):
        return line[:len(line) - len(line.lstrip())]
    return fallback


def _item_indent(block: str, fallback: str) -> str:
    """Read the indentation the file already uses for list items.

    Assuming it instead (key indent plus two spaces) silently re-indented
    every existing entry, so a one-line addition arrived as a five-line
    diff. Preserving a file's own style is the whole job here; a tool that
    reformats while editing is the thing this tool replaces.
    """
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if stripped and stripped not in ("]", "[",):
            return line[:len(line) - len(line.lstrip())]
    return fallback


def _list_block(text: str, key: str) -> "tuple[int, int, str]":
    """Locate one top-level list literal by key, without parsing the file."""
    match = re.search(rf'^([ \t]*)"{re.escape(key)}"\s*:\s*\[',
                      text, re.MULTILINE)
    if match is None:
        raise PolicyEditError(
            f"no list named {key!r} in the policy file; "
            f"available keys are {', '.join(sorted(load_keys(text)))}")
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                return start, index + 1, match.group(1)
    raise PolicyEditError(f"unterminated list for {key!r}")


def load_keys(text: str) -> list:
    try:
        return sorted(json.loads(text))
    except ValueError:
        return []


def add_to_list(path: Path, key: str, value: str) -> dict:
    """Append one entry to a list, touching only that list's lines."""
    text = path.read_text(encoding="utf-8")
    data = load(path)
    if key not in data:
        # Ordered before the type check on purpose: a missing key and a
        # wrong-typed key are different problems, and reporting "NoneType,
        # not a list" for a typo tells the caller nothing about which keys
        # exist. A closed vocabulary refused without stating itself leaves
        # the next attempt to guess again.
        raise PolicyEditError(
            f"no key {key!r} in the policy file; available keys are "
            f"{', '.join(sorted(data))}")
    current = data[key]
    if not isinstance(current, list):
        raise PolicyEditError(
            f"{key!r} is {type(current).__name__}, not a list")
    if value in current:
        return {"changed": False, "why": f"{value!r} is already present",
                "count": len(current)}
    start, end, indent = _list_block(text, key)
    inner = _item_indent(text[start:end], indent + "  ")
    body = ",\n".join(f'{inner}{json.dumps(item)}' for item in [*current, value])
    closing = _closing_indent(text[start:end], indent)
    replacement = "[\n" + body + "\n" + closing + "]"
    updated = text[:start] + replacement + text[end:]
    json.loads(updated)          # refuse to write anything unparsable
    before_lines = text.count("\n")
    path.write_text(updated, encoding="utf-8")
    return {"changed": True, "key": key, "added": value,
            "count": len(current) + 1,
            "lines_moved": abs(updated.count("\n") - before_lines) + 1}


def remove_from_list(path: Path, key: str, value: str) -> dict:
    text = path.read_text(encoding="utf-8")
    data = load(path)
    if key not in data:
        raise PolicyEditError(
            f"no key {key!r} in the policy file; available keys are "
            f"{', '.join(sorted(data))}")
    current = data[key]
    if not isinstance(current, list):
        raise PolicyEditError(
            f"{key!r} is {type(current).__name__}, not a list")
    if value not in current:
        return {"changed": False, "why": f"{value!r} is not present",
                "count": len(current)}
    remaining = [item for item in current if item != value]
    start, end, indent = _list_block(text, key)
    inner = _item_indent(text[start:end], indent + "  ")
    body = ",\n".join(f'{inner}{json.dumps(item)}' for item in remaining)
    closing = _closing_indent(text[start:end], indent)
    replacement = ("[\n" + body + "\n" + closing + "]") if remaining else "[]"
    updated = text[:start] + replacement + text[end:]
    json.loads(updated)
    path.write_text(updated, encoding="utf-8")
    return {"changed": True, "key": key, "removed": value,
            "count": len(remaining)}


def self_test() -> dict:
    """Prove surgical edits and that damage modes are refused."""
    import tempfile

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:150]})

    original = (
        '{\n'
        ' "untouched_before": {\n  "a": 1,\n  "b": 2\n },\n'
        ' "subprocess_allowed_modules": [\n'
        '  "core/one.py",\n'
        '  "core/two.py"\n'
        ' ],\n'
        ' "untouched_after": ["x", "y"]\n'
        '}\n')
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "policy.json"
        path.write_text(original, encoding="utf-8")

        result = add_to_list(path, "subprocess_allowed_modules", "core/new.py")
        after = path.read_text(encoding="utf-8")
        check("append_adds_the_entry",
              json.loads(after)["subprocess_allowed_modules"]
              == ["core/one.py", "core/two.py", "core/new.py"],
              str(result))
        # The whole point: neighbouring keys are byte-identical.
        check("neighbouring_keys_are_untouched",
              '"untouched_before": {\n  "a": 1,\n  "b": 2\n }' in after
              and '"untouched_after": ["x", "y"]' in after,
              "json.dump(sort_keys=True) rewrites these; this must not")
        # A real diff, not a zip: inserting a line shifts every line after
        # it, so zip-comparison reports the whole tail as changed and the
        # measurement says nothing. This is the same class of mistake as
        # the json.dump diff the tool exists to prevent.
        import difflib
        delta = [line for line in difflib.unified_diff(
            original.splitlines(), after.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        check("the_diff_is_the_change_and_nothing_else", len(delta) <= 3,
              f"{len(delta)} diff lines: {delta}")

        again = add_to_list(path, "subprocess_allowed_modules", "core/new.py")
        check("adding_twice_is_a_no_op_not_a_duplicate",
              again["changed"] is False
              and json.loads(path.read_text())[
                  "subprocess_allowed_modules"].count("core/new.py") == 1)

        removed = remove_from_list(path, "subprocess_allowed_modules", "core/one.py")
        check("remove_takes_exactly_one_entry",
              json.loads(path.read_text())["subprocess_allowed_modules"]
              == ["core/two.py", "core/new.py"], str(removed))

        try:
            add_to_list(path, "no_such_key", "v")
            check("an_unknown_key_refusal_names_the_real_keys", False)
        except PolicyEditError as exc:
            check("an_unknown_key_refusal_names_the_real_keys",
                  "subprocess_allowed_modules" in str(exc), str(exc)[:110])

        try:
            add_to_list(path, "untouched_before", "v")
            check("editing_a_non_list_is_refused", False)
        except PolicyEditError as exc:
            check("editing_a_non_list_is_refused", "not a list" in str(exc))

    return {"module": "tools.policy_edit", "tests": tests,
            "passed": all(item["passed"] for item in tests)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["get", "add", "remove", "keys", "self-test"])
    ap.add_argument("key", nargs="?", default="")
    ap.add_argument("value", nargs="?", default="")
    ap.add_argument("--file", default=str(DEFAULT_POLICY))
    args = ap.parse_args()
    path = Path(args.file)

    if args.action == "self-test":
        result = self_test()
        for item in result["tests"]:
            print(("  PASS  " if item["passed"] else "  FAIL  ")
                  + item["test"] + (f"   -- {item['detail']}" if item["detail"] else ""))
        print(f"\n  {sum(t['passed'] for t in result['tests'])}"
              f"/{len(result['tests'])}")
        return 0 if result["passed"] else 1
    if args.action == "keys":
        for key, value in sorted(load(path).items()):
            kind = type(value).__name__
            size = len(value) if isinstance(value, (list, dict)) else ""
            print(f"  {key:44} {kind:6} {size}")
        return 0
    if not args.key:
        raise SystemExit("this action needs a key")
    if args.action == "get":
        print(json.dumps(load(path).get(args.key), indent=2))
        return 0
    if not args.value:
        raise SystemExit("this action needs a value")
    try:
        result = (add_to_list if args.action == "add" else remove_from_list)(
            path, args.key, args.value)
    except PolicyEditError as exc:
        print(f"refused: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read the declarations of a GDScript file and check a Baltor Godot component package against its contract card.

    python3 inspect_gdscript.py PACKAGE_DIR    check the package's component script against component.json
    python3 inspect_gdscript.py SCRIPT.gd      print the declarations of one script as JSON

Standard library only (Python 3.10 or later). The reader handles the top level of a GDScript 2 file (Godot 4):
class_name, extends, signals, exported and other variables, constants, enums, inner class names and function
signatures, with the "##" documentation comment above each. Function bodies, inner class members, comments and
string contents are skipped, so text inside them cannot look like a declaration. It reads declarations only; it
does not type-check or run anything. The Godot engine remains the authority on whether a script compiles.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

CARD_NAME = "component.json"
TEST_FOLDER = "tests"
TEST_BASE = '"../baltor_test.gd"'
MINIMUM_TESTS = 4
#: Annotations that stand alone: they group inspector fields and never export the next variable themselves.
STANDALONE_ANNOTATIONS = ("@export_group", "@export_subgroup", "@export_category")
CONTRACT_LISTS = ("signals", "exports", "properties", "methods", "enums")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INTEGER = re.compile(r"[+-]?(?:0x[0-9A-Fa-f_]+|0b[01_]+|[0-9][0-9_]*)")
_FLOAT = re.compile(r"[+-]?(?:[0-9][0-9_]*\.[0-9_]*|\.[0-9][0-9_]*|[0-9][0-9_]*)(?:[eE][+-]?[0-9]+)?")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\", "0": "\0"}


def logical_lines(source: str) -> list:
    """Split GDScript source into logical lines with comments removed and strings kept.

    Each row is a dict: "line" (first physical line, from 1), "end_line", "indent" (leading whitespace of the
    first physical line), "code" (the statement on one line), "doc" (the "##" comment lines directly above,
    without the markers) and "detached_docs" (earlier "##" blocks separated from the statement by blank lines).
    Bracketed continuations and backslash continuations join into one logical line.
    """
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    rows, pending_doc, detached = [], [], []
    position, line, length = 0, 1, len(text)
    while position < length:
        end = text.find("\n", position)
        end = length if end < 0 else end
        physical = text[position:end]
        stripped = physical.strip()
        if not stripped:
            if pending_doc:
                detached.append(pending_doc)
                pending_doc = []
            position, line = end + 1, line + 1
            continue
        if stripped.startswith("#"):
            if stripped.startswith("##"):
                body = stripped[2:]
                pending_doc.append(body[1:] if body.startswith(" ") else body)
            position, line = end + 1, line + 1
            continue
        indent = physical[: len(physical) - len(physical.lstrip())]
        start_line = line
        position += len(indent)
        code, depth = [], 0
        while position < length:
            char = text[position]
            if char in "\"'":
                closing = _string_end(text, position)
                token = text[position:closing]
                code.append(token)
                line += token.count("\n")
                position = closing
                continue
            if char == "#":
                newline = text.find("\n", position)
                position = length if newline < 0 else newline
                continue
            if char == "\\" and text.startswith("\n", position + 1):
                code.append(" ")
                position, line = position + 2, line + 1
                continue
            if char == "\n":
                if depth > 0:
                    code.append(" ")
                    position, line = position + 1, line + 1
                    continue
                break
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth = max(0, depth - 1)
            code.append(char)
            position += 1
        rows.append({"line": start_line, "end_line": line, "indent": indent, "code": "".join(code).strip(),
                     "doc": pending_doc, "detached_docs": detached})
        pending_doc, detached = [], []
        position, line = position + 1, line + 1
    return rows


def _string_end(text: str, start: int) -> int:
    """The index just after the string literal that starts at ``start`` (a quote character)."""
    quote = text[start]
    if text.startswith(quote * 3, start):
        index = start + 3
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text.startswith(quote * 3, index):
                return index + 3
            index += 1
        return len(text)
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        if char == "\n":
            return index
        index += 1
    return len(text)


def _scan(text: str, stops: str, start: int = 0) -> int:
    """The index of the first character of ``stops`` outside brackets and strings, or len(text)."""
    depth, index = 0, start
    while index < len(text):
        char = text[index]
        if char in "\"'":
            index = _string_end(text, index)
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif depth == 0 and char in stops:
            return index
        index += 1
    return len(text)


def _split(text: str, separator: str = ",") -> list:
    """Split at top-level separators, ignoring separators inside brackets and strings."""
    parts, start = [], 0
    while start <= len(text):
        stop = _scan(text, separator, start)
        part = text[start:stop].strip()
        if part:
            parts.append(part)
        start = stop + 1
    return parts


def _squash(text: str) -> str:
    """Whitespace outside strings collapsed to single spaces, and no space just inside brackets."""
    out, index = [], 0
    while index < len(text):
        char = text[index]
        if char in "\"'":
            closing = _string_end(text, index)
            out.append(text[index:closing])
            index = closing
            continue
        if char.isspace():
            if out and not out[-1].endswith((" ", "(", "[", "{")):
                out.append(" ")
            index += 1
            continue
        if char in ")]}" and out and out[-1] == " ":
            out.pop()
        out.append(char)
        index += 1
    return "".join(out).strip()


def _matching(text: str, open_index: int) -> int:
    """The index of the bracket that closes the one at ``open_index``."""
    depth, index = 0, open_index
    while index < len(text):
        char = text[index]
        if char in "\"'":
            index = _string_end(text, index)
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return len(text)


def _argument(text: str) -> str:
    """One parameter normalised to "name", "name: Type", "name: Type = default" or "name := default"."""
    match = _IDENTIFIER.match(text.strip())
    if not match:
        return _squash(text)
    name, rest = match.group(0), text.strip()[match.end():].strip()
    if rest.startswith(":="):
        return f"{name} := {_squash(rest[2:])}"
    kind, default = None, None
    if rest.startswith(":"):
        stop = _scan(rest, "=", 1)
        kind = _squash(rest[1:stop])
        rest = rest[stop:]
    if rest.startswith("="):
        default = _squash(rest[1:])
    words = [name] if kind is None else [f"{name}: {kind}"]
    if default is not None:
        words.append(f"= {default}")
    return " ".join(words)


def literal_value(expression: "str | None"):
    """The JSON value of a simple GDScript literal (bool, int, float, plain string, null), else the squashed text."""
    if expression is None:
        return None
    text = _squash(expression)
    if text in ("true", "false"):
        return text == "true"
    if text == "null":
        return None
    if _INTEGER.fullmatch(text):
        sign = -1 if text.startswith("-") else 1
        digits = text.lstrip("+-").replace("_", "")
        base = 16 if digits[:2].lower() == "0x" else 2 if digits[:2].lower() == "0b" else 10
        return sign * int(digits[2:] if base != 10 else digits, base)
    if _FLOAT.fullmatch(text) and any(mark in text for mark in ".eE"):
        value = float(text.replace("_", ""))
        return value if math.isfinite(value) else text
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0] and _string_end(text, 0) == len(text) \
            and not text.startswith(text[0] * 3):
        body, out, index = text[1:-1], [], 0
        while index < len(body):
            if body[index] == "\\" and index + 1 < len(body):
                out.append(_ESCAPES.get(body[index + 1], body[index + 1]))
                index += 2
                continue
            out.append(body[index])
            index += 1
        return "".join(out)
    return text


def _take_annotation(text: str) -> tuple:
    """(annotation with any arguments, remaining text) for text that starts with "@"."""
    match = _IDENTIFIER.match(text, 1)
    end = match.end() if match else 1
    rest = text[end:]
    if rest.lstrip().startswith("("):
        open_index = end + (len(rest) - len(rest.lstrip()))
        close = _matching(text, open_index)
        return _squash(text[: close + 1]), text[close + 1:].strip()
    return text[:end], rest.strip()


def _variable(text: str) -> dict:
    """Parse the part of a variable declaration after "var"."""
    match = _IDENTIFIER.match(text)
    name = match.group(0) if match else text
    rest = text[match.end():].strip() if match else ""
    kind, default, inferred = None, None, False
    if rest.startswith(":="):
        inferred = True
        rest = rest[2:].strip()
        stop = _scan(rest, ":")
        default, rest = rest[:stop].strip(), rest[stop:]
    else:
        if rest.startswith(":"):
            stop = _scan(rest, "=:", 1)
            kind = _squash(rest[1:stop]) or None
            rest = rest[stop:].strip()
        if rest.startswith("=") and not rest.startswith("=="):
            rest = rest[1:].strip()
            stop = _scan(rest, ":")
            default, rest = rest[:stop].strip(), rest[stop:]
    return {"name": name, "type": kind, "default_text": _squash(default) if default else None,
            "inferred": inferred, "accessors": bool(rest.strip())}


def _function(text: str) -> "dict | None":
    """Parse a function declaration that starts after "func"."""
    match = _IDENTIFIER.match(text)
    if not match:
        return None
    open_index = text.find("(", match.end())
    if open_index < 0:
        return None
    close = _matching(text, open_index)
    arguments = [_argument(part) for part in _split(text[open_index + 1:close])]
    rest = text[close + 1:].strip()
    returns = None
    if rest.startswith("->"):
        stop = _scan(rest, ":", 2)
        returns = _squash(rest[2:stop])
        rest = rest[stop:]
    body = rest[1:].strip() if rest.startswith(":") else rest
    return {"name": match.group(0), "arguments": arguments, "returns": returns, "inline_body": bool(body)}


def parse_source(source: str) -> dict:
    """The top-level declarations of one GDScript source text."""
    parsed = {"class_name": None, "extends": None, "tool": False, "icon": None, "class_doc": "", "signals": [],
              "exports": [], "variables": [], "constants": [], "enums": [], "methods": [], "inner_classes": []}
    pending, pending_doc, header_only = [], "", True
    for row in logical_lines(source):
        if row["indent"]:
            continue
        code, annotations = row["code"], []
        while code.startswith("@"):
            annotation, code = _take_annotation(code)
            annotations.append(annotation)
        for annotation in annotations:
            if annotation == "@tool":
                parsed["tool"] = True
            elif annotation.startswith("@icon("):
                parsed["icon"] = literal_value(annotation[6:-1])
        doc = "\n".join(row["doc"]).strip()
        if header_only and not parsed["class_doc"] and row["detached_docs"]:
            parsed["class_doc"] = "\n".join(row["detached_docs"][0]).strip()
        if not code:
            pending += [item for item in annotations if not item.startswith(STANDALONE_ANNOTATIONS)]
            pending_doc = pending_doc or doc
            continue
        annotations, pending = pending + annotations, []
        doc, pending_doc = doc or pending_doc, ""
        keyword = _IDENTIFIER.match(code)
        word = keyword.group(0) if keyword else ""
        place = {"line": row["line"], "end_line": row["end_line"], "doc": doc}
        if word == "class_name":
            found = re.match(r"class_name\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+extends\s+(.+))?$", code)
            if found:
                parsed["class_name"] = found.group(1)
                if found.group(2):
                    parsed["extends"] = _squash(found.group(2))
            continue
        if word == "extends":
            parsed["extends"] = _squash(code[len("extends"):])
            continue
        header_only = False
        static = word == "static"
        if static:
            code = code[len("static"):].strip()
            keyword = _IDENTIFIER.match(code)
            word = keyword.group(0) if keyword else ""
        body = code[len(word):].strip()
        if word == "signal":
            found = _IDENTIFIER.match(body)
            if not found:
                continue
            arguments = []
            if "(" in body:
                open_index = body.index("(")
                arguments = [_argument(part) for part in _split(body[open_index + 1:_matching(body, open_index)])]
            parsed["signals"].append({"name": found.group(0), "arguments": arguments, **place})
        elif word == "var":
            variable = _variable(body)
            exports = [item for item in annotations if item.startswith("@export")]
            row_out = {"name": variable["name"], "type": variable["type"], "default": literal_value(
                variable["default_text"]), "inferred": variable["inferred"], "static": static, **place}
            if exports:
                row_out["annotation"] = exports[-1]
                parsed["exports"].append(row_out)
            else:
                row_out["onready"] = "@onready" in annotations
                parsed["variables"].append(row_out)
        elif word == "const":
            variable = _variable(body)
            parsed["constants"].append({"name": variable["name"], "type": variable["type"],
                                        "value": literal_value(variable["default_text"]), **place})
        elif word == "enum":
            found = re.match(r"([A-Za-z_][A-Za-z0-9_]*)?\s*\{", body)
            if found:
                open_index = body.index("{")
                values = [_IDENTIFIER.match(part).group(0) for part in
                          _split(body[open_index + 1:_matching(body, open_index)]) if _IDENTIFIER.match(part)]
                parsed["enums"].append({"name": found.group(1), "values": values, **place})
        elif word == "func":
            function = _function(body)
            if function:
                parsed["methods"].append({**function, "static": static, **place})
        elif word == "class":
            found = _IDENTIFIER.match(body)
            if found:
                parsed["inner_classes"].append({"name": found.group(0), **place})
    return parsed


def parse_file(path) -> dict:
    """The declarations of one .gd file (UTF-8)."""
    return parse_source(Path(path).read_text(encoding="utf-8"))


def contract_from_parse(parsed: dict, placement: str, depends_on=()) -> dict:
    """The contract card section a parsed component script implies: its public surface and where it goes."""
    contract = {"class_name": parsed["class_name"], "extends": parsed["extends"],
                "signals": [{"name": row["name"], "arguments": row["arguments"]} for row in parsed["signals"]],
                "exports": [], "methods": [], "placement": placement, "depends_on": list(depends_on)}
    for row in parsed["exports"]:
        entry = {"name": row["name"], "type": row["type"], "default": row["default"]}
        if row["annotation"] != "@export":
            entry["annotation"] = row["annotation"]
        contract["exports"].append(entry)
    properties = [{"name": row["name"], "type": row["type"]} | ({"static": True} if row["static"] else {})
                  for row in parsed["variables"] if not row["name"].startswith("_")]
    if properties:
        contract["properties"] = properties
    for row in parsed["methods"]:
        if row["name"].startswith("_"):
            continue
        entry = {"name": row["name"], "arguments": row["arguments"], "returns": row["returns"]}
        if row["static"]:
            entry["static"] = True
        contract["methods"].append(entry)
    enums = [{"name": row["name"], "values": row["values"]} for row in parsed["enums"]
             if row["name"] and not row["name"].startswith("_")]
    if enums:
        contract["enums"] = enums
    return contract


def compare_contract(contract: dict, parsed: dict) -> list:
    """Every difference between a contract card section and a parsed script, as readable sentences."""
    actual = contract_from_parse(parsed, contract.get("placement", ""), contract.get("depends_on", []))
    problems = []
    for key in ("class_name", "extends"):
        if contract.get(key) != actual[key]:
            problems.append(f"{key}: the card has {contract.get(key)!r}, the script has {actual[key]!r}")
    for key in CONTRACT_LISTS:
        expected = {row["name"]: row for row in contract.get(key, [])}
        found = {row["name"]: row for row in actual.get(key, [])}
        for name in sorted(set(expected) - set(found)):
            problems.append(f"{key}: {name} is in the card but not in the script")
        for name in sorted(set(found) - set(expected)):
            problems.append(f"{key}: {name} is in the script but not in the card")
        for name in sorted(set(expected) & set(found)):
            if expected[name] != found[name]:
                problems.append(f"{key}: {name} differs: the card has {json.dumps(expected[name], sort_keys=True)}, "
                                f"the script has {json.dumps(found[name], sort_keys=True)}")
    placement = contract.get("placement", "")
    if not (isinstance(placement, str) and placement.startswith("res://") and placement.endswith("/")):
        problems.append(f"placement: {placement!r} is not a res:// folder ending with /")
    return problems


def check_package(directory) -> dict:
    """Check a package folder: its component script against component.json, its engine tests and file digests."""
    root = Path(directory)
    card = json.loads((root / CARD_NAME).read_text(encoding="utf-8"))
    identity = card["job"]["identity"]
    contract = card["contract"]
    problems, test_names = [], []
    script = root / f"{identity}.gd"
    parsed = parse_file(script) if script.is_file() else None
    if parsed is None:
        problems.append(f"{script.name} is missing")
    else:
        problems += compare_contract(contract, parsed)
    tests = root / TEST_FOLDER / f"test_{identity}.gd"
    if tests.is_file():
        tested = parse_file(tests)
        test_names = [row["name"] for row in tested["methods"] if row["name"].startswith("test_")]
        if len(test_names) < MINIMUM_TESTS:
            problems.append(f"{tests.name} declares {len(test_names)} test methods, fewer than {MINIMUM_TESTS}")
        if tested["extends"] != TEST_BASE:
            problems.append(f"{tests.name} extends {tested['extends']}, not {TEST_BASE}")
    else:
        problems.append(f"{TEST_FOLDER}/test_{identity}.gd is missing")
    for row in card.get("files", []):
        path = root / row["path"]
        if not path.is_file():
            problems.append(f"{row['path']} is listed in the card but missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            problems.append(f"{row['path']} does not match its digest in the card")
    return {"identity": identity, "class_name": None if parsed is None else parsed["class_name"],
            "tests": test_names, "problems": problems}


def main(argv=None) -> int:
    """Command line: a package folder is checked, a .gd file is parsed; JSON goes to standard output."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: python3 inspect_gdscript.py PACKAGE_DIR | SCRIPT.gd", file=sys.stderr)
        return 2
    target = Path(arguments[0])
    if target.is_dir():
        report = check_package(target)
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if not report["problems"] else 1
    if target.suffix == ".gd" and target.is_file():
        print(json.dumps(parse_file(target), indent=1, sort_keys=True))
        return 0
    print(f"not a package folder or .gd file: {target}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

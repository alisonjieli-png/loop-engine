"""Check a project's values and render the project commands section for the host. Effects: reads the values file and the section template; writes nothing; no network, no model call.

The host runs this before it composes the section into a step's instruction
files. It reads the values as JSON, {"values": {"MARKER": "value", ...}} with an
optional "description", from a file or from standard input (--values -), and
the template from --template (default: AGENTS.md of this package).

The rules below are a host-side filter. They refuse the listed installer and
package-runner words and shell operators, but they cannot prove that a command
fetches nothing: many build and test tools download dependencies on their own.
Run steps without network access, or install dependencies before the step.

    every marker in the template gets exactly one value, and no value is extra;
    each value is one line of 1 to 300 characters without backticks or double braces;
    a command value is none or one simple command: no ; & | < > or $( and no
    installer or package-runner word such as install, npx, uvx, pipx or npm ci;
    TEST_COMMAND is the command every step needs, so it is never none;
    TEST_ONE_FILE_COMMAND names FILE once and FORMAT_COMMAND names FILES once,
    unless the value is none;
    SOURCE_DIRS, TEST_DIRS and PROTECTED_PATHS are comma-separated relative
    paths or glob patterns made of letters, digits and . _ - / * ? [ ] @ +,
    without .. and without a leading / or -; only PROTECTED_PATHS may be none.

The answer is one JSON object: the rendered text and its SHA-256, or every
problem found with the marker it belongs to. Exit 0: rendered. Exit 1: a value
breaks a rule. Exit 2: the values or the template cannot be read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MARKER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
COMMAND_MARKERS = ("BUILD_COMMAND", "TEST_COMMAND", "TEST_ONE_FILE_COMMAND", "LINT_COMMAND", "FORMAT_COMMAND")
PATH_MARKERS = ("SOURCE_DIRS", "TEST_DIRS", "PROTECTED_PATHS")
REQUIRED_COMMAND = "TEST_COMMAND"
NONE_ALLOWED_PATHS = ("PROTECTED_PATHS",)
SLOT_WORDS = {"TEST_ONE_FILE_COMMAND": "FILE", "FORMAT_COMMAND": "FILES"}
MAX_VALUE_CHARACTERS = 300
MAX_INPUT_BYTES = 256 * 1024
MAX_PATHS = 50
SHELL_OPERATORS = re.compile(r"[;&|<>]|\$\(")
PATH_ITEM = re.compile(r"[A-Za-z0-9._*?/\[\]@+-]{1,200}\Z")
#: Words that install or fetch packages wherever they appear in a command.
FETCHING_WORDS = {"install", "npx", "pnpx", "bunx", "uvx", "pipx", "dlx", "curl", "wget"}
#: Program and first argument pairs that install, fetch or run packages that may not be present yet.
FETCHING_PAIRS = {("npm", "ci"), ("npm", "i"), ("npm", "add"), ("npm", "exec"), ("npm", "x"), ("pnpm", "add"),
                  ("pnpm", "exec"), ("yarn", "add"), ("bun", "add"), ("uv", "add"), ("uv", "sync"), ("uv", "tool"),
                  ("uv", "pip"), ("poetry", "add"), ("cargo", "add"), ("go", "get"), ("gem", "fetch"),
                  ("dotnet", "restore"), ("git", "clone"), ("git", "fetch"), ("git", "pull"), ("git", "push")}
NEXT_RENDERED = "Compose the text into the step's instruction files. Put the same text in GEMINI.md for Gemini CLI."
NEXT_REFUSED = "Correct the values named in problems and run the check again. Do not compose this section until it passes."


class Unreadable(Exception):
    """The values, the template or the arguments cannot be read."""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # an argument error is refused input, answered as JSON
        raise Unreadable(f"arguments: {message}")


def parse(argv) -> argparse.Namespace:
    parser = Parser(prog="render_commands_section.py", description="Check values and render the section.")
    parser.add_argument("--values", required=True, help="the values JSON file, or - for standard input")
    parser.add_argument("--template", default=str(Path(__file__).resolve().parent.parent / "AGENTS.md"))
    return parser.parse_args(argv)


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


def read_text(source: str) -> str:
    try:
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1) if source == "-" else Path(source).read_bytes()
    except OSError as error:
        raise Unreadable(f"{source}: {error.strerror or error}") from None
    if len(data) > MAX_INPUT_BYTES:
        raise Unreadable(f"{source} is larger than {MAX_INPUT_BYTES} bytes")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Unreadable(f"{source} is not UTF-8 text") from None


def read_values(source: str) -> dict:
    try:
        document = strict_json(read_text(source))
    except ValueError as error:
        raise Unreadable(f"the values are not strict JSON: {error}") from None
    if not isinstance(document, dict) or not {"values"} <= set(document) <= {"values", "description"} \
            or not isinstance(document["values"], dict):
        raise Unreadable('the values file is one object with "values" and an optional "description"')
    return document["values"]


def command_problems(name: str, value: str) -> list:
    if value == "none":
        return [("required_command_is_none", f"{name} is needed by every step and cannot be none")] \
            if name == REQUIRED_COMMAND else []
    problems = []
    if SHELL_OPERATORS.search(value):
        problems.append(("shell_operator", f"{name} is one simple command without ; & | < > or $("))
    tokens = [token.strip("'\"") for token in value.split()]
    words = [Path(token).name.lower() for token in tokens]
    fetching = sorted({word for word in words if word in FETCHING_WORDS}
                      | {f"{first} {second}" for first, second in zip(words, words[1:]) if (first, second) in FETCHING_PAIRS})
    if fetching or "://" in value:
        problems.append(("installs_or_fetches", f"{name} names {fetching or ['a URL']}; commands never install or fetch"))
    slot = SLOT_WORDS.get(name)
    if slot and tokens.count(slot) != 1:
        problems.append(("slot_word_missing", f"{name} names {slot} once, in the place of the file paths"))
    return problems


def path_problems(name: str, value: str) -> list:
    if value == "none":
        return [] if name in NONE_ALLOWED_PATHS else [("paths_missing", f"{name} names at least one folder")]
    items = [item.strip() for item in value.split(",")]
    if not 1 <= len(items) <= MAX_PATHS:
        return [("paths_invalid", f"{name} holds 1 to {MAX_PATHS} comma-separated paths")]
    for item in items:
        if not PATH_ITEM.fullmatch(item) or item.startswith(("/", "-")) or ".." in item.split("/"):
            return [("paths_invalid", f"{name}: {item[:60]!r} is not a relative path or glob pattern made of path "
                                      "characters")]
    return []


def check(template: str, values: dict) -> list:
    """Every problem of the values against the template, as (marker, code, detail)."""
    wanted = set(MARKER.findall(template))
    problems = [(name, "value_missing", f"{name} has no value") for name in sorted(wanted - set(values))]
    problems += [(name, "value_extra", f"{name} is not a marker of the section") for name in sorted(set(values) - wanted)]
    for name in sorted(set(values) & wanted):
        value = values[name]
        if (not isinstance(value, str) or not value.strip() or value != value.strip()
                or len(value) > MAX_VALUE_CHARACTERS or any(ord(character) < 32 or ord(character) == 127
                                                            for character in value)
                or "`" in value or "{" * 2 in value or "}" * 2 in value):
            problems.append((name, "value_invalid", f"{name} is one trimmed line of 1 to {MAX_VALUE_CHARACTERS} "
                                                    "characters without backticks or double braces"))
            continue
        if name in COMMAND_MARKERS:
            problems += [(name, code, detail) for code, detail in command_problems(name, value)]
        elif name in PATH_MARKERS:
            problems += [(name, code, detail) for code, detail in path_problems(name, value)]
    return problems


def main(argv=None) -> int:
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
        values = read_values(options.values)
        template = read_text(options.template)
    except Unreadable as error:
        print(json.dumps({"result": "refused", "problems": [{"marker": None, "code": "input_unreadable",
                                                             "detail": str(error)}], "next": NEXT_REFUSED},
                         ensure_ascii=False, sort_keys=True))
        return 2
    problems = check(template, values)
    if problems:
        print(json.dumps({"result": "refused", "problems": [{"marker": marker, "code": code, "detail": detail}
                                                            for marker, code, detail in problems],
                          "next": NEXT_REFUSED}, ensure_ascii=False, sort_keys=True))
        return 1
    rendered = MARKER.sub(lambda match: values[match.group(1)], template)
    print(json.dumps({"result": "rendered", "text": rendered,
                      "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(), "next": NEXT_RENDERED},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

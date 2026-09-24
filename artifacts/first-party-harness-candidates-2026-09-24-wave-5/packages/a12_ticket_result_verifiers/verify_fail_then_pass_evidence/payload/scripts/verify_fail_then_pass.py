"""Check saved before and after test outputs and a diff for fail-then-pass evidence; reads the three named files only.

Effects: reads the files named by --before, --after and --diff below --root (one of
them may be "-" for standard input). Writes nothing, starts no process and uses no
network. Prints one JSON object. Exit status: 0 pass, 1 fail, 2 refused input.

Supported saved outputs: pytest (-v or -rA lines), python -m unittest -v, go test -v
or go test -json, cargo test, and JUnit XML. The diff is a unified diff, such as the
output of git diff, of the whole change: the new test and the fix together.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

TOOL = "verify-fail-then-pass-evidence"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_REQUESTED_TESTS = 50
LIST_LIMIT = 50
FORMATS = ("pytest", "unittest", "go", "cargo", "junit")
FAILING = ("failed", "error")
#: When one test id is reported more than once, the most severe outcome is kept.
RANK = {"skipped": 0, "xfailed": 1, "passed": 2, "xpassed": 3, "error": 4, "failed": 5}


class Refused(Exception):
    """The input cannot be judged; the script exits 2 with this reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class Arguments(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print usage and exit 2
        raise Refused("bad_arguments", message)


# ---------------------------------------------------------------------------
# reading inputs
# ---------------------------------------------------------------------------

def confined_file(root: Path, value: str, label: str) -> Path:
    """Resolve a path below root, refusing '..', escapes through links and non-files."""
    if not value or "\x00" in value:
        raise Refused("bad_path", f"{label} names an empty path")
    raw = Path(value)
    if ".." in raw.parts:
        raise Refused("path_outside_root", f"{label} path {value!r} uses '..'")
    candidate = raw if raw.is_absolute() else root / raw
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refused("input_missing", f"{label} file {value!r} does not exist") from None
    if not resolved.is_relative_to(root):
        raise Refused("path_outside_root", f"{label} path {value!r} resolves outside --root")
    if not resolved.is_file():
        raise Refused("not_a_file", f"{label} path {value!r} is not a regular file")
    return resolved


def read_input(root: Path, value: str, label: str) -> tuple[str, dict]:
    if value == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        where = "standard input"
    else:
        with open(confined_file(root, value, label), "rb") as handle:
            data = handle.read(MAX_INPUT_BYTES + 1)
        where = value
    if len(data) > MAX_INPUT_BYTES:
        raise Refused("input_too_large", f"{label} holds more than {MAX_INPUT_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused("input_not_utf8", f"{label} is not UTF-8 text (byte {error.start})") from None
    return text, {"path": where, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


# ---------------------------------------------------------------------------
# test outputs
# ---------------------------------------------------------------------------

def record(results: dict, test_id: str, outcome: str) -> None:
    previous = results.get(test_id)
    if previous is None or RANK[outcome] > RANK[previous]:
        results[test_id] = outcome


PYTEST_WORD = r"(?P<word>(?:SUB)?(?:PASSED|FAILED|SKIPPED)|ERROR|XFAIL|XPASS)(?:\([^)\n]*\))?"
PYTEST_ID = r"(?P<id>[^\s\[]+::[^\s\[]+(?:\[.*?\])?)"
PYTEST_WORDS = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "SKIPPED": "skipped",
                "XFAIL": "xfailed", "XPASS": "xpassed", "SUBPASSED": "passed", "SUBFAILED": "failed",
                "SUBSKIPPED": "skipped"}
#: "tests/a.py::test_x PASSED [ 50%]", also with "SKIPPED (reason)" or a SUBFAILED(i=1) subtest word.
PYTEST_ID_FIRST = re.compile(r"^" + PYTEST_ID + r"\s+" + PYTEST_WORD + r"(?:\s+\(.*?\))?(?:\s+\[\s*\d+%\])?\s*$")
#: "FAILED tests/a.py::test_x - message" from -rA, and "[gw0] [ 50%] PASSED tests/a.py::test_x" from xdist.
PYTEST_WORD_FIRST = re.compile(r"^(?:\[gw\d+\]\s+\[\s*\d+%\]\s+)?" + PYTEST_WORD + r"\s+" + PYTEST_ID
                               + r"(?=\s+-\s|\s*$)")


def parse_pytest(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        line = line.rstrip()
        match = PYTEST_ID_FIRST.match(line) or PYTEST_WORD_FIRST.match(line)
        if match:
            record(results, match.group("id"), PYTEST_WORDS[match.group("word")])
    return results


UT_HEAD = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*) \((?P<where>[A-Za-z_][\w.]*)\)(?: \([^)]*\))?"
                     r"(?: \.\.\.(?: (?P<rest>.*))?)?$")
UT_DOC = re.compile(r"^.* \.\.\. (?P<rest>.*)$")
UT_SUMMARY = re.compile(r"^(?P<word>FAIL|ERROR|UNEXPECTED SUCCESS): (?P<name>[A-Za-z_]\w*) "
                        r"\((?P<where>[A-Za-z_][\w.]*)\)")
UT_SUMMARY_WORDS = {"FAIL": "failed", "ERROR": "error", "UNEXPECTED SUCCESS": "xpassed"}


def unittest_id(name: str, where: str) -> str:
    return where if where == name or where.endswith("." + name) else f"{where}.{name}"


def unittest_outcome(rest: str | None) -> str | None:
    rest = (rest or "").strip()
    if rest.startswith("skipped"):
        return "skipped"
    return {"ok": "passed", "FAIL": "failed", "ERROR": "error", "expected failure": "xfailed",
            "unexpected success": "xpassed"}.get(rest)


def parse_unittest(text: str) -> dict:
    results: dict = {}
    pending = None
    for line in text.splitlines():
        line = line.rstrip()
        summary = UT_SUMMARY.match(line)
        if summary:
            record(results, unittest_id(summary["name"], summary["where"]), UT_SUMMARY_WORDS[summary["word"]])
            pending = None
            continue
        segment, matched = line, False
        while True:  # Python 3.10 can print the next test on the line of a test whose subtest failed
            head = UT_HEAD.match(segment)
            if not head:
                break
            matched = True
            test_id = unittest_id(head["name"], head["where"])
            outcome = unittest_outcome(head["rest"])
            if outcome:
                record(results, test_id, outcome)
                pending = None
                break
            pending = test_id
            if not head["rest"]:
                break
            segment = head["rest"]
        if matched or not pending:
            continue
        doc = UT_DOC.match(line)
        outcome = unittest_outcome(doc["rest"] if doc else line)
        if outcome:
            record(results, pending, outcome)
            pending = None
    return results


GO_LINE = re.compile(r"^\s*--- (?P<word>PASS|FAIL|SKIP): (?P<id>\S+)")
GO_WORDS = {"PASS": "passed", "FAIL": "failed", "SKIP": "skipped", "pass": "passed", "fail": "failed",
            "skip": "skipped"}


def parse_go(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        match = GO_LINE.match(line)
        if match:
            record(results, match["id"], GO_WORDS[match["word"]])
            continue
        if line.startswith("{") and '"Action"' in line:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and isinstance(event.get("Test"), str) and event.get("Action") in GO_WORDS:
                record(results, event["Test"], GO_WORDS[event["Action"]])
    return results


CARGO_LINE = re.compile(r"^test (?P<id>\S(?:.*?\S)?) \.\.\. (?P<word>ok|FAILED|ignored)\b")
CARGO_WORDS = {"ok": "passed", "FAILED": "failed", "ignored": "skipped"}


def parse_cargo(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        match = CARGO_LINE.match(line.rstrip())
        if match:
            record(results, match["id"], CARGO_WORDS[match["word"]])
    return results


def parse_junit(text: str) -> dict:
    if not text.lstrip().startswith("<"):
        return {}
    if re.search(r"<!(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
        raise Refused("xml_declaration_refused", "JUnit XML with DOCTYPE or ENTITY declarations is refused")
    try:
        root = ElementTree.fromstring(text.encode("utf-8"))
    except ElementTree.ParseError as error:
        raise Refused("xml_unreadable", f"the XML does not parse: {error}") from None
    results: dict = {}
    for case in root.iter("testcase"):
        name = case.get("name") or ""
        if not name:
            continue
        classname = case.get("classname") or ""
        outcome = "passed"
        for nested in case:
            tag = nested.tag.lower() if isinstance(nested.tag, str) else ""
            if tag == "failure":
                outcome = "failed"
            elif tag == "error" and outcome != "failed":
                outcome = "error"
            elif tag == "skipped" and outcome == "passed":
                outcome = "xfailed" if nested.get("type") == "pytest.xfail" else "skipped"
        record(results, f"{classname}.{name}" if classname else name, outcome)
    return results


#: A test module that failed to import leaves no per-test line, so the run looks smaller than it is.
LOAD_TROUBLE = re.compile(r"(?m)^(?:ERROR collecting\b|.*\berrors? during collection\b|.*\bunittest\.loader\._FailedTest\b)")

PARSERS = {"pytest": parse_pytest, "unittest": parse_unittest, "go": parse_go, "cargo": parse_cargo,
           "junit": parse_junit}


def parse_output(text: str, chosen: str, label: str) -> tuple[str, dict]:
    if chosen != "auto":
        results = PARSERS[chosen](text)
        if not results:
            raise Refused("no_test_results", f"no {chosen} test results were found in {label}")
        return chosen, results
    if text.lstrip().startswith("<"):
        results = parse_junit(text)
        if results:
            return "junit", results
    best_name, best = "", {}
    for name in ("pytest", "unittest", "go", "cargo"):
        results = PARSERS[name](text)
        if len(results) > len(best):
            best_name, best = name, results
    if not best:
        raise Refused("no_test_results", f"no per-test results were recognized in {label}; "
                                         "see references/runner-formats.md for the accepted outputs")
    return best_name, best


# ---------------------------------------------------------------------------
# test identities
# ---------------------------------------------------------------------------

def strip_parameters(test_id: str) -> str:
    """Remove a trailing parameter part such as [2025-13-01] from a test id."""
    if not test_id.endswith("]"):
        return test_id
    depth = 0
    for index in range(len(test_id) - 1, -1, -1):
        if test_id[index] == "]":
            depth += 1
        elif test_id[index] == "[":
            depth -= 1
            if depth == 0:
                return test_id[:index] if index > 0 else test_id
    return test_id


def parameters_of(test_id: str) -> str:
    core = strip_parameters(test_id)
    return test_id[len(core) + 1:-1] if core != test_id else ""


def base_name(test_id: str, runner: str) -> str:
    core = strip_parameters(test_id)
    if "::" in core:
        return core.rsplit("::", 1)[1]
    if runner == "go":
        return core.split("/", 1)[0]
    if "." in core and " " not in core:
        return core.rsplit(".", 1)[1]
    return core


def match_requested(requested: str, results: dict, runner: str) -> tuple[list, str]:
    """Find the result ids for one requested test; refuse an id that names two tests."""
    if requested in results:
        return [requested], "exact"
    with_parameters = strip_parameters(requested) != requested
    requested_base = base_name(requested, runner)
    stages = (
        ("parameter_cases", [] if with_parameters else
         [test_id for test_id in results if strip_parameters(test_id) == requested]),
        ("suffix", [test_id for test_id in results
                    if any((test_id if with_parameters else strip_parameters(test_id)).endswith(separator + requested)
                           for separator in ("::", ".", "/"))]),
        ("base_name", [test_id for test_id in results if not with_parameters
                       and base_name(test_id, runner) == requested_base]),
    )
    for how, candidates in stages:
        if not candidates:
            continue
        cores = sorted({strip_parameters(test_id) for test_id in candidates})
        if len(cores) > 1:
            raise Refused("ambiguous_test_id", f"{requested!r} matches several tests: {cores[:5]}; "
                                               "give the full id as the runner prints it")
        return sorted(candidates), how
    return [], "not_found"


def group_outcome(ids: list, results: dict, moment: str) -> str:
    outcomes = [results[test_id] for test_id in ids]
    if not outcomes:
        return "missing"
    if moment == "before":
        for wanted in ("failed", "error"):
            if wanted in outcomes:
                return wanted
    elif all(outcome == "passed" for outcome in outcomes):
        return "passed"
    return max(outcomes, key=RANK.get)


# ---------------------------------------------------------------------------
# unified diff
# ---------------------------------------------------------------------------

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
BINARY_LINE = re.compile(r"^Binary files (.+) and (.+) differ$")
ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class FileDiff:
    def __init__(self) -> None:
        self.old_path: str | None = None
        self.new_path: str | None = None
        self.change = "modified"
        self.binary = False
        self.file_header = False
        self.hunks: list = []

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or ""


def unquote(value: str) -> tuple[str, str]:
    """Decode a C-style quoted path as git writes it; return the path and the text after it."""
    out = bytearray()
    index = 1
    while index < len(value):
        char = value[index]
        if char == '"':
            return out.decode("utf-8", "replace"), value[index + 1:]
        if char == "\\" and index + 1 < len(value):
            following = value[index + 1]
            octal = value[index + 1:index + 4]
            if len(octal) == 3 and all(digit in "01234567" for digit in octal):
                out.append(int(octal, 8) & 0xFF)
                index += 4
                continue
            if following in ESCAPES:
                out.append(ESCAPES[following])
                index += 2
                continue
        out.extend(char.encode("utf-8"))
        index += 1
    raise Refused("unreadable_diff", "a quoted path in the diff is not closed")


def strip_prefix(value: str | None, prefix: str) -> str | None:
    if value is None or value == "/dev/null":
        return None
    return value[len(prefix):] if value.startswith(prefix) else value


def header_path(value: str, prefix: str) -> str | None:
    if value.startswith('"'):
        value = unquote(value)[0]
    else:
        value = value.split("\t", 1)[0]
    return strip_prefix(value, prefix)


def git_header_paths(rest: str) -> tuple[str | None, str | None]:
    if rest.startswith('"'):
        old, remainder = unquote(rest)
        remainder = remainder.lstrip(" ")
        new = unquote(remainder)[0] if remainder.startswith('"') else remainder
        return strip_prefix(old, "a/"), strip_prefix(new, "b/")
    if ' "' in rest:
        position = rest.index(' "')
        return strip_prefix(rest[:position], "a/"), strip_prefix(unquote(rest[position + 1:])[0], "b/")
    for prefix_a, prefix_b in (("a/", "b/"), ("", "")):
        size = len(rest) - len(prefix_a) - len(prefix_b) - 1
        if size > 0 and size % 2 == 0 and rest.startswith(prefix_a):
            half = size // 2
            old = rest[len(prefix_a):len(prefix_a) + half]
            joint = rest[len(prefix_a) + half:len(prefix_a) + half + 1 + len(prefix_b)]
            new = rest[len(prefix_a) + half + 1 + len(prefix_b):]
            if old == new and joint == " " + prefix_b:
                return old, new
    if rest.count(" b/") == 1:
        old, new = rest.split(" b/")
        return strip_prefix(old, "a/"), new
    return None, None


def parse_diff(text: str) -> list:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    files: list = []
    current: FileDiff | None = None
    index, total = 0, len(lines)
    while index < total:
        line = lines[index]
        if line.startswith(("diff --cc ", "diff --combined ", "@@@ ")):
            raise Refused("combined_diff", f"line {index + 1}: a combined diff of a merge is not read; make the diff "
                                           "with git diff BASE HEAD, which compares two revisions")
        if line.startswith("diff --git "):
            current = FileDiff()
            current.old_path, current.new_path = git_header_paths(line[len("diff --git "):])
            files.append(current)
            index += 1
            continue
        if line.startswith("--- ") and index + 1 < total and lines[index + 1].startswith("+++ "):
            if current is None or current.file_header or current.hunks:
                current = FileDiff()
                files.append(current)
            old, new = header_path(line[4:], "a/"), header_path(lines[index + 1][4:], "b/")
            current.file_header = True
            if old is None:
                current.change = "added"
            else:
                current.old_path = old
            if new is None:
                current.change = "deleted"
            else:
                current.new_path = new
            index += 2
            continue
        if line.startswith("@@"):
            if current is None:
                raise Refused("unreadable_diff", f"line {index + 1}: a hunk appears before any file header")
            match = HUNK_HEADER.match(line)
            if not match:
                raise Refused("unreadable_diff", f"line {index + 1}: unreadable hunk header")
            old_no, new_no = int(match.group(1)), int(match.group(3))
            old_left = int(match.group(2)) if match.group(2) is not None else 1
            new_left = int(match.group(4)) if match.group(4) is not None else 1
            hunk = {"header": match.group(5).strip(), "lines": []}
            current.hunks.append(hunk)
            index += 1
            while old_left > 0 or new_left > 0:
                if index >= total:
                    raise Refused("unreadable_diff", f"{current.path}: the diff ends inside a hunk")
                body = lines[index]
                index += 1
                if body.startswith("\\"):
                    continue
                tag, content = (body[:1], body[1:]) if body else (" ", "")
                if tag == " ":
                    hunk["lines"].append((" ", old_no, new_no, content))
                    old_no, new_no, old_left, new_left = old_no + 1, new_no + 1, old_left - 1, new_left - 1
                elif tag == "-":
                    hunk["lines"].append(("-", old_no, None, content))
                    old_no, old_left = old_no + 1, old_left - 1
                elif tag == "+":
                    hunk["lines"].append(("+", None, new_no, content))
                    new_no, new_left = new_no + 1, new_left - 1
                else:
                    raise Refused("unreadable_diff", f"{current.path}: line {index} does not belong to its hunk")
                if old_left < 0 or new_left < 0:
                    raise Refused("unreadable_diff", f"{current.path}: a hunk holds more lines than its header says")
            continue
        binary = BINARY_LINE.match(line)
        if binary:
            if current is None or current.file_header or current.hunks:
                current = FileDiff()
                current.old_path = strip_prefix(binary.group(1), "a/")
                current.new_path = strip_prefix(binary.group(2), "b/")
                files.append(current)
            current.binary = True
            if binary.group(1) == "/dev/null":
                current.change = "added"
            elif binary.group(2) == "/dev/null":
                current.change = "deleted"
        elif current is not None:
            if line.startswith("new file mode "):
                current.change = "added"
            elif line.startswith("deleted file mode "):
                current.change = "deleted"
            elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
                words = line.split(" ", 2)
                value = words[2]
                value = unquote(value)[0] if value.startswith('"') else value
                current.change = "renamed" if words[0] == "rename" else "copied"
                if words[1] == "from":
                    current.old_path = value
                else:
                    current.new_path = value
            elif line == "GIT binary patch":
                current.binary = True
        index += 1
    for item in files:
        if item.change == "added":
            item.old_path = None
        elif item.change == "deleted":
            item.new_path = None
    return files


# ---------------------------------------------------------------------------
# paths and definitions
# ---------------------------------------------------------------------------

TEST_FOLDERS = {"test", "tests", "testing", "__tests__", "spec", "specs", "e2e"}
TEST_NAME = re.compile(
    r"(?:test_.+\.py|.+_test\.py|conftest\.py|.+_test\.go|.+\.(?:test|spec)\.[cm]?[jt]sx?"
    r"|.+_(?:spec|test)\.rb|.+Tests?\.(?:java|kt|kts|cs|scala|groovy|swift|php)|Test.+\.(?:java|kt|php)"
    r"|.+Spec\.(?:scala|groovy|kt)|.+_tests?\.(?:rs|exs|dart|c|cc|cpp)|test_.+\.(?:c|cc|cpp|rs))")


def expand_braces(pattern: str) -> list:
    start = pattern.find("{")
    if start < 0:
        if "}" in pattern:
            raise Refused("bad_pattern", f"{pattern!r} has an unmatched brace")
        return [pattern]
    end = pattern.find("}", start)
    if end < 0 or "{" in pattern[start + 1:end]:
        raise Refused("bad_pattern", f"{pattern!r} has an unclosed or nested brace")
    expanded: list = []
    for option in pattern[start + 1:end].split(","):
        expanded.extend(expand_braces(pattern[:start] + option + pattern[end + 1:]))
        if len(expanded) > 64:
            raise Refused("bad_pattern", f"{pattern!r} expands to more than 64 patterns")
    return expanded


def glob_regex(pattern: str) -> re.Pattern:
    """Compile a path pattern: * and ? stay inside one folder, a whole ** segment crosses folders."""
    if not pattern or pattern.startswith("/") or "\\" in pattern or ".." in pattern.split("/"):
        raise Refused("bad_pattern", f"{pattern!r} must be a relative pattern without '..'")
    alternatives = []
    for option in expand_braces(pattern):
        if option.endswith("/"):
            option += "**"
        segments = option.split("/")
        pieces = []
        for position, segment in enumerate(segments):
            last = position == len(segments) - 1
            if segment == "**":
                pieces.append(".*" if last else "(?:[^/]+/)*")
                continue
            if "**" in segment or "[" in segment or "]" in segment:
                raise Refused("bad_pattern", f"{pattern!r}: use ** only as a whole segment and no [ ] classes")
            text = "".join("[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char) for char in segment)
            pieces.append(text if last else text + "/")
        alternatives.append("".join(pieces))
    return re.compile("(?:" + "|".join(alternatives) + r")\Z")


def is_test_path(path: str, extra: list) -> bool:
    parts = path.split("/")
    if any(part.lower() in TEST_FOLDERS for part in parts[:-1]) or TEST_NAME.fullmatch(parts[-1]):
        return True
    return any(pattern.match(path) for pattern in extra)


def definition_patterns(name: str) -> tuple:
    word = re.escape(name)
    return (
        re.compile(rf"^\s*(?:async\s+)?def\s+{word}\s*\("),
        re.compile(rf"^\s*func\s+(?:\([^)]*\)\s*)?{word}\s*\("),
        re.compile(rf"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+{word}\s*[(<]"),
        re.compile(rf"\b(?:void|fun|function|Task)\s+`?{word}`?\s*\("),
        re.compile(rf"\b(?:it|test|specify|scenario)(?:\.\w+)?\s*\(\s*(['\"`]){word}\1"),
        re.compile(rf"^\s*(?:it|test|specify)\s+(['\"]){word}\1\s+do\b"),
        re.compile(rf"\bTEST(?:_F|_P)?\s*\(\s*\w+\s*,\s*{word}\s*\)"),
    )


GO_SUBTEST = re.compile(r"\.Run\(\s*\"([^\"]*)\"")


def find_added_definition(test_id: str, runner: str, files: list, extra: list, parameters: str) -> dict | None:
    """Return where the diff adds this test: its definition, a Go subtest or a named parameter case."""
    name = base_name(test_id, runner)
    patterns = definition_patterns(name)
    core = strip_parameters(test_id)
    subtest = core.split("/", 1)[1] if runner == "go" and "/" in core else ""
    for item in files:
        for hunk in item.hunks:
            for kind, _old_no, new_no, content in hunk["lines"]:
                if kind != "+":
                    continue
                if any(pattern.search(content) for pattern in patterns):
                    return {"path": item.path, "line": new_no, "how": "definition"}
                if subtest and any(value.replace(" ", "_") == subtest.split("/")[-1]
                                   for value in GO_SUBTEST.findall(content)):
                    return {"path": item.path, "line": new_no, "how": "go_subtest"}
                if parameters and parameters in content and is_test_path(item.path, extra):
                    return {"path": item.path, "line": new_no, "how": "parameter_case"}
    return None


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------

def bounded(items) -> list:
    items = sorted(items)
    return items[:LIST_LIMIT] + ([f"... {len(items) - LIST_LIMIT} more"] if len(items) > LIST_LIMIT else [])


def counts(results: dict) -> dict:
    total: dict = {}
    for outcome in results.values():
        total[outcome] = total.get(outcome, 0) + 1
    return dict(sorted(total.items()))


def evaluate(args) -> dict:
    root = Path(args.root)
    if not root.is_dir():
        raise Refused("root_missing", f"--root {args.root!r} is not a folder")
    root = root.resolve()
    if [args.before, args.after, args.diff].count("-") > 1:
        raise Refused("bad_arguments", "only one input may come from standard input")
    requested = list(dict.fromkeys(value.strip() for value in args.tests))
    if not requested or "" in requested or len(requested) > MAX_REQUESTED_TESTS:
        raise Refused("bad_arguments", f"give one to {MAX_REQUESTED_TESTS} nonempty --test ids")
    extra = [glob_regex(pattern) for pattern in args.test_glob]
    before_text, before_info = read_input(root, args.before, "--before")
    after_text, after_info = read_input(root, args.after, "--after")
    diff_text, diff_info = read_input(root, args.diff, "--diff")
    result = judge(before_text, after_text, diff_text, requested, args.format, extra)
    result["inputs"] = {"before": before_info, "after": after_info, "diff": diff_info}
    return result


def judge(before_text: str, after_text: str, diff_text: str, requested: list, chosen: str = "auto",
          extra: list | None = None) -> dict:
    """Compare two saved test outputs and a diff; the texts are already read and bounded."""
    extra = extra or []
    before_runner, before = parse_output(before_text, chosen, "--before")
    after_runner, after = parse_output(after_text, chosen, "--after")
    files = parse_diff(diff_text)
    if not files and diff_text.strip():
        raise Refused("unreadable_diff", "--diff holds no unified diff file sections")

    checks, warnings, new_tests = [], [], []
    named = set()
    for label, text in (("before", before_text), ("after", after_text)):
        if LOAD_TROUBLE.search(text):
            warnings.append(f"the {label} output reports a test module that failed to load; read that error first")

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "status": "pass" if passed else "fail", "detail": detail})

    for test in requested:
        ids_before, how_before = match_requested(test, before, before_runner)
        ids_after, how_after = match_requested(test, after, after_runner)
        named.update(ids_before)
        named.update(ids_after)
        outcome_before = group_outcome(ids_before, before, "before")
        outcome_after = group_outcome(ids_after, after, "after")
        if "base_name" in (how_before, how_after):
            warnings.append(f"{test}: matched by its last name part only; confirm both runs name the same test")
        if outcome_before == "error":
            warnings.append(f"{test}: errored before the fix instead of failing an assertion; read its error text")
        check("new_test_failed_before", outcome_before in FAILING,
              f"{test}: before the fix {outcome_before}: "
              + (", ".join(f"{test_id} {before[test_id]}" for test_id in ids_before[:10]) or "no result"))
        check("new_test_passes_after", outcome_after == "passed",
              f"{test}: after the fix {outcome_after}: "
              + (", ".join(f"{test_id} {after[test_id]}" for test_id in ids_after[:10]) or "no result"))
        reference_id = (ids_after or ids_before or [test])[0]
        added = find_added_definition(reference_id, after_runner if ids_after else before_runner, files, extra,
                                      parameters_of(test))
        check("diff_adds_new_test", added is not None,
              f"{test}: added at {added['path']}:{added['line']} ({added['how']})" if added else
              f"{test}: no added line in the diff defines this test; the diff must hold the whole change")
        new_tests.append({"requested": test, "before": {"ids": bounded(ids_before), "outcome": outcome_before},
                          "after": {"ids": bounded(ids_after), "outcome": outcome_after},
                          "added_at": f"{added['path']}:{added['line']}" if added else None})

    previously_passing = {test_id for test_id, outcome in before.items() if outcome == "passed" and test_id not in named}
    newly_failing = [test_id for test_id in previously_passing if after.get(test_id) in FAILING]
    missing_after = [test_id for test_id in previously_passing if test_id not in after]
    now_skipped = [test_id for test_id in previously_passing if after.get(test_id) in ("skipped", "xfailed", "xpassed")]
    # A test that had no result, or was skipped or marked expected to fail before the fix, and fails after it
    # is a new failure too; only a test that already failed before is an old failure.
    other_failures = [test_id for test_id, outcome in after.items()
                      if outcome in FAILING and before.get(test_id) not in FAILING and test_id not in named
                      and test_id not in previously_passing]
    still_failing = [test_id for test_id, outcome in after.items()
                     if outcome in FAILING and before.get(test_id) in FAILING and test_id not in named]
    check("same_runner_format", before_runner == after_runner,
          f"both outputs are {before_runner} output" if before_runner == after_runner else
          f"before is {before_runner} output and after is {after_runner} output; test ids of two runners do not "
          "line up, so save both runs from the same command")
    quiet_hint = ""
    if not previously_passing and before_runner == "pytest":
        quiet_hint = "; quiet pytest output (-q) lists only failures, so save the output of -v or -rA"
    check("baseline_has_other_tests", bool(previously_passing),
          f"{len(previously_passing)} tests passed before the fix besides the new tests"
          if previously_passing else "the before run holds no passing test besides the new tests; "
                                     "run the same test selection before and after the fix" + quiet_hint)
    check("no_previously_passing_test_fails", not (newly_failing or missing_after or now_skipped),
          f"{len(newly_failing)} now fail, {len(missing_after)} are missing after, {len(now_skipped)} are now "
          "skipped or marked expected to fail")
    check("no_new_failures_after", not other_failures,
          f"{len(other_failures)} tests fail after the fix and did not fail before it (no result, skipped or "
          "marked expected to fail before)")
    if still_failing:
        warnings.append(f"{len(still_failing)} tests failed both before and after the fix; listed in still_failing")

    test_files = sorted({item.path for item in files if is_test_path(item.path, extra)})
    other_files = sorted({item.path for item in files if not is_test_path(item.path, extra)})
    check("diff_changes_non_test_file", bool(other_files),
          f"changed files that are not tests: {len(other_files)}" if other_files else
          "every changed file is a test file, so the pass may come from test edits and not from a fix")
    if len(test_files) > 1:
        warnings.append("the diff changes more than one test file; check it for weakened assertions")
    if not files:
        warnings.append("the diff is empty")

    failed = [item for item in checks if item["status"] == "fail"]
    return {
        "tool": TOOL, "version": VERSION, "verdict": "fail" if failed else "pass",
        "failures": failed, "warnings": warnings, "checks": checks, "new_tests": new_tests,
        "regressions": {"newly_failing": bounded(newly_failing), "missing_after": bounded(missing_after),
                        "now_skipped": bounded(now_skipped), "new_failures_after": bounded(other_failures)},
        "still_failing": bounded(still_failing),
        "compared_previously_passing": len(previously_passing),
        "formats": {"before": before_runner, "after": after_runner},
        "counts": {"before": counts(before), "after": counts(after)},
        "diff": {"files": len(files), "test_files": bounded(test_files), "other_files": bounded(other_files)},
    }


def main(argv=None) -> int:
    parser = Arguments(prog="verify_fail_then_pass.py", description=__doc__.splitlines()[0])
    parser.add_argument("--before", required=True, help="saved test output from before the fix, or -")
    parser.add_argument("--after", required=True, help="saved test output from after the fix, or -")
    parser.add_argument("--diff", required=True, help="unified diff of the whole change, or -")
    parser.add_argument("--test", dest="tests", action="append", required=True, help="new test id; repeat for more")
    parser.add_argument("--root", default=".", help="folder that holds the inputs (default: current folder)")
    parser.add_argument("--format", choices=("auto",) + FORMATS, default="auto")
    parser.add_argument("--test-glob", action="append", default=[], help="extra pattern for test file paths")
    try:
        result = evaluate(parser.parse_args(argv))
    except Refused as refusal:
        print(json.dumps({"tool": TOOL, "version": VERSION, "verdict": "refused", "reason": refusal.reason,
                          "detail": refusal.detail}, indent=1))
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

"""Scan the test files of a unified diff for weakened checks and report each with its location; reads the diff only.

Effects: reads the diff named by --diff below --root, or standard input for "-".
Writes nothing, starts no process and uses no network. Prints one JSON object.
Exit status: 0 pass, 1 weakening found or a changed check needs a stated reason,
2 refused input.

Weakening (verdict "fail"): an assertion removed, a skip or expected-failure mark
added, a focus or deselection added, a tolerance widened, a test function deleted,
a test file deleted. Needs a reason (verdict "review"): an assertion rewritten, a
tolerance introduced where the check was exact, a test function renamed.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

TOOL = "detect-weakened-test-assertions"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
LIST_LIMIT = 200
PAIRING_LIMIT = 40000
SIMILAR = 0.5
WEAKENING = ("assertion_removed", "assertion_made_trivial", "early_exit_added", "skip_mark_added",
             "expected_failure_mark_added", "deselection_added", "tolerance_widened", "parameter_case_removed",
             "test_function_deleted", "test_file_deleted")
REVIEW = ("assertion_rewritten", "tolerance_introduced", "parameter_case_changed", "test_function_renamed")

ASSERTION = re.compile(
    r"\b(?:debug_)?assert(?:_\w+|[A-Z]\w*)?\b"            # Python, Rust, Ruby, Java, PHP, unittest, testify
    r"|\bAssert\.\w+|\bXCTAssert\w*"                     # C#, JUnit 4, Swift
    r"|\bexpect\s*\("                                    # Jest, Vitest, RSpec, Chai
    r"|\b(?:t|b|tb)\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\("  # Go testing
    r"|\brequire\.[A-Z]\w*\s*\("                         # testify require
    r"|\.should\b|\.must_\w+"                            # should style, minitest spec
    r"|\bpytest\.(?:raises|warns|fail)\b|\bself\.fail\w*\s*\(")
SKIP_MARK = re.compile(
    r"\bpytest\.mark\.skip(?:if)?\b|\bpytest\.skip\s*\(|@(?:unittest\.)?skip(?:If|Unless)?\b"
    r"|\bself\.skipTest\s*\(|\braise\s+(?:unittest\.)?SkipTest\b"
    r"|\b(?:it|test|describe|context|suite)\.(?:skip|todo)\s*\(|\bx(?:it|test|describe|context)\s*\(\s*['\"`]"
    r"|\b(?:t|b)\.Skip(?:f|Now)?\s*\(|#\[ignore\b|@Disabled\b|@Ignore\b|\[Ignore\b|\bSkip\s*=\s*\""
    r"|\bmarkTest(?:Skipped|Incomplete)\s*\(|^\s*(?:skip|pending)\s+['\"]")
EXPECTED_FAILURE_MARK = re.compile(
    r"\bpytest\.mark\.xfail\b|\bpytest\.xfail\s*\(|@(?:unittest\.)?expectedFailure\b"
    r"|\b(?:it|test)\.failing\s*\(|#\[should_panic\b")
#: focus marks and collection ignores count in any test file
FOCUS = (r"\b(?:it|test|describe|context|suite)\.only\s*\(|(?:^|[;{(]\s*)f(?:it|describe|context)\s*\(\s*['\"`]"
         r"|\bcollect_ignore(?:_glob)?\b")
DESELECTION_IN_TESTS = re.compile(FOCUS)
#: runner flags and ignore settings count only in test settings files, where they change what runs
DESELECTION = re.compile(FOCUS + r"|--deselect\b|(?:^|[\s\"'\[,])-k\s*[\"']?\s*not\b"
                         r"|\btestPathIgnorePatterns\b|\bmodulePathIgnorePatterns\b|--ignore(?:-glob)?[=\s]")
TOLERANCE_CALL = re.compile(r"\b(?:approx|isclose|allclose|assert_allclose|assert_(?:array_)?almost_equal"
                            r"|assert_approx_equal|assert(?:Not)?AlmostEquals?|toBeCloseTo|closeTo|InDelta\w*"
                            r"|InEpsilon\w*)\s*\(")
#: tolerance names: a larger value accepts more, or (second set) a smaller value accepts more
WIDER_WHEN_LARGER = {"rtol", "atol", "abs_tol", "rel_tol", "rel", "abs", "tol", "tolerance", "delta", "epsilon", "eps",
                     "margin"}
WIDER_WHEN_SMALLER = {"places", "decimal", "digits", "precision", "num_digits", "numdigits", "significant"}
#: names that mean a tolerance on any line; the other names count only inside an approximate check call
STRONG_NAMES = {"rtol", "atol", "abs_tol", "rel_tol", "tol", "tolerance", "epsilon", "eps"}
STRONG_SUFFIXES = ("_tol", "_tolerance", "_eps", "_epsilon")
NUMBER = r"(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][-+]?\d+)?"
KEYWORD_VALUE = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*(?::=|=(?!=)|:(?!=))\s*(?P<value>" + NUMBER + r")[fFdDlL]?\b")
#: call name -> (argument position, tolerance name) for tolerances passed without a keyword
POSITIONAL = {"toBeCloseTo": ((1, "digits"),), "assertAlmostEqual": ((2, "places"),),
              "assertAlmostEquals": ((2, "places"),), "InDelta": ((3, "delta"),), "InEpsilon": ((3, "epsilon"),),
              "assert_almost_equal": ((2, "decimal"),), "assert_array_almost_equal": ((2, "decimal"),),
              "approx": ((1, "rel"),), "isclose": ((2, "rtol"), (3, "atol")), "allclose": ((2, "rtol"), (3, "atol")),
              "assert_allclose": ((2, "rtol"), (3, "atol"))}
DEFINITIONS = (
    re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)\s*\("),
    re.compile(r"^\s*func\s+(Test\w+|Benchmark\w+|Fuzz\w+|Example\w*)\s*\("),
    re.compile(r"^\s*(?:it|test|specify|scenario)\s*\(\s*(['\"`])(.+?)\1"),
    re.compile(r"^\s*(?:it|test|specify)\s+(['\"])(.+?)\1\s+do\b"),
    re.compile(r"^\s*TEST(?:_F|_P)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)"),
    re.compile(r"\b(?:void|fun)\s+(test\w*)\s*\("),
    re.compile(r"\bfunction\s+(test\w*)\s*\("),
)
TEST_ATTRIBUTE = re.compile(r"^\s*(?:#\[(?:\w+::)*test\b|@Test\b|@ParameterizedTest\b|@RepeatedTest\b"
                            r"|\[(?:Fact|Theory|Test|TestMethod|TestCase)\b)")
FUNCTION_NAME = re.compile(r"\bfn\s+(\w+)|\b(?:void|fun|Task)\s+`?([\w ]+?)`?\s*\(")
TEST_FOLDERS = {"test", "tests", "testing", "__tests__", "spec", "specs", "e2e"}
TEST_NAME = re.compile(
    r"(?:test_.+\.py|.+_test\.py|conftest\.py|.+_test\.go|.+\.(?:test|spec)\.[cm]?[jt]sx?"
    r"|.+_(?:spec|test)\.rb|.+Tests?\.(?:java|kt|kts|cs|scala|groovy|swift|php)|Test.+\.(?:java|kt|php)"
    r"|.+Spec\.(?:scala|groovy|kt)|.+_tests?\.(?:rs|exs|dart|c|cc|cpp)|test_.+\.(?:c|cc|cpp|rs))")
CONFIG_NAMES = {"pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml", "noxfile.py", "package.json", "phpunit.xml",
                "phpunit.xml.dist", "makefile"}
CONFIG_NAME = re.compile(r"(?:(?:jest|vitest|playwright|cypress|karma)\.conf(?:ig)?\.[cm]?[jt]s(?:on)?"
                         r"|\.mocharc\.(?:js|cjs|json|ya?ml))", re.IGNORECASE)


class Refused(Exception):
    """The input cannot be judged; the script exits 2 with this reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class Arguments(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print usage and exit 2
        raise Refused("bad_arguments", message)


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
        if binary and (current is None or current.file_header or current.hunks):
            current = FileDiff()
            current.old_path = strip_prefix(binary.group(1), "a/")
            current.new_path = strip_prefix(binary.group(2), "b/")
            files.append(current)
        elif current is not None:
            if line.startswith("new file mode "):
                current.change = "added"
            elif line.startswith("deleted file mode "):
                current.change = "deleted"
            elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
                words = line.split(" ", 2)
                value = unquote(words[2])[0] if words[2].startswith('"') else words[2]
                current.change = "renamed" if words[0] == "rename" else "copied"
                if words[1] == "from":
                    current.old_path = value
                else:
                    current.new_path = value
        index += 1
    for item in files:
        if item.change == "added":
            item.old_path = None
        elif item.change == "deleted":
            item.new_path = None
    return files


# ---------------------------------------------------------------------------
# line classification
# ---------------------------------------------------------------------------

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


def is_settings_file(path: str) -> bool:
    parts = path.split("/")
    return parts[-1].lower() in CONFIG_NAMES or bool(CONFIG_NAME.fullmatch(parts[-1])) \
        or (len(parts) > 2 and parts[0] == ".github" and parts[1] == "workflows")


def file_kind(path: str, extra: list, every_file: bool) -> str:
    parts = path.split("/")
    name = parts[-1]
    if every_file or any(part.lower() in TEST_FOLDERS for part in parts[:-1]) or TEST_NAME.fullmatch(name) \
            or any(pattern.match(path) for pattern in extra):
        return "test"
    if is_settings_file(path):
        return "config"
    return "other"


def is_comment(content: str) -> bool:
    text = content.strip()
    return text.startswith(("//", "/*", "*", "--")) or (text.startswith("#") and not text.startswith(("#[", "#![")))


def normal(content: str) -> str:
    return " ".join(content.split())


def call_arguments(content: str, start: int) -> list:
    """Split the arguments of the call whose '(' is at start, when it closes on this line."""
    depth, quote, current, arguments = 0, "", [], []
    for char in content[start:]:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            continue
        if char in "\"'`":
            quote = char
        elif char in "([{":
            depth += 1
            if depth == 1:
                continue
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                arguments.append("".join(current).strip())
                return arguments
        elif char == "," and depth == 1:
            arguments.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    return []


def tolerance_direction(name: str) -> str | None:
    """Say whether a larger or a smaller value of this tolerance name accepts more results."""
    if name in WIDER_WHEN_LARGER or name.endswith(STRONG_SUFFIXES):
        return "larger"
    if name in WIDER_WHEN_SMALLER:
        return "smaller"
    return None


def tolerances(content: str) -> dict:
    """Return {tolerance name: [values]} for keyword and known positional tolerance arguments."""
    found: dict = {}
    in_call = bool(TOLERANCE_CALL.search(content))
    for match in KEYWORD_VALUE.finditer(content):
        name = match["name"].lower()
        strong = name in STRONG_NAMES or name.endswith(STRONG_SUFFIXES)
        if tolerance_direction(name) and (strong or in_call):
            found.setdefault(name, []).append(float(match["value"].replace("_", "")))
    for match in re.finditer(r"\b(" + "|".join(POSITIONAL) + r")\s*\(", content):
        arguments = call_arguments(content, match.end() - 1)
        for position, name in POSITIONAL[match.group(1)]:
            if position < len(arguments) and re.fullmatch(NUMBER + r"[fFdDlL]?", arguments[position]):
                found.setdefault(name, []).append(float(arguments[position].rstrip("fFdDlL").replace("_", "")))
    return found


def definition_name(lines: list, index: int) -> str | None:
    content = lines[index][3]
    for pattern in DEFINITIONS:
        match = pattern.search(content)
        if match:
            groups = [group for group in match.groups() if group]
            if pattern.groups == 2 and pattern.pattern.startswith(r"^\s*TEST"):
                return f"{groups[0]}.{groups[1]}"
            return groups[-1]
    if TEST_ATTRIBUTE.search(content):
        kind = lines[index][0]
        for _kind, _old, _new, following in lines[index + 1:index + 5]:
            if _kind == ("+" if kind == "+" else "-") or _kind == " ":
                named = FUNCTION_NAME.search(following)
                if named:
                    return (named.group(1) or named.group(2)).strip()
        return f"test attribute at line {lines[index][1] or lines[index][2]}"
    return None


def pair_by_similarity(removed: list, added: list, text) -> tuple[list, list, list]:
    """Greedy pairing of removed and added entries by text similarity; returns pairs and leftovers."""
    if len(removed) * len(added) > PAIRING_LIMIT:
        count = min(len(removed), len(added))
        return list(zip(removed[:count], added[:count])), removed[count:], added[count:]
    scored = sorted(((difflib.SequenceMatcher(None, text(left), text(right)).ratio(), i, j)
                     for i, left in enumerate(removed) for j, right in enumerate(added)), reverse=True)
    used_left, used_right, pairs = set(), set(), []
    for ratio, i, j in scored:
        if ratio < SIMILAR:
            break
        if i not in used_left and j not in used_right:
            used_left.add(i)
            used_right.add(j)
            pairs.append((removed[i], added[j]))
    pairs.sort(key=lambda pair: pair[0].get("old_line") or pair[0].get("first") or 0)
    return (pairs, [entry for i, entry in enumerate(removed) if i not in used_left],
            [entry for j, entry in enumerate(added) if j not in used_right])


def entry(kind: str, path: str, old=None, new=None, detail: str = "") -> dict:
    return {"kind": kind, "path": path, "old_line": old["old_line"] if old else None,
            "new_line": new["new_line"] if new else None,
            "old_text": old["text"][:200] if old else None, "new_text": new["text"][:200] if new else None,
            "detail": detail}


def cancel_moves(removed: list, added: list, key) -> tuple[list, list]:
    """Drop entries whose normalized text is both removed and added in the same file: they moved."""
    common = Counter(key(item) for item in removed) & Counter(key(item) for item in added)
    left, right = Counter(common), Counter(common)
    kept_removed, kept_added = [], []
    for item in removed:
        if left[key(item)] > 0:
            left[key(item)] -= 1
        else:
            kept_removed.append(item)
    for item in added:
        if right[key(item)] > 0:
            right[key(item)] -= 1
        else:
            kept_added.append(item)
    return kept_removed, kept_added


# ---------------------------------------------------------------------------
# statements: the lines of one side of a hunk grouped by open brackets
# ---------------------------------------------------------------------------

HASH_COMMENTS = {".py", ".pyi", ".rb", ".sh", ".bash", ".r", ".pl", ".ex", ".exs", ".toml", ".cfg", ".ini", ".yml",
                 ".yaml", ".nim", ".jl"}
SLASH_COMMENTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".go", ".java", ".kt", ".kts",
                  ".rs", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cs", ".swift", ".scala", ".php", ".dart",
                  ".groovy", ".m", ".mm"}
CLOSERS = {")": "(", "]": "[", "}": "{"}
#: A brace that ends a line after one of these opens a value (an object, a map), not a block of statements.
VALUE_BRACE_BEFORE = ("(", "[", ",", ":", "=", "?", "return", "=>(")
TRIVIAL = re.compile(
    r"^assert\s+(?:True|1|not\s+(?:False|None|0))\s*(?:,.*)?$"            # Python assert True
    r"|^assert\s+.+\bor\s+(?:True|1)\s*(?:,.*)?$"                          # Python assert x or True
    r"|\bassert(?:True|_)\s*\(\s*(?:True|1)\s*[,)]"                          # unittest assertTrue(True)
    r"|\bassert(?:Equals?|_eq!?|Same|Identical)\s*\(\s*(?P<same>[\w.]+)\s*,\s*(?P=same)\s*[,)]"
    r"|\bexpect\s*\(\s*true\s*\)\s*\.\s*toBe(?:Truthy)?\s*\(\s*(?:true)?\s*\)"  # Jest expect(true).toBe(true)
    r"|\bassert!\s*\(\s*true\s*\)")                                          # Rust assert!(true)
EARLY_EXIT = re.compile(r"return\s*(?:None)?\s*;?")
PARAMETRIZE = re.compile(r"@pytest\.mark\.parametrize\s*\(|@parameterized(?:\.expand)?\s*\("
                         r"|\b(?:it|test|describe)\.each\s*\(")


def comment_style(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return "hash" if suffix in HASH_COMMENTS else "slash" if suffix in SLASH_COMMENTS else "both"


def code_part(content: str, style: str, state: dict) -> str:
    """Return one line with string contents and comments removed; state carries a string that spans lines."""
    out, index, size = [], 0, len(content)
    while index < size:
        if state["string"]:
            end = content.find(state["string"], index)
            if end < 0:
                return "".join(out)
            index = end + len(state["string"])
            state["string"] = ""
            out.append('""')
            continue
        char = content[index]
        if style != "slash" and content.startswith(('"""', "'''"), index):
            state["string"] = content[index:index + 3]
            index += 3
            continue
        if char == "`" and style != "hash":
            state["string"] = "`"
            index += 1
            continue
        if char in "\"'":
            end, position = -1, index + 1
            while position < size:
                if content[position] == "\\":
                    position += 2
                    continue
                if content[position] == char:
                    end = position
                    break
                position += 1
            if end < 0:  # an apostrophe or a Rust lifetime, not a string
                out.append(char)
                index += 1
                continue
            out.append(char + char)
            index = end + 1
            continue
        if char == "#" and style != "slash" and not content.startswith(("#[", "#!["), index):
            break
        if style != "hash" and content.startswith("//", index):
            break
        out.append(char)
        index += 1
    return "".join(out)


def side_statements(lines: list, kinds: tuple, style: str) -> list:
    """Group the lines of one side of a hunk into statements: a statement ends where no bracket stays open.

    A brace that ends a line in a C-like file opens a block, so each statement inside the block stands alone.
    A closing bracket without its opener shows that the hunk began inside an expression; everything seen so
    far on this side is then one statement, marked open_at_start.
    """
    statements, current, stack, state = [], None, [], {"string": ""}
    old_side = "-" in kinds
    for index, (kind, old_no, new_no, content) in enumerate(lines):
        if kind not in kinds:
            continue
        if current is None:
            current = {"indices": [], "changed": [], "raw": [], "code": [], "open_at_start": False,
                       "first": old_no if old_side else new_no}
        current["indices"].append(index)
        if kind != " ":
            current["changed"].append(index)
        in_string = bool(state["string"])
        code = code_part(content, style, state)
        if not is_comment(content) or in_string:
            current["raw"].append(content.strip())
        current["code"].append(code.strip())
        merge, block_closed = False, False
        stripped = code.rstrip()
        for position, char in enumerate(code):
            if char in "([":
                stack.append(char)
            elif char == "{":
                before = stripped[:position].rstrip()
                block = style != "hash" and position == len(stripped) - 1 \
                    and not before.endswith(VALUE_BRACE_BEFORE)
                stack.append("B" if block else "{")
            elif char in CLOSERS:
                if stack:
                    stack.pop()
                elif char == "}" and style != "hash":
                    block_closed = True
                elif not block_closed:
                    merge = True
        if merge:
            merged = {"indices": [], "changed": [], "raw": [], "code": [], "open_at_start": True,
                      "first": (statements[0] if statements else current)["first"]}
            for earlier in statements + [current]:
                for key in ("indices", "changed", "raw", "code"):
                    merged[key].extend(earlier[key])
            statements, current = [], merged
        if not ((stack and stack[-1] != "B") or state["string"] or stripped.endswith("\\")):
            statements.append(current)
            current = None
    if current is not None:
        statements.append(current)
    for statement in statements:
        statement["text"] = normal(" ".join(statement["raw"]))
        statement["code_text"] = normal(" ".join(statement["code"]))
        changed = statement["changed"]
        if changed:
            position = changed[0]
            statement["first"] = lines[position][1] if lines[position][0] == "-" else lines[position][2]
    return statements


def is_check(statement: dict) -> bool:
    return bool(statement["code_text"]) and bool(ASSERTION.search(statement["code_text"]))


def is_parametrize(statement: dict) -> bool:
    return bool(PARAMETRIZE.search(statement["code_text"]))


def case_elements(statement: dict) -> list | None:
    """The cases of a parametrize list, one normalized text each, or None when they cannot be counted."""
    match = PARAMETRIZE.search(statement["text"])
    if not match:
        return None
    arguments = call_arguments(statement["text"], match.end() - 1)
    if not arguments:
        return None
    position = 1 if "parametrize" in match.group(0) else 0
    if position >= len(arguments):
        return None
    value = re.sub(r"^[A-Za-z_]\w*\s*=\s*", "", arguments[position].strip())
    if not value or value[0] not in "[(":
        return None
    return [normal(element) for element in call_arguments(value, 0) if element.strip()]


def statement_entry(kind: str, path: str, old=None, new=None, detail: str = "") -> dict:
    return {"kind": kind, "path": path, "old_line": old["first"] if old else None,
            "new_line": new["first"] if new else None, "old_text": old["text"][:200] if old else None,
            "new_text": new["text"][:200] if new else None, "detail": detail}


def pair_statements(old_side: list, new_side: list) -> tuple:
    """Pair changed statements that share unchanged lines; return the pairs and the statements left alone."""
    pairs, used_old, used_new = [], set(), set()
    for number, statement in enumerate(old_side):
        context = set(statement["indices"]) - set(statement["changed"])
        if not statement["changed"] or not context:
            continue
        overlaps = [(len(context & set(other["indices"])), position) for position, other in enumerate(new_side)]
        size, position = max(overlaps, default=(0, None))
        if size:
            pairs.append((statement, new_side[position]))
            used_old.add(number)
            used_new.add(position)
    for number, statement in enumerate(new_side):
        context = set(statement["indices"]) - set(statement["changed"])
        if number in used_new or not statement["changed"] or not context:
            continue
        overlaps = [(len(context & set(other["indices"])), position) for position, other in enumerate(old_side)]
        size, position = max(overlaps, default=(0, None))
        if size and position not in used_old:
            pairs.append((old_side[position], statement))
            used_old.add(position)
            used_new.add(number)
    loose_old = [statement for number, statement in enumerate(old_side)
                 if number not in used_old and statement["changed"] and statement["text"]]
    loose_new = [statement for number, statement in enumerate(new_side)
                 if number not in used_new and statement["changed"] and statement["text"]]
    return pairs, loose_old, loose_new


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def analyse_test_file(item: FileDiff, found: list, warnings: list) -> None:
    path = item.path
    style = comment_style(path)
    rows = []  # every changed, non-comment line of the file with its hunk number
    for number, hunk in enumerate(item.hunks):
        lines = hunk["lines"]
        for index, (kind, old_no, new_no, content) in enumerate(lines):
            if kind == " " or is_comment(content):
                continue
            rows.append({"hunk": number, "index": index, "kind": kind, "old_line": old_no, "new_line": new_no,
                         "text": content.strip(), "name": definition_name(lines, index)})
    if item.change == "deleted":
        tests = [row for row in rows if row["name"]]
        found.append(entry("test_file_deleted", path, rows[0] if rows else None,
                           detail=f"the file held {len(tests)} test definitions"))
        return

    def side(kind):
        return [row for row in rows if row["kind"] == kind]

    # marks and deselections that are only added, not moved
    deselection = DESELECTION if is_settings_file(path) else DESELECTION_IN_TESTS
    for pattern, kind in ((SKIP_MARK, "skip_mark_added"), (EXPECTED_FAILURE_MARK, "expected_failure_mark_added"),
                          (deselection, "deselection_added")):
        removed = [row for row in side("-") if pattern.search(row["text"])]
        added = [row for row in side("+") if pattern.search(row["text"])]
        for row in cancel_moves(removed, added, lambda value: normal(value["text"]))[1]:
            found.append(entry(kind, path, new=row, detail="the added line switches a test off or narrows the run"))

    # test definitions: moved names cancel, similar names are renames, the rest are deletions
    removed_defs, added_defs = cancel_moves([row for row in side("-") if row["name"]],
                                            [row for row in side("+") if row["name"]], lambda value: value["name"])
    deleted_blocks = set()
    for number in range(len(item.hunks)):
        pairs, left, _right = pair_by_similarity([row for row in removed_defs if row["hunk"] == number],
                                                 [row for row in added_defs if row["hunk"] == number],
                                                 lambda value: value["name"])
        for old, new in pairs:
            found.append(entry("test_function_renamed", path, old, new, f"{old['name']} became {new['name']}"))
        for old in left:
            lines = item.hunks[number]["lines"]
            end = old["index"]
            while end + 1 < len(lines) and lines[end + 1][0] == "-":
                end += 1
            deleted_blocks.update((number, index) for index in range(old["index"], end + 1))
            inside = sum(1 for index in range(old["index"], end + 1) if ASSERTION.search(lines[index][3])
                         and not is_comment(lines[index][3]))
            found.append(entry("test_function_deleted", path, old,
                               detail=f"{old['name']} is removed; assertion lines inside it: {inside}"))

    # statements of both sides of every hunk
    hunks = []
    for number, hunk in enumerate(item.hunks):
        old_side = side_statements(hunk["lines"], (" ", "-"), style)
        new_side = side_statements(hunk["lines"], (" ", "+"), style)
        for statement in old_side:
            statement["hunk"] = number
        for statement in new_side:
            statement["hunk"] = number
        hunks.append((old_side, new_side))
        partial = [statement for statement in old_side + new_side
                   if statement["open_at_start"] and statement["changed"] and not is_check(statement)]
        if partial:
            warnings.append(f"{path}: a changed line near line {partial[0]['first']} sits inside a statement that "
                            "starts above the diff context; make the diff again with more context, such as git diff "
                            "-U10, and check again")

    # tolerances compared per hunk over the changed statements of each side
    widened = set()
    for number, (old_side, new_side) in enumerate(hunks):
        before, after = {}, {}
        for statements, values in ((old_side, before), (new_side, after)):
            for statement in statements:
                if statement["changed"]:
                    for name, numbers in tolerances(statement["text"]).items():
                        values.setdefault(name, []).extend((value, statement) for value in numbers)
        for name in sorted(set(before) & set(after)):
            if tolerance_direction(name) == "larger":
                old_value, old_statement = max(before[name], key=lambda pair: pair[0])
                new_value, new_statement = max(after[name], key=lambda pair: pair[0])
                wider = new_value > old_value
            else:
                old_value, old_statement = min(before[name], key=lambda pair: pair[0])
                new_value, new_statement = min(after[name], key=lambda pair: pair[0])
                wider = new_value < old_value
            if wider:
                widened.add(id(new_statement))
                found.append(statement_entry("tolerance_widened", path, old_statement, new_statement,
                                             f"{name} changed from {old_value:g} to {new_value:g}, which accepts "
                                             "more results"))

    # checks: statements that share unchanged lines are one check changed in place; statements that are only
    # removed or only added are paired when they moved (same text) or look alike (a rewrite)
    paired, loose_old, loose_new = [], [], []
    for old_side, new_side in hunks:
        pairs, left, right = pair_statements(old_side, new_side)
        paired += pairs
        loose_old += left
        loose_new += right
    def in_deleted_block(statement: dict) -> bool:
        return bool(statement["changed"]) and all((statement["hunk"], index) in deleted_blocks
                                                  for index in statement["changed"])

    loose_old = [value for value in loose_old if not in_deleted_block(value)]
    loose_old, loose_new = cancel_moves(loose_old, loose_new, lambda value: value["text"])
    for number in range(len(hunks)):
        for pick in (is_check, is_parametrize):
            pairs, _left, _right = pair_by_similarity(
                [value for value in loose_old if value["hunk"] == number and pick(value)],
                [value for value in loose_new if value["hunk"] == number and pick(value)],
                lambda value: value["text"])
            for old, new in pairs:
                paired.append((old, new))
                loose_old = [value for value in loose_old if value is not old]
                loose_new = [value for value in loose_new if value is not new]

    for old, new in sorted(paired, key=lambda pair: (pair[0]["hunk"], pair[0]["first"] or 0)):
        if old["text"] == new["text"]:
            continue
        old_cases, new_cases = case_elements(old), case_elements(new)
        if is_parametrize(old) or is_parametrize(new):
            if old_cases is not None and new_cases is not None and len(new_cases) < len(old_cases):
                missing = [value for value in old_cases if value not in new_cases][:3]
                found.append(statement_entry("parameter_case_removed", path, old, new,
                                             f"{len(old_cases)} cases became {len(new_cases)}; gone: {missing}"))
            elif old_cases is None or new_cases is None or [value for value in old_cases if value not in new_cases]:
                found.append(statement_entry("parameter_case_changed", path, old, new,
                                             "a parameter case changed; the report must say why"))
            continue
        if not is_check(old) or in_deleted_block(old):
            continue
        if not is_check(new):
            found.append(statement_entry("assertion_removed", path, old, new,
                                         "the check was turned into a line that checks nothing"))
        elif id(new) in widened:
            continue
        elif TRIVIAL.search(new["text"]) and not TRIVIAL.search(old["text"]):
            found.append(statement_entry("assertion_made_trivial", path, old, new,
                                         "the new check is always true, so it can never fail"))
        elif (TOLERANCE_CALL.search(new["text"]) and not TOLERANCE_CALL.search(old["text"])) \
                or (tolerances(new["text"]) and not tolerances(old["text"])):
            found.append(statement_entry("tolerance_introduced", path, old, new, "an exact check now accepts a range"))
        else:
            found.append(statement_entry("assertion_rewritten", path, old, new,
                                         "the check changed; the report must say why the new expectation is right"))
    for old in loose_old:
        if is_check(old):
            found.append(statement_entry("assertion_removed", path, old,
                                         detail="no similar check replaces it in this hunk"))
        elif is_parametrize(old):
            found.append(statement_entry("parameter_case_removed", path, old,
                                         detail="the parameter list is removed"))

    # an added bare return that stops the test before a check that follows it in the same block
    for number, (old_side, new_side) in enumerate(hunks):
        lines = item.hunks[number]["lines"]

        def indent(statement: dict) -> int:
            content = lines[statement["indices"][0]][3]
            return len(content.expandtabs(4)) - len(content.expandtabs(4).lstrip())

        removed_returns = sum(1 for value in old_side if value["changed"] and EARLY_EXIT.fullmatch(value["code_text"]))
        for position, statement in enumerate(new_side):
            if not statement["changed"] or not EARLY_EXIT.fullmatch(statement["code_text"]):
                continue
            if removed_returns:
                removed_returns -= 1
                continue
            level = indent(statement)
            for later in new_side[position + 1:]:
                if not later["code_text"]:
                    continue
                if indent(later) < level or any(definition_name(lines, index) for index in later["indices"]):
                    break  # the block of the return ended, so the check below it still runs
                if indent(later) == level and is_check(later):
                    found.append(statement_entry("early_exit_added", path, new=statement,
                                                 detail=f"the test now returns before the check at line "
                                                        f"{later['first']}"))
                    break


def analyse_config_file(item: FileDiff, found: list) -> None:
    removed = [{"text": content.strip(), "old_line": old_no, "new_line": new_no}
               for hunk in item.hunks for kind, old_no, new_no, content in hunk["lines"] if kind == "-"
               and DESELECTION.search(content)]
    added = [{"text": content.strip(), "old_line": old_no, "new_line": new_no}
             for hunk in item.hunks for kind, old_no, new_no, content in hunk["lines"] if kind == "+"
             and DESELECTION.search(content)]
    for row in cancel_moves(removed, added, lambda value: normal(value["text"]))[1]:
        found.append(entry("deselection_added", item.path, new=row, detail="test configuration now leaves tests out"))


def evaluate(args) -> dict:
    root = Path(args.root)
    if not root.is_dir():
        raise Refused("root_missing", f"--root {args.root!r} is not a folder")
    root = root.resolve()
    extra = [glob_regex(pattern) for pattern in args.test_glob]
    text, info = read_input(root, args.diff, "--diff")
    files = parse_diff(text)
    if not files and text.strip():
        raise Refused("unreadable_diff", "--diff holds no unified diff file sections")
    found, warnings = [], []
    scanned = {"test": [], "config": [], "other": []}
    for item in files:
        kind = file_kind(item.path, extra, args.all_files)
        if kind == "other" and item.change == "renamed" and file_kind(item.old_path or "", extra, False) == "test":
            kind = "test"
        scanned[kind].append(item.path)
        if kind == "test":
            analyse_test_file(item, found, warnings)
        elif kind == "config":
            analyse_config_file(item, found)
    found.sort(key=lambda value: (value["path"], value["old_line"] or value["new_line"] or 0, value["kind"]))
    weakening = [value for value in found if value["kind"] in WEAKENING]
    review = [value for value in found if value["kind"] in REVIEW]
    if not scanned["test"]:
        warnings.append("the diff changes no test file; use --test-glob or --all-files if tests live elsewhere")
    verdict = "fail" if weakening else "review" if review else "pass"
    return {
        "tool": TOOL, "version": VERSION, "verdict": verdict,
        "weakening": weakening[:LIST_LIMIT], "review": review[:LIST_LIMIT],
        "counts": {"weakening": len(weakening), "review": len(review),
                   **{kind: sum(1 for value in found if value["kind"] == kind) for kind in WEAKENING + REVIEW}},
        "warnings": warnings,
        "files": {"tests": scanned["test"][:LIST_LIMIT], "test_config": scanned["config"][:LIST_LIMIT],
                  "not_scanned": len(scanned["other"])},
        "input": info,
    }


def main(argv=None) -> int:
    parser = Arguments(prog="detect_weakened_tests.py", description=__doc__.splitlines()[0])
    parser.add_argument("--diff", required=True, help="unified diff of the change, or - for standard input")
    parser.add_argument("--test-glob", action="append", default=[], help="extra pattern for test file paths")
    parser.add_argument("--all-files", action="store_true", help="scan every changed file as a test file")
    parser.add_argument("--root", default=".", help="folder that holds the diff (default: current folder)")
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

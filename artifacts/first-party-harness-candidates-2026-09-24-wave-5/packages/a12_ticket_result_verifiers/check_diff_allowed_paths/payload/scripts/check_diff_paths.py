"""Check a unified diff against the allowed path patterns of one step; reads the named files only.

Effects: reads the diff named by --diff, the list of new untracked files named by
--untracked (either may be "-" for standard input), an optional --allow-file, and
the first bytes of each listed new file, all below --root. Writes nothing, starts no
process and uses no network. Prints one JSON object. Exit status: 0 pass, 1 fail,
2 refused input.

Rules: every touched path matches an allowed pattern; no test file is deleted or
moved out of the test folders; no binary file is added or changed; no file grows by
more than the size limits; no lock file or generated file is edited; no symbolic
link, submodule pointer or unsafe path appears. A --permit value lets one named
category through and lists it under "permitted". Files below this skill's own folder
and files that match an --ignore pattern (files the host placed for the step) are left
out and listed under "ignored".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

TOOL = "check-diff-allowed-paths"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_PATTERNS = 200
LIST_LIMIT = 100
DEFAULT_MAX_FILE_BYTES = 262144
DEFAULT_MAX_FILE_LINES = 2000
#: --permit value -> the rule it lets through
PERMITS = {"test_deletion": "test_file_deleted", "binary_file": "binary_file", "large_file": "large_file",
           "lock_file": "lock_file", "generated_file": "generated_file"}
LOCK_NAMES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb",
              "cargo.lock", "gemfile.lock", "poetry.lock", "pipfile.lock", "uv.lock", "pdm.lock", "composer.lock",
              "go.sum", "mix.lock", "packages.lock.json", "podfile.lock", "pubspec.lock", "flake.lock",
              "gradle.lockfile", "deno.lock", "package.resolved", "conan.lock", "pixi.lock", "shard.lock"}
LOCK_SUFFIX = re.compile(r"(?:\.lock|\.lockb|\.lockfile|-lock\.(?:json|ya?ml))\Z", re.IGNORECASE)
GENERATED_GLOBS = ("**/*.min.js", "**/*.min.css", "**/*.js.map", "**/*.css.map", "**/*_pb2.py", "**/*_pb2_grpc.py",
                   "**/*_pb2.pyi", "**/*.pb.go", "**/*.pb.cc", "**/*.pb.h", "**/*.generated.*", "**/*.g.dart",
                   "**/*.freezed.dart", "**/*.designer.cs", "**/__generated__/**", "**/generated/**",
                   "**/node_modules/**", "**/vendor/**", "**/dist/**")
GENERATED_MARKER = re.compile(r"@generated\b|\bCode generated\b.*\bDO NOT EDIT\b"
                              r"|\b(?:auto-?generated|automatically generated)\b.{0,80}\b(?:do not|don't) (?:edit|modify)\b"
                              r"|\bthis file (?:is|was|has been) (?:automatically |auto-?)?generated\b", re.IGNORECASE)


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
# path patterns
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
    """Compile a path pattern: * and ? stay inside one folder, a whole ** segment crosses folders.

    A pattern without *, ? or braces names one file or one folder: "src" matches src and everything below it.
    """
    while pattern.startswith("./"):
        pattern = pattern[2:]
    if not pattern or pattern.startswith("/") or "\\" in pattern or ".." in pattern.split("/"):
        raise Refused("bad_pattern", f"{pattern!r} must be a relative pattern without '..'")
    alternatives = []
    for option in expand_braces(pattern):
        if option.endswith("/"):
            option += "**"
        elif not any(char in option for char in "*?[]"):
            alternatives.append(re.escape(option) + "(?:/.*)?")
            continue
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


def load_patterns(root: Path, values: list, files: list) -> list:
    patterns = [value.strip() for value in values if value.strip()]
    for value in files:
        text, _info = read_input(root, value, "--allow-file")
        if value.lower().endswith(".json"):
            try:
                document = json.loads(text)
            except ValueError as error:
                raise Refused("bad_allow_file", f"{value} is not JSON: {error}") from None
            if isinstance(document, dict):
                document = document.get("allowed_paths", document.get("allow"))
            if not isinstance(document, list) or not all(isinstance(item, str) for item in document):
                raise Refused("bad_allow_file", f"{value} must hold a list of patterns or an allowed_paths list")
            patterns += [item.strip() for item in document if item.strip()]
        else:
            patterns += [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    patterns = list(dict.fromkeys(patterns))
    if not patterns:
        raise Refused("no_allowed_paths", "give the step's allowed path patterns with --allow or --allow-file")
    if len(patterns) > MAX_PATTERNS:
        raise Refused("bad_arguments", f"at most {MAX_PATTERNS} allowed path patterns")
    return patterns


# ---------------------------------------------------------------------------
# unified diff
# ---------------------------------------------------------------------------

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
BINARY_LINE = re.compile(r"^Binary files (.+) and (.+) differ$")
INDEX_MODE = re.compile(r"^index [0-9a-f]+\.\.[0-9a-f]+ (\d{6})$")
ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class FileDiff:
    def __init__(self) -> None:
        self.old_path: str | None = None
        self.new_path: str | None = None
        self.change = "modified"
        self.binary = False
        self.binary_size: int | None = None
        self.modes: set = set()
        self.new_mode: str | None = None
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
    binary_patch = False
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
            binary_patch = False
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
            mode = INDEX_MODE.match(line)
            if mode:
                current.modes.add(mode.group(1))
            elif line.startswith("new file mode "):
                current.change = "added"
                current.new_mode = line[len("new file mode "):].strip()
                current.modes.add(current.new_mode)
            elif line.startswith("deleted file mode "):
                current.change = "deleted"
                current.modes.add(line[len("deleted file mode "):].strip())
            elif line.startswith("new mode "):
                current.new_mode = line[len("new mode "):].strip()
                current.modes.add(current.new_mode)
            elif line.startswith("old mode "):
                current.modes.add(line[len("old mode "):].strip())
            elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
                words = line.split(" ", 2)
                value = unquote(words[2])[0] if words[2].startswith('"') else words[2]
                current.change = "renamed" if words[0] == "rename" else "copied"
                if words[1] == "from":
                    current.old_path = value
                else:
                    current.new_path = value
            elif line == "GIT binary patch":
                current.binary = True
                binary_patch = True
            elif binary_patch and line.startswith(("literal ", "delta ")):
                if line.startswith("literal ") and line[8:].strip().isdigit():
                    current.binary_size = int(line[8:].strip())
                binary_patch = False  # the first block is the new content; the second is the reverse
        index += 1
    for item in files:
        if item.change == "added":
            item.old_path = None
        elif item.change == "deleted":
            item.new_path = None
    return files


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------

TEST_FOLDERS = {"test", "tests", "testing", "__tests__", "spec", "specs", "e2e"}
TEST_NAME = re.compile(
    r"(?:test_.+\.py|.+_test\.py|conftest\.py|.+_test\.go|.+\.(?:test|spec)\.[cm]?[jt]sx?"
    r"|.+_(?:spec|test)\.rb|.+Tests?\.(?:java|kt|kts|cs|scala|groovy|swift|php)|Test.+\.(?:java|kt|php)"
    r"|.+Spec\.(?:scala|groovy|kt)|.+_tests?\.(?:rs|exs|dart|c|cc|cpp)|test_.+\.(?:c|cc|cpp|rs))")


def is_test_path(path: str, extra: list) -> bool:
    parts = path.split("/")
    if any(part.lower() in TEST_FOLDERS for part in parts[:-1]) or TEST_NAME.fullmatch(parts[-1]):
        return True
    return any(pattern.match(path) for pattern in extra)


def unsafe(path: str) -> bool:
    parts = path.split("/")
    return (not path or path.startswith("/") or "\\" in path or "\x00" in path
            or any(part in ("", ".", "..") or part.lower() == ".git" for part in parts))


def touched_paths(item: FileDiff) -> list:
    if item.change == "renamed":
        return [path for path in (item.old_path, item.new_path) if path is not None]
    if item.change == "deleted":
        return [item.old_path or ""]
    return [item.new_path or item.old_path or ""]


#: A 'git status --short' line for a tracked file, such as " M src/a.py"; its change belongs in the diff.
STATUS_LINE = re.compile(r"^[ MTADRCU!][ MTADRCU!] \S")


def untracked_paths(text: str) -> list:
    """Read 'git ls-files --others --exclude-standard' output; '?? path' status lines also work."""
    paths = []
    for number, raw in enumerate(text.splitlines(), 1):
        if STATUS_LINE.match(raw) and not raw.startswith("   "):
            raise Refused("status_line_in_untracked_list",
                          f"line {number} {raw[:80]!r} is a git status line for a tracked file; give only new files, "
                          "from git ls-files --others --exclude-standard, and check tracked changes with --diff")
        line = raw.strip()
        if line.startswith("?? "):
            line = line[3:]
        if line:
            paths.append(unquote(line)[0] if line.startswith('"') else line)
    return list(dict.fromkeys(paths))


def looks_binary(data: bytes) -> bool:
    """Treat a file as binary when its first 8 KiB hold a NUL byte, as git does."""
    return b"\x00" in data[:8192]


def inspect_new_file(root: Path, path: str, window: int) -> dict:
    """Look at one new file without following a link out of root: link, binary, size and lines."""
    facts = {"exists": False, "symlink": False, "outside": False, "binary": False, "bytes": 0, "lines": 0}
    candidate = root / path
    if candidate.is_symlink():
        facts.update(exists=True, symlink=True)
        return facts
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return facts
    if not resolved.is_relative_to(root):
        facts.update(exists=True, outside=True)
        return facts
    if not resolved.is_file():
        return facts
    with open(resolved, "rb") as handle:
        data = handle.read(window + 1)
    facts.update(exists=True, bytes=resolved.stat().st_size, binary=looks_binary(data),
                 lines=data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0))
    return facts


def evaluate(args) -> dict:
    root = Path(args.root)
    if not root.is_dir():
        raise Refused("root_missing", f"--root {args.root!r} is not a folder")
    root = root.resolve()
    if args.diff is None and args.untracked is None:
        raise Refused("bad_arguments", "give --diff, --untracked or both")
    if [args.diff, args.untracked, *args.allow_file].count("-") > 1:
        raise Refused("bad_arguments", "only one input may come from standard input")
    if args.max_file_bytes < 1 or args.max_file_lines < 1:
        raise Refused("bad_arguments", "size limits are positive whole numbers")
    patterns = load_patterns(root, args.allow, args.allow_file)
    allowed = [(pattern, glob_regex(pattern)) for pattern in patterns]
    extra_tests = [glob_regex(pattern) for pattern in args.test_glob]
    generated = [glob_regex(pattern) for pattern in (*GENERATED_GLOBS, *args.generated_glob)]
    permitted_rules = {PERMITS[value] for value in args.permit}
    files, inputs = [], {}
    if args.diff is not None:
        diff_text, inputs["diff"] = read_input(root, args.diff, "--diff")
        files = parse_diff(diff_text)
        if not files and diff_text.strip():
            raise Refused("unreadable_diff", "--diff holds no unified diff file sections")
    new_files = []
    if args.untracked is not None:
        untracked_text, inputs["untracked"] = read_input(root, args.untracked, "--untracked")
        new_files = untracked_paths(untracked_text)

    findings, permitted, warnings, summary, ignored = [], [], [], [], []
    skip_patterns = [(pattern, glob_regex(pattern)) for pattern in args.ignore]
    own_folder = Path(__file__).resolve().parent.parent
    own_prefix = own_folder.relative_to(root).as_posix() if own_folder.is_relative_to(root) and own_folder != root \
        else None

    def skipped(path: str) -> str:
        """Why a path is left out: the folder of this skill, or an --ignore pattern the task gave."""
        if own_prefix and (path == own_prefix or path.startswith(own_prefix + "/")):
            return "the folder of this skill"
        return next((f"--ignore {pattern}" for pattern, regex in skip_patterns if regex.match(path)), "")

    def finding(rule: str, path: str, detail: str) -> None:
        entry = {"rule": rule, "path": path, "detail": detail}
        (permitted if rule in permitted_rules else findings).append(entry)

    for item in files:
        paths = touched_paths(item)
        reasons = [skipped(path) for path in paths]
        if paths and all(reasons) and not any(unsafe(path) for path in paths):
            ignored.append({"path": item.path, "change": item.change, "reason": reasons[0]})
            continue
        added = [content for hunk in item.hunks for kind, _o, _n, content in hunk["lines"] if kind == "+"]
        removed = sum(1 for hunk in item.hunks for kind, _o, _n, _c in hunk["lines"] if kind == "-")
        added_bytes = sum(len(content.encode("utf-8")) + 1 for content in added)
        summary.append({"path": item.path, "change": item.change, "added_lines": len(added), "removed_lines": removed,
                        "binary": item.binary})
        for path in touched_paths(item):
            if unsafe(path):
                finding("unsafe_path", path, "the path is empty, absolute, uses '..' or names a .git folder")
                continue
            if not any(regex.match(path) for _pattern, regex in allowed):
                finding("outside_allowed_paths", path, f"{item.change}; matches no allowed pattern")
            name = PurePosixPath(path).name
            if name.lower() in LOCK_NAMES or LOCK_SUFFIX.search(name):
                finding("lock_file", path, f"{item.change}; lock files change only through the package manager")
            if any(regex.match(path) for regex in generated):
                finding("generated_file", path, f"{item.change}; the path is a generated or vendored location")
        if item.change == "deleted" and is_test_path(item.old_path or "", extra_tests):
            finding("test_file_deleted", item.old_path or "", "a test file is deleted")
        if item.change == "renamed" and is_test_path(item.old_path or "", extra_tests) \
                and not is_test_path(item.new_path or "", extra_tests):
            finding("test_file_deleted", item.old_path or "", f"a test file moves out of the test paths to {item.new_path}")
        if item.binary and item.change != "deleted":
            size = f", {item.binary_size} bytes" if item.binary_size is not None else ""
            finding("binary_file", item.path, f"{item.change} binary file{size}")
        too_big = len(added) > args.max_file_lines or added_bytes > args.max_file_bytes \
            or (item.binary_size or 0) > args.max_file_bytes
        if too_big:
            finding("large_file", item.path, f"adds {len(added)} lines and {max(added_bytes, item.binary_size or 0)} bytes; "
                                             f"limits {args.max_file_lines} lines, {args.max_file_bytes} bytes")
        markers = [content for hunk in item.hunks for _k, _o, _n, content in hunk["lines"]
                   if GENERATED_MARKER.search(content)]
        if markers and not any(entry["rule"] == "generated_file" and entry["path"] == item.path
                               for entry in findings + permitted):
            finding("generated_file", item.path, f"the diff shows a generated-file marker: {markers[0].strip()[:120]}")
        if "120000" in item.modes:
            finding("symlink", item.path, "a symbolic link is added or changed; it can point outside the allowed paths")
        if "160000" in item.modes or any(content.startswith("Subproject commit ")
                                         for hunk in item.hunks for _k, _o, _n, content in hunk["lines"]):
            finding("submodule", item.path, "a submodule pointer changes")
        if item.new_mode == "100755" and item.change != "added":
            warnings.append(f"{item.path}: the change makes the file executable")
    in_diff = {path for item in files for path in touched_paths(item)}
    window = max(args.max_file_bytes, 8192)
    for path in new_files:
        if unsafe(path):
            finding("unsafe_path", path, "the new file path is absolute, uses '..' or names a .git folder")
            continue
        if skipped(path):
            ignored.append({"path": path, "change": "untracked", "reason": skipped(path)})
            continue
        facts = inspect_new_file(root, path, window)
        summary.append({"path": path, "change": "untracked", "added_lines": facts["lines"], "removed_lines": 0,
                        "binary": facts["binary"]})
        if path in in_diff:
            continue
        if not facts["exists"]:
            warnings.append(f"{path}: listed as a new file but not found below --root")
        if not any(regex.match(path) for _pattern, regex in allowed):
            finding("outside_allowed_paths", path, "new untracked file; matches no allowed pattern")
        name = PurePosixPath(path).name
        if name.lower() in LOCK_NAMES or LOCK_SUFFIX.search(name):
            finding("lock_file", path, "new untracked lock file")
        if any(regex.match(path) for regex in generated):
            finding("generated_file", path, "new untracked file in a generated or vendored location")
        if facts["symlink"] or facts["outside"]:
            finding("symlink", path, "the new file is a symbolic link or resolves outside --root")
        if facts["binary"]:
            finding("binary_file", path, f"new untracked binary file, {facts['bytes']} bytes")
        if facts["bytes"] > args.max_file_bytes or facts["lines"] > args.max_file_lines:
            finding("large_file", path, f"new untracked file of {facts['bytes']} bytes and {facts['lines']} lines; "
                                        f"limits {args.max_file_lines} lines, {args.max_file_bytes} bytes")
    if args.diff is not None and not files:
        warnings.append("the diff is empty")
    return {
        "tool": TOOL, "version": VERSION, "verdict": "fail" if findings else "pass",
        "findings": findings[:LIST_LIMIT], "findings_total": len(findings),
        "permitted": permitted[:LIST_LIMIT], "ignored": ignored[:LIST_LIMIT], "warnings": warnings[:LIST_LIMIT],
        "files": summary[:LIST_LIMIT], "files_total": len(summary),
        "allowed_patterns": patterns, "permit": sorted(set(args.permit)),
        "limits": {"max_file_bytes": args.max_file_bytes, "max_file_lines": args.max_file_lines},
        "inputs": inputs,
    }


def main(argv=None) -> int:
    parser = Arguments(prog="check_diff_paths.py", description=__doc__.splitlines()[0])
    parser.add_argument("--diff", help="unified diff of the change, or - for standard input")
    parser.add_argument("--untracked", help="list of new untracked files, one per line, or - for standard input")
    parser.add_argument("--allow", action="append", default=[], help="allowed path pattern; repeat for more")
    parser.add_argument("--allow-file", action="append", default=[], help="file of allowed patterns, text or JSON")
    parser.add_argument("--permit", action="append", default=[], choices=sorted(PERMITS),
                        help="let one category through, only when the step allows it")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-file-lines", type=int, default=DEFAULT_MAX_FILE_LINES)
    parser.add_argument("--test-glob", action="append", default=[], help="extra pattern for test file paths")
    parser.add_argument("--generated-glob", action="append", default=[], help="extra pattern for generated files")
    parser.add_argument("--ignore", action="append", default=[],
                        help="pattern of files the host placed for this step, left out and listed under ignored")
    parser.add_argument("--root", default=".", help="folder that holds the inputs (default: current folder)")
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

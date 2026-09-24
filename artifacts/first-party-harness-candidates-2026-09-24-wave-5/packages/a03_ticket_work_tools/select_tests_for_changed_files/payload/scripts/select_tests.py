"""Effects: reads Python files and a diff or path list under --root (or from standard input), parses them without running them, and prints one JSON object; writes no files and uses no network.

Select the Python test files that import, directly or through local modules, the files
changed in a diff. Imports are read with the ast module; no project code is imported
or run. A conftest.py applies to every test below its folder, and package __init__.py
files count as imported with their modules. A changed file that no test imports is
matched by name against the text of the test files, which finds tests that run a
script or read a data file by path. Changes that cannot be traced, and changes to
project-wide build or test configuration such as pyproject.toml, are listed, and the
result then recommends the full suite.

Exit status: 0 when at least one test is selected and every changed file is traced,
or when only documentation changed; 1 when the full suite is recommended (a change
that cannot be traced, a project-wide configuration file, a Python file that cannot
be parsed, or no test for any change); 2 when the input is refused.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import stat
import sys
from collections import deque
from pathlib import Path

RECORD_TYPE = "selected_tests/v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_FILES = 50000
HARD_MAX_FILES = 500000
DEFAULT_TEST_PATTERNS = ("test_*.py", "*_test.py", "tests.py")
SKIPPED_FOLDERS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".nox",
                   ".mypy_cache", ".pytest_cache", ".ruff_cache", ".eggs", "site-packages", "build", "dist",
                   ".ipynb_checkpoints"}
DOC_SUFFIXES = {".md", ".rst", ".adoc", ".markdown"}
DOC_NAMES = re.compile(r"^(?:readme|changelog|changes|history|license|licence|authors|contributing|notice)"
                       r"(?:\.(?:md|rst|txt|adoc|markdown))?$", re.IGNORECASE)
PROJECT_WIDE_NAMES = {"pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "pytest.ini", "noxfile.py", ".coveragerc",
                      "pipfile", "pipfile.lock", "poetry.lock", "uv.lock", "constraints.txt"}
PROJECT_WIDE_PATTERN = re.compile(r"^requirements[\w.-]*\.(?:txt|in)$", re.IGNORECASE)
DYNAMIC_CALLS = {"import_module", "__import__"}
NAME_STATUS = re.compile(r"^([ACDMRTUX])(\d*)\t([^\t]+)(?:\t([^\t]+))?$")
IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")
C_ESCAPES = {"n": 10, "t": 9, '"': 34, "\\": 92, "a": 7, "b": 8, "f": 12, "r": 13, "v": 11}


class Refused(Exception):
    """Raised for input the script will not read."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": f"arguments: {message}"})
        raise SystemExit(2)


def emit(document: dict) -> None:
    sys.stdout.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# changed paths
# ---------------------------------------------------------------------------

def unquote(path: str) -> str:
    """Undo git's C-style quoting of unusual path names."""
    if not (len(path) >= 2 and path.startswith('"') and path.endswith('"')):
        return path
    body, output, index = path[1:-1], bytearray(), 0
    while index < len(body):
        character = body[index]
        if character == "\\" and index + 1 < len(body):
            following = body[index + 1]
            if following in C_ESCAPES:
                output.append(C_ESCAPES[following])
                index += 2
                continue
            if re.fullmatch(r"[0-7]{3}", body[index + 1:index + 4]):
                output.append(int(body[index + 1:index + 4], 8))
                index += 4
                continue
        output.extend(character.encode("utf-8"))
        index += 1
    return output.decode("utf-8", errors="replace")


def header_path(value: str, prefix: str) -> str | None:
    value = unquote(value.split("\t", 1)[0].rstrip())
    if value == "/dev/null":
        return None
    return value[len(prefix):] if value.startswith(prefix) else value


def parse_diff(text: str) -> dict[str, str]:
    """Map each changed path of a unified diff to added, deleted, modified or renamed."""
    changes: dict[str, str] = {}
    lines = text.splitlines()

    def close(section):
        if section is None:
            return
        old, new, kind = section["old"], section["new"], section["kind"]
        if old is None and new is None and section["fallback"]:
            old, new = section["fallback"]
            if kind == "deleted":
                new = None
            elif kind == "added":
                old = None
        if kind == "renamed" and old and new:
            changes[old], changes[new] = "renamed", "renamed"
        elif new is None and old:
            changes[old] = "deleted"
        elif old is None and new:
            changes[new] = "added"
        elif new:
            changes[new] = "modified"

    section, index = None, 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git "):
            close(section)
            section = {"old": None, "new": None, "kind": "modified", "header": True, "fallback": None, "git": True}
            match = re.match(r'^diff --git ("a/.+"|a/.+?) ("b/.+"|b/.+)$', line)
            if match:
                section["fallback"] = (header_path(match.group(1), "a/"), header_path(match.group(2), "b/"))
        elif line.startswith("--- ") and index + 1 < len(lines) and lines[index + 1].startswith("+++ ") and (
                section is None or section["header"] or not section["git"]):
            if section is None or not section["header"]:
                close(section)
                section = {"old": None, "new": None, "kind": "modified", "header": True, "fallback": None,
                           "git": False}
            section["old"] = header_path(line[4:], "a/")
            section["new"] = header_path(lines[index + 1][4:], "b/")
            index += 2
            continue
        elif section is not None and section["header"]:
            if line.startswith("@@"):
                section["header"] = False
            elif line.startswith("rename from "):
                section["old"], section["kind"] = unquote(line[12:].strip()), "renamed"
            elif line.startswith("rename to "):
                section["new"], section["kind"] = unquote(line[10:].strip()), "renamed"
            elif line.startswith("deleted file mode"):
                section["kind"] = "deleted"
            elif line.startswith("new file mode"):
                section["kind"] = "added"
            elif line.startswith("Binary files "):
                match = re.match(r"^Binary files (.+?) and (.+?) differ$", line)
                if match:
                    section["old"] = header_path(match.group(1), "a/")
                    section["new"] = header_path(match.group(2), "b/")
        index += 1
    close(section)
    return changes


def parse_path_list(text: str) -> dict[str, str]:
    """Read plain paths, NUL separated paths, or git --name-status lines."""
    changes: dict[str, str] = {}
    entries = text.split("\x00") if "\x00" in text else text.splitlines()
    for raw in entries:
        if not raw.strip():
            continue
        match = NAME_STATUS.match(raw)
        if match:
            code = match.group(1)
            if code in ("R", "C") and match.group(4):
                changes[unquote(match.group(3))] = "renamed"
                changes[unquote(match.group(4))] = "renamed"
            else:
                changes[unquote(match.group(3))] = {"A": "added", "D": "deleted"}.get(code, "modified")
        else:
            changes[unquote(raw.strip())] = "modified"
    return changes


def checked_relative(path: str, real_root: Path) -> str:
    candidate = path.strip()
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if not candidate or "\x00" in candidate:
        raise Refused("a changed path is empty")
    if Path(candidate).is_absolute():
        try:
            candidate = Path(candidate).resolve().relative_to(real_root).as_posix()
        except ValueError as error:
            raise Refused(f"a changed path is outside --root: {path[:120]!r}") from error
    if any(part in ("", ".", "..") for part in candidate.split("/")):
        raise Refused(f"a changed path holds '.' or '..' segments: {path[:120]!r}")
    return candidate


# ---------------------------------------------------------------------------
# the import graph
# ---------------------------------------------------------------------------

def parent_of(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def folder_basedir(folder: str, packages: set[str]) -> str:
    """The first folder upward that is not a package; pytest puts it on the import path."""
    current = folder
    while current and current in packages:
        current = parent_of(current)
    return current


class Project:
    def __init__(self, real_root: Path, patterns: tuple[str, ...], max_files: int, extra_roots: list[str]):
        self.root, self.patterns, self.max_files, self.extra_roots = real_root, patterns, max_files, extra_roots
        self.python: list[str] = []
        self.packages: set[str] = set()
        self.unreadable: dict[str, str] = {}
        self.dynamic: list[str] = []
        self.texts: dict[str, str] = {}

    def is_test(self, relative: str) -> bool:
        name = relative.rsplit("/", 1)[-1]
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in self.patterns)

    def scan(self) -> None:
        for current, folders, names in os.walk(self.root, followlinks=False):
            folders[:] = sorted(name for name in folders if name not in SKIPPED_FOLDERS
                                and not name.endswith(".egg-info")
                                and not os.path.exists(os.path.join(current, name, "pyvenv.cfg")))
            relative_dir = Path(current).relative_to(self.root).as_posix()
            relative_dir = "" if relative_dir == "." else relative_dir
            if "__init__.py" in names and relative_dir:
                self.packages.add(relative_dir)
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                try:
                    info = os.lstat(os.path.join(current, name))
                except OSError:
                    continue
                if not stat.S_ISREG(info.st_mode):
                    continue
                if len(self.python) >= self.max_files:
                    raise Refused(f"more than {self.max_files} Python files under --root; pass a narrower --root "
                                  "or raise --max-files")
                self.python.append((relative_dir + "/" if relative_dir else "") + name)

    def import_roots(self) -> list[str]:
        roots = {""}
        if (self.root / "src").is_dir():
            roots.add("src")
        for package in self.packages:
            if parent_of(package) not in self.packages:
                roots.add(parent_of(package))
        roots.update(self.extra_roots)
        return sorted(roots)

    def read(self, relative: str) -> str | None:
        try:
            with open(self.root / relative, "rb") as stream:
                data = stream.read(MAX_SOURCE_BYTES + 1)
        except OSError as error:
            self.unreadable[relative] = f"not readable: {type(error).__name__}"
            return None
        if len(data) > MAX_SOURCE_BYTES:
            self.unreadable[relative] = f"larger than {MAX_SOURCE_BYTES} bytes"
            return None
        text = data.decode("utf-8", errors="replace")
        self.texts[relative] = text
        return text


def module_names(relative: str, roots: list[str]) -> list[str]:
    names = []
    for root in roots:
        prefix = root + "/" if root else ""
        if not relative.startswith(prefix):
            continue
        parts = relative[len(prefix):-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts and all(IDENTIFIER.match(part) for part in parts):
            names.append(".".join(parts))
    return names


def imported_names(tree: ast.AST, relative: str, dynamic: list[str]) -> list[tuple[int, str, list[str]]]:
    """Return (level, module, names) for every import; level 0 means an absolute import."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((0, alias.name, []) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.level or 0, node.module or "", [alias.name for alias in node.names]))
        elif isinstance(node, ast.Call):
            target = node.func
            name = target.attr if isinstance(target, ast.Attribute) else target.id if isinstance(target, ast.Name) else ""
            if name in DYNAMIC_CALLS:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    found.append((0, node.args[0].value, []))
                elif relative not in dynamic:
                    dynamic.append(relative)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "pytest_plugins"
                                                  for target in node.targets):
            values = node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
            found.extend((0, value.value, []) for value in values
                         if isinstance(value, ast.Constant) and isinstance(value.value, str))
    return found


def build_graph(project: Project, deleted: list[str], allow_unparsed: bool) -> tuple[dict, list[str], int]:
    roots = project.import_roots()
    known = set(project.python) | {path for path in deleted if path.endswith(".py")}
    index: dict[str, set[str]] = {}
    for relative in sorted(known):
        for name in module_names(relative, roots):
            index.setdefault(name, set()).add(relative)
    edges: dict[str, set[str]] = {relative: set() for relative in project.python}
    ambiguous = 0

    def link(source: str, module: str) -> None:
        nonlocal ambiguous
        parts = module.split(".")
        for size in range(1, len(parts) + 1):
            targets = index.get(".".join(parts[:size]), set())
            if len(targets) > 1:
                ambiguous += 1
            edges[source].update(target for target in targets if target != source)

    for relative in project.python:
        text = project.read(relative)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=relative)
        except (SyntaxError, ValueError, RecursionError) as error:
            project.unreadable[relative] = f"does not parse with this Python: {type(error).__name__}"
            continue
        folder = parent_of(relative)
        basedir = folder_basedir(folder, project.packages)
        for level, module, names in imported_names(tree, relative, project.dynamic):
            if level:
                base_parts = folder.split("/") if folder else []
                if level - 1 > len(base_parts):
                    continue
                base = "/".join(base_parts[:len(base_parts) - (level - 1)])
                stem = ((base + "/" if base else "") + module.replace(".", "/")) if module else base
                candidates = [stem + ".py", stem + "/__init__.py"] if module else \
                    [(base + "/" if base else "") + "__init__.py"]
                for name in names:
                    candidates += [(stem + "/" if stem else "") + name + ".py",
                                   (stem + "/" if stem else "") + name + "/__init__.py"]
                edges[relative].update(candidate for candidate in candidates
                                       if candidate in known and candidate != relative)
                continue
            link(relative, module)
            for name in names:
                if name != "*":
                    link(relative, f"{module}.{name}")
            if basedir not in roots:
                local = (basedir + "/" if basedir else "") + module.replace(".", "/")
                edges[relative].update(candidate for candidate in (local + ".py", local + "/__init__.py")
                                       if candidate in known and candidate != relative)
        chain = folder
        while chain and chain in project.packages:
            init = chain + "/__init__.py"
            if init != relative and init in known:
                edges[relative].add(init)
            chain = parent_of(chain)
    for relative in project.python:
        if not project.is_test(relative):
            continue
        folder = parent_of(relative)
        while True:
            conftest = (folder + "/" if folder else "") + "conftest.py"
            if conftest in edges and conftest != relative:
                edges[relative].add(conftest)
            if not folder:
                break
            folder = parent_of(folder)
    if allow_unparsed:
        project.unreadable = {path: reason + "; allowed by --allow-unparsed" for path, reason in
                              project.unreadable.items()}
    return edges, roots, ambiguous


def is_documentation(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    suffix = os.path.splitext(name)[1].lower()
    if suffix == ".py":
        return False
    return suffix in DOC_SUFFIXES or bool(DOC_NAMES.match(name)) or \
        (path.startswith(("docs/", "doc/")) and suffix in (".txt", ".png", ".svg", ".jpg"))


def is_project_wide(path: str) -> bool:
    """Build and test configuration that any test can depend on, such as pyproject.toml."""
    name = path.rsplit("/", 1)[-1].lower()
    return name in PROJECT_WIDE_NAMES or bool(PROJECT_WIDE_PATTERN.match(name))


def select(project: Project, edges: dict, changes: dict[str, str], gone: set[str]) -> tuple[dict, list, list, list]:
    reverse: dict[str, set[str]] = {}
    for source, targets in edges.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)
    tests = sorted(path for path in project.python if project.is_test(path))
    selected: dict[str, list] = {}
    records, untraced, untested = [], [], []
    for path, change in sorted(changes.items()):
        record = {"path": path, "change": change}
        name = path.rsplit("/", 1)[-1]
        if is_documentation(path):
            record.update({"kind": "documentation", "tests": 0})
            records.append(record)
            continue
        if is_project_wide(path):
            record.update({"kind": "project_config", "tests": 0})
            records.append(record)
            untraced.append({"path": path, "reason": "project-wide build or test configuration; any test can depend on it"})
            continue
        found, basis = {}, None
        in_graph = path.endswith(".py") and (path in edges or path in gone)
        record["kind"] = "python" if path.endswith(".py") else "other"
        if in_graph:
            basis = "imports"
            if project.is_test(path) and path in edges:
                found[path] = [path]
            parents = {path: None}
            queue = deque([path])
            while queue:
                current = queue.popleft()
                for importer in sorted(reverse.get(current, ())):
                    if importer not in parents:
                        parents[importer] = current
                        queue.append(importer)
            for test in tests:
                if test in parents and test not in found:
                    chain, node = [], test
                    while node is not None:
                        chain.append(node)
                        node = parents[node]
                    found[test] = chain
        if not found and path not in gone:
            pattern = re.compile(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])")
            for test in tests:
                if test != path and pattern.search(project.texts.get(test, "")):
                    found[test] = [test, path]
            if found:
                basis = "file name in test text"
        for test, chain in found.items():
            selected.setdefault(test, []).append({"changed": path, "via": chain, "basis": basis})
        record["tests"] = len(found)
        records.append(record)
        if found:
            continue
        if in_graph:
            untested.append({"path": path, "reason": "no test imports it or names it"})
        elif path not in gone and not (project.root / path).exists():
            untraced.append({"path": path, "reason": "does not exist under --root"})
        elif record["kind"] == "python":
            untraced.append({"path": path, "reason": "not importable from the project roots, and no test names it"})
        else:
            untraced.append({"path": path, "reason": "not a Python file, and no test names it"})
    return selected, records, untraced, untested


def read_source(name: str, real_root: Path) -> str:
    if name == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        given = Path(name)
        if ".." in given.parts:
            raise Refused("the input path may not contain '..'")
        real = (given if given.is_absolute() else real_root / given).resolve()
        if real_root not in real.parents or not real.is_file():
            raise Refused("the input file must be a regular file inside --root")
        with open(real, "rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise Refused(f"the input is larger than {MAX_INPUT_BYTES} bytes")
    return data.decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description="Select the Python tests that import the changed files.")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--diff", help="unified diff file inside --root, or - for standard input")
    parser.add_argument("--changed-from", help="file inside --root, or -, listing changed paths: plain, NUL "
                                               "separated, or git --name-status lines")
    parser.add_argument("--changed", nargs="+", default=[], help="changed paths relative to --root; may be "
                                                                 "combined with --diff, for example for new files")
    parser.add_argument("--import-root", action="append", default=[], help="extra folder on the import path")
    parser.add_argument("--test-pattern", action="append", default=[], help="test file name pattern, repeatable")
    parser.add_argument("--allow-unparsed", action="store_true",
                        help="report Python files that do not parse without forcing the full suite")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    options = parser.parse_args(argv)
    try:
        if not 1 <= options.max_files <= HARD_MAX_FILES:
            raise Refused(f"--max-files must be between 1 and {HARD_MAX_FILES}")
        root = Path(options.root)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        real_root = root.resolve()
        if options.diff is None and options.changed_from is None and not options.changed:
            raise Refused("name the change with --diff, --changed-from or --changed")
        if options.diff == "-" and options.changed_from == "-":
            raise Refused("only one of --diff and --changed-from can read standard input")
        raw_changes: dict[str, str] = {}
        if options.diff is not None:
            raw_changes.update(parse_diff(read_source(options.diff, real_root)))
        if options.changed_from is not None:
            raw_changes.update(parse_path_list(read_source(options.changed_from, real_root)))
        for path in options.changed:
            raw_changes.setdefault(path, "modified")
        changes = {checked_relative(path, real_root): kind for path, kind in raw_changes.items()}
        if not changes:
            raise Refused("the input names no changed file")
        extra = []
        for folder in options.import_root:
            relative = checked_relative(folder, real_root)
            if not (real_root / relative).is_dir():
                raise Refused(f"--import-root {folder!r} is not a folder inside --root")
            extra.append(relative)
        project = Project(real_root, tuple(options.test_pattern) or DEFAULT_TEST_PATTERNS, options.max_files, extra)
        project.scan()
        # A deleted file, or the old side of a rename, is gone from disk; its importers still name it.
        gone = {path for path, kind in changes.items()
                if kind == "deleted" or (kind == "renamed" and not (real_root / path).exists())}
        edges, roots, ambiguous = build_graph(project, sorted(gone), options.allow_unparsed)
        selected, records, untraced, untested = select(project, edges, changes, gone)
    except Refused as error:
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": str(error)})
        return 2
    def counted(number: int, one: str, many: str) -> str:
        return f"{number} {one if number == 1 else many}"

    warnings = []
    blocking_unreadable = {path: reason for path, reason in project.unreadable.items()
                           if not reason.endswith("allowed by --allow-unparsed")}
    if project.unreadable:
        warnings.append(counted(len(project.unreadable), "Python file was", "Python files were") +
                        " not read or parsed; tests that import through them may be missing")
    if project.dynamic:
        warnings.append(counted(len(project.dynamic), "file loads", "files load") +
                        " modules by a name computed at run time; tests reached that way are not found")
    if ambiguous:
        warnings.append(counted(ambiguous, "import lookup", "import lookups") +
                        " matched more than one file; every match was followed")
    if untested:
        warnings.append(counted(len(untested), "changed file has", "changed files have") +
                        " no test that imports or names it")
    code_changes = [record for record in records if record["kind"] != "documentation"]
    if not code_changes:
        status, code = "no_code_changed", 0
    elif untraced or blocking_unreadable:
        status, code = "full_suite_recommended", 1
    elif not selected:
        status, code = "none_selected", 1
    else:
        status, code = "selected", 0
    test_paths = sorted(selected)
    document = {
        "record_type": RECORD_TYPE, "status": status, "changed": records,
        "selected_tests": [{"path": path, "reasons": selected[path]} for path in test_paths],
        "test_paths": test_paths, "untraced_changes": untraced, "untested_changes": untested,
        "unreadable_files": [{"path": path, "reason": reason} for path, reason in sorted(project.unreadable.items())][:50],
        "dynamic_import_files": sorted(project.dynamic)[:50], "warnings": warnings, "import_roots": roots,
        "counts": {"python_files": len(project.python),
                   "test_files": len([path for path in project.python if project.is_test(path)]),
                   "selected": len(test_paths)},
    }
    emit(document)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

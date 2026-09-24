"""Effects: lists folder entries under --root (or reads a path list from a file under --root or standard input) and prints one JSON object; reads no other file contents, writes no files and uses no network.

Produce a bounded map of a repository. Every file is counted into a category (source,
test, config, docs, data, generated, asset or other) by its name and folder, and each
folder takes the category that holds most of its files. Build output folders are
counted but not expanded. Dependency, cache and version control folders are listed as
skipped and never walked. Symbolic links are counted and never followed. The tree
shows every top-level folder first and then opens the folders that hold the most
source and test files, within a line budget, so a small model can choose where to
look without opening every file.

Exit status: 0 when the map holds source or test files, 1 when it holds none (often a
wrong --root or --focus), 2 when the input is refused (unsafe path, too many entries,
or an unreadable path list).
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import shlex
import stat
import sys
from pathlib import Path

RECORD_TYPE = "repository_layout/v1"
DEFAULT_MAX_ENTRIES = 200000
HARD_MAX_ENTRIES = 2000000
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_LINES = 60
MAX_FOLDER_RECORDS = 400
MAX_LIST_BYTES = 64 * 1024 * 1024
CATEGORIES = ("source", "test", "config", "docs", "data", "generated", "asset", "other")
PRIORITY = {name: index for index, name in enumerate(("test", "source", "config", "docs", "data", "asset",
                                                      "generated", "other"))}

SKIPPED_FOLDERS = {
    ".git": "version control data", ".hg": "version control data", ".svn": "version control data",
    "node_modules": "installed dependencies", "bower_components": "installed dependencies",
    ".venv": "virtual environment", "venv": "virtual environment", "site-packages": "installed dependencies",
    "__pycache__": "cache", ".mypy_cache": "cache", ".pytest_cache": "cache", ".ruff_cache": "cache",
    ".tox": "test environments", ".nox": "test environments", ".eggs": "installed dependencies",
    ".gradle": "cache", ".cache": "cache", ".parcel-cache": "cache", ".turbo": "cache", ".next": "build cache",
    ".nuxt": "build cache", ".svelte-kit": "build cache", ".terraform": "installed dependencies",
    ".ipynb_checkpoints": "cache",
}
GENERATED_FOLDERS = {"build": "build output", "dist": "build output", "out": "build output", "_build": "build output",
                     "coverage": "coverage report", "htmlcov": "coverage report", "generated": "generated files",
                     "__generated__": "generated files", "vendor": "third-party copy", "third_party": "third-party copy"}
TARGET_MARKERS = ("Cargo.toml", "pom.xml", "build.sbt")
TEST_FOLDERS = {"test", "tests", "testing", "__tests__", "spec", "specs", "e2e", "integration_tests", "unit_tests",
                "testdata", "test_data"}
DOCS_FOLDERS = {"docs", "doc", "documentation"}
CONFIG_FOLDERS = {".github", ".circleci", ".gitlab", "config", "configs", "conf", ".vscode", ".idea",
                  ".devcontainer", "deploy", "deployment", "k8s", "helm", "infra", "terraform", "ansible"}
SOURCE_EXTENSIONS = {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt",
                     ".kts", ".scala", ".rb", ".php", ".cs", ".fs", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp",
                     ".m", ".mm", ".swift", ".dart", ".lua", ".pl", ".r", ".jl", ".ex", ".exs", ".erl", ".hs", ".ml",
                     ".clj", ".sh", ".bash", ".ps1", ".sql", ".vue", ".svelte", ".zig", ".groovy", ".proto",
                     ".ipynb", ".html", ".css", ".scss", ".less"}
CONFIG_EXTENSIONS = {".toml", ".ini", ".cfg", ".conf", ".yaml", ".yml", ".properties", ".xml", ".plist"}
DOCS_EXTENSIONS = {".md", ".rst", ".adoc", ".txt", ".mdx"}
DATA_EXTENSIONS = {".csv", ".tsv", ".parquet", ".jsonl", ".ndjson", ".json", ".xlsx", ".xls", ".feather", ".arrow",
                   ".npy", ".npz", ".pkl", ".pickle", ".h5", ".hdf5", ".sqlite", ".db", ".avro", ".orc"}
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp", ".woff", ".woff2", ".ttf",
                    ".otf", ".eot", ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".pdf"}
GENERATED_EXTENSIONS = {".pyc", ".pyo", ".o", ".obj", ".so", ".dll", ".dylib", ".class", ".jar", ".war", ".map",
                        ".lock"}
CONFIG_NAMES = {"pyproject.toml", "setup.py", "setup.cfg", "pipfile", "tox.ini", "pytest.ini", "noxfile.py",
                "package.json", "makefile", "dockerfile", "containerfile", "cargo.toml", "go.mod", "go.work",
                "pom.xml", "gemfile", "rakefile", "composer.json", "justfile", "cmakelists.txt", "meson.build",
                ".editorconfig", ".gitignore", ".gitattributes", ".dockerignore", ".pre-commit-config.yaml",
                ".python-version", ".nvmrc", ".tool-versions", "jenkinsfile", ".gitlab-ci.yml", "procfile",
                "manifest.in", "environment.yml", "build.gradle", "build.gradle.kts", "settings.gradle",
                "settings.gradle.kts", "deno.json", "bunfig.toml", ".travis.yml", "azure-pipelines.yml",
                "bitbucket-pipelines.yml"}
CI_NAMES = {".gitlab-ci.yml", "jenkinsfile", ".travis.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml"}
CI_FOLDERS = (".github/workflows", ".circleci", ".gitlab", ".buildkite")
CONFIG_PATTERNS = (re.compile(r"^requirements.*\.(?:txt|in)$"), re.compile(r"^tsconfig.*\.json$"),
                   re.compile(r"^\.(?:eslintrc|prettierrc|babelrc|stylelintrc)"),
                   re.compile(r"^(?:jest|vitest|vite|webpack|rollup|babel|next|nuxt|svelte|playwright|cypress)"
                              r"\.config\.\w+$"), re.compile(r"^(?:docker-)?compose.*\.ya?ml$"))
GENERATED_PATTERNS = (re.compile(r"^(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|pipfile\.lock|"
                                 r"cargo\.lock|go\.sum|uv\.lock|gemfile\.lock|composer\.lock|bun\.lockb)$"),
                      re.compile(r"\.min\.(?:js|css)$"), re.compile(r"_pb2(?:_grpc)?\.pyi?$"),
                      re.compile(r"\.pb\.go$"), re.compile(r"\.generated\.\w+$"), re.compile(r"\.g\.dart$"))
TEST_FILE_PATTERNS = (re.compile(r"^test_.*\.py$"), re.compile(r".*_tests?\.py$"), re.compile(r"^conftest\.py$"),
                      re.compile(r".*_test\.go$"), re.compile(r".*\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$"),
                      re.compile(r".*Tests?\.(?:java|kt|cs)$"), re.compile(r".*_(?:spec|test)\.rb$"),
                      re.compile(r"^test_.*\.rb$"), re.compile(r".*_test\.exs$"), re.compile(r".*_test\.dart$"))
DOC_NAMES = re.compile(r"^(?:readme|changelog|changes|history|license|licence|copying|contributing|authors|"
                       r"code_of_conduct|security|notice)(?:\.(?:md|markdown|rst|txt|adoc))?$", re.IGNORECASE)
SENSITIVE = (re.compile(r"^\.env(?:\.(?!example$|sample$|template$|dist$)[\w.-]+)?$"),
             re.compile(r"\.(?:pem|key|p12|pfx|jks|keystore)$"), re.compile(r"^credentials.*\.json$"),
             re.compile(r"^service[-_]account.*\.json$"))


class Refused(Exception):
    """Raised for input the script will not read."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": f"arguments: {message}"})
        raise SystemExit(2)


def emit(document: dict) -> None:
    """Print one JSON object with each list item on its own line, which keeps the map short to read."""
    pieces = []
    for key, value in document.items():
        if isinstance(value, list) and value:
            items = ",\n".join("  " + json.dumps(item, ensure_ascii=False) for item in value)
            pieces.append(f" {json.dumps(key)}: [\n{items}\n ]")
        else:
            pieces.append(f" {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}")
    sys.stdout.write("{\n" + ",\n".join(pieces) + "\n}\n")


def classify_file(relative: str) -> str:
    """Category of one file from its name and the names of the folders above it."""
    parts = relative.split("/")
    name = parts[-1]
    lower = name.lower()
    suffix = os.path.splitext(lower)[1]
    folders = [part.lower() for part in parts[:-1]]
    if any(pattern.search(lower) for pattern in GENERATED_PATTERNS) or suffix in GENERATED_EXTENSIONS:
        return "generated"
    if any(pattern.match(name) for pattern in TEST_FILE_PATTERNS):
        return "test"
    if lower in CONFIG_NAMES or any(pattern.match(lower) for pattern in CONFIG_PATTERNS):
        return "config"
    if any(folder in TEST_FOLDERS for folder in folders) and suffix not in DOCS_EXTENSIONS:
        return "test"
    if DOC_NAMES.match(name) or suffix in DOCS_EXTENSIONS or any(folder in DOCS_FOLDERS for folder in folders):
        return "docs"
    if suffix in SOURCE_EXTENSIONS:
        return "source"
    if suffix in CONFIG_EXTENSIONS or any(folder in CONFIG_FOLDERS for folder in folders) or name.startswith("."):
        return "config"
    if suffix in DATA_EXTENSIONS:
        return "data"
    if suffix in ASSET_EXTENSIONS:
        return "asset"
    return "other"


class Folder:
    __slots__ = ("path", "depth", "counts", "direct", "links", "generated_reason", "subfolders")

    def __init__(self, path: str):
        self.path = path
        self.depth = 0 if path == "" else path.count("/") + 1
        self.counts = {name: 0 for name in CATEGORIES}
        self.direct = {name: 0 for name in CATEGORIES}
        self.links, self.generated_reason, self.subfolders = 0, None, []

    @property
    def files(self) -> int:
        return sum(self.counts.values())

    @property
    def code(self) -> int:
        return self.counts["source"] + self.counts["test"]

    def category(self) -> str:
        if self.generated_reason:
            return "generated"
        if not self.files:
            return "empty"
        return max(CATEGORIES, key=lambda name: (self.counts[name], -PRIORITY[name]))


def rank(folder: Folder) -> tuple:
    """Folders with more source and test files come first, then larger folders, then by name."""
    return (-folder.code, -folder.files, folder.path)


class Mapper:
    def __init__(self, max_entries: int):
        self.max_entries = max_entries
        self.entries = 0
        self.folders: dict[str, Folder] = {"": Folder("")}
        self.skipped: list[dict] = []
        self.sensitive: list[str] = []
        self.top_files: list[str] = []
        self.links = 0
        self.extensions: dict[str, int] = {}

    def count_entry(self) -> None:
        self.entries += 1
        if self.entries > self.max_entries:
            raise Refused(f"more than {self.max_entries} entries; map a smaller --focus folder, or pass a list of "
                          "tracked files with --paths-from")

    def folder(self, path: str) -> Folder:
        if path not in self.folders:
            record = Folder(path)
            self.folders[path] = record
            parent = self.folder(path.rsplit("/", 1)[0] if "/" in path else "")
            parent.subfolders.append(record)
            name = path.rsplit("/", 1)[-1].lower()
            if parent.generated_reason and parent.path:
                record.generated_reason = parent.generated_reason
            elif name in GENERATED_FOLDERS:
                record.generated_reason = GENERATED_FOLDERS[name]
            elif name.endswith(".egg-info"):
                record.generated_reason = "package metadata"
        return self.folders[path]

    def add_file(self, relative: str) -> None:
        folder_path, _, name = relative.rpartition("/")
        own = self.folder(folder_path)
        category = "generated" if own.generated_reason else classify_file(relative)
        lower = name.lower()
        if any(pattern.search(lower) for pattern in SENSITIVE):
            self.sensitive.append(relative)
        if not folder_path:
            self.top_files.append(name)
        suffix = os.path.splitext(lower)[1]
        if suffix and category in ("source", "test"):
            self.extensions[suffix] = self.extensions.get(suffix, 0) + 1
        own.direct[category] += 1
        current = own
        while True:
            current.counts[category] += 1
            if current.path == "":
                break
            current = self.folders[current.path.rsplit("/", 1)[0] if "/" in current.path else ""]

    def walk(self, base: Path) -> None:
        """Walk base without following symbolic links; paths are recorded relative to base."""
        pending = [(base, "")]
        while pending:
            directory, relative = pending.pop()
            try:
                with os.scandir(directory) as iterator:
                    entries = sorted(iterator, key=lambda item: item.name)
            except OSError as error:
                self.skipped.append({"path": relative or ".", "reason": f"not readable: {type(error).__name__}"})
                continue
            names = {entry.name for entry in entries}
            for entry in entries:
                self.count_entry()
                path = f"{relative}/{entry.name}" if relative else entry.name
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISLNK(info.st_mode):
                    self.links += 1
                    self.folder(relative).links += 1
                elif stat.S_ISDIR(info.st_mode):
                    reason = SKIPPED_FOLDERS.get(entry.name)
                    if reason is None and os.path.exists(os.path.join(entry.path, "pyvenv.cfg")):
                        reason = "virtual environment"
                    if reason:
                        self.skipped.append({"path": path, "reason": reason})
                        continue
                    record = self.folder(path)
                    if entry.name == "target" and any(marker in names for marker in TARGET_MARKERS):
                        record.generated_reason = "build output"
                    pending.append((Path(entry.path), path))
                elif stat.S_ISREG(info.st_mode):
                    self.add_file(path)

    def from_list(self, paths: list[str]) -> None:
        for raw in paths:
            if not raw.strip():
                continue
            self.count_entry()
            path = raw.strip()
            parts = path.split("/")
            if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
                raise Refused(f"the path list holds an unsafe or empty path segment: {raw[:120]!r}")
            skipped_at = next((index for index, part in enumerate(parts[:-1]) if part in SKIPPED_FOLDERS), None)
            if skipped_at is not None:
                folder_path = "/".join(parts[:skipped_at + 1])
                if not any(item["path"] == folder_path for item in self.skipped):
                    self.skipped.append({"path": folder_path, "reason": SKIPPED_FOLDERS[parts[skipped_at]]})
                continue
            self.add_file(path)


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def label(folder: Folder, top_name: str = "./") -> str:
    name = (folder.path.rsplit("/", 1)[-1] + "/") if folder.path else top_name
    category = folder.category()
    mix = [f"{key} {count}" for key, count in sorted(folder.counts.items(), key=lambda item: (-item[1], item[0]))
           if count and key != category]
    text = f"{name} [{category}] {plural(folder.files, 'file')}"
    if mix:
        text += " (" + ", ".join(mix[:4]) + ")"
    if folder.generated_reason and folder.path:
        text += f"; {folder.generated_reason}, not expanded"
    if folder.links:
        text += f"; {plural(folder.links, 'link')} not followed"
    return text


def skipped_groups(skipped: list[dict]) -> list[dict]:
    """Group skipped folders by name, such as every __pycache__ folder, keeping the first place seen."""
    groups: dict[tuple[str, str], dict] = {}
    for item in skipped:
        name = item["path"].rsplit("/", 1)[-1]
        key = (name, item["reason"])
        if key not in groups:
            groups[key] = {"name": name, "reason": item["reason"], "places": 0, "first": item["path"]}
        groups[key]["places"] += 1
    return sorted(groups.values(), key=lambda group: (-group["places"], group["name"]))


def selection_order(mapper: Mapper, max_depth: int) -> list[Folder]:
    """Every top-level folder first, then the folders below them that hold the most source and test files."""
    top = mapper.folders[""]
    order = sorted((sub for sub in top.subfolders if sub.depth <= max_depth), key=rank)
    queue: list = []
    for folder in order:
        if not folder.generated_reason:
            for sub in folder.subfolders:
                if sub.depth <= max_depth:
                    heapq.heappush(queue, (rank(sub), sub.path))
    while queue:
        _key, path = heapq.heappop(queue)
        folder = mapper.folders[path]
        order.append(folder)
        if not folder.generated_reason:
            for sub in folder.subfolders:
                if sub.depth <= max_depth:
                    heapq.heappush(queue, (rank(sub), sub.path))
    return order


def tree_lines(mapper: Mapper, max_depth: int, max_lines: int, top_name: str) -> tuple[list[str], int]:
    top = mapper.folders[""]
    prefix = "" if top_name == "./" else top_name  # the --focus folder, with a final slash
    order = selection_order(mapper, max_depth)
    skipped_line = None
    if mapper.skipped:
        groups = skipped_groups(mapper.skipped)
        names = ", ".join(f"{group['name']}/ ({group['reason']}" + (f", {group['places']} places)" if group["places"] > 1
                                                                    else ")") for group in groups[:4])
        more = f" and {plural(len(groups) - 4, 'more name')}" if len(groups) > 4 else ""
        skipped_line = f"skipped, not walked: {names}{more}"

    def render(shown: set) -> tuple[list[str], int]:
        lines, hidden_total = [label(top, top_name)], 0

        def visit(folder: Folder, indent: int) -> None:
            nonlocal hidden_total
            if folder.generated_reason and folder is not top:
                return
            hidden = 0
            for sub in sorted(folder.subfolders, key=rank):
                if sub.path in shown:
                    lines.append("  " * indent + label(sub))
                    visit(sub, indent + 1)
                elif sub.depth <= max_depth:
                    hidden += 1
            if hidden:
                hidden_total += hidden
                # Name the exact --focus value, so a reader need not rebuild the path from indentation.
                hint = (f"use --focus {shlex.quote(prefix + folder.path)} to open them" if folder.path
                        else "raise --max-lines to list them")
                lines.append("  " * indent + f"... {plural(hidden, 'more folder')} here; {hint}")

        visit(top, 1)
        if skipped_line:
            lines.append(skipped_line)
        return lines, hidden_total

    count = min(len(order), max_lines - 1)  # every shown folder takes at least one line
    while True:
        lines, hidden = render({folder.path for folder in order[:count]})
        if len(lines) <= max_lines or count == 0:
            return lines[:max_lines], hidden
        count -= 1


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description="Print a bounded, categorized map of a repository.")
    parser.add_argument("--root", default=".", help="repository folder to map")
    parser.add_argument("--focus", default="", help="map only this folder below --root")
    parser.add_argument("--paths-from", default=None, help="read relative file paths, one per line or NUL separated, "
                                                           "from a file inside --root, or - for standard input")
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--max-entries", type=int, default=DEFAULT_MAX_ENTRIES)
    parser.add_argument("--folder-records", action="store_true",
                        help="also list one record per folder, up to 400; off by default to keep the output short")
    options = parser.parse_args(argv)
    focus = options.focus.strip().strip("/")
    try:
        if not 1 <= options.max_depth <= 12:
            raise Refused("--max-depth must be between 1 and 12")
        if not 5 <= options.max_lines <= 1000:
            raise Refused("--max-lines must be between 5 and 1000")
        if not 1 <= options.max_entries <= HARD_MAX_ENTRIES:
            raise Refused(f"--max-entries must be between 1 and {HARD_MAX_ENTRIES}")
        root = Path(options.root)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        real_root = root.resolve()
        if focus and (Path(focus).is_absolute() or any(part in ("", ".", "..") for part in focus.split("/"))):
            raise Refused("--focus must be a relative folder below --root without '.' or '..'")
        mapper = Mapper(options.max_entries)
        if options.paths_from is not None:
            source = "path_list"
            if options.paths_from == "-":
                data = sys.stdin.buffer.read(MAX_LIST_BYTES + 1)
            else:
                given = Path(options.paths_from)
                if ".." in given.parts:
                    raise Refused("the --paths-from path may not contain '..'")
                real = (given if given.is_absolute() else real_root / given).resolve()
                if real_root not in real.parents or not real.is_file():
                    raise Refused("the --paths-from file must be a regular file inside --root")
                with open(real, "rb") as stream:
                    data = stream.read(MAX_LIST_BYTES + 1)
            if len(data) > MAX_LIST_BYTES:
                raise Refused(f"the path list is larger than {MAX_LIST_BYTES} bytes")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as error:
                raise Refused("the path list is not UTF-8") from error
            paths = text.split("\x00") if "\x00" in text else text.splitlines()
            if any(path.startswith('"') for path in paths):
                raise Refused("the path list holds quoted paths; produce it with 'git ls-files -z'")
            if focus:
                paths = [path[len(focus) + 1:] for path in paths if path.startswith(focus + "/")]
            mapper.from_list(paths)
        else:
            source = "walk"
            base = real_root / focus if focus else real_root
            if focus and base.is_symlink():
                raise Refused("--focus may not be a symbolic link")
            try:
                real_base = base.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise Refused("--focus does not exist below --root") from error
            if focus and (real_root not in real_base.parents or not real_base.is_dir()):
                raise Refused("--focus must be a folder inside --root")
            mapper.walk(real_base)
    except Refused as error:
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": str(error)})
        return 2

    def shown(path: str) -> str:
        return f"{focus}/{path}" if focus and path else (focus or path or ".")

    top = mapper.folders[""]
    lines, hidden = tree_lines(mapper, options.max_depth, options.max_lines, f"{focus}/" if focus else "./")
    notes = []
    if mapper.links:
        notes.append(f"{plural(mapper.links, 'symbolic link')} counted and not followed")
    if source == "path_list":
        notes.append("built from a path list: skipped folders are those named in the list, and nothing on disk was read")
    key_files = {"readme": [], "build_and_config": [], "ci": []}
    for name in sorted(mapper.top_files):
        lower = name.lower()
        if lower.startswith("readme"):
            key_files["readme"].append(shown(name))
        if lower in CI_NAMES:
            key_files["ci"].append(shown(name))
        elif classify_file(name) == "config" and lower in CONFIG_NAMES | {"requirements.txt"}:
            key_files["build_and_config"].append(shown(name))
    for path in CI_FOLDERS:
        if path in mapper.folders:
            key_files["ci"].append(shown(path) + "/")
    usable = [folder for folder in mapper.folders.values()
              if folder.path and not folder.generated_reason and folder.depth <= options.max_depth]
    source_folders = [folder for folder in usable if folder.counts["source"] and not any(
        sub.counts["source"] == folder.counts["source"] for sub in folder.subfolders)]
    source_folders.sort(key=lambda item: (-item.counts["source"], item.path))
    test_folders = [folder for folder in mapper.folders.values() if not folder.generated_reason and folder.direct["test"]]
    test_folders.sort(key=lambda item: (-item.direct["test"], item.path))
    languages = [{"extension": ext, "files": count}
                 for ext, count in sorted(mapper.extensions.items(), key=lambda item: (-item[1], item[0]))[:8]]
    status = "ok" if top.counts["source"] or top.counts["test"] else "no_source_found"
    groups = skipped_groups(mapper.skipped)
    document = {
        "record_type": RECORD_TYPE, "status": status, "source": source, "root": options.root, "focus": focus or None,
        "totals": {"files": top.files, "folders": len(mapper.folders) - 1, "links": mapper.links,
                   "skipped_folders": len(mapper.skipped),
                   "by_category": {key: value for key, value in top.counts.items() if value}},
        "languages": languages, "key_files": key_files,
        "largest_source_folders": [{"path": shown(folder.path), "source_files": folder.counts["source"]}
                                   for folder in source_folders[:5]],
        "test_file_folders": [{"path": shown(folder.path), "test_files_here": folder.direct["test"]}
                              for folder in test_folders[:5]],
        "tree": lines, "omitted_tree_folders": hidden,
        "skipped": [dict(group, first=shown(group["first"])) for group in groups[:20]],
        "sensitive_files": {"count": len(mapper.sensitive), "paths": [shown(path) for path in mapper.sensitive[:20]]},
        "notes": notes,
    }
    if options.folder_records:
        records = []
        for folder in sorted(mapper.folders.values(), key=lambda item: item.path):
            if folder.path == "" or folder.depth > options.max_depth:
                continue
            record = {"path": shown(folder.path), "category": folder.category(), "files": folder.files,
                      "counts": {key: value for key, value in folder.counts.items() if value}}
            if folder.generated_reason:
                record["reason"] = folder.generated_reason
            if folder.links:
                record["links"] = folder.links
            records.append(record)
        if len(records) > MAX_FOLDER_RECORDS:
            notes.append(f"{len(records) - MAX_FOLDER_RECORDS} folder records beyond {MAX_FOLDER_RECORDS} are not "
                         "listed; totals stay exact")
            records = records[:MAX_FOLDER_RECORDS]
        document["folders"] = records
    emit(document)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

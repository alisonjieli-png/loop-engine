"""The facts of a Python library release for its API cards: the PyPI record, the wheels, and the repository at the tag.

```text
one library release (a row of python_libraries.json)
├── PyPI: the release's JSON record (pypi.org), naming each file with its SHA-256
├── wheels: the library's and each pinned dependency's, chosen for the pinned interpreter (cp314, abi3 or pure;
│   manylinux up to the machine's glibc), streamed once from files.pythonhosted.org, the published SHA-256 checked,
│   every member checked against the wheel's own RECORD, and unpacked under a folder named by that digest (no path
│   outside it, no link)
├── the repository at the tag: one tree read; a wheel file is proven when the git blob identity of its bytes is
│   the tree's at the same path (a src/ layout or a package below the root maps by the file's unique path suffix)
└── the text corpus: every proven Python file, and the tag's Cython and Python sources under the same package
    folders that the wheel does not ship (read by blob identity), less any file whose nearest licence file or own
    licence statement names another licence; every line, and every line of every string literal, indexed
```

Nothing here imports the library: the sandbox does (python_native.py).
"""
from __future__ import annotations

import ast
import base64
import csv
import hashlib
import io
import json
import re
import shutil
import tokenize
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME
from loop_engine.core.library_ingestion.licences import governing_licence_path, is_licence_file, match_licence
from loop_engine.core.library_ingestion.record_rules import git_blob_identity

PYPI_HOST, FILES_HOST = "pypi.org", "files.pythonhosted.org"
WHEEL_SUFFIX = ".whl"
MAXIMUM_WHEEL_BYTES = 192 * 1024 * 1024
#: A wheel's metadata folder, its RECORD and the signature files RECORD cannot list with a hash.
DIST_INFO_SUFFIX, RECORD_NAME, UNHASHED = ".dist-info", "RECORD", ("RECORD", "RECORD.jws", "RECORD.p7s")
#: A wheel's .data folder: purelib and platlib install beside the packages; scripts, headers and data do not.
DATA_SUFFIX, INSTALLED_DATA = ".data", ("purelib", "platlib")
#: The file mode bits of a symbolic link in a zip member's external attributes.
LINK_MODE, MODE_MASK = 0o120000, 0o170000
UNPACKED_MARKER = ".baltor-unpacked.json"
#: The source files a text corpus reads: Python, Cython, stubs.
SOURCE_SUFFIXES = (".py", ".pyx", ".pxd", ".pxi", ".pyi")
PYTHON_SUFFIX = ".py"
#: At most this many repository files outside the wheel join one corpus (a package's own sources at the tag).
MAXIMUM_EXTRA_FILES = 2000
TEST_PARTS = frozenset(("tests", "test", "testing", "benchmarks", "conftest.py"))
#: A line of text the coverage rule counts: at least this many characters once its spaces are collapsed.
MINIMUM_LINE = 4


class WheelError(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def pypi_address(distribution: str, version: str) -> str:
    """The address of a release's PyPI JSON record."""
    return urllib.parse.urlunsplit((HTTPS_SCHEME, PYPI_HOST, f"/pypi/{distribution}/{version}/json", "", ""))


def pypi_record(reader, distribution: str, version: str) -> tuple:
    """(document, fetched answer) of a release's PyPI JSON record; raises WheelError."""
    answer = reader.get(pypi_address(distribution, version))
    if answer.status != 200:
        raise WheelError("source_unreadable", f"{distribution} {version}: PyPI answered {answer.status}")
    document = json.loads(answer.body)
    if (document.get("info") or {}).get("version") != version:
        raise WheelError("source_unreadable", f"{distribution}: PyPI's record is not version {version}")
    return document, answer


# -- which wheel ------------------------------------------------------------------------------------------------
_WHEEL = re.compile(r"(?P<name>[^-]+)-(?P<version>[^-]+)(?:-(?P<build>\d[^-]*))?-(?P<python>[^-]+)-(?P<abi>[^-]+)-"
                    r"(?P<platform>[^-]+)\.whl\Z")
_MANYLINUX = re.compile(r"manylinux_(\d+)_(\d+)_(\w+)\Z")
#: The legacy manylinux tags and the glibc each stands for (PEP 600).
LEGACY_MANYLINUX = {"manylinux1": (2, 5), "manylinux2010": (2, 12), "manylinux2014": (2, 17)}
_CPYTHON = re.compile(r"cp(\d)(\d+)\Z")


def wheel_rank(filename: str, interpreter: dict) -> "tuple | None":
    """How well a wheel fits the pinned interpreter (lower is better), or None when it cannot be installed:
    its own ABI (cp314) first, then the stable ABI (abi3 of an earlier CPython), then pure Python; on Linux the
    newest manylinux the machine's glibc allows."""
    match = _WHEEL.match(filename)
    if not match:
        return None
    pythons, abis, platforms = (match.group(part).split(".") for part in ("python", "abi", "platform"))
    own, glibc, machine = interpreter["python_tag"], tuple(interpreter["glibc"]), interpreter["machine"]
    major, minor = (int(part) for part in _CPYTHON.match(own).groups())
    best = None
    for python in pythons:
        for abi in abis:
            if python == own and abi == own:
                kind = 0
            elif abi == "abi3" and _CPYTHON.match(python) and (int(_CPYTHON.match(python).group(1)), int(
                    _CPYTHON.match(python).group(2))) <= (major, minor):
                kind = 1
            elif abi == "none" and python in ("py3", f"py{major}", f"py{major}{minor}", own):
                kind = 2
            else:
                continue
            for platform in platforms:
                if platform == "any":
                    version = (0, 0)
                else:
                    legacy = next((tag for tag in LEGACY_MANYLINUX if platform == f"{tag}_{machine}"), None)
                    if legacy is not None:
                        version = LEGACY_MANYLINUX[legacy]
                    else:
                        found = _MANYLINUX.match(platform)
                        if not found or found.group(3) != machine:
                            continue
                        version = (int(found.group(1)), int(found.group(2)))
                    if version > glibc:
                        continue
                rank = (kind, tuple(-part for part in version), filename)
                best = rank if best is None or rank < best else best
    return best


def choose_wheel(document: dict, interpreter: dict) -> dict:
    """The release file the pinned interpreter installs: the best ranked wheel PyPI publishes with a SHA-256."""
    rows = [row for row in document.get("urls", ()) if row.get("packagetype") == "bdist_wheel" and not
            row.get("yanked") and (row.get("digests") or {}).get("sha256")]
    ranked = sorted((rank, row["filename"], row) for row in rows
                    for rank in [wheel_rank(row["filename"], interpreter)] if rank is not None)
    if not ranked:
        raise WheelError("engine_binary_unverified", f"no wheel of {document['info']['name']} "
                                                     f"{document['info']['version']} installs on this interpreter")
    return ranked[0][2]


# -- one wheel, unpacked ------------------------------------------------------------------------------------------
def _record_rows(text: str) -> dict:
    rows = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2 and row[0]:
            rows[row[0]] = row[1]
    return rows


def _digest_hex(value: str) -> "str | None":
    algorithm, _, encoded = value.partition("=")
    if algorithm != "sha256" or not encoded:
        return None
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).hex()


def install_path(name: str) -> "str | None":
    """Where a wheel member installs, relative to the folder the wheel is unpacked into; None when it does not
    install beside the packages (a .data folder's scripts, headers or data)."""
    parts = PurePosixPath(name).parts
    if parts and parts[0].endswith(DATA_SUFFIX) and len(parts) > 1:
        return "/".join(parts[2:]) if parts[1] in INSTALLED_DATA and len(parts) > 2 else None
    return name


def unpack_wheel(path: Path, folder: Path) -> dict:
    """Unpack a wheel's regular files under folder, each member's bytes checked against the wheel's RECORD; raises
    WheelError when a member is missing from RECORD, differs from it, is a link or would leave the folder."""
    folder = Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    members = {}
    with zipfile.ZipFile(path) as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        records = [name for name in names if PurePosixPath(name).name == RECORD_NAME and len(
            PurePosixPath(name).parts) == 2 and PurePosixPath(name).parts[0].endswith(DIST_INFO_SUFFIX)]
        if len(records) != 1:
            raise WheelError("engine_binary_unverified", f"{Path(path).name}: {len(records)} RECORD files")
        record = _record_rows(archive.read(records[0]).decode("utf-8"))
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in name or (info.external_attr >> 16) & MODE_MASK \
                    == LINK_MODE:
                raise WheelError("engine_binary_unverified", f"{Path(path).name}: member {name[:120]} is refused")
            data = archive.read(info)
            digest = hashlib.sha256(data).hexdigest()
            if pure.name not in UNHASHED or len(pure.parts) != 2:
                expected = _digest_hex(record.get(name, ""))
                if expected != digest:
                    raise WheelError("engine_binary_unverified", f"{Path(path).name}: {name[:120]} differs from RECORD")
            target_name = install_path(name)
            if target_name is None:
                continue
            target = folder.joinpath(*PurePosixPath(target_name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            members[target_name] = digest
    summary = {"files": len(members), "members": members}
    (folder / UNPACKED_MARKER).write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    return summary


@dataclass(frozen=True)
class InstalledWheel:
    distribution: str
    version: str
    filename: str
    url: str
    sha256: str
    size_bytes: int
    retrieved_at: str
    folder: Path
    members: dict  # installed path -> SHA-256


def install(reader, distribution: str, version: str, interpreter: dict, cache_root: Path) -> tuple:
    """(InstalledWheel, PyPI document, PyPI answer) of one release: its record read, its wheel chosen, streamed once,
    checked and unpacked under cache_root/<sha256>, reused while that folder holds the unpacked marker."""
    document, answer = pypi_record(reader, distribution, version)
    row = choose_wheel(document, interpreter)
    published = row["digests"]["sha256"]
    folder = Path(cache_root) / published[:2] / published
    marker = folder / UNPACKED_MARKER
    digested = reader.digest(row["url"], published={"sha256": published}, maximum_bytes=MAXIMUM_WHEEL_BYTES,
                             inspect=lambda path: unpack_wheel(path, folder), use_cache=marker.is_file())
    if not digested.ok or digested.sha256 != published:
        raise WheelError("engine_binary_unverified", f"{row['filename']}: the download does not match PyPI's SHA-256")
    summary = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else digested.inspected
    if not summary or summary.get("files", 0) < 1:
        raise WheelError("engine_binary_unverified", f"{row['filename']}: nothing was unpacked")
    wheel = InstalledWheel(distribution, version, row["filename"], row["url"], published,
                           int(digested.size_bytes or row.get("size") or 0), digested.retrieved_at, folder,
                           dict(summary["members"]))
    return wheel, document, answer


def requirement(pin: str) -> tuple:
    """(distribution, version) of an exact pin "name==version"."""
    name, separator, version = pin.partition("==")
    if not separator or not name.strip() or not version.strip():
        raise ValueError(f"an environment pin is name==version: {pin!r}")
    return name.strip(), version.strip()


# -- the repository at the tag ------------------------------------------------------------------------------------
@dataclass
class Repository:
    """The tree at the tag (path -> blob identity) and which wheel files it proves."""

    blobs: dict
    proven: dict = field(default_factory=dict)  # wheel path -> repository path
    differs: list = field(default_factory=list)  # wheel Python files whose bytes are not the tag's
    absent: list = field(default_factory=list)  # wheel Python files the tag does not hold (generated at build)
    prefixes: dict = field(default_factory=dict)  # top-level package -> repository folder that holds it


def prove(blobs: dict, wheel: InstalledWheel) -> Repository:
    """Which of the wheel's Python files are the tag's bytes: the blob identity of the file must be the tree's at
    the same path, or at the one path whose suffix is the wheel path (src/ layouts, packages below the root)."""
    by_name = {}
    for path in blobs:
        by_name.setdefault(PurePosixPath(path).name, []).append(path)
    repository = Repository(dict(blobs))
    prefixes = {}
    for name in sorted(wheel.members):
        if not name.endswith(PYTHON_SUFFIX) or PurePosixPath(name).parts[0].endswith(DIST_INFO_SUFFIX):
            continue
        candidates = [path for path in by_name.get(PurePosixPath(name).name, ()) if path == name or
                      path.endswith("/" + name)]
        identity = git_blob_identity((wheel.folder / name).read_bytes())
        same = sorted((path for path in candidates if blobs[path] == identity), key=lambda path: (len(path), path))
        if same:
            repository.proven[name] = same[0]
            top = PurePosixPath(name).parts[0]
            prefixes.setdefault(top, {}).setdefault(same[0][:len(same[0]) - len(name)], 0)
            prefixes[top][same[0][:len(same[0]) - len(name)]] += 1
        elif candidates:
            repository.differs.append(name)
        else:
            repository.absent.append(name)
    repository.prefixes = {top: max(counts.items(), key=lambda pair: (pair[1], -len(pair[0])))[0]
                           for top, counts in prefixes.items()}
    return repository


def extra_sources(repository: Repository) -> list:
    """The tag's Cython and Python source paths under the wheel's package folders that the wheel does not ship
    (the text of compiled modules lives there), tests left out, sorted, at most MAXIMUM_EXTRA_FILES."""
    shipped = set(repository.proven.values())
    found = []
    for top, prefix in sorted(repository.prefixes.items()):
        folder = f"{prefix}{top}/"
        for path in repository.blobs:
            if path.startswith(folder) and path.endswith(SOURCE_SUFFIXES) and path not in shipped and not (
                    set(PurePosixPath(path).parts) & TEST_PARTS):
                found.append(path)
    return sorted(set(found))[:MAXIMUM_EXTRA_FILES]


# -- the text corpus ----------------------------------------------------------------------------------------------
def normal(line: str) -> str:
    return " ".join(str(line).split())


def string_lines(text: str):
    """The lines of every string literal of a Python file, as the running module holds them (escapes read)."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.STRING:
                continue
            try:
                value = ast.literal_eval(token.string)
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                continue
            if isinstance(value, str):
                yield from value.splitlines()
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return


@dataclass
class Corpus:
    """Every line of the release's licence-cleared source files, with the files that hold it."""

    files: list = field(default_factory=list)  # [repository path]
    lines: dict = field(default_factory=dict)  # normalized line -> set of file indices
    excluded: dict = field(default_factory=dict)  # repository path -> reason

    def add(self, path: str, text: str) -> None:
        index = len(self.files)
        self.files.append(path)
        rows = set(text.splitlines())
        if path.endswith(PYTHON_SUFFIX):
            rows.update(string_lines(text))
        for row in rows:
            key = normal(row)
            if key:
                self.lines.setdefault(key, set()).add(index)

    def trace(self, text: str) -> tuple:
        """(share of the counted lines found, counted lines, the file holding the most of them or None)."""
        counted = [normal(row) for row in str(text or "").splitlines() if len(normal(row)) >= MINIMUM_LINE]
        if not counted:
            return 1.0, 0, None
        hits, votes = 0, {}
        for row in counted:
            holders = self.lines.get(row)
            if holders:
                hits += 1
                for index in holders:
                    votes[index] = votes.get(index, 0) + 1
        best = min(votes, key=lambda index: (-votes[index], self.files[index])) if votes else None
        return hits / len(counted), len(counted), None if best is None else self.files[best]


def licence_problem(path: str, text: str, spdx: str, licence_files: list, root_licence: str,
                    licence_texts: dict, foreign_licences) -> "str | None":
    """Why a source file's own licence is not the repository's, or None: the nearest licence file names another
    licence (nested_licence_differs), or the file states one (module_licence_differs)."""
    governing = governing_licence_path(path, licence_files)
    if governing is not None and governing != root_licence:
        governing_text = licence_texts.get(governing)
        matched = match_licence(governing_text.decode("utf-8", "replace")).spdx if governing_text else None
        if matched != spdx:
            return "nested_licence_differs"
    try:
        if path.endswith(PYTHON_SUFFIX) and foreign_licences(text, spdx):
            return "module_licence_differs"
    except (SyntaxError, ValueError, RecursionError):
        return None
    return None


def nested_licence_paths(paths, blobs: dict, root_licence: str) -> list:
    """The licence files a corpus must read to decide its files: the nearest one of each, when it is not the root's."""
    licence_files = [path for path in blobs if is_licence_file(path)]
    return sorted({found for path in paths for found in [governing_licence_path(path, licence_files)]
                   if found is not None and found != root_licence})


# -- static wheel AST surface reader (the non-importing engine variation) ----------------------------------------
AST_RESULTS_RECORD = "python_api_introspection/v1"


def _module_source_file(wheel_folder: Path, module_name: str) -> "tuple[str, bool] | None":
    rel = module_name.replace(".", "/")
    init = f"{rel}/__init__.py"
    if (wheel_folder / init).is_file():
        return init, True
    single = f"{rel}.py"
    if (wheel_folder / single).is_file():
        return single, False
    return None


def _decorator_names(node) -> set:
    names = set()
    for decorator in getattr(node, "decorator_list", ()):
        if isinstance(decorator, ast.Name):
            names.add(decorator.id)
        elif isinstance(decorator, ast.Attribute):
            names.add(decorator.attr)
    return names


def _ast_type(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ast.unparse(node)


def _ast_default(node: ast.AST, sentinels: set = frozenset()) -> str:
    if isinstance(node, ast.Name) and node.id in sentinels:
        return "<object object>"
    return ast.unparse(node)[:200]


def _ast_signature(node: "ast.FunctionDef | ast.AsyncFunctionDef", *, drop_first: bool = False,
                   omit_returns: bool = False, sentinels: set = frozenset()) -> dict:
    args = node.args
    pos = [(arg, "positional_only") for arg in args.posonlyargs] + [
        (arg, "positional_or_keyword") for arg in args.args]
    pos_defaults = [None] * (len(pos) - len(args.defaults)) + list(args.defaults)
    items = list(zip(pos, pos_defaults))
    if drop_first and items:
        items = items[1:]
    rows = []
    for (arg, kind), default in items:
        row = {"name": arg.arg, "kind": kind}
        if arg.annotation is not None:
            row["type"] = _ast_type(arg.annotation)
        if default is not None:
            row["default"] = _ast_default(default, sentinels)
        rows.append(row)
    if args.vararg is not None:
        row = {"name": args.vararg.arg, "kind": "var_positional"}
        if args.vararg.annotation is not None:
            row["type"] = _ast_type(args.vararg.annotation)
        rows.append(row)
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        row = {"name": arg.arg, "kind": "keyword_only"}
        if arg.annotation is not None:
            row["type"] = _ast_type(arg.annotation)
        if default is not None:
            row["default"] = _ast_default(default, sentinels)
        rows.append(row)
    if args.kwarg is not None:
        row = {"name": args.kwarg.arg, "kind": "var_keyword"}
        if args.kwarg.annotation is not None:
            row["type"] = _ast_type(args.kwarg.annotation)
        rows.append(row)
    returns = None if omit_returns or node.returns is None else _ast_type(node.returns)
    return {"params": rows, "returns": returns}


def _parse_wheel_module(wheel_folder: Path, module_name: str, cache: dict) -> "dict | None":
    if module_name in cache:
        return cache[module_name]
    located = _module_source_file(wheel_folder, module_name)
    if located is None:
        cache[module_name] = None
        return None
    rel_file, is_package = located
    try:
        tree = ast.parse((wheel_folder / rel_file).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        cache[module_name] = None
        return None
    package_parts = module_name.split(".") if is_package else module_name.split(".")[:-1]
    declared_all, defs, imports, sentinels = None, {}, {}, set()
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs[stmt.name] = stmt
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(stmt.value, (ast.List, ast.Tuple)):
                    if all(isinstance(elt, ast.Constant) and isinstance(elt.value, str) for elt in stmt.value.elts):
                        declared_all = [elt.value for elt in stmt.value.elts]
                elif isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call) and isinstance(
                        stmt.value.func, ast.Name) and stmt.value.func.id == "object" and not stmt.value.args:
                    sentinels.add(target.id)
        elif isinstance(stmt, ast.ImportFrom):
            base = package_parts[:len(package_parts) - (stmt.level - 1)] if stmt.level else []
            target_mod = ".".join(base + ([stmt.module] if stmt.module else []))
            if target_mod:
                for alias in stmt.names:
                    if alias.name != "*":
                        imports[alias.asname or alias.name] = (target_mod, alias.name)
    parsed = {"name": module_name, "file": rel_file, "is_package": is_package, "all": declared_all,
              "defs": defs, "imports": imports, "sentinels": sentinels}
    cache[module_name] = parsed
    return parsed


def _resolve_ast_symbol(wheel_folder: Path, module_name: str, symbol: str, cache: dict, depth: int = 0) -> "tuple | None":
    if depth > 6:
        return None
    parsed = _parse_wheel_module(wheel_folder, module_name, cache)
    if parsed is None:
        return None
    if symbol in parsed["defs"]:
        return module_name, parsed["file"], symbol, parsed["defs"][symbol]
    if symbol in parsed["imports"]:
        target_mod, orig_name = parsed["imports"][symbol]
        return _resolve_ast_symbol(wheel_folder, target_mod, orig_name, cache, depth + 1)
    return None


def _ast_class_members(owner_key: str, rel_file: str, node: ast.ClassDef,
                       sentinels: set = frozenset()) -> list:
    by_name = {}
    setters = {stmt.name for stmt in node.body if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and
               any(isinstance(dec, ast.Attribute) and dec.attr == "setter" for dec in stmt.decorator_list)}
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and not stmt.name.startswith("_"):
            decs = _decorator_names(stmt)
            if "setter" in decs or "deleter" in decs:
                continue
            source = {"root": 0, "file": rel_file, "line": stmt.lineno, "compiled": False}
            doc = ast.get_docstring(stmt)
            flags = (["abstract"] if "abstractmethod" in decs else []) + (
                ["async"] if isinstance(stmt, ast.AsyncFunctionDef) else [])
            if "property" in decs or "cached_property" in decs:
                qualifiers = (["abstract"] if "abstractmethod" in decs else []) + (
                    ["readonly"] if "property" in decs and stmt.name not in setters else [])
                by_name[stmt.name] = {"name": stmt.name, "owner": owner_key, "kind": "property",
                                      "qualifiers": qualifiers,
                                      "type": _ast_type(stmt.returns) if stmt.returns is not None else None,
                                      "doc": doc, "source": source}
            elif "staticmethod" in decs:
                by_name[stmt.name] = {"name": stmt.name, "owner": owner_key, "kind": "method",
                                      "qualifiers": flags + ["staticmethod"],
                                      "signature": _ast_signature(stmt, drop_first=False, sentinels=sentinels),
                                      "doc": doc, "source": source}
            elif "classmethod" in decs:
                by_name[stmt.name] = {"name": stmt.name, "owner": owner_key, "kind": "method",
                                      "qualifiers": flags + ["classmethod"],
                                      "signature": _ast_signature(stmt, drop_first=True, sentinels=sentinels),
                                      "doc": doc, "source": source}
            else:
                by_name[stmt.name] = {"name": stmt.name, "owner": owner_key, "kind": "method",
                                      "qualifiers": flags,
                                      "signature": _ast_signature(stmt, drop_first=True, sentinels=sentinels),
                                      "doc": doc, "source": source}
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and not stmt.target.id.startswith("_"):
            row = {"name": stmt.target.id, "owner": owner_key, "kind": "field", "qualifiers": [],
                   "type": _ast_type(stmt.annotation), "doc": None, "source": None}
            if stmt.value is not None:
                row["default"] = _ast_default(stmt.value, sentinels)
            by_name[stmt.target.id] = row
        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            if not name.startswith("_") and name not in by_name:
                by_name[name] = {"name": name, "owner": owner_key, "kind": "constant", "qualifiers": [],
                                 "value": _ast_default(stmt.value, sentinels), "doc": None, "source": None}
    return [by_name[name] for name in sorted(by_name)]


def read_wheel_ast(wheel_folder: Path, spec: dict, interpreter_version: str = "") -> dict:
    """Read a wheel's public Python surface from its syntax trees alone (no import), in the record shape
    python_introspect.read writes (python_api_introspection/v1)."""
    wheel_folder = Path(wheel_folder)
    excluded = tuple(spec.get("exclude", ()))
    cache = {}
    queue, visited, modules, candidates, aliases, order = list(spec["modules"]), set(), [], {}, {}, []
    while queue:
        name = queue.pop(0)
        parts = name.split(".")
        if name in visited or any(part.startswith("_") or part in TEST_PARTS for part in parts[1:]) or any(
                name == prefix or name.startswith(prefix + ".") for prefix in excluded):
            continue
        visited.add(name)
        parsed = _parse_wheel_module(wheel_folder, name, cache)
        if parsed is None:
            modules.append({"name": name, "ok": False, "error": "ModuleNotFoundError: no .py source in wheel"})
            continue
        declared = parsed["all"] is not None
        names = sorted(set(parsed["all"])) if declared else sorted(
            key for key in set(parsed["defs"]) | set(parsed["imports"]) if not key.startswith("_"))
        modules.append({"name": name, "ok": True,
                        "file": {"root": 0, "file": parsed["file"], "line": None, "compiled": False},
                        "declared_all": declared, "exported": len(names)})
        for attribute in names:
            if attribute.startswith("_"):
                continue
            sub = f"{name}.{attribute}"
            if spec.get("recurse") and declared and _module_source_file(wheel_folder, sub) is not None:
                queue.append(sub)
                continue
            resolved = _resolve_ast_symbol(wheel_folder, name, attribute, cache)
            if resolved is None:
                continue
            def_mod, def_file, orig_name, node = resolved
            identity = (def_file, node.lineno, orig_name)
            path = f"{name}.{attribute}"
            if identity in candidates:
                aliases.setdefault(identity, []).append(path)
                continue
            candidates[identity] = (path, name, attribute, def_mod, def_file, orig_name, node)
            order.append(identity)
    objects = []
    for identity in order:
        path, module_name, attribute, def_mod, def_file, orig_name, node = candidates[identity]
        key = f"{def_mod}.{orig_name}"
        sentinels = (cache.get(def_mod) or {}).get("sentinels", frozenset())
        source = {"root": 0, "file": def_file, "line": node.lineno, "compiled": False}
        record = {"path": path, "module": module_name, "qualname": attribute, "key": key,
                  "kind": "class" if isinstance(node, ast.ClassDef) else "function", "source": source,
                  "doc": ast.get_docstring(node), "aliases": sorted(aliases.get(identity, []))[:20]}
        if isinstance(node, ast.ClassDef):
            init = next((stmt for stmt in node.body if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__"),
                        None)
            mro, members_by_name = [], {row["name"]: row for row in _ast_class_members(key, def_file, node, sentinels)}
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else None
                resolved_base = _resolve_ast_symbol(wheel_folder, def_mod, base_name, cache) if base_name else None
                if resolved_base is not None and isinstance(resolved_base[3], ast.ClassDef):
                    base_mod, base_file, base_orig, base_node = resolved_base
                    base_key = f"{base_mod}.{base_orig}"
                    base_sentinels = (cache.get(base_mod) or {}).get("sentinels", frozenset())
                    mro.append({"key": base_key, "owned": True})
                    for row in _ast_class_members(base_key, base_file, base_node, base_sentinels):
                        members_by_name.setdefault(row["name"], row)
                elif base is not None:
                    raw = ast.unparse(base)
                    if raw != "object":
                        mro.append({"key": raw, "owned": False})
            record.update(constructor=_ast_signature(init, drop_first=True, omit_returns=True, sentinels=sentinels)
                          if init is not None else {"params": [], "returns": None},
                          mro=mro, members=[members_by_name[k] for k in sorted(members_by_name)])
        else:
            decs = _decorator_names(node)
            flags = (["abstract"] if "abstractmethod" in decs else []) + (
                ["async"] if isinstance(node, ast.AsyncFunctionDef) else [])
            record.update(signature=_ast_signature(node, sentinels=sentinels), qualifiers=flags)
        objects.append(record)
    return {"record_type": AST_RESULTS_RECORD, "interpreter": interpreter_version, "modules": modules,
            "objects": objects, "events": []}


__all__ = ["WheelError", "pypi_record", "wheel_rank", "choose_wheel", "unpack_wheel", "install", "InstalledWheel",
           "requirement", "Repository", "prove", "extra_sources", "Corpus", "licence_problem", "normal",
           "string_lines", "nested_licence_paths", "read_wheel_ast", "PYPI_HOST", "FILES_HOST"]


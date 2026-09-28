"""Line function_extracts: one tested function per documented function of a well-tested, permissively licensed
Python library, copied with exactly the code it needs.

```text
function_sources.json: repository, branch, package folder, the modules to read
├── licence: the repository's, where GitHub's licence interface and the text agree at the pinned commit
├── each module read at that commit by its git blob identity
├── each top-level function whose docstring holds examples (>>> lines)
│   ├── its closure: the top-level statements it and its examples use, transitively, copied line for line
│   │   in source order, across the package's own modules; standard library imports written as imports
│   ├── refused by name: no examples, a name nothing binds, a module outside the standard library and the
│   │   package, a closure above the bound, two modules binding one name differently
│   └── tests: the examples run as doctests with the network closed; then a known-wrong control, the same
│       function raising NotImplementedError under its own docstring, must fail them
└── package: <module>.py (the closure), test_<module>.py, README.md, LICENSE (Baltor's, for the generated
    lines), UPSTREAM-LICENSE (the library's), ATTRIBUTION.md
```

No line of the function or its closure is rewritten: each statement is copied
whole from the pinned file, and the only generated lines are the header, the
standard library imports the closure uses and the module's __all__.
"""
from __future__ import annotations

import ast
import builtins
import doctest
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .licences import repository_licence
from .openapi_operations import run_tests
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import RAW_HOST, github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, FUNCTION_EXTRACTS, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

SOURCES_FILE = Path(__file__).with_name("function_sources.json")
SOURCES_RECORD_TYPE = "library_supply_function_sources/v1"
GENERATOR_VERSION = "1.0.0"
NATIVE_FORMAT = "python_function"
HOSTS = (RAW_HOST,)
#: The most lines one extracted closure may hold; a larger one is not a function-level component.
MAXIMUM_CLOSURE_LINES = 400
#: The doctest options the examples run with: whitespace runs and ellipses as upstream test suites allow them.
DOCTEST_FLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
_BUILTINS = frozenset(dir(builtins)) | {"__name__", "__file__", "__doc__", "__all__", "__builtins__"}
_STANDARD_LIBRARY = frozenset(sys.stdlib_module_names)
NO_EXAMPLES, CLOSURE_UNRESOLVED, NEEDS_A_DEPENDENCY, CLOSURE_TOO_LARGE, CLOSURE_NAME_CONFLICT, EXAMPLES_FAILED, \
    EXAMPLES_DO_NOT_EXERCISE = (
        "no_examples", "closure_unresolved", "needs_a_dependency", "closure_too_large", "closure_name_conflict",
        "examples_failed", "examples_do_not_exercise_the_function")


class ExtractRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


def read_sources(path: Path = SOURCES_FILE) -> list:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    rows = []
    for row in record["sources"]:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", row["vendor"]) or not row.get("modules"):
            raise ValueError(f"{row.get('source_id')}: a vendor is a lower-case word and a source names modules")
        rows.append(row)
    return rows


# -- one module's top-level statements ----------------------------------------------------------------------------
@dataclass
class Statement:
    """One top-level statement of a module: its lines, the names it binds and the names it reads."""

    module: str
    index: int
    start: int  # first line (decorators included), 1-based
    end: int
    text: str
    binds: frozenset
    reads: frozenset
    imports: tuple = ()  # (bound name, module, attribute or None, level) of an import statement


def _names_read(node) -> set:
    """Names a statement reads (loads), leaving out names it binds inside itself (arguments and locals)."""
    loaded, stored = set(), set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            (loaded if isinstance(child.ctx, ast.Load) else stored).add(child.id)
        elif isinstance(child, ast.arg):
            stored.add(child.arg)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child is not node:
            stored.add(child.name)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            stored.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)) and child is not node:
            stored.update((alias.asname or alias.name).split(".")[0] for alias in child.names)
    top_binds = _names_bound(node)
    return (loaded - (stored - top_binds)) - top_binds if not isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else loaded - stored


def _names_bound(node) -> set:
    """Names a top-level statement binds in the module."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {(alias.asname or alias.name).split(".")[0] for alias in node.names if alias.name != "*"}
    bound = set()
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            for child in ast.walk(target):
                if isinstance(child, ast.Name):
                    bound.add(child.id)
    elif isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)) or type(node).__name__ == "TryStar":
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt) or isinstance(child, ast.ExceptHandler):
                for grandchild in ([child] if isinstance(child, ast.stmt) else child.body):
                    bound |= _names_bound(grandchild)
    return bound


def module_statements(module: str, source: str) -> list:
    """The top-level statements of one module, with the lines each spans (decorators included)."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    statements = []
    for index, node in enumerate(tree.body):
        start = min([node.lineno] + [decorator.lineno for decorator in getattr(node, "decorator_list", ())])
        text = "".join(lines[start - 1:node.end_lineno])
        imports = ()
        if isinstance(node, ast.Import):
            imports = tuple(((alias.asname or alias.name).split(".")[0], alias.name if alias.asname else
                             alias.name.split(".")[0], None, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports = tuple(((alias.asname or alias.name), node.module or "", alias.name, node.level)
                            for alias in node.names)
        statements.append(Statement(module, index, start, node.end_lineno, text, frozenset(_names_bound(node)),
                                    frozenset(_names_read(node)), imports))
    return statements


def docstring_examples(node) -> list:
    """The doctest examples of a function's docstring."""
    docstring = ast.get_docstring(node, clean=False) or ""
    return doctest.DocTestParser().get_examples(docstring) if ">>>" in docstring else []


def example_names(examples) -> set:
    """Names the examples read: each example's source parsed; an example that does not parse reads none."""
    names = set()
    for example in examples:
        try:
            tree = ast.parse(example.source)
        except SyntaxError:
            continue
        for child in ast.walk(tree):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                names.add(child.id)
    return names


# -- the closure ---------------------------------------------------------------------------------------------------
@dataclass
class Closure:
    statements: list = field(default_factory=list)  # Statement rows, in dependency order of modules
    imports: dict = field(default_factory=dict)  # bound name -> (module, attribute or None) of the standard library
    future: bool = False


def closure_of(target: str, module: str, modules: dict, package_root: str, extra_names=()) -> Closure:
    """The statements one function needs, across the package's modules. modules maps a module path to
    (statements, source); an import from the package itself is followed into the module it names, a standard
    library import is written as an import, and any other import refuses the function."""
    closure = Closure()
    included: dict = {}  # (module, index) -> Statement
    order: list = []  # modules in the order their statements were first needed
    bound_by: dict = {}  # name -> module that supplies it
    pending = [(module, name) for name in extra_names] + [(module, target)]
    while pending:
        current, name = pending.pop()
        if name in _BUILTINS:
            continue
        statements, source = modules[current]
        if "from __future__ import annotations" in source:
            closure.future = True
        binder = next((row for row in statements if name in row.binds), None)
        if binder is None:
            raise ExtractRefused(CLOSURE_UNRESOLVED, f"{name} in {current}")
        if bound_by.get(name, current) != current:
            raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{name} in {bound_by[name]} and {current}")
        bound_by[name] = current
        imported = next((row for row in binder.imports if row[0] == name), None) if _is_plain_import(binder) else None
        if imported is not None:
            _bound, imported_module, attribute, level = imported
            if level or _within(imported_module, package_root):
                target_module = _resolve(current, imported_module, level, package_root, modules)
                if target_module is None or attribute is None:
                    raise ExtractRefused(NEEDS_A_DEPENDENCY, f"{'.' * level}{imported_module or ''} from {current}")
                if attribute != name:
                    raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{attribute} imported as {name}")
                del bound_by[name]  # the name is supplied by the module it is imported from
                pending.append((target_module, attribute))
                continue
            if (imported_module or "").split(".")[0] not in _STANDARD_LIBRARY:
                raise ExtractRefused(NEEDS_A_DEPENDENCY, imported_module or "")
            closure.imports[name] = (imported_module, attribute)
            continue
        key = (current, binder.index)
        if key in included:
            continue
        included[key] = binder
        if current not in order:
            order.append(current)
        for read in sorted(binder.reads, reverse=True):
            pending.append((current, read))
    by_module = {}
    for (current, _index), statement in included.items():
        by_module.setdefault(current, []).append(statement)
    # A module reached later is one an earlier module imports from: its statements come first. Within a module
    # the statements keep their source order.
    for current in reversed(order):
        closure.statements += sorted(by_module.get(current, []), key=lambda row: row.index)
    size = sum(row.end - row.start + 1 for row in closure.statements)
    if size > MAXIMUM_CLOSURE_LINES:
        raise ExtractRefused(CLOSURE_TOO_LARGE, f"{size} lines")
    return closure


def _is_plain_import(statement: Statement) -> bool:
    return bool(statement.imports)


def _within(module_name: str, package_root: str) -> bool:
    return bool(module_name) and (module_name == package_root or module_name.startswith(package_root + "."))


def _package_folder(modules: dict, package_root: str) -> "Path | None":
    """The folder of the read modules that is the package the root names (more_itertools, src/pydash)."""
    suffix = Path(*package_root.split("."))
    for path in modules:
        for folder in Path(path).parents:
            if folder.parts[-len(suffix.parts):] == suffix.parts:
                return folder
    return None


def _resolve(current: str, imported: str, level: int, package_root: str, modules: dict) -> "str | None":
    """The module path (as in modules) an import from the package names, or None when it is not a read module."""
    parts = [part for part in (imported or "").split(".") if part]
    if level:
        base = Path(current).parent
        for _step in range(level - 1):
            base = base.parent
    else:
        base = _package_folder(modules, package_root)
        if base is None:
            return None
        parts = parts[len(package_root.split(".")):]
    candidate = base.joinpath(*parts) if parts else base
    for option in (f"{candidate}.py", f"{candidate}/__init__.py"):
        if option in modules:
            return option
    return None


# -- the package ---------------------------------------------------------------------------------------------------
def module_text(closure: Closure, target: str, header: str) -> str:
    lines = [header]
    if closure.future:
        lines.append("from __future__ import annotations\n")
    imports = []
    for name, (module, attribute) in sorted(closure.imports.items()):
        if attribute is None:
            imports.append(f"import {module}" if name == module.split(".")[0] else f"import {module} as {name}")
        else:
            imports.append(f"from {module} import {attribute}" + ("" if attribute == name else f" as {name}"))
    if imports:
        lines.append("\n".join(imports) + "\n")
    for statement in closure.statements:
        lines.append("\n" + statement.text.rstrip("\n") + "\n")
    lines.append(f"\n__all__ = [{target!r}]\n")
    return "\n".join(line.rstrip("\n") for line in lines) + "\n"


def mutant_text(text: str, target: str, docstring: str) -> str:
    """The module with the function replaced by one that raises under the same docstring: its examples must
    fail, or they do not exercise the function."""
    return text + (f"\n\ndef {target}(*args, **kwargs):\n    {docstring!r}\n"
                   "    raise NotImplementedError('known-wrong control')\n")


def test_text(module: str) -> str:
    return (f'"""The examples of {module}\'s docstrings, run as doctests with the network closed."""\n'
            "import doctest\nimport os\nimport sys\nimport unittest\n\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            f"import {module}  # noqa: E402\n\n\n"
            "def load_tests(loader, tests, ignore):\n"
            f"    tests.addTests(doctest.DocTestSuite({module}, optionflags={int(DOCTEST_FLAGS)}))\n"
            "    return tests\n\n\n"
            'if __name__ == "__main__":\n    unittest.main()\n')


def generate(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: "dict | None" = None) -> tuple:
    """(built, refusals, facts, summary): every documented function of every declared library, tested."""
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/function_extracts.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    for source in sources:
        repository = source["repository"]
        pinned = {}
        for path in source["modules"]:
            try:
                pinned[path] = reader.pinned_file(repository, source["branch"], path)
            except LookupError as error:
                refused.append(refusal(FUNCTION_EXTRACTS, "source_unreadable", f"{repository} {path}", str(error)))
        if not pinned:
            continue
        commit = next(iter(pinned.values()))["commit"]
        licence = repository_licence(reader, repository, commit)
        if not licence.allowed:
            refused.append(refusal(FUNCTION_EXTRACTS, licence.refusal_reason(
                ("licence_not_on_allowlist", "licence_signals_disagree", "licence_unknown")), repository,
                str(licence.github_spdx)))
            continue
        modules = {}
        for path, found in pinned.items():
            facts[found["sha256"]] = found["bytes"]
            text = found["bytes"].decode("utf-8")
            try:
                modules[path] = (module_statements(path, text), text)
            except SyntaxError as error:
                refused.append(refusal(FUNCTION_EXTRACTS, "source_unreadable", path, str(error)[:120]))
        taken, seen = 0, set()
        for path in source["modules"]:
            if path not in modules:
                continue
            tree = ast.parse(modules[path][1])
            for node in tree.body:
                if taken >= source.get("maximum_functions", 1000):
                    break
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("_"):
                    continue
                label = f"{repository} {path} {node.name}"
                if node.name in seen:
                    refused.append(refusal(FUNCTION_EXTRACTS, "duplicate_function", label))
                    continue
                try:
                    payload = _package(node, path, modules, source, pinned, licence, commit, generator, licence_text,
                                       generated_on, staging, repository_facts or {})
                except ExtractRefused as error:
                    refused.append(refusal(FUNCTION_EXTRACTS, error.reason, label, error.detail))
                    continue
                except SupplyRecordError as error:
                    reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                        GENERATED_TEST_FAILED
                    refused.append(refusal(FUNCTION_EXTRACTS, reason, label, str(error)))
                    continue
                seen.add(node.name)
                built.append(payload)
                taken += 1
        summary.append({"source_id": source["source_id"], "repository": repository, "commit": commit,
                        "licence": licence.spdx, "modules": len(modules), "packaged": taken})
    return built, refused, facts, summary


def _package(node, path, modules, source, pinned, licence, commit, generator, licence_text, generated_on, staging,
             repository_facts):
    examples = docstring_examples(node)
    if not examples:
        raise ExtractRefused(NO_EXAMPLES)
    closure = closure_of(node.name, path, modules, source["package_root"],
                         extra_names=sorted(example_names(examples) - {node.name}))
    module = f"{source['vendor']}_{node.name}"[:80].lower()
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", module):
        raise ExtractRefused(CLOSURE_UNRESOLVED, f"no module name for {node.name}")
    paths = sorted({statement.module for statement in closure.statements})
    header = (f"# {node.name}, extracted by Baltor from {source['repository']} at commit {commit}\n"
              f"# ({', '.join(paths)}). Every statement below the imports is copied whole from those files;\n"
              f"# licence {licence.spdx}, see UPSTREAM-LICENSE and ATTRIBUTION.md.\n")
    text = module_text(closure, node.name, header)
    tests = test_text(module)
    folder = staging / module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{module}.py").write_text(text, encoding="utf-8")
    (folder / f"test_{module}.py").write_text(tests, encoding="utf-8")
    passed, count, output = run_tests(folder, module)
    if not passed:
        raise ExtractRefused(EXAMPLES_FAILED, output[-300:])
    docstring = ast.get_docstring(node, clean=False) or ""
    (folder / f"{module}.py").write_text(mutant_text(text, node.name, docstring), encoding="utf-8")
    mutant_passed, _count, _output = run_tests(folder, module)
    for leftover in folder.iterdir():
        leftover.unlink()
    folder.rmdir()
    if mutant_passed:
        raise ExtractRefused(EXAMPLES_DO_NOT_EXERCISE, node.name)
    signature = ast.get_source_segment(modules[path][1], node).split("\n", 1)[0].strip()
    summary = (ast.get_docstring(node) or "").strip().split("\n\n", 1)[0].replace("\n", " ")[:300]
    segments = [[statement.module, statement.start, statement.end] for statement in closure.statements]
    readme = (f"# {node.name}\n\n`{signature}`\n\n{summary}\n\n"
              f"From {source['title']} ({source['repository']}), commit `{commit}`, licensed {licence.spdx}.\n"
              f"`{module}.py` holds the function and exactly the code it needs, each statement copied whole:\n\n"
              + "".join(f"- `{segment[0]}` lines {segment[1]} to {segment[2]}\n" for segment in segments)
              + ("\nStandard library imports the code uses are written at the top.\n" if closure.imports else "")
              + f"\n`test_{module}.py` runs the {len(examples)} examples of the docstrings as doctests, offline "
              f"({count} test run{'s' if count != 1 else ''}). The same function raising NotImplementedError under "
              "its own docstring fails them, so the examples exercise it.\n")
    upstream_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(f"{module}.py", text.encode("utf-8"), "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode("utf-8"), "executable_tool"),
             PackageFile("README.md", readme.encode("utf-8"), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": upstream_address, "sha256": licence.sha256})]
    facts = [fact_source(https_address(RAW_HOST, f"{source['repository']}/{commit}/{segment_path}"),
                         pinned[segment_path]["retrieved_at"], pinned[segment_path]["sha256"],
                         len(pinned[segment_path]["bytes"]), "data_source", spdx=licence.spdx,
                         basis="github_licence_interface_and_text_agree", evidence_sha256=licence.sha256)
             for segment_path in paths]
    facts.append(fact_source(upstream_address, pinned[path]["retrieved_at"], licence.sha256, len(licence.text),
                             "licence_text", spdx=licence.spdx, basis="licence_file_at_the_pinned_commit"))
    expression = " AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx]))
    name = f"{source['vendor']}-{node.name.replace('_', '-')}"[:90]
    identity = f"{source['repository']}:{path}:{node.name}"
    stars = ((repository_facts.get(source["repository"].lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=FUNCTION_EXTRACTS, identity=identity, key=upstream_key(FUNCTION_EXTRACTS, identity), kind="code_module",
        native_format=NATIVE_FORMAT, form="function", name=name,
        description=f"{node.name} from {source['title']}: {summary[:200]} One tested Python function, copied with "
                    "the code it needs.",
        files=files, licence_expression=expression,
        provenance=provenance("github_repository", source["repository"], path, commit, facts, generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False,
               "known_wrong_control": "the function raising NotImplementedError under its own docstring fails"},
        repository={"name": source["repository"], "stars": stars, "module": path, "function": node.name,
                    "segments": segments},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


__all__ = ["Closure", "ExtractRefused", "closure_of", "docstring_examples", "generate", "module_statements",
           "module_text", "mutant_text", "read_sources", "test_text"]

"""Line function_extracts: one tested function per documented function of a well-tested, permissively licensed
Python library, copied with exactly the code it needs.

```text
function_sources.json: repository, branch, package folder, the modules to read
├── withheld: a declared source not read, with the measured reason (refused as source_withheld)
├── licence: the repository's, where GitHub's licence interface and the text agree at the pinned commit
├── each module read at that commit by its git blob identity
├── each top-level function whose docstring holds examples (>>> lines)
│   ├── its closure: the top-level statements it and its examples use, transitively, copied line for line
│   │   in source order, across the package's own modules; standard library imports written as imports;
│   │   names only annotations read are bound too (a definition copied, a TYPE_CHECKING block copied whole,
│   │   a typing_extensions name that typing provides imported from typing)
│   ├── refused by name: not a reusable job (test or test_*, a main without parameters), no description,
│   │   no examples, a name nothing binds, a module outside the standard library and the package, a closure
│   │   above the bound, two modules binding one name differently, a copied module whose own text states a
│   │   licence other than the repository's
│   ├── effects: read from the syntax tree of the copied code and of every docstring example the tests run
│   │   (files opened, written or listed, processes started, network modules), never from its words
│   └── tests: the examples run as doctests in the qualification sandbox; then a known-wrong control, the same
│       function raising NotImplementedError under its own docstring, must fail them
└── package: <module>.py (the closure), test_<module>.py, README.md (the whole signature, the docstring's own
    description, the other definitions the module holds, the examples its tests run), LICENSE (Baltor's, for
    the generated lines), UPSTREAM-LICENSE (the library's), ATTRIBUTION.md
```

No line of the function or its closure is rewritten: each statement is copied
whole from the pinned file, and the only generated lines are the header, the
imports the closure uses and the module's __all__.

Version 1.2.0 repairs what the sampled review of September 30, 2026 found in
1.1.0 (21 of 58 sampled packages defective; the classification is in
tools/supply_lines/README.md): effects read from words, README signatures cut
at their first line and summaries that ran into the examples or stopped inside
a number, names only annotations read left unbound, a module's own tests
packaged as jobs, functions whose docstrings say nothing in words, and a file
under another licence (NLTK's copy of the BSD decorator module) labelled with
the repository's licence.
"""
from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import io
import shutil
import doctest
import json
import re
import sys
import tokenize
import typing
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from component_qualification.components import GeneratedComponent
from component_qualification.sandbox import SandboxSettings, run_component
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile

from .licences import repository_licence
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build, notice_files
from .reading import RAW_HOST, github_blob_address, https_address, pinned_files, repository_notice
from .records import (
    BLOCKED_BY_STATIC_CHECK, FUNCTION_EXTRACTS, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

SOURCES_FILE = Path(__file__).with_name("function_sources.json")
SOURCES_RECORD_TYPE = "library_supply_function_sources/v1"
GENERATOR_VERSION = "1.3.0"
NATIVE_FORMAT = "python_function"
HOSTS = (RAW_HOST,)
#: The most lines one extracted closure may hold; a larger one is not a function-level component.
MAXIMUM_CLOSURE_LINES = 400
#: The name the generated namespace of a package import is built with (import types as ...).
NAMESPACE_MODULE = "_namespace_types"
#: The doctest options the examples run with: whitespace runs and ellipses as upstream test suites allow them.
DOCTEST_FLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
_BUILTINS = frozenset(dir(builtins)) | {"__name__", "__file__", "__doc__", "__all__", "__builtins__"}
_STANDARD_LIBRARY = frozenset(sys.stdlib_module_names)
#: The backport of typing's newer names. A name only annotations read is imported from typing when typing provides
#: it: under `from __future__ import annotations` an annotation is never evaluated, so the backport's own version
#: of the name never runs (pydash imports TypeGuard from it for 99 of the 226 packages 1.1.0 wrote from it).
BACKPORT_MODULE = "typing_extensions"
NO_EXAMPLES, CLOSURE_UNRESOLVED, NEEDS_A_DEPENDENCY, CLOSURE_TOO_LARGE, CLOSURE_NAME_CONFLICT, EXAMPLES_FAILED, \
    EXAMPLES_DO_NOT_EXERCISE = (
        "no_examples", "closure_unresolved", "needs_a_dependency", "closure_too_large", "closure_name_conflict",
        "examples_failed", "examples_do_not_exercise_the_function")
#: Refusals 1.2.0 adds, each measured on the 3,067 packages 1.1.0 wrote from the cached sources of the September 28
#: and October 1, 2026 runs (re-read offline on October 5; 1.2.0 writes 2,795 of them):
#: - not_a_reusable_job: a function named test or test_* is its module's own test, and a main that takes no
#:   parameters is its module's demonstration. 1.1.0 packaged 7 tests and 4 such mains, all from TheAlgorithms, all
#:   read by hand: each asserts or prints a fixed example. A main with parameters runs its module's algorithm
#:   (the travelling salesman and ant colony mains) and stays.
#: - no_description: the docstring says nothing in words before its examples, sections and fields, and gives no
#:   returns text either, so neither the README nor the catalogue card can say what the job is. 232 of 1.1.0's
#:   packages (229 from TheAlgorithms; the other 3 read by hand: examples only).
#: - module_licence_differs: a module the closure copies states a licence that names no family of the repository's
#:   licence, so the repository's licence does not decide those bytes. 11 of the 2,400 modules read from the cached
#:   sources: 8 files copied from other projects (NLTK's decorators.py, BSD; lazyimport.py, eGenix;
#:   tag/perceptron.py, Matthew Honnibal's MIT; pyrsistent's _toolz.py, BSD; fluids' optional irradiance.py, spa.py
#:   and pychebfun.py, BSD-3-Clause; rdflib's notation3.py, W3C), fluids/core.py's note on its twelve SciPy
#:   temperature conversions (BSD-3-Clause, the twelve alone), and 2 NLTK corpus readers that state their data's
#:   licence, refused with them because their words do not say which bytes they cover. 17 of 1.1.0's packages copied
#:   code from these files under the repository's licence: the 12 conversions, 3 rdflib and 2 NLTK functions.
NOT_A_REUSABLE_JOB, NO_DESCRIPTION, MODULE_LICENCE_DIFFERS = (
    "not_a_reusable_job", "no_description", "module_licence_differs")
#: A declared source whose row says withheld (the measured reason): nothing of it is read or packaged.
SOURCE_WITHHELD = "source_withheld"


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
        if "withheld" in row and not (isinstance(row["withheld"], str) and row["withheld"].strip()):
            raise ValueError(f"{row.get('source_id')}: withheld is the measured reason a source is not read")
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
    #: Names the examples of a definition's docstring read and do not bind themselves.
    example_reads: frozenset = frozenset()
    #: (name, attribute) of every attribute read on a plain name (pyd.camel_case), for a package namespace.
    attributes: frozenset = frozenset()
    #: (module, level) of every import inside the statement or its docstring examples (a function that imports
    #: numpy when it runs needs numpy as much as one that imports it at the top).
    inner_imports: frozenset = frozenset()
    #: Names only the statement's annotations read, when `from __future__ import annotations` or quotes keep them
    #: from being evaluated: the written module still binds them, so a reader, a type checker and
    #: typing.get_type_hints find every name it shows.
    annotation_reads: frozenset = frozenset()
    #: An `if TYPE_CHECKING:` block without an else: its imports run only under a type checker.
    type_checking: bool = False


def _is_type_checking_block(node) -> bool:
    test = node.test if isinstance(node, ast.If) and not node.orelse else None
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _annotations(node) -> list:
    """Every annotation of a statement: of arguments, of returns and of annotated assignments."""
    found = []
    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(child.returns)
        elif isinstance(child, ast.arg):
            found.append(child.annotation)
        elif isinstance(child, ast.AnnAssign):
            found.append(child.annotation)
    return [annotation for annotation in found if annotation is not None]


def _annotation_nodes(node) -> set:
    """The ids of every node inside an annotation of a statement (arguments, returns, annotated assignments)."""
    return {id(grandchild) for annotation in _annotations(node) for grandchild in ast.walk(annotation)}


def _quoted_annotation_names(node) -> set:
    """Names inside annotations written as strings ("SupportsDunderGT[T]"), which Python never evaluates on its
    own, less the names the statement binds itself (its arguments, locals and nested definitions)."""
    names = set()
    for annotation in _annotations(node):
        for item in ast.walk(annotation):
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                try:
                    names |= {name.id for name in ast.walk(ast.parse(item.value.strip(), mode="eval"))
                              if isinstance(name, ast.Name)}
                except SyntaxError:
                    continue
    local = {child.id for child in ast.walk(node)
             if isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Load)}
    local |= {child.arg for child in ast.walk(node) if isinstance(child, ast.arg)}
    local |= {child.name for child in ast.walk(node) if isinstance(
        child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child is not node}
    return names - local


def _names_read(node, lazy_annotations: bool = False) -> set:
    """Names a statement reads (loads), leaving out names it binds inside itself (arguments and locals). With
    `from __future__ import annotations` an annotation is never evaluated, so the names only annotations read are
    left out."""
    skipped = _annotation_nodes(node) if lazy_annotations else set()
    loaded, stored = set(), set()
    for child in ast.walk(node):
        if id(child) in skipped:
            continue
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


def _inner_imports(node) -> set:
    """(module, level) of every import statement inside a statement and in its docstring examples."""
    found = set()
    trees = [node]
    for example in docstring_examples(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                  ast.ClassDef)) else ():
        try:
            trees.append(ast.parse(example.source))
        except SyntaxError:
            continue
    for tree in trees:
        for child in ast.walk(tree):
            if child is node:
                continue
            if isinstance(child, ast.Import):
                found.update((alias.name, 0) for alias in child.names)
            elif isinstance(child, ast.ImportFrom):
                found.add((child.module or "", child.level))
    return found


def _attributes(node) -> set:
    return {(child.value.id, child.attr) for child in ast.walk(node)
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name)}


def _example_reads(node) -> frozenset:
    """Names the docstring examples of a definition read, less the names the examples bind themselves."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return frozenset()
    loaded, stored = set(), set()
    for example in docstring_examples(node):
        try:
            tree = ast.parse(example.source)
        except SyntaxError:
            continue
        for child in ast.walk(tree):
            if isinstance(child, ast.Name):
                (loaded if isinstance(child.ctx, ast.Load) else stored).add(child.id)
            elif isinstance(child, ast.arg):
                stored.add(child.arg)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stored.add(child.name)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                stored.update((alias.asname or alias.name).split(".")[0] for alias in child.names)
    return frozenset(loaded - stored)


def module_statements(module: str, source: str) -> list:
    """The top-level statements of one module, with the lines each spans (decorators included)."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    lazy = any(isinstance(node, ast.ImportFrom) and node.module == "__future__" and
               any(alias.name == "annotations" for alias in node.names) for node in tree.body)
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
        reads = frozenset(_names_read(node, lazy))
        annotation_only = (set(_names_read(node)) - reads if lazy else set()) | _quoted_annotation_names(node)
        statements.append(Statement(module, index, start, node.end_lineno, text, frozenset(_names_bound(node)),
                                    reads, imports, _example_reads(node), frozenset(_attributes(node)),
                                    frozenset(_inner_imports(node)), frozenset(annotation_only - reads),
                                    _is_type_checking_block(node)))
    return statements


def docstring_examples(node) -> list:
    """The doctest examples of a function's docstring."""
    docstring = ast.get_docstring(node, clean=False) or ""
    return doctest.DocTestParser().get_examples(docstring) if ">>>" in docstring else []


def example_names(node) -> set:
    """Names the docstring examples of a definition read and do not bind themselves."""
    return set(_example_reads(node))


# -- the closure ---------------------------------------------------------------------------------------------------
@dataclass
class Closure:
    statements: list = field(default_factory=list)  # Statement rows, in dependency order of modules
    imports: dict = field(default_factory=dict)  # bound name -> (module, attribute or None) of the standard library
    future: bool = False
    #: A name bound to the package itself (import pydash as pyd) -> the attributes the copied code reads on it,
    #: written as a namespace of the copied definitions.
    namespaces: dict = field(default_factory=dict)
    #: A name an import from the package binds under another name (_ for _gettext) -> the definition's name.
    aliases: dict = field(default_factory=dict)
    #: A name only annotations read that the upstream imports from typing_extensions -> the name typing provides.
    backports: dict = field(default_factory=dict)


def closure_of(target: str, module: str, modules: dict, package_root: str, extra_names=()) -> Closure:
    """The statements one function needs, across the package's modules. modules maps a module path to
    (statements, source). A definition brings the names it reads and the names its docstring examples read; an
    import from the package itself is followed into the module it names (a name bound to the whole package
    becomes a namespace of the attributes the copied code reads on it); a standard library import is written as
    an import; any other import refuses the function.

    A name only annotations read is bound the same way, so the written module shows no name it does not bind
    (1.1.0 left them out: pydash packages showed `t.Any` and `TypeGuard`, and typing.get_type_hints raised
    NameError). Two differences, because such an annotation is never evaluated: an `if TYPE_CHECKING:` block is
    copied whole without its imports being followed, and a typing_extensions name typing provides is imported
    from typing."""
    closure = Closure()
    included: dict = {}  # (module, index) -> Statement
    order: list = []  # modules in the order their statements were first needed
    defined_in: dict = {}  # name -> module whose definition supplies it
    # (module, name, read only by annotations)
    pending = [(module, name, False) for name in sorted(extra_names, reverse=True)] + [(module, target, False)]
    seen = set()
    while pending:
        current, name, annotation = pending.pop()
        if name in _BUILTINS or (current, name, annotation) in seen or (current, name, False) in seen:
            continue
        seen.add((current, name, annotation))
        statements, source = modules[current]
        if "from __future__ import annotations" in source:
            closure.future = True
        binders = [row for row in statements if name in row.binds]
        if not binders:
            raise ExtractRefused(CLOSURE_UNRESOLVED, f"{name} in {current}")
        definitions = [row for row in binders if not row.imports]
        if definitions:
            if defined_in.get(name, current) != current:
                # Two modules may define a name the same way (T = t.TypeVar("T")): one copy serves both.
                earlier = [row.text for row in modules[defined_in[name]][0] if name in row.binds and not row.imports]
                if [row.text for row in definitions] == earlier:
                    continue
                raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{name} in {defined_in[name]} and {current}")
            defined_in[name] = current
            # Every statement binding the name, in source order: overload stubs and then the definition used.
            for binder in definitions:
                key = (current, binder.index)
                if key in included:
                    continue
                for imported_name, level in sorted(() if binder.type_checking else binder.inner_imports):
                    top = imported_name.split(".")[0]
                    if not level and top not in _STANDARD_LIBRARY and not _within(imported_name, package_root):
                        raise ExtractRefused(NEEDS_A_DEPENDENCY, f"{imported_name} inside {name}")
                included[key] = binder
                if current not in order:
                    order.append(current)
                for read in sorted(binder.reads | binder.example_reads, reverse=True):
                    pending.append((current, read, False))
                for read in sorted(binder.annotation_reads, reverse=True):
                    pending.append((current, read, True))
                for alias, attribute in sorted(binder.attributes):
                    if closure.namespaces.get(alias) is not None:
                        pending.append((closure.namespaces[alias][0], attribute, False))
                        closure.namespaces[alias][1].add(attribute)
            continue
        imported = next(row for row in binders[0].imports if row[0] == name)
        _bound, imported_module, attribute, level = imported
        if level or _within(imported_module, package_root):
            target_module = _resolve(current, imported_module, level, package_root, modules)
            if target_module is None:
                raise ExtractRefused(NEEDS_A_DEPENDENCY, f"{'.' * level}{imported_module or ''} from {current}")
            if attribute is None:
                # The whole package under a name: the copied code reads attributes on it.
                known = closure.namespaces.setdefault(name, (target_module, set()))
                if known[0] != target_module:
                    raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{name} names two modules")
                for statement in list(included.values()):
                    for alias, read in statement.attributes:
                        if alias == name and read not in known[1]:
                            known[1].add(read)
                            pending.append((target_module, read, False))
                continue
            if attribute != name:
                # from .i18n import _gettext as _: the definition is copied under its own name and the alias
                # is written after it (generated).
                if closure.aliases.get(name, attribute) != attribute:
                    raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{name} names two definitions")
                closure.aliases[name] = attribute
            pending.append((target_module, attribute, annotation))
            continue
        if (imported_module or "").split(".")[0] not in _STANDARD_LIBRARY:
            if not (annotation and imported_module == BACKPORT_MODULE and attribute
                    and hasattr(typing, attribute)):
                raise ExtractRefused(NEEDS_A_DEPENDENCY, imported_module or "")
            closure.backports[name] = attribute
            imported_module = "typing"
        if closure.imports.get(name, (imported_module, attribute)) != (imported_module, attribute):
            raise ExtractRefused(CLOSURE_NAME_CONFLICT, f"{name} imported from two places")
        closure.imports[name] = (imported_module, attribute)
    # A namespace attribute that is itself a name the closure imports from the package resolves to its definition;
    # every attribute must end as a copied definition.
    for alias, (_module, attributes) in closure.namespaces.items():
        for attribute in attributes:
            if attribute not in defined_in and attribute not in closure.imports:
                raise ExtractRefused(CLOSURE_UNRESOLVED, f"{alias}.{attribute}")
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


# -- what the package says about the function ------------------------------------------------------------------------
#: A docstring line that ends its description: an example, a field (:param, @return), a directive (.. note::), a
#: section header (Args:, Returns, Examples, Input Parameters:) or a section's underline.
_DESCRIPTION_STOP = re.compile(
    r"^\s*(?:>>>|:\w|@\w|\.\. |[-=~^*]{3,}\s*$|(?:args|arguments|parameters|params|param|input parameters|"
    r"inputs?|keyword arguments|other parameters|returns?|return value|yields?|raises?|examples?|example usage|"
    r"usage|doctests?|tests?|notes?|see also|references?|attributes|warnings?|todo)\s*:?\s*$)", re.I)
_RETURNS_FIELD = re.compile(r"^\s*(?::returns?:|@returns?:?)\s*(\S.*)$", re.I)
_RETURNS_SECTION = re.compile(r"^\s*returns?\s*:?\s*$", re.I)
#: The longest description a README shows, and the longest the candidate record's description holds.
README_DESCRIPTION_CHARACTERS, RECORD_DESCRIPTION_CHARACTERS = 300, 200


def _has_words(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]{2,}", re.sub(r"https?://\S+", "", text)))


def description_of(docstring: str) -> str:
    """What a docstring says in words: the first paragraph before its examples, fields and sections, or else the
    text its returns field or section gives; empty when it has neither. 1.1.0 took the docstring's first
    paragraph whole, which ran into the examples when no blank line came first and was cut at 300 characters
    inside a number (find_median's README showed 2.6 for 2.65)."""
    lines = []
    for line in docstring.expandtabs().splitlines():
        if _DESCRIPTION_STOP.match(line):
            break
        if not line.strip() and lines:
            break
        if line.strip():
            lines.append(line.strip())
    text = " ".join(" ".join(lines).split())
    if _has_words(text):
        return text
    rows = docstring.expandtabs().splitlines()
    for index, line in enumerate(rows):
        field_text = _RETURNS_FIELD.match(line)
        if field_text and _has_words(field_text.group(1)):
            return "Returns: " + " ".join(field_text.group(1).split())
        if _RETURNS_SECTION.match(line):
            # The section's first line of text; an example or another section right after it says nothing.
            following = next((row.strip() for row in rows[index + 1:] if row.strip()
                              and not re.match(r"^\s*[-=~^*]{3,}\s*$", row)), "")
            if _has_words(following) and not _DESCRIPTION_STOP.match(following):
                return "Returns: " + following
    return ""


def shortened(text: str, limit: int) -> str:
    """text, or its first whole sentences within limit characters, or its first words and an ellipsis; never a
    cut inside a word or a number (a text with no space before the limit stays whole)."""
    if len(text) <= limit:
        return text
    kept = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if len(kept) + len(sentence) + 1 > limit:
            break
        kept = f"{kept} {sentence}".strip()
    if kept:
        return kept
    if " " not in text[:limit - 1]:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def signature_text(node) -> str:
    """The function's whole signature on one line as Python writes it, without decorators or comments (1.1.0
    showed the first source line, `def find_unit_clauses(`, for 301 of its 3,067 packages)."""
    header = copy.copy(node)
    header.body, header.decorator_list = [ast.Pass()], []
    return ast.unparse(header).split("\n", 1)[0]


def example_count(text: str) -> int:
    """How many docstring examples a module's doctests run: those of its functions and classes and of the methods
    of its classes, as doctest finds them (not those of functions nested in functions)."""
    count, pending = 0, list(ast.parse(text).body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            count += len(docstring_examples(node))
            if isinstance(node, ast.ClassDef):
                pending += node.body
    return count


def not_a_reusable_job(node) -> str:
    """Why a function is not a job of its own: its module's test (test, test_*) or its module's demonstration (a
    main that takes no parameters); empty otherwise."""
    if node.name == "test" or node.name.startswith("test_"):
        return f"{node.name} is a test of its module"
    arguments = node.args
    if node.name == "main" and not (arguments.posonlyargs or arguments.args or arguments.kwonlyargs
                                    or arguments.vararg or arguments.kwarg):
        return "main without parameters demonstrates its module"
    return ""


#: Words that state a file's own licence: a grant, an SPDX identifier, a licence field, or the opening words of
#: the MIT and BSD texts.
_LICENCE_STATEMENT = re.compile(r"licen[sc]ed\s+under|distributed\s+under|under\s+the\s+terms\s+of|"
                                r"SPDX-License-Identifier|^\W*licen[sc]e\s*:|permission\s+is\s+hereby\s+granted|"
                                r"redistribution\s+and\s+use\s+in\s+source", re.I | re.M)
#: The licence family of each allowlisted identifier, and the words that name each family.
_LICENCE_FAMILY = {"MIT": "MIT", "Apache-2.0": "Apache", "BSD-2-Clause": "BSD", "BSD-3-Clause": "BSD", "0BSD": "BSD",
                   "ISC": "ISC", "CC0-1.0": "CC0", "CC-BY-4.0": "CC-BY", "Unlicense": "Unlicense"}
_FAMILY_WORDS = (("Apache", r"\bApache\b"), ("MIT", r"\bMIT\b|permission\s+is\s+hereby\s+granted"),
                 ("BSD", r"\bBSD\b|redistribution\s+and\s+use\s+in\s+source"), ("ISC", r"\bISC\b"),
                 ("CC0", r"\bCC0\b|public\s+domain"), ("CC-BY", r"Creative\s+Commons\s+Attribution|\bCC[- ]BY\b"),
                 ("Unlicense", r"\bUnlicense\b"))
#: Words that name a licence outside those families (babel's catalog template, "distributed under the same license
#: as the PROJECT project", names none and states nothing).
_OTHER_LICENCE_WORDS = re.compile(r"\b(?:GNU|A?GPL|LGPL|MPL|Mozilla|Eclipse|EPL|Artistic|PSF|Python\s+Software\s+"
                                  r"Foundation|Zope|ZPL|W3C|eGenix|CDDL|EUPL|OFL|WTFPL|Boost|zlib)\b|"
                                  r"\w+\s+(?:Public|Software)\s+Licen[cs]e", re.I)


def _text_blocks(text: str) -> list:
    """(first line, text) of a module's string literals (its docstrings among them) and of its runs of comment
    lines: where a file states a licence, and never its code (a `license: str` field is not a statement)."""
    blocks = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.STRING:
                blocks.append([token.start[0], token.end[0], token.string])
            elif token.type == tokenize.COMMENT:
                if blocks and blocks[-1][2].startswith("#") and blocks[-1][1] == token.start[0] - 1:
                    blocks[-1][1:] = [token.start[0], blocks[-1][2] + "\n" + token.string]
                else:
                    blocks.append([token.start[0], token.start[0], token.string])
    except (tokenize.TokenError, SyntaxError):
        return [(1, text)]
    return [(first, block) for first, _last, block in blocks]


def foreign_licences(text: str, spdx: str) -> list:
    """(names, excerpt) of each licence statement in a module's comments and strings whose words name no family
    of the repository's licence: a file copied from another project keeps its own ("distributed under the terms
    of the BSD License" in NLTK's decorators.py). A statement in the module's header (its docstring and the
    comments before its first statement) covers the whole module (names None); a later one covers the module's
    definitions it names, or the whole module when it names none: fluids/core.py's note that its twelve
    temperature conversions came from SciPy under the BSD 3-Clause licence covers those twelve, not Reynolds."""
    family = _LICENCE_FAMILY.get(spdx, spdx)
    tree = ast.parse(text)
    body = tree.body[1:] if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(
        tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str) else tree.body
    header_end = min([body[0].lineno] + [row.lineno for row in getattr(body[0], "decorator_list", ())]) \
        if body else float("inf")
    defined = {name for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))
               for name in _names_bound(node)}
    found = []
    for first, block in _text_blocks(text):
        for match in _LICENCE_STATEMENT.finditer(block):
            window = block[max(0, match.start() - 200):match.end() + 300]
            named = {name for name, pattern in _FAMILY_WORDS if re.search(pattern, window, re.I)}
            if not re.search(r"licen[cs]|copyright", window, re.I) or family in named or not (
                    named or _OTHER_LICENCE_WORDS.search(window)):
                continue
            names = None if first < header_end else (frozenset(re.findall(r"[A-Za-z_]\w*", block)) & defined
                                                     or None)
            found.append((names, " ".join(block[match.start():match.end() + 120].split())[:140]))
            break
    return found


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
    if closure.namespaces:
        imports.append(f"import types as {NAMESPACE_MODULE}")
    if imports:
        lines.append("\n".join(sorted(imports)) + "\n")
    for statement in closure.statements:
        lines.append("\n" + statement.text.rstrip("\n") + "\n")
    for alias, original in sorted(closure.aliases.items()):
        lines.append(f"\n{alias} = {original}\n")
    for alias, (_module, attributes) in sorted(closure.namespaces.items()):
        # The package itself, as far as the copied code reads it (generated).
        members = ", ".join(f"{attribute}={attribute}" for attribute in sorted(attributes))
        lines.append(f"\n{alias} = {NAMESPACE_MODULE}.SimpleNamespace({members})\n")
    lines.append(f"\n__all__ = [{target!r}]\n")
    return "\n".join(line.rstrip("\n") for line in lines) + "\n"


# -- effects, from the syntax tree ---------------------------------------------------------------------------------
# 1.1.0 read the module's words with the licensed import's rules for instruction files, which take "x > 0" for a
# shell redirect and "find the" for a file read: 868 of the 3,067 packages it wrote from the cached sources declared
# a file effect, and none of those packages holds a file call (measured October 5, 2026; the September 30 review
# rejected five packages for effects they declared and do not have). The qualification's effects check reads the
# syntax tree too and refuses an effect the code shows and the record does not declare; this reading is the
# generator's own, and it also reads the docstring examples, which the tests run.
_PROCESS_MODULES = frozenset({"subprocess", "multiprocessing", "pty"})
_PROCESS_CALLS = ("os.system", "os.popen", "os.fork", "os.exec", "os.spawn", "os.posix_spawn",
                  "concurrent.futures.ProcessPoolExecutor", "webbrowser.open")
_NETWORK_MODULES = frozenset({"socket", "ssl", "urllib.request", "http.client", "http.server", "socketserver",
                              "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "nntplib", "xmlrpc.client",
                              "xmlrpc.server", "requests", "httpx", "aiohttp", "urllib3", "websocket", "websockets"})
_WRITE_CALLS = frozenset({
    "os.remove", "os.unlink", "os.rename", "os.renames", "os.replace", "os.makedirs", "os.mkdir", "os.rmdir",
    "os.removedirs", "os.chmod", "os.chown", "os.lchown", "os.symlink", "os.link", "os.truncate", "os.utime",
    "os.mkfifo", "os.mknod", "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree", "shutil.move",
    "shutil.rmtree", "shutil.make_archive", "shutil.unpack_archive", "shutil.chown", "shutil.copymode",
    "shutil.copystat", "tempfile.mkstemp", "tempfile.mkdtemp", "tempfile.NamedTemporaryFile",
    "tempfile.TemporaryDirectory", "tempfile.TemporaryFile", "tempfile.SpooledTemporaryFile"})
_WRITE_METHODS = frozenset({"write_text", "write_bytes", "touch", "unlink", "rmdir", "mkdir", "symlink_to",
                            "hardlink_to"})
_READ_CALLS = frozenset({"os.listdir", "os.scandir", "os.walk", "os.stat", "os.lstat", "os.access",
                         "os.path.exists", "os.path.lexists", "os.path.isfile", "os.path.isdir", "os.path.islink",
                         "os.path.getsize", "os.path.getmtime", "os.path.getatime", "os.path.getctime",
                         "glob.glob", "glob.iglob", "fileinput.input", "pkgutil.get_data", "linecache.getline",
                         "linecache.getlines"})
_READ_METHODS = frozenset({"read_text", "read_bytes", "iterdir", "glob", "rglob"})
#: Calls that open a file by a mode, read unless the mode writes, appends, creates or updates.
_OPEN_CALLS = frozenset({"open", "io.open", "builtins.open", "codecs.open", "gzip.open", "bz2.open", "lzma.open",
                         "tarfile.open", "zipfile.ZipFile", "shelve.open", "dbm.open"})


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return ".".join([node.id] + parts[::-1]) if isinstance(node, ast.Name) else ""


def _tree_effects(tree, where, aliases: dict, found: dict) -> None:
    """Add effect -> rule for what one syntax tree shows; aliases maps an imported name to its full dotted name."""
    def note(effect, what, node):
        found.setdefault(effect, f"{what} {where(node)}")

    def module_effects(module, node):
        parts = module.split(".")
        if parts[0] in _PROCESS_MODULES:
            note("spawns_process", f"imports {module}", node)
        if module in _NETWORK_MODULES or parts[0] in _NETWORK_MODULES or ".".join(parts[:2]) in _NETWORK_MODULES:
            note("network", f"imports {module}", node)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else \
                    alias.name.split(".")[0]
                module_effects(alias.name, node)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
                module_effects(f"{node.module}.{alias.name}", node)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        head, _, rest = name.partition(".")
        resolved = (f"{aliases.get(head, head)}.{rest}" if rest else aliases.get(head, head)) if name else ""
        method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        called = resolved or method
        if resolved.startswith(_PROCESS_CALLS):
            note("spawns_process", f"calls {called}", node)
        if resolved in _WRITE_CALLS or method in _WRITE_METHODS:
            note("writes_fs", f"calls {called}", node)
        if resolved in _READ_CALLS or method in _READ_METHODS:
            note("reads_fs", f"calls {called}", node)
        if resolved == "os.open" or (resolved == "sqlite3.connect" and not (
                node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == ":memory:")):
            note("reads_fs", f"calls {called}", node)
            note("writes_fs", f"calls {called}", node)
        elif resolved in _OPEN_CALLS or (method == "open" and resolved != "webbrowser.open"):
            mode = node.args[1] if len(node.args) > 1 else next(
                (keyword.value for keyword in node.keywords if keyword.arg == "mode"), None)
            text = mode.value if isinstance(mode, ast.Constant) and isinstance(mode.value, str) else "r"
            note("writes_fs" if set(text) & set("wax+") else "reads_fs", f"calls {called}", node)


def code_effects(text: str) -> list:
    """(effect, rule) of every effect the module's syntax tree and its docstring examples show; each rule names the
    import or call and where it is. The tests run every example of every docstring in the module, so an example's
    effects are the package's."""
    tree = ast.parse(text)
    aliases, found = {}, {}
    _tree_effects(tree, lambda node: f"at line {getattr(node, 'lineno', 0)}", aliases, found)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            sources = [example.source for example in docstring_examples(node)]
            try:
                examples = ast.parse("".join(sources)) if sources else None
            except SyntaxError:
                continue  # examples that do not parse fail their doctests, and the package with them
            if examples is not None:
                _tree_effects(examples, lambda _node, name=node.name: f"in an example of {name}", dict(aliases),
                              found)
    return sorted(found.items())


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


def run_tests(folder: Path, module: str) -> tuple:
    """Run extracted upstream code only through the existing qualification sandbox.

    The two files are copied into a fresh workspace for every run, including
    the known-wrong control. A missing or failed sandbox never falls back to
    importing the code into the generator process.
    """
    settings = SandboxSettings()
    available, reason = settings.available()
    if not available:
        raise ExtractRefused("sandbox_unavailable", reason)
    payloads = {name: (folder / name).read_bytes() for name in (f"{module}.py", f"test_{module}.py")}
    package = CataloguePackage(tuple(CataloguePackageFile(
        name, hashlib.sha256(body).hexdigest(), len(body), "text/x-python", "executable_tool")
        for name, body in payloads.items()))
    component = GeneratedComponent(module, "1", MappingProxyType({}), package, MappingProxyType(payloads))
    try:
        report = run_component(component, settings, folder / "sandbox")
    except OSError as error:
        raise ExtractRefused("sandbox_unavailable", type(error).__name__) from error
    if not report.get("ran") or report.get("timed_out"):
        raise ExtractRefused("sandbox_failed", report.get("reason", "sandbox did not finish"))
    tests = report.get("tests") or {}
    imports = report.get("imports", ())
    if tests.get("timed_out") or any(row.get("timed_out") for row in imports):
        raise ExtractRefused("sandbox_failed", "extracted code exceeded its time limit")
    passed = (tests.get("passed", False) and tests.get("ran", 0) > 0
              and all(row["ok"] for row in imports))
    detail = "\n".join(row.get("tail", "") for row in imports if not row["ok"])
    return passed, tests.get("ran", 0), (detail + tests.get("tail", ""))[-800:]


def generate(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: "dict | None" = None) -> tuple:
    """(built, refusals, facts, summary): every documented function of every declared library, tested."""
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/function_extracts.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    for source in sources:
        repository = source["repository"]
        if source.get("withheld"):
            # Declared and not read: the row keeps its curated modules, and its reason says what was measured.
            refused.append(refusal(FUNCTION_EXTRACTS, SOURCE_WITHHELD, repository, source["withheld"]))
            continue
        try:
            pinned, missing = pinned_files(reader, repository, source["branch"], source["modules"])
        except LookupError as error:
            refused.append(refusal(FUNCTION_EXTRACTS, "source_unreadable", repository, str(error)))
            continue
        for path in missing:
            refused.append(refusal(FUNCTION_EXTRACTS, "source_unreadable", f"{repository} {path}",
                                   "not a file at the commit, or its bytes differ from the blob"))
        if not pinned:
            continue
        commit = next(iter(pinned.values()))["commit"]
        licence = repository_licence(reader, repository, commit)
        if not licence.allowed:
            refused.append(refusal(FUNCTION_EXTRACTS, licence.refusal_reason(
                ("licence_not_on_allowlist", "licence_signals_disagree", "licence_unknown")), repository,
                str(licence.github_spdx)))
            continue
        source = {**source, "notice": repository_notice(reader, repository, commit, licence.spdx)}
        modules = {}
        for path, found in pinned.items():
            facts[found["sha256"]] = found["bytes"]
            text = found["bytes"].decode("utf-8")
            try:
                modules[path] = (module_statements(path, text), text)
            except SyntaxError as error:
                refused.append(refusal(FUNCTION_EXTRACTS, "source_unreadable", path, str(error)[:120]))
        licence_statements = {path: foreign_licences(text, licence.spdx) for path, (_rows, text) in modules.items()}
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
                # A library of many independent files (one algorithm each) names each function by its file too.
                identity = (path, node.name) if source.get("name_by_module") else node.name
                if identity in seen:
                    refused.append(refusal(FUNCTION_EXTRACTS, "duplicate_function", label))
                    continue
                try:
                    payload = _package(node, path, modules, source, pinned, licence, commit, generator, licence_text,
                                       generated_on, staging, repository_facts or {}, licence_statements)
                except ExtractRefused as error:
                    refused.append(refusal(FUNCTION_EXTRACTS, error.reason, label, error.detail))
                    continue
                except SupplyRecordError as error:
                    reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                        GENERATED_TEST_FAILED
                    refused.append(refusal(FUNCTION_EXTRACTS, reason, label, str(error)))
                    continue
                seen.add(identity)
                built.append(payload)
                taken += 1
        summary.append({"source_id": source["source_id"], "repository": repository, "commit": commit,
                        "licence": licence.spdx, "modules": len(modules), "packaged": taken})
    return built, refused, facts, summary


def _package(node, path, modules, source, pinned, licence, commit, generator, licence_text, generated_on, staging,
             repository_facts, licence_statements):
    reason = not_a_reusable_job(node)
    if reason:
        raise ExtractRefused(NOT_A_REUSABLE_JOB, reason)
    examples = docstring_examples(node)
    if not examples:
        raise ExtractRefused(NO_EXAMPLES)
    summary = description_of(ast.get_docstring(node) or "")
    if not summary:
        raise ExtractRefused(NO_DESCRIPTION, "its docstring says nothing in words before its examples and fields")
    closure = closure_of(node.name, path, modules, source["package_root"],
                         extra_names=sorted(example_names(node) - {node.name}))
    qualifier = re.sub(r"[^a-z0-9]+", "_", Path(path).with_suffix("").as_posix().lower()).strip("_") \
        if source.get("name_by_module") else ""
    module = "_".join(part for part in (source["vendor"], qualifier, node.name.lower()) if part)
    if len(module) > 80:
        module = f"{source['vendor']}_{hashlib.sha256(module.encode()).hexdigest()[:10]}_{node.name.lower()}"[:80]
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", module):
        raise ExtractRefused(CLOSURE_UNRESOLVED, f"no module name for {node.name}")
    paths = sorted({statement.module for statement in closure.statements})
    for copied in paths:
        names = {name for statement in closure.statements if statement.module == copied for name in statement.binds}
        for covered, excerpt in licence_statements.get(copied, ()):
            if covered is None or covered & names:
                raise ExtractRefused(MODULE_LICENCE_DIFFERS, f"{copied}: {excerpt}")
    backports = ", ".join(sorted(closure.backports.values()))
    header = (f"# {node.name}, extracted by Baltor from {source['repository']} at commit {commit}\n"
              f"# ({', '.join(paths)}). Every statement below the imports is copied whole from those files;\n"
              + (f"# typing provides {backports}, which the upstream imports from {BACKPORT_MODULE} for its "
                 "annotations;\n" if backports else "")
              + f"# licence {licence.spdx}, see UPSTREAM-LICENSE and ATTRIBUTION.md.\n")
    text = module_text(closure, node.name, header)
    tests = test_text(module)
    folder = staging / module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{module}.py").write_text(text, encoding="utf-8")
    (folder / f"test_{module}.py").write_text(tests, encoding="utf-8")
    try:
        passed, count, output = run_tests(folder, module)
        if not passed:
            raise ExtractRefused(EXAMPLES_FAILED, output[-300:])
        docstring = ast.get_docstring(node, clean=False) or ""
        (folder / f"{module}.py").write_text(mutant_text(text, node.name, docstring), encoding="utf-8")
        mutant_passed, _count, _output = run_tests(folder, module)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if mutant_passed:
        raise ExtractRefused(EXAMPLES_DO_NOT_EXERCISE, node.name)
    segments = [[statement.module, statement.start, statement.end] for statement in closure.statements]
    others = sorted({name for statement in closure.statements if not statement.type_checking
                     for name in statement.binds} - {node.name})
    total = example_count(text)
    readme = (f"# {node.name}\n\n`{signature_text(node)}`\n\n{shortened(summary, README_DESCRIPTION_CHARACTERS)}\n\n"
              f"From {source['title']} ({source['repository']}), commit `{commit}`, licensed {licence.spdx}.\n"
              f"`{module}.py` holds the function and the code it and its examples use, each statement copied "
              "whole:\n\n"
              + "".join(f"- `{segment[0]}` lines {segment[1]} to {segment[2]}\n" for segment in segments)
              + (f"\nBesides the function it defines {_listed(others)}, which the function or its examples use; "
                 "`__all__` names the function alone.\n" if others else "")
              + ("\nStandard library imports the code uses are written at the top"
                 + (f"; {backports} is imported from typing, where the upstream imports it from {BACKPORT_MODULE} "
                    "for its annotations" if backports else "") + ".\n" if closure.imports else "")
              + f"\n`test_{module}.py` {_tests_sentence(module, total, len(examples), count)} The same function "
              "raising NotImplementedError under its own docstring fails them, so the examples exercise it.\n")
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
    notices, notice_facts = notice_files([source.get("notice")])
    files += notices
    facts += notice_facts
    expression = " AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx]))
    name = module.replace("_", "-")[:90]
    identity = f"{source['repository']}:{path}:{node.name}"
    stars = ((repository_facts.get(source["repository"].lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=FUNCTION_EXTRACTS, identity=identity, key=upstream_key(FUNCTION_EXTRACTS, identity), kind="code_module",
        native_format=NATIVE_FORMAT, form="function", name=name,
        description=f"{node.name} from {source['title']}: {shortened(summary, RECORD_DESCRIPTION_CHARACTERS)} One "
                    "tested Python function, copied with the code it needs.",
        files=files, licence_expression=expression,
        provenance=provenance("github_repository", source["repository"], path, commit, facts, generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=code_effects(text), credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False, "sandbox_engine": SandboxSettings().engine,
               "known_wrong_control": "the function raising NotImplementedError under its own docstring fails"},
        repository={"name": source["repository"], "stars": stars, "module": path, "function": node.name,
                    "segments": segments},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def _listed(names) -> str:
    quoted = [f"`{name}`" for name in names]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " and " + quoted[-1]


def _tests_sentence(module: str, total: int, own: int, tests: int) -> str:
    """What the tests run, counted as doctest counts it: every example of every docstring in the module, one test
    per docstring (1.1.0 said "runs the 1 examples of the docstrings (4 test runs)" when the function's one example
    sat beside the examples of three helpers)."""
    if total == own:
        return (f"runs the function's {own} docstring example{'s' if own != 1 else ''} as "
                f"{'doctests' if own != 1 else 'a doctest'}, offline ({tests} test{'s' if tests != 1 else ''}).")
    return (f"runs all {total} docstring examples of `{module}.py` as doctests, offline, one test per docstring "
            f"({tests} tests); {own} of them {'are' if own != 1 else 'is'} the function's own.")


__all__ = ["Closure", "ExtractRefused", "closure_of", "code_effects", "description_of", "docstring_examples",
           "foreign_licences", "generate", "module_statements", "module_text", "mutant_text", "not_a_reusable_job",
           "read_sources", "shortened", "signature_text", "test_text"]

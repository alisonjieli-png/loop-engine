#!/usr/bin/env python3
"""Check that the component guides describe the source that exists.

A component guide drifts in two directions. It can name a command, a record
type, a refusal code or a class that the source no longer defines, and it can
fall silent about a component the runtime gained. This check refuses both.

What it decides
---------------

1. Component coverage. Every operational boundary registered in the audited
   repository's ``loop_engine/core/boundary_registry.py`` is resolved to the
   source directory that owns its envelope. The rows are read from that file
   as a literal, without importing or running it, so the tree being checked is
   always compared against its own boundaries. Every such directory must be
   listed in ``docs/components/COMPONENT-GUIDE-MAP.yaml`` with a guide that
   exists. A new boundary in a directory with no guide fails this check. The
   rule resolves one guide for each directory, not one for each boundary; the
   map's ``limits`` field records what that does and does not prove.

2. Claim verification. Every claim a guide writes in backticks must resolve
   against the source:

   * a record type such as ``loop_definition/v2`` must appear in the package;
   * a command such as ``loop-engine records`` or ``loop-engine --profiles``
     must be a registered command or root option;
   * a refusal code, status value or field name such as
     ``record_id_outside_scope`` must appear in the package. Loop Engine
     writes these in lower case with underscores, so that is the shape this
     rule reads; an upper case constant is read the same way;
   * a class, function, module or field name must be defined in the package.

   A name that belongs to another project, such as a third-party client class,
   is declared once in the map's ``external_names`` list with the reason it is
   not a Loop Engine name. A placeholder an example asks the reader to supply
   is declared the same way in ``reader_supplied_names``, and a contract name
   invented to make an example concrete in ``example_record_types``. A single
   lower case word carrying no underscore is too common to decide from its
   name, so the rule stays silent on it rather than guessing.

3. Guide registration. Every Markdown file under ``docs/components`` is listed
   in the map, so a new guide carries a decision about what it covers and a
   guide for a removed component is visible.

4. Documented checks, with ``--run-documented-checks``. A guide that tells a
   reader to run a command is making a claim, and this runs it. Only one exact
   shape is executed, the ``self_test`` command every guide writes, and it is
   rebuilt from the module and the expression rather than handed to a shell.
   This is the rule that catches a command naming a report field the source
   builds at run time and nowhere else.

Rules one to three read files. They run no Loop, call no provider, and write
nothing. Rule four runs the package's own local self tests in a subprocess.
None of it decides whether a guide's sentences are true, only whether the
names they use exist and the commands they give work; a reviewer still reads
the prose.

Usage::

    PYTHONPATH=src python tools/check_component_guides.py
    PYTHONPATH=src python tools/check_component_guides.py --format json
    PYTHONPATH=src python tools/check_component_guides.py \\
        --run-documented-checks
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

#: The map lives beside the guides it governs.
MAP_PATH = "docs/components/COMPONENT-GUIDE-MAP.yaml"
#: The installed package whose names a guide may cite.
PACKAGE_PATH = "src/loop_engine"
#: The module whose argument parser owns the root command options.
MAIN_MODULE = "src/loop_engine/__main__.py"
#: The module whose table owns the public command names.
HELP_MODULE = "src/loop_engine/cli_help.py"
#: The module whose literal tuple registers every operational boundary.
REGISTER_MODULE = "src/loop_engine/core/boundary_registry.py"
#: Files whose text can carry a record type or a literal identity.
SOURCE_SUFFIXES = (".py", ".yaml", ".yml", ".json", ".toml", ".md")

_RECORD_TYPE = re.compile(r"\b([a-z][a-z0-9_]*/v[0-9]+)\b")
_UPPER_CODE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
#: Loop Engine writes almost every refusal code, status value and field name in
#: lower case with underscores, so this is the shape that matters most here. A
#: single word is too common to decide, so at least one underscore is required.
_SNAKE_NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_CAMEL_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*$")
_DOTTED_NAME = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)+$")
_CALL_NAME = re.compile(r"^[A-Za-z_][A-Za-z_0-9.]*\(\)$")
#: A service address a guide gives a reader, such as ``/api/v1/capabilities``.
#: A reader pastes these into a request, so a renamed route has to fail here.
_ROUTE = re.compile(r"^/[a-z][a-z0-9/_.-]*$")
#: A documented self-test command, in the exact shape every guide writes it:
#: import ``self_test`` from one package module and print one expression over
#: its report. Only this shape is executed, and it is rebuilt from these two
#: captured parts rather than handed to a shell.
_DOCUMENTED_CHECK = re.compile(
    r"from\s+(loop_engine[A-Za-z_0-9.]*)\s+import\s+self_test;\s*"
    r"print\((.+)\)\s*[\"']\s*$")
#: Seconds one documented check may take before it is reported as stuck.
DOCUMENTED_CHECK_TIMEOUT = 600

_COMMAND = re.compile(r"\bloop-engine\s+(--?[a-z][a-z0-9-]*|[a-z][a-z0-9-]*)")
_MODULE_COMMAND = re.compile(r"\b(?:python[0-9.]*\s+)?-m\s+loop_engine\s+(--[a-z][a-z0-9-]*)")
_INLINE_CODE = re.compile(r"`([^`\n]{2,120})`")
_FENCE = re.compile(r"^\s*```")


@dataclass(frozen=True)
class Finding:
    """One component guide statement the source does not support."""

    kind: str
    location: str
    line: int
    claim: str
    detail: str

    def render(self) -> str:
        where = f"{self.location}:{self.line}" if self.line else self.location
        return f"{where}: {self.kind}: {self.claim}: {self.detail}"


@dataclass(frozen=True)
class SourceFacts:
    """Everything the package really defines, read without importing it."""

    definitions: frozenset
    literals: frozenset
    modules: frozenset
    directories: frozenset
    commands: frozenset
    options: frozenset
    text: str

    def defines(self, name: str) -> bool:
        """Whether the package defines this exact name or a dotted path to it."""
        if name in self.definitions or name in self.modules:
            return True
        if any(module == name or module.endswith("." + name)
               for module in self.modules):
            return True
        leaf = name.split(".")[-1]
        if leaf in self.definitions:
            return True
        head = ".".join(name.split(".")[:-1])
        return bool(head) and any(
            module == head or module.endswith("." + head)
            for module in self.modules)

    def holds_literal(self, value: str) -> bool:
        """Whether this exact text appears anywhere in the package."""
        return value in self.literals or value in self.text


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def build_source_facts(package_root: Path, main_module: Path,
                       help_module: Path) -> SourceFacts:
    """Index the package's definitions, literals, modules and command surface."""
    definitions: set = set()
    literals: set = set()
    modules: set = set()
    directories: set = set()
    blob: list = []

    for path in sorted(package_root.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        text = _read(path)
        blob.append(text)
        relative = path.relative_to(package_root)
        directories.add(str(relative.parent))
        if path.suffix != ".py":
            literals.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text))
            continue
        dotted = ".".join(relative.with_suffix("").parts)
        modules.add(dotted)
        modules.add(package_root.name + "." + dotted)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                definitions.add(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                definitions.add(node.id)
            elif isinstance(node, ast.Attribute):
                definitions.add(node.attr)
            elif isinstance(node, ast.arg):
                definitions.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                definitions.add(node.arg)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                definitions.add(node.target.id)
            elif isinstance(node, ast.alias):
                definitions.add((node.asname or node.name).split(".")[0])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for inner in node.body:
                    if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        definitions.add(node.name + "." + inner.name)
                    elif isinstance(inner, ast.AnnAssign) and isinstance(
                            inner.target, ast.Name):
                        definitions.add(node.name + "." + inner.target.id)
                    elif isinstance(inner, ast.Assign):
                        for target in inner.targets:
                            if isinstance(target, ast.Name):
                                definitions.add(node.name + "." + target.id)

    return SourceFacts(
        definitions=frozenset(definitions),
        literals=frozenset(literals),
        modules=frozenset(modules),
        directories=frozenset(directories),
        commands=frozenset(_command_names(help_module)),
        options=frozenset(_root_options(main_module)),
        text="\n".join(blob))


def _command_names(help_module: Path) -> set:
    """The public command words the focused help table registers."""
    names: set = set()
    try:
        tree = ast.parse(_read(help_module))
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "COMMAND_HELP":
                for key in getattr(node.value, "keys", []):
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        names.add(key.value.split()[0])
    return names


def _root_options(main_module: Path) -> set:
    """The long options the root argument parser registers."""
    options: set = set()
    try:
        tree = ast.parse(_read(main_module))
    except SyntaxError:
        return options
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (isinstance(function, ast.Attribute)
                and function.attr == "add_argument"):
            continue
        for argument in node.args:
            if (isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and argument.value.startswith("-")):
                options.add(argument.value)
    return options


def owning_directory(envelope: str, package_root: Path) -> str:
    """The source directory that owns a registered boundary's envelope.

    The envelope is a dotted path into the package, sometimes ending in a
    class or function and sometimes carrying a template selector after a
    colon. The directory is the folder of the deepest module that exists.
    """
    head = envelope.split(":")[0]
    parts = [part for part in head.split(".") if part]
    while parts:
        module = package_root.joinpath(*parts).with_suffix(".py")
        if module.exists():
            return str(module.parent.relative_to(package_root))
        package = package_root.joinpath(*parts)
        if (package / "__init__.py").exists():
            return str(package.relative_to(package_root))
        parts = parts[:-1]
    # An envelope may name a module through a selector rather than its full
    # dotted path. Accept it only when exactly one module carries that name.
    first = envelope.split(":")[0].split(".")[0]
    matches = sorted(package_root.rglob(first + ".py"))
    if len(matches) == 1:
        return str(matches[0].parent.relative_to(package_root))
    return ""


def _registered_boundaries(repository: Path) -> tuple:
    """The boundary rows this repository registers.

    The rows are read from the audited repository's own register rather than
    from whichever copy of the package happens to be importable, so a checked
    tree is always compared against its own boundaries. The register is a
    literal tuple of dictionaries, so it is read without importing or running
    any of it.
    """
    source = repository / REGISTER_MODULE
    rows = None
    if source.exists():
        try:
            tree = ast.parse(_read(source))
        except SyntaxError:
            tree = None
        for node in ast.walk(tree) if tree else ():
            if not isinstance(node, ast.Assign):
                continue
            names = [target.id for target in node.targets
                     if isinstance(target, ast.Name)]
            if "BOUNDARIES" not in names:
                continue
            try:
                rows = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                rows = None
            break
    if rows is None:
        raise SystemExit(
            f"cannot read the boundary register at {REGISTER_MODULE}; "
            "the coverage rule has nothing to check against")
    return tuple(
        {"boundary": row["boundary"], "envelope": row.get("envelope", "")}
        for row in rows)


def _guide_claims(text: str):
    """Yield (line number, claim text, inside a fenced block) for one guide."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            yield number, line, True
            continue
        for claim in _INLINE_CODE.findall(line):
            yield number, claim.strip(), False
        yield number, line, True


def _check_commands(location: str, number: int, line: str,
                    facts: SourceFacts, findings: list) -> None:
    for match in _COMMAND.finditer(line):
        word = match.group(1)
        if word.startswith("--"):
            if word not in facts.options:
                findings.append(Finding(
                    "unknown command option", location, number, word,
                    "the root argument parser registers no such option"))
        elif word.startswith("-"):
            continue
        elif word not in facts.commands:
            findings.append(Finding(
                "unknown command", location, number, word,
                "no such command is registered in the public help table"))
    for match in _MODULE_COMMAND.finditer(line):
        option = match.group(1)
        if option not in facts.options:
            findings.append(Finding(
                "unknown command option", location, number, option,
                "the root argument parser registers no such option"))


def _check_record_types(location: str, number: int, text: str,
                        facts: SourceFacts, examples: set,
                        findings: list) -> None:
    for name in _RECORD_TYPE.findall(text):
        if name in examples or facts.holds_literal(name):
            continue
        findings.append(Finding(
            "unknown record type", location, number, name,
            "the package defines no record type with this exact identity, "
            "and the map does not declare it as an example contract name"))


def _check_identifier(location: str, number: int, claim: str,
                      facts: SourceFacts, external: set, findings: list) -> None:
    bare = claim[:-2] if claim.endswith("()") else claim
    if bare in external:
        return
    if _ROUTE.match(bare):
        if not facts.holds_literal(bare):
            findings.append(Finding(
                "unknown service address", location, number, bare,
                "the package serves no route with this exact address"))
        return
    if _UPPER_CODE.match(bare) or _SNAKE_NAME.match(bare):
        if not (facts.holds_literal(bare) or facts.defines(bare)):
            findings.append(Finding(
                "unknown refusal or status code", location, number, bare,
                "the package defines no constant, field or literal with this "
                "name, and the map does not declare it as a name the reader "
                "supplies"))
        return
    if not (_CAMEL_NAME.match(bare) or _DOTTED_NAME.match(bare)
            or _CALL_NAME.match(claim)):
        return
    if facts.defines(bare) or facts.holds_literal(bare):
        return
    findings.append(Finding(
        "unknown name", location, number, bare,
        "the package defines no class, function, module, field or literal "
        "with this name"))


def documented_checks(guides_root: Path, repository: Path):
    """Yield (location, line, module, expression) for each documented check.

    A guide that tells a reader to run something is making a claim like any
    other. This finds the claims that can be decided by running them.
    """
    for path in sorted(guides_root.rglob("*.md")):
        try:
            location = str(path.relative_to(repository))
        except ValueError:
            # The guides being read need not sit inside the repository whose
            # package the commands import. Name the file as given.
            location = str(path)
        for number, line in enumerate(_read(path).splitlines(), 1):
            for module, expression in _DOCUMENTED_CHECK.findall(line):
                yield location, number, module, expression.strip()


def run_documented_checks(guides_root: Path, repository: Path) -> list:
    """Run each documented self-test command and report the ones that fail.

    This is the rule that catches a guide whose command names a report field
    the source does not build. The field is only there at run time, so no
    amount of reading the source decides it.
    """
    findings: list = []
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repository / "src")
    for location, number, module, expression in documented_checks(
            guides_root, repository):
        program = f"from {module} import self_test; print({expression})"
        try:
            completed = subprocess.run(
                [sys.executable, "-c", program], cwd=str(repository),
                env=environment, capture_output=True, text=True,
                timeout=DOCUMENTED_CHECK_TIMEOUT)
        except subprocess.TimeoutExpired:
            findings.append(Finding(
                "documented check does not finish", location, number, program,
                f"it ran longer than {DOCUMENTED_CHECK_TIMEOUT} seconds"))
            continue
        if completed.returncode == 0:
            continue
        reason = (completed.stderr or completed.stdout).strip().splitlines()
        findings.append(Finding(
            "documented check fails", location, number, program,
            reason[-1] if reason else
            f"it exited {completed.returncode} with no message"))
    return findings


def audit(repository: Path, boundaries=None) -> list:
    """Return every component guide statement the source does not support."""
    findings: list = []
    package_root = repository / PACKAGE_PATH
    guides_root = repository / "docs" / "components"
    map_path = repository / MAP_PATH

    if not map_path.exists():
        return [Finding("missing map", MAP_PATH, 0, MAP_PATH,
                        "the component guide map is required")]
    document = yaml.safe_load(_read(map_path)) or {}
    components = document.get("components") or {}
    guides = document.get("guides") or {}
    external = set(document.get("external_names") or {})
    external |= set(document.get("reader_supplied_names") or {})
    examples = set(document.get("example_record_types") or {})

    facts = build_source_facts(
        package_root, repository / MAIN_MODULE, repository / HELP_MODULE)

    rows = (_registered_boundaries(repository) if boundaries is None
            else tuple(boundaries))
    for row in rows:
        directory = owning_directory(row["envelope"], package_root)
        entry = components.get(directory or ".")
        if not entry:
            findings.append(Finding(
                "undocumented component", MAP_PATH, 0, row["boundary"],
                f"the boundary runs in {directory or '.'!r}, which the map "
                "lists no guide for"))
            continue
        guide = entry.get("guide", "") if isinstance(entry, dict) else str(entry)
        if not guide or not (repository / guide).exists():
            findings.append(Finding(
                "missing guide", MAP_PATH, 0, row["boundary"],
                f"the map sends {directory or '.'!r} to {guide!r}, "
                "which does not exist"))

    declared = set(guides)
    for path in sorted(guides_root.rglob("*.md")):
        relative = str(path.relative_to(repository))
        if relative not in declared:
            findings.append(Finding(
                "unregistered guide", relative, 0, relative,
                "every component guide is listed in the map with what it "
                "covers"))
    for relative in sorted(declared):
        if not (repository / relative).exists():
            findings.append(Finding(
                "guide for nothing", MAP_PATH, 0, relative,
                "the map lists a guide that does not exist"))

    for path in sorted(guides_root.rglob("*.md")):
        location = str(path.relative_to(repository))
        for number, claim, is_line in _guide_claims(_read(path)):
            if is_line:
                # The whole line already contains any backticked text on it,
                # so commands and record types are read once, here. Reading
                # them again from the inline claim would report each one twice.
                _check_commands(location, number, claim, facts, findings)
                _check_record_types(location, number, claim, facts, examples,
                                    findings)
            else:
                _check_identifier(location, number, claim, facts, external,
                                  findings)

    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_component_guides",
        description="Refuse a component guide that names source that is "
                    "not there, and a registered boundary with no guide.")
    parser.add_argument(
        "--repository", default=str(Path(__file__).resolve().parents[1]),
        help="repository root to read (default: this checkout)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--run-documented-checks", action="store_true",
        help="also run each self-test command a guide tells a reader to run, "
             "and refuse the ones that fail (slower; needs the package's "
             "dependencies installed)")
    arguments = parser.parse_args(argv)

    repository = Path(arguments.repository).resolve()
    findings = audit(repository)
    if arguments.run_documented_checks:
        findings += run_documented_checks(
            repository / "docs" / "components", repository)
    if arguments.format == "json":
        print(json.dumps({
            "record_type": "component_guide_audit/v1",
            "repository": str(repository),
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }, indent=1))
    else:
        for finding in findings:
            print(finding.render())
        print(f"{len(findings)} component guide findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

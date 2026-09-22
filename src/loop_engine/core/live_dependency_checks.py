"""Live dependency guard: a module that collected suites import at load keeps its own checks.

Owns: the ratchet check
``every_module_a_collected_suite_imports_at_load_has_its_suite_collected_or_a_recorded_exemption``,
the measurement behind it and its recorded baseline. Belongs to: core,
development assurance over the package's own suite registration. Never:
imports a module it measures, runs a suite, or edits the suite registration or
the rules store.

Why it exists. On September 21, 2026 the owner parked the in-process execution
capability (roadmap S-6.28): its suites left ``_FOLDED_SUBMODULE_TESTS`` in
``_self_test.py`` and are listed with a reason in ``suite_collection_exceptions``
of ``forbidden_paths.json``. Parking retired suites, not dependencies
(``docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md``, section 18.4, item 3):
modules whose suites were parked are still imported when collected suites
load, so live code rested on code whose own checks no longer ran.

What it measures. Source files are parsed, never imported. From every
collected suite it follows the import statements that run when a module loads:
the module body, class bodies, every part of a ``try`` and both branches of an
``if``, except the body of an ``if TYPE_CHECKING:`` block, which never runs.
Imports inside a function run only when the function is called, so they are
not followed. The package initializers on the way to a module are followed
too, because they load first. A call to ``importlib`` is not an import
statement and is not followed; the conformance scan confines such calls to
declared modules. A module reached this way has up to two suites:
its own ``self_test`` and the ``self_test`` of its companion module named
``<module>_checks``. A suite counts as collected when the registration names
it, or names a facade whose ``self_test`` only returns it, the rule
``scan_uncollected_self_tests`` already applies. The helpers that read the
registration are the conformance scan's own, so both read one registration
the same way.

The rule. Every suite of a module reached that way is collected, or is a
recorded exemption: an entry of the baseline below that also has a reason in
``suite_collection_exceptions``. The baseline is the list measured on
September 22, 2026 at revision ``e2898c7`` and may only shrink. An exemption
leaves it when its suite is collected again or when no collected suite imports
its module at load any more, and the check refuses a stale entry, so paid debt
cannot silently return. An entry that was not on the starting list is refused
by the digest of that list.
"""
from __future__ import annotations

import ast
import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass

from .._conformance_scan import (
    _registered_test_modules, _resolved_imports, _rules, _source_tree, _test_delegate)
from ..architecture_map import PACKAGE

_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRATION_FILE = "_self_test.py"
_COMPANION_SUFFIX = "_checks"

MEASUREMENT_RECORD_TYPE = "live_dependency_measurement/v1"
_MEASUREMENT_FIELDS = frozenset({"record_type", "collected_suites", "loaded_modules", "gaps"})
_GAP_FIELDS = frozenset({"suite", "module", "loaded_by"})

#: The baseline as measured on September 22, 2026 at revision e2898c7: every
#: suite that checks a module a collected suite imports at load, and that no
#: collected suite ran. This is a dated measurement. It never grows, and the
#: digest below makes any later edit of it visible to the check.
_BASELINE_AT_START: tuple[str, ...] = (
    "code_nodes/capture.py",
    "code_nodes/learning_bundle.py",
    "code_nodes/solution_model_port.py",
    "code_nodes/solve_terminal.py",
    "core/capability_directory.py",
    "core/context_artifacts.py",
    "core/context_budget.py",
    "core/context_classification.py",
    "core/context_ontology.py",
    "core/contract_matching.py",
    "core/evaluation_suite.py",
    "core/mistral_client.py",
    "core/model_capabilities.py",
    "core/model_ontology.py",
    "core/model_response_admission.py",
    "core/model_response_admission_checks.py",
    "core/model_response_text.py",
    "core/model_token_preflight.py",
    "core/night_budget.py",
    "core/observation_expectations.py",
    "core/ollama_client.py",
    "core/openrouter_client.py",
    "core/outcome_vector.py",
    "core/overnight_outcome.py",
    "core/practitioner_context.py",
    "core/provider_failover.py",
    "core/reasoning_call.py",
    "core/resolution.py",
    "core/runtime_capacity.py",
    "core/runtime_observer.py",
    "core/solution_library.py",
    "core/step_state.py",
    "core/suggested_output.py",
    "core/terminal_layer.py",
    "loop/atomic_primitives.py",
    "loop/effect_approval.py",
    "loop/intelligence_loops.py",
    "loop/intrinsic_kernel.py",
    "loop/loop_capsule.py",
    "loop/loop_definition_checks.py",
    "loop/loop_profile_ontology.py",
    "loop/loop_templates.py",
    "memory/model/memory_type.py",
    "memory/working/state.py",
    "ontology/artifacts.py",
    "ontology/records.py",
    "strings/context.py",
    "strings/intelligence_strings.py",
    "strings/notes.py",
    "strings/output_templates.py",
)
_BASELINE_AT_START_DIGEST = "597aace25dc46bfa234966aecce4c3599ad1411753b38909ad7c9d43d1f8321b"

#: Entries that left the baseline since the start, because their suite is
#: collected again or because no collected suite imports their module at load
#: any more.
_LEFT_THE_BASELINE: tuple[str, ...] = ()


@dataclass(frozen=True)
class LiveSuiteGap:
    """One suite that no collected suite runs, although one imports its module at load."""

    suite: str
    module: str
    loaded_by: tuple[str, ...]


@dataclass(frozen=True)
class LiveDependencyMeasurement:
    """What the collected suites import at load, and which of those suites are not run.

    Paths are relative to the package root; suites in ``collected_suites`` and
    ``loaded_by`` are dotted module names, the spelling the registration uses.
    """

    collected_suites: tuple[str, ...]
    loaded_modules: tuple[str, ...]
    gaps: tuple[LiveSuiteGap, ...]

    def to_dict(self) -> dict:
        return {"record_type": MEASUREMENT_RECORD_TYPE,
                "collected_suites": list(self.collected_suites),
                "loaded_modules": list(self.loaded_modules),
                "gaps": [{"suite": gap.suite, "module": gap.module,
                          "loaded_by": list(gap.loaded_by)} for gap in self.gaps]}

    @classmethod
    def from_dict(cls, value: object) -> "LiveDependencyMeasurement":
        """Read one record; refuse another version, a missing field or an unknown one."""
        if not isinstance(value, dict):
            raise ValueError("a live dependency measurement must be a mapping")
        if value.get("record_type") != MEASUREMENT_RECORD_TYPE:
            raise ValueError(f"unsupported record type {value.get('record_type')!r}; "
                             f"this reader accepts {MEASUREMENT_RECORD_TYPE}")
        if set(value) != _MEASUREMENT_FIELDS:
            raise ValueError("a live dependency measurement has exactly the fields "
                             f"{sorted(_MEASUREMENT_FIELDS)}; got {sorted(value)}")
        gaps = value["gaps"]
        if not isinstance(gaps, list) or any(
                not isinstance(gap, dict) or set(gap) != _GAP_FIELDS for gap in gaps):
            raise ValueError(f"every gap has exactly the fields {sorted(_GAP_FIELDS)}")
        return cls(_strings(value["collected_suites"], "collected_suites"),
                   _strings(value["loaded_modules"], "loaded_modules"),
                   tuple(LiveSuiteGap(_string(gap["suite"], "suite"),
                                      _string(gap["module"], "module"),
                                      _strings(gap["loaded_by"], "loaded_by"))
                         for gap in gaps))


@dataclass(frozen=True)
class LiveDependencyVerdict:
    """The ratchet's answer: new gaps, stale exemptions and exemptions without a reason."""

    new_gaps: tuple[LiveSuiteGap, ...]
    stale_exemptions: tuple[str, ...]
    unexplained_exemptions: tuple[str, ...]

    @property
    def holds(self) -> bool:
        return not (self.new_gaps or self.stale_exemptions
                    or self.unexplained_exemptions)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _strings(value: object, field: str) -> "tuple[str, ...]":
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(_string(item, field) for item in value)


def _source_path(root: str, module: str) -> str:
    """The package-relative source file of a dotted module name, or an empty string.

    A folder with an initializer is found before a file of the same name, the
    order Python's own path finder uses.
    """
    parts = [part for part in module.split(".") if part]
    if os.path.isfile(os.path.join(root, *parts, "__init__.py")):
        return "/".join([*parts, "__init__.py"])
    if parts and os.path.isfile(os.path.join(root, *parts) + ".py"):
        return "/".join(parts) + ".py"
    return ""


def _tree(root: str, module: str):
    relative = _source_path(root, module)
    return _source_tree(os.path.join(root, relative)) if relative else None


def _is_type_checking(test: ast.expr) -> bool:
    return ((isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"))


def _statements_run_at_load(node: ast.stmt) -> list:
    """The statements nested in one statement that run when the module loads.

    A function body runs only when the function is called. The body of an
    ``if TYPE_CHECKING:`` block never runs; its ``else`` branch does. Every
    other block is followed, including class bodies and both branches of any
    other ``if``, because a static reading cannot tell which branch runs.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    if isinstance(node, ast.If) and _is_type_checking(node.test):
        return list(node.orelse)
    nested = []
    for field in ("body", "orelse", "finalbody"):
        block = getattr(node, field, None)
        if isinstance(block, list):
            nested.extend(block)
    for field in ("handlers", "cases"):
        for clause in getattr(node, field, None) or ():
            nested.extend(clause.body)
    return nested


def _load_time_import_statements(tree: ast.Module) -> list:
    found, pending = [], list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.append(node)
        else:
            pending.extend(_statements_run_at_load(node))
    return found


def _with_initializers(root: str, module: str) -> "tuple[str, ...]":
    """The module and every package initializer that loads before it."""
    parts = module.split(".") if module else []
    chain = ["", *(".".join(parts[:index]) for index in range(1, len(parts) + 1))]
    return tuple(name for name in chain if _source_path(root, name))


def _direct_load_imports(root: str, module: str, memo: dict) -> frozenset:
    if module not in memo:
        found = set()
        relative = _source_path(root, module)
        tree = _source_tree(os.path.join(root, relative)) if relative else None
        prefix = PACKAGE + "."
        for node in _load_time_import_statements(tree) if tree is not None else ():
            for name in _resolved_imports(relative, node):
                if name == PACKAGE or name.startswith(prefix):
                    target = name[len(prefix):] if name != PACKAGE else ""
                    if _source_path(root, target):
                        found.update(_with_initializers(root, target))
        found.discard(module)
        memo[module] = frozenset(found)
    return memo[module]


def _load_closure(root: str, module: str, memo: dict) -> set:
    reached, pending = set(), list(_with_initializers(root, module))
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(_direct_load_imports(root, current, memo) - reached)
    return reached


def _defines_self_test(root: str, module: str) -> bool:
    tree = _tree(root, module)
    return tree is not None and any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "self_test"
        for node in tree.body)


def _delegate_of(root: str, module: str) -> str:
    tree = _tree(root, module)
    return _test_delegate(_source_path(root, module), tree) if tree is not None else ""


def _collected_suites(root: str) -> set:
    """The registered suites and every suite a registered facade returns."""
    tree = _source_tree(os.path.join(root, _REGISTRATION_FILE))
    if tree is None:
        raise ValueError(f"{_REGISTRATION_FILE} is missing or cannot be parsed")
    collected = set(_registered_test_modules(tree))
    pending = list(collected)
    while pending:
        target = _delegate_of(root, pending.pop())
        if target and target not in collected:
            collected.add(target)
            pending.append(target)
    return collected


def _suites_of(root: str, module: str) -> "tuple[str, ...]":
    """A module's own suite and its companion checks suite, where they exist."""
    if not module:
        return ()
    companion = module + _COMPANION_SUFFIX
    return tuple(name for name in (module, companion)
                 if _source_path(root, name) and _defines_self_test(root, name))


def measure_live_dependencies(root: "str | None" = None) -> LiveDependencyMeasurement:
    """Measure which suites of modules loaded by collected suites are not collected.

    Reads source files only. Raises ``ValueError`` when the registration cannot
    be read, because an unreadable registration measures nothing.
    """
    root = os.path.abspath(root or _PACKAGE_ROOT)
    collected = _collected_suites(root)
    memo: dict = {}
    loaded_by: dict = {}
    for suite in sorted(collected):
        for module in _load_closure(root, suite, memo):
            loaded_by.setdefault(module, set()).add(suite)
    gaps: dict = {}
    for module in sorted(loaded_by):
        for suite in _suites_of(root, module):
            if suite in collected or _delegate_of(root, suite) in collected:
                continue
            subject, importers = gaps.get(suite, (module, set()))
            gaps[suite] = (subject, importers | loaded_by[module])
    return LiveDependencyMeasurement(
        collected_suites=tuple(sorted(collected)),
        loaded_modules=tuple(sorted(_source_path(root, module) for module in loaded_by)),
        gaps=tuple(LiveSuiteGap(_source_path(root, suite), _source_path(root, subject),
                                tuple(sorted(importers)))
                   for suite, (subject, importers) in sorted(gaps.items())))


def judge_live_dependencies(measurement: LiveDependencyMeasurement,
                            baseline: "tuple[str, ...]",
                            recorded_reasons: dict) -> LiveDependencyVerdict:
    """Hold a measurement to a baseline of recorded exemptions.

    A gap outside the baseline is new debt and is refused. A baseline entry with
    no gap is stale: its suite is collected again or its module is no longer
    imported at load, so it must leave the baseline. A baseline entry without a
    reason in the rules store is refused, because an exemption is recorded only
    with its reason.
    """
    allowed = set(baseline)
    measured = {gap.suite for gap in measurement.gaps}
    return LiveDependencyVerdict(
        new_gaps=tuple(gap for gap in measurement.gaps if gap.suite not in allowed),
        stale_exemptions=tuple(sorted(allowed - measured)),
        unexplained_exemptions=tuple(sorted(
            entry for entry in allowed
            if not isinstance(recorded_reasons.get(entry), str)
            or not recorded_reasons[entry].strip())))


def _list_digest(entries: "tuple[str, ...]") -> str:
    return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


def baseline_problems(at_start: "tuple[str, ...]", left: "tuple[str, ...]",
                      expected_digest: str) -> "tuple[str, ...]":
    """Why a baseline could hold an entry the start did not; empty when it cannot.

    The baseline in force is the starting list less the entries that left it,
    so it can only shrink while the starting list is the one whose digest was
    recorded and every entry that left was on it.
    """
    problems = []
    if len(set(at_start)) != len(at_start):
        problems.append("the starting list names a suite twice")
    if _list_digest(at_start) != expected_digest:
        problems.append("the starting list differs from the list whose digest was recorded")
    outside = sorted(set(left) - set(at_start))
    if outside:
        problems.append(f"entries left the baseline that were never on it: {outside}")
    return tuple(problems)


def active_baseline() -> "tuple[str, ...]":
    """The recorded exemptions in force: the starting list less the entries that left it."""
    return tuple(sorted(set(_BASELINE_AT_START) - set(_LEFT_THE_BASELINE)))


_FIXTURE_SUITE = ('def self_test():\n'
                  '    return {"tests": [{"test": "fixture", "passed": True}]}\n')


def _fixture_files() -> dict:
    """A small package whose collected suites reach every import shape once."""
    return {
        "_self_test.py": '_FOLDED_SUBMODULE_TESTS = ["planted.live", "planted.facade"]\n',
        "__init__.py": '"""Fixture package."""\n',
        "planted/__init__.py": '"""Fixture folder."""\n',
        "planted/live.py": (
            "from typing import TYPE_CHECKING\n"
            "from . import parked\n"
            "from .helper import VALUE\n"
            "from .record import RECORD\n"
            "from ..planted_package.leaf import LEAF\n"
            f"import {PACKAGE}.planted.absolute\n"
            "if TYPE_CHECKING:\n"
            "    from . import typed_only\n"
            "try:\n"
            "    from . import in_try\n"
            "except ImportError:\n"
            "    in_try = None\n"
            "class Holder:\n"
            "    from . import in_class\n"
            "def later():\n"
            "    from . import lazy\n"
            "    return lazy\n" + _FIXTURE_SUITE),
        "planted/parked.py": _FIXTURE_SUITE,
        "planted/helper.py": "from .deep import DEPTH\nVALUE = DEPTH\n",
        "planted/deep.py": "DEPTH = 1\n" + _FIXTURE_SUITE,
        "planted/record.py": "RECORD = 1\n",
        "planted/record_checks.py": "from .record import RECORD\n" + _FIXTURE_SUITE,
        "planted/absolute.py": _FIXTURE_SUITE,
        "planted/typed_only.py": _FIXTURE_SUITE,
        "planted/in_try.py": _FIXTURE_SUITE,
        "planted/in_class.py": _FIXTURE_SUITE,
        "planted/lazy.py": _FIXTURE_SUITE,
        "planted/facade.py": ("def self_test():\n"
                              "    from .facade_checks import self_test as run\n"
                              "    return run()\n"),
        "planted/facade_checks.py": "from . import delegated\n" + _FIXTURE_SUITE,
        "planted/delegated.py": _FIXTURE_SUITE,
        "planted_package/__init__.py": "from . import initializer_import\n",
        "planted_package/initializer_import.py": _FIXTURE_SUITE,
        "planted_package/leaf.py": "LEAF = 1\n",
    }


#: The suites the fixture's collected suites leave unrun: the known-wrong cases.
_FIXTURE_GAPS = frozenset({
    "planted/parked.py", "planted/deep.py", "planted/record_checks.py",
    "planted/absolute.py", "planted/in_try.py", "planted/in_class.py",
    "planted/delegated.py", "planted_package/initializer_import.py"})


def _write_fixture(root: str, files: dict) -> None:
    for relative, text in files.items():
        path = os.path.join(root, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)


class _ImportAttempts:
    """A finder placed first on the import path that records lookups of fixture modules."""

    def __init__(self, names: frozenset) -> None:
        self.names, self.seen = names, []

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.names:
            self.seen.append(fullname)
        return None


def _fixture_module_names(files: dict) -> frozenset:
    names = set()
    for relative in files:
        parts = relative[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.add(".".join([PACKAGE, *parts]))
    return frozenset(names)


def self_test() -> dict:
    """Plant each known-wrong case, then hold the live package to the ratchet."""
    tests: list = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    files = _fixture_files()
    attempts = _ImportAttempts(_fixture_module_names(files))
    with tempfile.TemporaryDirectory(prefix="live-dependency-fixture-") as root:
        _write_fixture(root, files)
        sys.meta_path.insert(0, attempts)
        try:
            fixture = measure_live_dependencies(root)
        finally:
            sys.meta_path.remove(attempts)
    found = {gap.suite for gap in fixture.gaps}
    planted = judge_live_dependencies(fixture, (), {})
    exemptions = tuple(sorted(_FIXTURE_GAPS | {"planted/lazy.py", "planted/live.py"}))
    exempted = judge_live_dependencies(
        fixture, exemptions,
        {suite: "fixture reason" for suite in exemptions if suite != "planted/deep.py"})
    known_wrong_refused = {gap.suite for gap in planted.new_gaps} == set(_FIXTURE_GAPS)

    live_error = ""
    try:
        live = measure_live_dependencies()
        verdict = judge_live_dependencies(
            live, active_baseline(),
            _rules().get("suite_collection_exceptions", {}))
    except (ValueError, OSError) as exc:
        live, verdict = None, None
        live_error = f"{type(exc).__name__}: {exc}"

    check("every_module_a_collected_suite_imports_at_load_has_its_suite_collected_or_a_recorded_exemption",
          known_wrong_refused and verdict is not None and not verdict.new_gaps,
          live_error or (
              "the planted load-time import of a module with an uncollected suite was not refused"
              if not known_wrong_refused else
              "; ".join(f"{gap.suite} checks {gap.module}, imported at load by "
                        f"{', '.join(gap.loaded_by[:3])}" for gap in verdict.new_gaps)
              or f"{len(live.gaps)} gaps, all recorded exemptions"))
    check("an_exemption_leaves_the_baseline_once_its_suite_is_collected_or_its_module_is_not_imported_at_load",
          set(exempted.stale_exemptions) == {"planted/lazy.py", "planted/live.py"}
          and verdict is not None and not verdict.stale_exemptions,
          live_error or f"fixture stale: {list(exempted.stale_exemptions)}; "
                        f"live stale: {list(verdict.stale_exemptions)}")
    check("every_recorded_exemption_names_its_reason_in_the_rules_store",
          exempted.unexplained_exemptions == ("planted/deep.py",)
          and verdict is not None and not verdict.unexplained_exemptions,
          live_error or f"fixture: {list(exempted.unexplained_exemptions)}; "
                        f"live: {list(verdict.unexplained_exemptions)}")
    grown = _BASELINE_AT_START + ("core/an_entry_added_later.py",)
    check("the_baseline_only_shrinks_from_the_list_measured_at_the_start",
          not baseline_problems(_BASELINE_AT_START, _LEFT_THE_BASELINE, _BASELINE_AT_START_DIGEST)
          and bool(baseline_problems(grown, _LEFT_THE_BASELINE, _BASELINE_AT_START_DIGEST))
          and bool(baseline_problems(_BASELINE_AT_START, ("core/never_on_the_baseline.py",),
                                     _BASELINE_AT_START_DIGEST)),
          f"{len(active_baseline())} exemptions in force of {len(_BASELINE_AT_START)} "
          "measured at the start")
    check("an_import_inside_a_function_is_not_a_load_time_import",
          "planted/deep.py" in found and "planted/lazy.py" not in found, str(sorted(found)))
    check("an_import_under_type_checking_is_not_a_load_time_import",
          "planted/deep.py" in found and "planted/typed_only.py" not in found, str(sorted(found)))
    check("transitive_class_body_try_absolute_and_package_initializer_imports_are_load_time_imports",
          {"planted/deep.py", "planted/in_class.py", "planted/in_try.py", "planted/absolute.py",
           "planted_package/initializer_import.py"} <= found, str(sorted(found)))
    check("an_uncollected_companion_checks_module_is_the_suite_of_its_module",
          "planted/record_checks.py" in found, str(sorted(found)))
    check("a_facade_counts_its_delegate_as_collected_and_the_delegate_imports_as_loaded",
          "planted/delegated.py" in found and "planted/facade_checks.py" not in found
          and "planted.facade_checks" in fixture.collected_suites, str(sorted(found)))
    check("measuring_imports_no_module_it_measures",
          bool(found) and not attempts.seen, str(sorted(set(attempts.seen))[:5]))
    record = live.to_dict() if live is not None else {}
    refusals = []
    missing_field = {key: value for key, value in record.items() if key != "gaps"}
    for mutated in ({**record, "record_type": "live_dependency_measurement/v2"},
                    {**record, "unexpected_field": True}, missing_field):
        try:
            LiveDependencyMeasurement.from_dict(mutated)
            refusals.append(False)
        except ValueError:
            refusals.append(True)
    check("the_measurement_record_round_trips_and_refuses_another_version_or_a_changed_field_set",
          live is not None and LiveDependencyMeasurement.from_dict(record) == live
          and all(refusals), live_error or str(refusals))
    passed = sum(1 for item in tests if item["passed"])
    return {"module": "core.live_dependency_checks", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}

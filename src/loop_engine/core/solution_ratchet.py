"""Keep the best attempt a run ever produced, judged without its own constants.

Measured on 2026-09-05, run ``adaptive-c5800afdb0ce7b8525ecc2de``: the engine
produced a fully correct ISO-8601 parser on attempt 1, produced another correct
one on attempt 2, regressed to a broken one on attempt 3, and terminated
reporting failure.  It discarded a solved task because the only signal it had
was constants it wrote itself.

Two observations from that run drive the design here.

First, a model's test *inputs* are reliable while its expected *outputs* are
not.  Of eight expected constants it emitted, six were correct; both failures
were durations combining a date part with a time part, where the arithmetic is
multi-step.  Every input string it chose was valid.  Writing code delegates
arithmetic to the interpreter; writing a constant performs it by hand.  So this
module harvests INPUTS from the generated tests and refuses to read their
expected values.

Second, agreement between independently generated attempts is evidence that
needs no oracle.  Attempts 1 and 2 agreed on every input and were both correct;
attempt 3 dissented on exactly the four inputs it got wrong.  A majority across
attempts localises the regression without anyone knowing a single answer.

The ratchet is therefore: harvest inputs, compare attempts against each other,
score each attempt by how often it sits with the majority, and never let a
later attempt displace an earlier one that scored higher.  A run that solves
the task on attempt 1 keeps that solution even if it spends the rest of the
night breaking it.

THE MAJORITY IS A VOTE, NOT A NEIGHBOUR (2026-09-13).  The first version
compared each attempt with whichever peer happened to sort first, so the same
three attempts scored differently depending on directory order.  Now every
attempt is compared with every peer on every input, and an input's majority
outcome is the one held by a STRICT majority of the attempts voting on it.  An
attempt agrees when it holds that outcome, dissents when it does not, and is
undecided when no strict majority exists at all -- an even split is an absence
of evidence, not a room full of dissenters.  Attempt names sort naturally, so
attempt-10 follows attempt-9, and the module a test imports is preferred over
the first ``.py`` by name.
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .differential_verification import collect_outcomes, verify_differential

#: Test files are the input source; they are never read for expected values.
_TEST_PREFIXES = ("test_", "tests_")

#: How the majority is taken.  ``all``: the attempt's own outcome votes with
#: its peers', so at 3 attempts a 2-1 split has a majority.  ``peers``: only
#: the OTHER attempts vote, which is stricter (at 3 attempts each good one
#: sees a 1-1 split and stays undecided) and, at an even split, labels every
#: attempt a dissenter.  ``all`` is the default; ``peers`` remains available.
MAJORITY_SCOPES = ("all", "peers")
ALL_ATTEMPTS_VOTE, PEERS_VOTE = MAJORITY_SCOPES

_NUMBER_RUNS = re.compile(r"(\d+)")


def natural_key(text: str) -> tuple:
    """Sort key that puts attempt-10 after attempt-9, not after attempt-1.

    Digit runs compare as integers, everything else as text; each piece is
    tagged so a number and a word at the same position never raise.
    """
    return tuple((1, int(part)) if part.isdigit() else (0, part)
                 for part in _NUMBER_RUNS.split(str(text)) if part != "")


def attempt_sort_key(path: "str | Path") -> tuple:
    """Natural order on the attempt's name, then its full path as tiebreak."""
    return (natural_key(Path(path).name), str(path))


def sort_attempts(paths) -> list:
    """Attempt directories in natural order, as strings."""
    return sorted((str(p) for p in paths), key=attempt_sort_key)


@dataclass(frozen=True)
class AttemptScore:
    """How one attempt fared against the others on shared inputs."""

    attempt: str
    module: str
    majority_agreements: int
    dissents: int
    total: int
    #: Inputs on which no comparison could be decided -- the peers disagreed
    #: with each other, or the oracle could not run. Counting these separately
    #: is the whole point: an attempt compared with nobody has zero dissents,
    #: and reading that as unanimity turned maximal disagreement into the
    #: engine's strongest evidence (measured 2026-09-06: three mutually
    #: contradictory implementations, every pair FAIL, all scored
    #: dissents=0 is_best_available=True, promoting under cross_attempt_weight
    #: with the detail "3 attempts agree on 5 harvested inputs").
    undecided: int = 0
    #: Agreements whose majority outcome was a returned value or written
    #: artifact rather than an exception.  Three attempts that all raise
    #: NotImplementedError agree on every input and have done no work; a
    #: caller that promotes on agreement must ask for THIS number.
    value_agreements: int = 0

    @property
    def is_best_available(self) -> bool:
        """True only on POSITIVE agreement across every compared input.

        Absence of dissent is not agreement. This requires the attempt to have
        actually agreed with its peers on every input, with nothing undecided.
        """
        return (self.total > 0 and self.majority_agreements == self.total
                and self.dissents == 0 and self.undecided == 0)

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "module": self.module,
            "majority_agreements": self.majority_agreements,
            "value_agreements": self.value_agreements,
            "dissents": self.dissents,
            "undecided": self.undecided,
            "total": self.total,
            "is_best_available": self.is_best_available,
        }


@dataclass(frozen=True)
class RatchetReport:
    record_type: str = "solution_ratchet/v1"
    entry_point: str = ""
    inputs_harvested: int = 0
    scores: tuple[AttemptScore, ...] = ()
    retained: str = ""
    notes: tuple[str, ...] = ()
    majority_scope: str = "all"

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "entry_point": self.entry_point,
            "inputs_harvested": self.inputs_harvested,
            "scores": [s.to_dict() for s in self.scores],
            "retained": self.retained,
            "notes": list(self.notes),
            "majority_scope": self.majority_scope,
        }


def discover_entry_point(module_path: str | Path) -> str:
    """Name the module's most likely public entry point, without importing it.

    Parsing rather than importing keeps generated code unexecuted at this
    stage; execution happens later, in a separate process, under the oracle.
    """
    try:
        tree = ast.parse(Path(module_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return ""
    public = [node.name for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and not node.name.startswith("_")]
    if not public:
        return ""
    # A module written to expose one operation usually exposes exactly one.
    # With several, prefer the one taking a single positional argument, which
    # is what a differential oracle can drive.
    if len(public) == 1:
        return public[0]
    for node in tree.body:
        if (isinstance(node, ast.FunctionDef) and node.name in public
                and len(node.args.args) == 1):
            return node.name
    return public[0]


def harvest_inputs(test_path: str | Path, entry_point: str) -> tuple:
    """Collect the arguments a generated test passes to the entry point.

    Only call arguments are read.  The expected values those calls are compared
    against are deliberately ignored: they are the part a model gets wrong.

    Arguments are resolved through local assignments as well as inline
    literals, because a structured input is almost never written inline.  A
    scheduling test says ``tasks = [{...}, {...}]`` on one line and
    ``build_schedule(tasks)`` on the next -- reading only inline literals
    harvested nothing at all from a real generated scheduler, which is the
    shape of every planning, document and data task.
    """
    try:
        tree = ast.parse(Path(test_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return ()
    harvested: list = []
    seen: set = set()

    def collect(value) -> None:
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            harvested.append(value)

    def scan(scope) -> None:
        """Walk one scope, tracking literal locals so a Name can resolve."""
        locals_seen: dict = {}
        for node in ast.walk(scope):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            locals_seen[target.id] = ast.literal_eval(node.value)
                        except (ValueError, SyntaxError):
                            continue
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            name = (function.attr if isinstance(function, ast.Attribute)
                    else getattr(function, "id", ""))
            if name != entry_point or not node.args:
                continue
            # Multi-argument calls are the common case for anything that
            # takes a destination or a configuration alongside its input:
            # measured 2026-09-06, render_gantt_html(tasks, finish_times,
            # output_path) harvested NOTHING under a single-argument rule, so
            # a correct renderer produced no comparable evidence and was
            # reported as unrecoverable. Resolve every positional argument,
            # and keep the call only if all of them resolve.
            resolved = []
            unresolved = []
            for position, argument in enumerate(node.args):
                if isinstance(argument, ast.Name):
                    if argument.id in locals_seen:
                        resolved.append(locals_seen[argument.id])
                        continue
                    resolved.append(None)
                    unresolved.append(position)
                    continue
                try:
                    resolved.append(ast.literal_eval(argument))
                except (ValueError, SyntaxError):
                    unresolved.append(position)
                    resolved.append(None)
            # A destination computed at run time -- os.path.join(d, 'out.html')
            # -- is worth substituting, because the function's real output is
            # the file it writes. Fabricating anything ELSE is inventing
            # evidence: measured 2026-09-06, substituting None for the sole
            # argument of parse_csv(path) made a real csv.DictReader parser and
            # a stub returning {'rows': 0} compare EQUAL, because the driver
            # hashed an empty file it had created itself and neither
            # implementation had been given real input.
            #
            # So a sink is admitted only when it is the LAST positional
            # argument AND at least one earlier argument resolved to a real
            # value. A call whose only argument is unresolvable carries no
            # information and is dropped.
            if not unresolved:
                collect(resolved[0] if len(resolved) == 1
                        else {"__argv__": resolved})
            elif (len(unresolved) == 1
                  and unresolved[0] == len(resolved) - 1
                  and len(resolved) > 1
                  and all(value is not None
                          for value in resolved[:-1])):
                collect({"__argv__": resolved, "__sink__": unresolved[0]})

    scopes = [n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for scope in scopes or [tree]:
        scan(scope)
    if not harvested:
        # A file-based API takes a PATH, so a test writes a fixture and passes
        # its location -- there is no literal argument anywhere to harvest.
        # Measured 2026-05-09 on a real CSV parser: three attempts, zero
        # harvestable inputs, nothing to compare. The fixture CONTENT is the
        # real input, so collect what the test writes and let the caller
        # materialise it.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", ""))
            if name not in ("write_text", "write"):
                continue
            if len(node.args) != 1:
                continue
            try:
                written = ast.literal_eval(node.args[0])
            except (ValueError, SyntaxError):
                continue
            if isinstance(written, str) and written.strip():
                collect({"__fixture_content__": written})
    if not harvested and scopes:
        # Module-level calls, if the tests are written as a bare script.
        scan(tree)
    return tuple(harvested)


def imported_module_names(test_path: str | Path) -> tuple:
    """Top-level names a test file imports, in order, without importing them."""
    try:
        tree = ast.parse(Path(test_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return ()
    names: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module.split(".")[0])
    ordered: list = []
    for name in names:
        if name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def _attempt_files(attempt_dir: str | Path) -> tuple[str, str]:
    """Return (module, test) paths for one attempt directory.

    The module is the one the test imports when the attempt holds several --
    measured 2026-09-13, an attempt with ``helpers.py`` and ``mod.py`` was
    ranked on ``helpers.helper`` because it sorted first, harvested nothing,
    and retained nothing.  The first ``.py`` by name remains the fallback.
    """
    directory = Path(attempt_dir)
    modules, tests = [], []
    for path in sorted(directory.glob("*.py")):
        (tests if path.name.startswith(_TEST_PREFIXES) else modules).append(path)
    # A generator script that writes the project is not the project.
    modules = [m for m in modules if not m.name.startswith("generate")]
    test = tests[0] if tests else None
    module = None
    if test is not None and len(modules) > 1:
        by_stem = {m.stem: m for m in modules}
        for name in imported_module_names(test):
            if name in by_stem:
                module = by_stem[name]
                break
    if module is None and modules:
        module = modules[0]
    return (str(module) if module else "", str(test) if test else "")


def _outcome_table(live, entry_point: str, harvested, *, timeout: float,
                   host_execution_permitted: bool) -> dict:
    """Every attempt's outcome on every input, one contained process each.

    A module that times out over the whole set is retried one input at a
    time so a single hanging input does not erase its evidence elsewhere; a
    module that cannot load is not retried, because it cannot produce
    anything.  ``None`` marks an input with no outcome.
    """
    table: dict = {}
    for directory, module in live:
        outcomes, error = collect_outcomes(
            module, entry_point, harvested, timeout=timeout,
            host_execution_permitted=host_execution_permitted)
        if error is None and len(outcomes) == len(harvested):
            table[directory] = list(outcomes)
            continue
        row: list = [None] * len(harvested)
        salvageable = error is None or "exceeded" in error or (
            "no readable result" in error)
        if salvageable:
            for index, value in enumerate(harvested):
                single, single_error = collect_outcomes(
                    module, entry_point, [value], timeout=timeout,
                    host_execution_permitted=host_execution_permitted)
                if single_error is None and single:
                    row[index] = single[0]
        table[directory] = row
    return table


def majority_outcome(outcomes, voters: int) -> "str | None":
    """The outcome a STRICT majority of ``voters`` holds, or None.

    An attempt with no outcome still counts as a voter -- it voted for
    nothing -- so a majority is always measured against everyone who was
    asked, never only against those who answered.
    """
    counts = Counter(o for o in outcomes if o is not None)
    if not counts:
        return None
    outcome, count = counts.most_common(1)[0]
    return outcome if count * 2 > voters else None


def rank_attempts(attempt_dirs: "list[str] | tuple[str, ...]", *,
                  majority_scope: str = "all",
                  host_execution_permitted: bool = False,
                  timeout: float = 30.0) -> RatchetReport:
    """Score every attempt by agreement with the majority on harvested inputs."""
    if majority_scope not in MAJORITY_SCOPES:
        raise ValueError(f"majority_scope must be one of {MAJORITY_SCOPES}")
    pairs = [(_attempt_files(d)) for d in attempt_dirs]
    modules = [m for m, _ in pairs]
    if len([m for m in modules if m]) < 2:
        return RatchetReport(
            majority_scope=majority_scope,
            notes=("fewer than two attempts carry a module; "
                   "cross-attempt agreement cannot be computed",))
    entry_point = ""
    for module in modules:
        if module:
            entry_point = discover_entry_point(module)
            if entry_point:
                break
    if not entry_point:
        return RatchetReport(majority_scope=majority_scope,
                             notes=("no public entry point found",))

    harvested: list = []
    seen: set = set()
    for _, test in pairs:
        if not test:
            continue
        for value in harvest_inputs(test, entry_point):
            if repr(value) not in seen:
                seen.add(repr(value))
                harvested.append(value)
    if not harvested:
        return RatchetReport(
            entry_point=entry_point, majority_scope=majority_scope,
            notes=("no literal inputs could be harvested from the tests",))
    if host_execution_permitted is not True:
        return RatchetReport(
            entry_point=entry_point, inputs_harvested=len(harvested),
            majority_scope=majority_scope,
            notes=("host execution not permitted: the attempts were not "
                   "executed, so no agreement was measured",))

    live = [(str(d), m) for d, m in zip(attempt_dirs, modules) if m]
    table = _outcome_table(live, entry_point, harvested, timeout=timeout,
                           host_execution_permitted=host_execution_permitted)
    scores: list[AttemptScore] = []
    for directory, module in live:
        agreements = value_agreements = dissents = undecided = total = 0
        voters = [d for d, _ in live
                  if majority_scope == "all" or d != directory]
        if not [d for d in voters if d != directory]:
            continue
        for index in range(len(harvested)):
            total += 1
            mine = table[directory][index]
            majority = majority_outcome(
                [table[d][index] for d in voters], len(voters))
            if mine is None or majority is None:
                # No outcome, or no strict majority to agree or dissent
                # with: an absence of evidence that must never read as
                # agreement.
                undecided += 1
            elif mine == majority:
                agreements += 1
                if not majority.startswith("raises:"):
                    value_agreements += 1
            else:
                dissents += 1
        scores.append(AttemptScore(
            attempt=directory, module=module,
            majority_agreements=agreements, dissents=dissents,
            undecided=undecided, total=total,
            value_agreements=value_agreements))

    ranked = sorted(scores, key=lambda s: (-s.majority_agreements, s.dissents,
                                           s.undecided,
                                           attempt_sort_key(s.attempt)))
    retained = ranked[0].attempt if ranked else ""
    scope_note = ("all attempts vote on each input" if majority_scope == ALL_ATTEMPTS_VOTE
                  else "only the other attempts vote on each input")
    return RatchetReport(
        entry_point=entry_point, inputs_harvested=len(harvested),
        scores=tuple(scores), retained=retained, majority_scope=majority_scope,
        notes=("inputs harvested from generated tests; expected values ignored",
               "retention prefers the earliest attempt at the best score, so a "
               "later regression cannot displace an earlier solution",
               f"majority is a strict majority per input ({scope_note}), so "
               "the verdict does not depend on directory order"))


def self_test() -> dict:
    """Offline proof that the ratchet keeps the correct attempt."""
    import tempfile
    from functools import partial
    rank_attempts = partial(globals()["rank_attempts"], host_execution_permitted=True)

    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    good = ("def parse(text):\n"
            "    table = {'PT30S': 30, 'PT1M': 60, 'P1D': 86400}\n"
            "    if text not in table:\n"
            "        raise ValueError('bad')\n"
            "    return table[text]\n")
    broken = ("def parse(text):\n"
              "    table = {'P1D': 86400}\n"
              "    if text not in table:\n"
              "        raise ValueError('bad')\n"
              "    return table[text]\n")
    # Expected values here are deliberately WRONG; only the inputs are used.
    tests = ("import unittest\n"
             "from mod import parse\n"
             "class T(unittest.TestCase):\n"
             "    def test_a(self):\n"
             "        self.assertEqual(parse('PT30S'), 99999)\n"
             "        self.assertEqual(parse('PT1M'), 88888)\n"
             "        self.assertEqual(parse('P1D'), 77777)\n")

    def workspace(root, bodies, extra=None):
        base = Path(root)
        for name, source in bodies.items():
            directory = base / name
            directory.mkdir(parents=True)
            (directory / "mod.py").write_text(source, encoding="utf-8")
            (directory / "test_mod.py").write_text(tests, encoding="utf-8")
            for extra_name, extra_body in (extra or {}).items():
                (directory / extra_name).write_text(extra_body, encoding="utf-8")
        return base

    with tempfile.TemporaryDirectory() as root:
        base = workspace(root, {"attempt-1": good, "attempt-2": good,
                                "attempt-3": broken})

        entry = discover_entry_point(str(base / "attempt-1" / "mod.py"))
        check("entry_point_discovered_without_importing", entry == "parse", entry)

        harvested = harvest_inputs(str(base / "attempt-1" / "test_mod.py"),
                                   "parse")
        check("inputs_harvested_from_tests",
              set(harvested) == {"PT30S", "PT1M", "P1D"}, str(harvested))

        source = (base / "attempt-1" / "test_mod.py").read_text(encoding="utf-8")
        check("wrong_expected_values_are_never_read",
              "99999" in source and 99999 not in harvested)

        dirs = [str(base / "attempt-1"), str(base / "attempt-2"),
                str(base / "attempt-3")]
        report = rank_attempts(dirs)
        by_attempt = {Path(s.attempt).name: s for s in report.scores}
        check("all_three_attempts_scored", len(report.scores) == 3,
              str(len(report.scores)))
        check("broken_attempt_dissents",
              by_attempt.get("attempt-3") is not None
              and by_attempt["attempt-3"].dissents > 0,
              str(report.to_dict()["scores"]))
        check("correct_attempt_does_not_dissent",
              by_attempt.get("attempt-1") is not None
              and by_attempt["attempt-1"].dissents == 0)
        check("earliest_best_attempt_is_retained",
              Path(report.retained).name == "attempt-1", report.retained)
        check("report_serializes",
              report.to_dict()["record_type"] == "solution_ratchet/v1")

        # H4: the same attempts in any order give the same scores.
        def signature(rep):
            return {Path(s.attempt).name: (s.majority_agreements, s.dissents,
                                           s.undecided, s.is_best_available)
                    for s in rep.scores}
        reversed_report = rank_attempts([dirs[2], dirs[0], dirs[1]])
        rotated_report = rank_attempts([dirs[1], dirs[2], dirs[0]])
        check("verdict_does_not_depend_on_directory_order",
              signature(report) == signature(reversed_report)
              == signature(rotated_report)
              and Path(reversed_report.retained).name == "attempt-1"
              and Path(rotated_report.retained).name == "attempt-1",
              f"{signature(report)} vs {signature(reversed_report)}")
        check("two_agreeing_attempts_are_a_majority_of_three",
              by_attempt["attempt-1"].is_best_available
              and by_attempt["attempt-2"].is_best_available
              and not by_attempt["attempt-3"].is_best_available)

        single = rank_attempts([str(base / "attempt-1")])
        check("one_attempt_cannot_be_ranked", single.retained == "",
              single.retained)

        # H5: unanimous exceptions agree, but not on values.
        raising = "def parse(text):\n    raise NotImplementedError('todo')\n"
        stubs = workspace(Path(root) / "stubs",
                          {f"attempt-{i}": raising for i in (1, 2, 3)})
        stub_report = rank_attempts(sort_attempts(stubs.glob("attempt-*")))
        check("unanimous_exceptions_agree_but_not_on_values",
              stub_report.scores
              and all(s.majority_agreements == s.total and s.total == 3
                      and s.value_agreements == 0 for s in stub_report.scores)
              and all(s.value_agreements == 3 for s in report.scores
                      if Path(s.attempt).name != "attempt-3"),
              str([s.to_dict() for s in stub_report.scores]))

        # An even split is an absence of evidence, not a dissent.
        pair = workspace(Path(root) / "pair",
                         {"attempt-1": good, "attempt-2": broken})
        even = rank_attempts(sort_attempts(pair.glob("attempt-*")))
        check("an_even_split_is_undecided_not_dissent",
              all(s.undecided == 2 and s.dissents == 0 for s in even.scores)
              and Path(even.retained).name == "attempt-1",
              str([s.to_dict() for s in even.scores]))
        peers = rank_attempts(sort_attempts(pair.glob("attempt-*")),
                              majority_scope="peers")
        check("peers_only_majority_scope_is_available",
              peers.majority_scope == "peers"
              and all(s.dissents == 2 for s in peers.scores),
              str([s.to_dict() for s in peers.scores]))

        # L5: ten or more attempts sort by number, not by string.
        check("attempt_ten_sorts_after_attempt_nine",
              sort_attempts(["attempt-10", "attempt-9", "attempt-11"])
              == ["attempt-9", "attempt-10", "attempt-11"])
        many = workspace(Path(root) / "many",
                         {"attempt-9": good, "attempt-10": good,
                          "attempt-11": broken})
        many_report = rank_attempts(sorted(str(p) for p in many.glob("attempt-*")))
        check("retention_ties_break_on_natural_order",
              Path(many_report.retained).name == "attempt-9",
              many_report.retained)

        # L6: the module the test imports wins over the first .py by name.
        multi = workspace(Path(root) / "multi",
                          {"attempt-1": good, "attempt-2": good},
                          extra={"helpers.py": "def helper(x):\n    return x\n"})
        module, test = _attempt_files(multi / "attempt-1")
        check("the_module_the_test_imports_is_preferred",
              Path(module).name == "mod.py" and Path(test).name == "test_mod.py",
              module)
        multi_report = rank_attempts(sort_attempts(multi.glob("attempt-*")))
        check("a_multi_file_attempt_is_still_ranked",
              multi_report.entry_point == "parse"
              and Path(multi_report.retained).name == "attempt-1",
              f"{multi_report.entry_point} {list(multi_report.notes)}")
        (multi / "attempt-1" / "test_mod.py").write_text(
            "import unittest\n", encoding="utf-8")
        fallback, _ = _attempt_files(multi / "attempt-1")
        check("first_module_by_name_remains_the_fallback",
              Path(fallback).name == "helpers.py", fallback)

        # Permission travels through: nothing runs without it.
        closed = rank_attempts(dirs, host_execution_permitted=False)
        check("host_execution_can_be_refused",
              closed.retained == "" and closed.scores == ()
              and any("not permitted" in note for note in closed.notes),
              str(closed.notes))

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

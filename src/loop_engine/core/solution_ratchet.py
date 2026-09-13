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
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .differential_verification import verify_differential

#: Test files are the input source; they are never read for expected values.
_TEST_PREFIXES = ("test_", "tests_")


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

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "entry_point": self.entry_point,
            "inputs_harvested": self.inputs_harvested,
            "scores": [s.to_dict() for s in self.scores],
            "retained": self.retained,
            "notes": list(self.notes),
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


def _attempt_files(attempt_dir: str | Path) -> tuple[str, str]:
    """Return (module, test) paths for one attempt directory."""
    directory = Path(attempt_dir)
    modules, tests = [], []
    for path in sorted(directory.glob("*.py")):
        (tests if path.name.startswith(_TEST_PREFIXES) else modules).append(path)
    # A generator script that writes the project is not the project.
    modules = [m for m in modules if not m.name.startswith("generate")]
    return (str(modules[0]) if modules else "",
            str(tests[0]) if tests else "")


def rank_attempts(attempt_dirs: "list[str] | tuple[str, ...]") -> RatchetReport:
    """Score every attempt by agreement with the majority on harvested inputs."""
    pairs = [(_attempt_files(d)) for d in attempt_dirs]
    modules = [m for m, _ in pairs]
    if len([m for m in modules if m]) < 2:
        return RatchetReport(
            notes=("fewer than two attempts carry a module; "
                   "cross-attempt agreement cannot be computed",))
    entry_point = ""
    for module in modules:
        if module:
            entry_point = discover_entry_point(module)
            if entry_point:
                break
    if not entry_point:
        return RatchetReport(notes=("no public entry point found",))

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
            entry_point=entry_point,
            notes=("no literal inputs could be harvested from the tests",))

    live = [(d, m) for d, m in zip(attempt_dirs, modules) if m]
    scores: list[AttemptScore] = []
    for directory, module in live:
        agreements = dissents = undecided = total = 0
        for value in harvested:
            others = [m for d, m in live if d != directory]
            if not others:
                continue
            total += 1
            majority = (verify_differential(others, entry_point, [value])
                        if len(others) > 1 else None)
            against = verify_differential([module, others[0]], entry_point,
                                          [value])
            if against.verdict == "PASS":
                agreements += 1
            elif majority is not None and majority.verdict != "PASS":
                # The peers do not agree with each other either, so there is
                # no majority to dissent FROM. This is an absence of evidence
                # and must never read as agreement.
                undecided += 1
            elif against.verdict == "UNVERIFIED":
                undecided += 1
            else:
                dissents += 1
        scores.append(AttemptScore(
            attempt=str(directory), module=module,
            majority_agreements=agreements, dissents=dissents,
            undecided=undecided, total=total))

    ranked = sorted(scores, key=lambda s: (-s.majority_agreements, s.dissents,
                                           s.undecided, str(s.attempt)))
    retained = ranked[0].attempt if ranked else ""
    return RatchetReport(
        entry_point=entry_point, inputs_harvested=len(harvested),
        scores=tuple(scores), retained=retained,
        notes=("inputs harvested from generated tests; expected values ignored",
               "retention prefers the earliest attempt at the best score, so a "
               "later regression cannot displace an earlier solution"))


def self_test() -> dict:
    """Offline proof that the ratchet keeps the correct attempt."""
    import tempfile

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

    with tempfile.TemporaryDirectory() as root:
        base = Path(root)
        for name, source in (("attempt-1", good), ("attempt-2", good),
                             ("attempt-3", broken)):
            directory = base / name
            directory.mkdir()
            (directory / "mod.py").write_text(source, encoding="utf-8")
            (directory / "test_mod.py").write_text(tests, encoding="utf-8")

        entry = discover_entry_point(str(base / "attempt-1" / "mod.py"))
        check("entry_point_discovered_without_importing", entry == "parse", entry)

        harvested = harvest_inputs(str(base / "attempt-1" / "test_mod.py"),
                                   "parse")
        check("inputs_harvested_from_tests",
              set(harvested) == {"PT30S", "PT1M", "P1D"}, str(harvested))

        source = (base / "attempt-1" / "test_mod.py").read_text(encoding="utf-8")
        check("wrong_expected_values_are_never_read",
              "99999" in source and 99999 not in harvested)

        report = rank_attempts([str(base / "attempt-1"),
                                str(base / "attempt-2"),
                                str(base / "attempt-3")])
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

        single = rank_attempts([str(base / "attempt-1")])
        check("one_attempt_cannot_be_ranked", single.retained == "",
              single.retained)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

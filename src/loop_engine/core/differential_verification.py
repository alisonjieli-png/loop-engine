"""Verify a generated artifact without trusting model-authored expected values.

The generated-project path grades an artifact against tests the same model
wrote in the same run.  Measured on 2026-09-05 (run
``adaptive-1fcd0362ddf7eab66ab7fc43``): the model emitted a *correct*
ISO-8601 parser and *incorrect* expected constants, then diagnosed the correct
parser as broken and scheduled it for repair.  Six of eight of its constants
were right; the two wrong ones were exactly the durations combining a date part
with a time part.

The asymmetry is the point.  Writing code delegates arithmetic to the
interpreter; writing an expected constant bakes in the model's own mental
arithmetic.  Self-grading therefore pits the model's weakest faculty against
its strongest and lets the weak one adjudicate.

Two oracles here avoid constants entirely:

``differential``
    Run two independently produced implementations over the same inputs and
    compare.  Two implementations agreeing on an input is evidence; a single
    implementation agreeing with a remembered number is not.  A wrong constant
    cannot corrupt this because no constant is consulted.

``metamorphic``
    Assert relations that hold by construction — ``f("PT60S") == f("PT1M")``,
    ``f(a + b) == f(a) + f(b)`` — rather than absolute values.  A relation is
    checkable without knowing any answer.

Both report ``UNVERIFIED`` rather than ``PASS`` when they cannot decide.  An
oracle that cannot run is not a passing oracle.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

#: An oracle that cannot decide must not report success.
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")


@dataclass(frozen=True)
class Divergence:
    """One input on which the implementations disagreed."""

    argument: str
    outcomes: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"argument": self.argument, "outcomes": list(self.outcomes)}


@dataclass(frozen=True)
class ConstraintLikeResult:
    """Verdict of an oracle that judges one implementation on its own."""

    oracle: str
    verdict: str
    violations: tuple = ()
    detail: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "oracle_result/v1", "oracle": self.oracle,
                "verdict": self.verdict, "violations": list(self.violations),
                "detail": self.detail}


@dataclass(frozen=True)
class VerificationReport:
    record_type: str = "differential_verification/v1"
    verdict: str = "UNVERIFIED"
    oracle: str = ""
    entry_point: str = ""
    checked: int = 0
    agreed: int = 0
    divergences: tuple[Divergence, ...] = ()
    errors: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "verdict": self.verdict,
            "oracle": self.oracle,
            "entry_point": self.entry_point,
            "checked": self.checked,
            "agreed": self.agreed,
            "divergences": [d.to_dict() for d in self.divergences],
            "errors": list(self.errors),
            "notes": list(self.notes),
        }


#: Generated code is executed in a separate process, never imported into the
#: engine.  Importing a model-authored module would run it with the engine's
#: own privileges, which contradicts the sandbox posture the rest of this
#: package maintains.  A separate process also contains a hang behind a timeout
#: and a crash behind a return code.
_DRIVER = """
import json, sys, importlib.util
path, entry = sys.argv[1], sys.argv[2]
arguments = json.loads(sys.argv[3])
spec = importlib.util.spec_from_file_location("_candidate", path)
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, __import__("os").path.dirname(path))
try:
    spec.loader.exec_module(module)
except Exception as exc:
    print(json.dumps({"load_error": type(exc).__name__ + ": " + str(exc)[:200]}))
    raise SystemExit(0)
function = getattr(module, entry, None)
if not callable(function):
    print(json.dumps({"load_error": "no callable " + entry}))
    raise SystemExit(0)
import tempfile as _tempfile
outcomes = []
for argument in arguments:
    scratch = None
    try:
        # A harvested fixture is file CONTENT for an API that takes a PATH.
        # Materialise it here so both implementations read byte-identical
        # input; comparing a parser that reads files is otherwise impossible.
        if isinstance(argument, dict) and "__fixture_content__" in argument:
            handle, scratch = _tempfile.mkstemp(suffix=".fixture")
            with __import__("os").fdopen(handle, "w", encoding="utf-8") as fh:
                fh.write(argument["__fixture_content__"])
            argument = scratch
        if isinstance(argument, dict) and "__argv__" in argument:
            argv = list(argument["__argv__"])
            sink = argument.get("__sink__", -1)
            if sink >= 0:
                # Compare the ARTIFACT, not the return value: a renderer
                # returns None and expresses everything through the file it
                # writes. Two implementations agree when their output bytes
                # agree.
                handle, destination = _tempfile.mkstemp(suffix=".sink")
                __import__("os").close(handle)
                argv[sink] = destination
                function(*argv)
                try:
                    with open(destination, "rb") as fh:
                        body = fh.read()
                finally:
                    try:
                        __import__("os").unlink(destination)
                    except OSError:
                        pass
                outcomes.append("wrote:" + __import__("hashlib").sha256(
                    body).hexdigest())
            else:
                outcomes.append("value:" + json.dumps(
                    function(*argv), sort_keys=True, default=repr))
        else:
            outcomes.append("value:" + json.dumps(function(argument),
                                                  sort_keys=True, default=repr))
    except Exception as exc:
        outcomes.append("raises:" + type(exc).__name__)
    finally:
        if scratch:
            try:
                __import__("os").unlink(scratch)
            except OSError:
                pass
print(json.dumps({"outcomes": outcomes}))
"""


def _run_implementation(path, entry_point, arguments, timeout=30.0):
    """Evaluate one implementation over every argument in a separate process.

    Returns ``(outcomes, error)``.  An exception raised by the implementation
    is an *outcome*, not an error: an implementation that raises where another
    returns has diverged, and that is exactly what the oracle must see.  An
    error means the oracle could not run at all.
    """
    resolved = Path(path).resolve()
    if not resolved.is_file():
        return None, f"not a file: {resolved}"
    with tempfile.TemporaryDirectory() as scratch:
        driver = Path(scratch) / "_driver.py"
        driver.write_text(_DRIVER, encoding="utf-8")
        try:
            finished = subprocess.run(
                [sys.executable, str(driver), str(resolved), entry_point,
                 json.dumps(list(arguments))],
                capture_output=True, text=True, timeout=timeout, shell=False)
        except subprocess.TimeoutExpired:
            return None, f"implementation exceeded {timeout}s: {resolved.name}"
    if finished.returncode != 0:
        return None, (f"driver failed for {resolved.name}: "
                      f"{(finished.stderr or '').strip()[:200]}")
    try:
        payload = json.loads(finished.stdout.strip() or "{}")
    except ValueError:
        return None, f"driver produced no readable result for {resolved.name}"
    if "load_error" in payload:
        return None, f"{resolved.name}: {payload['load_error']}"
    return tuple(payload.get("outcomes") or ()), None


def verify_differential(
        implementations: "list[str] | tuple[str, ...]",
        entry_point: str,
        arguments: "list | tuple") -> VerificationReport:
    """Compare two or more implementations over the same arguments.

    No expected value is supplied by anyone.  Agreement across independently
    produced implementations is the evidence.
    """
    if len(tuple(implementations)) < 2:
        return VerificationReport(
            verdict="UNVERIFIED", oracle="differential",
            entry_point=entry_point,
            errors=("differential verification needs at least two "
                    "implementations",))
    if not tuple(arguments):
        return VerificationReport(
            verdict="UNVERIFIED", oracle="differential",
            entry_point=entry_point,
            errors=("no arguments supplied; an oracle with no inputs "
                    "decides nothing",))
    collected = []
    for implementation in implementations:
        outcomes, error = _run_implementation(
            implementation, entry_point, list(arguments))
        if error is not None:
            return VerificationReport(
                verdict="UNVERIFIED", oracle="differential",
                entry_point=entry_point, errors=(error,))
        collected.append(outcomes)
    divergences: list[Divergence] = []
    agreed = 0
    # A driver whose output was truncated returns fewer outcomes than it was
    # given arguments, and indexing past it raised IndexError -- which the
    # caller reported as "ranking unavailable", silently discarding real
    # agreement evidence (measured 2026-09-06, unit 04 of a 6-unit solve).
    # Compare only the prefix every implementation actually produced, and say
    # so rather than pretending the whole set was checked.
    usable = min((len(o) for o in collected), default=0)
    if usable < len(list(arguments)):
        divergences.append(Divergence(
            "(truncated)",
            (f"only {usable} of {len(list(arguments))} arguments produced an "
             f"outcome in every implementation",)))
    for index, argument in enumerate(list(arguments)[:usable]):
        row = tuple(o[index] for o in collected)
        if len(set(row)) == 1:
            agreed += 1
        else:
            divergences.append(Divergence(repr(argument), row))
    return VerificationReport(
        verdict="PASS" if not divergences else "FAIL",
        oracle="differential", entry_point=entry_point,
        checked=len(tuple(arguments)), agreed=agreed,
        divergences=tuple(divergences),
        notes=(f"{len(collected)} independent implementations compared; "
               "no expected values consulted, each in its own process",))


#: Scaling is measured on an ENGINE-CHOSEN input distribution, because a model
#: that picks its own benchmark picks a benign one.  Measured 2026-09-06 on a
#: real refactor ticket ("this is O(n^2) and times out on our 200k-row export;
#: make it linear"): the model shipped `if item in seen_twice` over a LIST,
#: which is linear in items but quadratic in the number of distinct duplicates,
#: then wrote its own timing test over randint(0, 1000) -- capping distinct
#: duplicates at a thousand, where the list scan is bounded and the ratio is
#: 9.3x. Its assertion was honest and passed. On randint(0, n/2) the same code
#: measures 1522x. The implementation was not dishonest and neither was the
#: test; the model simply chose the regime that flattered its fix, which is the
#: performance analogue of choosing a wrong expected constant.
_COMPLEXITY_DRIVER = """
import json, sys, time, random, importlib.util, os
path, entry = sys.argv[1], sys.argv[2]
sizes = json.loads(sys.argv[3]); distinct_ratio = float(sys.argv[4])
spec = importlib.util.spec_from_file_location("_candidate", path)
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(path))
try:
    spec.loader.exec_module(module)
except Exception as exc:
    print(json.dumps({"load_error": type(exc).__name__ + ": " + str(exc)[:150]}))
    raise SystemExit(0)
function = getattr(module, entry, None)
if not callable(function):
    print(json.dumps({"load_error": "no callable " + entry}))
    raise SystemExit(0)
timings = []
for size in sizes:
    random.seed(12345)
    span = max(1, int(size * distinct_ratio))
    data = [random.randint(0, span) for _ in range(size)]
    best = None
    # CPU time of THIS process, not wall clock. A complexity oracle timed
    # on the wall measures the machine's load as much as the algorithm:
    # this check failed at "10x input cost 30.6x time" on a correct linear
    # implementation while the host sat at load average 18, and passed
    # 13/13 alone minutes later. An overnight verdict that changes with
    # what else is running is not a verdict.
    for _ in range(5):
        began = time.process_time()
        try:
            function(list(data))
        except Exception as exc:
            print(json.dumps({"call_error": type(exc).__name__ + ": " + str(exc)[:120]}))
            raise SystemExit(0)
        elapsed = time.process_time() - began
        best = elapsed if best is None else min(best, elapsed)
    timings.append({"size": size, "seconds": best})
print(json.dumps({"timings": timings}))
"""


def verify_complexity(
        implementation: str, entry_point: str, *,
        sizes: "tuple[int, ...]" = (4000, 40000),
        distinct_ratio: float = 0.5,
        maximum_ratio: float = 20.0,
        timeout: float = 180.0) -> ConstraintLikeResult:
    """Measure scaling on inputs the ENGINE chooses, not the model.

    ``distinct_ratio`` is the share of the input that is distinct, and it is
    the parameter a model's own benchmark quietly sets low.  The default of 0.5
    is adversarial on purpose: it is the regime a "times out on our 200k-row
    export" ticket actually describes.
    """
    resolved = Path(implementation).resolve()
    if not resolved.is_file():
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED", (f"not a file: {resolved}",))
    with tempfile.TemporaryDirectory() as scratch:
        driver = Path(scratch) / "_complexity.py"
        driver.write_text(_COMPLEXITY_DRIVER, encoding="utf-8")
        try:
            finished = subprocess.run(
                [sys.executable, str(driver), str(resolved), entry_point,
                 json.dumps(list(sizes)), str(distinct_ratio)],
                capture_output=True, text=True, timeout=timeout, shell=False)
        except subprocess.TimeoutExpired:
            # Exceeding the clock at these sizes IS the finding.
            return ConstraintLikeResult(
                "complexity", "FAIL",
                (f"did not finish {max(sizes)} items within {timeout}s",))
    try:
        payload = json.loads((finished.stdout or "{}").strip() or "{}")
    except ValueError:
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED", ("driver produced no readable result",))
    if "load_error" in payload or "call_error" in payload:
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED",
            (payload.get("load_error") or payload["call_error"],))
    timings = payload.get("timings") or []
    if len(timings) < 2 or timings[0]["seconds"] <= 0:
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED", ("timings too small to compare",))
    growth = timings[-1]["size"] / timings[0]["size"]
    ratio = timings[-1]["seconds"] / timings[0]["seconds"]
    detail = (f"{growth:.0f}x input cost {ratio:.1f}x time at "
              f"distinct_ratio={distinct_ratio}")
    if ratio <= maximum_ratio:
        return ConstraintLikeResult("complexity", "PASS", (), detail)
    return ConstraintLikeResult(
        "complexity", "FAIL",
        (f"{detail}; expected at most {maximum_ratio:.0f}x",), detail)


def verify_metamorphic(
        implementation: str,
        entry_point: str,
        relations: "list[tuple[str, str]] | tuple") -> VerificationReport:
    """Assert relations between calls rather than absolute values.

    Each relation is a pair of argument tuples whose results must be equal:
    ``(("PT60S",), ("PT1M",))`` asserts one minute is sixty seconds without
    anyone knowing that it is 60.
    """
    if not tuple(relations):
        return VerificationReport(
            verdict="UNVERIFIED", oracle="metamorphic",
            entry_point=entry_point,
            errors=("no relations supplied",))
    flattened = [side for pair in relations for side in pair]
    outcomes, error = _run_implementation(
        implementation, entry_point, flattened)
    if error is not None:
        return VerificationReport(
            verdict="UNVERIFIED", oracle="metamorphic",
            entry_point=entry_point, errors=(error,))
    divergences: list[Divergence] = []
    agreed = 0
    for index, (left, right) in enumerate(relations):
        left_out, right_out = outcomes[2 * index], outcomes[2 * index + 1]
        if left_out == right_out:
            agreed += 1
        else:
            divergences.append(
                Divergence(f"{left!r} vs {right!r}", (left_out, right_out)))
    return VerificationReport(
        verdict="PASS" if not divergences else "FAIL",
        oracle="metamorphic", entry_point=entry_point,
        checked=len(tuple(relations)), agreed=agreed,
        divergences=tuple(divergences),
        notes=("relations checked without any expected value",))


def self_test() -> dict:
    """Offline proof that both oracles decide correctly."""
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    good = ("def parse(text):\n"
            "    if not text.startswith('P'):\n"
            "        raise ValueError('bad')\n"
            "    return {'P1D': 86400, 'PT24H': 86400, 'PT1M': 60,\n"
            "            'PT60S': 60}[text]\n")
    # Same behaviour, different source — an independent implementation.
    other = ("def parse(text):\n"
             "    if text[:1] != 'P':\n"
             "        raise ValueError('bad')\n"
             "    units = {'P1D': 24 * 60 * 60, 'PT24H': 24 * 3600,\n"
             "             'PT1M': 60, 'PT60S': 60}\n"
             "    return units[text]\n")
    # Diverges on exactly one input.
    broken = ("def parse(text):\n"
              "    if not text.startswith('P'):\n"
              "        raise ValueError('bad')\n"
              "    return {'P1D': 86400, 'PT24H': 90000, 'PT1M': 60,\n"
              "            'PT60S': 60}[text]\n")

    with tempfile.TemporaryDirectory() as root:
        base = Path(root)
        a, b, c = base / "a.py", base / "b.py", base / "c.py"
        a.write_text(good, encoding="utf-8")
        b.write_text(other, encoding="utf-8")
        c.write_text(broken, encoding="utf-8")
        args = ["P1D", "PT24H", "PT1M", "PT60S"]

        agree = verify_differential([str(a), str(b)], "parse", args)
        check("agreeing_implementations_pass", agree.verdict == "PASS"
              and agree.agreed == 4, agree.verdict)

        disagree = verify_differential([str(a), str(c)], "parse", args)
        check("one_diverging_input_is_located",
              disagree.verdict == "FAIL" and len(disagree.divergences) == 1
              and "PT24H" in disagree.divergences[0].argument,
              str(disagree.divergences))

        raising = verify_differential([str(a), str(b)], "parse", ["nope"])
        check("identical_exceptions_are_agreement",
              raising.verdict == "PASS", raising.verdict)

        single = verify_differential([str(a)], "parse", args)
        check("one_implementation_cannot_decide",
              single.verdict == "UNVERIFIED", single.verdict)

        empty = verify_differential([str(a), str(b)], "parse", [])
        check("no_arguments_cannot_decide", empty.verdict == "UNVERIFIED",
              empty.verdict)

        missing = verify_differential([str(a), str(b)], "absent", args)
        check("missing_entry_point_is_unverified_not_failed",
              missing.verdict == "UNVERIFIED", missing.verdict)

        relations = [("PT60S", "PT1M"), ("PT24H", "P1D")]
        meta_ok = verify_metamorphic(str(a), "parse", relations)
        check("relations_hold_without_expected_values",
              meta_ok.verdict == "PASS" and meta_ok.agreed == 2,
              meta_ok.verdict)

        meta_bad = verify_metamorphic(str(c), "parse", relations)
        check("broken_implementation_breaks_a_relation",
              meta_bad.verdict == "FAIL" and len(meta_bad.divergences) == 1,
              str(meta_bad.divergences))

        check("report_serializes",
              agree.to_dict()["record_type"] == "differential_verification/v1")

        # Complexity is measured on engine-chosen inputs, so a quadratic
        # implementation cannot pass by being benchmarked on a benign one.
        quadratic = base / "quad.py"
        quadratic.write_text(
            "def dup(items):\n"
            "    out = []\n"
            "    for i, x in enumerate(items):\n"
            "        if x in items[:i] and x not in out:\n"
            "            out.append(x)\n"
            "    return out\n", encoding="utf-8")
        linear = base / "lin.py"
        linear.write_text(
            "def dup(items):\n"
            "    seen = set(); twice = set(); out = []\n"
            "    for x in items:\n"
            "        if x in seen:\n"
            "            if x not in twice:\n"
            "                twice.add(x); out.append(x)\n"
            "        else:\n"
            "            seen.add(x)\n"
            "    return out\n", encoding="utf-8")
        slow = verify_complexity(str(quadratic), "dup", sizes=(500, 5000))
        check("a_quadratic_implementation_is_caught",
              slow.verdict == "FAIL", slow.detail)
        fast = verify_complexity(str(linear), "dup", sizes=(500, 5000))
        check("a_linear_implementation_passes",
              fast.verdict == "PASS", fast.detail)
        check("a_missing_entry_point_is_unverified_not_failed",
              verify_complexity(str(linear), "absent",
                                sizes=(500, 5000)).verdict == "UNVERIFIED")
        check("oracle_result_serializes",
              fast.to_dict()["record_type"] == "oracle_result/v1")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

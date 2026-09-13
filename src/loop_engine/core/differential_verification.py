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

CONTAINMENT (2026-09-13).  Every oracle runs model-authored code, so the
process it runs in is built from nothing: the working directory is the
implementation's own directory (or an explicit ``workspace``), the environment
is an allowlist of the same names the OpenCode step session inherits, the
interpreter runs ``-I`` (no user site, no ``PYTHON*`` variables), arguments
travel over stdin rather than argv (so a 200 KB fixture cannot fail the exec
with E2BIG), output files are capped, and a driver that cannot start is an
``UNVERIFIED`` report with the reason rather than an exception.  The
model-reachable capability additionally needs an explicit permission
(``allow_host_verification`` on the run's services); without it the operation
executes nothing and says so.
"""
from __future__ import annotations

import json
import os
import subprocess
import signal
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .differential_drivers import (
    COMPLEXITY_DRIVER,
    DIFFERENTIAL_DRIVER,
    DRIVER_FILE_SIZE_LIMIT,
    HOST_EXECUTION_REFUSED,
    OUTPUT_CAPTURE_BYTES,
    TIMING_RESOLUTION_FLOOR_SECONDS,
    DriverRun,
    allowlisted_environment,
    inheritable_environment_names,
)

#: An oracle that cannot decide must not report success.
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")

#: The programs the driver process runs live in differential_drivers; these names keep
#: the oracle module's own vocabulary.
_DRIVER = DIFFERENTIAL_DRIVER
_COMPLEXITY_DRIVER = COMPLEXITY_DRIVER


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
    #: Agreements on a returned value or written artifact.  Implementations
    #: that all raise the same exception on an input agree -- and that is
    #: counted in ``agreed`` -- but they have not shown they can do the work,
    #: so unanimous ``raises:`` outcomes must not read as evidence of it.
    agreed_on_values: int = 0

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "verdict": self.verdict,
            "oracle": self.oracle,
            "entry_point": self.entry_point,
            "checked": self.checked,
            "agreed": self.agreed,
            "agreed_on_values": self.agreed_on_values,
            "divergences": [d.to_dict() for d in self.divergences],
            "errors": list(self.errors),
            "notes": list(self.notes),
        }


def _spawn_driver(source: str, request: dict, *, cwd: Path,
                  timeout: float) -> DriverRun:
    """Run one driver in a contained process and collect its result file.

    Containment: ``cwd`` is the implementation's directory (or the caller's
    workspace), the environment is an allowlist built from nothing, the
    interpreter runs isolated (``-I``), the request travels over stdin, stdout
    and stderr go to scratch files of which at most OUTPUT_CAPTURE_BYTES are
    read back, and the driver process caps its own file sizes.  Failing to start is a
    result, not an exception.
    """
    with tempfile.TemporaryDirectory() as scratch:
        base = Path(scratch)
        driver = base / "_driver.py"
        driver.write_text(source, encoding="utf-8")
        result_path = base / "_result.json"
        out_path, err_path = base / "_stdout.bin", base / "_stderr.bin"
        body = dict(request, result_path=str(result_path),
                    file_size_limit=DRIVER_FILE_SIZE_LIMIT)
        try:
            with open(out_path, "wb") as out, open(err_path, "wb") as err:
                process = subprocess.Popen(
                    [sys.executable, "-I", str(driver)],
                    stdin=subprocess.PIPE,
                    stdout=out, stderr=err, cwd=str(cwd),
                    env=allowlisted_environment(),
                    shell=False, start_new_session=True)
                try:
                    process.communicate(json.dumps(body).encode("utf-8"),
                                        timeout=timeout)
                finally:
                    # Only the process group we created is ours to stop.
                    # Descendants cannot outlive a timed-out driver or hold
                    # its output files open after a successful return.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                finished = process
        except subprocess.TimeoutExpired:
            return DriverRun(None, f"implementation exceeded {timeout}s",
                             timed_out=True)
        except (OSError, ValueError) as exc:
            # E2BIG, a missing interpreter, an unusable cwd: the oracle could
            # not run, and that is a reason to report, never a crash.
            return DriverRun(None, f"could not start the driver: {exc}")
        try:
            stdout_bytes = out_path.stat().st_size
            with err_path.open("rb") as stream:
                stderr_head = stream.read(OUTPUT_CAPTURE_BYTES).decode(
                    "utf-8", errors="replace")
        except OSError:
            stdout_bytes, stderr_head = 0, ""
        if finished.returncode != 0:
            return DriverRun(None, (f"driver failed (exit {finished.returncode}): "
                                    f"{stderr_head.strip()[:200]}"))
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return DriverRun(None, "driver produced no readable result")
        if not isinstance(payload, dict):
            return DriverRun(None, "driver produced no readable result")
        return DriverRun(payload, None, stdout_bytes=stdout_bytes)


def _run_implementation(path, entry_point, arguments, timeout=30.0, *,
                        workspace=None, host_execution_permitted=False):
    """Evaluate one implementation over every argument in a separate process.

    Returns ``(outcomes, error)``.  An exception raised by the implementation
    is an *outcome*, not an error: an implementation that raises where another
    returns has diverged, and that is exactly what the oracle must see.  An
    error means the oracle could not run at all.
    """
    resolved = Path(path).resolve()
    if host_execution_permitted is not True:
        return None, f"{HOST_EXECUTION_REFUSED}: {resolved.name} was not executed"
    if not resolved.is_file():
        return None, f"not a file: {resolved}"
    cwd = Path(workspace) if workspace else resolved.parent
    run = _spawn_driver(
        _DRIVER, {"path": str(resolved), "entry": entry_point,
                  "arguments": list(arguments)}, cwd=cwd, timeout=timeout)
    if run.error is not None:
        return None, f"{run.error}: {resolved.name}"
    if "load_error" in run.payload:
        return None, f"{resolved.name}: {run.payload['load_error']}"
    return tuple(run.payload.get("outcomes") or ()), None


def collect_outcomes(implementation, entry_point, arguments, *, timeout=30.0,
                     workspace=None, host_execution_permitted=False) -> tuple:
    """Public form of the per-implementation run, for callers that compare
    outcome vectors themselves (the solution ratchet's majority vote)."""
    return _run_implementation(
        implementation, entry_point, list(arguments), timeout,
        workspace=workspace, host_execution_permitted=host_execution_permitted)


def _containment_note(count: int) -> str:
    return (f"{count} independent implementations compared; no expected "
            "values consulted, each in its own isolated process (cwd = its "
            "own directory, allowlisted environment, python -I)")


def _refused(oracle: str, entry_point: str) -> VerificationReport:
    return VerificationReport(
        verdict="UNVERIFIED", oracle=oracle, entry_point=entry_point,
        errors=(f"{HOST_EXECUTION_REFUSED}; nothing was executed",))


def verify_differential(
        implementations: "list[str] | tuple[str, ...]",
        entry_point: str,
        arguments: "list | tuple", *,
        host_execution_permitted: bool = False,
        workspace: "str | None" = None,
        timeout: float = 30.0) -> VerificationReport:
    """Compare two or more implementations over the same arguments.

    No expected value is supplied by anyone.  Agreement across independently
    produced implementations is the evidence.
    """
    if host_execution_permitted is not True:
        return _refused("differential", entry_point)
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
            implementation, entry_point, list(arguments), timeout,
            workspace=workspace, host_execution_permitted=True)
        if error is not None:
            return VerificationReport(
                verdict="UNVERIFIED", oracle="differential",
                entry_point=entry_point, errors=(error,))
        collected.append(outcomes)
    divergences: list[Divergence] = []
    agreed = agreed_on_values = 0
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
            if not row[0].startswith("raises:"):
                agreed_on_values += 1
        else:
            divergences.append(Divergence(repr(argument), row))
    return VerificationReport(
        verdict="PASS" if not divergences else "FAIL",
        oracle="differential", entry_point=entry_point,
        checked=len(tuple(arguments)), agreed=agreed,
        agreed_on_values=agreed_on_values,
        divergences=tuple(divergences),
        notes=(_containment_note(len(collected)),))


def verify_complexity(
        implementation: str, entry_point: str, *,
        sizes: "tuple[int, ...]" = (4000, 40000),
        distinct_ratio: float = 0.5,
        maximum_ratio: float = 20.0,
        timeout: float = 180.0,
        host_execution_permitted: bool = False,
        workspace: "str | None" = None,
        resolution_floor: float = TIMING_RESOLUTION_FLOOR_SECONDS,
        ) -> ConstraintLikeResult:
    """Measure scaling on inputs the ENGINE chooses, not the model.

    ``distinct_ratio`` is the share of the input that is distinct, and it is
    the parameter a model's own benchmark quietly sets low.  The default of 0.5
    is adversarial on purpose: it is the regime a "times out on our 200k-row
    export" ticket actually describes.
    """
    if host_execution_permitted is not True:
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED",
            (f"{HOST_EXECUTION_REFUSED}; nothing was executed",))
    resolved = Path(implementation).resolve()
    if not resolved.is_file():
        return ConstraintLikeResult(
            "complexity", "UNVERIFIED", (f"not a file: {resolved}",))
    run = _spawn_driver(
        _COMPLEXITY_DRIVER,
        {"path": str(resolved), "entry": entry_point, "sizes": list(sizes),
         "distinct_ratio": distinct_ratio,
         "resolution_floor": float(resolution_floor)},
        cwd=Path(workspace) if workspace else resolved.parent,
        timeout=timeout)
    if run.timed_out:
        # Exceeding the clock at these sizes IS the finding.
        return ConstraintLikeResult(
            "complexity", "FAIL",
            (f"did not finish {max(sizes)} items within {timeout}s",))
    if run.error is not None:
        return ConstraintLikeResult("complexity", "UNVERIFIED", (run.error,))
    payload = run.payload
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
    batched = max(int(t.get("repetitions") or 1) for t in timings)
    if batched > 1:
        detail += (f" (small sizes batched x{batched} to clear the clock's "
                   "resolution)")
    if ratio <= maximum_ratio:
        return ConstraintLikeResult("complexity", "PASS", (), detail)
    return ConstraintLikeResult(
        "complexity", "FAIL",
        (f"{detail}; expected at most {maximum_ratio:.0f}x",), detail)


def verify_metamorphic(
        implementation: str,
        entry_point: str,
        relations: "list[tuple[str, str]] | tuple", *,
        host_execution_permitted: bool = False,
        workspace: "str | None" = None,
        timeout: float = 30.0) -> VerificationReport:
    """Assert relations between calls rather than absolute values.

    Each relation is a pair of argument tuples whose results must be equal:
    ``(("PT60S",), ("PT1M",))`` asserts one minute is sixty seconds without
    anyone knowing that it is 60.
    """
    if host_execution_permitted is not True:
        return _refused("metamorphic", entry_point)
    if not tuple(relations):
        return VerificationReport(
            verdict="UNVERIFIED", oracle="metamorphic",
            entry_point=entry_point,
            errors=("no relations supplied",))
    flattened = [side for pair in relations for side in pair]
    outcomes, error = _run_implementation(
        implementation, entry_point, flattened, timeout, workspace=workspace,
        host_execution_permitted=True)
    if error is not None:
        return VerificationReport(
            verdict="UNVERIFIED", oracle="metamorphic",
            entry_point=entry_point, errors=(error,))
    divergences: list[Divergence] = []
    agreed = agreed_on_values = 0
    for index, (left, right) in enumerate(relations):
        if 2 * index + 1 >= len(outcomes):
            divergences.append(Divergence(
                f"{left!r} vs {right!r}", ("no outcome produced",)))
            continue
        left_out, right_out = outcomes[2 * index], outcomes[2 * index + 1]
        if left_out == right_out:
            agreed += 1
            if not left_out.startswith("raises:"):
                agreed_on_values += 1
        else:
            divergences.append(
                Divergence(f"{left!r} vs {right!r}", (left_out, right_out)))
    return VerificationReport(
        verdict="PASS" if not divergences else "FAIL",
        oracle="metamorphic", entry_point=entry_point,
        checked=len(tuple(relations)), agreed=agreed,
        agreed_on_values=agreed_on_values,
        divergences=tuple(divergences),
        notes=("relations checked without any expected value, in an "
               "isolated process",))


def differential_verification_operation(arguments, services) -> dict:
    """Run one oracle for the Practitioner's ``core.verify.differential``
    capability without consulting model-authored values.

    Two oracles, neither of which needs an expected constant: ``differential``
    compares independently produced implementations against each other, and
    ``metamorphic`` asserts relations between calls. Both exist because the
    generated-project path grades an artifact against tests the same model
    wrote, which was measured inverting on 2026-09-05: correct code condemned
    by wrong constants. Every path is confined to the run's own workspace.

    This is the model-reachable path, so executing anything needs an explicit
    permission: the run's services must expose a truthy
    ``allow_host_verification``.  Without it the paths are still checked but
    nothing runs, and the report says exactly that.
    """
    oracle = str(arguments.get("oracle") or "differential")
    entry_point = str(arguments.get("entry_point") or "")
    if not entry_point:
        return {"record_type": "differential_verification/v1",
                "verdict": "UNVERIFIED",
                "errors": ["entry_point is required"]}
    root = Path(services.workspace_base) if getattr(
        services, "workspace_base", None) else Path(".")
    permitted = getattr(services, "allow_host_verification", False) is True

    def _confined(candidate: str) -> str:
        """Keep every path inside the run's own workspace."""
        resolved = (root / candidate).resolve() if not Path(
            candidate).is_absolute() else Path(candidate).resolve()
        if root.resolve() not in resolved.parents and resolved != root.resolve():
            raise PermissionError(f"path outside workspace: {candidate}")
        return str(resolved)

    try:
        if oracle == "metamorphic":
            relations = [tuple(r) for r in (arguments.get("relations") or [])
                         if isinstance(r, (list, tuple)) and len(r) == 2]
            target = _confined(str(arguments.get("implementation") or ""))
            if not permitted:
                return _refused_operation(oracle, entry_point)
            report = verify_metamorphic(
                target, entry_point, relations,
                host_execution_permitted=permitted)
        else:
            paths = [_confined(str(item)) for item
                     in (arguments.get("implementations") or [])]
            if not permitted:
                return _refused_operation(oracle, entry_point)
            report = verify_differential(
                paths, entry_point, list(arguments.get("arguments") or []),
                host_execution_permitted=permitted)
    except (PermissionError, OSError) as exc:
        return {"record_type": "differential_verification/v1",
                "verdict": "UNVERIFIED", "errors": [str(exc)],
                "host_execution_permitted": permitted}
    payload = report.to_dict()
    payload["host_execution_permitted"] = permitted
    return payload


def _refused_operation(oracle: str, entry_point: str) -> dict:
    return {
        "record_type": "differential_verification/v1",
        "verdict": "UNVERIFIED", "oracle": oracle, "entry_point": entry_point,
        "errors": [f"{HOST_EXECUTION_REFUSED}: the run's services do not "
                   "grant allow_host_verification, so model-supplied code "
                   "was not executed"],
        "host_execution_permitted": False,
    }


def self_test() -> dict:
    """Offline proof that both oracles decide correctly and run contained."""
    from types import SimpleNamespace
    from functools import partial

    # Host permission is explicit for these locally authored fixtures.
    verify_differential = partial(globals()["verify_differential"],
                                  host_execution_permitted=True)
    verify_complexity = partial(globals()["verify_complexity"],
                                host_execution_permitted=True)
    verify_metamorphic = partial(globals()["verify_metamorphic"],
                                 host_execution_permitted=True)

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
        check("raises_agreements_are_not_value_agreements",
              raising.agreed == 1 and raising.agreed_on_values == 0
              and agree.agreed_on_values == 4
              and agree.to_dict()["agreed_on_values"] == 4,
              f"{raising.agreed_on_values} of {raising.agreed}")

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

        # H3: the driver process is built from nothing.  Generated code sees
        # its own directory as cwd, an allowlisted environment, and an
        # isolated interpreter -- never the engine's cwd or secrets.
        secret_name = "_DIFFERENTIAL_SELF_TEST_SECRET"
        os.environ[secret_name] = "must-not-leak"
        peek = base / "peek.py"
        peek.write_text(
            "import os, sys\n"
            "def peek(_):\n"
            "    return [os.getcwd(), os.environ.get("
            f"{secret_name!r}, 'absent'), sys.flags.isolated,\n"
            "            'PYTHONPATH' in os.environ]\n", encoding="utf-8")
        try:
            outcomes, error = _run_implementation(
                str(peek), "peek", ["x"], host_execution_permitted=True)
        finally:
            os.environ.pop(secret_name, None)
        seen = json.loads(outcomes[0][len("value:"):]) if outcomes else []
        check("driver_runs_in_the_implementation_directory",
              error is None and seen and Path(seen[0]).resolve()
              == base.resolve(), str(seen))
        check("driver_environment_is_allowlisted_from_nothing",
              error is None and seen and seen[1] == "absent"
              and seen[3] is False, str(seen))
        check("driver_runs_python_isolated",
              error is None and seen and seen[2] == 1, str(seen))
        check("inheritable_names_match_the_step_session_allowlist",
              set(inheritable_environment_names())
              >= {"PATH", "HOME", "TMPDIR"},
              str(inheritable_environment_names()))

        # L4 / E2BIG: a fixture far larger than one argv element may carry.
        sizer = base / "sz.py"
        sizer.write_text("import os\ndef size(p):\n    return os.path.getsize(p)\n",
                         encoding="utf-8")
        sizer2 = base / "sz2.py"
        sizer2.write_text("def size(p):\n    return len(open(p, 'rb').read())\n",
                          encoding="utf-8")
        big = [{"__fixture_content__": "r,v\n" * 80000}]      # ~320 KB
        wide = verify_differential([str(sizer), str(sizer2)], "size", big)
        check("large_arguments_travel_by_stdin_not_argv",
              wide.verdict == "PASS" and wide.agreed_on_values == 1,
              f"{wide.verdict} {list(wide.errors)}")

        # A driver that cannot start is a report, never an exception.
        nowhere = verify_differential([str(a), str(b)], "parse", args,
                                      workspace=str(base / "missing"))
        check("unstartable_driver_is_unverified_not_an_exception",
              nowhere.verdict == "UNVERIFIED" and nowhere.errors
              and "could not start the driver" in nowhere.errors[0],
              str(nowhere.errors))

        # Output is bounded and out of band: junk on stdout cannot corrupt
        # the result, and an implementation that exits is an outcome.
        noisy = base / "noisy.py"
        noisy.write_text("import sys\nsys.stdout.write('x' * 300000)\n" + good,
                         encoding="utf-8")
        loud = verify_differential([str(noisy), str(b)], "parse", args)
        check("noisy_stdout_does_not_corrupt_the_result",
              loud.verdict == "PASS" and loud.agreed == 4,
              f"{loud.verdict} {list(loud.errors)}")
        exiting = base / "exiting.py"
        exiting.write_text("def parse(t):\n    raise SystemExit(0)\n",
                           encoding="utf-8")
        exited = verify_differential([str(exiting), str(a)], "parse", ["P1D"])
        check("system_exit_inside_the_implementation_is_an_outcome",
              exited.verdict == "FAIL" and exited.divergences
              and "raises:SystemExit" in exited.divergences[0].outcomes,
              str([d.to_dict() for d in exited.divergences]))

        # The explicit permission: tool callers default to permitted; the
        # model-reachable operation needs the services to say so.
        refused = verify_differential([str(a), str(b)], "parse", args,
                                      host_execution_permitted=False)
        refused_meta = verify_metamorphic(str(a), "parse", relations,
                                          host_execution_permitted=False)
        refused_cost = verify_complexity(str(a), "parse", sizes=(10, 100),
                                         host_execution_permitted=False)
        check("host_execution_refused_without_permission",
              all(r.verdict == "UNVERIFIED" for r in (refused, refused_meta,
                                                       refused_cost))
              and HOST_EXECUTION_REFUSED in refused.errors[0]
              and HOST_EXECUTION_REFUSED in refused_meta.errors[0]
              and HOST_EXECUTION_REFUSED in refused_cost.violations[0])
        request = {"entry_point": "parse", "implementations": ["a.py", "b.py"],
                   "arguments": args}
        closed = differential_verification_operation(
            request, SimpleNamespace(workspace_base=str(base)))
        check("operation_refuses_host_execution_without_services_permission",
              closed["verdict"] == "UNVERIFIED"
              and HOST_EXECUTION_REFUSED in closed["errors"][0]
              and closed["host_execution_permitted"] is False, str(closed))
        opened = differential_verification_operation(
            request, SimpleNamespace(workspace_base=str(base),
                                     allow_host_verification=True))
        check("operation_runs_with_explicit_services_permission",
              opened["verdict"] == "PASS"
              and opened["host_execution_permitted"] is True, str(opened))
        escaped = differential_verification_operation(
            {"entry_point": "parse",
             "implementations": ["a.py", str(Path(root).parent / "x.py")],
             "arguments": args},
            SimpleNamespace(workspace_base=str(base),
                            allow_host_verification=True))
        check("operation_still_confines_paths_when_permitted",
              escaped["verdict"] == "UNVERIFIED"
              and "outside workspace" in escaped["errors"][0], str(escaped))

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
        check("timings_below_clock_resolution_are_batched",
              "batched" in fast.detail, fast.detail)
        check("a_missing_entry_point_is_unverified_not_failed",
              verify_complexity(str(linear), "absent",
                                sizes=(500, 5000)).verdict == "UNVERIFIED")
        check("oracle_result_serializes",
              fast.to_dict()["record_type"] == "oracle_result/v1")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

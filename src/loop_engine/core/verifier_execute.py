"""Run the operator-declared verifier script as a mid-solve observation.

Only the explicit ``verifier_path`` on the run request ever executes:
nothing is discovered, inferred, or defaulted. The verifier runs with
its parent directory as cwd (so a task gate sees its data and the run's
solution), a bounded timeout, a minimal environment, and its own process
group, so a timeout stops every process the script started. Captured
output is bounded to a rolling tail. The exit code and output tail return
as an observation for replanning; a passing gate never accepts the task by
itself, acceptance stays with verification. This is raw-host execution,
not an untrusted-code sandbox: the script runs with the calling user's
authority on the host.
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path

VERIFIER_RECORD_TYPE = "verifier_execution/v2"
DEFAULT_TIMEOUT_SECONDS = 600.0
MAX_OUTPUT_BYTES = 8192
TAIL_LINES = 12


class VerifierError(ValueError):
    """The declared verifier cannot be run as specified.

    ``output_tail`` carries the last captured lines when the verifier
    started and then failed or timed out, so the observation is retained.
    """

    def __init__(self, message: str, *, output_tail=(), timed_out: bool = False,
                 output_bytes_total: int = 0) -> None:
        super().__init__(message)
        self.output_tail = list(output_tail)
        self.timed_out = timed_out
        self.output_bytes_total = output_bytes_total


class _BoundedCapture:
    """Keep the last ``limit`` bytes of a stream and count everything read."""

    def __init__(self, stream, limit: int) -> None:
        self._stream = stream
        self._limit = limit
        self.total = 0
        self.truncated = False
        self._tail = bytearray()
        self.thread = threading.Thread(target=self._drain, daemon=True)
        self.thread.start()

    def _drain(self) -> None:
        while True:
            chunk = self._stream.read(4096)
            if not chunk:
                break
            self.total += len(chunk)
            self._tail.extend(chunk)
            if len(self._tail) > self._limit:
                self.truncated = True
                del self._tail[:len(self._tail) - self._limit]

    def lines(self) -> list:
        self.thread.join(timeout=2.0)
        text = bytes(self._tail).decode("utf-8", errors="replace")
        return text.strip().splitlines()[-TAIL_LINES:]


def _terminate_group(process) -> bool:
    """Kill the verifier's whole process group; report whether anything remained."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return False
    except OSError:
        return False
    return True


def verifier_execute_operation(arguments, services) -> dict:
    """Execute the declared verifier script, returning score evidence."""
    request = getattr(services, "request", None)
    declared = str(getattr(request, "verifier_path", "") or "").strip()
    if not declared:
        raise VerifierError(
            "no verifier declared: mid-solve verification needs an "
            "explicit operator-declared verifier path")
    candidate = Path(declared)
    if not candidate.is_absolute():
        candidate = Path(os.getcwd()) / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise VerifierError(
            f"verifier path does not resolve: {declared!r}") from exc
    if not resolved.is_file():
        raise VerifierError(
            f"verifier is not a file: {declared!r}")
    timeout = (arguments or {}).get("timeout_seconds",
                                    DEFAULT_TIMEOUT_SECONDS)
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not timeout > 0 or timeout > 3600):
        raise VerifierError(
            "verifier timeout_seconds must be within (0, 3600]")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/tmp")}
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            ["bash", str(resolved)], cwd=str(resolved.parent),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=env, start_new_session=True)
    except OSError as exc:
        raise VerifierError(
            f"verifier launch failed: {type(exc).__name__}") from exc
    capture = _BoundedCapture(process.stdout, MAX_OUTPUT_BYTES)
    timed_out = False
    try:
        process.wait(timeout=float(timeout))
    except subprocess.TimeoutExpired:
        timed_out = True
    # The script's own process group is terminated in every case, so a
    # background process it started cannot outlive the observation.
    group_terminated = _terminate_group(process)
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        pass
    tail = capture.lines()
    process.stdout.close()
    elapsed = round(time.monotonic() - started, 3)
    if timed_out:
        raise VerifierError(
            f"verifier exceeded {timeout:g}s; output tail retained",
            output_tail=tail, timed_out=True,
            output_bytes_total=capture.total)
    return {
        "record_type": VERIFIER_RECORD_TYPE,
        "verifier": str(resolved),
        "exit_code": process.returncode,
        "passed": process.returncode == 0,
        "timeout_seconds": float(timeout),
        "elapsed_seconds": elapsed,
        "output_tail": tail,
        "output_bytes_total": capture.total,
        "output_truncated": capture.truncated,
        "process_group_terminated": group_terminated,
        "containment": "raw_host_process_group",
        "note": ("observation for replanning only: a passing gate does "
                 "not accept the task"),
    }


def self_test() -> dict:
    """Offline verifier-operation checks; the script fixtures are local."""
    import tempfile
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    class _Services:
        def __init__(self, path):
            self.request = type("Request", (),
                                {"verifier_path": path})()

    with tempfile.TemporaryDirectory(prefix="verifier-op-") as folder:
        passing = Path(folder) / "gate-pass.sh"
        passing.write_text("#!/bin/bash\necho 'holdout metric = 0.9900 (floor 0.1000)'\n",
                           encoding="utf-8")
        failing = Path(folder) / "gate-fail.sh"
        failing.write_text("#!/bin/bash\necho 'holdout metric = 0.0100'\nexit 3\n",
                           encoding="utf-8")
        ok_result = verifier_execute_operation(
            {}, _Services(str(passing)))
        check("passing_verifier_returns_score_evidence",
              ok_result["passed"] is True and ok_result["exit_code"] == 0
              and any("0.9900" in line
                      for line in ok_result["output_tail"]),
              "exit code plus output tail, never acceptance")
        bad_result = verifier_execute_operation(
            {}, _Services(str(failing)))
        check("failing_verifier_returns_failure_as_observation",
              bad_result["passed"] is False and bad_result["exit_code"] == 3)
        missing = False
        try:
            verifier_execute_operation(
                {}, _Services(str(Path(folder) / "absent.sh")))
        except VerifierError:
            missing = True
        check("missing_verifier_path_is_refused", missing)
        undeclared = False
        try:
            verifier_execute_operation({}, _Services("   "))
        except VerifierError:
            undeclared = True
        check("undeclared_verifier_never_runs_anything", undeclared)
        slow = Path(folder) / "gate-slow.sh"
        slow.write_text("#!/bin/bash\nsleep 30\n", encoding="utf-8")
        timed_out = False
        try:
            verifier_execute_operation({"timeout_seconds": 1},
                                       _Services(str(slow)))
        except VerifierError:
            timed_out = True
        check("verifier_timeout_is_bounded_and_typed", timed_out)

        # A timed-out verifier takes every process it started with it, and
        # the observation keeps the output produced before the deadline.
        marker = Path(folder) / "descendant-wrote-this"
        pidfile = Path(folder) / "sleeper.pid"
        orphaning = Path(folder) / "gate-orphan.sh"
        orphaning.write_text(
            "#!/bin/bash\necho before-timeout\nsleep 300 &\necho $! > '%s'\n"
            "(sleep 3; touch '%s') &\nwait\n" % (pidfile, marker),
            encoding="utf-8")
        tail = None
        try:
            verifier_execute_operation({"timeout_seconds": 1},
                                       _Services(str(orphaning)))
        except VerifierError as exc:
            tail = exc.output_tail
        time.sleep(4)
        owned_alive = False
        try:
            pid = int(pidfile.read_text().strip())
            with open("/proc/%d/cmdline" % pid, "rb") as handle:
                owned_alive = handle.read().startswith(b"sleep\x00300")
            if owned_alive:
                os.kill(pid, signal.SIGKILL)
        except (OSError, ValueError):
            owned_alive = False
        check("verifier_timeout_terminates_descendants",
              not owned_alive and not marker.exists(),
              "process group killed on timeout; late marker never written")
        check("verifier_timeout_error_carries_output_tail",
              tail is not None and "before-timeout" in " ".join(tail))

        flood = Path(folder) / "gate-flood.sh"
        flood.write_text("#!/bin/bash\nhead -c 200000 /dev/zero | tr '\\0' 'x'\n"
                         "echo\necho last-line\n", encoding="utf-8")
        flood_result = verifier_execute_operation({}, _Services(str(flood)))
        check("verifier_output_capture_is_bounded",
              flood_result["output_truncated"] is True
              and flood_result["output_bytes_total"] >= 200000
              and flood_result["output_tail"][-1] == "last-line",
              "only the last %d bytes are kept" % MAX_OUTPUT_BYTES)
    passed = sum(1 for item in results if item["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}

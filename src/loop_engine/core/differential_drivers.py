"""The programs the differential oracles run inside a contained driver process.

This module owns the text of those programs and the containment constants
they are run under; it never spawns anything.  ``differential_verification``
writes one of these sources to a scratch file and runs it with ``python -I``,
an allowlisted environment, the implementation's own directory as cwd, the
request on stdin, and the result returned through a file -- so the size of
the arguments and anything the implementation prints cannot corrupt the
exchange.  Split out on 2026-09-13 when the oracle module crossed the size
cap; the surface is three source strings, the environment allowlist, and the
``DriverRun`` record the spawn returns.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

#: Names a driver process may inherit from the engine's environment, and
#: nothing else.  The authoritative tuple is ``INHERITABLE_ENVIRONMENT`` in
#: core.opencode_step_session; this is the same list, used only if that module
#: cannot be imported, so both paths build the driver process environment by allowlist.
FALLBACK_INHERITABLE_ENVIRONMENT = (
    "PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR")

#: How much of a driver's stdout and stderr the engine reads back.  What the
#: driver process writes is capped separately, inside that process, by RLIMIT_FSIZE.
OUTPUT_CAPTURE_BYTES = 4096

#: Largest file a driver process may write, its own stdout included.  Generous
#: for an oracle artifact; small enough that a runaway print cannot fill a
#: disk before the timeout ends it.
DRIVER_FILE_SIZE_LIMIT = 64 * 1024 * 1024

#: User-CPU below this is inside the kernel's accounting granularity, so a
#: single call is timed as a batch of repetitions until the batch clears it.
#: Measured 2026-09-13: the oracle module's own linear implementation at 500
#: items reported "0.0x" on one run and failed the 20x bound on the next,
#: because both timings were a tick or less.  Zero disables batching.
TIMING_RESOLUTION_FLOOR_SECONDS = 0.02

#: The reason an oracle gives when it was not allowed to run anything.
HOST_EXECUTION_REFUSED = "host execution not permitted"


def inheritable_environment_names() -> tuple:
    """The names a driver may inherit: the step session's allowlist."""
    try:
        from .opencode_step_session import INHERITABLE_ENVIRONMENT
        return tuple(INHERITABLE_ENVIRONMENT)
    except Exception:                                    # noqa: BLE001
        return FALLBACK_INHERITABLE_ENVIRONMENT


def allowlisted_environment(extra: "tuple[str, ...]" = ()) -> dict:
    """Build the driver process environment from nothing, by allowlist."""
    names = inheritable_environment_names() + tuple(extra)
    return {name: os.environ[name] for name in names if name in os.environ}


@dataclass(frozen=True)
class DriverRun:
    """What came back from one driver process."""

    payload: "dict | None"
    error: "str | None"
    timed_out: bool = False
    stdout_bytes: int = 0


#: Generated code is executed in a separate process, never imported into the
#: engine.  Importing a model-authored module would run it with the engine's
#: own privileges, which contradicts the sandbox posture the rest of this
#: package maintains.  A separate process also contains a hang behind a timeout
#: and a crash behind a return code.  The request arrives on stdin and the
#: result leaves through a file named in it, so neither the size of the
#: arguments nor anything the implementation prints can corrupt the exchange.
DRIVER_PRELUDE = """
import json, sys, os, importlib.util
request = json.load(sys.stdin)
path, entry, result_path = request["path"], request["entry"], request["result_path"]
def _emit(payload):
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
try:
    import resource
    _limit = int(request.get("file_size_limit") or 0)
    if _limit > 0:
        _soft, _hard = resource.getrlimit(resource.RLIMIT_FSIZE)
        if _hard != resource.RLIM_INFINITY and _hard < _limit:
            _limit = _hard
        resource.setrlimit(resource.RLIMIT_FSIZE, (_limit, _hard))
except Exception:
    pass
spec = importlib.util.spec_from_file_location("_candidate", path)
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(path))
try:
    spec.loader.exec_module(module)
except BaseException as exc:
    _emit({"load_error": type(exc).__name__ + ": " + str(exc)[:200]})
    raise SystemExit(0)
function = getattr(module, entry, None)
if not callable(function):
    _emit({"load_error": "no callable " + entry})
    raise SystemExit(0)
"""

DIFFERENTIAL_DRIVER = DRIVER_PRELUDE + """
import tempfile as _tempfile, hashlib as _hashlib
arguments = request["arguments"]
outcomes = []
for argument in arguments:
    scratch = None
    try:
        # A harvested fixture is file CONTENT for an API that takes a PATH.
        # Materialise it here so both implementations read byte-identical
        # input; comparing a parser that reads files is otherwise impossible.
        if isinstance(argument, dict) and "__fixture_content__" in argument:
            handle, scratch = _tempfile.mkstemp(suffix=".fixture")
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
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
                os.close(handle)
                argv[sink] = destination
                function(*argv)
                try:
                    with open(destination, "rb") as fh:
                        body = fh.read()
                finally:
                    try:
                        os.unlink(destination)
                    except OSError:
                        pass
                outcomes.append("wrote:" + _hashlib.sha256(body).hexdigest())
            else:
                outcomes.append("value:" + json.dumps(
                    function(*argv), sort_keys=True, default=repr))
        else:
            outcomes.append("value:" + json.dumps(function(argument),
                                                  sort_keys=True, default=repr))
    except BaseException as exc:
        # SystemExit and KeyboardInterrupt included: an implementation that
        # exits is an outcome to compare, not a reason to lose every other.
        outcomes.append("raises:" + type(exc).__name__)
    finally:
        if scratch:
            try:
                os.unlink(scratch)
            except OSError:
                pass
_emit({"outcomes": outcomes})
"""

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
COMPLEXITY_DRIVER = DRIVER_PRELUDE + """
import random, resource
sizes = request["sizes"]; distinct_ratio = float(request["distinct_ratio"])
floor = float(request.get("resolution_floor") or 0.0)
def _user_time():
    # USER CPU time of this process -- not wall clock, and not process_time.
    # Wall clock measured the machine's load: "10x input cost 30.6x time" on
    # a correct linear implementation at load average 18. process_time fixed
    # that and held 13/13 at load 31.7 -- then failed again, "21.5x", at load
    # 48 with swap at 37 of 39 GB. process_time includes SYSTEM time, and
    # page-fault handling for a swapped process is charged there. User time
    # is the algorithm's own instructions and nothing else. An overnight
    # verdict that changes with what else is running is not a verdict.
    return resource.getrusage(resource.RUSAGE_SELF).ru_utime
timings = []
for size in sizes:
    random.seed(12345)
    span = max(1, int(size * distinct_ratio))
    data = [random.randint(0, span) for _ in range(size)]
    repetitions = 1
    while True:
        best = None
        for _ in range(5):
            began = _user_time()
            try:
                for _ in range(repetitions):
                    function(list(data))
            except BaseException as exc:
                _emit({"call_error": type(exc).__name__ + ": " + str(exc)[:120]})
                raise SystemExit(0)
            elapsed = _user_time() - began
            best = elapsed if best is None else min(best, elapsed)
        # Below the clock's resolution a single call is noise; time a batch
        # large enough to clear it and report the per-call share.
        if best >= floor or repetitions >= 4096:
            break
        repetitions *= 4
    timings.append({"size": size, "seconds": best / repetitions,
                    "repetitions": repetitions})
_emit({"timings": timings})
"""

"""One durable, bounded deployment operation on the Fly volume.

The workflow sends these exact bytes through the Machines API. The short
start call reserves once; subsequent calls only read its result. This is
operator tooling, not a customer endpoint or an execution engine.
"""
import fcntl
from enum import Enum
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path("/data/incoming/deployment-operations")
LIMIT_SECONDS = 600
OUTPUT_LIMIT = 2 * 1024 * 1024
COMMANDS = {name: ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups",
                   "loop-engine", "service", name, "--config", "/data/host.json"]
            for name in ("apply-grants", "apply-billing-policy")}


class OperationMode(str, Enum):
    """The closed operator protocol; only work executes the reserved command."""

    START = "start"
    STATUS = "status"
    WORK = "work"


def save(path, value):
    """Publish a complete record and flush it before another process can use it."""
    temporary = path.with_suffix(".pending")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def binding(operation, revision, run_id):
    if operation not in COMMANDS or not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(r"[0-9]{1,20}", run_id):
        raise ValueError("invalid_deployment_operation")
    return {"operation": operation, "revision": revision, "run_id": run_id}


def directory_for(record):
    return ROOT / (record["revision"] + "-" + record["run_id"] + "-" + record["operation"])


def status(record):
    directory = directory_for(record)
    if not directory.exists():
        return {"state": "absent", "binding": record}
    if json.loads((directory / "reservation.json").read_text()) != record:
        raise ValueError("operation_binding_mismatch")
    result = directory / "result.json"
    if not result.exists():
        return {"state": "pending", "binding": record}
    report = json.loads(result.read_text())
    if report.get("binding") != record:
        raise ValueError("result_binding_mismatch")
    if report["state"] == "succeeded":
        output = directory / "stdout.json"
        if output.stat().st_size > OUTPUT_LIMIT:
            raise ValueError("operation_output_too_large")
        report["stdout"] = output.read_text()
    return report


def start(record, source):
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ROOT.resolve() != ROOT:
        raise ValueError("operation_root_is_not_direct")
    with (ROOT / "operation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory = directory_for(record)
        if directory.exists():
            return status(record)
        active = ROOT / "active.json"
        if active.exists():
            prior = status(json.loads(active.read_text()))
            if prior["state"] not in ("succeeded", "failed"):
                raise ValueError("previous_operation_requires_reconciliation")
        directory.mkdir(mode=0o700)
        save(directory / "reservation.json", record)
        save(active, record)
        script = directory / "worker.py"
        with script.open("x", encoding="utf-8") as stream:
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        # Transfer the lock to the detached supervisor. A lost start response
        # must never cause a second command; the durable reservation survives.
        subprocess.Popen([sys.executable, str(script), OperationMode.WORK.value, record["operation"],
                          record["revision"], record["run_id"], str(lock.fileno())],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True,
                         pass_fds=(lock.fileno(),))
        return {"state": "pending", "binding": record}


def work(record, descriptor):
    directory = directory_for(record)
    started = time.monotonic()
    report = {"binding": record, "state": "uncertain", "exit_code": None}
    try:
        if json.loads((directory / "reservation.json").read_text()) != record:
            raise ValueError("operation_binding_mismatch")
        with (directory / "stdout.json").open("xb") as output, (directory / "stderr.txt").open("xb") as errors:
            child = subprocess.Popen(COMMANDS[record["operation"]], stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=errors, start_new_session=True)
            try:
                code = child.wait(timeout=LIMIT_SECONDS)
                report.update(state="succeeded" if code == 0 else ("failed" if code > 0 else "uncertain"), exit_code=code)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                report["reason"] = "deadline_requires_reconciliation"
    except Exception as error:
        # Do not include exception messages or environment values in results.
        report["reason"] = type(error).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save(directory / "result.json", report)
        os.close(descriptor)


def main(source=None):
    mode_name, operation, revision, run_id = sys.argv[1:5]
    mode = OperationMode(mode_name)
    record = binding(operation, revision, run_id)
    if mode is OperationMode.START:
        result = start(record, source if source is not None else Path(__file__).read_text())
    elif mode is OperationMode.STATUS:
        result = status(record)
    elif mode is OperationMode.WORK:
        work(record, int(sys.argv[5]))
        return
    else:
        raise ValueError("invalid_deployment_mode")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

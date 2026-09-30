"""Apply one packaged deployment operation, polling its durable result.

A failed start transport is an unknown outcome, never permission to dispatch
again. Only status reads are retried. The existing workflow checks the exact
command output and service readiness after this helper succeeds.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

import fly_reconcile_remote as remote


def remote_command(mode, record):
    mode = remote.OperationMode(mode).value
    source = Path(remote.__file__).read_text()
    # Import the exact reviewed source, without executing its file entry point.
    program = "scope={'__name__':'deployment_operation'}; exec(" + repr(source) + ",scope); scope['main'](" + repr(source) + ")"
    return shlex.join(["python", "-c", program, mode, record["operation"], record["revision"], record["run_id"]])


def invoke(app, machine, mode, record):
    result = subprocess.run(["flyctl", "machine", "exec", machine, remote_command(mode, record),
                             "--app", app, "--json", "--timeout", "30"],
                            capture_output=True, text=True, timeout=40, check=False)
    if result.returncode:
        raise RuntimeError("machines_api_outcome_unknown")
    envelope = json.loads(result.stdout)
    if envelope.get("exit_code", 0) != 0:
        raise RuntimeError("remote_operation_refused")
    report = json.loads(envelope["stdout"])
    if report.get("binding") != record:
        raise ValueError("operation_binding_mismatch")
    return report


def reconcile(app, machine, record, *, call=invoke, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + 660
    try:
        call(app, machine, "start", record)
    except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired):
        print("Start not confirmed; reading the reservation without redispatching.", file=sys.stderr)
    while clock() < deadline:
        try:
            report = call(app, machine, "status", record)
        except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired):
            sleep(5)
            continue
        if report["state"] == "succeeded":
            if type(report.get("exit_code")) is not int or report["exit_code"] != 0 or not isinstance(report.get("stdout"), str):
                raise RuntimeError("invalid_operation_success")
            print("Operation completed in " + str(report["elapsed_seconds"]) + " seconds.", file=sys.stderr)
            return {"exit_code": 0, "stdout": report["stdout"], "elapsed_seconds": report["elapsed_seconds"]}
        if report["state"] not in ("pending", "absent"):
            raise RuntimeError("operation_" + report["state"] + "_requires_reconciliation")
        sleep(5)
    raise RuntimeError("operation_deadline_requires_reconciliation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--operation", choices=tuple(remote.COMMANDS), required=True)
    parser.add_argument("--command", required=True, help="Exact command already qualified by the container check")
    parser.add_argument("--timeout", type=int, choices=(660,), required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--run-id", required=True)
    options = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", options.app) or not re.fullmatch(r"[0-9a-f]{8,32}", options.machine):
        parser.error("an exact app and Machine identity are required")
    record = remote.binding(options.operation, options.revision, options.run_id)
    if shlex.split(options.command) != remote.COMMANDS[options.operation]:
        parser.error("operation must match the container-qualified command")
    try:
        print(json.dumps(reconcile(options.app, options.machine, record)))
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

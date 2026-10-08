#!/usr/bin/env python3
"""Local operator queue around canonical `loop-engine solve`, not a new runtime.

V2 binds manifest bytes, tasks and limits; reserves the remaining call allowance
durably before dispatch; and holds unknown outcomes for explicit reconciliation.
Reservations are conservatively charged in full, never claimed as observed
provider usage. They are not refunded after failed or interrupted children.
Completed tasks are skipped, not resumed reasoning. See OVERNIGHT-QUEUE.md.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import selectors
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

from overnight_queue_state import (
    LOCK_FILENAME, MAX_MANIFEST_BYTES, MAX_TASK_BYTES, STATE_FILENAME,
    QueueBinding, QueueLimits, QueueRefusal, bytes_digest, calls_allocated,
    load_state, new_state, parse, plain_path, queue_lock, read_bytes, require,
    save_state, sync_directory, validate_reconciliation, validate_state,
)

STOP_WAIT_SECONDS = 2.0
SUMMARY_FILE_LIMIT = 10000


def load_tasks(manifest: Path) -> list[Path]:
    """Read every declared task; missing or duplicate inputs fail closed."""
    tasks = []
    for line in read_bytes(manifest, MAX_MANIFEST_BYTES).decode("utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        path = plain_path(Path(text).expanduser())
        require(path.is_file() and path not in tasks, "task_missing_or_duplicate")
        tasks.append(path)
    require(bool(tasks), "tasks_required")
    return tasks


def checkpoint_candidates(runs_dir: Path) -> list:
    """Every checkpoint a task could have left, oldest first.

    The engine nests history under a per-run directory, so a completed run's
    checkpoint is at runs_dir/<run_id>/checkpoint.json.  An interrupted run
    writes its checkpoint where the handler was armed, which is
    runs_dir/checkpoint.json when the interruption came before the run id
    was known.  Both are read; the newest wins.
    """
    found = []
    if not runs_dir.is_symlink() and runs_dir.is_dir():
        with os.scandir(runs_dir) as entries:
            for count, entry in enumerate(entries):
                if count >= SUMMARY_FILE_LIMIT:
                    break
                if entry.is_dir(follow_symlinks=False):
                    path = Path(entry.path) / "checkpoint.json"
                    if path.is_file() and not path.is_symlink():
                        found.append(path)
    direct = runs_dir / "checkpoint.json"
    if direct.is_file() and not direct.is_symlink():
        found.append(direct)

    def modified(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    return sorted(found, key=modified)


def summarise(workspace: Path, runs_dir: Path) -> dict:
    """Report what a finished task left behind, ranked if it can be."""
    candidates = checkpoint_candidates(runs_dir)
    data = {}
    if candidates:
        try:
            # Metadata only: do not traverse arbitrary checkpoint-named trees
            # during shutdown. Artifact verification belongs to the checkpoint
            # owner's separately authorized read, never this budget projection.
            from loop_engine.core.run_checkpoint import read_checkpoint
            read_bytes(candidates[-1])
            data = read_checkpoint(candidates[-1].parent, verify_digests=False)
            if data.get("record_type") != "run_checkpoint/v1":
                data = {}
        except (OSError, ValueError):
            data = {}
    count, examined = 0, 0
    pending = [workspace] if workspace.is_dir() and not workspace.is_symlink() else []
    while pending and examined < SUMMARY_FILE_LIMIT:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                examined += 1
                if entry.is_file(follow_symlinks=False) and entry.name.endswith(".py"):
                    count += 1
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                if examined >= SUMMARY_FILE_LIMIT:
                    break
    return {
        "attempts": len(data.get("attempts") or ()),
        "retained": data.get("retained", ""),
        "ranked": bool(data.get("retained_is_ranked")),
        "files": count,
        "files_truncated": examined >= SUMMARY_FILE_LIMIT,
        "checkpoint_digests_verified": False,
        # Which file the numbers above came from, and why the run ended,
        # so a morning reader can tell an interrupted task from a finished one.
        "checkpoint": str(candidates[-1]) if candidates else "",
        "reason": str(data.get("reason") or ""),
    }


def run_task(command: list, *, timeout: float, grace_seconds: float = 30.0,
             pass_fds: tuple = ()):
    """Run one task; a hung one is asked to stop before it is killed.

    Returns ``(exit_code, stdout_tail, how_it_ended)``.  ``how_it_ended`` is
    ``finished`` for a task that exited on its own; otherwise it says whether
    SIGTERM was honoured within the grace period or SIGKILL had to follow.
    The exit code for an abandoned task stays 124, as before.
    """
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, shell=False, start_new_session=True,
        pass_fds=pass_fds)

    def signal_owned_group(number):
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            pass

    tail = bytearray()
    with selectors.DefaultSelector() as selector:
        for pipe in (process.stdout, process.stderr):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ)

        def drain_until(deadline):
            while time.monotonic() < deadline:
                if process.poll() is not None and not selector.get_map():
                    return True
                for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.fileobj is process.stdout:
                        tail.extend(chunk)
                        del tail[:-400]
            return process.poll() is not None and not selector.get_map()

        try:
            if drain_until(time.monotonic() + timeout):
                signal_owned_group(signal.SIGKILL)
                return process.returncode, tail.decode("utf-8", errors="replace"), "finished"
            ended = "killed (SIGKILL sent at once; --grace-seconds is 0)"
            if grace_seconds > 0:
                signal_owned_group(signal.SIGTERM)
                if drain_until(time.monotonic() + grace_seconds):
                    ended = f"terminated (SIGTERM honoured within {grace_seconds:g}s)"
                else:
                    ended = f"killed (SIGTERM ignored for {grace_seconds:g}s)"
            signal_owned_group(signal.SIGKILL)
            process.wait(timeout=STOP_WAIT_SECONDS)
            return 124, tail.decode("utf-8", errors="replace"), ended
        except BaseException:
            # Cleanup never converts cancellation into a successful attempt.
            signal_owned_group(signal.SIGTERM)
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                pass
            signal_owned_group(signal.SIGKILL)
            try:
                process.wait(timeout=STOP_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                pass
            raise
        finally:
            process.stdout.close()
            process.stderr.close()


def bind_queue(args):
    manifest = plain_path(args.manifest)
    paths = load_tasks(manifest)
    tasks = []
    for path in paths:
        raw = read_bytes(path, MAX_TASK_BYTES)
        require(raw.strip(), "empty_task_refused")
        raw.decode("utf-8")
        tasks.append({"path": str(path), "sha256": bytes_digest(raw), "size_bytes": len(raw)})
    python = shutil.which(args.python)
    require(bool(python), "python_unavailable")
    limits = QueueLimits(args.max_calls_per_task, args.queue_call_budget, args.max_passes,
                         args.task_timeout, args.grace_seconds, args.queue_timeout)
    return QueueBinding(str(manifest), bytes_digest(read_bytes(manifest, MAX_MANIFEST_BYTES)),
                        tuple(tasks), str(plain_path(args.runs_dir)), str(plain_path(args.workspace_root)),
                        str(Path(python).absolute()), str(Path.cwd().resolve()), limits)


def persist(path, state):
    now = time.time()
    require(now >= state["updated_at"], "clock_moved_backwards")
    state["updated_at"] = now
    state["revision"] += 1
    save_state(path, state)


def attempt_paths(state, attempt):
    binding = state["binding"]
    return (Path(binding["workspace_root"]) / attempt["id"],
            Path(binding["runs_root"]) / attempt["id"])


def attempts_for_report(state):
    """All attempts, including held/failed ones; not an alternate budget store."""
    validate_state(state)
    entries = []
    for attempt in state["attempts"]:
        workspace, runs = attempt_paths(state, attempt)
        outcome = attempt["outcome"] or {}
        entries.append({"workspace": str(workspace), "runs_dir": str(runs),
            "task_file": state["binding"]["tasks"][attempt["task_index"]]["path"],
            "index": attempt["task_index"] + 1, "attempt_id": attempt["id"],
            "queue_status": attempt["status"], "allocation": attempt["allocation"],
            "exit": outcome.get("exit"), "seconds": outcome.get("seconds"),
            **outcome.get("summary", {})})
    return entries


def status_record(state):
    return {"record_type": "overnight_queue_status/v2", "binding_sha256": state["binding_sha256"],
            "calls_allocated": calls_allocated(state), "observed_model_calls": None,
            "call_budget": state["binding"]["limits"]["queue_call_budget"],
            "deadline": state["deadline"], "attempts": attempts_for_report(state)}


def reconcile(state, request):
    matches = [attempt for attempt in state["attempts"] if attempt["id"] == request.get("attempt_id")]
    require(len(matches) == 1 and matches[0]["status"] in ("reserved", "unknown"), "attempt_not_unresolved")
    attempt = matches[0]
    validate_reconciliation(request, state, attempt)
    raw = read_bytes(request["evidence_path"])
    require(bytes_digest(raw) == request["evidence_sha256"], "reconciliation_evidence_changed")
    attempt["status"] = "reconciled"
    attempt["reconciliation"] = request
    # No refund, no provider replay, and no dispatch in a reconcile invocation.


@contextmanager
def interruption_handlers():
    previous = {}
    def stop(_number, _frame):
        raise KeyboardInterrupt
    try:
        for name in ("SIGINT", "SIGTERM", "SIGHUP"):
            number = getattr(signal, name)
            previous[number] = signal.signal(number, stop)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def run_queue(args, *, runner=run_task):
    require(not args.fresh, "fresh_allowance_reset_forbidden")
    binding = bind_queue(args)
    runs_root = Path(binding.runs_root)
    state_path = runs_root / STATE_FILENAME
    with queue_lock(runs_root) as lock_fd:
        if state_path.exists():
            state = load_state(state_path, binding)
        else:
            require(not args.status and not args.reconcile, "queue_state_missing")
            require(not any(path.name != LOCK_FILENAME for path in runs_root.iterdir()),
                    "state_missing_in_nonempty_runs_root")
            state = new_state(binding, time.time())
            save_state(state_path, state)
        require(time.time() >= state["updated_at"], "clock_moved_backwards")
        if args.status:
            print(json.dumps(status_record(state)))
            return 0
        if args.reconcile:
            require(args.authorize_reconcile, "reconciliation_authority_required")
            request = parse(read_bytes(args.reconcile))
            require(type(request) is dict, "reconciliation_record_required")
            reconcile(state, request)
            persist(state_path, state)
            print(json.dumps(status_record(state)))
            return 0
        require(not args.authorize_reconcile, "reconciliation_record_required")
        require(not any(row["status"] in ("reserved", "unknown") for row in state["attempts"]),
                "unknown_outcome_requires_reconciliation")
        monotonic_deadline = time.monotonic() + max(0, state["deadline"] - time.time())
        for index, task in enumerate(binding.tasks):
            previous = [row for row in state["attempts"] if row["task_index"] == index]
            if previous and not (previous[-1]["status"] == "reconciled"
                    and previous[-1]["reconciliation"]["action"] == "retry"):
                continue
            remaining = binding.limits.queue_call_budget - calls_allocated(state)
            seconds = min(state["deadline"] - time.time(), monotonic_deadline - time.monotonic())
            if remaining <= 0 or seconds <= binding.limits.grace_seconds + STOP_WAIT_SECONDS:
                break
            raw = read_bytes(task["path"], MAX_TASK_BYTES)
            require(bytes_digest(raw) == task["sha256"], "task_changed_before_dispatch")
            allocation = min(binding.limits.max_calls_per_task, remaining)
            attempt = {"id": f"attempt-{len(state['attempts']) + 1:06d}", "task_index": index,
                       "allocation": allocation, "reserved_at": time.time(), "status": "reserved",
                       "outcome": None, "reconciliation": None}
            state["attempts"].append(attempt)
            persist(state_path, state)  # Must succeed durably before any child can start.
            workspace, task_runs = attempt_paths(state, attempt)
            began = time.monotonic()
            try:
                task_runs.mkdir(mode=0o700)
                snapshot = task_runs / "task.txt"
                with snapshot.open("xb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                sync_directory(task_runs)
                command = [binding.python, "-m", "loop_engine", "solve", "--file", str(snapshot),
                    "--quickstart", "--unattended", "--authorize-model-calls", "--workspace", str(workspace),
                    "--runs-dir", str(task_runs), "--max-passes", str(binding.limits.max_passes),
                    "--max-model-calls", str(allocation), "--quiet-model-io"]
                code, _tail, ended = runner(command,
                    timeout=min(binding.limits.task_timeout, seconds - binding.limits.grace_seconds - STOP_WAIT_SECONDS),
                    grace_seconds=binding.limits.grace_seconds, pass_fds=(lock_fd,))
                attempt["outcome"] = {"exit": code, "ended": ended,
                    "seconds": round(time.monotonic() - began, 3), "summary": summarise(workspace, task_runs),
                    "observed_model_calls": None}
                attempt["status"] = "finished" if code == 0 and ended == "finished" else "unknown"
                persist(state_path, state)
                if attempt["status"] == "unknown":
                    print(json.dumps(status_record(state)))
                    return 2
            except BaseException:
                # Even an exception before Popen retains its full reservation.
                # A process crash can occur after dispatch but before a PID save.
                attempt["status"] = "unknown"
                persist(state_path, state)
                raise
        print(json.dumps(status_record(state)))
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="file listing one task file per line")
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--task-timeout", type=int, default=1800,
                        help="seconds before a hung task is abandoned")
    parser.add_argument("--grace-seconds", type=float, default=30.0,
                        help="after --task-timeout, seconds between SIGTERM "
                             "(which lets the engine write its checkpoint) "
                             "and SIGKILL; 0 kills at once as earlier "
                             "versions did")
    parser.add_argument("--max-calls-per-task", type=int, default=120)
    parser.add_argument("--queue-call-budget", type=int, default=1200,
                        help="ceiling across the whole night")
    parser.add_argument("--max-passes", type=int, default=6)
    parser.add_argument("--queue-timeout", type=float, default=43200,
                        help="cumulative wall seconds from first initialization, not renewed on resume")
    parser.add_argument("--fresh", action="store_true",
                        help="retired: always refuses; never resets an existing allowance")
    parser.add_argument("--status", action="store_true", help="report current v2 state without dispatch")
    parser.add_argument("--reconcile", type=Path, help="exact evidence-bound reconciliation record; starts no child")
    parser.add_argument("--authorize-reconcile", action="store_true")
    args = parser.parse_args(argv)
    try:
        require(not (args.status and args.reconcile), "queue_mode_conflict")
        with interruption_handlers():
            return run_queue(args)
    except KeyboardInterrupt:
        print("queue_refused: interrupted; reservations retained", file=sys.stderr)
        return 130
    except (QueueRefusal, OSError, UnicodeError) as error:
        code = str(error) if isinstance(error, QueueRefusal) else "operator_io_failure"
        print("queue_refused: " + code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

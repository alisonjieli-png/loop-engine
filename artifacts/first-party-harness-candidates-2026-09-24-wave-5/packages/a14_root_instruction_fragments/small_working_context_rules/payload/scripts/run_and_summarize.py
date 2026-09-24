"""Run one command, save its output in a file and print a short summary. Effects: starts the named command as a subprocess in the workspace root and writes its output to one file under .baltor/state/; no network, no model call.

Usage, from the workspace root:

    python3 -I -B .baltor/small-working-context-rules/scripts/run_and_summarize.py [--save PATH] [--timeout SECONDS] -- COMMAND [ARGUMENT ...]

The command runs without a shell, in the workspace root, with standard input
closed. Its standard output and standard error go together to the save file,
by default .baltor/state/small-working-context-rules/out.txt. A save path is
relative to the workspace root and must stay inside .baltor/state/, so the
helper never overwrites a project file. A command that needs shell syntax is
named as a shell with its script, for example: -- sh -c "make test".

The answer is one JSON object: the exit code, the save path, the number of
lines and bytes, the last 40 lines and at most 20 error lines with their line
numbers. Each line in the answer is cut at 300 characters. At most 64 MiB of
output is saved; the rest is counted in dropped_bytes. On timeout the command
and every process it started in its own process group are stopped. Output that
a leftover background process writes more than 5 seconds after the command
exits is not saved. The helper needs a POSIX system (select on pipes and
process groups); Windows is not supported.

Exit 0: the command exited 0. Exit 1: the command exited with another code or
timed out. Exit 2: the input was refused or the command could not start.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import signal
import select
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SAVE = ".baltor/state/small-working-context-rules/out.txt"
STATE_ROOT = (".baltor", "state")
TAIL_LINES = 40
MAX_ERROR_LINES = 20
MAX_LINE_CHARACTERS = 300
MAX_SAVED_BYTES = 64 * 1024 * 1024
DEFAULT_TIMEOUT = 1800.0
MAX_TIMEOUT = 86400.0
ERROR_LINE = re.compile(r"FAIL|ERROR|Error|error:|Traceback|panic")
NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
#: How long output may stay open after the command exits, for example held by a background process it started.
GRACE_SECONDS = 5.0
NEXT_PASSED = "The command exited 0. Read tail or the saved file only if you need a detail."
NEXT_FAILED = ("Read error_lines first. For more, read a slice of at most 120 lines of the saved file around a line "
               "number, not the whole file.")
NEXT_REFUSED = "Fix the helper command and run it again. Do not run the command without the helper to see its output."


class Refusal(Exception):
    """A refused call: a stable code and a short detail."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code, self.detail = code, detail


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # an argument error is refused input, answered as JSON
        raise Refusal("arguments_invalid", message)


def seconds(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("a number of seconds") from None
    if not 0 < number <= MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(f"more than 0 and at most {MAX_TIMEOUT:g} seconds")
    return number


def parse(argv: list) -> tuple:
    if "--" not in argv:
        raise Refusal("command_missing", "name the command after --")
    split = argv.index("--")
    parser = Parser(prog="run_and_summarize.py", description="Run one command and summarize its output.")
    parser.add_argument("--save", default=DEFAULT_SAVE)
    parser.add_argument("--timeout", type=seconds, default=DEFAULT_TIMEOUT)
    parser.add_argument("--root", default=".")
    options = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    if not command or not command[0]:
        raise Refusal("command_missing", "name the command after --")
    return options, command


def save_path(root: Path, value: str) -> Path:
    """Resolve the save path inside .baltor/state/, creating folders, refusing links and paths that leave it."""
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != STATE_ROOT \
            or len(relative.parts) < 3:
        raise Refusal("save_path_refused", f"{value!r} must be a file path inside .baltor/state/")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise Refusal("save_path_refused", f"{current.relative_to(root).as_posix()} is a symbolic link")
        if not current.exists():
            try:
                current.mkdir(exist_ok=True)
            except OSError:
                raise Refusal("save_path_refused", f"{current.relative_to(root).as_posix()} cannot be created") from None
        if current.is_symlink() or not current.is_dir():
            raise Refusal("save_path_refused", f"{current.relative_to(root).as_posix()} is not a folder")
    path = current / relative.parts[-1]
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise Refusal("save_path_refused", f"{value} is not a regular file")
    return path


def cut(line: bytes) -> str:
    return line.decode("utf-8", "replace").rstrip("\r\n")[:MAX_LINE_CHARACTERS]


def stop_group(process: subprocess.Popen) -> None:
    """Stop the command and the processes it started in its own process group."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, AttributeError):
        try:
            process.kill()
        except OSError:
            pass


def run(root: Path, command: list, path: Path, timeout: float) -> dict:
    """Run the command and copy its output into the save file, never waiting past the deadline and grace period."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | NO_FOLLOW, 0o644)
    saved = dropped = 0
    timed_out, exited_at = False, None
    started = time.monotonic()
    deadline = started + timeout
    with os.fdopen(descriptor, "wb") as sink:
        try:
            process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            raise Refusal("command_not_started", f"{command[0]}: {error.strerror or error}") from None
        pipe = process.stdout.fileno()
        try:
            while True:
                if exited_at is None and process.poll() is not None:
                    exited_at = time.monotonic()
                if exited_at is None and time.monotonic() >= deadline:
                    timed_out = True
                    stop_group(process)
                    process.wait()
                    exited_at = time.monotonic()
                if exited_at is not None and time.monotonic() - exited_at > GRACE_SECONDS:
                    break  # a process the command left running still holds the output open
                ready, _write, _error = select.select([pipe], [], [], 0.2)
                if not ready:
                    continue
                chunk = os.read(pipe, 65536)
                if not chunk:
                    break
                room = max(MAX_SAVED_BYTES - saved, 0)
                sink.write(chunk[:room])
                saved += min(len(chunk), room)
                dropped += max(len(chunk) - room, 0)
        finally:
            process.stdout.close()
        if process.poll() is None:  # the output closed, but the command still runs
            try:
                process.wait(timeout=max(deadline - time.monotonic(), 0.01))
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_group(process)
                process.wait()
    return {"exit_code": process.returncode, "timed_out": timed_out, "seconds": round(time.monotonic() - started, 3),
            "saved_bytes": saved, "dropped_bytes": dropped}


def summarize(path: Path) -> dict:
    tail, errors, lines = collections.deque(maxlen=TAIL_LINES), [], 0
    with open(path, "rb") as stream:
        for number, line in enumerate(stream, 1):
            lines = number
            text = cut(line)
            tail.append(text)
            if len(errors) < MAX_ERROR_LINES and ERROR_LINE.search(text):
                errors.append(f"{number}: {text}")
    return {"output_lines": lines, "tail": list(tail), "error_lines": errors}


def main(argv=None) -> int:
    try:
        options, command = parse(sys.argv[1:] if argv is None else argv)
        try:
            root = Path(options.root).resolve(strict=True)
        except (OSError, RuntimeError):
            raise Refusal("root_missing", "the --root folder does not exist") from None
        if not root.is_dir():
            raise Refusal("root_missing", "the --root path is not a folder")
        path = save_path(root, options.save)
        outcome = run(root, command, path, options.timeout)
        summary = summarize(path)
    except Refusal as refusal:
        print(json.dumps({"result": "refused", "code": refusal.code, "detail": refusal.detail, "next": NEXT_REFUSED},
                         ensure_ascii=False, sort_keys=True))
        return 2
    except OSError as error:
        print(json.dumps({"result": "refused", "code": "file_system_error",
                          "detail": f"{type(error).__name__}: {error.strerror or error}"[:300], "next": NEXT_REFUSED},
                         ensure_ascii=False, sort_keys=True))
        return 2
    passed = outcome["exit_code"] == 0 and not outcome["timed_out"]
    answer = {"result": "timed_out" if outcome["timed_out"] else "exited", "program": Path(command[0]).name,
              "output_file": path.relative_to(root).as_posix(), **outcome, **summary,
              "next": NEXT_PASSED if passed else NEXT_FAILED}
    print(json.dumps(answer, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

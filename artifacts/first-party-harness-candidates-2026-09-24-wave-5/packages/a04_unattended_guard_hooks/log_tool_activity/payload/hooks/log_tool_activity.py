"""Effects: reads one JSON event on standard input; appends one line to .baltor/state/log-tool-activity/activity.jsonl under the workspace and writes one JSON answer to standard output; makes no network call, starts no program and copies no file contents or command output.

Tool activity logger for a coding harness, run after each tool call.

Each call adds one JSON line with the time, the harness, the tool name, a short
target and the outcome. The target is a root-relative path for file tools, the
program and at most two short word arguments for shell tools, and empty for
other tools. Tool results, file contents, command output, search patterns and
long or mixed arguments are never written, so a morning report can count what
the agent did without holding what it read.

Usage:
    python3 -I -B log_tool_activity.py --harness claude_code|cursor|copilot [--event NAME] [--root DIR] [--max-log-bytes N]

Line format (at most 1024 bytes):
    {"record_type": "tool_activity/v1", "time": "2026-09-23T01:02:03Z", "harness": "claude_code",
     "tool": "Bash", "target": "python3 -m pytest", "outcome": "ok"}

Outcomes: ok, failed, interrupted, timeout, denied, unknown. When the log
reaches its size limit (default 4 MiB), one line with outcome log_full is
added and later calls are not recorded. The logger fails open: every problem
gives exit status 0, the empty answer {} and one diagnostic line on standard
error. Licensed MIT, like the rest of this package.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import signal
import stat
import sys
from pathlib import Path

try:
    import fcntl
except ImportError:  # not available on Windows; appends are then unlocked
    fcntl = None

NATIVE_NAME = "log-tool-activity"
RECORD = "tool_activity/v1"
LOG_FOLDER = Path(".baltor") / "state" / NATIVE_NAME
HARNESSES = ("claude_code", "cursor", "copilot")
MAX_EVENT_BYTES = 1024 * 1024
MAX_LINE_BYTES = 1024
FULL_RESERVE = 256
DEFAULT_LOG_BYTES = 4 * 1024 * 1024
TIME_LIMIT_SECONDS = 8
SHELL_TOOLS = frozenset({"Bash", "Shell", "bash", "powershell"})
PATH_FIELDS = ("file_path", "notebook_path", "path")
PROGRAM = re.compile(r"[A-Za-z0-9._+-]{1,40}\Z")
WORD_ARGUMENT = re.compile(r"-{0,2}[A-Za-z][A-Za-z0-9._-]{0,23}\Z")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
FAILURE_TYPES = {"error": "failed", "timeout": "timeout", "permission_denied": "denied"}
RESULT_TYPES = {"success": "ok", "failure": "failed", "denied": "denied"}


class Skip(Exception):
    """The call is not recorded; the reason goes to standard error."""


def strict_json(raw: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def constant(name):
        raise ValueError("nonstandard number " + name)

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeDecodeError, RecursionError) as error:
        raise ValueError(type(error).__name__) from error


def printable(text: str, limit: int) -> str:
    clean = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)
    return clean if len(clean) <= limit else clean[: limit - 3] + "..."


def read_event(stream) -> dict:
    raw = stream.read(MAX_EVENT_BYTES + 1)
    if len(raw) > MAX_EVENT_BYTES:
        raise Skip("the event is larger than 1 MiB")
    try:
        event = strict_json(raw)
    except ValueError as error:
        raise Skip("the event is not valid JSON") from error
    if not isinstance(event, dict):
        raise Skip("the event is not a JSON object")
    return event


def workspace_roots(options) -> tuple:
    if options.root:
        value = options.root
    elif options.harness == "claude_code":
        value = os.environ.get("CLAUDE_PROJECT_DIR", "")
    elif options.harness == "cursor":
        value = os.environ.get("CURSOR_PROJECT_DIR", "") or os.environ.get("CLAUDE_PROJECT_DIR", "")
    else:
        value = os.getcwd()  # the Copilot registration starts the hook in the repository root
    if not value:
        raise Skip("the workspace root is unknown")
    real = Path(os.path.realpath(value))
    if not real.is_dir() or real == Path(real.anchor):
        raise Skip("the workspace root is not a usable folder")
    return real, Path(os.path.abspath(value))


# ---------------------------------------------------------------------------
# What one line holds
# ---------------------------------------------------------------------------

def call_parts(event: dict, harness: str, event_name: str) -> tuple:
    """Return (tool, arguments, outcome) of an after-call event."""
    if harness == "copilot":
        tool, arguments = event.get("toolName"), event.get("toolArgs")
        if isinstance(arguments, str):
            try:
                arguments = strict_json(arguments.encode("utf-8"))
            except ValueError:
                arguments = {}
        result = event.get("toolResult")
        kind = result.get("resultType") if isinstance(result, dict) else None
        outcome = RESULT_TYPES.get(kind, "unknown")
    else:
        name = event_name or event.get("hook_event_name")
        tool, arguments = event.get("tool_name"), event.get("tool_input")
        if harness == "claude_code":
            if name == "PostToolUse":
                response = event.get("tool_response")
                interrupted = isinstance(response, dict) and response.get("interrupted") is True
                outcome = "interrupted" if interrupted else "ok"
            elif name == "PostToolUseFailure":
                outcome = "interrupted" if event.get("is_interrupt") is True else "failed"
            else:
                raise Skip("the event is not an after-call event")
        else:
            if name == "postToolUse":
                outcome = "ok"
            elif name == "postToolUseFailure":
                outcome = "interrupted" if event.get("is_interrupt") is True else \
                    FAILURE_TYPES.get(event.get("failure_type"), "failed")
            else:
                raise Skip("the event is not an after-call event")
    if not isinstance(tool, str) or not tool:
        raise Skip("the event names no tool")
    return tool, arguments if isinstance(arguments, dict) else {}, outcome


def command_head(command) -> str:
    """The program and at most two short word arguments of the first simple command."""
    if not isinstance(command, str):
        return ""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    words = []
    for token in tokens:
        if token and all(ch in ";&|()<>" for ch in token):
            break
        words.append(token)
    while words and ASSIGNMENT.match(words[0]):
        words = words[1:]
    if not words:
        return ""
    program = words[0].rsplit("/", 1)[-1]
    if not PROGRAM.fullmatch(program):
        return ""
    head = [program]
    for word in words[1:3]:
        if not WORD_ARGUMENT.fullmatch(word):
            break
        head.append(word)
    return " ".join(head)


def path_target(arguments: dict, event: dict, roots: tuple) -> str:
    raw = next((arguments[name] for name in PATH_FIELDS if isinstance(arguments.get(name), str)), None)
    if not raw or "\x00" in raw or len(raw) > 4096:
        return ""
    cwd = event.get("cwd")
    base = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else str(roots[1])
    joined = os.path.normpath(os.path.join(base, raw))
    for root in (roots[1], roots[0]):
        try:
            return printable(Path(joined).relative_to(root).as_posix(), 200)
        except ValueError:
            continue
    return "[outside workspace]"


def activity_line(options, event: dict, roots: tuple) -> bytes:
    tool, arguments, outcome = call_parts(event, options.harness, options.event or "")
    if tool in SHELL_TOOLS:
        target = command_head(arguments.get("command"))
    else:
        target = path_target(arguments, event, roots)
    line = {"record_type": RECORD,
            "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "harness": options.harness, "tool": printable(tool, 64), "target": target, "outcome": outcome}
    data = (json.dumps(line, ensure_ascii=True) + "\n").encode("ascii")
    if len(data) > MAX_LINE_BYTES:
        raise Skip("the line would be larger than 1024 bytes")
    return data


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def log_folder(root: Path) -> Path:
    """Create the log folder one level at a time, never through a symbolic link."""
    current = root
    for part in LOG_FOLDER.parts:
        current = current / part
        if current.is_symlink():
            raise Skip("the log folder leads through a symbolic link")
        if not current.exists():
            current.mkdir()
        elif not current.is_dir():
            raise Skip("the log folder path is not a folder")
    return current


def append(folder: Path, data: bytes, harness: str, limit: int) -> None:
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(str(folder / "activity.jsonl"), flags, 0o644)
    except OSError as error:
        raise Skip("the log file cannot be opened (%s)" % type(error).__name__) from error
    try:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise Skip("the log path is not a regular file")
        size = details.st_size
        usable = limit - FULL_RESERVE
        if size + MAX_LINE_BYTES <= usable:  # decided on the largest line, so nothing follows the full marker
            os.write(descriptor, data)
            return
        os.lseek(descriptor, max(0, size - FULL_RESERVE), os.SEEK_SET)
        tail = os.read(descriptor, FULL_RESERVE)
        if b'"outcome": "log_full"' in tail:
            raise Skip("the log is full")
        marker = {"record_type": RECORD,
                  "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "harness": harness, "tool": "", "target": "", "outcome": "log_full"}
        os.write(descriptor, (json.dumps(marker) + "\n").encode("ascii"))
        raise Skip("the log reached its size limit; this call and later calls are not recorded")
    finally:
        os.close(descriptor)


def out_of_time(_signal_number, _frame):
    raise TimeoutError("time limit")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Append one bounded line per tool call to the step activity log.")
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--event", help="hook event name when the event itself carries none")
    parser.add_argument("--root", help="workspace root; defaults to the harness project folder")
    parser.add_argument("--max-log-bytes", type=int, default=DEFAULT_LOG_BYTES)
    try:
        options = parser.parse_args(argv)
    except SystemExit as leaving:
        if leaving.code == 0:
            raise
        options = None
    try:
        if options is None or not options.harness:
            raise Skip("the registration gives no valid --harness")
        if not 4096 <= options.max_log_bytes <= 64 * 1024 * 1024:
            raise Skip("--max-log-bytes must be between 4096 and 67108864")
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, out_of_time)
            signal.alarm(TIME_LIMIT_SECONDS)
        event = read_event(sys.stdin.buffer)
        real, given = workspace_roots(options)
        data = activity_line(options, event, (real, given))
        append(log_folder(real), data, options.harness, options.max_log_bytes)
    except Skip as skip:
        sys.stderr.write("log-tool-activity: %s; not recorded\n" % skip)
    except Exception as error:  # noqa: BLE001 - a logger never blocks the agent
        sys.stderr.write("log-tool-activity: %s; not recorded\n" % type(error).__name__)
    sys.stdout.write("{}\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

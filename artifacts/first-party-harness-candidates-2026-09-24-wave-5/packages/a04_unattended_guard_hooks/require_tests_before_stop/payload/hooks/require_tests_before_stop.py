"""Effects: reads one JSON event on standard input, the step policy file and this hook's state file; writes only .baltor/state/require-tests-before-stop/ under the workspace and one JSON answer to standard output; makes no network call and starts no program.

Test-before-finish gate for a coding harness.

After each tool call the hook records two kinds of fact in its state file: a
source file was edited, or the declared test command ran. When the agent tries
to finish, the hook compares the two. If a source file changed after the last
recorded test run, it blocks the finish once and names the test command to
run. A second attempt to finish for the same changes is let through and
counted as a finish without tests, so the agent can never be kept running
without end.

Usage:
    python3 -I -B require_tests_before_stop.py --harness claude_code|cursor|copilot [--event NAME] [--root DIR] [--policy FILE]
    python3 -I -B require_tests_before_stop.py --check-policy [--root DIR] [--policy FILE]

Events: Claude Code PostToolUse, PostToolUseFailure and Stop (shell tools Bash,
PowerShell and Monitor); Cursor afterShellExecution, afterFileEdit and stop;
Copilot postToolUse and agentStop (pass --event for Copilot). The policy file
defaults to <root>/.baltor/step/require-tests-before-stop.json. The package
places a default there for Python projects tested with pytest; the host
replaces it with the step's own policy and a new step_id before launch and can
validate it with --check-policy (exit 0 valid, 1 refused):
    {"record_type": "tests_before_stop_policy/v1", "step_id": "ticket-42-step-3",
     "test_commands": [["python3", "-m", "pytest"]],
     "source_globs": ["src/**", "tests/**"], "ignore_globs": [".baltor/**", "**/*.md"],
     "excluded_arguments": ["--collect-only", "--version", "--help"]}

A shell line counts as a test run when one of its parts starts with a test
command, holds no excluded argument, does not run in the background with &
and does not follow ||, which runs it only when an earlier part failed.

Claude Code worktrees: when the event's cwd lies in .claude/worktrees/<name>/,
a real folder that holds a .git file, edited paths are matched relative to
that worktree, so source_globs mean the same inside it.

This gate fails open: when it cannot read its input, policy or state, it lets
the finish happen and writes one diagnostic line to standard error, which
Claude Code keeps in its debug log only. Licensed MIT, like the rest of this
package.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import functools
import json
import os
import re
import shlex
import signal
import stat
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

try:
    import fcntl
except ImportError:  # not available on Windows; state updates are then unlocked
    fcntl = None

NATIVE_NAME = "require-tests-before-stop"
POLICY_RECORD = "tests_before_stop_policy/v1"
STATE_RECORD = "tests_before_stop_state/v1"
DEFAULT_POLICY = Path(".baltor") / "step" / (NATIVE_NAME + ".json")
STATE_FOLDER = Path(".baltor") / "state" / NATIVE_NAME
HARNESSES = ("claude_code", "cursor", "copilot")
MAX_EVENT_BYTES = 1024 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_CHANGED = 20
TIME_LIMIT_SECONDS = 8
STEP_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
EDIT_TOOLS = {"claude_code": {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path",
                              "NotebookEdit": "notebook_path"},
              "copilot": {"create": "path", "edit": "path"}}
SHELL_TOOLS = {"claude_code": ("Bash", "PowerShell", "Monitor"), "copilot": ("bash", "powershell")}
# Arguments that make a test command list, describe or plan tests instead of running them.
DEFAULT_EXCLUDED = ("--help", "-h", "--version", "--collect-only", "--co", "--fixtures", "--markers",
                    "--setup-plan", "--dry-run")
WORKTREE_PARTS = (".claude", "worktrees")


class Skip(Exception):
    """The hook cannot use its input, policy or state; the finish is let through."""


class Policy(NamedTuple):
    step_id: str
    test_commands: tuple
    source_globs: tuple
    ignore_globs: tuple
    excluded_arguments: tuple = DEFAULT_EXCLUDED


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


def glob_match(pattern: str, path: str) -> bool:
    wanted, parts = tuple(pattern.split("/")), tuple(path.split("/"))

    @functools.lru_cache(maxsize=None)
    def match(i: int, j: int) -> bool:
        if i == len(wanted):
            return j == len(parts)
        if wanted[i] == "**":
            return any(match(i + 1, k) for k in range(j, len(parts) + 1))
        return j < len(parts) and fnmatch.fnmatchcase(parts[j], wanted[i]) and match(i + 1, j + 1)

    return match(0, 0)


def shown(text: str, limit: int = 80) -> str:
    clean = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)
    return clean if len(clean) <= limit else "..." + clean[-(limit - 3):]


# ---------------------------------------------------------------------------
# Root, policy and state
# ---------------------------------------------------------------------------

def workspace_root(options) -> tuple:
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


def read_small_file(path: Path, follow: bool = True) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | (0 if follow else getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(str(path), flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Skip("%s is not a regular file" % path.name)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise Skip("%s is larger than 256 KiB" % path.name)
    return raw


def token_lists(value, name: str, required: bool) -> tuple:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise Skip("%s is a list of 1 to 10 commands" % name)
    result = []
    for command in value:
        if not isinstance(command, list) or not 1 <= len(command) <= 8 or any(
                not isinstance(token, str) or not token or len(token) > 100 or any(ch.isspace() for ch in token)
                for token in command):
            raise Skip("each test command is a list of 1 to 8 tokens without spaces")
        result.append(tuple(command))
    return tuple(result)


def pattern_list(value, name: str, default: tuple) -> tuple:
    if value is None:
        return default
    if not isinstance(value, list) or len(value) > 100 or any(
            not isinstance(item, str) or not item or len(item) > 200 or item.startswith("/")
            or ".." in item.split("/") for item in value):
        raise Skip("%s is a list of root-relative patterns" % name)
    return tuple(value)


def argument_list(value) -> tuple:
    if value is None:
        return DEFAULT_EXCLUDED
    if not isinstance(value, list) or len(value) > 50 or any(
            not isinstance(item, str) or not 2 <= len(item) <= 100 or not item.startswith("-")
            or any(ch.isspace() for ch in item) for item in value):
        raise Skip("excluded_arguments is a list of at most 50 options that start with -")
    return tuple(value)


def load_policy(options, root: Path) -> Policy:
    if options.policy and Path(options.policy).is_absolute():
        path = Path(options.policy)
    else:
        path = root / (Path(options.policy) if options.policy else DEFAULT_POLICY)
    try:
        document = strict_json(read_small_file(path))
    except FileNotFoundError as error:
        raise Skip("there is no policy file") from error
    except (OSError, ValueError) as error:
        raise Skip("the policy file cannot be read") from error
    allowed = {"record_type", "step_id", "test_commands", "source_globs", "ignore_globs", "excluded_arguments"}
    if not isinstance(document, dict) or document.get("record_type") != POLICY_RECORD or set(document) - allowed:
        raise Skip("the policy file is not a %s record" % POLICY_RECORD)
    step_id = document.get("step_id")
    if not isinstance(step_id, str) or not STEP_ID.fullmatch(step_id):
        raise Skip("the policy step_id is missing or not a short identifier")
    return Policy(step_id, token_lists(document.get("test_commands"), "test_commands", True),
                  pattern_list(document.get("source_globs"), "source_globs", ("**",)),
                  pattern_list(document.get("ignore_globs"), "ignore_globs", (".baltor/**", "**/*.md")),
                  argument_list(document.get("excluded_arguments")))


def state_folder(root: Path) -> Path:
    """Create the state folder one level at a time, never through a symbolic link."""
    current = root
    for part in STATE_FOLDER.parts:
        current = current / part
        if current.is_symlink():
            raise Skip("the state folder leads through a symbolic link")
        if not current.exists():
            current.mkdir()
        elif not current.is_dir():
            raise Skip("the state folder path is not a folder")
    return current


def fresh_state(step_id: str) -> dict:
    return {"record_type": STATE_RECORD, "step_id": step_id, "sequence": 0, "last_edit": 0, "last_test": 0,
            "blocked_for_edit": 0, "changed_paths": [], "last_test_at": "", "finishes_without_tests": 0}


def load_state(folder: Path, step_id: str) -> tuple:
    """Return (state, reset) where reset says an older step's record was replaced."""
    try:
        document = strict_json(read_small_file(folder / "state.json", follow=False))
    except FileNotFoundError:
        return fresh_state(step_id), False
    except (OSError, ValueError) as error:
        raise Skip("the state file cannot be read") from error
    expected = fresh_state(step_id)
    if not isinstance(document, dict) or set(document) != set(expected) or document.get("record_type") != STATE_RECORD:
        raise Skip("the state file is not a %s record" % STATE_RECORD)
    if document["step_id"] != step_id:
        return expected, True  # a new step starts with a clean record
    numbers = ("sequence", "last_edit", "last_test", "blocked_for_edit", "finishes_without_tests")
    if any(type(document[name]) is not int or document[name] < 0 for name in numbers) \
            or not isinstance(document["changed_paths"], list) or not isinstance(document["last_test_at"], str):
        raise Skip("the state file holds values of the wrong type")
    return document, False


def save_state(folder: Path, state: dict) -> None:
    handle, temporary = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=str(folder))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(state, indent=1, sort_keys=True) + "\n")
        os.replace(temporary, folder / "state.json")
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


# ---------------------------------------------------------------------------
# Reading events
# ---------------------------------------------------------------------------

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


def tool_arguments(event: dict):
    arguments = event.get("toolArgs")
    if isinstance(arguments, str):
        try:
            arguments = strict_json(arguments.encode("utf-8"))
        except ValueError:
            return {}
    return arguments if isinstance(arguments, dict) else {}


def classify(event: dict, harness: str, event_name: str) -> tuple:
    """Return (kind, value): ("test", command), ("edit", path), ("stop", None) or ("other", None)."""
    if harness == "claude_code":
        name = event_name or event.get("hook_event_name")
        if name == "Stop":
            return "stop", None
        tool, arguments = event.get("tool_name"), event.get("tool_input")
        arguments = arguments if isinstance(arguments, dict) else {}
        if name in ("PostToolUse", "PostToolUseFailure") and tool in SHELL_TOOLS[harness]:
            if name == "PostToolUseFailure" and event.get("is_interrupt") is True:
                return "other", None  # an interrupted run gave no result to read
            return "test", arguments.get("command")
        if name == "PostToolUse" and tool in EDIT_TOOLS[harness]:
            return "edit", arguments.get(EDIT_TOOLS[harness][tool])
        return "other", None
    if harness == "cursor":
        name = event_name or event.get("hook_event_name")
        if name == "stop":
            return ("stop", None) if event.get("status", "completed") == "completed" else ("other", None)
        if name == "afterShellExecution":
            return "test", event.get("command")
        if name == "afterFileEdit":
            return "edit", event.get("file_path")
        return "other", None
    name = event_name or ("postToolUse" if "toolName" in event else "agentStop")
    if name == "agentStop":
        return "stop", None
    if name != "postToolUse":
        return "other", None
    result = event.get("toolResult")
    if isinstance(result, dict) and result.get("resultType") == "denied":
        return "other", None
    tool, arguments = event.get("toolName"), tool_arguments(event)
    if tool in SHELL_TOOLS[harness]:
        return "test", arguments.get("command")
    if tool in EDIT_TOOLS[harness]:
        return "edit", arguments.get(EDIT_TOOLS[harness][tool])
    return "other", None


def runs_a_test(command, policy: Policy) -> bool:
    if not isinstance(command, str) or len(command) > 65536:
        return False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return False
    parts, current, before = [], [], ""
    for token in tokens:
        if token and all(ch in ";&|()" for ch in token):
            parts.append((current, before, token))
            current, before = [], token
        else:
            current.append(token)
    parts.append((current, before, ""))
    for words, before, after in parts:
        if before == "||" or after == "&":
            continue  # runs only when an earlier part failed, or runs in the background
        while words and ASSIGNMENT.match(words[0]):
            words = words[1:]
        if not any(tuple(words[:len(command_start)]) == command_start for command_start in policy.test_commands):
            continue
        if any(word.split("=", 1)[0] in policy.excluded_arguments for word in words):
            continue  # lists, describes or plans the tests without running them
        return True
    return False


def claude_worktree(cwd, real: Path, given: Path):
    """(real, given) of the Claude Code worktree folder that holds cwd, or None.

    Only .claude/worktrees/<name> directly under the root counts, when none of its three
    folders is a symbolic link and it holds a .git regular file, as a git worktree does.
    """
    if not isinstance(cwd, str) or not cwd or "\x00" in cwd or not os.path.isabs(cwd):
        return None
    folder = os.path.normpath(cwd)
    for root in (given, real):
        try:
            parts = Path(folder).relative_to(root).parts
        except ValueError:
            continue
        if len(parts) < 3 or tuple(parts[:2]) != WORKTREE_PARTS:
            return None
        current = real
        for part in (*WORKTREE_PARTS, parts[2]):
            current = current / part
            if current.is_symlink() or not current.is_dir():
                return None
        marker = current / ".git"
        if marker.is_symlink() or not marker.is_file():
            return None
        return Path(os.path.realpath(current)), given.joinpath(*WORKTREE_PARTS, parts[2])
    return None


def source_path(path, event: dict, roots: tuple, policy: Policy):
    if not isinstance(path, str) or not path or "\x00" in path or len(path) > 4096:
        return None
    base = event.get("cwd") if isinstance(event.get("cwd"), str) and os.path.isabs(event.get("cwd", "")) else str(roots[0])
    joined = os.path.normpath(os.path.join(base, path))
    for root in roots:
        try:
            relative = Path(joined).relative_to(root).as_posix()
        except ValueError:
            continue
        if relative == ".":
            return None
        if any(glob_match(pattern, relative) for pattern in policy.source_globs) \
                and not any(glob_match(pattern, relative) for pattern in policy.ignore_globs):
            return relative
        return None
    return None


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def block(harness: str, reason: str) -> dict:
    if harness == "cursor":
        return {"followup_message": reason}
    return {"decision": "block", "reason": reason}


def reminder(state: dict, policy: Policy) -> str:
    changed = [shown(item) for item in state["changed_paths"][:3]]
    extra = len(state["changed_paths"]) - len(changed)
    listed = ", ".join(changed) if changed else "source files"
    if extra > 0:
        listed += " and %d more" % extra
    commands = "; ".join(" ".join(command) for command in policy.test_commands)
    return ("Source files changed after the last test run: %s. Before you finish, run this test command and read its "
            "result: %s. Fix failures your change caused, or write them into your handoff. Then finish. "
            "This reminder is given once for these changes." % (listed, commands))


def apply_event(options, state: dict, policy: Policy, kind: str, value, event: dict, roots: tuple) -> dict:
    if kind == "test" and runs_a_test(value, policy):
        state["sequence"] += 1
        state["last_test"] = state["sequence"]
        state["changed_paths"] = []
        state["last_test_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif kind == "edit":
        relative = source_path(value, event, roots, policy)
        if relative is not None:
            state["sequence"] += 1
            state["last_edit"] = state["sequence"]
            if relative not in state["changed_paths"] and len(state["changed_paths"]) < MAX_CHANGED:
                state["changed_paths"].append(relative)
    elif kind == "stop" and state["last_edit"] > state["last_test"]:
        already = state["blocked_for_edit"] == state["last_edit"] or event.get("stop_hook_active") is True
        if already:
            state["finishes_without_tests"] += 1
        else:
            state["blocked_for_edit"] = state["last_edit"]
            return block(options.harness, reminder(state, policy))
    return {}


def decide(options) -> dict:
    event = read_event(sys.stdin.buffer)
    kind, value = classify(event, options.harness, options.event or "")
    if kind == "other":
        return {}
    real, given = workspace_root(options)
    policy = load_policy(options, real)
    roots = (given, real)
    if kind == "edit" and options.harness == "claude_code":
        worktree = claude_worktree(event.get("cwd"), real, given)
        if worktree is not None:
            roots = (worktree[1], worktree[0], given, real)
    folder = state_folder(real)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    lock = os.open(str(folder / "lock"), flags, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        state, reset = load_state(folder, policy.step_id)
        before = json.dumps(state, sort_keys=True)
        answer = apply_event(options, state, policy, kind, value, event, roots)
        if reset or json.dumps(state, sort_keys=True) != before:
            save_state(folder, state)
    finally:
        os.close(lock)
    return answer


def out_of_time(_signal_number, _frame):
    raise TimeoutError("time limit")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Block a finish once when source files changed after the last test run.")
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--event", help="hook event name; needed for Copilot, whose events carry no name")
    parser.add_argument("--root", help="workspace root; defaults to the harness project folder")
    parser.add_argument("--policy", help="policy file; relative paths start at the workspace root")
    parser.add_argument("--check-policy", action="store_true", help="validate the policy and exit (0 valid, 1 refused)")
    try:
        options = parser.parse_args(argv)
    except SystemExit as leaving:
        if leaving.code == 0:
            raise
        options = None  # exit status 2 would block a Claude Code finish, so a bad registration is let through
    if options is not None and options.check_policy:
        try:
            real, _given = workspace_root(options)
            policy = load_policy(options, real)
        except Skip as error:
            print(json.dumps({"policy": "refused", "reason": str(error)}))
            return 1
        print(json.dumps({"policy": "valid", "step_id": policy.step_id,
                          "test_commands": [" ".join(command) for command in policy.test_commands],
                          "source_globs": list(policy.source_globs), "ignore_globs": list(policy.ignore_globs),
                          "excluded_arguments": list(policy.excluded_arguments)}))
        return 0
    if options is None or not options.harness:
        sys.stderr.write("require-tests-before-stop: the registration gives no valid --harness; nothing was blocked\n")
        sys.stdout.write("{}\n")
        return 0
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, out_of_time)
        signal.alarm(TIME_LIMIT_SECONDS)
    try:
        answer = decide(options)
    except Skip as skip:
        sys.stderr.write("require-tests-before-stop: %s; nothing was blocked\n" % skip)
        answer = {}
    except Exception as error:  # noqa: BLE001 - this gate fails open
        sys.stderr.write("require-tests-before-stop: %s; nothing was blocked\n" % type(error).__name__)
        answer = {}
    sys.stdout.write(json.dumps(answer, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Effects: reads one JSON event on standard input, the step budget policy and this hook's state file; writes only .baltor/state/cap-tool-call-budget/ under the workspace and one JSON answer to standard output; makes no network call and starts no program.

Tool call budget guard for a coding harness, run before each tool call.

The hook counts the tool calls it lets through in the current step. Once the
count reaches the declared ceiling, it refuses every further call and tells
the agent to write its handoff. Reads and writes of the declared handoff file
stay allowed after the ceiling, up to a small separate allowance, so the agent
can still leave its handoff. The guard never widens what the harness allows:
Claude Code and Copilot get the empty object {} for an allowed call, which
leaves the decision to the harness's own permission settings. Cursor documents
an answer that always names a permission, so there an allowed call gets
{"permission": "allow"}.

Ending the session: every refused call is counted. In Claude Code, the refusal
that brings the count to max_refused_calls also answers "continue": false,
which the hook reference documents as ending Claude's work. Cursor and Copilot
document no such answer for a tool call, so there the hook keeps refusing and
each refusal costs one more model turn until the harness's own limits apply.

Usage:
    python3 -I -B cap_tool_calls.py --harness claude_code|cursor|copilot [--root DIR] [--policy FILE]
    python3 -I -B cap_tool_calls.py --check-policy [--root DIR] [--policy FILE]

The policy file defaults to <root>/.baltor/step/cap-tool-call-budget.json. The
package places a default there (200 calls); the host replaces it with the
step's own budget and a new step_id before launch:
    {"record_type": "tool_call_budget_policy/v1", "step_id": "ticket-42-step-3",
     "max_tool_calls": 40, "handoff_path": ".baltor/step/handoff.md", "max_handoff_calls": 5,
     "max_refused_calls": 5}

A new step_id starts a new count. The count lives in files under the
workspace, so the cap holds only while the agent cannot edit the policy or
the state: pair it with the workspace write guard and the shell command
allowlist. Malformed input, a missing or invalid policy, an unreadable state
and internal errors are refused (fail closed). Licensed MIT, like the rest of
this package.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import stat
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

try:
    import fcntl
except ImportError:  # not available on Windows; counting is then unlocked
    fcntl = None

NATIVE_NAME = "cap-tool-call-budget"
POLICY_RECORD = "tool_call_budget_policy/v1"
STATE_RECORD = "tool_call_budget_state/v1"
DEFAULT_POLICY = Path(".baltor") / "step" / (NATIVE_NAME + ".json")
STATE_FOLDER = Path(".baltor") / "state" / NATIVE_NAME
HARNESSES = ("claude_code", "cursor", "copilot")
MAX_EVENT_BYTES = 1024 * 1024
MAX_FILE_BYTES = 64 * 1024
TIME_LIMIT_SECONDS = 8
STEP_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
FILE_TOOLS = {"claude_code": {"Read": ("file_path",), "Write": ("file_path",), "Edit": ("file_path",),
                              "MultiEdit": ("file_path",)},
              "cursor": {"Read": ("file_path", "path"), "Write": ("file_path", "path")},
              "copilot": {"view": ("path",), "create": ("path",), "edit": ("path",)}}


class Refusal(Exception):
    """The call is refused; the text is shown to the model."""


class Policy(NamedTuple):
    step_id: str
    max_calls: int
    handoff_path: str
    max_handoff_calls: int
    label: str
    max_refused_calls: int = 5


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


def read_small_file(path: Path, follow: bool) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | (0 if follow else getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(str(path), flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("larger than 64 KiB")
    return raw


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
        raise Refusal("the workspace root is unknown")
    real = Path(os.path.realpath(value))
    if not real.is_dir() or real == Path(real.anchor):
        raise Refusal("the workspace root is not a usable folder")
    return real, Path(os.path.abspath(value))


def whole_number(document: dict, name: str, low: int, high: int, default=None) -> int:
    value = document.get(name, default)
    if type(value) is not int or not low <= value <= high:
        raise Refusal("the budget policy field %s is a whole number from %d to %d" % (name, low, high))
    return value


def load_policy(options, root: Path) -> Policy:
    if options.policy and Path(options.policy).is_absolute():
        path, label = Path(options.policy), Path(options.policy).name
    else:
        relative = Path(options.policy) if options.policy else DEFAULT_POLICY
        path, label = root / relative, relative.as_posix()
    try:
        document = strict_json(read_small_file(path, follow=True))
    except FileNotFoundError as error:
        raise Refusal("there is no budget policy file at %s" % label) from error
    except (OSError, ValueError) as error:
        raise Refusal("the budget policy file %s cannot be read" % label) from error
    allowed = {"record_type", "step_id", "max_tool_calls", "handoff_path", "max_handoff_calls", "max_refused_calls"}
    if not isinstance(document, dict) or document.get("record_type") != POLICY_RECORD or set(document) - allowed:
        raise Refusal("the budget policy file is not a %s record" % POLICY_RECORD)
    step_id = document.get("step_id")
    if not isinstance(step_id, str) or not STEP_ID.fullmatch(step_id):
        raise Refusal("the budget policy step_id is missing or not a short identifier")
    handoff = document.get("handoff_path", ".baltor/step/handoff.md")
    if not isinstance(handoff, str) or not handoff or len(handoff) > 200 or handoff.startswith("/") \
            or "\\" in handoff or any(part in ("", ".", "..") for part in handoff.split("/")):
        raise Refusal("the budget policy handoff_path is a plain root-relative file path")
    return Policy(step_id, whole_number(document, "max_tool_calls", 0, 100000), handoff,
                  whole_number(document, "max_handoff_calls", 0, 50, 5), label,
                  whole_number(document, "max_refused_calls", 1, 100, 5))


def state_folder(root: Path) -> Path:
    """Create the state folder one level at a time, never through a symbolic link."""
    current = root
    for part in STATE_FOLDER.parts:
        current = current / part
        if current.is_symlink():
            raise Refusal("the budget state folder leads through a symbolic link")
        if not current.exists():
            current.mkdir()
        elif not current.is_dir():
            raise Refusal("the budget state folder path is not a folder")
    return current


def load_state(folder: Path, step_id: str) -> dict:
    fresh = {"record_type": STATE_RECORD, "step_id": step_id, "calls_used": 0, "handoff_calls_used": 0,
             "refused_calls": 0}
    try:
        document = strict_json(read_small_file(folder / "state.json", follow=False))
    except FileNotFoundError:
        return fresh
    except (OSError, ValueError) as error:
        raise Refusal("the budget state file cannot be read") from error
    if not isinstance(document, dict) or set(document) != set(fresh) or document.get("record_type") != STATE_RECORD:
        raise Refusal("the budget state file is not a %s record" % STATE_RECORD)
    if document["step_id"] != step_id:
        return fresh  # a new step starts a new count
    if any(type(document[name]) is not int or document[name] < 0
           for name in ("calls_used", "handoff_calls_used", "refused_calls")):
        raise Refusal("the budget state file holds values of the wrong type")
    return document


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
# Events and the decision
# ---------------------------------------------------------------------------

class InputError(Exception):
    """The event on standard input cannot be read as one tool call."""


def read_event(stream) -> dict:
    raw = stream.read(MAX_EVENT_BYTES + 1)
    if len(raw) > MAX_EVENT_BYTES:
        raise InputError("the event is larger than 1 MiB")
    try:
        event = strict_json(raw)
    except ValueError as error:
        raise InputError("the event is not valid JSON") from error
    if not isinstance(event, dict):
        raise InputError("the event is not a JSON object")
    return event


def tool_call(event: dict, harness: str):
    """Return (tool, arguments) of a before-call event, or None for other events."""
    if harness == "copilot":
        tool, arguments = event.get("toolName"), event.get("toolArgs")
        if isinstance(arguments, str):
            try:
                arguments = strict_json(arguments.encode("utf-8"))
            except ValueError:
                arguments = {}
    else:
        default = "PreToolUse" if harness == "claude_code" else "preToolUse"
        if event.get("hook_event_name", default) != default:
            return None
        tool, arguments = event.get("tool_name"), event.get("tool_input")
    if not isinstance(tool, str) or not tool:
        raise InputError("the event names no tool")
    return tool, arguments if isinstance(arguments, dict) else {}


def is_handoff_call(tool: str, arguments: dict, event: dict, harness: str, roots: tuple, policy: Policy) -> bool:
    fields = FILE_TOOLS[harness].get(tool)
    if not fields:
        return False
    raw = next((arguments[name] for name in fields if isinstance(arguments.get(name), str)), None)
    if not raw or "\x00" in raw or len(raw) > 4096:
        return False
    real, given = roots
    cwd = event.get("cwd")
    base = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else str(given)
    target = os.path.normpath(os.path.join(base, raw))
    wanted = {os.path.normpath(os.path.join(str(root), policy.handoff_path)) for root in roots}
    if target not in wanted:
        return False
    # No symbolic link may redirect the handoff path, not even to a file inside the workspace.
    return os.path.realpath(target) == os.path.normpath(os.path.join(str(real), policy.handoff_path))


def allow(harness: str) -> dict:
    """The answer for a call this guard does not refuse."""
    return {"permission": "allow"} if harness == "cursor" else {}


def deny(harness: str, reason: str) -> dict:
    if harness == "claude_code":
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}
    if harness == "cursor":
        return {"permission": "deny", "user_message": reason, "agent_message": reason}
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def end_session(harness: str, reason: str, refused: int) -> dict:
    """The refusal that also ends the session where the harness documents a way to do so."""
    answer = deny(harness, reason)
    if harness == "claude_code":
        answer["continue"] = False
        answer["stopReason"] = ("The tool call budget of this step is used and %d further calls were refused, so "
                                "the tool call budget hook ended the session." % refused)
    return answer


def budget_decision(state: dict, policy: Policy, handoff: bool) -> str:
    """Update the counters; return "" to allow, or the refusal text."""
    if state["calls_used"] < policy.max_calls:
        state["calls_used"] += 1
        return ""
    if handoff and state["handoff_calls_used"] < policy.max_handoff_calls:
        state["handoff_calls_used"] += 1
        return ""
    state["refused_calls"] += 1
    left = policy.max_handoff_calls - state["handoff_calls_used"]
    if left <= 0:
        return ("this step has used its tool calls and its handoff allowance. Make no more tool calls. Finish now "
                "and put what is done, what is not done and the next action in your final message.")
    return ("this step has used all %d of its tool calls. Do not start new work. Write your handoff now to %s with "
            "one file write: what is done, what is not done, and the exact next action. Then finish. "
            "Handoff calls left: %d." % (policy.max_calls, policy.handoff_path, left))


def decide(options) -> dict:
    harness = options.harness
    prefix = "Refused by the tool call budget: "
    try:
        event = read_event(sys.stdin.buffer)
        call = tool_call(event, harness)
    except InputError as error:
        return deny(harness, prefix + "the hook could not read this tool call (%s). Stop and report this to the host." % error)
    if call is None:
        return allow(harness)
    tool, arguments = call
    try:
        roots = workspace_root(options)
        policy = load_policy(options, roots[0])
        folder = state_folder(roots[0])
    except Refusal as error:
        return deny(harness, prefix + "%s. No tool call can run in this step. Stop and report this to the host." % error)
    handoff = is_handoff_call(tool, arguments, event, harness, roots, policy)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    lock = os.open(str(folder / "lock"), flags, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = load_state(folder, policy.step_id)
        except Refusal as error:
            return deny(harness, prefix + "%s. Stop and report this to the host." % error)
        refusal = budget_decision(state, policy, handoff)
        save_state(folder, state)
    finally:
        os.close(lock)
    if not refusal:
        return allow(harness)
    if state["refused_calls"] >= policy.max_refused_calls:
        return end_session(harness, prefix + refusal, state["refused_calls"])
    return deny(harness, prefix + refusal)


def out_of_time(_signal_number, _frame):
    raise TimeoutError("time limit")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refuse tool calls after the step's declared ceiling.")
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--root", help="workspace root; defaults to the harness project folder")
    parser.add_argument("--policy", help="budget policy file; relative paths start at the workspace root")
    parser.add_argument("--check-policy", action="store_true", help="validate the policy and exit")
    options = parser.parse_args(argv)
    if options.check_policy:
        try:
            real, _given = workspace_root(options)
            policy = load_policy(options, real)
        except Refusal as error:
            print(json.dumps({"policy": "refused", "reason": str(error)}))
            return 1
        print(json.dumps({"policy": "valid", "path": policy.label, "step_id": policy.step_id,
                          "max_tool_calls": policy.max_calls, "handoff_path": policy.handoff_path,
                          "max_handoff_calls": policy.max_handoff_calls,
                          "max_refused_calls": policy.max_refused_calls}))
        return 0
    if not options.harness:
        parser.error("--harness is required")
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, out_of_time)
        signal.alarm(TIME_LIMIT_SECONDS)
    try:
        answer = decide(options)
    except TimeoutError:
        answer = deny(options.harness, "Refused by the tool call budget: the hook ran out of time. Stop and report this to the host.")
    except Exception:  # noqa: BLE001 - a guard refuses when it cannot decide
        answer = deny(options.harness, "Refused by the tool call budget: the hook failed inside. Stop and report this to the host.")
    sys.stdout.write(json.dumps(answer, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

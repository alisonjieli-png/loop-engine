"""Effects: reads one JSON event on standard input, the step write policy file and file metadata under the workspace; writes one JSON answer to standard output; writes no file, makes no network call and starts no program.

Workspace write guard, run by a coding harness before each file write, edit or
delete made with its file tools. Writes made by shell commands are not seen.

The guard resolves the target path the way the operating system would,
following symbolic links, and refuses the tool call when the real target is
outside the workspace root, inside version control metadata (.git, .hg, .svn,
.bzr), inside the harness and step folders (.baltor, .claude, .cursor,
.github/hooks), on a protected path that the step policy declares, not a
regular file, or a file with other hard links. The guard never widens what the
harness allows: Claude Code and Copilot get the empty object {} for an allowed
call, which leaves the decision to the harness's own permission settings.
Cursor documents an answer that always names a permission, so there an allowed
call gets {"permission": "allow"}.

Claude Code worktrees: Claude Code keeps CLAUDE_PROJECT_DIR at the main
checkout and moves the event's cwd into .claude/worktrees/<name>/ when the
session or a subagent works in a worktree. When the cwd lies in such a folder,
and the folder is a real folder that holds a .git file as git worktrees do,
that folder is the workspace root for the check; the policy is still read from
the main checkout.

Usage:
    python3 -I -B guard_file_writes.py --harness claude_code|cursor|copilot [--root DIR] [--policy FILE]
    python3 -I -B guard_file_writes.py --check-policy [--root DIR] [--policy FILE]

The policy file defaults to <root>/.baltor/step/guard-workspace-file-writes.json.
The package places a default there that also protects files that widen a later
session's authority (instruction files, protocol server and editor settings,
workflows); the host replaces it with the step's own policy before launch:
    {"record_type": "workspace_write_guard/v1",
     "protected_globs": ["data/raw/**", "**/*.lock", ".mcp.json", "**/AGENTS.md"],
     "writable_globs": [".baltor/step/handoff.md"]}

Patterns are relative to the workspace root; * stays inside one folder and **
spans folders. Protected patterns match without regard to letter case.
writable_globs may only reopen paths inside the built-in harness and step
folders. Malformed input, a missing or invalid policy and internal errors are
refused (fail closed). Licensed MIT, like the rest of this package.
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
import json
import os
import signal
import stat
import sys
from pathlib import Path
from typing import NamedTuple

NATIVE_NAME = "guard-workspace-file-writes"
POLICY_RECORD = "workspace_write_guard/v1"
DEFAULT_POLICY = Path(".baltor") / "step" / (NATIVE_NAME + ".json")
HARNESSES = ("claude_code", "cursor", "copilot")
MAX_EVENT_BYTES = 1024 * 1024
MAX_POLICY_BYTES = 256 * 1024
MAX_PATH_CHARS = 4096
MAX_REASON_CHARS = 1000
TIME_LIMIT_SECONDS = 8
VERSION_CONTROL = frozenset({".git", ".hg", ".svn", ".bzr"})
BUILT_IN = ((".baltor/**", ".baltor"), (".claude/**", ".claude"), (".cursor/**", ".cursor"),
            (".github/hooks/**", ".github/hooks"))
WORKTREE_PARTS = (".claude", "worktrees")
WRITE_TOOLS = {
    "claude_code": {"Write": ("file_path",), "Edit": ("file_path",), "MultiEdit": ("file_path",),
                    "NotebookEdit": ("notebook_path",)},
    "cursor": {"Write": ("file_path", "path"), "Delete": ("file_path", "path")},
    "copilot": {"create": ("path",), "edit": ("path",)},
}


class Refusal(Exception):
    """A write this guard refuses. The text is shown to the model."""


class InputError(Exception):
    """The event on standard input cannot be read as one tool call."""


class PolicyError(Exception):
    """The step write policy or the workspace root cannot be used."""


class Policy(NamedTuple):
    protected: tuple
    writable: tuple
    label: str


class Target(NamedTuple):
    raw: str
    base: str


class Root(NamedTuple):
    real: Path
    given: Path
    label: str = "the workspace folder"


def shown(text: str, limit: int = 120) -> str:
    clean = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)
    return clean if len(clean) <= limit else "..." + clean[-(limit - 3):]


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


def glob_match(pattern: str, path: str, fold: bool) -> bool:
    """Match a root-relative path; * stays inside one folder and ** spans folders."""
    if fold:
        pattern, path = pattern.casefold(), path.casefold()
    wanted, parts = tuple(pattern.split("/")), tuple(path.split("/"))

    @functools.lru_cache(maxsize=None)
    def match(i: int, j: int) -> bool:
        if i == len(wanted):
            return j == len(parts)
        if wanted[i] == "**":
            return any(match(i + 1, k) for k in range(j, len(parts) + 1))
        return j < len(parts) and fnmatch.fnmatchcase(parts[j], wanted[i]) and match(i + 1, j + 1)

    return match(0, 0)


# ---------------------------------------------------------------------------
# Root and policy
# ---------------------------------------------------------------------------

def workspace_root(options) -> Root:
    if options.root:
        value = options.root
    elif options.harness == "claude_code":
        value = os.environ.get("CLAUDE_PROJECT_DIR", "")
    elif options.harness == "cursor":
        value = os.environ.get("CURSOR_PROJECT_DIR", "") or os.environ.get("CLAUDE_PROJECT_DIR", "")
    else:
        value = os.getcwd()  # the Copilot registration starts the hook in the repository root
    if not value:
        raise PolicyError("the workspace root is unknown")
    real = Path(os.path.realpath(value))
    if not real.is_dir():
        raise PolicyError("the workspace root is not a folder")
    if real == Path(real.anchor):
        raise PolicyError("the workspace root is the filesystem root")
    return Root(real, Path(os.path.abspath(value)))


def valid_pattern(pattern) -> bool:
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 200 or pattern.startswith("/") \
            or "\\" in pattern or any(ord(ch) < 32 for ch in pattern):
        return False
    parts = pattern.split("/")
    return len(parts) <= 32 and parts.count("**") <= 4 and all(part and part not in (".", "..") for part in parts)


def read_policy_bytes(path: Path) -> bytes:
    try:
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError as error:
        raise PolicyError("there is no write policy file") from error
    except OSError as error:
        raise PolicyError("the write policy file cannot be opened") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PolicyError("the write policy path is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_POLICY_BYTES:
        raise PolicyError("the write policy file is larger than 256 KiB")
    return raw


def parse_policy(raw: bytes, label: str) -> Policy:
    try:
        document = strict_json(raw)
    except ValueError as error:
        raise PolicyError("the write policy file is not valid JSON") from error
    if not isinstance(document, dict) or document.get("record_type") != POLICY_RECORD:
        raise PolicyError("the write policy file is not a %s record" % POLICY_RECORD)
    if set(document) - {"record_type", "protected_globs", "writable_globs"}:
        raise PolicyError("the write policy file has unknown fields")
    protected = document.get("protected_globs", [])
    writable = document.get("writable_globs", [])
    for name, patterns in (("protected_globs", protected), ("writable_globs", writable)):
        if not isinstance(patterns, list) or len(patterns) > 200 or not all(valid_pattern(item) for item in patterns):
            raise PolicyError("%s is a list of at most 200 root-relative patterns without .. parts" % name)
    for pattern in writable:
        inside = any(pattern.startswith(folder + "/") for _glob, folder in BUILT_IN)
        if not inside or any(part.casefold() in VERSION_CONTROL for part in pattern.split("/")):
            raise PolicyError("writable_globs may only reopen paths inside .baltor, .claude, .cursor or .github/hooks")
    return Policy(tuple(protected), tuple(writable), label)


def load_policy(options, root: Root) -> Policy:
    if options.policy and Path(options.policy).is_absolute():
        path, label = Path(options.policy), Path(options.policy).name
    else:
        relative = Path(options.policy) if options.policy else DEFAULT_POLICY
        path, label = root.real / relative, relative.as_posix()
    return parse_policy(read_policy_bytes(path), label)


# ---------------------------------------------------------------------------
# Events, targets and the decision
# ---------------------------------------------------------------------------

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


def write_target(event: dict, harness: str):
    """Return the Target of a write call, or None when the event is not a write call."""
    if harness == "copilot":
        tool, arguments = event.get("toolName"), event.get("toolArgs")
        if not isinstance(tool, str):
            raise InputError("the event names no tool")
        if isinstance(arguments, str) and tool in WRITE_TOOLS[harness]:
            try:
                arguments = strict_json(arguments.encode("utf-8"))
            except ValueError as error:
                raise InputError("the tool arguments are not valid JSON") from error
    else:
        default = "PreToolUse" if harness == "claude_code" else "preToolUse"
        if event.get("hook_event_name", default) != default:
            return None
        tool, arguments = event.get("tool_name"), event.get("tool_input")
    fields = WRITE_TOOLS[harness].get(tool)
    if fields is None:
        return None
    if not isinstance(arguments, dict):
        raise InputError("the %s call has no arguments" % tool)
    raw = next((arguments[name] for name in fields if isinstance(arguments.get(name), str)), None)
    if not raw or len(raw) > MAX_PATH_CHARS or "\x00" in raw:
        raise InputError("the %s call names no usable target path" % tool)
    base = event.get("cwd")
    return Target(raw, base if isinstance(base, str) and base and "\x00" not in base else "")


def inside(path: str, root: Path) -> str | None:
    """Root-relative POSIX form of an absolute path, or None when it lies outside the root."""
    try:
        relative = Path(path).relative_to(root)
    except ValueError:
        return None
    return relative.as_posix()


def claude_worktree(root: Root, cwd: str) -> Root | None:
    """The Claude Code worktree folder that holds the event's working folder, or None.

    Only .claude/worktrees/<name> directly under the root counts, and only when none of
    its three folders is a symbolic link and it holds a .git regular file, as a git
    worktree does. A folder the agent made up has no such file, because .git is refused.
    """
    if not cwd or "\x00" in cwd or not os.path.isabs(cwd):
        return None
    folder = os.path.normpath(cwd)
    relative = inside(folder, root.given)
    if relative is None:
        relative = inside(folder, root.real)
    parts = relative.split("/") if relative else []
    if len(parts) < 3 or tuple(parts[:2]) != WORKTREE_PARTS or parts[2] in (".", ".."):
        return None
    current = root.real
    for part in (*WORKTREE_PARTS, parts[2]):
        current = current / part
        if current.is_symlink() or not current.is_dir():
            return None
    marker = current / ".git"
    if marker.is_symlink() or not marker.is_file():
        return None
    return Root(Path(os.path.realpath(current)), root.given.joinpath(*WORKTREE_PARTS, parts[2]),
                "the worktree folder %s/%s/%s" % (*WORKTREE_PARTS, shown(parts[2], 60)))


def check_target(target: Target, root: Root, policy: Policy) -> None:
    if target.raw.startswith("~"):
        raise Refusal("%s starts with ~, which some tools expand to the home folder. Use a path inside %s"
                      % (shown(target.raw), root.label))
    base = target.base if target.base and os.path.isabs(target.base) else os.path.join(str(root.real), target.base)
    joined = os.path.join(base, target.raw)
    lexical_path = os.path.normpath(joined)
    real_path = os.path.realpath(joined)
    lexical = inside(lexical_path, root.given)
    if lexical is None:
        lexical = inside(lexical_path, root.real)
    real = inside(real_path, root.real)
    label = lexical if lexical not in (None, ".") else target.raw
    if real is None:
        if lexical is not None:
            raise Refusal("%s leads through a symbolic link to a place outside %s. Write to a real file inside %s "
                          "instead, or stop and report" % (shown(label), root.label, root.label))
        raise Refusal("%s is outside %s. Write only inside %s. If the step needs this change, stop and report the "
                      "path and why" % (shown(label), root.label, root.label))
    for relative in {item for item in (lexical, real) if item not in (None, ".")}:
        for part in relative.split("/"):
            if part.casefold() in VERSION_CONTROL:
                raise Refusal("%s is inside version control metadata (%s). Change working files only; the host "
                              "handles commits" % (shown(label), part))
        for pattern, folder in BUILT_IN:
            if glob_match(pattern, relative, True) and not any(glob_match(item, relative, False) for item in policy.writable):
                raise Refusal("%s is inside %s, which holds harness settings, hooks or step files. Do not change "
                              "it; write your output elsewhere, or stop and report" % (shown(label), folder))
        for pattern in policy.protected:
            if glob_match(pattern, relative, True):
                raise Refusal('%s is a protected path (it matches "%s" in %s). Write a new file outside protected '
                              "paths, or stop and report why this file must change" % (shown(label), shown(pattern), policy.label))
    if real == "." or lexical == ".":
        raise Refusal("the target is %s itself, not a file" % root.label)
    try:
        details = os.stat(real_path)
    except FileNotFoundError:
        return  # a new file inside the workspace
    except OSError as error:
        raise Refusal("%s cannot be inspected (%s)" % (shown(label), type(error).__name__)) from error
    if not stat.S_ISREG(details.st_mode):
        raise Refusal("%s is not a regular file" % shown(label))
    if details.st_nlink > 1:
        raise Refusal("%s has other hard links, so a write could change a file outside the workspace. Stop and "
                      "report this path" % shown(label))


def allow(harness: str) -> dict:
    """The answer for a call this guard does not refuse."""
    return {"permission": "allow"} if harness == "cursor" else {}


def deny(harness: str, reason: str) -> dict:
    reason = reason if len(reason) <= MAX_REASON_CHARS else reason[: MAX_REASON_CHARS - 3] + "..."
    if harness == "claude_code":
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}
    if harness == "cursor":
        return {"permission": "deny", "user_message": reason, "agent_message": reason}
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def decide(options) -> dict:
    harness = options.harness
    prefix = "Refused by the workspace write guard: "
    try:
        target = write_target(read_event(sys.stdin.buffer), harness)
    except InputError as error:
        return deny(harness, prefix + "the hook could not read this tool call (%s). Stop and report this to the host." % error)
    if target is None:
        return allow(harness)
    try:
        root = workspace_root(options)
        policy = load_policy(options, root)
    except PolicyError as error:
        return deny(harness, prefix + "the step write policy cannot be used (%s). No file can be written in this step. "
                                      "Stop and report this to the host." % error)
    try:
        if harness == "claude_code":
            root = claude_worktree(root, target.base) or root
        check_target(target, root, policy)
    except Refusal as refusal:
        return deny(harness, prefix + str(refusal) + ".")
    except (OSError, ValueError):
        return deny(harness, prefix + "the target path cannot be checked. Stop and report this to the host.")
    return allow(harness)


def out_of_time(_signal_number, _frame):
    raise TimeoutError("time limit")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refuse file writes outside the workspace or onto protected paths.")
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--root", help="workspace root; defaults to the harness project folder")
    parser.add_argument("--policy", help="write policy file; relative paths start at the workspace root")
    parser.add_argument("--check-policy", action="store_true", help="validate the policy and exit")
    options = parser.parse_args(argv)
    if options.check_policy:
        try:
            policy = load_policy(options, workspace_root(options))
        except PolicyError as error:
            print(json.dumps({"policy": "refused", "reason": str(error)}))
            return 1
        print(json.dumps({"policy": "valid", "path": policy.label, "protected_globs": len(policy.protected),
                          "writable_globs": len(policy.writable)}))
        return 0
    if not options.harness:
        parser.error("--harness is required")
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, out_of_time)
        signal.alarm(TIME_LIMIT_SECONDS)
    try:
        answer = decide(options)
    except TimeoutError:
        answer = deny(options.harness, "Refused by the workspace write guard: the hook ran out of time. Stop and report this to the host.")
    except Exception:  # noqa: BLE001 - a guard refuses when it cannot decide
        answer = deny(options.harness, "Refused by the workspace write guard: the hook failed inside. Stop and report this to the host.")
    sys.stdout.write(json.dumps(answer, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

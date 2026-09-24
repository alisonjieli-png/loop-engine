"""Effects: reads one JSON event on standard input and the step allowlist file; writes one JSON answer to standard output; writes no file, makes no network call and starts no program.

Shell command allowlist guard, run by a coding harness before each shell command.

The harness starts this file for a shell tool call and passes the event on
standard input. The guard splits the command line into its simple commands and
refuses the call when any part does not start with an entry of the step
allowlist, or uses shell syntax the guard does not check. A refusal uses the
harness's own answer format. The guard never widens the step's list: Claude
Code and Copilot get the empty object {} for an allowed call, which leaves the
decision to the harness's own permission settings. Cursor documents an answer
that always names a permission, so there an allowed call gets
{"permission": "allow"}.

Covered tools: Claude Code Bash and Monitor (each command is checked as one
shell line) and PowerShell (always refused); Cursor beforeShellExecution, or
preToolUse for the Shell tool; Copilot bash (powershell is refused).

Usage:
    python3 -I -B guard_shell_commands.py --harness claude_code|cursor|copilot [--root DIR] [--policy FILE]
    python3 -I -B guard_shell_commands.py --check-policy [--root DIR] [--policy FILE]

The policy file defaults to <root>/.baltor/step/guard-shell-command-allowlist.json.
The package places a default there that allows only inspection commands; the
host replaces it with the step's own list before launch:
    {"record_type": "shell_command_allowlist/v1",
     "allowed_commands": [{"start": ["python3", "-m", "pytest"]},
                          {"start": ["git", "diff"], "refused_arguments": ["--output"]}],
     "environment_names": ["PYTHONPATH"]}

Rules after a start matches:
- $NAME, ${...}, $(...), backticks and unquoted braces are refused in every
  word, because the guard cannot see what bash would turn them into.
- For an entry with refused_arguments, unquoted *, ? and [ are refused in the
  words after the start, because a file name can expand into a refused option.
- A refused option also matches its =value form, an abbreviation of a long
  option (--outp for --output) and, for a two-character option such as -o, an
  attached value (-ofile) and short-option groups that hold its letter (-uo).
- Programs that run other programs (env, xargs, bash and others) and shell
  builtins that change how later commands run (export, alias, hash and others)
  are refused even when a policy lists them.

A listed program may read or write any path its own arguments name: the list
limits programs and options, not paths. A listed reader such as rg, find or
git diff can read files outside the workspace, including private files in the
home folder. Listing an interpreter such as python3, node, awk or sed, or a
test runner, lets it run any code the workspace holds. Malformed input, a
missing or invalid policy and internal errors are refused (fail closed).
Licensed MIT, like the rest of this package.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import stat
import sys
from pathlib import Path
from typing import NamedTuple

NATIVE_NAME = "guard-shell-command-allowlist"
POLICY_RECORD = "shell_command_allowlist/v1"
DEFAULT_POLICY = Path(".baltor") / "step" / (NATIVE_NAME + ".json")
HARNESSES = ("claude_code", "cursor", "copilot")
MAX_EVENT_BYTES = 1024 * 1024
MAX_POLICY_BYTES = 256 * 1024
MAX_COMMAND_CHARS = 65536
MAX_PARTS = 256
MAX_REASON_CHARS = 1000
TIME_LIMIT_SECONDS = 8

# Programs that run another program named in their own arguments. The guard
# cannot see what they would run, so it refuses them even when a policy lists them.
LAUNCHERS = frozenset({
    "env", "xargs", "sudo", "doas", "su", "runuser", "pkexec", "nohup", "timeout", "nice",
    "ionice", "stdbuf", "setsid", "chroot", "unshare", "nsenter", "watch", "exec", "eval",
    "command", "builtin", "source", ".", "bash", "sh", "zsh", "dash", "ksh", "fish", "csh",
    "tcsh", "busybox", "time", "strace", "ltrace", "script", "flock", "parallel", "coproc", "trap",
})
# Shell builtins that change how later commands on the same line run: which program a
# name starts, which variables it sees, or which code a name loads. Refused even when listed.
SHELL_STATE = frozenset({
    "export", "declare", "typeset", "readonly", "local", "set", "shopt", "unset", "alias",
    "unalias", "hash", "enable",
})
# Variable names that change which program runs, load code before it starts, or point a
# program at a configuration file that names other programs to run.
UNSAFE_NAMES = frozenset({
    "PATH", "IFS", "ENV", "BASH_ENV", "SHELLOPTS", "BASHOPTS", "PS4", "PROMPT_COMMAND",
    "PYTHONSTARTUP", "PYTHONHOME", "NODE_OPTIONS", "PERL5OPT", "RUBYOPT", "GIT_SSH",
    "GIT_SSH_COMMAND", "GIT_EXEC_PATH", "GIT_PAGER", "GIT_EDITOR", "PAGER", "EDITOR", "VISUAL",
    "HOME", "XDG_CONFIG_HOME", "RIPGREP_CONFIG_PATH", "GIT_EXTERNAL_DIFF", "GIT_ASKPASS",
    "SSH_ASKPASS", "GIT_PROXY_COMMAND", "GIT_SEQUENCE_EDITOR", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_COMMON_DIR", "GIT_TEMPLATE_DIR", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS",
    "DOTNET_STARTUP_HOOKS", "LESSOPEN", "LESSCLOSE", "MANPAGER", "BROWSER", "SHELL",
})
UNSAFE_PREFIXES = ("LD_", "DYLD_", "GIT_CONFIG")

OPERATORS = ("&>>", "<<<", "&&", "||", ";;", "|&", ">>", "<<", ">&", "<&", "&>", ">|", "<>",
             ";", "&", "|", "<", ">", "(", ")")
SEPARATORS = frozenset({";", "&&", "||", "|", "|&"})
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
# Policy tokens hold no character that a shell would expand, quote or treat as syntax.
START_TOKEN = re.compile(r"[A-Za-z0-9._+,:@%/=-]{1,100}\Z")
OPTION_TOKEN = re.compile(r"--?[A-Za-z0-9][A-Za-z0-9._+-]{0,97}\Z")
GLOB_CHARACTERS = "*?["


class Refusal(Exception):
    """A command this guard refuses. The text is shown to the model."""


class InputError(Exception):
    """The event on standard input cannot be read as one tool call."""


class PolicyError(Exception):
    """The step allowlist is missing, unreadable or not valid."""


class Entry(NamedTuple):
    start: tuple
    refused_arguments: tuple


class Policy(NamedTuple):
    entries: tuple
    environment_names: frozenset
    label: str


def shown(text: str, limit: int = 60) -> str:
    """Printable, bounded form of a token for a refusal reason."""
    clean = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)
    return clean if len(clean) <= limit else clean[: limit - 3] + "..."


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


# ---------------------------------------------------------------------------
# Reading the command line
# ---------------------------------------------------------------------------

def starts_expansion(char: str) -> bool:
    """True when bash expands a $ that this character follows ($NAME, ${...}, $[...], $1, $@ and similar)."""
    return char.isascii() and (char.isalnum() or char in "_{[@*#?$!-")


PARAMETER_REFUSAL = "the $NAME, ${...} and $[...] forms are not checked by this guard; write the value itself"


def read_double_quoted(line: str, index: int, word: list) -> int:
    """Read a double-quoted section that starts at index; return the index after it."""
    size = len(line)
    while index < size:
        char = line[index]
        following = line[index + 1] if index + 1 < size else ""
        if char == '"':
            return index + 1
        if char == "`" or (char == "$" and following == "("):
            raise Refusal("command substitution inside double quotes is not checked by this guard")
        if char == "$" and starts_expansion(following):
            raise Refusal(PARAMETER_REFUSAL + ", also inside double quotes")
        if char == "\\" and following in ('"', "\\", "$", "`"):
            word.append(following)
            index += 2
            continue
        word.append(char)
        index += 1
    raise Refusal("the command has an unclosed double quote")


def tokenize(line: str) -> list:
    """Split one shell line into ("word", text, has_glob) and ("op", text, False) tokens.

    has_glob is True when the word holds an unquoted *, ? or [, which bash
    would replace with matching file names.
    """
    tokens = []
    word = []
    state = {"open": False, "quoted": False, "glob": False}

    def flush() -> None:
        if state["open"]:
            tokens.append(("word", "".join(word), state["glob"]))
        word.clear()
        state["open"] = state["quoted"] = state["glob"] = False

    index, size = 0, len(line)
    while index < size:
        char = line[index]
        following = line[index + 1] if index + 1 < size else ""
        if char == "'":
            end = line.find("'", index + 1)
            if end < 0:
                raise Refusal("the command has an unclosed single quote")
            word.append(line[index + 1:end])
            state["open"] = state["quoted"] = True
            index = end + 1
        elif char == '"':
            index = read_double_quoted(line, index + 1, word)
            state["open"] = state["quoted"] = True
        elif char == "\\":
            if not following or following in "\r\n":
                raise Refusal("the command continues over more than one line; send one line per command")
            word.append(following)
            state["open"] = state["quoted"] = True
            index += 2
        elif char == "`":
            raise Refusal("backtick command substitution is not checked by this guard")
        elif char == "$" and following in ("(", "'", '"'):
            raise Refusal("the $( ), $'...' and $\"...\" forms are not checked by this guard")
        elif char == "$" and starts_expansion(following):
            raise Refusal(PARAMETER_REFUSAL)
        elif char in "\r\n":
            raise Refusal("the command has more than one line; send one line per command")
        elif char in " \t":
            flush()
            index += 1
        elif char == "#" and not state["open"]:
            break  # the rest of the line is a shell comment
        elif char in ";&|<>()":
            if char in "<>" and following == "(":
                raise Refusal("process substitution is not checked by this guard")
            prefix = ""
            if char in "<>" and state["open"] and not state["quoted"] and "".join(word).isdigit():
                prefix = "".join(word)
                word.clear()
                state["open"] = False
            else:
                flush()
            operator = next(item for item in OPERATORS if line.startswith(item, index))
            tokens.append(("op", prefix + operator, False))
            index += len(operator)
        elif char == "{":
            raise Refusal("unquoted braces can expand into other words, which this guard does not check; "
                          "put the word in single quotes")
        else:
            word.append(char)
            state["open"] = True
            if char in GLOB_CHARACTERS:
                state["glob"] = True
            index += 1
    flush()
    return tokens


def simple_commands(tokens: list) -> list:
    """Group tokens into simple commands of (text, has_glob) words; refuse syntax this guard does not check."""
    parts, current, last_separator = [], [], ""
    index = 0
    while index < len(tokens):
        kind, text, glob = tokens[index]
        index += 1
        if kind == "word":
            current.append((text, glob))
            continue
        if text in SEPARATORS:
            if not current:
                raise Refusal("the command has an empty part before " + text)
            parts.append(current)
            current, last_separator = [], text
            continue
        if text == "&":
            raise Refusal("background jobs with & are not allowed in this step")
        if text in ("(", ")", ";;"):
            raise Refusal("subshells, ( ) groups and case syntax are not checked by this guard")
        operator = text.lstrip("0123456789")
        if operator in ("<<", "<<<"):
            raise Refusal("here-documents and here-strings are not checked by this guard")
        if index >= len(tokens) or tokens[index][0] != "word":
            raise Refusal("a redirection has no target")
        target = tokens[index][1]
        index += 1
        if operator in (">&", "<&") and target in ("1", "2", "-"):
            continue
        if operator in (">", ">>", "&>", "&>>", ">|", "<") and target == "/dev/null":
            continue
        raise Refusal("redirection to or from a file is not allowed; only 2>&1 and /dev/null are accepted")
    if current:
        parts.append(current)
    elif not parts or last_separator in ("&&", "||", "|", "|&"):
        raise Refusal("the command is empty or ends with an operator")
    if len(parts) > MAX_PARTS:
        raise Refusal("the command has more than %d parts" % MAX_PARTS)
    return parts


def refused_argument(argument: str, refused: tuple) -> str:
    """Return the refused option that this argument uses, or the empty string."""
    for item in refused:
        if argument == item or argument.startswith(item + "="):
            return item
        if item.startswith("--"):
            name = argument.split("=", 1)[0]
            if len(name) > 2 and name.startswith("--") and item.startswith(name):
                return item  # an abbreviation that many option readers accept, such as --outp for --output
        elif len(item) == 2 and argument.startswith("-") and not argument.startswith("--") and item[1] in argument[1:]:
            # One rule covers the option with an attached value (-ofile, -o/tmp/x, -o../x) and the
            # letter inside a group of short options (-uo). It can refuse a harmless value that
            # holds the letter, which is the safe direction.
            return item
    return ""


def check_part(words: list, policy: Policy) -> None:
    words = list(words)
    while words and ASSIGNMENT.match(words[0][0]):
        name = words[0][0].split("=", 1)[0]
        if name not in policy.environment_names:
            raise Refusal("the variable prefix %s= is not allowed in this step; run the command without it" % shown(name))
        words.pop(0)
    if not words:
        raise Refusal("a part of the command only sets variables and runs no program")
    texts = [text for text, _glob in words]
    base = texts[0].rsplit("/", 1)[-1]
    if base in LAUNCHERS:
        raise Refusal('"%s" runs other programs, which this guard cannot check; run the inner command directly if it is allowed'
                      % shown(base))
    if base in SHELL_STATE:
        raise Refusal('"%s" changes how later commands in the shell run, which this guard cannot check; '
                      "run the allowed command on its own" % shown(base))
    matches = [entry for entry in policy.entries if tuple(texts[:len(entry.start)]) == entry.start]
    if not matches:
        raise Refusal('"%s" does not start with an allowed command' % shown(" ".join(texts[:3])))
    for entry in matches:
        if not entry.refused_arguments:
            continue
        label = shown(" ".join(entry.start))
        for text, glob in words[len(entry.start):]:
            if glob:
                raise Refusal('the word "%s" holds an unquoted *, ? or [, which can expand to file names that look like '
                              'options of "%s"; put the pattern in single quotes' % (shown(text), label))
            hit = refused_argument(text, entry.refused_arguments)
            if hit:
                raise Refusal('the argument "%s" is not allowed with "%s"' % (shown(hit), label))


def check_command(command: str, policy: Policy) -> None:
    if len(command) > MAX_COMMAND_CHARS:
        raise Refusal("the command is longer than %d characters" % MAX_COMMAND_CHARS)
    for part in simple_commands(tokenize(command)):
        check_part(part, policy)


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

def workspace_root(options) -> Path | None:
    if options.root:
        return Path(options.root)
    if options.harness == "claude_code":
        value = os.environ.get("CLAUDE_PROJECT_DIR", "")
    elif options.harness == "cursor":
        value = os.environ.get("CURSOR_PROJECT_DIR", "") or os.environ.get("CLAUDE_PROJECT_DIR", "")
    else:
        value = os.getcwd()  # the Copilot registration starts the hook in the repository root
    return Path(value) if value else None


def policy_path(options) -> tuple:
    root = workspace_root(options)
    if options.policy and Path(options.policy).is_absolute():
        return Path(options.policy), Path(options.policy).name
    if root is None:
        raise PolicyError("the workspace root is unknown, so the allowlist cannot be found")
    if not root.is_dir():
        raise PolicyError("the workspace root does not exist")
    relative = Path(options.policy) if options.policy else DEFAULT_POLICY
    return root / relative, relative.as_posix()


def read_policy_bytes(path: Path) -> bytes:
    try:
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError as error:
        raise PolicyError("there is no allowlist file") from error
    except OSError as error:
        raise PolicyError("the allowlist file cannot be opened") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PolicyError("the allowlist path is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_POLICY_BYTES:
        raise PolicyError("the allowlist file is larger than 256 KiB")
    return raw


def parse_policy(raw: bytes, label: str) -> Policy:
    try:
        document = strict_json(raw)
    except ValueError as error:
        raise PolicyError("the allowlist file is not valid JSON") from error
    if not isinstance(document, dict) or document.get("record_type") != POLICY_RECORD:
        raise PolicyError("the allowlist file is not a %s record" % POLICY_RECORD)
    if set(document) - {"record_type", "allowed_commands", "environment_names"}:
        raise PolicyError("the allowlist file has unknown fields")
    commands = document.get("allowed_commands")
    if not isinstance(commands, list) or len(commands) > 200:
        raise PolicyError("allowed_commands is a list of at most 200 entries")
    entries = []
    for item in commands:
        if not isinstance(item, dict) or set(item) - {"start", "refused_arguments"}:
            raise PolicyError("each allowed command has start and optional refused_arguments")
        start = item.get("start")
        if not isinstance(start, list) or not 1 <= len(start) <= 8 \
                or any(not isinstance(token, str) or not START_TOKEN.fullmatch(token) for token in start):
            raise PolicyError("each start is a list of 1 to 8 tokens made of letters, digits and . _ + , : @ % / = -")
        if start[0].rsplit("/", 1)[-1] in LAUNCHERS | SHELL_STATE or ASSIGNMENT.match(start[0]):
            raise PolicyError('the start "%s" names a program that runs other programs or changes how later '
                              "commands run" % shown(start[0]))
        refused = item.get("refused_arguments", [])
        if not isinstance(refused, list) or len(refused) > 50 or any(
                not isinstance(value, str) or not OPTION_TOKEN.fullmatch(value) for value in refused):
            raise PolicyError("refused_arguments is a list of at most 50 options such as -o or --output")
        entries.append(Entry(tuple(start), tuple(refused)))
    names = document.get("environment_names", [])
    if not isinstance(names, list) or len(names) > 50 \
            or any(not isinstance(name, str) or not NAME.fullmatch(name) for name in names):
        raise PolicyError("environment_names is a list of at most 50 variable names")
    for name in names:
        if name in UNSAFE_NAMES or name.startswith(UNSAFE_PREFIXES):
            raise PolicyError("the variable name %s can change which program runs" % name)
    return Policy(tuple(entries), frozenset(names), label)


def load_policy(options) -> Policy:
    path, label = policy_path(options)
    return parse_policy(read_policy_bytes(path), label)


# ---------------------------------------------------------------------------
# Harness events and answers
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


def command_field(container, where: str) -> str:
    if not isinstance(container, dict) or not isinstance(container.get("command"), str):
        raise InputError("the %s has no command text" % where)
    return container["command"]


def shell_command_of(event: dict, harness: str):
    """Return the command text, or None when the event is not a shell call."""
    if harness == "claude_code":
        if event.get("hook_event_name", "PreToolUse") != "PreToolUse":
            return None
        tool = event.get("tool_name")
        if tool == "PowerShell":
            raise Refusal("PowerShell commands are not checked by this guard; use the Bash tool with an allowed command")
        if tool not in ("Bash", "Monitor"):
            return None
        arguments = event.get("tool_input")
        if tool == "Monitor" and isinstance(arguments, dict) and arguments.get("ws") is not None:
            raise Refusal("a Monitor call that opens a WebSocket is not checked by this guard; "
                          "use a Monitor command that starts with an allowed command")
        return command_field(arguments, "%s tool input" % tool)
    if harness == "cursor":
        name = event.get("hook_event_name")
        if name == "beforeShellExecution" or (name is None and "command" in event):
            return command_field(event, "shell event")
        if name == "preToolUse":
            if event.get("tool_name") != "Shell":
                return None
            return command_field(event.get("tool_input"), "Shell tool input")
        if name is None:
            raise InputError("the event names no hook event")
        return None
    tool = event.get("toolName")
    if not isinstance(tool, str):
        raise InputError("the event names no tool")
    if tool == "powershell":
        raise Refusal("PowerShell commands are not checked by this guard; use the bash tool with an allowed command")
    if tool != "bash":
        return None
    arguments = event.get("toolArgs")
    if isinstance(arguments, str):
        try:
            arguments = strict_json(arguments.encode("utf-8"))
        except ValueError as error:
            raise InputError("the tool arguments are not valid JSON") from error
    return command_field(arguments, "bash tool arguments")


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


def refusal_text(detail: str, policy: Policy) -> str:
    starts = ['"%s"' % shown(" ".join(entry.start)) for entry in policy.entries[:12]]
    listed = ", ".join(starts) if starts else "none"
    if len(policy.entries) > 12:
        listed += " and %d more" % (len(policy.entries) - 12)
    return ("Refused by the shell command guard: %s. Allowed command starts: %s (see %s). "
            "Use an allowed form, or stop and report the command you need and why." % (detail, listed, policy.label))


def decide(options) -> dict:
    harness = options.harness
    try:
        command = shell_command_of(read_event(sys.stdin.buffer), harness)
    except InputError as error:
        return deny(harness, "Refused by the shell command guard: the hook could not read this tool call (%s). "
                             "Stop and report this to the host." % error)
    except Refusal as refusal:
        return deny(harness, "Refused by the shell command guard: %s. If the step needs this, stop and report "
                             "the command and why." % refusal)
    if command is None:
        return allow(harness)
    try:
        policy = load_policy(options)
    except PolicyError as error:
        return deny(harness, "Refused by the shell command guard: the step allowlist cannot be used (%s). "
                             "No shell command can run in this step. Stop and report this to the host." % error)
    try:
        check_command(command, policy)
    except Refusal as refusal:
        return deny(harness, refusal_text(str(refusal), policy))
    return allow(harness)


def out_of_time(_signal_number, _frame):
    raise TimeoutError("time limit")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refuse shell commands that are not on the step allowlist.")
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--root", help="workspace root; defaults to the harness project folder")
    parser.add_argument("--policy", help="allowlist file; relative paths start at the workspace root")
    parser.add_argument("--check-policy", action="store_true", help="validate the allowlist and exit")
    options = parser.parse_args(argv)
    if options.check_policy:
        try:
            policy = load_policy(options)
        except PolicyError as error:
            print(json.dumps({"policy": "refused", "reason": str(error)}))
            return 1
        print(json.dumps({"policy": "valid", "path": policy.label, "allowed_commands": len(policy.entries),
                          "environment_names": sorted(policy.environment_names)}))
        return 0
    if not options.harness:
        parser.error("--harness is required")
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, out_of_time)
        signal.alarm(TIME_LIMIT_SECONDS)
    try:
        answer = decide(options)
    except TimeoutError:
        answer = deny(options.harness, "Refused by the shell command guard: the hook ran out of time. Stop and report this to the host.")
    except Exception:  # noqa: BLE001 - a guard refuses when it cannot decide
        answer = deny(options.harness, "Refused by the shell command guard: the hook failed inside. Stop and report this to the host.")
    sys.stdout.write(json.dumps(answer, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

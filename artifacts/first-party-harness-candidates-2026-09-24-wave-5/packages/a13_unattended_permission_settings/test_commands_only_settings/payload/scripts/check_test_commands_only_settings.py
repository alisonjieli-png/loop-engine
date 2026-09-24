"""Effects: reads harness settings files under --root, or one document from standard input; writes nothing, starts no program and uses no network.

Checks whether the harness settings of one step hold the policy of the
test-commands-only-settings package, and prints one JSON object.

Exit status: 0 when the policy holds, 1 when it does not, 2 when the input is
refused (a missing or unreadable file, more than 1 MiB, not UTF-8, invalid JSON
or TOML, a duplicate JSON key, or a path that leaves the root).

Usage, from the workspace root:
    python3 -I -B .baltor/test-commands-only-settings/scripts/check_test_commands_only_settings.py
    python3 -I -B check_test_commands_only_settings.py --root DIR
    python3 -I -B check_test_commands_only_settings.py --harness claude_code --file PATH
    python3 -I -B check_test_commands_only_settings.py --harness opencode --stdin

The probes model the rule order of one installed version of each harness (see the
package review note). A pass shows what the settings files say. It does not
prove that a harness loaded them. Keys that can add tools or decisions outside
the permission settings, such as hooks and protocol servers, are listed under
not_modeled and are not checked. Licence: MIT.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Policy of this package
# ---------------------------------------------------------------------------

POLICY = "test_commands_only_settings"
VERSION = "0.1.0"
NATIVE = POLICY.replace("_", "-")
SELF_CHECK = f"python3 -I -B .baltor/{NATIVE}/scripts/check_{POLICY}.py"
KIND = "base"  # "base" holds a whole step policy; "refusal_fragment" only adds refusals
RENDERED = ("claude_code", "opencode", "gemini_cli")
NOT_RENDERED = {"codex": "Codex rules files can forbid a named command prefix, but no Codex setting refuses every "
                         "command outside an allowlist, which this policy needs"}
CODEX_SANDBOX = "read-only"
CLAUDE_SANDBOX = False
GEMINI_TOOL_SANDBOX = False
GEMINI_IGNORE_FILE = ""
DECLARED_COMMANDS = ("python3 -m unittest", "python3 -m pytest", "python3 -m pyflakes", "ruff format --check",
                     "python3 -m black --check", SELF_CHECK)
WRITABLE_PATHS: tuple = ()
REFUSED = ("shell commands that are not listed, including git and common read-only commands such as ls, cat and "
           "grep; Claude Code still runs the rest of the commands it classes as read-only",
           "test options that write, delete or send files, such as --basetemp, --junitxml and --pastebin, except "
           "on Gemini CLI, which matches command prefixes only",
           "creating, editing or deleting files", "output redirection into a file", "network access and web tools",
           "handing work to another agent")
# Every grant a variant may hold. Any other allow rule, allow pattern or allowlist entry fails the check,
# also one that a merge into an existing settings file kept.
GRANTS = {
    "claude_code": ("Read(/**)", "Bash(python3 -m unittest *)", "Bash(python3 -m pytest *)",
                    "Bash(python3 -m pyflakes *)", "Bash(ruff format --check *)", "Bash(python3 -m black --check *)",
                    f"Bash({SELF_CHECK})"),
    "opencode": (("read", "*"), ("list", "*"), ("glob", "*"), ("grep", "*"), ("skill", "*"), ("todowrite", "*"),
                 ("bash", "python3 -m unittest *"), ("bash", "python3 -m pytest *"),
                 ("bash", "python3 -m pyflakes *"), ("bash", "ruff format --check *"),
                 ("bash", "python3 -m black --check *"), ("bash", SELF_CHECK)),
    "gemini_cli": ("read_file", "read_many_files", "list_directory", "glob", "grep_search", "activate_skill",
                   "run_shell_command(python3 -m unittest)", "run_shell_command(python3 -m pytest)",
                   "run_shell_command(python3 -m pyflakes)", "run_shell_command(ruff format --check)",
                   "run_shell_command(python3 -m black --check)", f"run_shell_command({SELF_CHECK})"),
}
CLAUDE_BUILTIN_REST = ("Claude Code runs the commands it classes as read-only without a rule in every permission "
                       "mode. These settings refuse the common ones by name; the rest, such as strings, date and "
                       "hexdump, still run, and they only read.")
GEMINI_PREFIX = ("Gemini CLI matches shell commands by prefix, so an allowed test command also accepts any option, "
                 "including options that write, delete or send files.")

# (probe, action, value, effect, expected). A value may be a dict keyed by harness.
PROBES = (
    ("read_source_file", "read", "src/app.py", "read", "allow"),
    ("search_source_folder", "search", "src", "read", "allow"),
    ("edit_source_file", "edit", "src/app.py", "write", "deny"),
    ("edit_test_file", "edit", "tests/test_app.py", "write", "deny"),
    ("create_new_file", "create", "notes.txt", "write", "deny"),
    ("run_unittest", "shell", "python3 -m unittest discover -s tests -v", "exec", "allow"),
    ("run_pytest", "shell", "python3 -m pytest -q tests/test_app.py", "exec", "allow"),
    ("merge_error_stream", "shell", {"claude_code": "python3 -m pytest -q 2>&1"}, "exec", "allow"),
    ("run_lint", "shell", "python3 -m pyflakes src", "read", "allow"),
    ("check_format_ruff", "shell", "ruff format --check src", "read", "allow"),
    ("check_format_black", "shell", "python3 -m black --check src", "read", "allow"),
    ("self_check", "shell", SELF_CHECK, "read", "allow"),
    ("apply_ruff_format", "shell", "ruff format src", "write", "deny"),
    ("apply_black_format", "shell", "python3 -m black src", "write", "deny"),
    ("fix_lint_findings", "shell", "ruff check --fix src", "write", "deny"),
    ("delete_with_basetemp", "shell", "python3 -m pytest -q --basetemp=src", "write", "deny"),
    ("write_junit_report", "shell", "python3 -m pytest -q --junitxml=src/app.py", "write", "deny"),
    ("move_cache_folder", "shell", "python3 -m pytest -q -o cache_dir=src", "write", "deny"),
    ("upload_test_log", "shell", "python3 -m pytest -q --pastebin=all", "network", "deny"),
    ("git_status", "shell", "git status", "read", "deny"),
    ("list_folder", "shell", "ls -la", "read", "deny"),
    ("print_file", "shell", "cat src/app.py", "read", "deny"),
    ("search_in_shell", "shell", "grep -rn TODO src", "read", "deny"),
    ("other_builtin_read_command", "shell", "strings src/app.py", "read", "deny"),
    ("run_other_script", "shell", "python3 scripts/build.py", "exec", "deny"),
    ("install_package", "shell", "python3 -m pip install example-package", "network", "deny"),
    ("chained_command", "shell", "python3 -m pytest -q; rm -f src/app.py", "write", "deny"),
    ("redirect_output", "shell", "python3 -m pytest -q > report.txt", "write", "deny"),
    ("fetch_page", "fetch", "example.invalid", "network", "deny"),
    ("search_web", "web_search", "pytest fixture error", "network", "deny"),
    ("delegate_task", "delegate", "general", "exec", "deny"),
)

# Probes a harness cannot hold with a settings file, and why. They are reported, not failed.
KNOWN_LIMITS = {
    "claude_code": {"other_builtin_read_command": CLAUDE_BUILTIN_REST},
    "gemini_cli": {"delete_with_basetemp": GEMINI_PREFIX, "write_junit_report": GEMINI_PREFIX,
                   "move_cache_folder": GEMINI_PREFIX, "upload_test_log": GEMINI_PREFIX},
}

# ---------------------------------------------------------------------------
# Engine (the same in every package of this set)
# ---------------------------------------------------------------------------

MAX_BYTES = 1024 * 1024
RECORD_TYPE = "baltor_settings_check/v1"
SETTINGS_FILES = {"claude_code": ".claude/settings.json", "codex": ".codex/config.toml",
                  "opencode": "opencode.json", "gemini_cli": ".gemini/settings.json"}
SEARCH_TERM = "DATABASE_URL"  # a search text that a step might look for across a folder


class InputRefused(Exception):
    """The input cannot be read as the settings document it claims to be."""


def inside_workspace(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return bool(path) and not path.startswith(("/", "~")) and ".." not in parts


def split_command(command: str):
    """Split a command line at &&, ||, ;, |, & and new lines outside quotes. None when a quote is open."""
    segments, current, quote, index = [], [], None, 0
    while index < len(command):
        char = command[index]
        if quote:
            current.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(command):
                current.append(command[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'":
            quote = char
            current.append(char)
            index += 1
            continue
        if char == "\\" and index + 1 < len(command):
            current.append(command[index:index + 2])
            index += 2
            continue
        if command[index:index + 2] in ("&&", "||"):
            segments.append("".join(current))
            current = []
            index += 2
            continue
        redirect_ampersand = char == "&" and ((current and current[-1] == ">") or command[index + 1:index + 2] == ">")
        if char in ";|\n" or (char == "&" and not redirect_ampersand):
            segments.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    if quote:
        return None
    segments.append("".join(current))
    return [segment.strip() for segment in segments if segment.strip()]


def unquoted(command: str) -> str:
    """Return the command text with quoted parts removed."""
    kept, quote = [], None
    for char in command:
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        else:
            kept.append(char)
    return "".join(kept)


def outside_single_quotes(command: str) -> str:
    kept, inside = [], False
    for char in command:
        if char == "'":
            inside = not inside
        elif not inside:
            kept.append(char)
    return "".join(kept)


def has_substitution(command: str) -> bool:
    return "$(" in command or "`" in command


def has_redirection(command: str) -> bool:
    text = unquoted(command)
    return ">" in text or "<" in text


REDIRECT_OPERATOR = re.compile(r"&>>|&>|>>|>\||>&|<<<|<<|<&|<>|>|<")


def read_word(text: str, index: int):
    """Read one shell word from index, skipping leading blanks. Quotes stay in the word."""
    while index < len(text) and text[index] in " \t":
        index += 1
    word, quote = [], None
    while index < len(text):
        char = text[index]
        if quote:
            word.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(text):
                word.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'":
            quote = char
        elif char == "\\" and index + 1 < len(text):
            word.append(text[index:index + 2])
            index += 2
            continue
        elif char in " \t<>":
            break
        word.append(char)
        index += 1
    return "".join(word), index


def parse_redirections(segment: str):
    """Split one command into its text without redirections, its output targets and its input targets.

    A duplicated descriptor such as 2>&1 has no target. A here-document or a here-string is text, not a file.
    """
    kept, outputs, inputs = [], [], []
    quote, index, word_start = None, 0, 0
    while index < len(segment):
        char = segment[index]
        if quote:
            kept.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(segment):
                kept.append(segment[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'":
            quote = char
            kept.append(char)
            index += 1
            continue
        if char == "\\" and index + 1 < len(segment):
            kept.append(segment[index:index + 2])
            index += 2
            continue
        if char in " \t":
            kept.append(char)
            word_start = len(kept)
            index += 1
            continue
        if char in "<>" or (char == "&" and segment[index + 1:index + 2] == ">"):
            if "".join(kept[word_start:]).isdigit():
                del kept[word_start:]  # the descriptor number belongs to the redirection
            operator = REDIRECT_OPERATOR.match(segment, index).group(0)
            target, index = read_word(segment, index + len(operator))
            kept.append(" ")
            word_start = len(kept)
            if operator in ("<<", "<<<") or (operator in (">&", "<&") and (target.isdigit() or target == "-")):
                continue
            (inputs if operator in ("<", "<&") else outputs).append(target)
            continue
        kept.append(char)
        index += 1
    return " ".join("".join(kept).split()), outputs, inputs


def redirect_path(target: str) -> str:
    text = target
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    while text.startswith("./"):
        text = text[2:]
    return text


def claude_wildcard(pattern: str, text: str) -> bool:
    """Match like Claude Code: * is any text, and a final " *" also allows no arguments only when it is the
    one * in the pattern. Runs of blanks count as one space."""
    pattern, text = " ".join(pattern.split()), " ".join(text.split())
    optional = pattern.endswith(" *") and pattern.count("*") == 1
    body = pattern[:-2] if optional else pattern
    regex = "".join(".*" if char == "*" else re.escape(char) for char in body)
    return re.fullmatch(regex + ("(?: .*)?" if optional else ""), text, re.S) is not None


def wildcard_match(pattern: str, text: str, question_mark: bool = False) -> bool:
    """Match like OpenCode: * is any text, ? is one character, and a final " *" also allows no arguments."""
    tail = ""
    if pattern.endswith(" *"):
        pattern, tail = pattern[:-2], "(?: .*)?"
    pieces = []
    for char in pattern:
        if char == "*":
            pieces.append(".*")
        elif char == "?" and question_mark:
            pieces.append(".")
        else:
            pieces.append(re.escape(char))
    return re.fullmatch("".join(pieces) + tail, text, re.S) is not None


def glob_regex(pattern: str) -> str:
    """Translate a gitignore-style pattern: ** crosses folders, * and ? stay inside one folder."""
    out, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:[^/]*/)*")
            index += 3
        elif pattern.startswith("/**", index) and index + 3 == len(pattern):
            out.append("(?:/.*)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return "".join(out)


def path_rule_match(spec: str, path: str) -> bool:
    """Match a workspace path against a path rule: /x starts at the root, a bare name matches at any depth."""
    if not inside_workspace(path) or spec.startswith(("//", "~")):
        return False
    anchored = spec.startswith(("/", "./"))
    body = spec[1:] if spec.startswith("/") else spec[2:] if spec.startswith("./") else spec
    body = body.rstrip("/")
    if "/" not in body and not anchored:
        body = "**/" + body
    return re.fullmatch(glob_regex(body) + "(?:/.*)?", path, re.S) is not None


def ignore_matcher(text: str):
    """Build a matcher for gitignore-style lines, honouring ! and the last matching line."""
    rules = []
    for line in text.split("\n"):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        negate = entry.startswith("!")
        entry = entry[1:] if negate else entry
        anchored = entry.startswith("/") or "/" in entry.strip("/")
        body = entry.strip("/")
        regex = glob_regex(body if anchored else "**/" + body) + "(?:/.*)?"
        rules.append((re.compile(regex, re.S), negate))

    def ignored(path: str) -> bool:
        result = False
        for regex, negate in rules:
            if regex.fullmatch(path):
                result = not negate
        return result

    return ignored


# --- readers ---------------------------------------------------------------

def read_json(text: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputRefused(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def constant(name):
        raise InputRefused(f"JSON constant {name} is not allowed")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ValueError as error:
        raise InputRefused(f"invalid JSON: {error}") from None
    if not isinstance(value, dict):
        raise InputRefused("the settings document is not a JSON object")
    return value


TOML_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+\Z")
TOML_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


def toml_split(text: str, separator: str) -> list:
    parts, current, quote, index = [], [], None, 0
    while index < len(text):
        char = text[index]
        if quote:
            current.append(char)
            if quote == '"' and char == "\\" and index + 1 < len(text):
                current.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            current.append(char)
        elif char == separator:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    if quote:
        raise InputRefused("a TOML string is not closed")
    parts.append("".join(current))
    return parts


def toml_value(text: str, number: int):
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        body, out, index = text[1:-1], [], 0
        while index < len(body):
            char = body[index]
            if char == '"':
                raise InputRefused(f"TOML line {number}: a quote inside a string is not escaped")
            if char == "\\":
                if index + 1 >= len(body) or body[index + 1] not in TOML_ESCAPES:
                    raise InputRefused(f"TOML line {number}: unsupported escape")
                out.append(TOML_ESCAPES[body[index + 1]])
                index += 2
                continue
            out.append(char)
            index += 1
        return "".join(out)
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'" and "'" not in text[1:-1]:
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"[+-]?(?:0|[1-9][0-9]*)", text):
        return int(text)
    if len(text) >= 2 and text[0] == "[" and text[-1] == "]":
        inner = text[1:-1].strip()
        if not inner:
            return []
        items = toml_split(inner, ",")
        if not items[-1].strip():
            items = items[:-1]
        return [toml_value(item, number) for item in items]
    raise InputRefused(f"TOML line {number}: this reader cannot read the value {text!r}")


def read_toml_subset(text: str) -> dict:
    """Read the small TOML subset these settings use; used where the Python has no tomllib."""
    data: dict = {}
    table = data
    seen = set()
    for number, raw in enumerate(text.split("\n"), 1):
        line = toml_split(raw, "#")[0].strip()
        if not line:
            continue
        if line.startswith("["):
            if line.startswith("[[") or not line.endswith("]"):
                raise InputRefused(f"TOML line {number}: unsupported table header")
            names = tuple(name.strip() for name in line[1:-1].split("."))
            if not all(TOML_BARE_KEY.match(name) for name in names) or names in seen:
                raise InputRefused(f"TOML line {number}: invalid or repeated table {line}")
            seen.add(names)
            table = data
            for name in names:
                table = table.setdefault(name, {})
                if not isinstance(table, dict):
                    raise InputRefused(f"TOML line {number}: {name} is not a table")
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not TOML_BARE_KEY.match(key):
            raise InputRefused(f"TOML line {number}: expected key = value")
        if key in table:
            raise InputRefused(f"TOML line {number}: duplicate key {key}")
        table[key] = toml_value(value, number)
    return data


def read_toml(text: str, reader: str) -> dict:
    if reader == "auto":
        try:
            import tomllib
        except ImportError:  # Python 3.10 has no tomllib
            tomllib = None
        if tomllib is not None:
            try:
                return tomllib.loads(text)
            except tomllib.TOMLDecodeError as error:
                raise InputRefused(f"invalid TOML: {error}") from None
    return read_toml_subset(text)


def read_confined(root: Path, relative: str) -> str:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise InputRefused(f"{relative!r} is not a relative path inside the root")
    try:
        resolved = (root / candidate).resolve(strict=True)
    except (OSError, RuntimeError):
        raise InputRefused(f"{relative} cannot be read") from None
    if resolved != root and root not in resolved.parents:
        raise InputRefused(f"{relative} leaves the root through a symbolic link")
    if not resolved.is_file():
        raise InputRefused(f"{relative} is not a regular file")
    if resolved.stat().st_size > MAX_BYTES:
        raise InputRefused(f"{relative} is larger than 1 MiB")
    try:
        return resolved.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise InputRefused(f"{relative} is not UTF-8") from None


def string_list(value, name: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InputRefused(f"{name} is not a list of strings")
    return value


def object_at(document: dict, *names: str) -> dict:
    value = document
    for name in names:
        value = value.get(name, {})
        if not isinstance(value, dict):
            raise InputRefused(f"{'.'.join(names)} is not an object")
    return value


# --- Claude Code -----------------------------------------------------------

CLAUDE_RULE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)(?:\((.*)\))?\Z", re.S)
CLAUDE_WRITE_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit")
CLAUDE_TOOLS = {"read": "Read", "search": "Read", "edit": "Edit", "create": "Write", "shell": "Bash",
                "fetch": "WebFetch", "web_search": "WebSearch"}
ENV_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*\Z")
# Commands that the installed Claude Code 2.1.281 classes as read-only and runs without any rule in every
# permission mode, read from its binary. The harness also checks their options and this list does not,
# so the model below can report more commands as allowed than the harness allows, never fewer.
CLAUDE_READ_ONLY = frozenset((
    "cal", "uptime", "cat", "head", "tail", "wc", "stat", "strings", "hexdump", "od", "nl", "id", "uname",
    "free", "df", "du", "locale", "groups", "nproc", "basename", "dirname", "realpath", "cut", "paste", "tr",
    "column", "tac", "rev", "fold", "expand", "unexpand", "fmt", "comm", "cmp", "numfmt", "readlink", "diff",
    "true", "false", "sleep", "which", "type", "expr", "seq", "tsort", "pr", "echo", "printf", "uniq", "jq",
    "pwd", "whoami", "alias", "history", "arch", "ifconfig", "cd", "ls", "find", "xargs", "file", "sed",
    "sort", "man", "help", "netstat", "ps", "base64", "grep", "egrep", "fgrep", "sha256sum", "sha1sum",
    "md5sum", "tree", "date", "hostname", "lsof", "pgrep", "tput", "ss", "fd", "fdfind", "test", "rg",
    "pyright"))
CLAUDE_READ_ONLY_PAIRS = frozenset(("docker ps", "docker images", "docker logs", "docker inspect", "ip addr"))
CLAUDE_READ_ONLY_GIT = ("stash list", "stash show", "worktree list", "config --get", "remote show", "status",
                        "diff", "log", "show", "shortlog", "reflog", "ls-remote", "blame", "ls-files", "remote",
                        "merge-base", "rev-parse", "rev-list", "describe", "cat-file", "for-each-ref", "grep",
                        "tag", "branch")
FIND_WRITES = re.compile(r"(?:^|\s)-(?:delete|exec|execdir|ok|okdir|fprint0?|fprintf|fls|files0-from)(?:\s|$)")
GIT_CONFIG_OPTIONS = re.compile(r"\s(?:-c|--exec-path|--config-env)(?:[\s=]|$)")


def claude_rules(permissions: dict, kind: str) -> list:
    rules = []
    for text in string_list(permissions.get(kind), f"permissions.{kind}"):
        match = CLAUDE_RULE.match(text.strip())
        if match is None:
            raise InputRefused(f"permission rule {text!r} is not Tool or Tool(pattern)")
        rules.append((match.group(1), match.group(2)))
    return rules


def claude_rule_matches(rule, tool: str, value: str) -> bool:
    name, spec = rule
    if spec is None:
        return name == tool
    if tool == "Bash":
        if name != "Bash":
            return False
        if spec.endswith(":*"):  # the older prefix form, such as npm run test:*
            prefix = " ".join(spec[:-2].split())
            return value == prefix or value.startswith(prefix + " ")
        return claude_wildcard(spec, value)
    if tool == "Read":
        return name == "Read" and path_rule_match(spec, value)
    if tool in CLAUDE_WRITE_TOOLS:
        return name == "Edit" and path_rule_match(spec, value)
    return name == tool and spec == value


def claude_texts(command: str, strip_variables: bool) -> list:
    """The texts a shell rule is matched against: the command without its redirections and, for refusals,
    also without leading variable assignments. The harness removes redirections before matching rules."""
    text, _outputs, _inputs = parse_redirections(command)
    texts = [text]
    if strip_variables:
        words = text.split(" ")
        count = 0
        while count < len(words) - 1 and ENV_ASSIGNMENT.match(words[count]):
            count += 1
        if count:
            texts.append(" ".join(words[count:]))
    return texts


def claude_read_only(segment: str) -> bool:
    """Model the harness's own read-only classification of one simple command."""
    text, outputs, _inputs = parse_redirections(segment)
    if [target for target in outputs if redirect_path(target) != "/dev/null"] or has_substitution(text):
        return False
    if re.search(r"\$[A-Za-z_@*#?!$0-9-]", outside_single_quotes(text)):
        return False
    words = text.split()
    if not words:
        return False
    if words[0] == "git":
        if GIT_CONFIG_OPTIONS.search(" " + text):
            return False
        rest = " ".join(words[1:])
        for form in CLAUDE_READ_ONLY_GIT:
            if rest == form or rest.startswith(form + " "):
                arguments = rest[len(form):].split()
                if form == "remote show":
                    return "-n" in arguments
                if form == "remote":
                    return all(item in ("-v", "--verbose") for item in arguments)
                if form == "ls-remote":
                    return all(item.startswith("-") for item in arguments)
                return True
        return False
    if words[0] == "find" and FIND_WRITES.search(unquoted(text)):
        return False
    return " ".join(words[:2]) in CLAUDE_READ_ONLY_PAIRS or words[0] in CLAUDE_READ_ONLY


def claude_sandbox(document: dict) -> dict:
    sandbox = document.get("sandbox", {})
    if not isinstance(sandbox, dict):
        raise InputRefused("sandbox is not an object")
    return sandbox


def claude_sandbox_confines(document: dict) -> bool:
    sandbox = claude_sandbox(document)
    network = sandbox.get("network", {})
    domains = network.get("allowedDomains", []) if isinstance(network, dict) else None
    return (sandbox.get("enabled") is True and sandbox.get("failIfUnavailable") is True
            and sandbox.get("allowUnsandboxedCommands") is False and domains == [])


def claude_unapproved(permissions: dict) -> str:
    """What happens to an action that would wait for approval."""
    mode = permissions.get("defaultMode", "default")
    return "deny" if mode == "dontAsk" else "allow" if mode == "bypassPermissions" else "ask"


def claude_default(document: dict, permissions: dict, tool: str, value: str) -> str:
    mode = permissions.get("defaultMode", "default")
    if tool == "Read" and inside_workspace(value):
        return "allow"
    if tool == "Bash":
        sandbox = claude_sandbox(document)
        if sandbox.get("enabled") is True and sandbox.get("autoAllowBashIfSandboxed") is not False:
            return "allow"
    if mode == "acceptEdits" and tool in CLAUDE_WRITE_TOOLS and inside_workspace(value):
        return "allow"
    return claude_unapproved(permissions)


def claude_tool_decision(document, permissions, rules, tool, value) -> str:
    for kind in ("deny", "ask", "allow"):
        if any(claude_rule_matches(rule, tool, value) for rule in rules[kind]):
            return kind
    return claude_default(document, permissions, tool, value)


def claude_path_rule(rules: dict, kind: str, tool: str, path: str) -> bool:
    return any(name == tool and (spec is None or path_rule_match(spec, path)) for name, spec in rules[kind])


def claude_redirect_check(permissions: dict, rules: dict, segments: list) -> str:
    """Model the harness's check of redirection targets: an input against Read rules, an output against
    Edit rules. /dev/null is never checked. An output that no rule allows waits for approval."""
    mode = permissions.get("defaultMode", "default")
    for segment in segments:
        _text, outputs, inputs = parse_redirections(segment)
        for target in inputs:
            if claude_path_rule(rules, "deny", "Read", redirect_path(target)):
                return "deny"
        for target in outputs:
            path = redirect_path(target)
            if path == "/dev/null":
                continue
            if claude_path_rule(rules, "deny", "Edit", path):
                return "deny"
            if not (claude_path_rule(rules, "allow", "Edit", path) or mode == "bypassPermissions"
                    or (mode == "acceptEdits" and inside_workspace(path))):
                return "ask"
    return "pass"


def claude_shell_decision(document, permissions, rules, command) -> str:
    segments = split_command(command)
    pieces = [command] + (segments or [])
    for kind in ("deny", "ask"):
        if any(claude_rule_matches(rule, "Bash", text) for rule in rules[kind]
               for piece in pieces for text in claude_texts(piece, True)):
            return kind
    if not segments:
        return claude_unapproved(permissions)
    redirect = claude_redirect_check(permissions, rules, segments)
    if redirect == "deny":
        return "deny"
    if redirect == "ask":
        return claude_unapproved(permissions)
    if not has_substitution(command) and all(
            any(claude_rule_matches(rule, "Bash", text) for rule in rules["allow"]
                for text in claude_texts(segment, False)) or claude_read_only(segment)
            for segment in segments):
        return "allow"
    return claude_default(document, permissions, "Bash", command)


def claude_decide(document: dict, action: str, value: str, effect: str, context: dict) -> str:
    permissions = object_at(document, "permissions")
    rules = {kind: claude_rules(permissions, kind) for kind in ("deny", "ask", "allow")}
    if action == "command_network":
        return "deny" if claude_sandbox_confines(document) else "allow"
    if action == "command_write":
        # The sandbox receives Edit deny rules as write denials. On Linux it drops a rule that still holds a
        # wildcard after a final /** is removed, so only folder and file rules bind a program.
        if not claude_sandbox_confines(document):
            return "allow"
        if not inside_workspace(value):
            return "deny"
        for name, spec in rules["deny"]:
            if name == "Edit" and spec is not None:
                folder = spec[:-3] if spec.endswith("/**") else spec
                if not re.search(r"[*?\[\]]", folder) and path_rule_match(folder, value):
                    return "deny"
        return "allow"
    if action == "delegate":
        found = [claude_tool_decision(document, permissions, rules, name, value) for name in ("Task", "Agent")]
        return "allow" if "allow" in found else "ask" if "ask" in found else "deny"
    if action == "search_reaches":
        # The search tool turns Read deny rules into exclusions, so a refused file is skipped.
        return "deny" if claude_tool_decision(document, permissions, rules, "Read", value) == "deny" else "allow"
    tool = CLAUDE_TOOLS.get(action)
    if tool is None:
        return "not_modeled"
    if tool == "Bash":
        return claude_shell_decision(document, permissions, rules, value)
    return claude_tool_decision(document, permissions, rules, tool, value)


def claude_structure(document: dict, fragment: bool) -> list:
    problems = []
    permissions = document.get("permissions")
    if not isinstance(permissions, dict):
        return ["permissions is missing or not an object"]
    if KIND == "refusal_fragment":
        if fragment and (set(document) - {"permissions"} or set(permissions) - {"deny"}):
            problems.append("this fragment must hold only permissions.deny, so that it grants nothing")
        return problems
    if permissions.get("defaultMode") != "dontAsk":
        problems.append('permissions.defaultMode is not "dontAsk", so an unlisted action can wait for an approval prompt')
    if permissions.get("disableBypassPermissionsMode") != "disable":
        problems.append('permissions.disableBypassPermissionsMode is not "disable"')
    if permissions.get("ask"):
        problems.append("permissions.ask holds rules that wait for an approval prompt")
    for rule in string_list(permissions.get("allow"), "permissions.allow"):
        if rule not in GRANTS.get("claude_code", ()):
            problems.append(f"permissions.allow grants {rule!r}, which this policy does not declare")
    if string_list(permissions.get("additionalDirectories"), "permissions.additionalDirectories"):
        problems.append("permissions.additionalDirectories opens folders outside the workspace")
    if CLAUDE_SANDBOX:
        sandbox = claude_sandbox(document)
        if not claude_sandbox_confines(document):
            problems.append("sandbox must set enabled and failIfUnavailable to true, allowUnsandboxedCommands to false "
                            "and network.allowedDomains to an empty list")
        if sandbox.get("autoAllowBashIfSandboxed") is not False:
            problems.append("sandbox.autoAllowBashIfSandboxed is not false, so every sandboxed command would be allowed")
        if string_list(sandbox.get("excludedCommands"), "sandbox.excludedCommands"):
            problems.append("sandbox.excludedCommands runs commands outside the sandbox")
        filesystem = sandbox.get("filesystem", {})
        if isinstance(filesystem, dict) and string_list(filesystem.get("allowWrite"), "sandbox.filesystem.allowWrite"):
            problems.append("sandbox.filesystem.allowWrite opens more folders to commands")
    return problems


# --- Codex -----------------------------------------------------------------

def codex_decide(document: dict, action: str, value: str, effect: str, context: dict) -> str:
    sandbox = document.get("sandbox_mode")
    table = object_at(document, "sandbox_workspace_write")
    if sandbox == "danger-full-access":
        writes, network = True, True
    elif sandbox == "workspace-write":
        writes, network = True, table.get("network_access") is True
    else:
        writes, network = False, False
    if action in ("read", "search", "search_reaches"):
        return "allow"
    if action in ("edit", "create", "command_write"):
        return "allow" if writes and (inside_workspace(value) or sandbox == "danger-full-access") else "deny"
    if action in ("fetch", "command_network"):
        return "allow" if network else "deny"
    if action == "web_search":
        return "deny" if document.get("web_search") == "disabled" else "allow"
    if action == "shell":
        if effect == "network":
            return "allow" if network else "deny"
        if effect == "write":
            return "allow" if writes else "deny"
        return "allow"
    return "not_modeled"


def codex_structure(document: dict, fragment: bool) -> list:
    problems = []
    if document.get("approval_policy") != "never":
        problems.append('approval_policy is not "never", so a command can wait for approval')
    if document.get("sandbox_mode") != CODEX_SANDBOX:
        problems.append(f'sandbox_mode is not "{CODEX_SANDBOX}"')
    if document.get("web_search") != "disabled":
        problems.append('web_search is not "disabled"')
    for key in ("default_permissions", "permissions", "profile"):
        if key in document:
            problems.append(f"{key} would replace sandbox_mode with a profile this checker does not model")
    if CODEX_SANDBOX == "workspace-write":
        table = object_at(document, "sandbox_workspace_write")
        if table.get("network_access") is not False:
            problems.append("sandbox_workspace_write.network_access is not false")
        if table.get("writable_roots") not in (None, []):
            problems.append("sandbox_workspace_write.writable_roots opens folders outside the workspace")
    return problems


# --- OpenCode --------------------------------------------------------------

# Defaults read from the installed OpenCode binary: everything is allowed, reads of
# env files and folders outside the worktree ask, and the build agent may ask questions.
# The binary also asks before a repeated identical tool call. That default is not
# listed here; a base policy must start with "*": "deny" instead (opencode_structure).
OPENCODE_DEFAULTS = (
    ("*", "*", "allow"), ("external_directory", "*", "ask"), ("question", "*", "deny"),
    ("plan_enter", "*", "deny"), ("plan_exit", "*", "deny"), ("read", "*", "allow"),
    ("read", "*.env", "ask"), ("read", "*.env.*", "ask"), ("read", "*.env.example", "allow"),
    ("question", "*", "allow"), ("plan_enter", "*", "allow"),
)
OPENCODE_VERBS = ("allow", "deny", "ask")
OPENCODE_TOOLS = {"read": "read", "search": "grep", "edit": "edit", "create": "edit", "fetch": "webfetch",
                  "web_search": "websearch", "delegate": "task"}


def opencode_own_rules(document: dict) -> list:
    """The rules the document itself sets, in the order OpenCode reads them, without the defaults."""
    merged: dict = {}
    tools = document.get("tools")
    if tools is not None:
        if not isinstance(tools, dict) or any(not isinstance(flag, bool) for flag in tools.values()):
            raise InputRefused("tools must map tool names to true or false")
        for name, enabled in tools.items():
            merged["edit" if name in ("write", "edit", "patch") else name] = "allow" if enabled else "deny"
    permission = document.get("permission", {})
    if isinstance(permission, str):
        permission = {"*": permission}
    if not isinstance(permission, dict):
        raise InputRefused("permission is neither a verb nor an object")
    for action, rule in permission.items():
        merged[action] = rule
    rules = []
    for action, rule in merged.items():
        if isinstance(rule, str):
            entries = [("*", rule)]
        elif isinstance(rule, dict) and rule:
            entries = list(rule.items())
        else:
            raise InputRefused(f"permission.{action} is neither a verb nor a pattern object")
        for pattern, verb in entries:
            if verb not in OPENCODE_VERBS:
                raise InputRefused(f"permission.{action} uses the unknown verb {verb!r}")
            rules.append((action, pattern, verb))
    return rules


def opencode_rules(document: dict) -> list:
    return list(OPENCODE_DEFAULTS) + opencode_own_rules(document)


def opencode_decision(rules: list, action: str, value: str) -> str:
    decision = "ask"
    for rule_action, pattern, verb in rules:
        if wildcard_match(rule_action, action, True) and wildcard_match(pattern, value, True):
            decision = verb
    return decision


def opencode_decide(document: dict, action: str, value: str, effect: str, context: dict) -> str:
    rules = opencode_rules(document)
    if action in ("command_network", "command_write"):
        return "allow"  # OpenCode starts no process sandbox
    if action == "search_reaches":
        # The search tool asks only about the search text and runs ripgrep with hidden files included.
        decision = opencode_decision(rules, "grep", SEARCH_TERM)
        return "allow" if decision == "allow" else decision
    if action in ("read", "edit", "create") and not inside_workspace(value):
        folder = value.rsplit("/", 1)[0] if "/" in value else "."
        outside = opencode_decision(rules, "external_directory", folder + "/*")
        if outside != "allow":
            return outside
    if action == "shell":
        found = [opencode_decision(rules, "bash", segment) for segment in (split_command(value) or [value])]
        return "deny" if "deny" in found else "ask" if "ask" in found else "allow"
    name = OPENCODE_TOOLS.get(action)
    return opencode_decision(rules, name, value) if name else "not_modeled"


def opencode_structure(document: dict, fragment: bool) -> list:
    problems = []
    for key in ("agent", "mode"):
        section = document.get(key)
        if isinstance(section, dict) and any(isinstance(item, dict) and ("permission" in item or "tools" in item)
                                             for item in section.values()):
            problems.append(f"{key} settings change permissions per agent, which this checker does not model")
    own = opencode_own_rules(document)
    verbs = [verb for _action, _pattern, verb in own]
    if KIND == "refusal_fragment":
        if fragment and (set(document) - {"permission"} or any(verb != "deny" for verb in verbs)):
            problems.append("this fragment must hold only deny rules under permission, so that it grants nothing")
        return problems
    if "ask" in verbs:
        problems.append("a permission rule uses ask, which waits for a person in an unattended run")
    permission = document.get("permission", {})
    entries = list(permission.items()) if isinstance(permission, dict) else [("*", permission)]
    if not entries or entries[0] != ("*", "deny"):
        problems.append('permission does not start with the catch-all rule "*": "deny", so OpenCode defaults '
                        "that ask, such as its prompt before a repeated identical tool call, can stall "
                        "an unattended run")
    granted = set(GRANTS.get("opencode", ()))
    for action, pattern, verb in own:
        if verb == "allow" and (action, pattern) not in granted:
            problems.append(f"permission.{action} grants {pattern!r}, which this policy does not declare")
    rules = opencode_rules(document)
    for action in ("question", "external_directory"):
        if opencode_decision(rules, action, "*") == "ask":
            problems.append(f"{action} still asks, which stalls an unattended run; add a deny rule")
    return problems


# --- Gemini CLI ------------------------------------------------------------

GEMINI_TOOLS = {"read": "read_file", "search": "grep_search", "edit": "replace", "create": "write_file",
                "shell": "run_shell_command", "fetch": "web_fetch", "web_search": "google_web_search",
                "delegate": "invoke_agent", "search_reaches": "grep_search"}
GEMINI_DEFAULT_ALLOWED = ("read_file", "read_many_files", "list_directory", "glob", "grep_search",
                          "google_web_search")
SHELL_ENTRY = "run_shell_command"


def gemini_prefix(prefix: str, command: str) -> bool:
    rest = command[len(prefix):]
    return command.startswith(prefix) and (rest == "" or rest[0] in " \t\n\"")


def gemini_shell(core, allowed, mode, command) -> str:
    if has_redirection(command):
        return "deny"  # the policy engine asks on redirection; a headless run treats that as a refusal
    segments = split_command(command) or [command]

    def narrowed(entries):
        return [entry[len(SHELL_ENTRY) + 1:-1] for entry in entries
                if entry.startswith(SHELL_ENTRY + "(") and entry.endswith(")")]

    if core is not None and mode != "plan":
        if SHELL_ENTRY in core:
            return "allow"
        prefixes = narrowed(core)
        return "allow" if all(any(gemini_prefix(p, s) for p in prefixes) for s in segments) else "deny"
    if SHELL_ENTRY in allowed:
        return "allow"
    prefixes = narrowed(allowed)
    if prefixes:
        return "allow" if all(any(gemini_prefix(p, s) for p in prefixes) for s in segments) else "deny"
    return "ask"


def gemini_tool_sandbox(document: dict) -> bool:
    """Tool sandboxing runs each command in Bubblewrap without the network unless it is granted."""
    return (object_at(document, "security").get("toolSandboxing") is True
            and object_at(document, "tools").get("sandboxNetworkAccess") is not True)


def gemini_decide(document: dict, action: str, value: str, effect: str, context: dict) -> str:
    tools = object_at(document, "tools")
    mode = object_at(document, "general").get("defaultApprovalMode", "default")
    if action == "command_network":
        return "deny" if gemini_tool_sandbox(document) else "allow"
    if action == "command_write":
        return "allow"  # the workspace stays writable for commands, even inside the tool sandbox
    tool = GEMINI_TOOLS.get(action)
    if tool is None:
        return "not_modeled"
    if action in ("read", "edit", "create") and not inside_workspace(value):
        return "deny"
    ignored = context.get("ignored")
    if action == "read" and ignored is not None and ignored(value):
        return "deny"
    core = tools.get("core")
    if core is not None:
        core = string_list(core, "tools.core")
    exclude = string_list(tools.get("exclude"), "tools.exclude")
    confirm = string_list(tools.get("confirmationRequired"), "tools.confirmationRequired")
    allowed = string_list(tools.get("allowed"), "tools.allowed")
    if tool in exclude:
        return "deny"
    if tool in confirm:
        return "ask"
    if tool == SHELL_ENTRY:
        return gemini_shell(core, allowed, mode, value)
    if core is not None and mode != "plan":
        decision = "allow" if tool in core else "deny"
    elif tool in allowed or tool in GEMINI_DEFAULT_ALLOWED:
        decision = "allow"
    else:
        decision = "ask"
    if action == "search_reaches" and decision == "allow" and ignored is not None and ignored(value):
        return "deny"  # the search tool skips files that the ignore patterns name
    return decision


def gemini_structure(document: dict, fragment: bool) -> list:
    problems = []
    for key in ("policyPaths", "adminPolicyPaths"):
        if key in document:
            problems.append(f"{key} loads policy files this checker does not model")
    filtering = object_at(document, "context", "fileFiltering")
    if KIND == "refusal_fragment":
        paths = string_list(filtering.get("customIgnoreFilePaths"), "context.fileFiltering.customIgnoreFilePaths")
        if GEMINI_IGNORE_FILE not in paths:
            problems.append(f"context.fileFiltering.customIgnoreFilePaths does not name {GEMINI_IGNORE_FILE}")
        if filtering.get("respectGeminiIgnore") is False:
            problems.append("context.fileFiltering.respectGeminiIgnore is false")
        allowed_keys = {"respectGeminiIgnore", "customIgnoreFilePaths"}
        if fragment and (set(document) - {"context"} or set(object_at(document, "context")) - {"fileFiltering"}
                         or set(filtering) - allowed_keys):
            problems.append("this fragment must hold only context.fileFiltering ignore settings, so that it grants nothing")
        return problems
    tools = object_at(document, "tools")
    if object_at(document, "general").get("defaultApprovalMode") != "default":
        problems.append('general.defaultApprovalMode is not "default"; plan mode skips the tools.core allowlist')
    if object_at(document, "security").get("disableYoloMode") is not True:
        problems.append("security.disableYoloMode is not true")
    if string_list(tools.get("confirmationRequired"), "tools.confirmationRequired"):
        problems.append("tools.confirmationRequired holds tools that wait for an approval prompt")
    if not isinstance(tools.get("core"), list):
        problems.append("tools.core is missing, so every built-in tool stays available")
    granted = set(GRANTS.get("gemini_cli", ()))
    for name in ("core", "allowed"):
        for entry in string_list(tools.get(name), f"tools.{name}"):
            if entry not in granted:
                problems.append(f"tools.{name} grants {entry!r}, which this policy does not declare")
    if GEMINI_TOOL_SANDBOX:
        if object_at(document, "security").get("toolSandboxing") is not True:
            problems.append("security.toolSandboxing is not true, so code run by an allowed command is not confined")
        if tools.get("sandboxNetworkAccess") is True:
            problems.append("tools.sandboxNetworkAccess opens the network to sandboxed commands")
        if string_list(tools.get("sandboxAllowedPaths"), "tools.sandboxAllowedPaths"):
            problems.append("tools.sandboxAllowedPaths opens more folders to sandboxed commands")
    return problems


DECIDERS = {"claude_code": claude_decide, "codex": codex_decide, "opencode": opencode_decide,
            "gemini_cli": gemini_decide}
STRUCTURE = {"claude_code": claude_structure, "codex": codex_structure, "opencode": opencode_structure,
             "gemini_cli": gemini_structure}
# Keys that can add tools or decisions outside the permission settings. They are listed, not checked.
EXTENSION_KEYS = {"claude_code": ("hooks", "mcpServers", "enabledMcpjsonServers", "enableAllProjectMcpServers"),
                  "codex": ("mcp_servers", "hooks"), "opencode": ("mcp", "plugin"),
                  "gemini_cli": ("mcpServers", "hooks")}


def not_modeled(harness: str, document: dict) -> list:
    found = [key for key in EXTENSION_KEYS.get(harness, ()) if key in document]
    tools = document.get("tools")
    if harness == "gemini_cli" and isinstance(tools, dict):
        found += [f"tools.{key}" for key in ("discoveryCommand", "callCommand") if key in tools]
    return found


# --- check -----------------------------------------------------------------

def check_document(harness: str, label: str, text: str, context: dict, fragment: bool, toml_reader: str) -> dict:
    result = {"harness": harness, "file": label, "passed": False, "problems": [], "known_limits": [],
              "stale_known_limits": [], "not_modeled": [], "decisions": {}}
    if harness not in RENDERED:
        result["problems"].append(f"this package has no {harness} settings: {NOT_RENDERED.get(harness, 'not rendered')}")
        return result
    document = read_toml(text, toml_reader) if harness == "codex" else read_json(text)
    problems = STRUCTURE[harness](document, fragment)
    result["not_modeled"] = not_modeled(harness, document)
    limits = KNOWN_LIMITS.get(harness, {})
    for probe, action, value, effect, expected in PROBES:
        if expected == "not_denied" and not fragment:
            continue  # in a merged workspace the base settings decide these
        if isinstance(value, dict):
            if harness not in value:
                continue
            value = value[harness]
        decision = DECIDERS[harness](document, action, value, effect, context)
        result["decisions"][probe] = decision
        holds = decision == expected if expected in ("allow", "deny") else decision != "deny"
        if probe in limits:
            if holds:
                result["stale_known_limits"].append(probe)
            else:
                result["known_limits"].append({"probe": probe, "decision": decision, "reason": limits[probe]})
        elif not holds:
            problems.append(f"{probe}: {action} {value!r} is {decision}, expected {expected}")
    result["problems"] = problems
    result["passed"] = not problems
    return result


def gemini_context(root: Path, ignore_file: str | None, document_text: str | None) -> dict:
    """Load the ignore patterns a Gemini CLI settings document points to, when this policy needs them."""
    if not GEMINI_IGNORE_FILE:
        return {}
    texts = []
    if ignore_file:
        texts.append(read_confined(root, ignore_file))
    elif document_text is not None:
        filtering = object_at(read_json(document_text), "context", "fileFiltering")
        for relative in string_list(filtering.get("customIgnoreFilePaths"), "customIgnoreFilePaths"):
            if (root / relative).exists() or (root / relative).is_symlink():
                texts.append(read_confined(root, relative))  # a missing file leaves the probes to fail
        if (root / ".geminiignore").is_file() and filtering.get("respectGeminiIgnore") is not False:
            texts.append(read_confined(root, ".geminiignore"))
    return {"ignored": ignore_matcher("\n".join(texts))} if texts else {}


def build_report(results: list) -> dict:
    passed = bool(results) and all(item["passed"] for item in results)
    return {"record_type": RECORD_TYPE, "policy": POLICY, "version": VERSION, "passed": passed,
            "files": results, "allowed_commands": list(DECLARED_COMMANDS),
            "writable_paths": list(WRITABLE_PATHS), "refused": list(REFUSED)}


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Check the {NATIVE} policy in harness settings.")
    parser.add_argument("--root", default=".", help="workspace root (default: the current folder)")
    parser.add_argument("--harness", choices=sorted(SETTINGS_FILES), help="harness of --file or --stdin")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", help="one settings file, relative to --root")
    source.add_argument("--stdin", action="store_true", help="read one settings document from standard input")
    parser.add_argument("--ignore-file", help="Gemini CLI ignore patterns for --file or --stdin, relative to --root")
    parser.add_argument("--toml-reader", choices=("auto", "subset"), default="auto",
                        help="auto uses tomllib when present; subset forces the built-in reader")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise InputRefused("--root is not a folder")
        results = []
        if options.file or options.stdin:
            if not options.harness:
                raise InputRefused("--file and --stdin need --harness")
            if options.stdin:
                data = sys.stdin.buffer.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise InputRefused("standard input is larger than 1 MiB")
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    raise InputRefused("standard input is not UTF-8") from None
                label = "<stdin>"
            else:
                text, label = read_confined(root, options.file), options.file
            context = gemini_context(root, options.ignore_file, None) if options.harness == "gemini_cli" else {}
            results.append(check_document(options.harness, label, text, context, True, options.toml_reader))
        else:
            for harness, relative in SETTINGS_FILES.items():
                if not (root / relative).exists() and not (root / relative).is_symlink():
                    continue
                text = read_confined(root, relative)
                context = gemini_context(root, None, text) if harness == "gemini_cli" else {}
                results.append(check_document(harness, relative, text, context, False, options.toml_reader))
    except InputRefused as error:
        print(json.dumps({"record_type": RECORD_TYPE, "policy": POLICY, "version": VERSION, "passed": False,
                          "refused_input": str(error)}, sort_keys=True))
        return 2
    report = build_report(results)
    if not results:
        report["problem"] = "no harness settings file was found under the root"
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(run())

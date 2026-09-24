"""Run one declared test command without a shell and print a short JSON summary. Effects: starts that one command as a subprocess and reads its output; stops that command's process group at the time limit or on a stop signal; writes no file.

Usage, from the repository root:

    python3 -I -B summarize_test_run.py [--cwd FOLDER] [--timeout SECONDS] -- COMMAND [ARGUMENT ...]

The summary names the exact command, the exit status, the test counts and the
first failure, so the caller does not have to read the raw log. The script
keeps at most the first 4 MiB and the last 4 MiB of the output in memory. The
middle of a longer log is not parsed, and output_bytes reports the full length.

Leading NAME=value words of the command are passed as environment variables,
as a shell would pass them. Before anything starts, a short guard refuses
commands that are plainly not a test run: shell operators written as separate
words, shells, wrapper programs such as env, timeout or xargs, privilege
tools, file and deletion tools, git and network clients, package installers,
and the install, remove, publish and fetch words of common package tools. The
guard is not a sandbox. A test runner, a make target or a "run" subcommand can
still start any program, write files or use the network, so the host must
limit those effects. No shell is used, so quotes and substitutions inside one
argument reach the program as plain text.

--timeout defaults to 540 seconds, so that the script finishes inside a shell
tool limit of 600 seconds. Give the shell tool a longer limit than --timeout.
If a stop signal (SIGTERM, SIGINT or SIGHUP) arrives first, the script stops
the command's process group and still prints its JSON object, with the result
"interrupted".

Exit status: 0 when the command ran and passed; 1 when it did not pass
(failed, no_tests, unconfirmed, timeout, interrupted or not_started); 2 when
the input was refused and nothing was started. Every outcome prints one JSON
object on standard output.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

RECORD_TYPE = "test_run_summary/v1"
DEFAULT_TIMEOUT = 540
MAXIMUM_TIMEOUT = 7200
HEAD_BYTES = 4 * 1024 * 1024
TAIL_BYTES = 4 * 1024 * 1024
READ_CHUNK = 64 * 1024
EXCERPT_LINES = 20
TAIL_LINES = 15
LINE_CHARACTERS = 240
NAME_CHARACTERS = 300
POLL_SECONDS = 0.2

SHELL_OPERATORS = frozenset({"|", "||", "&", "&&", ";", ";;", ">", ">>", "<", "<<", "<<<", "2>", "2>>", "&>",
                             "2>&1", "|&"})
SHELL_PROGRAMS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish", "csh", "tcsh", "pwsh", "powershell", "cmd"})
WRAPPER_PROGRAMS = frozenset({"env", "timeout", "nice", "nohup", "xargs", "stdbuf", "ionice", "time", "setsid",
                              "unbuffer", "chrt", "taskset", "flock", "busybox", "command", "exec", "builtin",
                              "watch", "script", "strace", "ltrace", "chroot", "nsenter", "unshare", "runuser",
                              "sg", "newgrp", "systemd-run"})
PRIVILEGE_PROGRAMS = frozenset({"sudo", "su", "doas", "pkexec"})
FILE_PROGRAMS = frozenset({"rm", "rmdir", "unlink", "shred", "truncate", "dd", "mv", "cp", "ln", "chmod", "chown",
                           "chgrp", "install", "mkfs", "find", "tee", "touch", "mkdir", "wipe", "srm"})
NETWORK_PROGRAMS = frozenset({"git", "gh", "curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "netcat",
                              "telnet", "ftp"})
PACKAGE_PROGRAMS = frozenset({"pip", "pip3", "pipx", "easy_install", "npx", "pnpx", "bunx", "uvx", "gem", "apt",
                              "apt-get", "dnf", "yum", "pacman", "apk", "brew", "snap", "port", "choco", "winget",
                              "scoop", "flatpak"})
CONDA_INSTALL_WORDS = frozenset({"install", "create", "remove", "uninstall", "update", "upgrade", "env", "clean"})
#: For tools that can also run tests: after the program, the first word that is in one of these two tables
#: decides. A word in RUN_WORDS lets the command through; a word in INSTALL_WORDS refuses it. Other words,
#: such as option values, are skipped.
RUN_WORDS = {
    "npm": frozenset({"test", "t", "tst", "run", "run-script", "rum", "urn"}),
    "pnpm": frozenset({"test", "t", "run", "run-script", "exec"}),
    "yarn": frozenset({"test", "run"}),
    "bun": frozenset({"test", "run"}),
    "uv": frozenset({"run"}),
    "poetry": frozenset({"run"}),
    "pdm": frozenset({"run"}),
    "cargo": frozenset({"test", "t", "nextest"}),
    "go": frozenset({"test", "vet"}),
    "bundle": frozenset({"exec"}),
    "composer": frozenset({"test", "run-script", "run"}),
    "conda": frozenset({"run"}),
    "mamba": frozenset({"run"}),
    "micromamba": frozenset({"run"}),
    "dotnet": frozenset({"test"}),
    "deno": frozenset({"test", "task"}),
    "make": frozenset({"test", "tests", "check"}),
}
INSTALL_WORDS = {
    "npm": frozenset({"install", "i", "in", "ins", "inst", "insta", "instal", "isnt", "isnta", "isntal", "isntall",
                      "add", "ci", "clean-install", "ic", "install-clean", "isntall-clean", "install-test", "it",
                      "install-ci-test", "cit", "uninstall", "unlink", "remove", "rm", "r", "un", "update", "up",
                      "upgrade", "udpate", "link", "ln", "publish", "exec", "x", "dedupe", "ddp", "prune",
                      "rebuild", "rb"}),
    "pnpm": frozenset({"install", "i", "add", "remove", "rm", "uninstall", "un", "update", "up", "upgrade", "link",
                       "ln", "unlink", "publish", "dlx", "import", "fetch", "install-test", "it", "rebuild", "rb",
                       "prune", "dedupe"}),
    "yarn": frozenset({"install", "add", "remove", "upgrade", "up", "upgrade-interactive", "dlx", "publish", "link",
                       "unlink", "import", "global"}),
    "bun": frozenset({"install", "i", "add", "a", "remove", "rm", "update", "link", "unlink", "publish", "x",
                      "create", "upgrade", "pm"}),
    "uv": frozenset({"sync", "add", "remove", "lock", "pip", "tool", "python", "venv", "self", "publish", "init"}),
    "poetry": frozenset({"install", "add", "remove", "update", "lock", "publish", "self", "sync"}),
    "pdm": frozenset({"install", "add", "remove", "update", "lock", "sync", "publish", "self"}),
    "cargo": frozenset({"install", "uninstall", "add", "remove", "update", "publish", "fetch", "yank", "login",
                        "owner", "vendor"}),
    "go": frozenset({"install", "get", "mod", "work", "clean"}),
    "bundle": frozenset({"install", "add", "update", "remove", "lock"}),
    "composer": frozenset({"install", "require", "update", "remove", "upgrade", "reinstall", "global",
                           "create-project"}),
    "conda": CONDA_INSTALL_WORDS,
    "mamba": CONDA_INSTALL_WORDS,
    "micromamba": CONDA_INSTALL_WORDS,
    "dotnet": frozenset({"add", "remove", "restore", "tool", "workload", "nuget", "new"}),
    "deno": frozenset({"install", "add", "remove", "uninstall", "upgrade", "cache"}),
    "make": frozenset({"install", "uninstall", "clean", "distclean", "deploy", "publish", "release"}),
}
INSTALL_WITHOUT_A_WORD = frozenset({"yarn", "bundle"})
PYTHON_PROGRAM = re.compile(r"(?:python|pypy)[0-9.]*|py")
PYTHON_MODULE_FLAG = re.compile(r"-[bBdEhiIOPqsSuvVx]*m(.*)")
PYTHON_CODE_FLAG = re.compile(r"-[bBdEhiIOPqsSuvVx]*c.*")
PYTHON_VALUE_OPTIONS = frozenset({"-W", "-X", "-Q"})
PYTHON_INSTALL_MODULES = frozenset({"pip", "pipx", "ensurepip"})
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
TIMEOUT_TEXT = re.compile(r"[0-9]{1,5}")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
STOP_SIGNALS = tuple(getattr(signal, name) for name in ("SIGTERM", "SIGINT", "SIGHUP") if hasattr(signal, name))
STOP_REQUESTS: list[int] = []

PYTEST_SUMMARY = re.compile(r"^=*\s*(\d+ (?:passed|failed|errors?|skipped|xfailed|xpassed|deselected|warnings?|rerun)"
                            r"(?:, \d+ \w+)*) in [\d.]+s(?: \([^)]*\))?\s*=*$")
PYTEST_EMPTY = re.compile(r"^=*\s*no tests ran(?:, [^=]*)? in [\d.]+s(?: \([^)]*\))?\s*=*$")
PYTEST_COLLECTED = re.compile(r"^=*\s*(?:\d+(?:/\d+)? tests? collected|no tests collected)(?: \(\d+ deselected\))?"
                              r"(?:, \d+ \w+)* in [\d.]+s(?: \([^)]*\))?\s*=*$")
PYTEST_PART = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)\b")
PYTEST_SECTION = re.compile(r"^=+ (FAILURES|ERRORS) =+$")
PYTEST_HEADER = re.compile(r"^_{3,} (.+?) _{3,}$")
PYTEST_ERROR_HEADER = re.compile(r"^ERROR (?:at (?:setup|teardown) of|collecting) (.+)$")
PYTEST_SHORT = re.compile(r"^(FAILED|ERROR) (\S+)(?: - (.*))?$")
PYTEST_LOCATION = re.compile(r"^\S+:\d+: \S")
PYTEST_CAPTURED = re.compile(r"^-+ Captured ")
UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in [\d.]+s$")
UNITTEST_STATUS = re.compile(r"^(?:OK|FAILED)(?: \((.*)\))?$")
UNITTEST_HEADER = re.compile(r"^(?:FAIL|ERROR|UNEXPECTED SUCCESS): (.+)$")
UNITTEST_RULE = re.compile(r"^(?:={20,}|-{20,})$")
CARGO_RESULT = re.compile(r"^test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;")
CARGO_STDOUT = re.compile(r"^---- (\S+) stdout ----$")
CARGO_FAILED_TEST = re.compile(r"^test (\S+) \.\.\. FAILED$")
GO_RESULT = re.compile(r"^(\s*)--- (PASS|FAIL|SKIP): (\S+)")
GO_RUN = re.compile(r"^=== RUN\s+(\S+)")
GO_PACKAGE = re.compile(r"^(?:ok|FAIL|\?)\s+\S+\s+(?:[\d.]+s|\(cached\)|\[)")
GO_BROKEN = re.compile(r"^FAIL\s+\S+ \[(?:build|setup) failed\]")
JEST_TESTS = re.compile(r"^\s*Tests:?\s+(.*\d.*)$")
JEST_PART = re.compile(r"(\d+) (failed|passed|skipped|todo|pending)\b")
JEST_BULLET = re.compile(r"^\s*● (.+)$")
VITEST_FAIL = re.compile(r"^\s*FAIL\s+(\S.* > .+)$")


class Refusal(Exception):
    """Input that this script will not run."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class BoundedOutput:
    """Keeps the first HEAD_BYTES and about the last TAIL_BYTES of one stream."""

    def __init__(self) -> None:
        self.head = bytearray()
        self.tail: deque[bytes] = deque()
        self.tail_size = 0
        self.total = 0
        self.left_out = 0
        self.lock = threading.Lock()

    def drain(self, stream) -> None:
        try:
            while True:
                chunk = stream.read1(READ_CHUNK)
                if not chunk:
                    break
                with self.lock:
                    self.total += len(chunk)
                    room = HEAD_BYTES - len(self.head)
                    if room > 0:
                        self.head += chunk[:room]
                        chunk = chunk[room:]
                    if chunk:
                        self.tail.append(chunk)
                        self.tail_size += len(chunk)
                        while self.tail and self.tail_size - len(self.tail[0]) >= TAIL_BYTES:
                            dropped = self.tail.popleft()
                            self.tail_size -= len(dropped)
                            self.left_out += len(dropped)
        except (OSError, ValueError):
            return

    def text(self) -> str:
        with self.lock:
            head, tail, left_out = bytes(self.head), b"".join(self.tail), self.left_out
        middle = f"\n[{left_out} bytes of output left out]\n".encode("ascii") if left_out else b""
        return (head + middle + tail).decode("utf-8", "replace")


def clip(text: str, limit: int = LINE_CHARACTERS) -> str:
    return text if len(text) <= limit else text[:limit - 3] + "..."


def bounded(lines: list[str], keep_end: bool = False) -> list[str]:
    kept = [clip(line.rstrip()) for line in lines if line.strip()]
    if len(kept) <= EXCERPT_LINES:
        return kept
    left_out = len(kept) - (EXCERPT_LINES - 1)
    if keep_end:
        return [f"[{left_out} lines left out]"] + kept[-(EXCERPT_LINES - 1):]
    return kept[:EXCERPT_LINES - 1] + [f"[{left_out} lines left out]"]


def clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        lines.append(ANSI.sub("", raw.rsplit("\r", 1)[-1]).rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return lines


def failure(name: str | None, excerpt: list[str]) -> dict:
    return {"test": clip(name, NAME_CHARACTERS) if name else None, "excerpt": excerpt}


def parse_pytest(lines: list[str]):
    summary_line = next((line for line in reversed(lines) if PYTEST_SUMMARY.match(line) or PYTEST_EMPTY.match(line)
                         or PYTEST_COLLECTED.match(line)), None)
    if summary_line is None:
        return None
    found: dict[str, int] = {}
    for number, word in PYTEST_PART.findall(summary_line):
        key = {"error": "errors", "xfailed": "skipped", "xpassed": "passed"}.get(word, word)
        found[key] = found.get(key, 0) + int(number)
    counts = {key: found.get(key, 0) for key in ("passed", "failed", "errors", "skipped")}
    if not PYTEST_SUMMARY.match(summary_line):
        counts = {"passed": 0, "failed": 0, "errors": counts["errors"], "skipped": 0}
    return "pytest", counts, pytest_first_failure(lines), sum(counts.values()) == 0


def pytest_blocks(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Each report block of the FAILURES and ERRORS sections, in output order: section, header, lines."""
    blocks: list[tuple[str, str, list[str]]] = []
    section = current = None
    for line in lines:
        heading = PYTEST_SECTION.match(line)
        if heading:
            section, current = heading.group(1), None
            continue
        if section is None:
            continue
        if line.startswith("="):
            section = current = None
            continue
        header = PYTEST_HEADER.match(line)
        if header:
            current = (section, header.group(1), [])
            blocks.append(current)
        elif current is not None:
            if PYTEST_CAPTURED.match(line):
                current = None
            else:
                current[2].append(line)
    return blocks


def pytest_node(section: str, header: str, short: list[tuple]) -> str:
    """The full test id from the short summary for one block header, or the header's own name."""
    error = PYTEST_ERROR_HEADER.match(header)
    kind = "ERROR" if error or section == "ERRORS" else "FAILED"
    name = error.group(1) if error else header
    base, bracket, rest = name.partition("[")
    wanted = base.replace(".", "::") + bracket + rest
    for short_kind, node, _message in short:
        if short_kind == kind and (node == name or node.endswith("::" + wanted)):
            return node
    return name


def pytest_first_failure(lines: list[str]):
    short = [match.groups() for match in (PYTEST_SHORT.match(line) for line in lines) if match]
    blocks = pytest_blocks(lines)
    if blocks:
        section, header, block = blocks[0]
        chosen = [line for line in block if line.startswith(("E ", ">")) or PYTEST_LOCATION.match(line)]
        excerpt = bounded(chosen) if chosen else bounded(block, keep_end=True)
        return failure(pytest_node(section, header, short), excerpt)
    if short:
        _kind, node, message = short[0]
        return failure(node, [clip(message)] if message else [])
    return None


def parse_unittest(lines: list[str]):
    ran_index = next((index for index in range(len(lines) - 1, -1, -1) if UNITTEST_RAN.match(lines[index])), None)
    if ran_index is None:
        return None
    total = int(UNITTEST_RAN.match(lines[ran_index]).group(1))
    parts: dict[str, int] = {}
    for line in lines[ran_index + 1:ran_index + 6]:
        status = UNITTEST_STATUS.match(line.strip())
        if status:
            for item in (status.group(1) or "").split(","):
                key, _, value = item.strip().partition("=")
                if value.strip().isdigit():
                    parts[key.strip()] = int(value)
            break
    failed = parts.get("failures", 0) + parts.get("unexpected successes", 0)
    errors = parts.get("errors", 0)
    skipped = parts.get("skipped", 0) + parts.get("expected failures", 0)
    counts = {"passed": max(total - failed - errors - skipped, 0), "failed": failed, "errors": errors,
              "skipped": skipped}
    return "unittest", counts, unittest_first_failure(lines[:ran_index]), total == 0


def unittest_first_failure(lines: list[str]):
    for index, line in enumerate(lines):
        header = UNITTEST_HEADER.match(line)
        if not header:
            continue
        position = index + 1
        if position < len(lines) and UNITTEST_RULE.match(lines[position]):
            position += 1
        block = []
        for inner in lines[position:]:
            if UNITTEST_RULE.match(inner):
                break
            stripped = inner.strip()
            if stripped and stripped != "Traceback (most recent call last):" and set(stripped) - set("^~"):
                block.append(inner)
        return failure(header.group(1), bounded(block, keep_end=True))
    return None


def parse_cargo(lines: list[str]):
    results = [match for match in (CARGO_RESULT.match(line) for line in lines) if match]
    if not results:
        return None
    passed, failed, ignored = (sum(int(match.group(number)) for match in results) for number in (1, 2, 3))
    counts = {"passed": passed, "failed": failed, "errors": 0, "skipped": ignored}
    first = None
    for index, line in enumerate(lines):
        header = CARGO_STDOUT.match(line)
        if header:
            block = []
            for inner in lines[index + 1:]:
                if CARGO_STDOUT.match(inner) or inner == "failures:" or inner.startswith("test result:"):
                    break
                if not inner.startswith("note: run with"):
                    block.append(inner)
            first = failure(header.group(1), bounded(block))
            break
    if first is None:
        failed_test = next((match for match in (CARGO_FAILED_TEST.match(line) for line in lines) if match), None)
        if failed_test:
            first = failure(failed_test.group(1), [])
    return "cargo", counts, first, passed + failed + ignored == 0


def parse_go(lines: list[str]):
    results = [(match, index) for index, match in enumerate(GO_RESULT.match(line) for line in lines) if match]
    packages = [line for line in lines if GO_PACKAGE.match(line) or GO_BROKEN.match(line)]
    if not results and not packages:
        return None
    verbose = any(GO_RUN.match(line) for line in lines)
    top = [match for match, _ in results if match.group(1) == ""]
    failed = sum(1 for match in top if match.group(2) == "FAIL")
    errors = sum(1 for line in lines if GO_BROKEN.match(line))
    if verbose:
        counts = {"passed": sum(1 for match in top if match.group(2) == "PASS"), "failed": failed,
                  "errors": errors, "skipped": sum(1 for match in top if match.group(2) == "SKIP")}
    else:
        counts = {"passed": None, "failed": failed, "errors": errors, "skipped": None}
    no_tests = not results and bool(packages) and all(
        "[no test files]" in line or "[no tests to run]" in line for line in packages)
    return "go", counts, go_first_failure(lines, results), no_tests


def go_first_failure(lines: list[str], results):
    for match, index in results:
        if match.group(2) != "FAIL":
            continue
        name, indent = match.group(3), len(match.group(1))
        block: list[str] = []
        run_index = next((position for position in range(index - 1, -1, -1)
                          if GO_RUN.match(lines[position]) and GO_RUN.match(lines[position]).group(1) == name), None)
        if run_index is not None:
            block = [line for line in lines[run_index + 1:index]
                     if line.startswith((" ", "\t")) and not GO_RESULT.match(line)]
        if not block:
            for line in lines[index + 1:]:
                if not line.strip() or len(line) - len(line.lstrip()) <= indent:
                    break
                block.append(line)
        return failure(name, bounded(block))
    for index, line in enumerate(lines):
        if line.startswith("panic: "):
            return failure(None, bounded(lines[index:index + EXCERPT_LINES]))
    return None


def parse_jest(lines: list[str]):
    summary_line = None
    for line in reversed(lines):
        match = JEST_TESTS.match(line)
        if match and JEST_PART.search(match.group(1)):
            summary_line = match.group(1)
            break
    if summary_line is None:
        return None
    runner = "vitest" if "|" in summary_line else "jest"
    found: dict[str, int] = {}
    for number, word in JEST_PART.findall(summary_line):
        key = {"todo": "skipped", "pending": "skipped"}.get(word, word)
        found[key] = found.get(key, 0) + int(number)
    counts = {"passed": found.get("passed", 0), "failed": found.get("failed", 0), "errors": 0,
              "skipped": found.get("skipped", 0)}
    first = None
    for index, line in enumerate(lines):
        bullet, vitest = JEST_BULLET.match(line), VITEST_FAIL.match(line)
        if (bullet and not bullet.group(1).startswith("Console")) or vitest:
            block = []
            for inner in lines[index + 1:]:
                if JEST_BULLET.match(inner) or VITEST_FAIL.match(inner) or JEST_TESTS.match(inner) \
                        or inner.lstrip().startswith(("Test Suites:", "Test Files")):
                    break
                block.append(inner.strip())
            first = failure((bullet or vitest).group(1).strip(), bounded(block))
            break
    return runner, counts, first, sum(counts.values()) == 0


def parse(lines: list[str]):
    for parser in (parse_pytest, parse_unittest, parse_cargo, parse_go, parse_jest):
        found = parser(lines)
        if found is not None:
            return found
    return "unknown", None, None, False


def parse_options(arguments: list[str]) -> tuple[str, int]:
    if "--" not in arguments:
        raise Refusal("put -- between the options and the declared test command")
    options = arguments[:arguments.index("--")]
    cwd, timeout = ".", DEFAULT_TIMEOUT
    index = 0
    while index < len(options):
        name = options[index]
        if name not in ("--cwd", "--timeout") or index + 1 >= len(options):
            raise Refusal(f"unknown or incomplete option {name!r}; the options are --cwd and --timeout")
        value = options[index + 1]
        if name == "--cwd":
            cwd = value
        elif not TIMEOUT_TEXT.fullmatch(value) or not 1 <= int(value) <= MAXIMUM_TIMEOUT:
            raise Refusal(f"--timeout takes whole seconds from 1 to {MAXIMUM_TIMEOUT}, written with the digits 0 to 9")
        else:
            timeout = int(value)
        index += 2
    return cwd, timeout


def split_assignments(command: list[str]) -> tuple[dict[str, str], list[str]]:
    environment: dict[str, str] = {}
    index = 0
    while index < len(command) and ASSIGNMENT.match(command[index]):
        name, _, value = command[index].partition("=")
        environment[name] = value
        index += 1
    return environment, command[index:]


def python_module(words: list[str]) -> str | None:
    """The module named by -m in the options of a Python interpreter, or None."""
    index = 0
    while index < len(words):
        word = words[index]
        module = PYTHON_MODULE_FLAG.fullmatch(word)
        if module:
            if module.group(1):
                return module.group(1)
            return words[index + 1] if index + 1 < len(words) else None
        if PYTHON_CODE_FLAG.fullmatch(word) or not word.startswith("-"):
            return None
        index += 2 if word in PYTHON_VALUE_OPTIONS else 1
    return None


def check_command(command: list[str], words: list[str]) -> None:
    if not command:
        raise Refusal("no declared test command after --")
    if not words:
        raise Refusal("the command sets variables but names no program")
    for word in command:
        if word in SHELL_OPERATORS:
            raise Refusal(f"the command needs a shell because of {word!r}; declare a plain command")
    full = Path(words[0]).name.lower()
    full = full[:-4] if full.endswith(".exe") else full
    program = full.split(".")[0]
    rest = words[1:]
    if program in SHELL_PROGRAMS:
        raise Refusal(f"{program} starts a shell; declare the test command itself")
    if program in WRAPPER_PROGRAMS:
        raise Refusal(f"{program} is a wrapper that starts another program; declare the test command itself and "
                      "use NAME=value words or --timeout instead")
    if program in PRIVILEGE_PROGRAMS:
        raise Refusal(f"{program} changes the user or its privileges and is not a test runner")
    if program in FILE_PROGRAMS:
        raise Refusal(f"{program} changes or deletes files and is not a test runner")
    if program in NETWORK_PROGRAMS:
        raise Refusal(f"{program} uses the network or changes the repository and is not a test runner")
    if program in PACKAGE_PROGRAMS:
        raise Refusal(f"{program} installs packages or fetches and runs them, and is not a test runner")
    if PYTHON_PROGRAM.fullmatch(full):
        module = python_module(rest)
        if module is not None and module.split(".")[0] in PYTHON_INSTALL_MODULES:
            raise Refusal(f"python -m {clip(module, 40)} installs or fetches packages; declare the test command itself")
    if program in RUN_WORDS or program in INSTALL_WORDS:
        plain = [word for word in rest if not word.startswith("-")]
        if program in INSTALL_WITHOUT_A_WORD and not plain:
            raise Refusal(f"{program} without a command installs packages; declare its test command")
        for word in plain:
            if word in RUN_WORDS.get(program, ()):
                break
            if word in INSTALL_WORDS.get(program, ()):
                raise Refusal(f"{program} {clip(word, 40)} installs, removes, publishes or fetches packages")


def resolve_folder(text: str) -> Path:
    try:
        root = Path.cwd().resolve()
        given = Path(text)
        if given.is_absolute() or ".." in given.parts:
            raise Refusal("--cwd must name a folder inside the repository root, written without ..")
        folder = (root / given).resolve()
        if folder != root and root not in folder.parents:
            raise Refusal("--cwd resolves outside the repository root")
        if not folder.is_dir():
            raise Refusal("--cwd does not name an existing folder")
    except (OSError, ValueError, RuntimeError) as error:
        raise Refusal(f"--cwd cannot be resolved ({type(error).__name__})") from None
    return folder


def note_stop_signal(number: int, _frame) -> None:
    STOP_REQUESTS.append(number)


def watch_stop_signals() -> None:
    for number in STOP_SIGNALS:
        try:
            signal.signal(number, note_stop_signal)
        except (OSError, ValueError):
            continue


def signal_name(number: int) -> str:
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"


def stop_group(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, PermissionError):
        return


def run_and_summarize(summary: dict, words: list[str], environment: dict[str, str], folder: Path,
                      timeout: int) -> None:
    started = time.monotonic()
    process_environment = dict(os.environ)
    process_environment.update(environment)
    try:
        process = subprocess.Popen(words, cwd=str(folder), env=process_environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=(os.name == "posix"))
    except OSError as error:
        summary.update(result="not_started", seconds=round(time.monotonic() - started, 3),
                       reason=clip(f"the program could not start: {error.strerror or error}"))
        return
    output = BoundedOutput()
    reader = threading.Thread(target=output.drain, args=(process.stdout,), daemon=True)
    reader.start()
    timed_out, stopped_by, exit_status = False, None, None
    deadline = started + timeout
    while True:
        if STOP_REQUESTS:
            stopped_by = STOP_REQUESTS[0]
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            exit_status = process.wait(timeout=min(POLL_SECONDS, remaining))
            break
        except subprocess.TimeoutExpired:
            continue
    if timed_out or stopped_by is not None:
        stop_group(process)
        try:
            exit_status = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            exit_status = None
    wait_for_reader = 1 if stopped_by is not None else 5
    reader.join(timeout=wait_for_reader)
    if reader.is_alive():
        stop_group(process)
        reader.join(timeout=wait_for_reader)
    lines = clean_lines(output.text())
    runner, counts, first_failure, no_tests = parse(lines)
    summary.update(exit_status=exit_status, timed_out=timed_out, seconds=round(time.monotonic() - started, 3),
                   runner=runner, counts=counts, first_failure=first_failure, output_lines=len(lines),
                   output_bytes=output.total)
    failing = bool(counts) and any((counts.get(key) or 0) > 0 for key in ("failed", "errors"))
    if stopped_by is not None:
        summary.update(result="interrupted", reason=f"stopped by {signal_name(stopped_by)} before the command "
                                                    "finished; give the shell tool a longer time limit than --timeout")
    elif timed_out:
        summary.update(result="timeout", reason=f"stopped after {timeout} seconds")
    elif no_tests and not failing:
        summary.update(result="no_tests", reason="the runner reported that no test ran")
    elif exit_status == 0 and not failing:
        if counts is None:
            summary.update(result="unconfirmed", reason="the exit status is 0, but the output holds no test summary "
                                                        "that this script knows, so it cannot confirm that tests ran")
        elif counts.get("passed") == 0 and (counts.get("skipped") or 0) > 0:
            summary.update(result="no_tests", reason="every test that the runner reported was skipped")
        else:
            summary.update(result="passed")
    else:
        summary.update(result="failed")
        if exit_status == 0:
            summary["reason"] = "the exit status is 0, but the runner reported failed tests or errors"
        elif not failing and counts is not None:
            summary["reason"] = "the runner reported no failed test, but the exit status is not 0"
    if summary["result"] != "passed" and first_failure is None:
        summary["tail"] = [clip(line) for line in lines if line.strip()][-TAIL_LINES:]


def main(argv: list[str] | None = None) -> int:
    watch_stop_signals()
    arguments = list(sys.argv[1:] if argv is None else argv)
    command = arguments[arguments.index("--") + 1:] if "--" in arguments else []
    summary = {"record_type": RECORD_TYPE, "command": command, "cwd": ".", "exit_status": None, "timed_out": False,
               "seconds": None, "runner": None, "counts": None, "first_failure": None, "tail": [],
               "output_lines": 0, "output_bytes": 0, "result": "refused", "reason": None}
    try:
        cwd_text, timeout = parse_options(arguments)
        summary["cwd"] = cwd_text
        environment, words = split_assignments(command)
        check_command(command, words)
        folder = resolve_folder(cwd_text)
    except Refusal as refusal:
        summary["reason"] = clip(refusal.reason)
        print(json.dumps(summary))
        return 2
    if STOP_REQUESTS:
        summary.update(result="interrupted", reason=f"stopped by {signal_name(STOP_REQUESTS[0])} before the "
                                                    "command started")
        print(json.dumps(summary))
        return 1
    run_and_summarize(summary, words, environment, folder, timeout)
    print(json.dumps(summary))
    return 0 if summary["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

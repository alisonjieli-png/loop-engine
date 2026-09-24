"""Effects: reads the workspace, runs git and the step's two test commands, writes one evidence file and one diff file under .baltor/.

Run the checks of a ticket fix verification step and save the result.

Usage, from the workspace root:

    python3 -I -B .baltor/ticket-fix-verification-packet/scripts/run_fix_checks.py \
        --input .baltor/step/input.json
    python3 -I -B .baltor/ticket-fix-verification-packet/scripts/run_fix_checks.py \
        --input .baltor/step/input.json --check-commit-message

The first form checks, in this order: HEAD is still the base revision (or,
when the input allows commits since the base, the base is still an ancestor
of HEAD, so no history was rewritten); the reproduction test file is byte for
byte the file the reproduction step saw; every changed path lies under an
allowed prefix; the number of changed files is within the limit; the relevant
tests pass. The full test command runs only when every earlier check passed,
so a broken fix does not spend the night on a long run. Commands run without a
shell and under a time limit. Every run writes a new evidence file, and a new
diff file that holds the changes of the judged paths since the base revision
and nothing else: files the host placed, the step folders under .baltor/ and
byte caches are left out, and untracked files are listed in new_paths instead.
Every evidence file records the sha256 of the step input as it was read. The
output files must be inside .baltor/ and outside .baltor/step/, the packet
folder the step only reads. It prints one JSON object.

The second form reads the proposed commit message named in the step input and
checks its shape: a subject of at most 72 characters that names the ticket, a
blank second line, and a body of two to five nonempty lines of at most 100
characters. It writes nothing.

Exit status: 0 when every check passed; 1 when a check failed (the output says
which); 2 when the input was refused and nothing was run or written.

Python 3.10 or later, standard library only, POSIX systems.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

INPUT_TYPE = "ticket_fix_verification_input/v1"
RECORD_TYPE = "ticket_fix_verification_run/v1"
INPUT_FIELDS = frozenset({"record_type", "ticket_id", "base_revision", "reproduction_test_file",
                          "reproduction_test_sha256", "relevant_test_command", "full_test_command",
                          "timeout_seconds", "allowed_path_prefixes", "max_files_changed", "host_placed_paths",
                          "evidence_dir", "summary_path", "commit_message_path", "commit_message_style",
                          "allow_commits_since_base"})
CHECK_NAMES = ("head_at_base_revision", "base_is_ancestor_of_head", "reproduction_test_unchanged",
               "changed_paths_allowed", "changed_file_count", "relevant_tests_pass", "full_tests_pass")
MAX_INPUT_BYTES = 1024 * 1024
MAX_TEST_FILE_BYTES = 4 * 1024 * 1024
MAX_MESSAGE_BYTES = 16 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_DIFF_BYTES = 4 * 1024 * 1024
DIFF_TIMEOUT_SECONDS = 120
SUBJECT_LIMIT = 72
BODY_LINE_LIMIT = 100
BODY_LINES = (2, 5)
TAIL_BYTES = 64 * 1024
TAIL_LINES = 120
TAIL_CHARACTERS = 16000
MARKER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
REVISION = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
ANSI_SEQUENCE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
CACHE_SEGMENTS = frozenset({"__pycache__", ".pytest_cache"})
STEP_FOLDER = ".baltor"
PACKET_FOLDER = ".baltor/step"


class Refused(Exception):
    """The input cannot be used. Nothing was run and nothing was written."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def read_bounded(path: Path, limit: int, name: str) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as error:
        raise Refused(f"{name} cannot be read: {type(error).__name__}") from None
    if len(data) > limit:
        raise Refused(f"{name} is larger than {limit} bytes")
    return data


def strict_object(data: bytes, name: str) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key {key!r}")
            value[key] = item
        return value

    def no_constant(word):
        raise ValueError(f"nonstandard number {word}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{name} is not UTF-8 text") from None
    if MARKER.search(text):
        raise Refused(f"unrendered_step_input: {name} still holds a marker in double braces")
    try:
        value = json.loads(text, object_pairs_hook=unique, parse_constant=no_constant)
    except ValueError as error:
        raise Refused(f"{name} is not strict JSON: {error}") from None
    if not isinstance(value, dict):
        raise Refused(f"{name} must be one JSON object")
    return value


def confined(root: Path, value, name: str) -> Path:
    """Return the path for a workspace-relative value, refusing every way out of the root."""
    if not isinstance(value, str) or not value or len(value) > 400 or "\x00" in value or "\\" in value:
        raise Refused(f"{name} must be a relative path of at most 400 characters")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith("~") or ".." in pure.parts:
        raise Refused(f"{name} must stay inside the workspace: {value}")
    path = root.joinpath(*pure.parts)
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise Refused(f"{name} cannot be resolved, for example because two symbolic links point at each other: {value}") from None
    if resolved != root and root not in resolved.parents:
        raise Refused(f"{name} leaves the workspace through a symbolic link: {value}")
    return path


def in_folder(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "/")


def output_path(root: Path, step: dict, name: str) -> Path:
    value = step.get(name)
    path = confined(root, value, name)
    if not in_folder(value, STEP_FOLDER) or in_folder(value, PACKET_FOLDER):
        raise Refused(f"{name} must be inside .baltor/ and outside .baltor/step/, which the step only reads")
    return path


def under_any(path: str, prefixes) -> bool:
    """A prefix that ends with / matches everything below it; any other prefix matches one file."""
    return any(path.startswith(prefix) if prefix.endswith("/") else path == prefix for prefix in prefixes)


def text_field(step: dict, name: str, limit: int) -> str:
    value = step.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Refused(f"{name} must be nonempty text of at most {limit} characters")
    return value


def path_list(root: Path, step: dict, name: str, minimum: int, maximum: int) -> list:
    value = step.get(name)
    if not isinstance(value, list) or not minimum <= len(value) <= maximum or len(set(map(str, value))) != len(value):
        raise Refused(f"{name} must be a list of {minimum} to {maximum} distinct relative paths")
    for item in value:
        confined(root, item, name)
    return value


def command_field(step: dict, name: str) -> list:
    command = step.get(name)
    if not isinstance(command, list) or not 1 <= len(command) <= 64 \
            or any(not isinstance(part, str) or len(part) > 1000 or "\x00" in part for part in command) \
            or not command[0].strip():
        raise Refused(f"{name} must be a list of 1 to 64 strings, the program first")
    return command


def load_step(root: Path, input_value: str) -> tuple[dict, str]:
    """Return the checked step input and the sha256 of its bytes as read."""
    data = read_bounded(confined(root, input_value, "--input"), MAX_INPUT_BYTES, "the step input")
    step = strict_object(data, "the step input")
    if step.get("record_type") != INPUT_TYPE:
        raise Refused(f"record_type must be {INPUT_TYPE}")
    if set(step) != INPUT_FIELDS:
        raise Refused(f"the step input fields differ: missing {sorted(INPUT_FIELDS - set(step))}, "
                      f"unexpected {sorted(set(step) - INPUT_FIELDS)}")
    if not IDENTIFIER.match(text_field(step, "ticket_id", 64)):
        raise Refused("ticket_id uses letters, digits, dot, underscore and hyphen, at most 64 characters")
    if not isinstance(step["base_revision"], str) or not REVISION.match(step["base_revision"]):
        raise Refused("base_revision must be a full commit id in lower-case hexadecimal")
    if not isinstance(step["reproduction_test_sha256"], str) or not DIGEST.match(step["reproduction_test_sha256"]):
        raise Refused("reproduction_test_sha256 must be 64 lower-case hexadecimal characters")
    confined(root, step["reproduction_test_file"], "reproduction_test_file")
    command_field(step, "relevant_test_command")
    command_field(step, "full_test_command")
    for name, top in (("timeout_seconds", 7200), ("max_files_changed", 500)):
        if type(step[name]) is not int or not 1 <= step[name] <= top:
            raise Refused(f"{name} must be a whole number from 1 to {top}")
    path_list(root, step, "allowed_path_prefixes", 1, 50)
    path_list(root, step, "host_placed_paths", 0, 50)
    for name in ("evidence_dir", "summary_path", "commit_message_path"):
        output_path(root, step, name)
    text_field(step, "commit_message_style", 1000)
    if type(step["allow_commits_since_base"]) is not bool:
        raise Refused("allow_commits_since_base must be true or false")
    return step, hashlib.sha256(data).hexdigest()


def git_output(root: Path, *arguments: str) -> bytes:
    command = ["git", "-C", str(root), "--no-optional-locks", *arguments]
    try:
        done = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    except FileNotFoundError:
        raise Refused("git is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        raise Refused(f"git {arguments[0]} did not finish within 60 seconds") from None
    if done.returncode != 0:
        lines = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise Refused(f"git {arguments[0]} failed: {(lines[-1] if lines else 'no message')[:300]}")
    if len(done.stdout) > MAX_GIT_OUTPUT_BYTES:
        raise Refused(f"git {arguments[0]} printed more than {MAX_GIT_OUTPUT_BYTES} bytes")
    return done.stdout


def git_exit_code(root: Path, *arguments: str) -> int:
    try:
        return subprocess.run(["git", "-C", str(root), "--no-optional-locks", *arguments], stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=60).returncode
    except FileNotFoundError:
        raise Refused("git is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        raise Refused(f"git {arguments[0]} did not finish within 60 seconds") from None


def require_top_folder(root: Path) -> None:
    top = git_output(root, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip()
    if Path(top).resolve() != root:
        raise Refused("--root must be the top folder of the git worktree")


def untracked_paths(root: Path) -> set:
    tokens = git_output(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\x00")
    paths, index = set(), 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2:3] != b" ":
            raise Refused("git status printed an entry that this script cannot read")
        code = token[:2].decode("ascii", "replace")
        if code == "??":
            paths.add(token[3:].decode("utf-8", "replace"))
        if "R" in code or "C" in code:
            index += 1
    return paths


def tracked_changes(root: Path, base: str) -> set:
    """Tracked paths that differ between the base commit and the working tree."""
    tokens = git_output(root, "diff", "--name-only", "-z", "--no-renames", base, "--").split(b"\x00")
    return {token.decode("utf-8", "replace") for token in tokens if token}


def is_ignored(path: str, host_placed) -> bool:
    parts = path.split("/")
    return (parts[0] == STEP_FOLDER or under_any(path, host_placed) or bool(CACHE_SEGMENTS.intersection(parts))
            or path.endswith(".pyc"))


def stop_group(process: subprocess.Popen) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, PermissionError):
        pass


def run_command(argv: list, cwd: Path, timeout: int) -> dict:
    """Run argv without a shell, keep a digest of all output and only its last part in memory."""
    started_at, clock = utc_now(), time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as error:
        return {"ran": False, "command": argv, "start_error": f"{type(error).__name__}: {error}"[:300],
                "exit_code": None, "timed_out": False, "started_at": started_at, "finished_at": utc_now(),
                "duration_seconds": 0.0, "output_bytes": 0, "output_sha256": None, "output_truncated": False,
                "output_tail": ""}
    digest, tail, total = hashlib.sha256(), bytearray(), [0]

    def drain() -> None:
        while True:
            chunk = process.stdout.read1(65536)
            if not chunk:
                break
            digest.update(chunk)
            total[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > TAIL_BYTES:
                del tail[:len(tail) - TAIL_BYTES]

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_group(process)
        exit_code = process.wait()
    reader.join(timeout=10)
    text = ANSI_SEQUENCE.sub("", bytes(tail).decode("utf-8", "replace"))
    truncated = total[0] > len(tail)
    if truncated:
        text = text.split("\n", 1)[-1]
    text = "\n".join(text.splitlines()[-TAIL_LINES:])[-TAIL_CHARACTERS:]
    return {"ran": True, "command": argv, "start_error": None, "exit_code": exit_code, "timed_out": timed_out,
            "started_at": started_at, "finished_at": utc_now(),
            "duration_seconds": round(time.monotonic() - clock, 3), "output_bytes": total[0],
            "output_sha256": digest.hexdigest(), "output_truncated": truncated, "output_tail": text}


def passed_run(run: dict) -> bool:
    return run["start_error"] is None and not run["timed_out"] and run["exit_code"] == 0


def describe_run(run: dict, timeout: int) -> str:
    if run["start_error"]:
        return f"the command could not start: {run['start_error']}"
    if run["timed_out"]:
        return f"the command did not finish within {timeout} seconds"
    return f"exit code {run['exit_code']}"


def new_file(root: Path, folder: str, stem: str, suffix: str, binary: bool):
    """Create a file that did not exist before, below the evidence folder, and return it open with its path."""
    directory = confined(root, folder, "evidence_dir")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for attempt in range(100):
        target = directory / (f"{stem}-{stamp}{suffix}" if attempt == 0 else f"{stem}-{stamp}-{attempt}{suffix}")
        try:
            stream = target.open("xb") if binary else target.open("x", encoding="utf-8")
        except FileExistsError:
            continue
        return stream, target.relative_to(root).as_posix()
    raise Refused("no new evidence file name was free")


def write_evidence(root: Path, folder: str, stem: str, record: dict) -> str:
    stream, relative = new_file(root, folder, stem, ".json", binary=False)
    with stream:
        stream.write(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
    return relative


def write_diff(root: Path, folder: str, base: str, paths: list) -> dict:
    """Save the changes of the judged tracked paths since base in a new diff file; bounded, never refused."""
    stream, relative = new_file(root, folder, "verification", ".diff", binary=True)
    result = {"diff_path": relative, "diff_bytes": 0, "diff_truncated": False, "diff_error": None}
    with stream:
        if not paths:
            return result
        command = ["git", "--literal-pathspecs", "-C", str(root), "--no-optional-locks", "diff", "--no-color",
                   "--no-ext-diff", "--no-textconv", "--no-renames", base, "--", *paths]
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            result["diff_error"] = f"git diff could not start: {type(error).__name__}"
            return result
        written = [0]

        def drain() -> None:
            while True:
                chunk = process.stdout.read1(65536)
                if not chunk:
                    break
                room = MAX_DIFF_BYTES - written[0]
                if room > 0:
                    stream.write(chunk[:room])
                    written[0] += min(room, len(chunk))
                if len(chunk) > max(room, 0):
                    result["diff_truncated"] = True

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            code = process.wait(timeout=DIFF_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            stop_group(process)
            code = process.wait()
            result["diff_error"] = f"git diff did not finish within {DIFF_TIMEOUT_SECONDS} seconds"
        reader.join(timeout=10)
        result["diff_bytes"] = written[0]
        if code != 0 and result["diff_error"] is None:
            result["diff_error"] = f"git diff exited with code {code}"
    return result


def verify(root: Path, step: dict, input_value: str, input_sha256: str) -> tuple[bool, dict]:
    require_top_folder(root)
    base = step["base_revision"]
    try:
        git_output(root, "rev-parse", "--verify", "--quiet", base + "^{commit}")
    except Refused:
        raise Refused(f"base_revision {base} is not a commit in this repository") from None
    head = git_output(root, "rev-parse", "HEAD").decode("ascii", "replace").strip()
    tracked, untracked = tracked_changes(root, base), untracked_paths(root)
    changed_all = sorted(tracked | untracked)
    host_placed = step["host_placed_paths"]
    changed = [path for path in changed_all if not is_ignored(path, host_placed)]
    ignored = [path for path in changed_all if is_ignored(path, host_placed)]
    new_paths = [path for path in changed if path in untracked and path not in tracked]
    outside = [path for path in changed if not under_any(path, step["allowed_path_prefixes"])]
    test_path = confined(root, step["reproduction_test_file"], "reproduction_test_file")
    found = hashlib.sha256(read_bounded(test_path, MAX_TEST_FILE_BYTES, "reproduction_test_file")).hexdigest() \
        if test_path.is_file() else None
    if step["allow_commits_since_base"]:
        code = git_exit_code(root, "merge-base", "--is-ancestor", base, "HEAD")
        if code not in (0, 1):
            raise Refused("git merge-base could not compare the base revision with HEAD")
        history = {"name": "base_is_ancestor_of_head", "passed": code == 0,
                   "detail": "the base revision is an ancestor of HEAD" if code == 0
                   else f"HEAD {head} does not descend from the base revision; history was rewritten"}
    else:
        history = {"name": "head_at_base_revision", "passed": head == base,
                   "detail": "HEAD is the base revision" if head == base else f"HEAD is {head}; something was committed"}
    checks = [
        history,
        {"name": "reproduction_test_unchanged", "passed": found == step["reproduction_test_sha256"],
         "detail": "the reproduction test has the recorded digest" if found == step["reproduction_test_sha256"]
         else "the reproduction test is missing" if found is None
         else f"the reproduction test changed after it was recorded; its digest is now {found}"},
        {"name": "changed_paths_allowed", "passed": not outside,
         "detail": "every changed path is under an allowed prefix" if not outside
         else f"changed paths outside the allowed prefixes: {outside[:20]}"},
        {"name": "changed_file_count", "passed": len(changed) <= step["max_files_changed"],
         "detail": f"{len(changed)} changed files; the limit is {step['max_files_changed']}"},
    ]
    timeout = step["timeout_seconds"]
    relevant = run_command(step["relevant_test_command"], root, timeout)
    checks.append({"name": "relevant_tests_pass", "passed": passed_run(relevant),
                   "detail": describe_run(relevant, timeout)})
    if all(check["passed"] for check in checks):
        full = run_command(step["full_test_command"], root, timeout)
        checks.append({"name": "full_tests_pass", "passed": passed_run(full), "detail": describe_run(full, timeout)})
    else:
        full = {"ran": False, "command": step["full_test_command"], "skipped": "an earlier check failed"}
        checks.append({"name": "full_tests_pass", "passed": False,
                       "detail": "not run, because an earlier check failed"})
    ready = all(check["passed"] for check in checks)
    diff = write_diff(root, step["evidence_dir"], base, [path for path in changed if path in tracked])
    record = {"record_type": RECORD_TYPE, "ticket_id": step["ticket_id"],
              "verdict": "ready_for_review" if ready else "not_ready", "input_path": input_value,
              "input_sha256": input_sha256, "base_revision": base, "head_revision": head, "checks": checks,
              "failed_checks": [check["name"] for check in checks if not check["passed"]],
              "changed_paths": changed, "new_paths": new_paths, "paths_outside_allowed": outside,
              "ignored_paths": ignored, "reproduction_test_file": step["reproduction_test_file"],
              "reproduction_test_sha256_expected": step["reproduction_test_sha256"],
              "reproduction_test_sha256_found": found, **diff,
              "runs": {"relevant": relevant, "full": full}, "written_at": utc_now()}
    evidence_path = write_evidence(root, step["evidence_dir"], "verification", record)
    summary = {"verdict": record["verdict"], "evidence_path": evidence_path, "input_sha256": input_sha256,
               "failed_checks": record["failed_checks"],
               "checks": [{key: check[key] for key in ("name", "passed", "detail")} for check in checks],
               "changed_paths": changed, "new_paths": new_paths, "diff_path": diff["diff_path"],
               "diff_truncated": diff["diff_truncated"], "diff_error": diff["diff_error"]}
    return ready, summary


def check_message(root: Path, step: dict) -> tuple[bool, dict]:
    path = output_path(root, step, "commit_message_path")
    if not path.is_file():
        return False, {"passed": False, "path": step["commit_message_path"],
                       "problems": ["the commit message file does not exist yet"]}
    try:
        text = read_bounded(path, MAX_MESSAGE_BYTES, "the commit message").decode("utf-8")
    except UnicodeDecodeError:
        return False, {"passed": False, "path": step["commit_message_path"], "problems": ["the message is not UTF-8"]}
    problems = []
    lines = text.rstrip("\n").split("\n")
    subject = lines[0]
    ticket = re.compile(r"(?<![A-Za-z0-9])" + re.escape(step["ticket_id"]) + r"(?![A-Za-z0-9])")
    if not subject.strip():
        problems.append("the first line, the subject, is empty")
    if len(subject) > SUBJECT_LIMIT:
        problems.append(f"the subject has {len(subject)} characters; the limit is {SUBJECT_LIMIT}")
    if not ticket.search(subject):
        problems.append(f"the subject does not name the ticket {step['ticket_id']}")
    if len(lines) > 1 and lines[1].strip():
        problems.append("the second line must be empty, and the body starts on the third line")
    body = [line for line in lines[2:] if line.strip()]
    if not BODY_LINES[0] <= len(body) <= BODY_LINES[1]:
        problems.append(f"the body has {len(body)} nonempty lines; write {BODY_LINES[0]} to {BODY_LINES[1]}")
    long_lines = [number for number, line in enumerate(lines[2:], start=3) if len(line) > BODY_LINE_LIMIT]
    if long_lines:
        problems.append(f"body lines longer than {BODY_LINE_LIMIT} characters: {long_lines[:10]}")
    if MARKER.search(text):
        problems.append("the message still holds a marker in double braces")
    if "\r" in text or "\t" in text:
        problems.append("the message holds a carriage return or a tab")
    return not problems, {"passed": not problems, "path": step["commit_message_path"], "subject": subject,
                          "problems": problems}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the checks of a ticket fix verification step.")
    parser.add_argument("--input", default=".baltor/step/input.json", help="workspace-relative step input")
    parser.add_argument("--root", default=".", help="the workspace root, the top folder of the git worktree")
    parser.add_argument("--check-commit-message", action="store_true",
                        help="check the proposed commit message instead of running the fix checks")
    options = parser.parse_args(argv)
    try:
        try:
            root = Path(options.root).resolve(strict=True)
        except OSError:
            raise Refused("--root does not exist") from None
        if not root.is_dir():
            raise Refused("--root is not a folder")
        step, input_sha256 = load_step(root, options.input)
        if options.check_commit_message:
            passed, summary = check_message(root, step)
        else:
            passed, summary = verify(root, step, options.input, input_sha256)
    except Refused as refusal:
        print(json.dumps({"verdict": "refused", "reason": str(refusal)}, indent=1))
        return 2
    print(json.dumps(summary, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

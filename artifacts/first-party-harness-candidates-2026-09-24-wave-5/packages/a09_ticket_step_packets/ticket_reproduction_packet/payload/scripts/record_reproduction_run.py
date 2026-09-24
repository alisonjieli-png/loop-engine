"""Effects: reads the workspace, runs git status and the step's test command, writes one evidence file under .baltor/.

Record one reproduction run for a ticket step.

Usage, from the workspace root:

    python3 -I -B .baltor/ticket-reproduction-packet/scripts/record_reproduction_run.py \
        --input .baltor/step/input.json

The script reads the step input that the host wrote and lists the changed files
with git. It refuses to run the test while a file outside the declared test
prefixes is changed, or while another file under those prefixes is changed:
this step may change test_file and nothing else. It also checks that test_file
holds test_name as a whole word on a line that is not a comment. Otherwise it
runs the host's test command without a shell, under a time limit, and saves the
exit code and the end of the output in a new evidence file. Every run gets its
own evidence file; nothing is overwritten. Every evidence file records the
sha256 of the step input as it was read, so the host can compare it with the
input it wrote. The evidence folder must be inside .baltor/ and outside
.baltor/step/, the packet folder the step only reads. It prints one JSON object
on standard output.

A non-zero exit of the test command is recorded as nonzero_exit_recorded. The
script cannot tell a failure of the new test from a broken test or a failure
elsewhere; the step judges that from the saved output.

Exit status: 0 when a run with a non-zero exit was recorded; 1 when the run or
a check gave another result (the evidence file says which); 2 when the input
was refused, in which case nothing was run and nothing was written.

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

INPUT_TYPE = "ticket_reproduction_input/v1"
RECORD_TYPE = "ticket_reproduction_run/v1"
INPUT_FIELDS = frozenset({"record_type", "ticket_id", "ticket_path", "test_file", "test_name", "behavior",
                          "test_path_prefixes", "test_command", "timeout_seconds", "host_placed_paths",
                          "evidence_dir"})
MAX_INPUT_BYTES = 1024 * 1024
MAX_TEST_FILE_BYTES = 4 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
TAIL_BYTES = 64 * 1024
TAIL_LINES = 120
TAIL_CHARACTERS = 16000
MARKER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
ANSI_SEQUENCE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
CACHE_SEGMENTS = frozenset({"__pycache__", ".pytest_cache"})
COMMENT_STARTS = ("#", "//", "--", ";", "/*", "*")
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


def under_any(path: str, prefixes) -> bool:
    """A prefix that ends with / matches everything below it; any other prefix matches one file."""
    return any(path.startswith(prefix) if prefix.endswith("/") else path == prefix for prefix in prefixes)


def in_folder(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "/")


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
    text_field(step, "behavior", 2000)
    text_field(step, "test_name", 200)
    confined(root, step["ticket_path"], "ticket_path")
    confined(root, step["test_file"], "test_file")
    prefixes = path_list(root, step, "test_path_prefixes", 1, 20)
    path_list(root, step, "host_placed_paths", 0, 50)
    if not under_any(step["test_file"], prefixes):
        raise Refused("test_file is not under any of test_path_prefixes")
    command = step["test_command"]
    if not isinstance(command, list) or not 1 <= len(command) <= 64 \
            or any(not isinstance(part, str) or len(part) > 1000 or "\x00" in part for part in command) \
            or not command[0].strip():
        raise Refused("test_command must be a list of 1 to 64 strings, the program first")
    timeout = step["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise Refused("timeout_seconds must be a whole number from 1 to 3600")
    evidence = step["evidence_dir"]
    confined(root, evidence, "evidence_dir")
    if not in_folder(evidence, STEP_FOLDER) or in_folder(evidence, PACKET_FOLDER):
        raise Refused("evidence_dir must be inside .baltor/ and outside .baltor/step/, which the step only reads")
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


def require_top_folder(root: Path) -> None:
    top = git_output(root, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip()
    if Path(top).resolve() != root:
        raise Refused("--root must be the top folder of the git worktree")


def changed_entries(root: Path) -> dict:
    """Map each changed or untracked path to its two-letter git status code."""
    tokens = git_output(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\x00")
    entries = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2:3] != b" ":
            raise Refused("git status printed an entry that this script cannot read")
        code = token[:2].decode("ascii", "replace")
        entries[token[3:].decode("utf-8", "replace")] = code
        if "R" in code or "C" in code:
            if index < len(tokens) and tokens[index]:
                entries.setdefault(tokens[index].decode("utf-8", "replace"), code)
            index += 1
    return entries


def is_ignored(path: str, host_placed) -> bool:
    parts = path.split("/")
    return (parts[0] == STEP_FOLDER or under_any(path, host_placed) or bool(CACHE_SEGMENTS.intersection(parts))
            or path.endswith(".pyc"))


def whole_word(name: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")


def name_lines(text: str, name: str) -> list:
    """Line numbers where name stands as a whole word on a line that does not start as a comment."""
    pattern = whole_word(name)
    return [number for number, line in enumerate(text.splitlines(), start=1)
            if not line.lstrip().startswith(COMMENT_STARTS) and pattern.search(line)]


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
        return {"ran": False, "start_error": f"{type(error).__name__}: {error}"[:300], "exit_code": None,
                "timed_out": False, "started_at": started_at, "finished_at": utc_now(), "duration_seconds": 0.0,
                "output_bytes": 0, "output_sha256": None, "output_truncated": False, "output_tail": ""}
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
    return {"ran": True, "start_error": None, "exit_code": exit_code, "timed_out": timed_out,
            "started_at": started_at, "finished_at": utc_now(),
            "duration_seconds": round(time.monotonic() - clock, 3), "output_bytes": total[0],
            "output_sha256": digest.hexdigest(), "output_truncated": truncated, "output_tail": text}


def write_evidence(root: Path, folder: str, stem: str, record: dict) -> str:
    directory = confined(root, folder, "evidence_dir")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for attempt in range(100):
        target = directory / (f"{stem}-{stamp}.json" if attempt == 0 else f"{stem}-{stamp}-{attempt}.json")
        try:
            with target.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
        except FileExistsError:
            continue
        return target.relative_to(root).as_posix()
    raise Refused("no new evidence file name was free")


def record_run(root: Path, step: dict, input_value: str, input_sha256: str) -> tuple[dict, dict]:
    require_top_folder(root)
    entries = changed_entries(root)
    changed = sorted(path for path in entries if not is_ignored(path, step["host_placed_paths"]))
    ignored = sorted(path for path in entries if is_ignored(path, step["host_placed_paths"]))
    product = [path for path in changed if not under_any(path, step["test_path_prefixes"])]
    other_tests = [path for path in changed
                   if under_any(path, step["test_path_prefixes"]) and path != step["test_file"]]
    test_path = confined(root, step["test_file"], "test_file")
    code = entries.get(step["test_file"])
    test_status = "unchanged" if code is None else "new" if code == "??" else "modified"
    problems, digest, lines = [], None, []
    if test_path.is_file():
        data = read_bounded(test_path, MAX_TEST_FILE_BYTES, "test_file")
        digest = hashlib.sha256(data).hexdigest()
        lines = name_lines(data.decode("utf-8", "replace"), step["test_name"])
    if product:
        problems.append(f"files outside test_path_prefixes changed: {product[:20]}. This step changes no product "
                        "code. Change back only what you changed yourself.")
    if other_tests:
        problems.append(f"other files under test_path_prefixes changed: {other_tests[:20]}. This step changes only "
                        "test_file. Change back only what you changed yourself.")
    if digest is None:
        problems.append("test_file does not exist or is not a regular file. Write the new test first.")
    elif not lines:
        problems.append("test_file does not hold test_name as a whole word outside a comment line. Use exactly "
                        "the name from the step input for the new test.")
    elif test_status == "unchanged":
        problems.append("test_file has no change since the last commit. Add the new test to it.")
    run = {"ran": False, "start_error": None, "exit_code": None, "timed_out": False, "started_at": None,
           "finished_at": None, "duration_seconds": None, "output_bytes": 0, "output_sha256": None,
           "output_truncated": False, "output_tail": ""}
    mentions = None
    if product:
        verdict = "product_code_changed"
    elif other_tests:
        verdict = "other_test_files_changed"
    elif digest is None:
        verdict = "test_file_missing"
    elif not lines:
        verdict = "test_name_not_in_file"
    elif test_status == "unchanged":
        verdict = "test_file_unchanged"
    else:
        run = run_command(step["test_command"], root, step["timeout_seconds"])
        mentions = bool(whole_word(step["test_name"]).search(run["output_tail"]))
        if not run["ran"]:
            verdict = "command_not_started"
            problems.append(f"the test command could not start: {run['start_error']}")
        elif run["timed_out"]:
            verdict = "timed_out"
            problems.append(f"the test command did not finish within {step['timeout_seconds']} seconds")
        elif run["exit_code"] == 0:
            verdict = "test_passed"
            problems.append("the test passed, so the reported behavior was not reproduced. Do not force a failure.")
        else:
            verdict = "nonzero_exit_recorded"
    record = {"record_type": RECORD_TYPE, "ticket_id": step["ticket_id"], "verdict": verdict,
              "problems": problems, "input_path": input_value, "input_sha256": input_sha256,
              "test_file": step["test_file"], "test_name": step["test_name"], "test_file_status": test_status,
              "test_file_sha256": digest, "test_name_lines": lines[:20], "changed_paths": changed,
              "product_paths_changed": product, "other_test_paths_changed": other_tests, "ignored_paths": ignored,
              "command": step["test_command"], **run, "output_mentions_test_name": mentions,
              "written_at": utc_now()}
    evidence_path = write_evidence(root, step["evidence_dir"], "reproduction-run", record)
    summary = {"verdict": verdict, "exit_code": run["exit_code"], "evidence_path": evidence_path,
               "input_sha256": input_sha256, "test_file_sha256": digest, "product_paths_changed": product,
               "other_test_paths_changed": other_tests, "output_mentions_test_name": mentions,
               "problems": problems}
    return record, summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record one reproduction run for a ticket step.")
    parser.add_argument("--input", default=".baltor/step/input.json", help="workspace-relative step input")
    parser.add_argument("--root", default=".", help="the workspace root, the top folder of the git worktree")
    options = parser.parse_args(argv)
    try:
        try:
            root = Path(options.root).resolve(strict=True)
        except OSError:
            raise Refused("--root does not exist") from None
        if not root.is_dir():
            raise Refused("--root is not a folder")
        step, input_sha256 = load_step(root, options.input)
        record, summary = record_run(root, step, options.input, input_sha256)
    except Refused as refusal:
        print(json.dumps({"verdict": "refused", "reason": str(refusal)}, indent=1))
        return 2
    print(json.dumps(summary, indent=1))
    return 0 if record["verdict"] == "nonzero_exit_recorded" else 1


if __name__ == "__main__":
    raise SystemExit(main())

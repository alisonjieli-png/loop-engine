"""Create a dated development checkpoint of the entire system.

Captures the repository tree, self-test results, conformance gates,
git state, and a human-readable summary into checkpoints/<date>-<slug>/.

Every command runs with stdout and stderr captured separately and its
return code preserved in the written records. Suite JSON is parsed from
stdout only; a summary that does not parse is recorded as a failed run
with the parse error and a stderr tail, never as "unknown". The slug must
be a bounded identifier, the target directory must not already exist, and
--dry-run validates both and prints what would be written without running
either suite. Exit status is 0 only when the self-test and the conformance
gates both passed, 1 when either failed, and 2 when the checkpoint was
refused before any suite ran.

The conformance command prints a human summary and writes the machine
readable manifest to src/loop_engine/architecture_conformance.json; this
tool keeps the printed text and parses the manifest, refusing a manifest
older than the run that was supposed to write it.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import time
from typing import Callable, NamedTuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINTS_DIR = os.path.join(REPO, "checkpoints")
#: Written by `python -m loop_engine --conformance`; parsed after that run.
CONFORMANCE_MANIFEST = os.path.join(
    REPO, "src", "loop_engine", "architecture_conformance.json")
SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
STATE_RECORD_TYPE = "development_checkpoint_state/v1"
COMMAND_RECORD_TYPE = "development_checkpoint_command/v1"
CHECKPOINT_FILES = ("SNAPSHOT.md", "state.json", "tree.txt", "untracked.txt",
                    "test-report.json", "conformance.json", "git-state.txt")
TREE_NOTE = ("tree.txt lists tracked files only (git ls-files); untracked "
             "paths are listed in untracked.txt and git-state.txt")
#: Last characters of a stream kept in a record when the whole stream is
#: not stored.
TAIL_CHARS = 4000
#: Characters of conformance stdout stored in full before truncation.
CONFORMANCE_STDOUT_KEEP = 20000
#: Seconds of clock tolerance when checking that the conformance manifest
#: was written by this run rather than an earlier one.
MANIFEST_CLOCK_TOLERANCE = 2.0
#: Default wall-clock limit per suite command, in seconds.
DEFAULT_SUITE_TIMEOUT = 3600.0
GIT_COMMANDS = (
    ("branch", ("git", "branch", "--show-current")),
    ("status", ("git", "status", "--short", "--branch")),
    ("head", ("git", "rev-parse", "HEAD")),
    ("tracked", ("git", "ls-files")),
    ("untracked", ("git", "ls-files", "--others", "--exclude-standard")),
)


class CheckpointRefused(ValueError):
    """The checkpoint was refused before any suite ran."""


class CommandResult(NamedTuple):
    """One finished command with its two streams kept apart.

    returncode is None only when the command never returned a code: a
    launch failure or a timeout, described in error.
    """
    command: tuple
    returncode: int | None
    stdout: str
    stderr: str
    error: str = ""


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    text = text or ""
    return text[-limit:]


def run_command(command, *, env: dict | None = None,
                timeout: float | None = None) -> CommandResult:
    """Run one command in the repository with stdout and stderr kept apart.

    The return code is preserved. A launch failure or a timeout becomes a
    result with returncode None and the error text, so the caller records
    it instead of crashing.
    """
    command = list(command)
    try:
        completed = subprocess.run(
            command, cwd=REPO, capture_output=True, text=True,
            env=env or os.environ.copy(), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(tuple(command), None, _text(exc.stdout),
                             _text(exc.stderr),
                             f"timed out after {timeout} seconds")
    except OSError as exc:
        return CommandResult(tuple(command), None, "", "",
                             f"launch failed: {type(exc).__name__}: {exc}")
    return CommandResult(tuple(command), completed.returncode,
                         _text(completed.stdout), _text(completed.stderr))


#: The runner every checkpoint step goes through. Tests replace this
#: attribute, or pass runner= to main, so no real suite runs. A runner is
#: called as runner(command, env=..., timeout=...) and returns a
#: CommandResult, a subprocess.CompletedProcess, or a dict with the keys
#: returncode, stdout, and stderr.
COMMAND_RUNNER: Callable[..., object] = run_command


def _as_result(command, value) -> CommandResult:
    """Accept the runner's return value in any of its documented shapes."""
    if isinstance(value, CommandResult):
        return value
    if isinstance(value, dict):
        return CommandResult(tuple(command), value.get("returncode"),
                             _text(value.get("stdout")),
                             _text(value.get("stderr")),
                             _text(value.get("error")))
    return CommandResult(tuple(command), getattr(value, "returncode", None),
                         _text(getattr(value, "stdout", "")),
                         _text(getattr(value, "stderr", "")),
                         _text(getattr(value, "error", "")))


def _run(command: list[str], *, env: dict | None = None) -> str:
    """Legacy helper kept for callers of the old interface.

    It still returns stdout and stderr joined as one string and drops the
    return code, which is why the checkpoint writer no longer uses it. Use
    run_command for separated streams and the preserved return code.
    """
    result = run_command(command, env=env)
    return result.stdout + result.stderr


def _engine_env() -> dict:
    env = os.environ.copy()
    source = os.path.join(REPO, "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = source + (os.pathsep + existing if existing else "")
    return env


def _engine_command(flags) -> list[str]:
    return [sys.executable, "-m", "loop_engine", *flags]


def _invoke(runner, command, *, env=None, timeout=None) -> CommandResult:
    runner = runner or COMMAND_RUNNER
    return _as_result(command, runner(list(command), env=env, timeout=timeout))


def _command_record(name: str, result: CommandResult) -> dict:
    """The recorded shape of one command: streams apart, code preserved."""
    return {
        "record_type": COMMAND_RECORD_TYPE,
        "name": name,
        "command": list(result.command),
        "returncode": result.returncode,
        "launch_error": result.error,
        "stdout_chars": len(result.stdout),
        "stderr_chars": len(result.stderr),
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _parse_stdout_json(stdout: str) -> tuple[dict | None, str, str]:
    """Parse one JSON object from stdout only.

    Returns (value, error, mode). The whole stream is tried first; when
    that fails, the last JSON object starting at a line beginning is used
    so a stray progress line on stdout does not hide a real summary. The
    error text names why nothing parsed. stderr is never consulted.
    """
    text = (stdout or "").strip()
    if not text:
        return None, "stdout was empty", ""
    try:
        value = json.loads(text)
    except ValueError as exc:
        strict_error = f"{type(exc).__name__}: {exc}"
    else:
        if isinstance(value, dict):
            return value, "", "whole_stdout"
        strict_error = f"stdout JSON is {type(value).__name__}, not an object"
    decoder = json.JSONDecoder()
    found = None
    for match in re.finditer(r"(?m)^\{", text):
        try:
            candidate, _end = decoder.raw_decode(text, match.start())
        except ValueError:
            continue
        if isinstance(candidate, dict):
            found = candidate
    if found is not None:
        return found, "", "last_object_in_stdout"
    return None, strict_error, ""


def _self_test(runner=None, timeout: float | None = None) -> dict:
    """Run the self-test and record it; parse its summary from stdout only.

    A summary that does not parse makes the run a recorded failure with
    the parse error, the return code, and a stderr tail.
    """
    command = _engine_command(["--self-test", "--format", "json"])
    result = _invoke(runner, command, env=_engine_env(), timeout=timeout)
    record = _command_record("self_test", result)
    summary, error, mode = _parse_stdout_json(result.stdout)
    record["summary"] = summary
    record["parse_mode"] = mode
    record["parse_error"] = error
    if summary is None:
        record["passed"] = False
        record["reason"] = "self-test summary did not parse from stdout"
    else:
        all_passed = bool(summary.get("all_passed"))
        record["passed"] = result.returncode == 0 and all_passed
        record["reason"] = ("" if record["passed"] else
                            f"returncode {result.returncode}, "
                            f"all_passed {all_passed}")
    return record


def _read_manifest(path: str, not_before: float) -> tuple[dict | None, str]:
    """Read the conformance manifest written by this run.

    A manifest older than the run's start is refused as stale so a crash
    before writing cannot pass on an earlier run's result.
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError as exc:
        return None, f"manifest unreadable: {type(exc).__name__}: {exc}"
    if mtime < not_before - MANIFEST_CLOCK_TOLERANCE:
        written = datetime.datetime.fromtimestamp(
            mtime, datetime.timezone.utc).isoformat(timespec="seconds")
        return None, (f"manifest at {path} predates this run "
                      f"(written {written}); the conformance command did "
                      "not refresh it")
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, f"manifest unparseable: {type(exc).__name__}: {exc}"
    if not isinstance(value, dict):
        return None, f"manifest JSON is {type(value).__name__}, not an object"
    return value, ""


def _conformance(runner=None, timeout: float | None = None,
                 manifest_path: str | None = None) -> dict:
    """Run the conformance gates and record text, manifest, and code.

    The command's stdout is tried as JSON first, so a future JSON rendering
    is honored; otherwise the human text is kept and the manifest file the
    run writes is parsed.
    """
    manifest_path = manifest_path or CONFORMANCE_MANIFEST
    started = time.time()
    command = _engine_command(["--conformance", "--format", "json"])
    result = _invoke(runner, command, env=_engine_env(), timeout=timeout)
    record = _command_record("conformance", result)
    record["stdout"] = result.stdout[:CONFORMANCE_STDOUT_KEEP]
    record["stdout_truncated"] = len(result.stdout) > CONFORMANCE_STDOUT_KEEP
    manifest, error, mode = _parse_stdout_json(result.stdout)
    source = "stdout" if manifest is not None else ""
    if manifest is None:
        manifest, file_error = _read_manifest(manifest_path, started)
        if manifest is not None:
            source, error = "manifest_file", ""
        else:
            error = f"stdout: {error}; manifest: {file_error}"
    record["manifest"] = manifest
    record["manifest_path"] = manifest_path
    record["manifest_source"] = source
    record["parse_mode"] = mode
    record["parse_error"] = error
    gates_pass = (bool(manifest.get("all_gates_pass"))
                  if manifest is not None else None)
    record["all_gates_pass"] = gates_pass
    record["passed"] = result.returncode == 0 and gates_pass is True
    record["reason"] = ("" if record["passed"] else
                        error or f"returncode {result.returncode}, "
                                 f"all_gates_pass {gates_pass}")
    return record


def _git_records(runner=None, timeout: float | None = None) -> dict:
    """Run every git query with its return code kept."""
    results = {name: _invoke(runner, command, timeout=timeout)
               for name, command in GIT_COMMANDS}
    tracked = results["tracked"].stdout.splitlines()
    untracked = results["untracked"].stdout.splitlines()
    return {
        "branch": results["branch"].stdout.strip(),
        "commit": results["head"].stdout.strip(),
        "status": results["status"].stdout,
        "tracked_count": len(tracked),
        "untracked_paths": untracked,
        "untracked_count": len(untracked),
        "returncodes": {name: result.returncode
                        for name, result in results.items()},
        "commands": [_command_record(f"git_{name}", result)
                     for name, result in results.items()],
        "tree_note": TREE_NOTE,
        "results": results,
    }


def _tree(runner=None) -> str:
    """The tracked-file listing (git ls-files), as before."""
    return _invoke(runner, GIT_COMMANDS[3][1]).stdout


def _render_git_state(git: dict) -> str:
    codes = git["returncodes"]
    lines = [f"branch: {git['branch']}",
             f"commit: {git['commit']}",
             "",
             f"status (git status --short --branch, rc={codes['status']}):",
             git["status"].rstrip("\n"),
             "",
             f"untracked paths (git ls-files --others --exclude-standard, "
             f"rc={codes['untracked']}): {git['untracked_count']}"]
    lines.extend(git["untracked_paths"])
    lines.extend(["", f"note: {git['tree_note']}", ""])
    return "\n".join(lines)


def _git_state(runner=None) -> str:
    """The text for git-state.txt: branch, commit, status, untracked."""
    return _render_git_state(_git_records(runner))


def validate_slug(slug: str) -> str:
    """Accept only a bounded identifier that cannot leave the target."""
    if not isinstance(slug, str) or not SLUG_PATTERN.match(slug):
        raise CheckpointRefused(
            f"slug {slug!r} is not a bounded identifier matching "
            f"{SLUG_PATTERN.pattern}")
    return slug


def validate_date(value: str | None) -> str:
    """Accept only an ISO calendar date; default to today."""
    if not value:
        return datetime.date.today().isoformat()
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CheckpointRefused(f"date {value!r} is not YYYY-MM-DD") from exc


def checkpoint_target(checkpoints_dir: str, date: str, slug: str) -> str:
    """The target directory, confined to the checkpoints directory."""
    root = os.path.realpath(checkpoints_dir)
    target = os.path.join(root, f"{date}-{slug}")
    if os.path.commonpath([root, os.path.realpath(target)]) != root:
        raise CheckpointRefused(f"target {target} escapes {root}")
    return target


def _dry_run_lines(target: str, manifest_path: str) -> list[str]:
    self_test = " ".join(_engine_command(["--self-test", "--format", "json"]))
    conformance = " ".join(
        _engine_command(["--conformance", "--format", "json"]))
    git = "; ".join(" ".join(command) for _name, command in GIT_COMMANDS)
    return [
        f"dry run: would create {target}",
        f"dry run: would run {self_test} (stdout parsed as JSON, stderr "
        "kept apart, return code recorded)",
        f"dry run: would run {conformance} (text kept, manifest parsed "
        f"from {manifest_path}, return code recorded)",
        f"dry run: would run {git}",
        f"dry run: would write {', '.join(CHECKPOINT_FILES)}",
        "dry run: no suite was run and nothing was written",
    ]


def _write_json(path: str, value) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=1)
        handle.write("\n")


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _snapshot(date: str, slug: str, tests: dict, conformance: dict,
              git: dict, exit_status: int) -> str:
    summary = tests.get("summary") or {}
    if tests.get("summary") is None:
        self_test_line = (f"FAILED to parse (return code "
                          f"{tests['returncode']}): {tests['parse_error']}")
    else:
        self_test_line = (f"{summary.get('passed')}/{summary.get('total')} "
                          f"passed, all_passed={bool(summary.get('all_passed'))}, "
                          f"return code {tests['returncode']}")
    if conformance.get("manifest") is None:
        conformance_line = (f"manifest unavailable (return code "
                            f"{conformance['returncode']}): "
                            f"{conformance['parse_error']}")
    else:
        conformance_line = (
            ("ALL GATES PASS" if conformance["all_gates_pass"]
             else "GATES FAILED")
            + f", return code {conformance['returncode']}"
            + f", manifest from {conformance['manifest_source']}")
    passed = "yes" if exit_status == 0 else "no"
    return f"""# Checkpoint {date}-{slug}

## System state

- self-test: {self_test_line}
- conformance: {conformance_line}
- checkpoint passed: {passed} (exit status {exit_status})
- git: branch {git['branch'] or 'unknown'}, commit {git['commit'] or 'unknown'}, {git['untracked_count']} untracked path(s)

## Contents

- state.json: machine-readable state, including every command's return code
- tree.txt: tracked files only (git ls-files); untracked paths are in untracked.txt
- untracked.txt: untracked, not ignored paths (git ls-files --others --exclude-standard)
- test-report.json: self-test command record with the parsed summary, or the parse error
- conformance.json: conformance command record with the parsed manifest, or the parse error
- git-state.txt: branch, commit, status, and untracked paths
"""


def _summary_line(date: str, slug: str, tests: dict, conformance: dict,
                  git: dict, target: str, exit_status: int) -> str:
    summary = tests.get("summary")
    if summary is None:
        self_test = (f"self-test parse_error rc={tests['returncode']} FAILED")
    else:
        self_test = (f"self-test {summary.get('passed')}/{summary.get('total')} "
                     f"rc={tests['returncode']} "
                     f"{'PASSED' if tests['passed'] else 'FAILED'}")
    if conformance.get("manifest") is None:
        gates = "NO MANIFEST"
    else:
        gates = ("ALL GATES PASS" if conformance["all_gates_pass"]
                 else "GATES FAILED")
    return (f"checkpoint {date}-{slug}: {self_test}; conformance "
            f"rc={conformance['returncode']} {gates}; git "
            f"{(git['commit'] or 'unknown')[:12]} ({git['untracked_count']} "
            f"untracked); written to {target}; exit {exit_status}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a dated development checkpoint of the system.")
    parser.add_argument("slug", nargs="?", default="checkpoint",
                        help="bounded identifier for the checkpoint name "
                             "(default: checkpoint)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the slug and target and print what "
                             "would be written without running the suites")
    parser.add_argument("--checkpoints-dir", default=CHECKPOINTS_DIR,
                        help="directory that holds checkpoints "
                             "(default: checkpoints/ in the repository)")
    parser.add_argument("--date", default=None,
                        help="ISO date for the directory name "
                             "(default: today)")
    parser.add_argument("--suite-timeout", type=float,
                        default=DEFAULT_SUITE_TIMEOUT,
                        help="wall seconds allowed per suite command "
                             f"(default: {DEFAULT_SUITE_TIMEOUT:.0f})")
    return parser


def main(argv=None, *, runner=None) -> int:
    """Write one checkpoint; exit 0 only when both suites passed."""
    args = _parser().parse_args(argv)
    try:
        slug = validate_slug(args.slug)
        date = validate_date(args.date)
        target = checkpoint_target(args.checkpoints_dir, date, slug)
    except CheckpointRefused as exc:
        print(f"checkpoint refused: {exc}", file=sys.stderr)
        return 2
    if os.path.lexists(target):
        print(f"checkpoint refused: target already exists: {target}",
              file=sys.stderr)
        return 2
    if args.dry_run:
        for line in _dry_run_lines(target, CONFORMANCE_MANIFEST):
            print(line)
        return 0
    try:
        os.makedirs(target, exist_ok=False)
    except FileExistsError:
        print(f"checkpoint refused: target already exists: {target}",
              file=sys.stderr)
        return 2
    timeout = args.suite_timeout if args.suite_timeout > 0 else None

    tests = _self_test(runner, timeout)
    _write_json(os.path.join(target, "test-report.json"), tests)
    conformance = _conformance(runner, timeout)
    _write_json(os.path.join(target, "conformance.json"), conformance)
    git = _git_records(runner, timeout)
    results = git.pop("results")
    _write_text(os.path.join(target, "tree.txt"), results["tracked"].stdout)
    _write_text(os.path.join(target, "untracked.txt"),
                results["untracked"].stdout)
    _write_text(os.path.join(target, "git-state.txt"),
                _render_git_state(git))

    checkpoint_passed = bool(tests["passed"] and conformance["passed"])
    exit_status = 0 if checkpoint_passed else 1
    summary = tests.get("summary") or {}
    state = {
        "record_type": STATE_RECORD_TYPE,
        "date": date,
        "slug": slug,
        "target": target,
        "created_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "self_test_passed": summary.get("passed"),
        "self_test_total": summary.get("total"),
        "self_test_all_passed": bool(summary.get("all_passed")),
        "self_test_returncode": tests["returncode"],
        "self_test_parse_error": tests["parse_error"],
        "self_test_run_passed": tests["passed"],
        "conformance": {
            "returncode": conformance["returncode"],
            "all_gates_pass": conformance["all_gates_pass"],
            "manifest_source": conformance["manifest_source"],
            "parse_error": conformance["parse_error"],
            "passed": conformance["passed"],
        },
        "conformance_returncode": conformance["returncode"],
        "conformance_all_gates_pass": conformance["all_gates_pass"],
        "conformance_run_passed": conformance["passed"],
        "checkpoint_passed": checkpoint_passed,
        "exit_status": exit_status,
        "git": {key: value for key, value in git.items()
                if key != "commands"},
        "commands": [
            {"name": record["name"], "command": record["command"],
             "returncode": record["returncode"],
             "launch_error": record["launch_error"]}
            for record in (tests, conformance, *git["commands"])],
        "files": list(CHECKPOINT_FILES),
    }
    _write_json(os.path.join(target, "state.json"), state)
    _write_text(os.path.join(target, "SNAPSHOT.md"),
                _snapshot(date, slug, tests, conformance, git, exit_status))
    print(_summary_line(date, slug, tests, conformance, git, target,
                        exit_status))
    return exit_status


if __name__ == "__main__":
    sys.exit(main())

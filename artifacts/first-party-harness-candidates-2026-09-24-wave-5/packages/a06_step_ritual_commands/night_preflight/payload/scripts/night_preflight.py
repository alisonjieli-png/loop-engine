"""Check that an unattended night run can start and write a go or no-go report. Effects: reads files under --root; writes new files under .baltor/state/night-preflight/; starts the declared test command without a shell in its own process group and stops that group when it runs past its timeout; no network of its own, no model call.

Usage from the workspace root, run as two separate tool calls:

    python3 -I -B .baltor/night-preflight/scripts/night_preflight.py probe --root .
    python3 -I -B .baltor/night-preflight/scripts/night_preflight.py check --root . --nonce NONCE

probe writes a new random nonce and prints it together with will_run, the test
command that check will start. check passes the tool call test only when the nonce
printed by probe comes back unchanged, within the allowed age, and only once: a
model that writes tool calls as text never sees the nonce, and an invented value
does not match. check then reads .baltor/night/settings.json, checks the budget,
the content of every guard file, the queue and its status file, and runs the
declared test command as an argument list with a timeout, keeping only the last
64 KiB of its output. Every run writes a new report that names the command, the
folder and the timeout it used. Exit status: 0 go, 1 no-go, 2 refused input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

STATE = Path(".baltor") / "state" / "night-preflight"
SETTINGS = Path(".baltor") / "night" / "settings.json"
QUEUE = ".baltor/night/queue.json"
STATUS = ".baltor/night/queue-status.json"
MAX_BYTES = 4 * 1024 * 1024
OUTPUT_TAIL_BYTES = 64 * 1024
NONCE = re.compile(r"[0-9a-f]{12}\Z")
WORK_STATES = ("queued", "in_progress")
SETTING_KEYS = {"record_type", "time_minutes", "model_calls", "reserve_percent", "hold_high_risk", "order",
                "one_ticket_per_harness", "test_command", "test_timeout_seconds", "expected_test_exit",
                "guard_files"}
ALLOW_EVERY_SHELL_COMMAND = {"Bash", "Bash(*)", "Bash(:*)", "Bash(**)"}
RECOGNIZED = (".claude/settings.json, .claude/settings.local.json, .cursor/hooks.json, "
              ".github/hooks/<name>.json, opencode.json and .gemini/settings.json")


class Refused(Exception):
    """Input that this script will not process."""


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=1, ensure_ascii=False))
    return code


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def strict_json(text: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def under(root: Path, text: str) -> Path | None:
    """Return root/text when text is a relative path that stays under root, else None."""
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        return None
    full = root / candidate
    return full if full.resolve().is_relative_to(root) else None


def read_json(path: Path) -> tuple[object, str, str | None]:
    """Return (value, problem, sha256); problem is empty when the file held strict JSON."""
    if path.is_symlink() or not path.is_file():
        return None, "missing or not a regular file", None
    if path.stat().st_size > MAX_BYTES:
        return None, f"larger than {MAX_BYTES} bytes", None
    data = path.read_bytes()
    try:
        return strict_json(data.decode("utf-8")), "", hashlib.sha256(data).hexdigest()
    except (UnicodeDecodeError, ValueError) as error:
        return None, f"not strict UTF-8 JSON: {error}", None


def state_folder(root: Path) -> Path:
    folder = under(root, STATE.as_posix())
    if folder is None:
        raise Refused("the state folder leaves the workspace through a link")
    folder.mkdir(parents=True, exist_ok=True)
    if not folder.resolve().is_relative_to(root):
        raise Refused("the state folder leaves the workspace through a link")
    return folder


def whole_number(value, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def load_settings(root: Path) -> tuple[dict | None, str]:
    path = under(root, SETTINGS.as_posix())
    if path is None:
        raise Refused("the settings path leaves the workspace through a link")
    settings, problem, _digest = read_json(path)
    if settings is not None and not isinstance(settings, dict):
        return None, "is not one JSON object"
    if isinstance(settings, dict) and settings.get("record_type") != "night_settings/v1":
        return None, "has no record_type night_settings/v1"
    return settings, problem


def planned_test(root: Path, settings: dict | None, problem: str) -> tuple[dict | None, str]:
    """The test command check will run, or (None, why it cannot run)."""
    if settings is None:
        return None, f"settings file {problem}"
    argv = settings.get("test_command")
    if isinstance(argv, str):
        return None, "test_command is one string; write it as a list of arguments, it is never run through a shell"
    if not isinstance(argv, list) or not argv or len(argv) > 64 \
            or any(not isinstance(part, str) or not part or len(part) > 4096 for part in argv):
        return None, "test_command must be a list of 1 to 64 nonempty strings"
    timeout = settings.get("test_timeout_seconds", 900)
    expected = settings.get("expected_test_exit", 0)
    if not whole_number(timeout, 1, 7200) or not whole_number(expected, 0, 255):
        return None, "test_timeout_seconds must be 1 to 7200 and expected_test_exit 0 to 255"
    program = argv[0]
    if "/" in program:
        located = Path(program) if Path(program).is_absolute() else under(root, program)
        found = str(located) if located is not None and located.is_file() else None
    else:
        found = shutil.which(program)
    plan = {"argv": argv, "cwd": ".", "timeout_seconds": timeout, "expected_exit": expected, "program": found}
    if found is None:
        return plan, f"the program {program} was not found"
    return plan, ""


def command_probe(root: Path) -> int:
    folder = state_folder(root)
    nonce = uuid.uuid4().hex[:12]
    record = {"record_type": "night_preflight_probe/v1", "nonce": nonce,
              "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "created_epoch": int(time.time())}
    with open(folder / f"probe-{nonce}.json", "x", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    settings, problem = load_settings(root)
    plan, why = planned_test(root, settings, problem)
    return emit({"record_type": "night_preflight_probe/v1", "nonce": nonce, "will_run": plan,
                 "will_run_problem": why or None,
                 "next": "Show will_run to the person, then run check with this exact nonce as a separate tool call."}, 0)


def check_tool_calls(folder: Path, nonce: str | None, max_age_minutes: int) -> dict:
    name = "structured_tool_calls"
    if not nonce:
        return {"name": name, "passed": False, "detail": "no nonce was given; run probe first and pass its nonce"}
    if not NONCE.fullmatch(nonce):
        return {"name": name, "passed": False, "detail": "the nonce is not the 12 lower-case hex characters probe prints"}
    probe, problem, _digest = read_json(folder / f"probe-{nonce}.json")
    if problem or not isinstance(probe, dict) or probe.get("nonce") != nonce:
        return {"name": name, "passed": False,
                "detail": "no probe wrote this nonce; the value was not read from a real probe result"}
    age = time.time() - probe.get("created_epoch", 0) if isinstance(probe.get("created_epoch"), int) else None
    if age is None or age < 0 or age > max_age_minutes * 60:
        return {"name": name, "passed": False,
                "detail": f"the probe is older than {max_age_minutes} minutes or has no valid time; run probe again"}
    try:
        with open(folder / f"probe-{nonce}.used", "x", encoding="utf-8") as stream:
            stream.write(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    except FileExistsError:
        return {"name": name, "passed": False, "detail": "this nonce was used before; run probe again"}
    return {"name": name, "passed": True,
            "detail": f"the nonce from probe came back unchanged {int(age)} seconds after it was written"}


def check_budgets(settings: dict | None, problem: str) -> dict:
    name = "budgets"
    if settings is None:
        return {"name": name, "passed": False, "detail": f"settings file {problem}"}
    issues = []
    unknown = sorted(set(settings) - SETTING_KEYS)
    if unknown:
        issues.append(f"unknown settings {unknown}")
    if not whole_number(settings.get("time_minutes"), 1, 1440):
        issues.append("time_minutes must be a whole number from 1 to 1440")
    if not whole_number(settings.get("model_calls"), 1, 100000):
        issues.append("model_calls must be a whole number from 1 to 100000")
    if "reserve_percent" in settings and not whole_number(settings["reserve_percent"], 0, 90):
        issues.append("reserve_percent must be a whole number from 0 to 90")
    if issues:
        return {"name": name, "passed": False, "detail": "; ".join(issues)}
    return {"name": name, "passed": True,
            "detail": f"{settings['time_minutes']} minutes and {settings['model_calls']} model calls declared"}


def guard_kind(text: str) -> str:
    parts = PurePosixPath(text).parts
    if text in (".claude/settings.json", ".claude/settings.local.json"):
        return "claude_code_settings"
    if text == ".cursor/hooks.json":
        return "cursor_hooks"
    if len(parts) == 3 and parts[:2] == (".github", "hooks") and text.endswith(".json"):
        return "copilot_hooks"
    if text == "opencode.json":
        return "opencode_config"
    if text == ".gemini/settings.json":
        return "gemini_settings"
    return "unrecognized"


def hook_commands(hooks, keys: tuple) -> int:
    """Count hook entries that name a command, in the event to list shape the hook files use."""
    def names_command(entry) -> bool:
        return isinstance(entry, dict) and any(isinstance(entry.get(key), str) and entry[key].strip() for key in keys)

    count = 0
    for entries in (hooks.values() if isinstance(hooks, dict) else []):
        for entry in (entries if isinstance(entries, list) else []):
            count += names_command(entry)
            nested = entry.get("hooks") if isinstance(entry, dict) else None
            count += sum(names_command(inner) for inner in (nested if isinstance(nested, list) else []))
    return count


def holds_value(value, wanted: str) -> bool:
    if isinstance(value, dict):
        return any(holds_value(item, wanted) for item in value.values())
    if isinstance(value, list):
        return any(holds_value(item, wanted) for item in value)
    return value == wanted


def inspect_guard(kind: str, value: dict) -> tuple[list[str], list[str]]:
    """Return (problems, guards) for one parsed guard file of a recognized kind."""
    problems, guards = [], []
    if kind == "claude_code_settings":
        permissions = value.get("permissions") if isinstance(value.get("permissions"), dict) else {}
        mode = permissions.get("defaultMode")
        if mode == "bypassPermissions":
            problems.append("has permissions.defaultMode bypassPermissions, which turns permission checks off")
        allow = permissions.get("allow") if isinstance(permissions.get("allow"), list) else []
        broad = [rule for rule in allow if isinstance(rule, str) and rule.replace(" ", "") in ALLOW_EVERY_SHELL_COMMAND]
        if broad:
            problems.append(f"allows every shell command through the permissions.allow rule {broad[0]}")
        deny = permissions.get("deny") if isinstance(permissions.get("deny"), list) else []
        if any(isinstance(rule, str) and rule.strip() for rule in deny):
            guards.append("deny rules")
        if mode in ("dontAsk", "plan"):
            guards.append(f"default mode {mode}")
        if hook_commands(value.get("hooks"), ("command",)):
            guards.append("hook commands")
        if isinstance(value.get("sandbox"), dict) and value["sandbox"].get("enabled") is True:
            guards.append("sandbox")
    elif kind in ("cursor_hooks", "copilot_hooks"):
        keys = ("command",) if kind == "cursor_hooks" else ("bash", "powershell", "command")
        if hook_commands(value.get("hooks"), keys):
            guards.append("hook commands")
    elif kind == "opencode_config":
        permission = value.get("permission")
        if permission == "allow" or (isinstance(permission, dict) and permission.get("bash") == "allow"):
            problems.append("allows every shell command through its permission setting")
        if holds_value(permission, "deny"):
            guards.append("deny rules")
    elif kind == "gemini_settings":
        tools = value.get("tools") if isinstance(value.get("tools"), dict) else {}
        if any(isinstance(item, list) and item for item in (tools.get("core"), tools.get("exclude"),
                                                             value.get("coreTools"), value.get("excludeTools"))):
            guards.append("tool lists")
        if hook_commands(value.get("hooks"), ("command",)):
            guards.append("hook commands")
    return problems, guards


def check_guards(root: Path, settings: dict | None, problem: str) -> tuple[dict, list]:
    name = "guards"
    if settings is None:
        return {"name": name, "passed": False, "detail": f"settings file {problem}"}, []
    listed = settings.get("guard_files")
    if not isinstance(listed, list) or not listed or len(listed) > 20 or any(not isinstance(item, str) for item in listed):
        return {"name": name, "passed": False,
                "detail": "guard_files must list 1 to 20 guard file paths, such as a hook or permission settings file"}, []
    issues, files, guarded = [], [], []
    for text in listed:
        entry = {"path": text, "kind": guard_kind(text), "guards": [], "problems": []}
        files.append(entry)
        path = under(root, text)
        if path is None:
            entry["problems"].append("is outside the workspace")
        elif path.is_symlink() or not path.is_file():
            entry["problems"].append("is missing")
        elif path.stat().st_size == 0:
            entry["problems"].append("is empty")
        elif text.endswith(".json"):
            value, parse_problem, _digest = read_json(path)
            if parse_problem or not isinstance(value, dict) or not value:
                entry["problems"].append("is not one nonempty strict JSON object")
            elif entry["kind"] != "unrecognized":
                entry["problems"], entry["guards"] = inspect_guard(entry["kind"], value)
                if not entry["guards"]:
                    entry["problems"].append("holds no guard rule, such as a deny rule or a hook command")
        if entry["kind"] == "unrecognized" and not entry["problems"]:
            entry["note"] = "present; content not checked"
        issues += [f"{text} {item}" for item in entry["problems"]]
        if entry["guards"] and not entry["problems"]:
            guarded.append(f"{text} ({', '.join(entry['guards'])})")
    if not guarded and not issues:
        issues.append(f"no listed file is a recognized guard file that holds a guard rule; recognized: {RECOGNIZED}")
    if issues:
        return {"name": name, "passed": False, "detail": "; ".join(issues)}, files
    return {"name": name, "passed": True, "detail": "guard rules found in " + "; ".join(guarded)}, files


def check_queue(root: Path) -> dict:
    name = "queue"
    path = under(root, QUEUE)
    if path is None:
        return {"name": name, "passed": False, "detail": "the queue path leaves the workspace through a link"}
    queue, problem, digest = read_json(path)
    if problem:
        return {"name": name, "passed": False, "detail": f"{QUEUE} {problem}"}
    items = queue.get("items") if isinstance(queue, dict) else None
    if not isinstance(queue, dict) or queue.get("record_type") != "night_queue/v1" or not isinstance(items, list):
        return {"name": name, "passed": False,
                "detail": f"{QUEUE} is not a night_queue/v1 queue with an items list; plan it with plan-night-queue"}
    statuses = {}
    status_path = under(root, STATUS)
    if status_path is not None and (status_path.exists() or status_path.is_symlink()):
        status, problem, _ = read_json(status_path)
        if problem or not isinstance(status, dict) or status.get("record_type") != "night_queue_status/v1" \
                or not isinstance(status.get("tickets"), dict):
            return {"name": name, "passed": False, "detail": f"{STATUS} is not a night_queue_status/v1 file"}
        if status.get("queue_sha256") != digest:
            return {"name": name, "passed": False,
                    "detail": f"{STATUS} belongs to another queue; move it aside with that queue"}
        statuses = {ticket: entry.get("status") for ticket, entry in status["tickets"].items() if isinstance(entry, dict)}
    work = [item for item in items if isinstance(item, dict) and statuses.get(item.get("id"), "queued") in WORK_STATES]
    if not work:
        return {"name": name, "passed": False, "detail": f"{QUEUE} holds no queued or in_progress ticket"}
    return {"name": name, "passed": True, "detail": f"{len(work)} ticket(s) queued or in progress in {QUEUE}"}


def stop_group(process: subprocess.Popen) -> None:
    """Stop the test command and every process it started in its group."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError, PermissionError):
        process.kill()


def run_bounded(argv: list, root: Path, timeout: int) -> tuple[int, bool, bytes, int]:
    """Run argv without a shell; keep only the last OUTPUT_TAIL_BYTES of its output in memory."""
    process = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    tail, total = bytearray(), [0]

    def drain() -> None:
        for chunk in iter(lambda: process.stdout.read(65536), b""):
            total[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > OUTPUT_TAIL_BYTES:
                del tail[:len(tail) - OUTPUT_TAIL_BYTES]

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_group(process)
        process.wait()
    reader.join(timeout=5)
    return process.returncode, timed_out, bytes(tail), total[0]


def check_test_command(root: Path, folder: Path, plan: dict | None, why: str, run_stamp: str) -> tuple[dict, str | None]:
    name = "test_command"
    if plan is None or why:
        return {"name": name, "passed": False, "detail": why}, None
    started = time.monotonic()
    try:
        code, timed_out, tail, total = run_bounded(plan["argv"], root, plan["timeout_seconds"])
    except OSError as error:
        return {"name": name, "passed": False, "detail": f"the test command could not start: {error.strerror}"}, None
    seconds = round(time.monotonic() - started, 1)
    tail_path = folder / f"test-output-{run_stamp}.txt"
    header = (f"argv {json.dumps(plan['argv'])}; exit {code}; {total} bytes of output; "
              f"only the last {OUTPUT_TAIL_BYTES} bytes are kept below\n").encode("utf-8")
    with open(tail_path, "xb") as stream:
        stream.write(header + tail)
    relative = tail_path.relative_to(root).as_posix()
    if timed_out:
        return {"name": name, "passed": False,
                "detail": f"the test command did not finish in {plan['timeout_seconds']} seconds and was stopped "
                          f"with the processes it started; see {relative}"}, relative
    if code != plan["expected_exit"]:
        return {"name": name, "passed": False,
                "detail": f"exit {code} after {seconds} seconds; expected {plan['expected_exit']}; see {relative}"}, relative
    return {"name": name, "passed": True, "detail": f"exit {code} after {seconds} seconds"}, relative


def command_check(root: Path, options) -> int:
    folder = state_folder(root)
    run_stamp = stamp()
    settings, problem = load_settings(root)
    plan, why = planned_test(root, settings, problem)
    guards, guard_files = check_guards(root, settings, problem)
    checks = [check_tool_calls(folder, options.nonce, options.max_probe_age_minutes),
              check_budgets(settings, problem), guards, check_queue(root)]
    test_check, output_path = check_test_command(root, folder, plan, why, run_stamp)
    checks.append(test_check)
    failed = [item["name"] for item in checks if not item["passed"]]
    report_path = folder / f"report-{run_stamp}.json"
    report = {"record_type": "night_preflight_report/v1",
              "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "decision": "no-go" if failed else "go", "failed": failed, "checks": checks,
              "test_command": plan, "guard_files": guard_files, "test_output": output_path,
              "report_path": report_path.relative_to(root).as_posix()}
    with open(report_path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return emit(report, 1 if failed else 0)


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=".", help="workspace root; every path stays under it")
    parser = argparse.ArgumentParser(description="Check that an unattended night run can start.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("probe", parents=[shared], help="write a new nonce and show the test command")
    check = commands.add_parser("check", parents=[shared], help="run every check and write a report")
    check.add_argument("--nonce", help="the nonce printed by probe")
    check.add_argument("--max-probe-age-minutes", type=int, default=15, choices=range(1, 121), metavar="1-120")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        return command_probe(root) if options.command == "probe" else command_check(root, options)
    except (Refused, OSError) as error:
        return emit({"record_type": "night_preflight_refused/v1", "refused": True, "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())

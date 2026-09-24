"""Ticket ledger for unattended runs. Effects: reads evidence files and reads, locks and appends to one ledger file under --root; no network, no model call.

The ledger is .baltor/state/unattended-run-rules/ledger.jsonl below the
workspace root. Each line is one JSON object: a start line or a finish line
for one ticket. The ledger allows one open ticket at a time and one finish
line for every ticket that started.

    start  --ticket KEY
        Open KEY. Refused while any ticket is open or when KEY already finished.
    finish --ticket KEY --status done|blocked|skipped --summary TEXT
           [--needs TEXT] [--evidence PATH ...]
        Close the open ticket. done needs at least one evidence file. blocked
        needs --needs: what is needed, from whom. Every evidence file is a
        nonempty file inside .baltor/state/unattended-run-rules/, written after
        the ticket started, and not named by an earlier finish line.
    status
        Print the open ticket, how many tickets finished with each status and
        the keys of the tickets that finished last.

Run it from the workspace root, or name the root with --root. Every answer is
one JSON object on standard output. A refusal carries a "next" field that says
what to do instead, and "stop_run": true when the ledger itself cannot be
trusted. Exit 0: the command did its work. Exit 1: a run rule refused the
command, or another ledger command held the lock too long. Exit 2: the input
was refused (bad arguments, an unsafe path, or a ledger that cannot be read).

start and finish hold an exclusive lock on ledger.lock beside the ledger while
they read and append, and status holds a shared lock while it reads, so two
harnesses that call the ledger at the same moment cannot both open a ticket.
Where the fcntl module is missing (Windows), the ledger assumes one writer.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl; one writer is assumed there
    fcntl = None

STATE_FOLDERS = (".baltor", "state", "unattended-run-rules")
LEDGER_NAME = "ledger.jsonl"
LOCK_NAME = "ledger.lock"
STATE_TEXT = "/".join(STATE_FOLDERS)
LEDGER_TEXT = STATE_TEXT + "/" + LEDGER_NAME
LINE_TYPE = "unattended_ticket_ledger_line/v1"
TICKET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
STATUSES = ("done", "blocked", "skipped")
MAX_LEDGER_BYTES = 1024 * 1024
MAX_TEXT_CHARACTERS = 500
MAX_EVIDENCE = 20
MAX_LISTED = 100
#: File systems with coarse timestamps can date a file up to two seconds early.
CLOCK_TOLERANCE_SECONDS = 2.0
DEFAULT_LOCK_SECONDS = 10.0
MAX_LOCK_SECONDS = 60.0
NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)

EXAMPLE_EVIDENCE = STATE_TEXT + "/KEY-checks.txt"
NEXT = {
    "another_ticket_open": "Finish the open ticket first. If its work cannot be completed now, finish it with "
                           "--status blocked and say in --needs what a person must do.",
    "ticket_already_open": "An earlier attempt left this ticket open. Check what it changed. If you cannot tell "
                           "that the work is complete and correct, finish it with --status blocked and "
                           "--needs \"a person to check the partial work\".",
    "ticket_already_finished": "This ticket already has a finish line. Do not work on it again. Take the next "
                               "ticket on the host's list, or stop the run when none is left.",
    "no_open_ticket": "No ticket is open. Run start --ticket KEY before you work on a ticket.",
    "ticket_not_open": "Finish the ticket that is open, not another one. Run status to see it.",
    "done_without_evidence": "Save the output of the checks to a new file named after the ticket, for example "
                             + EXAMPLE_EVIDENCE + ", and pass it with --evidence. Without evidence, finish with "
                             "--status blocked.",
    "evidence_missing": "Pass a file that exists and is not empty, for example " + EXAMPLE_EVIDENCE + ".",
    "evidence_outside_state_folder": "Evidence files live in " + STATE_TEXT + "/. Save the output of the checks "
                                     "there in a new file named after the ticket, for example " + EXAMPLE_EVIDENCE
                                     + ", and pass that path.",
    "evidence_is_ledger": "The ledger and its lock file are not evidence. Save the output of the checks to a new "
                          "file, for example " + EXAMPLE_EVIDENCE + ".",
    "evidence_older_than_ticket": "This file was not written during this ticket. Run the checks again, save "
                                  "their output to a new file, for example " + EXAMPLE_EVIDENCE
                                  + ", and pass that file.",
    "evidence_reused": "An earlier ticket already used this file. Save this ticket's output to a new file named "
                       "after the ticket, for example " + EXAMPLE_EVIDENCE + ".",
    "blocked_without_needs": "Add --needs with what is needed and from whom.",
    "ledger_busy": "Another ledger command is running. Wait a few seconds and run the same command again.",
}
NEXT_FOR_INPUT = "Fix the command and run it again."
#: Codes that mean the ledger itself cannot be trusted; the whole run stops.
STOP_RUN = {"ledger_unreadable", "ledger_inconsistent", "ledger_too_large", "unsafe_state_path", "root_missing",
            "file_system_error"}
NEXT_FOR_STOP = "Stop the whole run and report this answer. Do not edit the ledger by hand."


class Refusal(Exception):
    """A refused command: the exit status, a stable code and a short detail."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status, self.code, self.detail = status, code, detail


def rule(code: str, detail: str) -> Refusal:
    return Refusal(1, code, detail)


def bad_input(code: str, detail: str) -> Refusal:
    return Refusal(2, code, detail)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # an argument error is refused input, answered as JSON
        raise bad_input("arguments_invalid", message)


def seconds(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("a number of seconds") from None
    if not 0 <= number <= MAX_LOCK_SECONDS:
        raise argparse.ArgumentTypeError(f"0 to {MAX_LOCK_SECONDS:g} seconds")
    return number


def parse(argv) -> argparse.Namespace:
    parser = Parser(prog="ticket_ledger.py", description="Ticket ledger for unattended runs.")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="open one ticket")
    start.add_argument("--ticket", required=True)
    finish = commands.add_parser("finish", help="close the open ticket")
    finish.add_argument("--ticket", required=True)
    finish.add_argument("--status", required=True, choices=STATUSES)
    finish.add_argument("--summary", required=True)
    finish.add_argument("--needs")
    finish.add_argument("--evidence", action="append", default=[])
    status = commands.add_parser("status", help="print the open ticket and the counts")
    for command in (start, finish, status):
        command.add_argument("--root", default=".")
        command.add_argument("--lock-timeout", type=seconds, default=DEFAULT_LOCK_SECONDS,
                             help="how long to wait for another ledger command, in seconds")
    return parser.parse_args(argv)


def workspace(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise bad_input("root_missing", "the --root folder does not exist") from None
    if not root.is_dir():
        raise bad_input("root_missing", "the --root path is not a folder")
    return root


def ticket_key(value: str) -> str:
    if not TICKET.fullmatch(value or ""):
        raise bad_input("ticket_invalid", "a ticket key is 1 to 64 letters, digits, dots, dashes or underscores, "
                                          "starting with a letter or digit")
    return value


def one_line(value, name: str) -> str:
    text = (value or "").strip()
    if not text or len(text) > MAX_TEXT_CHARACTERS or any(ord(character) < 32 or ord(character) == 127
                                                           for character in text):
        raise bad_input("text_invalid", f"{name} is one line of 1 to {MAX_TEXT_CHARACTERS} characters")
    return text


def state_folder(root: Path, create: bool) -> Path:
    """Return the state folder; refuse a symbolic link or a file where a folder belongs.

    Two commands may create the folders at the same moment, so a folder that
    appears between the check and the creation is accepted, then checked again.
    """
    current = root
    for part in STATE_FOLDERS:
        current = current / part
        shown = current.relative_to(root).as_posix()
        if current.is_symlink():
            raise bad_input("unsafe_state_path", f"{shown} is a symbolic link")
        if create and not current.exists():
            try:
                current.mkdir(exist_ok=True)
            except OSError:
                raise bad_input("unsafe_state_path", f"{shown} cannot be created as a folder") from None
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise bad_input("unsafe_state_path", f"{shown} is not a folder")
    return current


def ledger_path(folder: Path) -> Path:
    path = folder / LEDGER_NAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise bad_input("unsafe_state_path", f"{LEDGER_TEXT} is not a regular file")
    return path


class LedgerLock:
    """An exclusive or shared lock on ledger.lock, released when the process ends in any way."""

    def __init__(self, folder: Path, exclusive: bool, timeout: float) -> None:
        self.path, self.exclusive, self.timeout, self.descriptor = folder / LOCK_NAME, exclusive, timeout, None

    def __enter__(self) -> "LedgerLock":
        if fcntl is None:
            return self
        flags = (os.O_RDWR | os.O_CREAT if self.exclusive else os.O_RDONLY) | NO_FOLLOW
        try:
            self.descriptor = os.open(self.path, flags, 0o644)
        except FileNotFoundError:
            return self  # a reader before any writer: nothing is written yet, so nothing to wait for
        except OSError:
            raise bad_input("unsafe_state_path", f"{STATE_TEXT}/{LOCK_NAME} cannot be opened as a regular file") from None
        mode = (fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self.descriptor, mode)
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self.release()
                    raise rule("ledger_busy", f"another ledger command held the lock for {self.timeout:g} seconds")
                time.sleep(0.05)

    def release(self) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)  # closing the descriptor releases the lock
            self.descriptor = None

    def __exit__(self, *_exception) -> None:
        self.release()


def strict_object(line: str) -> dict:
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    value = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("a ledger line is one JSON object")
    return value


def read_ledger(path: Path) -> list:
    if not path.exists():
        return []
    if path.stat().st_size > MAX_LEDGER_BYTES:
        raise bad_input("ledger_too_large", f"the ledger is larger than {MAX_LEDGER_BYTES} bytes")
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise bad_input("ledger_unreadable", "the ledger is not UTF-8 text") from None
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = strict_object(line)
        except ValueError as error:
            raise bad_input("ledger_unreadable", f"line {number}: {error}") from None
        if (record.get("record_type") != LINE_TYPE or record.get("event") not in ("start", "finish")
                or not isinstance(record.get("ticket"), str) or not TICKET.fullmatch(record["ticket"])
                or not isinstance(record.get("at"), str)
                or (record["event"] == "finish" and (record.get("status") not in STATUSES
                                                     or not isinstance(record.get("evidence"), list)))):
            raise bad_input("ledger_unreadable", f"line {number} is not a ledger line")
        lines.append(record)
    return lines


def replay(lines: list):
    """Return the open start line, the status of every finished ticket and every evidence path used so far."""
    open_line, finished, used = None, {}, set()
    for number, record in enumerate(lines, 1):
        ticket = record["ticket"]
        if record["event"] == "start":
            if open_line is not None or ticket in finished:
                raise bad_input("ledger_inconsistent", f"ledger line {number} starts {ticket} out of order")
            open_line = record
        else:
            if open_line is None or ticket != open_line["ticket"]:
                raise bad_input("ledger_inconsistent", f"ledger line {number} finishes {ticket}, which is not open")
            finished[ticket] = record["status"]
            used.update(path for path in record["evidence"] if isinstance(path, str))
            open_line = None
    return open_line, finished, used


def started_at(line: dict) -> float:
    try:
        moment = _dt.datetime.fromisoformat(line["at"])
    except ValueError:
        raise bad_input("ledger_unreadable", f"the start line of {line['ticket']} has no readable time") from None
    if moment.tzinfo is None:
        raise bad_input("ledger_unreadable", f"the start line of {line['ticket']} has no time zone")
    return moment.timestamp()


def evidence_paths(root: Path, values: list, since: float, used: set) -> list:
    if len(values) > MAX_EVIDENCE:
        raise bad_input("evidence_invalid", f"at most {MAX_EVIDENCE} evidence files")
    folder = root.joinpath(*STATE_FOLDERS)
    checked = []
    for value in values:
        relative = Path(value)
        if not value or relative.is_absolute() or ".." in relative.parts:
            raise bad_input("evidence_path_unsafe", f"{value!r} must be a relative path inside the workspace")
        try:
            resolved = (root / relative).resolve(strict=True)
        except (OSError, RuntimeError):
            raise rule("evidence_missing", f"{value} does not exist") from None
        if not resolved.is_relative_to(root):
            raise bad_input("evidence_path_unsafe", f"{value} leaves the workspace through a symbolic link")
        if not resolved.is_relative_to(folder):
            raise rule("evidence_outside_state_folder", f"{value} is not inside {STATE_TEXT}/")
        if resolved.parent == folder and resolved.name in (LEDGER_NAME, LOCK_NAME):
            raise rule("evidence_is_ledger", f"{value} is the ledger or its lock file")
        if not resolved.is_file() or resolved.stat().st_size == 0:
            raise rule("evidence_missing", f"{value} is not a nonempty file")
        if resolved.stat().st_mtime < since - CLOCK_TOLERANCE_SECONDS:
            raise rule("evidence_older_than_ticket", f"{value} was last written before this ticket started")
        shown = resolved.relative_to(root).as_posix()
        if shown in used:
            raise rule("evidence_reused", f"{value} is already the evidence of an earlier ticket")
        if shown not in checked:
            checked.append(shown)
    return checked


def append(path: Path, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | NO_FOLLOW, 0o644)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def command_start(root: Path, ticket: str, timeout: float) -> dict:
    folder = state_folder(root, create=True)
    with LedgerLock(folder, exclusive=True, timeout=timeout):
        path = ledger_path(folder)
        open_line, finished, _used = replay(read_ledger(path))
        if open_line is not None and open_line["ticket"] == ticket:
            raise rule("ticket_already_open", f"{ticket} is already open")
        if open_line is not None:
            raise rule("another_ticket_open", f"{open_line['ticket']} is open; one ticket at a time")
        if ticket in finished:
            raise rule("ticket_already_finished", f"{ticket} already finished as {finished[ticket]}")
        append(path, {"record_type": LINE_TYPE, "event": "start", "ticket": ticket, "at": now()})
    return {"result": "started", "ticket": ticket, "ledger": LEDGER_TEXT}


def command_finish(root: Path, ticket: str, status: str, summary, needs, evidence: list, timeout: float) -> dict:
    folder = state_folder(root, create=True)
    with LedgerLock(folder, exclusive=True, timeout=timeout):
        path = ledger_path(folder)
        open_line, _finished, used = replay(read_ledger(path))
        if open_line is None:
            raise rule("no_open_ticket", "no ticket is open")
        if open_line["ticket"] != ticket:
            raise rule("ticket_not_open", f"{open_line['ticket']} is open, not {ticket}")
        summary = one_line(summary, "--summary")
        if status == "blocked" and needs is None:
            raise rule("blocked_without_needs", "a blocked ticket names what is needed and from whom")
        needs = one_line(needs, "--needs") if needs is not None else None
        paths = evidence_paths(root, evidence, started_at(open_line), used)
        if status == "done" and not paths:
            raise rule("done_without_evidence", "a done ticket names at least one evidence file")
        record = {"record_type": LINE_TYPE, "event": "finish", "ticket": ticket, "status": status,
                  "summary": summary, "evidence": paths, "at": now()}
        if needs is not None:
            record["needs"] = needs
        append(path, record)
    return {"result": "finished", "ticket": ticket, "status": status, "ledger": LEDGER_TEXT}


def command_status(root: Path, timeout: float) -> dict:
    folder = state_folder(root, create=False)
    if not folder.is_dir():
        lines = []
    else:
        with LedgerLock(folder, exclusive=False, timeout=timeout):
            lines = read_ledger(ledger_path(folder))
    open_line, finished, _used = replay(lines)
    counts = {status: sum(1 for value in finished.values() if value == status) for status in STATUSES}
    recent = list(finished.items())[-MAX_LISTED:]
    return {"result": "ok", "open_ticket": open_line["ticket"] if open_line else None, "finished": counts,
            "finished_tickets": [{"ticket": key, "status": value} for key, value in recent],
            "finished_tickets_shown": len(recent), "ledger": LEDGER_TEXT}


def main(argv=None) -> int:
    ticket = "KEY"
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
        ticket = getattr(options, "ticket", None) or ticket
        root = workspace(options.root)
        if options.command == "status":
            answer = command_status(root, options.lock_timeout)
        elif options.command == "start":
            answer = command_start(root, ticket_key(options.ticket), options.lock_timeout)
        else:
            answer = command_finish(root, ticket_key(options.ticket), options.status, options.summary,
                                    options.needs, options.evidence, options.lock_timeout)
    except OSError as error:  # an unexpected file system failure is still answered as one JSON object
        refusal = bad_input("file_system_error", f"{type(error).__name__}: {error.strerror or error}"[:300])
        return answer_refusal(refusal, ticket)
    except Refusal as refusal:
        return answer_refusal(refusal, ticket)
    print(json.dumps(answer, ensure_ascii=False, sort_keys=True))
    return 0


def answer_refusal(refusal: Refusal, ticket: str) -> int:
    stop_run = refusal.code in STOP_RUN
    next_step = NEXT_FOR_STOP if stop_run else NEXT.get(refusal.code, NEXT_FOR_INPUT)
    if TICKET.fullmatch(ticket):
        next_step = next_step.replace("KEY", ticket)
    print(json.dumps({"result": "refused", "code": refusal.code, "detail": refusal.detail, "next": next_step,
                      "stop_run": stop_run}, ensure_ascii=False, sort_keys=True))
    return refusal.status


if __name__ == "__main__":
    raise SystemExit(main())

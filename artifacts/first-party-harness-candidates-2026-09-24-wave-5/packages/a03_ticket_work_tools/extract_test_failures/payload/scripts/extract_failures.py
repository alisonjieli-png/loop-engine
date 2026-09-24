"""Effects: reads one test output file under --root, or standard input, and prints one JSON object; writes no files and uses no network.

Extract failing tests from pytest, unittest or JUnit XML output. Each failure
keeps its test id, the exception type, a short message and the first project
frame, found by reading the traceback from the innermost frame outward and
skipping library and standard library frames. Passing tests, captured logs and
long tracebacks are left out, but every count is exact.

Exit status: 0 when the output shows a finished run with no failure, 1 when it
shows failures, errors, no tests or no recognizable result, 2 when the input is
refused (unsafe path, too large, unreadable, or XML with a document type).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

RECORD_TYPE = "test_failures/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 256 * 1024 * 1024
MESSAGE_LINES = 8
MESSAGE_CHARS = 1200
DEFAULT_MAX_FAILURES = 25

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PYTEST_SECTION = re.compile(r"^={3,} (.+?) ={3,}$")
PYTEST_BLOCK = re.compile(r"^_{3,} (.+?) _{3,}$")
PYTEST_CAPTURE = re.compile(r"^-{3,} (.+?) -{3,}$")
PYTEST_SEPARATOR = re.compile(r"^(?:_ ){5,}_?\s*$")
PYTEST_SUMMARY_ITEM = re.compile(r"^(FAILED|ERROR) (\S+)(?: - (.*))?$")
PYTEST_COUNT = re.compile(r"(\d+) (failed|passed|errors?|skipped|xfailed|xpassed|deselected|warnings?|rerun)\b")
PYTEST_FINAL = re.compile(
    r"^=*\s*(?:(?:\d+ (?:failed|passed|errors?|skipped|xfailed|xpassed|deselected|warnings?|rerun),? ?)+"
    r"|no tests ran) in \d+(?:\.\d+)?s\b.*$")
LOCATION = re.compile(r"^(?P<path>[^\s:>][^:]*?\.\w+|<[^>\n]+>):(?P<line>\d+):(?: (?P<rest>.*))?$")
PY_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+)(?:, in (?P<function>.+))?$')
JAVA_FRAME = re.compile(r"^\s*at (?P<qualified>[\w$.<>]+)\((?P<file>[^:()]+)(?::(?P<line>\d+))?\)\s*$")
E_LINE = re.compile(r"^E(\s*)(.*)$")
EXCEPTION_NAME = re.compile(r"^([A-Za-z_][\w.]*)(?::\s|:$|$)")
EXCEPTION_REST = re.compile(r"^(?:[A-Z_]\w*|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)(?::|$)")
UNITTEST_RULE = re.compile(r"^={20,}$")
UNITTEST_DASH = re.compile(r"^-{20,}$")
UNITTEST_HEADER = re.compile(r"^(FAIL|ERROR|UNEXPECTED SUCCESS): (?P<name>\S+) \((?P<where>[^)]*)\)(?P<extra>.*)$")
E_PREFIX = ("E ", "E\t")
UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in ")
UNITTEST_RESULT = re.compile(r"^(OK|FAILED|NO TESTS RAN)(?: \((.*)\))?\s*$")
TRACEBACK_START = "Traceback (most recent call last):"
CHAIN_MARKERS = ("During handling of the above exception, another exception occurred:",
                 "The above exception was the direct cause of the following exception:")
LIBRARY_MARKERS = ("/site-packages/", "/dist-packages/", "<frozen", "<string>", "<stdin>", "/.venv/",
                   "/venv/", "/.tox/", "/.nox/")
STDLIB = re.compile(r"(?:^|/)lib/python\d+(?:\.\d+)?/")
JAVA_LIBRARY = ("java.", "javax.", "jdk.", "sun.", "com.sun.", "org.junit.", "junit.", "org.opentest4j.",
                "org.gradle.", "org.apache.maven.", "kotlin.", "scala.", "org.testng.")
TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]*\.py|[^/]*_test\.py|conftest\.py)$|(?:^|/)tests?/")
# In pytest's long mode a frame's function is named only by the def line of its source excerpt.
DEF_LINE = re.compile(r"^[>\s]*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(")
# Python 3.10 names an unexpected success only on its verbose progress line, which can share a
# line with the progress text of a test that has subtests.
UNITTEST_VERBOSE_UNEXPECTED = re.compile(r"(\S+) \(([^()\s]+)\) \.\.\. unexpected success\s*$")
UNITTEST_NOT_A_TEST = ("class setup", "class teardown", "module setup", "module teardown")
XPASS_STRICT = "[XPASS(strict)]"
CHAIN_NOTE = "chained exceptions; the last one is shown and cause holds the first"


class Refused(Exception):
    """Raised for input the script will not read."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": f"arguments: {message}"})
        raise SystemExit(2)


def emit(document: dict) -> None:
    sys.stdout.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")


def read_input(name: str, root: Path, max_bytes: int) -> bytes:
    if name == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise Refused(f"standard input is larger than {max_bytes} bytes")
        return data
    if "\x00" in name or not name:
        raise Refused("the input path is empty or holds a NUL character")
    given = Path(name)
    if ".." in given.parts:
        raise Refused("the input path may not contain '..'")
    real_root = root.resolve(strict=True)
    try:
        real = (given if given.is_absolute() else real_root / given).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise Refused(f"the input path cannot be resolved: {type(error).__name__}") from error
    if real != real_root and real_root not in real.parents:
        raise Refused("the input path leaves --root, directly or through a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(real, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise Refused("the input is not a regular file")
        if info.st_size > max_bytes:
            raise Refused(f"the input is {info.st_size} bytes, above the limit of {max_bytes}")
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise Refused(f"the input grew above the limit of {max_bytes} bytes while it was read")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


# ---------------------------------------------------------------------------
# frames
# ---------------------------------------------------------------------------

class FrameJudge:
    """Decides which frames belong to the project and how to print their paths."""

    def __init__(self, project_root: str | None):
        self.root = project_root.rstrip("/") if project_root else None
        self.root_matched = False

    def is_library(self, path: str) -> bool:
        return any(marker in path for marker in LIBRARY_MARKERS) or bool(STDLIB.search(path))

    def is_project(self, frame: dict, strict: bool) -> bool:
        path = frame["path"]
        if frame.get("style") == "java":
            return not frame.get("function", "").startswith(JAVA_LIBRARY)
        if self.is_library(path) or path.startswith("../"):
            return False
        if os.path.isabs(path) and strict and self.root:
            return path == self.root or path.startswith(self.root + "/")
        return True

    def display(self, path: str) -> str:
        if self.root and os.path.isabs(path) and path.startswith(self.root + "/"):
            return path[len(self.root) + 1:]
        return path

    def choose(self, frames: list[dict]) -> tuple[dict | None, dict | None]:
        """Return (first project frame from the innermost outward, outermost project test frame)."""
        chosen = None
        for strict in (True, False):
            for frame in reversed(frames):
                if self.is_project(frame, strict):
                    chosen = frame
                    break
            if chosen is not None:
                if strict:
                    self.root_matched = True
                break
        test_frame = None
        for frame in frames:
            if self.is_project(frame, False) and TEST_FILE.search(self.display(frame["path"])):
                test_frame = frame
                break
        return self.public(chosen), self.public(test_frame)

    def public(self, frame: dict | None) -> dict | None:
        if frame is None:
            return None
        return {"path": self.display(frame["path"]), "line": frame.get("line"),
                "function": frame.get("function")}


def python_traceback(lines: list[str]) -> tuple[list[dict], list[str], bool]:
    """Frames (outermost first) and the final exception lines of a Python traceback text."""
    chained = any(line.strip() in CHAIN_MARKERS for line in lines)
    start = 0
    for index, line in enumerate(lines):
        if line.strip() == TRACEBACK_START:
            start = index
    frames, last_frame_at = [], None
    for index in range(start, len(lines)):
        match = PY_FRAME.match(lines[index])
        if match:
            frames.append({"path": match["path"], "line": int(match["line"]),
                           "function": (match["function"] or "").strip() or None, "style": "python"})
            last_frame_at = index
    message = []
    if last_frame_at is not None:
        index = last_frame_at + 1
        while index < len(lines) and (lines[index].startswith((" ", "\t")) or not lines[index].strip()):
            index += 1
        message = [line for line in lines[index:] if line.strip()]
    return frames, message, chained


def chain_parts(lines: list[str]) -> list[list[str]]:
    """Split a block at the lines that join chained exceptions; the last part ended the test."""
    parts, current = [], []
    for line in lines:
        if line.strip() in CHAIN_MARKERS:
            parts.append(current)
            current = []
        else:
            current.append(line)
    parts.append(current)
    return parts


def location_frames(lines: list[str]) -> list[dict]:
    """Frames from pytest location lines such as 'src/app.py:7: in load' or 'src/app.py:7: KeyError'.

    When the location line names no function (long mode), the first def line printed since
    the previous location line names it.
    """
    frames, first_def = [], None
    for line in lines:
        match = LOCATION.match(line)
        if match and not line.startswith(E_PREFIX):
            rest = (match["rest"] or "").strip()
            function = rest[3:].strip() if rest.startswith("in ") else first_def
            frames.append({"path": match["path"], "line": int(match["line"]), "function": function,
                           "style": "location", "rest": rest})
            first_def = None
        elif first_def is None and not line.startswith(E_PREFIX):
            definition = DEF_LINE.match(line)
            if definition:
                first_def = definition.group(1)
    return frames


def java_frames(lines: list[str]) -> list[dict]:
    frames = []
    for line in lines:
        match = JAVA_FRAME.match(line)
        if match:
            frames.append({"path": match["file"], "line": int(match["line"]) if match["line"] else None,
                           "function": match["qualified"], "style": "java"})
    frames.reverse()  # Java prints the innermost frame first; keep the innermost last like Python
    return frames


def e_message(lines: list[str]) -> list[str]:
    message, indent = [], None
    for line in lines:
        match = E_LINE.match(line)
        if not match or (line[1:2] not in (" ", "\t", "")):
            continue
        spaces, text = match.group(1), match.group(2)
        if indent is None:
            indent = len(spaces)
        extra = max(len(spaces) - indent, 0)
        message.append(" " * extra + text)
    return message


def exception_name(message: list[str], frames: list[dict]) -> str | None:
    for frame in reversed(frames):
        rest = frame.get("rest") or ""
        match = EXCEPTION_NAME.match(rest)
        if match and not rest.startswith("in "):
            return match.group(1)
    if message:
        match = EXCEPTION_NAME.match(message[0].strip())
        if match and (match.group(1)[:1].isupper() or "." in match.group(1)):
            return match.group(1)
    return None


def bounded(message: list[str]) -> tuple[str, bool]:
    lines = [line.rstrip() for line in message if line.strip()]
    truncated = len(lines) > MESSAGE_LINES
    text = "\n".join(lines[:MESSAGE_LINES])
    if len(text) > MESSAGE_CHARS:
        text, truncated = text[:MESSAGE_CHARS], True
    return text, truncated


def first_line(lines: list[str]) -> str | None:
    for line in lines:
        if line.strip():
            return line.strip()[:200]
    return None


def failure_record(test_id: str, kind: str, block: list[str], judge: FrameJudge, summary_message: str | None,
                   phase: str | None = None) -> dict:
    notes, cause = [], None
    parts = chain_parts(block)
    if any(line.strip() == TRACEBACK_START for line in block):
        frames, message, chained = python_traceback(block)
        if chained:
            notes.append(CHAIN_NOTE)
            cause = first_line(python_traceback(parts[0])[1])
    else:
        # pytest prints each exception of a chain with its own frames and E lines; the last
        # part is the exception that ended the test.
        last = parts[-1]
        frames = location_frames(last)
        message = e_message(last)
        if len(parts) > 1:
            notes.append(CHAIN_NOTE)
            cause = first_line(e_message(parts[0]) or parts[0])
        if not frames:
            frames = java_frames(last)
            if frames and not message:
                message = []
                for line in last:
                    if JAVA_FRAME.match(line):
                        break
                    if line.strip():
                        message.append(line.strip())
    if not message and not frames:
        # A block with no traceback, such as a strict unexpected pass, holds its message as text.
        message = [line.strip() for line in block if line.strip() and not PYTEST_SEPARATOR.match(line)]
    if not message and summary_message:
        message = [summary_message]
        notes.append("message taken from the summary line, which the runner may cut short")
    text, truncated = bounded(message)
    project, test_frame = judge.choose(frames)
    if text.startswith(XPASS_STRICT):
        notes.append("the test is marked as an expected failure (strict) and passed, so no traceback exists")
    elif frames and project is None:
        notes.append("every printed frame is outside the project; rerun this test with --tb=short "
                     "or check --project-root")
    elif not frames and kind in ("failed", "error") and not notes:
        notes.append("no frame was printed for this failure; rerun this test with --tb=short")
    record = {"id": test_id, "kind": kind, "exception": exception_name(message, frames), "message": text,
              "message_truncated": truncated, "first_project_frame": project, "test_frame": test_frame,
              "frames_seen": len(frames)}
    if cause:
        record["cause"] = cause
    if phase:
        record["phase"] = phase
    if notes:
        record["notes"] = notes
    return record


# ---------------------------------------------------------------------------
# pytest
# ---------------------------------------------------------------------------

def pytest_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    sections, name, current = [], "", []
    for line in lines:
        match = PYTEST_SECTION.match(line)
        if match and not PYTEST_FINAL.match(line):
            sections.append((name, current))
            name, current = match.group(1).strip(), []
        else:
            current.append(line)
    sections.append((name, current))
    return sections


def split_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks, header, current = [], None, []
    for line in lines:
        match = PYTEST_BLOCK.match(line)
        if match:
            if header is not None:
                blocks.append((header, current))
            header, current = match.group(1).strip(), []
        elif header is not None:
            current.append(line)
    if header is not None:
        blocks.append((header, current))
    return blocks


def without_captures(lines: list[str]) -> list[str]:
    kept = []
    for line in lines:
        if PYTEST_CAPTURE.match(line):
            break
        kept.append(line)
    return kept


def header_key(header: str) -> tuple[str, str | None]:
    """Normalize a block header to the key used to match summary lines, and the phase."""
    for prefix, phase in (("ERROR at setup of ", "setup"), ("ERROR at teardown of ", "teardown"),
                          ("ERROR collecting ", "collection")):
        if header.startswith(prefix):
            return header[len(prefix):].strip(), phase
    return header, None


def node_key(node_id: str) -> str:
    if "::" not in node_id:
        return node_id
    return ".".join(node_id.split("::")[1:])


def claim_by_message(summary_items: list[dict], used: set, kind: str, printed: str) -> dict | None:
    """Pick the summary item whose message starts the printed location message.

    In --tb=line mode pytest prints no block header, and a failure such as a strict
    unexpected pass prints no location line at all, so pairing by order would shift
    every later message onto the wrong test. The summary message may end with '...'
    where pytest cut it short; only the part before the cut is compared.
    """
    candidates = [item for item in summary_items if item["kind"] == kind and id(item) not in used]
    for item in candidates:
        message = (item["message"] or "").rstrip()
        if message.endswith("..."):
            message = message[:-3].rstrip()
        if message and printed.startswith(message):
            return item
    for item in candidates:
        if not item["message"]:
            return item  # nothing to compare: keep the printed order
    return None


def parse_pytest(lines: list[str], judge: FrameJudge) -> dict:
    counts, summary_items, notes = {}, [], []
    final_seen = False
    for line in lines:
        if PYTEST_FINAL.match(line):
            final_seen = True
            counts = {}
            for number, word in PYTEST_COUNT.findall(line):
                key = {"error": "errors", "warning": "warnings"}.get(word, word)
                counts[key] = counts.get(key, 0) + int(number)
    sections = pytest_sections(lines)
    for name, body in sections:
        if name.startswith("short test summary info"):
            for line in body:
                match = PYTEST_SUMMARY_ITEM.match(line)
                if match:
                    summary_items.append({"kind": "failed" if match.group(1) == "FAILED" else "error",
                                          "id": match.group(2), "message": match.group(3)})
    by_key = {}
    for item in summary_items:
        by_key.setdefault((item["kind"], node_key(item["id"])), item)
        by_key.setdefault((item["kind"], item["id"]), item)
    failures, used = [], set()
    for name, body in sections:
        if name not in ("FAILURES", "ERRORS"):
            continue
        kind = "failed" if name == "FAILURES" else "error"
        blocks = split_blocks(body)
        if blocks:
            for header, block in blocks:
                key, phase = header_key(header)
                item = by_key.get((kind, key))
                if item is None:
                    for candidate in summary_items:
                        if candidate["kind"] == kind and (candidate["id"].endswith("::" + key) or candidate["id"] == key):
                            item = candidate
                            break
                block = without_captures(block)
                if item is not None:
                    used.add(id(item))
                    test_id = item["id"]
                else:
                    frames = location_frames(block)
                    test_id = f"{frames[0]['path']}::{key}" if frames and phase is None else key
                failures.append(failure_record(test_id, kind, block, judge, item and item["message"],
                                               phase or ("call" if kind == "failed" else None)))
        else:
            # --tb=line prints one location line per failure, after its E lines, with no block header.
            # Captured output can sit between the E lines and the location line; it is skipped, and
            # inside it only a location line that names an exception ends the failure.
            pending, in_capture = [], False
            for line in body:
                if PYTEST_CAPTURE.match(line):
                    in_capture = True
                    continue
                if line.startswith(XPASS_STRICT) and not in_capture:
                    # A strict unexpected pass prints its reason with no location line, sometimes
                    # twice; the first copy is paired with its summary item and the rest are dropped.
                    item = next((candidate for candidate in summary_items if candidate["kind"] == kind
                                 and id(candidate) not in used
                                 and (candidate["message"] or "").startswith(XPASS_STRICT)
                                 and line.strip().startswith((candidate["message"] or "").rstrip(".").rstrip())),
                                None)
                    if item is not None:
                        used.add(id(item))
                        failures.append(failure_record(item["id"], kind, [line], judge, item["message"]))
                    continue
                location = LOCATION.match(line)
                rest = (location["rest"] or "").strip() if location else ""
                ends = bool(location) and not line.startswith(E_PREFIX) and (
                    not in_capture or bool(EXCEPTION_REST.match(rest)))
                if in_capture and not ends:
                    continue
                pending.append(line)
                if ends:
                    in_capture = False
                    item = claim_by_message(summary_items, used, kind, rest)
                    if item is not None:
                        used.add(id(item))
                    failures.append(failure_record(item["id"] if item else f"unnamed {kind} {len(failures) + 1}",
                                                   kind, pending, judge, item and item["message"]))
                    pending = []
    for item in summary_items:
        if id(item) not in used:
            failures.append({"id": item["id"], "kind": item["kind"], "exception": exception_name([item["message"] or ""], []),
                             "message": (item["message"] or "")[:MESSAGE_CHARS], "message_truncated": False,
                             "first_project_frame": None, "test_frame": None, "frames_seen": 0,
                             "notes": ["only the summary line was printed; rerun with --tb=short to see frames"]})
    totals = {"failed": counts.get("failed", 0), "errors": counts.get("errors", 0), "passed": counts.get("passed", 0),
              "skipped": counts.get("skipped", 0), "xfailed": counts.get("xfailed", 0),
              "xpassed": counts.get("xpassed", 0)} if final_seen else None
    if not final_seen:
        notes.append("no final pytest summary line was found; the run may have been cut short")
    return {"totals": totals, "failures": failures, "notes": notes, "finished": final_seen}


# ---------------------------------------------------------------------------
# unittest
# ---------------------------------------------------------------------------

def unittest_id(name: str, where: str) -> tuple[str, str | None]:
    if where.startswith("unittest.loader._FailedTest"):
        return name, "import"
    if where == name or where.endswith("." + name):
        return where, None
    phase = {"setUpClass": "class setup", "tearDownClass": "class teardown", "setUpModule": "module setup",
             "tearDownModule": "module teardown"}.get(name)
    return f"{where}.{name}", phase


def unexpected_success(test_id: str) -> dict:
    return {"id": test_id, "kind": "unexpected_success", "exception": None,
            "message": "the test was marked as an expected failure but passed", "message_truncated": False,
            "first_project_frame": None, "test_frame": None, "frames_seen": 0}


def parse_unittest(lines: list[str], judge: FrameJudge) -> dict:
    failures, notes, index = [], [], 0
    ran, result = None, None
    verbose_unexpected = []
    while index < len(lines):
        line = lines[index]
        progress = UNITTEST_VERBOSE_UNEXPECTED.search(line)
        if progress:
            verbose_unexpected.append(unittest_id(progress.group(1), progress.group(2))[0])
        ran_match = UNITTEST_RAN.match(line)
        if ran_match:
            ran = int(ran_match.group(1))
        result_match = UNITTEST_RESULT.match(line)
        if result_match and ran is not None:
            result = result_match
        if line.startswith("UNEXPECTED SUCCESS: "):
            header = UNITTEST_HEADER.match(line)
            if header:
                failures.append(unexpected_success(unittest_id(header["name"], header["where"])[0]))
        if UNITTEST_RULE.match(line) and index + 1 < len(lines):
            header = UNITTEST_HEADER.match(lines[index + 1])
            if header and header.group(1) != "UNEXPECTED SUCCESS":
                index += 2
                while index < len(lines) and not UNITTEST_DASH.match(lines[index]):
                    index += 1
                index += 1
                block = []
                while index < len(lines) and not UNITTEST_RULE.match(lines[index]):
                    if UNITTEST_DASH.match(lines[index]) and index + 1 < len(lines) \
                            and UNITTEST_RAN.match(lines[index + 1]):
                        break
                    if lines[index].startswith("UNEXPECTED SUCCESS: "):
                        break
                    block.append(lines[index])
                    index += 1
                test_id, phase = unittest_id(header["name"], header["where"])
                extra = header["extra"].strip()
                kind = {"FAIL": "failed", "ERROR": "error"}.get(header.group(1), "unexpected_success")
                record = failure_record(test_id, kind, block, judge, None, phase)
                if extra:
                    record["subtest"] = extra
                failures.append(record)
                continue
        index += 1
    named = {record["id"] for record in failures if record["kind"] == "unexpected_success"}
    for test_id in verbose_unexpected:
        if test_id not in named:
            named.add(test_id)
            failures.append(unexpected_success(test_id))
    totals = None
    if ran is not None:
        detail = {}
        if result and result.group(2):
            for part in result.group(2).split(","):
                key, _, value = part.strip().partition("=")
                if value.isdigit():
                    detail[key] = int(value)
        failed, errors = detail.get("failures", 0), detail.get("errors", 0)
        skipped = detail.get("skipped", 0)
        expected = detail.get("expected failures", 0)
        unexpected = detail.get("unexpected successes", 0)
        # The runner counts each failing subtest, and each class or module fixture error, as
        # a failure or error, but counts a test once in 'Ran'; subtract each failing test once.
        failing_tests = {record["id"] for record in failures if record["kind"] in ("failed", "error")
                         and record.get("phase") not in UNITTEST_NOT_A_TEST}
        totals = {"tests": ran, "failed": failed, "errors": errors, "skipped": skipped,
                  "expected_failures": expected, "unexpected_successes": unexpected,
                  "passed": max(ran - len(failing_tests) - skipped - expected - unexpected, 0)}
        if unexpected > len(named):
            notes.append(f"{unexpected - len(named)} unexpected successes are counted but not named; rerun with -v")
    else:
        notes.append("no 'Ran N tests' line was found; the run may have been cut short")
    return {"totals": totals, "failures": failures, "notes": notes, "finished": ran is not None}


# ---------------------------------------------------------------------------
# JUnit XML
# ---------------------------------------------------------------------------

def parse_junit(data: bytes, judge: FrameJudge) -> dict:
    head = data[:4096].lower()
    if b"<!doctype" in data.lower() or b"<!entity" in head:
        raise Refused("XML with a document type or entity declaration is refused")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise Refused(f"the XML does not parse: {error}") from error
    tests = failed = errors = skipped = 0
    failures = []
    for case in root.iter("testcase"):
        tests += 1
        name = case.get("name", "")
        classname = case.get("classname", "")
        test_id = f"{classname}.{name}" if classname else name
        outcome = None
        for element in case:
            tag = element.tag.split("}")[-1]
            if tag in ("failure", "error") and outcome is None:
                outcome = (tag, element)
            elif tag == "skipped":
                skipped += 1
        if outcome is None:
            continue
        tag, element = outcome
        if tag == "failure":
            failed += 1
        else:
            errors += 1
        body = (element.text or "").splitlines()
        attribute = (element.get("message") or "").splitlines()
        record = failure_record(test_id, "failed" if tag == "failure" else "error", body, judge,
                                attribute[0] if attribute else None)
        declared = element.get("type")
        if declared:
            record["exception"] = declared
        summary_note = "message taken from the summary line, which the runner may cut short"
        if attribute and (not record["message"] or summary_note in record.get("notes", [])):
            # The message attribute of a JUnit report is complete, unlike a runner's summary line.
            record["message"], record["message_truncated"] = bounded(attribute)
            record["notes"] = [note for note in record.get("notes", []) if note != summary_note]
            if not record["notes"]:
                record.pop("notes")
        if case.get("file"):
            record["file"] = case.get("file")
        if case.get("line", "").isdigit():
            record["line"] = int(case.get("line"))
        failures.append(record)
    if tests == 0:
        return {"totals": {"tests": 0, "failed": 0, "errors": 0, "skipped": 0, "passed": 0}, "failures": [],
                "notes": ["the XML holds no testcase element"], "finished": True}
    totals = {"tests": tests, "failed": failed, "errors": errors, "skipped": skipped,
              "passed": tests - failed - errors - skipped}
    return {"totals": totals, "failures": failures, "notes": [], "finished": True}


# ---------------------------------------------------------------------------
# plain traceback and detection
# ---------------------------------------------------------------------------

def parse_crash(lines: list[str], judge: FrameJudge) -> dict:
    record = failure_record("process crashed before a test result", "crash", lines, judge, None)
    return {"totals": None, "failures": [record], "notes": ["no test runner summary; a Python traceback was found"],
            "finished": False}


def detect_format(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<testsuite"):
        return "junit"
    lines = text.splitlines()
    if any(line.startswith(("platform ", "rootdir: ")) or "short test summary info" in line for line in lines) \
            or any(PYTEST_FINAL.match(line) for line in lines):
        return "pytest"
    if any(UNITTEST_RAN.match(line) for line in lines) or any(
            UNITTEST_HEADER.match(line) for line in lines):
        return "unittest"
    if any(line.strip() == TRACEBACK_START for line in lines):
        return "traceback"
    return "unknown"


def summarize(parsed: dict, max_failures: int, judge: FrameJudge, fmt: str, decoding_note: str | None) -> tuple[dict, int]:
    failures = parsed["failures"]
    totals = parsed["totals"]
    notes = list(parsed["notes"])
    if decoding_note:
        notes.append(decoding_note)
    if failures and not judge.root_matched and any(item.get("first_project_frame") for item in failures):
        notes.append("no frame lay under --project-root; frames outside library folders were used instead")
    counted = None
    if totals is not None:
        counted = totals.get("failed", 0) + totals.get("errors", 0)
    extracted = len([item for item in failures if item["kind"] in ("failed", "error")])
    consistency = {"summary_failed_and_errors": counted, "extracted": extracted,
                   "matches": counted == extracted if counted is not None else None}
    tests_seen = None if totals is None else totals.get("tests", sum(
        totals.get(key, 0) for key in ("failed", "errors", "passed", "skipped", "xfailed", "xpassed")))
    if failures:
        status, code = "failures_found", 1
    elif not parsed["finished"] or totals is None:
        status, code = "no_result_found", 1
    elif tests_seen == 0:
        status, code = "no_tests_ran", 1
    else:
        status, code = "no_failures", 0
    document = {"record_type": RECORD_TYPE, "status": status, "format": fmt, "totals": totals,
                "consistency": consistency, "failures": failures[:max_failures],
                "omitted_failures": max(len(failures) - max_failures, 0), "notes": notes}
    return document, code


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description="Extract failing tests from pytest, unittest or JUnit XML output.")
    parser.add_argument("input", nargs="?", default="-", help="test output file, or - for standard input")
    parser.add_argument("--format", choices=("auto", "pytest", "unittest", "junit"), default="auto")
    parser.add_argument("--root", default=".", help="folder the input path must stay inside")
    parser.add_argument("--project-root", default=".", help="folder whose frames count as project frames")
    parser.add_argument("--max-failures", type=int, default=DEFAULT_MAX_FAILURES)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    options = parser.parse_args(argv)
    try:
        if not 0 < options.max_bytes <= HARD_MAX_BYTES:
            raise Refused(f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
        if not 0 < options.max_failures <= 1000:
            raise Refused("--max-failures must be between 1 and 1000")
        root = Path(options.root)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        data = read_input(options.input, root, options.max_bytes)
        project_root = str(Path(options.project_root).resolve()) if options.project_root else None
        judge = FrameJudge(project_root)
        text = data.decode("utf-8", errors="replace")
        replaced = text.count("\ufffd") - data.decode("utf-8", errors="ignore").count("\ufffd")
        decoding_note = f"{replaced} bytes that are not UTF-8 were replaced" if replaced > 0 else None
        text = ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
        fmt = detect_format(text) if options.format == "auto" else options.format
        if fmt == "junit":
            parsed = parse_junit(data, judge)
        elif fmt == "pytest":
            parsed = parse_pytest(text.splitlines(), judge)
        elif fmt == "unittest":
            parsed = parse_unittest(text.splitlines(), judge)
        elif fmt == "traceback":
            parsed = parse_crash(text.splitlines(), judge)
        else:
            parsed = {"totals": None, "failures": [], "finished": False,
                      "notes": ["no pytest, unittest, JUnit XML or traceback text was recognized"]}
        document, code = summarize(parsed, options.max_failures, judge, fmt, decoding_note)
    except Refused as error:
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": str(error)})
        return 2
    emit(document)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

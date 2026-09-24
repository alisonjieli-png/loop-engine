"""Check each item a morning report marks complete against its evidence; reads only files the report or its handoffs name.

Effects: reads the report named by --report (or standard input for "-"), every evidence
file and step handoff it cites, and the files a cited handoff lists, all below --root.
Writes nothing, starts no process and uses no network. Prints one JSON object.
Exit status: 0 pass, 1 fail or review, 2 refused input.

A completion claim is supported when it cites at least one evidence file, every cited
file exists below the root, matches its cited SHA-256 digest (when one is cited),
agrees with every cited exit code, shows no failure that its citation says should be a
pass, and at least one cited file shows a passing gate by itself: a JSON gate record
with a passing verdict, passed flag, checks or exit code, a JUnit XML report without
failures, or a test or build log with a passing summary line. An exit code written in
the report is compared, but it never proves a pass on its own.

A cited file that shows a failure without a stated expectation, a step handoff whose
listed files changed after it was written, and a pass reached by changing only tests
are not refused; they are listed under needs_reading (verdict review), because only a
reader of the claim can say whether they fit it.

Reports: a JSON list of items (or an object holding one), a night_morning_report/v1
record, or Markdown with a table that has a status column and an evidence column.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

TOOL = "verify-morning-report-claims"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 5000
MAX_EVIDENCE_FILES = 1000
LIST_LIMIT = 200
NIGHT_REPORT = "night_morning_report/v1"
HANDOFF = "night_step_handoff/v1"
REPRODUCTION_RECORD = "ticket_reproduction_run/v1"
CHECK_MARK, HEAVY_CHECK, CHECK_BOX, CROSS = "\u2713", "\u2714", "\u2705", "\u274c"
#: Status words that claim the item is complete. --claim-word adds more.
CLAIMS = {"verified", "verified_by_test_change", "complete", "completed", "done", "fixed", "resolved", "passed",
          "pass", "finished", "merged", "shipped", "closed", "success", "succeeded", "green", "implemented",
          "delivered", "landed", "ready_for_review", "accepted", CHECK_BOX, HEAVY_CHECK, CHECK_MARK, "[x]"}
#: Status words that make no completion claim, such as the rungs of a graded night.
NOT_CLAIMS = {"negative_result", "cause_localised", "cause_localized", "blocked", "blocked_named", "narrowed",
              "no_progress", "already_green", "skipped", "attempted", "partial", "failed", "fail", "in_progress",
              "not_started", "open", "todo", "deferred", "wont_fix", "not_done", "nothing_found", "unfinished",
              "incomplete", "not_ready", "needs_review", "waiting", "pending", CROSS, "[_]"}
#: Verdict words inside an evidence record.
PASS_WORDS = {"pass", "passed", "passing", "ok", "success", "succeeded", "successful", "green", "verified",
              "ready_for_review"}
FAIL_WORDS = {"fail", "failed", "failure", "failing", "error", "errored", "errors", "red", "not_ready", "timed_out",
              "timeout", "refused", "broken", "cancelled", "canceled", "aborted", "crashed"}
ITEM_LISTS = ("items", "tickets", "results", "entries", "tasks")
ID_KEYS = ("id", "ticket", "ticket_id", "key", "task", "step_id", "name")
STATUS_KEYS = ("status", "outcome", "rung", "state", "result")
EVIDENCE_KEYS = ("evidence", "evidence_files", "artifacts", "proof")
EXIT_KEYS = ("exit_code", "exitcode", "returncode", "exit_status", "exit")
VERDICT_KEYS = ("verdict", "conclusion", "outcome", "result", "status")
HEX = re.compile(r"(?:sha256[:=]\s*)?([0-9a-fA-F]{64})\Z")
TOKEN_WORDS = re.compile(r"\[x\]|\[_\]|[" + CHECK_BOX + CHECK_MARK + HEAVY_CHECK + CROSS + r"]|[^\W_]+")

# Summary lines of common test and build runners. Any failure line wins over a pass line.
PYTEST_SUMMARY = re.compile(r"^=*\s*((?:\d+ [a-z]+, )*\d+ [a-z]+) in \d+(?:\.\d+)?s\b.*$", re.MULTILINE)
FAILURE_LINE = re.compile(
    r"^FAILED \([^)\n]*=\d+"                                  # unittest
    r"|^\s*--- FAIL: |^FAIL\s*$|^FAIL\t"                     # go test
    r"|^test result: FAILED\."                               # cargo test
    r"|^\s*Tests:?\s+.*\b[1-9]\d* failed\b"                  # Jest, Vitest
    r"|^\s*[1-9]\d* failing\b"                               # Mocha
    r"|^\d+ examples?, [1-9]\d* failures?\b"                 # RSpec
    r"|^\d+% tests passed, [1-9]\d* tests? failed\b"         # CTest
    r"|^Failed!\s+-\s+Failed:"                               # dotnet test
    r"|^(?:\[\w+\] )?BUILD FAIL(?:ED|URE)\b", re.MULTILINE)  # Gradle, Maven
SUCCESS_LINE = re.compile(
    r"^OK(?: \([^)\n]*\))?\s*$"                              # unittest
    r"|^ok\s+\S+\s+(?:\d+(?:\.\d+)?s|\(cached\))|^PASS\s*$"  # go test
    r"|^test result: ok\."                                   # cargo test
    r"|^\s*Tests:?\s+\d+ passed\b"                           # Jest, Vitest
    r"|^\s*\d+ passing\b"                                    # Mocha
    r"|^\d+ examples?, 0 failures\b"                         # RSpec
    r"|^100% tests passed\b"                                 # CTest
    r"|^Passed!\s+-\s+Failed:\s+0\b"                         # dotnet test
    r"|^(?:\[\w+\] )?BUILD SUCCESS(?:FUL)?\b", re.MULTILINE)  # Gradle, Maven
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
CELL_TOKEN = re.compile(r"`([^`\n]+)`|\[[^\]\n]*\]\(([^)\s]+)\)")
INLINE_DIGEST = re.compile(r"\bsha256\s*[:=]\s*`?([0-9a-fA-F]{64})\b")
INLINE_EXIT = re.compile(r"\bexit(?:[ _]code)?\s*[:=]?\s*`?(-?\d+)\b", re.IGNORECASE)
ONLY_DIGEST = re.compile(r"(?:sha256[:=]\s*)?[0-9a-fA-F]{64}\Z")
ONLY_EXIT = re.compile(r"exit(?:[ _]code)?\s*[:=]?\s*-?\d+\Z", re.IGNORECASE)
EMPTY_CELL = ("none", "n/a", "-", "\u2014")


class Refused(Exception):
    """The input cannot be judged; the script exits 2 with this reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class Arguments(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print usage and exit 2
        raise Refused("bad_arguments", message)


def confined_file(root: Path, value: str, label: str) -> Path:
    """Resolve a path below root, refusing '..', escapes through links and non-files."""
    if not isinstance(value, str) or not value or "\x00" in value:
        raise Refused("bad_path", f"{label} names an empty path")
    raw = Path(value)
    if ".." in raw.parts:
        raise Refused("path_outside_root", f"{label} path {value!r} uses '..'")
    candidate = raw if raw.is_absolute() else root / raw
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refused("input_missing", f"{label} file {value!r} does not exist") from None
    if not resolved.is_relative_to(root):
        raise Refused("path_outside_root", f"{label} path {value!r} resolves outside --root")
    if not resolved.is_file():
        raise Refused("not_a_file", f"{label} path {value!r} is not a regular file")
    return resolved


def read_bytes(root: Path, value: str, label: str) -> bytes:
    if value == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with open(confined_file(root, value, label), "rb") as handle:
            data = handle.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise Refused("input_too_large", f"{label} holds more than {MAX_INPUT_BYTES} bytes")
    return data


def normal_status(value) -> str:
    text = str(value).replace("\ufe0f", "").strip().lower()
    return re.sub(r"[\s-]+", "_", text)


def status_kind(value, extra_claims: set) -> tuple[str, str]:
    """Return the status word and whether it is a claim, not a claim, or unknown."""
    text = normal_status(value)
    tokens = TOKEN_WORDS.findall(text)
    for candidate in (text, tokens[0] if tokens else ""):
        if candidate in CLAIMS or candidate in extra_claims:
            return candidate, "claim"
        if candidate in NOT_CLAIMS:
            return candidate, "not_claim"
    return text, "unknown"


def first(mapping: dict, keys: tuple):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def first_int(mapping: dict, keys: tuple):
    for key in keys:
        if type(mapping.get(key)) is int:
            return mapping[key]
    return None


# ---------------------------------------------------------------------------
# reading the report
# ---------------------------------------------------------------------------

def citation(value, claim: str = "") -> dict:
    """One evidence citation: path, cited digest, cited exit code, stated expected exit code and claim text."""
    if isinstance(value, str):
        return {"path": value.strip(), "sha256": None, "exit_code": None, "expect_exit": None, "claim": claim}
    if isinstance(value, dict):
        path = first(value, ("path", "file", "evidence"))
        return {"path": str(path).strip() if isinstance(path, (str, int)) else "",
                "sha256": first(value, ("sha256", "digest")), "exit_code": first(value, EXIT_KEYS),
                "expect_exit": value.get("expect_exit"), "claim": str(value.get("text") or claim)}
    return {"path": "", "sha256": None, "exit_code": None, "expect_exit": None, "claim": claim}


def json_items(document) -> list:
    if isinstance(document, dict):
        document = next((document[key] for key in ITEM_LISTS if isinstance(document.get(key), list)), None)
    if not isinstance(document, list):
        raise Refused("no_claims_found", f"a JSON report is a list of items, an object with one of "
                                         f"{list(ITEM_LISTS)}, or a {NIGHT_REPORT} record")
    items = []
    for number, value in enumerate(document, 1):
        if not isinstance(value, dict):
            raise Refused("bad_report", f"item {number} is not a JSON object")
        identity = first(value, ID_KEYS)
        evidence = first(value, EVIDENCE_KEYS)
        evidence = evidence if isinstance(evidence, list) else [] if evidence is None else [evidence]
        items.append({"item": str(identity) if identity is not None else f"item {number}",
                      "status": first(value, STATUS_KEYS) or "",
                      "citations": [citation(entry) for entry in evidence],
                      "item_exit": first(value, EXIT_KEYS), "handoff": None})
    return items


def night_report_items(document: dict) -> list:
    """Read a night_morning_report/v1 record: each complete entry is one claim, the rest are not claims."""
    items = []
    for section in ("complete", "blocked", "unfinished"):
        entries = document.get(section)
        if not isinstance(entries, list):
            raise Refused("bad_report", f"a {NIGHT_REPORT} record holds a {section} list")
        for number, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                raise Refused("bad_report", f"{section} entry {number} is not a JSON object")
            ticket, step = entry.get("ticket_id"), entry.get("step_id")
            identity = f"{ticket}/{step}" if ticket and step else ticket or step or f"{section} {number}"
            claims = entry.get("claims") if isinstance(entry.get("claims"), list) else []
            cited = [citation(claim, str(claim.get("text") or "")) if isinstance(claim, dict) else citation(None)
                     for claim in claims]
            handoff = entry.get("handoff") if section == "complete" else None
            items.append({"item": str(identity), "status": section, "citations": cited, "item_exit": None,
                          "handoff": handoff if isinstance(handoff, str) and handoff.strip() else None})
    return items


def split_row(line: str) -> list:
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [cell.strip().replace("\\|", "|") for cell in cells]


def column(headers: list, words: tuple) -> int | None:
    """Index of the header that holds the earliest listed word; the order of words is a priority."""
    for word in words:
        for index, header in enumerate(headers):
            if any(part.startswith(word) for part in re.findall(r"[a-z0-9]+", header)):
                return index
    return None


def cell_citations(cell: str) -> list:
    """Evidence paths in one table cell: backticked paths or link targets, else the first word of each part."""
    found: list = []
    tokens = list(CELL_TOKEN.finditer(cell))
    if tokens:
        for position, match in enumerate(tokens):
            text = (match.group(1) or match.group(2)).strip()
            tail = cell[match.end():tokens[position + 1].start() if position + 1 < len(tokens) else len(cell)]
            if found and ONLY_DIGEST.match(text):
                found[-1]["sha256"] = found[-1]["sha256"] or text.split(":")[-1].split("=")[-1].strip()
                continue
            if found and ONLY_EXIT.match(text):
                found[-1]["exit_code"] = int(re.search(r"-?\d+\Z", text).group(0))
                continue
            entry = citation(text)
            digest, code = INLINE_DIGEST.search(tail), INLINE_EXIT.search(tail)
            entry["sha256"] = digest.group(1) if digest else None
            entry["exit_code"] = int(code.group(1)) if code else None
            found.append(entry)
        return found
    for piece in re.split(r"<br\s*/?>|[,;]", cell):
        words = piece.split()
        if words and words[0].lower() not in EMPTY_CELL:
            entry = citation(words[0])
            digest, code = INLINE_DIGEST.search(piece), INLINE_EXIT.search(piece)
            entry["sha256"] = digest.group(1) if digest else None
            entry["exit_code"] = int(code.group(1)) if code else None
            found.append(entry)
    return found


def markdown_items(text: str) -> list:
    lines = text.splitlines()
    items = []
    for index in range(len(lines) - 1):
        if "|" not in lines[index] or not TABLE_SEPARATOR.match(lines[index + 1]):
            continue
        headers = [header.lower() for header in split_row(lines[index])]
        status_at = column(headers, ("status", "outcome", "result", "state"))
        evidence_at = column(headers, ("evidence", "proof", "artifact", "file"))
        if status_at is None or evidence_at is None:
            continue
        id_at = column(headers, ("ticket", "item", "task", "key", "id"))
        digest_at = column(headers, ("sha256", "digest"))
        exit_at = column(headers, ("exit",))
        for row_number, line in enumerate(lines[index + 2:], 1):
            if "|" not in line or not line.strip():
                break
            cells = split_row(line)
            cells += [""] * (len(headers) - len(cells))
            cited = cell_citations(cells[evidence_at])
            if digest_at is not None and digest_at != evidence_at:
                for entry, digest in zip(cited, re.findall(r"[0-9a-fA-F]{64}", cells[digest_at])):
                    entry["sha256"] = entry["sha256"] or digest
            item_exit = None
            if exit_at is not None and re.fullmatch(r"-?\d+", cells[exit_at].strip("` ")):
                item_exit = int(cells[exit_at].strip("` "))
            identity = cells[id_at].strip("` ") if id_at is not None and cells[id_at].strip() else f"row {row_number}"
            items.append({"item": identity, "status": cells[status_at].strip("` *"), "citations": cited,
                          "item_exit": item_exit, "handoff": None})
    if not items:
        raise Refused("no_claims_found", "the Markdown report has no table with a status column and an evidence "
                                         "column; if the report also exists as JSON, check that file")
    return items


def load_report(text: str, value: str) -> tuple[list, dict | None, dict | None, str]:
    """Return the items, the report's own counts, the JSON document and the report form."""
    if value.lower().endswith(".json") or text.lstrip().startswith(("{", "[")):
        try:
            document = json.loads(text)
        except ValueError as error:
            raise Refused("bad_report", f"the report is not valid JSON: {error}") from None
        record_type = document.get("record_type") if isinstance(document, dict) else None
        if record_type == NIGHT_REPORT:
            items, form = night_report_items(document), "night_morning_report_v1"
        elif isinstance(record_type, str) and record_type.startswith("night_morning_report/"):
            raise Refused("unsupported_report_version", f"{record_type} is not {NIGHT_REPORT}")
        else:
            items, form = json_items(document), "json_items"
        counts = None
        if isinstance(document, dict):
            counts = document.get("counts")
            if counts is None and isinstance(document.get("summary"), dict):
                counts = document["summary"].get("counts")
        return items, counts if isinstance(counts, dict) else None, document, form
    return markdown_items(text), None, None, "markdown_table"


# ---------------------------------------------------------------------------
# what one evidence file shows
# ---------------------------------------------------------------------------

def record_outcome(document: dict) -> dict:
    """Read pass or fail from a JSON gate record. A stated verdict word outranks the record's own exit code.

    A ticket_reproduction_run/v1 record is read by its own rule: the verdict failing_test_recorded with a
    nonzero exit code shows a failure recorded on purpose ("reproduced"); any other verdict shows that the
    reproduction step did not reach its goal ("fail").
    """
    code = first_int(document, EXIT_KEYS)
    if document.get("record_type") == REPRODUCTION_RECORD:
        verdict = normal_status(document.get("verdict", ""))
        if verdict == "failing_test_recorded" and code not in (None, 0):
            return {"kind": "reproduction_record", "outcome": "reproduced",
                    "detail": f"a failing run of {str(document.get('test_name'))[:80]} was recorded, exit {code}",
                    "exit_code": code, "unknown_word": None}
        return {"kind": "reproduction_record", "outcome": "fail",
                "detail": f"the reproduction record says {verdict or 'nothing'} with exit {code}", "exit_code": code,
                "unknown_word": None}
    signals, unknown = [], None
    passed = document.get("passed")
    if isinstance(passed, bool):
        signals.append(("pass" if passed else "fail", f"passed {str(passed).lower()}"))
    failed_checks = document.get("failed_checks")
    if isinstance(failed_checks, list) and failed_checks:
        signals.append(("fail", f"failed_checks {failed_checks[:5]}"))
    checks = document.get("checks")
    if isinstance(checks, list) and checks and all(isinstance(check, dict) and isinstance(check.get("passed"), bool)
                                                   for check in checks):
        failing = sum(1 for check in checks if not check["passed"])
        signals.append(("fail" if failing else "pass", f"{len(checks) - failing} of {len(checks)} checks passed"))
    word_key = next((key for key in VERDICT_KEYS if isinstance(document.get(key), str) and document[key].strip()),
                    None)
    if word_key is not None:
        word = normal_status(document[word_key])
        if word in PASS_WORDS:
            signals.append(("pass", f"{word_key} {word}"))
        elif word in FAIL_WORDS:
            signals.append(("fail", f"{word_key} {word}"))
        else:
            unknown = f"{word_key} {word!r}"
    elif code is not None:
        signals.append(("pass" if code == 0 else "fail", f"exit code {code}"))
    outcomes = {outcome for outcome, _text in signals}
    outcome = "fail" if "fail" in outcomes else "pass" if "pass" in outcomes else "unknown"
    detail = ", ".join(text for result, text in signals if result == outcome)
    return {"kind": "json_record", "outcome": outcome, "detail": detail, "exit_code": code, "unknown_word": unknown}


def junit_outcome(text: str) -> tuple[str, str]:
    if re.search(r"<!(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
        return "unreadable", "JUnit XML with DOCTYPE or ENTITY declarations is not read"
    try:
        root = ElementTree.fromstring(text.encode("utf-8"))
    except ElementTree.ParseError as error:
        return "unreadable", f"the XML does not parse: {error}"
    cases = failed = skipped = 0
    for case in root.iter("testcase"):
        cases += 1
        tags = {nested.tag.lower() for nested in case if isinstance(nested.tag, str)}
        if tags & {"failure", "error"}:
            failed += 1
        elif "skipped" in tags:
            skipped += 1
    if failed:
        return "fail", f"{failed} of {cases} test cases failed or errored"
    if cases > skipped:
        return "pass", f"{cases - skipped} test cases passed, {skipped} skipped"
    return "unknown", ""


def text_outcome(text: str) -> tuple[str, str]:
    """Read the summary lines of a test or build log; a failure anywhere wins."""
    failures, passes = [], []
    for match in PYTEST_SUMMARY.finditer(text):
        counted = {word: int(number) for number, word in re.findall(r"(\d+) ([a-z]+)", match.group(1))}
        if counted.get("failed") or counted.get("error") or counted.get("errors"):
            failures.append(match.group(0).strip())
        elif counted.get("passed"):
            passes.append(match.group(0).strip())
    failure = FAILURE_LINE.search(text)
    if failure:
        failures.append(failure.group(0).strip())
    for line in text.splitlines():  # go test -json: one event per line; package events have no Test field
        if not line.startswith("{") or '"Action"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and "Test" not in event and event.get("Action") in ("pass", "fail"):
            (failures if event["Action"] == "fail" else passes).append(
                f"package {event.get('Package', '')} {event['Action']}")
    success = SUCCESS_LINE.search(text)
    if success:
        passes.append(success.group(0).strip())
    if failures:
        return "fail", failures[0][:160]
    if passes:
        return "pass", passes[0][:160]
    return "unknown", ""


def observe(data: bytes) -> dict:
    """Say what one evidence file shows: pass, fail, reproduced, unknown or unreadable."""
    text = data.decode("utf-8", "replace")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            document = json.loads(text)
        except ValueError:
            document = None
        if isinstance(document, dict):
            return record_outcome(document)
    if stripped.startswith("<") and "<testsuite" in text:
        outcome, detail = junit_outcome(text)
        return {"kind": "junit_xml", "outcome": outcome, "detail": detail, "exit_code": None, "unknown_word": None}
    outcome, detail = text_outcome(text)
    return {"kind": "text", "outcome": outcome, "detail": detail, "exit_code": None, "unknown_word": None}


def load_evidence(root: Path, path: str, cache: dict):
    """Read and observe one evidence file once; a refusal is cached like a result."""
    if path not in cache:
        if len(cache) >= MAX_EVIDENCE_FILES:
            raise Refused("too_many_evidence_files", f"the report cites more than {MAX_EVIDENCE_FILES} files")
        try:
            data = read_bytes(root, path, "evidence")
            cache[path] = (data, observe(data), None)
        except Refused as refusal:
            cache[path] = (None, None, refusal)
    data, seen, refusal = cache[path]
    if refusal is not None:
        raise refusal
    return data, seen


def refusal_problem(refusal: Refused) -> str:
    return {"input_missing": "evidence_missing", "path_outside_root": "evidence_path_unsafe",
            "bad_path": "evidence_path_unsafe"}.get(refusal.reason, refusal.reason)


# ---------------------------------------------------------------------------
# checking one claim
# ---------------------------------------------------------------------------

def check_citation(root: Path, entry: dict, item_exit, cache: dict, require_digests: bool) -> dict:
    """Check one cited evidence file; return its problems, its reasons to read the claim, and what it shows.

    The expectation of a citation is a pass or a failure when the report states expect_exit or an exit code,
    and none otherwise. A file that shows a failure against a stated pass is a problem; against no stated
    expectation it is a reason to read the claim, such as a run from before the fix.
    """
    problems, reading = [], []
    path = entry["path"]

    def note(target: list, code: str, detail: str) -> None:
        record = {"problem" if target is problems else "reason": code, "path": path, "detail": detail}
        if entry.get("claim"):
            record["claim"] = entry["claim"][:200]
        target.append(record)

    result = {"problems": problems, "reading": reading, "shows_pass": False, "unbound": False, "seen": None}
    expected = entry["expect_exit"]
    if not path:
        note(problems, "evidence_path_missing", "an evidence entry names no path")
        return result
    if expected is not None and type(expected) is not int:
        note(problems, "expect_exit_malformed", "expect_exit is a whole number")
        return result
    try:
        data, seen = load_evidence(root, path, cache)
    except Refused as refusal:
        if refusal.reason == "too_many_evidence_files":
            raise
        note(problems, refusal_problem(refusal), refusal.detail)
        return result
    result["seen"] = seen
    if entry["sha256"] is None:
        if require_digests:
            note(problems, "digest_not_cited", "without a digest the claim is not bound to these exact bytes")
        else:
            result["unbound"] = True
    else:
        match = HEX.match(str(entry["sha256"]).strip())
        if not match:
            note(problems, "digest_malformed", "sha256 is 64 hexadecimal characters")
        elif match.group(1).lower() != hashlib.sha256(data).hexdigest():
            note(problems, "digest_mismatch", "the file changed after the report cited it, or the report cites other bytes")
    cited = entry["exit_code"] if entry["exit_code"] is not None else item_exit
    if cited is not None and type(cited) is not int:
        note(problems, "exit_code_malformed", "an exit code is a whole number")
        cited = None
    contradicted = False
    if cited is not None:
        if seen["exit_code"] is not None and seen["exit_code"] != cited:
            note(problems, "exit_code_contradicted", f"the report cites exit {cited}; the file records exit "
                                                     f"{seen['exit_code']}")
            contradicted = True
        elif seen["exit_code"] is None and ((cited == 0 and seen["outcome"] in ("fail", "reproduced"))
                                            or (cited != 0 and seen["outcome"] == "pass")):
            note(problems, "exit_code_contradicted", f"the report cites exit {cited}; the file shows: {seen['detail']}")
            contradicted = True
        if expected is not None and cited != expected:
            note(problems, "exit_code_failed" if expected == 0 else "expected_failure_not_shown",
                 f"the report cites exit {cited}; this citation expects exit {expected}")
    effective = ("pass" if expected == 0 else "fail") if expected is not None else \
        ("pass" if cited == 0 else "fail") if cited is not None else None
    outcome = seen["outcome"]
    if outcome == "unreadable":
        note(problems, "evidence_unreadable", seen["detail"])
    elif not contradicted:
        if effective == "pass" and outcome in ("fail", "reproduced"):
            note(problems, "evidence_shows_failure", seen["detail"])
        elif effective == "fail" and outcome == "pass":
            note(problems, "expected_failure_not_shown", f"the citation expects a failing run; the file shows: "
                                                         f"{seen['detail']}")
        elif effective is None and outcome == "fail":
            note(reading, "evidence_shows_failure", f"the file shows a failing run ({seen['detail']}); read the "
                                                    "claim: it must describe that failure, such as a run before the fix")
    result["shows_pass"] = outcome == "pass" and effective in (None, "pass") and not problems
    return result


def check_handoff(root: Path, path: str, cache: dict) -> tuple[list, list]:
    """Check the step handoff a complete night report entry cites: it exists, says complete, and every file it
    lists still has the digest it recorded (a null digest means the step deleted the file)."""
    problems, reading = [], []
    try:
        data, _seen = load_evidence(root, path, cache)
    except Refused as refusal:
        if refusal.reason == "too_many_evidence_files":
            raise
        problems.append({"problem": "handoff_" + refusal_problem(refusal).replace("evidence_", ""), "path": path,
                         "detail": refusal.detail})
        return problems, reading
    try:
        handoff = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        problems.append({"problem": "handoff_unreadable", "path": path, "detail": "the handoff is not JSON"})
        return problems, reading
    return compare_handoff(root, path, handoff, cache)


def compare_handoff(root: Path, path: str, handoff, cache: dict) -> tuple[list, list]:
    """Compare one parsed handoff with the workspace: its status, and the digest of every file it lists."""
    problems, reading = [], []
    if not isinstance(handoff, dict) or handoff.get("record_type") != HANDOFF:
        reading.append({"reason": "handoff_not_checked", "path": path,
                        "detail": f"the handoff is not a {HANDOFF} record, so its files were not compared"})
        return problems, reading
    if handoff.get("status") != "complete":
        problems.append({"problem": "handoff_status_differs", "path": path,
                         "detail": f"the report lists the step as complete; its handoff says {handoff.get('status')!r}"})
    files = handoff.get("files") if isinstance(handoff.get("files"), list) else []
    for entry in files[:MAX_EVIDENCE_FILES]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        listed, digest = entry["path"], entry.get("sha256")
        try:
            current = hashlib.sha256(load_evidence(root, listed, cache)[0]).hexdigest()
        except Refused as refusal:
            if refusal.reason == "too_many_evidence_files":
                raise
            current = None if refusal.reason == "input_missing" else refusal.reason
        if digest is None and current is None:
            continue
        if digest is not None and current == str(digest).lower():
            continue
        found = "missing" if current is None else "unsafe" if len(str(current)) != 64 else f"sha256 {current[:12]}"
        wanted = "deleted" if digest is None else f"sha256 {str(digest)[:12]}"
        reading.append({"reason": "changed_since_handoff", "path": listed,
                        "detail": f"the handoff {path} recorded it as {wanted}; it is now {found}, so the evidence "
                                  "was made for other bytes"})
    return problems, reading


def count_problems(counts: dict, document, items: list) -> tuple[list, list]:
    """Compare every whole-number count the report states with its lists or its item statuses."""
    problems, warnings = [], []
    statuses: dict = {}
    for item in items:
        word = normal_status(item["status"])
        statuses[word] = statuses.get(word, 0) + 1
    for key, value in counts.items():
        if type(value) is not int:
            warnings.append(f"counts.{key} is not a whole number, so it was not compared")
            continue
        prefix, _joint, status = key.partition("_")
        if isinstance(document, dict) and isinstance(document.get(key), list):
            real = len(document[key])
        elif isinstance(document, dict) and status and isinstance(document.get(prefix), list):
            # such as tickets_complete: the entries of the tickets list whose status is complete
            real = sum(1 for entry in document[prefix] if isinstance(entry, dict) and entry.get("status") == status)
        elif normal_status(key) in ("total", "items", "all"):
            real = len(items)
        else:
            real = statuses.get(normal_status(key), 0)
        if value != real:
            problems.append({"problem": "count_mismatch", "detail": f"the report counts {key} as {value}; "
                                                                    f"its entries give {real}"})
    return problems, warnings


def ticket_problems(document) -> list:
    """A night report that lists tickets must back every complete ticket with a complete entry of its final step."""
    tickets = document.get("tickets") if isinstance(document, dict) else None
    if not isinstance(tickets, list):
        return []
    complete_steps = {entry.get("step_id") for entry in document.get("complete", []) if isinstance(entry, dict)}
    problems = []
    for ticket in tickets:
        if not isinstance(ticket, dict) or ticket.get("status") != "complete":
            continue
        final = ticket.get("final_step_id")
        if final not in complete_steps:
            problems.append({"problem": "ticket_final_step_not_complete",
                             "detail": f"{ticket.get('ticket_id')} is listed as complete, but its final step "
                                       f"{final!r} is not among the complete entries"})
    return problems


def note_warnings(root: Path, document, cache: dict) -> list:
    """A night report's notes cite files too; a note whose file is missing is a warning."""
    warnings = []
    notes = document.get("notes") if isinstance(document, dict) else None
    for number, note in enumerate(notes if isinstance(notes, list) else [], 1):
        path = note.get("evidence") if isinstance(note, dict) else None
        if not isinstance(path, str) or not path.strip():
            warnings.append(f"note {number} cites no file")
            continue
        try:
            load_evidence(root, path, cache)
        except Refused as refusal:
            if refusal.reason == "too_many_evidence_files":
                raise
            warnings.append(f"note {number} cites {path}, which is {refusal_problem(refusal).replace('_', ' ')}")
    return warnings


def evaluate(args) -> dict:
    root = Path(args.root)
    if not root.is_dir():
        raise Refused("root_missing", f"--root {args.root!r} is not a folder")
    root = root.resolve()
    extra_claims = {normal_status(word) for word in args.claim_word if word.strip()}
    data = read_bytes(root, args.report, "--report")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused("input_not_utf8", f"--report is not UTF-8 text (byte {error.start})") from None
    items, claimed_counts, document, form = load_report(text, args.report)
    if not items:
        raise Refused("no_claims_found", "the report holds no items")
    if len(items) > MAX_ITEMS:
        raise Refused("bad_report", f"more than {MAX_ITEMS} items")
    supported, unsupported, needs_reading, unbound, not_claims, warnings, cache = [], [], [], [], [], [], {}
    evidence_rows = []
    seen_ids: dict = {}
    warned_records: set = set()
    for item in items:
        seen_ids[item["item"]] = seen_ids.get(item["item"], 0) + 1
        word, kind = status_kind(item["status"], extra_claims)
        if kind != "claim":
            if kind == "unknown":
                warnings.append(f"{item['item']}: status {word!r} is not a known word, so it was not checked; "
                                f"if it means complete, run again with --claim-word {word}")
            not_claims.append({"item": item["item"], "status": word})
            continue
        problems, reading, passing, unbound_paths = [], [], False, []
        if not item["citations"]:
            problems.append({"problem": "no_evidence", "path": "", "detail": "the item claims completion and "
                                                                             "cites nothing"})
        for entry in item["citations"]:
            checked = check_citation(root, entry, item["item_exit"], cache, args.require_digests)
            problems += checked["problems"]
            reading += checked["reading"]
            passing = passing or checked["shows_pass"]
            if checked["unbound"]:
                unbound_paths.append(entry["path"])
            seen = checked["seen"]
            evidence_rows.append({"item": item["item"], "path": entry["path"],
                                  "shows": seen["outcome"] if seen else "not read",
                                  "detail": (seen["detail"] if seen else "")[:160], "claim": entry["claim"][:200]})
            if seen and seen["unknown_word"] and entry["path"] not in warned_records:
                warned_records.add(entry["path"])
                warnings.append(f"{entry['path']}: the record states {seen['unknown_word']}, which is not a known "
                                "pass or fail word; read the file")
        if item.get("handoff"):
            handoff_problems, handoff_reading = check_handoff(root, item["handoff"], cache)
            problems += handoff_problems
            reading += handoff_reading
        if item["citations"] and not passing:
            # the failures seen are part of why nothing shows a pass
            problems += [{"problem": entry.pop("reason"), **entry} for entry in reading]
            reading = []
            problems.append({"problem": "no_passing_gate_evidence", "path": "",
                             "detail": "no cited file without a problem shows a passing gate; cite a gate record, "
                                       "a JUnit XML report or a test log"})
        if word == "verified_by_test_change":
            reading.append({"reason": "only_tests_changed", "path": "",
                            "detail": "the gate passed after only test files changed; read the diff before this "
                                      "counts as a fix"})
        if unbound_paths:
            unbound.append({"item": item["item"], "paths": unbound_paths[:20]})
        if problems:
            unsupported.append({"item": item["item"], "status": word, "problems": problems[:20]})
        elif reading:
            needs_reading.append({"item": item["item"], "status": word, "reasons": reading[:20]})
        else:
            supported.append(item["item"])
    for identity, number in seen_ids.items():
        if number > 1:
            warnings.append(f"{identity}: appears {number} times in the report")
    report_problems = []
    if claimed_counts is not None:
        report_problems, count_warnings = count_problems(claimed_counts, document, items)
        warnings += count_warnings
    if form == "night_morning_report_v1":
        warnings += note_warnings(root, document, cache)
        report_problems += ticket_problems(document)
    verdict = "fail" if unsupported or report_problems else "review" if needs_reading else "pass"
    return {
        "tool": TOOL, "version": VERSION, "verdict": verdict,
        "unsupported": unsupported[:LIST_LIMIT], "needs_reading": needs_reading[:LIST_LIMIT],
        "supported": supported[:LIST_LIMIT], "unbound": unbound[:LIST_LIMIT],
        "not_claims": not_claims[:LIST_LIMIT], "report_problems": report_problems[:LIST_LIMIT],
        "warnings": warnings[:LIST_LIMIT], "evidence": evidence_rows[:LIST_LIMIT],
        "counts": {"items": len(items), "claims": len(supported) + len(unsupported) + len(needs_reading),
                   "supported": len(supported), "unsupported": len(unsupported),
                   "needs_reading": len(needs_reading), "unbound": len(unbound), "files_read": len(cache)},
        "format": form, "require_digests": bool(args.require_digests),
        "input": {"path": "standard input" if args.report == "-" else args.report, "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest()},
    }


def main(argv=None) -> int:
    parser = Arguments(prog="verify_report_claims.py", description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, help="the morning report, JSON or Markdown, or - for standard input")
    parser.add_argument("--root", default=".", help="folder the evidence paths are relative to (default: current folder)")
    parser.add_argument("--require-digests", action="store_true",
                        help="count a citation without a SHA-256 digest as a problem")
    parser.add_argument("--claim-word", action="append", default=[],
                        help="another status word that means complete; repeat for more")
    try:
        result = evaluate(parser.parse_args(argv))
    except Refused as refusal:
        print(json.dumps({"tool": TOOL, "version": VERSION, "verdict": "refused", "reason": refusal.reason,
                          "detail": refusal.detail}, indent=1))
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

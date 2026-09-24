"""Match every acceptance criterion of a ticket checklist to evidence that holds up; reads the named files only.

Effects: reads the criteria file, the evidence file and every file an evidence entry
cites, all below --root (the criteria or the evidence may be "-" for standard input).
Writes nothing, starts no process and uses no network. Prints one JSON object.
Exit status: 0 pass, 1 fail, 2 refused input.

Criteria: a Markdown checklist (list items under a heading that names acceptance,
criteria or done, else every checkbox item) or JSON. Evidence: JSON entries, each
naming the criteria it supports and one of three kinds: a test that passed in a
saved test output, a command with its recorded exit code, or a file that exists.
A ticked box is never evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

TOOL = "verify-criteria-have-evidence"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_CRITERIA = 500
MAX_ENTRIES = 2000
LIST_LIMIT = 200
KINDS = ("test", "command", "file")
FAILING = ("failed", "error")
RANK = {"skipped": 0, "xfailed": 1, "passed": 2, "xpassed": 3, "error": 4, "failed": 5}
DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{64})\Z")


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


def as_text(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused("input_not_utf8", f"{label} is not UTF-8 text (byte {error.start})") from None


def info(value: str, data: bytes) -> dict:
    return {"path": "standard input" if value == "-" else value, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+[.)])\s+(?:\[(?P<box>[ xX])\]\s+)?(?P<text>\S.*)$")
SECTION = re.compile(r"acceptance|criteria|\bdone\b", re.IGNORECASE)
ID_FIRST = re.compile(r"^(?P<id>[A-Za-z][A-Za-z0-9]*[-_.]?\d+[a-z]?)\s*[:.)-]\s+(?P<rest>\S.*)$")
ID_BRACKETED = re.compile(r"^\[(?P<id>[A-Za-z][A-Za-z0-9]*[-_.]?\d+[a-z]?)\]\s+(?P<rest>\S.*)$")


def markdown_criteria(text: str) -> list:
    lines = text.splitlines()
    chosen, level = None, 0
    for number, line in enumerate(lines):
        heading = HEADING.match(line)
        if heading and SECTION.search(heading.group(2)):
            chosen, level = number, len(heading.group(1))
            break
    items = []
    if chosen is not None:
        for line in lines[chosen + 1:]:
            heading = HEADING.match(line)
            if heading and len(heading.group(1)) <= level:
                break
            item = LIST_ITEM.match(line)
            if item:
                items.append(item)
    else:
        items = [item for item in map(LIST_ITEM.match, lines) if item and item.group("box") is not None]
    if not items:
        return []
    shallow = min(len(item.group("indent").expandtabs(4)) for item in items)
    criteria = []
    for item in items:
        if len(item.group("indent").expandtabs(4)) != shallow:
            continue  # a nested item explains its parent criterion
        text = item.group("text").strip()
        named = ID_BRACKETED.match(text) or ID_FIRST.match(text)
        criteria.append({"id": named.group("id") if named else None, "text": named.group("rest") if named else text,
                         "ticked": (item.group("box") or " ").lower() == "x"})
    return criteria


def json_criteria(document) -> list:
    if isinstance(document, dict):
        document = document.get("criteria", document.get("acceptance_criteria"))
    if not isinstance(document, list):
        raise Refused("bad_criteria", "JSON criteria are a list, or an object with a criteria list")
    criteria = []
    for value in document:
        if isinstance(value, str):
            criteria.append({"id": None, "text": value.strip(), "ticked": False})
        elif isinstance(value, dict):
            text = next((value[key] for key in ("text", "criterion", "description", "title")
                         if isinstance(value.get(key), str)), "")
            identity = value.get("id", value.get("key"))
            criteria.append({"id": str(identity) if identity is not None else None, "text": text.strip(),
                             "ticked": value.get("done") is True})
        else:
            raise Refused("bad_criteria", "each criterion is a string or an object with id and text")
    return criteria


def load_criteria(text: str, value: str) -> list:
    stripped = text.lstrip()
    if value.lower().endswith(".json") or stripped.startswith(("[", "{")):
        try:
            criteria = json_criteria(json.loads(text))
        except ValueError as error:
            raise Refused("bad_criteria", f"the criteria are not valid JSON: {error}") from None
    else:
        criteria = markdown_criteria(text)
    criteria = [criterion for criterion in criteria if criterion["text"] or criterion["id"]]
    if not criteria:
        raise Refused("no_criteria_found", "no criteria were found; use a list under an 'Acceptance criteria' "
                                           "heading, checkbox items or JSON")
    if len(criteria) > MAX_CRITERIA:
        raise Refused("bad_criteria", f"more than {MAX_CRITERIA} criteria")
    for number, criterion in enumerate(criteria, 1):
        if not criterion["id"]:
            criterion["id"] = f"C{number}"
    identities = [criterion["id"] for criterion in criteria]
    repeated = sorted({identity for identity in identities if identities.count(identity) > 1})
    if repeated:
        raise Refused("duplicate_criterion_id", f"criterion ids repeat: {repeated[:10]}")
    return criteria


# ---------------------------------------------------------------------------
# saved test outputs
# ---------------------------------------------------------------------------

def record(results: dict, test_id: str, outcome: str) -> None:
    previous = results.get(test_id)
    if previous is None or RANK[outcome] > RANK[previous]:
        results[test_id] = outcome


PYTEST_WORD = r"(?P<word>(?:SUB)?(?:PASSED|FAILED|SKIPPED)|ERROR|XFAIL|XPASS)(?:\([^)\n]*\))?"
PYTEST_ID = r"(?P<id>[^\s\[]+::[^\s\[]+(?:\[.*?\])?)"
PYTEST_WORDS = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "SKIPPED": "skipped",
                "XFAIL": "xfailed", "XPASS": "xpassed", "SUBPASSED": "passed", "SUBFAILED": "failed",
                "SUBSKIPPED": "skipped"}
PYTEST_ID_FIRST = re.compile(r"^" + PYTEST_ID + r"\s+" + PYTEST_WORD + r"(?:\s+\(.*?\))?(?:\s+\[\s*\d+%\])?\s*$")
PYTEST_WORD_FIRST = re.compile(r"^(?:\[gw\d+\]\s+\[\s*\d+%\]\s+)?" + PYTEST_WORD + r"\s+" + PYTEST_ID
                               + r"(?=\s+-\s|\s*$)")
UT_HEAD = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*) \((?P<where>[A-Za-z_][\w.]*)\)(?: \([^)]*\))?"
                     r"(?: \.\.\.(?: (?P<rest>.*))?)?$")
UT_DOC = re.compile(r"^.* \.\.\. (?P<rest>.*)$")
UT_SUMMARY = re.compile(r"^(?P<word>FAIL|ERROR|UNEXPECTED SUCCESS): (?P<name>[A-Za-z_]\w*) "
                        r"\((?P<where>[A-Za-z_][\w.]*)\)")
UT_SUMMARY_WORDS = {"FAIL": "failed", "ERROR": "error", "UNEXPECTED SUCCESS": "xpassed"}
GO_LINE = re.compile(r"^\s*--- (?P<word>PASS|FAIL|SKIP): (?P<id>\S+)")
GO_WORDS = {"PASS": "passed", "FAIL": "failed", "SKIP": "skipped", "pass": "passed", "fail": "failed",
            "skip": "skipped"}
CARGO_LINE = re.compile(r"^test (?P<id>\S(?:.*?\S)?) \.\.\. (?P<word>ok|FAILED|ignored)\b")
CARGO_WORDS = {"ok": "passed", "FAILED": "failed", "ignored": "skipped"}


def parse_pytest(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        match = PYTEST_ID_FIRST.match(line.rstrip()) or PYTEST_WORD_FIRST.match(line.rstrip())
        if match:
            record(results, match.group("id"), PYTEST_WORDS[match.group("word")])
    return results


def unittest_id(name: str, where: str) -> str:
    return where if where == name or where.endswith("." + name) else f"{where}.{name}"


def unittest_outcome(rest: str | None) -> str | None:
    rest = (rest or "").strip()
    if rest.startswith("skipped"):
        return "skipped"
    return {"ok": "passed", "FAIL": "failed", "ERROR": "error", "expected failure": "xfailed",
            "unexpected success": "xpassed"}.get(rest)


def parse_unittest(text: str) -> dict:
    results: dict = {}
    pending = None
    for line in text.splitlines():
        line = line.rstrip()
        summary = UT_SUMMARY.match(line)
        if summary:
            record(results, unittest_id(summary["name"], summary["where"]), UT_SUMMARY_WORDS[summary["word"]])
            pending = None
            continue
        segment, matched = line, False
        while True:  # Python 3.10 can print the next test on the line of a test whose subtest failed
            head = UT_HEAD.match(segment)
            if not head:
                break
            matched = True
            test_id = unittest_id(head["name"], head["where"])
            outcome = unittest_outcome(head["rest"])
            if outcome:
                record(results, test_id, outcome)
                pending = None
                break
            pending = test_id
            if not head["rest"]:
                break
            segment = head["rest"]
        if matched or not pending:
            continue
        doc = UT_DOC.match(line)
        outcome = unittest_outcome(doc["rest"] if doc else line)
        if outcome:
            record(results, pending, outcome)
            pending = None
    return results


def parse_go(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        match = GO_LINE.match(line)
        if match:
            record(results, match["id"], GO_WORDS[match["word"]])
        elif line.startswith("{") and '"Action"' in line:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and isinstance(event.get("Test"), str) and event.get("Action") in GO_WORDS:
                record(results, event["Test"], GO_WORDS[event["Action"]])
    return results


def parse_cargo(text: str) -> dict:
    results: dict = {}
    for line in text.splitlines():
        match = CARGO_LINE.match(line.rstrip())
        if match:
            record(results, match["id"], CARGO_WORDS[match["word"]])
    return results


def parse_junit(text: str) -> dict:
    if not text.lstrip().startswith("<"):
        return {}
    if re.search(r"<!(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
        raise Refused("xml_declaration_refused", "JUnit XML with DOCTYPE or ENTITY declarations is refused")
    try:
        root = ElementTree.fromstring(text.encode("utf-8"))
    except ElementTree.ParseError as error:
        raise Refused("xml_unreadable", f"the XML does not parse: {error}") from None
    results: dict = {}
    for case in root.iter("testcase"):
        name = case.get("name") or ""
        if not name:
            continue
        classname = case.get("classname") or ""
        outcome = "passed"
        for nested in case:
            tag = nested.tag.lower() if isinstance(nested.tag, str) else ""
            if tag == "failure":
                outcome = "failed"
            elif tag == "error" and outcome != "failed":
                outcome = "error"
            elif tag == "skipped" and outcome == "passed":
                outcome = "xfailed" if nested.get("type") == "pytest.xfail" else "skipped"
        record(results, f"{classname}.{name}" if classname else name, outcome)
    return results


PARSERS = {"pytest": parse_pytest, "unittest": parse_unittest, "go": parse_go, "cargo": parse_cargo,
           "junit": parse_junit}


def parse_output(text: str, chosen: str) -> tuple[str, dict]:
    if chosen != "auto":
        return chosen, PARSERS[chosen](text)
    if text.lstrip().startswith("<"):
        results = parse_junit(text)
        if results:
            return "junit", results
    best_name, best = "", {}
    for name in ("pytest", "unittest", "go", "cargo"):
        results = PARSERS[name](text)
        if len(results) > len(best):
            best_name, best = name, results
    return best_name, best


#: Summary lines of common runners in a saved command output. A failure line anywhere wins over a pass line.
FAILURE_SUMMARY = re.compile(
    r"^=*\s*(?:\d+ [a-z]+, )*\d+ (?:failed|errors?)\b.* in \d+(?:\.\d+)?s\b"   # pytest
    r"|^FAILED \((?:failures|errors)=\d+"                                      # unittest
    r"|^\s*--- FAIL: |^FAIL\s*$|^FAIL\t"                                       # go test
    r"|^test result: FAILED\."                                                  # cargo test
    r"|^\s*Tests:?\s+.*\b[1-9]\d* failed\b"                                    # Jest, Vitest
    r"|^(?:\[\w+\] )?BUILD FAIL(?:ED|URE)\b", re.MULTILINE)                     # Gradle, Maven
PASS_SUMMARY = re.compile(
    r"^=*\s*(?:\d+ [a-z]+, )*\d+ passed\b.* in \d+(?:\.\d+)?s\b"             # pytest
    r"|^OK(?: \([^)\n]*\))?\s*$"                                                # unittest
    r"|^ok\s+\S+\s+(?:\d+(?:\.\d+)?s|\(cached\))|^PASS\s*$"                     # go test
    r"|^test result: ok\."                                                      # cargo test
    r"|^\s*Tests:?\s+\d+ passed\b"                                               # Jest, Vitest
    r"|^(?:\[\w+\] )?BUILD SUCCESS(?:FUL)?\b", re.MULTILINE)                     # Gradle, Maven
EXIT_KEYS = ("exit_code", "returncode", "exit_status")


def observe_output(data: bytes) -> dict:
    """Say what a saved command output shows by itself: pass, fail or unknown, and any exit code it records."""
    text = data.decode("utf-8", "replace")
    if text.lstrip().startswith("{"):
        try:
            document = json.loads(text)
        except ValueError:
            document = None
        if isinstance(document, dict):
            code = next((document[key] for key in EXIT_KEYS if type(document.get(key)) is int), None)
            passed = document.get("passed")
            if isinstance(passed, bool):
                return {"outcome": "pass" if passed else "fail", "detail": f"passed {str(passed).lower()}",
                        "exit_code": code}
            if code is not None:
                return {"outcome": "pass" if code == 0 else "fail", "detail": f"exit code {code}", "exit_code": code}
            return {"outcome": "unknown", "detail": "a JSON record without an exit code or passed flag",
                    "exit_code": None}
    if text.lstrip().startswith("<") and "<testcase" in text:
        try:
            results = parse_junit(text)
        except Refused as refusal:
            return {"outcome": "unknown", "detail": refusal.detail, "exit_code": None}
        failing = sorted(test_id for test_id, outcome in results.items() if outcome in FAILING)
        if failing:
            return {"outcome": "fail", "detail": f"{len(failing)} test cases failed, such as {failing[0]}",
                    "exit_code": None}
        if any(outcome == "passed" for outcome in results.values()):
            return {"outcome": "pass", "detail": f"{len(results)} test cases, none failed", "exit_code": None}
        return {"outcome": "unknown", "detail": "no test case passed or failed", "exit_code": None}
    failure = FAILURE_SUMMARY.search(text)
    if failure:
        return {"outcome": "fail", "detail": failure.group(0).strip()[:160], "exit_code": None}
    success = PASS_SUMMARY.search(text)
    if success:
        return {"outcome": "pass", "detail": success.group(0).strip()[:160], "exit_code": None}
    return {"outcome": "unknown", "detail": "no pass or fail summary line was found", "exit_code": None}


def strip_parameters(test_id: str) -> str:
    if not test_id.endswith("]"):
        return test_id
    depth = 0
    for index in range(len(test_id) - 1, -1, -1):
        if test_id[index] == "]":
            depth += 1
        elif test_id[index] == "[":
            depth -= 1
            if depth == 0:
                return test_id[:index] if index > 0 else test_id
    return test_id


def base_name(test_id: str, runner: str) -> str:
    core = strip_parameters(test_id)
    if "::" in core:
        return core.rsplit("::", 1)[1]
    if runner == "go":
        return core.split("/", 1)[0]
    if "." in core and " " not in core:
        return core.rsplit(".", 1)[1]
    return core


def match_test(requested: str, results: dict, runner: str) -> list:
    """Return the result ids of one requested test; refuse an id that names two different tests."""
    if requested in results:
        return [requested]
    with_parameters = strip_parameters(requested) != requested
    requested_base = base_name(requested, runner)
    stages = (
        [] if with_parameters else [test_id for test_id in results if strip_parameters(test_id) == requested],
        [test_id for test_id in results
         if any((test_id if with_parameters else strip_parameters(test_id)).endswith(separator + requested)
                for separator in ("::", ".", "/"))],
        [test_id for test_id in results if not with_parameters and base_name(test_id, runner) == requested_base],
    )
    for candidates in stages:
        if candidates:
            cores = sorted({strip_parameters(test_id) for test_id in candidates})
            if len(cores) > 1:
                raise Refused("ambiguous_test_id", f"{requested!r} matches several tests: {cores[:5]}")
            return sorted(candidates)
    return []


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------

def load_evidence(text: str) -> list:
    try:
        document = json.loads(text)
    except ValueError as error:
        raise Refused("bad_evidence", f"the evidence is not valid JSON: {error}") from None
    if isinstance(document, dict):
        document = document.get("evidence")
    if not isinstance(document, list):
        raise Refused("bad_evidence", "the evidence is a JSON list, or an object with an evidence list")
    if len(document) > MAX_ENTRIES:
        raise Refused("bad_evidence", f"more than {MAX_ENTRIES} evidence entries")
    return document


def named_criteria(entry: dict) -> list:
    value = entry.get("criteria", entry.get("criterion"))
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return [str(item).strip() for item in values if isinstance(item, (str, int)) and str(item).strip()]


def judge_entry(entry, root: Path, chosen_format: str, outputs: dict) -> tuple[str, str, str]:
    """Return (state, problem, detail); state is valid, contradicts or invalid."""
    if not isinstance(entry, dict):
        return "invalid", "not_an_object", "an evidence entry is a JSON object"
    kind = entry.get("kind")
    if kind not in KINDS:
        return "invalid", "unknown_kind", f"kind is one of {list(KINDS)}; a note or a ticked box is not evidence"
    try:
        if kind == "test":
            test, output = entry.get("test"), entry.get("output")
            if not isinstance(test, str) or not test.strip() or not isinstance(output, str):
                return "invalid", "missing_field", "a test entry names test and output"
            if output not in outputs:
                data = read_bytes(root, output, "output")
                outputs[output] = parse_output(as_text(data, output), chosen_format)
            runner, results = outputs[output]
            ids = match_test(test.strip(), results, runner)
            if not ids:
                return "invalid", "test_not_found", f"{test} has no result in {output}"
            outcomes = sorted({results[test_id] for test_id in ids})
            if any(outcome in FAILING for outcome in outcomes):
                return "contradicts", "test_failed", f"{test} in {output}: {', '.join(outcomes)}"
            if outcomes != ["passed"]:
                return "invalid", "test_not_passed", f"{test} in {output}: {', '.join(outcomes)}"
            return "valid", "", f"{test} passed in {output}"
        if kind == "command":
            command, code, expected = entry.get("command"), entry.get("exit_code"), entry.get("expect_exit", 0)
            if not isinstance(command, str) or not command.strip() or type(code) is not int or type(expected) is not int:
                return "invalid", "missing_field", "a command entry names command and an integer exit_code"
            output = entry.get("output")
            if not isinstance(output, str) or not output.strip():
                return "invalid", "output_not_cited", ("a command entry cites the saved output of its run in output; "
                                                       "an exit code typed into the evidence is not evidence")
            problem = check_file(root, output, entry.get("sha256"), None)
            if problem:
                return "invalid", problem[0], problem[1]
            seen = observe_output(read_bytes(root, output, "output"))
            if seen["exit_code"] is not None and seen["exit_code"] != code:
                return "contradicts", "exit_code_contradicted", (f"the entry says {command!r} exited {code}; "
                                                                 f"{output} records exit {seen['exit_code']}")
            if code == 0 and seen["outcome"] == "fail":
                return "contradicts", "output_shows_failure", (f"the entry says {command!r} exited 0; {output} "
                                                               f"shows: {seen['detail']}")
            if code != 0 and seen["outcome"] == "pass" and seen["exit_code"] is None:
                return "contradicts", "output_shows_pass", (f"the entry says {command!r} exited {code}; {output} "
                                                            f"shows: {seen['detail']}")
            if code != expected:
                return "contradicts", "exit_code", f"{command!r} exited {code}, expected {expected}"
            if seen["outcome"] == "unknown":
                return "valid", "", f"{command!r} exited {code}; {output} shows no summary: {seen['detail']}"
            return "valid", "", f"{command!r} exited {code}; {output} shows: {seen['detail']}"
        problem = check_file(root, entry.get("path"), entry.get("sha256"), entry.get("contains"))
        if problem:
            return "invalid", problem[0], problem[1]
        return "valid", "", f"{entry.get('path')} exists" + (" and matches its digest" if entry.get("sha256") else "")
    except Refused as refusal:
        return "invalid", ("file_missing" if refusal.reason == "input_missing" else refusal.reason), refusal.detail


def check_file(root: Path, path, digest, contains) -> tuple | None:
    if not isinstance(path, str) or not path.strip():
        return "missing_field", "a file entry names path"
    try:
        data = read_bytes(root, path, "evidence file")
    except Refused as refusal:
        return ("file_missing" if refusal.reason == "input_missing" else refusal.reason), refusal.detail
    if digest is not None:
        match = DIGEST.match(str(digest).strip().lower())
        if not match:
            return "bad_digest", f"{path}: sha256 must be 64 hexadecimal characters"
        if hashlib.sha256(data).hexdigest() != match.group(1):
            return "digest_mismatch", f"{path}: the bytes differ from the cited sha256"
    if contains is not None:
        if not isinstance(contains, str) or contains not in data.decode("utf-8", "replace"):
            return "text_not_found", f"{path} does not contain {contains!r}"
    return None


def evaluate(args) -> dict:
    root = Path(args.root)
    if not root.is_dir():
        raise Refused("root_missing", f"--root {args.root!r} is not a folder")
    root = root.resolve()
    if [args.criteria, args.evidence].count("-") > 1:
        raise Refused("bad_arguments", "only one input may come from standard input")
    criteria_bytes = read_bytes(root, args.criteria, "--criteria")
    evidence_bytes = read_bytes(root, args.evidence, "--evidence")
    criteria = load_criteria(as_text(criteria_bytes, "--criteria"), args.criteria)
    entries = load_evidence(as_text(evidence_bytes, "--evidence"))
    known = {criterion["id"] for criterion in criteria}
    supporting = {identity: [] for identity in known}
    against = {identity: [] for identity in known}
    problems, unknown, outputs = [], [], {}
    for number, entry in enumerate(entries):
        names = named_criteria(entry) if isinstance(entry, dict) else []
        state, problem, detail = judge_entry(entry, root, args.format, outputs)
        if not names:
            problems.append({"entry": number, "problem": "no_criterion_named", "detail": "name criteria or criterion"})
        for name in names:
            if name not in known:
                unknown.append({"entry": number, "criterion": name})
            elif state == "valid":
                supporting[name].append(number)
            elif state == "contradicts":
                against[name].append(number)
        if state != "valid":
            problems.append({"entry": number, "problem": problem, "detail": detail, "state": state})
    rows = []
    for criterion in criteria:
        identity = criterion["id"]
        status = "contradicted" if against[identity] else "covered" if supporting[identity] else "uncovered"
        rows.append({"id": identity, "text": criterion["text"][:300], "status": status,
                     "evidence": supporting[identity], "against": against[identity], "ticked": criterion["ticked"]})
    uncovered = [row["id"] for row in rows if row["status"] == "uncovered"]
    contradicted = [row["id"] for row in rows if row["status"] == "contradicted"]
    warnings = [f"{row['id']} is ticked but has no evidence that holds up" for row in rows
                if row["ticked"] and row["status"] != "covered"]
    failed = bool(uncovered or contradicted or unknown)
    return {
        "tool": TOOL, "version": VERSION, "verdict": "fail" if failed else "pass",
        "uncovered": uncovered, "contradicted": contradicted, "unknown_criteria": unknown[:LIST_LIMIT],
        "criteria": rows[:LIST_LIMIT], "evidence_problems": problems[:LIST_LIMIT], "warnings": warnings[:LIST_LIMIT],
        "counts": {"criteria": len(rows), "covered": len(rows) - len(uncovered) - len(contradicted),
                   "evidence_entries": len(entries), "entries_with_problems": len(problems)},
        "inputs": {"criteria": info(args.criteria, criteria_bytes), "evidence": info(args.evidence, evidence_bytes)},
    }


def main(argv=None) -> int:
    parser = Arguments(prog="verify_criteria_evidence.py", description=__doc__.splitlines()[0])
    parser.add_argument("--criteria", required=True, help="ticket checklist, Markdown or JSON, or -")
    parser.add_argument("--evidence", required=True, help="evidence entries as JSON, or -")
    parser.add_argument("--format", choices=("auto", "pytest", "unittest", "go", "cargo", "junit"), default="auto",
                        help="format of the saved test outputs that test entries cite")
    parser.add_argument("--root", default=".", help="folder that holds every input (default: current folder)")
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

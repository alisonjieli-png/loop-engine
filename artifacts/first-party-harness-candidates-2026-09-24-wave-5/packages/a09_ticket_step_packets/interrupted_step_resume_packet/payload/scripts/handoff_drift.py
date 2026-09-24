"""Effects: reads the workspace, runs git rev-parse and git status, writes one new handoff file (write) or one evidence file (check) under .baltor/.

Write and check the handoff of an interrupted step.

The host runs write right after it stops a step, from its own copy of this
package, before anything else changes the workspace:

    python3 -I -B handoff_drift.py write --root WORKSPACE --step-id t-104-fix --ticket-id T-104 \
        --instructions .baltor/resume/interrupted-instructions.md --handoff .baltor/resume/handoff.json \
        --host-placed AGENTS.md --host-placed CLAUDE.md --host-placed GEMINI.md

write needs the workspace root to be the top folder of a git worktree. It
records HEAD as the revision and every path that differs from it: changed,
added, deleted and untracked files, with the sha256 of each file, or null for
a deleted one. The host's files under .baltor/, the host placed paths and byte
caches are left out. The first action and the done conditions are copied from
the host's own rendered copy of the interrupted step's instructions; code
block lines become text in backticks. The status is unfinished and the
handoff holds no claims. It prints the digests of the handoff and of the
instructions, which the host copies into the resume step's input.

The resume step runs check first:

    python3 -I -B .baltor/interrupted-step-resume-packet/scripts/handoff_drift.py check \
        --input .baltor/resume/input.json

check first compares the host's files (the handoff, the interrupted
instructions and every other file the input lists) with the digests the host
recorded. Then it compares the handoff with the workspace: HEAD against the
recorded revision, each recorded file against its digest, and the changed
files that git reports against the recorded list. It accepts the recorded
first action and remaining actions only when each one quotes, in backticks, at
least one command or path that the interrupted instructions show in backticks
or in a code block, and quotes nothing else. It changes nothing in the
workspace, writes one new evidence file that records the digest of its input,
and prints one JSON object; only on a match does it print the actions.

Exit status. write: 0 when the handoff was written; 2 when the input was
refused and nothing was written. check: 0 when the workspace matches; 1 for
drift or a handoff that cannot be resumed; 2 when the input was refused and
nothing was written.

Python 3.10 or later, standard library only, POSIX systems.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

INPUT_TYPE = "interrupted_step_resume_input/v1"
HANDOFF_TYPE = "night_step_handoff/v1"
RECORD_TYPE = "interrupted_step_drift_check/v1"
INPUT_FIELDS = frozenset({"record_type", "step_id", "handoff_path", "handoff_sha256", "interrupted_instructions_path",
                          "interrupted_instructions_sha256", "host_files", "host_placed_paths", "evidence_dir"})
HANDOFF_FIELDS = frozenset({"record_type", "step_id", "ticket_id", "status", "written_at", "revision", "files",
                            "claims", "blocker", "first_action", "remaining_actions", "done_when"})
STATUSES = ("complete", "blocked", "unfinished")
MAX_INPUT_BYTES = 1024 * 1024
MAX_HASHED_FILE_BYTES = 256 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_FILES = 500
MAX_HOST_FILES = 100
MARKER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
REVISION = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
FENCE = re.compile(r"^\s*(?:```|~~~)")
QUOTED = re.compile(r"`([^`\n]+)`")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
CACHE_SEGMENTS = frozenset({"__pycache__", ".pytest_cache"})
STEP_FOLDER = ".baltor"
PACKET_FOLDER = ".baltor/step"


class Refused(Exception):
    """The input cannot be used. Nothing was written."""


def utc_now(precise: bool = True) -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ" if precise else "%Y-%m-%dT%H:%M:%SZ")


def read_bounded(path: Path, limit: int, name: str) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as error:
        raise Refused(f"{name} cannot be read: {type(error).__name__}") from None
    if len(data) > limit:
        raise Refused(f"{name} is larger than {limit} bytes")
    return data


def utf8_text(data: bytes, name: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{name} is not UTF-8 text") from None
    if MARKER.search(text):
        raise Refused(f"unrendered_step_input: {name} still holds a marker in double braces")
    return text


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

    text = utf8_text(data, name)
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


def output_path(root: Path, value, name: str) -> Path:
    path = confined(root, value, name)
    if not in_folder(value, STEP_FOLDER) or in_folder(value, PACKET_FOLDER):
        raise Refused(f"{name} must be inside .baltor/ and outside .baltor/step/, the interrupted step's packet")
    return path


def under_any(path: str, prefixes) -> bool:
    """A prefix that ends with / matches everything below it; any other prefix matches one file."""
    return any(path.startswith(prefix) if prefix.endswith("/") else path == prefix for prefix in prefixes)


def is_ignored(path: str, host_placed) -> bool:
    parts = path.split("/")
    return (parts[0] == STEP_FOLDER or under_any(path, host_placed) or bool(CACHE_SEGMENTS.intersection(parts))
            or path.endswith(".pyc"))


def is_time(value) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        moment = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return moment.tzinfo is not None


def text_or_none(value, limit: int) -> bool:
    return value is None or (isinstance(value, str) and 0 < len(value.strip()) and len(value) <= limit)


def file_digest(path: Path) -> str:
    digest, total = hashlib.sha256(), 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                total += len(chunk)
                if total > MAX_HASHED_FILE_BYTES:
                    raise Refused(f"a file is larger than {MAX_HASHED_FILE_BYTES} bytes: {path.name}")
                digest.update(chunk)
    except OSError as error:
        raise Refused(f"a file cannot be read: {type(error).__name__}") from None
    return digest.hexdigest()


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


def git_head(root: Path) -> str:
    top = git_output(root, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip()
    if Path(top).resolve() != root:
        raise Refused("--root must be the top folder of the git worktree")
    return git_output(root, "rev-parse", "HEAD").decode("ascii", "replace").strip()


def changed_paths(root: Path) -> set:
    """Every path that differs from HEAD: changed, added, deleted, renamed on either side, and untracked."""
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
        paths.add(token[3:].decode("utf-8", "replace"))
        if "R" in code or "C" in code:
            if index < len(tokens) and tokens[index]:
                paths.add(tokens[index].decode("utf-8", "replace"))
            index += 1
    return paths


# ---------------------------------------------------------------------------
# The interrupted instructions: sections, and the commands and paths they show
# ---------------------------------------------------------------------------

def section_lines(markdown: str, heading: str) -> list:
    lines, inside = [], False
    for line in markdown.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == heading
            continue
        if inside:
            lines.append(line)
    return lines


def one_line(lines: list) -> str:
    """Join a section into one line; each code block line becomes text in backticks."""
    parts, in_code = [], False
    for line in lines:
        if FENCE.match(line):
            in_code = not in_code
            continue
        if line.strip():
            parts.append(f"`{line.strip()}`" if in_code else line.strip())
    return " ".join(parts)


def listed(lines: list) -> list:
    items = [match.group(1) for match in map(LIST_ITEM.match, lines) if match]
    if items:
        return items
    paragraph = one_line(lines)
    return [paragraph] if paragraph else []


def shown_items(markdown: str) -> set:
    """Every text the instructions show in backticks, and every nonempty line of their code blocks."""
    shown, in_code = set(), False
    for line in markdown.splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            if line.strip():
                shown.add(line.strip())
        else:
            shown.update(item.strip() for item in QUOTED.findall(line) if item.strip())
    return shown


def action_problems(handoff: dict, shown: set) -> list:
    labeled = [("first_action", handoff["first_action"])] + [
        (f"remaining_actions[{number}]", action) for number, action in enumerate(handoff["remaining_actions"])]
    problems = []
    for label, action in labeled:
        if "```" in action:
            problems.append(f"{label} holds a code fence")
            continue
        quoted = [item.strip() for item in QUOTED.findall(action)]
        if not quoted:
            problems.append(f"{label} quotes no command or path of the interrupted instructions in backticks")
            continue
        unknown = [item for item in quoted if item not in shown]
        if unknown:
            problems.append(f"{label} quotes {unknown[0][:120]!r}, which the interrupted instructions do not show")
    return problems


# ---------------------------------------------------------------------------
# The handoff record
# ---------------------------------------------------------------------------

def handoff_problems(handoff: dict) -> list:
    """Every way the handoff differs from night_step_handoff/v1; an empty list means it is usable."""
    if set(handoff) != HANDOFF_FIELDS:
        return [f"handoff fields differ: missing {sorted(HANDOFF_FIELDS - set(handoff))}, "
                f"unexpected {sorted(set(handoff) - HANDOFF_FIELDS)[:5]}"]
    problems = []
    if handoff["record_type"] != HANDOFF_TYPE:
        problems.append(f"record_type must be {HANDOFF_TYPE}")
    if not isinstance(handoff["step_id"], str) or not IDENTIFIER.match(handoff["step_id"]):
        problems.append("step_id must be an identifier of at most 64 characters")
    if handoff["ticket_id"] is not None and (not isinstance(handoff["ticket_id"], str)
                                             or not IDENTIFIER.match(handoff["ticket_id"])):
        problems.append("ticket_id must be null or an identifier")
    if handoff["status"] not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")
    if not is_time(handoff["written_at"]):
        problems.append("written_at must be an ISO 8601 time with a zone, such as 2026-09-23T02:41:07Z")
    if handoff["revision"] is not None and (not isinstance(handoff["revision"], str)
                                            or not REVISION.match(handoff["revision"])):
        problems.append("revision must be null or a full commit id in lower-case hexadecimal")
    files = handoff["files"]
    if not isinstance(files, list) or len(files) > MAX_FILES or any(
            not isinstance(item, dict) or set(item) != {"path", "sha256"} or not isinstance(item["path"], str)
            or (item["sha256"] is not None and (not isinstance(item["sha256"], str) or not DIGEST.match(item["sha256"])))
            for item in files):
        problems.append("files must be a list of at most 500 objects with path and sha256 (null for a deleted file)")
    elif len({item["path"] for item in files}) != len(files):
        problems.append("files names one path twice")
    claims = handoff["claims"]
    if not isinstance(claims, list) or len(claims) > 50 or any(
            not isinstance(item, dict) or set(item) != {"text", "evidence"} or not text_or_none(item["text"], 500)
            or item["text"] is None or not text_or_none(item["evidence"], 400) for item in claims):
        problems.append("claims must be a list of at most 50 objects with text and evidence")
    blocker = handoff["blocker"]
    if blocker is not None and (not isinstance(blocker, dict) or set(blocker) != {"reason", "question", "evidence"}
                                or blocker["reason"] is None or not text_or_none(blocker["reason"], 500)
                                or not text_or_none(blocker["question"], 500)
                                or not text_or_none(blocker["evidence"], 400)):
        problems.append("blocker must be null or an object with reason, question and evidence")
    if not text_or_none(handoff["first_action"], 1000):
        problems.append("first_action must be null or text of at most 1000 characters")
    for name, count, limit in (("remaining_actions", 50, 1000), ("done_when", 20, 500)):
        value = handoff[name]
        if not isinstance(value, list) or len(value) > count or any(
                item is None or not text_or_none(item, limit) for item in value):
            problems.append(f"{name} must be a list of at most {count} texts")
    if handoff["status"] == "blocked" and blocker is None:
        problems.append("a blocked handoff names its blocker")
    if handoff["status"] == "unfinished" and handoff["first_action"] is None:
        problems.append("an unfinished handoff names its first_action")
    return problems


# ---------------------------------------------------------------------------
# write: the host records the handoff of a step it stopped
# ---------------------------------------------------------------------------

def command_write(options) -> int:
    root = resolve_root(options.root)
    if not IDENTIFIER.match(options.step_id or ""):
        raise Refused("--step-id must be an identifier of at most 64 characters")
    if options.ticket_id is not None and not IDENTIFIER.match(options.ticket_id):
        raise Refused("--ticket-id must be an identifier of at most 64 characters")
    host_placed = list(dict.fromkeys(options.host_placed))
    for item in host_placed:
        confined(root, item, "--host-placed")
    instructions_path = confined(root, options.instructions, "--instructions")
    if instructions_path.is_symlink() or not instructions_path.is_file():
        raise Refused("--instructions must name a regular file")
    instructions_bytes = read_bounded(instructions_path, MAX_INPUT_BYTES, "the interrupted instructions")
    instructions = utf8_text(instructions_bytes, "the interrupted instructions")
    first_action = one_line(section_lines(instructions, "## First action"))
    if not first_action:
        raise Refused("the interrupted instructions have no First action section")
    if len(first_action) > 1000:
        raise Refused("the First action section of the interrupted instructions is longer than 1000 characters")
    done_when = [item if len(item) <= 500 else item[:497] + "..."
                 for item in listed(section_lines(instructions, "## Done when"))][:20]
    target = output_path(root, options.handoff, "--handoff")
    if target.exists() or target.is_symlink():
        raise Refused("--handoff names a file that exists; a handoff is never replaced")
    head = git_head(root)
    files = []
    for path in sorted(changed_paths(root)):
        if is_ignored(path, host_placed):
            continue
        current = confined(root, path, "a changed path")
        if current.is_symlink():
            raise Refused(f"a changed path is a symbolic link, and a handoff records regular files only: {path}")
        if current.is_dir():
            raise Refused(f"a changed path is a folder, such as a nested repository: {path}")
        files.append({"path": path, "sha256": file_digest(current) if current.exists() else None})
    if len(files) > MAX_FILES:
        raise Refused(f"more than {MAX_FILES} paths differ from HEAD")
    handoff = {"record_type": HANDOFF_TYPE, "step_id": options.step_id, "ticket_id": options.ticket_id,
               "status": "unfinished", "written_at": utc_now(precise=False), "revision": head, "files": files,
               "claims": [], "blocker": None, "first_action": first_action, "remaining_actions": [],
               "done_when": done_when}
    data = (json.dumps(handoff, indent=1, ensure_ascii=True) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        raise Refused("--handoff names a file that exists; a handoff is never replaced") from None
    print(json.dumps({"verdict": "written", "handoff_path": options.handoff,
                      "handoff_sha256": hashlib.sha256(data).hexdigest(),
                      "interrupted_instructions_path": options.instructions,
                      "interrupted_instructions_sha256": hashlib.sha256(instructions_bytes).hexdigest(),
                      "revision": head, "files": len(files)}, indent=1))
    return 0


# ---------------------------------------------------------------------------
# check: the resume step compares the handoff with the workspace
# ---------------------------------------------------------------------------

def load_input(root: Path, input_value: str) -> tuple[dict, str]:
    data = read_bounded(confined(root, input_value, "--input"), MAX_INPUT_BYTES, "the step input")
    step = strict_object(data, "the step input")
    if step.get("record_type") != INPUT_TYPE:
        raise Refused(f"record_type must be {INPUT_TYPE}")
    if set(step) != INPUT_FIELDS:
        raise Refused(f"the step input fields differ: missing {sorted(INPUT_FIELDS - set(step))}, "
                      f"unexpected {sorted(set(step) - INPUT_FIELDS)}")
    if not isinstance(step["step_id"], str) or not IDENTIFIER.match(step["step_id"]):
        raise Refused("step_id must be an identifier of at most 64 characters")
    for name in ("handoff_sha256", "interrupted_instructions_sha256"):
        if not isinstance(step[name], str) or not DIGEST.match(step[name]):
            raise Refused(f"{name} must be 64 lower-case hexadecimal characters")
    confined(root, step["handoff_path"], "handoff_path")
    confined(root, step["interrupted_instructions_path"], "interrupted_instructions_path")
    host_files = step["host_files"]
    if not isinstance(host_files, list) or len(host_files) > MAX_HOST_FILES or any(
            not isinstance(item, dict) or set(item) != {"path", "sha256"} or not isinstance(item["sha256"], str)
            or not DIGEST.match(item["sha256"]) for item in host_files):
        raise Refused(f"host_files must be a list of at most {MAX_HOST_FILES} objects with path and sha256")
    for item in host_files:
        confined(root, item["path"], "host_files")
    paths = [step["handoff_path"], step["interrupted_instructions_path"]] + [item["path"] for item in host_files]
    if len(set(paths)) != len(paths):
        raise Refused("handoff_path, interrupted_instructions_path and host_files name one path twice")
    placed = step["host_placed_paths"]
    if not isinstance(placed, list) or len(placed) > 50:
        raise Refused("host_placed_paths must be a list of at most 50 relative paths")
    for item in placed:
        confined(root, item, "host_placed_paths")
    output_path(root, step["evidence_dir"], "evidence_dir")
    return step, hashlib.sha256(data).hexdigest()


def host_file_differences(root: Path, step: dict) -> list:
    expected = [(step["handoff_path"], step["handoff_sha256"]),
                (step["interrupted_instructions_path"], step["interrupted_instructions_sha256"])]
    expected += [(item["path"], item["sha256"]) for item in step["host_files"]]
    differences = []
    for path, digest in expected:
        current = confined(root, path, "a host file")
        if current.is_symlink() or not current.exists():
            differences.append({"kind": "host_file_missing", "path": path, "expected": digest, "found": None})
        elif not current.is_file():
            differences.append({"kind": "host_file_changed", "path": path, "expected": digest,
                                "found": "not a regular file"})
        else:
            found = file_digest(current)
            if found != digest:
                differences.append({"kind": "host_file_changed", "path": path, "expected": digest, "found": found})
    return differences


def compare(root: Path, step: dict, handoff: dict) -> tuple[list, dict]:
    differences, git_checks, head = [], "skipped_no_revision", None
    if handoff["revision"] is not None:
        head = git_head(root)
        git_checks = "run"
        if head != handoff["revision"]:
            differences.append({"kind": "head_moved", "path": None, "expected": handoff["revision"], "found": head})
    recorded, skipped = {}, 0
    for item in handoff["files"]:
        if is_ignored(item["path"], step["host_placed_paths"]):
            skipped += 1
            continue
        path = confined(root, item["path"], "a path in the handoff files")
        recorded[item["path"]] = item["sha256"]
        exists = path.exists() or path.is_symlink()
        if item["sha256"] is None:
            if exists:
                differences.append({"kind": "file_present_but_recorded_absent", "path": item["path"],
                                    "expected": None, "found": "present"})
        elif not exists:
            differences.append({"kind": "file_missing", "path": item["path"], "expected": item["sha256"],
                                "found": None})
        elif path.is_symlink() or not path.is_file():
            differences.append({"kind": "not_a_regular_file", "path": item["path"], "expected": item["sha256"],
                                "found": "not a regular file"})
        else:
            found = file_digest(path)
            if found != item["sha256"]:
                differences.append({"kind": "file_changed", "path": item["path"], "expected": item["sha256"],
                                    "found": found})
    if git_checks == "run":
        for path in sorted(changed_paths(root)):
            if path not in recorded and not is_ignored(path, step["host_placed_paths"]):
                differences.append({"kind": "unrecorded_change", "path": path, "expected": None, "found": "changed"})
    return differences, {"git_checks": git_checks, "head_found": head, "files_checked": len(recorded),
                         "files_skipped_host_placed": skipped}


def write_evidence(root: Path, folder: str, record: dict) -> str:
    directory = output_path(root, folder, "evidence_dir")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for attempt in range(100):
        target = directory / (f"drift-check-{stamp}.json" if attempt == 0 else f"drift-check-{stamp}-{attempt}.json")
        try:
            with target.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
        except FileExistsError:
            continue
        return target.relative_to(root).as_posix()
    raise Refused("no new evidence file name was free")


def command_check(options) -> int:
    root = resolve_root(options.root)
    step, input_sha256 = load_input(root, options.input)
    facts = {"git_checks": "not_run", "head_found": None, "files_checked": 0, "files_skipped_host_placed": 0}
    reasons, handoff, handoff_digest = [], None, None
    differences = host_file_differences(root, step)
    if differences:
        verdict = "drift"
        reasons.append("a file the host placed for this step differs from the digest the host recorded")
    else:
        handoff_bytes = read_bounded(confined(root, step["handoff_path"], "handoff_path"), MAX_INPUT_BYTES,
                                     "the handoff")
        handoff_digest = hashlib.sha256(handoff_bytes).hexdigest()
        handoff = strict_object(handoff_bytes, "the handoff")
        problems = handoff_problems(handoff)
        if problems:
            raise Refused("the handoff does not match night_step_handoff/v1: " + "; ".join(problems[:5]))
        instructions = utf8_text(read_bounded(confined(root, step["interrupted_instructions_path"],
                                                       "interrupted_instructions_path"),
                                              MAX_INPUT_BYTES, "the interrupted instructions"),
                                 "the interrupted instructions")
        if handoff["step_id"] != step["step_id"]:
            reasons.append(f"the handoff belongs to step {handoff['step_id']}, not {step['step_id']}")
        if handoff["status"] != "unfinished":
            reasons.append(f"the handoff status is {handoff['status']}; only unfinished work is resumed")
        if not reasons:
            reasons = action_problems(handoff, shown_items(instructions))
        if reasons:
            verdict = "not_resumable"
        else:
            differences, facts = compare(root, step, handoff)
            verdict = "drift" if differences else "match"
    record = {"record_type": RECORD_TYPE, "step_id": step["step_id"], "verdict": verdict, "reasons": reasons,
              "input_path": options.input, "input_sha256": input_sha256, "handoff_path": step["handoff_path"],
              "handoff_sha256": handoff_digest, "interrupted_instructions_path": step["interrupted_instructions_path"],
              "revision_expected": handoff["revision"] if handoff else None, "revision_found": facts["head_found"],
              "git_checks": facts["git_checks"], "files_checked": facts["files_checked"],
              "files_skipped_host_placed": facts["files_skipped_host_placed"], "differences": differences,
              "written_at": utc_now()}
    summary = {"verdict": verdict, "evidence_path": write_evidence(root, step["evidence_dir"], record),
               "input_sha256": input_sha256, "reasons": reasons, "differences": differences[:50],
               "git_checks": facts["git_checks"]}
    if verdict == "match":
        summary.update(first_action=handoff["first_action"], remaining_actions=handoff["remaining_actions"],
                       interrupted_instructions_path=step["interrupted_instructions_path"])
    print(json.dumps(summary, indent=1))
    return 0 if verdict == "match" else 1


def resolve_root(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except OSError:
        raise Refused("--root does not exist") from None
    if not root.is_dir():
        raise Refused("--root is not a folder")
    return root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write or check the handoff of an interrupted step.")
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="for the host: record the handoff of a step it stopped")
    write.add_argument("--root", default=".", help="the workspace root, the top folder of the git worktree")
    write.add_argument("--step-id", required=True, help="the identifier of the stopped step")
    write.add_argument("--ticket-id", default=None, help="the ticket of the stopped step, if any")
    write.add_argument("--instructions", required=True,
                       help="workspace-relative path of the host's rendered copy of the step's instructions")
    write.add_argument("--handoff", required=True, help="workspace-relative path of the new handoff file")
    write.add_argument("--host-placed", action="append", default=[],
                       help="a file or folder the host placed; repeat for each")
    check = commands.add_parser("check", help="for the resume step: compare the handoff with the workspace")
    check.add_argument("--input", default=".baltor/resume/input.json", help="workspace-relative step input")
    check.add_argument("--root", default=".", help="the workspace root")
    options = parser.parse_args(argv)
    try:
        return command_write(options) if options.command == "write" else command_check(options)
    except Refused as refusal:
        print(json.dumps({"verdict": "refused", "reason": str(refusal)}, indent=1))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

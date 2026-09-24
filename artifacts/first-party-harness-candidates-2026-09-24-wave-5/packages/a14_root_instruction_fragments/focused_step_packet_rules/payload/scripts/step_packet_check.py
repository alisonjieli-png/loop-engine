"""Read and check the focused step packet. Effects: reads files under --root only; writes nothing; no network, no model call.

The host places the packet for one step in .baltor/step/ below the workspace
root: task.json (a node_assignment/v3 record), node_context.md and, when
present, checklist.md, a contracts/ folder and input files. This check prints
one JSON object with the objective, the effects, the first action, the
acceptance items and the checklist items, so a fresh harness can start without
guessing. A host can also run it before launch; exit 0 means the packet is ready.

It refuses a packet file that still holds a double-brace marker the host
never filled in (reason unrendered_step_input), a task record with missing or
extra fields, a context file without its Objective or Acceptance section, and a
packet without a first action. task.json, node_context.md and checklist.md must
be UTF-8 text of at most 256 KiB. Every other packet file is searched for
markers when it is UTF-8 text within that size; a larger or binary input file
is listed in unchecked_files instead of refusing the packet. The first action
is searched under a "## First action" or "## First actions" heading in
node_context.md, then in the root AGENTS.md, GEMINI.md and CLAUDE.md. Root
instruction files are read only when they are UTF-8 text inside the workspace;
a marker there is reported in instruction_markers, because such a file may
quote a template on purpose.

Exit 0: the packet is ready. Exit 1: the packet is readable but a check
failed. Exit 2: the packet cannot be read safely.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

TASK_FIELDS = {"record_type", "node_id", "kind", "objective", "output_contract_refs", "dependency_ids",
               "required_capabilities", "effects", "harness_style", "model_calls_authorized", "mode"}
LIST_FIELDS = ("output_contract_refs", "dependency_ids", "required_capabilities", "effects")
KINDS = ("reason", "build")
MODES = ("deterministic", "hybrid", "non_deterministic")
#: Effect names are checked for form only. The host's assignment contract owns the effect vocabulary.
EFFECT_NAME = re.compile(r"[a-z][a-z_]{0,39}\Z")
MARKER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
FIRST_ACTION_HEADINGS = ("## First action", "## First actions")
ROOT_INSTRUCTION_FILES = ("AGENTS.md", "GEMINI.md", "CLAUDE.md")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.*\S)\s*$")
MAX_FILE_BYTES = 256 * 1024
MAX_PACKET_FILES = 1000
MAX_SCANNED_BYTES = 16 * 1024 * 1024
#: Packet files that must be readable text; every other file may be an input of any kind.
TEXT_FILES = ("task.json", "node_context.md", "checklist.md")
MAX_ITEM_CHARACTERS = 600
MAX_ITEMS = 40
NEXT_READY = ("First make every before_work item hold; if one cannot hold, stop and report it. Then do the "
              "first_action. Work only on the objective and use only the listed effects. Before you finish, make "
              "every item in acceptance and before_handoff hold and report each check with its result.")
NEXT_MARKERS = ("A root instruction file holds a double-brace marker. If your instructions still hold a value "
                "the host should have filled in, stop and report unrendered_step_input. Otherwise: ")
NEXT_FAILED = "Stop. Report this answer to the host. Do not guess the missing part and do not edit the packet."


class Refusal(Exception):
    """A refused packet: the exit status, a stable reason and a short detail."""

    def __init__(self, status: int, reason: str, detail) -> None:
        super().__init__(str(detail))
        self.status, self.reason, self.detail = status, reason, detail


def failed(reason: str, detail) -> Refusal:
    return Refusal(1, reason, detail)


def unreadable(reason: str, detail) -> Refusal:
    return Refusal(2, reason, detail)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # an argument error is refused input, answered as JSON
        raise unreadable("arguments_invalid", message)


def parse(argv) -> argparse.Namespace:
    parser = Parser(prog="step_packet_check.py", description="Read and check the focused step packet.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--step-dir", default=".baltor/step")
    return parser.parse_args(argv)


def inside(root: Path, relative: str) -> Path:
    """Resolve a relative path under root, refusing absolute paths, '..' and links that leave root."""
    pure = Path(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise unreadable("unsafe_packet_path", f"{relative!r} must be a relative path inside the workspace")
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise unreadable("unsafe_packet_path", f"{current.relative_to(root).as_posix()} is a symbolic link")
    return current


def read_text(path: Path, shown: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise unreadable("packet_file_missing", f"{shown} is missing or not a regular file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise unreadable("packet_file_too_large", f"{shown} is larger than {MAX_FILE_BYTES} bytes")
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise unreadable("packet_file_not_text", f"{shown} is not UTF-8 text") from None


def strict_json(text: str, shown: str) -> dict:
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ValueError as error:
        raise unreadable("task_record_unreadable", f"{shown}: {error}") from None
    if not isinstance(value, dict):
        raise unreadable("task_record_unreadable", f"{shown} is not one JSON object")
    return value


def packet_texts(root: Path, step: Path) -> tuple:
    """The packet files that can be read as text, keyed by workspace-relative path, and the files left unchecked."""
    texts, unchecked, count, budget = {}, [], 0, MAX_SCANNED_BYTES
    required = {(step / name).relative_to(root).as_posix() for name in TEXT_FILES}
    for current, folders, names in os.walk(step, followlinks=False):
        folders.sort()
        for name in folders + names:
            if (Path(current) / name).is_symlink():
                raise unreadable("unsafe_packet_path", f"{(Path(current) / name).relative_to(root).as_posix()} "
                                                       "is a symbolic link")
        for name in sorted(names):
            path = Path(current) / name
            shown = path.relative_to(root).as_posix()
            count += 1
            if count > MAX_PACKET_FILES:
                raise unreadable("packet_too_large", f"the packet holds more than {MAX_PACKET_FILES} files")
            if shown in required:
                texts[shown] = read_text(path, shown)
                budget -= len(texts[shown])
                continue
            if not path.is_file():
                unchecked.append({"path": shown, "reason": "not a regular file"})
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                unchecked.append({"path": shown, "reason": f"larger than {MAX_FILE_BYTES} bytes"})
            elif size > budget:
                unchecked.append({"path": shown, "reason": f"the check reads at most {MAX_SCANNED_BYTES} bytes"})
            else:
                budget -= size
                try:
                    texts[shown] = path.read_bytes().decode("utf-8")
                except UnicodeDecodeError:
                    unchecked.append({"path": shown, "reason": "not UTF-8 text"})
    return texts, unchecked


def task_problems(task: dict) -> list:
    problems = []
    if set(task) != TASK_FIELDS:
        problems.append(f"fields differ: missing {sorted(TASK_FIELDS - set(task))}, extra {sorted(set(task) - TASK_FIELDS)}")
    if task.get("record_type") != "node_assignment/v3":
        problems.append("record_type is node_assignment/v3")
    node_id = task.get("node_id")
    if (not isinstance(node_id, str) or not node_id.strip() or node_id in (".", "..")
            or any(character in node_id for character in "/\\:") or any(ord(ch) < 32 for ch in node_id)):
        problems.append("node_id is nonempty text without slashes, colons or control characters")
    if task.get("kind") not in KINDS:
        problems.append(f"kind is one of {list(KINDS)}")
    if not isinstance(task.get("objective"), str) or not task.get("objective", "").strip():
        problems.append("objective is nonempty text")
    for name in LIST_FIELDS:
        value = task.get(name)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            problems.append(f"{name} is a list of nonempty strings")
    effects = task.get("effects") if isinstance(task.get("effects"), list) else []
    if (any(not isinstance(effect, str) or not EFFECT_NAME.fullmatch(effect) for effect in effects)
            or len(set(map(str, effects))) != len(effects) or ("pure" in effects and len(effects) != 1)):
        problems.append("effects are distinct lower-case effect names; pure stands alone")
    if not isinstance(task.get("harness_style"), str):
        problems.append("harness_style is text")
    if type(task.get("model_calls_authorized")) is not bool:
        problems.append("model_calls_authorized is true or false")
    if task.get("mode") not in MODES:
        problems.append(f"mode is one of {list(MODES)}")
    return problems


def sections(markdown: str) -> dict:
    """Level-two sections: heading line to the lines below it, until the next level-two heading."""
    found, current = {}, None
    for line in markdown.splitlines():
        if line.startswith("## "):
            current = line.strip()
            found.setdefault(current, [])
        elif current is not None:
            found[current].append(line)
    return found


def items(lines: list) -> list:
    listed = [match.group(1)[:MAX_ITEM_CHARACTERS] for match in map(LIST_ITEM.match, lines) if match]
    if listed:
        return listed[:MAX_ITEMS]
    paragraph = " ".join(line.strip() for line in lines if line.strip())
    return [paragraph[:MAX_ITEM_CHARACTERS]] if paragraph else []


def root_instruction(root: Path, name: str):
    """A root instruction file as text, or None when it is absent, too large, not text or outside the root."""
    path = root / name
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size > MAX_FILE_BYTES:
        return None
    try:
        return resolved.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def first_action(sources: list):
    for shown, markdown in sources:
        found = sections(markdown)
        for heading in FIRST_ACTION_HEADINGS:
            if heading in found:
                listed = items(found[heading])
                if listed:
                    return listed[0], shown
    return None, None


def check(root: Path, step_dir: str) -> dict:
    step = inside(root, step_dir)
    if not step.is_dir():
        raise unreadable("packet_missing", f"{step_dir} is not a folder")
    step_shown = step.relative_to(root).as_posix()
    texts, unchecked = packet_texts(root, step)
    task_shown, context_shown = f"{step_shown}/task.json", f"{step_shown}/node_context.md"
    for shown in (task_shown, context_shown):
        if shown not in texts:
            raise unreadable("packet_file_missing", f"{shown} is missing")
    task = strict_json(texts[task_shown], task_shown)
    instructions = [(name, content) for name in ROOT_INSTRUCTION_FILES
                    if (content := root_instruction(root, name)) is not None]
    marked = sorted(shown for shown, content in texts.items() if MARKER.search(content))
    if marked:
        raise failed("unrendered_step_input", {"files": marked})
    instruction_markers = sorted(name for name, content in instructions if MARKER.search(content))
    problems = task_problems(task)
    if problems:
        raise failed("task_record_invalid", {"problems": problems})
    context = sections(texts[context_shown])
    missing = [heading for heading in ("## Objective", "## Acceptance") if heading not in context]
    if missing:
        raise failed("node_context_incomplete", {"missing_sections": missing})
    acceptance = items(context["## Acceptance"])
    if not acceptance:
        raise failed("acceptance_missing", "the Acceptance section of node_context.md is empty")
    action, source = first_action([(context_shown, texts[context_shown])] + instructions)
    if action is None:
        raise failed("first_action_missing", "no First action section in node_context.md or a root instruction file")
    checklist = sections(texts.get(f"{step_shown}/checklist.md", ""))
    return {"result": "ready", "step_dir": step_shown, "node_id": task["node_id"], "kind": task["kind"],
            "mode": task["mode"], "objective": task["objective"], "effects": task["effects"],
            "model_calls_authorized": task["model_calls_authorized"],
            "output_contract_refs": task["output_contract_refs"], "first_action": action,
            "first_action_source": source, "acceptance": acceptance,
            "before_work": items(checklist.get("## Before work", [])),
            "before_handoff": items(checklist.get("## Before handoff", [])),
            "instruction_markers": instruction_markers, "unchecked_files": unchecked[:50],
            "unchecked_count": len(unchecked),
            "next": (NEXT_MARKERS if instruction_markers else "") + NEXT_READY}


def main(argv=None) -> int:
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
        try:
            root = Path(options.root).resolve(strict=True)
        except (OSError, RuntimeError):
            raise unreadable("root_missing", "the --root folder does not exist") from None
        if not root.is_dir():
            raise unreadable("root_missing", "the --root path is not a folder")
        answer = check(root, options.step_dir)
    except Refusal as refusal:
        print(json.dumps({"result": "refused", "reason": refusal.reason, "detail": refusal.detail,
                          "next": NEXT_FAILED}, ensure_ascii=False, sort_keys=True))
        return refusal.status
    print(json.dumps(answer, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

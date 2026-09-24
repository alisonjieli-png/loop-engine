"""Effects: reads the step folder and the packet manifest under the workspace root and runs the packet check in this process; writes nothing.

Prints one JSON status card of the current focused step, for use at any time
and again before handoff:

  step         node_id, kind, mode, objective, model_calls_authorized and
               effects, read from task.json as given
  output       the output contract refs, the output schema path, its top-level
               type and its required fields
  handoff      the items under "## Before handoff" in checklist.md
  packet       the result of check_step_packet.py (loaded from this folder by
               its exact path): passed, failure codes, bound to a host digest
  next_action  one sentence: go on, or stop and report

It does not judge whether the assignment itself is complete or sensible.

Exit status: 0 the packet check passed, 1 the packet check failed,
2 the step folder or task.json cannot be read.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

STEP_DEFAULT = ".baltor/step"
MANIFEST_DEFAULT = ".baltor/step/packet-manifest.json"
MAX_TEXT_BYTES = 256 * 1024
MAX_OBJECTIVE_CHARS = 400
MAX_ITEM_CHARS = 300
MAX_ITEMS = 30
HANDOFF_HEADING = "## Before handoff"
ITEM = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(.+\S)\s*$")
STOP = ("Stop. The packet is not the one the host placed. Report packet.failures and do no step work; "
        "do not repair or recreate packet files.")
GO = ("Work only on step.objective and use only step.effects. Before handoff, make every handoff item true "
      "and give a result that holds every field in output.required_fields.")


def load_checker():
    """Load check_step_packet.py from this folder by exact path; isolated mode ignores the script folder."""
    path = Path(__file__).resolve().with_name("check_step_packet.py")
    spec = importlib.util.spec_from_file_location("step_status_packet_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_small(path: Path) -> bytes | None:
    if path.is_symlink() or not path.is_file():
        return None
    with open(path, "rb") as stream:
        data = stream.read(MAX_TEXT_BYTES + 1)
    return None if len(data) > MAX_TEXT_BYTES else data


def shorten(value, limit: int):
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def handoff_items(text: str) -> list[str]:
    """List items under the Before handoff heading, up to the next heading of any level."""
    items, inside = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = line.strip() == HANDOFF_HEADING
            continue
        match = ITEM.match(line)
        if inside and match and len(items) < MAX_ITEMS:
            items.append(shorten(match.group(1), MAX_ITEM_CHARS))
    return items


def output_summary(checker, step: Path, step_relative: str, task: dict) -> dict:
    refs = task.get("output_contract_refs")
    summary = {"contract_refs": [ref for ref in refs if isinstance(ref, str)] if isinstance(refs, list) else [],
               "schema": None, "type": None, "required_fields": []}
    raw = read_small(step / "contracts" / "output.schema.json")
    if raw is None:
        return summary
    try:
        schema = checker.strict_json(raw)
    except checker.Refused:
        summary["schema"] = "unreadable"
        return summary
    if isinstance(schema, dict):
        summary["schema"] = f"{step_relative}/contracts/output.schema.json"
        summary["type"] = schema.get("type") if isinstance(schema.get("type"), str) else None
        required = schema.get("required")
        summary["required_fields"] = [name for name in required if isinstance(name, str)] \
            if isinstance(required, list) else []
    return summary


def status(checker, root: Path, step_relative: str, manifest: str, expected) -> tuple[int, dict]:
    if not checker.safe_relative(step_relative):
        return 2, {"error": "step_dir_unsafe", "detail": str(step_relative)[:120]}
    step = checker.inside(root, step_relative)
    if step is None or step.is_symlink() or not step.is_dir():
        return 2, {"error": "step_dir_missing", "detail": step_relative}
    raw = read_small(step / "task.json")
    if raw is None:
        return 2, {"error": "task_missing", "detail": f"{step_relative}/task.json"}
    try:
        task = checker.strict_json(raw)
    except checker.Refused as error:
        return 2, {"error": "task_unreadable", "detail": error.code}
    if not isinstance(task, dict):
        return 2, {"error": "task_unreadable", "detail": "not a JSON object"}
    effects = task.get("effects")
    card = {"node_id": shorten(task.get("node_id"), 120), "kind": shorten(task.get("kind"), 40),
            "mode": shorten(task.get("mode"), 40), "objective": shorten(task.get("objective"), MAX_OBJECTIVE_CHARS),
            "model_calls_authorized": task.get("model_calls_authorized")
            if isinstance(task.get("model_calls_authorized"), bool) else None,
            "effects": [effect for effect in effects if isinstance(effect, str)] if isinstance(effects, list) else []}
    checklist = read_small(step / "checklist.md")
    items = handoff_items(checklist.decode("utf-8", "replace")) if checklist is not None else []
    try:
        report = checker.verify(root, checker.load_manifest(root, manifest), expected, manifest)
        packet = {"passed": report["passed"], "failures": sorted({failure["code"] for failure in report["failures"]}),
                  "bound_to_host_digest": report["bound_to_host_digest"],
                  "packet_content_sha256": report["packet_content_sha256"]}
    except checker.Refused as error:
        packet = {"passed": False, "failures": [error.code], "bound_to_host_digest": False,
                  "packet_content_sha256": None}
    result = {"step": card, "output": output_summary(checker, step, step_relative, task),
              "handoff": items, "packet": packet, "next_action": GO if packet["passed"] else STOP}
    return (0 if packet["passed"] else 1), result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print the status card of the current focused step as one JSON object.")
    parser.add_argument("--root", help="workspace root; default GEMINI_PROJECT_DIR, CURSOR_PROJECT_DIR, "
                                       "CLAUDE_PROJECT_DIR or the current folder")
    parser.add_argument("--step-dir", default=STEP_DEFAULT, help="step folder relative to the root")
    parser.add_argument("--manifest", default=MANIFEST_DEFAULT, help="manifest path relative to the root")
    parser.add_argument("--expect-content-sha256", dest="expected",
                        help="the packet digest the host gave in the first message")
    options = parser.parse_args(argv)
    checker = load_checker()
    try:
        code, result = status(checker, checker.workspace_root(options.root), options.step_dir, options.manifest,
                              options.expected)
    except OSError as error:
        code, result = 2, {"error": "os_error", "detail": type(error).__name__}
    print(json.dumps(result, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

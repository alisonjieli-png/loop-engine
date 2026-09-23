"""Check pinned occupation references in this candidate batch.

This is a source-identity and obvious-copy screen, not an originality,
licence, usefulness, safety, or independent-approval judgment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPPORTUNITIES = ROOT.parent / "occupation-grid-research-2026-09-22" / "task-opportunities.json"
NOTES = ROOT / "review-notes"
PACKAGES = ROOT / "packages"
COMBINED = re.compile(r"(\d{2}-\d{4}\.\d{2}) / (\d+)\Z")
CODE = re.compile(r"\d{2}-\d{4}\.\d{2}\Z")
TASK_ID = re.compile(r"\d+\Z")
BACKTICKS = re.compile(r"`([^`]+)`")


def _source_references(note: str) -> list[tuple[str, str]]:
    source_lines = [line for line in note.splitlines() if line.startswith("- Source")]
    if len(source_lines) != 1:
        raise ValueError("each review note needs one source-basis line")
    found = []
    code = task_id = None
    for token in BACKTICKS.findall(source_lines[0]):
        combined = COMBINED.fullmatch(token)
        if combined:
            found.append(combined.groups())
            continue
        if CODE.fullmatch(token):
            code = token
        elif TASK_ID.fullmatch(token):
            task_id = token
        if code is not None and task_id is not None:
            found.append((code, task_id))
            code = task_id = None
    if code is not None or task_id is not None:
        raise ValueError("source occupation and task identifiers are unpaired")
    return found


def check() -> tuple[int, int]:
    source = json.loads(OPPORTUNITIES.read_text(encoding="utf-8"))
    if source.get("record_type") != "occupation_task_opportunity_inventory/v1":
        raise ValueError("unsupported occupation source inventory")
    valid = {(row["occupation_code"], row["task_id"]): row["source_task_text"]
             for row in source["task_references"]}
    if NOTES.is_symlink() or not NOTES.is_dir():
        raise ValueError("review-note folder missing or symlinked")
    notes = sorted(NOTES.glob("*.md"))
    if len(notes) != 20:
        raise ValueError("occupation-linked batch must contain 20 review notes")
    references = []
    for note in notes:
        if note.is_symlink():
            raise ValueError(f"symlinked review note: {note}")
        text = note.read_text(encoding="utf-8")
        cited = _source_references(text)
        if not cited:
            raise ValueError(f"source task ID missing from review note: {note}")
        for reference in cited:
            if reference not in valid:
                raise ValueError(f"unknown source task ID in {note}: {reference}")
        references.extend(cited)
        slug = note.stem
        matches = list(PACKAGES.glob(f"*/{slug}/SKILL.md"))
        if len(matches) != 1 or matches[0].is_symlink():
            raise ValueError(f"native skill missing or ambiguous for {slug}")
        skill = " ".join(matches[0].read_text(encoding="utf-8").casefold().split())
        for reference in cited:
            source_text = " ".join(valid[reference].casefold().split())
            if source_text in skill:
                raise ValueError(f"complete source task statement copied into {matches[0]}")
    if len(references) != 21 or len(set(references)) != 21:
        raise ValueError("source task reference population changed or was duplicated")
    return len(notes), len(references)


if __name__ == "__main__":
    count, source_count = check()
    print(f"checked {count} native candidates and {source_count} pinned task references")

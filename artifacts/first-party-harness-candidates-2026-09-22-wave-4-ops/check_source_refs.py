"""Verify pinned O*NET task IDs and screen obvious copied prose in wave four.

This is a source identity and lexical screen, not independent originality,
licence approval, usefulness, or permission to publish a candidate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPPORTUNITIES = ROOT.parent / "occupation-grid-research-2026-09-22" / "task-opportunities.json"
NOTES = ROOT / "review-notes"
PACKAGES = ROOT / "packages"
EXPECTED_ITEMS = 12
EXPECTED_SOURCE_DIGEST = "55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd"
SOURCE_LINE = re.compile(r"^- Source basis and rights:.*?task ID `(\d+)`, occupation `(\d{2}-\d{4}\.\d{2})`", re.MULTILINE)
WORDS = re.compile(r"[a-z0-9]+")


def _word_windows(text: str, size: int) -> set[tuple[str, ...]]:
    words = WORDS.findall(text.casefold())
    return {tuple(words[index:index + size]) for index in range(len(words) - size + 1)}


def check() -> tuple[int, int]:
    if OPPORTUNITIES.is_symlink() or not OPPORTUNITIES.is_file():
        raise ValueError("pinned occupation inventory missing or symlinked")
    source = json.loads(OPPORTUNITIES.read_text(encoding="utf-8"))
    if source.get("record_type") != "occupation_task_opportunity_inventory/v1":
        raise ValueError("unsupported occupation source inventory")
    if source.get("source", {}).get("sha256") != EXPECTED_SOURCE_DIGEST:
        raise ValueError("occupation source digest changed")
    valid = {(row["occupation_code"], row["task_id"]): row["source_task_text"]
             for row in source["task_references"]}
    if NOTES.is_symlink() or not NOTES.is_dir():
        raise ValueError("review-note folder missing or symlinked")
    notes = sorted(NOTES.glob("*.md"))
    if len(notes) != EXPECTED_ITEMS:
        raise ValueError("occupation-linked batch note count changed")
    seen: set[tuple[str, str]] = set()
    for note in notes:
        if note.is_symlink():
            raise ValueError(f"symlinked review note: {note}")
        note_text = note.read_text(encoding="utf-8")
        cited = SOURCE_LINE.findall(note_text)
        if len(cited) != 1:
            raise ValueError(f"expected exactly one task ID and occupation in {note}")
        task_id, occupation = cited[0]
        source_key = (occupation, task_id)
        if source_key not in valid:
            raise ValueError(f"unknown source task ID in {note}: {source_key}")
        if source_key in seen:
            raise ValueError(f"duplicate source task ID in {note}: {source_key}")
        seen.add(source_key)
        if EXPECTED_SOURCE_DIGEST not in note_text:
            raise ValueError(f"source digest absent from {note}")
        matches = list(PACKAGES.glob(f"*/{note.stem}/SKILL.md"))
        if len(matches) != 1 or matches[0].is_symlink():
            raise ValueError(f"native skill missing or ambiguous for {note.stem}")
        skill = matches[0].read_text(encoding="utf-8")
        if _word_windows(skill, 8) & _word_windows(valid[source_key], 8):
            raise ValueError(f"eight-word source span copied into {matches[0]}")
    return len(notes), len(seen)


if __name__ == "__main__":
    count, references = check()
    print(f"checked {count} native candidates and {references} pinned task references")

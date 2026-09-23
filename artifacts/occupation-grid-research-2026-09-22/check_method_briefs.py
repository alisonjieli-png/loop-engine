"""Check that every brief cites a real task in the pinned source inventory.

This verifies identity and coverage only. It cannot judge whether a proposed
method is original, useful, safe, or actually implied by the cited task.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "task-opportunities.json"
BRIEFS = ROOT / "next-method-briefs.md"
ROW = re.compile(r"^\|\s*\d+\s*\|", re.MULTILINE)
REFERENCE = re.compile(r"`(\d{2}-\d{4}\.\d{2}) / (\d+)`")


def check(brief: str, inventory: dict) -> tuple[int, int]:
    valid = {(row["occupation_code"], row["task_id"])
             for row in inventory["task_references"]}
    references = REFERENCE.findall(brief)
    rows = ROW.findall(brief)
    if not references or len(rows) != 20 or len(references) != 21:
        raise ValueError("brief population or source-reference count changed")
    missing = sorted(set(references) - valid)
    if missing:
        raise ValueError(f"unknown occupation task references: {missing}")
    if len(set(references)) != len(references):
        raise ValueError("duplicate task reference in the brief table")
    return len(rows), len(references)


def main() -> int:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if inventory.get("record_type") != "occupation_task_opportunity_inventory/v1":
        raise ValueError("unsupported opportunity inventory")
    rows, references = check(BRIEFS.read_text(encoding="utf-8"), inventory)
    print(f"checked {rows} original method briefs with {references} pinned task references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

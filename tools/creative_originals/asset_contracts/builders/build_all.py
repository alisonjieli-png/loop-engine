"""Regenerate every item's fixtures and the fixture list in its item.json contract.

    python3 builders/build_all.py [ITEM ...]

Each builders/<identity>.py defines build(item_dir) -> fixture rows. The rows replace contract.fixtures in the
item's item.json (key order kept), and the fixture entries of its file list are replaced by the files under
fixtures/ (role skill_asset), so the record always lists exactly the fixtures on disk.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAMILY = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FAMILY / "shared"))


def update_contract(item_dir: Path, rows: list) -> None:
    path = item_dir / "item.json"
    if not path.is_file():
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    record["contract"]["fixtures"] = rows
    kept = [row for row in record["files"] if not row["path"].startswith("fixtures/")]
    fixtures = sorted(str(file.relative_to(item_dir)) for file in (item_dir / "fixtures").rglob("*") if file.is_file())
    record["files"] = kept + [{"path": fixture, "role": "skill_asset"} for fixture in fixtures]
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(names) -> int:
    builders = sorted(path.stem for path in HERE.glob("*.py") if path.stem not in ("kit", "build_all"))
    for name in names or builders:
        module = importlib.import_module(name)
        item_dir = FAMILY / "items" / name
        rows = module.build(item_dir)
        update_contract(item_dir, rows)
        print(f"{name}: {len(rows)} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

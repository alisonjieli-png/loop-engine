"""Run the package activation check over the failure laboratory and print one line per fixture.

Offline: no network, no model, no harness process. The check writes only
into a temporary folder that it removes afterwards.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "tools", ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import check_package_activation as activation  # noqa: E402

LABORATORY = Path(__file__).resolve().parent / "packages"


def main():
    with tempfile.TemporaryDirectory() as scratch:
        rows = activation.laboratory_outcome(activation.laboratory_fixtures(LABORATORY), scratch)
    for row in rows:
        expected = ", ".join(row["expected_refusals"]) or "activates"
        print(f"{row['outcome']:4}  {row['fixture']:26}  expected: {expected}")
        if row["outcome"] != activation.PASS:
            print("      missing:", row["missing"], "unexpected:", row["unexpected"])
    failed = [row["fixture"] for row in rows if row["outcome"] != activation.PASS]
    print(json.dumps({"fixtures": len(rows), "passed": len(rows) - len(failed), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

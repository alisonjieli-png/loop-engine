"""Build a pinned O*NET task opportunity subset without promoting skills.

Download the O*NET 31.0 CSV ZIP to `source/db_31_0_csv.zip` first. The source
file is ignored by Git; `task-opportunities.json` keeps a small attributed
selection for research and candidate ideation. Nothing here is a reviewed
harness package or a demand estimate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source" / "db_31_0_csv.zip"
OUTPUT = ROOT / "task-opportunities.json"
SOURCE_SHA256 = "55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd"
SOURCE_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip"
SOURCE_LICENSE_URL = "https://www.onetcenter.org/license_db.html"
OCCUPATION_CODES = (
    "13-1081.00",  # Logisticians
    "13-1082.00",  # Project Management Specialists
    "13-1111.00",  # Management Analysts
    "13-1161.00",  # Market Research Analysts and Marketing Specialists
    "13-2011.00",  # Accountants and Auditors
    "15-1211.00",  # Computer Systems Analysts
    "15-1252.00",  # Software Developers
    "15-2051.00",  # Data Scientists
    "27-3042.00",  # Technical Writers
    "43-4051.00",  # Customer Service Representatives
)


def _rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    raw = archive.read(f"db_31_0_csv/{name}.csv")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def render(source: Path = SOURCE, expected_sha256: str = SOURCE_SHA256) -> str:
    if source.is_symlink() or not source.is_file():
        raise ValueError("pinned O*NET source ZIP is missing or symlinked")
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"O*NET source digest mismatch: {actual}")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        all_occupation_rows = _rows(archive, "occupation_data")
        all_task_rows = _rows(archive, "task_statements")
        all_dwa_rows = _rows(archive, "tasks_to_dwas")
        occupations = {row["O*NET-SOC Code"]: row["Title"] for row in all_occupation_rows}
        task_rows = [row for row in all_task_rows
                     if row["O*NET-SOC Code"] in OCCUPATION_CODES]
        dwa_rows = [row for row in all_dwa_rows
                    if row["O*NET-SOC Code"] in OCCUPATION_CODES]
        rating_rows = [row for row in _rows(archive, "task_ratings")
                       if row["O*NET-SOC Code"] in OCCUPATION_CODES]
    if set(OCCUPATION_CODES) - occupations.keys():
        raise ValueError("selected occupation is absent from the pinned release")

    activities: dict[tuple[str, str], set[str]] = defaultdict(set)
    activity_occupations: dict[str, set[str]] = defaultdict(set)
    for row in dwa_rows:
        code = row["O*NET-SOC Code"]
        task_id = row["Task ID"]
        activity_id = row["DWA Element ID"]
        activities[(code, task_id)].add(activity_id)
        activity_occupations[activity_id].add(code)

    counts = []
    for code in OCCUPATION_CODES:
        matching = [row for row in task_rows if row["O*NET-SOC Code"] == code]
        counts.append({
            "occupation_code": code,
            "occupation_title": occupations[code],
            "task_rows": len(matching),
            "core_task_rows": sum(row["Task Type"] == "Core" for row in matching),
            "task_rating_rows": sum(row["O*NET-SOC Code"] == code for row in rating_rows),
            "task_to_activity_rows": sum(row["O*NET-SOC Code"] == code for row in dwa_rows),
        })

    task_refs = []
    for row in sorted(task_rows, key=lambda item: (item["O*NET-SOC Code"], int(item["Task ID"]))):
        code = row["O*NET-SOC Code"]
        task_id = row["Task ID"]
        task_refs.append({
            "occupation_code": code,
            "task_id": task_id,
            "task_type": row["Task Type"],
            "source_task_text": row["Task"],
            "detailed_work_activity_ids": sorted(activities[(code, task_id)]),
        })

    result = {
        "record_type": "occupation_task_opportunity_inventory/v1",
        "source": {
            "title": "O*NET 31.0 Database",
            "url": SOURCE_URL,
            "sha256": actual,
            "license": "CC BY 4.0",
            "license_url": SOURCE_LICENSE_URL,
            "attribution": "O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration",
            "changes": "Selected ten occupations; joined task IDs to detailed work activity identifiers; calculated counts. Source task text is otherwise unchanged.",
            "endorsement": "The U.S. Department of Labor has not approved, endorsed, or tested this selection or any generated package.",
        },
        "selection_rule": "Ten explicitly listed occupations chosen to span digital, analysis, project, customer and operational work; not a representative or demand-weighted sample.",
        "counts": {
            "source_occupation_rows": len(all_occupation_rows),
            "source_task_rows": len(all_task_rows),
            "source_task_to_activity_rows": len(all_dwa_rows),
            "selected_occupations": len(OCCUPATION_CODES),
            "task_rows": len(task_refs),
            "unique_task_ids": len({row["task_id"] for row in task_refs}),
            "unique_detailed_work_activity_ids": len(activity_occupations),
            "activities_shared_across_selected_occupations": sum(
                len(codes) > 1 for codes in activity_occupations.values()
            ),
        },
        "occupations": counts,
        "task_references": task_refs,
        "state": "research_opportunities_only",
    }
    return json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write", action="store_true")
    choice.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = render()
        if args.write:
            temp = OUTPUT.with_suffix(".json.tmp")
            temp.write_text(expected, encoding="utf-8")
            temp.replace(OUTPUT)
            print(f"wrote {OUTPUT}")
        elif OUTPUT.read_text(encoding="utf-8") != expected:
            raise ValueError("opportunity inventory differs from pinned source")
        else:
            print(f"checked {OUTPUT}")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f"opportunity inventory refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

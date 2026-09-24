"""Expand the pinned occupation inventory for diverse generation.

Reads the same pinned O*NET 31.0 CSV ZIP (digest-checked) that the
September 22 research pinned, selects a stratified set of occupations
across every major SOC group, and emits a task-opportunities JSON with
the same record shape the idea matrix reads: occupations with titles and
task statements with their source text. This is candidate ideation
source data only. O*NET data is used under Creative Commons Attribution
4.0; this tool adds original selection logic and records attribution,
change notice and no implied endorsement. The U.S. Department of Labor,
Employment and Training Administration has not approved, endorsed, or
tested anything built from this selection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/occupation-grid-research-2026-09-22/source/db_31_0_csv.zip"
OUTPUT = ROOT / "artifacts/occupation-grid-research-2026-09-22/task-opportunities-expanded.json"
SOURCE_SHA256 = "55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd"
SOURCE_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip"
SOURCE_LICENSE_URL = "https://www.onetcenter.org/license_db.html"
RECORD_TYPE = "onet_task_opportunities/v2"

#: How many occupations to take per SOC major group. The full database
#: holds 1,016 occupations across 23 major groups; a stratified sample
#: spreads generation grounding across the whole economy instead of
#: ten occupations.
PER_GROUP = 8
#: Occupations already in the September 22 selection, kept so the old
#: artifact stays the record of that selection.
EXISTING = (
    "13-1081.00", "13-1082.00", "13-1111.00", "13-1161.00", "13-2011.00",
    "15-1211.00", "15-1252.00", "15-2051.00", "27-3042.00", "43-4051.00",
)


class InventoryError(ValueError):
    """The source or the selection request is invalid."""


def _rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    raw = archive.read(f"db_31_0_csv/{name}.csv")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def render(source: Path = SOURCE, per_group: int = PER_GROUP) -> str:
    if source.is_symlink() or not source.is_file():
        raise InventoryError("pinned O*NET source ZIP is missing or symlinked")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise InventoryError("O*NET source digest mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        occupations = _rows(archive, "occupation_data")
        task_rows = _rows(archive, "task_statements")

    tasks_by_code: dict[str, list[dict[str, str]]] = {}
    for row in task_rows:
        tasks_by_code.setdefault(row["O*NET-SOC Code"], []).append(row)

    # Stratify by SOC major group (the first two digits of the code),
    # keeping occupations that have task statements, in database order.
    by_group: dict[str, list[dict[str, str]]] = {}
    for occupation in occupations:
        code = occupation["O*NET-SOC Code"]
        if code not in tasks_by_code:
            continue
        major = code.split("-")[0]
        by_group.setdefault(major, []).append(occupation)

    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for major in sorted(by_group):
        pool = [row for row in by_group[major] if row["O*NET-SOC Code"] not in EXISTING]
        for row in pool[:per_group]:
            selected.append(row)
            seen.add(row["O*NET-SOC Code"])

    occupations_out = []
    tasks_out = []
    for occupation in selected:
        code = occupation["O*NET-SOC Code"]
        occupations_out.append({
            "occupation_code": code,
            "occupation_title": occupation["Title"],
            "task_rows": len(tasks_by_code[code]),
        })
        for row in tasks_by_code[code]:
            tasks_out.append({
                "occupation_code": code,
                "source_task_text": row["Task"],
                "task_id": row["Task ID"],
                "task_type": row["Task Type"],
                "detailed_work_activity_ids": [],
            })

    record = {
        "record_type": RECORD_TYPE,
        "selection_rule": (
            f"Stratified {per_group} occupations per SOC major group with "
            "task statements, excluding the ten occupations of the September 22 "
            "selection, in database order. Original selection logic; no demand "
            "estimate and no method claim."
        ),
        "source": {
            "url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "license_url": SOURCE_LICENSE_URL,
            "license": "CC BY 4.0 for the applicable database files",
            "attribution": (
                "O*NET 31.0 Database by the U.S. Department of Labor, "
                "Employment and Training Administration, used under CC BY 4.0. "
                "Derived selection; the original database has been filtered "
                "and only task statements, titles and codes are carried. "
                "No implied endorsement."
            ),
        },
        "counts": {
            "selected_occupations": len(occupations_out),
            "task_rows": len(tasks_out),
            "soc_major_groups": len({row["occupation_code"].split("-")[0]
                                     for row in occupations_out}),
        },
        "occupations": occupations_out,
        "task_references": tasks_out,
    }
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--per-group", type=int, default=PER_GROUP)
    args = parser.parse_args(argv)
    if args.output.exists() and args.output.resolve() == OUTPUT.resolve() \
            and args.output.is_file():
        raise InventoryError("output_already_exists")
    args.output.write_text(render(per_group=args.per_group), encoding="utf-8")
    record = json.loads(args.output.read_text(encoding="utf-8"))
    counts = record["counts"]
    print(f"wrote {counts['selected_occupations']} occupations across "
          f"{counts['soc_major_groups']} SOC groups with {counts['task_rows']} "
          f"task statements to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
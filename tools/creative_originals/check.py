"""Check a whole family the way the line and qualification will: records, packages, package tests, duplicates.

    PYTHONPATH=src:. python -m tools.creative_originals.check --family godot_shaders \
        --evidence /run/media/username/baltor-offload/creative-3d-20261009/evidence \
        --packages /run/media/username/baltor-offload/creative-3d-20261009/packages [--item ID ...]

For every item: the item record reads, the package assembles (with its evidence when the family has a verifier),
and the package's own root tests pass under the isolated system interpreter. Across items: no two items share a
title, and no two items share the bytes of a non-shared file (an exact copy is one capability, not two). The report
lists every failure by item; the exit status is non-zero when any item fails.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path

from .assemble import assemble_and_test, repository_licence
from .records import CreativeRecordError, item_identities, read_family, read_item

ROOT = Path(__file__).resolve().parent


def check_item(family_directory: Path, family: dict, identity: str, evidence: "Path | None", packages: Path) -> dict:
    try:
        evidence_bytes = preview = None
        if family["native_verifier"] is not None:
            record = (evidence / family["family"] / f"{identity}.json") if evidence else None
            if record is None or not record.is_file():
                return {"identity": identity, "state": "failed", "reason": "evidence_missing"}
            evidence_bytes = record.read_bytes()
            image = record.with_suffix(".png")
            preview = image.read_bytes() if image.is_file() else None
        result = assemble_and_test(family_directory, identity, packages / family["family"], evidence=evidence_bytes,
                                   preview=preview, licence=repository_licence())
    except CreativeRecordError as error:
        return {"identity": identity, "state": "failed", "reason": error.reason, "detail": error.detail}
    row = {"identity": identity, "state": result["state"], "files": result.get("files"), "bytes": result.get("bytes")}
    if result["state"] != "passed":
        row["reason"] = result.get("reason", "package_tests_failed")
        row["output_tail"] = result.get("output_tail", "")[-1500:]
    return row


def duplicates(family_directory: Path, family: dict, identities: list) -> list:
    titles, digests, problems = collections.defaultdict(list), collections.defaultdict(list), []
    for identity in identities:
        try:
            item = read_item(family_directory, identity, family)
        except CreativeRecordError:
            continue
        titles[item["title"].lower()].append(identity)
        for row in item["files"]:
            if row["path"] == "README.md":
                continue
            data = (family_directory / "items" / identity / row["path"]).read_bytes()
            digests[hashlib.sha256(data).hexdigest()].append(f"{identity}/{row['path']}")
    problems += [{"reason": "title_repeated", "items": names} for names in titles.values() if len(names) > 1]
    problems += [{"reason": "file_bytes_repeated", "files": names} for names in digests.values() if len(names) > 1]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", required=True)
    parser.add_argument("--root", type=Path, default=ROOT, help="the folder holding the families")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--item", action="append", default=[])
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args(argv)
    family_directory = args.root.resolve() / args.family
    family = read_family(family_directory)
    identities = args.item or item_identities(family_directory)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.jobs, 8))) as pool:
        for row in pool.map(lambda identity: check_item(family_directory, family, identity, args.evidence,
                                                        args.packages.resolve()), identities):
            rows.append(row)
            if row["state"] != "passed":
                print(json.dumps(row), flush=True)
    problems = duplicates(family_directory, family, identities)
    report = {"family": args.family, "items": len(rows), "passed": sum(row["state"] == "passed" for row in rows),
              "failed": [row["identity"] for row in rows if row["state"] != "passed"], "duplicates": problems,
              "files": sum(row.get("files") or 0 for row in rows), "bytes": sum(row.get("bytes") or 0 for row in rows)}
    print(json.dumps(report, indent=1))
    return 0 if not report["failed"] and not problems else 1


if __name__ == "__main__":
    sys.exit(main())

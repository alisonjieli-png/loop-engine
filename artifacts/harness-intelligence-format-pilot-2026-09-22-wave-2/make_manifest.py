"""Bind every source and support file in this candidate batch to an exact role and digest."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path

PACKAGE_IDS = {
    "audit-join-cardinality",
    "audit-zip-package",
    "audit-text-encoding",
}
OTHER_FILES = {
    "INITIAL-FAILED-CONTROLS-2026-09-22.md": "historical_failure_evidence",
    "README.md": "batch_document",
    "SECOND-REVIEW-OVERCOUNT-2026-09-22.md": "historical_failure_evidence",
    "candidate-items.json": "candidate_metadata",
    "make_manifest.py": "local_manifest_builder",
    "manifest-initial-failed-2026-09-22.json": "historical_failed_manifest",
    "manifest-successor-overcount-2026-09-22.json": "historical_failed_manifest",
    "test_make_manifest.py": "batch_test",
}
INITIAL_FAILED_SHA256 = (
    "92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e"
)
OVERCOUNT_SHA256 = "86e6b56d2ce8fb8bafe91622583a9d16f837e31c139f508e24ae8360cdb0c8a4"


def _catalogue(root: Path) -> list[dict]:
    catalogue = json.loads((root / "candidate-items.json").read_text(encoding="utf-8"))
    if catalogue.get("schema") != "first_party_multifile_harness_candidates/v1":
        raise ValueError("candidate_catalogue_schema_mismatch")
    if catalogue.get("approval_state") != "candidate_only":
        raise ValueError("candidate_approval_state_mismatch")
    items = catalogue.get("items")
    if not isinstance(items, list) or {item.get("id") for item in items} != PACKAGE_IDS:
        raise ValueError("candidate_id_set_mismatch")
    if len(items) != len(PACKAGE_IDS):
        raise ValueError("duplicate_candidate_id")
    return items


def build_manifest(root: Path) -> dict:
    root = root.resolve(strict=True)
    historical = (root / "manifest-initial-failed-2026-09-22.json").read_bytes()
    if hashlib.sha256(historical).hexdigest() != INITIAL_FAILED_SHA256:
        raise ValueError("historical_failed_manifest_changed")
    overcount = (root / "manifest-successor-overcount-2026-09-22.json").read_bytes()
    if hashlib.sha256(overcount).hexdigest() != OVERCOUNT_SHA256:
        raise ValueError("historical_overcount_manifest_changed")
    items = _catalogue(root)
    roles = dict(OTHER_FILES)
    for item in items:
        package_id = item["id"]
        prefix = f"packages/{package_id}/"
        delivery = item.get("delivery_files")
        if (
            not isinstance(delivery, list)
            or len(delivery) != 3
            or len(set(delivery)) != 3
        ):
            raise ValueError("delivery_file_set_mismatch")
        expected_delivery = {
            prefix + "SKILL.md": "skill_entry",
            prefix
            + f"scripts/{package_id.replace('-', '_')}.py": "implementation_script",
            prefix + "scripts/confined_input.py": "reused_confinement_helper",
        }
        if set(delivery) != set(expected_delivery):
            raise ValueError("delivery_file_set_mismatch")
        roles.update(expected_delivery)
        review = f"reviews/{package_id}.md"
        test = f"tests/test_{package_id.replace('-', '_')}.py"
        if item.get("review_note") != review or item.get("verification") != test:
            raise ValueError("review_or_test_file_mismatch")
        roles[review] = "producer_note"
        roles[test] = "known_wrong_tests"
    found: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"symlink_in_candidate_tree:{relative}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f"nonregular_file_in_candidate_tree:{relative}")
        if relative != "manifest.json":
            found.add(relative)
    if found != set(roles):
        raise ValueError(
            f"candidate_tree_mismatch:missing={sorted(set(roles) - found)}:extra={sorted(found - set(roles))}"
        )
    rows = []
    for relative in sorted(found):
        data = (root / relative).read_bytes()
        rows.append(
            {
                "path": relative,
                "role": roles[relative],
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    by_path = {row["path"]: row for row in rows}
    trees = {
        item["id"]: [by_path[path] for path in sorted(item["delivery_files"])]
        for item in sorted(items, key=lambda item: item["id"])
    }
    delivery_rows = [
        row
        for row in rows
        if row["role"]
        in {"skill_entry", "implementation_script", "reused_confinement_helper"}
    ]
    helpers = {
        row["sha256"] for row in rows if row["role"] == "reused_confinement_helper"
    }
    if len(helpers) != 1:
        raise ValueError("reused_helper_bytes_diverged")
    return {
        "schema": "first_party_multifile_manifest/v1",
        "approval_state": "candidate_only",
        "logical_packages": len(items),
        "physical_delivery_paths": len(delivery_rows),
        "distinct_delivery_body_digests": len({row["sha256"] for row in delivery_rows}),
        "all_tracked_files_excluding_manifest": len(rows),
        "reused_helper_sha256": next(iter(helpers)),
        "package_trees": trees,
        "file_inventory": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest(args.root)
    target = args.root / "manifest.json"
    if args.write:
        target.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        if (
            not target.is_file()
            or json.loads(target.read_text(encoding="utf-8")) != manifest
        ):
            raise SystemExit("manifest_mismatch")
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "logical_packages",
                    "physical_delivery_paths",
                    "distinct_delivery_body_digests",
                    "all_tracked_files_excluding_manifest",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

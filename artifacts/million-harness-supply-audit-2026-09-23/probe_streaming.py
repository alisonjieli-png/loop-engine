"""Reproduce an offline metadata-volume probe without retaining fake supply.

The fixture consists only of bundle item metadata and one repeated file digest.
It contains no package bodies, approvals or active catalogue state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--items", type=int, required=True)
    parser.add_argument("--per-bundle", type=int, default=200_000)
    parser.add_argument("--address-space-mib", type=int, default=768)
    args = parser.parse_args()
    if not 1 <= args.items <= 2_000_000 or not 1 <= args.per_bundle <= 200_000:
        parser.error("one to two million metadata rows, at most 200,000 per bundle")
    if not 128 <= args.address_space_mib <= 1024:
        parser.error("the address-space ceiling is between 128 and 1024 MiB")
    resource.setrlimit(resource.RLIMIT_AS, (args.address_space_mib * 1024 * 1024,) * 2)
    tool = Path(__file__).resolve().parent / "audit_supply.py"
    tool_sha = hashlib.sha256(tool.read_bytes()).hexdigest()
    repo = args.repo.resolve(strict=True)
    repeated_digest = hashlib.sha256(b"synthetic metadata only").hexdigest()
    source_rows = []
    with tempfile.TemporaryDirectory(prefix="harness-supply-scale-") as directory:
        root = Path(directory)
        folders = []
        start_generation = time.monotonic()
        for batch, offset in enumerate(range(0, args.items, args.per_bundle)):
            count = min(args.per_bundle, args.items - offset)
            folder = root / f"bundle-{batch:04d}"
            folder.mkdir()
            folders.append(folder)
            checksum = hashlib.sha256()
            total_bytes = 0
            with (folder / "items.jsonl").open("xb") as output:
                for index in range(count):
                    row = {
                        "record_type": "catalogue_bundle_item/v1",
                        "reference": {
                            "identity": f"synthetic-{offset + index:09d}",
                            "kind": "skill",
                        },
                        "package": {
                            "files": [
                                {
                                    "path": "SKILL.md",
                                    "digest": repeated_digest,
                                    "size_bytes": 23,
                                    "role": "skill_definition",
                                }
                            ]
                        },
                    }
                    line = (
                        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                    ).encode()
                    output.write(line)
                    checksum.update(line)
                    total_bytes += len(line)
            header = {
                "record_type": "catalogue_release_bundle/v1",
                "items": count,
                "items_bytes": total_bytes,
                "items_digest": checksum.hexdigest(),
            }
            (folder / "bundle.json").write_text(
                json.dumps(header, sort_keys=True) + "\n", encoding="utf-8"
            )
            source_rows.append(
                {
                    "items": count,
                    "items_bytes": total_bytes,
                    "items_sha256": checksum.hexdigest(),
                }
            )
        generation_seconds = time.monotonic() - start_generation
        command = [
            sys.executable,
            "-B",
            str(tool),
            "--repo",
            str(repo),
            "--out-dir",
            str(args.out_dir),
        ]
        for folder in folders:
            command.extend(("--bundle-dir", str(folder)))
        start_audit = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        audit_seconds = time.monotonic() - start_audit
        if result.returncode:
            sys.stderr.write(result.stderr[-2000:])
            return result.returncode
        report_path = args.out_dir / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        summary = {
            "record_type": "harness_supply_scale_probe/v1",
            "synthetic_metadata_only": True,
            "tool_sha256": tool_sha,
            "repository_revision": report["repository_revision"],
            "source_rows": source_rows,
            "address_space_ceiling_mib": args.address_space_mib,
            "peak_child_rss_kib": resource.getrusage(
                resource.RUSAGE_CHILDREN
            ).ru_maxrss,
            "generation_seconds": round(generation_seconds, 3),
            "audit_seconds": round(audit_seconds, 3),
            "observed": {
                key: report["prospective_bundles"][key]
                for key in (
                    "logical_records",
                    "physical_file_paths",
                    "distinct_file_sha256",
                    "active_release_credit",
                )
            },
            "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "limits": "No body blobs, rights, approval, active release, native loading or task benefit.",
        }
        (args.out_dir / "scale-probe.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "items": args.items,
                    "audit_seconds": summary["audit_seconds"],
                    "peak_child_rss_kib": summary["peak_child_rss_kib"],
                    "active_release_credit": summary["observed"][
                        "active_release_credit"
                    ],
                    "receipt": str(args.out_dir),
                },
                sort_keys=True,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Known-wrong controls for the offline supply inventory."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import audit_supply as audit


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


class SupplyAuditTests(unittest.TestCase):
    def test_changed_payload_fails_before_it_can_be_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "packages/method/SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"reviewed")
            digest = hashlib.sha256(b"reviewed").hexdigest()
            audit._body(root, "packages/method/SKILL.md", digest, 8)
            target.write_bytes(b"replaced")
            with self.assertRaisesRegex(audit.AuditError, "changed_body"):
                audit._body(root, "packages/method/SKILL.md", digest, 8)

    def test_symlinked_ancestor_cannot_contribute_a_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside").mkdir()
            (root / "outside/secret.md").write_bytes(b"secret")
            (root / "packages").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaisesRegex(audit.AuditError, "symlink_in_input_path"):
                audit._body(
                    root, "packages/secret.md", hashlib.sha256(b"secret").hexdigest(), 6
                )

    def test_one_file_bound_to_two_clients_is_one_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = "context/shared/AGENTS.md"
            payload = b"one native instruction body"
            target = root / path
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            write_json(
                root / "candidate-items.json",
                {
                    "record_type": "heterogeneous_harness_candidate_catalog/v1",
                    "approval_state": "none",
                    "items": [
                        {
                            "id": "one-method",
                            "kind": "native_step_instructions",
                            "delivery_variants": {"codex": [path], "opencode": [path]},
                        }
                    ],
                },
            )
            manifest = {
                "approval_state": "none",
                "rights_state": "pending_independent_review",
                "delivery_payload_file_count": 1,
                "entries": [
                    {
                        "path": path,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload),
                        "file_role": "delivery_payload",
                    }
                ],
            }
            db = sqlite3.connect(":memory:")
            audit._db(db)
            variants, bindings = audit._mixed_batch(db, root, manifest, [])
            self.assertEqual((variants, bindings), (2, 2))
            self.assertEqual(db.execute("SELECT count(*) FROM files").fetchone()[0], 1)
            self.assertEqual(
                db.execute("SELECT count(*) FROM packages").fetchone()[0], 1
            )
            db.close()

    def test_conflicting_unmerged_reviews_hold_identity_without_approval_credit(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            starter = root / "examples/29_intelligence_service/starter-catalogue"
            body = b"candidate text"
            digest = hashlib.sha256(body).hexdigest()
            (starter / "bodies").mkdir(parents=True)
            (starter / "bodies/a.md").write_bytes(body)
            write_json(
                starter / "items.json",
                {
                    "record_type": "starter_catalogue_candidate_items/v2",
                    "source_revision": "revision",
                    "items": [
                        {
                            "reference": {
                                "identity": "a",
                                "kind": "skill",
                                "digest": digest,
                                "size_bytes": len(body),
                                "source_ref": "first-party@example",
                            },
                            "body_path": "bodies/a.md",
                        }
                    ],
                },
            )
            write_json(
                starter / "reviews.json",
                {
                    "record_type": "starter_catalogue_independent_review/v2",
                    "catalogue_source_revision": "revision",
                    "rows": [
                        {
                            "identity": "a",
                            "outcome": "not_reviewed",
                            "body_digest": None,
                            "approval_ref": "",
                            "decisions": [],
                        }
                    ],
                },
            )
            write_json(
                starter / "host-release/manifest.json",
                {
                    "record_type": "host_attested_intelligence_manifest/v1",
                    "items": [],
                },
            )
            (root / "artifacts").mkdir()
            rejected = root / "new-review/panel-rejected.json"
            approved = root / "historical-review/reviews.json"
            for path, outcome in ((rejected, "rejected"), (approved, "approved")):
                revision = "f29bddc" if outcome == "rejected" else "0cf19eb"
                reviewed_body = (
                    f"method\nWritten for this catalogue at revision {revision}.\n"
                ).encode()
                body_path = path.parent / "bodies/a.md"
                body_path.parent.mkdir(parents=True)
                body_path.write_bytes(reviewed_body)
                reviewed_digest = hashlib.sha256(reviewed_body).hexdigest()
                write_json(
                    path,
                    {
                        "record_type": audit.PANEL
                        if outcome == "rejected"
                        else audit.HISTORICAL_REVIEW,
                        "rows": [
                            {
                                "identity": "a",
                                "body_sha256"
                                if outcome == "rejected"
                                else "body_digest": reviewed_digest,
                                "body_size_bytes": len(reviewed_body),
                                "body_path": "bodies/a.md",
                                "outcome": outcome,
                            }
                        ],
                        "totals": {"disagreements": 0},
                    },
                )
            out = root / "audit-receipt"
            report = audit.audit(root, out, panel_paths=[rejected, approved])
            self.assertEqual(report["local"]["recorded_approved"], 0)
            self.assertEqual(report["panels"]["conflicting_identity_count"], 1)
            self.assertEqual(
                report["panels"]["same_body_after_closing_anchor_conflict_count"], 1
            )
            self.assertEqual(report["panels"]["approval_credit_from_panels"], 0)
            queued = json.loads(
                (out / "review-queue.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual(
                queued["next_gate"], "adjudicate_conflicting_review_records"
            )
            self.assertFalse(queued["approval_ready"])

    def test_prospective_bundle_copy_does_not_become_active_supply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            digest = hashlib.sha256(b"same file").hexdigest()
            rows = [
                {
                    "record_type": audit.BUNDLE_ITEM,
                    "reference": {"identity": identity, "kind": "skill"},
                    "package": {
                        "files": [
                            {
                                "path": "SKILL.md",
                                "digest": digest,
                                "size_bytes": 9,
                                "role": "skill_definition",
                            }
                        ]
                    },
                }
                for identity in ("one", "two")
            ]
            raw = b"".join(
                json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows
            )
            (folder / "items.jsonl").write_bytes(raw)
            write_json(
                folder / "bundle.json",
                {
                    "record_type": audit.BUNDLE,
                    "items": 2,
                    "items_bytes": len(raw),
                    "items_digest": hashlib.sha256(raw).hexdigest(),
                },
            )
            db = sqlite3.connect(":memory:")
            audit._db(db)
            bundles = audit._bundle_lines(db, [folder], [])
            self.assertEqual(bundles[0]["active_release_proven"], False)
            self.assertEqual(
                db.execute("SELECT count(*) FROM packages").fetchone()[0], 2
            )
            self.assertEqual(
                db.execute("SELECT count(DISTINCT digest) FROM files").fetchone()[0], 1
            )
            db.close()

    def test_outside_ingestion_leads_cannot_inflate_approved_packages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run-report.json"
            write_json(
                path,
                {
                    "record_type": "library_ingestion_run_report/v1",
                    "approved": False,
                    "hosted_publication": False,
                    "sources": [{"source_id": "one"}],
                    "counts": {
                        "discovered": 12,
                        "candidates": 10,
                        "batch_refusals": 2,
                        "staged_rows": 8,
                        "staged_by_kind": {"skill": 8},
                    },
                },
            )
            rows = audit._ingestion_reports([path], [])
            self.assertEqual(rows[0]["staged_rows"], 8)
            self.assertEqual(rows[0]["approved_package_credit"], 0)
            self.assertIsNone(rows[0]["distinct_native_file_count"])
            record = json.loads(path.read_text())
            record["approved"] = True
            write_json(path, record)
            with self.assertRaisesRegex(
                audit.AuditError, "ingestion_report_state_or_counts_mismatch"
            ):
                audit._ingestion_reports([path], [])

    def test_duplicate_json_field_refused(self) -> None:
        with self.assertRaisesRegex(audit.AuditError, "duplicate_json_field"):
            audit._json(b'{"record_type":"x","record_type":"y"}', label="planted")


if __name__ == "__main__":
    unittest.main()

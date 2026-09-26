"""Checks for combining reviewed catalogue folders into one release snapshot.

```text
Combined release folder
├── the starter rows keep their Verified tier and name their reviewer group
├── an added Community row keeps its tier, decisions and digest, and the bundle builds
├── a withdrawn identity leaves the snapshot and is listed with its note
├── a relabelled source revision must hold the same cited bytes
├── a Verified row judged by only part of its group, or naming an unknown group, is refused
└── a long cited path keeps its last whole parts within the keyword limit
```
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import build_catalogue_release_bundle as bundle_tool  # noqa: E402
import combine_reviewed_catalogues as combine  # noqa: E402
from build_host_catalogue_manifest import ManifestBuildError  # noqa: E402
from loop_engine.core.harness_intelligence import HarnessIntelligenceItem  # noqa: E402

STARTER = HERE.parent / "examples/29_intelligence_service/starter-catalogue"
WITHDRAWN = "normalize_phone_numbers"
BODY = (b"---\nname: check-a-sum\ndescription: Use when a list of integers must be summed and checked.\n"
        b"license: MIT\n---\n\n# Check a sum\n\nRecompute the sum and report it only when both agree.\n")
SOURCE = "artifacts/review-throughput-2026-09-24/overnight-attribution-v2/ideas/" + "a-very-long-idea-name-" * 3 + ".json"


def community_folder(root: Path) -> Path:
    """One approved Community row judged by one reviewer the starter panel does not name."""
    folder = root / "community"
    (folder / "bodies").mkdir(parents=True)
    (folder / "bodies" / "check_a_sum.md").write_bytes(BODY)
    digest = hashlib.sha256(BODY).hexdigest()
    item = HarnessIntelligenceItem(identity="check_a_sum", kind="skill", purpose="Check a sum before reporting it.",
                                   digest=digest, size_bytes=len(BODY), source_layer="harness_local",
                                   source_ref=SOURCE + "@" + "1" * 40, license_name="MIT",
                                   declared_effects=("reads_fs",), styles=("claude", "codex"))
    items = {"record_type": combine.ITEMS_RECORD, "source_revision": "1" * 40, "previous_source_revisions": [],
             "source_digests": {}, "publication": "not_published",
             "items": [{"reference": item.reference(), "body_path": "bodies/check_a_sum.md", "lifecycle": "candidate",
                        "license_state": "declared", "tier": "community",
                        "attributes": {"step_functions": ["verification"]},
                        "attribute_engines": {"step_functions": {"engine_id": "step_function_rules",
                                                                 "engine_version": "1.0.0"}}}]}
    review = {"record_type": combine.REVIEW_RECORD, "recorded_at": "2026-09-25", "catalogue_source_revision": "1" * 40,
              "reviewers": [{"reviewer_id": "claude_code.subscription", "label": "claude-opus-5-5 (anthropic)",
                             "lens": "provenance_licence_and_safety", "produced_any_item_under_review": False}],
              "rows": [{"identity": "check_a_sum", "body_path": "bodies/check_a_sum.md", "body_digest": digest,
                        "body_size_bytes": len(BODY), "declared_license": "MIT", "source_layer": "context_intelligence",
                        "decisions": [{"reviewer_id": "claude_code.subscription", "decision": "approve", "reason": ""}],
                        "outcome": "approved", "approval_state": "reviewed", "rule_applied": "community_tier_rule",
                        "approval_ref": "reviews.json#check_a_sum", "tier": "community"}],
              "totals": {"items_in_catalogue": 1, "items_reviewed": 1, "approved": 1, "approved_as_reviewed": 1,
                         "approved_by_carry": 0, "rejected": 0, "carry_refused": 0, "not_reviewed": 0}}
    (folder / "items.json").write_text(json.dumps(items))
    (folder / "reviews.json").write_text(json.dumps(review))
    return folder


class CombineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def combined(self, **changes) -> Path:
        options = argparse.Namespace(base=STARTER, base_group="starter-panel-2026-09-21",
                                     add=[community_folder(self.root)], withdraw=[f"{WITHDRAWN}=measured harm"],
                                     relabel_revision="", output=self.root / "combined")
        for key, value in changes.items():
            setattr(options, key, value)
        combine.combine(options)
        return Path(options.output)

    def test_the_snapshot_keeps_tiers_and_builds_without_the_withdrawn_item(self):
        folder = self.combined()
        review = json.loads((folder / "reviews.json").read_text())
        rows = {row["identity"]: row for row in review["rows"]}
        self.assertNotIn(WITHDRAWN, rows)
        self.assertEqual(review["withdrawn"], [{"identity": WITHDRAWN, "note": "measured harm"}])
        starter = next(row for row in rows.values() if row["outcome"] == "approved" and row["identity"] != "check_a_sum")
        self.assertEqual((starter["tier"], starter["reviewer_group"]), ("verified", "starter-panel-2026-09-21"))
        self.assertEqual(rows["check_a_sum"]["tier"], "community")
        schema, lines, _payloads = bundle_tool.build(folder, accepted_licenses=("MIT",))
        tiers = {line["reference"]["identity"]: line["attributes"]["tier"] for line in lines}
        self.assertEqual(tiers["check_a_sum"], "community")
        self.assertEqual(tiers[starter["identity"]], "verified")
        self.assertNotIn(WITHDRAWN, tiers)
        self.assertTrue(any(attribute.name == "tier" for attribute in schema.attributes))
        # The step function tags of an added row travel through the snapshot into the bundle line, and the
        # combined schema declares the attribute even when the base folder's schema does not (S-6.206).
        self.assertTrue(any(attribute.name == "step_functions" for attribute in schema.attributes))
        tags = {line["reference"]["identity"]: line["attributes"].get("step_functions") for line in lines}
        self.assertEqual(tags["check_a_sum"], ["verification"])
        self.assertIsNone(tags[starter["identity"]], "a starter row written before the tagger carries no tag")
        dates = {line["reference"]["identity"]: line["attributes"]["catalogued_on"] for line in lines}
        self.assertEqual(dates["check_a_sum"], "2026-09-25", "a Community row keeps its own review date")
        self.assertEqual(dates[starter["identity"]], "2026-09-21", "a starter row keeps the starter review date")

    def test_a_verified_row_needs_every_reviewer_of_its_group_and_a_declared_group(self):
        folder = self.combined()
        review = json.loads((folder / "reviews.json").read_text())
        target = next(row for row in review["rows"] if row["outcome"] == "approved" and row.get("tier") == "verified")
        cases = {"part of the group": lambda row: row["decisions"].pop(),
                 "an undeclared group": lambda row: row.update(reviewer_group="another-panel")}
        for name, change in cases.items():
            with self.subTest(case=name):
                broken = json.loads(json.dumps(review))
                change(next(row for row in broken["rows"] if row["identity"] == target["identity"]))
                (folder / "reviews.json").write_text(json.dumps(broken))
                with self.assertRaises(ManifestBuildError) as held:
                    bundle_tool.build(folder, accepted_licenses=("MIT",))
                self.assertEqual(held.exception.code, "review_record_inconsistent")

    def test_a_relabel_needs_the_same_cited_bytes_at_both_revisions(self):
        repository = self.root / "repository"
        repository.mkdir()
        git = ["git", "-C", str(repository)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run([*git, "config", "user.name", "Fixture"], check=True)
        cited = repository / SOURCE
        cited.parent.mkdir(parents=True)
        revisions = []
        for text in ("first", "second"):
            cited.write_text(text)
            subprocess.run([*git, "add", "."], check=True)
            subprocess.run([*git, "commit", "-q", "-m", text], check=True)
            revisions.append(subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True,
                                            check=True).stdout.strip())
        folder = community_folder(self.root / "other")
        items = json.loads((folder / "items.json").read_text())
        items["items"][0]["reference"]["source_ref"] = f"{SOURCE}@{revisions[0]}"
        (folder / "items.json").write_text(json.dumps(items))
        with mock.patch.object(combine, "REPOSITORY", repository):
            with self.assertRaisesRegex(combine.CombineError, "relabel_changes_bytes"):
                self.combined(add=[folder], relabel_revision=f"{revisions[0]}={revisions[1]}")

    def test_a_folder_inside_this_repository_is_refused(self):
        with self.assertRaisesRegex(combine.CombineError, "folder_inside_repository"):
            self.combined(output=HERE.parent / "artifacts" / "combined-check")

    def test_a_long_cited_path_keeps_its_last_whole_parts(self):
        short = "src/loop_engine/core/service_runtime/catalogue_packages.py"
        self.assertEqual(bundle_tool.cited_source(short + "@" + "0" * 40), short)
        kept = bundle_tool.cited_source(SOURCE + "@" + "1" * 40)
        self.assertLessEqual(len(kept), bundle_tool.KEYWORD_LIMIT)
        self.assertTrue(SOURCE.endswith(kept))
        self.assertTrue(kept.startswith("ideas/") or kept.startswith("overnight-attribution-v2/"))


if __name__ == "__main__":
    unittest.main()

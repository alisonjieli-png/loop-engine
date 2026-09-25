"""Checks for tools/write_reviewed_catalogue.py: a reviewed folder the release tools accept, with its tier.

```text
Reviewed catalogue writer
├── a Community approval by one non-producer family is written with its tier, and
│   the release bundle builder accepts the folder and carries the tier
├── a rejection is written as rejected with its reason and is never bundled
├── a named reviewer of the producer's family leaves the item out
├── a verdict from a scripted fixture reviewer leaves the item out unless a check allows it
└── a folder inside this public repository is refused
```

Every verdict comes from the real review panel run over fixture reviewers into a
real ledger; no model is called.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent))

import build_catalogue_release_bundle as bundle_tool  # noqa: E402
import write_reviewed_catalogue as writer  # noqa: E402
from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, native, native_profile  # noqa: E402
from candidate_review import panel as panel_module  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.reviewers import PROVIDER_REPORTED, ReviewerAttempt, Usage  # noqa: E402
from candidate_review.reviewers.fixture import FixtureReviewer  # noqa: E402
from loop_engine.core.harness_intelligence import HarnessIntelligenceItem  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile  # noqa: E402

ROOT = HERE.parent
SOURCE = "src/loop_engine/core/service_runtime/catalogue_packages.py"
REVISION = "9c57c9a4c813578bffa504108ef9d785b308bb86"
PANEL = json.loads((HERE / "candidate_review/resources/panel.json").read_text())
SKILL = (b"---\nname: check-a-sum\ndescription: Use when a supplied list of integers must be summed and the sum "
         b"checked against a recomputation before it is reported.\nlicense: MIT\n---\n\n# Check a sum\n\n"
         b"Read the supplied integers, recompute their sum and report it only when both agree.\n")


def skill_catalogue(folder: Path, identity: str, family: str) -> None:
    """One native candidate: a one-file skill package, produced by a declared family."""
    package = CataloguePackage((CataloguePackageFile("SKILL.md", hashlib.sha256(SKILL).hexdigest(), len(SKILL),
                                                     "text/markdown", "skill_definition"),))
    producer = {"producer_identity": "fixture producer", "family": family, "method_identity": "fixture_method/v1"}
    digests = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (SOURCE, "LICENSE")}
    item = HarnessIntelligenceItem(identity=identity, kind="skill", purpose="Check a sum before reporting it.",
                                   digest=package.package_digest, size_bytes=package.served_size,
                                   source_layer="harness_local", source_ref=SOURCE + "@" + REVISION,
                                   license_name="MIT", declared_effects=("reads_fs",), styles=("claude", "codex"))
    row = {"reference": item.reference(), "body_path": f"bodies/{identity}.package.json",
           "package": package.to_dict(), "package_root": f"packages/{identity}", "producer": producer,
           "dependencies": []}
    spec = {"id": identity, "layer": "context", "family": "original_native_skill", "title": "Check a sum",
            "tags": ["sum"], "text": "# Search metadata only\n", "sources": [SOURCE, "LICENSE"], "symbols": [],
            "kind": "skill", "purpose": item.purpose, "styles": ["claude", "codex"], "dependencies": [],
            "producer": producer, "declared_effects": ["reads_fs"], "package": package.to_dict(),
            "package_digest": package.package_digest, "package_root": row["package_root"],
            "body_path": row["body_path"],
            "provenance": {"authoring": "original_assistant_authored", "source_revision": REVISION,
                           "source_digests": {SOURCE: digests[SOURCE]},
                           "license": {"expression": "MIT", "path": "LICENSE", "sha256": digests["LICENSE"]}}}
    (folder / row["package_root"]).mkdir(parents=True)
    (folder / row["package_root"] / "SKILL.md").write_bytes(SKILL)
    (folder / "bodies").mkdir()
    (folder / row["body_path"]).write_bytes(package.document())
    (folder / "items.json").write_text(json.dumps({"record_type": native.NATIVE_ITEMS, "source_revision": REVISION,
                                                   "source_digests": digests, "publication": "not_published",
                                                   "items": [row]}))
    (folder / "specifications-001.json").write_text(json.dumps({"record_type": native.NATIVE_SPECIFICATIONS,
                                                                "population": 1, "populations": 1,
                                                                "specifications": [spec]}))


def fixture_panel(path: Path) -> config.PanelConfiguration:
    value = copy.deepcopy(PANEL)
    value["installations"] = [{"record_type": config.INSTALLATION_RECORD, "installation_id": name,
                               "engine_kind": "fixture", "family": family, "model": "fixture-model",
                               "quota_group": "fixture-" + name, "lens": "adversarial", "enabled": True,
                               "disabled_reason": "", "settings": {}}
                              for name, family in (("fixture.reviewer", "anthropic"), ("fixture.second", "google"))]
    path.write_text(json.dumps(value))
    return config.PanelConfiguration.from_dict(value)


def verdict_script(decision):
    def script(prompt, number):
        findings = ([{"criterion_id": "whole_package", "blocking": True, "text": "The recomputation is missing."}]
                    if decision == "reject" else [])
        text = json.dumps({"body_sha256": prompt.body_sha256, "decision": decision, "findings": findings,
                           "reasons": "It fails its own check." if decision == "reject" else "Every criterion holds."})
        return ReviewerAttempt("answered", text, Usage(100, 20, source=PROVIDER_REPORTED), 1, 0.1, None,
                               "fixture-model", "fixture")
    return script


class WriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def review(self, decision="approve", family="zhipu", ask_producer_family=False, second=None):
        folder = self.root / "candidates"
        folder.mkdir()
        skill_catalogue(folder, "check_a_sum", family)
        configuration = native_profile.configuration(fixture_panel(self.root / "panel.json"))
        criteria, instructions = native_profile.resources()
        catalogue = native.NativeCatalogue.load(folder, ROOT)
        first, other = configuration.installations
        scripts = {first.installation_id: FixtureReviewer(first, verdict_script(decision))}
        if second is not None:
            scripts[other.installation_id] = FixtureReviewer(other, verdict_script(second))
        panel = ReviewPanel(configuration, criteria, instructions, scripts,
                            engines.build_precheck_engines(configuration), ReviewLedger(self.root / "ledger.jsonl"))
        request = catalogue.request("check_a_sum", catalogue.producer_for("check_a_sum"), criteria, instructions.sha256)
        # A defect that let the producer's family be asked is simulated by switching the panel's exclusion off.
        exclusion = ((lambda installation, producer: False) if ask_producer_family
                     else panel_module.producer_family_excluded)
        with mock.patch.object(panel_module, "producer_family_excluded", exclusion):
            panel.run(PanelRunRequest(run_id="run-1", requests=(request,), population=catalogue.population_bodies(),
                                      call_ceiling=2, token_ceiling=1_000_000, model_calls_authorized=True,
                                      fixture_run=True, collect_below_quorum_reason="one family in this check"))
        return folder

    def write(self, folder, *, allow_fixture=True, output=None, scan_record=()):
        options = argparse.Namespace(repository=ROOT, panel=self.root / "panel.json", catalogue=folder,
                                     ledger=[str(self.root / "ledger.jsonl")], reviewer=["fixture.reviewer"],
                                     tier="community", output=output or self.root / "reviewed",
                                     recorded_at="2026-09-24", allow_fixture=allow_fixture,
                                     scan_record=list(scan_record))
        return writer.write(options)

    def test_a_refusing_or_missing_safety_scan_leaves_the_item_out(self):
        folder = self.review()
        digest = json.loads((folder / "items.json").read_text())["items"][0]["reference"]["digest"]
        for packages in ({digest: {"identity": "check_a_sum", "refused": True, "refusals": ["skillspector_issue"],
                                   "notes": []}}, {}):
            with self.subTest(packages=bool(packages)):
                path = self.root / "scan.json"
                path.write_text(json.dumps({"record_type": "package_safety_scan/v1", "packages": packages}))
                with self.assertRaisesRegex(writer.WriterError, "no_judged_items"):
                    self.write(folder, scan_record=[str(path)])

    def test_a_community_approval_is_written_and_the_bundle_builder_carries_its_tier(self):
        summary = self.write(self.review())
        self.assertEqual((summary["approved"], summary["rejected"], summary["left_out"]), (1, 0, 0))
        reviewed = self.root / "reviewed"
        review = json.loads((reviewed / "reviews.json").read_text())
        [row] = review["rows"]
        self.assertEqual((row["outcome"], row["tier"], row["approval_state"]), ("approved", "community", "reviewed"))
        self.assertEqual(row["body_digest"], hashlib.sha256(SKILL).hexdigest())
        self.assertEqual(row["decisions"][0]["approved_digest"], row["reviewed_package"]["package_digest"])
        self.assertEqual(row["reviewed_package"]["files"], [{"path": "SKILL.md", "digest": row["body_digest"]}])
        schema, lines, payloads = bundle_tool.build(reviewed, accepted_licenses=("MIT",))
        self.assertEqual([line["attributes"]["tier"] for line in lines], ["community"])
        self.assertEqual(lines[0]["approval"]["approved_digest"], row["body_digest"])
        self.assertEqual(payloads, [SKILL])

    def test_a_rejection_is_written_as_rejected_and_never_bundled(self):
        self.write(self.review("reject"))
        review = json.loads((self.root / "reviewed" / "reviews.json").read_text())
        self.assertEqual(review["rows"][0]["outcome"], "rejected")
        self.assertIn("fails its own check", review["rows"][0]["decisions"][0]["reason"])
        with self.assertRaises(Exception):
            bundle_tool.build(self.root / "reviewed", accepted_licenses=("MIT",))

    def test_a_verdict_from_the_producer_family_leaves_the_item_out(self):
        folder = self.review(family="anthropic", ask_producer_family=True)
        with self.assertRaisesRegex(writer.WriterError, "no_judged_items"):
            self.write(folder)

    def test_mutant_without_the_producer_family_rule_writes_an_own_family_approval(self):
        """Mutant control: with the producer family ignored, an anthropic item approved by anthropic is written."""
        folder = self.review(family="anthropic", ask_producer_family=True)
        with mock.patch.object(writer, "_same_family", lambda reviewers, producer: False):
            summary = self.write(folder)
        self.assertEqual(summary["approved"], 1)

    def test_a_verdict_from_a_reviewer_the_folder_does_not_name_leaves_the_item_out(self):
        for second in ("reject", "approve"):
            with self.subTest(second=second):
                self.root = Path(tempfile.mkdtemp(dir=self.tmp.name)).resolve()
                folder = self.review(second=second)
                with self.assertRaisesRegex(writer.WriterError, "no_judged_items"):
                    self.write(folder)
                report = self.root / "reviewed"
                self.assertFalse(report.exists())

    def test_a_scripted_fixture_verdict_is_left_out_unless_a_check_allows_it(self):
        with self.assertRaisesRegex(writer.WriterError, "no_judged_items"):
            self.write(self.review(), allow_fixture=False)

    def test_a_folder_inside_this_repository_is_refused(self):
        with self.assertRaisesRegex(writer.WriterError, "folder_inside_repository"):
            self.write(self.review(), output=ROOT / "artifacts" / "reviewed-catalogue-check")


if __name__ == "__main__":
    unittest.main()

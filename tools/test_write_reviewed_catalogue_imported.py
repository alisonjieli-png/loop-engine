"""The reviewed catalogue writer reads a licensed import export and carries its upstream provenance (S-6.196).

The verdict comes from the real review panel run over a fixture reviewer into a real ledger; no model is called.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent))

import build_catalogue_release_bundle as bundle_tool  # noqa: E402
import write_reviewed_catalogue as writer  # noqa: E402
from candidate_review import engines, imported, imported_profile  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.reviewers.fixture import FixtureReviewer  # noqa: E402
from test_candidate_review_imported import IDENTITY, UPSTREAM_PATH, UPSTREAM_REVISION, fixture  # noqa: E402
from test_write_reviewed_catalogue import fixture_panel, verdict_script  # noqa: E402

ROOT = HERE.parent


class ImportedWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def review(self, decision="approve"):
        folder = self.root / "export"
        folder.mkdir()
        fixture(folder)
        configuration = imported_profile.configuration(fixture_panel(self.root / "panel.json"))
        criteria, instructions = imported_profile.resources()
        catalogue = imported.ImportedCatalogue.load(folder, ROOT)
        first = configuration.installations[0]
        panel = ReviewPanel(configuration, criteria, instructions,
                            {first.installation_id: FixtureReviewer(first, verdict_script(decision))},
                            engines.build_precheck_engines(configuration), ReviewLedger(self.root / "ledger.jsonl"))
        request = catalogue.request(IDENTITY, catalogue.producer_for(IDENTITY), criteria, instructions.sha256)
        panel.run(PanelRunRequest(run_id="run-1", requests=(request,), population=catalogue.population_bodies(),
                                  call_ceiling=2, token_ceiling=1_000_000, model_calls_authorized=True,
                                  fixture_run=True, collect_below_quorum_reason="one family in this check"))
        return folder

    def write(self, folder, identities=None):
        options = argparse.Namespace(repository=ROOT, panel=self.root / "panel.json", catalogue=folder,
                                     ledger=[str(self.root / "ledger.jsonl")], reviewer=["fixture.reviewer"],
                                     tier="community", output=self.root / "reviewed", recorded_at="2026-09-25",
                                     allow_fixture=True, scan_record=[], identities_file=identities)
        return writer.write(options)

    def test_an_imported_approval_is_written_with_its_upstream_provenance_and_bundles(self):
        summary = self.write(self.review())
        self.assertEqual((summary["approved"], summary["rejected"], summary["left_out"]), (1, 0, 0))
        reviewed = self.root / "reviewed"
        [item] = json.loads((reviewed / "items.json").read_text())["items"]
        provenance = item["provenance"]
        self.assertEqual(provenance["authoring"], imported.AUTHORING)
        self.assertEqual(provenance["upstream"]["path"], UPSTREAM_PATH)
        self.assertEqual(provenance["upstream"]["immutable_revision"], UPSTREAM_REVISION)
        self.assertEqual(provenance["licence_decision"], imported.VERBATIM)
        self.assertEqual(provenance["license"]["attribution"], "ATTRIBUTION.md")
        self.assertEqual({entry["path"] for entry in item["package_files"]}, {"SKILL.md", "LICENSE", "ATTRIBUTION.md"})
        [row] = json.loads((reviewed / "reviews.json").read_text())["rows"]
        self.assertEqual((row["outcome"], row["tier"], row["producer"]["family"]),
                         ("approved", "community", imported.UPSTREAM_FAMILY))
        # The writer tags each approved item with the kinds of step it supports (S-6.206): the fixture is a
        # review skill, so it carries reviewing; the tag names the rules engine and reaches the bundle line.
        self.assertEqual(item["attributes"], {"harness_kind": "skill", "step_functions": ["reviewing"]})
        self.assertEqual(item["attribute_engines"]["step_functions"]["engine_id"], "step_function_rules")
        schema = json.loads((reviewed / "attribute-schema.json").read_text())
        self.assertIn("step_functions", [attribute["name"] for attribute in schema["attributes"]])
        _schema, lines, _payloads = bundle_tool.build(reviewed, accepted_licenses=("MIT",))
        self.assertEqual([line["attributes"]["tier"] for line in lines], ["community"])
        self.assertEqual(lines[0]["attributes"]["step_functions"], ["reviewing"])
        self.assertEqual(len(lines[0]["package"]["files"]), 3)

    def test_an_imported_rejection_is_written_as_rejected(self):
        self.write(self.review("reject"))
        [row] = json.loads((self.root / "reviewed" / "reviews.json").read_text())["rows"]
        self.assertEqual((row["outcome"], row["approval_state"]), ("rejected", "none"))

    def test_the_identities_file_limits_the_folder_and_refuses_an_unknown_name(self):
        folder = self.review()
        names = self.root / "names.txt"
        names.write_text("not_in_this_catalogue\n")
        with self.assertRaisesRegex(writer.WriterError, "identity_unknown"):
            self.write(folder, identities=names)
        names.write_text(IDENTITY + "\n")
        self.assertEqual(self.write(folder, identities=names)["approved"], 1)


if __name__ == "__main__":
    unittest.main()

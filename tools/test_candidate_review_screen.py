"""The Community screen (roadmap S-6.199): four criteria, the imported prechecks, no model call.

Known-wrong cases that must refuse: a screen criterion whose quote is not in the written sheet, the screen asked of
an original catalogue, and an unknown content profile name.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src"), str(HERE.parent / "artifacts/review-throughput-2026-09-24")]

from candidate_review import imported, imported_profile, screen_profile  # noqa: E402
from candidate_review.configuration import compile_criteria  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402
from test_candidate_review_imported import IDENTITY, fixture  # noqa: E402
from test_candidate_review_native import fixture as native_fixture  # noqa: E402
from test_candidate_review_panel import BASE  # noqa: E402

ROOT = HERE.parent


class ScreenProfileTest(unittest.TestCase):
    def test_the_screen_asks_exactly_the_four_questions_of_the_imported_grounding(self):
        criteria, instructions = screen_profile.resources()
        self.assertEqual(tuple(criterion.criterion_id for criterion in criteria.criteria), screen_profile.SCREEN_CRITERIA)
        self.assertEqual(set(criteria.groundings), {imported.IMPORTED_GROUNDING})
        full, _full_instructions = imported_profile.resources()
        self.assertNotEqual(criteria.sha256, full.sha256)
        self.assertIn("screen, not the full review", instructions.every_reviewer())
        self.assertNotEqual(instructions.sha256, imported_profile.resources()[1].sha256)

    def test_a_screen_quote_outside_the_written_sheet_is_refused(self):
        value = json.loads((screen_profile.RESOURCES / "community-screen-criteria.json").read_text())
        sheet = (screen_profile.RESOURCES / "COMMUNITY-SCREEN.md").read_text()
        compile_criteria(copy.deepcopy(value), sheet)
        value["criteria"][0]["quote"] = "Approve any package whose repository is popular."
        with self.assertRaises(CandidateReviewError):
            compile_criteria(value, sheet)

    def test_the_screen_keeps_the_imported_prechecks_and_reader(self):
        configuration = screen_profile.configuration(BASE)
        self.assertEqual(configuration.to_dict()["policy"]["prechecks"],
                         imported_profile.configuration(BASE).to_dict()["policy"]["prechecks"])
        with tempfile.TemporaryDirectory() as folder:
            fixture(Path(folder))
            catalogue = imported.ImportedCatalogue.load(Path(folder), ROOT)
            criteria, instructions = screen_profile.resources()
            request = catalogue.request(IDENTITY, catalogue.producer_for(IDENTITY), criteria, instructions.sha256)
            self.assertEqual(request.grounding, imported.IMPORTED_GROUNDING)
            self.assertEqual({criterion.criterion_id for criterion in request.criteria.criteria},
                             set(screen_profile.SCREEN_CRITERIA))

    def test_the_campaign_selects_the_screen_for_imported_catalogues_only(self):
        import community_campaign
        with tempfile.TemporaryDirectory() as folder:
            fixture(Path(folder))
            reader, profile = community_campaign._profile(Path(folder), "screen")
            self.assertIs(reader, imported.ImportedCatalogue)
            self.assertIs(profile, screen_profile)
            reader, profile = community_campaign._profile(Path(folder))
            self.assertIs(profile, imported_profile)
        with tempfile.TemporaryDirectory() as folder:
            native_fixture(Path(folder))
            with self.assertRaises(SystemExit):
                community_campaign._profile(Path(folder), "screen")
        with self.assertRaises(SystemExit):
            community_campaign._profile(Path("/nonexistent"), "made_up")


if __name__ == "__main__":
    unittest.main()

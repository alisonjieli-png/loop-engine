"""The library tier contract agrees with the owner's decision and with the release rules it relies on.

The decision table of AGENTS.md records the two tiers in its row "Library
tiers", with the labels every served item shows. These checks hold the code to
that row and keep the process effect that marks a runnable file one value in
the provisioning authority and the release rules. Each check has a
known-wrong control.
"""
import json
from pathlib import Path
import unittest

from loop_engine.core import provisioning_server
from loop_engine.core.service_runtime import catalogue_packages, catalogue_tiers

ROOT = Path(__file__).resolve().parents[1]


def decision_row(text):
    return next((line for line in text.splitlines() if line.startswith("| Library tiers |")), "")


def label_findings(row, labels):
    """Each label the code shows that the decision row does not name in bold, as the row writes them."""
    return [label for label in labels if f"**{label}**" not in row]


FIRST_CATALOGUE_REVIEW = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "reviews.json"
FIRST_CATALOGUE_PANEL = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "reviews-panel-2026-09-22.json"


def families_shown(record, producer_family):
    """The model families a review record names for its reviewers, other than the producer's.

    A reviewer whose family the record does not name counts for no family: a label that mentions a model is not a
    declared family."""
    return {row["family"] for row in record["reviewers"] if row.get("family") and row["family"] != producer_family}


def verified_meaning_findings(meaning, record, producer_family):
    """What is wrong with the published meaning of Verified, given the review record of the first catalogue.

    The first catalogue's items are served as Verified. While its record shows fewer than two families other than the
    producer's, the meaning must say so (release 30 live check, September 25, 2026)."""
    if len(families_shown(record, producer_family)) >= 2 or "first catalogue" in meaning:
        return []
    return ["the meaning of Verified claims two families for the first catalogue, whose record does not show them"]


class LibraryTierContractTests(unittest.TestCase):
    def test_the_code_shows_exactly_the_labels_the_decision_names(self):
        row = decision_row((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertTrue(row, "the decision table has no Library tiers row")
        self.assertEqual(label_findings(row, catalogue_tiers.TIER_LABELS.values()), [])
        self.assertEqual(catalogue_tiers.TIER_LABELS, {"verified": "Verified", "community": "Community"})

    def test_known_wrong_a_label_the_decision_does_not_name_is_found(self):
        row = decision_row((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(label_findings(row, ["Baltor verified"]), ["Baltor verified"])

    def test_the_legend_publishes_each_tier_with_its_label_and_the_default(self):
        legend = catalogue_tiers.tier_legend()
        self.assertEqual([(row["library_tier"], row["label"]) for row in legend["tiers"]],
                         [("verified", "Verified"), ("community", "Community")])
        self.assertEqual(legend["community_items"]["default"], "included")

    def test_the_meaning_of_verified_states_the_first_catalogue_exception(self):
        record = json.loads(FIRST_CATALOGUE_REVIEW.read_text(encoding="utf-8"))
        producer = json.loads(FIRST_CATALOGUE_PANEL.read_text(encoding="utf-8"))["producers"]["default_producer"]["family"]
        self.assertEqual(producer, "anthropic")
        meaning = catalogue_tiers.TIER_MEANINGS["verified"]
        self.assertEqual(verified_meaning_findings(meaning, record, producer), [])
        # Known wrong: the meaning without its exception, while the record still shows no two other families.
        claimed = meaning.split(" The first catalogue")[0]
        self.assertNotIn("first catalogue", claimed)
        self.assertEqual(len(verified_meaning_findings(claimed, record, producer)), 1)
        # Not required once two other families have reviewed it, which is how the exception ends (roadmap S-6.178).
        reviewed = {**record, "reviewers": [{"reviewer_id": "a", "family": "openai"}, {"reviewer_id": "b", "family": "zhipu"}]}
        self.assertEqual(verified_meaning_findings(claimed, reviewed, producer), [])
        # A reviewer of the producer's own family never counts.
        same = {**record, "reviewers": [{"reviewer_id": "a", "family": "anthropic"}, {"reviewer_id": "b", "family": "openai"}]}
        self.assertEqual(len(verified_meaning_findings(claimed, same, producer)), 1)

    def test_the_runnable_file_effect_is_the_release_rules_process_effect(self):
        # catalogue_packages.py is a pinned cited source of reviewed candidates, so it keeps its own
        # constant; this check holds the two values together instead.
        self.assertEqual(catalogue_packages.EXECUTABLE_EFFECT, provisioning_server.RUNNABLE_EFFECT)
        self.assertNotEqual("network", provisioning_server.RUNNABLE_EFFECT)


if __name__ == "__main__":
    unittest.main()

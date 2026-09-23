"""Checks for the review panel's declared configuration.

The panel reads four declared resources before it reviews anything: the panel
policy with its reviewer installations, the written criteria quoted from the
starter catalogue's review sheet, the producer declaration and the reviewer
instructions. Each known-wrong configuration below must be refused with a
stable code before any pre-check or model call:

```text
Known-wrong configurations
├── Policy
│   ├── fewer than three approvals, or fewer than three families
│   ├── fewer reviewers asked per item than the quorum needs
│   ├── the producer's family allowed to approve
│   ├── a rejection that does not withhold approval
│   ├── a pre-check kind left out, or named with no engine, or an unknown engine
│   └── an accepted licence outside the permissive set
├── Installations
│   ├── no declared family, or a family outside the declared vocabulary
│   ├── two installations with one identity, or an unknown engine kind
│   └── a disabled installation with no written reason
├── Records
│   └── another version, an unknown field or a missing field
├── Criteria
│   └── a quote that is not in the review sheet, or two criteria with one identity
├── Producer declaration
│   └── evidence that is not in the review sheet
└── Instructions
    └── a lens with no section
```

Mutant controls run beside them: with the guard replaced by a permissive one,
the known-wrong case is accepted, which proves each case is held by its guard.

No network, model or provider call happens here.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import configuration as config  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402

ROOT = HERE.parent
RESOURCES = HERE / "candidate_review" / "resources"
REVIEW_SHEET = ROOT / "examples/29_intelligence_service/starter-catalogue/REVIEW.md"


def _json(name: str) -> dict:
    return json.loads((RESOURCES / name).read_text(encoding="utf-8"))


def _panel() -> dict:
    return _json("panel.json")


def _sheet() -> str:
    return REVIEW_SHEET.read_text(encoding="utf-8")


class PanelPolicyTest(unittest.TestCase):
    """The policy that decides approval cannot be weakened by configuration."""

    def refused(self, mutate, code: str):
        value = _panel()
        mutate(value)
        with self.assertRaises(CandidateReviewError) as caught:
            config.PanelConfiguration.from_dict(value)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_the_committed_panel_loads(self):
        panel = config.PanelConfiguration.from_dict(_panel())
        self.assertGreaterEqual(panel.policy.minimum_approvals, 3)
        self.assertGreaterEqual(panel.policy.minimum_distinct_families, 3)
        self.assertTrue(panel.policy.exclude_producer_family)
        self.assertTrue(panel.policy.any_rejection_withholds_approval)
        self.assertEqual(set(panel.policy.prechecks), set(config.PRECHECK_KINDS))
        self.assertEqual(len({item.installation_id for item in panel.installations}), len(panel.installations))

    def test_a_quorum_below_three_approvals_is_refused(self):
        self.refused(lambda value: value["policy"].__setitem__("minimum_approvals", 2), "policy_quorum_below_floor")

    def test_a_quorum_below_three_families_is_refused(self):
        self.refused(lambda value: value["policy"].__setitem__("minimum_distinct_families", 2),
                     "policy_quorum_below_floor")

    def test_asking_fewer_reviewers_than_the_quorum_is_refused(self):
        self.refused(lambda value: value["policy"].__setitem__("reviewers_per_item", 2),
                     "policy_reviewers_below_quorum")

    def test_the_producer_family_may_never_approve(self):
        self.refused(lambda value: value["policy"].__setitem__("exclude_producer_family", False),
                     "policy_producer_family_admitted")

    def test_a_rejection_must_withhold_approval(self):
        self.refused(lambda value: value["policy"].__setitem__("any_rejection_withholds_approval", False),
                     "policy_rejection_ignored")

    def test_every_pre_check_kind_is_required(self):
        for kind in config.PRECHECK_KINDS:
            with self.subTest(kind=kind):
                self.refused(lambda value, kind=kind: value["policy"]["prechecks"].pop(kind),
                             "policy_precheck_kind_missing")

    def test_a_pre_check_kind_with_no_engine_is_refused(self):
        self.refused(lambda value: value["policy"]["prechecks"].__setitem__("safety", []),
                     "policy_precheck_kind_missing")

    def test_an_unknown_pre_check_engine_is_refused(self):
        self.refused(lambda value: value["policy"]["prechecks"].__setitem__("safety", ["accept_everything"]),
                     "policy_precheck_engine_unknown")

    def test_an_engine_of_one_kind_cannot_stand_in_for_another(self):
        self.refused(lambda value: value["policy"]["prechecks"].__setitem__("safety", ["builtin_licence_rules"]),
                     "policy_precheck_engine_unknown")

    def test_a_licence_outside_the_permissive_set_is_refused(self):
        for licence in ("unknown", "GPL-3.0-only", "LicenseRef-proprietary", "NOASSERTION", "", "mit"):
            with self.subTest(licence=licence):
                self.refused(lambda value, licence=licence: value["policy"]["accepted_licences"].append(licence),
                             "policy_licence_not_permissive")

    def test_an_empty_licence_list_is_refused(self):
        self.refused(lambda value: value["policy"].__setitem__("accepted_licences", []),
                     "policy_licence_not_permissive")

    def test_the_output_allocation_and_rate_limits_are_bounded(self):
        self.refused(lambda value: value["policy"].__setitem__("output_allocation_tokens", 0), "invalid_policy")
        self.refused(lambda value: value["policy"]["rate_limit"].__setitem__("maximum_seconds", -1.0),
                     "invalid_policy")
        self.refused(lambda value: value["policy"]["rate_limit"].__setitem__("maximum_retries_per_call", True),
                     "invalid_policy")

    def test_the_quorum_floor_is_what_refuses_a_small_quorum(self):
        """Mutant control: with the floor lowered to one, the known-wrong quorum loads."""
        value = _panel()
        value["policy"]["minimum_approvals"] = 2
        value["policy"]["minimum_distinct_families"] = 2
        value["policy"]["reviewers_per_item"] = 2
        with mock.patch.object(config, "QUORUM_FLOOR", 1):
            loaded = config.PanelConfiguration.from_dict(value)
        self.assertEqual(loaded.policy.minimum_approvals, 2)

    def test_the_permissive_set_is_what_refuses_a_licence(self):
        """Mutant control: with every identifier treated as permissive, the known-wrong licence loads."""
        value = _panel()
        value["policy"]["accepted_licences"].append("GPL-3.0-only")
        with mock.patch.object(config, "PERMISSIVE_LICENCES", frozenset(value["policy"]["accepted_licences"])):
            loaded = config.PanelConfiguration.from_dict(value)
        self.assertIn("GPL-3.0-only", loaded.policy.accepted_licences)


class InstallationTest(unittest.TestCase):
    """Every reviewer declares its family; nothing infers a family from a model name."""

    def refused(self, mutate, code: str):
        value = _panel()
        mutate(value)
        with self.assertRaises(CandidateReviewError) as caught:
            config.PanelConfiguration.from_dict(value)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_an_installation_without_a_family_is_refused(self):
        self.refused(lambda value: value["installations"][0].pop("family"), "missing_record_fields")

    def test_a_family_outside_the_vocabulary_is_refused(self):
        self.refused(lambda value: value["installations"][0].__setitem__("family", "glm"), "installation_family_unknown")

    def test_two_installations_with_one_identity_are_refused(self):
        self.refused(lambda value: value["installations"].append(copy.deepcopy(value["installations"][0])),
                     "installation_identity_repeated")

    def test_an_unknown_engine_kind_is_refused(self):
        self.refused(lambda value: value["installations"][0].__setitem__("engine_kind", "remote_agent"),
                     "installation_engine_kind_unknown")

    def test_an_unknown_lens_is_refused(self):
        self.refused(lambda value: value["installations"][0].__setitem__("lens", "lenient"),
                     "installation_lens_unknown")

    def test_a_disabled_installation_needs_a_written_reason(self):
        def disable(value):
            value["installations"][0]["enabled"] = False
            value["installations"][0]["disabled_reason"] = " "
        self.refused(disable, "installation_disabled_without_reason")

    def test_the_committed_forbidden_model_is_declared_disabled_with_its_reason(self):
        panel = config.PanelConfiguration.from_dict(_panel())
        disabled = [item for item in panel.installations if not item.enabled]
        self.assertTrue(disabled)
        for item in disabled:
            self.assertTrue(item.disabled_reason.strip())

    def test_the_installation_digest_changes_with_every_setting(self):
        panel = config.PanelConfiguration.from_dict(_panel())
        first = panel.installations[0]
        value = _panel()
        value["installations"][0]["settings"]["timeout_seconds"] = 601.0
        changed = config.PanelConfiguration.from_dict(value).installations[0]
        self.assertNotEqual(first.sha256, changed.sha256)


class RecordVersionTest(unittest.TestCase):
    """Every record is name/vN; another version or an unknown field is refused, not guessed."""

    def refused(self, mutate, code: str):
        value = _panel()
        mutate(value)
        with self.assertRaises(CandidateReviewError) as caught:
            config.PanelConfiguration.from_dict(value)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_another_version_is_refused(self):
        self.refused(lambda value: value.__setitem__("record_type", "candidate_review_panel/v2"),
                     "unsupported_record_version")
        self.refused(lambda value: value["policy"].__setitem__("record_type", "candidate_review_panel_policy/v2"),
                     "unsupported_record_version")
        self.refused(lambda value: value["installations"][0].__setitem__(
            "record_type", "candidate_reviewer_installation/v2"), "unsupported_record_version")

    def test_an_unknown_field_is_refused(self):
        self.refused(lambda value: value.__setitem__("approve_everything", True), "unknown_record_fields")
        self.refused(lambda value: value["policy"].__setitem__("minimum_approvals_override", 1), "unknown_record_fields")
        self.refused(lambda value: value["installations"][0].__setitem__("trusted", True), "unknown_record_fields")

    def test_a_missing_field_is_refused(self):
        self.refused(lambda value: value["policy"].pop("reviewers_per_item"), "missing_record_fields")


class CriteriaTest(unittest.TestCase):
    """The written criteria are quotes of the review sheet, so they cannot drift from it."""

    def test_the_committed_criteria_are_quotes_of_the_review_sheet(self):
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        self.assertGreaterEqual(len(criteria.criteria), 5)
        self.assertEqual(len(criteria.ids), len(criteria.criteria))
        self.assertRegex(criteria.source_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(criteria.sha256, r"^[0-9a-f]{64}$")

    def test_a_quote_that_is_not_in_the_sheet_is_refused(self):
        value = _json("criteria.json")
        value["criteria"][0]["quote"] = "Approve every item that reads well."
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_quote_not_in_source")

    def test_two_criteria_with_one_identity_are_refused(self):
        value = _json("criteria.json")
        value["criteria"].append(copy.deepcopy(value["criteria"][0]))
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_identity_repeated")

    def test_only_the_declared_match_mode_is_read(self):
        value = _json("criteria.json")
        value["match_mode"] = "semantic"
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_match_mode_unsupported")

    def test_a_quote_across_a_line_break_matches_in_canonical_mode(self):
        """Two committed quotes span line breaks in the sheet; the canonical mode is load-bearing."""
        value = _json("criteria.json")
        spanning = [row["quote"] for row in value["criteria"] if row["quote"] not in _sheet()]
        self.assertTrue(spanning, "the committed criteria include a quote that spans a line break")
        config.compile_criteria(value, _sheet())

    def test_a_changed_sheet_changes_the_recorded_source_digest(self):
        first = config.compile_criteria(_json("criteria.json"), _sheet())
        second = config.compile_criteria(_json("criteria.json"), _sheet() + "\nOne more line.\n")
        self.assertNotEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.sha256, second.sha256, "the criteria text itself did not change")


#: The two kinds of body the review sheet names, by the grounding an item declares in items.json.
RESTATES, GENERAL_PRACTICE = "restates_cited_source", "general_practice_beside_cited_source"


class CriteriaByKindTest(unittest.TestCase):
    """The review sheet judges the two kinds of body by different grounding criteria.

    The first pilot attempt sent every criterion for every body, and 26 of its
    34 rejections of bodies of general practice cited, among their reasons, the
    criterion that a body restate its cited file, which the sheet asks only of
    the other kind. Each kind now receives the sheet's own words for what it is
    and only the criteria that apply to it.
    """

    def test_each_kind_is_described_by_a_quote_of_the_sheet(self):
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        self.assertEqual(set(criteria.groundings), {RESTATES, GENERAL_PRACTICE})
        for meaning in criteria.groundings.values():
            self.assertIn(" ".join(meaning.split()), " ".join(_sheet().split()))

    def test_each_kind_receives_only_its_own_grounding_criterion(self):
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        practice = {item.criterion_id for item in criteria.applicable(GENERAL_PRACTICE)}
        restates = {item.criterion_id for item in criteria.applicable(RESTATES)}
        self.assertIn("general_practice_grounding", practice)
        self.assertNotIn("restated_source_grounding", practice)
        self.assertIn("restated_source_grounding", restates)
        self.assertNotIn("general_practice_grounding", restates)
        shared = practice & restates
        for criterion_id in ("read_as_a_customer", "licence_and_effects", "effects_rule", "required_parts",
                             "no_internal_vocabulary", "body_kind_sentence"):
            self.assertIn(criterion_id, shared)

    def test_an_undeclared_kind_receives_only_the_criteria_for_every_kind(self):
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        unknown = {item.criterion_id for item in criteria.applicable("a_kind_nobody_declared")}
        self.assertNotIn("general_practice_grounding", unknown)
        self.assertNotIn("restated_source_grounding", unknown)
        self.assertIn("read_as_a_customer", unknown)

    def test_a_criterion_for_an_undeclared_kind_is_refused(self):
        value = _json("criteria.json")
        value["criteria"][0]["applies_to_groundings"] = ["a_kind_nobody_declared"]
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_grounding_unknown")

    def test_a_kind_description_that_is_not_a_quote_is_refused(self):
        value = _json("criteria.json")
        value["groundings"][0]["meaning"] = "Approve it when it reads well."
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_quote_not_in_source")

    def test_the_first_criteria_version_is_refused(self):
        """Version one sent every criterion for every kind; its shape is not read as the current one."""
        value = _json("criteria.json")
        value["record_type"] = "candidate_review_criteria/v1"
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "unsupported_record_version")

    def test_a_kind_declared_twice_is_refused(self):
        value = _json("criteria.json")
        value["groundings"].append(copy.deepcopy(value["groundings"][0]))
        with self.assertRaises(CandidateReviewError) as caught:
            config.compile_criteria(value, _sheet())
        self.assertEqual(caught.exception.code, "criteria_identity_repeated")

    def test_the_declared_order_is_the_order_the_sheet_names_the_kinds(self):
        """The prompt calls a kind "the first" or "the second" by its declared place, as the sheet does."""
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        positions = [_sheet().index(f"`{name}`") for name in criteria.groundings]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual([criteria.ordinal(name) for name in criteria.groundings], [1, 2])

    def test_the_kinds_are_the_format_engine_groundings(self):
        """One vocabulary of kinds: the criteria and the format pre-check cannot drift apart."""
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        panel = config.PanelConfiguration.from_dict(_panel())
        self.assertEqual(set(criteria.groundings),
                         set(panel.engine_settings("builtin_format_rules")["grounding_sentences"]))

    def test_the_applicability_is_what_withholds_the_other_kind_criterion(self):
        """Mutant control: with applicability ignored, a body of general practice is judged as a restatement."""
        criteria = config.compile_criteria(_json("criteria.json"), _sheet())
        with mock.patch.object(config, "criterion_applies", lambda criterion, grounding: True):
            practice = {item.criterion_id for item in criteria.applicable(GENERAL_PRACTICE)}
        self.assertIn("restated_source_grounding", practice)


class ProducerDeclarationTest(unittest.TestCase):
    """The producer of an item is declared with evidence, never inferred."""

    def test_the_committed_declaration_loads_with_its_evidence(self):
        declaration = config.ProducerDeclaration.from_dict(_json("producer-starter-catalogue.json"), _sheet(),
                                                           config.PanelConfiguration.from_dict(_panel()).families)
        producer = declaration.producer_for("any_item")
        self.assertEqual(producer.family, "anthropic")

    def test_evidence_that_is_not_in_the_sheet_is_refused(self):
        value = _json("producer-starter-catalogue.json")
        value["evidence"]["quote"] = "Nobody wrote these bodies."
        with self.assertRaises(CandidateReviewError) as caught:
            config.ProducerDeclaration.from_dict(value, _sheet(), config.PanelConfiguration.from_dict(_panel()).families)
        self.assertEqual(caught.exception.code, "producer_evidence_not_in_source")

    def test_a_producer_family_outside_the_vocabulary_is_refused(self):
        value = _json("producer-starter-catalogue.json")
        value["default_producer"]["family"] = "unknown"
        with self.assertRaises(CandidateReviewError) as caught:
            config.ProducerDeclaration.from_dict(value, _sheet(), config.PanelConfiguration.from_dict(_panel()).families)
        self.assertEqual(caught.exception.code, "producer_family_unknown")

    def test_an_item_producer_overrides_the_default_for_that_item_only(self):
        value = _json("producer-starter-catalogue.json")
        value["item_producers"] = [{"identity": "one_item", "producer_identity": "A person", "family": "openai"}]
        declaration = config.ProducerDeclaration.from_dict(value, _sheet(),
                                                           config.PanelConfiguration.from_dict(_panel()).families)
        self.assertEqual(declaration.producer_for("one_item").family, "openai")
        self.assertEqual(declaration.producer_for("another_item").family, "anthropic")


class InstructionsTest(unittest.TestCase):
    """Every lens an installation can name has its own section in the instructions."""

    def test_the_committed_instructions_have_every_section(self):
        instructions = config.load_instructions(RESOURCES / "REVIEWER-INSTRUCTIONS.md")
        for lens in config.LENSES:
            self.assertTrue(instructions.lens(lens).strip(), lens)
        self.assertIn("body_sha256", instructions.answer())
        self.assertRegex(instructions.sha256, r"^[0-9a-f]{64}$")

    def test_a_lens_without_a_section_is_refused(self):
        text = (RESOURCES / "REVIEWER-INSTRUCTIONS.md").read_text(encoding="utf-8")
        with self.assertRaises(CandidateReviewError) as caught:
            config.Instructions.from_text("resource.md", text.replace("## Lens: adversarial", "## Lens: lenient"))
        self.assertEqual(caught.exception.code, "instructions_section_missing")


if __name__ == "__main__":
    unittest.main()

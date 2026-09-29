"""Community material cannot authorize itself or become an approved component."""
import unittest

from loop_engine.loop.effect_approval import EffectClass
from tools.knowledge_radar.community import approval_request, draft, lead


class CommunityResearchTests(unittest.TestCase):
    def test_draft_discloses_purpose_and_does_not_send(self):
        value = draft("aigamedev", "browser game")
        self.assertIn("Baltor", value["body"])
        self.assertIsNone(value["public_post_id"])
        self.assertFalse(value["grants_authority"])

    def test_exact_effect_uses_existing_approval_and_changes_with_content(self):
        value = draft("aigamedev", "browser game")
        options = {"account_id": "research-account", "loop_id": "research-loop",
                   "rules_evidence": "record:rules-reviewed", "platform_access_evidence": "record:access-reviewed"}
        first = approval_request(value, **options)
        self.assertEqual(first.effect.effect_class, EffectClass.EXTERNAL_MESSAGE)
        changed = approval_request({**value, "body": value["body"] + "\nCorrection."}, **options)
        self.assertNotEqual(dict(first.effect.parameters)["operation_identity"],
                            dict(changed.effect.parameters)["operation_identity"])
        self.assertEqual(dict(first.effect.parameters)["body"], value["body"])

    def test_missing_policy_review_or_changed_state_refuses(self):
        value = draft("godot", "terrain")
        options = {"account_id": "research-account", "loop_id": "research-loop",
                   "rules_evidence": "rules", "platform_access_evidence": ""}
        with self.assertRaises(ValueError):
            approval_request(value, **options)
        options["platform_access_evidence"] = "access"
        with self.assertRaises(ValueError):
            approval_request({**value, "state": "posted"}, **options)
        with self.assertRaises(ValueError):
            draft("all", "everything")

    def test_reply_is_an_unverified_lead_even_if_it_claims_approval(self):
        value = lead(source_url="https://www.reddit.com/r/aigamedev/", observation_date="2026-09-29",
                     summary="The creator says their workflow is production ready.")
        self.assertFalse(value["component_approved"])
        self.assertFalse(value["executable_authority"])
        self.assertFalse(value["reproduced"])
        self.assertEqual(value["reuse_rights"], "not_established")


if __name__ == "__main__":
    unittest.main()

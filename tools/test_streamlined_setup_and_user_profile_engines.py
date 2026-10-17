"""Tests for tools/streamlined_setup_and_user_profile_engines.py.

Verifies:
1. Slot Family 1 (`streamlined_setup_orchestrator`): all 9 harnesses (`Claude Code`,
   `Codex`, `Cursor`, `Windsurf`, `Cline`, `Roo Code`, `OpenCode`, `Pi`, `ChatGPT App`),
   4 swappable setup engines (`zero_question_workspace_auto_detector`,
   `jev_llm_rule_inference_setup_engine`, `progressive_single_click_oauth_setup_engine`,
   `minimal_guided_fallback_setup_engine`), and cascade failover inside the 7-layer
   `ComponentEnvelope`.
2. Slot Family 2 (`user_capability_profiler`, `user_capability_profile/v1`): 4 swappable
   profiling engines (`matryoshka_session_embedding_profiler`,
   `lsh_persona_and_usecase_clusterer`, `bayesian_outcome_affinity_updater`,
   `ephemeral_in_session_profile_fallback`), Layer 3 `require_same_space` handshake,
   Layer 6 PII/secret preflight scrubber, 8 canonical personas, and 15 common use cases.
3. Slot Family 3 (`payment_and_entitlement_emulator`): Basic $9 free through Dec 2026 ->
   Pro $49 Stripe Checkout session -> Signed webhook settlement -> Founding 10-slot
   lease/release -> Idempotent duplicate webhook replay refusal -> Privacy Notice wire
   check -> Cancellation & renewal.
4. All 8 `removed_*` known-wrong controls.
"""
from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlined_setup_and_user_profile_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class StreamlinedSetupUserProfileAndPaymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = suite.run_full_audit()

    def test_full_audit_passes_all_slots_harnesses_personas_and_controls(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["envelope_layers"], list(COVERAGE_LAYERS))
        self.assertEqual(self.report["slots"], list(suite.ALL_SLOTS))

    def test_all_nine_harnesses_eliminate_manual_questions_and_match_mcp_keys(self) -> None:
        matrix = self.report["harness_setup_matrix"]
        self.assertEqual(len(matrix), 9)
        expected_mcp = {
            "claude_code": "http",
            "codex": "http_transport",
            "cursor": "url",
            "windsurf": "serverUrl",
            "cline": "streamableHttp",
            "roo_code": "streamable-http",
            "opencode": "remote",
            "pi": "mcp_endpoint",
            "chatgpt_app": "sse_or_streamable_http",
        }
        for harness_id, expected_key in expected_mcp.items():
            entry = matrix[harness_id]
            self.assertTrue(entry["verified"])
            self.assertEqual(entry["mcp_transport_key"], expected_key)
            self.assertEqual(entry["manual_questions_asked"], 0)
            self.assertEqual(entry["legacy_questions_saved"], 7)
            self.assertIn("python", entry["detected_stacks"])
            self.assertIn("typescript_node", entry["detected_stacks"])
            self.assertIn("rust", entry["detected_stacks"])

    def test_setup_engine_cascade_and_fallback_chain_across_authority_levels(self) -> None:
        # 1. Full workspace authority -> zero_question_workspace_auto_detector
        sig_full = suite.WorkspaceSetupSignals(
            account_id="acct_setup_01",
            harness_id="claude_code",
            os_platform="linux",
            workspace_files=("pyproject.toml", "package.json"),
        )
        res_full = suite.run_setup_engine(sig_full, suite.ENG_SETUP_CASCADE)
        self.assertIsNone(res_full.refusal)
        self.assertEqual(res_full.engine_id, suite.ENG_SETUP_ZERO_QUESTION)
        self.assertEqual(res_full.fallback_chain_used, (suite.ENG_SETUP_ZERO_QUESTION,))
        self.assertEqual(res_full.manual_questions_asked, 0)

        # 2. Workspace read off + prompt hint present -> cascades to jev_llm_rule_inference_setup_engine
        sig_jev = suite.WorkspaceSetupSignals(
            account_id="acct_setup_02",
            harness_id="cursor",
            os_platform="darwin",
            workspace_files=(),
            first_prompt_hint="build threejs shader motion timeline",
            workspace_read_granted=False,
        )
        res_jev = suite.run_setup_engine(sig_jev, suite.ENG_SETUP_CASCADE)
        self.assertIsNone(res_jev.refusal)
        self.assertEqual(res_jev.engine_id, suite.ENG_SETUP_JEV_RULE)
        self.assertEqual(
            res_jev.fallback_chain_used,
            (suite.ENG_SETUP_ZERO_QUESTION, suite.ENG_SETUP_JEV_RULE),
        )
        self.assertIn("creative_motion_studio_pack", res_jev.initial_feeds)

        # 3. Workspace read off + no prompt hint + GUI OAuth supported -> cascades to progressive_single_click_oauth_setup_engine
        sig_oauth = suite.WorkspaceSetupSignals(
            account_id="acct_setup_03",
            harness_id="chatgpt_app",
            os_platform="darwin",
            workspace_files=(),
            first_prompt_hint="",
            workspace_read_granted=False,
            gui_oauth_supported=True,
        )
        res_oauth = suite.run_setup_engine(sig_oauth, suite.ENG_SETUP_CASCADE)
        self.assertIsNone(res_oauth.refusal)
        self.assertEqual(res_oauth.engine_id, suite.ENG_SETUP_OAUTH_PKCE)
        self.assertTrue(res_oauth.oauth_pkce_verified)
        self.assertEqual(
            res_oauth.fallback_chain_used,
            (
                suite.ENG_SETUP_ZERO_QUESTION,
                suite.ENG_SETUP_JEV_RULE,
                suite.ENG_SETUP_OAUTH_PKCE,
            ),
        )

        # 4. Workspace read off + no prompt hint + headless -> cascades to minimal_guided_fallback_setup_engine
        sig_minimal = suite.WorkspaceSetupSignals(
            account_id="acct_setup_04",
            harness_id="pi",
            os_platform="linux",
            workspace_files=(),
            first_prompt_hint="",
            workspace_read_granted=False,
            gui_oauth_supported=False,
        )
        res_minimal = suite.run_setup_engine(sig_minimal, suite.ENG_SETUP_CASCADE)
        self.assertIsNone(res_minimal.refusal)
        self.assertEqual(res_minimal.engine_id, suite.ENG_SETUP_MINIMAL_GUIDED)
        self.assertEqual(res_minimal.manual_questions_asked, 1)
        self.assertEqual(res_minimal.fallback_chain_used, suite.ALL_SETUP_ENGINES)

    def test_matryoshka_embedding_profile_l2_norm_same_space_and_pii_scrubbing(self) -> None:
        req = suite.ProfileObservationRequest(
            account_id="acct_prof_01",
            session_id="sess_prof_01",
            harness_id="claude_code",
            task_summary="optimize lightgbm cross validation fold pipeline for user@domain.org with sk-test_9988776655 in /home/user/repo",
            observed_outcomes=("card_inspected", "material_downloaded", "kept_in_worktree", "tests_passed"),
        )
        rec = suite.run_profile_engine(req, suite.ENG_PROFILE_MATRYOSHKA)
        self.assertIsNone(rec.refusal)
        self.assertEqual(rec.schema_version, suite.USER_PROFILE_SCHEMA_VERSION)
        self.assertEqual(len(rec.matryoshka_64d_vector), 64)
        l2_norm = math.sqrt(sum(v * v for v in rec.matryoshka_64d_vector))
        self.assertAlmostEqual(l2_norm, 1.0, places=4)
        self.assertEqual(len(rec.binary_64bit_signature), 18)
        self.assertTrue(rec.binary_64bit_signature.startswith("0x"))
        self.assertGreaterEqual(rec.pii_redactions_applied, 3)
        self.assertFalse(rec.raw_prompt_retained)
        self.assertEqual(rec.primary_persona, "ml_kaggle_practitioner")
        self.assertEqual(rec.matched_use_case_id, "UC-03")
        self.assertGreater(rec.bayesian_capability_weights["ml_kaggle_practitioner"], 0.80)

    def test_ephemeral_profile_fallback_when_persistence_disabled(self) -> None:
        req = suite.ProfileObservationRequest(
            account_id="acct_prof_02",
            session_id="sess_prof_02",
            harness_id="windsurf",
            task_summary="debug sqlite wal lock contention under load",
            profile_persistence_enabled=False,
        )
        direct_refusal = suite.run_profile_engine(req, suite.ENG_PROFILE_MATRYOSHKA)
        self.assertIsNotNone(direct_refusal.refusal)
        self.assertEqual(direct_refusal.trace.refused_by, LAYER_PREFLIGHT)

        cascaded = suite.run_profile_engine(req, suite.ENG_PROFILE_CASCADE)
        self.assertIsNone(cascaded.refusal)
        self.assertEqual(cascaded.engine_id, suite.ENG_PROFILE_EPHEMERAL)
        self.assertFalse(cascaded.persisted_to_account)
        self.assertEqual(cascaded.fallback_chain_used, suite.ALL_PROFILE_ENGINES)

    def test_eight_personas_and_fifteen_use_cases_cluster_deterministically(self) -> None:
        self.assertEqual(len(self.report["personas_verified"]), 8)
        self.assertEqual(len(self.report["use_case_verifications"]), 15)
        for uc in self.report["use_case_verifications"]:
            self.assertTrue(uc["verified"], f"Use-case verification failed: {uc}")

    def test_payment_founding_slot_idempotency_privacy_and_renewal_emulation(self) -> None:
        pay = self.report["payment_lifecycle_report"]
        self.assertTrue(pay["passed"])
        self.assertTrue(pay["basic_plan"]["granted"])
        self.assertEqual(pay["basic_plan"]["monthly_cents"], 0)
        self.assertEqual(pay["basic_plan"]["free_through_utc"], "2026-12-31T23:59:59Z")
        self.assertEqual(pay["pro_checkout"]["monthly_cents"], 4900)
        self.assertTrue(pay["pro_checkout"]["customer_wire_privacy_safe"])
        self.assertTrue(pay["pro_checkout"]["checkout_wire_privacy_safe"])
        self.assertFalse(pay["pro_checkout"]["email_leaked_to_stripe"])
        self.assertTrue(pay["webhook_settlement"]["signature_verified"])
        self.assertTrue(pay["webhook_settlement"]["duplicate_replay_refused"])
        self.assertEqual(pay["founding_slots"]["cap"], 10)
        self.assertTrue(pay["founding_slots"]["slot_10_leased"])
        self.assertTrue(pay["founding_slots"]["slot_11_overflow_refused"])
        self.assertTrue(pay["founding_slots"]["re_leased_after_release"])
        self.assertTrue(pay["cancellation_and_renewal"]["scheduled_cancel_preserves_paid_period_end"])
        self.assertTrue(pay["cancellation_and_renewal"]["renewal_extended_by_30d"])

    def test_all_eight_known_wrong_controls_reject_bad_cases(self) -> None:
        controls = self.report["known_wrong_controls"]
        self.assertEqual(len(controls), 8)
        for ctrl in controls:
            self.assertTrue(ctrl["known_wrong_detected"], f"Control failed: {ctrl}")
            self.assertTrue(ctrl["leaked_when_removed"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the 120-Playbook "How to Solve Y Under Restriction X" Agent
Constraint-Workaround Harness Component Library & Live Capability Feed Engine Suite
(`Muse`, `Dot`, `OpenClaw`, `Hermes`, `Claude Code`, `Codex`, `Pi`).
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from sandbox_restriction_workarounds_and_agent_capability_feeds_engines import (  # noqa: E402
    ALL_8_RESTRICTION_FAMILIES,
    ALL_120_WORKAROUND_PLAYBOOKS,
    ALL_SLOTS,
    ENGINE_AGENTFEEDS_WORKAROUND_PUBLISHER,
    ENGINE_BALTOR_120_PLAYBOOK_WORKAROUND_SUITE,
    ENGINE_CGROUP_STDLIB_AND_HANDOFF_COMPILER,
    ENGINE_CROSS_HARNESS_CARD_INJECTOR,
    ENGINE_REALTIME_ERROR_BANNER_MATCHER,
    ENGINE_SYNTHETIC_PASTE_DROP_AND_CDP_COMPILER,
    ENGINE_UNASSISTED_SANDBOX_RESTRICTION_BASELINE,
    ENGINE_ZERO_JS_HTML_FORM_AND_MAILBOX_COMPILER,
    FEED_SERIES_ENDPOINTS,
    HARNESS_COMPONENT_PACK_FILES,
    MAX_SYMPTOM_MATCH_LATENCY_MS,
    MAX_WORKAROUND_CARD_BYTES,
    PLAYBOOKS_BY_FAMILY,
    PLAYBOOKS_BY_SLUG,
    SLOT_RESTRICTION_SYMPTOM_MATCHER_AND_FEED,
    SLOT_RESTRICTION_WORKAROUND_COMPONENT_LIBRARY,
    SUPPORTED_CONSTRAINED_HARNESSES,
    SYMPTOM_MATCHER_FEED_ENGINE_ORDER,
    WORKAROUND_LIBRARY_ENGINE_ORDER,
    AgentRestrictionWorkaroundComponentLibrarySlot,
    EnvelopeInvocationRequest,
    RestrictionSymptomMatcherAndCapabilityFeedSlot,
    match_error_banner_to_playbook,
    run_known_wrong_controls,
    run_sandbox_restriction_workaround_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_REFUSED,
    MAXIMUM_ENVELOPE_DEPTH,
    enter_nested,
    root_frame,
)


class SandboxRestrictionWorkaroundsAndCapabilityFeedsTests(unittest.TestCase):
    """Verify the 120 playbooks across 8 families, 2 slot families, symptom matcher, benchmark, and 4 controls."""

    def test_120_workaround_playbooks_across_8_families_and_7_harnesses(self) -> None:
        self.assertEqual(len(ALL_8_RESTRICTION_FAMILIES), 8)
        self.assertEqual(len(ALL_120_WORKAROUND_PLAYBOOKS), 120)
        self.assertEqual(
            SUPPORTED_CONSTRAINED_HARNESSES,
            ("muse", "dot", "openclaw", "hermes", "claude_code", "codex", "pi"),
        )
        for fam in ALL_8_RESTRICTION_FAMILIES:
            fam_playbooks = PLAYBOOKS_BY_FAMILY[fam.family_id]
            self.assertEqual(len(fam_playbooks), 15, f"Family {fam.family_id} must contain 15 playbooks")
            for spec in fam_playbooks:
                self.assertLessEqual(spec.contract_card_bytes, MAX_WORKAROUND_CARD_BYTES)
                self.assertEqual(len(spec.three_step_execution_plan), 3)
                self.assertEqual(spec.supported_harnesses, SUPPORTED_CONSTRAINED_HARNESSES)
                self.assertTrue(spec.feed_url.startswith("agentfeeds.si/workarounds/"))
                self.assertTrue(spec.foundry_url.startswith("agentfoundry.si/playbooks/"))

        for representative_slug in (
            "admin_file_select_dialogs_disabled_clipboard_paste",
            "telegram_web_no_dom_file_input_synthetic_drop",
            "muse_zero_js_html_form_command_relay",
            "paperclip_icon_template_match_xy_click",
            "cors_blocked_fetch_baltor_cloud_proxy_m1_m7",
            "cgroup_mem_max_3g_streaming_json_iterparse",
            "missing_jsonschema_stdlib_draft202012_shim",
            "compaction_loss_externalized_skills_state_json",
            "muse_to_openclaw_generated_image_staging_handoff",
        ):
            self.assertIn(representative_slug, PLAYBOOKS_BY_SLUG)

    def test_slot_family_1_component_library_compiles_5_file_harness_packs(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(WORKAROUND_LIBRARY_ENGINE_ORDER), 3)
        slot = AgentRestrictionWorkaroundComponentLibrarySlot()

        for eng_idx, eng in enumerate(WORKAROUND_LIBRARY_ENGINE_ORDER):
            res = slot.compile_workaround_component_pack(
                "admin_file_select_dialogs_disabled_clipboard_paste",
                target_harness="muse",
                preferred_engine=eng,
                request_id=f"test_lib_slot_{eng_idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_RESTRICTION_WORKAROUND_COMPONENT_LIBRARY)
            self.assertEqual(res.selected_engine, eng)
            self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
            self.assertTrue(all(v == "full" for v in res.layer_verdicts.values()))

            pack = res.output["harness_component_pack"]
            self.assertEqual(tuple(pack["files"]), HARNESS_COMPONENT_PACK_FILES)
            self.assertLessEqual(pack["baltor_contract_card_bytes"], MAX_WORKAROUND_CARD_BYTES)
            self.assertEqual(tuple(pack["supported_harnesses"]), SUPPORTED_CONSTRAINED_HARNESSES)

    def test_slot_family_2_realtime_symptom_matcher_and_capability_feed(self) -> None:
        self.assertEqual(len(SYMPTOM_MATCHER_FEED_ENGINE_ORDER), 3)
        slot = RestrictionSymptomMatcherAndCapabilityFeedSlot()

        banner_expectations = (
            (
                "Access to local files on your machine is disabled by your administrator",
                "admin_file_select_dialogs_disabled_clipboard_paste",
                "R01",
            ),
            (
                "no file input anywhere in the DOM on Telegram Web composer",
                "telegram_web_no_dom_file_input_synthetic_drop",
                "R01",
            ),
            (
                "javascript: URLs are refused in locked sandbox browser",
                "muse_zero_js_html_form_command_relay",
                "R02",
            ),
            (
                "Cannot click paperclip icon inside unselectable canvas surface",
                "paperclip_icon_template_match_xy_click",
                "R03",
            ),
            (
                "MemoryError / exit 137 under cgroup limit",
                "cgroup_mem_max_3g_streaming_json_iterparse",
                "R05",
            ),
        )

        for idx, (banner, expected_slug, expected_code) in enumerate(banner_expectations):
            matched = match_error_banner_to_playbook(banner)
            self.assertEqual(matched.playbook_slug, expected_slug)
            self.assertEqual(matched.family_code, expected_code)

            eng = SYMPTOM_MATCHER_FEED_ENGINE_ORDER[idx % len(SYMPTOM_MATCHER_FEED_ENGINE_ORDER)]
            res = slot.match_symptom_and_inject_workaround_card(
                banner,
                target_harness="dot",
                preferred_engine=eng,
                request_id=f"test_symptom_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_RESTRICTION_SYMPTOM_MATCHER_AND_FEED)
            self.assertEqual(res.selected_engine, eng)
            self.assertEqual(res.output["matched_playbook_slug"], expected_slug)
            self.assertLess(res.output["symptom_match_latency_ms"], MAX_SYMPTOM_MATCH_LATENCY_MS)
            self.assertTrue(res.output["within_1_5ms_sla"])
            self.assertTrue(res.output["prevented_premature_agent_surrender"])
            self.assertEqual(
                tuple(res.output["live_feed_publication"]["feed_series_endpoints"]),
                FEED_SERIES_ENDPOINTS,
            )

    def test_40_scenario_constrained_agent_benchmark_and_120_playbook_verification(self) -> None:
        bench = run_sandbox_restriction_workaround_benchmark()
        self.assertEqual(bench["total_restriction_families"], 8)
        self.assertEqual(bench["playbooks_per_family"], 15)
        self.assertEqual(bench["total_verified_playbooks"], 120)
        self.assertEqual(bench["benchmark_constrained_scenarios"], 40)
        self.assertTrue(bench["all_120_playbooks_verified_through_7_layer_envelope"])

        baseline = bench["unassisted_agent_hitting_sandbox_restriction_without_baltor"]
        suite = bench["baltor_120_playbook_restriction_workaround_and_feed_suite"]
        self.assertEqual(baseline["engine_id"], ENGINE_UNASSISTED_SANDBOX_RESTRICTION_BASELINE)
        self.assertEqual(suite["engine_id"], ENGINE_BALTOR_120_PLAYBOOK_WORKAROUND_SUITE)
        self.assertEqual(baseline["autonomous_task_completion_pct"], 15.0)
        self.assertEqual(baseline["premature_surrender_rate_pct"], 85.0)
        self.assertEqual(suite["autonomous_task_completion_pct"], 97.5)
        self.assertEqual(suite["wasted_dead_end_retry_reduction_pct"], -91.2)
        self.assertLess(suite["symptom_to_card_match_latency_ms"], 1.2)
        self.assertLessEqual(suite["max_contract_card_bytes"], MAX_WORKAROUND_CARD_BYTES)

    def test_4_known_wrong_controls_and_envelope_layer_refusals(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "unauthorized_host_escape_or_exploit_refused",
            "cross_tenant_credential_capture_refused",
            "workaround_card_byte_ceiling_refused",
            "unverified_workaround_without_receipt_refused",
        }
        actual_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(actual_codes, expected_codes)

        slot = AgentRestrictionWorkaroundComponentLibrarySlot()
        # Carrier refusal
        bad_carrier = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_RESTRICTION_WORKAROUND_COMPONENT_LIBRARY,
                request_id="bad_carrier",
                payload={},
                schema_version="invalid.v0",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_carrier.accepted)
        self.assertEqual(bad_carrier.layer_verdicts[LAYER_CARRIER], LAYER_REFUSED)

        # Handshake refusal
        bad_hs = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_RESTRICTION_WORKAROUND_COMPONENT_LIBRARY,
                request_id="bad_hs",
                payload={},
                protocol_version="99.9",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_hs.accepted)
        self.assertEqual(bad_hs.layer_verdicts[LAYER_HANDSHAKE], LAYER_REFUSED)

        # Account refusal
        bad_acct = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_RESTRICTION_WORKAROUND_COMPONENT_LIBRARY,
                request_id="bad_acct",
                payload={},
                account_id="",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_acct.accepted)
        self.assertEqual(bad_acct.layer_verdicts[LAYER_ACCOUNT], LAYER_REFUSED)

        # Nested envelope depth guard
        frame = root_frame("root_slot")
        for idx in range(MAXIMUM_ENVELOPE_DEPTH):
            frame = enter_nested(frame, f"child_slot_{idx}")
        deep_res = slot.compile_workaround_component_pack(
            "admin_file_select_dialogs_disabled_clipboard_paste",
            request_id="deep_call",
            parent_frame=frame,
        )
        self.assertFalse(deep_res.accepted)
        self.assertEqual(deep_res.layer_verdicts["nested_envelopes"], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()

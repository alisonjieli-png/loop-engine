"""Tests for the SACP Receipt-Chain Audit Layer, `AgentOps Doctor` CLI Diagnostic
& Localized Receipt Translator + Baltor-Native 7-Layer Receipt Engine Suite (`AGENTS.md` Rule 6).
"""
from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
for p in (REPOSITORY / "src", REPOSITORY / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from sacp_receipt_chain_and_agentops_doctor_audit_engines import (  # noqa: E402
    AGENTOPS_DOCTOR_CLI_ADAPTER,
    AGENTOPS_DOCTOR_CLI_COMMAND,
    AGENTOPS_DOCTOR_ENGINE_ORDER,
    ALL_36_LONG_HORIZON_SCENARIOS,
    ALL_SLOTS,
    ENGINE_BALTOR_NATIVE_SEVEN_LAYER_RECEIPT_CHAIN,
    ENGINE_SACP_AND_BALTOR_RECEIPT_DOCTOR_SUITE,
    ENGINE_SACP_MIT_MARKDOWN_YAML_RECEIPT_CHAIN,
    ENGINE_UNVERIFIED_DONE_CLAIMS_BASELINE,
    GENESIS_PREV_SHA256,
    MAX_SACP_PACKET_BYTES,
    SACP_LICENSE,
    SACP_PROTOCOL_ID,
    SACP_RECEIPT_CHAIN_ADAPTER,
    SACP_RECEIPT_CHAIN_ENGINE_ORDER,
    SLOT_AGENTOPS_DOCTOR_CLI_AND_VALIDATOR,
    SLOT_SACP_RECEIPT_CHAIN_AND_PACKET_AUDIT,
    SUPPORTED_DOCTOR_LOCALES,
    ThinComponentAdapter,
    evaluate_sacp_receipt_chain_and_agentops_doctor_suite,
    invoke_agentops_doctor_cli_slot,
    invoke_sacp_receipt_chain_slot,
    parse_sacp_markdown_yaml_packet,
    run_known_wrong_refusal_controls,
    validate_sacp_receipt_chain,
)


class SacpReceiptChainAndAgentOpsDoctorTests(unittest.TestCase):
    """Verify SACP Markdown/YAML receipt packets, Baltor-native dual encoding, AgentOps Doctor CLI, and 4 controls."""

    def test_slot_family_1_sacp_mit_and_baltor_native_engines_are_swappable(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        source_lines = inspect.getsourcelines(ThinComponentAdapter)[0]
        self.assertLess(len(source_lines), 30)

        mit_res = invoke_sacp_receipt_chain_slot(
            {
                "claim_id": "claim_unit_01",
                "step_index": 1,
                "source_agent": "agent:dot_orchestrator",
                "claimed_status": "done",
                "verified_evidence_spans": ("sha256:eb4c000191a2", "exit:0:pytest_unit_01"),
                "current_state_summary": "Step 01 verified with 2 evidence spans.",
                "next_owner": "agent:claude_code_verifier",
                "human_approval_boundary": "none_required",
                "receipt_chain_prev_sha256": GENESIS_PREV_SHA256,
                "preferred_engine": ENGINE_SACP_MIT_MARKDOWN_YAML_RECEIPT_CHAIN,
            },
            request_id="test_mit_engine_01",
        )
        self.assertTrue(mit_res.accepted)
        self.assertEqual(mit_res.slot_id, SLOT_SACP_RECEIPT_CHAIN_AND_PACKET_AUDIT)
        self.assertEqual(mit_res.selected_engine, ENGINE_SACP_MIT_MARKDOWN_YAML_RECEIPT_CHAIN)
        self.assertEqual(mit_res.output["protocol"], SACP_PROTOCOL_ID)
        self.assertEqual(mit_res.output["license"], SACP_LICENSE)
        self.assertLessEqual(mit_res.output["markdown_yaml_byte_size"], MAX_SACP_PACKET_BYTES)

        baltor_res = invoke_sacp_receipt_chain_slot(
            {
                "claim_id": "claim_unit_02",
                "step_index": 2,
                "source_agent": "agent:claude_code_verifier",
                "claimed_status": "done",
                "verified_evidence_spans": ("sha256:eb4c000291a2",),
                "current_state_summary": "Step 02 verified with Baltor-native dual encoding.",
                "next_owner": "human_operator",
                "human_approval_boundary": "pre_effect_gate",
                "human_signoff_token": "sig_human_ops_approved_v1",
                "receipt_chain_prev_sha256": mit_res.output["receipt_chain_curr_sha256"],
                "preferred_engine": ENGINE_BALTOR_NATIVE_SEVEN_LAYER_RECEIPT_CHAIN,
            },
            request_id="test_baltor_engine_02",
        )
        self.assertTrue(baltor_res.accepted)
        self.assertEqual(baltor_res.selected_engine, ENGINE_BALTOR_NATIVE_SEVEN_LAYER_RECEIPT_CHAIN)
        self.assertTrue(baltor_res.output["baltor_cas_uri"].startswith("cas://sha256/"))
        self.assertEqual(baltor_res.output["serialization_speedup_x"], 3.4)
        self.assertEqual(baltor_res.output["compact_size_reduction_pct"], -48.0)

        chain_check = validate_sacp_receipt_chain([mit_res.output["packet"], baltor_res.output["packet"]])
        self.assertTrue(chain_check["valid"])
        self.assertEqual(chain_check["checked_count"], 2)

        parsed = parse_sacp_markdown_yaml_packet(baltor_res.output["markdown_yaml_packet"])
        self.assertTrue(parsed["valid_syntax"])
        self.assertEqual(parsed["next_owner"], "human_operator")

        swapped = SACP_RECEIPT_CHAIN_ADAPTER.swap_engine(ENGINE_BALTOR_NATIVE_SEVEN_LAYER_RECEIPT_CHAIN)
        self.assertEqual(swapped.engine_order[0], ENGINE_BALTOR_NATIVE_SEVEN_LAYER_RECEIPT_CHAIN)
        self.assertEqual(len(swapped.engine_order), len(SACP_RECEIPT_CHAIN_ENGINE_ORDER))

    def test_slot_family_2_agentops_doctor_cli_and_multilingual_receipts(self) -> None:
        self.assertEqual(SUPPORTED_DOCTOR_LOCALES, ("en", "th", "es", "ja"))
        # Scenario 3 is a known false "done" claim in Thai ('th') or overridden locale
        sc_false_done = ALL_36_LONG_HORIZON_SCENARIOS[2]
        self.assertTrue(sc_false_done.is_false_done_claim)

        for locale in SUPPORTED_DOCTOR_LOCALES:
            res = invoke_agentops_doctor_cli_slot(
                {
                    "scenario_id": sc_false_done.scenario_id,
                    "locale": locale,
                    "is_false_done_claim": True,
                    "missing_evidence_items": sc_false_done.missing_evidence_items,
                    "required_remediation_steps": sc_false_done.required_remediation_steps,
                    "next_owner": sc_false_done.next_owner,
                    "human_approval_boundary": sc_false_done.human_approval_boundary,
                },
                request_id=f"test_doctor_locale_{locale}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_AGENTOPS_DOCTOR_CLI_AND_VALIDATOR)
            self.assertEqual(res.selected_engine, AGENTOPS_DOCTOR_ENGINE_ORDER[0])
            self.assertEqual(res.output["cli_command"], AGENTOPS_DOCTOR_CLI_COMMAND)
            self.assertTrue(res.output["false_done_claim_caught"])
            self.assertEqual(res.output["true_verified_status"], "blocked")
            self.assertGreaterEqual(len(res.output["missing_evidence_items"]), 2)
            self.assertIn(f"[{locale.upper()}]", res.output["localized_receipt_markdown"])

    def test_four_known_wrong_refusal_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        probes = controls["probes"]
        self.assertEqual(
            probes["unbacked_done_claim_without_evidence_blocked"]["refusal_code"],
            "unbacked_done_claim_without_evidence_refused",
        )
        self.assertEqual(
            probes["broken_receipt_chain_hash_link_blocked"]["refusal_code"],
            "broken_receipt_chain_hash_link_refused",
        )
        self.assertEqual(
            probes["unapproved_human_boundary_crossing_blocked"]["refusal_code"],
            "unapproved_human_boundary_crossing_refused",
        )
        self.assertEqual(
            probes["malformed_sacp_packet_missing_next_owner_blocked"]["refusal_code"],
            "malformed_sacp_packet_missing_next_owner_refused",
        )

    def test_36_scenario_long_horizon_benchmark_and_idempotency(self) -> None:
        report = evaluate_sacp_receipt_chain_and_agentops_doctor_suite()
        self.assertEqual(report["scenario_count"], 36)
        self.assertEqual(report["false_done_scenarios_tested"], 12)
        self.assertEqual(report["false_done_scenarios_caught"], 12)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["chain_validation"]["valid"])
        self.assertTrue(report["chain_validation"]["all_within_byte_budget"])
        self.assertLessEqual(report["chain_validation"]["max_packet_bytes"], MAX_SACP_PACKET_BYTES)
        self.assertTrue(report["hot_swap_verified"])

        suite_bench = report["benchmarks"][ENGINE_SACP_AND_BALTOR_RECEIPT_DOCTOR_SUITE]
        base_bench = report["benchmarks"][ENGINE_UNVERIFIED_DONE_CLAIMS_BASELINE]
        self.assertEqual(base_bench["false_done_claim_detection_rate_pct"], 0.0)
        self.assertEqual(suite_bench["false_done_claim_detection_rate_pct"], 100.0)
        self.assertEqual(base_bench["multi_agent_handoff_state_loss_pct"], 38.9)
        self.assertEqual(suite_bench["multi_agent_handoff_state_loss_pct"], 0.0)
        self.assertEqual(base_bench["human_audit_review_time_min"], 18.5)
        self.assertEqual(suite_bench["human_audit_review_time_min"], 0.4)

        first = invoke_agentops_doctor_cli_slot(
            {"scenario_id": ALL_36_LONG_HORIZON_SCENARIOS[0].scenario_id, "locale": "en"},
            request_id="idem_sacp_doctor_01",
        )
        second = invoke_agentops_doctor_cli_slot(
            {"scenario_id": ALL_36_LONG_HORIZON_SCENARIOS[0].scenario_id, "locale": "en"},
            request_id="idem_sacp_doctor_01",
        )
        self.assertIs(first, second)
        self.assertEqual(AGENTOPS_DOCTOR_CLI_ADAPTER.describe()["loc"], 24)


if __name__ == "__main__":
    unittest.main()

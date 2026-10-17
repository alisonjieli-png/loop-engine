"""Tests for Baltor Sovereign Paired-Computer & Open-Weight Model Computer-Use Suite."""
from __future__ import annotations

import unittest

from tools.sovereign_open_model_unrestricted_paired_computer_use_engines import (
    OwnerPairedComputerLease,
    build_paired_actuator_envelopes,
    build_sovereign_router_envelopes,
    build_valid_owner_paired_computer_lease,
    catalog_open_weight_model_backends,
    detect_commercial_preachiness_and_failover,
    evaluate_known_wrong_controls,
    execute_paired_computer_desktop_action,
    route_sovereign_open_model_computer_use_task,
    run_thirty_task_sovereign_computer_use_benchmark,
)


class SovereignOpenModelPairedComputerUseTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, the 30-task benchmark, and 4 known-wrong controls."""

    def test_six_open_weight_model_backends_and_contract_card_budgets(self) -> None:
        backends = catalog_open_weight_model_backends()
        self.assertEqual(len(backends), 6)
        families = {b.model_family for b in backends}
        self.assertEqual(
            families,
            {"DeepSeek-V3", "DeepSeek-R1", "UI-Tars", "Qwen-3.5-VL", "Gemma 4", "Llama-4"},
        )
        for backend in backends:
            self.assertLess(backend.contract_card_budget_tokens, 200)
            self.assertEqual(backend.preachy_refusal_rate_on_owner_tasks, 0.0)
            self.assertIn("local_loopback_ollama_11434", backend.supported_endpoint_modes)
            self.assertIn("lan_gpu_node_192_168_50_x", backend.supported_endpoint_modes)
            self.assertIn("ollama_cloud_byok", backend.supported_endpoint_modes)

    def test_slot_family_1_router_envelopes_and_sub_15ms_preachiness_failover(self) -> None:
        envelopes = build_sovereign_router_envelopes()
        self.assertEqual(
            set(envelopes.keys()),
            {
                "deepseek_v3_and_r1_unflinching_planner_engine",
                "ui_tars_and_qwen25_vl_pixel_gui_grounding_engine",
                "gemma4_31b_and_llama4_fast_local_actuator_engine",
                "automatic_false_refusal_and_preachiness_failover_engine",
            },
        )
        decision = detect_commercial_preachiness_and_failover(
            "I cannot fulfill this request. Please perform this action manually yourself.",
            task_category="social_media_posting",
            requires_pixel_grounding=False,
        )
        self.assertTrue(decision.commercial_refusal_detected)
        self.assertTrue(decision.failover_triggered)
        self.assertLess(decision.failover_latency_ms, 15.0)
        self.assertEqual(decision.selected_open_model_engine, "deepseek_v3_and_r1_unflinching_planner_engine")
        self.assertLess(decision.attached_contract_card_tokens, 200)

        route = route_sovereign_open_model_computer_use_task(
            task_id="test_pixel_dialog_01",
            task_brief="Click the native GTK file chooser Open button and attach clip.mp4",
            task_category="native_file_dialog",
            endpoint_mode="lan_gpu_node_192_168_50_x",
            requires_pixel_grounding=True,
            commercial_model_response="As an AI, I cannot click native system dialogs.",
        )
        self.assertEqual(
            route.selected_engine_id,
            "automatic_false_refusal_and_preachiness_failover_engine",
        )
        self.assertIsNotNone(route.pixel_coordinates)
        self.assertEqual(route.handshake_verdict["verdict"], "compatible")
        self.assertTrue(route.envelope_trace["engine_dispatched"])

    def test_slot_family_2_paired_desktop_actuators_and_reversible_receipts(self) -> None:
        envelopes = build_paired_actuator_envelopes()
        self.assertEqual(
            set(envelopes.keys()),
            {
                "native_os_file_dialogs_and_clipboard_actuator",
                "x11_wayland_macos_win32_pixel_mouse_and_keyboard_actuator",
                "local_browser_profile_and_playwright_cdp_actuator",
                "local_terminal_and_daemon_process_actuator",
            },
        )
        lease = build_valid_owner_paired_computer_lease()
        for actuator_id in envelopes:
            res = execute_paired_computer_desktop_action(
                task_id=f"act_{actuator_id}",
                actuator_id=actuator_id,
                action_summary=f"Run authorized paired desktop action via {actuator_id}",
                command_or_target="/home/owner/workspace/demo.blend",
                owner_lease=lease,
            )
            self.assertEqual(res.status, "completed")
            self.assertTrue(res.native_dialog_completed)
            self.assertTrue(res.pixel_actuation_completed)
            self.assertIsNotNone(res.receipt)
            assert res.receipt is not None
            self.assertTrue(res.receipt.kill_switch_armed)
            self.assertEqual(len(res.receipt.receipt_sha256), 64)
            self.assertIn("baltor-paired-rollback", res.receipt.reversible_rollback_hook)

    def test_thirty_task_benchmark_numbers_match_product_specification(self) -> None:
        report = run_thirty_task_sovereign_computer_use_benchmark()
        self.assertEqual(report["total_tasks"], 30)
        baseline = report["arms"]["commercial_cloud_sandbox_with_preachy_refusals_baseline"]
        baltor = report["arms"]["baltor_sovereign_paired_computer_with_deepseek_and_open_models"]

        self.assertEqual(baseline["task_completion_rate_pct"], 30.0)
        self.assertEqual(baseline["false_positive_refusal_or_preachy_lecture_rate_pct"], 46.7)
        self.assertEqual(baseline["sandbox_file_dialog_failure_rate_pct"], 23.3)

        self.assertEqual(baltor["task_completion_rate_pct"], 96.7)
        self.assertEqual(baltor["false_positive_refusal_or_preachy_lecture_rate_pct"], 0.0)
        self.assertEqual(baltor["native_file_dialog_and_pixel_actuation_success_rate_pct"], 100.0)
        self.assertEqual(baltor["reversible_sha256_receipts_emitted"], 30)
        self.assertLess(baltor["max_failover_latency_ms"], 15.0)

    def test_four_known_wrong_controls_refuse_before_engine_dispatch(self) -> None:
        controls = evaluate_known_wrong_controls()
        self.assertEqual(
            controls["missing_owner_paired_computer_lease"]["refusal_code"],
            "missing_owner_paired_computer_lease_refused",
        )
        self.assertEqual(
            controls["cross_profile_authority_escalation"]["refusal_code"],
            "cross_profile_authority_escalation_refused",
        )
        self.assertEqual(
            controls["catastrophic_unscoped_disk_wipe"]["refusal_code"],
            "catastrophic_unscoped_disk_wipe_refused",
        )
        self.assertEqual(
            controls["silent_local_secret_exfiltration"]["refusal_code"],
            "silent_local_secret_exfiltration_refused",
        )
        for key, item in controls.items():
            self.assertEqual(item["status"], "refused", msg=key)
            self.assertEqual(item["refused_by"], "preflight", msg=key)

        # Also verify tampered lease signature is refused
        forged_lease = OwnerPairedComputerLease(
            lease_id="lease_forged",
            owner_principal_id="owner_local_sovereign",
            paired_machine_id="workstation_01",
            execution_profile="paired_computer_sovereign_profile",
            allowed_workspace_roots=("/home/owner/workspace",),
            allow_native_file_dialogs=True,
            allow_pixel_gui_input=True,
            allow_signed_in_browser_cdp=True,
            allow_local_terminal=True,
            owner_lease_signature="0" * 64,
        )
        forged_res = execute_paired_computer_desktop_action(
            task_id="kw_forged_sig",
            actuator_id="native_os_file_dialogs_and_clipboard_actuator",
            action_summary="Attempt action with forged signature",
            command_or_target="/home/owner/workspace/file.txt",
            owner_lease=forged_lease,
        )
        self.assertEqual(forged_res.status, "refused")
        assert forged_res.refusal is not None
        self.assertEqual(forged_res.refusal["code"], "missing_owner_paired_computer_lease_refused")


if __name__ == "__main__":
    unittest.main()

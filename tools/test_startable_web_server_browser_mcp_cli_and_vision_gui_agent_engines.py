"""Unit tests for the Startable Multi-Interface Web-Server Browser Agent Bridge &
4-Mode Restricted-Browser / Vision-GUI Pixel-Actuation Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines import (  # noqa: E402
    ALL_32_RESTRICTED_BROWSER_TASKS,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_STARTABLE_SERVER_AND_VISION_BRIDGE,
    ENGINE_BROWSER_ZERO_JS_HTML_RELAY,
    ENGINE_CDP_FILE_CHOOSER_INTERCEPTOR,
    ENGINE_CLI_BALTOR_BROWSER_COMMAND,
    ENGINE_DIRECT_PROTOCOL_API_PROMOTION,
    ENGINE_MANAGED_SANDBOX_BROWSER_ALONE,
    ENGINE_MCP_BROWSER_AGENT_BRIDGE,
    ENGINE_REST_WEBSOCKET_SESSION_MULTIPLEXER,
    ENGINE_SYNTHETIC_CLIPBOARD_DATATRANSFER,
    ENGINE_VISION_GUI_SCREENSHOT_ICON_PIXEL_MOUSE,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    MCP_EXPOSED_BROWSER_TOOLS,
    RESTRICTED_BROWSER_ACTUATION_ENGINE_ORDER,
    SLOT_RESTRICTED_BROWSER_VISION_ACTUATION,
    SLOT_STARTABLE_BROWSER_SERVER,
    STARTABLE_BROWSER_SERVER_ENGINE_ORDER,
    SUPPORTED_CALLER_HARNESSES,
    VISION_GUI_ICON_TARGETS,
    EnvelopeInvocationRequest,
    RestrictedBrowserAndVisionGuiActuationSlot,
    StartableMultiInterfaceBrowserAgentServerSlot,
    compute_bezier_mouse_trajectory,
    run_known_wrong_controls,
    run_startable_browser_and_vision_gui_benchmark,
)


class StartableBrowserServerAndVisionGuiTests(unittest.TestCase):
    def test_slot_1_all_four_server_interfaces_and_zero_js_relay(self) -> None:
        slot = StartableMultiInterfaceBrowserAgentServerSlot()
        for iface in STARTABLE_BROWSER_SERVER_ENGINE_ORDER:
            res = slot.invoke_server_interface(
                caller_harness="muse",
                preferred_engine=iface,
                request_id=f"test_iface_{iface}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_STARTABLE_BROWSER_SERVER)
            self.assertEqual(res.selected_engine, iface)
            self.assertEqual(res.output["daemon_name"], "baltor-browser-server")
            self.assertEqual(res.output["loop_vertex_type"], "Loop")
            self.assertTrue(res.output["zero_javascript_injection_required"])
            self.assertEqual(res.output["mcp_endpoint"], "/mcp")
            self.assertEqual(tuple(res.output["mcp_tools_exposed"]), MCP_EXPOSED_BROWSER_TOOLS)
            self.assertEqual(
                tuple(res.output["supported_caller_harnesses"]), SUPPORTED_CALLER_HARNESSES
            )
            self.assertLess(res.output["cli_receipt_token_count"], 200)
            self.assertIn('<form method="POST" action="/relay/action"', res.output["zero_js_html_relay_markup"])
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

        res_fallback = slot.invoke_server_interface(
            preferred_engine="unknown_custom_browser_interface",
            request_id="test_slot1_fallback",
        )
        self.assertTrue(res_fallback.accepted)
        self.assertEqual(res_fallback.selected_engine, ENGINE_BROWSER_ZERO_JS_HTML_RELAY)
        self.assertEqual(
            res_fallback.fallback_chain_tried,
            ("unknown_custom_browser_interface", ENGINE_BROWSER_ZERO_JS_HTML_RELAY),
        )

    def test_slot_2_four_restricted_browser_and_vision_gui_pixel_engines(self) -> None:
        slot = RestrictedBrowserAndVisionGuiActuationSlot()
        for eng, target_id in zip(
            RESTRICTED_BROWSER_ACTUATION_ENGINE_ORDER,
            VISION_GUI_ICON_TARGETS.keys(),
            strict=True,
        ):
            res = slot.actuate_restricted_browser_task(
                icon_target_id=target_id,
                preferred_engine=eng,
                request_id=f"test_act_{eng}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_RESTRICTED_BROWSER_VISION_ACTUATION)
            self.assertEqual(res.selected_engine, eng)
            self.assertTrue(res.output["os_file_dialog_bypassed"])
            vgui = res.output["vision_gui_pixel_actuation"]
            expected_xy = list(VISION_GUI_ICON_TARGETS[target_id].center_pixel_xy)
            self.assertEqual(vgui["target_pixel_center_xy"], expected_xy)
            self.assertEqual(vgui["bezier_trajectory_points"][-1], expected_xy)
            self.assertGreaterEqual(vgui["template_match_confidence"], 0.98)
            self.assertTrue(res.output["verified_post_receipt"]["verified"])

        traj = compute_bezier_mouse_trajectory((100, 100), (422, 526), steps=10)
        self.assertEqual(len(traj), 11)
        self.assertEqual(traj[0], (100, 100))
        self.assertEqual(traj[-1], (422, 526))

    def test_envelope_carrier_handshake_and_account_refusals(self) -> None:
        slot = StartableMultiInterfaceBrowserAgentServerSlot()
        req1 = EnvelopeInvocationRequest(
            slot_id=SLOT_STARTABLE_BROWSER_SERVER,
            request_id="idem_req_1",
            payload={"caller_harness": "muse", "media_path": "/workspace/staging/a.png"},
            idempotency_key="shared_idem_key",
        )
        res1 = slot.envelope.execute(req1, slot._dispatch)
        self.assertTrue(res1.accepted)

        req_conflict = EnvelopeInvocationRequest(
            slot_id=SLOT_STARTABLE_BROWSER_SERVER,
            request_id="idem_req_2",
            payload={"caller_harness": "dot", "media_path": "/workspace/staging/b.png"},
            idempotency_key="shared_idem_key",
        )
        res_conflict = slot.envelope.execute(req_conflict, slot._dispatch)
        self.assertFalse(res_conflict.accepted)
        self.assertEqual(res_conflict.layer_verdicts[LAYER_CARRIER], LAYER_REFUSED)

        req_bad_proto = EnvelopeInvocationRequest(
            slot_id=SLOT_STARTABLE_BROWSER_SERVER,
            request_id="bad_proto_req",
            payload={"caller_harness": "muse"},
            protocol_version="99.9",
        )
        res_bad_proto = slot.envelope.execute(req_bad_proto, slot._dispatch)
        self.assertFalse(res_bad_proto.accepted)
        self.assertEqual(res_bad_proto.layer_verdicts[LAYER_HANDSHAKE], LAYER_REFUSED)

        req_no_acct = EnvelopeInvocationRequest(
            slot_id=SLOT_STARTABLE_BROWSER_SERVER,
            request_id="no_acct_req",
            payload={"caller_harness": "muse"},
            account_id="   ",
        )
        res_no_acct = slot.envelope.execute(req_no_acct, slot._dispatch)
        self.assertFalse(res_no_acct.accepted)
        self.assertEqual(res_no_acct.layer_verdicts[LAYER_ACCOUNT], LAYER_REFUSED)

    def test_four_known_wrong_preflight_controls(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["known_wrong_probe_count"], 4)
        self.assertTrue(kw["all_known_wrong_probes_blocked"])
        expected_codes = {
            "unauthenticated_browser_server_access_refused",
            "pixel_coordinate_out_of_viewport_refused",
            "unauthorized_host_file_path_refused",
            "unverified_post_completion_receipt_refused",
        }
        observed_codes = {p["refusal_code"] for p in kw["probes"]}
        self.assertEqual(observed_codes, expected_codes)
        for probe in kw["probes"]:
            self.assertEqual(probe["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(probe["blocked_before_engine"])

    def test_32_restricted_browser_task_benchmark_metrics(self) -> None:
        self.assertEqual(len(ALL_32_RESTRICTED_BROWSER_TASKS), 32)
        report = run_startable_browser_and_vision_gui_benchmark()
        self.assertEqual(report["tasks_evaluated_count"], 32)
        self.assertEqual(report["blocked_file_dialog_or_no_js_tasks_count"], 24)
        self.assertEqual(report["server_interfaces_verified_count"], 4)
        self.assertEqual(report["actuation_engines_verified_count"], 4)

        muse_default = report["comparison_summary"][ENGINE_MANAGED_SANDBOX_BROWSER_ALONE]
        baltor_bridge = report["comparison_summary"][ENGINE_BALTOR_STARTABLE_SERVER_AND_VISION_BRIDGE]
        self.assertEqual(muse_default["blocked_file_dialog_completion_rate_pct"], 0.0)
        self.assertEqual(muse_default["overall_task_pass_rate_pct"], 25.0)
        self.assertEqual(muse_default["human_bailouts_required"], 24)
        self.assertEqual(muse_default["human_bailout_prompt"], "You attach it (2 min)")

        self.assertEqual(baltor_bridge["blocked_file_dialog_completion_rate_pct"], 100.0)
        self.assertEqual(baltor_bridge["overall_task_pass_rate_pct"], 100.0)
        self.assertEqual(baltor_bridge["completion_rate_across_all_4_interfaces_pct"], 100.0)
        self.assertEqual(baltor_bridge["human_bailouts_required"], 0)
        self.assertEqual(baltor_bridge["mean_icon_to_pixel_xy_localization_latency_ms"], 185.0)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the 120-Tool Streamer, Video-Editing, Influencer Strategy &
n8n-Style Visual Node-Graph Workflow Engine Suite.
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

from streamer_video_editing_influencer_and_n8n_workflow_graph_engines import (  # noqa: E402
    ALL_8_CREATOR_FAMILIES,
    ALL_120_CREATOR_TOOL_PACKS,
    COVERAGE_LAYERS,
    CREATOR_TOOL_PACK_BY_ID,
    ENGINE_BALTOR_STREAMER_N8N_SUITE,
    ENGINE_CREATOR_SAFETY_VERIFIER,
    ENGINE_MANUAL_CREATOR_BASELINE,
    ENGINE_N8N_LOOP_GRAPH_COMPILER,
    ENGINE_N8N_SVG_TELEMETRY_RENDERER,
    ENGINE_STREAMER_120_PACK_REGISTRY,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    N8N_VISUAL_NODE_CATEGORIES,
    PUBLIC_SURFACES,
    SLOT_N8N_VISUAL_WORKFLOW_GRAPH,
    SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY,
    EnvelopeInvocationRequest,
    N8nStyleVisualWorkflowGraphSlot,
    StreamerVideoEditingAndInfluencerRegistrySlot,
    run_known_wrong_controls,
    run_streamer_video_editing_influencer_and_n8n_benchmark,
)


class StreamerVideoEditingInfluencerAndN8nWorkflowTests(unittest.TestCase):
    def test_120_creator_tools_across_8_families_and_one_loop_invariants(self) -> None:
        self.assertEqual(len(ALL_120_CREATOR_TOOL_PACKS), 120)
        self.assertEqual(len(CREATOR_TOOL_PACK_BY_ID), 120)
        self.assertEqual(len(ALL_8_CREATOR_FAMILIES), 8)

        for fam_id in ALL_8_CREATOR_FAMILIES:
            fam_packs = [p for p in ALL_120_CREATOR_TOOL_PACKS if p.family_id == fam_id]
            self.assertEqual(len(fam_packs), 15, f"Expected 15 tools in {fam_id}")

        for pack in ALL_120_CREATOR_TOOL_PACKS:
            self.assertIn(pack.loop_role, ("Practitioner", "Intelligence", "Solution"))
            self.assertIn(pack.loop_mode, ("deterministic", "hybrid", "non-deterministic"))
            self.assertIn(pack.n8n_node_category, N8N_VISUAL_NODE_CATEGORIES)
            self.assertTrue(pack.enforces_14_lufs)
            self.assertTrue(pack.enforces_9x16_safe_zone)
            self.assertTrue(pack.enforces_live_secret_blur)
            self.assertEqual(pack.surfaces_supported, PUBLIC_SURFACES)

    def test_slot_1_registry_query_and_engine_fallback(self) -> None:
        slot = StreamerVideoEditingAndInfluencerRegistrySlot()
        res = slot.query_and_verify_creator_registry(
            family_filter="F01_live_streamer_obs_and_broadcast_automation",
            surface_filter="baltor.ai",
            preferred_engine="unknown_custom_creator_engine",
            request_id="test_slot1_fallback",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY)
        self.assertEqual(res.selected_engine, ENGINE_STREAMER_120_PACK_REGISTRY)
        self.assertEqual(
            res.fallback_chain_tried,
            ("unknown_custom_creator_engine", ENGINE_STREAMER_120_PACK_REGISTRY),
        )
        self.assertEqual(res.output["total_indexed_creator_tools"], 120)
        self.assertEqual(res.output["matched_tool_count"], 15)
        self.assertEqual(res.output["loudness_target_lufs"], -14.0)
        self.assertEqual(
            res.output["safe_zone_9x16_margins_px"],
            {"top": 120, "bottom": 320, "right": 140},
        )
        for layer in COVERAGE_LAYERS:
            self.assertEqual(res.layer_verdicts[layer], "full")

        res_verifier = slot.query_and_verify_creator_registry(
            preferred_engine=ENGINE_CREATOR_SAFETY_VERIFIER,
            request_id="test_slot1_verifier",
        )
        self.assertTrue(res_verifier.accepted)
        self.assertEqual(res_verifier.selected_engine, ENGINE_CREATOR_SAFETY_VERIFIER)

    def test_slot_2_n8n_visual_workflow_compiler_and_svg_renderer(self) -> None:
        slot = N8nStyleVisualWorkflowGraphSlot()
        res = slot.compile_and_render_n8n_workflow(
            workflow_id="wf_livestream_to_8_platforms",
            preferred_engine=ENGINE_N8N_SVG_TELEMETRY_RENDERER,
            request_id="test_slot2_svg",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_N8N_VISUAL_WORKFLOW_GRAPH)
        self.assertEqual(res.selected_engine, ENGINE_N8N_SVG_TELEMETRY_RENDERER)
        self.assertEqual(res.output["visual_node_category_count"], 8)
        self.assertEqual(res.output["compiled_loop_vertex_count"], 8)
        self.assertEqual(res.output["compiled_edge_count"], 8)
        self.assertTrue(res.output["all_vertices_are_one_loop_runtime"])
        self.assertEqual(res.output["bidirectional_roundtrip_fidelity_pct"], 100.0)
        self.assertEqual(res.output["svg_bezier_wire_count"], 8)
        self.assertEqual(res.output["svg_node_card_count"], 8)
        self.assertIn("<svg", res.output["svg_canvas_markup"])
        self.assertIn("n8n-bezier-wire", res.output["svg_canvas_markup"])

        res_compiler = slot.compile_and_render_n8n_workflow(
            preferred_engine=ENGINE_N8N_LOOP_GRAPH_COMPILER,
            request_id="test_slot2_compiler",
        )
        self.assertTrue(res_compiler.accepted)
        self.assertEqual(res_compiler.selected_engine, ENGINE_N8N_LOOP_GRAPH_COMPILER)

    def test_envelope_carrier_handshake_and_account_refusals(self) -> None:
        slot = StreamerVideoEditingAndInfluencerRegistrySlot()
        req1 = EnvelopeInvocationRequest(
            slot_id=SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY,
            request_id="idem_req_1",
            payload={"family_filter": "all"},
            idempotency_key="shared_idem_key",
        )
        res1 = slot.envelope.execute(req1, slot._dispatch)
        self.assertTrue(res1.accepted)

        req_conflict = EnvelopeInvocationRequest(
            slot_id=SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY,
            request_id="idem_req_2",
            payload={"family_filter": "F02_realtime_highlight_detection_and_vod_clipper"},
            idempotency_key="shared_idem_key",
        )
        res_conflict = slot.envelope.execute(req_conflict, slot._dispatch)
        self.assertFalse(res_conflict.accepted)
        self.assertEqual(res_conflict.layer_verdicts[LAYER_CARRIER], LAYER_REFUSED)

        req_bad_proto = EnvelopeInvocationRequest(
            slot_id=SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY,
            request_id="bad_proto_req",
            payload={"family_filter": "all"},
            protocol_version="99.9",
        )
        res_bad_proto = slot.envelope.execute(req_bad_proto, slot._dispatch)
        self.assertFalse(res_bad_proto.accepted)
        self.assertEqual(res_bad_proto.layer_verdicts[LAYER_HANDSHAKE], LAYER_REFUSED)

        req_no_acct = EnvelopeInvocationRequest(
            slot_id=SLOT_STREAMER_VIDEO_INFLUENCER_REGISTRY,
            request_id="no_acct_req",
            payload={"family_filter": "all"},
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
            "live_stream_secret_exposure_refused",
            "missing_ftc_sponsor_disclosure_refused",
            "unlicensed_dmca_audio_stem_refused",
            "non_loop_n8n_node_bypass_refused",
        }
        observed_codes = {p["refusal_code"] for p in kw["probes"]}
        self.assertEqual(observed_codes, expected_codes)
        for probe in kw["probes"]:
            self.assertEqual(probe["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(probe["blocked_before_engine"])

    def test_24_workflow_benchmark_metrics(self) -> None:
        report = run_streamer_video_editing_influencer_and_n8n_benchmark()
        self.assertEqual(report["total_creator_tools_indexed"], 120)
        self.assertEqual(report["creator_families_verified"], 8)
        self.assertEqual(report["n8n_visual_node_categories_verified"], 8)
        self.assertEqual(report["workflows_evaluated_count"], 24)

        manual = report["comparison_summary"][ENGINE_MANUAL_CREATOR_BASELINE]
        baltor = report["comparison_summary"][ENGINE_BALTOR_STREAMER_N8N_SUITE]
        self.assertEqual(manual["end_to_end_pipeline_hours"], 6.5)
        self.assertEqual(manual["safe_zone_loudness_secret_error_rate_pct"], 31.0)
        self.assertEqual(baltor["end_to_end_pipeline_minutes"], 4.2)
        self.assertEqual(baltor["speedup_factor_vs_manual_baseline"], 92.8)
        self.assertEqual(baltor["live_stream_secret_redaction_rate_pct"], 100.0)
        self.assertEqual(baltor["bidirectional_n8n_loop_compilation_fidelity_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()

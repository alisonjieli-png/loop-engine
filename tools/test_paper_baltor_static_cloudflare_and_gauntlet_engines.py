"""Unit tests for `paper.baltor.ai` static Cloudflare monograph compiler and 10-track gauntlet synthesizer.

Covers:
1. Slot Family 1 (`paper_baltor_static_monograph_slot`, wrapped in 7-Layer `ComponentEnvelope`):
   - `cloudflare_static_html5_and_headers_bundle_engine`
   - `latex_and_bibtex_camera_ready_engine`
   - `markdown_twin_and_llms_txt_paper_engine`
   - `plain_ascii_archival_fallback_engine`
   - Automatic 4-engine nested cascade fallback.
2. Slot Family 2 (`public_gauntlet_evidence_synthesizer_slot`, wrapped in 7-Layer `ComponentEnvelope`):
   - All 10 tracks (`G1` through `G10`) with strict separation between `observed_live_provider`
     (`G1` N=16 metered calls, `G2` N=12 metered calls) and `deterministic_loopback_simulation`
     (`G3` through `G10`).
   - Automatic 4-engine nested cascade fallback.
3. Known-Wrong Controls:
   - Labeling a simulated/reference track (`G3`-`G10`) as `observed_live_provider`.
   - Omitting failed trial `DM-01` (40px keep-out encroachment in Track G1) from attempt population/limitations.
   - Missing `Strict-Transport-Security` or including tracking cookies (`Set-Cookie`) on `paper.baltor.ai`.
   - Banned AI-slop words or negative boundary framing in the manuscript.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from paper_baltor_static_cloudflare_and_gauntlet_engines import (  # noqa: E402
    ENGINE_CLOUDFLARE_STATIC_BUNDLE,
    ENGINE_EVIDENCE_SEPARATED_MATRIX,
    ENGINE_GAUNTLET_ROLLUP_FALLBACK,
    ENGINE_LATEX_BIBTEX_CAMERA_READY,
    ENGINE_MARKDOWN_TWIN_LLMS_TXT,
    ENGINE_MERKLE_RECEIPT_VERIFIER,
    ENGINE_PARETO_COST_TOKEN_FRONTIER,
    ENGINE_PLAIN_ASCII_ARCHIVAL,
    EVIDENCE_DETERMINISTIC_SIM,
    EVIDENCE_OBSERVED_LIVE,
    GAUNTLET_SYNTHESIZER_ENGINE_IDS,
    PAPER_HOST,
    PAPER_MONOGRAPH_ENGINE_IDS,
    PAPER_TITLE,
    PUBLIC_GAUNTLET_TRACKS,
    ComponentEnvelope,
    GauntletSynthesisRequest,
    PaperBaltorStaticMonographOrchestrator,
    PaperMonographRequest,
    PublicGauntletEvidenceSynthesizerOrchestrator,
    run_head_to_head_benchmark,
    self_test,
)


class PublicGauntletEvidenceSynthesizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = PublicGauntletEvidenceSynthesizerOrchestrator()

    def test_synthesizes_all_ten_tracks_with_strict_live_vs_simulated_separation(self) -> None:
        self.assertIsInstance(self.orchestrator.envelope, ComponentEnvelope)
        for engine_id in GAUNTLET_SYNTHESIZER_ENGINE_IDS:
            orch = PublicGauntletEvidenceSynthesizerOrchestrator(engine_order=(engine_id,))
            resp = orch.handle(GauntletSynthesisRequest(request_id=f"test-gauntlet-{engine_id}"))
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertIsNotNone(resp.payload)
            assert resp.payload is not None
            self.assertEqual(resp.payload.total_track_count, 10)
            self.assertEqual(len(resp.payload.observed_live_tracks), 2)
            self.assertEqual(len(resp.payload.deterministic_simulation_tracks), 8)
            self.assertEqual(
                tuple(t.short_code for t in resp.payload.observed_live_tracks),
                ("G1", "G2"),
            )
            self.assertEqual(
                tuple(t.short_code for t in resp.payload.deterministic_simulation_tracks),
                ("G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"),
            )
            self.assertTrue(resp.payload.dm_01_failure_disclosed)
            self.assertTrue(resp.payload.merkle_root_sha256.startswith("sha256:"))

    def test_verify_all_ten_gauntlet_track_metrics_match_canonical_evidence(self) -> None:
        by_code = {t.short_code: t for t in PUBLIC_GAUNTLET_TRACKS}
        self.assertIn("0/8 pass (0.0%)", by_code["G1"].baseline_without_baltor)
        self.assertIn("7/8 pass (87.5%)", by_code["G1"].result_with_baltor)
        self.assertIn("170.0 mean card tokens", by_code["G1"].result_with_baltor)
        self.assertIn("DM-01", by_code["G1"].recorded_failures_and_limits)
        self.assertIn("1/6 pass (16.7%)", by_code["G2"].baseline_without_baltor)
        self.assertIn("6/6 pass (100.0%)", by_code["G2"].result_with_baltor)
        self.assertIn("ECE 0.190 -> 0.007", by_code["G3"].result_with_baltor)
        self.assertIn("NDCG@10 0.462 -> 0.874", by_code["G3"].result_with_baltor)
        self.assertIn("94.02% LSH pair reduction", by_code["G4"].result_with_baltor)
        self.assertIn("0.125 -> 1.000", by_code["G4"].result_with_baltor)
        self.assertIn("-90.33% context token spend", by_code["G5"].token_and_cost_delta)
        self.assertIn("0 unchanged file regenerations", by_code["G5"].result_with_baltor)
        self.assertIn("0 duplicate side effects on worker retry", by_code["G6"].result_with_baltor)
        self.assertIn("24/24 + 8/8 attacks blocked", by_code["G7"].result_with_baltor)
        self.assertIn("584 initial MCP schema tokens (-77.68%)", by_code["G8"].result_with_baltor)
        self.assertIn("95.75% first-attempt pass rate", by_code["G8"].result_with_baltor)
        self.assertIn("Chronos-Bolt, TimesFM 2.0, BitNet-b1.58, and Model2Vec", by_code["G9"].sample_population)
        self.assertIn("68.0x mirror clarity gain", by_code["G10"].result_with_baltor)

    def test_automatic_cascade_fallback_across_all_four_gauntlet_engines(self) -> None:
        resp = self.orchestrator.handle(
            GauntletSynthesisRequest(
                request_id="test-gauntlet-cascade",
                simulate_matrix_deferral=True,
                simulate_pareto_deferral=True,
                simulate_merkle_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_GAUNTLET_ROLLUP_FALLBACK)
        self.assertEqual(
            resp.attempted_engines,
            (
                ENGINE_EVIDENCE_SEPARATED_MATRIX,
                ENGINE_PARETO_COST_TOKEN_FRONTIER,
                ENGINE_MERKLE_RECEIPT_VERIFIER,
                ENGINE_GAUNTLET_ROLLUP_FALLBACK,
            ),
        )
        self.assertEqual(resp.frame.depth, 4)

    def test_known_wrong_conflating_simulated_track_as_observed_live_refused_in_handshake(self) -> None:
        resp = self.orchestrator.handle(
            GauntletSynthesisRequest(
                request_id="wrong-conflate-g3",
                override_evidence_classes={"G3": EVIDENCE_OBSERVED_LIVE},
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "evidence_class_conflation_simulated_labeled_live")

    def test_known_wrong_omitting_dm_01_failed_trial_refused_in_preflight(self) -> None:
        resp = self.orchestrator.handle(
            GauntletSynthesisRequest(
                request_id="wrong-omit-dm01",
                include_failed_trial_dm_01=False,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_PREFLIGHT)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "attempt_population_omits_failed_trial_dm_01")


class PaperBaltorStaticMonographCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gauntlet_orch = PublicGauntletEvidenceSynthesizerOrchestrator()
        synth = self.gauntlet_orch.handle(GauntletSynthesisRequest(request_id="setup-synth"))
        assert synth.payload is not None
        self.gauntlet_payload = synth.payload
        self.paper_orch = PaperBaltorStaticMonographOrchestrator()

    def test_all_four_monograph_engines_emit_cloudflare_latex_markdown_and_ascii_bundles(self) -> None:
        self.assertIsInstance(self.paper_orch.envelope, ComponentEnvelope)
        for engine_id in PAPER_MONOGRAPH_ENGINE_IDS:
            orch = PaperBaltorStaticMonographOrchestrator(engine_order=(engine_id,))
            resp = orch.handle(
                PaperMonographRequest(
                    request_id=f"test-paper-{engine_id}",
                    gauntlet_payload=self.gauntlet_payload,
                )
            )
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            assert resp.bundle is not None
            self.assertEqual(resp.bundle.hostname, PAPER_HOST)
            self.assertIn(PAPER_TITLE, resp.bundle.index_html)
            self.assertIn("<svg", resp.bundle.index_html)
            self.assertIn("Strict-Transport-Security:", resp.bundle.cloudflare_headers)
            self.assertIn("Content-Security-Policy:", resp.bundle.cloudflare_headers)
            self.assertIn("\\begin{tabular}", resp.bundle.paper_tex)
            self.assertIn("@techreport{baltor2026monograph", resp.bundle.references_bib)
            self.assertIn("Perplexity, ChatGPT, Claude, Semantic Scholar", resp.bundle.llms_txt)
            self.assertIn("DM-01", resp.bundle.paper_md)
            self.assertTrue(resp.bundle.zero_js_verified)
            self.assertTrue(resp.bundle.zero_cookie_verified)
            self.assertTrue(resp.bundle.hsts_verified)
            merkle_doc = json.loads(resp.bundle.merkle_root_json)
            self.assertEqual(merkle_doc["observed_live_tracks"], ["G1", "G2"])
            self.assertEqual(len(merkle_doc["deterministic_simulation_tracks"]), 8)

    def test_automatic_cascade_fallback_across_all_four_monograph_engines(self) -> None:
        resp = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="test-paper-cascade",
                gauntlet_payload=self.gauntlet_payload,
                simulate_cloudflare_bundle_deferral=True,
                simulate_latex_engine_deferral=True,
                simulate_markdown_twin_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_PLAIN_ASCII_ARCHIVAL)
        self.assertEqual(
            resp.attempted_engines,
            (
                ENGINE_CLOUDFLARE_STATIC_BUNDLE,
                ENGINE_LATEX_BIBTEX_CAMERA_READY,
                ENGINE_MARKDOWN_TWIN_LLMS_TXT,
                ENGINE_PLAIN_ASCII_ARCHIVAL,
            ),
        )
        self.assertEqual(resp.frame.depth, 4)

    def test_known_wrong_missing_hsts_or_tracking_cookies_refused_in_preflight(self) -> None:
        no_hsts = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-no-hsts",
                gauntlet_payload=self.gauntlet_payload,
                include_hsts_header=False,
            )
        )
        self.assertFalse(no_hsts.succeeded)
        self.assertFalse(no_hsts.trace.engine_dispatched)
        self.assertEqual(no_hsts.trace.refused_by, LAYER_PREFLIGHT)
        assert no_hsts.refusal is not None
        self.assertEqual(no_hsts.refusal.code, "paper_cloudflare_headers_missing_hsts")

        cookie_injected = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-cookie",
                gauntlet_payload=self.gauntlet_payload,
                inject_tracking_cookie=True,
            )
        )
        self.assertFalse(cookie_injected.succeeded)
        self.assertFalse(cookie_injected.trace.engine_dispatched)
        self.assertEqual(cookie_injected.trace.refused_by, LAYER_PREFLIGHT)
        assert cookie_injected.refusal is not None
        self.assertEqual(cookie_injected.refusal.code, "paper_cloudflare_tracking_cookie_forbidden")

    def test_known_wrong_banned_slop_or_negative_framing_or_omitted_dm01_refused_in_handshake(self) -> None:
        slop = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-slop",
                gauntlet_payload=self.gauntlet_payload,
                inject_manuscript_override_text="Furthermore, we delve into a seamless tapestry.",
            )
        )
        self.assertFalse(slop.succeeded)
        self.assertFalse(slop.trace.engine_dispatched)
        self.assertEqual(slop.trace.refused_by, LAYER_HANDSHAKE)
        assert slop.refusal is not None
        self.assertEqual(slop.refusal.code, "paper_manuscript_wording_violation")

        neg_framing = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-neg",
                gauntlet_payload=self.gauntlet_payload,
                inject_manuscript_override_text="What Baltor is not: not just a library, it's a platform.",
            )
        )
        self.assertFalse(neg_framing.succeeded)
        self.assertFalse(neg_framing.trace.engine_dispatched)
        self.assertEqual(neg_framing.trace.refused_by, LAYER_HANDSHAKE)
        assert neg_framing.refusal is not None
        self.assertEqual(neg_framing.refusal.code, "paper_manuscript_wording_violation")

        omit_dm01 = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-paper-dm01",
                gauntlet_payload=self.gauntlet_payload,
                omit_dm_01_from_limitations=True,
            )
        )
        self.assertFalse(omit_dm01.succeeded)
        self.assertFalse(omit_dm01.trace.engine_dispatched)
        self.assertEqual(omit_dm01.trace.refused_by, LAYER_HANDSHAKE)
        assert omit_dm01.refusal is not None
        self.assertEqual(omit_dm01.refusal.code, "attempt_population_omits_failed_trial_dm_01")

    def test_carrier_layer_refuses_empty_hostname_or_bad_schema(self) -> None:
        bad_carrier = self.paper_orch.handle(
            PaperMonographRequest(
                request_id="wrong-carrier",
                gauntlet_payload=self.gauntlet_payload,
                hostname="   ",
            )
        )
        self.assertFalse(bad_carrier.succeeded)
        self.assertFalse(bad_carrier.trace.engine_dispatched)
        self.assertEqual(bad_carrier.trace.refused_by, LAYER_CARRIER)

    def test_benchmark_and_self_test_report_complete_pass(self) -> None:
        result = self_test()
        self.assertTrue(result["passed"])
        bench = run_head_to_head_benchmark()
        self.assertEqual(bench["total_gauntlet_tracks"], 10)
        self.assertEqual(bench["observed_live_track_count"], 2)
        self.assertEqual(bench["deterministic_simulation_track_count"], 8)
        self.assertTrue(bench["known_wrong_probes"]["all_blocked_before_engine"])


if __name__ == "__main__":
    unittest.main()

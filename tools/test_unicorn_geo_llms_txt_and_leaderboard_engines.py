"""Tests for Pillar 6: GEO /llms.txt & .md Twin Synthesizer and Verifiable Global Benchmark Leaderboard.

Covers:
1. Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`, wrapped in 7-Layer `ComponentEnvelope`):
   - `llms_txt_and_markdown_twin_compiler_engine` and `schema_org_jsonld_knowledge_graph_engine` across all
     24 domains (`baltor.ai`, `demos.baltor.ai`, `deterministicskills.baltor.ai`, `tools.baltor.ai`,
     `cornercases.baltor.ai`, `agentfeeds.si`, `agentfoundry.si`, `agentstudios.si`, `agentafk.si`,
     `agentbriefs.si`, `skillsforgood.org`, `theloopengine.org`, and sister domains).
   - Validated Schema.org `SoftwareApplication`, `Dataset`, `TechArticle`, and `FAQPage` JSON-LD graphs,
     `noindex, follow` `.md` twins, MCP connection snippets, SHA-256 evidence digests, and AI assistant
     citation targets (`ChatGPT Search`, `Claude`, `Perplexity`, `Gemini`, `Cursor`).
   - 7-layer automatic engine failover and Layer 6 preflight self-repair for stale release digests.
2. Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`, wrapped in 7-Layer `ComponentEnvelope`):
   - `merkle_receipt_verified_leaderboard_engine` and `reproducible_cli_challenge_pack_exporter` across all
     8 Baltor benchmark tracks (`Kaggle AI/ML`, `GitHub Common Projects`, `Entity Linking & Dedup`,
     `Messy Data Cleaning`, `Long-Horizon Cheap Models`, `Real-World SWE & Jev Decisions`,
     `Red-Teaming Security`, and `Social-Videos 3D/Material/Motion Studio`).
   - Tamper-evident SHA-256 Merkle root, interactive views for `demos.baltor.ai` and `agentbriefs.si`,
     and one-command reproducible CLI challenge packs.
3. Known-Wrong Refusal Controls:
   - (a) Leaderboard entry missing a valid `verifier_digest` or `receipt_sha256` (or tampered score).
   - (b) Cherry-picking by omitting failed/excluded trials from `attempt_population`.
   - (c) Banned AI-slop or negative `"What Baltor is not"` phrasing in `/llms.txt` or `.md` twins.
   - (d) Cross-brand session/auth leakage on standalone `.si` / `.org` GEO manifests.
"""
from __future__ import annotations

from dataclasses import replace
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
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REPAIRED,
)
from unicorn_geo_llms_txt_and_leaderboard_engines import (  # noqa: E402
    ASSISTANT_CITATION_TARGETS,
    BENCHMARK_TRACK_SPECS,
    DEFAULT_ATTEMPT_POPULATIONS,
    DEFAULT_TRIAL_RECEIPTS,
    ENGINE_CLI_CHALLENGE_EXPORTER,
    ENGINE_LLMS_TXT_COMPILER,
    ENGINE_MERKLE_LEADERBOARD,
    ENGINE_SCHEMA_ORG_JSONLD,
    GEO_ENGINE_IDS,
    GEO_SURFACE_REGISTRY,
    LEADERBOARD_ENGINE_IDS,
    STALE_RELEASE_DIGEST,
    SYNCHRONIZED_RELEASE_DIGEST,
    GeoLlmsTxtAndMarkdownTwinOrchestrator,
    GeoSynthesisRequest,
    VerifiableGlobalBenchmarkLeaderboardOrchestrator,
    VerifiableLeaderboardRequest,
    run_head_to_head_benchmark,
    scan_geo_wording_violations,
    self_test,
)


class GeoLlmsTxtAndMarkdownTwinSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = GeoLlmsTxtAndMarkdownTwinOrchestrator()

    def test_synthesizes_llms_txt_md_twins_and_jsonld_across_twenty_four_domains(self) -> None:
        required_domains = {
            "baltor.ai",
            "demos.baltor.ai",
            "deterministicskills.baltor.ai",
            "tools.baltor.ai",
            "cornercases.baltor.ai",
            "agentfeeds.si",
            "agentfoundry.si",
            "agentstudios.si",
            "agentafk.si",
            "agentbriefs.si",
            "skillsforgood.org",
            "theloopengine.org",
        }
        self.assertTrue(required_domains.issubset(set(GEO_SURFACE_REGISTRY.keys())))
        self.assertGreaterEqual(len(GEO_SURFACE_REGISTRY), 20)

        for engine_id in GEO_ENGINE_IDS:
            orch = GeoLlmsTxtAndMarkdownTwinOrchestrator(engine_order=(engine_id,))
            resp = orch.handle(GeoSynthesisRequest(request_id=f"geo-{engine_id}"))
            self.assertTrue(resp.succeeded)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertEqual(resp.domains_synthesized, 24)
            self.assertEqual(resp.total_jsonld_nodes, 96)
            self.assertEqual(resp.wording_violations_found, ())
            for artifact in resp.artifacts:
                self.assertEqual(artifact.markdown_twin_robots, "noindex, follow")
                self.assertEqual(len(artifact.evidence_sha256), 64)
                self.assertEqual(artifact.cited_by_assistants, ASSISTANT_CITATION_TARGETS)
                self.assertEqual(scan_geo_wording_violations(artifact.llms_txt_content), ())
                self.assertEqual(scan_geo_wording_violations(artifact.markdown_twin_content), ())
                schema_types = {node["@type"] for node in artifact.jsonld_graph}
                self.assertEqual(
                    schema_types,
                    {"SoftwareApplication", "Dataset", "TechArticle", "FAQPage"},
                )

    def test_geo_slot_automatic_failover_and_preflight_digest_self_repair(self) -> None:
        resp = self.orchestrator.handle(
            GeoSynthesisRequest(
                request_id="geo-failover-and-repair",
                release_digest=STALE_RELEASE_DIGEST,
                allow_digest_resync_repair=True,
                simulate_compiler_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_SCHEMA_ORG_JSONLD)
        self.assertEqual(resp.attempted_engines, GEO_ENGINE_IDS)
        self.assertIsNotNone(resp.preflight_report)
        assert resp.preflight_report is not None
        self.assertEqual(resp.preflight_report.verdict, VERDICT_REPAIRED)
        for artifact in resp.artifacts:
            self.assertIn(SYNCHRONIZED_RELEASE_DIGEST, artifact.llms_txt_content)

    def test_known_wrong_refuses_ai_slop_and_negative_what_baltor_is_not_phrasing(self) -> None:
        resp_negative = self.orchestrator.handle(
            GeoSynthesisRequest(
                request_id="geo-bad-negative",
                injected_summary_override="What Baltor is not: Baltor is not just a library, it is a platform.",
            )
        )
        self.assertFalse(resp_negative.succeeded)
        self.assertEqual(resp_negative.trace.refused_by, LAYER_HANDSHAKE)
        self.assertIsNotNone(resp_negative.refusal)
        assert resp_negative.refusal is not None
        self.assertEqual(resp_negative.refusal.code, "geo_manifest_wording_violation")

        resp_slop = self.orchestrator.handle(
            GeoSynthesisRequest(
                request_id="geo-bad-slop",
                injected_summary_override="We delve into a seamless tapestry that will unleash a game-changer.",
            )
        )
        self.assertFalse(resp_slop.succeeded)
        self.assertEqual(resp_slop.trace.refused_by, LAYER_HANDSHAKE)
        assert resp_slop.refusal is not None
        self.assertEqual(resp_slop.refusal.code, "geo_manifest_wording_violation")

    def test_known_wrong_refuses_cross_brand_cookie_leakage_on_standalone_manifests(self) -> None:
        resp = self.orchestrator.handle(
            GeoSynthesisRequest(
                request_id="geo-bad-cross-brand-cookie",
                target_hostnames=("agentfeeds.si", "skillsforgood.org"),
                inject_cross_brand_cookie_on_standalone="baltor_session=leaked_cookie_token",
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE)
        self.assertIsNotNone(resp.refusal)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "standalone_surface_cross_brand_auth_leakage")


class VerifiableGlobalBenchmarkLeaderboardSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = VerifiableGlobalBenchmarkLeaderboardOrchestrator()

    def test_verifies_merkle_root_and_cli_challenge_packs_across_all_eight_tracks(self) -> None:
        expected_titles = {
            "Kaggle AI/ML",
            "GitHub Common Projects",
            "Entity Linking & Dedup",
            "Messy Data Cleaning",
            "Long-Horizon Cheap Models",
            "Real-World SWE & Jev Decisions",
            "Red-Teaming Security",
            "Social-Videos 3D/Material/Motion Studio",
        }
        self.assertEqual({s.track_title for s in BENCHMARK_TRACK_SPECS}, expected_titles)

        roots: list[str] = []
        for engine_id in LEADERBOARD_ENGINE_IDS:
            orch = VerifiableGlobalBenchmarkLeaderboardOrchestrator(engine_order=(engine_id,))
            resp = orch.handle(VerifiableLeaderboardRequest(request_id=f"lb-{engine_id}"))
            self.assertTrue(resp.succeeded)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertEqual(resp.tracks_verified, 8)
            self.assertEqual(resp.receipts_verified, len(DEFAULT_TRIAL_RECEIPTS))
            assert resp.payload is not None
            self.assertEqual(len(resp.payload.global_merkle_root), 64)
            roots.append(resp.payload.global_merkle_root)
            self.assertEqual(resp.payload.demos_baltor_view["surface"], "demos.baltor.ai")
            self.assertEqual(resp.payload.agentbriefs_view["surface"], "agentbriefs.si")
            self.assertEqual(len(resp.payload.cli_challenge_packs), 8)
            for row in resp.payload.rows:
                self.assertGreater(row.with_baltor_score, row.without_baltor_score)
                self.assertIn("baltor-verify-pack --track", row.reproducible_cli_command)
        self.assertEqual(roots[0], roots[1])

    def test_leaderboard_slot_automatic_failover_to_cli_exporter(self) -> None:
        resp = self.orchestrator.handle(
            VerifiableLeaderboardRequest(
                request_id="lb-failover",
                simulate_merkle_engine_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_CLI_CHALLENGE_EXPORTER)
        self.assertEqual(resp.attempted_engines, LEADERBOARD_ENGINE_IDS)

    def test_known_wrong_refuses_missing_or_tampered_verifier_digest_or_receipt_sha256(self) -> None:
        bad_verifier = replace(DEFAULT_TRIAL_RECEIPTS[0], verifier_digest="missing_digest")
        resp_missing = self.orchestrator.handle(
            VerifiableLeaderboardRequest(
                request_id="lb-bad-verifier-digest",
                trial_receipts=(bad_verifier,) + DEFAULT_TRIAL_RECEIPTS[1:],
            )
        )
        self.assertFalse(resp_missing.succeeded)
        self.assertEqual(resp_missing.trace.refused_by, LAYER_HANDSHAKE)
        assert resp_missing.refusal is not None
        self.assertEqual(resp_missing.refusal.code, "invalid_or_missing_trial_receipt_digest")

        tampered_score = replace(DEFAULT_TRIAL_RECEIPTS[0], with_baltor_score=0.999)
        resp_tampered = self.orchestrator.handle(
            VerifiableLeaderboardRequest(
                request_id="lb-tampered-score",
                trial_receipts=(tampered_score,) + DEFAULT_TRIAL_RECEIPTS[1:],
            )
        )
        self.assertFalse(resp_tampered.succeeded)
        self.assertEqual(resp_tampered.trace.refused_by, LAYER_HANDSHAKE)
        assert resp_tampered.refusal is not None
        self.assertEqual(resp_tampered.refusal.code, "invalid_or_missing_trial_receipt_digest")

    def test_known_wrong_refuses_cherry_picked_attempt_population_omitting_failed_trials(self) -> None:
        cherry_picked_receipts = tuple(
            r for r in DEFAULT_TRIAL_RECEIPTS if r.trial_status == "completed"
        )
        resp = self.orchestrator.handle(
            VerifiableLeaderboardRequest(
                request_id="lb-cherry-picked",
                trial_receipts=cherry_picked_receipts,
                declared_populations=DEFAULT_ATTEMPT_POPULATIONS,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertEqual(resp.trace.refused_by, LAYER_PREFLIGHT)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "cherry_picked_attempt_population_mismatch")

    def test_carrier_refusal_and_self_test(self) -> None:
        resp = self.orchestrator.handle(
            VerifiableLeaderboardRequest(
                request_id="lb-bad-schema",
                schema="unsupported_schema/v0",
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertEqual(resp.trace.refused_by, LAYER_CARRIER)
        self.assertTrue(self_test())
        bench = run_head_to_head_benchmark()
        self.assertEqual(len(bench["geo_slot_benchmarks"]), 2)
        self.assertEqual(len(bench["leaderboard_slot_benchmarks"]), 2)


if __name__ == "__main__":
    unittest.main()

"""Tests for the Demo Subdomain (`demos.baltor.ai`) and Multi-Domain Side-by-Side Showcase Engine Suite.

Covers:
1. All 16 project archetypes in `github_developer_archetypes/v1` across 4 categories
   (`kaggle_ai_ml`, `github_common_projects`, `public_good_projects`, `design_media_projects`),
   verifying observed pilot citations (`comparison-pilot-2026-10-16`) vs. deterministic
   contract-card simulations, SHA-256 receipts, and `humanizer-context.md` compliance.
2. All 4 swappable showcase rendering and verification engines wrapped in the 7-layer
   `ComponentEnvelope`, plus bounded cascade failover and idempotent journal replay.
3. Known-wrong controls across Carrier (Layer 2), Handshake (Layer 3), Account (Layer 4),
   and Preflight (Layer 6), including unverified benchmark refusal, raw credential quarantine
   without echoing sensitive strings, cross-brand cookie refusal, category syndication refusal,
   and negative-framing refusal.
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

from demo_subdomain_showcase_engines import (  # noqa: E402
    ADMITTED_DEMO_HOSTS,
    ARCHETYPE_CATEGORIES,
    CATEGORY_DESIGN_MEDIA,
    CATEGORY_GITHUB_COMMON,
    CATEGORY_KAGGLE_AI_ML,
    CATEGORY_PUBLIC_GOOD,
    DEFAULT_RELEASE_DIGEST,
    ENGINE_BRAND_SYNDICATED,
    ENGINE_PLAYGROUND_RECEIPT,
    ENGINE_SIDE_BY_SIDE_DIFF,
    ENGINE_STATIC_MARKDOWN_TWIN,
    EVIDENCE_CONTRACT_SIMULATION,
    EVIDENCE_OBSERVED_PILOT,
    GITHUB_DEVELOPER_ARCHETYPES_REGISTRY,
    HOST_AGENTBRIEFS,
    HOST_AGENTSTUDIOS,
    HOST_DEMOS_BALTOR,
    HOST_GALLERY_BALTOR,
    HOST_SKILLSFORGOOD,
    PLAYGROUND_BUNDLE_SCHEMA,
    SHA256_HEX_RE,
    SHOWCASE_ENGINE_IDS,
    STALE_RELEASE_DIGEST,
    SUPPORTED_HARNESSES,
    BrandSyndicatedDemoProjectionEngine,
    DemoSubdomainShowcaseOrchestrator,
    DemoSubdomainShowcaseRequest,
    ExecutablePlaygroundReceiptEngine,
    InteractiveSideBySideDiffShowcaseEngine,
    StaticMarkdownTwinFallbackEngine,
    _find_humanizer_violation,
    run_head_to_head_benchmark,
    self_test,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    RESYNC_IN_SYNC,
    RESYNC_NOW,
)


class GitHubDeveloperArchetypeRegistryTests(unittest.TestCase):
    def test_sixteen_archetypes_across_four_categories(self) -> None:
        self.assertEqual(len(GITHUB_DEVELOPER_ARCHETYPES_REGISTRY), 16)
        by_category = {
            cat: [
                a.archetype_id
                for a in GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.values()
                if a.category == cat
            ]
            for cat in ARCHETYPE_CATEGORIES
        }
        self.assertEqual(
            by_category[CATEGORY_KAGGLE_AI_ML],
            [
                "spaceship_titanic_groupkfold",
                "ames_house_prices_oof_rmsle",
                "store_sales_lag_leakage_free",
                "credit_card_fraud_calibrated_prauc",
            ],
        )
        self.assertEqual(
            by_category[CATEGORY_GITHUB_COMMON],
            [
                "cachetools_tlru_cache",
                "python_dotenv_rfc_parser",
                "sqlite_wal_rate_limiter_webhook",
                "mcp_streamable_http_server",
            ],
        )
        self.assertEqual(
            by_category[CATEGORY_PUBLIC_GOOD],
            [
                "osha_niosh_wbgt_calculator",
                "offline_crisis_shelter_wcag_aaa_router",
                "open_air_quality_pm25_advisory",
                "municipal_benefits_rule_verifier",
            ],
        )
        self.assertEqual(
            by_category[CATEGORY_DESIGN_MEDIA],
            [
                "reelkit_vertical_motion_explainer",
                "fourier_epicycle_dft_animator",
                "html5_rigid_body_karplus_strong_arena",
                "headless_blender_glb_contract_verifier",
            ],
        )

    def test_observed_pilot_and_contract_simulation_evidence_separated(self) -> None:
        observed = {
            a.archetype_id
            for a in GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.values()
            if a.evidence_basis == EVIDENCE_OBSERVED_PILOT
        }
        simulated = {
            a.archetype_id
            for a in GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.values()
            if a.evidence_basis == EVIDENCE_CONTRACT_SIMULATION
        }
        self.assertEqual(
            observed,
            {
                "spaceship_titanic_groupkfold",
                "cachetools_tlru_cache",
                "python_dotenv_rfc_parser",
            },
        )
        self.assertEqual(len(simulated), 13)

    def test_every_archetype_has_valid_sha256_receipt_and_humanizer_clean_copy(self) -> None:
        for arch in GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.values():
            self.assertRegex(arch.trial_receipt_sha256, SHA256_HEX_RE, arch.archetype_id)
            self.assertEqual(arch.primary_demo_host, HOST_DEMOS_BALTOR)
            self.assertEqual(arch.supported_harnesses, SUPPORTED_HARNESSES)
            self.assertEqual(arch.model_id, "gemma4:31b")
            self.assertEqual(arch.model_provider, "ollama_cloud")
            self.assertGreater(arch.with_baltor_checks_passed, arch.without_baltor_checks_passed)
            self.assertEqual(arch.with_baltor_checks_passed, arch.with_baltor_checks_total)
            for text_field in (
                arch.title,
                arch.contract_card_summary,
                arch.without_baltor_failure_mode,
                arch.prompt_text,
            ):
                self.assertEqual(_find_humanizer_violation(text_field), "", arch.archetype_id)


class FourSwappableDemoShowcaseEnginesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = DemoSubdomainShowcaseOrchestrator()

    def test_engine_1_interactive_side_by_side_diff_showcase(self) -> None:
        resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="req-diff-01",
                archetype_id="spaceship_titanic_groupkfold",
                target_hostname=HOST_DEMOS_BALTOR,
                harness_id="opencode",
                preferred_engine=ENGINE_SIDE_BY_SIDE_DIFF,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_SIDE_BY_SIDE_DIFF)
        self.assertEqual(resp.output_format, "html+json")
        self.assertIn("baltor-demo-card", resp.rendered_html)
        self.assertIn("Without Baltor (3/5 checks passed)", resp.rendered_html)
        self.assertIn("With Baltor (5/5 checks passed)", resp.rendered_html)
        assert resp.structured_payload is not None
        self.assertEqual(
            resp.structured_payload["schema"],
            "interactive_side_by_side_diff_card/v1",
        )
        self.assertTrue(len(resp.structured_payload["unified_diff_lines"]) > 0)

    def test_engine_2_executable_playground_receipt_bundle(self) -> None:
        resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="req-playground-01",
                archetype_id="cachetools_tlru_cache",
                target_hostname=HOST_DEMOS_BALTOR,
                harness_id="claude_code",
                preferred_engine=ENGINE_PLAYGROUND_RECEIPT,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_PLAYGROUND_RECEIPT)
        self.assertEqual(resp.output_format, "playground_bundle+json")
        assert resp.structured_payload is not None
        self.assertEqual(resp.structured_payload["schema"], PLAYGROUND_BUNDLE_SCHEMA)
        files = resp.structured_payload["files"]
        self.assertEqual(
            set(files.keys()),
            {
                "prompt.txt",
                "contract_card.md",
                "without_baltor.py",
                "with_baltor.py",
                "verify.py",
                "receipt.json",
            },
        )
        self.assertRegex(resp.structured_payload["bundle_sha256"], SHA256_HEX_RE)

    def test_engine_3_brand_syndicated_demo_projection(self) -> None:
        syndication_cases = (
            ("osha_niosh_wbgt_calculator", HOST_SKILLSFORGOOD),
            ("reelkit_vertical_motion_explainer", HOST_AGENTSTUDIOS),
            ("python_dotenv_rfc_parser", HOST_AGENTBRIEFS),
            ("fourier_epicycle_dft_animator", HOST_GALLERY_BALTOR),
        )
        for archetype_id, host in syndication_cases:
            resp = self.orchestrator.handle(
                DemoSubdomainShowcaseRequest(
                    request_id=f"req-synd-{archetype_id}-{host}",
                    archetype_id=archetype_id,
                    target_hostname=host,
                    preferred_engine=ENGINE_BRAND_SYNDICATED,
                )
            )
            self.assertTrue(resp.succeeded, f"{archetype_id} on {host}")
            self.assertEqual(resp.selected_engine, ENGINE_BRAND_SYNDICATED)
            self.assertIn('data-zero-cookie="true"', resp.rendered_html)
            assert resp.structured_payload is not None
            self.assertTrue(resp.structured_payload["zero_cookie_enforced"])

    def test_engine_4_static_markdown_twin_fallback(self) -> None:
        resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="req-twin-01",
                archetype_id="headless_blender_glb_contract_verifier",
                target_hostname=HOST_GALLERY_BALTOR,
                harness_id="codex",
                preferred_engine=ENGINE_STATIC_MARKDOWN_TWIN,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_STATIC_MARKDOWN_TWIN)
        self.assertEqual(resp.output_format, "markdown_twin+html")
        assert resp.structured_payload is not None
        self.assertTrue(resp.structured_payload["zero_javascript"])
        self.assertEqual(
            resp.structured_payload["twin_route"],
            "https://gallery.baltor.ai/demos/headless_blender_glb_contract_verifier.md",
        )

    def test_cascade_failover_across_all_four_engines_shares_recovery_allowance(self) -> None:
        orchestrator = DemoSubdomainShowcaseOrchestrator(
            diff_engine=InteractiveSideBySideDiffShowcaseEngine(
                unavailable_archetypes=frozenset({"reelkit_vertical_motion_explainer"})
            ),
            playground_engine=ExecutablePlaygroundReceiptEngine(
                busy_archetypes=frozenset({"reelkit_vertical_motion_explainer"})
            ),
            syndicated_engine=BrandSyndicatedDemoProjectionEngine(
                cold_hosts=frozenset({HOST_AGENTSTUDIOS})
            ),
            twin_engine=StaticMarkdownTwinFallbackEngine(),
        )
        resp = orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="req-cascade-deep",
                archetype_id="reelkit_vertical_motion_explainer",
                target_hostname=HOST_AGENTSTUDIOS,
                preferred_engine=ENGINE_SIDE_BY_SIDE_DIFF,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_STATIC_MARKDOWN_TWIN)
        self.assertEqual(resp.attempted_engines, SHOWCASE_ENGINE_IDS)
        self.assertEqual(resp.frame.allowance.remaining, 0)
        self.assertEqual(len(resp.frame.path), 5)

    def test_idempotent_replay_and_release_resync_tracking(self) -> None:
        req = DemoSubdomainShowcaseRequest(
            request_id="req-idempotent-01",
            archetype_id="sqlite_wal_rate_limiter_webhook",
            release_digest=STALE_RELEASE_DIGEST,
            served_release_digest=DEFAULT_RELEASE_DIGEST,
        )
        first = self.orchestrator.handle(req)
        self.assertTrue(first.succeeded)
        self.assertTrue(first.trace.engine_dispatched)
        self.assertEqual(first.resync_state, RESYNC_NOW)

        replay = self.orchestrator.handle(req)
        self.assertTrue(replay.succeeded)
        self.assertFalse(replay.trace.engine_dispatched)
        self.assertEqual(replay.trace.steps[-1], ("tracking", LAYER_ANSWERED))

    def test_preflight_self_repair_sanitizes_negative_framing_when_allowed(self) -> None:
        resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="req-repair-humanizer",
                archetype_id="mcp_streamable_http_server",
                custom_annotation="Overview\u2014What Baltor is not and how we delve into cards.",
                allow_preflight_repair=True,
            )
        )
        self.assertTrue(resp.succeeded)
        assert resp.preflight_report is not None
        self.assertEqual(resp.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertNotIn("\u2014", resp.rendered_html)
        self.assertNotIn("What Baltor is not", resp.rendered_html)
        self.assertNotIn("delve", resp.rendered_html)


class KnownWrongSecurityAndEvidenceControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = DemoSubdomainShowcaseOrchestrator()

    def test_known_wrong_carrier_refuses_unknown_archetype_host_and_harness(self) -> None:
        bad_arch = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-arch",
                archetype_id="nonexistent_project",
            )
        )
        self.assertFalse(bad_arch.succeeded)
        self.assertFalse(bad_arch.trace.engine_dispatched)
        self.assertEqual(bad_arch.trace.refused_by, LAYER_CARRIER)
        assert bad_arch.refusal is not None
        self.assertEqual(bad_arch.refusal.code, "unregistered_project_archetype")

        bad_host = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-host",
                archetype_id="spaceship_titanic_groupkfold",
                target_hostname="untrusted.example.com",
            )
        )
        self.assertFalse(bad_host.succeeded)
        self.assertEqual(bad_host.trace.refused_by, LAYER_CARRIER)
        assert bad_host.refusal is not None
        self.assertEqual(bad_host.refusal.code, "unregistered_demo_surface_hostname")

        bad_harness = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-harness",
                archetype_id="spaceship_titanic_groupkfold",
                harness_id="unknown_ide",
            )
        )
        self.assertFalse(bad_harness.succeeded)
        self.assertEqual(bad_harness.trace.refused_by, LAYER_CARRIER)
        assert bad_harness.refusal is not None
        self.assertEqual(bad_harness.refusal.code, "unsupported_demo_harness")

    def test_known_wrong_handshake_refuses_session_cookies_external_idp_and_category_mismatch(self) -> None:
        for host in ADMITTED_DEMO_HOSTS:
            arch_id = (
                "osha_niosh_wbgt_calculator"
                if host == HOST_SKILLSFORGOOD
                else "reelkit_vertical_motion_explainer"
                if host == HOST_AGENTSTUDIOS
                else "spaceship_titanic_groupkfold"
            )
            cookie_resp = self.orchestrator.handle(
                DemoSubdomainShowcaseRequest(
                    request_id=f"kw-cookie-{host}",
                    archetype_id=arch_id,
                    target_hostname=host,
                    has_session_cookie=True,
                )
            )
            self.assertFalse(cookie_resp.succeeded)
            self.assertFalse(cookie_resp.trace.engine_dispatched)
            self.assertEqual(cookie_resp.trace.refused_by, LAYER_HANDSHAKE)
            assert cookie_resp.refusal is not None
            self.assertEqual(cookie_resp.refusal.code, "cross_brand_session_cookie_forbidden")

        idp_resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-idp-csp",
                archetype_id="osha_niosh_wbgt_calculator",
                target_hostname=HOST_SKILLSFORGOOD,
                includes_external_idp_csp=True,
            )
        )
        self.assertFalse(idp_resp.succeeded)
        self.assertEqual(idp_resp.trace.refused_by, LAYER_HANDSHAKE)
        assert idp_resp.refusal is not None
        self.assertEqual(idp_resp.refusal.code, "cross_brand_external_idp_csp_forbidden")

        mismatch_resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-cat-mismatch",
                archetype_id="credit_card_fraud_calibrated_prauc",
                target_hostname=HOST_SKILLSFORGOOD,
            )
        )
        self.assertFalse(mismatch_resp.succeeded)
        self.assertEqual(mismatch_resp.trace.refused_by, LAYER_HANDSHAKE)
        assert mismatch_resp.refusal is not None
        self.assertEqual(mismatch_resp.refusal.code, "cross_brand_category_projection_mismatch")

    def test_known_wrong_account_refuses_state_mutation_and_live_unbudgeted_model_calls(self) -> None:
        mutate_resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-account-mutate",
                archetype_id="spaceship_titanic_groupkfold",
                mutates_account_state=True,
            )
        )
        self.assertFalse(mutate_resp.succeeded)
        self.assertEqual(mutate_resp.trace.refused_by, LAYER_ACCOUNT)
        assert mutate_resp.refusal is not None
        self.assertEqual(mutate_resp.refusal.code, "demo_showcase_account_mutation_forbidden")

        live_call_resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-live-model",
                archetype_id="spaceship_titanic_groupkfold",
                requests_live_unbudgeted_model_call=True,
            )
        )
        self.assertFalse(live_call_resp.succeeded)
        self.assertEqual(live_call_resp.trace.refused_by, LAYER_ACCOUNT)
        assert live_call_resp.refusal is not None
        self.assertEqual(live_call_resp.refusal.code, "demo_showcase_live_model_call_forbidden")

    def test_known_wrong_preflight_refuses_missing_sha256_raw_credentials_and_negative_framing(self) -> None:
        no_receipt = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-no-sha256",
                archetype_id="spaceship_titanic_groupkfold",
                override_trial_receipt_sha256="unverified-claim",
            )
        )
        self.assertFalse(no_receipt.succeeded)
        self.assertFalse(no_receipt.trace.engine_dispatched)
        self.assertEqual(no_receipt.trace.refused_by, LAYER_PREFLIGHT)
        assert no_receipt.refusal is not None
        self.assertEqual(no_receipt.refusal.code, "unverified_benchmark_claim_missing_sha256_receipt")

        raw_marker_a = "s" + "k-live998877665544332211"
        raw_marker_b = "Bear" + "er tok_998877665544332211"
        for idx, marker in enumerate((raw_marker_a, raw_marker_b)):
            cred_resp = self.orchestrator.handle(
                DemoSubdomainShowcaseRequest(
                    request_id=f"kw-cred-{idx}",
                    archetype_id="cachetools_tlru_cache",
                    custom_annotation=f"Injected {marker} into demo card",
                )
            )
            self.assertFalse(cred_resp.succeeded)
            self.assertFalse(cred_resp.trace.engine_dispatched)
            self.assertEqual(cred_resp.trace.refused_by, LAYER_PREFLIGHT)
            assert cred_resp.refusal is not None
            self.assertEqual(cred_resp.refusal.code, "demo_payload_raw_credential_forbidden")
            self.assertNotIn(marker, cred_resp.refusal.message)
            self.assertNotIn(marker, cred_resp.refusal.next_action)

        neg_resp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-negative-framing",
                archetype_id="python_dotenv_rfc_parser",
                custom_annotation="Why What Baltor is not matters.",
                allow_preflight_repair=False,
            )
        )
        self.assertFalse(neg_resp.succeeded)
        self.assertEqual(neg_resp.trace.refused_by, LAYER_PREFLIGHT)
        assert neg_resp.refusal is not None
        self.assertEqual(neg_resp.refusal.code, "humanizer_negative_framing_or_slop_forbidden")

        bad_csp = self.orchestrator.handle(
            DemoSubdomainShowcaseRequest(
                request_id="kw-bad-csp",
                archetype_id="python_dotenv_rfc_parser",
                csp_header="default-src *;",
            )
        )
        self.assertFalse(bad_csp.succeeded)
        self.assertEqual(bad_csp.trace.refused_by, LAYER_PREFLIGHT)
        assert bad_csp.refusal is not None
        self.assertEqual(bad_csp.refusal.code, "cross_brand_csp_header_invalid")


class HeadToHeadBenchmarkAndSelfTestTests(unittest.TestCase):
    def test_benchmark_and_self_test_pass_completely(self) -> None:
        result = self_test()
        self.assertTrue(result["passed"], result["checks"])
        bench = run_head_to_head_benchmark()
        self.assertEqual(bench["archetype_count"], 16)
        self.assertEqual(bench["envelope_layers"], list(COVERAGE_LAYERS))
        self.assertEqual(bench["cascade_failover"]["succeeded"], 16)
        self.assertTrue(bench["known_wrong_probes"]["all_blocked_before_engine"])


if __name__ == "__main__":
    unittest.main()

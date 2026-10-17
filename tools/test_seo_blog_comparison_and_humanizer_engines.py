"""Tests for the Humanizer, Multi-Brand Visual Separation, and SEO Comparison/Blog Engine Suite.

Covers:
1. Engine Family 1: All four swappable humanizer & public prose quality engines
   (humanizer_strict_rule_gate, plain_customer_voice_rewriter,
   positive_boundary_framing_engine, deterministic_lexical_cleaner), detection of
   AI-slop vocabulary, negative boundary framing, internal engineering jargon, and
   unverified superlatives, strict refusal mode, and 7-layer automatic fallback.
2. Engine Family 2: Front-end design-skill & multi-brand visual separation auditor
   across all 11 surfaces (unique color tokens, typography scale, hero proposition,
   navigation chrome, own-origin canonical URLs, zero cross-brand cookie/chrome
   leakage, and shared backend release 29a2bc33 parity + preflight self-repair).
3. Engine Family 3: Programmatic SEO, 6 side-by-side comparison guides, and 8
   high-intent technical blog articles with noindex .md twins, /llms.txt manifests,
   and valid TechArticle / FAQPage / SoftwareSourceCode JSON-LD schemas.
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

from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REPAIRED,
)
from seo_blog_comparison_and_humanizer_engines import (  # noqa: E402
    AUDITED_BRAND_SURFACES,
    BRAND_AUDITOR_ENGINE_IDS,
    ENGINE_BACKEND_PARITY_AUDITOR,
    ENGINE_CANONICAL_COOKIE_AUDITOR,
    ENGINE_COMPARISON_MATRIX,
    ENGINE_HUMANIZER_STRICT,
    ENGINE_JSONLD_LLMS_EXPORTER,
    ENGINE_LEXICAL_CLEANER,
    ENGINE_PLAIN_CUSTOMER_VOICE,
    ENGINE_POSITIVE_BOUNDARY,
    ENGINE_STATIC_DESIGN_FALLBACK,
    ENGINE_TECHNICAL_BLOG,
    ENGINE_TOKEN_CHROME_AUDITOR,
    HUMANIZER_ENGINE_IDS,
    SEO_CONTENT_ENGINE_IDS,
    SHARED_BACKEND_FACTS,
    SIDE_BY_SIDE_COMPARISON_SPECS,
    STALE_RELEASE_DIGEST,
    SYNCHRONIZED_RELEASE_DIGEST,
    TECHNICAL_BLOG_SPECS,
    BrandSeparationAuditRequest,
    MultiBrandVisualSeparationOrchestrator,
    ProgrammaticSeoComparisonAndBlogOrchestrator,
    PublicProseHumanizerOrchestrator,
    PublicProseRequest,
    SeoContentGenerationRequest,
    build_surface_url,
    run_head_to_head_benchmark,
    scan_prose_violations,
    self_test,
)


class HumanizerEngineFamilyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = PublicProseHumanizerOrchestrator()

    def test_detects_and_rewrites_slop_negative_framing_jargon_and_superlatives(self) -> None:
        dirty = (
            "What Baltor is not: Baltor is not just a library, it's a platform. "
            "Moreover, we delve into a seamless tapestry and testament that will "
            "underscore pivotal outcomes and unleash a game-changer for tenant_id, "
            "loop_id, and FTS5. External identity flow qualified: no. "
            "It is the world's best AI platform with 100% hallucination-free forever."
        )
        violations = scan_prose_violations(dirty)
        categories = {v.category for v in violations}
        self.assertEqual(
            categories,
            {
                "ai_slop_vocabulary",
                "negative_boundary_framing",
                "internal_engineering_jargon",
                "unverified_superlative",
            },
        )
        for engine_id in HUMANIZER_ENGINE_IDS:
            orch = PublicProseHumanizerOrchestrator(engine_order=(engine_id,))
            resp = orch.handle(
                PublicProseRequest(
                    request_id=f"test-hum-{engine_id}",
                    surface_hostname="baltor.ai",
                    page_path="/overview",
                    raw_text=dirty,
                )
            )
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertEqual(resp.remaining_violation_count, 0, engine_id)
            self.assertNotIn("delve", resp.cleaned_text.lower())
            self.assertNotIn("tapestry", resp.cleaned_text.lower())
            self.assertNotIn("tenant_id", resp.cleaned_text.lower())
            self.assertNotIn("what baltor is not", resp.cleaned_text.lower())

    def test_known_wrong_strict_refuse_mode_blocks_in_handshake_layer_before_engine(self) -> None:
        resp = self.orchestrator.handle(
            PublicProseRequest(
                request_id="test-hum-strict-refuse",
                surface_hostname="baltor.ai",
                page_path="/",
                raw_text="Furthermore, we delve into a seamless game-changer.",
                strict_refuse=True,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(resp.refusal.code, "public_wording_violation_ai_slop_vocabulary")

    def test_automatic_cascade_fallback_across_all_four_humanizer_engines(self) -> None:
        resp = self.orchestrator.handle(
            PublicProseRequest(
                request_id="test-hum-cascade",
                surface_hostname="agentfeeds.si",
                page_path="/about",
                raw_text="Moreover, we delve into a pivotal tapestry for tenant_id.",
                simulate_strict_gate_deferral=True,
                simulate_voice_rewriter_deferral=True,
                simulate_boundary_framing_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_LEXICAL_CLEANER)
        self.assertEqual(
            resp.attempted_engines,
            (
                ENGINE_HUMANIZER_STRICT,
                ENGINE_PLAIN_CUSTOMER_VOICE,
                ENGINE_POSITIVE_BOUNDARY,
                ENGINE_LEXICAL_CLEANER,
            ),
        )
        self.assertEqual(resp.remaining_violation_count, 0)
        self.assertEqual(resp.frame.depth, 4)


class MultiBrandVisualSeparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = MultiBrandVisualSeparationOrchestrator()

    def test_all_eleven_surfaces_have_unique_design_tokens_chrome_and_shared_backend_parity(self) -> None:
        expected_hosts = {
            "baltor.ai",
            "deterministicskills.baltor.ai",
            "tools.baltor.ai",
            "cornercases.baltor.ai",
            "agentfeeds.si",
            "getagentfoundry.si",
            "agentstudios.si",
            "agentafk.si",
            "agentbriefs.si",
            "dontbeameatproxy.si",
            "skillsforgood.org",
        }
        self.assertEqual(set(AUDITED_BRAND_SURFACES.keys()), expected_hosts)
        primary_tokens = {s.primary_color_token for s in AUDITED_BRAND_SURFACES.values()}
        accent_tokens = {s.surface_accent_token for s in AUDITED_BRAND_SURFACES.values()}
        nav_chromes = {s.nav_chrome_id for s in AUDITED_BRAND_SURFACES.values()}
        heros = {s.hero_proposition for s in AUDITED_BRAND_SURFACES.values()}
        self.assertEqual(len(primary_tokens), 11)
        self.assertEqual(len(accent_tokens), 11)
        self.assertEqual(len(nav_chromes), 11)
        self.assertEqual(len(heros), 11)

        for host in expected_hosts:
            resp = self.orchestrator.handle(
                BrandSeparationAuditRequest(
                    request_id=f"test-brand-{host}",
                    surface_hostname=host,
                )
            )
            self.assertTrue(resp.succeeded, host)
            self.assertTrue(resp.frontend_visually_distinct, host)
            self.assertTrue(resp.backend_facts_synchronized, host)
            self.assertEqual(resp.effective_release_digest, SYNCHRONIZED_RELEASE_DIGEST)

    def test_known_wrong_brand_separation_controls_refuse_cookie_chrome_token_and_canonical_leaks(self) -> None:
        cookie_leak = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="wrong-cookie",
                surface_hostname="agentfeeds.si",
                carries_baltor_session_cookie=True,
            )
        )
        self.assertFalse(cookie_leak.succeeded)
        self.assertFalse(cookie_leak.trace.engine_dispatched)
        self.assertEqual(cookie_leak.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(cookie_leak.refusal.code, "cross_brand_session_cookie_leakage")

        chrome_leak = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="wrong-chrome",
                surface_hostname="agentstudios.si",
                leaks_other_brand_chrome="chrome-baltor-root-v4",
            )
        )
        self.assertFalse(chrome_leak.succeeded)
        self.assertEqual(chrome_leak.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(chrome_leak.refusal.code, "cross_brand_navigation_chrome_collision")

        token_collision = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="wrong-token",
                surface_hostname="getagentfoundry.si",
                primary_color_token="--baltor-ink-navy-950",
            )
        )
        self.assertFalse(token_collision.succeeded)
        self.assertEqual(token_collision.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(token_collision.refusal.code, "cross_brand_design_token_collision")

        canonical_leak = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="wrong-canonical",
                surface_hostname="dontbeameatproxy.si",
                canonical_url=build_surface_url("baltor.ai", "/meatproxy"),
            )
        )
        self.assertFalse(canonical_leak.succeeded)
        self.assertEqual(canonical_leak.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(canonical_leak.refusal.code, "cross_origin_canonical_url_leakage")

    def test_backend_release_digest_mismatch_refuses_or_self_repairs_in_preflight(self) -> None:
        refused = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="stale-refused",
                surface_hostname="skillsforgood.org",
                backend_release_digest=STALE_RELEASE_DIGEST,
                allow_digest_resync_repair=False,
            )
        )
        self.assertFalse(refused.succeeded)
        self.assertEqual(refused.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(refused.refusal.code, "shared_backend_release_digest_mismatch")

        repaired = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="stale-repaired",
                surface_hostname="skillsforgood.org",
                backend_release_digest=STALE_RELEASE_DIGEST,
                allow_digest_resync_repair=True,
            )
        )
        self.assertTrue(repaired.succeeded)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(repaired.effective_release_digest, SYNCHRONIZED_RELEASE_DIGEST)

    def test_brand_auditor_cascade_fallback_across_four_engines(self) -> None:
        resp = self.orchestrator.handle(
            BrandSeparationAuditRequest(
                request_id="brand-cascade",
                surface_hostname="agentbriefs.si",
                simulate_token_auditor_deferral=True,
                simulate_canonical_auditor_deferral=True,
                simulate_parity_auditor_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_STATIC_DESIGN_FALLBACK)
        self.assertEqual(resp.attempted_engines, BRAND_AUDITOR_ENGINE_IDS)


class ProgrammaticSeoComparisonAndBlogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = ProgrammaticSeoComparisonAndBlogOrchestrator()

    def test_generates_six_comparisons_and_eight_blogs_with_noindex_md_twins_and_jsonld(self) -> None:
        resp = self.orchestrator.handle(
            SeoContentGenerationRequest(
                request_id="seo-all",
                surface_hostname="*",
                inject_slop_into_draft=True,
            )
        )
        self.assertTrue(resp.succeeded)
        comparisons = [a for a in resp.artifacts if a.kind == "comparison_guide"]
        blogs = [a for a in resp.artifacts if a.kind == "technical_blog"]
        self.assertEqual(len(comparisons), 6)
        self.assertEqual(len(blogs), 8)
        for art in resp.artifacts:
            self.assertEqual(art.prose_violations, 0, art.artifact_id)
            self.assertTrue(art.canonical_html_url.startswith(f"https://{art.surface_hostname}/"))
            self.assertEqual(art.markdown_twin_url, f"{art.canonical_html_url}.md")
            self.assertIn("noindex", art.markdown_twin_robots_header)
            self.assertEqual(art.release_digest, SYNCHRONIZED_RELEASE_DIGEST)
            schema_types = {s["@type"] for s in art.jsonld_schemas}
            self.assertIn("TechArticle", schema_types)
            self.assertIn("FAQPage", schema_types)
            if art.kind == "technical_blog":
                self.assertIn("SoftwareSourceCode", schema_types)
        self.assertIn(SYNCHRONIZED_RELEASE_DIGEST, resp.llms_txt_manifest)

    def test_known_wrong_seo_preflight_refuses_indexable_md_twin_and_foreign_canonical_override(self) -> None:
        cannibalized = self.orchestrator.handle(
            SeoContentGenerationRequest(
                request_id="seo-wrong-noindex",
                surface_hostname="baltor.ai",
                markdown_twin_robots="index, follow",
            )
        )
        self.assertFalse(cannibalized.succeeded)
        self.assertFalse(cannibalized.trace.engine_dispatched)
        self.assertEqual(cannibalized.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(cannibalized.refusal.code, "markdown_twin_missing_noindex")

        foreign_canonical = self.orchestrator.handle(
            SeoContentGenerationRequest(
                request_id="seo-wrong-canonical",
                surface_hostname="agentstudios.si",
                canonical_host_override="baltor.ai",
            )
        )
        self.assertFalse(foreign_canonical.succeeded)
        self.assertEqual(foreign_canonical.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(foreign_canonical.refusal.code, "cross_origin_canonical_override_forbidden")

    def test_seo_engine_cascade_fallback_to_exporter(self) -> None:
        resp = self.orchestrator.handle(
            SeoContentGenerationRequest(
                request_id="seo-cascade",
                surface_hostname="baltor.ai",
                simulate_comparison_engine_deferral=True,
                simulate_blog_engine_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_JSONLD_LLMS_EXPORTER)
        self.assertEqual(resp.attempted_engines, SEO_CONTENT_ENGINE_IDS)


class SuiteBenchmarkAndSelfTestTests(unittest.TestCase):
    def test_self_test_and_benchmark_pass_all_checks(self) -> None:
        result = self_test()
        self.assertTrue(result["passed"], result["checks"])
        bench = run_head_to_head_benchmark()
        self.assertEqual(bench["audited_surface_count"], 11)
        self.assertEqual(bench["comparison_guide_count"], 6)
        self.assertEqual(bench["technical_blog_count"], 8)
        self.assertTrue(bench["known_wrong_probes"]["all_blocked_before_engine"])
        self.assertEqual(SHARED_BACKEND_FACTS["release_digest"], "29a2bc33")


if __name__ == "__main__":
    unittest.main()

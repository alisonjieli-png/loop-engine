"""Tests for the 54-Directory RepoDir.com-Sibling Ecosystem, Scientific Paper
Portals & Facebook Pages/Posts Continuous Scanner + Top-100 Resume GitHub
Systems Projects & Full-Startup Builder Engine Suite.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_REPO_ROOT / "src"), str(_REPO_ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from repodir_siblings_scientific_papers_facebook_and_top100_github_engines import (  # noqa: E402
    ALL_SLOTS,
    AUTHORIZED_FACEBOOK_ARCHIVE_PATHS,
    AUTHORIZED_FACEBOOK_EXPORT_ID,
    COOL_AI_LINKS_V3_SECTIONS,
    COOL_AI_LINKS_V3_TOTAL_LINKS,
    DISCOVERY_54_PLATFORMS_CATALOG,
    ENGINE_54_ECOSYSTEM_SCANNER,
    ENGINE_BUILDER_FALLBACK,
    ENGINE_SCANNER_FALLBACK,
    ENGINE_TOP100_DECOMPOSER,
    FIVE_HARNESS_PACK_FILES,
    MASTERY_CATEGORIES_COUNT,
    MAX_CONTRACT_CARD_BYTES,
    PROJECTS_PER_CATEGORY,
    RepoDirPapersFacebookScannerOrchestrator,
    RepoDirPapersFacebookScanRequest,
    SLOT_REPODIR_PAPERS_FB_SCANNER,
    SLOT_TOP100_GITHUB_STARTUP_BUILDER,
    TOP_100_RESUME_PROJECTS_CATALOG,
    TOTAL_DISCOVERY_PLATFORMS,
    TOTAL_RESUME_PROJECTS,
    Top100ProjectBuilderRequest,
    Top100ResumeGitHubAndStartupBuilderOrchestrator,
    run_repodir_siblings_and_top100_github_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_ACCEPTED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
)


class RepoDirSiblingsAndTop100GitHubEngineTests(unittest.TestCase):
    """Verify 54 discovery platforms, 100 resume GitHub & startup projects, and 4 known-wrong controls."""

    def test_grounding_constants_and_54_platform_catalog_completeness(self) -> None:
        self.assertEqual( len(ALL_SLOTS), 2)
        self.assertEqual(COOL_AI_LINKS_V3_TOTAL_LINKS, 2298)
        self.assertEqual(COOL_AI_LINKS_V3_SECTIONS, 53)
        self.assertEqual(AUTHORIZED_FACEBOOK_EXPORT_ID, "facebook-61571002675408-2026-09-07-io0DzAIg.zip")
        self.assertIn("start_here.html", AUTHORIZED_FACEBOOK_ARCHIVE_PATHS)
        self.assertIn("preferences/preferences/reels_preferences.html", AUTHORIZED_FACEBOOK_ARCHIVE_PATHS)
        self.assertIn("preferences/feed/reduce.html", AUTHORIZED_FACEBOOK_ARCHIVE_PATHS)
        self.assertEqual(len(DISCOVERY_54_PLATFORMS_CATALOG), TOTAL_DISCOVERY_PLATFORMS)

        scanner = RepoDirPapersFacebookScannerOrchestrator()
        res = scanner.handle(
            RepoDirPapersFacebookScanRequest(
                schema="repodir_siblings_papers_and_facebook_scan_request/v1",
                platforms=DISCOVERY_54_PLATFORMS_CATALOG,
                preferred_engine=ENGINE_54_ECOSYSTEM_SCANNER,
            )
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_REPODIR_PAPERS_FB_SCANNER)
        self.assertFalse(res.fallback_used)
        self.assertEqual(res.platforms_scanned_count, 54)
        self.assertEqual(
            res.ecosystem_counts,
            {
                "E1_repodir_sibling_tool_and_repo_directories": 20,
                "E2_scientific_paper_and_method_portals": 18,
                "E3_facebook_pages_posts_reels_and_social_archives": 16,
            },
        )
        self.assertEqual(res.extracted_primitives_count, 54)
        self.assertEqual(res.short_video_scripts_generated, 54)
        self.assertTrue(res.facebook_authorized_archive_verified)
        self.assertEqual(res.nested_frame_depth, 1)
        self.assertIn((LAYER_HANDSHAKE, LAYER_ACCEPTED), res.layer_trace)
        self.assertIn((LAYER_PREFLIGHT, LAYER_ACCEPTED), res.layer_trace)

    def test_top100_resume_projects_and_10_startup_blueprints(self) -> None:
        self.assertEqual(len(TOP_100_RESUME_PROJECTS_CATALOG), TOTAL_RESUME_PROJECTS)
        self.assertEqual(MASTERY_CATEGORIES_COUNT * PROJECTS_PER_CATEGORY, 100)

        builder = Top100ResumeGitHubAndStartupBuilderOrchestrator()
        res = builder.handle(
            Top100ProjectBuilderRequest(
                schema="top100_resume_github_and_startup_builder_request/v1",
                projects=TOP_100_RESUME_PROJECTS_CATALOG,
                preferred_engine=ENGINE_TOP100_DECOMPOSER,
                learning_iterations=3,
            )
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_TOP100_GITHUB_STARTUP_BUILDER)
        self.assertFalse(res.fallback_used)
        self.assertEqual(res.projects_built_count, 100)
        self.assertEqual(res.categories_covered_count, 10)
        self.assertEqual(res.full_stack_startups_built_count, 10)
        self.assertLessEqual(res.max_contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
        self.assertEqual(res.iteration_pass_rates_pct, (78.0, 91.0, 96.0))
        self.assertTrue(res.continuous_learning_improvement_verified)

        for pack in res.synthesized_packs:
            self.assertEqual(tuple(pack.harness_files.keys()), FIVE_HARNESS_PACK_FILES)
            self.assertLessEqual(pack.contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
            if pack.is_full_stack_startup:
                self.assertIsNotNone(pack.startup_blueprint)

    def test_engine_fallback_on_both_slots(self) -> None:
        scanner = RepoDirPapersFacebookScannerOrchestrator()
        scan_res = scanner.handle(
            RepoDirPapersFacebookScanRequest(
                schema="repodir_siblings_papers_and_facebook_scan_request/v1",
                preferred_engine="unknown_scanner_engine",
            )
        )
        self.assertTrue(scan_res.accepted)
        self.assertTrue(scan_res.fallback_used)
        self.assertEqual(scan_res.selected_engine, ENGINE_SCANNER_FALLBACK)

        builder = Top100ResumeGitHubAndStartupBuilderOrchestrator()
        build_res = builder.handle(
            Top100ProjectBuilderRequest(
                schema="top100_resume_github_and_startup_builder_request/v1",
                preferred_engine="unknown_builder_engine",
            )
        )
        self.assertTrue(build_res.accepted)
        self.assertTrue(build_res.fallback_used)
        self.assertEqual(build_res.selected_engine, ENGINE_BUILDER_FALLBACK)

    def test_four_known_wrong_controls_and_carrier_refusals(self) -> None:
        scanner = RepoDirPapersFacebookScannerOrchestrator()
        builder = Top100ResumeGitHubAndStartupBuilderOrchestrator()

        # Carrier refusals
        bad_scan_carrier = scanner.handle(RepoDirPapersFacebookScanRequest(schema="bad_schema/v0"))
        self.assertFalse(bad_scan_carrier.accepted)
        self.assertIn((LAYER_CARRIER, LAYER_REFUSED), bad_scan_carrier.layer_trace)

        bad_build_carrier = builder.handle(Top100ProjectBuilderRequest(schema="bad_schema/v0"))
        self.assertFalse(bad_build_carrier.accepted)
        self.assertIn((LAYER_CARRIER, LAYER_REFUSED), bad_build_carrier.layer_trace)

        # Control (a): Unauthorized scraping of private Facebook user profiles refused
        ctrl_a = scanner.handle(
            RepoDirPapersFacebookScanRequest(
                schema="repodir_siblings_papers_and_facebook_scan_request/v1",
                allow_unauthorized_private_facebook_scraping=True,
            )
        )
        self.assertFalse(ctrl_a.accepted)
        self.assertIsNotNone(ctrl_a.refusal)
        assert ctrl_a.refusal is not None
        self.assertEqual(ctrl_a.refusal.code, "unauthorized_private_facebook_scraping_refused")
        self.assertIn((LAYER_PREFLIGHT, LAYER_REFUSED), ctrl_a.layer_trace)

        # Control (b): Scientific paper method without reproducible deterministic verifier refused
        unverified_paper_plat = replace(
            DISCOVERY_54_PLATFORMS_CATALOG[20],
            has_reproducible_paper_verifier=False,
        )
        ctrl_b = scanner.handle(
            RepoDirPapersFacebookScanRequest(
                schema="repodir_siblings_papers_and_facebook_scan_request/v1",
                platforms=(unverified_paper_plat,),
            )
        )
        self.assertFalse(ctrl_b.accepted)
        self.assertIsNotNone(ctrl_b.refusal)
        assert ctrl_b.refusal is not None
        self.assertEqual(ctrl_b.refusal.code, "unverified_scientific_paper_method_refused")

        # Control (c): Top-100 project scaffolding with TODO or NotImplementedError stub refused
        stub_proj = replace(TOP_100_RESUME_PROJECTS_CATALOG[0], contains_todo_or_stub=True)
        ctrl_c = builder.handle(
            Top100ProjectBuilderRequest(
                schema="top100_resume_github_and_startup_builder_request/v1",
                projects=(stub_proj,),
            )
        )
        self.assertFalse(ctrl_c.accepted)
        self.assertIsNotNone(ctrl_c.refusal)
        assert ctrl_c.refusal is not None
        self.assertEqual(ctrl_c.refusal.code, "todo_stub_or_not_implemented_scaffolding_refused")

        # Control (d): Contract card bloat > 2,048 bytes refused
        bloated_proj = replace(TOP_100_RESUME_PROJECTS_CATALOG[0], forced_card_padding_bytes=2200)
        ctrl_d = builder.handle(
            Top100ProjectBuilderRequest(
                schema="top100_resume_github_and_startup_builder_request/v1",
                projects=(bloated_proj,),
            )
        )
        self.assertFalse(ctrl_d.accepted)
        self.assertIsNotNone(ctrl_d.refusal)
        assert ctrl_d.refusal is not None
        self.assertEqual(ctrl_d.refusal.code, "contract_card_bloat_refused")

    def test_benchmark_metrics_and_continuous_learning(self) -> None:
        report = run_repodir_siblings_and_top100_github_benchmark()
        self.assertEqual(report["platforms_scanned_count"], 54)
        self.assertEqual(report["projects_built_count"], 100)
        self.assertEqual(report["full_stack_startups_built_count"], 10)
        self.assertTrue(report["continuous_learning_improvement_verified"])
        strategies = {s["strategy_id"]: s for s in report["strategies"]}
        self.assertEqual(strategies["unassisted_cheap_model_without_baltor"]["top100_pass_rate_pct"], 22.0)
        baltor = strategies["baltor_top100_project_and_54_directory_assisted_harness"]
        self.assertEqual(baltor["top100_pass_rate_pct"], 96.0)
        self.assertEqual(baltor["relative_token_spend_delta_pct"], -86.4)
        self.assertEqual(baltor["continuous_learning_iter1_to_iter3_pct"], (78.0, 91.0, 96.0))


if __name__ == "__main__":
    unittest.main()

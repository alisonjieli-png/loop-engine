"""Unit tests for the Baltor Un-Nerfed Persistent Virtual Desktop, Residential/Paired-Node
Browser Profile, and Autonomous Multi-Platform Website/Social Posting Product Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
REPOSITORY = TOOLS_DIR.parent
for p in (TOOLS_DIR, REPOSITORY / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from unnerfed_virtual_desktop_and_website_posting_automation_engines import (  # noqa: E402
    ALL_10_WEB_SURFACES,
    ALL_30_WEBSITE_AUTOMATION_TASKS,
    BASELINE_NERFED_VENDOR_DOTS_AND_MUSE,
    ENGINE_CDP_FILE_CHOOSER_AND_PASTE_PUBLISHER,
    ENGINE_HYBRID_API_AND_VISION_GUI_PUBLISHER,
    ENGINE_NERFED_AGENT_RESCUE_DELEGATION_BRIDGE,
    ENGINE_PAIRED_RESIDENTIAL_EDGE_BROWSER_BRIDGE,
    ENGINE_RESCUE_DELEGATED_CRON_PUBLISHER,
    ENGINE_SINGLE_TENANT_PERSISTENT_CLOUD_DESKTOP,
    RESCUE_DELEGATION_CHANNELS,
    SLOT_AUTONOMOUS_WEBSITE_POSTING,
    SLOT_UNNERFED_VIRTUAL_DESKTOP,
    SUITE_BALTOR_UNNERFED_DESKTOP_AND_BRIDGE,
    VENDOR_NERF_SYMPTOMS,
    AutonomousWebsiteAndSocialPostingWorkflowSlot,
    UnnerfedPersistentVirtualDesktopSlot,
    run_known_wrong_controls,
    run_unnerfed_virtual_desktop_and_posting_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
)


class UnnerfedVirtualDesktopAndWebsitePostingTests(unittest.TestCase):
    def test_10_web_surfaces_and_30_tasks_catalog(self) -> None:
        self.assertEqual(len(ALL_10_WEB_SURFACES), 10)
        self.assertEqual(len(ALL_30_WEBSITE_AUTOMATION_TASKS), 30)
        self.assertEqual(len(VENDOR_NERF_SYMPTOMS), 4)

        expected_surfaces = {
            "S01_bluesky_web_and_atproto_multi_image_publisher",
            "S02_telegram_web_k_and_a_media_channel_publisher",
            "S03_x_twitter_longform_thread_and_video_publisher",
            "S04_linkedin_carousel_pdf_and_article_publisher",
            "S05_reddit_flair_and_crosspost_automation",
            "S06_discord_webhook_and_rich_embed_forum_publisher",
            "S07_youtube_shorts_and_studio_metadata_publisher",
            "S08_substack_and_ghost_newsletter_issue_publisher",
            "S09_producthunt_and_hackernews_launch_synchronizer",
            "S10_multi_step_authenticated_saas_form_and_portal_automator",
        }
        self.assertEqual({s.surface_id for s in ALL_10_WEB_SURFACES}, expected_surfaces)

    def test_slot_family_1_unnerfed_persistent_virtual_desktop_engines(self) -> None:
        slot = UnnerfedPersistentVirtualDesktopSlot()

        # 1. Single-tenant persistent cloud virtual desktop engine
        r_cloud = slot.provision_or_bridge_desktop_session(
            "S01_bluesky_web_and_atproto_multi_image_publisher",
            preferred_engine=ENGINE_SINGLE_TENANT_PERSISTENT_CLOUD_DESKTOP,
            request_id="test_desktop_cloud_01",
        )
        self.assertTrue(r_cloud.accepted)
        self.assertEqual(r_cloud.slot_id, SLOT_UNNERFED_VIRTUAL_DESKTOP)
        self.assertEqual(r_cloud.selected_engine, ENGINE_SINGLE_TENANT_PERSISTENT_CLOUD_DESKTOP)
        for layer in COVERAGE_LAYERS:
            self.assertEqual(r_cloud.layer_verdicts[layer], "full")
        self.assertTrue(r_cloud.output["file_select_dialogs_allowed"])
        self.assertTrue(r_cloud.output["cdp_file_chooser_interception_enabled"])
        self.assertTrue(r_cloud.output["virtual_staging_drive"].endswith("baltor-stage"))
        vault = r_cloud.output["persistent_encrypted_profile_vault"]
        self.assertEqual(vault["cipher"], "AES-256-GCM")
        self.assertFalse(vault["relogin_or_2fa_required_on_cron"])
        self.assertIn("cookies", vault["persisted_stores"])
        self.assertIn("IndexedDB", vault["persisted_stores"])

        # 2. Paired residential edge browser bridge engine
        r_res = slot.provision_or_bridge_desktop_session(
            "S03_x_twitter_longform_thread_and_video_publisher",
            preferred_engine=ENGINE_PAIRED_RESIDENTIAL_EDGE_BROWSER_BRIDGE,
            paired_lan_host="192.168.50.14",
            request_id="test_desktop_res_02",
        )
        self.assertTrue(r_res.accepted)
        self.assertEqual(r_res.selected_engine, ENGINE_PAIRED_RESIDENTIAL_EDGE_BROWSER_BRIDGE)
        bridge = r_res.output["paired_residential_bridge"]
        self.assertTrue(bridge["active"])
        self.assertEqual(bridge["paired_endpoint"], "192.168.50.14")
        self.assertTrue(bridge["reverse_websocket_tunnel_authenticated"])
        self.assertTrue(bridge["residential_ip_attested"])
        self.assertTrue(bridge["datacenter_captcha_loops_eliminated"])

        # 3. Nerfed agent rescue delegation bridge engine
        r_rescue = slot.provision_or_bridge_desktop_session(
            "S08_substack_and_ghost_newsletter_issue_publisher",
            preferred_engine=ENGINE_NERFED_AGENT_RESCUE_DELEGATION_BRIDGE,
            rescue_from_agent="OpenAI Operator / Dots",
            rescue_channel="signals_plus_post_email_drop",
            request_id="test_desktop_rescue_03",
        )
        self.assertTrue(r_rescue.accepted)
        self.assertEqual(r_rescue.selected_engine, ENGINE_NERFED_AGENT_RESCUE_DELEGATION_BRIDGE)
        rescue = r_rescue.output["nerfed_agent_rescue_delegation"]
        self.assertEqual(rescue["rescued_external_agent"], "OpenAI Operator / Dots")
        self.assertEqual(rescue["delegation_channel"], "signals_plus_post_email_drop")
        self.assertEqual(rescue["supported_channels"], RESCUE_DELEGATION_CHANNELS)
        self.assertEqual(rescue["human_bailout_prompts_triggered"], 0)

    def test_slot_family_2_autonomous_website_and_social_posting_across_10_surfaces(self) -> None:
        slot = AutonomousWebsiteAndSocialPostingWorkflowSlot()
        engines = (
            ENGINE_CDP_FILE_CHOOSER_AND_PASTE_PUBLISHER,
            ENGINE_HYBRID_API_AND_VISION_GUI_PUBLISHER,
            ENGINE_RESCUE_DELEGATED_CRON_PUBLISHER,
        )
        for idx, surface in enumerate(ALL_10_WEB_SURFACES):
            eng = engines[idx % len(engines)]
            res = slot.execute_website_publishing_workflow(
                surface.surface_id,
                preferred_engine=eng,
                request_id=f"test_pub_surface_{idx:02d}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_AUTONOMOUS_WEBSITE_POSTING)
            self.assertEqual(res.selected_engine, eng)
            self.assertTrue(res.output["nested_desktop_accepted"])
            self.assertTrue(res.output["multi_asset_upload_succeeded"])
            self.assertTrue(res.output["dom_publication_receipt_verified"])
            self.assertFalse(res.output["human_bailout_required"])
            self.assertIn(surface.domain_host, res.output["live_post_url_receipt"])

    def test_30_task_website_automation_and_posting_benchmark(self) -> None:
        bench = run_unnerfed_virtual_desktop_and_posting_benchmark()
        self.assertEqual(bench["total_tasks"], 30)
        self.assertEqual(bench["total_web_surfaces"], 10)
        self.assertEqual(bench["variations_per_surface"], 3)
        self.assertTrue(bench["all_30_tasks_executed_through_7_layer_envelope"])

        nerfed = bench["nerfed_vendor_virtual_desktop_dots_and_muse_baseline"]
        self.assertEqual(nerfed["engine_id"], BASELINE_NERFED_VENDOR_DOTS_AND_MUSE)
        self.assertEqual(nerfed["tasks_completed"], 5)
        self.assertEqual(nerfed["tasks_blocked_or_bailed_out"], 25)
        self.assertEqual(nerfed["autonomous_completion_pct"], "16.7%")
        self.assertEqual(nerfed["blocked_or_human_bailout_pct"], "83.3%")

        baltor = bench["baltor_unnerfed_persistent_desktop_and_residential_bridge_suite"]
        self.assertEqual(baltor["engine_id"], SUITE_BALTOR_UNNERFED_DESKTOP_AND_BRIDGE)
        self.assertEqual(baltor["tasks_completed"], 29)
        self.assertEqual(baltor["autonomous_completion_pct"], "96.7%")
        self.assertEqual(baltor["bluesky_and_telegram_multi_image_tasks"], 6)
        self.assertEqual(baltor["bluesky_and_telegram_multi_image_passed"], 6)
        self.assertEqual(baltor["bluesky_and_telegram_multi_image_success_pct"], "100.0%")
        self.assertEqual(baltor["persistent_session_cron_human_bailouts"], 0)

    def test_four_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "cross_tenant_browser_profile_leak_refused",
            "duplicate_unidempotent_social_post_refused",
            "public_post_secret_attachment_refused",
            "unverified_post_receipt_claim_refused",
        }
        observed_codes = set()
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])
            observed_codes.add(ctrl["actual_refusal_code"])
        self.assertEqual(observed_codes, expected_codes)


if __name__ == "__main__":
    unittest.main()

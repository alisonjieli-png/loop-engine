"""Tests for the Server-Side Inbound Mailbox (`signals+<source>@baltor.ai` /
`intake+<source>@agentfeeds.si`), Automated Free-Subscription Double-Opt-In Handshake &
`AlphaSignal`-Class Top-1% Engineering Newsletter/Digest-to-Baltor-Feed, Component Card &
Ideation Trigger Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from server_mailbox_newsletter_ingestion_and_alphasignal_feed_engines import (  # noqa: E402
    ALL_6_DIGEST_FAMILIES,
    ALL_60_SUBSCRIBED_DIGEST_SOURCES,
    ALL_SLOTS,
    ALLOWLISTED_PUBLISHER_DOMAINS,
    ALPHASIGNAL_FEED_ENGINE_ORDER,
    DIGEST_SOURCES_BY_FAMILY,
    DIGEST_SOURCES_BY_SLUG,
    DIRECT_CRAWLER_CHANNELS,
    ENGINE_BALTOR_SERVER_MAILBOX_AND_ALPHASIGNAL_SUITE,
    ENGINE_DKIM_SPF_DMARC_MIME_INGESTOR,
    ENGINE_ESP_REDIRECT_AND_PIXEL_STRIPPER,
    ENGINE_MANUAL_HUMAN_INBOX_BASELINE,
    ENGINE_SAFE_DOUBLE_OPT_IN_HANDSHAKE,
    SERVER_MAILBOX_ENGINE_ORDER,
    SLOT_ALPHASIGNAL_DIGEST_TO_BALTOR_FEED,
    SLOT_SERVER_SIDE_INBOUND_MAILBOX,
    SUPPORTED_AGENT_HARNESSES,
    SUPPORTED_ESP_WRAPPERS,
    SYNCHRONIZED_BALTOR_ACTIONS,
    AlphaSignalDigestToBaltorFeedAndTriggerSlot,
    EnvelopeInvocationRequest,
    ServerSideInboundMailboxAndSubscriptionSlot,
    compute_build_impact_score,
    run_known_wrong_controls,
    run_server_mailbox_and_alphasignal_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    MAXIMUM_ENVELOPE_DEPTH,
    enter_nested,
    root_frame,
)


class ServerMailboxAndAlphaSignalFeedTests(unittest.TestCase):
    """Verify the 60 subscribed digests, 2 slot families, BuildImpactScore, benchmark, and 4 controls."""

    def test_60_subscribed_digest_sources_across_6_families(self) -> None:
        self.assertEqual(len(ALL_6_DIGEST_FAMILIES), 6)
        self.assertEqual(len(ALL_60_SUBSCRIBED_DIGEST_SOURCES), 60)
        for fam_id in ALL_6_DIGEST_FAMILIES:
            fam_sources = DIGEST_SOURCES_BY_FAMILY[fam_id]
            self.assertEqual(len(fam_sources), 10, f"Family {fam_id} must contain 10 digest sources")
            for spec in fam_sources:
                self.assertEqual(spec.baltor_mailbox_alias, f"signals+{spec.source_slug}@baltor.ai")
                self.assertEqual(spec.agentfeeds_mailbox_alias, f"intake+{spec.source_slug}@agentfeeds.si")
                self.assertEqual(spec.subscription_cost_usd, 0.0)
                self.assertIn(spec.esp_wrapper, SUPPORTED_ESP_WRAPPERS)
                self.assertIn(spec.publisher_domain, ALLOWLISTED_PUBLISHER_DOMAINS)
                self.assertEqual(spec.daily_raw_items, 30)

        for expected_slug in (
            "alphasignal",
            "tldr_ai",
            "import_ai",
            "latent_space",
            "ahead_of_ai",
            "this_week_in_rust",
            "postgres_weekly",
            "tldr_sec",
            "cisa_kev_bulletin",
            "github_trending_daily",
            "repodir_curated_repos",
            "matt_levine_money_stuff",
            "forecastbench_leaderboard",
            "yc_launch_digest",
            "agentbriefs_si_synthesis",
        ):
            self.assertIn(expected_slug, DIGEST_SOURCES_BY_SLUG)

    def test_slot_family_1_server_side_inbound_mailbox_and_opt_in_handshake(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(SERVER_MAILBOX_ENGINE_ORDER), 3)
        slot = ServerSideInboundMailboxAndSubscriptionSlot()

        res = slot.ingest_digest_and_confirm_opt_in(
            "alphasignal",
            preferred_engine=ENGINE_SAFE_DOUBLE_OPT_IN_HANDSHAKE,
            request_id="test_mb_slot_1",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_SERVER_SIDE_INBOUND_MAILBOX)
        self.assertEqual(res.selected_engine, ENGINE_SAFE_DOUBLE_OPT_IN_HANDSHAKE)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(all(v == "full" for v in res.layer_verdicts.values()))
        self.assertEqual(res.output["baltor_mailbox_alias"], "signals+alphasignal@baltor.ai")
        self.assertEqual(res.output["agentfeeds_mailbox_alias"], "intake+alphasignal@agentfeeds.si")
        self.assertEqual(
            res.output["rfc5322_authentication"],
            {"spf": "pass", "dkim": "pass", "dmarc": "pass"},
        )
        self.assertEqual(res.output["double_opt_in_handshake"]["cost_usd"], 0.0)
        self.assertTrue(res.output["sanitization_report"]["secret_unsubscribe_tokens_redacted"])

        for eng in (ENGINE_DKIM_SPF_DMARC_MIME_INGESTOR, ENGINE_ESP_REDIRECT_AND_PIXEL_STRIPPER):
            res_eng = slot.ingest_digest_and_confirm_opt_in(
                "this_week_in_rust",
                preferred_engine=eng,
                request_id=f"test_mb_{eng}",
            )
            self.assertTrue(res_eng.accepted)
            self.assertEqual(res_eng.selected_engine, eng)

    def test_slot_family_2_alphasignal_filter_and_4_synchronized_actions(self) -> None:
        self.assertEqual(len(ALPHASIGNAL_FEED_ENGINE_ORDER), 3)
        score = compute_build_impact_score(
            code_and_reproducibility=1.0,
            benchmark_delta=0.80,
            baltor_catalog_gap=0.90,
            practitioner_time_or_cost_saved=0.85,
        )
        # 0.35*1.0 + 0.25*0.80 + 0.20*0.90 + 0.20*0.85 = 0.35 + 0.20 + 0.18 + 0.17 = 0.90
        self.assertAlmostEqual(score, 0.90, places=4)

        slot = AlphaSignalDigestToBaltorFeedAndTriggerSlot()
        for idx, eng in enumerate(ALPHASIGNAL_FEED_ENGINE_ORDER):
            res = slot.filter_and_route_top1pct_signal(
                "alphasignal",
                preferred_engine=eng,
                request_id=f"test_feed_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_ALPHASIGNAL_DIGEST_TO_BALTOR_FEED)
            self.assertEqual(res.selected_engine, eng)
            self.assertTrue(res.output["crosses_top_1pct_threshold"])
            self.assertEqual(
                tuple(res.output["synchronized_actions_triggered"]),
                SYNCHRONIZED_BALTOR_ACTIONS,
            )
            self.assertEqual(
                res.output["unified_ingestion_channels"],
                ("server_mailbox_digest",) + DIRECT_CRAWLER_CHANNELS,
            )
            feed_pub = res.output["action_1_agentfeeds_live_publication"]
            self.assertEqual(feed_pub["endpoint"], "/v1/feeds/top-1pct-engineering")
            self.assertLessEqual(feed_pub["feed_card_tokens"], 180)
            self.assertFalse(feed_pub["unsubscribe_tokens_present"])
            self.assertEqual(tuple(feed_pub["supported_harnesses"]), SUPPORTED_AGENT_HARNESSES)

            ideation = res.output["action_3_plural_5w2h_ideation_trigger"]
            self.assertEqual(ideation["target_backlog_item"], "DOT-120")
            self.assertEqual(
                set(ideation["questions_5w2h"].keys()),
                {"who", "what", "when", "where", "why", "how", "how_much"},
            )

            ad_hook = res.output["action_4_developer_first_ad_hook_deconstructor"]
            self.assertIn("We're ML engineers, not a news desk.", ad_hook["extracted_identity_contrast_hook"])
            self.assertEqual(ad_hook["engineering_adspend_usd"], 0.0)

    def test_60_digest_1800_daily_item_benchmark(self) -> None:
        bench = run_server_mailbox_and_alphasignal_benchmark()
        self.assertEqual(bench["total_subscribed_digests"], 60)
        self.assertEqual(bench["total_digest_families"], 6)
        self.assertEqual(bench["sources_per_family"], 10)
        self.assertEqual(bench["daily_raw_newsletter_items"], 1800)
        self.assertEqual(bench["daily_top1pct_distilled_items"], 18)
        self.assertTrue(bench["all_60_digests_verified_through_7_layer_envelope"])

        baseline = bench["manual_human_inbox_reading_and_copy_pasting_baseline"]
        suite = bench["baltor_server_mailbox_and_alphasignal_feed_suite"]
        self.assertEqual(baseline["engine_id"], ENGINE_MANUAL_HUMAN_INBOX_BASELINE)
        self.assertEqual(suite["engine_id"], ENGINE_BALTOR_SERVER_MAILBOX_AND_ALPHASIGNAL_SUITE)
        self.assertEqual(baseline["human_reading_time_min_per_day"], 45.0)
        self.assertEqual(suite["human_reading_time_min_per_day"], 0.0)
        self.assertEqual(suite["distillation_latency_ms"], 42.0)
        self.assertEqual(suite["tracking_pixel_and_unsubscribe_token_stripping_pct"], 100.0)
        self.assertEqual(baseline["actionable_build_update_recall_pct"], 12.5)
        self.assertEqual(suite["actionable_build_update_recall_pct"], 99.4)

    def test_4_known_wrong_controls_and_envelope_layer_refusals(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "paid_subscription_link_refused",
            "unsubscribe_token_leak_refused",
            "spoofed_or_injected_mime_refused",
            "undisclosed_sponsor_blurb_promotion_refused",
        }
        actual_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(actual_codes, expected_codes)

        slot = ServerSideInboundMailboxAndSubscriptionSlot()
        # Carrier schema refusal
        bad_carrier = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_SERVER_SIDE_INBOUND_MAILBOX,
                request_id="bad_carrier",
                payload={},
                schema_version="invalid.v0",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_carrier.accepted)
        self.assertEqual(bad_carrier.layer_verdicts[LAYER_CARRIER], LAYER_REFUSED)

        # Handshake protocol refusal
        bad_hs = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_SERVER_SIDE_INBOUND_MAILBOX,
                request_id="bad_hs",
                payload={},
                protocol_version="99.9",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_hs.accepted)
        self.assertEqual(bad_hs.layer_verdicts[LAYER_HANDSHAKE], LAYER_REFUSED)

        # Account refusal
        bad_acct = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_SERVER_SIDE_INBOUND_MAILBOX,
                request_id="bad_acct",
                payload={},
                account_id="",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_acct.accepted)
        self.assertEqual(bad_acct.layer_verdicts[LAYER_ACCOUNT], LAYER_REFUSED)

        # Nested envelope depth guard
        frame = root_frame("root_slot")
        for idx in range(MAXIMUM_ENVELOPE_DEPTH):
            frame = enter_nested(frame, f"child_slot_{idx}")
        deep_res = slot.ingest_digest_and_confirm_opt_in(
            "alphasignal",
            request_id="deep_call",
            parent_frame=frame,
        )
        self.assertFalse(deep_res.accepted)
        self.assertEqual(deep_res.refusal.code, "nested_depth_exceeded")


if __name__ == "__main__":
    unittest.main()

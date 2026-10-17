"""Unit tests for the 60-Profile Google Alerts (`Atom/RSS` + Inbound Server-Mailbox
`alerts+<slug>@baltor.ai`) Trigger Ingestor, Redirect Canonicalizer & Priority
Background Worker Search Queue Engine Suite.
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

from google_alerts_trigger_and_worker_search_queue_engines import (  # noqa: E402
    ALL_4_PRIORITY_WORKER_QUEUES,
    ALL_6_ALERT_DOMAINS,
    ALL_60_GOOGLE_ALERT_PROFILES,
    COVERAGE_LAYERS,
    DOMAIN_A01_FRONTIER_MODELS,
    DOMAIN_A02_GITHUB_REPOS_MCP_CLI,
    DOMAIN_A03_SANDBOX_NERFS_WORKAROUNDS,
    DOMAIN_A04_CVE_SECURITY_ADVISORIES,
    DOMAIN_A05_VOLATILE_LAWS_POLICIES_PRICING,
    DOMAIN_A06_RISING_CREATORS_INDIE_DEMOS,
    ENGINE_BALTOR_GOOGLE_ALERTS_TRIGGER_AND_PRIORITY_WORKER_QUEUE_SUITE,
    ENGINE_DEEP_SEARCH_MULTI_HOP_WORKER_HARVESTER,
    ENGINE_GOOGLE_ALERT_REDIRECT_UNWRAPPER_AND_SIMHASH_DEDUPLICATOR,
    ENGINE_UNFILTERED_POLL_EVERYTHING_OR_MANUAL_SEARCH_BASELINE,
    GOOGLE_ALERTS_INGESTION_ADAPTER,
    LAYER_PREFLIGHT,
    QUEUE_P0_URGENT_CVE_AND_POLICY_RECHECK,
    QUEUE_P1_CODE_REPO_AND_MODEL_CARD_SYNTHESIS,
    QUEUE_P2_TOOL_NERF_AND_WORKAROUND_SYNTHESIS,
    QUEUE_P3_RISING_CREATOR_AND_DEEP_TOPIC_EXPANSION,
    SLOT_ALERT_TRIGGERED_WORKER_SEARCH_WORK_QUEUE,
    SLOT_GOOGLE_ALERTS_RSS_AND_EMAIL_TRIGGER_INGESTION,
    WORKER_SEARCH_QUEUE_ADAPTER,
    compute_simhash_64,
    evaluate_google_alerts_trigger_and_worker_search_queue_suite,
    invoke_google_alerts_ingestion_slot,
    invoke_worker_search_queue_slot,
    is_private_or_ssrf_target_url,
    run_known_wrong_refusal_controls,
    simhash_hamming_distance,
    unwrap_google_alert_redirect_url,
)

SCHEME_HTTPS = "https" + "://"
SCHEME_HTTP = "http" + "://"


class GoogleAlertsTriggerAndWorkerSearchQueueTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 60-profile benchmarks, and 4 known-wrong controls."""

    def test_sixty_google_alert_profiles_across_six_domains(self) -> None:
        self.assertEqual(len(ALL_6_ALERT_DOMAINS), 6)
        self.assertEqual(len(ALL_60_GOOGLE_ALERT_PROFILES), 60)
        by_domain: dict[str, int] = {d: 0 for d in ALL_6_ALERT_DOMAINS}
        for prof in ALL_60_GOOGLE_ALERT_PROFILES:
            by_domain[prof.domain_id] += 1
            self.assertTrue(prof.inbound_mailbox_baltor.startswith("alerts+"))
            self.assertTrue(prof.inbound_mailbox_baltor.endswith("@baltor.ai"))
            self.assertTrue(prof.inbound_mailbox_agentfeeds.endswith("@agentfeeds.si"))
            self.assertIn(prof.target_priority_queue, ALL_4_PRIORITY_WORKER_QUEUES)
        for domain_id, count in by_domain.items():
            self.assertEqual(count, 10, f"Expected 10 profiles for {domain_id}")

    def test_redirect_unwrapper_simhash_and_ssrf_detector(self) -> None:
        wrapped = (
            f"{SCHEME_HTTPS}www.google.com/url?rct=j&sa=t"
            f"&url={SCHEME_HTTPS}github.com/org/mcp-server%3Futm_source%3Dga%26fbclid%3D123%26tab%3Dreadme"
            "&ct=ga&cd=CAEYAA&usg=AFQjCNG"
        )
        canonical, was_unwrapped = unwrap_google_alert_redirect_url(wrapped)
        self.assertTrue(was_unwrapped)
        self.assertEqual(canonical, f"{SCHEME_HTTPS}github.com/org/mcp-server?tab=readme")

        h1 = compute_simhash_64(
            "Qwen 3.5 open weights released with GGUF quantization kernel and full reasoning benchmark evaluation results"
        )
        h2 = compute_simhash_64(
            "Qwen 3.5 open weights released with GGUF quantization kernels and full reasoning benchmark evaluation result"
        )
        h3 = compute_simhash_64("FTC 16 CFR Part 255 civil penalty update for testimonial disclosures")
        self.assertLessEqual(simhash_hamming_distance(h1, h2), 6)
        self.assertGreater(simhash_hamming_distance(h1, h3), 12)

        self.assertTrue(is_private_or_ssrf_target_url(f"{SCHEME_HTTP}127.0.0.1:8080/admin"))
        self.assertTrue(is_private_or_ssrf_target_url(f"{SCHEME_HTTP}169.254.169.254/latest/meta-data"))
        self.assertTrue(is_private_or_ssrf_target_url(f"{SCHEME_HTTP}10.12.0.5/internal"))
        self.assertFalse(is_private_or_ssrf_target_url(f"{SCHEME_HTTPS}github.com/baltor/engine"))

    def test_priority_worker_search_queue_routing_and_slas(self) -> None:
        domain_expected_queue = {
            DOMAIN_A04_CVE_SECURITY_ADVISORIES: QUEUE_P0_URGENT_CVE_AND_POLICY_RECHECK,
            DOMAIN_A05_VOLATILE_LAWS_POLICIES_PRICING: QUEUE_P0_URGENT_CVE_AND_POLICY_RECHECK,
            DOMAIN_A01_FRONTIER_MODELS: QUEUE_P1_CODE_REPO_AND_MODEL_CARD_SYNTHESIS,
            DOMAIN_A02_GITHUB_REPOS_MCP_CLI: QUEUE_P1_CODE_REPO_AND_MODEL_CARD_SYNTHESIS,
            DOMAIN_A03_SANDBOX_NERFS_WORKAROUNDS: QUEUE_P2_TOOL_NERF_AND_WORKAROUND_SYNTHESIS,
            DOMAIN_A06_RISING_CREATORS_INDIE_DEMOS: QUEUE_P3_RISING_CREATOR_AND_DEEP_TOPIC_EXPANSION,
        }
        for prof in ALL_60_GOOGLE_ALERT_PROFILES[::10]:
            res = invoke_worker_search_queue_slot({"profile_id": prof.profile_id})
            self.assertTrue(res.accepted)
            self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
            q_rep = res.output["queue_report"]
            self.assertEqual(q_rep["priority_queue"], domain_expected_queue[prof.domain_id])
            self.assertEqual(q_rep["mem_max_mb"], 3072)
            self.assertGreaterEqual(q_rep["enqueued_and_completed_count"], 2)
            for job in q_rep["jobs"]:
                self.assertTrue(job["within_sla"])
                self.assertEqual(len(job["job_dedup_sha256"]), 64)
                self.assertEqual(len(job["sacp_receipt_sha256"]), 64)

    def test_thin_component_adapter_contract_receipt_and_hot_swap(self) -> None:
        c1 = GOOGLE_ALERTS_INGESTION_ADAPTER.inspect_contract()
        c2 = WORKER_SEARCH_QUEUE_ADAPTER.inspect_contract()
        self.assertEqual(c1["slot_id"], SLOT_GOOGLE_ALERTS_RSS_AND_EMAIL_TRIGGER_INGESTION)
        self.assertEqual(c2["slot_id"], SLOT_ALERT_TRIGGERED_WORKER_SEARCH_WORK_QUEUE)
        self.assertLess(c1["loc"], 30)
        self.assertLess(c2["loc"], 30)

        r1 = invoke_google_alerts_ingestion_slot({"profile_id": ALL_60_GOOGLE_ALERT_PROFILES[0].profile_id})
        self.assertTrue(GOOGLE_ALERTS_INGESTION_ADAPTER.verify_receipt(r1))

        swapped_s1 = GOOGLE_ALERTS_INGESTION_ADAPTER.swap_engine(
            ENGINE_GOOGLE_ALERT_REDIRECT_UNWRAPPER_AND_SIMHASH_DEDUPLICATOR
        )
        self.assertEqual(
            swapped_s1.engine_order[0],
            ENGINE_GOOGLE_ALERT_REDIRECT_UNWRAPPER_AND_SIMHASH_DEDUPLICATOR,
        )
        swapped_s2 = WORKER_SEARCH_QUEUE_ADAPTER.swap_engine(
            ENGINE_DEEP_SEARCH_MULTI_HOP_WORKER_HARVESTER
        )
        self.assertEqual(swapped_s2.engine_order[0], ENGINE_DEEP_SEARCH_MULTI_HOP_WORKER_HARVESTER)
        self.assertTrue(GOOGLE_ALERTS_INGESTION_ADAPTER.preflight({}).ready)
        self.assertTrue(WORKER_SEARCH_QUEUE_ADAPTER.preflight({}).ready)

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "alert_target_ssrf_private_ip_blocked": "alert_target_ssrf_private_ip_refused",
            "duplicate_alert_worker_job_blocked": "duplicate_alert_worker_job_refused",
            "unbounded_worker_queue_job_blocked": "unbounded_worker_queue_job_refused",
            "low_signal_seo_spam_alert_blocked": "low_signal_seo_spam_alert_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_60_profile_2400_to_140_benchmark_suite(self) -> None:
        report = evaluate_google_alerts_trigger_and_worker_search_queue_suite()
        self.assertEqual(report["profile_count"], 60)
        self.assertEqual(report["domain_count"], 6)
        self.assertEqual(report["priority_queue_count"], 4)
        self.assertEqual(report["total_raw_daily_notifications"], 2400)
        self.assertEqual(report["total_canonical_worker_jobs"], 140)
        self.assertEqual(report["duplicate_and_syndication_noise_eliminated_pct"], 94.2)
        self.assertTrue(report["all_profiles_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_UNFILTERED_POLL_EVERYTHING_OR_MANUAL_SEARCH_BASELINE]
        suite = report["benchmarks"][
            ENGINE_BALTOR_GOOGLE_ALERTS_TRIGGER_AND_PRIORITY_WORKER_QUEUE_SUITE
        ]
        self.assertEqual(base["wasted_worker_compute_on_clones_pct"], 68.0)
        self.assertEqual(base["discovery_lag_hours"], 4.5)
        self.assertEqual(suite["canonical_deduplicated_worker_jobs"], 140)
        self.assertEqual(suite["batch_deduplication_latency_ms"], 11.4)
        self.assertEqual(suite["duplicate_and_syndication_noise_eliminated_pct"], 94.2)
        self.assertEqual(suite["google_redirect_unwrap_rate_pct"], 100.0)
        self.assertLess(suite["p0_critical_turnaround_seconds"], 18.0)
        self.assertEqual(suite["idempotent_queue_lease_completion_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()

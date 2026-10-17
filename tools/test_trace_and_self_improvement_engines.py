"""Tests and known-wrong controls for the 4-slot, 12-engine trace and self-improvement suite."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeError,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_TRACKING,
    enter_nested,
    root_frame,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    journal_intent,
    request_identity_digest,
)
from loop_engine.core.service_runtime.feedback import (  # noqa: E402
    GAP_SCHEMA,
    RATING_SCHEMA,
    REQUEST_SCHEMA,
)
from loop_engine.core.service_runtime.observability import (  # noqa: E402
    FAILURE_RECORD_VERSION,
    new_request_reference,
)
from trace_and_self_improvement_engines import (  # noqa: E402
    ALL_SLOTS,
    BASELINE_ENVELOPE_GAP_CLOSURE,
    CLOUD_SYNC_REQUEST_VERSION,
    DIAGNOSTIC_BUNDLE_VERSION,
    FRONTEND_REQUEST_VERSION,
    FUNNEL_COUNTER_VERSION,
    LOCAL_TRACE_REQUEST_VERSION,
    SELF_IMPROVEMENT_REQUEST_VERSION,
    SLOT_CLOUD_TRACE_SYNC,
    SLOT_FRONTEND_TRACE,
    SLOT_LOCAL_TRACE_STORE,
    SLOT_SELF_IMPROVEMENT,
    SecretAndPiiScrubber,
    create_cloud_trace_sync_envelope,
    create_frontend_trace_envelope,
    create_local_trace_store_envelope,
    create_self_improvement_envelope,
    run_all_benchmarks,
    self_test,
)


class SlotFamilyAFrontendTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope, self.ctx = create_frontend_trace_envelope(max_ring_events=4)
        self.checks = self.ctx["extra_checks"]

    def test_in_tab_session_ring_buffer_tracks_funnel_refusals_and_frustration_with_zero_cookies(self) -> None:
        ref = new_request_reference().value
        events = [
            {"event_kind": "setup_recipe_selected", "harness_id": "opencode", "recipe_id": "mcp_stdio"},
            {"event_kind": "connection_check", "latency_ms": 18.5, "status": "connected"},
            {"event_kind": "funnel_step", "stage": "search", "mode": "lexical", "hit_count": 5, "latency_ms": 9.1},
            {"event_kind": "refusal_encountered", "request_reference": ref, "route": "/api/v1/provisioning"},
            {
                "event_kind": "frustration_signal",
                "signal_kind": "rage_click",
                "target_control": "copy_token",
                "click_count": 5,
                "window_ms": 420.0,
            },
        ]
        last = None
        for ev in events:
            last = self.envelope.execute(
                {
                    "record_type": FRONTEND_REQUEST_VERSION,
                    "preferred_engines": ("in_tab_session_ring_buffer",),
                    "payload": ev,
                },
                extra_preflight_checks=self.checks,
            )
            self.assertTrue(last.ok)
        assert last is not None and last.result is not None
        # Max ring size is 4, so the oldest event was evicted deterministically
        self.assertEqual(last.result["buffered_events"], 4)
        self.assertEqual(last.result["cookies_set"], 0)
        self.assertFalse(last.result["third_party_analytics_loaded"])
        self.assertEqual(last.result["refusal_references"], [ref])
        self.assertEqual(last.result["frustration_signals"], 1)

    def test_known_wrong_cookie_or_third_party_tracker_is_refused(self) -> None:
        outcome = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("in_tab_session_ring_buffer",),
                "payload": {
                    "event_kind": "funnel_step",
                    "cookies": {"_ga": "GA1.2.123"},
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.trace["refused_by"], LAYER_PREFLIGHT)
        self.assertFalse(outcome.trace["engine_dispatched"])
        self.assertEqual(outcome.refusal["code"], "cookie_or_third_party_tracker_forbidden")

    def test_known_wrong_unissued_refusal_reference_is_refused(self) -> None:
        outcome = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("in_tab_session_ring_buffer",),
                "payload": {
                    "event_kind": "refusal_encountered",
                    "request_reference": "ref_not_valid_base32_0189!",
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.refusal["code"], "invalid_refusal_reference")

    def test_aggregate_funnel_step_counter_matches_search_gap_and_refuses_raw_query_text(self) -> None:
        ok_out = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("aggregate_funnel_step_counter",),
                "payload": {
                    "stage": "search",
                    "mode": "lexical",
                    "hit_count": 0,
                    "filters": {"domain": {"equals": "robotics"}},
                    "library_tiers": ["free"],
                    "now_epoch": 1792191600.0,
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(ok_out.ok)
        self.assertEqual(ok_out.result["record_type"], FUNNEL_COUNTER_VERSION)
        self.assertEqual(ok_out.result["zero_hit_count"], 1)
        self.assertFalse(ok_out.result["retains_query_text"])

        # Known-wrong: passing raw query text to aggregate_funnel_step_counter is refused
        bad_out = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("aggregate_funnel_step_counter",),
                "payload": {
                    "stage": "search",
                    "mode": "lexical",
                    "hit_count": 0,
                    "query": "private customer unreleased product name",
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(bad_out.ok)
        self.assertEqual(bad_out.refusal["code"], "raw_query_text_forbidden_in_aggregate_gap")

    def test_voluntary_redacted_diagnostic_bundle_requires_opt_in_and_redacts_secrets_and_pii(self) -> None:
        # Known-wrong: opt_in=False is refused
        no_opt_in = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("voluntary_redacted_diagnostic_bundle",),
                "payload": {
                    "event_kind": "diagnostic_bundle",
                    "opt_in": False,
                    "note": "Please check my trace",
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(no_opt_in.ok)
        self.assertEqual(no_opt_in.refusal["code"], "voluntary_opt_in_required")

        # Positive with opt_in=True and automatic redaction
        ref = new_request_reference().value
        opted_in = self.envelope.execute(
            {
                "record_type": FRONTEND_REQUEST_VERSION,
                "preferred_engines": ("voluntary_redacted_diagnostic_bundle",),
                "secret_policy": "scrub",
                "payload": {
                    "event_kind": "diagnostic_bundle",
                    "opt_in": True,
                    "target_endpoint": "request_material",
                    "note": "Key baltor_live_abc123456789 failed for dev@company.io in /home/devuser/repo",
                    "refusal_references": [ref, "invalid_ref"],
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(opted_in.ok)
        bundle = opted_in.result
        self.assertEqual(bundle["record_type"], DIAGNOSTIC_BUNDLE_VERSION)
        self.assertGreaterEqual(bundle["redactions_applied"], 3)
        self.assertNotIn("baltor_live_abc123456789", bundle["note"])
        self.assertNotIn("dev@company.io", bundle["note"])
        self.assertNotIn("/home/devuser", bundle["note"])
        self.assertEqual(bundle["refusal_references"], [ref])


class SlotFamilyBLocalTraceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_slot_b_"))
        self.envelope, self.ctx = create_local_trace_store_envelope(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_known_wrong_secret_and_pii_scrubber_refuses_raw_keys_bearer_env_and_paths(self) -> None:
        samples = [
            {"leaked": "baltor_secret_key_9988776655"},
            {"leaked": "sk-proj-1234567890abcdefghijklmnop"},
            {"leaked": "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"},
            {"leaked": "OPENAI_API_KEY=sk-live-secret99999999"},
            {"leaked": "Found error in /home/alice/.config/opencode/auth.json for alice@example.org"},
        ]
        for sample in samples:
            findings = SecretAndPiiScrubber.inspect(sample)
            self.assertTrue(findings, f"Expected scrubber finding for {sample}")
            outcome = self.envelope.execute(
                {
                    "record_type": LOCAL_TRACE_REQUEST_VERSION,
                    "secret_policy": "refuse",
                    "payload": {"run_id": "run-sec", "turn_index": 1, **sample},
                }
            )
            self.assertFalse(outcome.ok)
            self.assertEqual(outcome.trace["refused_by"], LAYER_PREFLIGHT)
            self.assertFalse(outcome.trace["engine_dispatched"])
            self.assertEqual(outcome.refusal["code"], "secret_or_pii_detected_in_trace")
        self.assertEqual(self.ctx["sqlite"].query_traces(), [])

    def test_preflight_scrubber_self_repair_scrubs_secrets_before_sqlite_wal_write(self) -> None:
        outcome = self.envelope.execute(
            {
                "record_type": LOCAL_TRACE_REQUEST_VERSION,
                "secret_policy": "scrub",
                "payload": {
                    "run_id": "run-scrubbed",
                    "turn_index": 1,
                    "harness_id": "opencode with baltor_tok_1234567890",
                    "model": "gemma4:31b",
                    "router_decision": {
                        "route_selected": "lsh_fast_path",
                        "lsh_bucket": "bucket_07",
                        "jev_score": 0.92,
                        "candidates_considered": 8,
                    },
                    "mcp_spans": [
                        {"tool_name": "search", "latency_ms": 7.5, "status": "ok", "hit_count": 2},
                        {"tool_name": "inspect", "latency_ms": 4.2, "status": "ok", "selected_id": "card_1"},
                        {"tool_name": "download", "latency_ms": 12.0, "status": "ok", "selected_id": "card_1"},
                    ],
                    "prompt_tokens": 980,
                    "eval_tokens": 220,
                    "latency_ms": 340.0,
                    "acceptance": {"kept_in_worktree": True, "tests_passed": True},
                },
            }
        )
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.selected_engine, "local_sqlite_wal_trace_store")
        self.assertEqual(outcome.preflight[0]["verdict"], "repaired")
        self.assertGreaterEqual(outcome.redactions_applied, 1)
        stored = self.ctx["sqlite"].query_traces(run_id="run-scrubbed")
        self.assertEqual(len(stored), 1)
        self.assertNotIn("baltor_tok_1234567890", stored[0]["harness_id"])
        self.assertEqual(outcome.result["journal_mode"], "wal")

    def test_transient_lock_recovers_and_persistent_lock_falls_back_to_jsonl_and_memory(self) -> None:
        # 1. Transient SQLite lock recovers on the same engine via RecoveryAllowance
        recovered = self.envelope.execute(
            {
                "record_type": LOCAL_TRACE_REQUEST_VERSION,
                "payload": {
                    "simulate_sqlite_locked": True,
                    "persistent_sqlite_lock": False,
                    "run_id": "run-transient",
                    "turn_index": 1,
                },
            }
        )
        self.assertTrue(recovered.ok)
        self.assertEqual(recovered.selected_engine, "local_sqlite_wal_trace_store")
        self.assertEqual(recovered.frame["remaining_automatic_attempts"], 2)

        # 2. Persistent SQLite lock falls back to `local_jsonl_ring_spool`
        fallback_jsonl = self.envelope.execute(
            {
                "record_type": LOCAL_TRACE_REQUEST_VERSION,
                "payload": {
                    "simulate_sqlite_locked": True,
                    "persistent_sqlite_lock": True,
                    "run_id": "run-jsonl",
                    "turn_index": 1,
                },
            }
        )
        self.assertTrue(fallback_jsonl.ok)
        self.assertEqual(fallback_jsonl.selected_engine, "local_jsonl_ring_spool")
        self.assertEqual(
            fallback_jsonl.fallback_chain_tried,
            ("local_sqlite_wal_trace_store", "local_jsonl_ring_spool"),
        )

        # 3. When filesystem authority is not granted (`("pure",)`), handshake selects `in_memory_ephemeral_trace_buffer`
        mem_only = self.envelope.execute(
            {
                "record_type": LOCAL_TRACE_REQUEST_VERSION,
                "payload": {"run_id": "run-mem", "turn_index": 1},
            },
            granted_effects=("pure",),
        )
        self.assertTrue(mem_only.ok)
        self.assertEqual(mem_only.selected_engine, "in_memory_ephemeral_trace_buffer")


class SlotFamilyCCloudTraceSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_slot_c_"))
        self.envelope, self.ctx = create_cloud_trace_sync_envelope(self.temp_dir)
        self.checks = self.ctx["extra_checks"]

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cloud_batch_digest_exporter_compresses_deduplicates_and_replays_from_journal(self) -> None:
        traces = [
            {"trace_digest": "1" * 64, "run_id": "r1", "turn_index": 1, "model": "gemma4:31b"},
            {"trace_digest": "2" * 64, "run_id": "r1", "turn_index": 2, "model": "gemma4:31b"},
            {"trace_digest": "1" * 64, "run_id": "r1", "turn_index": 1, "model": "gemma4:31b"},
        ]
        first = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "request_id": "sync-batch-001",
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"traces": traces},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(first.ok)
        self.assertEqual(first.selected_engine, "cloud_batch_digest_exporter")
        self.assertEqual(first.result["submitted_traces"], 3)
        self.assertEqual(first.result["uploaded_new_traces"], 2)
        self.assertEqual(first.result["deduplicated_skipped"], 1)

        # Sending the exact same request_id replays from Layer 5 tracking journal without re-running engine
        replayed = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "request_id": "sync-batch-001",
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"traces": traces},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(replayed.ok)
        self.assertTrue(replayed.result["replayed_from_journal"])
        self.assertFalse(replayed.trace["engine_dispatched"])
        self.assertEqual(replayed.trace["steps"][-1], {"layer": LAYER_TRACKING, "result": "answered"})

    def test_edge_worker_beacon_and_offline_circuit_breaker_failover_with_replay(self) -> None:
        traces = [
            {
                "trace_digest": "a" * 64,
                "router_decision": {"lsh_bucket": "bucket_12"},
                "mcp_spans": [{"tool_name": "search", "hit_count": 0}],
            }
        ]
        # Origin lock contention routes to `edge_worker_beacon_exporter`
        edge_out = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"simulate_origin_lock_contention": True, "traces": traces},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(edge_out.ok)
        self.assertEqual(edge_out.selected_engine, "edge_worker_beacon_exporter")
        self.assertEqual(edge_out.result["origin_sqlite_locks_acquired"], 0)
        self.assertEqual(edge_out.result["edge_lsh_misses"]["bucket_12"], 1)

        # Complete network outage routes to `offline_spool_with_circuit_breaker`
        offline_out = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"simulate_network_unreachable": True, "traces": traces},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(offline_out.ok)
        self.assertEqual(offline_out.selected_engine, "offline_spool_with_circuit_breaker")
        self.assertEqual(offline_out.result["circuit_state"], "open")
        self.assertGreater(offline_out.result["backoff_seconds"], 1.0)

        # Replay upon network recovery is idempotent
        replay_1 = self.ctx["spool"].replay_spooled(self.ctx["cloud"])
        replay_2 = self.ctx["spool"].replay_spooled(self.ctx["cloud"])
        self.assertEqual(replay_1["replayed_batches"], 1)
        self.assertEqual(replay_2["replayed_batches"], 0)
        self.assertEqual(replay_2["skipped_already_replayed"], 1)

    def test_known_wrong_account_and_budget_and_nested_cycle_refusals(self) -> None:
        # Unauthorized account refused at Layer 4
        unauth = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_alpha", "authorized": False},
                "payload": {"traces": []},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(unauth.ok)
        self.assertEqual(unauth.trace["refused_by"], LAYER_ACCOUNT)
        self.assertEqual(unauth.refusal["code"], "account_authority_missing")

        # Cloud byte budget exceeded refused at Layer 6
        over_budget = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"max_batch_bytes": 10, "traces": [{"trace_digest": "b" * 64}]},
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(over_budget.ok)
        self.assertEqual(over_budget.trace["refused_by"], LAYER_PREFLIGHT)
        self.assertEqual(over_budget.refusal["code"], "cloud_budget_exceeded")

        # Nested envelope frame from Slot B into Slot C succeeds, while a cycle raises EnvelopeError
        parent = root_frame(SLOT_LOCAL_TRACE_STORE)
        nested_ok = self.envelope.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_alpha", "authorized": True},
                "payload": {"traces": []},
            },
            parent_frame=parent,
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(nested_ok.ok)
        self.assertEqual(nested_ok.frame["path"], [SLOT_LOCAL_TRACE_STORE, SLOT_CLOUD_TRACE_SYNC])

        with self.assertRaises(EnvelopeError):
            enter_nested(
                enter_nested(parent, SLOT_CLOUD_TRACE_SYNC),
                SLOT_LOCAL_TRACE_STORE,
            )


class SlotFamilyDSelfImprovementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope, self.ctx = create_self_improvement_envelope()
        self.checks = self.ctx["extra_checks"]

    def test_four_stage_closed_loop_pipeline_and_canary_rollback(self) -> None:
        ref = new_request_reference().value
        # Stage 1 & 2a: Heuristic gap clustering joins feedback & observability & harness traces
        cluster_out = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("heuristic_gap_cluster_improver",),
                "payload": {
                    "producer_id": "loop.self_improvement.heuristic_cluster",
                    "signals": {
                        "search_gaps": [
                            {
                                "record_type": GAP_SCHEMA,
                                "hour": "2026-10-16T21Z",
                                "mode": "lexical",
                                "filters": {},
                                "library_tiers": ["free"],
                                "hit_count": 0,
                                "searches": 6,
                            }
                        ],
                        "material_requests": [
                            {
                                "record_type": REQUEST_SCHEMA,
                                "tenant_id": "t1",
                                "description": "Three.js postprocessing bloom shader",
                                "state": "open",
                            }
                        ],
                        "catalogue_ratings": [
                            {
                                "record_type": RATING_SCHEMA,
                                "item_identity": "broken_bloom_v0",
                                "value": "not_useful",
                            }
                        ],
                        "service_failures": [
                            {
                                "record_type": FAILURE_RECORD_VERSION,
                                "request_reference": ref,
                                "route": "/api/v1/provisioning",
                                "refusal_code": "rate_limit_exceeded",
                            }
                        ],
                        "harness_traces": [
                            {
                                "run_id": "run-101",
                                "router_decision": {"lsh_bucket": "bucket_09"},
                                "mcp_spans": [
                                    {"tool_name": "search", "hit_count": 0},
                                    {"tool_name": "search", "hit_count": 2},
                                ],
                                "acceptance": {"kept_in_worktree": True, "tests_passed": True},
                            }
                        ],
                    },
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(cluster_out.ok)
        self.assertEqual(cluster_out.result["commit_status"], "candidate_only")
        self.assertFalse(cluster_out.result["active_intelligence_updated"])
        classifications = {p["classification"] for p in cluster_out.result["proposals"]}
        self.assertEqual(classifications, {"ranking_miss", "alias_or_lsh_trigger_miss", "supply_gap"})

        # Stage 2b: LSH alias & query relaxation synthesizer
        synth_out = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("lsh_alias_and_query_relaxation_synthesizer",),
                "payload": {
                    "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                    "retry_trace_pairs": [
                        {
                            "failed_symbol_or_token": "TLRUCache expiration",
                            "succeeded_item_identity": "cachetools_tlru_cache",
                        }
                    ],
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(synth_out.ok)
        self.assertEqual(synth_out.result["rule_count"], 1)
        rule = synth_out.result["synthesized_rules"][0]
        self.assertIn("tlru", rule["subtoken_aliases"])
        self.assertTrue(rule["lsh_3gram_shingles"])

        # Stage 3 & 4: Independent Pareto verifier promotes zero-regression winner
        promote_out = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("harmony_pareto_verified_promoter",),
                "payload": {
                    "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                    "reviewer_id": "loop.verifier.independent_pareto",
                    "candidate_proposal": {"proposal_id": rule["rule_id"]},
                    "baseline_metrics": {
                        "relevance_mrr_at_5": 0.62,
                        "non_exact_query_recall": 0.50,
                        "latency_p95_ms": 40.0,
                        "token_cost_per_solve": 1400.0,
                    },
                    "candidate_metrics": {
                        "relevance_mrr_at_5": 0.79,
                        "non_exact_query_recall": 0.82,
                        "latency_p95_ms": 38.0,
                        "token_cost_per_solve": 1100.0,
                        "held_out_negative_transfer_regressions": 0,
                    },
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(promote_out.ok)
        self.assertTrue(promote_out.result["pareto_dominates"])
        self.assertTrue(promote_out.result["independent_review_verified"])
        self.assertEqual(promote_out.result["promotion_state"], "promoted_canary")
        self.assertFalse(promote_out.result["canary_rolled_back"])

        # Stage 4 automatic rollback when live canary degrades
        rollback_out = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("harmony_pareto_verified_promoter",),
                "payload": {
                    "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                    "reviewer_id": "loop.verifier.independent_pareto",
                    "candidate_proposal": {"proposal_id": rule["rule_id"]},
                    "baseline_metrics": {
                        "relevance_mrr_at_5": 0.62,
                        "non_exact_query_recall": 0.50,
                        "latency_p95_ms": 40.0,
                        "token_cost_per_solve": 1400.0,
                    },
                    "candidate_metrics": {
                        "relevance_mrr_at_5": 0.79,
                        "non_exact_query_recall": 0.82,
                        "latency_p95_ms": 38.0,
                        "token_cost_per_solve": 1100.0,
                        "held_out_negative_transfer_regressions": 0,
                    },
                    "canary_live_observation": {
                        "baseline_acceptance_rate": 0.85,
                        "live_acceptance_rate": 0.71,
                        "live_refusal_rate": 0.08,
                        "live_latency_p95_ms": 52.0,
                    },
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertTrue(rollback_out.ok)
        self.assertTrue(rollback_out.result["canary_rolled_back"])
        self.assertEqual(rollback_out.result["promotion_state"], "rolled_back_to_baseline")
        self.assertFalse(rollback_out.result["active_intelligence_updated"])

    def test_known_wrong_producer_self_approval_and_pareto_regression_are_refused(self) -> None:
        # 1. Self-approval (`producer_id == reviewer_id`) is refused before engine dispatch
        self_app = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("harmony_pareto_verified_promoter",),
                "payload": {
                    "producer_id": "loop.same_author",
                    "reviewer_id": "loop.same_author",
                    "baseline_metrics": {"relevance_mrr_at_5": 0.60},
                    "candidate_metrics": {"relevance_mrr_at_5": 0.75},
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(self_app.ok)
        self.assertEqual(self_app.trace["refused_by"], LAYER_PREFLIGHT)
        self.assertFalse(self_app.trace["engine_dispatched"])
        self.assertEqual(self_app.refusal["code"], "self_approval_refused")

        # 2. Candidate that improves recall but regresses latency p95 or negative transfer is refused
        regressed = self.envelope.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("harmony_pareto_verified_promoter",),
                "payload": {
                    "producer_id": "loop.producer.a",
                    "reviewer_id": "loop.verifier.b",
                    "baseline_metrics": {
                        "relevance_mrr_at_5": 0.65,
                        "non_exact_query_recall": 0.55,
                        "latency_p95_ms": 40.0,
                        "token_cost_per_solve": 1200.0,
                    },
                    "candidate_metrics": {
                        "relevance_mrr_at_5": 0.72,
                        "non_exact_query_recall": 0.68,
                        "latency_p95_ms": 55.0,
                        "token_cost_per_solve": 1200.0,
                        "held_out_negative_transfer_regressions": 1,
                    },
                },
            },
            extra_preflight_checks=self.checks,
        )
        self.assertFalse(regressed.ok)
        self.assertEqual(regressed.refusal["code"], "pareto_regression_refused")
        self.assertFalse(regressed.trace["engine_dispatched"])


class BenchmarkAndCoverageClosureTests(unittest.TestCase):
    def test_benchmarks_and_self_test_and_baseline_gap_closure(self) -> None:
        report = self_test()
        self.assertTrue(report["all_passed"], report["tests"])
        bench = run_all_benchmarks(iterations=15)
        self.assertEqual(set(bench["slots"]), set(ALL_SLOTS))
        for slot_id in ALL_SLOTS:
            self.assertEqual(len(bench["slots"][slot_id]), 3)
            self.assertTrue(bench["fallback_cascades"][slot_id]["ok"])

        for legacy_slot in ("runtime_memory", "run_history_export", "usage_export", "failure_journal"):
            entry = BASELINE_ENVELOPE_GAP_CLOSURE[legacy_slot]
            self.assertEqual(set(entry["target_with_envelope_suite"]), set(COVERAGE_LAYERS))
            for layer in COVERAGE_LAYERS:
                self.assertEqual(entry["target_with_envelope_suite"][layer], "full")


if __name__ == "__main__":
    unittest.main()

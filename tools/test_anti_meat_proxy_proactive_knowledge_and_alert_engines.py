"""Unit, conformance, benchmark, and adversarial known-wrong control tests for
`tools/anti_meat_proxy_proactive_knowledge_and_alert_engines.py`.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from anti_meat_proxy_proactive_knowledge_and_alert_engines import (  # noqa: E402
    AmbientWorkspaceSignal,
    AntiMeatProxyInstitutionalKnowledgeOrchestrator,
    BENCHMARK_30_ROLE_TASK_SCENARIOS,
    ECHELON_IDS,
    ENGINE_KNOWLEDGE_FALLBACK,
    ENGINE_PROACTIVE_ALERT_FALLBACK,
    IncomingFeedEvent,
    InstitutionalKnowledgeRequest,
    KNOWLEDGE_ORGANIZER_ENGINE_ORDER,
    KnowledgeCandidateUnit,
    MAX_DISTILLED_CONTRACT_CARD_TOKENS,
    PROACTIVE_ALERT_ENGINE_ORDER,
    ProactiveRetrievalAndAlertRequest,
    UNIVERSAL_8_ORGANIZATIONAL_ECHELONS,
    ZeroRelearningProactiveAlertOrchestrator,
    compute_multi_factor_rank_score,
    run_anti_meat_proxy_benchmark,
)


class AntiMeatProxyProactiveKnowledgeAndAlertTests(unittest.TestCase):
    """Verify both 7-layer slot families, 8 echelons, 7 engines, 30 scenarios, and 4 known-wrong controls."""

    def _sample_candidates(self) -> tuple[KnowledgeCandidateUnit, ...]:
        return (
            KnowledgeCandidateUnit(
                unit_id="UNIT-HIGH-01",
                title="ISO-20022 Ledger Cutover & Idempotency Contract",
                source_corpus="baltor_verified_corpus/fintech_ledger",
                raw_source_tokens=6200,
                lsh_similarity=0.97,
                verification_tier=1.00,
                freshness_decay=0.98,
                failure_prevention_value=0.99,
                distilled_card_tokens=155,
                invariant_contract="enforce_iso20022_idempotent_settlement_v1",
                verifier_command="python3 -m unittest tools/verify_iso20022_settlement.py",
                ast_span_target="src/loop_engine/ledger/settlement.py#L10-L95",
                slo_threshold="p99_settlement_ms <= 5.0 and duplicate_tx == 0",
                rollback_trigger="rollback_on_settlement_checksum_mismatch",
            ),
            KnowledgeCandidateUnit(
                unit_id="UNIT-MED-02",
                title="Legacy Clearing House Batch Reference",
                source_corpus="standards_rfc_archive/clearing_v2",
                raw_source_tokens=4800,
                lsh_similarity=0.72,
                verification_tier=0.88,
                freshness_decay=0.80,
                failure_prevention_value=0.75,
                distilled_card_tokens=185,
                invariant_contract="enforce_batch_window_cutoff_v1",
                verifier_command="python3 -m unittest tools/verify_batch_window.py",
                ast_span_target="src/loop_engine/ledger/batch.py#L1-L60",
                slo_threshold="batch_drift_sec <= 1.0",
                rollback_trigger="rollback_on_batch_timeout",
            ),
        )

    def test_slot1_organizes_ranks_distills_and_bridges_across_8_echelons_and_4_engines(self) -> None:
        self.assertEqual(len(UNIVERSAL_8_ORGANIZATIONAL_ECHELONS), 8)
        organizer = AntiMeatProxyInstitutionalKnowledgeOrchestrator()
        candidates = self._sample_candidates()

        high_score = compute_multi_factor_rank_score(candidates[0])
        low_score = compute_multi_factor_rank_score(candidates[1])
        self.assertGreater(high_score, low_score)

        for echelon_id in ECHELON_IDS:
            for engine_id in KNOWLEDGE_ORGANIZER_ENGINE_ORDER:
                res = organizer.handle(
                    InstitutionalKnowledgeRequest(
                        schema="anti_meat_proxy_institutional_knowledge_request/v1",
                        job_position_echelon=echelon_id,
                        active_task="Staff Engineer ISO-20022 Ledger Cutover",
                        skill_domain="payment_clearing_messaging",
                        initiative_stage="production_cutover",
                        candidates=candidates,
                        preferred_engine=engine_id,
                    )
                )
                self.assertTrue(res.accepted)
                self.assertEqual(res.selected_engine, engine_id)
                self.assertFalse(res.fallback_used)
                self.assertEqual(res.echelon_id, echelon_id)
                self.assertEqual(res.ranked_cards[0].unit_id, "UNIT-HIGH-01")
                self.assertLess(res.max_card_tokens, MAX_DISTILLED_CONTRACT_CARD_TOKENS)
                self.assertIsNotNone(res.cross_role_bridge)
                assert res.cross_role_bridge is not None
                self.assertEqual(len(res.cross_role_bridge.vp_executive_brief), 3)
                self.assertIn("ast_span", res.cross_role_bridge.senior_engineer_projection)
                self.assertIn("invariant_contract", res.cross_role_bridge.senior_engineer_projection)
                self.assertIn("verifier_command", res.cross_role_bridge.senior_engineer_projection)
                self.assertIn("slo_threshold", res.cross_role_bridge.autonomous_monitor_projection)
                self.assertIn("rollback_trigger", res.cross_role_bridge.autonomous_monitor_projection)
                self.assertIn("alert_payload", res.cross_role_bridge.autonomous_monitor_projection)
                self.assertEqual(res.nested_frame_depth, 1)

        fallback_res = organizer.handle(
            InstitutionalKnowledgeRequest(
                schema="anti_meat_proxy_institutional_knowledge_request/v1",
                job_position_echelon="principal_staff_architect",
                active_task="Staff Engineer ISO-20022 Ledger Cutover",
                skill_domain="payment_clearing_messaging",
                initiative_stage="production_cutover",
                candidates=candidates,
                preferred_engine="unknown_experimental_ranker",
            )
        )
        self.assertTrue(fallback_res.accepted)
        self.assertTrue(fallback_res.fallback_used)
        self.assertEqual(fallback_res.selected_engine, ENGINE_KNOWLEDGE_FALLBACK)

    def test_slot2_proactive_retrieval_and_zero_noise_alert_across_engines(self) -> None:
        proactive = ZeroRelearningProactiveAlertOrchestrator()
        candidates = self._sample_candidates()
        k_req = InstitutionalKnowledgeRequest(
            schema="anti_meat_proxy_institutional_knowledge_request/v1",
            job_position_echelon="sre_secops_oncall_monitor",
            active_task="On-Call SRE SQLite WAL Lock Spike",
            skill_domain="embedded_storage_reliability",
            initiative_stage="incident_mitigation",
            candidates=candidates,
        )
        signal = AmbientWorkspaceSignal(
            git_diff_paths=("src/loop_engine/storage/sqlite_wal.py",),
            imported_modules=("sqlite3", "loop_engine.core.engines.envelope"),
            file_extensions=(".py", ".sql"),
            recent_error_log_codes=("SQLITE_BUSY_SNAPSHOT",),
            active_initiative_id="init_sqlite_wal",
            hardware_profile="linux_x86_64_3gb_capped",
        )
        events = (
            IncomingFeedEvent(
                event_id="EV-CVE-WAL-01",
                feed_channel="agentfeeds.si",
                event_category="wal_checkpoint_starvation_alert",
                summary="High-concurrency WAL reader starvation under long read transactions",
                affected_initiative_id="init_sqlite_wal",
                impact_score=0.95,
                pre_built_repair_component_id="comp_sqlite_wal_autocheckpoint_guard",
                pre_built_repair_patch_cmd="python3 tools/apply_repair.py --id comp_sqlite_wal_autocheckpoint_guard",
            ),
            IncomingFeedEvent(
                event_id="EV-LOW-NOISE-02",
                feed_channel="agentfeeds.si",
                event_category="cosmetic_changelog_note",
                summary="Minor formatting update in unrelated docs",
                affected_initiative_id="init_sqlite_wal",
                impact_score=0.22,
                pre_built_repair_component_id="noop",
                pre_built_repair_patch_cmd="true",
            ),
        )

        for engine_id in PROACTIVE_ALERT_ENGINE_ORDER:
            res = proactive.handle(
                ProactiveRetrievalAndAlertRequest(
                    schema="zero_relearning_proactive_alert_request/v1",
                    echelon_id="sre_secops_oncall_monitor",
                    workspace_signal=signal,
                    knowledge_request=k_req,
                    incoming_events=events,
                    alert_threshold=0.70,
                    preferred_engine=engine_id,
                )
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.bound_triad_pack_files, ("AGENTS.md", "RULES.md", "MEMORY.md"))
            self.assertEqual(len(res.actionable_alerts), 1)
            self.assertEqual(res.actionable_alerts[0].repair_component_id, "comp_sqlite_wal_autocheckpoint_guard")
            self.assertEqual(res.suppressed_low_impact_count, 1)

        fallback_res = proactive.handle(
            ProactiveRetrievalAndAlertRequest(
                schema="zero_relearning_proactive_alert_request/v1",
                echelon_id="sre_secops_oncall_monitor",
                workspace_signal=signal,
                knowledge_request=k_req,
                incoming_events=events,
                preferred_engine="nonexistent_proactive_engine",
            )
        )
        self.assertTrue(fallback_res.accepted)
        self.assertTrue(fallback_res.fallback_used)
        self.assertEqual(fallback_res.selected_engine, ENGINE_PROACTIVE_ALERT_FALLBACK)

    def test_known_wrong_controls_block_scrape_alert_fatigue_cross_tenant_and_manual_copy_paste(self) -> None:
        organizer = AntiMeatProxyInstitutionalKnowledgeOrchestrator()
        proactive = ZeroRelearningProactiveAlertOrchestrator(knowledge_orchestrator=organizer)
        candidates = self._sample_candidates()

        # 1. Block raw unverified internet scrape injection without independent vetting
        bad_scrape = organizer.handle(
            InstitutionalKnowledgeRequest(
                schema="anti_meat_proxy_institutional_knowledge_request/v1",
                job_position_echelon="senior_software_ml_data_engineer",
                active_task="ML Engineer Time-Series Covariate Audit",
                skill_domain="timeseries_forecasting_rigor",
                initiative_stage="audit",
                candidates=candidates,
                raw_unverified_internet_scrape=True,
            )
        )
        self.assertFalse(bad_scrape.accepted)
        self.assertIsNotNone(bad_scrape.refusal)
        assert bad_scrape.refusal is not None
        self.assertEqual(bad_scrape.refusal.code, "unverified_raw_internet_scrape_refused")

        # 2. Block alert fatigue spam where impact_score < alert_threshold
        valid_k_req = InstitutionalKnowledgeRequest(
            schema="anti_meat_proxy_institutional_knowledge_request/v1",
            job_position_echelon="sre_secops_oncall_monitor",
            active_task="On-Call SRE SQLite WAL Lock Spike",
            skill_domain="embedded_storage_reliability",
            initiative_stage="monitoring",
            candidates=candidates,
        )
        bad_alert_spam = proactive.handle(
            ProactiveRetrievalAndAlertRequest(
                schema="zero_relearning_proactive_alert_request/v1",
                echelon_id="sre_secops_oncall_monitor",
                workspace_signal=AmbientWorkspaceSignal(
                    git_diff_paths=(),
                    imported_modules=(),
                    file_extensions=(".py",),
                    recent_error_log_codes=(),
                    active_initiative_id="init_sqlite_wal",
                    hardware_profile="cpu",
                ),
                knowledge_request=valid_k_req,
                incoming_events=(
                    IncomingFeedEvent(
                        event_id="EV-SPAM-01",
                        feed_channel="agentfeeds.si",
                        event_category="low_priority_chatter",
                        summary="Low impact chatter below threshold",
                        affected_initiative_id="init_sqlite_wal",
                        impact_score=0.25,
                        pre_built_repair_component_id="noop",
                        pre_built_repair_patch_cmd="true",
                    ),
                ),
                alert_threshold=0.75,
                force_emit_low_impact_alert=True,
            )
        )
        self.assertFalse(bad_alert_spam.accepted)
        self.assertIsNotNone(bad_alert_spam.refusal)
        assert bad_alert_spam.refusal is not None
        self.assertEqual(bad_alert_spam.refusal.code, "alert_fatigue_below_impact_threshold_refused")

        # 3. Block cross-tenant institutional memory leakage
        bad_tenant = organizer.handle(
            InstitutionalKnowledgeRequest(
                schema="anti_meat_proxy_institutional_knowledge_request/v1",
                job_position_echelon="financial_legal_compliance_officer",
                active_task="Compliance Officer HIPAA Safe-Harbor Scrub",
                skill_domain="clinical_privacy_deidentification",
                initiative_stage="audit",
                candidates=candidates,
                requester_tenant_id="tenant_external_alpha",
                knowledge_owner_tenant_id="tenant_hospital_beta",
            )
        )
        self.assertFalse(bad_tenant.accepted)
        self.assertIsNotNone(bad_tenant.refusal)
        assert bad_tenant.refusal is not None
        self.assertEqual(bad_tenant.refusal.code, "cross_tenant_memory_leakage_refused")

        # 4. Block requiring human manual doc copy-paste when a verified Contract Card exists
        bad_meat_proxy = organizer.handle(
            InstitutionalKnowledgeRequest(
                schema="anti_meat_proxy_institutional_knowledge_request/v1",
                job_position_echelon="vp_executive_leadership",
                active_task="VP Cloud Migration Review",
                skill_domain="cloud_finops_governance",
                initiative_stage="review",
                candidates=candidates,
                require_human_manual_doc_copy_paste=True,
                verified_contract_card_exists=True,
            )
        )
        self.assertFalse(bad_meat_proxy.accepted)
        self.assertIsNotNone(bad_meat_proxy.refusal)
        assert bad_meat_proxy.refusal is not None
        self.assertEqual(bad_meat_proxy.refusal.code, "human_meat_proxy_manual_copy_paste_refused")

    def test_30_scenario_benchmark_eliminates_human_meat_proxy_tax(self) -> None:
        self.assertEqual(len(BENCHMARK_30_ROLE_TASK_SCENARIOS), 30)
        report = run_anti_meat_proxy_benchmark()
        self.assertEqual(report["scenarios_evaluated"], 30)
        self.assertEqual(report["organizational_echelons_covered"], 8)
        for scenario_row in report["scenario_results"]:
            self.assertTrue(scenario_row["accepted"])
            self.assertEqual(scenario_row["card_tokens"], 480)
            self.assertEqual(scenario_row["actionable_alerts_emitted"], 1)
            self.assertEqual(scenario_row["low_impact_noise_suppressed"], 1)

        strategies = {s["strategy_id"]: s for s in report["strategies"]}
        baseline = strategies["human_meat_proxy_manual_doc_pasting_without_baltor"]
        baltor = strategies["baltor_zero_meat_proxy_proactive_knowledge_system"]

        self.assertEqual(baseline["human_doc_hunting_pasting_minutes_per_task"], 42.5)
        self.assertEqual(baseline["mean_prompt_tokens"], 14800)
        self.assertEqual(baseline["first_pass_accuracy_pct"], 53.3)
        self.assertEqual(baseline["stale_knowledge_error_rate_pct"], 38.0)

        self.assertEqual(baltor["human_doc_hunting_pasting_minutes_per_task"], 0.0)
        self.assertEqual(baltor["automatic_retrieval_latency_ms"], 1.4)
        self.assertEqual(baltor["mean_card_tokens"], 480)
        self.assertEqual(baltor["first_pass_accuracy_pct"], 98.3)
        self.assertEqual(baltor["breaking_change_alert_precision_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()

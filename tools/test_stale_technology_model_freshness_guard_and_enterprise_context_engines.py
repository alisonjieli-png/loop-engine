"""Tests for Baltor 120-Rule Stale-Technology/Model Freshness Guard & Federated Enterprise BYOC Suite."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.sovereign_open_model_unrestricted_paired_computer_use_engines import (
    build_sovereign_router_envelopes,
    catalog_open_weight_model_backends,
)
from tools.stale_technology_model_freshness_guard_and_enterprise_context_engines import (
    build_enterprise_context_bridge_envelopes,
    build_freshness_guard_envelopes,
    build_valid_tenant_context_lease,
    catalog_enterprise_byoc_connectors,
    catalog_one_hundred_twenty_freshness_rules,
    evaluate_known_wrong_controls,
    intercept_and_upgrade_stale_technology,
    merge_federated_enterprise_context,
    run_forty_scenario_freshness_and_enterprise_byoc_benchmark,
)


class StaleTechModelFreshnessGuardAndEnterpriseContextTests(unittest.TestCase):
    """Verify Slot Family 1 (120-rule freshness guard), Slot Family 2 (8 BYOC connectors), benchmark & controls."""

    def test_one_hundred_twenty_freshness_rules_across_six_categories(self) -> None:
        rules = catalog_one_hundred_twenty_freshness_rules()
        self.assertEqual(len(rules), 120)
        expected_categories = {
            "F01_open_weight_model_currency_rules",
            "F02_commercial_frontier_model_currency_rules",
            "F03_agent_protocol_and_harness_currency_rules",
            "F04_python_rust_and_data_stack_currency_rules",
            "F05_web_frontend_and_cloud_infra_currency_rules",
            "F06_benchmark_and_evaluation_currency_rules",
        }
        counts = {cat: 0 for cat in expected_categories}
        for rule in rules:
            self.assertIn(rule.category_id, counts)
            counts[rule.category_id] += 1
            self.assertEqual(rule.feed_channel, "agentfeeds.si/freshness")
            self.assertLess(rule.contract_card_tokens, 200)
        for cat, count in counts.items():
            self.assertEqual(count, 20, msg=cat)

    def test_slot_family_1_realtime_interception_auto_upgrade_and_contract_card(self) -> None:
        envelopes = build_freshness_guard_envelopes()
        self.assertEqual(
            set(envelopes.keys()),
            {
                "outdated_model_and_token_interceptor_engine",
                "stale_library_and_protocol_auto_upgrader_engine",
                "agentfeeds_si_live_freshness_feed_emitter_engine",
                "current_stack_2026_contract_card_and_rules_generator_engine",
            },
        )
        stale_input = (
            "Run Qwen 2.5 and Qwen2.5-VL with Gemma 3, Llama 3.3, DeepSeek V2.5, GLM-4, Kimi 1.5, "
            "Mistral 7B v0.1, Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro over HTTP+SSE MCP (2024-11-05) "
            "and OpenAI Assistants API using pydantic v1 .dict(), datetime.utcnow(), pandas .append(), "
            "create-react-app, Docker Compose v1, and evaluate on HumanEval-only and GSM8K-only."
        )
        res = intercept_and_upgrade_stale_technology(stale_input)
        self.assertEqual(res.status, "upgraded")
        self.assertLess(res.interception_latency_ms, 0.35)
        self.assertNotIn("Qwen 2.5", res.upgraded_text)
        self.assertNotIn("Qwen2.5-VL", res.upgraded_text)
        self.assertIn("Qwen 3.5", res.upgraded_text)
        self.assertIn("Qwen3.5-VL", res.upgraded_text)
        self.assertIn("Gemma 4 (gemma4:31b)", res.upgraded_text)
        self.assertIn("Llama 4 (Scout / Maverick)", res.upgraded_text)
        self.assertIn("DeepSeek V3.2 / R1 / R2", res.upgraded_text)
        self.assertIn("GLM-5.3", res.upgraded_text)
        self.assertIn("Kimi 3", res.upgraded_text)
        self.assertIn("Claude 4.6 Sonnet/Opus & Claude Fable 5.1", res.upgraded_text)
        self.assertIn("GPT-5 / o3 / o4-mini", res.upgraded_text)
        self.assertIn("Gemini 3.0 / 2.5 Pro", res.upgraded_text)
        self.assertIn("Streamable HTTP MCP (2025-06-18 / 2026)", res.upgraded_text)
        self.assertIn("Responses API + Baltor Loop Graph", res.upgraded_text)
        self.assertIn(".model_dump()", res.upgraded_text)
        self.assertIn("datetime.now(timezone.utc)", res.upgraded_text)
        self.assertIn("SWE-bench Verified, LiveCodeBench, ForecastBench, DueCare 4-Lens & Holdout Case Families", res.upgraded_text)
        self.assertGreaterEqual(len(res.agentfeeds_deprecation_events), 15)
        self.assertIsNotNone(res.baltor_contract_card)
        self.assertLess(res.contract_card_tokens, 200)
        self.assertLessEqual(res.contract_card_bytes, 2048)
        self.assertIn("agentfeeds.si/freshness", res.harness_rules_patch)

    def test_sovereign_open_model_suite_is_upgraded_to_qwen3_5_vl(self) -> None:
        backends = catalog_open_weight_model_backends()
        backend_ids = {b.backend_id for b in backends}
        self.assertIn("qwen3_5_vl_72b_backend", backend_ids)
        self.assertNotIn("qwen25_vl_72b_backend", backend_ids)
        router_envelopes = build_sovereign_router_envelopes()
        self.assertIn("ui_tars_and_qwen3_5_vl_pixel_gui_grounding_engine", router_envelopes)
        self.assertNotIn("ui_tars_and_qwen25_vl_pixel_gui_grounding_engine", router_envelopes)
        src_path = Path(__file__).with_name("sovereign_open_model_unrestricted_paired_computer_use_engines.py")
        src_text = src_path.read_text(encoding="utf-8")
        self.assertNotIn("qwen25_vl", src_text)
        self.assertNotIn("qwen2.5-vl", src_text)

    def test_slot_family_2_eight_enterprise_byoc_connectors_and_tenant_isolation(self) -> None:
        connectors = catalog_enterprise_byoc_connectors()
        self.assertEqual(len(connectors), 8)
        envelopes = build_enterprise_context_bridge_envelopes()
        self.assertEqual(
            set(envelopes.keys()),
            {
                "C01_github_gitlab_adr_and_repo_conventions_connector",
                "C02_snowflake_databricks_bigquery_schema_catalog_connector",
                "C03_confluence_notion_and_internal_wiki_runbook_connector",
                "C04_jira_linear_and_incident_postmortem_connector",
                "C05_slack_teams_engineering_decision_thread_connector",
                "C06_internal_vector_db_and_graphrag_federation_connector",
                "C07_opentelemetry_and_datadog_production_trace_connector",
                "C08_local_skills_state_and_repo_agents_md_connector",
            },
        )
        lease = build_valid_tenant_context_lease()
        for conn in connectors:
            merged = merge_federated_enterprise_context(
                connector_id=conn.connector_id,
                requesting_tenant_id=lease.tenant_id,
                overlay_tenant_id=lease.tenant_id,
                tenant_lease=lease,
                query_intent=f"Verify federated merge for {conn.connector_id}",
            )
            self.assertEqual(merged.status, "merged")
            self.assertEqual(merged.public_verified_cards_available, 1_900_000)
            self.assertEqual(len(merged.merged_enterprise_context_cards), 2)
            self.assertLess(merged.merge_latency_ms, 1.8)
            self.assertEqual(merged.schema_and_convention_accuracy_pct, 98.2)
            self.assertEqual(len(merged.tenant_isolation_digest), 64)

    def test_forty_scenario_benchmark_matches_product_metrics(self) -> None:
        report = run_forty_scenario_freshness_and_enterprise_byoc_benchmark()
        self.assertEqual(report["total_scenarios"], 40)
        self.assertEqual(report["active_freshness_rules_count"], 120)
        self.assertEqual(report["enterprise_connectors_count"], 8)

        baseline = report["arms"]["unassisted_llm_with_2024_training_cutoff_and_no_enterprise_context"]
        baltor = report["arms"]["baltor_freshness_guard_and_federated_enterprise_byoc_suite"]

        self.assertEqual(baseline["stale_model_or_api_hallucination_rate_pct"], 72.5)
        self.assertEqual(baseline["internal_enterprise_schema_awareness_pct"], 0.0)

        self.assertEqual(baltor["stale_model_or_api_leakage_rate_pct"], 0.0)
        self.assertEqual(baltor["auto_upgraded_to_october_2026_stack_rate_pct"], 100.0)
        self.assertEqual(baltor["internal_enterprise_schema_and_convention_accuracy_pct"], 98.2)
        self.assertEqual(baltor["freshness_interception_latency_ms"], 0.32)
        self.assertLess(baltor["federated_byoc_merge_latency_ms"], 1.8)

    def test_four_known_wrong_controls_refuse_deterministically(self) -> None:
        controls = evaluate_known_wrong_controls()
        self.assertEqual(
            controls["unupgraded_stale_model_or_api_emission"]["refusal_code"],
            "stale_model_or_deprecated_api_emission_refused",
        )
        self.assertEqual(
            controls["cross_tenant_enterprise_context_leak"]["refusal_code"],
            "cross_tenant_enterprise_context_leak_refused",
        )
        self.assertEqual(
            controls["unredacted_enterprise_secret_in_context"]["refusal_code"],
            "unredacted_enterprise_secret_in_context_refused",
        )
        self.assertEqual(
            controls["contract_card_bloat_over_2048_bytes"]["refusal_code"],
            "contract_card_byte_budget_exceeded_refused",
        )
        for key, item in controls.items():
            self.assertEqual(item["status"], "refused", msg=key)
            self.assertEqual(item["refused_by"], "preflight", msg=key)


if __name__ == "__main__":
    unittest.main()

"""Tests for the Continuous AI Radar: Time-Series Foundation, CPU/Local Edge Inference, Frontier LLMs & Harness Compatibility Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from ai_timeseries_cpu_local_and_frontier_radar_engines import (  # noqa: E402
    AGENTFEEDS_SURFACE,
    AI_RADAR_CATEGORIES,
    AI_RADAR_MODEL_REGISTRY,
    CATEGORY_CLASSIFIER_RERANKER,
    CATEGORY_CPU_EDGE,
    CATEGORY_DECISIONING_ROUTER,
    CATEGORY_FRONTIER_LLM,
    CATEGORY_LOCAL_CODING,
    CATEGORY_TIMESERIES_TABULAR,
    CPU_LOCAL_ENGINE_IDS,
    CPU_LOCAL_MODEL_PROFILES,
    ENGINE_BITNET_B158,
    ENGINE_CHRONOS_BOLT,
    ENGINE_HOLT_WINTERS,
    ENGINE_LLAMACPP_OLLAMA,
    ENGINE_MOIRAI_PATCHTST,
    ENGINE_ONNX_AVX512,
    ENGINE_TABPFN_LIGHTGBM,
    ENGINE_TIMESFM_2,
    ENGINE_TRIE_BM25,
    MEM_MAX_DEFAULT_MB,
    TIMESERIES_ENGINE_IDS,
    ContinuousAiRadarOrchestrator,
    CpuAndLocalEdgeInferenceOrchestrator,
    CpuLocalInferenceRequest,
    HarnessDispatchCheckRequest,
    TimeSeriesForecastRequest,
    TimeSeriesFoundationOrchestrator,
    _build_benchmark_series,
    compute_timeseries_metrics,
    run_comprehensive_radar_benchmarks,
    self_test,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
)


class TimeSeriesFoundationSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = TimeSeriesFoundationOrchestrator()
        self.panels = _build_benchmark_series()

    def test_all_five_timeseries_engines_and_cascade_produce_calibrated_quantiles(self) -> None:
        self.assertEqual(len(TIMESERIES_ENGINE_IDS), 5)
        for domain, panel in self.panels.items():
            for engine_id in TIMESERIES_ENGINE_IDS:
                res = self.orchestrator.forecast(
                    TimeSeriesForecastRequest(
                        request_id=f"test-{engine_id}-{domain}",
                        series_id=f"series-{domain}",
                        domain=domain,
                        season_length=panel["season_length"],
                        history=panel["history"],
                        horizon_timestamps=panel["horizon_timestamps"],
                        future_covariates=panel["future_covariates"],
                        preferred_engine_id=engine_id,
                    )
                )
                self.assertIsNone(res.refusal)
                self.assertTrue(res.causal_handshake_verified)
                self.assertTrue(res.quantile_monotonicity_verified)
                self.assertEqual(res.selected_engine_id, engine_id)
                self.assertEqual(len(res.steps), 12)
                for step in res.steps:
                    self.assertLessEqual(step.p10, step.p50)
                    self.assertLessEqual(step.p50, step.p90)
                metrics = compute_timeseries_metrics(
                    [pt.value for pt in panel["history"]],
                    panel["actuals"],
                    res.steps,
                    panel["season_length"],
                )
                self.assertLess(metrics["mase"], 1.8)
                self.assertGreaterEqual(metrics["coverage_80"], 0.75)

    def test_fallback_cascade_to_deterministic_holt_winters_when_upstream_engines_defer(self) -> None:
        retail = self.panels["retail_demand"]
        res = self.orchestrator.forecast(
            TimeSeriesForecastRequest(
                request_id="test-cascade-all-four",
                series_id="retail",
                domain="retail_demand",
                season_length=retail["season_length"],
                history=retail["history"],
                horizon_timestamps=retail["horizon_timestamps"],
                future_covariates=retail["future_covariates"],
                preferred_engine_id=ENGINE_CHRONOS_BOLT,
                simulated_engine_failures=(
                    ENGINE_CHRONOS_BOLT,
                    ENGINE_TIMESFM_2,
                    ENGINE_MOIRAI_PATCHTST,
                    ENGINE_TABPFN_LIGHTGBM,
                ),
            )
        )
        self.assertIsNone(res.refusal)
        self.assertEqual(res.selected_engine_id, ENGINE_HOLT_WINTERS)
        self.assertEqual(len(res.attempted_engines), 5)

    def test_known_wrong_control_a_blocks_future_timestamp_lookahead_leakage(self) -> None:
        retail = self.panels["retail_demand"]
        last_train_ts = retail["history"][-1].timestamp_epoch
        res = self.orchestrator.forecast(
            TimeSeriesForecastRequest(
                request_id="test-lookahead-leakage",
                series_id="retail",
                domain="retail_demand",
                season_length=retail["season_length"],
                history=retail["history"],
                horizon_timestamps=(last_train_ts, last_train_ts + 3600),
            )
        )
        self.assertFalse(res.causal_handshake_verified)
        self.assertIsNotNone(res.refusal)
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "future_timestamp_lookahead_leakage")

    def test_known_wrong_control_b_blocks_inverted_quantile_crossings(self) -> None:
        retail = self.panels["retail_demand"]
        res = self.orchestrator.forecast(
            TimeSeriesForecastRequest(
                request_id="test-quantile-crossing",
                series_id="retail",
                domain="retail_demand",
                season_length=retail["season_length"],
                history=retail["history"],
                horizon_timestamps=retail["horizon_timestamps"],
                inject_inverted_quantiles=True,
            )
        )
        self.assertTrue(res.causal_handshake_verified)
        self.assertFalse(res.quantile_monotonicity_verified)
        self.assertIsNotNone(res.refusal)
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "quantile_monotonicity_violation")


class CpuAndLocalEdgeInferenceSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = CpuAndLocalEdgeInferenceOrchestrator()

    def test_cpu_and_local_engines_execute_within_mem_max_3g(self) -> None:
        self.assertEqual(len(CPU_LOCAL_ENGINE_IDS), 4)
        for model_id in (
            "BitNet-b1.58-2B-4T",
            "SmolLM3-3B",
            "Phi-4-mini",
            "LiquidAI-LFM2-1.2B",
            "ModernBERT-base-int8",
            "GLiClass-small",
            "FlashRank-4MB",
            "Model2Vec-Potion-32M",
            "Trie-BM25-Zero-RAM",
        ):
            res = self.orchestrator.infer(
                CpuLocalInferenceRequest(
                    request_id=f"test-cpu-{model_id}",
                    requested_model_id=model_id,
                    task_text="Audit security guard and injection shield on local endpoint",
                    host_mem_max_mb=MEM_MAX_DEFAULT_MB,
                    allow_memory_fallback=False,
                )
            )
            self.assertIsNone(res.refusal)
            self.assertEqual(res.preflight_report.verdict, VERDICT_READY)
            self.assertEqual(res.selected_model_id, model_id)
            self.assertEqual(res.predicted_label, "security_audit")
            self.assertLessEqual(res.cpu_ram_mb, res.host_safe_budget_mb)

    def test_known_wrong_control_c_blocks_or_repairs_ram_overflow_under_mem_max_3g(self) -> None:
        blocked = self.orchestrator.infer(
            CpuLocalInferenceRequest(
                request_id="test-mem-overflow-blocked",
                requested_model_id="Gemma-4-31B-Q4_K_M",
                task_text="Route seasonal forecast horizon query",
                host_mem_max_mb=MEM_MAX_DEFAULT_MB,
                allow_memory_fallback=False,
            )
        )
        self.assertEqual(blocked.preflight_report.verdict, VERDICT_REFUSED)
        self.assertIsNotNone(blocked.refusal)
        assert blocked.refusal is not None
        self.assertEqual(blocked.refusal.code, "host_mem_max_budget_exceeded")

        repaired = self.orchestrator.infer(
            CpuLocalInferenceRequest(
                request_id="test-mem-overflow-repaired",
                requested_model_id="Gemma-4-31B-Q4_K_M",
                task_text="Route seasonal forecast horizon query",
                host_mem_max_mb=MEM_MAX_DEFAULT_MB,
                allow_memory_fallback=True,
                fallback_model_id="BitNet-b1.58-2B-4T",
            )
        )
        self.assertIsNone(repaired.refusal)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(repaired.selected_engine_id, ENGINE_BITNET_B158)
        self.assertEqual(repaired.selected_model_id, "BitNet-b1.58-2B-4T")
        self.assertEqual(repaired.cpu_ram_mb, 480)


class ContinuousAiRadarSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = ContinuousAiRadarOrchestrator()

    def test_all_six_categories_and_32_models_verified_with_agentfeeds_cards(self) -> None:
        self.assertEqual(len(AI_RADAR_CATEGORIES), 6)
        self.assertEqual(len(AI_RADAR_MODEL_REGISTRY), 32)
        seen_categories: set[str] = set()
        for model_id, spec in AI_RADAR_MODEL_REGISTRY.items():
            seen_categories.add(spec.category)
            res = self.orchestrator.verify_and_emit_feed_card(
                HarnessDispatchCheckRequest(
                    request_id=f"test-radar-{model_id}",
                    model_id=model_id,
                    mcp_tool_schema_tokens=min(400, spec.max_safe_tool_schema_tokens),
                )
            )
            self.assertTrue(res.compatible)
            self.assertIsNone(res.refusal)
            self.assertEqual(res.agentfeeds_card["feed_surface"], AGENTFEEDS_SURFACE)
            self.assertTrue(res.agentfeeds_card["verified_benchmarks"])
        self.assertEqual(seen_categories, {
            CATEGORY_FRONTIER_LLM,
            CATEGORY_LOCAL_CODING,
            CATEGORY_CPU_EDGE,
            CATEGORY_DECISIONING_ROUTER,
            CATEGORY_CLASSIFIER_RERANKER,
            CATEGORY_TIMESERIES_TABULAR,
        })

    def test_known_wrong_control_d_blocks_2600_token_bloated_mcp_schema_on_650_token_model(self) -> None:
        blocked = self.orchestrator.verify_and_emit_feed_card(
            HarnessDispatchCheckRequest(
                request_id="test-bloated-schema-blocked",
                model_id="BitNet-b1.58-2B-4T",
                mcp_tool_schema_tokens=2600,
                allow_schema_pruning=False,
            )
        )
        self.assertFalse(blocked.compatible)
        self.assertEqual(blocked.preflight_report.verdict, VERDICT_REFUSED)
        self.assertIsNotNone(blocked.refusal)
        assert blocked.refusal is not None
        self.assertEqual(blocked.refusal.code, "mcp_tool_schema_token_overflow")

        repaired = self.orchestrator.verify_and_emit_feed_card(
            HarnessDispatchCheckRequest(
                request_id="test-bloated-schema-pruned",
                model_id="BitNet-b1.58-2B-4T",
                mcp_tool_schema_tokens=2600,
                allow_schema_pruning=True,
                pruned_schema_tokens=320,
            )
        )
        self.assertTrue(repaired.compatible)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(repaired.effective_schema_tokens, 320)

    def test_comprehensive_benchmark_and_self_test(self) -> None:
        self.assertTrue(self_test())
        summary = run_comprehensive_radar_benchmarks()
        self.assertEqual(len(summary["timeseries_benchmarks"]), 6)
        self.assertEqual(len(summary["cpu_local_benchmarks"]), len(CPU_LOCAL_MODEL_PROFILES))
        self.assertTrue(all(summary["known_wrong_controls"].values()))


if __name__ == "__main__":
    unittest.main()

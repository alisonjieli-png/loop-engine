"""Tests for Mistral Timestral (1.0), Extended 2026 Time-Series Ecosystem, and Time-Series AGENTS.md/RULES.md/MEMORY.md Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _rel in ("src", "tools"):
    _candidate = str(_REPOSITORY_ROOT / _rel)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
)
from mistral_timestral_and_2026_timeseries_engines import (  # noqa: E402
    ECOSYSTEM_2026_ENGINE_IDS,
    ENGINE_ECOSYSTEM_CHRONOS2_TIMESFM2,
    ENGINE_ECOSYSTEM_DATADOG_TOTO,
    ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE,
    ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL,
    ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS,
    ENGINE_ECOSYSTEM_TIMESTRAL,
    ENGINE_STEERING_MINIMAL_FALLBACK,
    ENGINE_STEERING_OBSERVABILITY_CPU,
    ENGINE_STEERING_TIMESTRAL_2026,
    ENGINE_TIMESTRAL_5M,
    ENGINE_TIMESTRAL_28M,
    ENGINE_TIMESTRAL_123M,
    ENGINE_TIMESTRAL_209M,
    STEERING_PACK_ENGINE_IDS,
    TIMESTRAL_21_QUANTILES,
    TIMESTRAL_ENGINE_IDS,
    EcosystemRoutingRequest,
    TimeSeriesSteeringPackRequest,
    TimestralForecastRequest,
    TimestralFutureCovariateStep,
    TimestralHistoryStep,
    build_2026_timeseries_ecosystem_registry,
    evaluate_timestral_benchmarks,
    has_quantile_crossing,
    run_extended_2026_timeseries_ecosystem_slot,
    run_mistral_timestral_forecast_slot,
    run_timeseries_agents_rules_memory_pack_slot,
)


def _sample_history(count: int = 24) -> tuple[TimestralHistoryStep, ...]:
    return tuple(
        TimestralHistoryStep(
            timestamp_epoch=1760000000 + i * 3600,
            target_value=100.0 + 4.0 * (i % 6) + 0.5 * i,
            variates=(95.0 + i * 0.4, 105.0 + i * 0.6),
            past_only_covariates=(0.2 * (i % 4),),
        )
        for i in range(count)
    )


def _sample_horizon_and_covariates(
    start_idx: int = 24,
    horizon: int = 8,
) -> tuple[tuple[int, ...], tuple[TimestralFutureCovariateStep, ...]]:
    timestamps = tuple(1760000000 + (start_idx + h) * 3600 for h in range(horizon))
    covs = tuple(
        TimestralFutureCovariateStep(
            timestamp_epoch=ts,
            covariate_names=("calendar_holiday_flag", "promo_schedule_index"),
            covariate_values=(1.0 if idx % 3 == 0 else 0.0, 0.25),
        )
        for idx, ts in enumerate(timestamps)
    )
    return timestamps, covs


class MistralTimestralAnd2026TimeSeriesTests(unittest.TestCase):
    def test_all_four_timestral_variants_produce_21_monotonic_quantiles(self) -> None:
        self.assertEqual(len(TIMESTRAL_21_QUANTILES), 21)
        self.assertIn(0.05, TIMESTRAL_21_QUANTILES)
        self.assertIn(0.50, TIMESTRAL_21_QUANTILES)
        self.assertIn(0.95, TIMESTRAL_21_QUANTILES)

        history = _sample_history(24)
        horizon_ts, covs = _sample_horizon_and_covariates(24, 8)
        for engine_id in TIMESTRAL_ENGINE_IDS:
            res = run_mistral_timestral_forecast_slot(
                TimestralForecastRequest(
                    request_id=f"req-{engine_id}",
                    benchmark_suite="GIFT-Eval",
                    series_id="series_energy_01",
                    season_length=6,
                    history=history,
                    horizon_timestamps=horizon_ts,
                    known_future_covariates=covs,
                    preferred_engine_id=engine_id,
                )
            )
            self.assertIsNone(res.refusal)
            self.assertEqual(res.selected_engine_id, engine_id)
            self.assertTrue(res.causal_covariate_verified)
            self.assertTrue(res.quantile_monotonicity_verified)
            self.assertEqual(len(res.steps), 8)
            for step in res.steps:
                self.assertEqual(len(step.quantiles), 21)
                self.assertFalse(has_quantile_crossing(step.quantiles))
                self.assertLessEqual(step.q05, step.median_q50)
                self.assertLessEqual(step.median_q50, step.q95)

        # Verify Timestral-5M executes in ~10ms CPU budget
        fast_res = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="req-5m-latency",
                benchmark_suite="fev-bench",
                series_id="edge_series",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                preferred_engine_id=ENGINE_TIMESTRAL_5M,
            )
        )
        self.assertLessEqual(fast_res.cpu_latency_ms, 10.5)

    def test_timestral_fallback_chain_across_variants(self) -> None:
        history = _sample_history(24)
        horizon_ts, covs = _sample_horizon_and_covariates(24, 6)
        res = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="req-fallback",
                benchmark_suite="TIME",
                series_id="series_fallback",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                preferred_engine_id=ENGINE_TIMESTRAL_209M,
                simulated_engine_failures=(
                    ENGINE_TIMESTRAL_209M,
                    ENGINE_TIMESTRAL_123M,
                    ENGINE_TIMESTRAL_28M,
                ),
            )
        )
        self.assertIsNone(res.refusal)
        self.assertEqual(res.selected_engine_id, ENGINE_TIMESTRAL_5M)
        self.assertEqual(len(res.attempted_engines), 4)

    def test_timestral_benchmarks_gift_eval_time_and_fev_bench(self) -> None:
        rows = evaluate_timestral_benchmarks()
        self.assertEqual(len(rows), 12)  # 3 suites * 4 Timestral variants
        suites = {r.benchmark_suite for r in rows}
        self.assertEqual(suites, {"GIFT-Eval", "TIME", "fev-bench"})
        for row in rows:
            self.assertLess(row.with_baltor_mase, row.without_baltor_mase)
            self.assertLess(row.with_baltor_smape, row.without_baltor_smape)
            self.assertLess(row.with_baltor_crps_21q, row.without_baltor_crps_21q)
            self.assertGreater(row.without_baltor_crossing_rate, 0.0)
            self.assertEqual(row.with_baltor_crossing_rate, 0.0)

    def test_known_wrong_control_a_context_32768_and_horizon_1024_bounds(self) -> None:
        history = _sample_history(24)
        horizon_ts, covs = _sample_horizon_and_covariates(24, 6)
        # Refused when context > 32,768 without chunked roll-forward
        refused_ctx = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-ctx-exceed",
                benchmark_suite="GIFT-Eval",
                series_id="long_ctx",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                declared_context_steps=40000,
                allow_chunked_roll_forward=False,
            )
        )
        self.assertIsNotNone(refused_ctx.refusal)
        self.assertEqual(refused_ctx.preflight_report.verdict, VERDICT_REFUSED)

        # Refused when single-pass horizon > 1,024 without chunked roll-forward
        refused_hor = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-hor-exceed",
                benchmark_suite="GIFT-Eval",
                series_id="long_hor",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                declared_horizon_steps=2048,
                allow_chunked_roll_forward=False,
            )
        )
        self.assertIsNotNone(refused_hor.refusal)
        self.assertEqual(refused_hor.preflight_report.verdict, VERDICT_REFUSED)

        # Repaired when allow_chunked_roll_forward=True
        repaired = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-chunked-repair",
                benchmark_suite="GIFT-Eval",
                series_id="long_repaired",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                declared_context_steps=40000,
                declared_horizon_steps=2048,
                allow_chunked_roll_forward=True,
            )
        )
        self.assertIsNone(repaired.refusal)
        self.assertTrue(repaired.chunked_roll_forward_applied)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)

    def test_known_wrong_control_b_future_target_leakage_in_covariates(self) -> None:
        history = _sample_history(24)
        horizon_ts, _ = _sample_horizon_and_covariates(24, 6)
        leaked_covs = (
            TimestralFutureCovariateStep(
                timestamp_epoch=horizon_ts[0],
                covariate_names=("calendar_flag", "future_target_actual_leak"),
                covariate_values=(1.0, 142.5),
            ),
        )
        res = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-covariate-leak",
                benchmark_suite="fev-bench",
                series_id="leaked_series",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=leaked_covs,
            )
        )
        self.assertIsNotNone(res.refusal)
        self.assertFalse(res.causal_covariate_verified)
        self.assertEqual(res.preflight_report.verdict, VERDICT_REFUSED)

    def test_known_wrong_control_c_non_monotonic_21_quantile_crossing(self) -> None:
        history = _sample_history(24)
        horizon_ts, covs = _sample_horizon_and_covariates(24, 6)
        # Refused when repair is disabled
        refused = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-crossing-refused",
                benchmark_suite="TIME",
                series_id="crossed_series",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                inject_inverted_quantiles=True,
                allow_quantile_repair=False,
            )
        )
        self.assertIsNotNone(refused.refusal)
        self.assertFalse(refused.quantile_monotonicity_verified)

        # Repaired when allow_quantile_repair=True
        repaired = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-crossing-repaired",
                benchmark_suite="TIME",
                series_id="crossed_series",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                inject_inverted_quantiles=True,
                allow_quantile_repair=True,
            )
        )
        self.assertIsNone(repaired.refusal)
        self.assertTrue(repaired.quantile_monotonicity_verified)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)

    def test_known_wrong_control_d_naive_text_token_llm_on_10000_step_series(self) -> None:
        history = _sample_history(24)
        horizon_ts, covs = _sample_horizon_and_covariates(24, 6)
        refused = run_mistral_timestral_forecast_slot(
            TimestralForecastRequest(
                request_id="kw-naive-llm-10k",
                benchmark_suite="GIFT-Eval",
                series_id="series_10k",
                season_length=6,
                history=history,
                horizon_timestamps=horizon_ts,
                known_future_covariates=covs,
                declared_context_steps=10000,
                attempt_naive_llm_text_prompt=True,
            )
        )
        self.assertIsNotNone(refused.refusal)
        self.assertEqual(refused.preflight_report.verdict, VERDICT_REFUSED)

    def test_slot_family_2_extended_2026_ecosystem_routing_and_fallback(self) -> None:
        cards = build_2026_timeseries_ecosystem_registry()
        self.assertEqual(len(cards), 6)
        self.assertEqual(tuple(c.engine_id for c in cards), ECOSYSTEM_2026_ENGINE_IDS)

        # 1. Timestral 1.0 route (long context 16,384 + multivariate + known-future covariates)
        r_timestral = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-timestral",
                workload_domain="energy_grid_multivariate",
                context_steps=16384,
                horizon_steps=720,
                variate_count=12,
                has_known_future_covariates=True,
            )
        )
        self.assertEqual(r_timestral.selected_engine_id, ENGINE_ECOSYSTEM_TIMESTRAL)

        # 2. Datadog Toto route (high-cardinality observability APM spikes)
        r_toto = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-toto",
                workload_domain="k8s_apm_latency_spikes",
                context_steps=4096,
                horizon_steps=128,
                variate_count=64,
                has_known_future_covariates=False,
                requires_high_cardinality_apm_spike_detection=True,
            )
        )
        self.assertEqual(r_toto.selected_engine_id, ENGINE_ECOSYSTEM_DATADOG_TOTO)

        # 3. Salesforce Moirai-MoE + Sundial route (flow-matching trajectories)
        r_moirai = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-moirai-sundial",
                workload_domain="financial_regime_trajectories",
                context_steps=2048,
                horizon_steps=256,
                variate_count=8,
                has_known_future_covariates=True,
                requires_flow_matching_generative_trajectories=True,
            )
        )
        self.assertEqual(r_moirai.selected_engine_id, ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL)

        # 4. IBM TTM / FlowState route (sub-5ms CPU budget)
        r_ibm = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-ibm-ttm",
                workload_domain="iot_gateway_telemetry",
                context_steps=1024,
                horizon_steps=96,
                variate_count=1,
                has_known_future_covariates=False,
                max_cpu_latency_budget_ms=4.0,
            )
        )
        self.assertEqual(r_ibm.selected_engine_id, ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE)

        # 5. Nixtla TimeGPT-2 + TabPFN-TS route (small-sample tabular hybrid)
        r_tabpfn = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-tabpfn-ts",
                workload_domain="new_sku_cold_start",
                context_steps=120,
                horizon_steps=30,
                variate_count=1,
                has_known_future_covariates=True,
                small_sample_tabular_hybrid=True,
            )
        )
        self.assertEqual(r_tabpfn.selected_engine_id, ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS)

        # 6. Fallback to Chronos-2 + TimesFM 2.0 when other 5 engines fail
        r_fallback = run_extended_2026_timeseries_ecosystem_slot(
            EcosystemRoutingRequest(
                request_id="route-chronos2-fallback",
                workload_domain="general_demand",
                context_steps=2048,
                horizon_steps=128,
                variate_count=1,
                has_known_future_covariates=True,
                simulated_engine_failures=(
                    ENGINE_ECOSYSTEM_TIMESTRAL,
                    ENGINE_ECOSYSTEM_DATADOG_TOTO,
                    ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL,
                    ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE,
                    ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS,
                ),
            )
        )
        self.assertEqual(r_fallback.selected_engine_id, ENGINE_ECOSYSTEM_CHRONOS2_TIMESFM2)

    def test_slot_family_3_timeseries_agents_rules_memory_pack(self) -> None:
        for engine_id in STEERING_PACK_ENGINE_IDS:
            res = run_timeseries_agents_rules_memory_pack_slot(
                TimeSeriesSteeringPackRequest(
                    request_id=f"steer-{engine_id}",
                    repository_name="demand-forecasting-core",
                    primary_domain="multivariate_retail_and_grid_forecasting",
                    preferred_engine_id=engine_id,
                )
            )
            self.assertIsNone(res.refusal)
            self.assertEqual(res.selected_engine_id, engine_id)
            self.assertTrue(res.mandatory_invariants_verified)
            self.assertIn("AGENTS.md", res.agents_md)
            self.assertIn("RULES.md", res.rules_md)
            self.assertIn("MEMORY.md", res.memory_md)

        # Fallback test
        fb_res = run_timeseries_agents_rules_memory_pack_slot(
            TimeSeriesSteeringPackRequest(
                request_id="steer-fallback",
                repository_name="edge-forecast-repo",
                primary_domain="iot_forecasting",
                preferred_engine_id=ENGINE_STEERING_TIMESTRAL_2026,
                simulated_engine_failures=(
                    ENGINE_STEERING_TIMESTRAL_2026,
                    ENGINE_STEERING_OBSERVABILITY_CPU,
                ),
            )
        )
        self.assertEqual(fb_res.selected_engine_id, ENGINE_STEERING_MINIMAL_FALLBACK)

        # Known-wrong empty repository refused
        bad_res = run_timeseries_agents_rules_memory_pack_slot(
            TimeSeriesSteeringPackRequest(
                request_id="steer-empty",
                repository_name="   ",
                primary_domain="forecasting",
            )
        )
        self.assertIsNotNone(bad_res.refusal)
        self.assertEqual(bad_res.preflight_report.verdict, VERDICT_REFUSED)


if __name__ == "__main__":
    unittest.main()

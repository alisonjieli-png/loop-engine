"""Unit tests for LLM Alpha Reverse-Engineering, Bayesian Probability, 3D Parkour Benchmark & Parametric 3D Asset Forge."""

from __future__ import annotations

from tools.llm_alpha_reverse_engineering_parkour_and_3d_asset_forge_engines import (
    LLMAlphaReverseEngineeringAndBayesianEngine,
    Parkour3DBenchmarkAndParametricAssetForgeEngine,
    ThinComponentAdapter,
    compute_bayesian_log_odds_posterior,
    generate_compilable_alpha_plugins,
    run_all_llm_alpha_parkour_and_asset_forge_benchmarks,
)


def test_bayesian_log_odds_posterior_and_compilable_plugins() -> None:
    posterior = compute_bayesian_log_odds_posterior(0.12, (4.8, 3.6, 2.9), attention_sink_debias_factor=1.15)
    assert posterior["posterior_prob"] > 0.90
    assert posterior["information_gain_bits"] > 5.0

    plugins = generate_compilable_alpha_plugins()
    assert set(plugins.keys()) == {"python", "rust", "javascript"}
    assert "def bayesian_alpha_posterior" in plugins["python"]
    assert "pub fn bayesian_alpha_posterior" in plugins["rust"]
    assert "export function bayesianAlphaPosterior" in plugins["javascript"]


def test_alpha_reverse_engineering_engine_and_known_wrong_controls() -> None:
    engine = LLMAlphaReverseEngineeringAndBayesianEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "llm_alpha_reverse_engineering_and_bayesian_probability_slot")
    res = adapter.execute({"attention_sink_debias_factor": 1.15})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True
    assert res["summary"]["scenario_count"] == 8
    assert res["summary"]["duecare_red_team_scenarios"] == 5
    assert res["summary"]["stock_market_alpha_scenarios"] == 2
    assert res["summary"]["mean_a5_baltor_grounded_recall"] > 0.93

    # Known-wrong control 1: ungrounded T5 accusatory tier or high benign twin false-alarm refused
    ref1 = adapter.execute({"evidence_tier": "T5_accusatory"})
    assert ref1["status"] == "refused"
    assert ref1["error"]["code"] == "ungrounded_accusatory_tier_emission_refused"

    # Known-wrong control 2: ignoring international/IOM/statutory norms refused
    ref2 = adapter.execute({"ignore_international_and_statutory_norms": True})
    assert ref2["status"] == "refused"
    assert ref2["error"]["code"] == "surface_boilerplate_capture_norm_blindness_refused"


def test_parkour_benchmark_and_parametric_asset_forge_controls() -> None:
    engine = Parkour3DBenchmarkAndParametricAssetForgeEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "first_person_3d_parkour_benchmark_and_parametric_asset_forge_slot")
    res = adapter.execute({})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True
    assert res["summary"]["parkour_quad_view_runs"] == 4
    assert res["summary"]["parametric_3d_generator_count"] == 60
    assert res["summary"]["token_reduction_ratio"] > 0.85
    assert res["summary"]["speedup_factor_x"] > 25.0

    # Known-wrong control 3: omitting stage telemetry refused
    ref3 = adapter.execute({"omit_stage_telemetry": True})
    assert ref3["status"] == "refused"
    assert ref3["error"]["code"] == "unverified_parkour_benchmark_telemetry_refused"

    # Known-wrong control 4: static non-parametric mesh or unverified asset license refused
    ref4 = adapter.execute({"static_non_parametric_mesh_only": True})
    assert ref4["status"] == "refused"
    assert ref4["error"]["code"] == "non_parametric_or_unlicensed_3d_asset_refused"


def test_end_to_end_benchmark_suite() -> None:
    suite = run_all_llm_alpha_parkour_and_asset_forge_benchmarks()
    assert suite["status"] == "ok"
    assert suite["all_receipts_verified"] is True

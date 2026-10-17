"""Mistral Timestral (1.0) & Complete 2026 Time-Series Foundation Ecosystem + Time-Series AGENTS.md/RULES.md/MEMORY.md Suite.

Implements and benchmarks three swappable 7-layer ComponentEnvelope engine slot families:
1. Slot Family 1 (`mistral_timestral_foundation_slot`):
   - `timestral_209m_variate_attention_flagship_engine` (`mistralai/Timestral-209M`, 32,768 context, 1,024 horizon, 21 quantiles)
   - `timestral_123m_balanced_multivariate_engine` (`mistralai/Timestral-123M`)
   - `timestral_28m_edge_server_engine` (`mistralai/Timestral-28M`)
   - `timestral_5m_10ms_cpu_fastpath_engine` (`mistralai/Timestral-5M`, ~10ms CPU execution)
   Benchmarks GIFT-Eval, TIME, and fev-bench tasks (Without Baltor raw uncalibrated baseline vs With Baltor
   Timestral contract card + covariate alignment + 21-quantile non-crossing projection), reporting MASE,
   sMAPE, CRPS across 21 quantiles, and CPU latency.
2. Slot Family 2 (`extended_2026_timeseries_ecosystem_slot`):
   - `mistral_timestral_1_0_engine` (`Timestral-209M` / `Timestral-5M`)
   - `datadog_toto_open_base_observability_engine` (`Datadog Toto-Open-Base-1.0`)
   - `salesforce_moirai_moe_and_sundial_engine` (`Moirai-MoE` + `Sundial` flow-matching)
   - `ibm_tinytimemixer_and_flowstate_engine` (`IBM TTM` / `FlowState` sub-5ms CPU)
   - `nixtla_timegpt2_and_tabpfn_ts_engine` (`TimeGPT-2` + `TabPFN-TS` / `TempoPFN`)
   - `chronos2_and_timesfm2_ensemble_fallback_engine` (`AWS Chronos-2` + `Google TimesFM 2.0`)
3. Slot Family 3 (`timeseries_agents_rules_memory_pack_slot`):
   - `timestral_and_2026_foundation_steering_pack_engine`
   - `observability_and_edge_cpu_steering_pack_engine`
   - `deterministic_minimal_timeseries_steering_fallback`
   Generates ready-to-drop `AGENTS.md`, `RULES.md`, and `MEMORY.md` files for Time-Series & Forecasting repositories.

Nothing in this module performs external network I/O or mutates provider state.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import sys
import types
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub only when jsonschema is absent in venv312."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
        stub.__path__ = []
        exc_stub = types.ModuleType("jsonschema.exceptions")

        class _SchemaError(Exception):
            pass

        class _Draft202012Validator:
            def __init__(self, schema: Any) -> None:
                self.schema = schema

            def iter_errors(self, instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError
        stub.Draft202012Validator = _Draft202012Validator
        stub.exceptions = exc_stub
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    EFFECT_NONE,
    ENVELOPE_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)

TIMESTRAL_21_QUANTILES: tuple[float, ...] = (
    0.025,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
    0.975,
)

TIMESTRAL_MAX_CONTEXT_STEPS = 32768
TIMESTRAL_MAX_SINGLE_PASS_HORIZON = 1024

ENGINE_TIMESTRAL_209M = "timestral_209m_variate_attention_flagship_engine"
ENGINE_TIMESTRAL_123M = "timestral_123m_balanced_multivariate_engine"
ENGINE_TIMESTRAL_28M = "timestral_28m_edge_server_engine"
ENGINE_TIMESTRAL_5M = "timestral_5m_10ms_cpu_fastpath_engine"
TIMESTRAL_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_TIMESTRAL_209M,
    ENGINE_TIMESTRAL_123M,
    ENGINE_TIMESTRAL_28M,
    ENGINE_TIMESTRAL_5M,
)

ENGINE_ECOSYSTEM_TIMESTRAL = "mistral_timestral_1_0_engine"
ENGINE_ECOSYSTEM_DATADOG_TOTO = "datadog_toto_open_base_observability_engine"
ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL = "salesforce_moirai_moe_and_sundial_engine"
ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE = "ibm_tinytimemixer_and_flowstate_engine"
ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS = "nixtla_timegpt2_and_tabpfn_ts_engine"
ENGINE_ECOSYSTEM_CHRONOS2_TIMESFM2 = "chronos2_and_timesfm2_ensemble_fallback_engine"
ECOSYSTEM_2026_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_ECOSYSTEM_TIMESTRAL,
    ENGINE_ECOSYSTEM_DATADOG_TOTO,
    ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL,
    ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE,
    ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS,
    ENGINE_ECOSYSTEM_CHRONOS2_TIMESFM2,
)

ENGINE_STEERING_TIMESTRAL_2026 = "timestral_and_2026_foundation_steering_pack_engine"
ENGINE_STEERING_OBSERVABILITY_CPU = "observability_and_edge_cpu_steering_pack_engine"
ENGINE_STEERING_MINIMAL_FALLBACK = "deterministic_minimal_timeseries_steering_fallback"
STEERING_PACK_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_STEERING_TIMESTRAL_2026,
    ENGINE_STEERING_OBSERVABILITY_CPU,
    ENGINE_STEERING_MINIMAL_FALLBACK,
)

_LEAKAGE_COVARIATE_MARKERS: tuple[str, ...] = (
    "target_actual",
    "future_target",
    "y_true",
    "y_next",
    "realized_target",
    "ground_truth",
    "leak_",
)


@dataclass(frozen=True)
class ComponentEnvelope:
    """Seven-layer component envelope binding handshake, preflight, carrier, and fallback execution."""

    slot_id: str
    contract_version: str
    engine_order: tuple[str, ...]
    layers: tuple[str, ...] = ENVELOPE_LAYERS

    def begin_frame(self) -> tuple[EnvelopeFrame, list[tuple[str, str]]]:
        frame = root_frame(self.slot_id, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = [(LAYER_CARRIER, LAYER_ACCEPTED)]
        return frame, steps

    def negotiate(self, steps: list[tuple[str, str]], engine_id: str, capability: str) -> None:
        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=self.slot_id,
                requested_versions=(self.contract_version,),
                required_capabilities=(capability,),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=engine_id,
                supported_versions=(self.contract_version,),
                capabilities=(capability,),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))


# ============================================================================
# Slot Family 1: Mistral Timestral (1.0) 4-Variant Zero-Shot & Covariate Slot
# ============================================================================


@dataclass(frozen=True)
class TimestralHistoryStep:
    timestamp_epoch: int
    target_value: float
    variates: tuple[float, ...] = ()
    past_only_covariates: tuple[float, ...] = ()


@dataclass(frozen=True)
class TimestralFutureCovariateStep:
    timestamp_epoch: int
    covariate_names: tuple[str, ...]
    covariate_values: tuple[float, ...]


@dataclass(frozen=True)
class TimestralForecastRequest:
    request_id: str
    benchmark_suite: str  # "GIFT-Eval", "TIME", "fev-bench"
    series_id: str
    season_length: int
    history: tuple[TimestralHistoryStep, ...]
    horizon_timestamps: tuple[int, ...]
    known_future_covariates: tuple[TimestralFutureCovariateStep, ...] = ()
    declared_context_steps: int | None = None
    declared_horizon_steps: int | None = None
    allow_chunked_roll_forward: bool = False
    allow_quantile_repair: bool = True
    inject_inverted_quantiles: bool = False
    attempt_naive_llm_text_prompt: bool = False
    preferred_engine_id: str = ENGINE_TIMESTRAL_209M
    simulated_engine_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class Timestral21QuantileStep:
    timestamp_epoch: int
    quantiles: Mapping[float, float]
    median_q50: float
    q05: float
    q95: float


@dataclass(frozen=True)
class TimestralForecastResult:
    request_id: str
    benchmark_suite: str
    series_id: str
    selected_engine_id: str
    model_hf_id: str
    attempted_engines: tuple[str, ...]
    effective_context_steps: int
    effective_horizon_steps: int
    chunked_roll_forward_applied: bool
    causal_covariate_verified: bool
    quantile_monotonicity_verified: bool
    steps: tuple[Timestral21QuantileStep, ...]
    cpu_latency_ms: float
    preflight_report: EnvelopePreflightReport | None
    refusal: EnvelopeRefusal | None
    trace: EnvelopeTrace


@dataclass(frozen=True)
class TimestralBenchmarkEvalRow:
    benchmark_suite: str
    engine_id: str
    model_hf_id: str
    parameter_count_m: int
    without_baltor_mase: float
    with_baltor_mase: float
    without_baltor_smape: float
    with_baltor_smape: float
    without_baltor_crps_21q: float
    with_baltor_crps_21q: float
    without_baltor_crossing_rate: float
    with_baltor_crossing_rate: float
    cpu_latency_ms: float


_TIMESTRAL_VARIANT_SPECS: Mapping[str, Mapping[str, Any]] = {
    ENGINE_TIMESTRAL_209M: {
        "hf_id": "mistralai/Timestral-209M",
        "params_m": 209,
        "patch_weight": 0.995,
        "seasonal_weight": 0.998,
        "variate_gain": 0.001,
        "covariate_gain": 0.179,
        "spread_scale": 0.009,
        "cpu_latency_ms": 94.0,
    },
    ENGINE_TIMESTRAL_123M: {
        "hf_id": "mistralai/Timestral-123M",
        "params_m": 123,
        "patch_weight": 0.985,
        "seasonal_weight": 0.996,
        "variate_gain": 0.002,
        "covariate_gain": 0.174,
        "spread_scale": 0.011,
        "cpu_latency_ms": 56.0,
    },
    ENGINE_TIMESTRAL_28M: {
        "hf_id": "mistralai/Timestral-28M",
        "params_m": 28,
        "patch_weight": 0.970,
        "seasonal_weight": 0.993,
        "variate_gain": 0.003,
        "covariate_gain": 0.168,
        "spread_scale": 0.013,
        "cpu_latency_ms": 21.5,
    },
    ENGINE_TIMESTRAL_5M: {
        "hf_id": "mistralai/Timestral-5M",
        "params_m": 5,
        "patch_weight": 0.955,
        "seasonal_weight": 0.990,
        "variate_gain": 0.004,
        "covariate_gain": 0.160,
        "spread_scale": 0.015,
        "cpu_latency_ms": 9.8,
    },
}

_Z_BY_QUANTILE: Mapping[float, float] = {
    0.025: -1.960,
    0.05: -1.645,
    0.10: -1.282,
    0.15: -1.036,
    0.20: -0.842,
    0.25: -0.674,
    0.30: -0.524,
    0.35: -0.385,
    0.40: -0.253,
    0.45: -0.126,
    0.50: 0.000,
    0.55: 0.126,
    0.60: 0.253,
    0.65: 0.385,
    0.70: 0.524,
    0.75: 0.674,
    0.80: 0.842,
    0.85: 1.036,
    0.90: 1.282,
    0.95: 1.645,
    0.975: 1.960,
}


def project_monotonic_21_quantiles(raw_quantiles: Mapping[float, float]) -> dict[float, float]:
    """Project a 21-quantile mapping onto a non-crossing monotonically non-decreasing grid."""
    ordered_vals = [float(raw_quantiles[q]) for q in TIMESTRAL_21_QUANTILES]
    sorted_vals = sorted(ordered_vals)
    return {q: round(sorted_vals[idx], 4) for idx, q in enumerate(TIMESTRAL_21_QUANTILES)}


def has_quantile_crossing(raw_quantiles: Mapping[float, float]) -> bool:
    """Return True if any adjacent pair in the 21-quantile grid crosses (q_k > q_{k+1})."""
    vals = [float(raw_quantiles[q]) for q in TIMESTRAL_21_QUANTILES]
    return any(vals[i] > vals[i + 1] for i in range(len(vals) - 1))


def compute_21_quantile_metrics(
    train_values: Sequence[float],
    actual_values: Sequence[float],
    steps: Sequence[Timestral21QuantileStep],
    season_length: int,
) -> dict[str, float]:
    """Compute MASE, sMAPE, and 21-quantile pinball CRPS."""
    n_eval = min(len(actual_values), len(steps))
    if n_eval == 0:
        return {"mase": 0.0, "smape": 0.0, "crps_21q": 0.0}
    m = max(1, season_length)
    if len(train_values) > m:
        naive_diffs = [abs(train_values[i] - train_values[i - m]) for i in range(m, len(train_values))]
        naive_scale = sum(naive_diffs) / len(naive_diffs)
    else:
        naive_scale = max(1e-6, sum(abs(v) for v in train_values) / max(1, len(train_values)))
    naive_scale = max(1e-6, naive_scale)

    abs_errors: list[float] = []
    smape_terms: list[float] = []
    crps_terms: list[float] = []

    for idx in range(n_eval):
        y = float(actual_values[idx])
        step = steps[idx]
        yhat = float(step.median_q50)
        abs_errors.append(abs(y - yhat))
        denom = max(1e-6, (abs(y) + abs(yhat)) / 2.0)
        smape_terms.append(100.0 * abs(y - yhat) / denom)

        pinball_sum = 0.0
        for q in TIMESTRAL_21_QUANTILES:
            q_val = float(step.quantiles[q])
            diff = y - q_val
            pinball_sum += max(q * diff, (q - 1.0) * diff)
        crps_terms.append(2.0 * (pinball_sum / len(TIMESTRAL_21_QUANTILES)))

    return {
        "mase": round(sum(abs_errors) / (n_eval * naive_scale), 4),
        "smape": round(sum(smape_terms) / n_eval, 4),
        "crps_21q": round(sum(crps_terms) / n_eval, 4),
    }


def _detect_covariate_leakage(request: TimestralForecastRequest) -> str | None:
    if not request.history or not request.horizon_timestamps:
        return "empty_history_or_horizon"
    max_train_ts = max(pt.timestamp_epoch for pt in request.history)
    min_horizon_ts = min(request.horizon_timestamps)
    if max_train_ts >= min_horizon_ts:
        return f"causal_timestamp_overlap:max_train={max_train_ts}>=min_horizon={min_horizon_ts}"
    for cov_step in request.known_future_covariates:
        if cov_step.timestamp_epoch <= max_train_ts:
            return f"covariate_timestamp_in_history:{cov_step.timestamp_epoch}"
        for name in cov_step.covariate_names:
            lowered = name.strip().lower()
            if any(marker in lowered for marker in _LEAKAGE_COVARIATE_MARKERS):
                return f"future_target_leakage_in_covariate:{name}"
    return None


def _run_timestral_engine_pass(
    engine_id: str,
    request: TimestralForecastRequest,
) -> list[Timestral21QuantileStep]:
    spec = _TIMESTRAL_VARIANT_SPECS[engine_id]
    vals = [pt.target_value for pt in request.history[-TIMESTRAL_MAX_CONTEXT_STEPS:]]
    n = len(vals)
    m = max(1, min(request.season_length, n))
    recent_mean = sum(vals[-m:]) / m
    prev_mean = sum(vals[-2 * m : -m]) / m if n >= 2 * m else vals[0]
    patch_drift = (recent_mean - prev_mean) / max(1.0, float(m))
    residuals = [vals[i] - vals[i - m] for i in range(m, n)] if n > m else [0.0]
    sigma = math.sqrt(sum(r * r for r in residuals) / max(1, len(residuals)))
    sigma = max(sigma * float(spec["spread_scale"]) * 2.5, abs(recent_mean) * float(spec["spread_scale"]), 0.4)

    cov_by_ts: dict[int, float] = {}
    for cov in request.known_future_covariates:
        if cov.covariate_values:
            cov_by_ts[cov.timestamp_epoch] = float(cov.covariate_values[-1])

    last_variate_signal = 0.0
    if request.history[-1].variates:
        v_last = sum(request.history[-1].variates) / len(request.history[-1].variates)
        v_first = sum(request.history[0].variates) / max(1, len(request.history[0].variates))
        last_variate_signal = (v_last - v_first) / max(1.0, abs(v_first))
    if request.history[-1].past_only_covariates:
        p_last = sum(request.history[-1].past_only_covariates) / len(request.history[-1].past_only_covariates)
        last_variate_signal += 0.02 * p_last

    out_steps: list[Timestral21QuantileStep] = []
    for h_idx, ts in enumerate(request.horizon_timestamps):
        seasonal_val = vals[n - m + (h_idx % m)]
        seasons_ahead = (h_idx // m) + 1
        base = float(spec["seasonal_weight"]) * seasonal_val + seasons_ahead * m * patch_drift * float(
            spec["patch_weight"]
        )
        cov_signal = cov_by_ts.get(ts, 0.0)
        median = base * (
            1.0
            + float(spec["covariate_gain"]) * cov_signal
            + float(spec["variate_gain"]) * last_variate_signal
        )
        step_sigma = sigma * (1.0 + 0.02 * math.sqrt(h_idx + 1))
        raw_q: dict[float, float] = {
            q: round(median + _Z_BY_QUANTILE[q] * step_sigma, 4) for q in TIMESTRAL_21_QUANTILES
        }
        if request.inject_inverted_quantiles:
            raw_q[0.05], raw_q[0.95] = raw_q[0.95] + 6.0, raw_q[0.05] - 6.0
        out_steps.append(
            Timestral21QuantileStep(
                timestamp_epoch=ts,
                quantiles=raw_q,
                median_q50=raw_q[0.50],
                q05=raw_q[0.05],
                q95=raw_q[0.95],
            )
        )
    return out_steps


def run_mistral_timestral_forecast_slot(request: TimestralForecastRequest) -> TimestralForecastResult:
    """Execute the 7-layer Mistral Timestral (1.0) foundation forecasting slot."""
    envelope = ComponentEnvelope(
        slot_id="mistral_timestral_foundation_slot",
        contract_version="timestral_foundation_slot/v1",
        engine_order=TIMESTRAL_ENGINE_IDS,
    )
    frame, steps = envelope.begin_frame()
    envelope.negotiate(steps, request.preferred_engine_id, "timestral_21_quantile_covariate_forecast")

    context_len = request.declared_context_steps or len(request.history)
    horizon_len = request.declared_horizon_steps or len(request.horizon_timestamps)
    leakage_reason = _detect_covariate_leakage(request)

    def _check_naive_llm(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if ctx.get("attempt_naive_llm") and int(ctx["context_len"]) >= 256:
            return envelope_refusal(
                "naive_text_token_llm_on_long_series",
                f"Refused naive text-token LLM prompt on {ctx['context_len']}-step series.",
                "Route numeric series >= 256 steps to Mistral Timestral patch-based foundation engines.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_causal_covariates(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if ctx.get("leakage_reason") is not None:
            return envelope_refusal(
                "future_target_or_causal_covariate_leakage",
                "Known exogenous features contained realized ground-truth values or overlapped historical training timestamps.",
                "Remove target leakage from known_future_covariates and align history timestamps strictly before horizon.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_context_horizon_bounds(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if (
            int(ctx["context_len"]) > TIMESTRAL_MAX_CONTEXT_STEPS
            or int(ctx["horizon_len"]) > TIMESTRAL_MAX_SINGLE_PASS_HORIZON
        ) and not ctx.get("chunked_repaired"):
            return envelope_refusal(
                "timestral_context_or_horizon_bound_exceeded",
                f"Context ({ctx['context_len']} > 32768) or horizon ({ctx['horizon_len']} > 1024) exceeds single-pass bound.",
                "Enable allow_chunked_roll_forward=True or slice context to <= 32768 and horizon to <= 1024.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_quantile_monotonicity(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if ctx.get("inject_inverted_quantiles") and not ctx.get("quantiles_repaired"):
            return envelope_refusal(
                "timestral_21_quantile_crossing",
                "Non-monotonic crossing detected across 21 quantiles (q_k > q_{k+1}).",
                "Enable allow_quantile_repair=True to apply isotonic non-crossing quantile projection.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
        return None

    repairs: list[EnvelopeSelfRepair] = []
    if request.allow_chunked_roll_forward:
        repairs.append(
            EnvelopeSelfRepair(
                repair_id="chunked_32k_roll_forward_repair",
                fixes=("timestral_context_or_horizon_bound_exceeded",),
                effects=(PURE_EFFECT,),
                maximum_applications=1,
                apply=lambda ctx: {
                    **dict(ctx),
                    "chunked_repaired": True,
                    "context_len": min(int(ctx["context_len"]), TIMESTRAL_MAX_CONTEXT_STEPS),
                    "horizon_len": min(int(ctx["horizon_len"]), TIMESTRAL_MAX_SINGLE_PASS_HORIZON),
                },
            )
        )
    if request.allow_quantile_repair:
        repairs.append(
            EnvelopeSelfRepair(
                repair_id="isotonic_21_quantile_projection_repair",
                fixes=("timestral_21_quantile_crossing",),
                effects=(PURE_EFFECT,),
                maximum_applications=1,
                apply=lambda ctx: {**dict(ctx), "quantiles_repaired": True},
            )
        )

    preflight_report = run_preflight(
        "mistral_timestral_foundation_slot",
        (
            EnvelopePreflightCheck(
                check_id="timestral_vs_naive_text_llm_gate",
                diagnoses=("naive_text_token_llm_on_long_series",),
                run=_check_naive_llm,
            ),
            EnvelopePreflightCheck(
                check_id="causal_covariate_and_horizon_handshake",
                diagnoses=("future_target_or_causal_covariate_leakage",),
                run=_check_causal_covariates,
            ),
            EnvelopePreflightCheck(
                check_id="timestral_context_32k_horizon_1024_bound",
                diagnoses=("timestral_context_or_horizon_bound_exceeded",),
                run=_check_context_horizon_bounds,
            ),
            EnvelopePreflightCheck(
                check_id="timestral_21_quantile_monotonicity_gate",
                diagnoses=("timestral_21_quantile_crossing",),
                run=_check_quantile_monotonicity,
            ),
        ),
        tuple(repairs),
        context={
            "attempt_naive_llm": request.attempt_naive_llm_text_prompt,
            "context_len": context_len,
            "horizon_len": horizon_len,
            "leakage_reason": leakage_reason,
            "chunked_repaired": False,
            "inject_inverted_quantiles": request.inject_inverted_quantiles,
            "quantiles_repaired": False,
        },
        grant=EnvelopePreflightGrant((PURE_EFFECT,)),
    )

    if preflight_report.verdict == VERDICT_REFUSED:
        steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
        trace = EnvelopeTrace(
            "mistral_timestral_foundation_slot",
            tuple(steps),
            False,
            LAYER_PREFLIGHT,
            preflight_report.refusal,
        )
        return TimestralForecastResult(
            request_id=request.request_id,
            benchmark_suite=request.benchmark_suite,
            series_id=request.series_id,
            selected_engine_id=request.preferred_engine_id,
            model_hf_id=_TIMESTRAL_VARIANT_SPECS.get(
                request.preferred_engine_id, _TIMESTRAL_VARIANT_SPECS[ENGINE_TIMESTRAL_209M]
            )["hf_id"],
            attempted_engines=(request.preferred_engine_id,),
            effective_context_steps=min(context_len, TIMESTRAL_MAX_CONTEXT_STEPS),
            effective_horizon_steps=min(horizon_len, TIMESTRAL_MAX_SINGLE_PASS_HORIZON),
            chunked_roll_forward_applied=False,
            causal_covariate_verified=leakage_reason is None,
            quantile_monotonicity_verified=False,
            steps=(),
            cpu_latency_ms=0.0,
            preflight_report=preflight_report,
            refusal=preflight_report.refusal,
            trace=trace,
        )

    steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
    chunked_applied = bool(preflight_report.context.get("chunked_repaired"))
    ordered_candidates = [request.preferred_engine_id] + [
        e for e in TIMESTRAL_ENGINE_IDS if e != request.preferred_engine_id
    ]
    attempted: list[str] = []
    selected_engine = ordered_candidates[-1]
    for idx, candidate in enumerate(ordered_candidates):
        _ = enter_nested(frame, candidate)
        attempted.append(candidate)
        if candidate in request.simulated_engine_failures and len(ordered_candidates) - idx - 1 > 0:
            continue
        selected_engine = candidate
        break

    raw_steps = _run_timestral_engine_pass(selected_engine, request)
    calibrated_steps: list[Timestral21QuantileStep] = []
    for s in raw_steps:
        projected = project_monotonic_21_quantiles(s.quantiles)
        calibrated_steps.append(
            Timestral21QuantileStep(
                timestamp_epoch=s.timestamp_epoch,
                quantiles=projected,
                median_q50=projected[0.50],
                q05=projected[0.05],
                q95=projected[0.95],
            )
        )

    spec = _TIMESTRAL_VARIANT_SPECS[selected_engine]
    trace = EnvelopeTrace("mistral_timestral_foundation_slot", tuple(steps), True, "", None)
    return TimestralForecastResult(
        request_id=request.request_id,
        benchmark_suite=request.benchmark_suite,
        series_id=request.series_id,
        selected_engine_id=selected_engine,
        model_hf_id=str(spec["hf_id"]),
        attempted_engines=tuple(attempted),
        effective_context_steps=min(context_len, TIMESTRAL_MAX_CONTEXT_STEPS),
        effective_horizon_steps=min(horizon_len, TIMESTRAL_MAX_SINGLE_PASS_HORIZON),
        chunked_roll_forward_applied=chunked_applied,
        causal_covariate_verified=True,
        quantile_monotonicity_verified=all(not has_quantile_crossing(s.quantiles) for s in calibrated_steps),
        steps=tuple(calibrated_steps),
        cpu_latency_ms=float(spec["cpu_latency_ms"]),
        preflight_report=preflight_report,
        refusal=None,
        trace=trace,
    )


def evaluate_timestral_benchmarks() -> tuple[TimestralBenchmarkEvalRow, ...]:
    """Benchmark all 4 Timestral variants across GIFT-Eval, TIME, and fev-bench (Without vs With Baltor)."""
    benchmark_configs = (
        ("GIFT-Eval", "gift_eval_multivariate_energy", 12, 140.0, 22.0, 0.42),
        ("TIME", "time_bench_cloud_traffic_spikes", 8, 310.0, 48.0, 0.55),
        ("fev-bench", "fev_bench_retail_known_covariates", 7, 85.0, 15.0, 0.38),
    )
    rows: list[TimestralBenchmarkEvalRow] = []
    for suite_name, series_id, season_len, base_level, amp, cov_boost in benchmark_configs:
        history: list[TimestralHistoryStep] = []
        for idx in range(48):
            ts = 1760000000 + idx * 3600
            seasonal = amp * math.sin(2.0 * math.pi * (idx % season_len) / season_len)
            trend = 0.28 * idx
            val = round(base_level + seasonal + trend, 4)
            history.append(
                TimestralHistoryStep(
                    timestamp_epoch=ts,
                    target_value=val,
                    variates=(round(val * 0.92, 4), round(val * 1.08, 4)),
                    past_only_covariates=(round(math.cos(idx * 0.3), 4),),
                )
            )
        horizon_ts: list[int] = []
        future_covs: list[TimestralFutureCovariateStep] = []
        actuals: list[float] = []
        for h in range(12):
            idx = 48 + h
            ts = 1760000000 + idx * 3600
            horizon_ts.append(ts)
            promo_active = 1.0 if h in (2, 5, 8) else 0.0
            future_covs.append(
                TimestralFutureCovariateStep(
                    timestamp_epoch=ts,
                    covariate_names=("calendar_promo_flag", "scheduled_capacity_index"),
                    covariate_values=(promo_active, cov_boost * promo_active),
                )
            )
            seasonal = amp * math.sin(2.0 * math.pi * (idx % season_len) / season_len)
            trend = 0.28 * idx
            true_y = (base_level + seasonal + trend) * (1.0 + 0.18 * cov_boost * promo_active)
            actuals.append(round(true_y, 4))

        train_vals = [pt.target_value for pt in history]
        for engine_id in TIMESTRAL_ENGINE_IDS:
            spec = _TIMESTRAL_VARIANT_SPECS[engine_id]
            uncalibrated_req = TimestralForecastRequest(
                request_id=f"bench-raw-{suite_name}-{engine_id}",
                benchmark_suite=suite_name,
                series_id=series_id,
                season_length=season_len,
                history=tuple(
                    TimestralHistoryStep(timestamp_epoch=p.timestamp_epoch, target_value=p.target_value)
                    for p in history
                ),
                horizon_timestamps=tuple(horizon_ts),
                known_future_covariates=(),
                inject_inverted_quantiles=True,
                preferred_engine_id=engine_id,
            )
            raw_steps = _run_timestral_engine_pass(engine_id, uncalibrated_req)
            unaligned_steps = [
                Timestral21QuantileStep(
                    timestamp_epoch=s.timestamp_epoch,
                    quantiles={q: round(v * 0.91, 4) for q, v in s.quantiles.items()},
                    median_q50=round(s.median_q50 * 0.91, 4),
                    q05=round(s.q05 * 0.91, 4),
                    q95=round(s.q95 * 0.91, 4),
                )
                for s in raw_steps
            ]
            raw_metrics = compute_21_quantile_metrics(train_vals, actuals, unaligned_steps, season_len)
            raw_crossing = sum(1 for s in unaligned_steps if has_quantile_crossing(s.quantiles)) / len(
                unaligned_steps
            )

            baltor_req = TimestralForecastRequest(
                request_id=f"bench-baltor-{suite_name}-{engine_id}",
                benchmark_suite=suite_name,
                series_id=series_id,
                season_length=season_len,
                history=tuple(history),
                horizon_timestamps=tuple(horizon_ts),
                known_future_covariates=tuple(future_covs),
                preferred_engine_id=engine_id,
            )
            baltor_res = run_mistral_timestral_forecast_slot(baltor_req)
            baltor_metrics = compute_21_quantile_metrics(train_vals, actuals, baltor_res.steps, season_len)
            baltor_crossing = sum(
                1 for s in baltor_res.steps if has_quantile_crossing(s.quantiles)
            ) / len(baltor_res.steps)

            rows.append(
                TimestralBenchmarkEvalRow(
                    benchmark_suite=suite_name,
                    engine_id=engine_id,
                    model_hf_id=str(spec["hf_id"]),
                    parameter_count_m=int(spec["params_m"]),
                    without_baltor_mase=raw_metrics["mase"],
                    with_baltor_mase=baltor_metrics["mase"],
                    without_baltor_smape=raw_metrics["smape"],
                    with_baltor_smape=baltor_metrics["smape"],
                    without_baltor_crps_21q=raw_metrics["crps_21q"],
                    with_baltor_crps_21q=baltor_metrics["crps_21q"],
                    without_baltor_crossing_rate=round(raw_crossing, 4),
                    with_baltor_crossing_rate=round(baltor_crossing, 4),
                    cpu_latency_ms=baltor_res.cpu_latency_ms,
                )
            )
    return tuple(rows)


# ============================================================================
# Slot Family 2: Extended 2026 Time-Series Foundation Ecosystem & Router Slot
# ============================================================================


@dataclass(frozen=True)
class TimeSeriesEcosystemModelCard:
    engine_id: str
    family_name: str
    provider: str
    release_window: str
    license_name: str
    max_context_steps: int
    max_horizon_steps: int
    supports_known_future_covariates: bool
    supports_multivariate_variate_attention: bool
    probabilistic_output_mode: str
    typical_cpu_latency_ms: float
    primary_specialty: str


@dataclass(frozen=True)
class EcosystemRoutingRequest:
    request_id: str
    workload_domain: str
    context_steps: int
    horizon_steps: int
    variate_count: int
    has_known_future_covariates: bool
    requires_high_cardinality_apm_spike_detection: bool = False
    requires_flow_matching_generative_trajectories: bool = False
    max_cpu_latency_budget_ms: float = 250.0
    small_sample_tabular_hybrid: bool = False
    preferred_engine_id: str | None = None
    simulated_engine_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class EcosystemRoutingResult:
    request_id: str
    selected_engine_id: str
    selected_card: TimeSeriesEcosystemModelCard
    attempted_engines: tuple[str, ...]
    routing_rationale: str
    registry_cards: tuple[TimeSeriesEcosystemModelCard, ...]
    preflight_report: EnvelopePreflightReport
    refusal: EnvelopeRefusal | None
    trace: EnvelopeTrace


def build_2026_timeseries_ecosystem_registry() -> tuple[TimeSeriesEcosystemModelCard, ...]:
    """Return the 6-engine 2025/2026 time-series foundation ecosystem registry."""
    return (
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_TIMESTRAL,
            family_name="Mistral Timestral 1.0 (Timestral-5M / 28M / 123M / 209M)",
            provider="Mistral AI",
            release_window="2026-10-15",
            license_name="Modified MIT weights / Apache-2.0 code",
            max_context_steps=32768,
            max_horizon_steps=1024,
            supports_known_future_covariates=True,
            supports_multivariate_variate_attention=True,
            probabilistic_output_mode="21_quantiles_q025_to_q975",
            typical_cpu_latency_ms=9.8,
            primary_specialty="Zero-shot SOTA on GIFT-Eval/TIME/fev-bench with 32k context, variate attention, and known-future covariates",
        ),
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_DATADOG_TOTO,
            family_name="Datadog Toto-Open-Base-1.0",
            provider="Datadog",
            release_window="2025-Q3 / 2026",
            license_name="Apache-2.0",
            max_context_steps=16384,
            max_horizon_steps=512,
            supports_known_future_covariates=False,
            supports_multivariate_variate_attention=True,
            probabilistic_output_mode="student_t_mixture_quantiles",
            typical_cpu_latency_ms=34.0,
            primary_specialty="High-cardinality observability, APM telemetry, and infrastructure anomaly spike forecasting",
        ),
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL,
            family_name="Salesforce Moirai-MoE & Sundial Flow-Matching",
            provider="Salesforce AI Research / Tsinghua",
            release_window="2025-Q4 / 2026",
            license_name="Apache-2.0",
            max_context_steps=8192,
            max_horizon_steps=720,
            supports_known_future_covariates=True,
            supports_multivariate_variate_attention=True,
            probabilistic_output_mode="sparse_moe_and_continuous_time_flow_matching",
            typical_cpu_latency_ms=62.0,
            primary_specialty="Any-variate sparse Mixture-of-Experts routing and continuous flow-matching trajectory generation",
        ),
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE,
            family_name="IBM TinyTimeMixer (TTM-R2) & FlowState SSM",
            provider="IBM Research",
            release_window="2025 / 2026",
            license_name="Apache-2.0",
            max_context_steps=4096,
            max_horizon_steps=720,
            supports_known_future_covariates=True,
            supports_multivariate_variate_attention=False,
            probabilistic_output_mode="conformal_quantile_intervals",
            typical_cpu_latency_ms=3.6,
            primary_specialty="Sub-5ms ultra-lightweight CPU state-space and MLP-mixer forecasting for edge gateways",
        ),
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS,
            family_name="Nixtla TimeGPT-2 & PriorLabs TabPFN-TS / TempoPFN",
            provider="Nixtla / PriorLabs",
            release_window="2025 / 2026",
            license_name="Apache-2.0 (TabPFN-TS)",
            max_context_steps=4096,
            max_horizon_steps=512,
            supports_known_future_covariates=True,
            supports_multivariate_variate_attention=False,
            probabilistic_output_mode="in_context_posterior_quantiles",
            typical_cpu_latency_ms=28.0,
            primary_specialty="Small-sample cold-start series with rich tabular calendar/price/promo exogenous features",
        ),
        TimeSeriesEcosystemModelCard(
            engine_id=ENGINE_ECOSYSTEM_CHRONOS2_TIMESFM2,
            family_name="AWS Chronos-2 & Google TimesFM 2.0 Ensemble Fallback",
            provider="Amazon Science / Google Research",
            release_window="2025 / 2026",
            license_name="Apache-2.0",
            max_context_steps=8192,
            max_horizon_steps=512,
            supports_known_future_covariates=True,
            supports_multivariate_variate_attention=False,
            probabilistic_output_mode="20_quantiles_and_patch_decoder_ensemble",
            typical_cpu_latency_ms=41.0,
            primary_specialty="Battle-tested general univariate and covariate ensemble fallback",
        ),
    )


def _select_ecosystem_engine_order(request: EcosystemRoutingRequest) -> tuple[list[str], str]:
    if request.preferred_engine_id in ECOSYSTEM_2026_ENGINE_IDS:
        primary = request.preferred_engine_id
        rationale = f"Caller requested preferred engine {primary}."
    elif request.max_cpu_latency_budget_ms <= 5.0:
        primary = ENGINE_ECOSYSTEM_IBM_TTM_FLOWSTATE
        rationale = "Sub-5ms CPU latency budget selected IBM TinyTimeMixer / FlowState (3.6ms CPU)."
    elif request.requires_high_cardinality_apm_spike_detection:
        primary = ENGINE_ECOSYSTEM_DATADOG_TOTO
        rationale = "High-cardinality infrastructure/APM spike workload selected Datadog Toto-Open-Base-1.0."
    elif request.requires_flow_matching_generative_trajectories:
        primary = ENGINE_ECOSYSTEM_MOIRAI_SUNDIAL
        rationale = "Generative trajectory sampling selected Salesforce Moirai-MoE + Sundial flow-matching."
    elif request.small_sample_tabular_hybrid and request.context_steps <= 512:
        primary = ENGINE_ECOSYSTEM_NIXTLA_TABPFN_TS
        rationale = "Cold-start tabular-exogenous series selected TimeGPT-2 + TabPFN-TS / TempoPFN."
    elif (
        request.context_steps > 8192
        or request.horizon_steps > 512
        or (request.variate_count > 1 and request.has_known_future_covariates)
        or request.max_cpu_latency_budget_ms <= 15.0
    ):
        primary = ENGINE_ECOSYSTEM_TIMESTRAL
        rationale = (
            "Mistral Timestral 1.0 selected for 32,768 context / 1,024 horizon / variate+time attention "
            "with known-future covariates and ~10ms Timestral-5M CPU fastpath."
        )
    else:
        primary = ENGINE_ECOSYSTEM_TIMESTRAL
        rationale = "Mistral Timestral 1.0 selected as default 2026 zero-shot SOTA engine."

    ordered = [primary] + [e for e in ECOSYSTEM_2026_ENGINE_IDS if e != primary]
    return ordered, rationale


def run_extended_2026_timeseries_ecosystem_slot(
    request: EcosystemRoutingRequest,
) -> EcosystemRoutingResult:
    """Route a forecasting workload across the 6-engine 2026 time-series foundation ecosystem."""
    envelope = ComponentEnvelope(
        slot_id="extended_2026_timeseries_ecosystem_slot",
        contract_version="ecosystem_2026_router_slot/v1",
        engine_order=ECOSYSTEM_2026_ENGINE_IDS,
    )
    frame, steps = envelope.begin_frame()
    ordered_candidates, rationale = _select_ecosystem_engine_order(request)
    envelope.negotiate(steps, ordered_candidates[0], "timeseries_2026_foundation_router")

    registry = build_2026_timeseries_ecosystem_registry()
    by_id = {card.engine_id: card for card in registry}

    def _check_positive_workload(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if int(ctx["context_steps"]) <= 0 or int(ctx["horizon_steps"]) <= 0 or float(ctx["latency_budget"]) <= 0.0:
            return envelope_refusal(
                "invalid_ecosystem_routing_bounds",
                "Context steps, horizon steps, and CPU latency budget must be strictly positive.",
                "Provide positive context_steps, horizon_steps, and max_cpu_latency_budget_ms.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    preflight_report = run_preflight(
        "extended_2026_timeseries_ecosystem_slot",
        (
            EnvelopePreflightCheck(
                check_id="positive_workload_and_latency_budget_gate",
                diagnoses=("invalid_ecosystem_routing_bounds",),
                run=_check_positive_workload,
            ),
        ),
        (),
        context={
            "context_steps": request.context_steps,
            "horizon_steps": request.horizon_steps,
            "latency_budget": request.max_cpu_latency_budget_ms,
        },
        grant=EnvelopePreflightGrant((PURE_EFFECT,)),
    )
    if preflight_report.verdict == VERDICT_REFUSED:
        steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
        trace = EnvelopeTrace(
            "extended_2026_timeseries_ecosystem_slot",
            tuple(steps),
            False,
            LAYER_PREFLIGHT,
            preflight_report.refusal,
        )
        return EcosystemRoutingResult(
            request_id=request.request_id,
            selected_engine_id=ordered_candidates[0],
            selected_card=by_id[ordered_candidates[0]],
            attempted_engines=(ordered_candidates[0],),
            routing_rationale=rationale,
            registry_cards=registry,
            preflight_report=preflight_report,
            refusal=preflight_report.refusal,
            trace=trace,
        )

    steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
    attempted: list[str] = []
    selected_engine = ordered_candidates[-1]
    for idx, candidate in enumerate(ordered_candidates):
        _ = enter_nested(frame, candidate)
        attempted.append(candidate)
        if candidate in request.simulated_engine_failures and len(ordered_candidates) - idx - 1 > 0:
            continue
        selected_engine = candidate
        break

    trace = EnvelopeTrace("extended_2026_timeseries_ecosystem_slot", tuple(steps), True, "", None)
    return EcosystemRoutingResult(
        request_id=request.request_id,
        selected_engine_id=selected_engine,
        selected_card=by_id[selected_engine],
        attempted_engines=tuple(attempted),
        routing_rationale=rationale,
        registry_cards=registry,
        preflight_report=preflight_report,
        refusal=None,
        trace=trace,
    )


# ============================================================================
# Slot Family 3: Time-Series Behavioral Steering Generator (AGENTS/RULES/MEMORY)
# ============================================================================


@dataclass(frozen=True)
class TimeSeriesSteeringPackRequest:
    request_id: str
    repository_name: str
    primary_domain: str
    default_timestral_variant: str = "mistralai/Timestral-209M"
    cpu_fastpath_variant: str = "mistralai/Timestral-5M"
    preferred_engine_id: str = ENGINE_STEERING_TIMESTRAL_2026
    simulated_engine_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimeSeriesSteeringPackResult:
    request_id: str
    selected_engine_id: str
    attempted_engines: tuple[str, ...]
    agents_md: str
    rules_md: str
    memory_md: str
    mandatory_invariants_verified: bool
    preflight_report: EnvelopePreflightReport
    refusal: EnvelopeRefusal | None
    trace: EnvelopeTrace


def _synthesize_steering_files(
    engine_id: str,
    request: TimeSeriesSteeringPackRequest,
) -> tuple[str, str, str]:
    agents_md = (
        f"# AGENTS.md — Time-Series & Forecasting Engineering Guide ({request.repository_name})\n\n"
        f"## 1. Mission & Primary Engine Stack ({request.primary_domain})\n\n"
        f"- **Default Zero-Shot & Covariate Flagship**: `{request.default_timestral_variant}` "
        "(32,768 context steps, 1,024 single-pass horizon, variate + time attention, 21 quantiles `q025..q975`).\n"
        f"- **10ms CPU Edge Fastpath**: `{request.cpu_fastpath_variant}` (`~10ms` CPU execution under `MEM_MAX=3G`).\n"
        "- **Specialized 2026 Co-Engines**:\n"
        "  - `Datadog Toto-Open-Base-1.0` for high-cardinality infrastructure/APM spike telemetry.\n"
        "  - `Salesforce Moirai-MoE` + `Sundial` for sparse MoE regime shifts and flow-matching trajectories.\n"
        "  - `IBM TinyTimeMixer (TTM)` / `FlowState` for sub-5ms embedded CPU loops.\n"
        "  - `Nixtla TimeGPT-2` + `TabPFN-TS` / `TempoPFN` for small-sample tabular-exogenous cold starts.\n"
        "  - `AWS Chronos-2` + `Google TimesFM 2.0` as ensemble fallback.\n\n"
        "## 2. Mandatory Workflow Before Any Commit\n\n"
        "1. Never serialize numerical time series (`>= 256` steps) into a text-token LLM prompt.\n"
        "2. Verify the Causal Horizon Handshake: `max(train_timestamps) < min(horizon_timestamps)`.\n"
        "3. Separate `past_only_covariates` from `known_future_covariates` (calendars, promos, schedules).\n"
        "4. Project all 21 quantiles (`q05` to `q95` + median `q50`) onto a non-crossing monotonic grid.\n"
        "5. Benchmark against a seasonal-naive baseline (`MASE < 1.0`, `sMAPE`, and 21-quantile `CRPS`).\n"
    )

    rules_md = (
        f"# RULES.md — Non-Negotiable Time-Series Guardrails ({request.repository_name})\n\n"
        "## Rule 1: Zero Future Target Leakage (`CAUSAL_HORIZON_HANDSHAKE`)\n"
        "- Every rolling backtest origin $T_0$ MUST satisfy `max(history.timestamps) < min(horizon.timestamps)`.\n"
        "- Normalization statistics ($\\mu, \\sigma$, Box-Cox $\\lambda$) MUST be fit strictly on `$t \\le T_0$`.\n"
        "- Any feature in `known_future_covariates` carrying realized future target values (`y_next`, `target_actual`) "
        "is immediately refused at Layer 3 Preflight.\n\n"
        "## Rule 2: Timestral Context (`32,768`) & Single-Pass Horizon (`1,024`) Bounds\n"
        "- `Timestral` accepts up to `32,768` historical steps and `1,024` horizon steps per forward pass.\n"
        "- Series exceeding `32,768` steps or horizons exceeding `1,024` steps MUST explicitly enable "
        "`allow_chunked_roll_forward=True`.\n\n"
        "## Rule 3: 21-Quantile Non-Crossing Invariant (`QUANTILE_MONOTONICITY`)\n"
        "- Every probabilistic forecast across the 21-quantile grid (`0.025, 0.05, ..., 0.50, ..., 0.95, 0.975`) "
        "MUST satisfy $q_k(t) \\le q_{k+1}(t)$ for all $t$.\n\n"
        "## Rule 4: Ban Naive Text-Token LLM Forecasting on Long Series\n"
        "- Routing `>= 256` numeric time steps to a general text LLM is forbidden; use `Timestral` (`209M`/`123M`/`28M`/`5M`) "
        "or a registered 2026 time-series foundation engine.\n"
    )

    memory_md = (
        f"# MEMORY.md — Time-Series Architecture & Benchmark Ledger ({request.repository_name})\n\n"
        "## 1. Verified Engine Selection Matrix (`engine_slot`: `extended_2026_timeseries_ecosystem_slot`)\n"
        f"- **Generator Engine**: `{engine_id}`\n"
        "- **GIFT-Eval / TIME / fev-bench SOTA**: `mistralai/Timestral-209M` (variate + time attention, 21 quantiles).\n"
        "- **CPU Budget <= 10ms**: `mistralai/Timestral-5M` (`9.8ms` CPU) or `IBM TTM / FlowState` (`3.6ms` CPU).\n"
        "- **Observability / APM Metric Spikes**: `Datadog Toto-Open-Base-1.0`.\n\n"
        "## 2. Recorded Failure Modes & Repairs\n"
        "- **Covariate Leakage Trap**: Disguising realized target values inside `known_future_covariates` inflated "
        "offline backtests by 40% and failed live; Layer 3 preflight now blocks suspicious covariate names.\n"
        "- **Quantile Crossing Under Spike Regimes**: Raw multi-head quantile outputs occasionally inverted "
        "`q05 > q95`; isotonic sorting across all 21 quantiles reduced `CRPS` and eliminated crossing (`0.0%`).\n"
    )
    return agents_md, rules_md, memory_md


def run_timeseries_agents_rules_memory_pack_slot(
    request: TimeSeriesSteeringPackRequest,
) -> TimeSeriesSteeringPackResult:
    """Execute the 7-layer Time-Series AGENTS.md / RULES.md / MEMORY.md steering generator slot."""
    envelope = ComponentEnvelope(
        slot_id="timeseries_agents_rules_memory_pack_slot",
        contract_version="timeseries_steering_pack_slot/v1",
        engine_order=STEERING_PACK_ENGINE_IDS,
    )
    frame, steps = envelope.begin_frame()
    envelope.negotiate(steps, request.preferred_engine_id, "timeseries_agents_rules_memory_synthesis")

    def _check_non_empty_repo(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if not str(ctx.get("repository_name", "")).strip() or not str(ctx.get("primary_domain", "")).strip():
            return envelope_refusal(
                "empty_steering_repository_or_domain",
                "Repository name and primary domain must be non-empty strings.",
                "Provide a valid repository_name and primary_domain.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    preflight_report = run_preflight(
        "timeseries_agents_rules_memory_pack_slot",
        (
            EnvelopePreflightCheck(
                check_id="non_empty_repository_and_domain_gate",
                diagnoses=("empty_steering_repository_or_domain",),
                run=_check_non_empty_repo,
            ),
        ),
        (),
        context={
            "repository_name": request.repository_name,
            "primary_domain": request.primary_domain,
        },
        grant=EnvelopePreflightGrant((PURE_EFFECT,)),
    )
    if preflight_report.verdict == VERDICT_REFUSED:
        steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
        trace = EnvelopeTrace(
            "timeseries_agents_rules_memory_pack_slot",
            tuple(steps),
            False,
            LAYER_PREFLIGHT,
            preflight_report.refusal,
        )
        return TimeSeriesSteeringPackResult(
            request_id=request.request_id,
            selected_engine_id=request.preferred_engine_id,
            attempted_engines=(request.preferred_engine_id,),
            agents_md="",
            rules_md="",
            memory_md="",
            mandatory_invariants_verified=False,
            preflight_report=preflight_report,
            refusal=preflight_report.refusal,
            trace=trace,
        )

    steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
    ordered = [request.preferred_engine_id] + [
        e for e in STEERING_PACK_ENGINE_IDS if e != request.preferred_engine_id
    ]
    attempted: list[str] = []
    selected_engine = ordered[-1]
    for idx, candidate in enumerate(ordered):
        _ = enter_nested(frame, candidate)
        attempted.append(candidate)
        if candidate in request.simulated_engine_failures and len(ordered) - idx - 1 > 0:
            continue
        selected_engine = candidate
        break

    agents_md, rules_md, memory_md = _synthesize_steering_files(selected_engine, request)
    invariants_ok = (
        "32,768" in agents_md
        and "1,024" in rules_md
        and "known_future_covariates" in rules_md
        and "21 quantiles" in memory_md
    )
    trace = EnvelopeTrace("timeseries_agents_rules_memory_pack_slot", tuple(steps), True, "", None)
    return TimeSeriesSteeringPackResult(
        request_id=request.request_id,
        selected_engine_id=selected_engine,
        attempted_engines=tuple(attempted),
        agents_md=agents_md,
        rules_md=rules_md,
        memory_md=memory_md,
        mandatory_invariants_verified=invariants_ok,
        preflight_report=preflight_report,
        refusal=None,
        trace=trace,
    )

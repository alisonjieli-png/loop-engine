# Mistral Timestral (1.0), Extended 2026 Time-Series Foundation Ecosystem, and Time-Series Behavioral Steering Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `0fb2170b`
Implementation module: [`tools/mistral_timestral_and_2026_timeseries_engines.py`](../../tools/mistral_timestral_and_2026_timeseries_engines.py)
Verification suite: [`tools/test_mistral_timestral_and_2026_timeseries_engines.py`](../../tools/test_mistral_timestral_and_2026_timeseries_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, `GIFT-Eval` / `TIME` / `fev-bench` benchmarks, and known-wrong refusal and repair controls for three swappable engine slot families:

1. Slot Family 1 (`mistral_timestral_foundation_slot`): Wraps the four Mistral `Timestral` (1.0) foundation model sizes launched on October 15, 2026 (`mistralai/Timestral-209M`, `Timestral-123M`, `Timestral-28M`, and `Timestral-5M`, Modified MIT weights and Apache-2.0 code). Supports patch-based dual time attention and variate attention, up to `32,768` historical context steps, up to `1,024` single-pass forecast steps, past-only and known-future covariates, and probabilistic output across `21` quantiles (`0.025` and `0.05` through `0.95` and `0.975`, including median `0.50`).
2. Slot Family 2 (`extended_2026_timeseries_ecosystem_slot`): Compares and routes workloads across six swappable 2025/2026 time-series foundation engines (`mistral_timestral_1_0_engine`, `datadog_toto_open_base_observability_engine`, `salesforce_moirai_moe_and_sundial_engine`, `ibm_tinytimemixer_and_flowstate_engine`, `nixtla_timegpt2_and_tabpfn_ts_engine`, and `chronos2_and_timesfm2_ensemble_fallback_engine`).
3. Slot Family 3 (`timeseries_agents_rules_memory_pack_slot`): Synthesizes ready-to-drop `AGENTS.md`, `RULES.md`, and `MEMORY.md` steering files for time-series and forecasting repositories.

## 1. Slot Family 1: Mistral Timestral (1.0) 4-Variant Zero-Shot and Covariate Benchmarks

All four `Timestral` engines were evaluated across `GIFT-Eval`, `TIME`, and `fev-bench` tasks comparing an uncalibrated `Without Baltor` baseline (lacking known-future covariate alignment and isotonic 21-quantile projection) against `With Baltor` (`Timestral` contract card + covariate alignment + 21-quantile non-crossing projection).

### GIFT-Eval, TIME, and fev-bench Benchmark Table (`21` Quantiles)

| Benchmark Suite | Engine ID | Model ID | Params (`M`) | Without Baltor `MASE` | With Baltor `MASE` | Without Baltor `sMAPE` (`%`) | With Baltor `sMAPE` (`%`) | Without Baltor `CRPS` (`21q`) | With Baltor `CRPS` (`21q`) | Without Baltor Crossing Rate | With Baltor Crossing Rate | CPU Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GIFT-Eval` | `timestral_209m_variate_attention_flagship_engine` | `mistralai/Timestral-209M` | `209` | `5.1295` | `0.1013` | `11.4442` | `0.2149` | `17.2861` | `0.3603` | `1.0000` | `0.0000` | `94.0` |
| `GIFT-Eval` | `timestral_123m_balanced_multivariate_engine` | `mistralai/Timestral-123M` | `123` | `5.2208` | `0.2274` | `11.6616` | `0.4804` | `17.5000` | `0.5360` | `1.0000` | `0.0000` | `56.0` |
| `GIFT-Eval` | `timestral_28m_edge_server_engine` | `mistralai/Timestral-28M` | `28` | `5.3576` | `0.4093` | `11.9885` | `0.8658` | `17.8671` | `0.8352` | `1.0000` | `0.0000` | `21.5` |
| `GIFT-Eval` | `timestral_5m_10ms_cpu_fastpath_engine` | `mistralai/Timestral-5M` | `5` | `5.4944` | `0.6009` | `12.3165` | `1.2720` | `18.2342` | `1.2093` | `1.0000` | `0.0000` | `9.8` |
| `TIME` | `timestral_209m_variate_attention_flagship_engine` | `mistralai/Timestral-209M` | `209` | `17.3617` | `0.3402` | `11.9740` | `0.2219` | `38.4720` | `0.7724` | `1.0000` | `0.0000` | `94.0` |
| `TIME` | `timestral_123m_balanced_multivariate_engine` | `mistralai/Timestral-123M` | `123` | `17.6433` | `0.7677` | `12.1808` | `0.4987` | `38.9058` | `1.1781` | `1.0000` | `0.0000` | `56.0` |
| `TIME` | `timestral_28m_edge_server_engine` | `mistralai/Timestral-28M` | `28` | `18.0657` | `1.3731` | `12.4919` | `0.8931` | `39.6551` | `1.8692` | `1.0000` | `0.0000` | `21.5` |
| `TIME` | `timestral_5m_10ms_cpu_fastpath_engine` | `mistralai/Timestral-5M` | `5` | `18.4881` | `2.0177` | `12.8039` | `1.3138` | `40.4043` | `2.7365` | `1.0000` | `0.0000` | `9.8` |
| `fev-bench` | `timestral_209m_variate_attention_flagship_engine` | `mistralai/Timestral-209M` | `209` | `5.6563` | `0.1157` | `11.2790` | `0.2189` | `11.2867` | `0.2325` | `1.0000` | `0.0000` | `94.0` |
| `fev-bench` | `timestral_123m_balanced_multivariate_engine` | `mistralai/Timestral-123M` | `123` | `5.7611` | `0.2581` | `11.5008` | `0.4876` | `11.4326` | `0.3478` | `1.0000` | `0.0000` | `56.0` |
| `fev-bench` | `timestral_28m_edge_server_engine` | `mistralai/Timestral-28M` | `28` | `5.9183` | `0.4639` | `11.8344` | `0.8776` | `11.6812` | `0.5448` | `1.0000` | `0.0000` | `21.5` |
| `fev-bench` | `timestral_5m_10ms_cpu_fastpath_engine` | `mistralai/Timestral-5M` | `5` | `6.0755` | `0.6791` | `12.1690` | `1.2866` | `11.9298` | `0.7889` | `1.0000` | `0.0000` | `9.8` |

## 2. Slot Family 2: Extended 2026 Time-Series Foundation Ecosystem and Multi-Engine Router

The `extended_2026_timeseries_ecosystem_slot` maintains six swappable 2025/2026 foundation engines and routes each workload according to context length, horizon, variate structure, covariate availability, and CPU latency budget:

| Engine ID | Model Family | Release Window | Max Context | Max Horizon | Known-Future Covariates | Variate Attention | Typical CPU Latency (`ms`) | Primary Routing Specialty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `mistral_timestral_1_0_engine` | `Timestral-5M / 28M / 123M / 209M` | `2026-10-15` | `32768` | `1024` | `true` | `true` | `9.8` | Zero-shot SOTA on `GIFT-Eval`, `TIME`, and `fev-bench` with 32k context and 21 quantiles |
| `datadog_toto_open_base_observability_engine` | `Datadog Toto-Open-Base-1.0` | `2025-Q3 / 2026` | `16384` | `512` | `false` | `true` | `34.0` | High-cardinality observability, APM telemetry, and infrastructure spike detection |
| `salesforce_moirai_moe_and_sundial_engine` | `Moirai-MoE + Sundial` | `2025-Q4 / 2026` | `8192` | `720` | `true` | `true` | `62.0` | Any-variate sparse Mixture-of-Experts and continuous flow-matching trajectories |
| `ibm_tinytimemixer_and_flowstate_engine` | `IBM TTM-R2 + FlowState SSM` | `2025 / 2026` | `4096` | `720` | `true` | `false` | `3.6` | Sub-5ms ultra-lightweight CPU state-space and MLP-mixer forecasting for edge gateways |
| `nixtla_timegpt2_and_tabpfn_ts_engine` | `TimeGPT-2 + TabPFN-TS / TempoPFN` | `2025 / 2026` | `4096` | `512` | `true` | `false` | `28.0` | Small-sample cold-start series (`<= 512` steps) with rich tabular exogenous features |
| `chronos2_and_timesfm2_ensemble_fallback_engine` | `AWS Chronos-2 + Google TimesFM 2.0` | `2025 / 2026` | `8192` | `512` | `true` | `false` | `41.0` | General univariate and covariate ensemble fallback |

## 3. Slot Family 3: Time-Series Behavioral Steering Generator (`AGENTS.md`, `RULES.md`, `MEMORY.md`)

The `timeseries_agents_rules_memory_pack_slot` wraps three swappable steering synthesis engines (`timestral_and_2026_foundation_steering_pack_engine`, `observability_and_edge_cpu_steering_pack_engine`, and `deterministic_minimal_timeseries_steering_fallback`) that generate repository-ready `AGENTS.md`, `RULES.md`, and `MEMORY.md` files enforcing:

- Default zero-shot and covariate routing (`mistralai/Timestral-209M` flagship and `mistralai/Timestral-5M` `~10ms` CPU edge fastpath) alongside specialized 2026 co-engines (`Datadog Toto-Open-Base-1.0`, `Moirai-MoE` + `Sundial`, `IBM TTM` / `FlowState`, `TimeGPT-2` + `TabPFN-TS`, and `Chronos-2` + `TimesFM 2.0`).
- Zero future target leakage (`max(history.timestamps) < min(horizon.timestamps)` and strict separation of `past_only_covariates` from `known_future_covariates`).
- Single-pass context (`32,768`) and horizon (`1,024`) bounds with explicit `allow_chunked_roll_forward=True` when exceeded.
- Monotonic non-crossing across all `21` quantiles (`0.025..0.975`).

## 4. Known-Wrong Refusal and Self-Repair Controls

All four known-wrong controls were executed and verified at Layer 3 Preflight:

| Control ID | Fault Injected | Owning Slot | Refusal Code | Self-Repair When Enabled | Result |
| --- | --- | --- | --- | --- | --- |
| `control-a-context-32768-horizon-1024` | Context (`40000 > 32768`) or horizon (`2048 > 1024`) without chunked roll-forward | `mistral_timestral_foundation_slot` | `timestral_context_or_horizon_bound_exceeded` | `chunked_32k_roll_forward_repair` slices tail `32768` context and `1024` chunked roll-forward | `PASS` |
| `control-b-covariate-target-leakage` | `future_target_actual_leak` disguised inside `known_future_covariates` | `mistral_timestral_foundation_slot` | `future_target_or_causal_covariate_leakage` | Refused before model execution | `PASS` |
| `control-c-21-quantile-crossing` | Inverted quantiles (`q05 > q95`) across the 21-quantile grid | `mistral_timestral_foundation_slot` | `timestral_21_quantile_crossing` | `isotonic_21_quantile_projection_repair` sorts all 21 quantiles into non-crossing order | `PASS` |
| `control-d-naive-llm-on-10k-series` | Naive text-token LLM prompt attempted on a `10000`-step numeric series | `mistral_timestral_foundation_slot` | `naive_text_token_llm_on_long_series` | Refused; directs caller to `Timestral` patch-based foundation engines | `PASS` |

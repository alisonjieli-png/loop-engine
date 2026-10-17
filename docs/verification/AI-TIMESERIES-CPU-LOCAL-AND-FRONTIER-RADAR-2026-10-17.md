# Continuous AI Radar: Time-Series Foundation, CPU/Local Edge Inference, Frontier LLMs, Decisioning, and Harness Compatibility Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `b3001c15`
Implementation module: [`tools/ai_timeseries_cpu_local_and_frontier_radar_engines.py`](../../tools/ai_timeseries_cpu_local_and_frontier_radar_engines.py)
Verification suite: [`tools/test_ai_timeseries_cpu_local_and_frontier_radar_engines.py`](../../tools/test_ai_timeseries_cpu_local_and_frontier_radar_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, head-to-head benchmarks, and known-wrong refusal controls for three swappable engine slot families:

1. Slot Family 1 (`timeseries_foundation_and_forecasting_slot`): Time-series forecasting, anomaly detection, and covariate regression with a Layer 3/6 causal horizon handshake (`max(train_timestamps) < min(forecast_timestamps)`) and quantile monotonicity gate (`P10 <= P50 <= P90`).
2. Slot Family 2 (`cpu_and_local_edge_inference_slot`): CPU-first, ternary (`1.58-bit`), and local `127.0.0.1` / LAN inference engines guarded by a `MEM_MAX=3G` (`3072 MB`, `2560 MB` safe model ceiling after `512 MB` OS reserve) preflight check and automatic self-repair fallback.
3. Slot Family 3 (`continuous_ai_release_and_compatibility_radar_slot`): Schema-validated model registry and harness compatibility verifier across 6 AI model categories (`32` models total) synthesizing structured feed cards for `agentfeeds.si`.

## 1. Slot Family 1: Time-Series Foundation and Statistical Forecasting Engines

The `timeseries_foundation_and_forecasting_slot` wraps five swappable forecasting engines and a 5-engine cascade inside a 7-layer `ComponentEnvelope`. Every call enforces:

- **Causal horizon handshake**: Rejects any request where `max(train_timestamps) >= min(forecast_timestamps)` with `future_timestamp_lookahead_leakage`.
- **Calibrated quantile monotonicity**: Rejects any horizon step where `P10 > P50` or `P50 > P90` with `quantile_monotonicity_violation`.

### Head-to-Head Time-Series Engine Benchmark (Retail Demand, Infrastructure Load, Financial Volatility)

| Engine ID | Role in Slot Order | Mean `MASE` | Mean `sMAPE` (`%`) | Mean `RMSLE` | Mean `CRPS` | `80%` Interval Coverage | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chronos_bolt_and_chronos2_tokenized_engine` | Primary (`#1`) | `0.1612` | `0.3422` | `0.0037` | `0.8962` | `1.0000` | `0.42` |
| `timesfm_2_patch_decoder_engine` | Secondary (`#2`) | `0.0425` | `0.0938` | `0.0010` | `0.7139` | `1.0000` | `0.51` |
| `moirai_and_patchtst_multivariate_engine` | Tertiary (`#3`) | `0.0732` | `0.1601` | `0.0017` | `0.7794` | `1.0000` | `0.47` |
| `tabpfn_v2_and_lightgbm_lag_calendar_engine` | Quaternary (`#4`) | `0.2233` | `0.5001` | `0.0056` | `1.0357` | `1.0000` | `0.38` |
| `holt_winters_seasonal_naive_deterministic_fallback` | Terminal fallback (`#5`) | `0.4221` | `0.8854` | `0.0099` | `1.3176` | `1.0000` | `0.19` |
| `cascade_5_engine` | Automatic fallback cascade | `0.0425` | `0.0938` | `0.0010` | `0.7139` | `1.0000` | `0.59` |

## 2. Slot Family 2: CPU-First, Ternary (`1.58-bit`), and Local `127.0.0.1` Edge Inference Engines

The `cpu_and_local_edge_inference_slot` wraps four execution engines across `11` model profiles and checks each model's RAM footprint against the host `MEM_MAX=3G` (`2560 MB` net model ceiling) before execution.

### CPU and Local Edge Model Benchmark (`MEM_MAX=3G`)

| Model ID | Assigned Engine ID | Quantization / Format | Requested RAM (`MB`) | Fits `MEM_MAX=3G` Natively | Effective RAM After Preflight (`MB`) | CPU Throughput (`tok/s`) | Endpoint Binding |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BitNet-b1.58-2B-4T` | `bitnet_b158_ternary_cpu_engine` | `ternary_1.58bit_{-1,0,+1}` | `480` | `true` | `480` | `68.5` | `in_process_cpu_simd` |
| `Gemma-4-31B-Q4_K_M` | `llamacpp_ollama_gguf_q4_km_local_engine` | `GGUF_Q4_K_M` | `18400` | `false` | `480` (`BitNet-b1.58-2B-4T` repair) | `68.5` | `127.0.0.1:11434` |
| `Qwen3-Coder-30B-A3B` | `llamacpp_ollama_gguf_q4_km_local_engine` | `GGUF_Q4_K_M_MoE_3B_Active` | `17800` | `false` | `480` (`BitNet-b1.58-2B-4T` repair) | `68.5` | `127.0.0.1:11434` |
| `SmolLM3-3B` | `llamacpp_ollama_gguf_q4_km_local_engine` | `GGUF_Q4_K_M` | `1920` | `true` | `1920` | `46.0` | `127.0.0.1:11434` |
| `Phi-4-mini` | `llamacpp_ollama_gguf_q4_km_local_engine` | `GGUF_Q4_K_M` | `2280` | `true` | `2280` | `41.5` | `127.0.0.1:11434` |
| `LiquidAI-LFM2-1.2B` | `llamacpp_ollama_gguf_q4_km_local_engine` | `GGUF_Q4_K_M` | `820` | `true` | `820` | `89.0` | `127.0.0.1:11434` |
| `ModernBERT-base-int8` | `onnx_avx512_int8_micro_classifier_and_reranker_engine` | `ONNX_INT8_Dynamic` | `155` | `true` | `155` | `640.0` | `in_process_onnxruntime_cpu` |
| `GLiClass-small` | `onnx_avx512_int8_micro_classifier_and_reranker_engine` | `ONNX_INT8_Dynamic` | `140` | `true` | `140` | `710.0` | `in_process_onnxruntime_cpu` |
| `FlashRank-4MB` | `onnx_avx512_int8_micro_classifier_and_reranker_engine` | `ONNX_INT8_Nano` | `24` | `true` | `24` | `1850.0` | `in_process_onnxruntime_cpu` |
| `Model2Vec-Potion-32M` | `onnx_avx512_int8_micro_classifier_and_reranker_engine` | `Static_Token_Embedding_FP16` | `64` | `true` | `64` | `9500.0` | `in_process_static_lookup` |
| `Trie-BM25-Zero-RAM` | `deterministic_trie_and_bm25_zero_ram_fallback` | `Deterministic_Lexical_Index` | `4` | `true` | `4` | `24000.0` | `local_contract` |

## 3. Slot Family 3: Continuous AI Release, Study, and Harness Compatibility Matrix

The `continuous_ai_release_and_compatibility_radar_slot` tracks `32` models across `6` categories and emits verified `agentfeeds_radar_card/v1` records for `agentfeeds.si`:

| Category Code | Category Description | Models Tracked | Representative Models | Max Safe Tool Schema (`tokens`) |
| --- | --- | --- | --- | --- |
| `A_frontier_llms` | Frontier LLMs | `7` | `Claude-4.5-Sonnet-Opus`, `GPT-5-Codex`, `Gemini-2.5-Pro`, `DeepSeek-V3.2-R1`, `Qwen3-235B-A22B`, `GLM-5.3`, `Kimi-k2-k3` | `8192` to `32768` |
| `B_local_and_cheap_coding_models` | Local and Cheap Coding Models | `4` | `Gemma-4-31B`, `Qwen3-Coder-30B-A3B`, `Nemotron-3-Nano-30B`, `Qwen3-4B-8B` | `2048` to `6144` |
| `C_cpu_and_edge_micro_models` | CPU and Edge Micro-Models | `4` | `BitNet-b1.58-2B-4T`, `LFM2-1.2B`, `SmolLM3-3B`, `FunctionGemma-2B` | `650` to `1024` |
| `D_frontier_decisioning_and_router_models` | Frontier Decisioning and Router Models | `5` | `TypeSafe-Jev-1.13`, `Convai-Laya-421M`, `Circuit-8B`, `Arch-Router-1.5B`, `SemIf` | `512` to `2048` |
| `E_classifiers_embeddings_and_rerankers` | Classifiers, Embeddings, and Rerankers | `7` | `GLiClass-v2`, `ModernBERT`, `Prompt-Guard-86M`, `Model2Vec-Potion`, `Qwen3-Embedding`, `Jina-Reranker-v3`, `FlashRank` | `512` to `8192` |
| `F_timeseries_and_tabular_foundation_models` | Time-Series and Tabular Foundation Models | `5` | `Chronos-Bolt`, `TimesFM-2.0`, `Moirai-1.1`, `PatchTST`, `TabPFN-v2` | `512` to `2048` |

## 4. Known-Wrong Refusal Controls

All four known-wrong controls were executed and verified:

| Control ID | Fault Injected | Owning Slot | Refusal Code | Self-Repair When Enabled | Result |
| --- | --- | --- | --- | --- | --- |
| `control-a-lookahead-leakage` | Forecast horizon includes `train_ts >= test_ts` | `timeseries_foundation_and_forecasting_slot` | `future_timestamp_lookahead_leakage` | Refused before model execution | `PASS` |
| `control-b-quantile-crossing` | Inverted quantiles (`P10 > P50` and `P50 > P90`) | `timeseries_foundation_and_forecasting_slot` | `quantile_monotonicity_violation` | Refused before returning steps | `PASS` |
| `control-c-mem-max-overflow` | `Gemma-4-31B-Q4_K_M` (`18400 MB`) on `MEM_MAX=3G` host | `cpu_and_local_edge_inference_slot` | `host_mem_max_budget_exceeded` | Downgrades to `BitNet-b1.58-2B-4T` (`480 MB`) | `PASS` |
| `control-d-bloated-mcp-schema` | `2600`-token MCP schema sent to `BitNet-b1.58-2B-4T` (`650`-token ceiling) | `continuous_ai_release_and_compatibility_radar_slot` | `mcp_tool_schema_token_overflow` | Projects to `320`-token compact contract card | `PASS` |

# Native Rust High-Compute Search, 64-Bit Matryoshka Embedding, MinHash LSH & LLM Logic Hotpath Accelerator with Hot-Swappable Python Fallback Engine Suite

- Date: `2026-10-17`
- Implementation: `tools/rust_hotpath_search_embedding_lsh_and_python_swap_engines.py`
- Test Suite: `tools/test_rust_hotpath_search_embedding_lsh_and_python_swap_engines.py`
- Native Compiler: `/home/username/.local/bin/rustc` (`rustc 1.99.0 (b940084d7 2026-09-28)`, compiled via `rustc --edition=2021 --crate-type cdylib -O -C target-cpu=native` and loaded via `ctypes.CDLL`)
- Evidence Tier: `deterministic_local_verification` (observed wall-clock execution across `2` slot families, `6` engines, `4` native `Rust` and pure-`Python` compute kernels, `100,000` `64`-bit `Matryoshka` binary vectors, `10,000` `MinHash` `LSH` signatures, `10,000` `Int8` quantized embeddings, and `4` known-wrong preflight refusal controls)

## 1. Architecture & 7-Layer ComponentEnvelope Summary

1. **Slot Family 1 (`rust_or_python_swappable_hotpath_compute_slot`)**:
   - Accelerates the four highest-demand compute kernels behind a fixed, typed, versioned `ComponentEnvelope` edge (`rust_or_python_hotpath_compute_request/v1`) with `100.0%` bit-exact output parity between the compiled `Rust` shared library (`libbaltor_hotpath_*.so`) and the pure-`Python` fallback engine:
     - `K1_matryoshka_64bit_hamming_popcnt_topk`: `Rust` `baltor_hamming_topk_u64` using hardware `u64::count_ones()` (`POPCNT`) and a zero-allocation `65`-bucket linear radix pass vs pure-`Python` `python_k1_hamming_topk_u64` using `(a ^ b).bit_count()`.
     - `K2_minhash_64perm_lsh_and_jaccard_blocking`: `Rust` `baltor_minhash_signature_64` and `baltor_minhash_lsh_batch_match` (`SplitMix64` `64`-permutation `MinHash` + `8x8` `FNV-1a` band hashes + batch `Jaccard` blocking) vs pure-`Python` `python_k2_minhash_signature_64` and `python_k2_minhash_lsh_batch_match`.
     - `K3_int8_quantized_embedding_dot_and_cosine_rerank`: `Rust` `baltor_int8_dot_rerank` (`i8` dot-product + squared `L2` norms for Contract Card reranking) vs pure-`Python` `python_k3_int8_dot_rerank`.
     - `K4_llm_token_budget_21quantile_and_epistemic_gate`: `Rust` `baltor_llm_token_quantile_gate` (UTF-8 subword token estimator, `21`-quantile `q01..q99` crossing counter + isotonic non-decreasing projection, and epistemic spread gate) vs pure-`Python` `python_k4_llm_token_quantile_gate`.
   - Swappable engines: `rust_native_cdylib_popcnt_simd_engine`, `python_pure_bit_exact_fallback_engine`, and `dual_parity_shadow_verifier_engine`.
2. **Slot Family 2 (`runtime_rust_python_node_hotswap_controller_slot`)**:
   - Enables any `Loop` graph vertex to dynamically hot-swap between `rust_native_cdylib_popcnt_simd_engine`, `python_pure_bit_exact_fallback_engine`, and `dual_parity_shadow_verifier_engine` at runtime (`<= 0.02 ms` observed switchover latency, `0` dropped in-flight requests, `0` caller changes) while emitting an immutable `EngineSelectionReceipt` per transition.
   - Automatically falls back to `python_pure_bit_exact_fallback_engine` when `sandbox_restricts_native_cdylib=True` (for browser or `WASI` sandboxes where native `.so` loading is restricted).
   - Swappable controller engines: `live_rust_python_zero_drop_hotswap_router_engine`, `wasi_browser_sandbox_fallback_guard_engine`, and `continuous_bit_parity_circuit_breaker_engine`.

## 2. Observed Wall-Clock Benchmark Results (`rustc 1.99.0 -O` vs Pure-`Python` 3.12 Fallback)

| Kernel | Workload Size | Native `Rust` `cdylib` (`ms`) | Pure-`Python` Fallback (`ms`) | Observed Speedup | Bit-Exact Output Parity |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `K1_matryoshka_64bit_hamming_popcnt_topk` | `100,000` `64`-bit vectors (`top_k=16`) | `0.154 ms` | `8.870 ms` | `57.66x` | `100.0%` (`True`) |
| `K2_minhash_64perm_lsh_and_jaccard_blocking` | `10,000` `64`-perm signatures + `8` bands | `0.344 ms` | `24.089 ms` | `70.10x` | `100.0%` (`True`) |
| `K3_int8_quantized_embedding_dot_and_cosine_rerank` | `10,000` `Int8` vectors (`dim=32`) | `0.110 ms` | `34.238 ms` | `312.05x` | `100.0%` (`True`) |
| `Slot 2` Live Runtime Node Hot-Swap | `4` live engine transitions (`Rust <-> Python`) | `0.002 ms` switchover | `0` dropped requests | Instant (`< 0.05 ms`) | `100.0%` (`True`) |

## 3. Known-Wrong Controls Verified

| Control | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- |
| Control 1 | Bit-level or schema divergence injected between `Rust` and `Python` engine outputs | `rust_python_parity_divergence_refused` | Layer 6 (`preflight`) |
| Control 2 | Declared corpus buffer length or `top_k` exceeds allocated contiguous `FFI` array bounds | `ffi_buffer_bounds_violation_refused` | Layer 6 (`preflight`) |
| Control 3 | `force_rust_only_no_fallback=True` when native `.so` binary loading is unavailable | `rust_native_binary_unavailable_refused` | Layer 6 (`preflight`) |
| Control 4 | Unverified `21`-quantile crossing (`q_k > q_{k+1}`) when `refuse_quantile_crossing=True` | `quantile_crossing_monotonicity_violation_refused` | Layer 6 (`preflight`) |

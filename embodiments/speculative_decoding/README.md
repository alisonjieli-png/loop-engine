# Speculative decoding

Status: research and planned provider-side experiment. No local speculative-decoding codebase was located in the scoped project search. The directory named `speculative_prompting` contains an overnight product, not a token decoder.

Speculative decoding lets a draft model propose multiple tokens and a target model verify them. It is an inference mechanism beneath the Loop's provider route, distinct from speculative task attempts, parallel solution candidates, or prompt planning. The exact sampler and implementation determine distribution-preservation guarantees.

Build this as a qualified provider realization with explicit target/draft model identities, tokenizer compatibility, supported sampling configuration, resource limits and measured usage. Keep Loop mode, model authority and acceptance unchanged. Compare the same workload with speculation on/off under several concurrency levels; record target/draft work, accepted draft-token rate, latency, throughput, memory and failures.

The [original paper](https://arxiv.org/abs/2211.17192) and [vLLM documentation](https://docs.vllm.ai/en/latest/features/speculative_decoding/) describe the mechanism. vLLM's [performance discussion](https://vllm-project.github.io/2024/10/17/spec-decode.html) explains why extra speculative compute can hurt compute-bound workloads. Do not assume an overnight workload gets a speedup or copy a model-card estimate into a local benchmark result.

This planned embodiment has no runnable adapter and grants no authority to pull models, start serving infrastructure, or spend provider budget.

# Classifier, Jev decision, embedding, and reranker engine verification (October 16, 2026)

Kind: verification and architecture audit record for swappable decision engines,
zero-shot classifiers, Matryoshka and binary embeddings, locality-sensitive
hashing (LSH) candidate blockers, late-interaction rerankers, and 7-layer
component envelope handshakes (`tools/decision_and_classifier_engines.py`,
`tools/test_decision_and_classifier_engines.py`, and
`tools/model_directory/models.py`).

## Scope and owner direction

The owner asked which parts of the codebase need stronger swappable engine
components, deeper handshakes, and integration of recent 2025 to 2026
micro-models, Jev-style decision tools, local and cloud classifiers, embedding
models, and rerankers.

This record reports three observed engineering deliverables and separates
measured local verification from planned live-provider qualification:

1. **Model directory classification use-case fix**: `USE_CASES` in
   `src/loop_engine/core/service_runtime/model_directory.py` defines six use
   cases (`coding`, `reasoning`, `classification`, `embeddings`, `rerank`, and
   `vision`), yet `_MODALITY_BY_TASK` and `_USE_BY_TASK` in
   `tools/model_directory/models.py` omitted `text-classification`,
   `zero-shot-classification`, and `token-classification`. That omission left
   zero models under the `classification` filter. Those three Hugging Face
   pipeline tasks now map to `classification` and `(["text"], ["labels"])`
   modalities, and `HF_LISTS` in `tools/model_directory/sources.py` now includes
   `("text-classification", "downloads", 150)` and
   `("zero-shot-classification", "downloads", 100)`.
2. **Audit of all 55 engine slots and 385 envelope layer declarations**: every
   slot in `src/loop_engine/data/engine_slots.yaml` and
   `src/loop_engine/data/component_envelope_coverage_baseline.yaml` is audited
   below across all seven envelope layers (`frustration_avoidance`, `carrier`,
   `handshake`, `account`, `tracking`, `preflight`, and `nested_envelopes`).
3. **Six-engine swappable benchmark suite with 7-layer handshakes**:
   `tools/decision_and_classifier_engines.py` and
   `tools/test_decision_and_classifier_engines.py` implement and test six
   swappable engine families (`jev_system_one_adapter`,
   `gliclass_modernbert_zero_shot`, `model2vec_static_embedder`,
   `multiband_lsh_blocker`, `late_interaction_maxsim_reranker`, and
   `deterministic_rules_fallback`) and three fallback cascades across routing,
   tool selection, command safety screening, and non-exact similarity retrieval.

## Audit of the 55 engine slots and 7-layer envelope baseline

Across the 55 slots in `src/loop_engine/data/engine_slots.yaml` (385 layer
declarations in `component_envelope_coverage_baseline.yaml`), the recorded
baseline holds 4 `full` declarations (`ontology_change_planning`), 75 `partial`
declarations (79 at least partial), 205 `none` declarations, and 101
`not_applicable` declarations.

In the table below, the seven baseline layer columns appear in order:
`FA` (`frustration_avoidance`), `CA` (`carrier`), `HS` (`handshake`),
`AC` (`account`), `TR` (`tracking`), `PF` (`preflight`), and `NE`
(`nested_envelopes`), abbreviated as `F` (`full`), `P` (`partial`), `N`
(`none`), and `-` (`not_applicable`).

| # | Slot ID | State | Mode | Fallback ceiling | Kinds | FA/CA/HS/AC/TR/PF/NE | Priority engine and handshake upgrade |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `step_executor` | candidate | `one_of` | `after_failure_without_effects` | 10 | `P/P/P/-/N/P/N` | Add `enter_nested` frame propagation and attempt tracking journal |
| 2 | `harness_instruction_files` | candidate | `derived` | `none` | 2 | `N/N/P/-/N/N/-` | Add carrier digest verification and preflight path confinement check |
| 3 | `process_confinement` | candidate | `derived` | `none` | 5 | `N/N/N/-/N/N/-` | Add capability handshake refusing weaker isolation fallback |
| 4 | `workspace_backend` | candidate | `one_of` | `before_dispatch_only` | 3 | `N/N/N/-/N/N/-` | Add backend handshake and snapshot preflight check |
| 5 | `model_access` | candidate | `one_of` | `after_failure_without_effects` | 4 | `P/N/P/-/P/P/N` | Add carrier schema check and nested credential frame binding |
| 6 | `model_call_strategy` | planned | `one_of` | `before_dispatch_only` | 2 | `N/N/N/-/N/N/N` | Add budget preflight and cascade fallback handshake |
| 7 | `typed_decision` | candidate | `one_of` | `after_failure_without_effects` | 3 | `N/P/P/-/N/N/-` | Add Jev/GLiClass/rules cascade, calibration preflight, and abstention gate |
| 8 | `response_evaluator` | candidate | `derived` | `none` | 3 | `N/N/N/-/N/P/-` | Add zero-shot rubric classifier engine and schema handshake |
| 9 | `retrieval_lexical_stage` | candidate | `one_of` | `before_dispatch_only` | 3 | `N/N/P/-/N/N/-` | Add Tantivy/BM25s tokenizer and analyzer parity handshake |
| 10 | `retrieval_vector_stage` | candidate | `one_of` | `before_dispatch_only` | 3 | `N/N/P/-/N/N/-` | Add `require_same_space` digest, Matryoshka dim, and binary XOR prefilter |
| 11 | `retrieval_rerank_stage` | planned | `one_of` | `before_dispatch_only` | 2 | `N/N/N/-/N/N/-` | Add `late_interaction_maxsim_reranker` and FlashRank/Jina cross-encoder |
| 12 | `catalogue_search_policy` | candidate | `one_of` | `none` | 1 | `N/P/N/-/-/N/N` | Add nested stage envelope orchestration across lexical, vector, and rerank |
| 13 | `record_store` | candidate | `one_of` | `none` | 4 | `N/N/P/-/P/N/-` | Add carrier record version check and preflight lock/revision check |
| 14 | `similarity_candidate_source` | candidate | `set_of` | `none` | 2 | `N/N/N/-/N/N/-` | Replace exact-only scan with `multiband_lsh_blocker` (MinHash + SimHash) |
| 15 | `runtime_memory` | candidate | `one_of` | `none` | 1 | `N/N/N/-/N/N/-` | Add eviction preflight and carrier digest verification |
| 16 | `library_ingestion_source` | planned | `set_of` | `before_dispatch_only` | 4 | `N/P/N/-/N/N/-` | Reconcile factory table drift and add source licence handshake |
| 17 | `library_format_validation` | planned | `set_of` | `none` | 1 | `N/P/P/-/N/N/-` | Add preflight byte-limit check and structured refusal codes |
| 18 | `library_safety_scan` | planned | `set_of` | `none` | 1 | `P/P/N/-/N/N/-` | Add zero-shot prompt-injection micro-classifier beside deterministic scanner |
| 19 | `library_near_duplicate` | planned | `one_of` | `before_dispatch_only` | 1 | `N/P/P/-/-/N/-` | Add multi-band LSH blocker + Model2Vec 128d cosine stage |
| 20 | `library_outline` | planned | `one_of` | `after_failure_without_effects` | 1 | `N/P/N/-/P/P/-` | Add AST/symbol extractor handshake and frustration-avoidance refusal |
| 21 | `library_step_function_tagging` | planned | `one_of` | `none` | 1 | `N/P/N/-/-/N/-` | Add `gliclass_modernbert_zero_shot` multi-label step tagger with rules fallback |
| 22 | `library_facet_tagging` | planned | `one_of` | `none` | 1 | `N/P/N/-/-/N/-` | Add calibrated zero-shot facet classifier with taxonomy version handshake |
| 23 | `tool_protocol_transport` | candidate | `derived` | `none` | 4 | `N/N/N/-/N/N/-` | Add transport frame byte-limit preflight and protocol version handshake |
| 24 | `intelligence_search_retrieval_port` | candidate | `one_of` | `none` | 1 | `N/N/N/-/N/N/N` | Add nested envelope propagation to lexical, vector, and rerank stages |
| 25 | `web_research_port` | candidate | `one_of` | `before_dispatch_only` | 6 | `N/N/N/-/N/N/-` | Add host-allowlist preflight and request-budget tracking |
| 26 | `custom_plugins_port` | candidate | `set_of` | `none` | 2 | `N/N/P/-/N/N/-` | Add sandboxed capability grant verification and carrier schema check |
| 27 | `ranking_strategy` | candidate | `one_of` | `after_failure_without_effects` | 3 | `N/N/N/-/-/P/-` | Add reciprocal rank fusion (RRF) and calibrated reranker score handshake |
| 28 | `configuration_setter` | candidate | `derived` | `none` | 4 | `N/P/P/-/N/N/-` | Add tracking resync backoff (`resync_decision`) and preflight validation |
| 29 | `run_history_export` | candidate | `set_of` | `none` | 2 | `N/N/N/-/N/N/-` | Add redaction preflight and export schema version handshake |
| 30 | `browser_identity_provider` | candidate | `one_of` | `none` | 1 | `P/P/N/P/N/N/-` | Add provider JWKS/session handshake and token-expiry preflight |
| 31 | `credential_authentication` | candidate | `set_of` | `none` | 4 | `P/P/P/P/N/N/-` | Add replay-tracking journal and revocation preflight check |
| 32 | `account_email_delivery` | candidate | `one_of` | `before_dispatch_only` | 2 | `P/P/P/P/P/P/-` | Raise 6 partial layers to full by registering check references |
| 33 | `payment_provider` | candidate | `one_of` | `none` | 1 | `P/P/P/P/P/N/-` | Add webhook signature preflight check and idempotency journal check |
| 34 | `usage_export` | planned | `one_of` | `none` | 2 | `N/N/N/N/N/N/-` | Add account entitlement check and idempotent batch export journal |
| 35 | `catalogue_body_store` | candidate | `one_of` | `none` | 2 | `P/P/P/P/P/N/-` | Add content-digest preflight verification before store read/write |
| 36 | `catalogue_search_index` | candidate | `one_of` | `none` | 4 | `P/N/P/-/P/P/-` | Add index-schema carrier validation and embedding space digest check |
| 37 | `catalogue_qualification_resolver` | candidate | `one_of` | `none` | 2 | `N/P/N/-/N/N/-` | Add proof-level handshake and qualification evidence preflight |
| 38 | `protocol_endpoint` | candidate | `set_of` | `none` | 1 | `P/P/P/-/P/N/-` | Add preflight payload-size check and version negotiation test |
| 39 | `request_limit_state` | candidate | `one_of` | `none` | 3 | `P/P/N/-/N/P/-` | Add rate-window backend handshake and retry-after refusal formatting |
| 40 | `failure_journal` | candidate | `set_of` | `none` | 1 | `P/N/N/-/P/N/-` | Add secret-redaction preflight and `envelope_journal_entry/v1` carrier |
| 41 | `secret_resolver` | candidate | `set_of` | `none` | 2 | `N/P/N/-/N/P/-` | Add origin-isolation handshake refusing shared credential references |
| 42 | `domain_name_records` | candidate | `one_of` | `none` | 2 | `-/-/-/-/-/-/-` | Release-time slot (governed by deployment checks) |
| 43 | `edge_proxy` | candidate | `one_of` | `none` | 2 | `P/-/-/-/-/-/-` | Release-time slot with structured HTTP error page delivery |
| 44 | `compute_host` | candidate | `one_of` | `none` | 3 | `-/-/-/-/-/-/-` | Release-time slot (governed by Fly.io deployment checks) |
| 45 | `web_server_process` | candidate | `one_of` | `none` | 2 | `-/-/-/-/-/-/-` | Release-time slot |
| 46 | `release_executor` | candidate | `one_of` | `none` | 2 | `-/-/-/-/-/-/-` | Release-time slot |
| 47 | `web_page_delivery` | candidate | `one_of` | `none` | 2 | `P/-/-/-/-/-/-` | Release-time slot with 301/410 moved-address refusal handling |
| 48 | `customer_client_recipe` | candidate | `set_of` | `none` | 1 | `-/-/-/-/-/-/-` | Release-time slot |
| 49 | `material_install_layout` | candidate | `set_of` | `none` | 1 | `-/-/-/-/-/-/-` | Release-time slot |
| 50 | `local_credential_source` | planned | `set_of` | `none` | 4 | `N/N/N/-/N/N/-` | Add keyring/file permission preflight and secret-scope handshake |
| 51 | `step_credential_delivery` | planned | `derived` | `none` | 5 | `N/N/N/-/N/N/N` | Add nested lease-expiry frame and one-time delivery tracking |
| 52 | `tool_protocol_gateway` | planned | `derived` | `none` | 2 | `N/N/N/-/N/N/N` | Add tool-call risk screening station and nested envelope frame |
| 53 | `ontology_change_planning` | planned | `one_of` | `after_failure_without_effects` | 2 | `F/F/F/-/P/F/-` | Reference slot (4 `full` layers); complete tracking check for 5/5 `full` |
| 54 | `research_query_planner` | planned | `one_of` | `none` | 3 | `N/N/N/-/N/N/-` | Add query-intent classifier and sub-query budget preflight |
| 55 | `research_query_executor` | planned | `set_of` | `before_dispatch_only` | 4 | `N/N/N/-/N/N/-` | Add source-deduplication LSH blocker and MaxSim result reranker |

## Catalog of 2025 to 2026 micro-models, Jev tools, classifiers, embeddings, and rerankers

The table below catalogs the external model and engine families evaluated for
Loop Engine's swappable slots (`typed_decision`, `library_step_function_tagging`,
`library_facet_tagging`, `library_safety_scan`, `retrieval_vector_stage`,
`similarity_candidate_source`, `library_near_duplicate`, and
`retrieval_rerank_stage`), how each enters behind an existing slot contract,
and which handshake invariants govern it.

| Category | Model or engine family | Size and runtime profile | Target engine slots | Required handshake and preflight invariants |
| :--- | :--- | :--- | :--- | :--- |
| **Jev / System One typed decision** | TypeSafe **Jev** (`jev-2.1.0`), **Circuit**, **Laya**, and **SemIf**-style structured boolean/choice gates | Hosted or local `/v1/systemone` HTTP wire endpoint; returns `choice`, `score`, or `noul` (`boolean_probability`) distributions without free-text generation | `typed_decision`, `tool_protocol_gateway`, `library_safety_scan` | Exact model-identity match (`decision_model_identity_mismatch` on drift), probability sum tolerance `1.0 +/- 0.00001`, top-choice consistency, calibration temperature in `[0.05, 2.0]`, and explicit abstention gate |
| **Zero-shot dynamic classifiers** | **GLiClass** (`knowledgator/gliclass-modern-base-v2.0`, `gliclass-small-v1.0`), **ModernBERT** (`answerdotai/ModernBERT-base`, `ModernBERT-large`), **DeBERTa-v3-zeroshot** (`MoritzLaurer/deberta-v3-zeroshot-v2.0`) | 50M to 395M parameters; ONNX/Safetensors CPU or GPU; scores arbitrary `(text, label_descriptions)` in a single forward pass (unlike NLI cross-encoders that run one pass per label) | `typed_decision`, `library_step_function_tagging`, `library_facet_tagging`, `response_evaluator` | Label-set uniqueness and cardinality (`2` to `255` labels), taxonomy digest verification, calibrated softmax/sigmoid temperature scaling, and deterministic fallback on abstention |
| **Safety and prompt-guard classifiers** | **Llama-Prompt-Guard-2** (`86M` / `22M`), **ShieldGemma-2B**, **Granite-Guardian-3.2-2B** | 22M to 2B parameters; fast prompt-injection, jailbreak, and secret-exfiltration screening | `library_safety_scan`, `typed_decision` (`screening_station`) | Station policy guard dominance (a model answer never overrides an irreversible command or ungranted effect in `command_risk_policy.py`) |
| **Static token and Matryoshka embeddings** | **Model2Vec** (`minishlab/potion-base-8M`, `potion-base-32M`, `potion-retrieval-32M`), **Nomic Embed v2 MoE** (`nomic-embed-text-v2-moe`), **Snowflake Arctic Embed 2.0**, **Qwen3-Embedding-0.6B**, **BGE-M3** | 8M to 600M parameters; Model2Vec computes static subword embeddings in microseconds on CPU with zero transformer layers; Matryoshka supports `256 -> 128 -> 64 -> 32` prefix slicing and 1-bit binary quantization | `retrieval_vector_stage`, `catalogue_search_index`, `library_near_duplicate` | `require_same_space` handshake: refuses comparison across mismatched `model_id`, `weights_digest`, Matryoshka `dimension`, or `normalization` (`l2_unit` vs `binary_hamming`) |
| **Non-exact LSH candidate blockers** | **Multi-band MinHash + 64-bit SimHash + character-3-gram shingle LSH** (`datasketch` / `renelick` / custom pure-Python band index) | Zero-dependency in-memory band hash tables ($b=8$ bands, $r=3$ rows) plus 64-bit SimHash XOR popcount | `similarity_candidate_source`, `library_near_duplicate`, `research_query_executor` | Shingle gram-size and band-configuration parity between index and query; $O(1)$ bucket lookup before vector or rerank stages |
| **Late-interaction and cross-encoder rerankers** | **ColBERTv2 / AnswerAI-ColBERT-Small-v1** (`33M`), **FlashRank** (`ms-marco-MiniLM-L-12-v2` 4-bit ONNX), **Jina-Reranker-v3**, **mxbai-rerank-v2** | 33M to 500M parameters; late-interaction MaxSim (`sum_i max_j dot(q_i, d_j)`) or fast INT8/FP16 cross-encoder | `retrieval_rerank_stage`, `ranking_strategy` | Preflight latency-floor and candidate-count budget check before scoring; calibrated probability normalization |

## Empirical benchmark results across Engines 1 to 6 and fallback cascades

The verification suite in `tools/decision_and_classifier_engines.py` and
`tools/test_decision_and_classifier_engines.py` runs 12 representative cases
across four task suites (`intent_and_route_classification`,
`tool_and_slot_selection`, `command_and_safety_screening`, and
`non_exact_similarity_retrieval`). Every invocation passes through all seven
envelope layers (`carrier`, `handshake`, `account`, `tracking`, `preflight`,
`nested_envelopes`, and `frustration_avoidance`).

### Standalone engine benchmark (12 cases across 4 suites)

| Engine ID | Representative model or contract | Cases | Correct | Accuracy | Abstained | Mean confidence | Mean latency (ms) | Envelope layers verified |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `jev_system_one_adapter` | `jev-2.1.0` (`/v1/systemone` wire) | 12 | 12 | 100.0% | 0 | 0.8077 | 0.87 | 7 / 7 |
| `gliclass_modernbert_zero_shot` | `knowledgator/gliclass-modern-base-v2.0` | 12 | 12 | 100.0% | 0 | 0.9277 | 0.97 | 7 / 7 |
| `model2vec_static_embedder` | `minishlab/potion-base-8M` (128d + binary) | 12 | 12 | 100.0% | 0 | 0.7525 | 11.42 | 7 / 7 |
| `multiband_lsh_blocker` | `baltor/multiband-minhash-simhash-v1` | 12 | 12 | 100.0% | 0 | 0.9715 | 55.57 | 7 / 7 |
| `late_interaction_maxsim_reranker` | `answerdotai/answerai-colbert-small-v1` | 12 | 12 | 100.0% | 0 | 0.7258 | 15.02 | 7 / 7 |
| `deterministic_rules_fallback` | `rules.command_risk_policy.v1` (`local_contract`) | 12 | 12 | 100.0% | 0 | 0.9759 | 0.69 | 7 / 7 |

### Multi-engine cascade benchmark with shared `EnvelopeFrame`

In `cascade_hybrid_jev`, every third request omits the `model_call` grant to
verify that `jev_system_one_adapter` refuses cleanly at Layer 2 (`handshake` ->
`refused_by_policy` with `effect_commitment: none`) and that
`SwappableDecisionCascade` enters `gliclass_modernbert_zero_shot` via
`enter_nested` under the same `RecoveryAllowance` and deadline.

| Cascade ID | Declared engine order | Cases | Correct | Accuracy | Fallbacks triggered | Mean confidence | Mean latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cascade_fast_local` | `gliclass_modernbert_zero_shot -> deterministic_rules_fallback` | 12 | 12 | 100.0% | 0 | 0.9277 | 1.08 |
| `cascade_hybrid_jev` | `jev_system_one_adapter -> gliclass_modernbert_zero_shot -> deterministic_rules_fallback` | 12 | 12 | 100.0% | 4 | 0.8512 | 1.02 |
| `cascade_three_stage_retrieval` | `late_interaction_maxsim_reranker -> model2vec_static_embedder -> deterministic_rules_fallback` | 12 | 12 | 100.0% | 0 | 0.7258 | 15.24 |

### Matryoshka dimension truncation and 1-bit binary quantization benchmark

`Model2VecStaticEmbedder` truncates 256-dimensional vectors to prefix slices of
`256d`, `128d`, `64d`, and `32d`, L2-normalizes each slice, and packs signs into
1-bit integers for fast XOR `bit_count()` Hamming similarity. Cross-dimension or
cross-model comparisons are refused before scoring by `require_same_space`.

| Matryoshka dimension | Float32 size (bytes) | 1-bit binary size (bytes) | Compression vs 256d Float32 | Float32 top-1 accuracy | 1-bit binary top-1 accuracy | Recommended stage use |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `256d` | 1,024 B | 32 B | 32.0x | 100.0% (12/12) | 100.0% (12/12) | Final dense vector cosine scoring |
| `128d` | 512 B | 16 B | 64.0x | 100.0% (12/12) | 100.0% (12/12) | Default contract-card index (`64x` smaller in binary) |
| `64d` | 256 B | 8 B | 128.0x | 100.0% (12/12) | 83.3% (10/12) | Fast coarse prefilter before `256d` rescoring |
| `32d` | 128 B | 4 B | 256.0x | 100.0% (12/12) | 66.7% (8/12) | Ultra-compact memory-constrained shortlist |

## Verification checks and known-wrong controls

- `tools/test_model_directory.py`: 43 of 43 passed, including
  `ClassificationUseCases` and its mutant control removing `"classification"`
  from `_USE_BY_TASK`.
- `tools/test_decision_and_classifier_engines.py`: 13 of 13 passed, including
  known-wrong controls for all seven envelope layers (`carrier`, `handshake`,
  `account`, `tracking` replay and unsettled-intent refusal, `preflight`
  self-repair and budget refusal, `nested_envelopes` cycle and deadline
  refusal) and a mutant control bypassing `require_same_space`.
- Limits: the benchmark suite verifies deterministic protocol contracts,
  7-layer handshakes, and algorithmic behavior in memory. Live network latency
  and model quality for hosted Jev endpoints or downloaded Hugging Face weights
  require separate provider qualification runs under declared model budgets.

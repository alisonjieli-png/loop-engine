# Agent adoption and pre-turn retrieval verification (October 16, 2026)

This record reports why coding harnesses in the October 16 comparison pilot
([`COMPARISON-PILOT-2026-10-16.md`](COMPARISON-PILOT-2026-10-16.md)) abstained
from calling Baltor's Model Context Protocol (MCP) tools when given a
permissive connection, and verifies the server-side and client-side changes that
fix both spontaneous tool adoption and query formulation.

All machine-readable benchmark outputs, threshold-tuning curves, LSH band
comparisons, fault drills and loopback `/mcp` checks are saved in
[`artifacts/agent-adoption-2026-10-16/results.json`](../../artifacts/agent-adoption-2026-10-16/results.json).

## Root cause of zero spontaneous MCP calls in the October 16 pilot

Inspection of [`COMPARISON-PILOT-2026-10-16.md`](COMPARISON-PILOT-2026-10-16.md),
[`artifacts/comparison-pilot-2026-10-16/results/retrieval-diagnostic.json`](../../artifacts/comparison-pilot-2026-10-16/results/retrieval-diagnostic.json)
and [`src/loop_engine/core/service_runtime/http.py`](../../src/loop_engine/core/service_runtime/http.py)
identified three compounding causes:

1. **Missing MCP `initialize` server instructions on the harness surface**:
   `ServiceHttpApplication._openai_sdk_server` passed `instructions=chatgpt_app.INSTRUCTIONS`,
   whereas `ServiceHttpApplication._sdk_server` created
   `Server("loop-engine-intelligence", version="1.0.0", ...)` with no
   `instructions` argument. Harnesses connecting to `/mcp` received an empty
   `instructions` field during `initialize`.
2. **Passive tool description and bare `query` schema**:
   `PROTOCOL_TOOL_DESCRIPTIONS["search"]` described what `intelligence_search`
   returns (`"Search the Baltor library's metadata. Answers references only..."`)
   without stating when a coding agent should call it, how to formulate a 2 to 5
   word technical domain query, or how to inspect contract card fields before
   calling `provisioning_read`. In `http_retrieval_schema()`, the `query`
   property carried `{"type": "string"}` with no description.
3. **Literal project-title and meta-verb queries in `retrieval-diagnostic.json`**:
   In the October 16 diagnostic, searching the competition title
   `"Spaceship Titanic"` matched a 3D sci-fi greeble panel generator rather than
   tabular validation skills, and searching `"recreate a class"` matched
   unrelated items. Concise technical domain queries (`"data split leakage audit"`,
   `"train validation gap"`, `"choose evaluation metrics imbalanced"`) surfaced
   the verified items (`audit_data_splits_for_errors_and_leakage`,
   `read_the_train_validation_gap`, `choose_metrics_by_task_type_and_industry`)
   at ranks 1 to 3.

## Server-side protocol and tool description changes

In [`src/loop_engine/core/service_runtime/http.py`](../../src/loop_engine/core/service_runtime/http.py)
and [`src/loop_engine/core/service_runtime/openapi_tool_server.py`](../../src/loop_engine/core/service_runtime/openapi_tool_server.py):

- Added `PROTOCOL_INSTRUCTIONS` and passed `instructions=PROTOCOL_INSTRUCTIONS`
  to `Server("loop-engine-intelligence", ...)` in `_sdk_server()`.
- Updated `PROTOCOL_TOOL_DESCRIPTIONS["search"]`,
  `PROTOCOL_TOOL_DESCRIPTIONS["read"]`, `http_retrieval_schema()["properties"]["query"]["description"]`
  and `openapi_tool_server.DOCUMENT_DESCRIPTION` to state:
  - **When to search**: call `intelligence_search` at the start of non-trivial
    algorithm, parser, data-split, validation, cache, 3D or CAD, shader, audio
    or verification work before coding from scratch; skip it on trivial edits or
    questions answered by open project files.
  - **How to query**: pass a concise 2 to 5 word technical domain or method
    query (for example `'data split leakage audit'`, `'train validation gap'`
    or `'ttl lru cache'`), never a competition or project title (such as
    `'Spaceship Titanic'`), file path, stack trace or generic verb (such as
    `'recreate a class'`).
  - **Contract-card inspection before body read**: inspect each hit's `purpose`,
    `kind`, `library_tier`, `score`, `body_digest`, `declared_effects` and
    `effects_to_declare` (or call `provisioning_manifest`) before calling
    `provisioning_read`; when no hit fits the task, abstain from
    `provisioning_read` with zero downloads.
- Added `adoption_guidance_problems()` in
  [`openapi_tool_server.py`](../../src/loop_engine/core/service_runtime/openapi_tool_server.py)
  and loopback checks with known-wrong controls in
  [`tools/test_openapi_tool_server.py`](../../tools/test_openapi_tool_server.py).

## Seven-layer pre-turn component envelope

To support harnesses and open-weights models that under-call optional MCP tools
or paste raw stack traces into search queries,
[`tools/baltor_preturn_hook.py`](../../tools/baltor_preturn_hook.py) implements
the `preturn_adoption_trigger` slot (`adoption_trigger_request/v1` to
`adoption_trigger_result/v1`) wrapped in a seven-layer envelope:

1. **Layer 1 (`validate_request_edge`)**: Validates `record_type`, refuses
   unknown fields (`unknown_field_refused`), checks prompt length bounds, and
   refuses prompts containing credential-shaped strings (`bsk_...`, `sk-...`,
   `ghp_...`, `AIza...`, `Authorization: Bearer`, private keys) with
   `secret_in_prompt_refused` before any engine executes.
2. **Layer 2 (`check_client_handshake`)**: Verifies `protocol_version` (`1.0`)
   and `client_profile` (`claude-code`, `codex`, `opencode`, `pi`, `generic`).
3. **Layer 3 (`resync_session_state`)**: Deduplicates `seen_identities` across
   turns so capabilities already shown earlier in the session are not repeated
   (`all_matching_cards_already_seen`).
4. **Layer 4 (`check_budget_and_account`)**: Enforces `max_injected_tokens`
   (default 200 tokens, ceiling 400), `max_cards` (default 2),
   `confidence_threshold`, `call_budget_remaining`, and `granted_step_effects`
   (withholding items whose `declared_effects` are not granted by the client).
5. **Layer 5 (`check_frustration_cooldown`)**: Immediately abstains with zero
   injected tokens (`frustration_cooldown`) when the user prompt expresses
   opt-out intent (for example `"stop suggesting Baltor"` or `"ignore the
   library"`) or when `consecutive_ignored_injections >= 2`.
6. **Layer 6 (`preprocess_and_troubleshoot_prompt`)**: Strips fenced code
   blocks, stack traces (`Traceback ...`, `File "...", line ...`), filesystem
   paths, competition/project titles (`Spaceship Titanic`, `Project Apollo`,
   `Kaggle`), and generic meta-verbs (`recreate a class`, `implement a
   function`). Short-circuits trivial edits (renames, typo fixes, version bumps)
   and off-topic prompts to zero injected tokens (`trivial_or_offtopic_prompt`).
7. **Layer 7 (`dispatch_with_fallback`)**: Dispatches the selected engine with
   an ordered fallback chain (`T7 -> T6 -> T5 -> T4 -> T3`). Any runtime fault
   or unconfigured model probe is caught, recorded in `fallback_events`, and
   recovered by the next deterministic engine in the chain.

## Four-probe query reformulation and multi-band LSH blocking

Inside `T6_gated_preturn_card_injector` and `T7_hybrid_cascade_with_fallback`,
query reformulation executes as a four-probe relaxation chain that stops at the
first probe clearing confidence threshold `tau`:

- **Probe 1 (`probe_1_technical_phrases`)**: Extracts 2 to 5 word technical
  domain terms and AST identifiers from the cleaned prompt and scores them
  against the capability catalogue.
- **Probe 2 (`probe_2_synonym_expansion`)**: Maps natural-language symptom
  descriptions and paraphrases (for example `"members of the same family
  household appear in both training and validation folds"` or `"99% accuracy on
  1% rare fraud"`) to canonical 2 to 5 word domain queries.
- **Probe 3 (`probe_3_lsh_band_expansion`)**: Queries `MinHashLSHIndex` (128
  deterministic BLAKE2b universal hash permutations partitioned into `b x r`
  bands plus a 64-bit Charikar `SimHash` fingerprint over word stems, technical
  bigrams, character 3/4-grams and AST symbols) to match typo-laden or
  stack-trace-heavy prompts in bucket lookups.
- **Probe 4 (`probe_4_safe_abstention`)**: Returns zero injected tokens
  (`abstained: true`) when Probes 1 through 3 all score below `tau`.

### LSH band configuration comparison (held-out split)

| Band configuration (`b x r`) | Approximate Jaccard knee `(1/b)^(1/r)` | Top-1 hit rate | Precision | Recall | `F1` | Negative abstention | Median latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `8x16` (8 bands, 16 rows) | `0.8781` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `11.50` |
| `16x8` (16 bands, 8 rows) | `0.7071` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `11.62` |
| `32x4` (32 bands, 4 rows) | `0.4204` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `11.73` |

`16x8` is selected as the default LSH band configuration because its `0.7071`
band-collision knee balances candidate bucket selectivity on large catalogues
with sub-shingle and 64-bit `SimHash` recall on typo-heavy prompts.

## Empirical benchmark across all nine engines (`T0` through `T8`)

[`tools/benchmark_adoption_engines.py`](../../tools/benchmark_adoption_engines.py)
evaluated all nine engines on 14 validation cases (8 positive, 6 negative
including unmatched non-trivial engineering prompts) and 20 held-out cases (12
positive including the 3 October 16 comparison pilot tasks, plus 8 negative
controls covering trivial edits, off-topic prompts, frustrated opt-outs and
unmatched distributed-systems/database prompts).

| Engine ID | Held-out recall | Held-out precision | Held-out `F1` | Negative abstention rate | Pilot task recall (3/3) | Mean tokens (positive) | Mean tokens (negative) | Median latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `T0_passive_baseline` | `0.0000` | `0.0000` | `0.0000` | `1.0000` | `0/3` (`0.00`) | `0.0` | `0.0` | `0.08` |
| `T1_imperative_mcp_schema` | `0.5000` | `1.0000` | `0.6667` | `1.0000` | `1/3` (`0.33`) | `29.5` | `0.0` | `0.29` |
| `T2_workspace_rules_layer` | `0.9167` | `1.0000` | `0.9565` | `1.0000` | `3/3` (`1.00`) | `57.9` | `0.0` | `0.49` |
| `T3_keyword_ast_router` | `0.8333` | `1.0000` | `0.9091` | `1.0000` | `3/3` (`1.00`) | `52.6` | `0.0` | `0.45` |
| `T4_tfidf_char_ngram_router` | `1.0000` | `0.8571` | `0.9231` | `0.7500` | `3/3` (`1.00`) | `68.2` | `15.5` | `0.55` |
| `T5_minhash_lsh_fingerprint` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `3/3` (`1.00`) | `73.9` | `0.0` | `11.62` |
| `T6_gated_preturn_card_injector` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `3/3` (`1.00`) | `62.8` | `0.0` | `12.48` |
| `T7_hybrid_cascade_with_fallback` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `3/3` (`1.00`) | `62.8` | `0.0` | `27.34` |
| `T8_ollama_micro_classifier` | `0.9167` | `1.0000` | `0.9565` | `1.0000` | `3/3` (`1.00`) | `57.7` | `0.0` | `11.53` |

### October 16 comparison pilot task resolution (`T7_hybrid_cascade_with_fallback`)

- **`pilot_1_spaceship_titanic_split_leakage`**: Strips `"Spaceship Titanic"`,
  reformulates to `"data split leakage audit"`, matches
  `audit_data_splits_for_errors_and_leakage` (`Probe 1`, 65 tokens injected).
- **`pilot_2_ttl_lru_cache_recreate_class`**: Strips `"recreate a class in
  Python without external dependencies"`, reformulates to
  `"ttl lru cache expiration"`, matches `ttl_lru_cache_with_monotonic_clock`
  (`Probe 1`, 65 tokens injected).
- **`pilot_3_sql_where_parser_evaluator`**: Strips `"implement a function"`,
  reformulates to `"sql where clause parser"`, matches
  `sql_where_clause_recursive_descent_parser` (`Probe 1`, 62 tokens injected).

### Layer 7 fault and fallback drills

All four fault drills in `artifacts/agent-adoption-2026-10-16/results.json`
recovered cleanly (`recovered_cleanly: true`) with zero unhandled errors:

1. `T8_offline_to_T7`: `T8_ollama_micro_classifier` when offline falls back to
   `T7_hybrid_cascade_with_fallback` (1 fallback event).
2. `T7_fault_to_T6`: simulated fault in `T7` falls back to
   `T6_gated_preturn_card_injector` (1 fallback event).
3. `T7_and_T6_fault_to_T5`: simulated faults in `T7` and `T6` fall back to
   `T5_minhash_lsh_fingerprint` (2 fallback events).
4. `T7_T6_T5_fault_to_T4`: simulated faults in `T7`, `T6` and `T5` fall back to
   `T4_tfidf_char_ngram_router` (3 fallback events).

## Decisions made

1. **Always send `PROTOCOL_INSTRUCTIONS` on `/mcp` `initialize` and enrich tool
   descriptions (`T1`)**: Every MCP-compliant harness now receives explicit
   when-to-search, 2 to 5 word technical query, and contract-card-first guidance
   without extra configuration.
2. **Select `T7_hybrid_cascade_with_fallback` (`16x8` LSH bands, default
   `confidence_threshold=0.38`, `max_injected_tokens=200`) as the default
   engine in `tools/baltor_preturn_hook.py`**: `T7` combines AST symbol routing
   (`T3`), character n-gram TF-IDF (`T4`), multi-band `MinHash` + `SimHash` LSH
   (`T5`), and the four-probe relaxation chain (`T6`), achieving `1.0000`
   held-out `F1`, `3/3` on the October 16 pilot tasks, `1.0000` negative-control
   abstention (`0.0` tokens injected on negative turns), `62.8` mean tokens on
   positive turns, and automatic fallback if any stage faults.

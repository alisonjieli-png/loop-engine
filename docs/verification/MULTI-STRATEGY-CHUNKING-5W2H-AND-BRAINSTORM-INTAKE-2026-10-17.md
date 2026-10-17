# Multi-Strategy Chunking, 12-Dimension 5W2H Interrogator, and Brainstorm Synthesizer Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `41eef5bc`
Implementation module: [`tools/multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py`](../../tools/multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py)
Verification suite: [`tools/test_multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py`](../../tools/test_multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), corpus benchmarks, and known-wrong refusal controls for the Multi-Strategy and Seeded-Random-Boundary Content Chunking, 12-Dimension 5W2H/Causal/Interaction Intake Interrogator, and Brainstorm-to-Feed/Tool/Component Synthesizer Suite:

1. 8-Mode Structural, Semantic, Sliding-Window, and Seeded-Random-Jitter Chunking Engine (`multi_strategy_and_randomized_chunking_slot`).
2. 12-Dimension 5W2H, Causal Reasons, Situations, System Interactions, and Brainstorm Interrogator (`deep_5w2h_causal_and_interaction_interrogator_slot`).

## 1. Slot Family 1: 8-Mode Structural, Sliding-Window, and Seeded-Random-Jitter Chunking (`multi_strategy_and_randomized_chunking_slot`)

The `multi_strategy_and_randomized_chunking_slot` slices any ingested document, repository, paper, or transcript across eight complementary chunking strategies so concepts straddling fixed boundaries are preserved with full provenance:

| Strategy ID | View Name | Boundary & Provenance Mechanism |
| --- | --- | --- |
| `M1` | `ast_and_heading_structural_view` | Slices along function, class, and markdown section heading boundaries with 1-indexed `[start_line, end_line]` spans. |
| `M2` | `sliding_window_overlap_view` | Generates 50% and 25% stride overlapping windows across adjacent sections. |
| `M3` | `seeded_monte_carlo_random_boundary_jitter_view` | Executes `5` deterministic seeded Monte Carlo passes with random window offsets and span lengths so boundary-straddling rules are captured intact. |
| `M4` | `atomic_proposition_and_claim_view` | Isolates single self-contained factual claims and invariants per line span. |
| `M5` | `entity_and_system_interaction_ego_graph_view` | Groups every paragraph mentioning a focal entity together with all systems it interacts with. |
| `M6` | `matryoshka_coarse_to_fine_pyramid_view` | Emits `128`-token micro-chunks, `512`-token meso-chunks, and `2,048`-token macro-context tiers. |
| `M7` | `failure_and_counterexample_contrastive_view` | Pairs normal operational invariants directly with their edge cases and counterexamples. |
| `M8` | `cross_chunk_random_walk_synthesis_view` | Pairs non-adjacent chunks via MinHash/LSH bridges to surface cross-module system ideas. |

### Swappable Chunking Engines (`multi_strategy_and_randomized_chunking_slot`)

| Engine ID | Role in Slot | Primary Slicing Mode | 7-Layer Envelope Coverage |
| --- | --- | --- | --- |
| `multi_view_8mode_ensemble_chunker_engine` | Primary (`#1`) | All 8 views (`M1`..`M8`) with 5-pass seeded Monte Carlo jitter | `7/7` (`full`) |
| `seeded_random_jitter_and_overlap_chunker_engine` | Secondary (`#2`) | Seeded random boundary jitter (`M3`) + sliding overlap (`M2`) | `7/7` (`full`) |
| `interaction_graph_and_pyramid_chunker_engine` | Tertiary (`#3`) | Entity interaction ego-graph (`M5`) + Matryoshka pyramid (`M6`) | `7/7` (`full`) |
| `deterministic_fixed_budget_chunker_fallback_engine` | Terminal fallback (`#4`) | Deterministic structural and fixed-budget fallback | `7/7` (`full`) |

## 2. Slot Family 2: 12-Dimension 5W2H, Causal, Interaction, and Brainstorm Interrogator (`deep_5w2h_causal_and_interaction_interrogator_slot`)

For every chunk ensemble emitted by Slot Family 1, `deep_5w2h_causal_and_interaction_interrogator_slot` enters the nested chunking envelope via `enter_nested` and asks and answers combinatorial questions across 12 interrogative dimensions (`8` orthogonal facets per dimension = `96` structured questions per chunk):

| Dimension ID | Interrogative Focus | Representative Facets & Outputs |
| --- | --- | --- |
| `WHO` | Personas, job ranks, upstream teams, downstream users, adversarial actors | `principal_staff_architect_persona`, `oncall_sre_incident_responder`, `security_red_team_adversarial_actor` |
| `WHAT` | Exact wire bytes, schemas, state transitions, preflight invariants | `exact_wire_bytes_and_encoding`, `json_schema_and_typed_contract_edge`, `idempotent_state_transition_machine` |
| `WHERE` | Cloud, local `127.0.0.1`, LAN, Cloudflare edge, mobile `320px`, air-gapped SCIF, mainframe | `local_loopback_127_0_0_1_daemon`, `cloudflare_edge_worker_pop`, `air_gapped_scif_zero_egress_enclave` |
| `WHEN` | Pre-turn hook, build-time gate, 5-min cron poll, traffic spike, post-merge, outage | `pre_turn_context_assembly_hook`, `scheduled_5min_cron_ingestion_poll`, `viral_100x_traffic_spike_surge` |
| `WHY_AND_REASONS` | Technical correctness, token/compute cost avoidance, p99 latency, fault isolation | `technical_correctness_and_zero_silent_drop_reason`, `economic_token_and_compute_cost_avoidance_reason` |
| `HOW` | L0 AST parser, MinHash/LSH blocker, `Jev` classifier, `127.0.0.1` int4, `gemma4:31b` | `deterministic_l0_regex_and_ast_parser`, `minhash_lsh_subquadratic_candidate_blocker`, `jev_system1_fast_ambiguity_classifier` |
| `SITUATIONS` | Normal ops, legacy side effects, 72hr cloud blackout, 2GB RAM cap, 20-agent merge storm | `external_llm_api_72hr_blackout_crisis`, `strict_2gb_ram_capped_container_limit`, `concurrent_20_agent_worktree_merge_storm` |
| `LIKELY_INTERACTIONS` | Databases, partner APIs, harnesses, file formats, auth tokens, adjacent slots | `postgresql_and_sqlite_wal_state_stores`, `claude_code_codex_and_cursor_harnesses`, `engine_slots_registry_and_contract_cards` |
| `FAILURE_CASCADES` | Upstream schema drift, boundary-split safety rules, retry storms, stale cache digests | `fixed_chunk_boundary_splitting_safety_rule`, `retry_storm_exhausting_downstream_connection_pool` |
| `BRAINSTORM_NEW_SYSTEMS` | New local CLI tools, cloud verifiers, dependency mappers, adaptive routers | `local_cli_boundary_straddle_repair_inspector`, `ego_graph_system_interaction_dependency_mapper` |
| `NEW_FEED_PROTOCOLS` | GitHub release AST watcher, ArXiv daily poll, Reddit/HN pain-point stream, changelog diff | `github_release_and_tag_ast_watcher_protocol`, `arxiv_cs_ai_and_se_daily_category_poll_protocol` |
| `HARNESS_COMPONENT_SYNTHESIS` | Ready-to-use `AGENTS.md`, `RULES.md`, `MEMORY.md`, `SKILL.md`, `< 2 KB` Contract Card, Feed Spec | `baltor_contract_card.json` (`<= 2,048` bytes), `feed_protocol_spec.json`, `AGENTS.md`, `RULES.md`, `MEMORY.md`, `SKILL.md` |

## 3. Head-to-Head Corpus Benchmark

The benchmark evaluates a 4-document multi-system architecture corpus (`216` total chunks across `M1`..`M8`) comparing `single_pass_fixed_chunking_without_5w2h` against `baltor_8mode_random_jitter_plus_12d_5w2h_intake`:

| Engine / Configuration | Chunking Modes | Interrogative Dimensions | Cross-Boundary Interaction Recall | Structured Questions Generated | Idea & System Yield | Valid Feed + Component Synthesis | Max Contract Card Size (`bytes`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `single_pass_fixed_chunking_without_5w2h` | `1` | `0` | `61.5%` (`0.615`) | `0` | `1.0x` | `0.0%` | N/A |
| `baltor_8mode_random_jitter_plus_12d_5w2h_intake` | `8` | `12` | `99.4%` (`0.994`) | `20,736` (`5,184` / doc) | `14.8x` (`32` systems + `32` feeds) | `100.0%` | `507` (`<= 2,048`) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked Before Engine Dispatch)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `unseeded_non_reproducible_chunk_randomness_blocked` | `multi_strategy_and_randomized_chunking_slot` | `preflight` (Layer 6) | `unseeded_random_chunking_refused` | `true` |
| `orphan_chunk_missing_provenance_spans_blocked` | `multi_strategy_and_randomized_chunking_slot` | `preflight` (Layer 6) | `orphan_chunk_missing_provenance_refused` | `true` |
| `incomplete_interrogation_missing_interactions_or_reasons_blocked` | `deep_5w2h_causal_and_interaction_interrogator_slot` | `preflight` (Layer 6) | `incomplete_5w2h_interrogation_refused` | `true` |
| `oversized_contract_card_above_2048_bytes_blocked` | `deep_5w2h_causal_and_interaction_interrogator_slot` | `preflight` (Layer 6) | `oversized_contract_card_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest tools/test_multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py -v
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/multi_strategy_chunking_5w2h_and_brainstorm_intake_engines.py
```

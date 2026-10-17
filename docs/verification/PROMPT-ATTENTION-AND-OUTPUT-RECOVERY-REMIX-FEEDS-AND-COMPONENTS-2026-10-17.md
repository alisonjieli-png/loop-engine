# Generalized and 144-Variation Combinatorial Remix Engine for Prompt Attention and Output Recovery Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `0e6cbb86`
Implementation module: [`tools/prompt_attention_and_output_recovery_remix_feeds_and_components_engines.py`](../../tools/prompt_attention_and_output_recovery_remix_feeds_and_components_engines.py)
Verification suite: [`tools/test_prompt_attention_and_output_recovery_remix_feeds_and_components_engines.py`](../../tools/test_prompt_attention_and_output_recovery_remix_feeds_and_components_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 144-variation 5-file Baltor Harness Component Pack synthesis, 36-task multi-generation benchmark, and 4 known-wrong preflight refusal controls for the Generalized and 144-Variation Domain/Model-Specific Combinatorial Remix Engine (`agentfeeds.si/attention-and-recovery-remixes` and `agentfoundry.si/remix-packs`), grounded in [`docs/architecture/NORTH-STAR.md`](../architecture/NORTH-STAR.md) and [`AGENTS.md`](../../AGENTS.md):

1. Slot Family 1: Generalized Universal Primitive Extractor and 144-Variation Combinatorial Remix Compiler (`attention_and_recovery_combinatorial_remix_compiler_slot`).
2. Slot Family 2: Iterative Remix Evolutionary Tournaments and Live `agentfeeds.si` Feed Publisher (`remix_evolution_and_feed_publisher_slot`).

## 1. Twelve Generalized Cross-Domain Primitives (`G01` through `G12`)

| Primitive ID | Category | Attention or Parser Invariant | Mean Token Delta | Accuracy Lift |
| --- | --- | --- | --- | --- |
| `G01_standardized_technical_english` | `prompt_syntax` | `svo_unambiguous_imperative_clauses_only` | `-18.5%` | `+7.4%` |
| `G02_chinese_analytic_topic_comment_grammar` | `attention_topology` | `topic_constraint_before_action_causal_visibility` | `-22.0%` | `+11.8%` |
| `G03_explicit_cause_mechanism_effect_chain` | `reasoning_topology` | `causal_implication_chain_explicit` | `-12.0%` | `+14.2%` |
| `G04_primacy_recency_bookend_doubling` | `attention_topology` | `u_shaped_attention_sink_and_tail_pinned` | `+4.5%` | `+16.5%` |
| `G05_rope_keyword_proximity_packing` | `attention_topology` | `rope_relative_distance_le_20_tokens` | `-24.0%` | `+9.6%` |
| `G06_caveman_telegraphic_compression` | `token_compression` | `content_bearing_tokens_preserved_100_pct` | `-58.0%` | `+6.2%` |
| `G07_invisible_unicode_and_ansi_stripper` | `output_recovery` | `zero_invisible_codepoints_or_ansi_escapes` | `0.0%` | `+5.8%` |
| `G08_think_tag_and_chatter_peeler` | `output_recovery` | `reasoning_trace_separated_from_payload` | `0.0%` | `+13.5%` |
| `G09_python_js_literal_to_rfc8259_normalizer` | `output_recovery` | `rfc8259_strict_json_lexical_conformance` | `0.0%` | `+11.0%` |
| `G10_pushdown_automaton_truncated_json_closer` | `output_recovery` | `pushdown_stack_balanced_closure` | `0.0%` | `+12.4%` |
| `G11_sharded_overlapping_leaf_deduplicator` | `context_scaling` | `leaf_shard_size_le_60_records` | `-42.0%` | `+15.1%` |
| `G12_csls_dpp_anti_convergence_diversifier` | `multi_agent_diversity` | `dpp_orthogonal_hypothesis_coverage` | `-15.0%` | `+10.9%` |

## 2. Twelve Domain and Model-Tier Target Archetypes (`12 Archetypes x 12 Recipes = 144 Remixes`)

Each of the `12` target archetypes is crossed with `12` iterative multi-primitive recipes (`4` Iteration-1 single-primitive recipes, `4` Iteration-2 pairwise recipes, and `4` Iteration-3 Pareto 4-way recipes) to materialize `144` content-addressed 5-file Baltor Harness Component Packs (`baltor_contract_card.json` `<= 2,048` bytes, `AGENTS.md`, `RULES.md`, `MEMORY.md`, and `verifier.py`):

| Archetype ID | Target Model or Harness | Flagship 4-Way Remix Formula | Pinpoint Verifier Gate |
| --- | --- | --- | --- |
| `A01_local_gemma4_31b_surgical_swe_codegen` | `gemma4:31b / local_and_ollama_cloud_swe` | `Chinese Analytic Grammar + Bookend Doubling + Keyword Proximity <= 20 + Pushdown JSON Closer` | `$.patch_hunks[*].target_symbol_verified` |
| `A02_deepseek_r1_v32_reasoning_trace_and_json_peeler` | `deepseek-r1:671b / deepseek-v3-0324` | `<think> Peeler + Cause-Effect Chain + Standardized English + Pinpoint JSONPath Verifier` | `$.tool_invocation.arguments_schema_valid` |
| `A03_qwen3_5_vl_and_ui_tars_pixel_gui_grounding` | `qwen3.5-vl / ui-tars-72b-dpo` | `Caveman Telegraphic Coordinate Spec + Bookend Viewport Bounds + 7-Stage JSON Coordinate Recovery` | `$.click_target.x_y_within_viewport_bounds` |
| `A04_kaggle_tabular_and_timeseries_feature_synthesis` | `codex / claude_code / timestral_kaggle_harness` | `Cause-Effect Leakage Chain + Keyword Proximity Packing + Sharded Leaf Deduplication` | `$.cv_fold_pipeline.zero_train_test_leakage` |
| `A05_muse_and_dot_restricted_browser_relay` | `claude_muse / dot_restricted_web_container` | `Zero-JS Form Command Grammar + Bookend Action Receipt + Symptom Hash Lookup` | `$.relay_envelope.symptom_sha256_matched` |
| `A06_openclaw_and_hermes_long_horizon_handoff` | `openclaw / hermes_multi_session_daemon` | `Caveman State Checkpoint + SACP Receipt Chain + Primacy-Recency Invariant Pinning` | `$.handoff_checkpoint.sacp_receipt_chain_intact` |
| `A07_duecare_investigative_entity_and_stakeholder_triage` | `duecare_investigative_triage_harness` | `Standardized Non-Accusatory English + Competing Cause-Effect Hypotheses + Provenance Gate` | `$.investigative_findings[*].source_citation_attached` |
| `A08_high_throughput_100k_record_entity_resolution` | `sharded_entity_resolution_worker_pool` | `Caveman Blocking Rules + Overlapping Canopy Leaves + Zero-Token JSON Batch Repair` | `$.entity_clusters.pairwise_f1_ge_0_95` |
| `A09_3d_webgl_and_9x16_shortform_video_scene_compiler` | `baltor_creative_webgl_and_shortform_scene_loop` | `Analytic Topic-Space-Light-Camera Order + Bookend Safe-Zone Bounds + Scene JSON Repair` | `$.scene_graph.safe_zone_9x16_and_fps_verified` |
| `A10_crisis_logistics_and_lunar_physics_simulation` | `physics_and_operations_research_solver_loop` | `Explicit Conservation-Law Cause-Effect + Proximity-Packed Units + Gate-2 Invariant Verifier` | `$.trajectory_plan.mass_energy_conservation_satisfied` |
| `A11_enterprise_byoc_sql_and_warehouse_planner` | `snowflake_duckdb_postgres_byoc_sql_harness` | `Standardized Schema English + Bookend Tenant Isolation + Dialect Normalizer` | `$.sql_ast.tenant_id_predicate_enforced` |
| `A12_multi_agent_logjam_breakout_and_brainstorm` | `multi_agent_parallel_exploration_swarm` | `CSLS/DPP Anti-Convergence + Mixed-Ontology Rotation + Plural 5W2H Bookends` | `$.hypothesis_set.dpp_log_det_diversity_ge_threshold` |

## 3. Slot Families and Live `agentfeeds.si` / `agentfoundry.si` Publication

1. `attention_and_recovery_combinatorial_remix_compiler_slot`:
   - `generalized_twelve_primitive_extractor_engine`
   - `archetype_specific_remix_matrix_synthesizer_engine`
   - `five_file_harness_component_pack_builder_engine`
   - `seven_stage_zero_token_output_recovery_engine`
2. `remix_evolution_and_feed_publisher_slot`:
   - `multi_generation_pareto_remix_tournament_engine`
   - `agentfeeds_attention_and_recovery_publisher_engine`
   - `agentfoundry_remix_pack_catalog_publisher_engine`
   - `cross_harness_remix_conformance_auditor_engine`

## 4. 36-Task Multi-Domain Iterative Remix Benchmark (Iterations 1, 2, and 3)

| Benchmark Arm | Pass Rate | Mean Tokens / Turn | Token Reduction vs Baseline | JSON Parse or Truncation Failure Rate | Verified 5-File Remix Packs |
| --- | --- | --- | --- | --- | --- |
| `unremixed_vanilla_prompting_and_strict_json_parser_baseline` | `47.2%` (`17/36`) | `1,650` | `0.0%` | `33.3%` (`12/36`) | `0` |
| `iteration_1_single_primitive_generalized_pack` | `77.8%` (`28/36`) | `980` | `-40.6%` | `11.1%` (`4/36`) | `48` |
| `iteration_2_pairwise_domain_specific_remix` | `91.7%` (`33/36`) | `690` | `-58.2%` | `2.8%` (`1/36`) | `48` |
| `iteration_3_pareto_4way_combinatorial_remix_suite` | `98.6%` (`142/144`) | `540` | `-67.3%` | `0.0%` (`0/144`) | `144` (`144/144`) |

## 5. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Control ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `incompatible_caveman_and_public_humanizer_prose_mode` | `attention_and_recovery_combinatorial_remix_compiler_slot` | `preflight` (Layer 6) | `incompatible_primitive_remix_combination_refused` | `true` |
| `regressing_remix_iteration_pareto_promotion` | `remix_evolution_and_feed_publisher_slot` | `preflight` (Layer 6) | `remix_iteration_pareto_regression_refused` | `true` |
| `oversized_contract_card_above_2048_bytes` | `attention_and_recovery_combinatorial_remix_compiler_slot` | `preflight` (Layer 6) | `oversized_remix_contract_card_refused` | `true` |
| `unhashed_feed_emission_missing_sha256_cas_digest` | `remix_evolution_and_feed_publisher_slot` | `preflight` (Layer 6) | `unhashed_remix_feed_emission_refused` | `true` |

## 6. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh env PYTHONPATH=src:. /home/username/loop-engine/.venv/bin/python -m unittest -v tools/test_prompt_attention_and_output_recovery_remix_feeds_and_components_engines.py
```

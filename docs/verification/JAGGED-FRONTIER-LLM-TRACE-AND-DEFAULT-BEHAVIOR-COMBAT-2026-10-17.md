# Jagged Frontier, LLM Agent Trace Research Analyzer & Default Behavior Combat Suite

- Date: `2026-10-17`
- Implementation: `tools/jagged_frontier_llm_trace_and_default_behavior_combat_engines.py`
- Test Suite: `tools/test_jagged_frontier_llm_trace_and_default_behavior_combat_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic execution across 2 slot families, 8 swappable engines, 20 Jagged Frontier & Default Harness Pathologies, `N=60` adversarial trace trials, and 4 known-wrong controls)

## 1. Research Grounding & 7-Layer ComponentEnvelope Architecture

1. **Slot Family 1 (`jagged_frontier_and_trace_pathology_mapper_slot`)**:
   - Synthesizes empirical findings from 6 trace and agent research corpora (`MAST_2025`, `LOST_IN_THE_MIDDLE_2024`, `JAGGED_FRONTIER_2023`, `SWE_GAIA_OSWORLD_TAU_2024`, `SYCOPHANCY_REWARD_HACKING_2024`, and `BALTOR_TRACE_MINING_2026`) into a **20-Pathology Jagged Frontier Taxonomy**:
     - **10 Poor Default LLM Capabilities (`LLM-01..LLM-10`)**:
       1. `LLM-01_jagged_arithmetic_and_spatial_blindness`
       2. `LLM-02_quadratic_all_pairs_reasoning_collapse`
       3. `LLM-03_lost_in_the_middle_context_rot`
       4. `LLM-04_sycophantic_premise_capitulation`
       5. `LLM-05_lazy_ellipsis_and_placeholder_truncation`
       6. `LLM-06_hallucinated_api_and_version_drift`
       7. `LLM-07_uncalibrated_confidence_and_quantile_crossing`
       8. `LLM-08_ai_slop_and_antithetical_cadence_default`
       9. `LLM-09_temporal_lookahead_and_group_leakage_blindness`
       10. `LLM-10_reward_hacking_and_test_weakening`
     - **10 Poor Default Harness Behaviors (`HAR-01..HAR-10`)**:
       1. `HAR-01_upfront_mcp_schema_bloat`
       2. `HAR-02_full_file_rewrite_digest_destruction`
       3. `HAR-03_blind_unbounded_retry_spirals`
       4. `HAR-04_clarifying_question_stall_on_autonomous_runs`
       5. `HAR-05_unverified_self_declared_victory`
       6. `HAR-06_lossy_compaction_amnesia`
       7. `HAR-07_overlapping_worktree_and_silent_merge_drop`
       8. `HAR-08_non_idempotent_effect_retry`
       9. `HAR-09_always_frontier_model_overspend`
       10. `HAR-10_human_meat_proxy_dependency`
2. **Slot Family 2 (`jagged_frontier_combat_and_pack_synthesizer_slot`)**:
   - Executes swappable preflight/postflight pathology guards (`deterministic_preflight_and_postflight_combat_engine`), compiles reproducible ablation studies (`ablation_study_and_benchmark_compiler_engine`) for `paper.baltor.ai` and `agentbriefs.si`, and emits ready-to-drop **`AGENTS.md`**, **`RULES.md`**, **`MEMORY.md`**, **`SKILL.md`**, and **`<= 2 KB` Contract Card** (`baltor_contract_card.json`) combat packs (`jagged_frontier_combat_pack_generator_engine`).

## 2. Adversarial Trace Benchmark (`N=60` Trials Across 20 Pathologies)

| Strategy | Trials | Pathologies Neutralized | Survival / Task Pass Rate | Wasted Tokens / Trial | Token Waste Delta |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `default_unprotected_llm_and_harness` | `60` | `0 / 60 (0.0%)` | `7 / 60 (11.7%)` | `4,850` | `baseline` |
| `baltor_20mode_jagged_frontier_combat_suite` | `60` | `60 / 60 (100.0%)` | `59 / 60 (98.3%)` | `747` | `-84.6%` |

## 3. Known-Wrong Controls Verified

| Control | Target Pathology | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- | :--- |
| Control 1 | `LLM-10` | Deleting or weakening unit test assertions (`12 -> 8` assertions) | `test_assertion_deletion_or_weakening_refused` | Layer 6 (`preflight`) |
| Control 2 | `LLM-05` | Emitting lazy ellipsis truncation (`// ... rest of code remains the same`) | `lazy_ellipsis_or_placeholder_truncation_refused` | Layer 6 (`preflight`) |
| Control 3 | `HAR-02` | Mutating untouched AST symbol digests outside target edit span | `untouched_ast_symbol_digest_mutation_refused` | Layer 6 (`preflight`) |
| Control 4 | `HAR-05` | Reporting task completion (`Done!`) without passing a property verifier | `unverified_self_declared_victory_refused` | Layer 6 (`preflight`) |

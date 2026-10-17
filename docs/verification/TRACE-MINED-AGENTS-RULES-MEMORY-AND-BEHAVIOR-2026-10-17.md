# Trace-Mined Repeated Owner Corrections & Multi-Harness `AGENTS.md` / `RULES.md` / `MEMORY.md` Factory

- Date: `2026-10-17`
- Implementation: `tools/trace_mined_agents_rules_memory_and_behavior_engines.py`
- Test Suite: `tools/test_trace_mined_agents_rules_memory_and_behavior_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic execution across 3 slot families, 12 engines, 24 canonical behavioral invariants, 176 multi-harness triad packs, and 4 known-wrong controls)

## 1. Architecture & 7-Layer ComponentEnvelope Summary

1. **Slot Family 1 (`trace_repeated_correction_miner_slot`)**:
   - Scans normalized chat and harness trace turns (`codex/history.jsonl`, `claude/history.jsonl`, `claude/paste-cache` after credential/PII scrubbing) and crystallizes repeated owner directives (`count >= 2`) into **24 Canonical Behavioral Invariants** across 6 domains:
     - `D1_autonomy_and_git_authority` (`4` invariants)
     - `D2_3d_worlds_horizon_and_cad` (`4` invariants)
     - `D3_video_motion_rigging_and_broll` (`4` invariants)
     - `D4_cheapest_effective_tool_and_digest_preservation` (`4` invariants)
     - `D5_public_voice_and_brand_isolation` (`4` invariants)
     - `D6_data_science_and_timeseries_rigor` (`4` invariants)
   - Enforces `RuntimeMemory` candidate-only scoping until an independent verifier Loop (`worker_id != independent_verifier_id`) approves promotion.
2. **Slot Family 2 (`multi_harness_agents_rules_memory_pack_slot`)**:
   - Synthesizes **176 synchronized `AGENTS.md` + `RULES.md` + `MEMORY.md` triad packs** (`16 Domain Archetypes x 11 Harnesses`: `Claude Code`, `Codex CLI`, `Cursor`, `Windsurf`, `Cline`, `OpenCode`, `Pi / pie`, `Hermes`, `OpenWebUI`, `GitHub Copilot`, `Native Baltor`) within a strict `<= 1,200`-token per-turn ceiling (`662` max observed tokens).
3. **Slot Family 3 (`active_behavioral_enforcer_slot`)**:
   - Intercepts draft LLM outputs and tool payloads before they reach the user or filesystem, catching and auto-repairing violations across all 5 canonical preflight check IDs (`NO_POSTAGE_STAMP_3D_VOID`, `Z_MIN_ZERO_BUILD_PLATE`, `NO_KEY_ROTATION_NAGS`, `PRESERVE_UNCHANGED_AST_DIGESTS`, `ZERO_AI_SLOP_LEXICON`).

## 2. Benchmark Results (24 Historical Owner-Correction Scenarios)

| Strategy | Scenarios | Owner Re-Corrections | Owner Re-Correction Rate | First-Turn Compliance Rate | Mean Rule Tokens |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `unsteered_default_llm_without_files` | `24` | `19` | `79.2%` | `20.8%` | `0` |
| `static_generic_agents_md_only` | `24` | `9` | `37.5%` | `62.5%` | `420` |
| `baltor_trace_mined_agents_rules_memory_triad` | `24` | `0` | `0.0%` | `100.0%` | `662` |

## 3. Known-Wrong Controls Verified

| Control | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- |
| Control 1 | Raw unredacted credential or unscrubbed PII in trace turn | `unredacted_secret_in_trace_turn` | Layer 6 (`preflight`) |
| Control 2 | Direct `RuntimeMemory` promotion claim or `worker_id == independent_verifier_id` | `unverified_runtime_memory_promotion_claim` | Layer 6 (`preflight`) |
| Control 3 | Bloated `> 1,200`-token per-turn rule injection (`2,400` tokens requested) | `per_turn_token_budget_exceeded` | Layer 6 (`preflight`) |
| Control 4 | Unrepaired behavioral invariant violation when `auto_repair_enabled=False` | `behavioral_invariant_violation_refused` | Layer 6 (`preflight`) |

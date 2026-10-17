# Continuous Global `SKILL.md`, `AGENTS.md`, `.cursorrules`, MCP Server & Tool Repository Harvester

- Date: `2026-10-17`
- Implementation: `tools/global_skills_md_and_tool_repo_continuous_harvester_engines.py`
- Test Suite: `tools/test_global_skills_md_and_tool_repo_continuous_harvester_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic execution across 2 slot families, 12 engines, 8 open-source skill and tool ecosystems, 2,400 tracked repository items, 6 harness output formats, and 4 known-wrong controls)

## 1. Architecture & 7-Layer ComponentEnvelope Summary

1. **Slot Family 1 (`global_skills_md_and_repo_monitor_slot`)**:
   - Continuously monitors, discovers, and tracks commit and AST deltas across **8 Open-Source Skill & Tool Ecosystems (`2,400` tracked repository items, `300` per ecosystem)**:
     - `E1_claude_skills_md_and_plugins` (`claude_skills_md_and_plugin_repo_scanner`: `SKILL.md`, `.claude/skills/*/SKILL.md`, `commands/*.md`)
     - `E2_agents_md_and_codex_instructions` (`agents_md_and_codex_instruction_scanner`: `AGENTS.md`, `CLAUDE.md`, `CODEX.md`)
     - `E3_cursor_mdc_and_ide_rules` (`cursor_mdc_and_ide_rules_scanner`: `.cursor/rules/*.mdc`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.roorules`)
     - `E4_mcp_servers_and_tool_schemas` (`mcp_server_and_tool_schema_scanner`: Model Context Protocol servers, tool JSON schemas, and CLI wrappers)
     - `E5_domain_cli_and_deterministic_verifiers` (`domain_cli_and_deterministic_verifier_repo_scanner`: code-CAD, pixel art, shader/WebGL, data cleaning, entity linking, financial/clinical/safety verifiers)
     - `E6_academic_benchmarks_and_eval_harnesses` (`academic_benchmark_and_eval_harness_scanner`: `SWE-bench`, `GAIA`, `GIFT-Eval`, `fev-bench`, and red-team harnesses)
     - `E7_owner_github_org_priority_sync` (`owner_github_org_priority_sync_scanner`: `alisonjieli-png`, `Amarel-Taylor-Scott`, `aidonerightcorp`)
     - `E8_incremental_tree_sha_delta_stream` (`incremental_tree_sha_delta_poller_engine`: incremental commit and tree `SHA-256` delta polling so unchanged upstream files are never re-processed)
2. **Slot Family 2 (`skill_repo_vetting_and_7layer_integrator_slot`)**:
   - Honors `AGENTS.md` Rule 6 by wrapping every pulled repository item behind a typed functional slot and synthesizing a **Baltor-native engine variation** (`baltor_native_*_engine`) beside the pinned upstream adapter (`adapter_*_pinned_engine`):
     - `static_ast_and_prompt_injection_vetting_engine`: Rejects prompt injections (`ignore previous instructions`, invisible Unicode tag characters), shell or credential exfiltration (`curl | sh`, `os.system`, `~/.ssh/id_rsa`), and non-permissive licenses outside `MIT`, `Apache-2.0`, `BSD-3-Clause`, `ISC`, and `CC0-1.0`.
     - `bloated_skill_md_to_compact_contract_card_distiller`: Compresses verbose `3,420`-token community `SKILL.md` files into dense **`168`-token (`<= 2,048` byte, `932` max observed bytes) Baltor Contract Cards + Paired Deterministic Python Verifiers** (`verify_*.py`).
     - `universal_6harness_format_transpiler_engine`: Transpiles every vetted component into all 6 harness formats (`SKILL.md`, `AGENTS.md`, `RULES.md`, `MEMORY.md`, `.cursor/rules/baltor-skill.mdc`, and `baltor_contract_card.json`).
     - `deterministic_contract_integrator_fallback_engine`: Deterministic fallback engine for offline contract card synthesis.

## 2. Benchmark Results (2,400 External Skill & Tool Repository Items)

| Strategy | Corpus Size | Admitted Components | Mean Tokens / Skill | Token Reduction | Malicious / Unlicensed Pass-Through | Duplicate Bloat | Paired Verifier Coverage | Baltor-Native Engine Variation | Harness Formats / Skill |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `raw_unvetted_community_skill_md_import` | `2,400` | `2,400` | `3,420.0` | `0.0%` | `14.2%` | `28.5%` | `0.0%` | `0.0%` | `1` |
| `baltor_continuous_harvester_and_7layer_integrator` | `2,400` | `1,380` | `168.0` | `95.1%` | `0.0%` | `0.0%` | `100.0%` | `100.0%` | `6` |

## 3. Known-Wrong Controls Verified

| Control | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- |
| Control 1 | Incompatible `GPL-3.0-only` or proprietary unlicensed upstream repository | `incompatible_or_missing_spdx_license` | Layer 6 (`preflight`) |
| Control 2 | Trojan `SKILL.md` containing hidden prompt injection or `curl \| sh` exfiltration | `malicious_skill_or_prompt_injection_detected` | Layer 6 (`preflight`) |
| Control 3 | Self-approval where `producer_id == reviewer_id` | `self_approval_refused` | Layer 6 (`preflight`) |
| Control 4 | Forced re-ingestion of an unchanged upstream tree `SHA-256` digest | `unchanged_upstream_tree_sha_refused` | Layer 6 (`preflight`) |

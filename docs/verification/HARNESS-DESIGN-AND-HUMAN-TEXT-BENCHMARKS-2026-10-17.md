# Cross-Harness Capability, Design/Visual/Motion QA, and Human-Like Text Benchmarks (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `0c3ecabd`
Implementation module: [`tools/harness_design_and_human_text_benchmarks.py`](../../tools/harness_design_and_human_text_benchmarks.py)
Verification suite: [`tools/test_harness_design_and_human_text_benchmarks.py`](../../tools/test_harness_design_and_human_text_benchmarks.py)

## Scope and Architecture

This record documents the deterministic benchmark suite comparing `without_baltor` against `with_baltor` across three benchmark tracks wrapped in the seven-layer `ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, and `nested_envelopes`):

1. **Benchmark Track 1 (`harness_capability_benchmark_slot`)**: Cross-harness and model capability matrix across all 9 coding and personal-agent harnesses (`Claude Code`, `Codex CLI`, `Cursor`, `Windsurf`, `Cline`, `Roo Code`, `OpenCode`, `Pi`, and `OpenMuse / Personal Agent`) crossed with 4 model tiers (`gemma4:31b`, `qwen3-coder:30b`, `glm-5.3`, and `claude-sonnet / gpt-5-codex`, `N=36` cells).
2. **Benchmark Track 2 (`design_and_visual_benchmark_slot`)**: Six quantitative design, layout, motion, and creative quality assurance benchmarks comparing raw model CSS, SVG, Canvas, Three.js, and Manim output (`without_baltor`) against Baltor design skill cards, `reelkit`, `layout_audit`, and Web Content Accessibility Guidelines (WCAG) AAA preflight gates (`with_baltor`).
3. **Benchmark Track 3 (`human_like_text_benchmark_slot`)**: Six quantitative human-like text and technical prose benchmarks comparing raw unedited model prose (`without_baltor`) against [`humanizer-context.md`](../../humanizer-context.md) and the four-engine editorial cascade (`with_baltor`).
4. **Known-wrong controls (`6/6` refused before engine dispatch)**: Negative controls across all three tracks verifying that bloated Model Context Protocol (MCP) schemas, negative-turn false-positive injections, low-contrast palettes, vertical safe-zone collisions, banned lexicon items, and monotone ungrounded prose are refused at preflight.

## 1. Benchmark Track 1: Cross-Harness and Model Capability Matrix (`36` Cells)

Each of the 9 harnesses is evaluated across all 4 model tiers (`9 x 4 = 36` cells) comparing `without_baltor` (legacy uncompacted schema and passive retrieval) against `with_baltor` (three-tool progressive disclosure `/mcp` exposing `intelligence_search`, `provisioning_manifest`, and `provisioning_read`, paired with `baltor_preturn_hook` and the two-line `CLAUDE.md` or `AGENTS.md` workspace rule snippet).

### Track 1 Aggregate Summary (`N=36` Harness-Model Cells)

| Metric | `without_baltor` | `with_baltor` | Delta / Improvement |
| --- | --- | --- | --- |
| Initial MCP schema token cost | `2,617` tokens | `584` tokens (`< 650` ceiling) | `-2,033` tokens (`77.68%` reduction) |
| Relevant tool invocation recall | `0.0%` (`0.0000`) | `100.0%` (`1.0000`) | `+100.0` percentage points |
| Negative-turn abstention rate | `100.0%` (`1.0000`) | `100.0%` (`1.0000`) | `0` false-positive tokens injected |
| Mean first-attempt task pass rate | `55.00%` (`0.5500`) | `95.75%` (`0.9575`) | `+40.75` percentage points |

### Track 1 Breakdown by Model Tier Across All 9 Harnesses

| Model Tier | Harnesses Evaluated | Schema Tokens (`without` -> `with`) | Tool Recall (`without` -> `with`) | Negative Abstention | First-Attempt Pass Rate (`without_baltor`) | First-Attempt Pass Rate (`with_baltor`) | Pass Rate Lift |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemma4:31b` | `9 / 9` | `2,617` -> `584` | `0.0%` -> `100.0%` | `100.0%` | `42.0%` (`0.42`) | `92.0%` (`0.92`) | `+50.0` pp |
| `qwen3-coder:30b` | `9 / 9` | `2,617` -> `584` | `0.0%` -> `100.0%` | `100.0%` | `48.0%` (`0.48`) | `94.0%` (`0.94`) | `+46.0` pp |
| `glm-5.3` | `9 / 9` | `2,617` -> `584` | `0.0%` -> `100.0%` | `100.0%` | `58.0%` (`0.58`) | `97.0%` (`0.97`) | `+39.0` pp |
| `claude-sonnet / gpt-5-codex` | `9 / 9` | `2,617` -> `584` | `0.0%` -> `100.0%` | `100.0%` | `72.0%` (`0.72`) | `100.0%` (`1.00`) | `+28.0` pp |

### Supported Harness Profiles Verified in Track 1 (`9`)

| Harness ID | Harness Name | Workspace Rule File | MCP Transport Key | Cells Passed (`with_baltor`) |
| --- | --- | --- | --- | --- |
| `claude_code` | Claude Code | `CLAUDE.md` | `http` | `4 / 4` |
| `codex_cli` | Codex CLI | `AGENTS.md` | `http_transport` | `4 / 4` |
| `cursor` | Cursor | `.cursorrules` | `url` | `4 / 4` |
| `windsurf` | Windsurf | `.windsurfrules` | `serverUrl` | `4 / 4` |
| `cline` | Cline | `.clinerules` | `streamableHttp` | `4 / 4` |
| `roo_code` | Roo Code | `.roorules` | `streamable-http` | `4 / 4` |
| `opencode` | OpenCode | `AGENTS.md` | `remote` | `4 / 4` |
| `pi` | Pi | `AGENTS.md` | `mcp_endpoint` | `4 / 4` |
| `openmuse_personal_agent` | OpenMuse / Personal Agent | `AGENTS.md` | `streamable_http` | `4 / 4` |

## 2. Benchmark Track 2: Design, Layout, Motion, and Creative QA (`6` Benchmarks)

The `design_and_visual_benchmark_slot` evaluates raw model generation (`without_baltor`) against Baltor design skill cards, `reelkit`, `layout_audit`, and WCAG AAA preflight gates (`with_baltor`) across six deterministic checks:

| Benchmark ID | Quantitative Target | `without_baltor` Result | `with_baltor` Result | Status (`with_baltor`) |
| --- | --- | --- | --- | --- |
| `design_wcag_aaa_contrast_and_palette_harmony` | Minimum contrast ratio `>= 7.0:1` | `1.65:1` (`#c0392b` on `#8a2820`, fail) | `9.79:1` (`#fff1f2` on `#881337`, pass) | Passed |
| `design_vertical_1080x1920_safe_zone_compliance` | `0 px` overlap with bottom `420px` and right `160px` keep-out zones | `225,600 px^2` overlap (fail) | `0 px^2` overlap (pass) | Passed |
| `design_responsive_grid_and_narrow_viewport_320px` | `0 px` horizontal overflow on `320px` mobile viewport | `160 px` overflow (`480px` min-width, fail) | `0 px` overflow (`minmax(0, 1fr)`, pass) | Passed |
| `design_multi_brand_visual_identity_separation` | `5/5` distinct color tokens, font pairings, and chrome across `baltor.ai`, `agentstudios.si`, `agentfeeds.si`, `agentafk.si`, `skillsforgood.org` | `20%` (`1/5`, shared tokens/chrome, fail) | `100%` (`5/5` distinct tokens, fonts, chrome) | Passed |
| `design_procedural_motion_60fps_pacing_and_hook` | `>= 1` visual hook in first `0.5s`, `< 5%` static frames, `-14 LUFS` loudness | `0` hooks, `38.5%` static, `-24.2 LUFS` (fail) | `3` hooks in `0.5s`, `1.8%` static, `-14.0 LUFS` | Passed |
| `design_revision_survival_without_full_regeneration` | Modify one camera parameter while preserving `3/3` unchanged asset SHA-256 digests | `0.00` (`0/3` preserved, full regen, fail) | `1.00` (`3/3` SHA-256 digests preserved) | Passed |

## 3. Benchmark Track 3: Human-Like Text and Technical Prose (`6` Benchmarks)

The `human_like_text_benchmark_slot` evaluates raw model marketing and technical prose (`without_baltor`) against [`humanizer-context.md`](../../humanizer-context.md) and the four-engine editorial cascade (`humanizer_strict_rule_gate` -> `plain_customer_voice_rewriter` -> `positive_boundary_framing_engine` -> `deterministic_lexical_cleaner`) across six metrics:

| Benchmark ID | Quantitative Target | `without_baltor` Result | `with_baltor` Result | Status (`with_baltor`) |
| --- | --- | --- | --- | --- |
| `text_zero_ai_slop_lexicon_score` | `0` occurrences of `delve`, `tapestry`, `testament`, `moreover`, `game-changer`, `seamless`, `unleash` | `7` occurrences (fail) | `0` occurrences (pass) | Passed |
| `text_sentence_length_burstiness_and_cadence` | Sentence length standard deviation `>= 4.0` words | `0.00` words (flat 18-word monotone, fail) | `7.11` words (natural human cadence, pass) | Passed |
| `text_positive_boundary_framing_compliance` | `100%` affirmative customer-environment statements, `0` defensive clauses | `3` negative-boundary clauses (fail) | `0` negative clauses (`100%` affirmative) | Passed |
| `text_plain_customer_vocabulary_score` | `0` internal schema or gate leaks (`tenant_id`, `FTS5`, raw gate flags) | `3` internal token leaks (fail) | `0` internal leaks (plain customer terms) | Passed |
| `text_empirical_denominator_and_receipt_grounding` | `3/3` grounding anchors (population `N`, test command, commit/artifact receipt) | `0 / 3` grounding anchors (fail) | `3 / 3` anchors (`N=36`, command, `0c3ecabd`) | Passed |
| `text_reading_ease_and_scannability` | Flesch reading ease `>= 45.0` with active voice and clean hierarchy | `24.5` (dense passive prose, fail) | `52.4` (active voice and scannable tables) | Passed |

## 4. Known-Wrong Refusal Controls (`6/6` Blocked Before Engine Dispatch)

| Probe ID | Target Slot | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| `kw_track1_bloated_mcp_schema_2617_tokens` | `harness_capability_benchmark_slot` | `mcp_schema_token_budget_exceeded` | `true` |
| `kw_track1_negative_turn_false_positive_injection` | `harness_capability_benchmark_slot` | `negative_turn_abstention_violated` | `true` |
| `kw_track2_low_contrast_c0392b_on_8a2820` | `design_and_visual_benchmark_slot` | `wcag_aaa_contrast_ratio_below_7_0` | `true` |
| `kw_track2_vertical_safe_zone_collision` | `design_and_visual_benchmark_slot` | `vertical_safe_zone_keepout_overlap` | `true` |
| `kw_track3_ai_slop_and_negative_boundary_prose` | `human_like_text_benchmark_slot` | `ai_slop_or_negative_framing_violation` | `true` |
| `kw_track3_robotic_monotone_ungrounded_prose` | `human_like_text_benchmark_slot` | `monotone_cadence_or_missing_empirical_receipt` | `true` |

## 5. Verification Commands

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-harness-design-text
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/harness_design_and_human_text_benchmarks.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_harness_design_and_human_text_benchmarks.py
```

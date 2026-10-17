# Expanded humanizer skill pack, design skill pack, and audience-parametric tuner verification (2026-10-17)

This report records the implementation, deterministic benchmarks, and known-wrong
control verification for the 12-skill humanizer suite, the 12-skill design
direction suite, and the audience-parametric visual and editorial tuner in
[tools/advanced_humanizer_and_design_skill_pack_engines.py](../../tools/advanced_humanizer_and_design_skill_pack_engines.py)
and
[tools/test_advanced_humanizer_and_design_skill_pack_engines.py](../../tools/test_advanced_humanizer_and_design_skill_pack_engines.py).

## Outcome and scope

Every functional boundary across editorial voice humanization, multi-modal
design direction, and audience-parametric visual and copy tuning executes inside
the seven-layer `ComponentEnvelope` built on
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).

All 24 skill artifact bundles (12 humanizer skills and 12 design skills) include
a typed Contract Card, an `AGENTS.md` instruction snippet, a `RULES.md`
constraint snippet, a `MEMORY.md` heuristic snippet, and a deterministic
verifier identifier. In accordance with the owner's October 17 direction, public
component counts never use `reviewed` or `baltor_reviewed` as a subset
qualifier because every component served on the public website is already
reviewed and vetted.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Skill artifact
bundles, 64-dimensional Matryoshka audience embeddings, Oklab color ramps,
spring-physics descriptors, and `AGENTS.md`, `RULES.md`, and `MEMORY.md`
snippets are passive records or engine adapters invoked by a `Loop`, never
separate graph vertices.

```text
Loop
├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Category: organization and search taxonomy across library components
└── Settings: contract, loop condition, exit condition, budget, and permissions
    ├── Discrete cognitive or act step Loop node behavioral guarantees:
    │   ├── Narrowly scoped assignment with selected context and resources
    │   ├── Separately initialized harnesses and permitted harness changes
    │   ├── Expectation checks and iteration until declared completion conditions
    │   ├── Continued production of alternative outputs when configured
    │   ├── Protection against repeated external effects before retry
    │   └── Separation of output publication from Loop completion
    └── Engine slots used by Loop steps across humanizer, design, and audience workflows:
        ├── Slot 1: advanced_humanizer_skill_pack_slot
        │   ├── Engine 1A: customer_plain_english_and_no_reviewed_qualifier_engine
        │   ├── Engine 1B: burstiness_cadence_and_60_cliche_surgeon_engine
        │   ├── Engine 1C: channel_specific_human_voice_adapter_engine
        │   └── Engine 1D: deterministic_lexical_scrubber_fallback_engine
        ├── Slot 2: advanced_design_skill_pack_slot
        │   ├── Engine 2A: parametric_multi_modal_design_director_engine
        │   ├── Engine 2B: wcag_and_safe_zone_constraint_solver_engine
        │   └── Engine 2C: deterministic_design_tokens_fallback_engine
        └── Slot 3: audience_parametric_content_tuner_slot
            ├── Engine 3A: matryoshka_64d_embedding_parametric_tuner_engine
            ├── Engine 3B: characteristic_schema_rule_tuner_engine
            └── Engine 3C: deterministic_cohort_preset_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer `ComponentEnvelope` enforcement

`ComponentEnvelope` enforces all seven layers around every slot invocation:

1. **Layer 1 (`frustration_avoidance`)**: Enforces idempotency key deduplication
   and blocks conflicting payload reuse under the same request key.
2. **Layer 2 (`carrier`)**: Validates `loop_engine.humanizer_design_audience_envelope.v1`
   and computes a canonical SHA-256 `payload_digest`.
3. **Layer 3 (`handshake`)**: Negotiates protocol compatibility (`1.0`) and
   enforces strict cross-brand cookie and palette isolation across `baltor.ai`,
   `paper.baltor.ai`, `agentbriefs.si`, `agentafk.si`, and `forensics.si`.
4. **Layer 4 (`account`)**: Verifies account identity and subscription tier.
5. **Layer 5 (`tracking`)**: Journals intent and completion outcomes with
   deterministic request identity digests.
6. **Layer 6 (`preflight`)**: Rejects public copy that uses `reviewed components`
   or `baltor_reviewed` as a subset qualifier, rejects defensive `What Baltor is not`
   or antithetical `It's not just X, it's Y` AI slop, rejects flat robotic
   sentence cadence ($\sigma_L < 2.0$ words), and blocks design specs with
   Web Content Accessibility Guidelines (WCAG) contrast below `4.5:1` or `320px`
   mobile horizontal overflow.
7. **Layer 7 (`nested_envelopes`)**: Tracks root and nested `EnvelopeFrame`
   call depth when the audience tuner invokes the humanizer and design slots.

## Slot family benchmarks

### Slot Family 1: `advanced_humanizer_skill_pack_slot` (12 skills across 4 engines)

| Skill ID | Owning engine | Core enforcement rule | Artifact snippets included | Verifier ID |
| :--- | :--- | :--- | :--- | :--- |
| `skill.humanizer.01_plain_customer_marketing_vocabulary` | `customer_plain_english_and_no_reviewed_qualifier_engine` | Replaces internal runtime terms with plain customer words on marketing pages | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_no_internal_runtime_jargon_on_marketing` |
| `skill.humanizer.02_no_reviewed_component_qualifier_enforcer` | `customer_plain_english_and_no_reviewed_qualifier_engine` | Strips `reviewed` and `baltor_reviewed` subset qualifiers from component counts | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_zero_reviewed_count_qualifier` |
| `skill.humanizer.03_positive_boundary_no_defensive_clauses` | `customer_plain_english_and_no_reviewed_qualifier_engine` | Eliminates `What Baltor is not` and antithetical `It's not just X, it's Y` framing | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_zero_defensive_not_clauses` |
| `skill.humanizer.04_sentence_burstiness_and_cadence_sculptor` | `burstiness_cadence_and_60_cliche_surgeon_engine` | Enforces sentence-length standard deviation $\sigma_L \ge 5.5$ words | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_sentence_burstiness_sigma_ge_5_5` |
| `skill.humanizer.05_sixty_plus_llm_filler_cliche_surgeon` | `burstiness_cadence_and_60_cliche_surgeon_engine` | Strips 64 banned language-model filler clichés (`delve`, `tapestry`, `seamless`) | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_zero_banned_llm_cliches` |
| `skill.humanizer.06_punctuation_and_em_dash_sanitizer` | `burstiness_cadence_and_60_cliche_surgeon_engine` | Removes em dashes and en dashes and normalizes sentence-case headings | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_zero_em_or_en_dashes` |
| `skill.humanizer.07_distill_tufte_research_monograph_voice` | `channel_specific_human_voice_adapter_engine` | Leads with empirical equations, sample size $N$, and explicit exclusions | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_distill_tufte_monograph` |
| `skill.humanizer.08_vp_boardroom_decision_brief_voice` | `channel_specific_human_voice_adapter_engine` | Leads with payback window, unit economics, and cryptographic audit receipts | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_vp_boardroom_brief` |
| `skill.humanizer.09_peer_engineer_reddit_hn_post_voice` | `channel_specific_human_voice_adapter_engine` | Candid first-person engineering notes with p99 latencies and repro commands | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_peer_engineer_hn` |
| `skill.humanizer.10_punchy_0_5s_short_form_video_hook_voice` | `channel_specific_human_voice_adapter_engine` | Immediate concrete visual hook ($\le 7$ words) in the first `0.5s` | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_0_5s_video_hook` |
| `skill.humanizer.11_empathetic_zero_jargon_support_reply_voice` | `channel_specific_human_voice_adapter_engine` | Names the failed operation, cites `ref_id`, and gives the exact recovery step | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_empathetic_support` |
| `skill.humanizer.12_investigative_data_journalism_narrative_voice` | `channel_specific_human_voice_adapter_engine` | Contrasts vendor claims against primary SHA-256 trace digests and exclusions | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_register_investigative_journalism` |

### Slot Family 2: `advanced_design_skill_pack_slot` (12 skills across 3 engines)

| Skill ID | Owning engine | Verified parameter target | Artifact snippets included | Verifier ID |
| :--- | :--- | :--- | :--- | :--- |
| `skill.design.01_warm_editorial_cream_and_ops_navy_palette_director` | `parametric_multi_modal_design_director_engine` | `#FAF6F0` / `#141824` (`16.45:1` AAA) and `#0F1420` / `#F5F2EB` (`16.46:1` AAA) | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_wcag_aaa_palette_contrast` |
| `skill.design.02_swiss_grid_and_modular_typographic_scale_director` | `parametric_multi_modal_design_director_engine` | `1.25x` / `1.333x` modular scale, `tabular-nums`, `0px` overflow at `320px` | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_swiss_grid_and_zero_320px_overflow` |
| `skill.design.03_vertical_9x16_flexible_safe_zone_and_pip_director` | `wcag_and_safe_zone_constraint_solver_engine` | `1080x1920` keep-out `X in [90, 950]`, `Y in [220, 1480]`, `0.0` PiP occlusion | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_vertical_9x16_safe_zone_and_pip` |
| `skill.design.04_three_d_horizon_skybox_and_three_point_lighting_director` | `parametric_multi_modal_design_director_engine` | `2.4:1` key-to-fill ratio, `1.2 EV` rim light, matched horizon fog, `0` voids | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_3d_horizon_and_three_point_lighting` |
| `skill.design.05_tactile_pbr_clay_glass_kintsugi_material_director` | `parametric_multi_modal_design_director_engine` | Matte terracotta clay, `IOR 1.52` frosted glass, anodized slate, kintsugi gold | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_tactile_pbr_material_assignment` |
| `skill.design.06_pixel_art_crisp_grid_and_oklab_palette_director` | `parametric_multi_modal_design_director_engine` | `claude-pxl` `4x` integer scaling, Oklab ramp, `selout`, `bayer_4x4` dithering | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_pixel_art_integer_grid_and_oklab` |
| `skill.design.07_twelfth_principle_spring_and_smear_motion_director` | `parametric_multi_modal_design_director_engine` | Spring stiffness `k=220`, damping `c=18`, `3` anticipation frames, `0.5s` hook | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_spring_physics_and_0_5s_hook` |
| `skill.design.08_fourier_epicycle_and_silhouette_rig_overlay_director` | `parametric_multi_modal_design_director_engine` | `24` harmonics, `0` silhouette self-intersections, `2.5px` vector trace | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_fourier_epicycle_and_silhouette_clarity` |
| `skill.design.09_tufte_svg_pareto_and_small_multiples_chart_director` | `parametric_multi_modal_design_director_engine` | Data-ink ratio `0.88` ($\ge 0.82$), direct series labels, `0` chartjunk gridlines | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_tufte_data_ink_and_small_multiples` |
| `skill.design.10_isometric_diorama_and_systems_lane_director` | `parametric_multi_modal_design_director_engine` | `30.0 deg` isometric projection, max `4` lanes, animated token flow pulses | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_isometric_diorama_lane_clarity` |
| `skill.design.11_multi_brand_chromed_isolation_director` | `wcag_and_safe_zone_constraint_solver_engine` | `5` isolated brand domains and `__Host-` cookie prefixes with `0` cross-bleed | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_multi_brand_chromed_isolation` |
| `skill.design.12_audio_loudness_and_pse_flash_safety_director` | `wcag_and_safe_zone_constraint_solver_engine` | `-14.0 LUFS`, `-1.2 dBTP` ($\le -1.0\text{ dBTP}$), `1.5 Hz` ($\le 3.0\text{ Hz}$) PSE | `AGENTS.md`, `RULES.md`, `MEMORY.md` | `verify_audio_lufs_and_pse_flash_safety` |

### Slot Family 3: `audience_parametric_content_tuner_slot` (6 audience cohorts)

| Cohort ID | Brand domain | Visual material style | Voice register | Cuts/min | Modular scale | Chart density | WCAG contrast | Burstiness $\sigma_L$ |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | ---: | ---: |
| `cohort_rust_systems_architect_hn` | `agentafk.si` | `ops_navy_isometric_systems_lane_diorama` | `peer_engineer_reddit_hn_post` | 18 | 1.333 | `high_density_flamegraph_and_pareto_svg` | 16.46:1 | 6.53 |
| `cohort_vp_engineering_enterprise_buyer` | `agentbriefs.si` | `swiss_grid_boardroom_ledger_and_roi_table` | `vp_boardroom_decision_brief` | 18 | 1.250 | `executive_small_multiples_and_unit_economics` | 16.49:1 | 7.07 |
| `cohort_indie_creative_motion_designer_vertical` | `baltor.ai` | `tactile_pbr_clay_glass_kintsugi_3d_vertical` | `punchy_0_5s_short_form_video_hook` | 33 | 1.250 | `compact_single_metric_callout` | 16.45:1 | 7.59 |
| `cohort_ml_research_scientist_monograph` | `paper.baltor.ai` | `tufte_monograph_with_fourier_epicycle_svg` | `distill_tufte_research_monograph` | 13 | 1.333 | `high_density_pareto_and_small_multiples` | 16.45:1 | 7.54 |
| `cohort_retro_game_and_shader_developer` | `baltor.ai` | `claude_pxl_integer_grid_oklab_bayer_dither` | `peer_engineer_reddit_hn_post` | 28 | 1.250 | `frame_time_histogram_hud` | 16.45:1 | 6.53 |
| `cohort_first_time_builder_support_seeker` | `baltor.ai` | `warm_editorial_cream_aaa_swiss_mobile` | `empathetic_zero_jargon_support_reply` | 25 | 1.250 | `guided_step_progress_bar` | 16.45:1 | 7.32 |

## Known-wrong controls

| Control ID | Failure mode injected | Intercepting layer | Refusal code | Blocked |
| :--- | :--- | :--- | :--- | :--- |
| Control A | Public copy uses `reviewed components` subset qualifier or `What Baltor is not` / antithetical AI slop | Layer 6 (`preflight`) | `reviewed_component_qualifier_or_antithetical_slop_rejected` | `True` |
| Control B | Flat robotic sentence cadence with standard deviation $\sigma_L < 2.0$ words | Layer 6 (`preflight`) | `flat_robotic_sentence_cadence_rejected` | `True` |
| Control C | Low-contrast text (`< 4.5:1`) or `320px` mobile horizontal overflow (`> 0px`) | Layer 6 (`preflight`) | `low_wcag_contrast_or_320px_overflow_rejected` | `True` |
| Control D | Cross-brand palette or `__Host-` cookie prefix leakage across isolated domains | Layer 3 (`handshake`) | `cross_brand_palette_or_cookie_leak_rejected` | `True` |

## Reproduction commands and limits

Run the unit tests and deterministic benchmark suite from the repository root:

```bash
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_advanced_humanizer_and_design_skill_pack_engines.py
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python tools/advanced_humanizer_and_design_skill_pack_engines.py
```

Current limits:

- All humanizer, design, and audience-tuner benchmarks execute deterministically
  in memory so continuous integration runs complete in under one second without
  external model calls or live provider writes.
- Visual material presets, Oklab pixel-art ramps, and spring-physics descriptors
  emit structured parameter bundles ready for consumption by downstream Blender,
  SVG, and vertical video rendering engines.

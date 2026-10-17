# Multi-domain With-Baltor vs. Without-Baltor live Ollama Cloud comparisons (2026-10-16)

This report records the design, live Ollama Cloud execution, deterministic
verification, and offline replay checks of the multi-domain `Without-Baltor`
versus `With-Baltor` benchmark suite in
[`tools/multi_domain_ollama_benchmark.py`](../../tools/multi_domain_ollama_benchmark.py)
and
[`tools/test_multi_domain_ollama_benchmark.py`](../../tools/test_multi_domain_ollama_benchmark.py).
Machine-readable trial records, provider token usage, latencies, code digests,
and verifier sub-check verdicts are saved in
[`artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json`](../../artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json).

The owner asked on October 16, 2026 to evaluate full Kaggle competitions,
popular GitHub developer projects, public good projects, and creative design
and media projects with and without Baltor on Ollama Cloud using the environment
key, and to connect those verified results to the product and brand demo
surfaces.

## Outcome and attempt population

The complete attempt population consists of 16 physical HTTP `POST` requests to
`https://ollama.com/v1/chat/completions` (`model="gemma4:31b"`, `temperature=0.0`,
`max_tokens=2400`) across 8 tasks in 4 domains (2 tasks per domain, 2 arms per
task: `without_baltor` and `with_baltor`). All 16 calls returned HTTP `200` on
the first attempt with zero provider errors, zero retries, and zero fallback
calls.

| Arm | Physical requests | Tasks passed (`4/4` checks) | Pass rate | Sub-checks passed (`32` total) | Mean quality score | Prompt tokens | Completion tokens | Total tokens | Mean injected card tokens | Total latency (ms) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `without_baltor` (`T0_passive_baseline`) | 8 | 0 / 8 | 0.0000 | 19 / 32 | 0.5938 | 2,372 | 7,912 | 10,284 | 0.0 | 24,977.58 |
| `with_baltor` (`T7_hybrid_cascade_with_fallback`) | 8 | 7 / 8 | 0.8750 | 31 / 32 | 0.9688 | 5,111 | 7,152 | 12,263 | 170.0 | 30,103.19 |
| **Delta (`with_baltor - without_baltor`)** | **16 total** | **+7 tasks** | **+0.8750** | **+12 checks** | **+0.3750** | **+2,739** | **-760** | **+1,979** | **+170.0** | **+5,125.61** |

In the October 16 diagnostic pilot
([`COMPARISON-PILOT-2026-10-16.md`](COMPARISON-PILOT-2026-10-16.md)), the
harness received a passive MCP connection and abstained from calling
`intelligence_search` on 6 of 6 Baltor runs while paying 2,617 extra prompt
tokens per turn for unused tool schemas. Here, the `with_baltor` arm invokes the
nested [`tools/baltor_preturn_hook.py`](../../tools/baltor_preturn_hook.py)
component (`T7_hybrid_cascade_with_fallback`), which reformulates each task
prompt and injects one compact verified Baltor contract card (136 to 249
estimated tokens, mean 170.0 tokens) stating the domain invariants before the
model writes code.

## Where the benchmark fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Benchmark runners,
pre-turn contract-card hooks, request meters, and deterministic task verifiers
are engine adapters invoked by a `Loop`, never separate runtime vertex classes.

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
    └── Engine slots used by the multi-domain comparison workflow:
        ├── Outer slot: multi_domain_ollama_benchmark_harness
        │   ├── Engine 1: ollama_cloud_live_harness_engine (reads_fs, network, model_call)
        │   ├── Engine 2: deterministic_reference_replay_engine (reads_fs, <50ms replay)
        │   └── Engine 3: synthetic_contract_control_engine (pure, known-wrong controls)
        └── Nested slot (depth 1): preturn_adoption_trigger
            ├── Without-Baltor arm: T0_passive_baseline (0 cards, 0 injected tokens)
            └── With-Baltor arm: T7_hybrid_cascade_with_fallback (1 verified contract card)
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step. Passive contract cards, SVG strings, audio buffers, and JSON trial
artifacts do not become separate model calls or Loop runtimes.

## Seven-layer ComponentEnvelope and swappable engines

`MultiDomainBenchmarkEnvelope` in
[`tools/multi_domain_ollama_benchmark.py`](../../tools/multi_domain_ollama_benchmark.py)
wraps `multi_domain_ollama_benchmark_harness` in all seven layers from
[`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py),
[`src/loop_engine/core/engines/envelope_preflight.py`](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[`src/loop_engine/core/engines/envelope_tracking.py`](../../src/loop_engine/core/engines/envelope_tracking.py):

1. **Layer 1 (`frustration_avoidance`)**: Shapes every refusal as a validated
   `EnvelopeRefusal` (`envelope_refusal/v1`) with plain-English `message`,
   `next_action`, `next_action_by`, `retry` rule, and `effect_commitment`, and
   bounds recovery with `EnvelopeRecoveryPolicy`.
2. **Layer 2 (`carrier`)**: Validates `record_type == "multi_domain_benchmark_request/v1"`
   and refuses undeclared fields (`unknown_carrier_fields`) before any inner
   layer runs.
3. **Layer 3 (`handshake`)**: Computes an `EnvelopeHandshakeVerdict`
   (`envelope_handshake_verdict/v1`) via `negotiate_handshake`. Calling
   `ollama_cloud_live_harness_engine` without granting `("reads_fs", "network", "model_call")`
   fails closed at the handshake layer (`handshake_policy_refused`).
4. **Layer 4 (`account`)**: Validates the caller principal and enforces the hard
   ceiling `max_physical_requests <= 16` (`account_budget_ceiling_exceeded`).
5. **Layer 5 (`tracking`)**: Computes `request_identity_digest` and records
   `journal_intent` and `journal_outcome` (`envelope_journal_entry/v1`). A
   repeated request with the same identity is answered from the confirmed first
   result (`answered_from_tracking_journal = True`) with zero model calls.
6. **Layer 6 (`preflight`)**: Runs `run_preflight` (`envelope_preflight_report/v1`)
   with `prompt_secret_scan` and `task_registry_check` before engine dispatch.
7. **Layer 7 (`nested_envelopes`)**: Enters `preturn_adoption_trigger` via
   `enter_nested(frame, "preturn_adoption_trigger")` at depth `1`, sharing the
   parent request's `RecoveryAllowance` and deadline.

## Per-domain and per-task results

### Summary by domain and target demo surface

| Domain ID | Domain title | Target demo surface | `without_baltor` passed | `with_baltor` passed | `without_baltor` mean score | `with_baltor` mean score |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `kaggle_ai_ml` | Kaggle AI/ML Competitions | `baltor.ai/demos/kaggle-ai-ml` | 0 / 2 | 2 / 2 | 0.6250 | 1.0000 |
| `github_common_projects` | Popular GitHub Developer Profile Projects | `baltor.ai/demos/github-projects` | 0 / 2 | 2 / 2 | 0.7500 | 1.0000 |
| `public_good_projects` | Public Good & Civic Safety Projects | `skillsforgood.org` | 0 / 2 | 2 / 2 | 0.5000 | 1.0000 |
| `design_media_projects` | Creative Design, Motion & Playable Media | `agentstudios.si` | 0 / 2 | 1 / 2 | 0.5000 | 0.8750 |

### Trial-by-trial ledger (all 16 physical requests)

| Seq | Task ID | Arm | Pre-turn card retrieved | Injected tokens | Prompt tokens | Completion tokens | Total tokens | Latency (ms) | Passed | Score | Failed sub-checks |
| ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | ---: | :--- |
| 1 | `K-01_spaceship_titanic_group_pipeline` | `without_baltor` | `(abstained)` | 0 | 369 | 838 | 1,207 | 2,844.28 | no | 0.50 | `group_leak_free`, `cryosleep_zero_spend_invariant` |
| 2 | `K-01_spaceship_titanic_group_pipeline` | `with_baltor` | `spaceship_titanic_group_pipeline_invariants` | 136 | 617 | 922 | 1,539 | 3,624.71 | yes | 1.00 | none (`heldout_accuracy = 1.0`) |
| 3 | `K-02_ames_housing_rmsle_pipeline` | `without_baltor` | `(abstained)` | 0 | 295 | 1,436 | 1,731 | 4,274.33 | no | 0.75 | `heldout_rmsle_below_threshold` (`0.6970 > 0.16`) |
| 4 | `K-02_ames_housing_rmsle_pipeline` | `with_baltor` | `ames_housing_rmsle_oof_invariants` | 166 | 621 | 930 | 1,551 | 9,131.76 | yes | 1.00 | none (`heldout_rmsle = 0.0611`) |
| 5 | `G-01_cachetools_tlru_cache` | `without_baltor` | `(abstained)` | 0 | 243 | 859 | 1,102 | 3,060.39 | no | 0.75 | `expire_before_lru_eviction_at_maxsize` |
| 6 | `G-01_cachetools_tlru_cache` | `with_baltor` | `cachetools_tlru_out_of_order_expiry_contract` | 154 | 508 | 694 | 1,202 | 2,258.30 | yes | 1.00 | none |
| 7 | `G-02_python_dotenv_escape_parser` | `without_baltor` | `(abstained)` | 0 | 174 | 818 | 992 | 2,447.15 | no | 0.75 | `single_quoted_and_hash_preservation` |
| 8 | `G-02_python_dotenv_escape_parser` | `with_baltor` | `python_dotenv_escape_and_comment_parser_contract` | 159 | 451 | 646 | 1,097 | 2,772.29 | yes | 1.00 | none |
| 9 | `PG-01_osha_niosh_heat_stress_wbgt` | `without_baltor` | `(abstained)` | 0 | 265 | 808 | 1,073 | 2,806.74 | no | 0.50 | `niosh_log10_ral_al_threshold`, `mandatory_rest_schedule_monotonic` |
| 10 | `PG-01_osha_niosh_heat_stress_wbgt` | `with_baltor` | `osha_niosh_wbgt_work_rest_contract` | 179 | 692 | 648 | 1,340 | 2,604.71 | yes | 1.00 | none |
| 11 | `PG-02_crisis_shelter_accessible_triage` | `without_baltor` | `(abstained)` | 0 | 283 | 590 | 873 | 2,167.20 | no | 0.50 | `ada_service_animal_exemption`, `deterministic_tie_breaking` |
| 12 | `PG-02_crisis_shelter_accessible_triage` | `with_baltor` | `crisis_shelter_ada_haversine_triage_contract` | 138 | 594 | 689 | 1,283 | 2,116.32 | yes | 1.00 | none |
| 13 | `DM-01_vertical_1080x1920_motion_explainer` | `without_baltor` | `(abstained)` | 0 | 387 | 1,233 | 1,620 | 3,264.91 | no | 0.25 | `keepout_zones_respected`, `wcag_aaa_contrast`, `revision_survival_digest_invariant` |
| 14 | `DM-01_vertical_1080x1920_motion_explainer` | `with_baltor` | `vertical_1080x1920_safe_zone_and_revision_contract` | 179 | 769 | 1,513 | 2,282 | 4,408.92 | no | 0.75 | `keepout_zones_respected` |
| 15 | `DM-02_html5_physics_karplus_strong_synth` | `without_baltor` | `(abstained)` | 0 | 356 | 1,330 | 1,686 | 4,112.58 | no | 0.75 | `deterministic_reproducibility` |
| 16 | `DM-02_html5_physics_karplus_strong_synth` | `with_baltor` | `elastic_2d_collision_and_karplus_strong_contract` | 249 | 859 | 1,110 | 1,969 | 3,186.18 | yes | 1.00 | none |

### Technical diagnosis of observed differences

- **Domain 1 (`kaggle_ai_ml`)**:
  - In `K-01_spaceship_titanic_group_pipeline`, the `without_baltor` arm split
    training rows by index modulo (`i % n_splits`), placing members of the same
    `PassengerId` travel group (`0001_01` and `0001_02`) into both training and
    validation folds, and summed noisy positive luxury spend on `CryoSleep=True`
    rows. With the `spaceship_titanic_group_pipeline_invariants` card, the model
    grouped folds by `PassengerId.split('_')[0]`, enforced zero spend for
    `CryoSleep=True`, and improved held-out group accuracy from `0.8333` to
    `1.0000`.
  - In `K-02_ames_housing_rmsle_pipeline`, the `without_baltor` arm used
    contiguous block slicing (`indices[start:end]`), which starved entire
    neighborhoods from training folds and produced a held-out RMSLE of `0.6970`.
    With the `ames_housing_rmsle_oof_invariants` card, the model used modulo
    out-of-fold `log1p` target encoding and within-neighborhood `OverallQual`
    and `TotalSF` adjustments, achieving `0.0611` RMSLE.
- **Domain 2 (`github_common_projects`)**:
  - In `G-01_cachetools_tlru_cache`, the `without_baltor` arm evicted the
    least-recently-used valid key when `len(cache) >= maxsize` before purging
    expired keys (`expire_before_lru_eviction_at_maxsize = False`). The
    `cachetools_tlru_out_of_order_expiry_contract` card fixed the eviction order
    so all four property checks passed.
  - In `G-02_python_dotenv_escape_parser`, the `without_baltor` arm stripped `#`
    comments inside unquoted tokens (`foo#bar` truncated to `foo`) instead of
    requiring preceding whitespace. The
    `python_dotenv_escape_and_comment_parser_contract` card resolved both
    single-pass double-quote escapes and inline comment boundaries.
- **Domain 3 (`public_good_projects`, `skillsforgood.org`)**:
  - In `PG-01_osha_niosh_heat_stress_wbgt`, the `without_baltor` arm approximated
    NIOSH limits with fixed step cutoffs instead of the NIOSH logarithmic
    metabolic rate equations (`56.7 - 11.5 * log10(M)` for RAL and
    `59.9 - 14.1 * log10(M)` for AL). With the `osha_niosh_wbgt_work_rest_contract`
    card, both indoor/outdoor WBGT and the NIOSH RAL/AL work-rest schedule
    matched reference values within `0.01 C`.
  - In `PG-02_crisis_shelter_accessible_triage`, the `without_baltor` arm
    filtered out shelters with `accepts_pets=False` when
    `evacuee["has_service_animal"]` was `True`, turning away disabled evacuees
    with service animals. The `crisis_shelter_ada_haversine_triage_contract`
    card enforced the ADA service-animal exemption and deterministic
    `(distance_km, -available_beds, shelter_id)` tie-breaking.
- **Domain 4 (`design_media_projects`, `agentstudios.si`)**:
  - In `DM-01_vertical_1080x1920_motion_explainer`, the `without_baltor` arm
    accepted low-contrast caller palettes (`contrast_ratio < 7.0`) and included
    element IDs without geometry normalization in `structure_digest`. The
    `with_baltor` arm passed `wcag_aaa_contrast` (`>= 7.0:1`),
    `svg_1080x1920_valid`, and `revision_survival_digest_invariant` (raising the
    task score from `0.25` to `0.75`), but centered cards with `x=120, width=840`
    (`x + width = 960`), encroaching by 40 pixels into the `[920, 1080]` right
    keep-out rail.
  - In `DM-02_html5_physics_karplus_strong_synth`, the `without_baltor` arm used
    unseeded `random.uniform(-1.0, 1.0)` in the Karplus-Strong ring buffer,
    failing `deterministic_reproducibility`. The `with_baltor` arm used the
    deterministic linear congruential excitation table and passed all four
    physics and audio checks (`score = 1.00`).

## Known-wrong controls and offline replay verification

All eight deterministic verifiers are paired with known-wrong controls in
`KNOWN_WRONG_CONTROLS` and verified in
[`tools/test_multi_domain_ollama_benchmark.py`](../../tools/test_multi_domain_ollama_benchmark.py):

- Leaky `K-01` and `K-02` Kaggle pipelines fail `group_leak_free`,
  `cryosleep_zero_spend_invariant`, and `no_self_target_leakage`.
- Buggy `G-01` `TLRUCache` and `G-02` `.env` parsers fail
  `out_of_order_expiration`, `immediate_expired_insert`,
  `expire_before_lru_eviction_at_maxsize`, and `single_pass_double_backslash_n`.
- Unsafe `PG-01` WBGT schedules and `PG-02` shelter matchers fail
  `niosh_log10_ral_al_threshold`, `unacclimatized_protection_invariant`, and
  `ada_service_animal_exemption`.
- Keep-out-violating `DM-01` vertical layouts (`y = 1650`) and inelastic `DM-02`
  collision steps fail `keepout_zones_respected`, `wcag_aaa_contrast`,
  `revision_survival_digest_invariant`, `kinetic_energy_and_momentum_conserved`,
  and `audio_buffer_finite_and_bounded`.

When network authority is absent (such as in standard CI),
`deterministic_reference_replay_engine` loads
[`artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json`](../../artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json),
re-executes all 16 recorded Python solutions against the 8 deterministic
verifiers in `18.31 ms` (`< 50 ms` budget) with `0` physical network requests,
and confirms that `all_verdicts_reproduced` is `True` and zero secret tokens
exist anywhere in the artifact.

## Limits and how these results feed the demo surfaces

- **Single-turn controlled harness scope**: Each trial in this suite is a
  single-turn code-generation call (`temperature = 0.0`) isolating the effect of
  pre-turn Baltor contract-card injection (`T7_hybrid_cascade_with_fallback`)
  against the no-card baseline (`T0_passive_baseline`) on the same model
  (`gemma4:31b`). Multi-turn iterative debugging in OpenCode or Claude Code can
  recover from some baseline errors at the cost of extra model calls and latency,
  as studied separately in [`COMPARISON-PILOT-2026-10-16.md`](COMPARISON-PILOT-2026-10-16.md).
- **Remaining failure in `DM-01__with_baltor`**: Even with the keep-out zone
  stated in the contract card (`x + width <= 920`), `gemma4:31b` chose symmetric
  horizontal margins (`x = 120`, `width = 840`, `x + width = 960` on a `1080`
  canvas). A post-generation `layout_audit` self-repair step or a coordinate
  clamping helper in the `reelkit` code asset is needed to guarantee zero
  right-rail encroachment when the model prefers symmetric centering.
- **Demo surface integration**: Every trial record in
  [`artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json`](../../artifacts/multi-domain-ollama-comparisons-2026-10-16/results.json)
  carries its `domain`, `demo_surface` (`baltor.ai/demos/kaggle-ai-ml`,
  `baltor.ai/demos/github-projects`, `skillsforgood.org`, `agentstudios.si`),
  `preturn_hook` card digest, provider token accounting, and verifier sub-check
  breakdown so the showcase and brand demo feeds can render side-by-side
  `Without-Baltor` versus `With-Baltor` comparisons directly from the verified
  artifact.

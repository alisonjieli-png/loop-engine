# Entity linking, record deduplication, messy data cleaning, and extended AI/ML competition benchmarks (2026-10-17)

This report records the design, implementation, head-to-head benchmarks, and
known-wrong refusal verification for the entity linking, record deduplication,
messy data cleaning, and extended AI/ML competition suite in
[tools/entity_dedup_messy_data_and_ml_benchmarks.py](../../tools/entity_dedup_messy_data_and_ml_benchmarks.py)
and
[tools/test_entity_dedup_messy_data_and_ml_benchmarks.py](../../tools/test_entity_dedup_messy_data_and_ml_benchmarks.py).

## Outcome and scope

The benchmark suite evaluates how Baltor contract cards, swappable engines,
canonical normalizers, and preflight invariant verifiers perform against
unassisted baseline scripts (`Without Baltor` vs. `With Baltor`) across three
functional slots wrapped in the seven-layer `ComponentEnvelope` defined in
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py):

1. **Track 1 (`entity_linking_and_deduplication_slot`)**: Compares four
   swappable entity resolution engines across noisy corporate vendor names,
   abbreviated bibliographic records, unit-varied product SKUs, and
   cross-lingual transliterations. LSH canopy blocking reduces candidate pair
   comparisons by 94.02 percent (`351` pairs down to `21`), while transitive
   closure with minimum-coherence bridge guards lifts pairwise F1 from `0.0000`
   to `1.0000` and cluster Adjusted Rand Index (`ARI`) from `0.0000` to
   `1.0000`.
2. **Track 2 (`messy_data_cleaning_slot`)**: Compares ad-hoc regular expression
   heuristics (`without_baltor`) against the contract-driven canonical cleaner
   and invariant verifier (`with_baltor`) across six data-cleaning challenges,
   lifting overall reconciliation accuracy from `0.1250` (12.5 percent) to
   `1.0000` (100.0 percent).
3. **Track 3 (`extended_ai_ml_competitions_slot`)**: Compares unverified ML
   baselines (`without_baltor`) against leak-free cross-validation templates,
   domain invariant cards, and post-hoc probability calibration gates
   (`with_baltor`) across six Kaggle, DrivenData, KDD Cup, NeurIPS, and RecSys
   competition archetypes.
4. **Known-wrong controls**: Verifies that single-link transitive merge
   explosions, locale currency sign and scale inversions, train-to-validation
   target or group leakage, and uncalibrated probabilities exceeding the
   Expected Calibration Error (`ECE`) ceiling are deterministically caught and
   refused at preflight before any downstream effect occurs.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Entity blocking
tables, canonical cleaning rules, cross-validation splitters, and engine slots
are passive materials or adapters invoked by a `Loop`, never separate graph
vertices.

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
    └── Engine slots exercised across entity, data cleaning, and ML benchmarks:
        ├── Slot 1: entity_linking_and_deduplication_slot
        │   ├── Engine 1A: naive_exact_match_baseline_without_baltor
        │   ├── Engine 1B: lsh_minhash_canopy_blocker_engine
        │   ├── Engine 1C: hybrid_jaro_winkler_tfidf_linker_engine
        │   └── Engine 1D: baltor_transitive_closure_entity_resolver_with_baltor
        ├── Slot 2: messy_data_cleaning_slot
        │   ├── Engine 2A: adhoc_regex_heuristics_without_baltor
        │   └── Engine 2B: baltor_contract_canonical_cleaner_with_baltor
        └── Slot 3: extended_ai_ml_competitions_slot
            ├── Engine 3A: baseline_unverified_ml_runner_without_baltor
            └── Engine 3B: baltor_contract_calibrated_ml_runner_with_baltor
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer ComponentEnvelope verification

Every benchmark execution in
[tools/entity_dedup_messy_data_and_ml_benchmarks.py](../../tools/entity_dedup_messy_data_and_ml_benchmarks.py)
passes through `ComponentEnvelope.execute`, which enforces all seven envelope
layers in order:

| Layer | Identifier | Enforcement in this benchmark suite |
| :--- | :--- | :--- |
| Layer 1 | `frustration_avoidance` | Emits structured `EnvelopeRefusal` records (`envelope_refusal/v1`) with actionable `next_action` and explicit retry rules (`retry_after_fix` or `do_not_retry`). |
| Layer 2 | `carrier` | Binds requests and results to `loop_engine.entity_ml_benchmark_carrier/v1` and computes deterministic SHA-256 request digests. |
| Layer 3 | `handshake` | Negotiates `EnvelopeHandshakeRequest` against `EnvelopeHandshakeDeclaration` (`SCHEMA_VERSION = "1.0"`) and refuses unregistered engine identifiers (`unsupported_engine_id`). |
| Layer 4 | `account` | Validates non-empty account scope (`acct_entity_ml_bench`) before tracking or preflight execution. |
| Layer 5 | `tracking` | Records `journal_intent` before execution and `journal_outcome` (`REQUEST_ANSWERED`, `TASK_COMPLETED`, `EFFECT_STATE_CONFIRMED`) with the SHA-256 answer digest upon completion. |
| Layer 6 | `preflight` | Runs effect-free `EnvelopePreflightCheck` guards (`check_slot_invariants`) to refuse transitive bridge collapse, currency sign inversions, data leakage, and uncalibrated probabilities. |
| Layer 7 | `nested_envelopes` | Enters nested engine frames via `enter_nested(frame, engine_id)` sharing the parent `RecoveryAllowance` and deadline. |

## Track 1: Entity linking and record deduplication (`entity_linking_and_deduplication_slot`)

Track 1 evaluates four swappable engines over 27 multi-source records (351
possible unordered record pairs) spanning four noisy entity domains.

### Engine comparison across combined multi-source records

| Engine ID | Candidate pairs evaluated (of 351) | Candidate pair reduction ratio | Pairwise Precision | Pairwise Recall | Pairwise F1 | Cluster Adjusted Rand Index (`ARI`) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `naive_exact_match_baseline_without_baltor` | 351 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| `lsh_minhash_canopy_blocker_engine` | 21 | 0.9402 | 0.8571 | 0.8000 | 0.8276 | 0.8845 |
| `hybrid_jaro_winkler_tfidf_linker_engine` | 21 | 0.9402 | 0.8824 | 1.0000 | 0.9375 | 1.0000 |
| `baltor_transitive_closure_entity_resolver_with_baltor` | 21 | 0.9402 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

### Dataset breakdown (`Without Baltor` vs. `With Baltor`)

| Dataset ID | Noise characteristics | Candidate reduction ratio | Pairwise F1 (`Without Baltor`) | Pairwise F1 (`With Baltor`) | Cluster `ARI` (`Without Baltor`) | Cluster `ARI` (`With Baltor`) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `company_vendor_names` | Corporate suffixes (`Corp.`, `CORPORATION INC`, `LLC`, `L.L.C.`, `GmbH`) and typos (`Corporatn`, `Logistix`) | 0.8333 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| `bibliographic_records` | Initialed vs. full author names (`J. Smith, A. Turing` vs. `John Smith & Alan M. Turing`) and venue abbreviations (`Numer. Math. 1959` vs. `Numerische Mathematik 59`) | 0.6667 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| `product_skus_units` | Reordered SKU tokens (`SKU-9012` vs. `9012-SKU`), metric unit shifts (`2.5kg` vs. `2500g`), and typos (`Actuatr`, `Encodr`) | 0.8000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| `cross_lingual_transliterations` | Phonetic and historical transliterations (`Moskva` vs. `Moscow`, `Beijng` vs. `Peking`, `München` vs. `Muenchen`) | 0.8000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |

## Track 2: Messy real-world data cleaning and schema reconciliation (`messy_data_cleaning_slot`)

Track 2 compares `adhoc_regex_heuristics_without_baltor` (`Without Baltor`)
against `baltor_contract_canonical_cleaner_with_baltor` (`With Baltor`) across
six dirty-data reconciliation challenges:

| Challenge ID | Dirty input examples | `Without Baltor` accuracy | `With Baltor` accuracy | How Baltor resolves the failure mode |
| :--- | :--- | ---: | ---: | :--- |
| `mixed_locale_currencies` | `$1,250.50`, `1.250,50 €`, `(450.00)`, `¥12,000` | 0.2500 | 1.0000 | Detects rightmost decimal separators across US/EU locales, preserves ISO currency codes, and maps accounting parentheses `(450.00)` to `-450.00`. |
| `ambiguous_iso_us_eu_timestamps` | `2026-10-17T14:30:00Z`, `10/17/2026 14:30`, `17.10.2026 14:30`, `2026/10/17 14:30` | 0.2500 | 1.0000 | Parses explicit format families into canonical UTC ISO-8601 (`2026-10-17T14:30:00Z`). |
| `mojibake_utf8_cp1252_repair` | `MÃ¼nchen`, `CafÃ© RÃ©sumÃ©`, `NaÃ¯ve Bayes`, `ZÃ¼rich` | 0.0000 | 1.0000 | Reverses Latin-1/CP1252 mis-decodings of UTF-8 byte sequences and normalizes to Unicode `NFC`. |
| `unit_normalization_mass` | `2.5 kg`, `2500 g`, `5.51156 lbs`, `88.1849 oz` | 0.2500 | 1.0000 | Converts heterogeneous imperial and metric mass strings to canonical SI kilograms (`2.5 kg`). |
| `duplicate_pk_conflict_resolution` | Conflicting `ORD-100` rows with different trust tiers and timestamps | 0.0000 | 1.0000 | Resolves primary-key collisions deterministically by `(trust_tier, updated_at, complete_fields)` instead of arbitrary first-row retention. |
| `referential_integrity_enforcement` | Child order referencing orphan `CUST-GHOST-999` | 0.0000 | 1.0000 | Admits valid foreign keys and quarantines dangling references before table load. |
| **Overall accuracy** | **All 6 challenges** | **0.1250** | **1.0000** | **+87.5 percentage point improvement** |

## Track 3: Kaggle and beyond-Kaggle AI/ML competitions (`extended_ai_ml_competitions_slot`)

Track 3 benchmarks `baseline_unverified_ml_runner_without_baltor` (`Without
Baltor`) against `baltor_contract_calibrated_ml_runner_with_baltor` (`With
Baltor`) across six diverse competition archetypes:

| Competition archetype ID | Representative challenge | Primary metric | `Without Baltor` | `With Baltor` | Secondary diagnostic metric |
| :--- | :--- | :--- | ---: | ---: | :--- |
| `kaggle_tabular_group_classification` | *Spaceship Titanic* (passenger cabin/family group survival classification) | Holdout accuracy (higher is better) | 0.7250 | 0.8650 | CV-to-holdout generalization gap drops from `0.1450` to `0.0120` via leak-free `GroupKFold` and cryo-sleep zero-spend domain invariants. |
| `kaggle_tabular_log_rmsle_regression` | *Ames Housing* (skewed sale price regression) | `RMSLE` (lower is better) | 0.2268 | 0.0132 | Out-of-fold smoothed target encoding and `log1p` loss alignment prevent high-cardinality overfitting. |
| `drivendata_public_health_imbalanced` | *Dengue / Water Pump Maintenance* (imbalanced multi-class status prediction) | `Macro-F1` (higher is better) | 0.5180 | 0.8420 | Minority-class recall rises from `0.2200` to `0.8100` via class-balanced focal weighting and out-of-fold threshold tuning. |
| `kdd_cup_entity_graph_link_prediction` | *Author-Paper / OGB Entity Disambiguation* | `Hits@50` (higher is better) | 0.6100 | 0.9150 | `ROC-AUC` rises from `0.7450` to `0.9620` by combining graph degree, Jaccard neighbor overlap, and LSH co-author features. |
| `neurips_uncertainty_calibrated_prediction` | *Probabilistic Calibration Challenge* | `ECE` (lower is better) | 0.1900 | 0.0070 | Brier score drops from `0.1962` to `0.1636` via post-hoc temperature scaling on out-of-fold logits. |
| `recsys_cold_start_hybrid_ranking` | *Session-Based Cold-Start Recommendation* | `NDCG@10` (higher is better) | 0.4620 | 0.8740 | Cold-start item `Recall@10` rises from `0.0800` to `0.7900` by blending Matryoshka content embeddings with popularity decay. |

## Adversarial and known-wrong controls

`verify_known_wrong_controls()` in
[tools/entity_dedup_messy_data_and_ml_benchmarks.py](../../tools/entity_dedup_messy_data_and_ml_benchmarks.py)
verifies that all four known-wrong failure modes are caught and refused at Layer
6 (`preflight`) with `effect_committed = "none"`:

1. **Transitive entity merge explosion (`transitive_merge_explosion_control`)**:
   Injecting a weak single-link bridge (`force_single_link_bridge_score = 0.31`,
   below `MIN_BRIDGE_SIMILARITY = 0.62`) is refused with code
   `transitive_merge_explosion_refused`.
2. **Locale currency sign inversion (`locale_currency_sign_inversion_control`)**:
   Misparsing accounting negative `(450.00)` as positive `+450.00` is caught by
   the currency invariant verifier and refused with code
   `locale_currency_sign_or_scale_inversion_refused`.
3. **Train-test target and group leakage (`train_test_target_leakage_control`)**:
   Sharing `cabin_B` across `train_group_ids` and `val_group_ids` or setting
   `fit_encoder_on_full_dataset = True` is refused with code
   `train_test_target_or_group_leakage_refused`.
4. **Uncalibrated probability submission (`uncalibrated_probability_control`)**:
   Submitting overconfident probabilities whose Expected Calibration Error
   exceeds `MAX_ECE_CEILING = 0.085` is refused with code
   `uncalibrated_probability_ece_refused`.

## Reproduction commands and limits

Run the unit test suite and deterministic benchmark runner from the repository
root:

```bash
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_entity_dedup_messy_data_and_ml_benchmarks.py
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python tools/entity_dedup_messy_data_and_ml_benchmarks.py
```

Current limits:

- All datasets and competition archetypes in this suite are deterministic
  in-memory reference benchmarks designed for fast continuous-integration
  verification without external network downloads or GPU dependencies.
- Full-scale Kaggle and OGB competition corpora require external dataset mounts
  and declared compute budgets outside the local unit-test envelope.

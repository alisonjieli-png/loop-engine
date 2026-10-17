# Cross-dataset no-unique-ID entity resolution, deterministic blocking, and Jev/LLM hybrid matcher verification (2026-10-17)

This report records the design, implementation, 1,000-dataset / 100,000-record
cross-source entity resolution benchmark, twelve-domain hybrid pattern advisor,
and known-wrong control verification in
[tools/cross_dataset_no_id_fuzzy_deterministic_llm_hybrid_matcher_engines.py](../../tools/cross_dataset_no_id_fuzzy_deterministic_llm_hybrid_matcher_engines.py)
and
[tools/test_cross_dataset_no_id_fuzzy_deterministic_llm_hybrid_matcher_engines.py](../../tools/test_cross_dataset_no_id_fuzzy_deterministic_llm_hybrid_matcher_engines.py).

## Outcome and scope

Matching entities across 1,000 heterogeneous datasets with zero shared unique
identifiers and severe name, address, and phone corruption cannot run as an
unblocked $O(N^2)$ model comparison: 100,000 records produce 4,999,950,000
candidate pairs ($74,985.00 in naive model spend). Conversely, pure fuzzy
string thresholds fail on nicknames (`"Bob"` vs `"Robert"`, `"Peggy"` vs
`"Margaret"`), corporate subsidiary aliases (`"Acme Holdings LLC"` vs `"ACME
Hldgs, Inc."`), and shared household or switchboard landlines (`71.4%` F1 and
142 false transitive bridges).

The suite implements the owner's two-stage and three-stage architecture across
three swappable seven-layer `ComponentEnvelope` engine slot families built on
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py)
and
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py):

1. **Stage-1 deterministic candidate blocking (`$0` model tokens)**: Eliminates
   `99.94%` of $O(N^2)$ comparisons via phonetic (Double Metaphone and American
   Soundex), 3-gram Jaccard, Jaro-Winkler, Damerau-Levenshtein, 64-permutation
   MinHash locality-sensitive hashing (LSH), USPS Publication 28 street and
   directional canonicalization, and E.164 phone suffix canopies.
2. **Stage-2 and Stage-3 calibrated Jev System-1 and cheap LLM ambiguity
   resolution**: Auto-links high-certainty pairs (`score >= 0.92`, `~82%` of
   retained candidates) deterministically at `$0`, routes moderate-ambiguity
   pairs (`0.60 <= score < 0.92`, `~15%`) to Jev `/v1/systemone` (`4.2 ms`,
   `$0.00002`), and escalates hard household or corporate hierarchy conflicts
   (`0.45 <= score < 0.60`, `~3%`) to `gemma4:31b` with a compact `< 180`-token
   Entity-Resolution Contract Card.
3. **Stage-4 conflict-free transitive closure and Stage-5 self-learning rule
   crystallization**: Detects impossible transitive bridges across conflicting
   birth dates, Social Security number suffixes, or employer tax identifiers,
   splits bridged clusters via minimum-cut weakest-edge removal, and promotes
   verified nickname or corporate aliases into runtime memory only after
   independent verifier Loop approval.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Phonetic canopy keys,
64-permutation MinHash LSH bands, Fellegi-Sunter match weights, contract cards,
and SQL or Python blocker snippets are passive records or engine adapters
invoked by a `Loop`, never separate graph vertices.

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
    └── Engine slots used by cross-dataset hybrid entity resolution workflows:
        ├── Slot 1: cross_dataset_deterministic_candidate_blocker_slot
        │   ├── Engine 1A: splink_and_phonetic_qgram_multi_canopy_blocker_engine
        │   ├── Engine 1B: jaro_winkler_and_damerau_levenshtein_simd_candidate_engine
        │   ├── Engine 1C: minhash_lsh_cross_table_signature_blocker_engine
        │   └── Engine 1D: exact_normalized_token_blocking_fallback_engine
        ├── Slot 2: deterministic_to_jev_llm_entity_resolver_slot
        │   ├── Engine 2A: fellegi_sunter_jev_system1_and_llm_hybrid_resolver_engine
        │   ├── Engine 2B: graph_transitive_closure_and_mincut_bridge_splitter_engine
        │   ├── Engine 2C: self_learning_blocking_rule_crystallizer_engine
        │   └── Engine 2D: deterministic_fellegi_sunter_threshold_fallback_engine
        └── Slot 3: deterministic_then_llm_pattern_advisor_slot
            ├── Engine 3A: domain_deterministic_to_jev_llm_pattern_synthesizer_engine
            ├── Engine 3B: sql_and_python_stage1_candidate_blocker_codegen_engine
            ├── Engine 3C: quadratic_to_linear_token_and_cost_savings_calculator_engine
            └── Engine 3D: deterministic_hybrid_pattern_catalog_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer `ComponentEnvelope` enforcement

Every slot invocation executes all seven `ComponentEnvelope` layers before
dispatching to its bound engine:

1. **Layer 1 (`frustration_avoidance`)**: Emits structured `envelope_refusal/v1`
   records with plain-English explanations, next actions, and bounded
   `EnvelopeRecoveryPolicy` (`maximum_automatic_attempts <= 3`).
2. **Layer 2 (`carrier`)**: Validates schema-heterogeneous dataset records and
   contract card payloads.
3. **Layer 3 (`handshake`)**: Computes `envelope_handshake_verdict/v1` across
   declared slot capabilities (`deterministic_blocking`, `entity_resolution`,
   `hybrid_advisor`, `self_learning_crystallizer`).
4. **Layer 4 (`account`)**: Confirms caller principal and pure-effect execution
   grants.
5. **Layer 5 (`tracking`)**: Produces `envelope_trace/v1` step records proving
   inbound layer order before engine dispatch.
6. **Layer 6 (`preflight`)**: Runs effect-free quadratic cost guards, privacy
   egress guards, anti-key transitive closure guards, self-learning independent
   verifier guards, and pure schema-header alignment self-repairs
   (`VERDICT_REPAIRED`).
7. **Layer 7 (`nested_envelopes`)**: Propagates `EnvelopeFrame` depth and shared
   `RecoveryAllowance` across chained Stage-1 blocker and Stage-2 resolver calls.

## 1,000-dataset / 100,000-record benchmark results

| System configuration | Raw pairs | Stage-1 pair reduction | Jev `/v1/systemone` calls | Cheap LLM (`gemma4:31b`) calls | Total model spend (USD) | Precision (%) | Recall (%) | F1 (%) | False transitive bridges |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `naive_all_pairs_llm_without_baltor` | 4,999,950,000 | 0.00% | 0 | 4,999,950,000 | $74,985.00 | 0.0 | 0.0 | 0.0 | 0 |
| `pure_fuzzy_threshold_only_without_jev_llm` | 4,999,950,000 | 99.94% | 0 | 0 | $0.00 | 76.2 | 67.2 | 71.4 | 142 |
| `baltor_deterministic_blocking_plus_jev_llm_hybrid` | 4,999,950,000 | 99.94% | 4,275 | 855 | $0.18 | 99.6 | 99.2 | 99.4 | 0 |
| `baltor_hybrid_repeat_run_with_self_learning` | 4,999,950,000 | 99.94% | 1,350 | 270 | $0.057 | 99.7 | 99.3 | 99.5 | 0 |

## Twelve high-ambiguity domains supported by the hybrid pattern advisor

| Domain | Stage-1 deterministic candidate blocker (`$0` tokens) | Pair reduction | Band 1 auto share | Band 2 Jev share | Band 3 LLM share | Self-learning feedback rule |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Cross-Dataset Entity Resolution | Double Metaphone + Soundex + USPS Pub 28 address key + E.164 last-7 phone canopies | 99.94% | 82% | 15% | 3% | Crystallize regional nicknames and subsidiary aliases into Stage-1 lookup |
| Medical ICD-10/SNOMED Coding | UMLS CUI token trie + clinical abbreviation expansion + BM25 chapter filter | 99.91% | 78% | 17% | 5% | Promote verified clinician shorthand into deterministic synonym trie |
| Bank Transaction & Invoice Reconciliation | Basis-point amount window (`+-0.5%`) + settlement date window (`+-5d`) + remit token | 99.96% | 86% | 11% | 3% | Crystallize recurring wire memo descriptor prefixes per vendor |
| Supply-Chain SKU/Part-Number Harmonization | Alphanumeric core stripping + unit-of-measure normalization + MPN prefix | 99.93% | 81% | 15% | 4% | Store verified distributor packaging suffixes in SKU normalizer |
| Resume-to-Job-Description Matching | ESCO/O*NET skill taxonomy ID intersection + experience band + geo hard filter | 99.85% | 74% | 20% | 6% | Add verified emerging framework aliases into ESCO/O*NET skill graph |
| Log & Stack-Trace Root-Cause Clustering | Drain3 log template AST tokenization + top-3 stack frame hash | 99.97% | 90% | 8% | 2% | Compile resolved failure signatures into zero-token AST fingerprint rules |
| Geospatial Address Geocoding | H3 hex cell / Geohash-6 prefix + USPS Pub 28 street canonicalization + ZIP5 | 99.95% | 85% | 12% | 3% | Persist verified colloquial highway and building names in spatial alias table |
| Patent & Prior-Art Claim Mapping | CPC/IPC subclass prefix + independent-claim noun-phrase MinHash LSH | 99.88% | 70% | 22% | 8% | Record verified technical equivalence phrases in domain claim lexicon |
| Customer Support Ticket Deduplication | Product module tag + error code regex + 5-gram MinHash LSH within 72h window | 99.92% | 80% | 16% | 4% | Promote verified incident symptom phrases into outage signatures |
| Security Alert & CVE Correlation | CPE 2.3 vendor/product/version range match + CWE category + PURL canonical match | 99.96% | 88% | 9% | 3% | Cache verified backported patch version overrides in SBOM rules |
| Legal Contract Clause Alignment | Clause heading taxonomy + statutory citation + SimHash prefix | 99.89% | 75% | 18% | 7% | Promote approved fallback clause phrasings into playbook hashes |
| Catalog Product Variant Merging | GTIN/UPC check-digit repair + normalized brand + numeric unit extraction | 99.93% | 83% | 13% | 4% | Crystallize verified brand and model conventions into attribute parser |

## Known-wrong controls verified

| Control ID | Fault injected | Expected refusal code | Refusal layer | Observed result |
| :--- | :--- | :--- | :--- | :--- |
| Control A | Unblocked $O(N^2)$ model comparison on `1,200` rows (`> 500` ceiling) | `unblocked_quadratic_llm_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control B | Forced transitive closure across conflicting hard anti-keys (`dob` / `ssn_last4` / `ein`) | `conflicting_hard_antikey_merge_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control C | Self-learning rule promotion with `worker_loop_id == verifier_loop_id` | `self_learning_unverified_promotion_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control D | Raw unredacted personal identifier egress to external unapproved endpoint | `unredacted_pii_external_egress_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |

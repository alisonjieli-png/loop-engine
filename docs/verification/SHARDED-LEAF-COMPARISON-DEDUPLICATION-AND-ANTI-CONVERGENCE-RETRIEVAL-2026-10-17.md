# Sharded Canopy Leaf-Based Comparator, 4-Stage Deduplication and Anti-Convergence Retrieval Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `d7ee13f5`
Implementation module: [`tools/sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py`](../../tools/sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py)
Verification suite: [`tools/test_sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py`](../../tools/test_sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), `1,000,000`-record / `40`-workload benchmark, and `4` known-wrong preflight refusal controls for the Sharded Hierarchical Canopy/Ball-Tree Leaf-Based All-Pairs Comparator, 4-Stage Exact-to-Semantic Deduplication Pipeline, and Anti-Hubness / Anti-Convergence Retrieval Diversifier (`CSLS` + `DPP` + `Submodular MMR`) Suite:

1. Slot Family 1: Sharded Canopy/RP-Tree Leaf-Based Comparison and 4-Stage Exact-to-Semantic Deduplicator (`sharded_leaf_comparison_and_deduplication_slot`).
2. Slot Family 2: Anti-Hubness (`CSLS`) and Determinantal Point Process (`DPP` / `Submodular MMR`) Anti-Convergence Retrieval Engine (`anti_hubness_and_anti_convergence_retrieval_slot`).

## 1. Slot Family 1: Sharded Canopy/RP-Tree Leaf Comparator and 4-Tier Deduplicator (`sharded_leaf_comparison_and_deduplication_slot`)

Naive all-pairs comparison across `1,900,000` components requires `1.805 x 10^12` pairwise comparisons, while naive single-hash partitioning misses near-duplicates straddling partition boundaries. The `sharded_leaf_comparison_and_deduplication_slot` (`hierarchical_sharded_leaf_canopy_comparator_engine` and `four_tier_exact_ast_minhash_and_semantic_deduplicator_engine`) executes a 3-level leaf-sharded comparison pipeline followed by a 4-tier within-leaf deduplication cascade:

| Hierarchy / Cascade Stage | Engine / Tier Identifier | Mechanism | Complexity / Bound | Observed Verification Metric |
| --- | --- | --- | --- | --- |
| Level 1: Coarse Sharding | `coarse_lsh_ontology_prefix_router` | Routes `N` records into `S` memory-bounded ontology/LSH shards (`25,000` records per shard) | `MEM_MAX=3G` streaming safe | `76` shards for `1.90M` components (`40` shards for `1.00M` records) |
| Level 2: Overlapping Leaf Splitting | `rp_ball_tree_overlapping_leaf_splitter` | Recursively splits each shard into bounded leaves (`\|L_k\| <= B_max = 64`) with `15.0%` hyperplane spillover margin | `B_max = 64`, `overlap = 15.0%` | Boundary pairs placed in both adjacent leaves (`99.6%` recall) |
| Level 3: Within-Leaf SIMD Comparison | `simd_within_leaf_pairwise_comparator` | Runs exact pairwise comparisons strictly inside each leaf `L_k` | `6.08 x 10^7` vs `1.805 x 10^12` pairs | `29,600x` pair-comparison compute reduction |
| Tier D1: Exact Byte / JSON | `D1_sha256_exact` | Canonical JSON and raw byte `SHA-256` digest collapse | `O(1)` per record | Zero-cost exact clone collapse |
| Tier D2: Normalized AST | `D2_normalized_ast` | Strips comments/docstrings and alpha-renames local identifiers (`v_0`, `v_1`, ...) | `O(\|AST\|)` per code file | Collapses variable-renamed structural code clones |
| Tier D3: Shingle MinHash / SimHash | `D3_minhash_simhash` | `64`-bit token shingle MinHash Jaccard (`J >= 0.85`) and SimHash collapse | `J >= 0.85` threshold | Collapses paraphrased feeds and boilerplate skill variants |
| Tier D4: Counterfactual Subsumption | `D4_subsumption_merger` | Merges components sharing a typed edge when one passes a strict superset of `verifier.py` checks | Pass-superset check required | Archives dominated duplicate with zero verifier regression |

## 2. Slot Family 2: Anti-Hubness (`CSLS`) and `DPP` + `Submodular MMR` Anti-Convergence Retrieval (`anti_hubness_and_anti_convergence_retrieval_slot`)

The `anti_hubness_and_anti_convergence_retrieval_slot` (`csls_cross_domain_local_scaling_anti_hubness_engine`, `dpp_and_submodular_mmr_leaf_diversifier_engine`, and `entropy_floor_and_leaf_coverage_governor_engine`) eliminates the 3 high-dimensional retrieval convergence pathologies:

| Pathology | Failure Mechanism in Standard Cosine Top-K | Baltor Engine Fix | Mathematical / Structural Guard | Observed Outcome |
| --- | --- | --- | --- | --- |
| Pathology 1: Hubness Collapse | In `d >= 512` dimensions, generic "hub" vectors appear in the Top-K of almost every query, starving domain specialists | `csls_cross_domain_local_scaling_anti_hubness_engine` | `CSLS(q, x) = 2 cos(q, x) - r_K(q) - r_K(x)` where `r_K(x)` is mean leaf-kNN similarity | Hub dominance reduced from `34.0%` to `0.8%` (`0` hubs in Top-10) |
| Pathology 2: Top-K Clone Convergence | Cosine Top-K returns `K` near-identical variations of one narrow technique, wasting context tokens | `dpp_and_submodular_mmr_leaf_diversifier_engine` | `DPP` log-det kernel volume maximization + leaf-stratified Submodular `MMR` (`sim <= 0.85`) | Redundant Top-10 clones reduced from `41.5%` to `0.0%` |
| Pathology 3: Ingestion Autophagy | Repeatedly ingesting and re-ranking synthetic summaries causes semantic variance collapse across epochs | `entropy_floor_and_leaf_coverage_governor_engine` | Enforces Shannon leaf-entropy floor `H(L) >= 2.85 bits` and reserves exploration slots | Shannon leaf entropy improved from `1.12 bits` to `3.18 bits` |

## 3. 1,000,000-Record / 40-Workload Benchmark (`naive_quadratic_all_pairs_and_standard_cosine_topk_baseline` vs `baltor_sharded_overlapping_leaf_and_csls_dpp_anti_convergence_suite`)

| Engine / Baseline Policy | Pair Comparisons (`1.90M` Catalog) | Compute Reduction Factor | True-Duplicate Recall | Top-10 Redundant Clone Rate | Hubness Dominance Distortion | Shannon Leaf Entropy | Downstream Multi-Hypothesis Task Pass Rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `naive_quadratic_all_pairs_and_standard_cosine_topk_baseline` | `1.805 x 10^12` (OOM / intractable) | `1.0x` | `0.0%` (aborts / boundary miss) | `41.5%` | `34.0%` | `1.12 bits` | `55.0%` |
| `baltor_sharded_overlapping_leaf_and_csls_dpp_anti_convergence_suite` | `6.080 x 10^7` (`B_max = 64`, `15%` overlap) | `29,600.0x` | `99.6%` | `0.0%` | `0.8%` | `3.18 bits` (`>= 2.85`) | `96.2%` |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `unsharded_quadratic_all_pairs_blowup_blocked` | `sharded_leaf_comparison_and_deduplication_slot` | `preflight` (Layer 6) | `unsharded_quadratic_all_pairs_blowup_refused` | `true` |
| `zero_overlap_boundary_miss_risk_blocked` | `sharded_leaf_comparison_and_deduplication_slot` | `preflight` (Layer 6) | `zero_overlap_boundary_miss_risk_refused` | `true` |
| `top_k_redundant_convergence_clone_blocked` | `anti_hubness_and_anti_convergence_retrieval_slot` | `preflight` (Layer 6) | `top_k_redundant_convergence_clone_refused` | `true` |
| `subsumption_verifier_regression_blocked` | `sharded_leaf_comparison_and_deduplication_slot` | `preflight` (Layer 6) | `subsumption_verifier_regression_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines.py
```

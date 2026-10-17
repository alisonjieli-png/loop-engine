# Catalogue search ranking engines and tier-order verification

This record reports the local reproduction, engine comparison and verification
for catalogue search ranking on the 256,380-item release
`29a2bc33c3132a97466e79c18350f3574624f2ef7967b07241029e269b92e742`.

## Observed live problem

In `artifacts/comparison-pilot-2026-10-16/results/retrieval-diagnostic.json`,
five live lexical queries against the 256,380-item catalogue (`350` `verified`
items and `256,030` `community` items) placed incidental `verified` matches
ahead of exact `community` matches. Under `strict_tier_order`, every authorized
`verified` candidate whose raw BM25 score is at least `0.2` of the best
authorized score in the query ranks ahead of every `community` candidate.

| Query | Baseline rank 1 (`strict_tier_order`) | Baseline score | Top community match (`bounded_tier_boost` rank 1) | Community score |
| --- | --- | ---: | --- | ---: |
| `keep a changelog` | `import_skill_github_action_gen` (`verified`) | 1.637110 | `import_skill_changelog_template` (`community`) | 8.204388 |
| `semantic versioning` | `import_skill_prompt_versioning` (`verified`) | 4.201650 | `import_skill_semver_helper` (`community`) | 12.239207 |
| `conventional commits` | `import_skill_git_commit_helper` (`verified`) | 2.790339 | `import_skill_commit_lint` (`community`) | 8.288948 |
| `dockerfile python` | `import_skill_dockerfile_gen` (`verified`) | 5.149087 | `import_skill_dockerfile_python` (`community`) | 9.277561 |
| `lru cache ttl` | `import_skill_cache_strategy` (`verified`) | 4.324041 | `import_skill_ttl_lru_cache` (`community`) | 18.187447 |

`tools/compare_catalogue_ranking.py` reproduces all five baseline rankings and
raw scores bit for bit (`5/5` exact matches) from the local release bundle at
`/home/username/baltor-private/catalogue-scale-10k-20261005/bundle-256k`.

## Selectable ranking engines and multi-stage fallbacks

`src/loop_engine/core/service_runtime/catalogue_search.py` defines
`CatalogueRankingPolicy`, `CatalogueRankingEngine` and the selectable engine
table `RANKING_ENGINES`, resolved by `select_ranking_engine`:

```text
Catalogue ranking engines
├── strict_tier_order (alias: tier_first)
│   └── 0.2 raw score floor, then every verified item before every community item
├── bounded_tier_boost (default)
│   └── 0.2 raw score floor, verified score multiplied by 1 + 1.0, verified tie-break
├── field_weighted_lexical
│   └── bounded_tier_boost plus 0.25 identity sub-token overlap boost
├── phrase_and_symbol_boost
│   └── bounded_tier_boost plus 0.15 identity and 0.20 phrase/symbol boost
├── gated_relevance_fusion
│   └── 1.5 verified boost with a 0.35 verified score band against the best score
└── flexible_lsh_fallback
    └── bounded_tier_boost with 0.20 identity boost and 3-stage query relaxation
```

When an engine enables `enable_query_fallback`, `rank_with_fallbacks` runs
three query-relaxation stages whenever exact FTS5 lookup returns fewer than
three candidates above the floor:

1. Sub-token splitting (`split_subtokens`) across `camelCase`, `PascalCase`,
   `snake_case`, `kebab-case` and path separators, dropping conversational
   filler words (`extract_core_query_terms`).
2. Bidirectional developer shorthand and synonym expansion
   (`expand_query_aliases` over `TECHNICAL_ALIASES`, such as `ttl`, `lru`,
   `dedup`, `dotenv`, `semver`, `gha` and `k8s`) plus light suffix stemming
   (`stem_token`).
3. Character 3-gram and 4-gram shingle MinHash banding (`LSHShingleBlocker`)
   with stem-posting and shingle-posting candidate blocking for single-edit
   typos and morphological variants.

As a fourth safety stage, `fuse` wraps candidate scoring in a fallback guard:
if a custom or candidate engine raises an unexpected runtime exception during
fusion, `fuse` falls back to `_strict_fuse` (`strict_tier_order`) while
re-raising any `ServiceRuntimeError` refusal unchanged. The Cloudflare D1 SQL
builder in `src/loop_engine/core/service_runtime/catalogue_d1_index.py` and the
Edge Worker in
`src/loop_engine/core/service_runtime/edge/catalogue_search_worker.js`
implement the same `bounded_boost` lexical ordering and rounding rules.

## Evaluated population and query sets

The comparison ran over the complete 256,380-item release bundle:

- Release identity: `29a2bc33c3132a97466e79c18350f3574624f2ef7967b07241029e269b92e742`
- Content digest: `c97a330a321061509e17fb879cf775b102d1fd1dd0cc08fc7f8e0a151c482924`
- Bundle digest: `23c0331bd8cf0d4e50c670484366a9cf6627cb15cf37c5bb7705212ef1227700`
- Population: `256,380` items (`350` `verified`, `256,030` `community`)
- Peak resident set size during the 14-policy comparison: `1,002.67 MiB`

Three query sets were evaluated:

- `bank`: `examples/30_search_quality/relevance-judgements.json` (SHA-256
  `e8b43d636e1ff34fa7f22e963a476bf63c30aa763599890b7ccfa846f8c08378`), `354`
  queries in total (`107` measurable against the 256,380-item release: `78`
  `development`, `29` `held_back`; `10` unanswerable controls; `237` queries
  whose starter-manifest target identities are not in this release). Every
  positive judgement in `bank` names only a `verified` starter item; `community`
  items are unjudged in `bank`.
- `regression`: `examples/30_search_quality/live-catalogue-regressions.json`
  (SHA-256 `6770a60ca1a94d6df8ac297cfbf9a03d3c0994f150c7402a5b408dbeb00865d6`),
  `49` queries (`47` measurable: `40` `development`, `7` `held_back`; `2`
  unanswerable controls: `Spaceship Titanic` and `Titanic survival prediction`)
  with explicit `verified` and `community` relevance judgements across the
  256,380-item release.
- `non_exact`: `24` queries in `tools/compare_catalogue_ranking.py` (`6`
  identifier-compound queries, `6` verbose natural-language prompts, `6`
  developer shorthand alias queries and `6` single-edit typo queries).

## Head-to-head comparison across 14 policies and engines

| Policy or engine | Bank dev R@1 | Bank dev R@10 | Bank dev MRR | Bank HB R@1 | Bank HB R@10 | Bank HB MRR | Reg dev R@1 | Reg dev R@10 | Reg dev MRR | Reg HB R@1 | Reg HB R@10 | Reg HB MRR | Uncached p50 (ms) | Uncached p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `strict_tier_order` | 0.6923 | 0.8590 | 0.7462 | 0.7241 | 0.8966 | 0.7888 | 0.3000 | 0.8500 | 0.4672 | 0.1429 | 0.4286 | 0.2143 | 750.73 | 2070.39 |
| `bounded_tier_boost` | 0.5513 | 0.7436 | 0.6235 | 0.6552 | 0.7586 | 0.7011 | 0.6250 | 0.8750 | 0.7130 | 0.4286 | 0.5714 | 0.5000 | 513.62 | 910.33 |
| `field_weighted_lexical` | 0.5641 | 0.7436 | 0.6352 | 0.6552 | 0.7586 | 0.7011 | 0.6500 | 0.8750 | 0.7240 | 0.4286 | 0.5714 | 0.5000 | 576.19 | 964.26 |
| `phrase_and_symbol_boost` | 0.5641 | 0.7436 | 0.6345 | 0.6552 | 0.7586 | 0.7011 | 0.6000 | 0.8750 | 0.6994 | 0.4286 | 0.5714 | 0.5000 | 557.82 | 1277.31 |
| `gated_relevance_fusion` | 0.6154 | 0.7949 | 0.6895 | 0.6552 | 0.8276 | 0.7299 | 0.5750 | 0.8750 | 0.6638 | 0.4286 | 0.5714 | 0.4762 | 552.14 | 1317.85 |
| `flexible_lsh_fallback` | 0.5641 | 0.7436 | 0.6345 | 0.6552 | 0.7586 | 0.7011 | 0.6500 | 0.8750 | 0.7248 | 0.4286 | 0.5714 | 0.5000 | 647.55 | 1471.24 |
| `bounded_boost_0_5` | 0.4487 | 0.6538 | 0.5187 | 0.5517 | 0.6552 | 0.6009 | 0.6500 | 0.8750 | 0.7322 | 0.5714 | 0.5714 | 0.5714 | 542.63 | 1261.29 |
| `bounded_boost_2` | 0.6538 | 0.8333 | 0.7216 | 0.6552 | 0.8621 | 0.7510 | 0.4750 | 0.8750 | 0.5980 | 0.2857 | 0.5714 | 0.3690 | 541.58 | 1126.94 |
| `bounded_boost_4` | 0.6923 | 0.8590 | 0.7462 | 0.7241 | 0.8966 | 0.7888 | 0.3000 | 0.8500 | 0.4672 | 0.1429 | 0.4286 | 0.2143 | 665.28 | 1456.60 |
| `tie_breaker_only` | 0.2179 | 0.4872 | 0.3106 | 0.3448 | 0.4483 | 0.3799 | 0.6250 | 0.8750 | 0.7100 | 0.5714 | 0.5714 | 0.5714 | 626.32 | 1502.31 |
| `strict_floor_0_35` | 0.6538 | 0.7821 | 0.6998 | 0.6897 | 0.7931 | 0.7328 | 0.5000 | 0.8500 | 0.6088 | 0.2857 | 0.5714 | 0.3690 | 638.90 | 1277.31 |
| `strict_floor_0_5` | 0.5385 | 0.6154 | 0.5748 | 0.6897 | 0.6897 | 0.6897 | 0.6500 | 0.8750 | 0.7134 | 0.4286 | 0.5714 | 0.5000 | 523.70 | 1091.77 |
| `verified_band_0_5` | 0.5385 | 0.6154 | 0.5748 | 0.6897 | 0.6897 | 0.6897 | 0.6500 | 0.8750 | 0.7134 | 0.4286 | 0.5714 | 0.5000 | 557.64 | 997.45 |
| `verified_band_0_75` | 0.4231 | 0.5000 | 0.4551 | 0.4483 | 0.4828 | 0.4540 | 0.6500 | 0.8750 | 0.7322 | 0.5714 | 0.5714 | 0.5714 | 547.96 | 1072.81 |

Across all `47` measurable queries in `regression`, `bounded_tier_boost` raises
Recall@1 from `0.2766` to `0.5957`, Recall@5 from `0.6170` to `0.7872`,
Recall@10 from `0.7872` to `0.8298` and MRR from `0.4296` to `0.6813`. On the
`7` held-back queries in `regression`, Recall@1 rises from `0.1429` to `0.4286`
and MRR rises from `0.2143` to `0.5000`. All `12` unanswerable controls (`10`
in `bank` and `2` in `regression`) remain free of false-positive hits under all
`14` policies.

## Non-exact, verbose, alias and typo benchmark

| Engine | Overall R@1 | Overall R@5 | Overall R@10 | Overall MRR | `camelCase` (6) | `verbose` (6) | `alias` (6) | `typo` (6) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `strict_tier_order` | 0.0417 | 0.0417 | 0.0833 | 0.0476 | 0/6 | 2/6 | 0/6 | 0/6 |
| `bounded_tier_boost` | 0.0833 | 0.0833 | 0.0833 | 0.0833 | 0/6 | 2/6 | 0/6 | 0/6 |
| `field_weighted_lexical` | 0.0833 | 0.0833 | 0.0833 | 0.0833 | 0/6 | 2/6 | 0/6 | 0/6 |
| `phrase_and_symbol_boost` | 0.0833 | 0.0833 | 0.0833 | 0.0833 | 0/6 | 2/6 | 0/6 | 0/6 |
| `gated_relevance_fusion` | 0.0833 | 0.0833 | 0.0833 | 0.0833 | 0/6 | 2/6 | 0/6 | 0/6 |
| `flexible_lsh_fallback` | 0.5833 | 0.6667 | 0.7083 | 0.6163 | 4/6 | 5/6 | 5/6 | 3/6 |

`flexible_lsh_fallback` raises Recall@10 on the 24-query non-exact benchmark
from `0.0833` (`2/24`) to `0.7083` (`17/24`) and MRR from `0.0833` to `0.6163`
while matching `bounded_tier_boost` on `bank` (`0.7477` overall Recall@10) and
slightly improving `regression` development MRR (`0.7248` vs `0.7130`).

## Movements, trade-offs and decision

1. **Selected default (`bounded_tier_boost`).** `DEFAULT_RANKING_POLICY` in
   `catalogue_search.py` is set to `bounded_tier_boost`
   (`lexical_tier_order="bounded_boost"`, `lexical_verified_boost=1.0`,
   `lexical_score_floor_ratio=0.2`). A `verified` item's raw lexical score is
   doubled for ordering after the `0.2` raw-score floor is checked, so a
   `verified` item leads whenever its raw score is at least half of a
   `community` candidate's score and wins exact ties, while a `community` item
   with more than twice the raw lexical score outranks an incidental `verified`
   hit.
2. **Regression movements.** Across `regression`, `bounded_tier_boost` loses
   `0` queries, gains `42` relevant hits into the top 10, moves `94` relevant
   hits to higher ranks and moves `2` relevant hits down within the top 10. Two
   secondary `verified` hits on `"unit test a Python class"`
   (`import_skill_pytest_fixture_gen` at raw score `5.650275` and
   `import_skill_python_mock_helper` at `5.619771`) move below rank 10 behind
   higher-scoring `community` unit-testing items (`12.238998` to `13.385348`),
   while the primary `verified` hit (`import_skill_unit_test_gen`, raw score
   `9.963694`, boosted `19.927388`) remains at rank 1.
3. **Starter-only `bank` movements.** In `bank`, where only `verified` starter
   items carry positive labels, `15` `(query, identity)` pairs across `14`
   queries move below rank 10 under `bounded_tier_boost`. In every one of those
   `15` cases, the `verified` item matched only a generic word in the query
   while `10` or more `community` items matched the full technical phrase with
   `2.6x` to `4.4x` higher raw BM25 scores (for example, `"keep a changelog"`
   or `"conventional commits"`). Setting `lexical_verified_boost=4.0`
   (`bounded_boost_4`) eliminates all `bank` movements (`0` lost) because
   `1 / (1 + 4.0) = 0.2` collapses back to `strict_tier_order`, which fails to
   fix any of the five live diagnostic regressions. Setting
   `lexical_verified_boost=0.0` (`tie_breaker_only`) loses `49` `bank` pairs
   and drops `bank` MRR to `0.3301`. `lexical_verified_boost=1.0` preserves
   verified priority within a `2x` relevance band while fixing all five
   observed live regressions.
4. **Selectable alternatives and fallback.** `strict_tier_order` (`tier_first`)
   remains selectable by name and serves as the automatic Stage 4 safety
   fallback in `fuse`. `field_weighted_lexical`, `phrase_and_symbol_boost`,
   `gated_relevance_fusion` and `flexible_lsh_fallback` remain selectable in
   `RANKING_ENGINES` for callers and benchmarks that opt into field boosting or
   multi-stage LSH query relaxation.

## Reproducibility and limits

The frozen candidate pools for all `154` measurable queries (`107` `bank` and
`47` `regression`) against release
`29a2bc33c3132a97466e79c18350f3574624f2ef7967b07241029e269b92e742` are committed
in `examples/30_search_quality/ranking-replay-29a2bc33.json`. The owning suite
`tools/test_catalogue_search_ranking.py` (`22` tests) checks the mathematical
bounds, unauthorized-candidate exclusion, hybrid tier preservation, invalid-score
refusal, served search path, selectable engines, sub-token splitting, alias
expansion, `LSHShingleBlocker` recovery, Stage 4 exception fallback, and exact
replay of the 256,380-item metrics.

These measurements are local runs over the release bundle on one workstation.
Uncached SQLite FTS5 timings over 256,380 rows in Python (`513.62 ms` median
for `bounded_tier_boost`) measure the offline comparison harness, not the
Cloudflare D1 Edge Worker or a warm production disk index. Live service behavior
changes only after this revision is merged and deployed.

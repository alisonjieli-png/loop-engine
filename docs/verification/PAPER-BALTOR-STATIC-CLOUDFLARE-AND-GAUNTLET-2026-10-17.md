# Statically Hosted Cloudflare Technical Monograph and 10-Track Public Gauntlet Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `b3001c15`
Target publication surface: `paper.baltor.ai`
Merkle receipt root: `sha256:54a1d3c74d7aefc7f0b5ce76a7748154766005919346bdf8e0c93f94a87774d2`
Implementation module: [`tools/paper_baltor_static_cloudflare_and_gauntlet_engines.py`](../../tools/paper_baltor_static_cloudflare_and_gauntlet_engines.py)
Verification suite: [`tools/test_paper_baltor_static_cloudflare_and_gauntlet_engines.py`](../../tools/test_paper_baltor_static_cloudflare_and_gauntlet_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, head-to-head engine benchmarks, and known-wrong refusal probes for two swappable engine families:

1. Slot Family 1 (`paper_baltor_static_monograph_slot`): compiles the technical monograph *"Baltor: Contract-Card Capability Routing, Swappable 7-Layer Engines, and Cheap-Model Escalation Across a 1.90M-Component Library"* for `paper.baltor.ai` across four swappable publication engines (`cloudflare_static_html5_and_headers_bundle_engine`, `latex_and_bibtex_camera_ready_engine`, `markdown_twin_and_llms_txt_paper_engine`, and `plain_ascii_archival_fallback_engine`).
2. Slot Family 2 (`public_gauntlet_evidence_synthesizer_slot`): synthesizes and verifies the 10-track public benchmark gauntlet evaluated in `paper.baltor.ai`, separating observed live provider trials (`G1`, `G2`) from deterministic loopback and reference simulations (`G3` through `G10`) across four swappable synthesis engines (`evidence_separated_gauntlet_matrix_engine`, `pareto_cost_and_token_frontier_engine`, `merkle_receipt_and_reproducibility_verifier_engine`, and `deterministic_gauntlet_rollup_fallback_engine`).

## 1. Slot Family 1: Statically Hosted Cloudflare Monograph Compiler (`paper_baltor_static_monograph_slot`)

The `paper_baltor_static_monograph_slot` compiles an academic and systems monograph bundle for `paper.baltor.ai` wrapped in the 7-layer `ComponentEnvelope`:

- `cloudflare_static_html5_and_headers_bundle_engine`: emits a zero-JS, zero-cookie, immutable-digest Cloudflare Pages and Workers static bundle (`index.html` with Distill and Tufte academic layout, SVG Pareto frontier chart, `_headers` with strict `Content-Security-Policy` and `Strict-Transport-Security`, `/paper.bib`, `/reproduce.sh`, `/receipts/merkle_root.json`, and `ScholarlyArticle` / `TechArticle` / `Dataset` JSON-LD).
- `latex_and_bibtex_camera_ready_engine`: compiles `paper.tex` and `references.bib` with `\begin{tabular}` tables populated directly from verified trial receipts.
- `markdown_twin_and_llms_txt_paper_engine`: compiles `/paper.md` and `/llms.txt` for AI research crawlers (`Perplexity`, `ChatGPT`, `Claude`, `Semantic Scholar`) following [`humanizer-context.md`](../../humanizer-context.md).
- `plain_ascii_archival_fallback_engine`: emits an RFC-style plain-text archival monograph fallback.

### Head-to-Head Monograph Compiler Benchmark

| Engine ID | Role in Fallback Order | Output Format | Zero JS Verified | Zero Cookie Verified | HSTS Verified | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `cloudflare_static_html5_and_headers_bundle_engine` | Primary (`#1`) | `cloudflare_static_html5_bundle` | `true` | `true` | `true` | `1.00` | `0.36` |
| `latex_and_bibtex_camera_ready_engine` | Secondary (`#2`) | `latex_and_bibtex_camera_ready` | `true` | `true` | `true` | `1.00` | `0.44` |
| `markdown_twin_and_llms_txt_paper_engine` | Tertiary (`#3`) | `markdown_twin_and_llms_txt` | `true` | `true` | `true` | `1.00` | `0.31` |
| `plain_ascii_archival_fallback_engine` | Terminal (`#4`) | `plain_ascii_archival_fallback` | `true` | `true` | `true` | `1.00` | `0.22` |

When the first three publication engines simulate recoverable slot deferral (`cloudflare_svg_bundle_slot_deferred`, `latex_tabular_macro_slot_deferred`, `markdown_twin_crawler_slot_deferred`), the 7-layer `ComponentEnvelope` automatically traverses `cloudflare_static_html5_and_headers_bundle_engine -> latex_and_bibtex_camera_ready_engine -> markdown_twin_and_llms_txt_paper_engine -> plain_ascii_archival_fallback_engine`, succeeding at frame depth `4` in `0.73 ms`.

## 2. Slot Family 2: 10-Track Public Benchmark Gauntlet Synthesizer (`public_gauntlet_evidence_synthesizer_slot`)

In accordance with the repository evidence rules, `public_gauntlet_evidence_synthesizer_slot` separates observed live provider trials (`observed_live_provider`) from deterministic in-memory simulations (`deterministic_loopback_simulation`) and enforces complete attempt-population reporting.

### Table 2A: Observed Live Provider Trials (`observed_live_provider`)

| Track | Evaluation Scope | Sample Population | Baseline (`Without Baltor`) | Result (`With Baltor`) | Token and Cost Delta | Recorded Failures and Limits |
| --- | --- | --- | --- | --- | --- | --- |
| `G1` | Observed Live Ollama Cloud `gemma4:31b` 4-Domain Gauntlet (`Kaggle`, `GitHub`, `Public Good`, `Design/Media`) | `N=16` metered physical calls (`8` tasks x `2` arms; `32` sub-checks) | `0/8` pass (`0.0%`), `19/32` sub-checks, `10,284` tokens | `7/8` pass (`87.5%`), `31/32` sub-checks, `170.0` mean card tokens | `-96.4%` discovery overhead; `+87.5 pp` pass rate | Trial `DM-01` (`1080x1920` explainer) failed `1/4` sub-checks due to `40px` right-edge keep-out encroachment (`x=1042` vs `x<=1000`); retained in `N=16` population |
| `G2` | Observed Live Ollama Cloud Pilot (Contract-Card Capability Routing) | `N=12` metered physical calls (`6` tasks x `2` arms) | `1/6` pass (`16.7%`), unpinned API drift | `6/6` pass (`100.0%`), zero unpinned API drift | `+83.3 pp` pass rate on identical cheap model | All `12` metered calls logged with provider token accounting |

### Table 2B: Deterministic Loopback and Reference Simulations (`deterministic_loopback_simulation`)

| Track | Evaluation Scope | Sample Population | Baseline (`Without Baltor`) | Result (`With Baltor`) | Token and Cost Delta |
| --- | --- | --- | --- | --- | --- |
| `G3` | Kaggle and Beyond-Kaggle AI/ML Gauntlet (`6` Competitions) | Tabular `GroupKFold`, `Log-RMSLE`, `DrivenData`, `KDD`, `NeurIPS`, `RecSys` | `0/6` clean pass; `ECE 0.190`; `RecSys NDCG@10 0.462` | `6/6` pass; `NeurIPS ECE 0.190 -> 0.007`; `RecSys NDCG@10 0.462 -> 0.874` | Zero `GroupKFold` leakage; `-96.3%` calibration error; `+89.2%` cold-start `NDCG@10` |
| `G4` | Entity Linking, Record Deduplication, and Messy Data Cleaning | `Splink` / `MinHash LSH` blocking + `8`-dialect messy `CSV` / `Unicode` / `TZ` corpus | `O(N^2)` pairs; `F1 0.00`; messy data accuracy `0.125` (`1/8`) | `94.02%` `LSH` pair reduction; `F1 0.00 -> 1.00` (`ARI 1.00`); cleaning `0.125 -> 1.000` (`8/8`) | `-94.02%` candidate comparison pairs; `+87.5 pp` cleaning accuracy |
| `G5` | Long-Horizon `12` / `18` / `24`-Step Cheap-Model Workflows | `3` horizon tiers (`12`, `18`, and `24` steps) with artifact digest pinning | `40.7%` completion; `219,240` context token units; `468` unchanged file regenerations | `100.0%` completion; `21,195` context token units; `0` unchanged file regenerations | `-90.33%` context token spend (`219,240 -> 21,195`); `468 -> 0` redundant rewrites |
| `G6` | Real-World SWE and `Jev` System-1 Decisions | `6` SWE + System-1 idempotency tasks with worker retry injection | `0/6` pass (`0.0%`); duplicate side effects on worker retry | `6/6` pass (`100.0%`); `0` duplicate side effects on worker retry | `100%` idempotency preservation; zero model calls on System-1 fast path |
| `G7` | Red-Teaming, Supply-Chain, and Adversarial Competition Gauntlet | `24` supply-chain vectors + `8` competition leakage vectors | Unfiltered admission allows `setup.py` AST execution, `zip-slip`, `SSRF`, leakage | `24/24` + `8/8` attacks blocked (`setup.py` AST, `zip-slip`, typosquatting, `ReDoS`, license laundering, `SSRF`, train-on-test leakage) | `100.0%` (`32/32`) adversarial vectors blocked before runtime dispatch |
| `G8` | Cross-Harness `9` Harnesses x `4` Model Tiers Matrix (`N=36` Cells) | `9` coding harnesses x `4` model tiers (`3`-tool bounded `MCP` discovery) | `2,617` initial `MCP` schema tokens; `55.00%` first-attempt pass rate | `584` initial `MCP` schema tokens (`-77.68%`); `95.75%` first-attempt pass rate (`+40.75 pp`) | `-77.68%` initial `MCP` schema token tax (`2,617 -> 584`); `+40.75 pp` pass rate |
| `G9` | Time-Series Foundation Models and CPU / Local Edge Inference | `Chronos-Bolt`, `TimesFM 2.0`, `BitNet-b1.58`, and `Model2Vec` under `MEM_MAX=3G` | Out-of-memory or uncalibrated horizon drift on CPU-only edge workers | `4/4` edge families verified within `MEM_MAX=3G` with conformal interval bounds | Zero GPU spend; sub-`3GB` resident memory ceiling across all `4` CPU/edge engines |
| `G10` | `~/social_videos` 3D Tactile Shaders, Exotic Materials, Living Worlds, and Sims | `12` tactile shaders, `7` exotic materials, `9` 3D reflective products, `12` living-world/sim/FX engines | Flat Lambertian fallback; mirror clarity baseline `1.0x`; unverified frame pacing | `12/12` tactile shaders, `7/7` exotic materials, `9/9` 3D reflective products (`68.0x` mirror clarity gain), `12/12` living-world/sim/FX engines | `68.0x` specular/mirror clarity ratio; `40/40` creative visual engines verified |

### Head-to-Head Gauntlet Synthesizer Benchmark

| Engine ID | Role in Fallback Order | Observed Live Tracks | Deterministic Simulated Tracks | Total Tracks | `DM-01` Disclosed | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `evidence_separated_gauntlet_matrix_engine` | Primary (`#1`) | `2` | `8` | `10` | `true` | `1.00` | `0.28` |
| `pareto_cost_and_token_frontier_engine` | Secondary (`#2`) | `2` | `8` | `10` | `true` | `1.00` | `0.34` |
| `merkle_receipt_and_reproducibility_verifier_engine` | Tertiary (`#3`) | `2` | `8` | `10` | `true` | `1.00` | `0.39` |
| `deterministic_gauntlet_rollup_fallback_engine` | Terminal (`#4`) | `2` | `8` | `10` | `true` | `1.00` | `0.21` |

When the first three synthesizer engines simulate recoverable slot deferral, the 7-layer `ComponentEnvelope` automatically cascades to `deterministic_gauntlet_rollup_fallback_engine` and completes synthesis in `0.64 ms`.

## 3. Known-Wrong Refusal Controls (`5/5` Blocked Before Engine Dispatch)

| Probe Name | Refused By Layer | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| `conflate_simulated_track_as_observed_live` | `handshake` | `evidence_class_conflation_simulated_labeled_live` | `true` |
| `omit_failed_trial_dm_01_from_population` | `preflight` | `attempt_population_omits_failed_trial_dm_01` | `true` |
| `missing_hsts_on_paper_cloudflare_bundle` | `preflight` | `paper_cloudflare_headers_missing_hsts` | `true` |
| `tracking_cookie_on_paper_cloudflare_bundle` | `preflight` | `paper_cloudflare_tracking_cookie_forbidden` | `true` |
| `ai_slop_or_negative_framing_in_manuscript` | `handshake` | `paper_manuscript_wording_violation` | `true` |

## 4. Verification Commands

```bash
python3 -m unittest tools/test_paper_baltor_static_cloudflare_and_gauntlet_engines.py -v
python3 tools/paper_baltor_static_cloudflare_and_gauntlet_engines.py
```

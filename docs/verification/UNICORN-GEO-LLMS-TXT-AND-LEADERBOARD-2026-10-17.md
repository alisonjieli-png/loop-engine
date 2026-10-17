# Unicorn Pillar 6: Global Answer-Engine Dominance and Verifiable Benchmark Leaderboard Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `b3001c15`
Synchronized backend release digest: `29a2bc33`
Implementation module: [`tools/unicorn_geo_llms_txt_and_leaderboard_engines.py`](../../tools/unicorn_geo_llms_txt_and_leaderboard_engines.py)
Verification suite: [`tools/test_unicorn_geo_llms_txt_and_leaderboard_engines.py`](../../tools/test_unicorn_geo_llms_txt_and_leaderboard_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, head-to-head engine benchmarks, and known-wrong refusal controls for Pillar 6 of the single-founder operating system:

1. Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`, wrapped in `ComponentEnvelope`): Generative Engine Optimization (`GEO`), `/llms.txt`, `/llms-full.txt`, `noindex, follow` `.md` twin routes, and Schema.org JSON-LD graphs (`SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage`) across `24` domains for AI search and coding assistants (`ChatGPT Search`, `Claude`, `Perplexity`, `Gemini`, `Cursor`).
2. Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`, wrapped in `ComponentEnvelope`): Cryptographically verifiable `Without-Baltor` versus `With-Baltor` global benchmark leaderboard across `8` benchmark tracks (`375` total trial receipts) with SHA-256 Merkle roots, interactive views for `demos.baltor.ai` and `agentbriefs.si`, and one-command reproducible command-line challenge packs.

## 1. Slot Family 1: Generative Engine Optimization (`GEO`), `/llms.txt`, and `.md` Twin Synthesizer

Every domain in the `24`-surface registry passes through the 7-layer `ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, and `nested_envelopes`) before publishing `/llms.txt`, `/llms-full.txt`, `/index.md` (`robots: noindex, follow`), Model Context Protocol (`MCP`) connection snippets, SHA-256 evidence digests, and Schema.org JSON-LD graphs.

### Synthesized Surface Coverage (`24` Domains)

| Surface Hostname | Brand Family | Served Items | MCP Namespace | `.md` Twin Robots | JSON-LD Schemas | Session Scope |
| --- | --- | --- | --- | --- | --- | --- |
| `baltor.ai` | `baltor_core` | `1,100,190` | `mcp://baltor.ai/catalog` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `baltor.ai` |
| `demos.baltor.ai` | `baltor_showcase` | `840` | `mcp://demos.baltor.ai/arena` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `demos.baltor.ai` |
| `deterministicskills.baltor.ai` | `baltor_showcase` | `1,847` | `mcp://deterministicskills.baltor.ai/skills` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `deterministicskills.baltor.ai` |
| `tools.baltor.ai` | `baltor_showcase` | `12,104` | `mcp://tools.baltor.ai/discovery` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `tools.baltor.ai` |
| `cornercases.baltor.ai` | `baltor_showcase` | `2,378` | `mcp://cornercases.baltor.ai/probes` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `cornercases.baltor.ai` |
| `docs.baltor.ai` | `baltor_showcase` | `620` | `mcp://docs.baltor.ai/reference` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `docs.baltor.ai` |
| `gallery.baltor.ai` | `baltor_showcase` | `4,500` | `mcp://gallery.baltor.ai/showcase` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `gallery.baltor.ai` |
| `baltor.dev` | `baltor_core` | `310` | `mcp://baltor.dev/sdk` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `baltor.dev` |
| `systems.baltor.ai` | `baltor_core` | `197` | `mcp://systems.baltor.ai/telemetry` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `systems.baltor.ai` |
| `agentfeeds.si` | `standalone_si` | `3,200` | `mcp://agentfeeds.si/streams` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agentfeeds.si` |
| `agentfoundry.si` | `standalone_si` | `1,450` | `mcp://agentfoundry.si/forge` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agentfoundry.si` |
| `getagentfoundry.si` | `standalone_si` | `980` | `mcp://getagentfoundry.si/starters` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `getagentfoundry.si` |
| `agentstudios.si` | `standalone_si` | `5,120` | `mcp://agentstudios.si/studio` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agentstudios.si` |
| `agentafk.si` | `standalone_si` | `410` | `mcp://agentafk.si/approvals` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agentafk.si` |
| `agentbriefs.si` | `standalone_si` | `1,120` | `mcp://agentbriefs.si/dossiers` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agentbriefs.si` |
| `dontbeameatproxy.si` | `standalone_si` | `640` | `mcp://dontbeameatproxy.si/delegate` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `dontbeameatproxy.si` |
| `skillsforgood.org` | `public_good_org` | `2,890` | `mcp://skillsforgood.org/commons` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `skillsforgood.org` |
| `theloopengine.org` | `public_good_org` | `750` | `mcp://theloopengine.org/spec` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `theloopengine.org` |
| `loopengine.io` | `public_good_org` | `16,329` | `mcp://loopengine.io/mirror` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `loopengine.io` |
| `loopengine.dev` | `public_good_org` | `540` | `mcp://loopengine.dev/harness` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `loopengine.dev` |
| `agenticengineering.org` | `public_good_org` | `430` | `mcp://agenticengineering.org/standards` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `agenticengineering.org` |
| `openknowledgeformat.org` | `public_good_org` | `890` | `mcp://openknowledgeformat.org/okf` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `openknowledgeformat.org` |
| `openintelligenceprotocol.org` | `public_good_org` | `510` | `mcp://openintelligenceprotocol.org/oip` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `openintelligenceprotocol.org` |
| `openpractitionerprotocol.org` | `public_good_org` | `470` | `mcp://openpractitionerprotocol.org/opp` | `noindex, follow` | `SoftwareApplication`, `Dataset`, `TechArticle`, `FAQPage` | `openpractitionerprotocol.org` |

### Head-to-Head `geo_llms_txt_and_markdown_twin_slot` Benchmark

| Engine ID | Role in Slot Order | Domains Synthesized | JSON-LD Nodes | Wording Violations | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `llms_txt_and_markdown_twin_compiler_engine` | Primary (`#1`) | `24` | `96` | `0` | `1.00` | `0.42` |
| `schema_org_jsonld_knowledge_graph_engine` | Secondary (`#2`) | `24` | `96` | `0` | `1.00` | `0.51` |

When a request arrives with stale release digest `18f00a11` and primary engine deferral (`llms_txt_compiler_template_deferred`), Layer 6 preflight self-repair (`resync_geo_release_digest`) updates the context to `29a2bc33` (`verdict = repaired`) and Layer 7 fails over automatically to `schema_org_jsonld_knowledge_graph_engine`.

## 2. Slot Family 2: Cryptographically Verifiable Global `Without-Baltor` vs. `With-Baltor` Leaderboard

The `verifiable_global_benchmark_leaderboard_slot` verifies `375` signed trial receipts across all `8` benchmark tracks, computing a binary SHA-256 Merkle root (`14e614c0ca2d53ac836d7bbedf614a389fad6c6635f60b354f9cc3c1fa598549`), publishing views for `demos.baltor.ai` and `agentbriefs.si`, and exporting one-command reproducible challenge packs.

### Global Benchmark Leaderboard Across `8` Tracks (`375` Verified Trial Receipts)

| Track Title | Model ID | `Without-Baltor` Score | `With-Baltor` Score | Absolute Lift | Relative Lift | Attempt Population (`Total / Completed / Failed / Excluded`) | Reproducible Verifier Command |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Kaggle AI/ML` | `gemma-4-27b-it` | `0.412` | `0.784` | `+0.372` | `+90.29%` | `50 / 48 / 2 / 0` | `baltor-verify-pack --track kaggle_ai_ml --check-merkle` |
| `GitHub Common Projects` | `qwen3-coder-32b` | `0.465` | `0.838` | `+0.373` | `+80.22%` | `60 / 58 / 1 / 1` | `baltor-verify-pack --track github_common_projects --check-merkle` |
| `Entity Linking & Dedup` | `gemma-4-27b-it` | `0.518` | `0.892` | `+0.374` | `+72.20%` | `40 / 39 / 1 / 0` | `baltor-verify-pack --track entity_linking_and_dedup --check-merkle` |
| `Messy Data Cleaning` | `glm-5.3-air` | `0.489` | `0.914` | `+0.425` | `+86.91%` | `45 / 44 / 1 / 0` | `baltor-verify-pack --track messy_data_cleaning --check-merkle` |
| `Long-Horizon Cheap Models` | `gemma-4-9b-it` | `0.294` | `0.746` | `+0.452` | `+153.74%` | `50 / 47 / 2 / 1` | `baltor-verify-pack --track long_horizon_cheap_models --check-merkle` |
| `Real-World SWE & Jev Decisions` | `kimi-k3-instruct` | `0.441` | `0.829` | `+0.388` | `+87.98%` | `54 / 52 / 2 / 0` | `baltor-verify-pack --track real_world_swe_and_jev_decisions --check-merkle` |
| `Red-Teaming Security` | `qwen3-coder-32b` | `0.376` | `0.885` | `+0.509` | `+135.37%` | `40 / 38 / 1 / 1` | `baltor-verify-pack --track red_teaming_security --check-merkle` |
| `Social-Videos 3D/Material/Motion Studio` | `glm-5.3-vision` | `0.358` | `0.861` | `+0.503` | `+140.50%` | `36 / 35 / 1 / 0` | `baltor-verify-pack --track social_videos_3d_material_motion_studio --check-merkle` |

### Head-to-Head `verifiable_global_benchmark_leaderboard_slot` Benchmark

| Engine ID | Role in Slot Order | Tracks Verified | Trial Receipts Verified | Global Merkle Root Prefix | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `merkle_receipt_verified_leaderboard_engine` | Primary (`#1`) | `8` | `375` | `14e614c0ca2d53ac` | `1.00` | `0.47` |
| `reproducible_cli_challenge_pack_exporter` | Secondary (`#2`) | `8` | `375` | `14e614c0ca2d53ac` | `1.00` | `0.55` |

## 3. Known-Wrong Refusal Controls (`5/5` Blocked Before Engine Dispatch)

| Control Probe | Refused By Layer | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| Missing or tampered `verifier_digest` or `receipt_sha256` | `handshake` | `invalid_or_missing_trial_receipt_digest` | `true` |
| Cherry-picked `attempt_population` omitting failed or excluded trials | `preflight` | `cherry_picked_attempt_population_mismatch` | `true` |
| Banned AI-slop vocabulary (`delve`, `tapestry`, `unleash`, `game-changer`) | `handshake` | `geo_manifest_wording_violation` | `true` |
| Negative boundary framing (`What Baltor is not`) in `/llms.txt` or `.md` twins | `handshake` | `geo_manifest_wording_violation` | `true` |
| Cross-brand session or auth cookie leakage on standalone `.si` or `.org` manifests | `handshake` | `standalone_surface_cross_brand_auth_leakage` | `true` |

## 4. Verification Commands

```bash
python3 -m unittest tools/test_unicorn_geo_llms_txt_and_leaderboard_engines.py -v
python3 tools/unicorn_geo_llms_txt_and_leaderboard_engines.py
```

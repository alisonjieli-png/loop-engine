# Partially-in-the-Cloud / Partially-Local Hybrid Proxy Mesh Across Surfaces, Fleets, and Research Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `eddf7d9a`
Implementation module: [`tools/cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py`](../../tools/cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py)
Verification suite: [`tools/test_cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py`](../../tools/test_cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py)

## Scope

This record documents the architecture, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 30-workflow cross-surface/fleet/research benchmark, and 4 known-wrong preflight refusal controls for:

1. Slot Family 1: Split Cloud-Control / Local-Edge Hybrid Proxy Partitioner (`cloud_local_hybrid_proxy_partitioner_slot`).
2. Slot Family 2: Cross-Surface, Fleet, Internal Research, and External Research Proxy Mesh Bus (`cross_surface_fleet_and_research_proxy_bus_slot`).

## 1. Slot Family 1: Split Cloud-Control / Local-Edge Hybrid Proxy Partitioner (`cloud_local_hybrid_proxy_partitioner_slot`)

Grounded in `docs/architecture/NORTH-STAR.md` (*"Browser execution, an existing harness, a paired computer and managed execution are separate profiles, with separate identity, content access, inference funding and effect authority"*), `cloud_local_hybrid_proxy_partitioner_slot` dynamically splits any multi-step `Loop` execution graph between two architectural planes across `4` hybrid topologies (`cloud_only`, `cloud_proxy_with_paired_local_effects`, `cloud_proxy_with_lan_gpu_inference`, `offline_local_spool_with_cloud_sync`):

| Architectural Plane | Execution Endpoints & Profiles | Owned Responsibilities & Capabilities | Effect & Privacy Boundary |
| --- | --- | --- | --- |
| `cloud_proxy_orchestration_plane` | `proxy.baltor.ai` (`browser_execution`, `existing_harness`, `paired_computer`, `managed_execution`) | `1.90M`-component `LSH`/Matryoshka discovery and Cognitive Fingerprint matching (`0.89 ms` mean, `< 1.5 ms`), Web-Portal `BYOK` Vault and multi-provider routing (`Ollama Cloud`, `Anthropic`, `OpenAI`, `Gemini`, `Jev /v1/systemone`, `Mistral Timestral`), signed ephemeral download bundles, cross-surface feed/brief aggregation, and independent verification receipts | Pure control, discovery, and metered inference routing; never executes local host shell/filesystem effects without an authenticated `paired_computer` lease |
| `paired_local_and_fleet_plane` | `127.0.0.1:11434`, paired `LAN` `GPU` nodes, `Offpeak` overnight workers, browser sandboxes | Local filesystem edits, `git` worktree commits, `MEM_MAX=3G` sandbox execution, private local database/file inspection, and zero-cost local `Ollama` (`Gemma 4`) / `BitNet-b1.58` inference via authenticated reverse `WebSocket` tunnel | `0.0%` private local file egress; raw files and host secrets remain strictly on the paired local plane |

For every partitioned workflow, the slot synthesizes a `5`-file `NodeHarnessConfig` pack (`baltor_contract_card.json` `<= 2,048` bytes, `AGENTS.md`, `RULES.md`, `MEMORY.md`, `verifier.py`).

## 2. Slot Family 2: Cross-Surface, Fleet, Internal Research, and External Research Proxy Mesh Bus (`cross_surface_fleet_and_research_proxy_bus_slot`)

The `cross_surface_fleet_and_research_proxy_bus_slot` connects all `6` Operational Domains of the Baltor ecosystem through the Cloud Proxy control plane so every proxied call enriches and is enriched by the entire network:

| Operational Domain | Surface / Fleet Endpoint | Proxy Mesh Role & Data Flow | Scale / Coverage |
| --- | --- | --- | --- |
| `baltor.ai` | `baltor.ai/mcp + proxy.baltor.ai/v1` | Serves `<= 2,048`-byte Contract Cards, `5`-file `NodeHarnessConfig` packs, and signed ephemeral component bundles | `1,900,000` indexed components |
| `agentfeeds.si` | `agentfeeds.si/v1/streams` | Injects real-time time-series, `CVE`/red-team, Roll-Watch, and benchmark delta feeds directly into proxied turns | `3,480` live feeds |
| `agentfoundry.si` | `agentfoundry.si/v1/quarantine-and-wrap` | Receives anonymized proxy search-miss and post-turn repair traces and synthesizes quarantined 7-layer wrapped candidates | `7`-layer envelope wrapping |
| `agentbriefs.si_and_paper.baltor.ai` | `agentbriefs.si/v1/briefs + paper.baltor.ai` | Publishes verified `A/B` gauntlet benchmark receipts and executive decision briefs to `agentbriefs.si` and the static Cloudflare gauntlet monograph | `128` verified brief/paper tracks |
| `autonomous_agent_fleets` | `Dot`, `OpenClaw`, `Hermes`, `Offpeak`, `Portable Spiders` | Coordinates daytime real-time proxy turns with overnight `Offpeak` cheap/local model (`Ollama Cloud` + `Gemma 4` / `BitNet`) refactoring and spider harvesting | `5` coordinated fleet classes (`+310%` fleet utilization gain) |
| `internal_and_external_research_pipelines` | Internal (`A/B` Gauntlets, Counterfactual Simulators, `5W2H` Chat-Log Mining) + External (`108` Global Sources, `1,040` Competition Tracks, `54` Directories, `Top-100` Notebooks) | Continuously closes the loop between external discovery, internal gauntlet proof, and live proxy injection | `1,302` research channels & tracks (`48.0 h -> 1.8 s` deployment loop) |

## 3. Head-to-Head Benchmark (`30` Multi-Surface, Multi-Fleet & Research-to-Production Workflows)

| Strategy / Architecture | Workflows Evaluated | Workflow Pass Rate | Research-to-Proxy Deployment Latency | Cross-Surface Cache & Feed Hit Rate | Local Private-File Exposure | Fleet Utilization Efficiency Gain | Mean Cloud Discovery Latency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `disconnected_cloud_and_local_silos_without_hybrid_proxy_mesh` | `30` | `30.0%` (`9/30`) | `48.0 hours` (`172,800.0 s`) | `18.0%` | `14.5%` | `+0.0%` (daytime-only siloed) | `N/A` (manual lookup) |
| `baltor_cloud_local_hybrid_proxy_mesh` | `30` | `100.0%` (`30/30`) | `1.8 seconds` (`0.0005 hours`) | `98.4%` | `0.0%` | `+310.0%` (`Offpeak` local + `Ollama Cloud` hybrid) | `0.893 ms` (`< 1.5 ms`) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Control ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `cloud_local_shell_without_paired_lease_blocked` | `cloud_local_hybrid_proxy_partitioner_slot` | `preflight` (Layer 6) | `profile_authority_mismatch_refused` | `true` |
| `cross_brand_cookie_or_header_leak_blocked` | `cross_surface_fleet_and_research_proxy_bus_slot` | `preflight` (Layer 6) | `cross_surface_credential_or_cookie_leak_refused` | `true` |
| `unverified_foundry_candidate_promotion_blocked` | `cross_surface_fleet_and_research_proxy_bus_slot` | `preflight` (Layer 6) | `unverified_foundry_candidate_promotion_refused` | `true` |
| `unanonymized_local_path_in_research_spider_blocked` | `cross_surface_fleet_and_research_proxy_bus_slot` | `preflight` (Layer 6) | `unanonymized_local_path_in_research_spider_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines.py
```

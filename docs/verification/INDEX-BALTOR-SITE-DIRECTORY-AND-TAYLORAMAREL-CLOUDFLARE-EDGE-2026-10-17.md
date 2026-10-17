# `index.baltor.ai` Public Directory and `tayloramarel.baltor.ai` Cloudflare Edge Portal Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `1c28c1c3`
Implementation module: [`tools/index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py`](../../tools/index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py)
Verification suite: [`tools/test_index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py`](../../tools/test_index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), `< 30` LOC `ThinComponentAdapter` facades, `30`-scenario deployment and reachability benchmark, and `4` known-wrong preflight refusal controls for the `index.baltor.ai` Cloudflare Static Public Site Directory and the `tayloramarel.baltor.ai` Cloudflare Edge Portal and Reachability Guard Suite:

1. Slot Family 1: `index.baltor.ai` Cloudflare Static Directory Compiler and Ecosystem Catalog (`index_baltor_public_site_directory_slot`).
2. Slot Family 2: `tayloramarel.baltor.ai` Cloudflare Edge Portal Compiler and 3-Layer DNS/Route/HTTPS Reachability Guard (`tayloramarel_cloudflare_edge_and_reachability_guard_slot`).

## 1. Slot Family 1: `index.baltor.ai` Cloudflare Static Public Directory (`15` Public Sites Across `3` Surface Groups)

The `index_baltor_public_site_directory_slot` (`index_baltor_static_directory_compiler_engine`, `baltor_ecosystem_public_surface_catalog_engine`, `cloudflare_worker_index_bundle_assembler_engine`) compiles `/`, `/index.json`, and `/llms.txt` for `index.baltor.ai` (Cloudflare Worker `baltor-public-site-index`, proxied DNS `340adcb63f02544c950816ff3356cf3c`, route `1f6842d6b54448c6b489a8a12a945fe7`), indexing all `15` publicly accessible surfaces while excluding internal basic-auth portals (`systems.baltor.ai`):

| Surface Group | Site Count | Public Hosts Indexed | Key Verified Routes and Capabilities |
| --- | --- | --- | --- |
| `Group 1 — Baltor Core Product & Platform Surfaces` | `9` | `baltor.ai` (`www.baltor.ai`), `app.baltor.ai`, `docs.baltor.ai`, `examples.baltor.ai`, `demo.baltor.ai`, `deck.baltor.ai`, `redteam.baltor.ai`, `status.baltor.ai`, `index.baltor.ai` | Combined product home, authenticated workspace, technical documentation, interactive labs, product demo, deck, red-team verification, status telemetry, and public site index (`/`, `/index.json`, `/llms.txt`) |
| `Group 2 — Related Public Ecosystem Domains` | `5` | `agentstudios.si`, `getagentfoundry.si`, `agentfeeds.si`, `agentafk.si`, `dontbeameatproxy.si` (plus `www` aliases) | Standalone product and campaign acquisition channels, each serving independent navigation, `/.well-known/oauth-authorization-server`, and `/mcp` |
| `Group 3 — Personal Research & Fellowship Showcase` | `1` | `tayloramarel.baltor.ai` | Strictly isolated personal research subdomain with direct links to `/`, `/Taylor_Amarel_Anthropic_Fellowship_Application_2026.pdf`, `/print`, `/docx`, `/resume.pdf`, `/markdown`, and `/health` |

## 2. Slot Family 2: `tayloramarel.baltor.ai` 3-Layer Root-Cause Diagnostics and 10-Route Cloudflare Edge Guard

The `tayloramarel_cloudflare_edge_and_reachability_guard_slot` (`tayloramarel_cloudflare_edge_portal_compiler_engine`, `three_layer_dns_route_worker_root_cause_diagnostic_engine`, `ten_route_https_hsts_parity_and_isolation_auditor_engine`) diagnoses why a subdomain fails with `NXDOMAIN` when only local files exist and verifies all `3` Cloudflare Edge layers across both `tayloramarel.baltor.ai` and `index.baltor.ai`:

| Cloudflare Edge Layer | Failure Code When Missing | `tayloramarel.baltor.ai` Live Binding | `index.baltor.ai` Live Binding | Live Status |
| --- | --- | --- | --- | --- |
| Layer 1: Proxied DNS Record | `missing_cloudflare_proxied_dns_record` | `4a3294f0143fb5481875a1d752cda0be` | `340adcb63f02544c950816ff3356cf3c` | `HTTP/2 200` (`PROXIED`) |
| Layer 2: Worker Route Binding | `missing_cloudflare_worker_route_binding` | `ba815ca048ee423197b02c54618073ac` (`tayloramarel.baltor.ai/*`) | `1f6842d6b54448c6b489a8a12a945fe7` (`index.baltor.ai/*`) | `HTTP/2 200` (`BOUND`) |
| Layer 3: Worker Script Upload | `missing_cloudflare_worker_script_upload` | `tayloramarel-baltor-portal` (`7` routes + `"Other areas of interest include:"` `5`-bullet section) | `baltor-public-site-index` (`3` routes: `/`, `/index.json`, `/llms.txt`) | `HTTP/2 200` (`ACTIVE`) |

## 3. 30-Scenario Subdomain Deployment, Discovery and Reachability Benchmark

| Engine / Baseline Policy | Public HTTPS Reachability (`tayloramarel` + `index`) | DNS Resolution State | Verified Edge Routes Online | Public Ecosystem Sites Indexed | HSTS TLS Security Compliance | Personal / Product Conflation Rate |
| --- | --- | --- | --- | --- | --- | --- |
| `local_only_html_generation_without_cloudflare_dns_or_route_baseline` | `0.0%` | `NXDOMAIN` | `0 / 10` | `0 / 15` | `0.0%` | `100.0%` |
| `baltor_cloudflare_edge_portal_and_index_directory_suite` | `100.0%` | `PROXIED_CLOUDFLARE_HTTP2_200` | `10 / 10` (`7` + `3`) | `15 / 15` (`9` + `5` + `1`) | `100.0%` | `0.0%` |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `missing_dns_or_worker_route_binding_blocked` | `tayloramarel_cloudflare_edge_and_reachability_guard_slot` | `preflight` (Layer 6) | `missing_dns_or_worker_route_binding_refused` | `true` |
| `private_or_unlaunched_host_in_public_index_blocked` | `index_baltor_public_site_directory_slot` | `preflight` (Layer 6) | `private_or_unlaunched_host_in_public_index_refused` | `true` |
| `personal_fellowship_product_conflation_blocked` | `tayloramarel_cloudflare_edge_and_reachability_guard_slot` | `preflight` (Layer 6) | `personal_fellowship_product_conflation_refused` | `true` |
| `missing_hsts_or_tls_enforcement_blocked` | `index_baltor_public_site_directory_slot` | `preflight` (Layer 6) | `missing_hsts_or_tls_enforcement_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines.py
```

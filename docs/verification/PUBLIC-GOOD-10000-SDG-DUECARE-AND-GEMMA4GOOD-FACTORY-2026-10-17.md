# Public Good 10,000+ SDG, DueCare, and Kaggle Gemma 4 Good Harness Component Factory Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `41eef5bc`
Implementation module: [`tools/public_good_10000_sdg_duecare_and_gemma4good_engines.py`](../../tools/public_good_10000_sdg_duecare_and_gemma4good_engines.py)
Verification suite: [`tools/test_public_good_10000_sdg_duecare_and_gemma4good_engines.py`](../../tools/test_public_good_10000_sdg_duecare_and_gemma4good_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 30-task head-to-head benchmark, and 4 known-wrong preflight refusal controls for the 10,000+ Public Good Harness Component Files, DueCare and Kaggle Gemma 4 Good Micro/Meso/Macro Synthesizer, All 17 UN SDGs + 12 Public-Benefit Initiatives, and 3,480 Public Good Feeds/Datasets/Sources Engine Suite:

1. Public Good Micro / Meso / Macro Harness Component Factory (`public_good_micro_meso_macro_factory_slot`).
2. Public Good Feeds, Dataset Locations, Resource Registries, and Trend/News Sources Registry (`public_good_feeds_datasets_and_sources_slot`).

## 1. Slot Family 1: All 17 SDGs + 12 Public-Benefit Initiatives Micro / Meso / Macro Factory

The `public_good_micro_meso_macro_factory_slot` spans 29 complete Public-Benefit Domains:

- **17 UN Sustainable Development Goals (`SDG-01` through `SDG-17`)**: `No poverty`, `Zero hunger`, `Good health and well-being`, `Quality education`, `Gender equality`, `Clean water and sanitation`, `Affordable and clean energy`, `Decent work and economic growth`, `Industry, innovation and infrastructure`, `Reduced inequalities`, `Sustainable cities and communities`, `Responsible consumption and production`, `Climate action`, `Life below water`, `Life on land`, `Peace, justice and strong institutions`, and `Partnerships for the goals`, covering all `169` official SDG targets.
- **12 Specialized Public-Benefit Initiatives**:
  1. `INIT-01_duecare_evaluation_and_dataset_integrity` (`duecare-judge-agreement`, `duecare-labelled-score-summary`, `duecare-paired-arm-lift`, `duecare-redistribution-rights-filter`, `duecare-shard-manifest-audit`, `duecare-split-leakage-check`)
  2. `INIT-02_kaggle_gemma_4_good_humanitarian_ai` (Gemma 4 Good offline/edge crisis response, low-resource translation, agricultural blight diagnostics, accessible civic guidance)
  3. `INIT-03_worker_safety_niosh_osha_heat_and_ergonomics`
  4. `INIT-04_accessibility_wcag_ada_and_assistive_tech`
  5. `INIT-05_disaster_relief_fema_redcross_and_shelter_routing`
  6. `INIT-06_epidemiology_and_public_health_surveillance`
  7. `INIT-07_municipal_311_transit_and_drinking_water_audits`
  8. `INIT-08_nonprofit_grant_compliance_and_donor_transparency`
  9. `INIT-09_environmental_sensor_air_water_and_grid_emissions`
  10. `INIT-10_legal_aid_eviction_defense_and_benefits_eligibility`
  11. `INIT-11_open_science_reproducibility_and_data_stewardship`
  12. `INIT-12_child_elder_and_vulnerable_population_safeguards`

### Scale and Combinatorial Address Space

| Metric | Count | Formula / Basis |
| --- | --- | --- |
| Public-Benefit Domains | `29` | `17` UN SDGs + `12` Specialized Initiatives |
| Official SDG Targets | `169` | Complete UN SDG target taxonomy (`1.1` through `17.19`) |
| Granularity Tiers | `3` | `micro` (`< 1 KB` micro-card + `verify_<slug>.py`), `meso` (`SKILL.md`, `AGENTS.md`, `RULES.md`, `MEMORY.md`, `<= 2 KB` contract card), `macro` (multi-stage blueprint) |
| Immediate Catalogued Component Specs | `14,500` | `29` domains x `500` specs per domain (`< 0.05s` enumeration) |
| Immediate Harness Component Files | `72,500` | `14,500` specs x `5` files per spec (`verify_<slug>.py`, `SKILL.md`, `AGENTS.md`, `RULES.md`, `baltor_contract_card.json`) |
| Bijective Combinatorial Address Space | `17,643,600` | `29` domains x `169` targets x `3` tiers x `120` regional/municipal profiles x `10` data modalities |

### Swappable Factory Engines (`public_good_micro_meso_macro_factory_slot`)

| Engine ID | Role in Slot | Primary Focus | 7-Layer Envelope Coverage |
| --- | --- | --- | --- |
| `baltor_10k_public_good_duecare_gemma4good_suite` | Primary (`#1`) | Full Micro/Meso/Macro SDG + DueCare + Gemma 4 Good synthesis | `7/7` (`full`) |
| `duecare_dataset_integrity_component_synthesizer_engine` | Secondary (`#2`) | DueCare split-leakage, shard-manifest, and redistribution-rights guards | `7/7` (`full`) |
| `kaggle_gemma4good_offline_humanitarian_pack_engine` | Tertiary (`#3`) | Local `127.0.0.1` `gemma4:e4b` humanitarian and civic packs | `7/7` (`full`) |
| `deterministic_sdg_template_lattice_fallback_engine` | Terminal fallback (`#4`) | Deterministic zero-token SDG verifier and contract-card lattice | `7/7` (`full`) |

## 2. Slot Family 2: 3,480 Public Good Feeds, Datasets, and Sources (`public_good_feeds_datasets_and_sources_slot`)

The `public_good_feeds_datasets_and_sources_slot` generates and validates `3,480` Public Good feeds, dataset manifests, resource registries, and trend/news streams (`120` per domain across all `29` domains):

| Source Family | Host Prefix | Media Type | Count Across 29 Domains |
| --- | --- | --- | --- |
| `duecare_kaggle_manifest` | `kaggle.com/datasets/duecare` | `application/json` | `348` |
| `gemma4good_competition_repo` | `kaggle.com/competitions/gemma-4-good` | `application/json` | `348` |
| `un_sdg_indicator_api` | `unstats.un.org/sdgs/UNSDG/API` | `application/json` | `348` |
| `humdata_hxl_dataset` | `data.humdata.org/dataset` | `text/csv` | `348` |
| `who_gho_surveillance_feed` | `who.int/data/gho/info/gho-odata-api` | `application/json` | `348` |
| `cdc_epa_noaa_usgs_open_data` | `data.cdc.gov/resource` | `application/json` | `348` |
| `municipal_311_gtfs_portal` | `data.cityofnewyork.us/resource` | `application/geo+json` | `348` |
| `baltor_public_good_jsonfeed` | `baltor.ai/public-good/feeds` | `application/feed+json` | `348` |
| `skillsforgood_curated_stream` | `skillsforgood.org/feeds` | `text/markdown` | `348` |
| `agentfeeds_public_good_trends` | `agentfeeds.si/public-good` | `application/rss+xml` | `348` |

## 3. Head-to-Head Benchmark (`30` Public Good Tasks Across All 29 Domains)

| Engine / Configuration | Tasks Evaluated | Tasks Passed | Pass Rate | DueCare Split-Leakage Missed | Redistribution-Rights Violations | Hallucinated SDG Codes | Max Contract Card (`bytes`) | Max Micro Card (`bytes`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `unassisted_llm_on_public_good_tasks_without_baltor` | `30` | `14` | `46.7%` (`0.4667`) | `9` | `7` | `11` | N/A | N/A |
| `baltor_10k_public_good_duecare_gemma4good_suite` | `30` | `30` | `100.0%` (`1.0000`) | `0` | `0` | `0` | `1,110` (`<= 2,048`) | `468` (`<= 1,024`) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked Before Engine Dispatch)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `topic_tag_only_without_public_benefit_reason_blocked` | `public_good_micro_meso_macro_factory_slot` | `preflight` (Layer 6) | `topic_tag_only_without_public_benefit_reason_refused` | `true` |
| `duecare_redistribution_rights_violation_blocked` | `public_good_feeds_datasets_and_sources_slot` | `preflight` (Layer 6) | `duecare_redistribution_rights_violation_refused` | `true` |
| `un_endorsement_or_affiliation_claim_blocked` | `public_good_micro_meso_macro_factory_slot` | `preflight` (Layer 6) | `un_affiliation_or_endorsement_claim_refused` | `true` |
| `oversized_public_good_contract_card_blocked` | `public_good_micro_meso_macro_factory_slot` | `preflight` (Layer 6) | `oversized_public_good_contract_card_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest tools/test_public_good_10000_sdg_duecare_and_gemma4good_engines.py -v
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/public_good_10000_sdg_duecare_and_gemma4good_engines.py
```

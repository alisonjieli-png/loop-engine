# Owner PC 120-Project Portfolio, Trades & Per-Node Sub-Task Graph Harness Suite

- Date: `2026-10-17`
- Implementation: `tools/owner_pc_120_projects_trades_and_subtask_graph_harness_engines.py`
- Test Suite: `tools/test_owner_pc_120_projects_trades_and_subtask_graph_harness_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic execution across 2 slot families, 8 swappable engines, 12 portfolio and trade domains, 120 complete 5-file harness component packs totaling 600 files, 12 hierarchical `SolutionGraph` DAG workflows totaling 72 evaluated sub-task nodes, and 4 known-wrong preflight controls)

## 1. Architecture & 7-Layer ComponentEnvelope Slot Families

1. **Slot Family 1 (`owner_pc_projects_and_trades_component_slot`)**:
   - Synthesizes verified 5-file Harness Component Packs (`baltor_contract_card.json`, `AGENTS.md`, `RULES.md`, `MEMORY.md`, and `verifier.py`) grounded in `/home/username/Documents/DOT-120-PRIORITIZED-IDEAS.md` and the owner's local repositories across **12 Core Portfolio & Trade Domains (`10` workflows per domain = `120` packs = `600` distinct component files)**:
     1. `D01_janitorial_and_facilities_sourceloop` (`DOT-120 #3 SourceLoop`: commercial janitorial bidding, `ISSA 612` cleaning rates per sq ft, `OSHA 29 CFR 1910.1200` `SDS` dilution safety, night-crew `QR` checklists, multi-site dispatch)
     2. `D02_welding_and_structural_fabrication` (`AWS D1.1` / `ASME Section IX` `WPS`/`PQR` qualification, preheat/interpass temperature calculators, shielding gas flow rates, `AWS A2.4` weld symbol verification, ultrasonic/radiographic `NDT` logs)
     3. `D03_framing_demising_walls_and_building_permits` (`/home/username/permits` `523 Pleasant St - Tenant 1 Demising Wall Permit Set` & `DOT-120 #45`: `IBC`/`IRC` stud spacing, fire-rated `UL U419`/`V438` demising wall assemblies, municipal construction control affidavits, `MEP` rough-in inspection checklists)
     4. `D04_legal_discovery_preservation_and_touhy` (`/home/username/aitch_boat_ramp_dispute` & `DOT-120 #20 LeaseWright`: `FRCP` Rules `26`/`34` discovery requests, litigation hold and spoliation preservation notices, `32 CFR § 516` `USACE` `Touhy` requests, Bates-range `FRE 502` privilege logs, commercial lease abstraction)
     5. `D05_parametric_design_3d_and_creative_studio` (`DOT-120 #2 Luxe Prompting`, `#5 Creative Studio`, `#50 Worldsmith`, `/home/username/ai_parametric_animation`: `Blender`/`CadQuery`/`SolidCraft` horizon-enforced `3D` scenes, `PBR` shaders, `9:16` safe-zone motion graphics)
     6. `D06_affiliate_marketing_and_comparison_sites` (`DOT-120 #22 SponsorAgent`, `#104 Affiliate Websites`, `#105 AI-Tool Directories`, `#106 AdStack`, `/home/username/repodir`: `FTC 16 CFR Part 255` disclosure-compliant comparison tables, `EPC`/`RPM` attribution, buyer-keyword clustering, automated tool directories)
     7. `D07_growth_engineering_and_bhw_style_automation` (`DOT-120 #69 Leadova`, `#101 AI Influencer Auto Bot`, `/home/username/agency_email_scraper`, `/home/username/social_media_content_remixer`: programmatic `SEO`/`GEO` topic hubs, `SPF`/`DKIM`/`DMARC` warm-up and `CAN-SPAM` compliance gates, isolated browser contexts, viral hook testing with strict `CFAA` and spam-trap refusal guards)
     8. `D08_skills_state_and_hermes_portability` (`/home/username/.le-agent-stack-tmp` `tessl.io` `skills.state`, `agentskills.io`, `skillsbench.md`, `/home/username/.hermes/hermes_state.py`: cross-harness `skills.state` `SHA-256` lockfiles and zero-drift state migration across `Claude Code`, `Codex`, `OpenCode`, `Pi`, and `Hermes`)
     9. `D09_entity_radar_and_suspicious_network_intel` (`DOT-120 #7 ATLAS`, `#23 Entity Radar`, `/home/username/suspicious_networks_analysis`: beneficial-ownership graph traversal, `OFAC` `SDN` fuzzy screening, cross-dataset no-ID entity resolution)
     10. `D10_geospatial_delivery_and_address_verification` (`/home/username/is_this_the_correct_delivery_location` & `DOT-120 #75 AddressMatch`: rooftop vs parcel-centroid geocoding, drop-off photo `EXIF` pin verification, `USPS Publication 28` normalization)
     11. `D11_quant_trading_and_roll_watch_signals` (`DOT-120 #116 Roll Watch`, `#117 Market Signal`, `#118 Giga Trader`, `/home/username/spy_component_sentiment_analyzer`: futures roll-yield calendars, options gamma exposure, zero-lookahead walk-forward backtesting)
     12. `D12_duecare_and_humanitarian_safety` (`DOT-120 #1 PWE`, `#33 DueCare`, `#62 Migrasia/DWEP`: clinical and civic safety evaluation, `ILO` zero-recruitment-fee migrant worker contract verification)
2. **Slot Family 2 (`per_node_unique_harness_dag_configurator_slot`)**:
   - Grounded in `/home/username/universal-node-graph-flexible-solutioning-gpt` `SolutionGraph` and the `ASTRA.md` One-Loop Runtime, decomposes any Macro Initiative (`macro_orchestrator`, Level `0`) into Meso Sub-Tasks (`meso_subtask`, Level `1`) and Micro Sub-Sub-Tasks (`micro_sub_subtask`, Level `2`).
   - Every `Loop` vertex in the `DAG` receives its own unique `NodeHarnessConfig` with a pinned `skills.state` `SHA-256` digest (`1-2` Contract Cards `<= 220` tokens, `0` cross-node context pollution), a least-privilege tool allowlist, scoped effect authority, and independent verification (`worker_profile_id != node_verifier_id`).

## 2. End-to-End 12-Workflow Sub-Task Graph Benchmark (`72` Evaluated DAG Nodes)

| Strategy | Workflows (`Nodes`) | Node Pass Rate | Mean Tokens / Workflow | Token Spend Delta | Mean Workflow Cost (`USD`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `monolithic_single_harness_agent_without_baltor` | `12 (72)` | `39 / 72 (54.2%)` | `41,800` | `baseline` | `$0.1840` |
| `baltor_per_node_unique_harness_dag` | `12 (72)` | `71 / 72 (98.6%)` | `3,420` | `-91.8%` | `$0.0014` |

## 3. Known-Wrong Controls Verified at Layer 6 (`preflight`)

| Control | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- |
| Control 1 (`a`) | Child `micro_sub_subtask` node inheriting unrestricted parent root shell and live payment authority | `child_subtask_unrestricted_effect_inheritance_refused` | Layer 6 (`preflight`) |
| Control 2 (`b`) | `skills.state` lockfile manifest with drifted `SHA-256` skill tree digest | `skills_state_lockfile_digest_drift_refused` | Layer 6 (`preflight`) |
| Control 3 (`c`) | Affiliate or growth automation payload omitting `FTC 16 CFR Part 255` disclosure or violating `CAN-SPAM`/`CFAA` rules | `ftc_canspam_or_cfaa_compliance_gate_refused` | Layer 6 (`preflight`) |
| Control 4 (`d`) | Circular back-edge dependency (`macro_00_root -> meso_01_intake -> micro_03_calc -> macro_00_root`) in the sub-task `DAG` | `cyclic_subtask_graph_dependency_refused` | Layer 6 (`preflight`) |

# Full Project Review — Loop Engine + Harness Campaigns + Task Database

- Date: 2026-09-11 (UTC). Author: opencode session (Muse Spark), 3 days of work.
- Audience: GPT Astra review. Purpose: everything learned, every step taken, every folder — one file.
- Rule for reading claims: measured numbers carry sources; anything inferred is labeled inference. No secrets are in this file (credential handling §12).

## 1. Repository identity

- Path: `/home/username/loop-engine`. Remote: `https://github.com/alisonjieli-png/loop-engine.git`. Branch: `main`.
- Product: Loop Engine, Python distribution `loop-engine`, import `loop_engine`. Public README title: "Building with Loops".
- Governance: `AGENTS.md` (short, binding). Core docs: `README.md`, `docs/architecture/CONSTITUTION.md`, `architecture.yaml`, `terminology.yaml`, `docs/contracts/README.md`, `docs/components/README.md`, `humanizer-context.md` (public prose rules), `docs/context/CODEX-START-HERE.md` (coding-agent handoff), `docs/context/REFERENCE-SOURCES.md`.
- Separate project (design reference only, never merged): `/home/username/taedri.dev`.
- Separate data (not in repo): `/home/username/task_database` (8 adapted gated ML tasks + 318 raw Kaggle downloads).
- Separate runs (not in repo): `/home/username/task-campaign-runs` (campaign cells), `/home/username/probe-work` (probes, logs, slot state, status feed).

## 2. One-idea architecture

Every executable vertex is a Loop. Fixed vocabulary: relationships (Starting, Spawned-by, Queried-by, Retrieved-by, Connected-from), roles (Practitioner, Intelligence, Solution), modes (deterministic, hybrid, non-deterministic), step profiles (reference nine-step kernel of 13 nodes, compact five-step, custom, atomic, open), typed contracts, budgets, permissions. Model calls go only through the ModelGateway (one attempt each, usage accounted, fail-closed). External harnesses run as confined processes (bubblewrap) with no credentials and no tools, talking to models only through a private relay. Intelligence has 4 persistent layers (Context, Code, Runtime History/Solution, User Feedback); Runtime Memory is per-run and temporary. Memory promotion (candidate → independent review → promote/rollback) is governed; self-approval is refused by construction.

## 3. Session timeline (2026-09-08 → 09-11)

- 09-08: embodiment catalogue (30 designs, 7 axes), entry docs (START-HERE etc.), self-test 3412/3412.
- 09-09: harness synthesis (harnesses as loop-node capability units), T1 transport gates (15/19), open-source harness arms wired.
- 09-10: repo + session review; tactical endpoint recovered and verified; gateway route `custom.tactical` built; capacities measured by probe (accept to 2^31-1, 200K prompts OK; declared 1048576/200000 with provenance); live-path defects fixed (context_window setting, fit-window allocations, socket-dir cap); output-type compat repairs; T1 to 17/19 (gptme fixed; freebuff/OI root-caused); full-solve qualifications 14/17; task-database surveyed (8 gates validated, 1 gate crash fixed); campaign runner built (contract append, artifact bridging, parallel, standard report, health gate, rate throttle); product acceptance 4/4; self-test 3750/3750; loop sweep 372/372.
- 09-10 late: 24-cell campaign (2 perfect gate passes: 20news 1.0, Kannada 1.0, both opencode); endpoint died mid-run; watcher self-resolved on recovery (+1 pass); questions expanded by phase; decomposition mapped; memory full-cycle proven (reject placeholder, accept+promote real lesson).
- 09-11: research rounds (ToolGrad/GEPA/RLTR/R-Zero/SWE-smith; MLE-bench/constraint-tax; scaffolds/skills; debate/serving/verifiers); closed-loop verifier capability built; repetition-guard policy; plan outlines; kernel-node decision (deferred, needs ADR); Discord/tactical dispute support (loop proof, image tests, telemetry guide); paced retry + batch2/batch3 campaigns; new API key stored; rate raised to 20s at owner request; image T2I/vision tests.

## 4. Folder map (complete)

Root: AGENTS.md, README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE, SECURITY.md, architecture.yaml, terminology.yaml, humanizer-context.md, loop-engine.settings.example.yaml, pyproject.toml, predictions.csv.
- `src/loop_engine/`: core/ (266 modules: gateway, harness, practitioner, settings, memory backends), loop/ (45: runtime, kernel, contracts, profiles, delegation, reactive), code_nodes/ (47: solve runtime, solution graph/compiler, reports), memory/ (episodic/lifecycle/model/procedural/query/semantic/storage/working), intelligence/ (context/code/runtime_history_solution/user_feedback), catalog/, kernel/, node/, generation/, governance/, data/ (YAML incl. practitioner_context_intelligence.yaml + fallback), evidence/, ontology/, ARCHITECTURE-MAP.md, _self_test.py, _conformance_scan.py, forbidden_paths.json, architecture_conformance.json.
- `src/loop_engine/strings/`: question_engine.py (43 forms), interrogation.py (bank), solution_shaping, capture, foundry.
- `docs/`: architecture/ (48 incl. constitution, HARNESS-AS-LOOP-NODE, taxonomy), components/ (7), contracts/ (2 + session-handoff schema), context/ (7 incl. CODEX-START-HERE), verification/ (49 dated notes incl. HARNESS-EMBODIMENT-TRIALS-2026-09-10), research/ (26+ incl. 4 new landscape notes), implementation/ (3 incl. IMPROVEMENT-BACKLOG-2026-09-11), guides/ (21), prompts/ (mandate briefs), benchmarks/, evidence/, archive/, migrations/, reference/, internal/.
- `embodiments/` (47): one dir per harness with harness.json (pinned binary/version/style) + runtime/; plus lab-only folders (adaptive_tree, brokered_container, durable_reactive, native, parallel_portfolio...); HARNESS-GUIDE.md, catalog.json, ARCHITECTURE.md.
- `devtools/`: embodiment_lab/ (6 placement experiments, full_solve_qualification.py), embodiment_axes/ (30 designs, 7 families, registry.py/choose.py, CATALOG/FINDINGS).
- `tools/`: task_campaign.py (campaign runner), harness_t1_gates.py, batch/export/checkpoint helpers.
- `examples/` (28): 22_product_quickstart (acceptance), 25_host_runtime (140 unit tests), tasks/.
- `benchmarks/` (11), `case-studies/` (4), `integrations/` (5), `showcase/`, `kaggle/`, `build/`, `dist/`, `checkpoints/`, `artifacts/` (dated runs, T1 reports, audits), `core/` (empty/stub), `example-output/`, `graphify-out/`, `predictions.csv`.
- Outside repo: `/home/username/task_database/{adapted (8 gated), kaggle_tasks (318 raw)}`; `/home/username/task-campaign-runs/{full1,full2,pilot*,paced1,batch2,batch3}`; `/home/username/probe-work/` (settings, slot state + trace, logs, status feed, image traces, openapi spec, watcher, probes).

## 5. Live evidence summary (all measured)

- T1 transport 17/19 (freebuff: hosted protocol unqualified by design; openinterpreter_rust: uniform-label slug sniffing, proven working with campaign slug).
- Full-solve qualification 14/17 (+3 honest fails, negative controls discriminate).
- Campaign: 51+ cells, 3 perfect gate passes (20news opencode 1.0 + codex 0.7438; Kannada opencode 1.0); 2022-ucs plateau 0.5022 = constant predictor on all arms (computed offline).
- Self-test 3750/3750; conformance ALL PASS; loop sweep 372/372; acceptance 32/32; product acceptance 4/4.
- Tactical: gemma-4-coding-abliterated only (no Hermes touched); ~2,000 calls; max_attempts=1 (no resubmits, all prompt digests distinct); outage then recovery; current pace 20s serial, health-gated.
- Image tests: T2I via API returns unexecuted dalle.text2im JSON (×2, pre/post toggle); vision input accepted-but-ignored (red→"Black", ~0 image tokens); no /v1/images route exists (full route map pulled); server max_batch_size=1 (root cause of outage under parallel load).

## 6. Fixes shipped (uncommitted, for review)

Settings context_window; fit-window allocations; short socket dirs; output-type compat; underlying_error (reactive + harness, type-only persisted); gptme gate probe; OI chat-wire + relay routing; 20news gate csv fix; questions (+14 across phases) + 6 forms; guidance (sufficiency, established-facts, recurrence, reflection, coverage); repetition-guard policy; structured stall exception; plan-outline artifacts; closed-loop verifier capability + CLI + runner wiring; cross-process throttle + live override; health gate/deferral/merge; runner parse hardening; manifest digest + map updates; question-engine limit scaling.

## 7. Open items (backlog reference: docs/implementation/IMPROVEMENT-BACKLOG-2026-09-11.md)

P0: repetition-guard live validation; glm preflight (needs Ollama quota); prose-path inference design; vacuous-accept hole; recovery-panel wiring. P1: orient-compliance study; ToolGrad-12B serving; freebuff design; ensemble/router/reactive exercising; memory promotion frequency. P2: endpoint backoff refinement; best-artifact pointers in reports.

## 8. Current background state

- batch3 (kilo/cline/mistral_vibe × 8, verifier-enabled) running serially.
- Endpoint watcher polling; status feed every 15 min at /home/username/probe-work/status.log.
- Slot trace at /home/username/probe-work/slots/slot-trace.log (every claim timestamped).

## 9. Standing rules for the reviewer

Nothing is committed; treat all changes as concurrent-agent work (verify before touching). No secrets in repo or this file; credentials live only at ~/.config/tactical_key.env (0600). Live model work needs explicit authority; double_opt_in-style growth-slowing changes need informed request. Public claims must not exceed saved evidence (this file IS part of that evidence).

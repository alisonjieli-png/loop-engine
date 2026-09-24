# Wave 5 gap matrix

Kind: scout count of the harness intelligence library and every candidate wave,
September 23, 2026, against `origin/main` at `a1fc7432`. It shows which file
classes, harnesses and domains are thin, and which wave 5 assignment fills each
gap. Counts are candidate inventory, not a public library number: only approved,
active packages count publicly, and today that is 43.

## How the counts were made

`scout/inventory.py` read, without changing anything:

- the starter catalogue (`items.json`, the three specification files and
  `host-release/manifest.json`) at `origin/main`;
- the manifests of first-party waves 1 to 4 and the two mixed-format pilots;
- the Codex integration worktree (12 native method packages, 20 planned methods)
  and the Codex review worktree (one plugin, two example packets);
- the staged outside-material index of the September 23 ingestion run
  (`artifacts/library-ingestion-2026-09-23/staged-index-2.json`).

Every row is in `scout/existing-inventory.tsv`; every identity is in
`existing-identities.txt`. File class comes from the record's kind and paths.
**Domain is a keyword heuristic over identity, title and purpose.** Outside
material has titles only, so 248 of its 596 skills stay unclassified. Treat
domain counts as a coarse signal and file-class counts as exact.

## 1. Population

| Status | Count | Notes |
|---|---:|---|
| Served and approved | 43 | Starter items in the host release. |
| Starter candidates without approval | 80 | Same catalogue: 6 rejected on September 21, 30 rejected by the September 22 panel pilot (dated record, not yet merged), 44 without a verdict. |
| First-party wave and pilot candidates | 89 | Waves 1 to 4 (80 text skills), pilot 1 (6), pilot 2 (3). |
| Codex candidates not yet on `main` | 13 | 12 native method packages and 1 Claude Code plugin. |
| Planned, not generated | 20 | Codex seed plan (10) and Hermes plan (10). |
| Example packets, not library items | 2 | Codex focused-step packets. |
| Staged outside candidates | 3,251 | 596 skills, 445 instruction files, 2,210 registry connections. |
| **All identities** | **3,498** | No identity repeats. |

First-party material (served plus first-party candidates) is 225 items.

## 2. Family and kind

| | Count |
|---|---:|
| Family `harness` | 3,498 |
| Family `loop_native` | 0 |
| Family `open_knowledge` | 0 |
| Kind `skill` | 806 (43 served, 166 first-party, 1 planned, 596 outside) |
| Kind `tool` | 2,243 (14 first-party, 19 planned, 2,210 outside registry links) |
| Kind `instruction_file` | 449 (2 first-party templates, 2 examples, 445 outside rules) |
| Kind `reusable_code` | 0 |

Every item is harness family because every body sits in the `harness_local`
source layer. Runtime History and Solution material and User Feedback material
have no items, by design, until real runs and real feedback exist.

## 3. File classes (the main gap)

| File class | Served | First-party candidates | Planned | Outside staged | Wave 5 adds |
|---|---:|---:|---:|---:|---:|
| Skill, text only | 43 | 156 (+4 text checklists) | 0 | 596 | 0 |
| Skill with scripts and tests | 0 | 6 | 1 | 0 | **15** |
| Standalone tool package (instruction plus tool) | 0 | 12 | 19 | 0 | 0 |
| Verifier or checklist package with code | 0 | 0 | 0 | 0 | **10** |
| Root instruction fragment or template | 0 | 2 | 0 | 0 | **5** |
| Task packet for one step | 0 | 0 (2 examples) | 0 | 0 | **10** |
| Hook with script | 0 | 0 (1 inside a plugin) | 0 | 0 | **5** |
| Subagent definition | 0 | 0 (1 inside a plugin) | 0 | 0 | **5** |
| Command or prompt file | 0 | 0 (1 inside a plugin) | 0 | 0 | **5** |
| Protocol server configuration, local server | 0 | 1 (needs a third-party package) | 0 | 0 | **5** |
| Protocol server configuration, remote link | 0 | 0 | 0 | 2,210 | 0 |
| Rules file (Cursor, Copilot, Cline, Claude rules) | 0 | 0 | 0 | 445 (252 Cursor, 193 Copilot) | **5** |
| Plugin bundling several classes | 0 | 1 | 0 | 0 | **5** |
| Settings or permission fragment | 0 | 0 | 0 | 0 | **5** |

Thin or empty first-party classes, most severe first: settings fragments (0
anywhere), task packet templates (0), hooks (0 standalone), subagents (0),
commands (0), rules files (0 first-party), verifiers with code (0), local
protocol servers that run without an install step (0 working in a clean home),
plugins (1), skills with scripts (6).

## 4. Harness targets

"Named" means the item lists the harness; "any skill client" means an Agent
Skills folder with no named harness.

| Harness | Served | First-party candidates | Planned | Outside staged | Wave 5 packages naming it |
|---|---:|---:|---:|---:|---:|
| Any skill client | 43 | 163 | 0 | 596 | 0 |
| Claude Code | 0 | 7 | 20 | 0 | 73 |
| Codex | 0 | 18 | 20 | 0 | 50 |
| OpenCode | 0 | 18 | 0 | 0 | 60 |
| Pi | 0 | 17 | 0 | 0 | 40 |
| Gemini CLI | 0 | 0 | 0 | 0 | 58 |
| Cursor | 0 | 0 | 0 | 252 | 23 |
| Copilot | 0 | 0 | 0 | 193 | 21 |
| Goose | 0 | 0 | 0 | 0 | 10 |
| Kimi CLI | 0 | 0 | 0 | 0 | 10 |
| Cline | 0 | 0 | 0 | 0 | 5 |
| Any protocol client | 0 | 0 | 0 | 2,210 | 0 |

No first-party item names Gemini CLI, Cursor, Copilot, Goose, Kimi CLI or Cline.
Kimi CLI placements are not documented in any repository research file, so wave 5
records them as unverified.

## 5. Domains (heuristic)

| Domain | Served | First-party candidates | Planned | Outside staged |
|---|---:|---:|---:|---:|
| Analytics and reconciliation | 1 | 32 | 0 | 3 |
| Software change and testing | 6 | 25 | 1 | 60 |
| Data cleaning and quality | 16 | 14 | 0 | 6 |
| Agent and harness operations | 1 | 24 | 0 | 79 |
| Security, secrets and compliance | 2 | 22 | 1 | 16 |
| Project, product and customer | 7 | 17 | 0 | 47 |
| Infrastructure and release | 2 | 20 | 0 | 86 |
| Algorithms and computation | 0 | 12 | 10 | 0 |
| Data science and machine learning | 8 | 3 | 0 | 18 |
| Operations, finance and logistics | 0 | 9 | 0 | 3 |
| Language and framework conventions | 0 | 0 | 0 | 330 |
| Frontend and design | 0 | 0 | 0 | 104 |
| Documentation and writing | 0 | 0 | 0 | 41 |
| External service connections | 0 | 0 | 0 | 2,210 |
| Unclassified | 0 | 4 | 8 | 248 |

### First-party domain by file class

| Domain | Text skill | Text checklist | Skill with scripts | Tool package | Instruction template | Local server | Plugin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analytics and reconciliation | 33 | 0 | 0 | 0 | 0 | 0 | 0 |
| Software change and testing | 31 | 0 | 0 | 0 | 0 | 0 | 0 |
| Data cleaning and quality | 21 | 2 | 6 | 0 | 1 | 0 | 0 |
| Agent and harness operations | 23 | 0 | 0 | 0 | 1 | 0 | 1 |
| Security, secrets and compliance | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| Project, product and customer | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| Infrastructure and release | 20 | 2 | 0 | 0 | 0 | 0 | 0 |
| Algorithms and computation | 0 | 0 | 0 | 12 | 0 | 0 | 0 |
| Data science and machine learning | 11 | 0 | 0 | 0 | 0 | 0 | 0 |
| Operations, finance and logistics | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| Unclassified | 3 | 0 | 0 | 0 | 0 | 1 | 0 |

Only data cleaning and algorithms have any executable first-party material. Data
science and software change, the heart of two of the three use cases, have none.

## 6. The three use cases, step by step

### Tickets worked overnight on a local model

| Step a fresh harness must do | Existing first-party material | Gap | Wave 5 |
|---|---|---|---|
| Decide which tickets fit tonight | none | no queue planning | a06 `plan_night_queue`, a09 `ticket_triage_packet` |
| Read the ticket as checkable criteria | prose on writing criteria | no extraction tool | a03 `extract_ticket_acceptance_criteria` |
| Find where to look without reading everything | none | no map or scout | a03 `map_repository_layout`, a05 `repository_scout` |
| Reproduce the report as a failing test | prose; pilot repairs an existing failure | no reproduction step | a09 `ticket_reproduction_packet` |
| Run only the relevant tests and read failures | prose | no selection or parsing tool | a03 `select_tests_for_changed_files`, `extract_test_failures`, a05 `test_run_summarizer` |
| Stay inside scope with no one watching | none | no hook, no settings, no rules | a04 hooks, a13 settings, a08 rules, a14 fragments |
| Prove the fix and that no check was weakened | review prose | no verifier | a12 verifiers |
| Survive interruption and hand over | prose | no resume or handoff step | a09 `interrupted_step_resume_packet`, a06 `write_step_handoff`, `record_blocker` |
| Report the night honestly | none | no report or claim check | a09 `morning_report_packet`, a12 `verify_morning_report_claims` |
| Notice a local model that cannot make tool calls | none; roadmap records 37 of 37 failed steps | no detector | a03 `detect_text_written_tool_calls`, a06 `night_preflight` |

### Data set cleanup without an expensive model

| Step | Existing first-party material | Gap | Wave 5 |
|---|---|---|---|
| Profile the table | one-column prose; CSV structure and encoding scripts | no whole-table profile tool a model can call | a07 `csv_profile_server`, `csv_row_sampler_server`, a05 `data_sample_inspector` |
| Plan rules with evidence | none | no planning step | a10 `cleaning_plan_packet` |
| Parse dates and numbers, map categories, missing tokens, outliers | prose restating repository functions for names, phones, emails, addresses | no executable parser for these types | a01 five executors |
| Apply approved rules to a copy | prose restating repository functions | no step template | a10 `cleaning_apply_packet`, a08 `raw_data_stays_read_only` |
| Check the result | none executable | no contract check, no change-log check | a15 `check_csv_column_contract`, `verify_cleaned_copy_change_log`, a07 `json_schema_check_server` |

### A full data science competition solve

| Step | Existing first-party material | Gap | Wave 5 |
|---|---|---|---|
| Turn the rules into a brief | none | no brief step | a10 `competition_brief_packet` |
| Check train and test for drift and leakage | a question set | no tool | a02 `audit_train_test_drift`, a05 `leakage_reviewer` |
| Build leakage-safe validation | none | no fold or time split tool | a02 `build_group_stratified_folds`, `build_time_ordered_splits`, a15 `verify_fold_group_separation` |
| Encode categories without leakage | none | no tool | a02 `target_encode_out_of_fold` |
| Train a baseline and log it | none | no step | a10 `baseline_training_packet`, a08 `reproducible_competition_notebooks` |
| Compare experiments honestly | prose on metrics | no ranking or recomputation | a02 `rank_experiments_by_fold_scores`, a15 `recompute_claimed_cv_score`, a06 `pick_next_experiment` |
| Submit a valid file | none | no validator | a10 `submission_assembly_packet`, a15 `validate_submission_file` |

## 7. Readiness for the first native review profile

| Class | Reviewable by the first native profile | Why |
|---|---|---|
| Skills with scripts, verifiers, task packets, root fragments | yes | Root `SKILL.md` or `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`; Python with executable roles; passive files under `references/`, `contracts/`, `examples/`. |
| Hooks, subagents, commands, protocol server configurations, rules, plugins, settings | held | Roles, activation folders or non-schema configuration the profile does not qualify yet. |

Wave 5 therefore gives the review panel 40 packages it can pre-check today and 35
packages that give the profile extension real material to qualify.

## 8. What wave 5 does not fill

- Loop-native and open knowledge families stay empty.
- Frontend, documentation and language convention domains stay outside-only.
- Standalone tool packages and text skills get nothing new; they are the two
  classes the library already has most of.
- Native loading of any wave 5 package is unobserved until the integrator's probes run.

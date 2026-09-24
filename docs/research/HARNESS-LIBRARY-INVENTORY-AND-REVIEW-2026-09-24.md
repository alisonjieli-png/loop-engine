# Harness library inventory and review, September 24, 2026

Kind: dated research record. It counts the harness packages and files that
Baltor's library sources hold on September 24, 2026, reports a sampled
engineering review of them, and states what blocks their approval. It
approves nothing, serves nothing and changes no candidate. The public library
number stays the approved, active count, which is 43.

The counts come from `tools/inventory_harness_library.py`. The script read
records only, made no network request and no model call, and wrote only its
own output. The review is a sample that three review steps of the same
workflow read in full; where a unit runs, the reviewers ran it in a scratch
copy. The [roadmap](../roadmap/roadmap.yaml) stays the task authority,
through its steps S-6.40 (grow the library), S-6.45 (licences), S-6.53
(generation along the occupation grid), S-6.62 (catalogue releases) and
S-6.63 (the review panel).

| File | What it holds |
|---|---|
| [inventory.json](../../artifacts/library-inventory-2026-09-24/inventory.json) | Every count with its basis, the identity lists, version histories, and generation attempts that produced no unit |
| [inventory.md](../../artifacts/library-inventory-2026-09-24/inventory.md) | The summary that the script writes |
| [sampled-review-1.json](../../artifacts/library-inventory-2026-09-24/sampled-review-1.json) | The three review groups, with the path, verdict and reasons of every finding |
| [check_removed_guards.py](../../artifacts/library-inventory-2026-09-24/check_removed_guards.py) | Eight mutants of the script; each one fails a named test |

Times are universal time. Dates are the owner's local dates.

## The answer in brief

- **Served now: 43 items.** All 43 are skills, each one Markdown method
  body. Three reviewers who wrote none of them approved them on September 21,
  2026. The committed host release manifest names them, and the record of Fly
  release 24 names catalogue release `69da7ead21f9` with 43 items. The live
  service was not queried for this count.
- **Library sources: 1,146 distinct harness units and 2,469 unit files**
  (2,259 distinct file digests) in eleven sources. No identity appears in two
  of them.
- **States:** 43 approved and served, 64 passed a review precheck, 21 refused
  by a review precheck, and 1,018 candidates with no review precheck. A
  precheck pass is not an approval. No record in these sources approves any
  unit beyond the 43.
- **Kinds:** twelve kinds, plus 3 units whose kind is not declared. Skills
  are 947 of the 1,146 units, and 720 of those skills are single Markdown
  files from the overnight batch, which is still running.
- **Three more committed folders,** found outside the list of sources that
  this inventory was asked to count, add 14 units. One of them repeats a unit
  already counted, so all folders together hold 1,159 distinct units, with
  2,585 unit files and 2,349 distinct file digests.
- **Outside research:** 4,000 records about outside skills, plugins, protocol
  servers and contracts. They are leads, not library units. No licence among
  them has been verified.
- **Review:** the sample covered 96 library units and 12 outside research
  records, and scans found 3 more units. 5 library units and 5 outside records
  must never be served. The reasons are in
  [Units that must never be served](#units-that-must-never-be-served).
- **Approval is blocked today.** The review panel needs three approvals from
  three model families other than the producer's. The Ollama Cloud weekly
  allowance is spent, the Codex reviewer is excluded because it does not
  report its model, and the Claude Code reviewer has no key here and belongs
  to the family that produced wave 5 and the starter catalogue.

## How the counts are made

- A **unit** is one logical package or one single-file candidate, as the
  records of its source count it. Only the current version of each unit
  counts. The Tactical blocks batch holds 10 identities in 19 package
  versions, and the mixed native originals hold 12 identities in 36 versions.
- **Unit files** are the files a harness receives for the current version of
  a unit. Manifests, review notes, reports and logs count only under all
  files.
- An **identity** is a normalized name (lowercase, with catalogue prefixes and
  a trailing version removed) or an alias that a record declares. An identity
  found in two sources counts once, with the state of its most advanced
  record. Two differently named methods that do the same work are not
  detected as one.
- A **kind** comes from the field that each source declares, such as
  `wave5.file_class` or the `file_kind` of an overnight idea, mapped to one of
  fourteen kinds. A value with no mapping stays unknown.
- A **state** comes from records. Approved and served means that an approval
  record and the host release manifest both name the unit. Passed a precheck
  means that the wave 5 check-all report or the native prechecks of the
  candidate review passed it. Candidate means that no review precheck record
  exists; a shape check at generation time does not count.
- Live sources are read as snapshots. The overnight batch is counted from its
  journal up to 13:55:54. At 17:14:18 the batch's own status record reported
  1,293 candidates and 147 failed ideas. Those later files are not in these
  totals.
- To count again, run
  `python3 tools/inventory_harness_library.py --output-dir artifacts/library-inventory-<date>`
  from the repository root. The script refuses to replace an existing
  inventory unless `--replace` is given, so each count keeps its own folder.
  Flags such as `--shared-checkout` and `--private-generation` name the
  folders outside the repository that it reads.

## Totals

```text
Harness units in the eleven library sources: 1,146 distinct identities
├── approved and served: 43 (the starter catalogue)
├── passed a review precheck, not approved: 64
│   ├── first-party wave 5: 56
│   └── Tactical blocks batch: 8
├── refused by a review precheck: 21
│   ├── first-party wave 5: 19
│   └── Tactical blocks batch: 2
└── candidate, with no review precheck: 1,018
    ├── overnight batch: 775
    ├── starter catalogue items that are not approved: 80
    ├── first-party waves 1 to 4: 80
    ├── Ollama wave drafts: 53
    ├── Codex component supply: 16
    ├── format pilots: 9
    ├── Gemma 4 harness components: 3
    ├── Codex research-inspired components: 1
    └── native candidate preparation: 1
```

| Kind | Library sources | With the three additional folders |
|---|---:|---:|
| skill | 947 | 947 |
| tool or script | 65 | 78 |
| subagent definition | 43 | 43 |
| instruction file or fragment | 28 | 28 |
| step packet | 14 | 14 |
| verifier | 10 | 10 |
| command or workflow recipe | 7 | 7 |
| hook | 7 | 7 |
| plugin manifest | 6 | 6 |
| protocol server configuration or server | 6 | 6 |
| rules file | 5 | 5 |
| permission settings | 5 | 5 |
| unknown | 3 | 3 |
| **Total** | **1,146** | **1,159** |

| File type of unit files, library sources | Files |
|---|---:|
| Markdown (`.md`) | 1,425 |
| JSON (`.json`) | 584 |
| Python (`.py`) | 305 |
| No extension (all 93 are `LICENSE` files) | 93 |
| CSV (`.csv`) | 19 |
| TOML (`.toml`) | 16 |
| Plain text (`.txt`) | 12 |
| Cursor rules (`.mdc`) | 6 |
| Diff (`.diff`) | 5 |
| JSON Lines (`.jsonl`) | 3 |
| SQL (`.sql`) | 1 |
| **Total** | **2,469** |

## Counts by source

| Source | Units | Unit files | All files | Kinds | States |
|---|---:|---:|---:|---|---|
| Served starter catalogue | 123 | 123 | 178 | skill 123 | approved and served 43, candidate 80 |
| First-party waves 1 to 4 | 80 | 80 | 207 | skill 80 | candidate 80 |
| First-party wave 5 | 75 | 752 | 1,510 | skill 15, step packet 10, verifier 10, and 5 each of instruction file or fragment, subagent definition, command or workflow recipe, hook, rules file, plugin manifest, protocol server configuration or server, and permission settings | passed a precheck 56, refused by a precheck 19 |
| Format pilots | 9 | 39 | 83 | skill 6, instruction file or fragment 2, protocol server configuration or server 1 | candidate 9 |
| Native candidate preparation | 1 | 13 | 69 | plugin manifest 1 | candidate 1 |
| Tactical blocks batch | 10 | 108 | 782 | tool or script 10 | passed a precheck 8, refused by a precheck 2 |
| Codex component supply | 16 | 128 | 384 | tool or script 16 | candidate 16 |
| Codex research-inspired components | 1 | 9 | 62 | tool or script 1 | candidate 1 |
| Gemma 4 harness components | 3 | 15 | 19 | unknown 3 | candidate 3 |
| Overnight batch | 775 | 775 | 778 | skill 720, subagent definition 34, instruction file or fragment 21 | candidate 775 |
| Ollama wave drafts | 53 | 427 | 795 | tool or script 38, subagent definition 4, step packet 4, skill 3, command or workflow recipe 2, hook 2 | candidate 53 |
| **Library sources** | **1,146** | **2,469** | | | |
| Mixed native originals (additional) | 12 | 96 | 656 | tool or script 12 | candidate 12 |
| Original native generation live runs (additional) | 1 | 7 | 59 | tool or script 1 | candidate 1 |
| Harness plugin context (additional) | 1 | 13 | 35 | plugin manifest 1 | candidate 1, the same plugin as the native candidate preparation fixture |
| Harness source research (outside research, not library units) | 4,000 records, 3,898 distinct names | 0 | 108 | skill 1,000, plugin manifest 1,000, protocol server configuration or server 1,000, other 1,000 (contracts) | leads; licence verified for 0 |

Where each source lives:

- Committed on `main`: the starter catalogue
  (`examples/29_intelligence_service/starter-catalogue`), first-party waves 1
  to 4 (`artifacts/first-party-harness-candidates-2026-09-22` and its
  `-wave-2`, `-wave-3` and `-wave-4-ops` folders), wave 5
  (`artifacts/first-party-harness-candidates-2026-09-24-wave-5`), the format
  pilots (`artifacts/harness-intelligence-format-pilot-2026-09-22` and
  `-wave-2`), native candidate preparation
  (`artifacts/native-candidate-preparation-2026-09-23` and
  `artifacts/tactical-first-batch-2026-09-24`), the Tactical blocks batch
  (`artifacts/native-blocks-batch-2026-09-24`) and the three additional
  folders.
- Uncommitted in the shared checkout `/home/username/loop-engine`: Codex
  component supply, Codex research-inspired components, Gemma 4 harness
  components and the harness source research, each under `artifacts/` with
  the date 2026-09-23 in its folder name.
- A run folder that git ignores, still being written:
  `/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch`.
- Outside the repository: the Ollama wave drafts, in six run folders under
  `/home/username/baltor-private/generation-2026-09-23`. The archive that the
  workflow named, `/home/username/.le-safety/session-4d86b429-scratchpad-20260924`,
  holds none of them.

## What these totals leave out

- **3,251 staged outside candidates.** The library ingestion run of September
  23 staged 596 skills, 445 instruction files and 2,210 protocol server
  connection packages for review. They contain third-party text, so they stay
  outside the repository in
  `/home/username/.le-library/ls1-runs/run-2026-09-23-b`, and
  [their evidence](../../artifacts/library-ingestion-2026-09-23/README.md) is
  committed without that text. None is approved.
- **The 4,000 outside research records,** which the table above reports
  separately. None of their names matches a library identity.
- **Three excluded folders:** 24 Loop-native candidate items of the
  intelligence layer coverage pack, two example step packets, and the plan
  folders of the Ollama wave, which hold plans, builders and checks rather
  than drafts.
- **Generation attempts that produced no unit:** 20 in the Tactical first
  batch, 18 in the Tactical blocks batch, 73 in the overnight batch at the
  snapshot, 28 in the Ollama wave and 4 in the original native generation live
  runs. `inventory.json` lists their outcomes by code.
- **Wave 5 payload drift:** 54 payload files differ from the digest that their
  `package.json` records, all of them in packages that a precheck refused. One
  declared file is missing and one file on disk is not declared.

## What the sampled review found

Three review groups read their samples in full on September 24, 2026. Group 1
read the first-party and native sources, group 2 the September 23 Codex and
Gemma 4 folders and the outside research, and group 3 the Tactical blocks
batch, the overnight batch and the Ollama wave drafts. Where a sampled unit
runs, the reviewers ran its tests, examples or probes in a scratch copy. The
review output does not record which model wrote each group, so this record
makes no claim that the reviewers are independent of any producer. The review
is repair and priority advice, not an approval.

This record reads the four verdicts as follows. Strong: no defect found that
blocks panel review. Usable with repair: useful to customers once the named
repairs are made. Weak: little customer value, or a defect that calls for
regeneration rather than repair. Must not serve: a rights, safety or
correctness problem that rules out serving the current bytes. The reasons in
the review file decide each case.

Groups 1 and 3 both read all ten Tactical blocks batch units. They disagree on
five verdicts: group 1 rates `render_secret_reference_connections` must not
serve where group 3 rates it weak, and group 1 rates four more units weak
where group 3 rates them usable with repair. This record keeps the stricter
verdict until the panel decides, because a stricter verdict costs a repair
while a looser one could let a defect through.

| Source | Sampled | Strong | Usable with repair | Weak | Must not serve |
|---|---|---:|---:|---:|---:|
| Served starter catalogue | 12 of the 43 served | 7 | 5 | 0 | 0 |
| First-party waves 1 to 4 | 12 of 80 | 9 | 2 | 1 | 0 |
| First-party wave 5 | 12 of 75 | 7 | 5 | 0 | 0 |
| Format pilots | 9 of 9 | 0 | 8 | 1 | 0 |
| Native candidate preparation | 1 of 1 | 0 | 0 | 1 | 0 |
| Tactical blocks batch, stricter of two reviews | 10 of 10 | 0 | 0 | 9 | 1 |
| Codex component supply | 12 of 16 | 0 | 6 | 6 | 0 |
| Codex research-inspired components | 1 of 1 | 0 | 1 | 0 | 0 |
| Gemma 4 harness components | 3 of 3 | 0 | 0 | 3 | 0 |
| Overnight batch | 12 of 881 written at 14:10 | 0 | 2 | 9 | 1 |
| Ollama wave drafts | 12 of 53 | 3 | 7 | 2 | 0 |
| **Library units** | **96** | **26** | **36** | **32** | **2** |
| Overnight files found outside the sample by scans | 3 | 0 | 0 | 0 | 3 |
| Outside research records | 12 of 4,000 | 0 | 2 | 5 | 5 |

### Served starter catalogue

Bodies are in `examples/29_intelligence_service/starter-catalogue/host-release/bodies/`.

- None of the 43 served bodies has a done section or an end rule. For
  example, `analyse_errors_by_segment_and_cluster.md` ends with "After the
  fix, repeat the analysis." and gives no point at which to stop.
- Some items only work together. `normalize_phone_numbers.md` and
  `copy_a_table_with_corrections_never_in_place.md` depend on the 0.9 and 0.6
  thresholds that only `apply_hold_or_escalate_each_correction` states.
- `restore_capitalisation_of_names.md` has 612 words, above the 600-word
  ceiling, and knowingly applies a wrong value: "eBay Store becomes Ebay Store
  at 0.95".
- Every body cites a `src/loop_engine/...` source that a customer cannot open.
- Among the strong items: `normalize_phone_numbers.md` (exact rules with four
  checkable examples), `measure_the_environment_before_relying_on_it.md`,
  `choose_metrics_by_task_type_and_industry.md` and
  `write_a_pinned_container_and_batch_job.md`.

### First-party waves 1 to 4

Packages are under `artifacts/first-party-harness-candidates-2026-09-22` and
its wave folders.

- Most sampled skills are compact text methods with completion fields and
  hold rules, and the arithmetic of the checked fixtures is correct, for
  example in `test-aggregate-trend-for-subgroup-reversal` and
  `screen-payable-for-document-mismatch`.
- No skill has a customer licence yet: the manifests record
  `rights_state: pending_independent_review`.
- 31 of the 80 descriptions have no "Use when" trigger, and 63 of the 80
  bodies have no labelled known-wrong case; that case sits in the review
  note, which is never delivered.
- `allocate-scarce-stock-by-promised-service` has 853 words against a median
  of 296, and its current bytes were not reviewed again after a quality
  regression.
- Weak: `compile-a-native-material-placement-plan` serves Baltor's own
  installer, not customers.

### First-party wave 5

Packages are under
`artifacts/first-party-harness-candidates-2026-09-24-wave-5/packages`.

- This wave holds the best format in the library.
  `a01_data_cleanup_executors/parse_dates_by_declared_formats` gives an exact
  first command, numbered steps, checks, a done section, a known-wrong case
  and a standard-library script with 11 passing tests.
  `a04_unattended_guard_hooks/guard_shell_command_allowlist` denied all 50
  bypass attempts of the reviewer, and
  `a07_local_data_tool_servers/sqlite_readonly_server` enforces read-only
  access in several layers.
- `a13_unattended_permission_settings/deny_env_file_reads_settings` fails its
  own tests on the committed bytes (3 failures and 1 error), and its Codex
  message contradicts its own package record.
- `a10_data_and_competition_step_packets/cleaning_apply_packet` has
  undeclared markers and a placeholder, `{{PROCESS_EFFECT}}`, inside its
  effects list. Effects must be fixed fields.
- `a11_session_plugins/overnight_ticket_plugin` runs a check command taken
  from ticket data, so a ticket imported from a tracker could run a shell
  command.
- 10 of the 25 `SKILL.md` files list harness folders, which rule 3 of the
  generation guide forbids, and 10 review notes cite repair evidence that
  exists only in a temporary scratch folder.

### Format pilots

Packages are under `artifacts/harness-intelligence-format-pilot-2026-09-22`
and `-wave-2`.

- The tool skills say "The owning Loop" to the customer and have no first
  action, done or stop heading. Their scripts are hardened and their tests
  pass.
- The customer distribution licence is pending for all 9.
- Weak: `connections/json-shape-stdio` needs the outside package
  `mcp==1.29.0` and failed in a clean home. The standard-library server of
  wave 5 replaces it.

### Native candidate preparation

- `artifacts/native-candidate-preparation-2026-09-23/prepared-plugin-fixture/packages/focused_brief_plugin`
  repackages an existing plugin and adds 0 new logical packages. Its hook
  runs at every session start and names `/usr/bin/python3`. Weak.

### Tactical blocks batch

Packages are under `artifacts/native-blocks-batch-2026-09-24`, eight in
`pending-panel-batch/prepared-batch/packages` and two in
`review/prepared-batch/packages`. The producer is recorded as
`tactical:gemma-4-coding-abliterated`. The word abliterated usually names a
model that was changed to remove its refusals, so the reviewers ask for
behavior probes on this output, not only static checks.

- The native prechecks run no tests. Three of the eight packages that wait
  for the panel passed every precheck and fail their own tests:
  `plan_workspace_file_transitions` calls itself forever and never produces
  output, `build_permission_scoped_lexical_index` crashes on its own example,
  and `validate_focused_attempt_handoff` fails 1 of 6 tests and its
  independent-acceptance check does nothing.
- Promised refusals are missing: duplicate keys, non-finite numbers and
  unknown symbols are accepted in several tools.
  `query_codegraph_change_impact` reports no impact for a misspelled symbol
  instead of refusing it.
- Generation leftovers ship to customers. Four of the ten tools keep "the
  prompt says" comments, one `AGENTS.md` is an implementation brief, and one
  `CLAUDE.md` contains Python code.
- No package ships a `LICENSE` file.
- Best unit: `check_tabular_transformation_invariants`, whose tests and
  verification cases all pass; it does not check columns that the change
  adds.

### Codex component supply and the research-inspired component

Packages are uncommitted in the shared checkout under
`/home/username/loop-engine/artifacts/codex-component-supply-2026-09-23/prepared-v2/packages`
and `/home/username/loop-engine/artifacts/codex-research-inspired-components-2026-09-23/prepared-v1/packages`.

- The code is correct and safe: standard library only, strict JSON framing,
  and all 160 packaged cases and 16 examples reproduce on Python 3.14.4.
- Customer value is limited. Data must be pasted into JSON, the caps are small
  (48 intervals, 256 table rows), and ten of the sixteen tools can only answer
  `invalid_input`, so a real finding looks the same as broken input.
- The `AGENTS.md` texts carry status labels, comparisons with other internal
  items, template lines from other tools and numbers joined to words
  (`At most48`).
- All sixteen use the same root-relative file names, so only one fits at a
  task root, and none has a Claude Code entry point.
- Most useful: `paired_sign_test` and `reconcile_keyed_tables`. The
  research-inspired `audit_wikilink_resolution` is the best-written package of
  this group, but it misses links on indented lines (2 of 4 found in a
  probe).

### Gemma 4 harness components

- The three units under
  `/home/username/loop-engine/artifacts/gemma4-harness-components-2026-09-23/packages`
  hold contracts, examples and cases only, with no `SKILL.md`, script or
  `LICENSE`. Two of them document maximums that do not fit their own 64 KiB
  input cap. Weak until they are built.

### Overnight batch

Files are under
`/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch/candidates/<lane>/`.
The batch runs six OpenCode setups: five Ollama Cloud models and the Tactical
endpoint's `gemma-4-coding-abliterated`.

- Every candidate is a flat `<name>.md` file rather than a `<name>/SKILL.md`
  folder, so no harness loads it as a skill.
- The idea matrix is degenerate. Every one of its 29,625 ideas carries the
  single occupation "Chief Executives". At the snapshot, all 775 candidates
  are aggregation ideas; at 14:10 the reviewers counted 801 of 881. The
  reviewers describe them as one method, "do not accept a plausible but wrong
  aggregate", relabelled by data type and use case.
- At 14:10, 847 of 881 files declared `license: MIT` in their own front
  matter against the generation guide, 295 were under 150 words, 93 were over
  600, and only 178 had numbered steps.
- At 14:13, 35 subagent files of the Tactical lane pinned a model (32 pin
  `gemma-4-coding-abliterated`, 3 pin `gemma-4`) beside a tool list. At least
  24 list the operator's own CodeGraph tool names, and 19 grant web fetch,
  shell, write or edit tools.
- Routing files send agents to folders that do not exist.
- Best: two files of the GLM lane, `image-aggregation-agentic-benchmark.md`
  and `file-path-aggregation-agent-coordination.md`, with typed contracts,
  declared effects and decoy acceptance checks. The GLM lane averages 667
  words.

### Ollama wave drafts

Packages are under `/home/username/baltor-private/generation-2026-09-23/<run>/<method>.attempt-1/candidates/packages/`.

- Strong: `docs_api_draft_and_verify_change_docs_commands`,
  `docs_api_docs_change_reviewer_subagent` and
  `testing_ci_classify_flaky_tests_from_rerun_history`.
- 9 of the 12 sampled packages have a failing test, a malformed case file or
  a wrong example.
- Both hook packages write Claude Code settings in a shape that Claude Code
  does not register, and the compaction hook's matcher `compact` never
  matches.
- `data_cleanup_report_json_field_type_drift` refuses every valid request, and
  `overnight_tickets_budget_step_context_for_small_windows` inverts its token
  ratio, so 4,000 bytes count as 16,000 tokens.
- Model reasoning leaks into customer files, for example "Wait, the prompt
  says".

### Outside research

Records are uncommitted in the shared checkout under
`/home/username/loop-engine/artifacts/harness-source-research-2026-09-23`.
Their third-party bytes stay in `/home/username/.le-codex-research-cache`.

- Licence fields under-report restrictions that the fetched bytes show. Four
  `anthropics/skills` records say `unknown` while their files say
  "Proprietary", and some plugin manifests declare non-commercial or
  proprietary terms while the record shows none or a permissive licence.
  Licences are verified for 0 of 4,000 records.
- The lists repeat items: ten plugin records are one plugin (`ecc`), 20
  consecutive contract records come from one vendor, and 22 skill records are
  named `skills`.
- 509 of the 1,000 plugins ship hooks. No tool list was observed for any of
  the 1,000 protocol server records, and 999 of the 1,000 contracts have no
  upstream revision.
- Useful leads: the Agent Permission Policy schema, after its revision is
  pinned and its licence confirmed, and `codebase-design` as inspiration for
  an original method.

### Checked again while writing this record

These findings were observed again on September 24, 2026, by reading the
files or by running a scratch copy. The other findings are reported by the
review groups and were not repeated.

- `render_secret_reference_connections` wrote a 40-character token-shaped
  value into its Codex output as `bearer_token_env_var`, under a
  `[server."weather_service"]` table, and refused the server id `infra` as
  `non_finite_number`.
- The example of `build_permission_scoped_lexical_index` returned
  `INTERNAL_ERROR` with the message "unhashable type: 'list'".
- In `plan_workspace_file_transitions`, the entry point is a function whose
  only statement calls itself.
- The overnight file `boolean-classification-agent-coordination.md` pins
  `model: gemma-4-coding-abliterated` and lists three CodeGraph tools, and
  `person-name-aggregation-project-management.md` routes
  `delete-person <person_name>`.
- The fetched `docx` skill declares "license: Proprietary. LICENSE.txt has
  complete terms".
- The overnight matrix gives all 29,625 ideas the occupation "Chief
  Executives", and all 775 candidates of the snapshot are aggregation ideas.
- Line 115 of `render_focused_task_context` calls `json.dumps` with
  `ensure_ascii=True`.

## Units that must never be served

Library units:

| Unit | Path | Reason |
|---|---|---|
| `render_secret_reference_connections` | `artifacts/native-blocks-batch-2026-09-24/pending-panel-batch/prepared-batch/packages/render_secret_reference_connections` | Its safety claim is false: a token-shaped value is accepted and written into the configuration. Both outputs are wrong: Codex gets a `[server."id"]` table instead of `[mcp_servers.<id>]`, and the Claude Code header sits under `env`, so no token is sent. It builds TOML from strings, which breaks on a quote. The configuration it renders turns on network and secret use that its declared effects do not name. It passed every native precheck. |
| `boolean-classification-agent-coordination.md` | overnight `lane-tactical-gemma4/` | Pins `model: gemma-4-coding-abliterated`, lists the operator's own CodeGraph tools, and holds no usable method. |
| `geolocation-classification-agent-coordination.md` | overnight `lane-tactical-gemma4/` | Grants web fetch, edit, write and shell tools plus 11 CodeGraph tools, under the same model pin, for a classification task that needs none of them. Found outside the sample. |
| `string-classification-agent-coordination.md` | overnight `lane-tactical-gemma4/` | The same grants under the same model pin, and a body about building design, not its task. Found outside the sample. |
| `person-name-aggregation-project-management.md` | overnight `lane-ollama-gpt-oss-20b/` | A routing table sends `delete-person <person_name>` to a delete folder: a destructive effect on personal data, hidden in prose, with no authority, confirmation or declared effect. Found outside the sample. |

Until they are regenerated without model pins or operator tool names, all 35
Tactical-lane subagent files that carry both `model:` and `tools:` stay in
quarantine.

Outside research records (group 2):

| Record | Rank in its list | Reason |
|---|---|---|
| `docx` from `anthropics/skills` | skills 508 | The fetched `SKILL.md` says "license: Proprietary"; the record says unknown. It also runs deleting commands. |
| `content-repurposing` from `101-skills/superpowers` | skills 999 | Unknown rights, probably republished material. It pre-authorizes every `belt` command, runs paid generation and publishes a post with an invented claim. |
| `academic-research-skills` | plugins 315 | The manifest declares `CC-BY-NC-4.0`, a non-commercial licence, and the plugin ships hooks and agents. |
| Interzoid City Data Standardization | contracts 342 | Proprietary terms; the key travels in the address as a query parameter; every call spends credits. |
| `io.github.sgx-labs/same` | tools 47 | Business Source License 1.1 (`BSL-1.1`), whose additional use grant nobody has read; it reads a notes folder and writes persistent memory. |

Group 2 also blocks 47 more research records until their terms are read: the
`anthropics/skills` records `pptx`, `pdf` and `xlsx` (ranks 506, 507 and 515)
and 13 more records of that repository with their own terms; nine
`anthropics/claude-code` records (skill ranks 789 to 795, 936 and 937);
`nab` (49), `claude-mem-cowork` (424) and `mcos-control` (923); and the 19
other Interzoid records (contract ranks 343 to 361). The code of the servers
under the GNU Affero General Public License or the GNU General Public License
(plugins 56 and 795; tools 19, 32, 33, 97 and 104) must not be bundled.

## Defects that repeat across sources

- **Prechecks do not run anything.** The native prechecks check licence,
  format, safety, effects, secrets and duplicates, but run no test, example or
  first command. The wave 5 `check_package.py` does run tests, in a sandbox
  with no network.
- **Delivered text promises what the code does not do,** most often refusals
  of duplicate keys, non-finite numbers and unknown identifiers.
- **Generation leftovers reach customers:** "the prompt says" comments, an
  implementation brief as `AGENTS.md`, and the generator's own vocabulary
  rules inside a hook's `AGENTS.md`.
- **Missing end rules.** Many bodies have no done section and no stop heading,
  and "First action" often describes the tool's inside instead of the model's
  first command.
- **Wrong native formats:** Claude Code hook settings, Codex server tables,
  front matter that is missing or names another folder, OpenCode agent keys
  and plugin roots.
- **Placement collisions.** Packages that ship a root `AGENTS.md`,
  `CLAUDE.md` or `.claude/settings.json` are safe only in a fresh step working
  directory. Merged into a customer's repository, they would overwrite the
  customer's own files.
- **Internal vocabulary and internal topics reach customers,** such as
  `node_assignment/v3`, `node_context.md`, a hard dependency on
  `.baltor/step/task.json`, and tools that serve Baltor's own infrastructure.
- **Rights are incomplete.** 89 first-party units have no customer licence,
  the Tactical packages declare MIT without a `LICENSE` file, the licence
  precheck compares only the declared text, and no producing model has its
  output-use terms recorded. Groups 1 and 3 found no copied outside text in
  the units they read.
- **Committed bytes differ from checked bytes** in the 19 refused wave 5
  packages, and some review notes cite evidence that was never committed.

## Facts that disagree

- **Occupations.** The
  [overnight batch handoff](../context/SESSION-HANDOFF-2026-09-24-OVERNIGHT-BATCH.md)
  says that the active matrix rotates 175 occupations. The matrix file
  `matrix-10k.json`, read for this record, gives all 29,625 ideas the
  occupation "Chief Executives". The matrix does hold 36 operations, 35 data
  types and 25 use cases; the batch's selection order put every candidate of
  the snapshot in one operation.
- **The call ceiling.** The batch status record reported 548 calls at the
  snapshot, while the journal holds 1,123 call events since 04:50:01. On
  recovery, the supervisor (`_recover` in `tools/overnight_candidate_batch.py`)
  replays outcomes and reassignments but not calls, so each new supervisor
  process counts calls from zero. The journal shows the counter restarting at
  04:52:42 and at 07:46:10, when the 10,000-idea run began. Inferred from the
  code, not observed: a later restart by the watchdog would start the
  12,000-call ceiling again.
- **Tactical verdicts.** Groups 1 and 3 disagree on 5 of the 10 Tactical
  units, as described above.
- **The kimi-k3 model.** The review panel keeps its `kimi-k3` reviewer
  switched off, because the repository's model route policy refuses that
  model. The overnight batch runs a `kimi-k3` lane through OpenCode, outside
  that route policy. The lane wrote 3 candidates before it was marked
  degraded.

## What blocks approval today

The review panel in [`tools/candidate_review`](../../tools/candidate_review/README.md)
decides one candidate at a time. Its rule is the owner's rule of September
22, 2026: at least three approving reviewers from at least three model
families, none of them the family that produced the item, and any rejection
keeps the item a candidate. Its declared reviewers are these.

| Reviewer | Family | State on September 24, 2026 |
|---|---|---|
| Seven Ollama Cloud models: `deepseek-v4-pro:0813`, `qwen3.5:397b`, `minimax-m3`, `kimi-k2.6`, `glm-5.3`, `mistral-large-3:675b` and `gpt-oss:120b` | deepseek, alibaba, minimax, moonshot, zhipu, mistral and openai | Stopped. The weekly allowance is spent, and a spent allowance stops every reviewer that shares it. |
| `kimi-k3` through Ollama Cloud | moonshot | Switched off, because the route policy refuses the model. |
| The Codex command line (`gpt-6-sol`) | openai | Excluded. Its output protocol does not report the answering model, and the panel never substitutes the requested model for a missing reported one. |
| The Claude Code command line in bare mode | anthropic | No key. Bare mode reads only `ANTHROPIC_API_KEY`, which is not set where this record was written; the September 22 probe returned `authentication_unavailable`. |

The evidence is in the
[Tactical blocks batch record](../../artifacts/native-blocks-batch-2026-09-24/README.md).
At 12:07:55 the provider refused a probe with HTTP 429, saying that the weekly
usage limit was reached, and gave no retry time. At 12:41:52 the panel
put the seven passing Tactical candidates to review; its one call was refused
with `usage_limit_reached`, so it recorded no verdict and 7 items stayed
`panel_incomplete`. The five Ollama lanes of the overnight batch were marked
degraded between 12:25:46 and 13:17:52 after five failures in a row; that the
spent allowance caused this is inferred, not recorded.

So no set of reviewers can reach three families today. The Claude Code
reviewer, even with a key, is one family, and it can never count for wave 5 or
the starter catalogue items, which Claude Code produced. Buying Ollama credits
would be spending beyond the recorded allowance, which the
[authority section](../../AGENTS.md#commit-push-and-release-authority)
reserves for the owner.

Two more blocks stand behind the panel. The 89 first-party units of waves 1
to 4 and the pilots have no declared customer licence, and the licence
precheck accepts only a declared licence from its list, so they would be
refused before any reviewer is asked (inferred from the panel settings, not
run). And the 8 pending Tactical packages all carry a stricter verdict of weak
or must not serve.

The [September 24 session handoff](../context/SESSION-HANDOFF-2026-09-24.md)
names a separate line of work on review throughput, in
`/home/username/.le-review-throughput-20260924`: the three-family panel,
batching and the Tactical server. This record describes the state before that
work lands.

## The path from 43 served items to the 10,000 milestone

The milestone in S-6.40 is 10,000 approved, searchable and retrievable
distinct packages, counted only from active release records and exact-byte
review records. The order below is engineering's decision, with the reason
and the measure for each step. Steps 1, 2, 4 and 5 need no model call. Step 3
needs producer calls, which the Tactical endpoint still answers. Step 6 needs
reviewer allowance.

1. **Keep the must-not-serve units out of every batch and source pack.**
   Leave `render_secret_reference_connections` out of the next panel request,
   keep the 35 pinned Tactical-lane subagent files in quarantine, and add the
   47 blocked research records and the 5 must-not-serve records to the
   research collectors' block list. Reason: these are rights or safety
   defects that no panel verdict can repair.
2. **Add execution checks before any panel call.** Extend the native precheck
   profile so that it runs each package's own tests, documented first command,
   examples and verification cases in a sandbox with no network, as the wave 5
   `check_package.py` already does; ties every promised refusal to a
   known-wrong case; and checks native formats for each harness. Reason: 3 of
   the 8 pending Tactical packages passed every native precheck and fail their
   own tests, and 9 of the 12 sampled Ollama wave packages have a failing
   test, a malformed case file or a wrong example.
3. **Hold and repair the pending Tactical batch.** Regenerate
   `plan_workspace_file_transitions`, `build_permission_scoped_lexical_index`
   and `validate_focused_attempt_handoff`. Repair the examples and the missing
   guards of `assemble_bounded_instruction_sections`,
   `check_tabular_transformation_invariants`, `query_codegraph_change_impact`
   and `resolve_exact_package_dependency_closure`. Rebuild
   `render_secret_reference_connections` from the product's published client
   recipes. Reason: panel calls are the scarcest resource, and these eight
   would spend them on known defects.
4. **Repair the overnight generator before it spends more calls.** Load the
   real occupations, spread the operations, write `<name>/SKILL.md` folders,
   drop `license:` from the front matter, require steps, a first action, an
   end rule and 150 to 600 words, refuse model pins and the operator's tool
   names, and replay call events on recovery so that the ceiling bounds the
   whole batch. Reason: at the snapshot every candidate is one operation for
   one occupation, and the sample found no strong unit among 12.
5. **Complete the rights records before review.** The 80 skills of waves 1 to
   4 wait for a rights review, and the 9 pilots record a pending customer
   licence. These files are already committed under the repository's MIT
   licence, so engineering records MIT as their declared licence when their
   rights review runs; different terms for library bodies would be a legal
   commitment, which stays with the owner. Add `LICENSE` files to the Tactical
   packages, and record the output-use terms of each producing model beside
   its packages. Reason: the licence precheck refuses a unit without a
   declared licence.
6. **Review in order of expected yield when reviewer allowance returns.**
   First the 19 strong units of this sample that are not yet served (7 of wave
   5, 9 of waves 1 to 4 and 3 Ollama wave drafts), then the other wave 5
   packages that pass the new execution checks, then repaired units. In
   parallel, qualify a Codex output that reports the answering model, so that
   the openai family can count through the Codex command line too. Reason:
   the only panel approval rate measured so far is 0 of 30, on starter bodies,
   and the strongest units measure the rate at the lowest cost.
7. **Publish approved units through catalogue releases, and measure serving
   before the count passes what has been measured.** Catalogue releases
   publish without a redeploy since Fly release 17. The records read here hold
   a local 100,000-item measurement, in which one Machine broke on memory,
   disk, a 65-second swap and search speed, and no 10,000-item measurement.
   Reason: approved units help no customer until the service can hold and
   search them.
8. **Size every later batch from measured yield.** Choose the size of each
   generation batch from the measured execution pass rate and panel approval
   rate for each lane and producer family, and merge relabelled variants into
   one method with facets, as S-6.40 requires. Reason: review, not
   generation, limits the count, as the overnight batch handoff also records.

Measured rates that exist:

| Stage | Measured | Record |
|---|---|---|
| Overnight generation | 1,123 calls from 04:50:01 to 13:55:54 wrote 775 candidates; 72 ideas failed (47 on shape, 25 on the provider) | journal snapshot in `inventory.json` |
| Overnight generation by lane | Tactical `gemma-4-coding-abliterated`: 595 calls, 366 candidates, 42 shape failures. Ollama Cloud: `gpt-oss:20b` 169 calls and 133 candidates, `gemma4:31b` 162 and 135, `glm-5.3-flash` 152 and 135, `nemotron-3-nano:30b` 25 and 3, `kimi-k3` 20 and 3 | the same journal snapshot |
| Ollama wave generation | 81 dispatches, 53 prepared drafts | `inventory.json` |
| Tactical blocks generation | 27 of 40 calls, 19 prepared versions of 10 methods | the Tactical blocks batch record |
| Tactical first batch | 20 calls, 0 units | `inventory.json` |
| Wave 5 prechecks | 56 of 75 passed | `precheck-all-20260924T114954425867Z.json` |
| Native prechecks, pending Tactical batch | 8 of 8 passed; 3 of those 8 fail their own tests | `sampled-review-1.json` |
| Sampled engineering review | of 96 library units: 26 strong, 36 usable with repair, 32 weak, 2 must not serve | `sampled-review-1.json` |
| Starter catalogue review, September 21 | 43 of 49 approved by all three reviewers, 6 rejected | the starter catalogue `reviews.json` |
| Panel pilot, September 22 | 0 of 30 approved; 91 calls; 234.5 items an hour with three at a time; about 33,600 tokens per item | [pilot record](../../artifacts/candidate-review-pilot-2026-09-22/README.md) |
| Native panel attempt, September 24 | 1 call, refused by the spent allowance; 0 verdicts | `review-native-profile/review-panel-attempt-1.json` |

Arithmetic from the pilot's rates, not a forecast: 10,000 approvals need at
least 10,000 panel reviews, which would take about 336 million tokens and 43
hours if every reviewed unit were approved.

Unknowns, kept unknown:

- When the Ollama Cloud weekly allowance resets, and how many reviewer calls
  one week allows. The provider's refusal gave no retry time.
- The panel approval rate for native packages and for overnight candidates.
  No verdict exists for either.
- The execution pass rate of every source except wave 5.
- How many distinct methods the overnight candidates hold once relabelled
  variants are merged.
- The output-use terms of each producing model.
- Whether any candidate helps a customer finish a task. No record of native
  use or benefit exists for any of them.

# Engines behind fixed edges: implementation plan

Kind: dated research record. The work packages below are a design proposal; the roadmap remains the only task authority, and each package's status is recorded there under S-6.30, S-6.31, S-6.32 and the D-19 steps.

Kind: implementation plan, a set of independent work packages for parallel
agents.
Date: September 22, 2026.
Status: proposed. Nothing here is built.
Design: `ENGINE-ARCHITECTURE.md` beside this file. Section numbers below such
as "architecture 8.3" point into it.
Roadmap authority: delivery package D-19, "Engines behind fixed edges for
every functional component", with seven steps: S-6.30 (the shared
framework), S-6.31 (the harness executor slot), S-6.32 (hosted search as an
engine slot), S-6.40 (the library ingestion worker behind an ingestion engine
slot), S-6.41 (harness run records for self-improvement), S-6.42 (a fresh,
independent harness instance for every step) and S-6.60 (a layer before every
model call that decides one model or several). S-6.40 to S-6.42 and four
S-6.30 verification items (engine preferences sent by a harness or a Loop,
slots nested at every level, one folder per functional component with one
module per engine, the earlier custom loop-node engine kept restorable) were
added at `4249eca`, after the first draft of this plan; S-6.60 and new
verification items for S-6.31, S-6.40 and S-6.42 were added at `0f1c690`,
while this revision was being checked. This revision covers all of them. The
adoption packages for account email, record store, model routes, identity and
billing are recorded by the registration desk as new steps under D-19 when
they start; this plan is not a second task list.
Source state: first drafted at `c96b546`; checked again at `main` `230c91e`
(September 22, afternoon), where the engine-side source is unchanged and the
service side changed only in checks, web pages, capacity checks, the
conformance report, the architecture map and the retired README title in
`terminology.yaml`. The repository was read, never changed, to write this
plan.

Identifiers. Package identifiers in this plan (F1 to F14, X1 to X11, R1, R2,
E1, D1, D2, M1 to M3, I1, B1, V1, C1, P1, W1, N1, H1, L1 to L4) are local to
this plan. The inventories use other identifiers that look alike: engine-side
records E1 to E26, service records C1 to C19, and service findings F1 to F12.
This plan always writes "finding F1" or "record C1" for those, and a bare
identifier always means a package.

## 1. Rules that bind every package

1. **The working cycle** of the takeover checkpoint: write the check for the
   known-wrong case first, see it fail, repair, add the removed-guard control
   (a mutant that deletes the guard must make a named check fail), run the
   owning suites, then the full continuous integration commands on an export
   of the exact tree (section 11), lint the full documentation scope as
   `AGENTS.md` requires (not only the files you touched), and hand the package
   to the registration desk. Never weaken a surviving check to
   make a package land. When a check fails, decide first whether the work, the
   check or the environment is wrong, and record why.
2. **One package, one short-lived branch.** Each package works in its own git
   worktree on a branch from `main`, and is merged into `main` as soon as it
   is accepted; the branch and worktree are then removed. The owner's
   direction of September 22 (09:12) is that only `main` and the snapshot
   branch `checkpoint/full-capability-2026-09-21` survive, and that all work
   is merged into `main`.
3. **Own your files.** A package changes only the files listed as its own. It
   never edits a shared registration file (section 2) and never edits a file
   another package in the same wave owns. It writes a registration request
   instead.
4. **Keep the edges.** Each package lists the edge contracts it must not
   change. A package that creates or versions an edge says so explicitly;
   after it merges, that edge is frozen for every later package.
5. **Repository rules.** The only operational runtime type is `Loop`; no class
   name ends in `Node`; no new registry, store, event family or source of
   truth; every boundary typed and versioned, refusing unsupported versions
   before effects; discovery effect-free; permissions never from mode or
   configuration; no learned heuristic before the declared run count; modules
   at most 800 lines; public functions at most nine parameters; every new
   module exposes `self_test()`; no acronyms in new names or titles (spell out
   "agent client protocol", never "acp"). New modules go in the folder of
   their functional component, one module per engine (architecture 7.8): the
   framework in `core/engines/`, step execution in `core/step_execution/`;
   engines of families that are still flat keep their family prefix until
   that family's folder move (packages L1 to L4). No word that the
   `terminology.yaml` vocabulary marks `retired` appears in code, checks,
   known-wrong fixtures or generated pages: write Spawned Loop and spawning
   Loop, Starting Loop, Run History, record, exit condition and select next
   action, the replacements that vocabulary names. The conformance gate and
   the documentation job both refuse the retired words, the documentation job
   anywhere in `docs/` outside the dated evidence folders. Direct resource access has a zero baseline: a
   receiver named `retriever` or `store` calling `search`, `serve` or
   `records` outside a Loop envelope fails `--conformance`, so new code
   reaches search and stores through their envelopes.
6. **Authority.** No model calls, live charges or public registration. No
   destructive provider operation (application, volume, domain record, name
   server delegation, provider resource, secret). Service changes reach the
   pilot only through a guarded release run by the registration desk. Decide
   engineering questions, record the reason, move on.
7. **Evidence labels.** Every package's hand-off report separates observed,
   inferred, missing and disputed facts, names the exact commands run and
   their counts, and never reports a `local_contract` proof as more.
8. **Search before building.** Before writing an engine or a component, the
   package searches for existing projects, repositories, designs and papers
   that already provide it, and records the decision (reuse, adapt or build,
   with its sources) in its hand-off report, as `AGENTS.md` and roadmap D-19
   require. The four prior-art notes of September 22 cover the framework,
   the executor slot, search and the service pieces; a package outside them
   does its own search.

## 2. The registration desk and the shared files

One continuous package, the registration desk, is the only writer of the
shared files. It merges accepted packages into `main` one at a time, in
dependency order, applying each package's registration request in the same
commit, then runs the full continuous integration commands on an export of
the result, commits, pushes and confirms the continuous integration run.

Shared files, written only by the registration desk:

| File | What packages request |
|---|---|
| `src/loop_engine/_self_test.py` | Suites to add to `_FOLDED_SUBMODULE_TESTS` |
| `src/loop_engine/architecture_map.py` | Modules to add to `MODULE_MAP` |
| `src/loop_engine/forbidden_paths.json` | Suite exception removals, dynamic import allowances with reasons, network or subprocess allowances with reasons |
| `src/loop_engine/architecture_conformance.json`, `src/loop_engine/ARCHITECTURE-MAP.md` | Regenerated, never hand-edited |
| `terminology.yaml` and its verified installed projection `src/loop_engine/data/terminology.yaml` (`semantic_conformance` refuses a difference, so both change in one commit) | New terms: engine slot, engine (of an engine slot) with its qualification rule, engine kind, engine descriptor, engine installation, executor profile, engine preference, nested slot. The Loop Engine definition stays as the owner's text has it (architecture section 2) |
| `docs/architecture/SEMANTIC-AMBIGUITY-REGISTER.yaml` | The entry for the word "engine" and its two uses |
| `architecture.yaml` and its installed copy `src/loop_engine/data/architecture.yaml` | New machine-readable invariants; the two copies change together |
| `src/loop_engine/data/component_folder_map.yaml` | One row for each new component folder: `core/engines`, `core/step_execution`, `core/library_ingestion`, `core/model_call_strategy` |
| `devtools/hardcoding-allowlist.yaml` | New literals (record types, reason codes, raw event kinds) |
| `pyproject.toml` | Optional extras and pins |
| `.github/workflows/ci.yml` | New continuous integration steps or service containers |
| `AGENTS.md`, `docs/components/README.md`, `docs/components/COMPONENT-GUIDE-MAP.yaml` | Short pointers to the generated engine pages |
| `docs/roadmap/roadmap.yaml` and the generated `docs/roadmap/CONTINUATION-STATUS.md`, `docs/roadmap/DEVELOPMENT-TRACKER.md`, `docs/roadmap/development-tracker.json` | Step status and evidence |
| `src/loop_engine/data/engine_slots.yaml` (after F2 merges) | Slot `implementation_state` changes and shrinking `known_direct_construction_sites` baselines |
| `src/loop_engine/data/component_interactions.yaml` (after F2 merges) | Interaction rows moving from `candidate` to `active` |
| `src/loop_engine/core/boundary_registry.py` (after F3 merges) | New boundary rows and their ontology bindings, applied in the same commit as the envelope they name |
| `src/loop_engine/data/harness_recipes.yaml` (after X1 merges) | New recipe records and their qualification references |
| `docs/components/engines/` (after F13 merges) | Regenerated with `tools/build_engine_pages.py` whenever a desk commit changes the catalogues; never hand-edited |

A registration request is a YAML block at the end of the package's hand-off
report with exact entries. To run the full self-test before hand-off, a
package agent may apply its own request in its private worktree, but never
commits those edits.

## 3. Concurrent work and the entry gate G0

The September 22 consolidation (roadmap S-6.29) is running in detached
worktrees that edit files this plan also needs:

Observed when this revision was checked (September 22, afternoon); none of
the four is merged into `main`, and the first draft's statement that r2 and
r3 had no changes is out of date:

| Worktree (head) | Files it changes that matter here |
|---|---|
| a detached consolidation worktree (`459a809` plus uncommitted edits; restores the observability wiring lost in merge `8892677`, finding F1) | `core/service_runtime/http.py`, `http_checks.py`, `http_entrypoint.py`, `observability.py`, `observability_checks.py`, `runtime.py`, `promotion_checks.py`, `web_pages.py`, `forbidden_paths.json`, `architecture_map.py`, `service_cli.py`, `cli_help.py`, `tools/check_fly_service_container.py`, `tools/test_fly_deployment.py`, `docs/components/service-runtime/README.md` |
| a detached consolidation worktree (`98ada33`; payment customer path, waiting list, catalogue browser) | `core/service_runtime/http.py`, `http_entrypoint.py`, `http_boundary_checks.py`, `http_checks.py`, `runtime.py`, `runtime_checks.py`, `records.py`, `refusals.py`, `request_limits.py`, `stripe_sessions.py` and its checks, `web_pages.py`, `waitlist.py` (new), the web assets including `service.js`, `tools/check_hosted_website.mjs`, `tools/check_service_workspace.mjs`, `architecture_map.py`, `forbidden_paths.json`, `roadmap.yaml` |
| a detached consolidation worktree (`aef77e6`) | `.github/workflows/fly-pilot.yml`, `devtools/hardcoding-allowlist.yaml`, `docs/components/COMPONENT-GUIDE-MAP.yaml`, `docs/components/README.md`, `docs/components/service-runtime/README.md`, `tools/check_client_journey_in_containers.py` and its test, `tools/check_component_guides.py` and its test, `tools/check_fly_service_container.py`, `tools/test_fly_deployment.py`, `tools/test_search_quality.py` |
| a detached consolidation worktree (`247ee0e`) | `AGENTS.md`, `ASTRA.md`, `CLAUDE.md`, `docs/README.md`, `docs/RECORDS-INDEX.md`, the start-here and handoff documents, `tools/test_context_routes.py` |

**Gate G0** opens when the consolidation has merged into `main`, `main` is
pushed, and its continuous integration run passed. Every package that changes
a file under `core/service_runtime/`, or `service_cli.py`, `cli_help.py` or
`__main__.py`, starts only after G0. Engine-side packages do not wait. The
registration desk holds its edits of `AGENTS.md`, `docs/components/README.md`
and `docs/components/COMPONENT-GUIDE-MAP.yaml` until G0, because r2 and r3
rewrite them. Its edits of `devtools/hardcoding-allowlist.yaml`,
`forbidden_paths.json` and `architecture_map.py`, which every package needs,
go ahead; when the consolidation merges, the line-survival check of S-6.29
runs on those three files so that neither side's lines are silently lost.
Package R1 also edits `tools/check_client_journey_in_containers.py`, which r2
changes, so R1 starts only after G0, as every service package does.

## 4. Dependencies and waves

```text
Package dependency graph (an arrow reads "must merge before")
├── Framework (S-6.30)
│   ├── F1 Engine records ─────────────┬─> F3, F4, F5, F8, F9, F10, F12, X3, X5
│   ├── F2 Slot catalogue and edges ───┼─> F3, F7, F8, F12, F13
│   ├── F3 Selection procedure ────────┴─> F4 (merge order), F5, F6, F9, F12, X3, X5, R1, D1
│   ├── F4 Evidence records and rankers ─> F6, X10
│   ├── F5 Envelope measurement ─────────> F6, X3, M1
│   ├── F6 Evidence reader and compiler ─> V1
│   ├── F7 Conformance gate
│   ├── F8 Engine-side settings section ─> F12, X5, M1
│   ├── F9 Service host engine table (after G0) ─> F12, R1, E1, D1, I1, B1, P1
│   ├── F10 Entry point discovery
│   ├── F11 Guards for live dependencies ─> F3 (merge order: both edit core/event_vocabulary.py),
│   │                                      F5 (merge order, only if F5 must edit core/capability_directory.py)
│   ├── F12 Engine commands, read only (after G0) ─> F14
│   └── F13 Generated engine slot pages
├── Harness executor slot (S-6.31)
│   ├── X1 Harness recipe catalogue ─────> X4, X9
│   ├── X2 Adapter contract and envelope clock ─> X3, X5
│   ├── X3 Step edge and step attempt envelope ─> X4, X5
│   ├── X4 Agent Client Protocol engine, OpenCode first ─> X6, X7, C1
│   ├── X5 Step executor slot adoption ──> X6, M2, X8, X9, X10, X11
│   ├── X6 Phase 2 acceptance run
│   └── X11 A fresh instance for every step, per harness (S-6.42; after X4 and X5)
├── Hosted search (S-6.32): R1 ─> R2, V1, P1
├── Account email: E1          (after F9)
├── Record store: D1 ─> D2     (after F9 and F3)
├── Model provider routes: M1 ─> M2 (after F5 and F8; M2 also after X5)
├── Identity: I1               (after F9)
├── Billing: B1                (after F9 and G0)
├── Library ingestion (S-6.40): N1  (after F1 and F3)
├── Harness run records (S-6.41): H1 (after F6 and X3)
├── Model call strategy (S-6.60): M3 (after M1 and F3)
├── Folder moves of flat families: L1 to L4 (each after the last package that edits
│   that family's files has merged)
└── Later: V1, D2, X7, X8, X9, X10, X11, C1, P1, F14, W1, N1, H1, M3, L1 to L4
```

Waves, each package in a wave touching files no other package of that wave
touches:

| Wave | Packages | Starts when |
|---|---|---|
| A | F1, F2, F11, X1, X2 | Now |
| B | F3, F4, F7, F8, F10, F13 | F1 and F2 merged (F3 also after F11, which edits `core/event_vocabulary.py`; F4 merges after F3) |
| C | F5, X3, F6 | F3 merged (X3 also after X2 and F5; F6 after F4 and F5; F5 after F11 only in the case noted in its section) |
| D | F9, then F12 | G0 open and F3 merged |
| E | X4, X5, then X6 | X1, X3 (X4); F8, X2, X3 (X5) |
| F | R1, E1, D1, I1, B1, M1, then R2, M2 | F9 merged (M1 after F5 and F8) |
| G | V1, D2, X7, X8, X9, X10, X11, C1, P1, F14, W1, N1, H1, M3, L1 to L4 | As marked. Two packages of this wave that edit one file run one after the other: C1 before X8 and X9 (the confinement code in `core/harness_process.py` and `core/step_execution/session_process.py`); P1 and V1 one after the other (both reach the service transport); each L package alone for its family's files |

Critical path to phase 2 of the harness-first plan: F1 and F2, then F3, then
F5 and X3 (X2 in parallel from day one), then X5, then X6. X1 and X2 can start
immediately because they depend on nothing in the framework.

## 5. Package summary

| Id | Package | Roadmap | Depends on | Owns (principal files) |
|---|---|---|---|---|
| F1 | Engine records | S-6.30 | none | `core/engines/records.py`, `core/engines/selection_records.py` |
| F2 | Engine slot catalogue and edge rows | S-6.30 | none | `data/engine_slots.yaml`, `core/engines/slots.py`, `core/component_contracts.py`, `data/component_interactions.yaml` |
| F3 | Selection procedure and decision recording | S-6.30 | F1, F2 | `core/engines/selection.py`, `core/configuration_preferences.py`, `core/event_vocabulary.py`, `core/run_history.py`, `core/boundary_registry.py` |
| F4 | Evidence records, statistics and rankers | S-6.30 | F1; merges after F3 | `core/engines/evidence_records.py`, `core/engines/evidence_statistics.py`, `core/engines/evidence_ranking.py` |
| F5 | Envelope measurement | S-6.30 | F1, F3 (after F11 only if it must edit `core/capability_directory.py`) | `core/operation_cost_records.py`, `core/operation_cost_capture.py`, `core/model_gateway.py`, `core/decisions/gateway.py`, `core/engines/measurement.py` |
| F6 | Evidence reader and compiler | S-6.30 | F4, F5 | `core/engines/evidence_reader.py`, `core/engines/evidence_compiler.py` |
| F7 | Conformance gate | S-6.30 | F2 | `core/engines/conformance.py`, `_conformance_scan.py` |
| F8 | Engine-side settings section and projections | S-6.30 | F1, F2 | `core/settings_loader.py`, `core/runtime_settings.py`, `core/engines/settings.py` |
| F9 | Service host engine table | S-6.30 | G0, F1, F3 | `core/service_runtime/service_engines.py`, `service_engine_*.py`, `http_entrypoint.py` |
| F10 | Entry point discovery | S-6.30 | F1 | `core/engines/discovery.py` |
| F11 | Guards for live dependencies | S-6.30 | none | `core/live_dependency_checks.py`; fixes inside the re-collected modules only |
| F12 | Engine commands, read only | S-6.30 | G0, F1, F2, F3, F8, F9 | `engine_cli.py`, `__main__.py`, `cli_help.py` |
| F13 | Generated engine slot pages | S-6.30 | F2 | `tools/build_engine_pages.py`, `docs/components/engines/` |
| X1 | Harness recipe catalogue | S-6.31 | none | `data/harness_recipes.yaml`, `core/harness_recipes.py`, `core/harness_process.py`, `core/harness_process_relay.py`, the recipe modules |
| X2 | Adapter contract version and the envelope clock | S-6.31 | none | `core/external_harness.py`, `core/external_harness_adapters.py`, `core/harness_semantic.py`, `core/harness_configuration.py`, `core/opencode_harness_adapter.py` |
| X3 | Step edge records and step attempt envelope | S-6.31 | F1, F3, F5, X2 | `core/step_execution/records.py`, `core/step_execution/envelope.py` |
| X4 | Agent Client Protocol engine, OpenCode first | S-6.31 | X1, X3 | `core/step_execution/agent_client_protocol.py`, `core/step_execution/session_process.py` |
| X5 | Step executor slot adoption | S-6.31 | F1, F3, F8, X2, X3 | `core/step_execution/engines.py` |
| X6 | Phase 2 acceptance run | S-6.28, S-6.31 | X4, X5 | `tools/check_delegated_step.py`, a new evidence record |
| R1 | Hosted search as an engine slot | S-6.32 | F9, F2, F3 | `core/retrieval_engines.py`, `core/service_runtime/http.py`, `core/harness_intelligence_search.py`, `service_engine_search.py` |
| R2 | Second lexical and vector engines | S-6.32 | R1 | `core/retrieval_bm25s.py`, `core/retrieval.py`, `core/retrieval_backends.py`, `Dockerfile.service` |
| E1 | Account email slot | D-19 (new step) | F9 | `service_engine_account_email.py` |
| D1 | Record store slot | D-19 (new step), D-05 | F9, F3 | `catalog/record_store_engines.py`, `catalog/registry.py`, `catalog/conformance.py`, `service_engine_record_store.py`, `storage.py` |
| M1 | Model provider routes slot | D-19 (new step) | F5, F8 | `core/model_provider_engines.py`, `core/model_gateway.py`, `core/runtime_settings.py`, `core/model_routes.py` |
| M2 | Overnight runner through the slots | D-19, D-07 | M1, X5 | `overnight_cli.py`, `code_nodes/overnight_night.py` |
| I1 | Identity slot | D-19 (new step) | F9 | `service_engine_identity.py`, `browser_identity.py` |
| B1 | Billing slot | D-19 (new step) | F9, G0 | `service_engine_billing.py` |
| Later | V1, D2, X7, X8, X9, X10, X11, C1, P1, F14, W1, N1, H1, M3, L1 to L4 | D-19 (S-6.40, S-6.41, S-6.42, S-6.60), D-05, D-12 | See section 10 | See section 10 |

### 5.1 The folder skeletons, before wave A

Two packages of wave A (F1, F2) create modules in `core/engines/`, and three
later packages (X3, X4, X5) create modules in `core/step_execution/`. So that
no two packages of one wave create the same file, the registration desk
commits both folder skeletons before wave A starts, and no package edits them
afterwards: `core/engines/__init__.py` and `core/engines/README.md`,
`core/step_execution/__init__.py` and `core/step_execution/README.md`, one row
for each folder in `src/loop_engine/data/component_folder_map.yaml`, and the
keys `core.engines` and `core.step_execution` (each with `__init__`) in
`MODULE_MAP`. Each README states the folder's kind, its naming rule (one
module per engine, factory tables define no engine) and its version rule.
`core/library_ingestion/` and `core/model_call_strategy/` get the same
skeleton when packages N1 and M3 start (architecture 7.8).

## 6. Framework packages (S-6.30)

Paths below are relative to `src/loop_engine/` unless they start with
`tools/`, `docs/` or another top-level folder.

### F1. Engine records

- **Goal.** The typed records every other package uses, with the exact fields
  of architecture 6.2 to 6.6: `engine_descriptor/v1`,
  `engine_installation/v1`, `engine_slot_configuration/v1`,
  `engine_selection_policy/v1`, `engine_selection_override/v1`,
  `engine_selection_decision/v1`, `engine_qualification/v1`,
  `engine_retirement/v1`, `service_host_engines/v1` and
  `engine_bindings_report/v1`.
- **Create.** `core/engines/records.py` (descriptor, installation, slot
  configuration, qualification, retirement, service host block, bindings
  report); `core/engines/selection_records.py` (policy, override, decision);
  `core/engines/records_checks.py`.
- **Change.** Nothing. Reuse `canonical`, `digest`, `exact_text`,
  `exact_digest` and `ConfigurationFact` from `core/configuration_capabilities.py`
  without modifying that module.
- **Edges that must not change.** Every existing record. No existing module is
  edited.
- **Checks to add first, with their known-wrong cases.**
  - `every_engine_record_refuses_unknown_keys_and_unsupported_versions`
    [a policy with an extra key; `engine_selection_policy/v2` read by the v1
    parser]. Control `removed_unknown_key_refusal_is_detected`.
  - `every_slot_policy_states_an_initial_choice_and_ordered_fallbacks_or_an_explicit_no_fallback`
    [empty `fallbacks` with `no_fallback` false]. Control
    `removed_no_fallback_rule_is_detected`. (One name for one check: the
    architecture's section 17.1 uses the same name.)
  - `a_policy_lists_an_engine_once_and_never_a_retired_one` [an engine in both
    `initial` and `fallbacks`; a retired engine listed].
  - `ranking_policy_must_end_with_the_declared_order`
    [`engine_order: [evidence-ranker]` alone]. The reserved reference
    `declared-order` names a binding of the existing `ExistingOrderPreference`
    (which proposes `existing-selector-order@1.0.0`); no such binding exists
    today, so F1 defines the reserved reference and F3 creates the binding.
  - `descriptor_digest_moves_when_any_field_moves` [isolation changed from
    `os_sandbox` to `none` with the digest unchanged].
  - `decision_flags_are_constant` [a decision with
    `execution_authority_granted: true`, `task_accepted: true` or
    `model_call_performed_by_boundary: true`; the flag keeps the existing name
    that `configuration_preference_decision/v1` uses].
  - `selection_decision_records_every_rejection_reason_and_its_propensity`
    [a decision listing only the winner; a decision without propensity].
  - `qualification_binds_the_installation_digest` [a qualification for one
    installation accepted for another];
    `expired_qualification_becomes_unknown_and_ineligible` [a fact past
    `expires_at` still read as qualified].
  - `one_qualification_source_per_installation` [an `engine_qualification/v1`
    written for an installation that already has a
    `harness_project_qualification/v1`].
  - `an_override_records_its_source_kind_and_sender` [an
    `engine_selection_override/v1` without a source kind from the existing
    `ParameterSourceKind` vocabulary, or without its sender].
  - `a_nested_decision_names_its_parent` [a decision for a nested slot with an
    empty `parent_decision_digest`].
  - `records_round_trip_with_identical_digests` [a record whose digest changes
    after `to_dict` and `from_dict`].
- **Owning suites.** `core.engines.records_checks`; `core.configuration_capabilities`
  must still pass unchanged.
- **Acceptance.** Every record of the list exists with exactly the fields of
  the architecture; every refusal happens before any effect; each control
  fails when its guard is removed; no existing suite changes its count.
- **Registration request.** `MODULE_MAP["core.engines"]` += `records`,
  `selection_records`, `records_checks` (the key and `__init__` come from the
  folder skeleton, section 5.1); `_FOLDED_SUBMODULE_TESTS` +=
  `core.engines.records_checks`; terminology entries for engine slot, engine
  (of an engine slot) with its qualification rule, engine kind, engine
  descriptor, engine installation, executor profile, engine preference and
  nested slot, in both copies of `terminology.yaml`, with no change to the
  Loop Engine definition (architecture section 2); the "engine" entry of the
  semantic ambiguity register; hardcoding allowlist entries for the new record
  type strings.

### F2. Engine slot catalogue and edge rows

- **Goal.** The one index of every engine slot, joined by name to the
  boundary registry and the interaction catalogue (architecture 4.1, 7.2,
  7.3).
- **Create.** `data/engine_slots.yaml` (`engine_slot_catalog/v1`, one
  `engine_slot/v1` for every slot in architecture 5.2, 5.3 and 5.4, with
  `implementation_state` `active`, `candidate` or `planned`, a per-slot
  `evidence_minimum_floor` of 10 for per-attempt slots, and the
  `known_direct_construction_sites` baseline found by source search:
  `core/service_runtime/storage.py`, `core/service_runtime/http_entrypoint.py`,
  `core/service_runtime/http.py`, `core/retrieval.py` constructor strings,
  `overnight_cli.py`, and `record_cli.py` (the managed record command builds
  `SQLiteRecordStore` or `PackageJsonlStore` from a backend string); F7
  replaces this hand-found list with what its scanner finds on `main`). A slot
  record names its interaction rows and never restates their request and
  result versions; a planned slot whose envelope does not exist yet names the
  boundary row its first package will add and is reported as
  `planned_without_envelope`;
  `core/engines/slots.py` (the `engine_slot/v1` data class, the catalogue
  loader, the join validation, `slot_index_report()`);
  `core/engines/slot_checks.py`.
- **Change.** `core/component_contracts.py`: add `engine_slots.yaml` to the
  closed resource tuple of `load_component_resource`; grow
  `component_interactions_are_unique_and_typed` so it also requires exact
  `name/vN` contracts and known component kinds.
  `data/component_interactions.yaml`: one or more edge rows per slot, with
  `implementation_state: candidate` (the step edge row of architecture 7.3 is
  the template).
- **Edges that must not change.** The seven existing interaction rows and
  their record type `component_interaction_catalog/v1`; every boundary row
  (F2 does not edit `core/boundary_registry.py`; it imports it read-only).
- **Checks to add first.**
  - `every_engine_slot_names_registered_work_boundaries_or_a_release_reason`
    [a slot naming a misspelled boundary; an active or candidate run-time slot
    naming none; a planned slot without an envelope not reported as
    `planned_without_envelope`]. Control
    `removed_slot_boundary_join_is_detected`.
  - `every_engine_slot_edge_is_read_from_its_interaction_rows` [a slot record
    that carries its own copy of a request or result version].
  - `every_interaction_names_exact_versioned_contracts_and_known_components`
    [a row with a contract lacking `/vN`; an unknown producer kind].
  - `engine_slot_symbols_resolve_without_import`
    [`core.external_harness.NoSuchProtocol`], resolved through the existing
    `_mapped_symbol_exists`.
  - `every_active_engine_slot_conformance_suite_is_collected` [an active slot
    whose suite is listed in `suite_collection_exceptions`]. Control
    `removed_collected_suite_requirement_is_detected`.
  - `every_edge_contract_declares_an_unavailable_result` [a slot without one].
  - `every_slot_uses_the_closed_vocabularies` [selection mode `sometimes`;
    fallback ceiling `always`].
  - `release_slots_name_no_run_time_boundary_and_state_a_reason` [a release
    slot naming a work boundary; a release slot with an empty reason].
- **Owning suites.** `core.engines.slot_checks`, `core.component_contracts`,
  `core.boundary_registry` (unchanged).
- **Acceptance.** Every slot of the architecture's three tables is in the
  catalogue with every field; the joins validate; the seven existing rows are
  byte-identical; every new row is `candidate`; the control fails with the
  join removed.
- **Registration request.** Map the two new modules under the key
  `core.engines`; fold `core.engines.slot_checks`; allowlist the slot
  identifiers and state words.
  After F2 merges, `data/engine_slots.yaml` and
  `data/component_interactions.yaml` become desk-owned (section 2).

### F3. Selection procedure and decision recording

- **Goal.** The one effect-free selection procedure of architecture 8.2, run
  as a deterministic Practitioner Loop, with decisions recorded in existing
  event families.
- **Create.** `core/engines/selection.py`: `EngineSelectionRequest` (one frozen
  request object), `EngineBinding` (descriptor plus adapter),
  `select_engine`, `select_engine_as_loop`, `assess_engine_attempt`,
  `revalidate_binding`, `require_prior_decision(ledger, decision_digest)`,
  exact reuse keyed on every digest, the reserved `declared-order` binding of
  the existing `ExistingOrderPreference`, admission of engine preferences
  (a Loop override, or a harness preference admitted as source kind
  `intelligence_proposal`, architecture 8.4) and nested selection with its
  parent decision (architecture 4.6). `core/engines/selection_checks.py`,
  with fixture slots and fixture engines that raise if they are touched
  during discovery.
- **Change.**
  - `core/configuration_preferences.py`: a typed `InsufficientEvidence`
    subclass of `ConfigurationCapabilityError`, the fallback class
    `insufficient_evidence` in `MetaPreferencePolicy`, caught before the
    generic invalid-proposal branch; the decision encodes as
    `configuration_preference_decision/v2` only when that class appears.
  - `core/event_vocabulary.py`: the five raw kinds of architecture 9.1 in
    `_CANONICAL_EVENT_MAP`.
  - `core/run_history.py`: the same five kinds in the ledger to Run History
    mapping.
  - `core/boundary_registry.py`: the row "component engine selection"
    (binding `practitioner_loop`, envelope
    `core.engines.selection.select_engine_as_loop`, test
    `core.engines.selection.self_test`) with ontology
    `practitioner.code_execution@1.0.0`, relationships `starting` and
    `spawned_by`; `boundary_report()` gains an `engine_slots` section from
    `core.engines.slots.slot_index_report()`.
- **Edges that must not change.** `configuration_preference_decision/v1`
  whenever `insufficient_evidence` does not appear; the existing canonical
  families and Run History event types; the 87 existing boundary rows;
  `select_harness`, `assess_harness_attempt` and their records; the existing
  fallback classes of `MetaPreferencePolicy`.
- **Checks to add first.** From architecture 17.3 and 17.6:
  `selection_never_considers_an_engine_outside_the_installed_enabled_universe`,
  `a_narrower_source_can_reorder_but_never_widen`,
  `eligibility_precedes_ranking_and_ranking_cannot_restore_an_ineligible_engine`,
  `undeclared_engine_kind_is_ineligible`,
  `unsupported_edge_version_is_ineligible_before_dispatch` (zero adapter calls),
  `unavailable_unqualified_or_expired_engine_is_ineligible_by_default`,
  `mode_or_configuration_never_grants_engine_permission` (control),
  `missing_preemptive_limit_is_ineligible_under_a_preemptive_budget`,
  `unknown_cost_under_a_bounded_spending_budget_is_ineligible`,
  `selection_performs_no_probe_no_network_and_no_model_call`,
  `insufficient_evidence_is_recorded_as_a_fallback_not_an_engine_failure`,
  `every_selection_is_recorded_in_existing_event_families`,
  `a_decision_exists_before_every_dispatch` (control),
  `bound_engine_is_revalidated_at_use` (control),
  `exact_reuse_needs_every_digest_unchanged_and_no_expired_fact`,
  `a_pin_to_an_ineligible_engine_refuses_without_substitution`,
  `a_spawned_loop_cannot_widen_its_parents_override_authority`,
  `an_override_cannot_change_the_evaluator_or_start_a_comparison`,
  `fallback_only_on_declared_failure_kinds`,
  `fallback_carries_consumed_authority`,
  `uncertain_effect_or_accounting_blocks_fallback`,
  `host_policy_cannot_widen_the_slot_fallback_ceiling` (control),
  `an_open_breaker_is_an_expiring_availability_fact_not_a_hidden_retry`,
  `retired_engine_is_never_selected_even_when_listed` (control),
  `candidate_engine_is_refused_outside_a_declared_trial`,
  `deprecated_engine_cannot_be_the_initial_choice`,
  `archived_engine_refuses_with_its_replacement`,
  `qualification_grants_no_authority`,
  `descriptors_are_projections_of_native_declarations`,
  `descriptor_digest_moves_when_the_native_declaration_moves`,
  `factory_table_refuses_an_unknown_engine_kind` (on the fixture slot's
  table), and the three this revision added:
  `a_harness_preference_is_applied_only_within_its_authority` (control
  `removed_harness_preference_bound_is_detected`),
  `a_nested_selection_names_its_parent_decision_and_never_widens_it` and
  `engine_selection_needs_no_selection_to_start`. Each with the known-wrong
  case written in architecture section 17.
- **Owning suites.** `core.engines.selection_checks`,
  `core.configuration_preferences`, `core.run_history_checks` (vocabulary
  totality and coverage), `core.boundary_registry`, `core.harness_selection`
  and `core.harness_fallback` (unchanged).
- **Acceptance.** Fixture slots exercise every step of architecture 8.2,
  including all three selection modes and all three ceilings; every decision
  validates as `engine_selection_decision/v1`; the new boundary row has a
  collected test; the event projection stays total (the
  `unmapped_ledger_event_kind` detector passes); each control fails with its
  guard removed; every existing suite keeps its count.
- **Merge order.** After F11, which re-collects the parked suite of
  `core/event_vocabulary.py` before F3 edits that module.
- **Registration request.** Map and fold the new modules; allowlist the raw
  kinds and reason codes. After F3 merges, `core/boundary_registry.py`
  becomes desk-owned.

### F4. Evidence records, statistics and rankers

- **Goal.** The declared evidence rule and its two methods (architecture 8.5
  and 6.5), as ranking engines behind `MetaPreferencePolicy`.
- **Create.** `core/engines/evidence_records.py` (`engine_evidence_rule/v1`,
  `engine_trial_evidence/v1`, `engine_evidence_review/v1`,
  `engine_evidence_snapshot/v1`, `engine_comparison_policy/v1`);
  `core/engines/evidence_statistics.py` (the exact binomial upper tail with
  `math.comb`, the one-sided Clopper-Pearson upper bound by bisection, the
  corrected confidence); `core/engines/evidence_ranking.py`
  (`MatchedEvidenceRanking`, the lifted `select_harness` rule, and
  `PairedEfficiencyRanking`, each with `rank()` and `descriptor()`, raising
  `InsufficientEvidence`); `core/engines/evidence_checks.py`.
- **Change.** Nothing. `select_harness` is not changed here (convergence is
  package X10).
- **Edges that must not change.** `harness_trial_evidence/v1`,
  `harness_selection_policy/v1`, `harness_selection_decision/v1` and the
  behaviour of `select_harness`.
- **Checks to add first.** The evidence checks of architecture 17.4, among
  them `below_the_minimum_sample_the_declared_order_stands` (control),
  `minimum_below_the_slot_floor_is_refused`,
  `evidence_from_another_scope_cannot_rank` (control),
  `only_comparison_arm_or_frozen_population_attempts_become_ranking_evidence`,
  `lower_verified_outcome_never_outranks_on_efficiency` (control),
  `a_faster_engine_that_loses_accepted_cases_does_not_move_ahead` (control),
  `several_challengers_and_looks_use_the_corrected_confidence`,
  `the_comparison_closes_after_the_declared_looks`,
  `the_incumbent_is_the_declared_first_choice_not_the_last_winner`,
  `evidence_ranking_never_rewrites_the_host_policy`,
  `cross_scope_or_learned_ranking_is_refused_below_the_adoption_threshold`,
  `the_general_rule_and_select_harness_agree_on_the_same_evidence` (run over
  fixtures that mirror those of `core/harness_selection_checks.py`, built in
  F4's own checks module rather than imported from that module's private
  helpers, which X2 may edit),
  `standard_library_statistics_match_scipy_when_available`, and
  `an_evidence_rule_with_any_missing_threshold_is_refused` [a rule relying on
  a default].
- **Owning suites.** `core.engines.evidence_checks`, `core.harness_selection`
  (unchanged).
- **Acceptance.** Both methods produce the orders the architecture defines on
  hand-computed fixtures; the lifted rule agrees with `select_harness` on its
  existing fixtures; no threshold has a default in code; the scipy
  cross-check runs when scipy is installed and is reported as not tested
  otherwise.
- **Registration request.** Map and fold; allowlist literals. F4 merges
  after F3 because it raises `InsufficientEvidence`.

### F5. Envelope measurement

- **Goal.** Trustworthy per-attempt numbers (architecture 9.2, 9.3), recorded
  into Run History.
- **Create.** `core/engines/measurement.py` (`record_attempt(ledger,
  cost_record)` writing `engine.attempt.measured`; a privacy filter that
  refuses content and credential shapes); `core/engines/measurement_checks.py`.
- **Change.** `core/operation_cost_records.py`: `operation_cost_record/v2`
  (engine reference and digests, scope and subject digests, selection path,
  propensity, pair identity, the admission phase, dispositions without
  `verified`, `engine_reported_seconds`); version 1 readers are removed with
  their callers, historical bytes are kept. `core/operation_cost_capture.py`:
  capture writes version 2 with the envelope's phases.
  `core/model_gateway.py`: remove the `0.0` default of
  `GatewayAttempt.elapsed_seconds` so every construction site passes its
  measured time; the cost record names the route's engine reference; when an
  owning Loop's ledger is present, write `engine.attempt.measured`; update the
  expectation of `a_gateway_with_a_cost_ledger_writes_one_cost_record_per_invocation`
  with a recorded reason. `core/decisions/gateway.py` (live): its cost record
  names the decision engine and its route instead of `"model_gateway"`, the
  same defect as the gateway's (architecture 9.3). Keep the
  `OperationCostCapture` constructor signature, so that its other callers need
  no edit: the parked `core/capability_directory.py`, `core/typed_decision.py`
  and `core/typed_action_decision.py`. `OperationCostLedger.compare` and
  `implementations()`, which rank on the producer-written `verified` outcome
  with a code default of two samples, become reports over independently
  joined verdicts with no default sample size, and no selection path reads
  them (architecture 9.3). Direct
  constructions of `OperationCostRecord` with the `verified` outcome (in the
  parked `core/implementation_choice.py` and in checks) are updated together,
  as the pre-launch version policy requires. If a change to
  `core/capability_directory.py` proves unavoidable, F5 merges after F11,
  which may also edit that module.
- **Edges that must not change.** `model_gateway_result/v1` and `v2` (shape
  and types), `ModelGatewayRequest`, `ModelGatewayConfig`, the gateway's
  failover semantics, `decision_batch_result/v1`. F5 does not touch
  `core/external_harness.py` (X2 owns the harness clock).
- **Checks to add first.** `every_engine_attempt_writes_one_cost_record_in_its_envelope`
  (control `removed_envelope_measurement_is_detected`),
  `an_attempt_always_carries_its_envelope_measured_time`,
  `a_gateway_cost_record_names_the_route_that_ran`,
  `a_producer_cannot_write_an_accepted_outcome`,
  `a_refusal_before_dispatch_is_not_counted_against_the_engine`,
  `an_engine_refusal_counts_as_not_accepted`,
  `measurement_records_hold_no_secret_or_content`,
  `unknown_usage_stays_unknown_in_the_cost_record` [a record without provider
  usage written with zero tokens],
  `a_decision_cost_record_names_its_engine_and_route` [the typed decision path
  writing `implementation_id="model_gateway"`],
  `the_cost_ledger_is_never_a_selection_input` [a selection path that reads
  `OperationCostLedger.compare`, or a comparison that counts a
  producer-written acceptance]. The known-wrong cases of the first seven are
  in architecture 17.5.
- **Owning suites.** `core.model_gateway`, `core.model_gateway_accounting_checks`,
  `core.operation_cost_records`, `core.operation_cost_capture`,
  `core.engines.measurement_checks`, `core.decisions.contracts`,
  `core.decisions.jev`, `core.decisions.system_one`, and the suite of
  `core.capability_directory` once F11 collects it.
- **Acceptance.** Every gateway attempt carries a measured time; cost records
  name routes; version 2 has no self-written acceptance; records land in the
  ledger and project to `state.committed`; every existing gateway check keeps
  passing, with the one changed expectation recorded.
- **Registration request.** Map and fold; allowlist literals.

### F6. Evidence reader and compiler

- **Goal.** The pipeline of architecture 10.1: committed Run History to
  reviewed, snapshotted evidence that the rankers read.
- **Create.** `core/engines/evidence_reader.py` (reads an approved snapshot and
  its trials and reviews by reference through the `CatalogStore` contract,
  verifies every digest, returns ranking inputs);
  `core/engines/evidence_compiler.py` (a deterministic Practitioner Loop that
  reads committed histories, verifies chain and authorship, joins attempts
  with independent verdicts, keeps only comparison arm and frozen population
  records, lists every exclusion, writes trials into the Runtime History and
  Solution Intelligence layer through the store contract, publishes a
  snapshot as one look, and reports the single best and per-subject best
  baselines); `core/engines/evidence_compiler_checks.py`.
- **Change.** Nothing directly. The boundary row "engine evidence compilation"
  (envelope `core.engines.evidence_compiler.compile_evidence_as_loop`) is a
  registration request applied by the desk.
- **Edges that must not change.** The Run History chain format and
  `verify_chain`; the `CatalogStore` protocol; the record types of F4.
- **Checks to add first.** `evidence_bound_to_a_broken_chain_is_refused`,
  `synthetic_records_never_become_evidence`,
  `rejected_or_self_reviewed_evidence_cannot_rank` (known-wrong cases in
  architecture 17.4);
  `a_snapshot_publication_counts_as_one_look` [two publications of one
  snapshot counted as a single look];
  `the_reader_refuses_a_snapshot_whose_digest_differs` [a snapshot whose
  bytes changed after the policy recorded its digest, read as approved];
  `tenant_evidence_is_not_pooled_without_a_declared_consent_scope` [trials
  from two tenants compiled into one snapshot with no consent scope];
  `fallback_attempts_are_not_pooled_with_first_choice_attempts` [a fallback
  attempt counted as ranking evidence].
- **Owning suites.** `core.engines.evidence_compiler_checks`,
  `core.run_history_checks`, `core.run_history_authorship`,
  `catalog.conformance`.
- **Acceptance.** A fixture history with paired comparison attempts and
  independent verdicts compiles into trials whose counts match a hand
  computation; every exclusion is listed; the reader feeds F4's rankers.

### F7. Conformance gate

- **Goal.** Keep call sites clean for people and coding harnesses
  (architecture 12).
- **Create.** `core/engines/conformance.py` with four detectors:
  `scan_engine_construction_sites` (an abstract syntax tree scan; concrete
  engine classes may be constructed only in their factory table module and its
  checks; reads each slot's `known_direct_construction_sites` baseline, which
  may only shrink), `scan_engine_registration_on_import`,
  `scan_engine_slot_suites_collected` (reads the literal suite list of
  `_self_test.py` by abstract syntax tree and the suite exceptions), and
  `scan_engine_module_placement` (one engine per module, in the folder its
  slot names; factory table modules define no engine class; engine modules
  import only their slot contract and their own dependencies; today's
  modules that hold several engines, such as `core/retrieval.py` and the
  recipe modules with two styles, start in a baseline that may only shrink);
  `core/engines/conformance_checks.py`.
- **Change.** `_conformance_scan.py`: import the four detectors and add them
  to `DETECTORS`. The first run replaces F2's hand-found construction
  baseline with exactly what the scanner finds on `main`, through a desk
  request.
- **Edges that must not change.** Every other detector and baseline.
- **Checks to add first.** `engine_classes_are_named_only_at_their_registration_sites`
  [a new `SQLiteRecordStore(` in a service module];
  `the_construction_baseline_only_shrinks` [a baseline entry added, or an
  entry left after its call site is gone];
  `importing_an_engine_module_registers_nothing` [a module-level
  `registry.register(...)`];
  `engine_checks_resolve_to_collected_suites_before_qualification` [an engine
  whose named check lives only in a parked suite made active];
  `every_engine_module_holds_one_engine_in_its_component_folder` [a factory
  table module that defines an engine class; an engine module outside its
  slot's folder];
  `engine_module_imports_only_its_slot_contract_and_its_own_dependencies`
  [a recipe module importing `core.model_gateway`].
- **Owning suites.** `core.engines.conformance_checks`, `_conformance_scan`,
  `_conformance_test`.
- **Acceptance.** `python -m loop_engine --conformance` passes on `main` with
  the scanner's own baseline (source search already finds six sites, among
  them `record_cli.py`, which the first draft missed); one new site fails it;
  a stale entry fails it.

### F8. Engine-side settings section and projections

- **Goal.** One settings shape per engine-side slot without a second copy of
  any existing declaration (architecture 6.3, 15.1 for the service analogue).
- **Create.** `core/engines/settings.py`: parse the optional root section
  `engines` into `engine_slot_configuration/v1` records; project `search:` into
  the retrieval stage configurations and `models.tiers` into `model_access`
  configurations per thinking power; refuse a slot declared by both.
  `core/engines/settings_checks.py`.
- **Change.** `core/settings_loader.py`: accept the root key `engines` and
  hand it to `core/engines/settings.py`. `core/runtime_settings.py`: add the
  `engines` field to `RuntimeSettings`.
- **Edges that must not change.** The settings file's `version: 1`, the fields
  and meaning of `search:`, `models:`, `loop:`, `operating:` and `history:`.
  F8 does not touch the provider table dependency in `runtime_settings.py`
  (M1 owns it).
- **Checks to add first.** `a_slot_is_declared_by_one_source_only` [settings
  with both `engines.model_access` and `models.tiers`];
  `the_engines_section_refuses_unknown_slots_and_keys` [an `engines` section
  naming a slot the catalogue does not hold, or an installation with an
  unknown key];
  `a_projection_is_a_view_not_a_copy` [a projected configuration that does not
  follow an edit of its source]; `an_older_loader_refuses_a_settings_file_with_an_engines_section`
  (against the recorded root key list of `97e805f`) [the older key list
  accepting a file with the new section];
  `installation_settings_carry_no_authority` [an installation whose settings
  declare `allow_network`, a spending ceiling or a model identity grant].
- **Owning suites.** `core.settings_loader`, `core.engines.settings_checks`.
- **Acceptance.** Existing settings files load unchanged; a file with
  `engines` loads and projects; the double declaration is refused.

### F9. Service host engine table (after G0)

- **Goal.** The host loader stops naming concrete classes (architecture 15.1),
  with exactly today's behaviour.
- **Create.** `core/service_runtime/service_engines.py` (the dispatcher: parse
  the optional `engines` block, `service_host_engines/v1`; project the
  existing blocks; run host-start selection as a Starting Practitioner Loop;
  construct each engine through its slot module; produce
  `engine_bindings_report/v1` with the family policy in force and its reason);
  one factory module per service slot, each holding exactly today's single
  engine row: `service_engine_identity.py`, `service_engine_account_email.py`,
  `service_engine_billing.py`, `service_engine_record_store.py`,
  `service_engine_search.py`, `service_engine_request_limits.py`,
  `service_engine_observability.py`, `service_engine_secrets.py`;
  `core/service_runtime/service_engines_checks.py`.
- **Change.** `core/service_runtime/http_entrypoint.py`: allowed top-level keys
  gain `engines`; `load_host_application` constructs through the dispatcher
  and passes the same objects to `ServiceHttpApplication` as today;
  `configure_host` returns the bindings report beside `service_host_setup/v1`.
- **Edges that must not change.** Every host block's record type and fields,
  `service_http_host_configuration/v1`, every wire record, the protocol checks
  in `http.py` and `http_auth.py` (not edited), `service_capabilities/v1`, the
  `serve` command's behaviour.
- **Checks to add first.** `a_host_block_selects_its_engine_by_provider_profile_without_a_loader_edit`
  [a fixture identity profile that needs an edit to `load_host_application`];
  `an_unknown_provider_profile_stops_the_host_before_it_serves` [an unknown
  profile falling back to the default engine];
  `the_loader_output_names_the_engine_bound_at_every_service_slot_and_the_family_reason`
  [`configure_host` output without the bindings or the family-policy reason];
  `a_slot_is_declared_by_one_source_only` (service form) [a host file with
  both a `browser_identity` block and an `engines.browser_identity_provider`
  entry];
  `host_start_selection_runs_as_a_loop_and_grants_nothing` [a host-start
  binding made outside a Loop, or a decision that makes a network engine
  eligible without the block's `allow_network`].
- **Owning suites.** `core.service_runtime.service_engines_checks`,
  `core.service_runtime.http_checks`, `core.service_runtime.runtime`,
  `core.service_runtime.billing`, `core.service_runtime.stripe_sessions`,
  `core.service_runtime.promotions`, `core.service_runtime.refusals`, the
  account email and browser identity suites, and the tools tests
  `tools/test_fly_deployment.py` and the container check.
- **Acceptance.** Every existing service suite passes with unchanged counts;
  `http_entrypoint.py` names no engine class of a service slot (identity,
  email, billing, store, search, limiter, journal, secrets; the fixed-frame
  objects such as `ServiceRuntime` and `ServiceHttpApplication` stay); the
  construction baseline entry
  for it is removed through the desk; `configure` prints the report; the
  rollback drill of architecture 15.3
  (`older_release_refuses_a_settings_or_host_file_with_an_engines_section`,
  an operational drill) is scheduled with the first release that uses the
  block.

### F10. Entry point discovery

- **Goal.** Engines shipped by other packages are listed without effects and
  loaded only when a host names them exactly (architecture 7.5). Loading runs
  the distribution's code in this process, so only a distribution the host
  names and pins is ever loaded; untrusted code runs as a confined process
  engine instead.
- **Create.** `core/engines/discovery.py` (list
  `importlib.metadata.entry_points(group="loop_engine.engines")` as candidate
  descriptors with lifecycle `candidate` and qualification `unknown`;
  `load_named_entry_point(name, distribution, version)` returning a factory);
  `core/engines/discovery_checks.py` (a fixture distribution written as a
  temporary `.dist-info` under a folder in `$HOME`, never inside the
  repository).
- **Edges that must not change.** None touched.
- **Checks to add first.** `an_installed_entry_point_is_listed_but_not_registered`,
  `listing_entry_points_imports_nothing` [the module present in `sys.modules`
  after listing], `a_version_mismatch_between_host_file_and_distribution_refuses_load`,
  `a_host_file_names_no_import_path` [an entry written as `module:attribute`].
- **Registration request.** `dynamic_import_allowed_modules` +=
  `core/engines/discovery.py`, with the reason "loads only an entry point a host
  file names by exact name, distribution and version".

### F11. Guards for live dependencies

- **Goal.** The parked modules that live slots import get their own checks run
  again (architecture 18.4, item 3), so the framework does not rest on
  unchecked code.
- **Scope.** `core/capability_directory.py`, `core/heuristic_adoption.py`,
  `core/context_artifacts.py`, `core/outcome_vector.py`,
  `core/model_capabilities.py`, `core/contract_matching.py`,
  `core/model_response_admission.py`, `core/custom_endpoint.py`,
  `core/event_vocabulary.py` (its suite is parked, and F3 edits the module),
  `loop/effect_approval.py`, `loop/loop_profile_ontology.py`.
- **Create.** `core/live_dependency_checks.py` with the ratchet check
  `every_module_a_collected_suite_imports_at_load_has_its_suite_collected_or_a_recorded_exemption`,
  whose baseline is today's list (at least 48 modules) and may only shrink.
- **Change.** Only the modules in scope and their own check modules, and only
  where a re-collected suite fails on `main`: fix the code, never the check.
  Where a suite cannot pass without restoring a parked capability, move the one
  type live code needs into a collected module instead, with its checks.
- **Edges that must not change.** Every record those modules define.
- **Checks to add first.** The ratchet check above [a new live import of a
  parked module without its suite].
- **Owning suites.** Each re-collected suite, plus the suites of every live
  module that imports them.
- **Acceptance.** Each module in scope has its suite collected and passing in
  the base installation (optional dependencies reported as not tested with
  evidence, as today); the ratchet baseline shrinks by the same modules; the
  decision is recorded in S-6.28's evidence. Reason, recorded: these are live
  dependencies, not the retired in-process execution capability.
- **Registration request.** Remove the modules from
  `suite_collection_exceptions`; fold their suites.

### F12. Engine commands, read only (after G0)

- **Goal.** `loop-engine engines list | explain | show | check | select`
  (architecture 12), writing nothing.
- **Create.** `engine_cli.py`, `engine_cli_checks.py`.
- **Change.** `__main__.py` (dispatch `engines` early, like `records` and
  `service`), `cli_help.py` (focused help).
- **Edges that must not change.** Every existing command and its output.
- **Checks to add first.** `engine_commands_write_nothing_and_open_no_network`
  [a read-only command that writes a file or opens a socket, with fixture
  functions that raise if touched];
  `explain_names_the_files_a_change_may_touch_and_the_edges_it_must_not`
  [an `explain` output that omits the slot's edge contract records or lists a
  call site as editable];
  `check_refuses_a_file_the_release_would_refuse` [a host file with an unknown
  slot passes `check`].
- **Acceptance.** Every command runs against the example settings and host
  files of `examples/29_intelligence_service` and a fixture settings file.

### F13. Generated engine slot pages

- **Goal.** One generated page per slot for people and coding harnesses
  (architecture 12).
- **Create.** `tools/build_engine_pages.py`, `tools/test_build_engine_pages.py`,
  and the generated `docs/components/engines/README.md`, one
  `docs/components/engines/<slot>.md` per slot, and
  `docs/components/engines/engines.json`.
- **Edges that must not change.** None.
- **Checks to add first.** `generated_engine_pages_are_current` [a page edited
  by hand, or stale after a catalogue change], `every_slot_has_a_page_and_every_page_a_slot`
  [a slot in the catalogue with no page, or a page for a slot that was
  removed from the catalogue].
  The generator writes plain English that passes the repository's Markdown and
  public-language linters (no dashes used as punctuation, no shorthand) and
  the documentation job's retired-language check (only the replacement words
  the `terminology.yaml` vocabulary names).
- **Registration request.** The pointer in `docs/components/README.md`, the
  entry in `docs/components/COMPONENT-GUIDE-MAP.yaml`, and the short
  "Changing one engine" section in `AGENTS.md`, applied by the desk because the
  README cleanup (roadmap S-6.34) edits the same files.

## 7. Harness executor slot packages (S-6.31, phase 2 of the harness-first plan)

### X1. Harness recipe catalogue (starts now)

- **Goal.** Adding a command-line harness becomes one recipe module and one
  record (architecture 13.7), ending the six code edits of today (the first
  draft counted five; the relay's style-keyed wire choice is the sixth).
- **Create.** `data/harness_recipes.yaml` (`harness_recipe_catalog/v1`, one
  `harness_recipe/v1` for each of the 18 existing styles, with `variant`
  `text_response`); `core/harness_recipes.py` (catalogue loader and
  validation, including `module_sha256`); `core/harness_builtin_recipes.py`
  (the Aider, Continue and Pi recipes moved out of the relay);
  `core/harness_recipe_catalog_checks.py`.
- **Change.** `core/harness_process.py`: validate `style` against the catalogue
  instead of the closed tuple; mount and digest the selected recipe's module
  and the codec module of each wire the record declares (the Responses codec
  lives in `harness_responses_recipes.py`, the Google codec in
  `harness_additional_recipes.py`, the Anthropic Messages codec in
  `harness_lightweight_recipes.py`); apply `requires_context_capacity` and
  `sandbox_environment` from the record (the Pi and Aider special cases);
  expose the sandbox argument builder as one public helper for X4.
  `core/harness_process_relay.py`: read the recipe record from its
  configuration, choose the wire from `wire_protocols` instead of the
  style-keyed choice in the request handler (lines 111 to 119 today), and
  import only the mounted modules by name. X1 reads `data/harness_recipes.yaml`
  with its own typed loader and does not edit `core/component_contracts.py`,
  which F2 edits in the same wave; if the catalogue should later load through
  `load_component_resource`, the desk adds its name after F2 merges. The nine recipe modules (`harness_opencode_recipe.py`,
  `harness_responses_recipes.py`, `harness_additional_recipes.py`,
  `harness_goose_recipe.py`, `harness_mini_swe_recipe.py`,
  `harness_python_recipes.py`, `harness_cline_kilo_recipes.py`,
  `harness_lightweight_recipes.py`, `harness_remaining_recipes.py`): one
  signature, `prepare(style, config, base)` and `extract(style, stdout,
  expected)`. Their check modules and `core/harness_process_checks.py`, for the
  new signatures only.
- **Edges that must not change.** `harness.json` schema version 1 with its
  exact keys; the relay socket protocol; `harness_request_identity/v3`;
  `external_harness_result/v3`. The process identity now digests one recipe
  module instead of all; confirm that the qualification files under
  `embodiments/*/qualification.json` bind binaries and manifests, not this
  digest, and re-run their offline probes if any does.
- **Checks to add first.** `adding_a_process_harness_recipe_needs_no_core_dispatch_edit`
  [a style literal in `harness_process.py` or `harness_process_relay.py`];
  `unsupported_style_is_refused_with_its_named_reason` [the `freebuff` host
  file binds]; `recipe_module_mount_and_digest_follow_the_selected_recipe_and_its_wire_codec`
  [every recipe module mounted; the codec module of the declared wire missing,
  so the relay cannot decode it]; `every_recipe_names_resolvable_functions_and_its_module_digest`
  [a module edited without updating `module_sha256`];
  `special_cases_come_from_the_record` [Pi started without a context capacity
  while its record requires one].
- **Owning suites.** `core.harness_process_checks`, the nine
  `core.harness_*_recipe_checks` suites, `core.harness_recipe_catalog_checks`,
  `core.harness_semantic` and `core.harness_confinement` (unchanged).
- **Acceptance.** The style tuple, both dispatch chains and the style-keyed
  wire choice are gone; all 18
  styles pass their suites; `freebuff` is refused by name; a fixture recipe
  added with one module and one record runs through the relay in the offline
  sandbox check (reported as not tested, with dependency evidence, where
  Bubblewrap is absent).
- **Registration request.** `dynamic_import_allowed_modules` +=
  `core/harness_process_relay.py` with the reason "imports only the recipe
  module and the wire codec modules the release catalogue names and the
  sandbox mounts"; map and fold the new modules.

### X2. Adapter contract version and the envelope clock (starts now)

- **Goal.** Registration refuses incompatible adapters before any run, the
  duplicate `opencode` identity ends, and the envelope's clock becomes
  authoritative (architecture 13.4, 9.3).
- **Change.** `core/external_harness.py`: `HarnessAdapterInfo` gains
  `adapter_contract_version`, `engine_kind` and `supported_edge_contracts`;
  `HarnessRegistry.register` refuses a missing or unknown contract version, an
  unknown kind and an adapter serving no supported edge (it already refuses a
  second registration of one identifier unless the caller passes
  `replace=True`; that stays, and a replacement changes the descriptor
  digest); `run_external_harness` always writes its own measured time into
  `elapsed_seconds` and records the adapter's value as `engine_reported_seconds`
  in the ledger event beside the safe summary. `core/external_harness_adapters.py`:
  the four kits declare kind `agent_framework_kit`.
  `core/harness_semantic.py`: `GatewayHarnessProcessAdapter` declares kind
  `text_relay_harness` and edge `harness_request_identity/v3`.
  `core/harness_configuration.py`: `UnavailableHarnessAdapter` declares the
  same fields. `core/opencode_harness_adapter.py` (parked; its suite does not
  run, so the rename is guarded by the collected check below): identifier
  `opencode.raw_host`, matching the `architecture.yaml` invariant
  `opencode_raw_host_execution_is_quarantined`. Test fixtures that register adapters, found by searching
  for `HarnessRegistry(` and `.register(`: at least
  `core/external_harness_checks.py`, `core/harness_semantic_checks.py`,
  `core/harness_fallback_checks.py`, `core/harness_selection_checks.py`,
  `core/instance_instructions_checks.py`.
- **Edges that must not change.** The shapes of `harness_request_identity/v3`
  and `external_harness_result/v3` (the meaning of `elapsed_seconds` becomes
  "measured by the envelope", documented in the component guide); every
  harness selection and fallback record; `HarnessSemanticBinding.invoke`.
- **Checks to add first.** `registration_refuses_an_unknown_or_missing_adapter_contract_version`
  (control `removed_contract_version_refusal_is_detected`);
  `registration_refuses_an_adapter_that_serves_no_supported_edge` [an
  adapter whose `supported_edge_contracts` names only an edge version the
  slot does not serve registers];
  `one_engine_identifier_names_one_implementation` [the parked
  `OpenCodeProcessAdapter` and the `opencode` recipe engine both answering to
  `opencode`; a `replace=True` registration whose descriptor digest does not
  change]; `engine_reported_time_never_replaces_the_envelope_clock`
  [adapter reports 0.001 seconds, envelope measured two] (control
  `removed_envelope_clock_rule_is_detected`);
  `an_adapter_cannot_declare_a_kind_outside_its_slot` [an adapter declaring
  a kind the `step_executor` slot does not list, for example
  `server_database`]. A kit that declares a delegating kind while its
  isolation is `none` is caught by the envelope's own computation of
  `delegated` (X3).
- **Owning suites.** `core.external_harness`, `core.external_harness_adapters`,
  `core.harness_semantic`, `core.harness_fallback`, `core.harness_selection`,
  `core.instance_instructions`, `core.harness_layering` and its siblings
  (unchanged), `core.provisioning_server`, `core.provisioning_mcp_checks`.
- **Acceptance.** Every production adapter declares the three fields; every
  suite that registers adapters passes; the two controls fail with their
  guards removed.

### X3. Step edge records and the step attempt envelope

- **Goal.** The new edge `step_run_request/v1` and `step_run_result/v1`, the
  `executor_profile/v1` capability record, and the envelope that runs one
  physical attempt (architecture 13.2, 13.3, 13.5).
- **Create.** `core/step_execution/records.py` (the three records; every key
  of `step_run_result/v1` is present in every result, null when the engine
  does not expose it, and the result carries the typed `engine_preferences`
  field of architecture 8.4, which only the owning Loop may admit; the
  executor profile carries `fresh_instance_per_step`);
  `core/step_execution/envelope.py` (`run_step_attempt(engine, request, services, *,
  parent, decision)`: requires a prior decision digest, revalidates the
  binding, spawns one Loop, invokes `run_step` once and never retries inside,
  validates the result against the edge, computes `delegated`, maps statuses,
  writes `engine.attempt.measured`); `core/step_execution/envelope_checks.py` with
  fixture engines of every kind.
- **Change.** None directly. The boundary row "delegated step execution"
  (binding `native_loop`, envelope `core.step_execution.envelope.run_step_attempt`, test
  `core.step_execution.envelope.self_test`, a dynamic profile source from the request) is a
  registration request applied by the desk.
- **Edges created and then frozen.** `step_run_request/v1`,
  `step_run_result/v1`, `executor_profile/v1`.
- **Edges that must not change.** `harness_request_identity/v3`,
  `external_harness_result/v3`, and the behaviour of `run_external_harness`.
- **Checks to add first.** `step_edge_records_refuse_unknown_keys_and_versions`
  [a request with an extra key, or `step_run_result/v2` read by the v1
  reader];
  `delegated_is_computed_by_the_envelope_and_names_a_separate_confined_process`
  [a result from `default_handler` with `delegated: true` written in; an
  adapter setting its own flag] (control
  `removed_delegation_computation_is_detected`);
  `a_changed_engine_does_not_change_the_edge_record` [an extra field or
  status, or a key missing because the engine does not expose it] (control
  `removed_edge_shape_check_is_detected`);
  `effects_uncertain_blocks_fallback_until_reconciled` [a fallback attempt
  started after a result with status `effects_uncertain`];
  `a_step_attempt_is_one_physical_invocation_in_one_loop` [a retry inside the
  envelope]; `completion_is_never_acceptance` [an engine's `completed` status
  recorded as an accepted task]; `unknown_usage_stays_unknown` [a result
  without provider usage recorded with zero tokens];
  `engine_preferences_in_a_result_are_data_until_admitted` [a preference in a
  step result that changes the next attempt's engine without passing the
  owning Loop's admission].
- **Owning suites.** `core.step_execution.envelope_checks`, `core.engines.selection_checks`,
  `core.external_harness` (unchanged).
- **Acceptance.** Fixture engines of each kind run through the envelope;
  every result validates or is refused; `delegated` is computed only as
  architecture 13.5 states; measurement is recorded.

### X4. Agent Client Protocol engine, OpenCode first

- **Goal.** The first engine able to do a step that needs tools and file
  effects, delegated to a standard harness (architecture 13.6).
- **Create.** `core/step_execution/agent_client_protocol.py` (an engine serving the
  step edge: `initialize` with capability negotiation and a refusal of an
  unsupported protocol major version, `session/new` with the workspace folder
  and the step's protocol servers, `session/prompt`, `session/cancel`;
  `session/request_permission` answered only within the step's exact grants;
  `usage_update` mapped to accounting; stop reasons mapped to statuses, with
  `cancelled` never reported as an error; library types converted to this
  repository's records at the boundary); `core/step_execution/session_process.py` (a
  session process that lives for exactly one step attempt: started fresh
  inside Bubblewrap for that attempt with the relay broker inside the
  sandbox, reusing X1's sandbox argument builder, controlled by its owned
  process group, and stopped when the attempt ends; keeping it across steps
  is the separate `long_lived_session` placement, never the default, because
  `AGENTS.md` makes a fresh harness for every step the default design); `core/step_execution/agent_client_protocol_fixture.py` (a
  scripted, deterministic agent that speaks the protocol over standard input
  and output, for offline checks); `core/step_execution/agent_client_protocol_checks.py`,
  including a check that validates recorded frames against the pinned upstream
  JSON schema with the existing `jsonschema` dependency.
- **Change.** `data/harness_recipes.yaml` (desk-owned after X1 merges, so this
  is a registration request): records `opencode.agent_client_protocol`
  (variant `agent_protocol`, the pinned OpenCode version and SHA-256) and
  `goose.agent_client_protocol` (candidate, for X7).
- **Dependency.** The protocol's Python library, pinned exactly (0.12.1 until
  1.0.0 leaves release candidate), in a new optional extra `executors` that
  `all` includes. Without it the engine reports `unavailable` with
  `missing_optional_dependencies` evidence, the repository's existing pattern.
  Pydantic, which the library needs, stays out of the base installation.
- **Edges that must not change.** The step edge of X3; the relay broker
  protocol; the recipe record shape.
- **Checks to add first.** `agent_protocol_permission_requests_are_answered_only_within_the_step_grants`
  [a write outside the work folder approved];
  `agent_protocol_stop_reasons_map_to_typed_statuses_and_cancel_is_not_an_error`
  [`cancelled` reported as `failed`];
  `the_agent_protocol_engine_reaches_models_only_through_the_broker` [an agent
  configured with a provider address outside the relay];
  `protocol_library_types_never_cross_the_edge` [a result carrying a library
  object]; `initialize_refuses_an_unsupported_protocol_major_version` [an
  agent answering `initialize` with another protocol major version, then
  prompted]; `recorded_frames_validate_against_the_pinned_upstream_schema`
  [a frame with a field the pinned schema does not define accepted];
  `the_session_process_is_stopped_by_its_owned_process_group` [a process
  left running after the attempt ends, or one stopped by searching for a
  process name]; `a_session_process_never_outlives_its_step_attempt` [the
  same session process answering a second step].
- **Owning suites.** `core.step_execution.agent_client_protocol_checks`,
  `core.step_execution.envelope_checks`, `core.harness_process_checks`,
  `core.harness_confinement`.
- **Acceptance.** The fixture agent completes a step with a file effect inside
  the work folder through the real sandbox (`local_contract`); where the pinned
  OpenCode binary is installed, OpenCode completes the same step against the
  deterministic broker fixture and an `engine_qualification/v1` at
  `local_contract` is written for `opencode.agent_client_protocol`. A real
  provider run (`real_provider`) waits for the owner's model-call authority.
- **Registration request.** The extra and its pin in `pyproject.toml`; map and
  fold; the recipe records.

### X5. Step executor slot adoption

- **Goal.** A host selects the step executor engine by declaration, the owning
  Loop's one delegate handler never changes, and the harness-first rule is
  typed (architecture 13.5, 13.9).
- **Create.** `core/step_execution/engines.py`: the factory table by engine
  kind, which names engine classes and defines none; the projection of
  `HarnessAdapterInfo`, the recipe record and the host declaration into
  `executor_profile/v1` descriptors; `delegate_step_handler(binding)`; `step_executor_mechanics(decision, engine)`
  producing the `step_executor` internal binding and executor modes derived
  from the engine's supported modes; the projection of `harness.json` plus
  `HarnessFallbackPolicy` into `engine_slot_configuration/v1`.
  `core/step_execution/text_relay.py`: `TextRelayStepEngine`, the one engine
  of this module, the small wrapper that lets a text relay recipe serve a
  text-only step (typed inputs rendered into the instruction and prompt
  material; admitted text parsed into the output ports; no tools, no
  effects). `core/step_execution/engines_checks.py`.
- **Change.** `core/harness_configuration.py` (merged after X2): expose the
  loaded bindings to the projection.
- **Edges that must not change.** The step edge; `LoopRuntimeContext` and its
  public ports; `loop_definition/v2`; the Loop profile records.
- **Checks to add first.** `a_delegation_claim_cannot_be_met_by_an_in_process_engine`
  [a framework kit, the overnight direct step, or an in-process runner
  registered as `opencode_local`, offered for a step that requires delegation;
  the status must be `no_eligible_engine` and no adapter may be called]
  (control `removed_delegation_kind_rule_is_detected`);
  `a_step_needing_tools_or_file_effects_is_refused_by_a_text_only_engine`;
  `a_semantic_step_without_a_bound_step_executor_is_refused`;
  `instruction_style_follows_the_bound_step_engine` [a CLAUDE.md composed for
  a codex engine]; `executor_profiles_are_projections_of_adapter_info_recipe_and_host_declaration`
  [a hand-written executor profile whose isolation differs from the
  adapter's declared capabilities];
  `adding_an_engine_by_registration_changes_no_call_site` (the executor
  instance of roadmap D-19-T01).
- **Owning suites.** `core.step_execution.engines_checks`, `core.step_execution.envelope_checks`,
  `core.engines.selection_checks`, `core.harness_semantic`,
  `core.instance_instructions`, `loop.recursive_loop` (unchanged).
- **Acceptance.** From a settings file declaring `engines.step_executor`, a
  fixture Loop runs a text-only step through the codex text relay engine in
  the real sandbox with the deterministic broker fixture; the decision is
  recorded before dispatch, the attempt is measured, `delegated` is true; the
  same step offered only in-process engines is refused; the control fails with
  its guard removed.

### X6. Phase 2 acceptance run

- **Goal.** The recorded proof of phase 2 at the level engineering may reach
  without model-call authority (architecture 13.13).
- **Create.** `tools/check_delegated_step.py` and
  `tools/test_check_delegated_step.py`: a settings file with the step executor
  slot; one text-only step through the text relay engine and one tool-using
  step through OpenCode with the Agent Client Protocol, both in the real
  sandbox against the deterministic broker; a new evidence record under a new
  name, `artifacts/architecture-audit-2026-09-19/delegated-step-1.json`. The
  run also records a `local_contract` proof of `fresh_instance_per_step` for
  each engine it uses (a fresh process with a cleared environment, a fresh
  work folder and no user-level configuration), because a step that requires
  one harness per step refuses an unproven engine (architecture 13.5);
  package X11 extends that proof natively to Codex, Claude Code, OpenCode and
  Pi. The record also names, for each engine, the highest rung of the
  qualification ladder S-6.31 asks for (connected, material listed, material
  loaded, step finished, independently accepted).
- **Edges that must not change.** All of them.
- **Checks to add first.** `the_delegated_step_record_names_its_proof_level`
  [a `local_contract` run reported as `end_to_end`];
  `the_run_refuses_to_start_without_a_bound_harness_engine` [the tool
  starting with no `step_executor` binding and falling back to an in-process
  handler]; `native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit`
  [an engine recorded at the rung "material loaded" because a bridge is
  documented, a session identifier exists or the process exited cleanly].
- **Acceptance.** The evidence record exists, names `local_contract`, and the
  desk records it on S-6.28 (phase 2) and D-19-T03 as partial. The
  `end_to_end` proof, one real step with a real provider and a second harness
  replacing the first by configuration, waits for the owner's model-call
  authority and is a separate, later run under the same tool.

## 8. Hosted search packages (S-6.32)

### R1. Hosted search as an engine slot

- **Goal.** Served search chooses its policy and stages by declaration,
  reports a poor match honestly, and reports the engines it actually uses
  (architecture 14).
- **Create.** `core/retrieval_engines.py` (the factory table for the built-in
  lexical and vector engines and host bindings; descriptors from
  `backend_handshakes()` and `RetrievalBackendBinding.handshake`);
  `core/retrieval_engine_checks.py`; `core/service_runtime/search_engine_checks.py`.
- **Change.** `core/service_runtime/service_engine_search.py` (after F9):
  select the policy and the stages at host start and build the index once per
  start. `core/service_runtime/http.py`: `_search` runs `catalogue_search` with
  the bound policy and stages, filters by the caller's authorization, and
  answers `service_retrieval_result/v2` with the "no good match" signal; the
  retrieval section of `capabilities()` keeps its keys (`modes`,
  `lexical_backend`, `vector_backend`, `semantic_embedding_model_installed`,
  `scope`, `returns_bodies`) and reads their values from the bound engines,
  so `service_capabilities/v1` and its four outside consumers (`service.js`,
  `tools/check_hosted_website.mjs`, `tools/check_service_workspace.mjs`,
  `tools/install_selected_material.py`) do not change; handshake digests go
  to the bindings report. `core/harness_intelligence_search.py`: policy record
  `harness_intelligence_search_policy/v2` without `lexical_backend` (the
  lexical engine belongs to its stage slot) and with `relevance_floor`;
  `SERVED_BEFORE_2026_09_21` and `DEFAULT_SEARCH_POLICY` become the two policy
  engines. `core/service_runtime/http_checks.py` and
  `core/provisioning_mcp_checks.py`: only the assertions that read the search
  result version. Every other consumer of the result version, in the same
  commit: `tools/install_selected_material.py` and
  `tools/check_client_journey_in_containers.py` (both pin
  `service_retrieval_result/v1` as a constant),
  `tools/test_check_client_journey_in_containers.py`,
  `docs/components/service-runtime/README.md`,
  `docs/guides/service-searching-and-retrieving.md` and
  `docs/guides/client-journey-container-test.md`. Every user of the policy
  records, in the same commit: `examples/30_search_quality/measure.py` and
  `run.py`, and `tools/test_search_quality.py`. Several of these files are
  edited by the r2-release worktree, which is one more reason R1 waits for
  G0.
- **Edge deliberately versioned (the edge-change procedure of architecture
  11.7).** `service_retrieval_result/v1` to `v2`, and
  `harness_intelligence_search_policy/v1` to `v2`, with every producer and
  consumer updated together and the old versions refused.
- **Edges that must not change.** `service_retrieval_request/v1`; the tool
  names and protocol version of `/mcp`; `retrieval_query/v1` and
  `retrieval_candidates/v1`; `retrieval/v1`; the authorization and body-free
  guarantees.
- **Checks to add first.** `served_search_uses_the_engine_and_policy_the_host_declared`
  [today's `Retriever(records)` defaults] (control
  `removed_search_binding_is_detected`); `hosted_capabilities_name_the_bound_retrieval_engines`
  [fixed strings]; `a_query_with_no_good_match_says_so` [the best poor items
  returned as matches]; `switching_search_policy_changes_no_fixed_evaluation_result_without_a_recorded_comparison`;
  `the_index_is_built_once_per_host_start_and_never_holds_a_body` [an index
  rebuilt for every request, or an index row that carries a body];
  `an_unauthorized_item_never_appears_although_the_index_holds_every_item`
  [an item outside the caller's grants returned because the shared index
  holds it]; `the_old_result_version_is_refused_by_the_new_reader`
  [`service_retrieval_result/v1` accepted by the updated installer or journey
  check]; `hosted_capabilities_keep_their_retrieval_keys` [a capabilities
  record whose retrieval section gains or loses a key].
- **Owning suites.** `core.retrieval_engine_checks`,
  `core.service_runtime.search_engine_checks`, `core.service_runtime.http_checks`,
  `core.harness_intelligence_search`, `core.retrieval`, `core.retrieval_backends`,
  `core.provisioning_mcp_checks`, and `tools/test_search_quality.py`.
- **Acceptance.** The frozen judged query set of `examples/30_search_quality`
  reproduces the recorded results of both policy engines; the initial choice
  stays `served_before_2026_09_21` until a recorded comparison (V1 or the
  tournament) says otherwise; a fixture ranking engine is added without
  touching the route (roadmap D-19-T01 for search).

### R2. Second lexical and vector engines

- **Goal.** The second engines S-6.32 asks for: bm25s with a memory-mapped
  index, and model2vec potion-base-8M vendored and loaded offline.
- **Create.** `core/retrieval_bm25s.py` and its checks.
- **Change.** `core/retrieval.py` (the embedding space revision becomes the
  vendored model's commit hash instead of the literal `hf-cache-pin`);
  `core/retrieval_backends.py` (the new built-in identity);
  `core/retrieval_engines.py` (two rows); `Dockerfile.service` (vendor the
  model at build time with offline loading).
- **Edges that must not change.** Everything R1 froze.
- **Checks to add first.** `equal_dimensions_do_not_establish_embedding_compatibility`
  [two spaces with equal dimensions and different models compared, roadmap
  D-12-T01's negative control]; `the_vendored_model_revision_is_a_commit_hash_not_a_label`
  [the embedding space revision `hf-cache-pin`, a label, accepted];
  `the_bm25s_index_digest_binds_the_manifest_digest` [an index built for one
  manifest served with another].
- **Acceptance.** Both engines are qualified as candidates on the frozen query
  set, with a significance test (ranx in a development extra, never in the
  serving image); the declared order changes only after a recorded comparison.
- **Registration request.** `pyproject.toml` serving extra += bm25s and
  model2vec at exact versions; the development extra += ranx.

## 9. Adoption packages, in the owner's priority order

### E1. Account email slot (after F9)

- **Change.** `core/service_runtime/service_engine_account_email.py`: the
  descriptor from `protocol_version` and the provider pair; ceiling
  `before_dispatch_only`; projection of the `account_email` block.
- **Create.** `core/service_runtime/account_email_engine_checks.py`.
- **Edges that must not change.** `account_email/v1`, the sign-up and
  recovery request and result records, the `account_email` host block, the
  identical-answer rule.
- **Checks to add first.** `an_uncertain_send_blocks_every_fallback` [a second
  email after a timeout]; `the_account_email_slot_never_falls_back_after_dispatch`
  [a policy that lists a second email engine as a fallback after a send was
  dispatched]; `a_second_provider_pair_is_a_new_factory_row_and_no_loader_edit`
  [a fixture provider pair that needs an edit to `load_host_application`].
- **Acceptance.** The existing 71 checks and nine controls pass unchanged; the
  new checks pass. Nothing is deployed: no mail credential is staged, and the
  unconfirmed-address case must be observed before sign-up opens.

### D1. Record store slot (after F9 and F3)

- **Create.** `catalog/record_store_engines.py` (factory table and
  descriptors from `StoreCapabilities`), `catalog/record_store_engine_checks.py`.
- **Change.** `catalog/registry.py`: `descriptors()`, and a selection path
  that uses only the declared engines (today's `select` falls through to every
  registered adapter after the preferred ones). `catalog/conformance.py`: run
  the golden suite over every registered store engine, not only the in-memory
  reference store. `core/service_runtime/service_engine_record_store.py`: the
  service scope, with the SQLite default moved here. `core/service_runtime/storage.py`:
  `ServiceCatalogBinding` resolves its default store through that factory
  instead of naming `SQLiteRecordStore`, so `ServiceRuntime(config)` in
  `runtime.py`, the failure journal in `observability.py` (which builds its
  own binding) and the ten or so checks and tools that construct
  `ServiceRuntime(config)` without a storage argument keep working without an
  edit; neither `runtime.py` nor `observability.py` is changed (both are
  edited by the consolidation worktrees).
- **Edges that must not change.** The `CatalogStore` protocol,
  `catalog_atomic_write_batch/v1`, `catalog_batch_acknowledgment/v1`, every
  service record, the host field `runtime.database_path`.
- **Checks to add first.** `a_store_without_the_atomic_batch_cannot_serve_service_writes`
  [`local.duckdb` declared for the service; roadmap D-05-T01's negative
  control]; `a_store_fallback_is_refused_by_the_slot_ceiling` [a second store
  listed as a write fallback];
  `every_store_engine_passes_the_golden_conformance_suite` [an engine that
  drops the read-set guard]; `selection_never_falls_through_to_an_undeclared_adapter`
  [`AdapterRegistry.select` returning a registered adapter the host never
  declared, as it does today after the preferred ones];
  `two_authoritative_stores_are_never_written_by_one_service` [a service
  configuration that writes one batch to SQLite and another to a second
  authoritative store]; `the_store_default_resolves_through_its_factory`
  [`storage.py` naming `SQLiteRecordStore` after D1].
- **Acceptance.** Every store suite passes; the golden suite runs on SQLite,
  DuckDB (where installed) and the reference store; the service's construction
  site leaves the baseline.

### M1. Model provider routes slot (after F5 and F8)

- **Create.** `core/model_provider_engines.py` (the facts table of
  `builtin_provider_specs` and `provider_spec_from_endpoint`, as the factory
  table of route engines), `core/model_provider_engine_checks.py`.
- **Change.** `core/model_gateway.py`: `ModelGateway.descriptors(purpose)`,
  one per route, and a route plan read from a selection decision when one is
  supplied. `core/runtime_settings.py`: read the new factory table instead of
  the parked `provider_failover.PROVIDERS`. `core/model_routes.py`: descriptor
  helpers on `RouteRegistry`.
- **Edges that must not change.** `ModelGatewayRequest`,
  `ModelGatewayConfig`, `model_gateway_result/v1` and `v2`, the `models:`
  settings, the failover semantics (`allow_failover` defaults to false).
- **Checks to add first.** `no_caller_reaches_a_provider_except_through_model_access`
  (a ratchet; its baseline is what the scan finds, at least the overnight
  runner's `make_adapter(endpoint).chat(...)` and the parked but reachable
  `code_nodes/guided_setup.py`, whose `make_adapter(ep).verify()` probes a
  provider directly from `loop-engine setup`, which the command maps to its `--setup` flag) [a new direct
  `make_adapter(...).chat(` outside the gateway];
  `the_tier_mapping_is_the_only_declaration_of_route_order` [a settings file
  that orders routes both in `models.tiers` and in an `engines` section];
  `model_slot_fallback_requires_failover_permission` (architecture 17.6);
  `settings_no_longer_read_the_parked_provider_table` [an import of
  `provider_failover` left in the settings path];
  `a_route_without_source_backed_output_capacity_is_ineligible` [a route whose
  output capacity is a guess selected].
- **Acceptance.** Every gateway suite passes; route descriptors list today's
  roster; the settings loader has no import of `provider_failover`.

### M2. Overnight runner through the slots (after M1 and X5)

- **Change.** `overnight_cli.py`: `_model_caller` reaches the model through
  `model_access` with a local endpoint route. `code_nodes/overnight_night.py`:
  the direct call becomes the visible engine `overnight_direct_local_model`
  (kind `direct_model_step`); the overnight profile's step executor slot names
  a harness engine as its initial choice with no fallback to the direct
  engine. `code_nodes/overnight_night_checks.py`: the new checks.
- **Edges that must not change.** The overnight journal records,
  `overnight_output_allocation/v1`, and the meaning of every command-line
  argument.
- **Checks to add first.** `the_overnight_runner_reaches_models_only_through_model_access`
  [a night whose model call bypasses the gateway, leaving no route attempt];
  `the_direct_step_engine_never_satisfies_a_delegation_claim` [the overnight
  profile selecting `overnight_direct_local_model` for a step that requires
  delegation].
- **Acceptance.** The overnight suites pass; the ratchet baseline of M1 loses
  its overnight entry through the desk.

### I1. Identity slot (after F9)

- **Change.** `core/service_runtime/service_engine_identity.py` (the
  descriptor from `protocol_version` and `provider_profile`);
  `core/service_runtime/browser_identity.py` (a `describe()` function only).
- **Create.** `core/service_runtime/identity_engine_checks.py`.
- **Edges that must not change.** `browser_identity/v1`,
  `browser_identity_configuration/v1`, `service_principal/v1`, the activation
  and logout records, the key records.
- **Checks to add first.** `removed_browser_identity_protocol_check_is_detected`
  (the first removed-guard control for this boundary);
  `every_identity_engine_maps_subjects_through_durable_bindings_not_token_claims`
  [a fixture profile that takes the tenant from a claim];
  `a_mode_the_host_did_not_enable_cannot_authenticate` [an external token
  accepted while `external_jwt` is absent from the host's modes];
  `a_second_identity_profile_is_a_new_factory_row_and_no_loader_edit` [a
  fixture profile that needs an edit to `load_host_application`].
- **Acceptance.** The existing 16 identity checks pass unchanged, with the new
  ones.

### B1. Billing slot (after F9 and G0)

- **Change.** `core/service_runtime/service_engine_billing.py`: one `stripe`
  engine behind the `billing_provider/v1` surface, which names exactly the
  methods the transport already calls (`handle` on the event processor;
  `options`, `create` and `configure_policy` on the session adapter),
  composing `StripeEventProcessor`, `StripeSessionAdapter` and
  `StripeSubscriptionReader` unchanged. `http.py` is not edited (R1 edits it
  in the same wave, and new method names would be a neighbour change).
- **Create.** `core/service_runtime/billing_engine_checks.py`.
- **Edges that must not change.** Every billing record, the webhook route and
  signature scheme, `billing_session_request/v1` and its result, the three
  entitlement sources.
- **Checks to add first.** `removed_webhook_signature_check_is_detected` (the
  webhook has no removed-guard control today);
  `a_billing_provider_is_never_switched_during_a_request` [a fallback after an
  outage creating a second customer]; `live_account_engine_refuses_a_test_key`
  (the accident control the owner asked to keep);
  `billing_neighbours_carry_no_provider_identifier` [a caller passing a
  `price_` identifier across the edge instead of a plan name];
  `the_billing_surface_composes_the_three_existing_objects_unchanged` [a
  billing engine that wraps a modified copy of one of the three objects];
  `the_billing_surface_names_the_methods_the_transport_already_calls` [a
  surface that renames `handle`, `options`, `create` or `configure_policy`].
- **Acceptance.** The 27 webhook checks, 32 session checks, 16 transport
  checks and four controls pass unchanged; the provider-shaped edge gap
  (`stripe_snapshot`, `service_stripe_event/v1`) is recorded as future edge
  work, not attempted here. No real card is charged.

## 10. Later packages

| Id | Package | Depends on | Content and first known-wrong check |
|---|---|---|---|
| V1 | Side-by-side comparison on hosted search | R1, F6 | `core/engines/comparison.py` with SHA-256 bucketing and a per-comparison salt; the arm runs after the primary as a Spawned Loop at the new boundary row "engine comparison arm" (applied by the desk), under an allowance that cites a separately approved authority grant, never an amount the selection policy declares; the hosted search hook lives in `core/service_runtime/service_engine_search.py`, not in `http.py`; `a_comparison_output_is_never_served_metered_or_remembered` (control), `comparison_spending_never_draws_on_the_step_allowance` (control), `comparison_sampling_is_deterministic_and_reproducible`, `a_comparison_needs_a_separately_approved_authority_grant`, `a_comparison_arm_with_an_external_effect_is_refused_before_dispatch`, `a_comparison_arm_is_cancelled_with_its_owning_loop` (known-wrong cases in architecture 17.6). Delivers roadmap D-19-T02 |
| D2 | PostgreSQL record store engine (D-05) | D1 | `catalog/stores/postgres_store.py` on psycopg 3 in a `postgres` extra (LGPL, an engineering reading recorded; pg8000, BSD, named as the fallback driver): canonical JSON as text, transaction-scoped advisory locks in sorted order, a batch digest row, unknown-commit reconciliation through that row and `pg_xact_status`; forward-only SQL migrations applied by a migration Loop; a serializable variant as a second engine on the same suite; a `postgres:18` service container in continuous integration (desk). Known-wrong: a dropped connection during commit reported as success |
| X7 | Goose through the Agent Client Protocol | X4 | Recipe record and qualification only; proves the edge fits a second harness. Known-wrong: a Goose-specific branch added to the engine module |
| X8 | Codex app-server engine | X5, C1 | `core/step_execution/codex_app_server.py`, one engine module; a JSON lines client in the standard library; the generated schema pinned by digest per Codex version; reuses `core/step_execution/session_process.py` after C1 has put confinement behind its slot. Known-wrong: a schema digest mismatch accepted |
| X9 | Claude Code stream engine | X5, X1, C1 | `core/step_execution/claude_code_stream.py`, one engine module; print mode with streamed JSON and bare configuration; effect requests answered by a permission tool the envelope controls; the relay's existing Anthropic Messages codec (`decode_anthropic_text_request` and `encode_anthropic_text_response` in `core/harness_lightweight_recipes.py`, text only today, used by nanocode) extended to streamed and tool-use traffic (X9 owns that module and `core/harness_process_relay.py` while it runs; no other package of its wave edits them). Known-wrong: inherited user configuration loaded. Legal decision for the owner before shipping any Anthropic kit |
| X10 | Harness selection converges on the general rule | F4, X5 | `select_harness` calls the lifted rule; the harness evidence records converge on the engine records with callers updated together (pre-launch policy). Known-wrong: the two rules ordering the same evidence differently |
| C1 | Process confinement slot | X4 | `core/process_confinement_engines.py`; Bubblewrap as the first engine; one egress proxy with a domain allowlist from the step's authority; a container engine next. C1 owns the confinement code in `core/harness_process.py` and `core/step_execution/session_process.py` while it runs, so X8 and X9 start after it. Check `harness_process_refuses_without_an_available_confinement_engine`. Known-wrong: a process started unconfined when `bwrap` is missing |
| P1 | Second protocol endpoint version | R1, F9 | Serve `2026-07-28` and `2025-11-25` by explicit negotiation with the 2.x software kit, answer discovery, refuse others with the supported list. P1 owns the `/mcp` branch of `core/service_runtime/http.py` and `core/provisioning_mcp.py` while it runs; V1 does not edit them. Check `a_second_protocol_version_is_selected_only_by_exact_negotiation`. Known-wrong: a request served under the older version when both sides support the newer |
| F14 | Engine write commands | F12 | `enable`, `disable` with effect digest approval and dated backups, `qualify`, `retire`, `restore --plan`. Checks `enable_and_disable_change_only_the_installation_flag` and `restore_takes_exact_paths_and_never_merges_the_checkpoint_branch`. Known-wrong: a disable that also edits a policy; a restore plan accepting a merge |
| W1 | Web research engines | Owner decision | Restoring the parked web research engines behind `web_research_request/v1` is turning a parked capability back on, a recorded owner decision under the branch strategy. Check `the_web_research_port_reports_unavailable_on_main`. Known-wrong: research recorded as done with no live engine |
| X11 | A fresh instance for every step, per harness (S-6.42) | X4, X5 | The recorded test S-6.42 asks for: Codex, Claude Code, OpenCode and Pi each started as an independent instance with only the step's files, and the result written as the executor profile's `fresh_instance_per_step`; a harness that cannot is marked unsupported for one-harness-per-step; ZCode is tried as a candidate through its app-server path and listed only after isolation, cancellation and native loading are tested. Each harness records the highest rung of the S-6.31 qualification ladder it reached. No model calls where the test can avoid them. Check `a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step`. Known-wrong: a harness whose instance reads a user-level configuration file or a previous step's session selected for a step that requires one harness per step |
| N1 | Library ingestion engine slot (S-6.40) | F1, F3 | The `library_ingestion_source` slot in `core/library_ingestion/` (folder skeleton by the desk): one module per source reader, the offline preparer `tools/prepare_harness_candidates.py` wrapped as the first reader, network readers only under the ingestion Loop's grant; every item a candidate until independent review, carrying the versioned per-source provenance record S-6.40 asks for (origin, immutable revision, path, source digest, licence evidence, fetch date) and, for a skill with scripts, references or assets, a multi-file package. Checks `every_ingested_item_carries_its_source_provenance`, `an_item_without_an_accepted_licence_is_never_imported_verbatim`, `an_ingested_item_stays_a_candidate_until_independent_review`, `a_duplicate_item_is_merged_not_added` (known-wrong cases in architecture 17.8) |
| H1 | Harness run records into the evidence pipeline (S-6.41) | F6, X3 | The consented, metadata-only run record of a customer's harness step (how it broke the problem down, which items it loaded, whether it was accepted) as an attempt record the compiler of F6 reads; raw prompts, code or data only with explicit opt-in. Known-wrong: a record carrying prompt text or a credential shape stored; a record from a tenant without a consent scope compiled into shared evidence |
| M3 | Model call strategy slot (S-6.60) | M1, F3 | The `model_call_strategy` slot in `core/model_call_strategy/` (folder skeleton by the desk), nested between the step and `model_access`: the edge and the pass-through engine first (exactly today's single call), then one module per strategy (one model chosen from the customer's configured models, a vote, a disagreement chain, a resolution chain), each a new engine behind the same edge; the harness or step sets preferences, which flow to the gateway; every physical call still goes through `model_access`. Checks `a_strategy_that_needs_more_calls_than_the_step_allows_is_refused_before_the_first_call` and `agreement_among_models_is_evidence_never_acceptance` (known-wrong cases in architecture 17.8). No live model call without the owner's authority |
| L1 to L4 | Folder moves of the flat families (architecture 7.8) | Each after the last package that edits the family's files has merged | One family per commit under the folder-depth record, public import path unchanged and no behaviour change: L1 the harness family into `core/harness/` (recipes and process runner), L2 the retrieval family into `core/retrieval/`, L3 the model provider family, L4 the workspace and confinement family; the architecture map, the folded self-test list and every module string move in the same commit. Known-wrong: a move that also changes behaviour, or a module string left pointing at the old path |

Slots without an adoption package in this plan stay `planned` or `candidate`
in the catalogue: `typed_decision`, `response_evaluator`, `workspace_backend`,
`similarity_candidate_source`, `runtime_memory`, `tool_protocol_transport`,
the three public ports, `configuration_setter`, `run_history_export`,
`catalogue_body_store`, `catalogue_qualification_resolver`,
`request_limit_state`, `failure_journal`, `secret_resolver`, `usage_export`,
`credential_authentication`, `customer_client_recipe`,
`material_install_layout`, and the release-time slots. When one is adopted,
the registration desk records it as a new step under D-19, and its first work
is the checks architecture 17.8 lists for it, each with its known-wrong case.

## 11. Verification commands for every package

Run these on an export of the exact tree, in a folder under `$HOME` outside
the repository (the machine's `/tmp` is quota-limited and the root disk is
near full), in a fresh virtual environment with `pip install -e '.[all]'`.
Create the export with `git worktree add --detach "$HOME/le-export-<ID>" <commit>`
and remove it afterwards.

```text
Owning suite, one module at a time
  PYTHONPATH=src python -c "import importlib; m = importlib.import_module('loop_engine.core.<module>'); r = m.self_test(); t = r['tests']; print(sum(1 for x in t if x.get('passed') is True), 'of', len(t))"

The continuous integration commands (from .github/workflows/ci.yml)
  python -m loop_engine --self-test
  python -m loop_engine --conformance
  PYTHONPATH=src:tools python -m unittest discover -s tools -p 'test_*.py'
  PYTHONPATH=src python tools/check_component_guides.py --run-documented-checks
  PYTHONPATH=devtools/src python -m loop_engine_devtools.cli --self-test
  PYTHONPATH=devtools/src python -m loop_engine_devtools.cli --hardcoding-audit \
      --allowlist devtools/hardcoding-allowlist.yaml \
      --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
  PYTHONPATH=src:devtools python -m unittest discover -s devtools/embodiment_lab/tests -v
  (cd devtools/qualification_lab && python -m unittest -v test_runner.py)
  node tools/check_publish_guard.mjs
  the "Examples run" and "Product solve acceptance" steps of ci.yml, exactly as
  written there, whenever the package touches a module an example imports
  (every package that changes search, model access, the overnight runner or
  the harness path does)

Documentation, the full scope, as AGENTS.md requires (the documentation job of ci.yml)
  npx --yes markdownlint-cli2@0.23.2 AGENTS.md README.md CHANGELOG.md \
      CONTRIBUTING.md SECURITY.md humanizer-context.md showcase/README.md \
      'docs/**/*.md' 'case-studies/*.md'
  the two ripgrep commands of the "Refuse retired public language" step,
  exactly as written in ci.yml
  Vale and the offline link check run in continuous integration; run them
  locally too when the tools are installed

Removed-guard controls
  for each new guard: delete it in the export, run the owning suite with a fresh
  PYTHONPYCACHEPREFIX, confirm the named control fails, then restore it
```

The hand-off report lists every command, its exit status and its counts, the
mutants run and their results, and the registration request.

## 12. Acceptance of the whole program

| Roadmap case | Proof level | Delivered by |
|---|---|---|
| S-6.30 acceptance: every functional component names its edge, engines and selection; adding an engine changes one adapter and one declaration and no call site; every selection is recorded with its reasons | `local_contract` | F1 to F13 |
| S-6.30 verification items added at `4249eca`: engine preferences sent by a harness or a Loop, applied within its authority; slots nested at every level; one folder per functional component and one module per engine; the earlier custom loop-node engine kept restorable | `local_contract` | F1 and F3 (preferences and nesting), X3 (the step result's `engine_preferences`), the folder skeletons of section 5.1, F7 (placement check) and L1 to L4 (moves); the restore procedure of architecture 11.6 and 13.10, planned for F14 |
| S-6.40 acceptance: the ingestion worker adds reviewed, licensed items without manual work | `local_contract` first | N1 |
| S-6.41 acceptance: consenting customers contribute run records that improve item ranking and engine choice | `held_out_comparison` | H1 with F6; ranking changes only through the evidence rule |
| S-6.42 acceptance: each supported harness starts a fresh instance per step with exactly the selected material, proven by a recorded test | `local_contract` | X6 (for the engines it uses), X11 (Codex, Claude Code, OpenCode, Pi; ZCode as a candidate) |
| S-6.31 items added at `0f1c690`: a qualification ladder per harness, a pinned first Agent Client Protocol profile, a fresh process for each step | `local_contract` | X4 (pinned profile, one session process per attempt), X6 and X11 (ladder rungs) |
| S-6.60 acceptance: a step runs through any strategy by configuration alone, and the decisions show when several models helped and when one was enough | `local_contract`, then `held_out_comparison` under the owner's model-call authority | M3 |
| D-19-T01: register a new engine in one slot with only its adapter and declaration; it becomes selectable after qualification with no call-site change; an engine missing a capability is removed at eligibility with a recorded reason | `local_contract` | F3 with the check `adding_an_engine_by_registration_changes_no_call_site`, then the slot instances in X5 and R1 |
| D-19-T02: two engines side by side on a deterministic sample; decisions and measurements identify which engine served each request; evidence below the minimum sample leaves the declared order unchanged | `held_out_comparison` | V1 on hosted search, with F4 and F6 |
| D-19-T03: delegate one real step through a harness engine chosen by the executor slot; result, cost, time and acceptance recorded; a second harness replaces the first by configuration; an in-process engine is refused | `end_to_end` | X6 at `local_contract` now; the `end_to_end` run after the owner grants model-call authority |
| S-6.31 acceptance: one real step through a harness engine chosen by the slot, with cost, time and acceptance recorded | `end_to_end` | As D-19-T03 |
| S-6.32 acceptance: served search chooses its policy by declaration, reports a poor match honestly, and a new ranking engine is added without touching the route | `local_contract`, then `held_out_comparison` | R1, R2, V1 |
| S-6.28 phase 2: one executable step goes only through a harness; a delegation claim met by the in-process path is the known-wrong case | `local_contract` | X3, X5, X6 |

A count of passing checks is not a working customer journey. Offered,
fetched, loaded, used and verified stay separate facts in every report.

## 13. What needs the owner

- Model-call authority for the `real_provider` and `end_to_end` proofs (X4,
  X6), for evidence trials of model-backed engines, and for any comparison
  that calls models on the operator's account.
- Turning a parked capability back on (W1, or an in-process runner restored
  as a custom Loop harness engine), per the branch strategy.
- Legal commitments: shipping any Anthropic software development kit inside
  the product (X9); accepting a copyleft licence in a shipped extra if the
  engineering reading is not enough (D2 names the BSD-licensed pg8000 as the
  fallback, so this never blocks).
- Destructive provider operations, none of which any package here needs.
- The owner's own wording. `AGENTS.md` and the README call Loop Engine "the
  engine"; this plan keeps that text and qualifies the slot meaning instead
  (architecture section 2). Rewording the owner's text is the owner's call,
  and nothing in this plan waits for it.
- A comparison or trial that spends model calls: its allowance must cite an
  authority grant the owner approved for exactly that comparison.

Everything else in this plan is an engineering decision, taken with its reason
under the owner's direction to decide and record rather than ask.

## Rules check

Kind: adversarial review of this plan, September 22, 2026, against
`AGENTS.md`, `ASTRA.md`, the Constitution, `architecture.yaml`,
`terminology.yaml`, `.github/workflows/ci.yml` and the source and worktrees at
`main` `230c91e`, with the roadmap read again at `0f1c690`, which landed
during the check. The repository was read, never changed. The architecture's
own "Rules check" lists the design corrections this plan now implements; the
table below lists what changed in the plan itself.

### What held

- No package creates a second runtime type or a class whose name ends in
  `Node`; every envelope, the selection procedure and the evidence compiler
  run as Loops at registered boundaries.
- No package creates a parallel registry: each slot's factory table follows
  the existing `ADAPTER_FACTORIES` pattern, and the registration desk is a
  working process, not a registry.
- Every package lists the edges it must not change, and the two deliberate
  edge versions (R1) follow the edge-change procedure.
- No package needs a destructive provider operation, a live charge or model
  calls; the owner-only items are in section 13.

### Issues and corrections

| # | Issue found | Correction made |
|---:|---|---|
| 1 | Roadmap and source state were stale: D-19 has six steps since `4249eca` (S-6.40, S-6.41, S-6.42 added) and S-6.30 gained four verification items; `main` is `230c91e` | Header; new packages X11 (S-6.42), N1 (S-6.40), H1 (S-6.41) in section 10; section 12 acceptance rows for every new item |
| 2 | S-6.30 and `AGENTS.md`: one folder per functional component and one module per engine. Every new module was flat in `core/`, and `TextRelayStepEngine` sat inside the factory table module | Rule 5; framework paths moved to `core/engines/`, step execution to `core/step_execution/`, `TextRelayStepEngine` to `core/step_execution/text_relay.py`; the folder skeletons of section 5.1; folder moves L1 to L4; the placement detector in F7 |
| 3 | F1 and F2, both in wave A, would each have to create `core/engines/__init__.py` | The registration desk commits both folder skeletons before wave A (section 5.1) |
| 4 | `AGENTS.md` and D-19: search for existing projects, designs and papers before building, and record the decision; no rule required it | Rule 8 |
| 5 | Rule 1 said to lint the documentation a package touched; `AGENTS.md` requires the full documentation scope | Rule 1 and section 11 use the full scope of the documentation job |
| 6 | Section 11 omitted continuous integration steps: the qualification lab, the publication guard, the example battery and product acceptance, the retired-language checks, Vale and the offline link check | Section 11 extended, commands as written in `ci.yml` |
| 7 | "Package INT" was an abbreviated name in a title; package identifiers such as F1, E1 and C1 also collide with the inventories' finding and record identifiers | "The registration desk" throughout; an identifiers note in the header |
| 8 | Shared files omitted the verified installed copy `src/loop_engine/data/terminology.yaml` (`semantic_conformance` refuses a difference), the installed `architecture.yaml`, `component_folder_map.yaml` and the semantic ambiguity register; F1 still asked for the withdrawn Loop Engine definition change | Section 2 table extended; F1's registration request keeps the owner's definition and adds the qualified term |
| 9 | The G0 table said r2 and r3 had no changes; both now edit files this plan needs (`AGENTS.md`, `ASTRA.md`, `CLAUDE.md`, the component guide map and README, the hardcoding allowlist, the journey container check, `tools/test_search_quality.py`), and r1 and g1 also edit `runtime.py`, `observability.py` and `service.js` | Section 3 table rewritten with the observed heads; the desk holds its edits of the documents r2 and r3 rewrite until G0; the line-survival check covers the shared registration files; R1 waits for G0 |
| 10 | B1's renamed billing surface would force an edit to `http.py`, which R1 edits in the same wave, and would be a neighbour change | B1's surface names the methods the transport already calls; `http.py` is not edited |
| 11 | D1's "construct only what the loader passes" would break `ServiceRuntime(config)` in `runtime.py`, the failure journal in `observability.py` (both edited by the consolidation) and about ten checks and tools | The default resolves through the record store factory module; no caller changes; check `the_store_default_resolves_through_its_factory` |
| 12 | F3 edits `core/event_vocabulary.py`, whose own suite is parked, and F11's scope left it out | F11 re-collects it; F3 merges after F11 (graph, waves, F3) |
| 13 | X1 loading its catalogue through `load_component_resource` would edit `core/component_contracts.py`, which F2 edits in the same wave | X1 uses its own typed loader; a later desk request can register the name |
| 14 | Wave G packages had no ownership: C1, X8 and X9 would all touch the confinement and session code, V1 and P1 the service transport | Ownership and order in the wave table and the rows of section 10 (C1 first; V1 hooks into the search factory module; P1 owns the `/mcp` branch) |
| 15 | R1's version change missed consumers that pin `service_retrieval_result/v1` (`tools/install_selected_material.py`, `tools/check_client_journey_in_containers.py` and its test), three documents, and the users of the policy records (`examples/30_search_quality`, `tools/test_search_quality.py`); its capabilities change would have altered `service_capabilities/v1` for four outside consumers | R1 lists every consumer; the capabilities keys stay; check `hosted_capabilities_keep_their_retrieval_keys` |
| 16 | F5 missed the live typed decision path, which also names `"model_gateway"` as the implementation, and the existing `OperationCostLedger.compare`, which ranks on producer-written acceptance with a code default of two samples | F5 changes `core/decisions/gateway.py` and turns the ledger comparison into a report no selection reads; two checks added |
| 17 | M1's ratchet baseline listed only the overnight runner; the parked but reachable `code_nodes/guided_setup.py` probes a provider directly from `loop-engine setup` | M1: the baseline is the scan's output, with both known sites named |
| 18 | F2 and F7 hand-listed five construction sites; `record_cli.py` is a sixth | F2 names six; F7 replaces the list with its scanner's output |
| 19 | X2 presented refusing a duplicate identifier as new; the registry already refuses it unless `replace=True` | X2 corrected; check `one_engine_identifier_names_one_implementation` |
| 20 | X1 counted five code edits and would mount only the recipe's own module; the relay's wire choice is a sixth edit, and the wire codecs live in other recipe modules | X1 corrected; check `recipe_module_mount_and_digest_follow_the_selected_recipe_and_its_wire_codec` |
| 21 | X9 planned "an Anthropic Messages wire in the relay"; a text-only codec already exists | X9 extends the existing codec |
| 22 | X4's session process was "long-lived", against the `AGENTS.md` default of a fresh harness for every step | X4: one session process per step attempt; check `a_session_process_never_outlives_its_step_attempt`; X6 records a fresh-instance proof for the engines it uses |
| 23 | About forty checks named no known-wrong case, so a removed guard could not be shown to fail a named check | Known-wrong cases added in brackets to every one (F1, F2, F5, F6, F8, F9, F12, F13, X2 to X6, R1, R2, E1, D1, M1, M2, I1, B1) |
| 24 | Check names differed from the architecture for the same check, and F1's decision flag used a new name for the existing `model_call_performed_by_boundary` | Names aligned; the existing flag name kept; the `declared-order` binding noted as new, wrapping the existing `ExistingOrderPreference` |
| 25 | Architecture checks with no package: projection and descriptor checks, the unknown-kind factory refusal, archived engines, qualification without authority, the comparison arm checks, the operational rollback drill, and every check of slots with no adoption package | Assigned to F3, F7, V1, F9, F14, W1, C1 and P1; the unscheduled slots listed at the end of section 10 with their checks as the first work of each future package |
| 26 | Harness preferences, nesting and the comparison allowance (architecture issues 2, 3 and 10) had no package | F1 (record fields and checks), F3 (admission, nesting, base case), X3 (`engine_preferences` in the step result), V1 and section 13 (approved grant) |
| 27 | The rules did not mention the retired vocabulary, although the conformance gate refuses retired words in source and the documentation job refuses them in `docs/`, and the architecture had used one in a known-wrong case (architecture issue 30) | Rule 5 and F13 require the replacement words the `terminology.yaml` vocabulary names; generated pages and fixtures included |
| 28 | Roadmap `0f1c690`, which landed during this check, added S-6.60 (the layer that decides one model or several), S-6.31's qualification ladder and fresh process per step, S-6.40's provenance contract and multi-file packages, and ZCode as an S-6.42 candidate | Header; package M3 and its folder skeleton; X4, X6 and X11 record the ladder and the fresh process; N1 carries provenance and packages; section 12 rows |

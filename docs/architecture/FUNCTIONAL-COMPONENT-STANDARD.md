# Functional component standard

Every functional component keeps one fixed, typed and versioned edge
contract, and every implementation behind that edge, whether written here or
taken from an outside project, is an engine of the component's one engine
slot that a host can install, select, test and replace without changing any
caller.

A functional component is internal structure used by work that a classified
Loop owns. The complete Loop classification comes first, as `AGENTS.md`
requires, and the functional component tree follows it.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

None of the parts below is a graph vertex, a runtime type or a scheduler.

```text
Functional component (one job, one owner, reached only through its edge contract)
├── Edge contract (fixed for one contract version)
│   ├── request and result records (name/vN, strict readers, one validation profile)
│   ├── interaction rows: delivery, retry owner, timeout, cancellation, compatibility,
│   │   authority transfer, failure, repair, verification, Run History
│   ├── required request fields and advisory request fields
│   ├── stream semantics, for an edge whose call pattern is stream
│   └── the declared unavailable answer
├── Envelope Loop (the registered boundary Loop that holds the edge constant)
│   ├── validates, selects, binds, dispatches, measures and validates the result
│   └── owns engine instances, engine leases, owned resource records and cleanup
├── Engine slot (the one swap point: one record in engine_slots.yaml)
│   ├── engine protocol and version, engine kinds, factory table, native registry
│   ├── selection mode: one_of | set_of | derived | all_of (proposed)
│   ├── fallback ceiling, failure kinds, ranking objectives, evidence floor, scope fields
│   ├── permitted call patterns, instance lifetimes and swap rule (proposed)
│   ├── Baltor-native engine track: required | optional | not_applicable (proposed)
│   ├── one conformance kit
│   └── nested slots, reached only through the envelope
├── Engines (adapters that a Loop uses)
│   ├── Baltor-native engine: code written here, or a fork kept here
│   ├── engine adapter: translates to an outside project pinned by revision and licence
│   └── composite engine: a declared engine composition over nested slots
├── From identity to one call
│   ├── engine identity: engine_id@engine_version with an implementation digest
│   ├── engine installation: the engine with typed settings, execution fields, lifetime
│   ├── slot configuration: installed engines and one selection policy per scope key
│   ├── engine instance: one started copy, with an owned handle and a fencing token
│   ├── engine lease: one attempt's expiring hold on a shared engine instance
│   ├── engine session: state kept across calls inside one attempt
│   ├── engine attempt: one dispatch under one execution specification digest
│   └── state binding: owner, format version, owner fencing token, lifetime
├── Selection
│   ├── selection basis on every decision: pinned | preferred | automatic
│   ├── engine preference kinds: pin, exclude, prefer, declared_order_only, objective
│   ├── selection decision: before dispatch, every refusal, propensity, parent, predecessor
│   └── a change applies at the slot's next selection phase, or under its swap rule
├── Composition
│   ├── selection level: ordered fallback, escalation cascade, routing, shadow comparison
│   └── engine level: pipeline, branches and merge, race, partitioned, fused, router
├── Status
│   ├── alive, ready, capacity: expiring facts of one engine availability snapshot
│   ├── binding facts of one slot: desired, prepared, routable, observed, rejected
│   ├── qualified: an independent engine qualification of one installation
│   └── result verified: an independent verdict on one result
└── Tests
    ├── conformance kit: each engine alone
    ├── composition test: joined and nested slots together
    ├── journey test: one customer path end to end
    └── inside them: lifecycle drills, containers, properties, comparisons, mutants
```

Kind: standard, draft for review. Status: proposed. Every statement below is
a proposal until its check is collected by the main self-test and
`architecture.yaml` carries its entry; the "Today" line of each statement
says what the repository does now. Roadmap: S-6.84 (write the standard into
the rules), with S-6.30, S-6.72, S-6.73, S-6.74, S-6.75 and the delivery
packages D-19, D-27 and D-28. The roadmap stays the only task authority.

Intended path: `docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md`. Links are
written for that path.

Base: `origin/main` at `e6346075` (September 24, 2026, 10:15 New York time).
Between `f6a7fb2c`, the base of the first draft, and `e6346075`, none of the
engine records, the slot catalogue, the interaction catalogue, the design, the
lifecycle modules or the route check changed; `model_gateway.py` gained one
error code, `tools/install_selected_material.py` gained four layout rows,
`AGENTS.md` changed outside rule 6, and two scheduled workflows arrived,
`live-pulse.yml` and `research-watch.yml`. Nothing under `src/` changed
between `3d48a36c`, the base of the second draft, and `e6346075`, and every
probe of the second draft ran again on an export of `e6346075` with the same
results, apart from the number of connection attempts of the retrieval
self-test, which depends on the cache folder (ran: `git diff --stat`; the
probe outputs are listed in the research record).

Landing note (September 24, 2026): the change that added this standard to
`main` also catalogued the four library ingestion slots that adoption step 2
names. `library_format_validation`, `library_safety_scan`,
`library_near_duplicate` and `library_outline` are planned slots with one edge
row each, and the slot index gained a join that reports a slot a factory table
declares when the catalogue lacks it or records other engine kinds or another
selection mode, checked by
`core.engines.slot_checks:every_slot_a_factory_table_declares_is_catalogued_with_its_kinds_and_mode`.
The catalogue now holds 49 records, 38 candidate and 11 planned.
`library_ingestion_source` still carries engine kinds that the code does not
have and is held on that join's shrinking baseline; the rest of step 2 is
open. Every other "Today" line and count below describes `e6346075`.

This standard extends two things and replaces neither:
[Engines behind fixed edges](ENGINES-BEHIND-FIXED-EDGES.md), the design with
its reasons, and
[`engine_slots.yaml`](../../src/loop_engine/data/engine_slots.yaml), the slot
catalogue. It adds no registry, no scheduler, no store and no runtime type.
The research behind it is the
[engine composition and lifecycle variations research](../research/ENGINE-COMPOSITION-AND-LIFECYCLE-VARIATIONS-RESEARCH-2026-09-24.md)
of September 23 and 24, the committed
[functional engine wrapping research](../research/FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md)
and the [ecosystem edge map](../research/ECOSYSTEM-EDGE-MAP-2026-09-23.md).

| Part | Today on `e6346075` | This standard proposes |
|---|---|---|
| Slot catalogue | 45 `engine_slot/v1` records: 38 candidate, 7 planned, 0 active; selection modes one_of 27, set_of 11, derived 7; the index reports 0 findings (ran, writer) | Catalogue the four missing library ingestion slots; `engine_slot/v2` fields; a fourth selection mode, all_of |
| Engine records | 13 record types in `core/engines/`; no module outside that package writes one (source) | Version the records that gain fields once and together; add `engine_instance/v1`, `engine_lease/v1`, `engine_availability_snapshot/v1`, `owned_resource/v1` and `conformance_kit_report/v1` |
| Selection | No shared selector. `resolve_preference` (the `ranking_strategy` slot's engine) and `select_harness` exist; library ingestion keeps its own selector and record | One selector built on those owners, pinned and preferred first |
| Edges | 53 interaction rows; 40 of their 93 contract names are defined in no Python file (ran, repository grounding line) | Validation profiles, conversion declarations and stream semantics defined once in the interaction catalogue |
| Kits | 30 slots name a suite, 28 are collected, 15 name none; only `run_store_conformance(store)` takes an engine (ran, writer) | One conformance kit per slot, broken engines, one kit report record, a nightly tier and a release gate |
| Lifecycle | Supervisor, hibernation and credential leases are reached only from the self-test (source) | Instances, leases, availability snapshots and owned resource records under one set of lease rules |
| Composition | Nested slots in the catalogue; no composite engine; the Loop scheduling vocabulary is parked | Composite engines in strategy slots, sequential forms first |
| Words | Eight engine words in `terminology.yaml`; ambiguity entry SEM-025 | 41 new vocabulary entries, 8 retired outside names and register entries SEM-026 to SEM-049 |

## The owner's words, September 23, 2026

- "Do more research on this, more variations of this, more seperation,
  wrapping, engine components, etc"
- "Consider the following and more ways we can have functional components,
  that have multiple functional engines that are wrapped around a
  contract/edge/typed input output, I'm not sure the best way to phrase this
  and implement it into our development rules but we need osmething like
  this"
- "I also want to make sure we are making appropriate simplified,
  abstractions, containerizations, and testing functional components
  individual, in groups, etc, and making clear seperation, and contracting
  component functionality even if different engines operate the actual
  functional execution, we should also create a clear index and manage that
  to make sure discussions, nomeclature, and things are simple,
  non-conflicting, non-conflcated, etc."
- "everytime we pull a project from github, we should containerize/wrap it
  as a functionality component then build our own variation and allow easy
  selection and swap out of functional engines that accomplish that task"
- "heavily research, standardize, and implement the appropriate a typed
  versioned component interface with selectable engines for all aspects of
  this project for maximum robustness, modularity, real time selection of
  preferences of engine, easily maintain, improve, etc"

[Rule 6 of the commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
carries these words and links this standard. The owner's words keep the
owner's meaning; the terms below are engineering's reading of them.

## How to read the statements

- The key words MUST, MUST NOT, SHOULD and SHOULD NOT carry the meanings of
  BCP 14 (RFC 2119 and RFC 8174) for the statements of this standard, and
  only when written in capitals. The
  [Constitution](CONSTITUTION.md#normative-language) keeps its own
  definitions for its own invariants and does not cite BCP 14.
- Each statement has a stable identifier, exactly one key word and one
  requirement. Lowercase "may" and "must" in explanations are ordinary
  English.
- "Maps to" names the field, record, file or check the statement constrains.
- "Enforced by" names one or more of: an **existing** check that the main
  self-test collects, written with its module, or an **existing gate** of the
  conformance report, or an **existing refusal** code in source; a
  **designed** check, named in section 17 of the design or in a slot's
  `planned_checks`; a **new** check that this standard adds, with the
  known-wrong case it must refuse; or a **review** by a named role.
- Review roles: the **independent reviewer** is a person or agent session
  that did not produce the change under review; the **integration reviewer**
  is the independent reviewer who performs the reviewed merge to `main`.
- "Today" starts with one state word: **holds**, **partly**, **fails**,
  **designed** or **not built**, then gives the evidence label: **ran** (a
  probe ran; "ran, writer" means it ran for this standard on an export of
  `e6346075`), **source** (read in repository or outside source) or
  **claim** (stated elsewhere and not rechecked). The research line or
  verifier that found a fact is named in brackets.
- Every SHOULD statement says when it may be set aside.
- Reasons live in the design and the research records. This standard states
  rules.

| Section | Identifiers | Subject |
|---|---|---|
| 1 | LE-EDGE-001 to 013, LE-SLOT-001 to 011 | Contract, edge and engine slot |
| 2 | LE-ENGINE-001 to 011 | Engines and engine adapters, with separated duties |
| 3 | LE-INSTANCE-001 to 027 | Definition, configuration, instance, lease, session, invocation and state |
| 4 | LE-LIFETIME-001 to 007 | Lifecycle profiles, written as call pattern, instance lifetime and instance owner |
| 5 | LE-SELECT-001 to 022 | Selection (pinned, preferred, automatic) and decision records |
| 6 | LE-COMPOSE-001 to 015 | Composition, with the declared and the resolved engine composition |
| 7 | LE-SUPPORT-001 to 014 | Support reports and required semantics |
| 8 | LE-STATUS-001 to 012 | Status: alive, ready, capacity, qualified, result verified, and binding facts |
| 9 | LE-TEST-001 to 015 | Testing at three levels, and containers |
| 10 | LE-ISOLATE-001 to 008 | Isolation and the choice of execution |
| 11 | LE-OUTSIDE-001 to 008 | Outside projects: an engine adapter pinned by revision and licence, and a Baltor-native engine track |
| 12 | LE-NAME-001 to 008 | Names |
| 13 | LE-RULE-001 to 005 | Writing and changing this standard |

## Rules that already apply

These rules keep their own homes. This standard links them and does not
repeat them.

- One Loop runtime: every executable graph vertex is a Loop, and an engine is
  an adapter that a Loop uses, never a runtime type or a second scheduler
  ([AGENTS.md](../../AGENTS.md#one-loop-runtime),
  [LE-NODE-001](CONSTITUTION.md#le-node-001)).
- A descendant Loop narrows permissions and never broadens them
  ([LE-PERM-001](CONSTITUTION.md#le-perm-001)).
- Prose, labels, folder paths and retrieved text never control permissions,
  routing or execution ([LE-DOC-001](CONSTITUTION.md#le-doc-001),
  [LE-TRUST-001](CONSTITUTION.md#le-trust-001),
  [LE-INTEL-002](CONSTITUTION.md#le-intel-002)).
- A producer never approves its own work
  ([LE-GOV-001](CONSTITUTION.md#le-gov-001)).
- Versioned contracts, and runtime negotiation between separately deployed
  parts ([pre-launch version decision](ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)).
- Every new check names its known-wrong case, and a removed guard fails a
  named check (the
  [working cycle](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle)).
- Never replace a failed model call with invented output; retry, fallback,
  failover and repair stay distinct; failover needs explicit permission
  ([AGENTS.md, models and providers](../../AGENTS.md#models-and-providers)).
- Discovery is effect-free, and effects need typed authority
  ([AGENTS.md, effects, workspaces and external tools](../../AGENTS.md#effects-workspaces-and-external-tools)).
- Imported and self-generated material stays a candidate until independent
  review ([AGENTS.md, intelligence rules](../../AGENTS.md#intelligence-rules)).

## Statements

### 1. Contract, edge and engine slot

The edge contract is what neighbours see. The engine slot is the one place
where engines plug in; the design calls it the owner's swap point.

#### LE-EDGE-001

Every functional component MUST have one edge contract: versioned request and
result record types, named in its rows of `component_interactions.yaml`,
where each row states delivery, retry, timeout, cancellation, compatibility,
authority transfer, failure, repair, verification and Run History.

- Maps to: `component_interaction_catalog/v1` rows; `interactions` in `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:every_interaction_names_exact_versioned_contracts_and_known_components`; existing `core.engines.slot_checks:every_engine_slot_edge_is_read_from_its_interaction_rows`.
- Today: holds as declarations. 53 rows fill every field, and the 37 run-time slots join 46 of them (ran, writer).

#### LE-EDGE-002

An interaction row or an engine slot MUST NOT be active while a request or
result record that it names is undefined in code.

- Maps to: `implementation_state` of interaction rows and of `engine_slot/v1`.
- Enforced by: new `an_active_slot_or_row_names_only_defined_contracts` (known-wrong: the active row `core.interaction.prompt.invoke_model`, whose request `model_invocation_request/v1` appears in no Python file, although two classes named `ModelInvocationRequest` exist).
- Today: fails. 40 of the 93 contract names in the 53 rows appear in no Python file, in 28 rows; three of those rows are active and one is a partial mapping (ran [repository grounding line]; confirmed by its verifier; the example rechecked, ran, writer).

#### LE-EDGE-003

When no engine is eligible or every engine is switched off, the edge MUST
return the unavailable answer that its slot record declares, never an
exception.

- Maps to: `unavailable_result` in `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:every_edge_contract_declares_an_unavailable_result` (the declaration); existing refusal `active_slot_is_not_complete` (a slot whose declared answer does not exist yet cannot be marked active); new `every_declared_unavailable_answer_is_produced_by_the_edge` (known-wrong: a switched-off slot whose edge raises).
- Today: partly. The gap is declared openly: 19 of the 37 run-time slots record `answer_exists: false`, and the slot reader refuses to mark such a slot active (source [rule and names verifier, September 24]). No check yet runs an edge with every engine switched off.

#### LE-EDGE-004

Every engine behind one engine slot MUST return the same result record type
and the same keys for one edge contract version, including for sparse records
and for records that carry keys the edge does not name.

- Maps to: `supported_edge_contracts` in `engine_descriptor/v1`; the slot's conformance kit; design rule 13 ("one result shape per edge version").
- Enforced by: designed `a_changed_engine_does_not_change_the_edge_record`; new `stores_return_the_same_keys_for_sparse_and_extra_key_records` (known-wrong: the SQLite and DuckDB store engines).
- Today: fails. For a record written with two keys, the SQLite and DuckDB engines return nine, seven of them empty, and they silently drop a key that the in-memory, package JSONL and DuckDB file engines keep (ran [testing line]; confirmed and widened by both verifiers, the second on `2658b7bb`).

#### LE-EDGE-005

An edge change that an older reader cannot honour MUST be a new record
version, with every in-repository producer, consumer and engine changed in the
same commit.

- Maps to: `name/vN` record types; section 11.7 of the design.
- Enforced by: existing `core.engines.selection_records_checks:every_engine_record_refuses_unknown_keys_and_unsupported_versions`; existing `core.engines.slot_checks:a_slot_record_refuses_unknown_keys_and_unsupported_versions`; designed `unsupported_edge_version_is_ineligible_before_dispatch`.
- Today: partly. Enforced for the engine records; designed for edges.

#### LE-EDGE-006

Every separately deployed client of the hosted service (a released installer,
a downloaded client extension, a customer's local engine) MUST be served under
the request version it declares, or refused with the list of supported
versions before any effect.

- Maps to: runtime negotiation in the pre-launch version decision; `request_record_type` in the service capabilities record; `tools/install_selected_material.py`; the Pi extension `src/loop_engine/core/service_runtime/web_assets/pi/baltor.ts`.
- Enforced by: new `every_supported_client_version_verifies_against_the_release_candidate` (known-wrong: the installer as released at `56639ee6`, which sends `service_retrieval_request/v1` and is refused with status 400 and `unsupported_version`).
- Today: fails for the Python installer and is untested for the extension. The installer imports the service's own version constant and never reads `retrieval.request_record_type`, so in-repository tests cannot see the break; a consumer contract of the `56639ee6` installer fails against today's service in 0.53 seconds (ran [qualification tools line]). The Pi extension, which customers download with `curl` since September 24, negotiates version 1 or 2 through the capabilities route, but the release 23 record checked only its served bytes (source [testing verifier, September 24]).

#### LE-EDGE-007

Types, file formats and identifiers of an outside project MUST stay inside its
engine adapter; an outside standard enters an edge only as a field or an
export format of one of this repository's records.

- Maps to: `request_contract` and `result_contract` of each interaction row.
- Enforced by: existing `core.engines.slot_checks:every_interaction_names_exact_versioned_contracts_and_known_components` (the rows name this repository's records); new `no_outside_type_crosses_an_edge` (known-wrong: an edge result field that holds an outside library object or an upstream record type).
- Today: partly. The rows name this repository's record types (source).

#### LE-EDGE-008

Each interaction row MUST be joined by exactly one engine slot, or belong to
the Loop runtime edges of the fixed frame.

- Maps to: `interactions` in `engine_slot/v1`; the fixed frame in section 5.5 of the design.
- Enforced by: new `every_interaction_row_is_joined_by_one_slot_or_the_fixed_frame` (known-wrong: a planted row joined by two slots; a candidate row joined by none).
- Today: holds. 46 rows are joined by exactly one slot and none by two; the other 7 are the Loop runtime's edges (6 active, 1 partial) (ran, writer). Whether the candidate row `core.interaction.model.invoke_route.v1`, which `model_access` joins, repeats the fixed frame's `core.interaction.prompt.invoke_model` (both name the same request and result contracts) is a design question for the independent reviewer (claim [wave A problem 12]).

#### LE-EDGE-009

A protocol request MUST be classified by the protocol version its body
carries before its header is read, and refused before any effect when the two
disagree.

- Maps to: `select_protocol_binding` in `core/service_runtime/http.py`; the `protocol_endpoint` slot.
- Enforced by: designed `a_second_protocol_version_is_selected_only_by_exact_negotiation` (the slot's planned check, whose named known-wrong case is this defect); new `a_protocol_request_is_classified_by_its_body_before_its_header` (known-wrong: a request whose header names 2025-11-25 while its body metadata names 2026-07-28 or the unknown 2099-01-01).
- Today: fails, with an effect. Such a request is served under 2025-11-25 rules with one item read and one `service_usage/v1` record written, also on a host that serves only 2025-11-25 (ran [protocol revisions line, `e8069610`]; reproduced by its verifier's probe and again on `e6346075`, ran, writer). The protocol library routes by header only and has "no version allowlist, no way to reject or disable an era" (source, `mcp` documentation on `main`).

#### LE-EDGE-010

The schema that an edge publishes MUST be no looser than the check that the
edge enforces, or its validation profile lists each difference.

- Maps to: `published_schema_relation` in `validation_profile/v1` (new, section 7); `http_retrieval_schema`; the tool `inputSchema` in `core/provisioning_mcp.py`.
- Enforced by: new `the_advertised_schema_is_no_looser_than_the_enforced_check` (known-wrong: `intelligence_search` with `top_n` 1000, `top_n` 10.0, an empty query, a blank query and a 5,000-byte query, each valid under the advertised schema and refused by the service).
- Today: fails. Six kinds of input that the published schemas accept are refused, and no protocol tool publishes an `outputSchema` (ran [validation line, qualification tools line]; reproduced by the validation verifier's probe).

#### LE-EDGE-011

An edge whose call pattern is stream MUST name its stream semantics: framing,
terminal signal, in-band error rule, malformed event rule, byte limit, total
deadline beside the idle timeout, ordering scope, acknowledgment meaning,
replay and partial result.

- Maps to: `stream_semantics/v1` (new), defined once in `component_interaction_catalog/v2` and referenced from the row and from `harness_wire_codec/v2`.
- Enforced by: new `every_stream_edge_names_its_stream_semantics` (known-wrong: a stream row with no terminal signal or no byte limit; the harness relay's two chunks for one finished response, not declared as an emulated stream).
- Today: not built. Nothing declares stream semantics; the relay turns one finished response into two stream chunks without saying so (ran [validation line]).

#### LE-EDGE-012

The retry field of an interaction row MUST name its owner from a closed list:
the envelope, the engine with a recorded permission, or no retry.

- Maps to: `retry` in `component_interaction_catalog/v1`, which moves to `retry_owner` and `budget_scope` in version 2; `HarnessFallbackPolicy.allow_native_retry`; `harness_native_control_policy/v1`.
- Enforced by: new `every_interaction_row_names_its_retry_owner_from_a_closed_list` (known-wrong: a row whose retry label names two owners, or a free label outside the list).
- Today: partly. Every one of the 53 rows fills its retry field, but with 39 distinct free labels such as `declared_fallback_before_dispatch_only` (ran, writer). All 18 harness recipes give native retry to the owning Loop (source [repository grounding line]).

#### LE-EDGE-013

The cancellation value of an interaction row MUST describe what the worker
path does after the request ends.

- Maps to: `cancellation` in the rows `core.interaction.service.read_approved_body` and `core.interaction.service.protocol_tool_call`.
- Enforced by: new `declared_cancellation_matches_the_worker_path` (known-wrong: a read cancelled or timed out before its meter commit, which commits later while its row says `inherited_request_cancellation`).
- Today: fails. A read past its 0.2 second deadline is answered 504 and its usage record commits afterwards, and a cancelled read commits afterwards too (ran [selection, activation and transition line]). With the default pool, four timed-out reads hold four of the account's shares, and a retry by the same account is refused with 429 `tenant_concurrency_limit_reached` (ran [its verifier]). The protocol allows a server to finish cancelled work, so the declaration, not the behavior, is wrong.

#### LE-SLOT-001

Every functional component outside the fixed frame MUST have exactly one
engine slot record in `engine_slots.yaml`, even while it has one engine, and a
slot table kept inside a component counts as a slot.

- Maps to: `engine_slot_catalog/v1`; the fixed frame in section 5.5 of the design (the Loop runtime, role profiles, run mode policy, step profile, typed contracts and ports, the boundary registry, Run History and the event vocabulary, the host configuration loader, the transport kernel, the selection mechanism).
- Enforced by: existing `core.engines.slot_checks:every_slot_of_the_design_tables_is_catalogued`; existing `core.engines.slot_checks:every_engine_slot_names_registered_work_boundaries_or_a_release_reason`; new `every_factory_table_slot_is_catalogued_with_its_engine_kinds` (known-wrong: the four library ingestion slots missing from the catalogue). The new check follows each catalogue row's `factory_table` field inside the package and compares slot identifiers, engine kinds and selection mode, generalizing `core.external_harness_contract:the_step_executor_slot_record_names_the_contract_kinds_version_and_edges`; a repository-level test covers the tables under `tools/`, which the installed package cannot read.
- Today: fails, while the index reports 0 findings. `core/library_ingestion/engines.py` declares five slots with working engines; `library_format_validation`, `library_safety_scan`, `library_near_duplicate` and `library_outline` are not catalogued, and `library_ingestion_source` is catalogued as planned with kinds that the code does not have (`offline_preparer`, `public_repository_reader`, `skill_directory_reader`, `registry_reader` against `pinned_repository_reader` and `registry_link_reader`) (ran, writer). `tools/candidate_review/engines.py` holds factory tables for 16 pre-check engines and 3 reviewer engines (source [testing verifier, September 24]).

#### LE-SLOT-002

A slot record MUST name, each from its closed vocabulary, its engine protocol
and version, engine kinds, native registry, native declaration, descriptor
projection, factory table, conformance suite, component folder, bindings,
selection mode, fallback ceiling, failure kinds and scope fields.

- Maps to: the fields of `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:every_slot_uses_the_closed_vocabularies`; existing `core.engines.slot_checks:engine_slot_symbols_resolve_without_import`; existing `core.engines.slot_checks:every_slot_names_its_component_folder_row`.
- Today: holds for all 45 records. Of the 37 run-time slots, 24 engine protocols, 7 factory tables and 0 descriptor projections resolve; the rest are planned symbols (ran, writer).

#### LE-SLOT-003

The engine framework MUST NOT add a registry, a store, an event family or a
scheduler of its own.

- Maps to: `native_registry`, `native_declaration` and `descriptor_projection` in `engine_slot/v1`; the package `core/engines/`.
- Enforced by: designed `descriptors_are_projections_of_native_declarations`; new `the_engine_package_defines_no_registry_store_or_scheduler` (known-wrong: a module under `core/engines/` that keeps a mutable table of engine objects, opens a store or starts a thread); review by the integration reviewer.
- Today: holds for `core/engines/`, which holds records and checks only (source). The gate `public_parallel_runtime_surfaces`, which the first draft named here, compares retired runtime names at the package root and does not test this statement (source [rule and names verifier, September 24]).

#### LE-SLOT-004

A call site other than the slot's factory table MUST NOT name a concrete
engine class, except a site in the slot's shrinking list of known
construction sites.

- Maps to: `factory_table` and `known_direct_construction_sites` in `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:existing_slot_checks_and_construction_sites_resolve`; designed `engine_classes_are_named_only_at_their_registration_sites`; new `a_listed_construction_site_still_constructs_what_it_names` (known-wrong: the two rows that list `core/service_runtime/http.py` as constructing `Retriever`, which that file stopped doing in `058e57b3` on September 22).
- Today: partly. A listed site is checked for file existence only (source [testing verifiers]).

#### LE-SLOT-005

Importing an engine module MUST register nothing; a host names an engine by
its identity in a host file, never by an import path.

- Maps to: the engine installation records of a host; section 1.6 of the design.
- Enforced by: existing gate `dynamic_import_registration_bypasses`; designed `importing_an_engine_module_registers_nothing`.
- Today: partly. The gate refuses dynamic registration paths; the designed check is not built (source).

#### LE-SLOT-006

Each functional component MUST keep one folder that holds one module per
engine and a factory table module that defines no engine class.

- Maps to: `component_folder_map/v1`; `component_folder` in `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:every_slot_names_its_component_folder_row`; designed `every_engine_module_holds_one_engine_in_its_component_folder`.
- Today: partly. 17 slots name the flat `src/loop_engine/core` folder and 6 name none (ran [rule and names verifier, September 24]).

#### LE-SLOT-007

A nested slot MUST be reached only through the envelope Loop of the engine
that uses it, with its parent decision recorded and with no grant, binding or
budget that its parent does not hold.

- Maps to: `nested_under` and `nesting_scope_rule` in `engine_slot/v1`; `parent_decision_digest` in `engine_selection_decision/v1`.
- Enforced by: existing `core.engines.slot_checks:a_nested_slot_fixes_its_parent_in_scope_or_states_why_not`; existing `core.engines.selection_records_checks:a_nested_decision_names_its_parent`; designed `a_nested_selection_names_its_parent_decision_and_never_widens_it`.
- Today: partly. Enforced in the records; the caller is still trusted (claim [wave A problem 6]).

#### LE-SLOT-008

A change to one engine MUST NOT edit an edge contract record, an interaction
row, a call site or another engine's module; a change that needs one of these
is an edge contract change under section 11.7 of the design.

- Maps to: the engine card of the planned generated engine pages; section 12 of the design.
- Enforced by: designed `engine_module_imports_only_its_slot_contract_and_its_own_dependencies`; designed `engine_classes_are_named_only_at_their_registration_sites`.
- Today: designed.

#### LE-SLOT-009

Product code under `src/loop_engine` MUST choose among implementations only
through the shared engine records of a catalogued slot, never through an
installation, policy or decision record family of its own.

- Maps to: `engine_installation/v1`, `engine_selection_policy/v1` and `engine_selection_decision/v1`; `core/library_ingestion/selection.py`.
- Enforced by: new `product_code_selects_engines_only_through_the_shared_records` (known-wrong: `library_engine_selection/v1` and the second `EngineSlot` class in `core/library_ingestion/selection.py`).
- Today: fails. Library ingestion keeps its own records "ahead of the shared framework", as its own docstring says, and its `EngineSlot` is a different class from the shared one (ran, writer).

#### LE-SLOT-010

A development tool under `tools/` that chooses among implementations SHOULD
use the shared engine records as well.

- Set aside when: the tool is a dated experiment whose records are kept as evidence and which serves nothing to customers.
- Maps to: `tools/candidate_review/`; `tools/opencode_generation_lanes.py`; `tools/overnight_candidate_batch.py`.
- Enforced by: review by the integration reviewer; the repository-level identifier test of LE-ENGINE-002.
- Today: partly. Two tool families keep their own records: `candidate_reviewer_installation/v1`, `candidate_review_panel_policy/v1` and `candidate_review_dispatch/v2`, and `opencode_generation_lane/v1` with `opencode_generation_lane_run/v1` (source).

#### LE-SLOT-011

Every engine of a catalogued slot MUST live in the installed package
`loop_engine`, so that the slot's conformance suite resolves and is collected.

- Maps to: `conformance_suite` in `engine_slot/v1`; the slot index resolves symbols from the installed package only.
- Enforced by: existing `core.engines.slot_checks:every_active_engine_slot_conformance_suite_is_collected`.
- Today: fails for `material_install_layout`. Its five layout rows (`opencode`, `claude-code`, `codex`, `pi` and `baltor-harness`) and its placement rule live in `tools/install_selected_material.py`; the slot record names no suite, native registry, declaration, factory table, component folder or interaction row, and a suite under `tools/` cannot even be named (source [testing verifier, September 24]).

### 2. Engines and engine adapters, with separated duties

An engine is one implementation behind one slot. An engine adapter is the
kind of engine whose code translates to an outside project. The outside
research lists seven duties of a "wrapper". Each duty has one owner here, so no
single class grows into a second runtime.

| Duty | What it owns | Owner in this repository |
|---|---|---|
| Package or build | Pinning, build recipe, dependencies, reproducible artifact | The engine descriptor's upstream entries and implementation digest; `harness_recipe/v1` for harnesses |
| Semantic translation | Request translation, upstream invocation, result and error normalization | The engine adapter module, with its conversion declarations |
| Transport | Function call, subprocess protocol, HTTP, Model Context Protocol, WebAssembly mechanics | The execution fields of section 10; `harness_wire_codec/v1` for harness relays |
| Lifecycle | Create or connect, prepare, ready, acquire and release, drain, close | The envelope Loop, with engine instances, engine leases and owned resource records (section 3) |
| Host service ports | Scoped model, artifact, connection, clock and log access | Bindings in the envelope's runtime context; `HarnessServices` |
| Invocation middleware | Ordered checks, deadlines, tracing, permitted cache and retry | Wrapper layers with declared control ownership (`harness_wrapper_composition/v1`) and the envelope's fixed order |
| Qualification | Independent tests and acceptance observations | The conformance kit and `engine_qualification/v1`, written by an independent reviewer |

#### LE-ENGINE-001

An engine's implementation digest MUST cover its own code bytes, every pinned
outside artifact and its dependency lock.

- Maps to: `implementation_digest` in `engine_descriptor/v1`; the registration digest of `harness_adapter_registration/v1`.
- Enforced by: existing `core.engines.records_checks:descriptor_digest_moves_when_any_field_moves`; new `the_implementation_digest_moves_when_code_bytes_move` (known-wrong: a changed adapter module whose registration digest stays the same).
- Today: partly. The registration digest covers the declaration and the class, not the code bytes (claim [wave A problem 21]).

#### LE-ENGINE-002

One engine identifier MUST name one implementation across `src` and `tools`.

- Maps to: `engine_id` in `engine_descriptor/v1`; every factory table.
- Enforced by: designed `one_engine_identifier_names_one_implementation` (inside the package); new `one_engine_identifier_names_one_implementation_across_the_repository` (known-wrong: `skillspector_static`, `datasketch_minhash_lsh` and `builtin_static_rules`, each defined as separate classes in `src/loop_engine/core/library_ingestion` and in `tools/candidate_review/prechecks`). It is a repository-level test, because the installed package cannot see `tools/`.
- Today: fails (source [repository grounding line and its verifier]). The Agent Skills reference validator is also wrapped twice, as `agent_skills_reference` (the `agentskills` command, in `tools`) and `agent_skills_reference_validator` (the `skills_ref` library, in `src`), and five `native_*` pre-check engines in `tools/candidate_review` wrap existing engines under new identifiers (source [its verifier]).

#### LE-ENGINE-003

An engine adapter MUST only translate: it keeps no scheduler, retry loop,
model manager or state database of its own, and it reaches models only
through the `model_access` slot.

- Maps to: the engine adapter module; `core/model_gateway.py`.
- Enforced by: existing gate `direct_model_or_network_calls_outside_gateway`; designed `no_caller_reaches_a_provider_except_through_model_access`.
- Today: partly. The overnight runner still builds a provider adapter directly with `make_adapter` in `overnight_cli.py` (source; design section 9.3).

#### LE-ENGINE-004

The retry owner of an edge MUST be the one that its interaction row names,
and an engine retries natively only when that row names the engine and the
slot's policy allows native retry.

- Maps to: `retry_owner` (LE-EDGE-012); `HarnessFallbackPolicy.allow_native_retry`; `harness_native_control_policy/v1`.
- Enforced by: new `an_engine_retries_only_when_its_row_names_it_the_retry_owner` (known-wrong: an engine that retries a timed-out call on its own while its row names the envelope).
- Today: partly. Harness recipes hand native retry to the owning Loop; other engines have no declared owner to compare with (source).

#### LE-ENGINE-005

A nested call MUST receive the remaining deadline of its caller, never a
fresh timeout.

- Maps to: `timeout` in the interaction rows; the envelope's budget.
- Enforced by: new `a_nested_call_receives_the_remaining_deadline` (known-wrong: a nested model call started with its full default timeout inside an attempt that has little time left).
- Today: not built (source [committed wrapping research, section 4]).

#### LE-ENGINE-006

Engine settings MUST be typed by the settings record that the slot's factory
table pairs with the engine kind, so that an undeclared key or an
authority-bearing key is refused before the installation is accepted.

- Maps to: `settings` in `engine_installation/v1`; the pattern of `ADAPTER_FACTORIES` in `core/decisions/configuration.py`, which pairs a settings class with each kind.
- Enforced by: existing `core.engines.records_checks:installation_settings_never_hold_a_credential`; new `installation_settings_are_typed_and_carry_no_authority` (known-wrong: `api_key_env`, `allow_network`, `spending_limit_usd`, `budget_tokens`, `max_cost_usd`, `allow_failover`, `network_hosts`, `permissions`, `token_env` and `secret_ref`).
- Today: fails. All ten keys are accepted and only `api_key` is refused (ran, writer). A key-name screen may stay as a backstop, but the typed record is the rule, because permissions come from typed fields, never from names.

#### LE-ENGINE-007

An engine, its installation and its selection MUST NOT grant model, file,
network, secret, spending or external-effect authority.

- Maps to: `execution_authority_granted` in `engine_selection_decision/v1`; the owning Loop's grants.
- Enforced by: existing `core.engines.selection_records_checks:decision_flags_are_constant`; designed `mode_or_configuration_never_grants_engine_permission`.
- Today: partly. Enforced in the decision record; designed for the selector.

#### LE-ENGINE-008

Listing engines, projecting descriptors and comparing requirements MUST start
no process, load no model weights, open no network connection and call no
model.

- Maps to: `descriptor_projection` and `requirement_comparison` in `engine_slot/v1`.
- Enforced by: existing `core.engines.slot_checks:engine_slot_symbols_resolve_without_import`; designed `selection_performs_no_probe_no_network_and_no_model_call`; designed `listing_entry_points_imports_nothing`; new `a_projection_succeeds_with_a_launcher_that_raises` (known-wrong: a projection that starts the harness binary to ask for its version).
- Today: designed. No projection exists yet; one `requirement_comparison` names an availability method instead of a comparison (`WorkspaceBackend.availability`) (ran [activation line]).

#### LE-ENGINE-009

An engine exception MUST become a typed failure kind of its slot, kept beside
any accounting failure, never an empty result or only text.

- Maps to: `failure_kinds` in `engine_slot/v1`; `run_external_harness` in `core/external_harness.py`.
- Enforced by: new `an_engine_exception_becomes_a_typed_failure_never_an_empty_result` (known-wrong: an engine error logged and returned as `None`, the stevedore default); new `an_engine_crash_keeps_its_own_failure_code_beside_the_accounting_code` (known-wrong: a step engine that raises under a one-call ceiling).
- Today: fails for the step executor. Under a call ceiling a crash ends as `budget_exhausted` with `model_call_accounting_incomplete`, and the crash survives only as the text field `underlying_error_type` (ran [testing line]; reproduced by its verifier on `2658b7bb` after `external_harness.py` changed).

#### LE-ENGINE-010

A retired engine MUST NOT be selected; its retirement record names its
replacement, and its code stays restorable.

- Maps to: `engine_retirement/v1`; `lifecycle` and `implementation_location` in `engine_descriptor/v1`.
- Enforced by: existing `core.engines.selection_records_checks:a_policy_lists_an_engine_once_and_never_a_retired_one`; designed `retired_engine_is_never_selected_even_when_listed`.
- Today: partly. Enforced in policies; designed in selection.

#### LE-ENGINE-011

An engine that declares its effects as pure MUST make no network request,
including while it validates input against a schema.

- Maps to: `effects` of the engine; `validator_for` in `core/library_ingestion/format_json_schema.py` and in `core/mcp_adapter.py`; `references` in `validation_profile/v1` (section 7).
- Enforced by: new `schema_validation_makes_no_network_request` (known-wrong: validating an `opencode.json` that names a model through the engine `connection_schema_validator`; a discovered tool schema with a remote `$ref`).
- Today: fails. The pinned OpenCode schema refers to `https://models.dev/model-schema.json`, and validating `{"model": "ollama/gemma4"}` through the engine, which declares `effects = ("pure",)`, opens a connection to `models.dev` on port 443; with the network blocked it raises an untyped referencing error. The Model Context Protocol client adapter fetches a tool schema's remote `$ref` in `approval_plan` and in `invoke` (ran [validation line]; reproduced by its verifier's probes). Revision 2026-07-28 says implementations "MUST NOT automatically dereference `$ref` values that resolve to a network URI" (source).

### 3. Definition, configuration, instance, lease, session, invocation and state

The outside draft names nine objects. This repository already has a name, a
record or a planned record for each. The outside names are not used.

| Outside name | Name here | Record | State today |
|---|---|---|---|
| EngineDefinition | engine identity, projected as the engine descriptor | `engine_descriptor/v1` | record exists; no projection built |
| EngineFactory | the slot's factory table | `factory_table` in `engine_slot/v1` | 7 of 37 resolve |
| EngineConfiguration | engine installation (one engine) and slot configuration (one host record per slot) | `engine_installation/v1`, `engine_slot_configuration/v1` | records exist; no host path declares them |
| EngineInstance | engine instance, with an owned handle and a fencing token | `engine_instance/v1` (proposed), replacing the ledger's `InstanceRecord` | ledger exists without a live caller |
| EngineLease | engine lease | `engine_lease/v1` (proposed) | none |
| EngineSession | engine session, inside one engine attempt | a field of the engine instance | none for engines |
| PreparedPlan | the execution specification digest of one engine attempt | `engine_selection_decision/v2` and the attempt measurement (proposed) | parts exist: `HarnessRunRequest.digest`, the gateway's request digests |
| InvocationAttempt | engine attempt | the attempt Loop and `operation_cost_record/v2` (designed) | partly |
| StateRef | state binding | `state_binding` in `engine_descriptor/v2` (proposed); `format_ref` on `InformationStorageBinding` | embedding spaces only |

#### LE-INSTANCE-001

Which engine runs and how it is configured MUST stay two identities: the
descriptor digest names the engine, and the installation digest names the
engine with its typed settings, its chosen execution fields and its chosen
instance lifetime.

- Maps to: `engine_descriptor/v1`; `engine_installation/v1` (to version 2 for the two new fields).
- Enforced by: existing `core.engines.records_checks:installation_digest_binds_the_settings_but_not_the_enabled_switch`; existing `core.engines.records_checks:qualification_binds_the_installation_digest`.
- Today: partly. Enforced for settings; the execution fields and the lifetime are proposed.

#### LE-INSTANCE-002

An engine installation MUST name the engine version it installs, so that a
host file and an exact pin can bind a version.

- Maps to: `engine_installation/v2` gains `engine_version`.
- Enforced by: designed `a_version_mismatch_between_host_file_and_distribution_refuses_load`.
- Today: not built. `host_records.py` says "An installation does not name its engine version", while the design's own planned check assumes a host file that names one (source [selection verifiers]).

#### LE-INSTANCE-003

Every started process, loaded runtime, open connection or remote session MUST
be recorded as an engine instance with an identity that is never reused, a
typed owned handle, and a fencing token that rises at every restart,
reconfiguration or fence.

- Maps to: `engine_instance/v1` (new), replacing `InstanceRecord` in `core/local_resources.py`; handle kinds: process file descriptor, control group, container with an owner label, remote session; the fencing token follows the `fencing_token` of `work_lease/v1`.
- Enforced by: new `an_ended_instance_never_becomes_live_again` (known-wrong: `stopped` moved back to `running`); new `a_fenced_instance_cannot_write_liveness_or_usage` (known-wrong: a heartbeat accepted for a hibernated or stopped instance).
- Today: fails. The ledger accepts both known-wrong cases, signals by bare process number and has no caller outside its own module, the hibernation module and the self-test (ran [lifecycle line]; confirmed by both verifiers, the second on `2658b7bb`). Re-registering an ended identity is refused; only its state comes back.

#### LE-INSTANCE-004

Ending one engine lease MUST NOT end an engine instance that another live
engine lease holds.

- Maps to: `engine_lease/v1` (new): instance, instance fencing token, holder Loop and attempt, units, times; `InternalRuntimeBinding` gains `lease_ref`. An engine lease grants no authority (LE-ENGINE-007); capacity stays a resource reservation.
- Enforced by: new `a_shared_engine_instance_survives_the_end_of_one_lease` (known-wrong: ten engine leases on one loaded model; one ends; the model is unloaded).
- Today: not built. `LoopRuntimeContext.derive` shares one service object with fewer capabilities and no release (ran [repository grounding line]). Ollama's scheduler keeps a runner loaded while its reference count is above zero, which is the behavior this statement asks for (source, Ollama v0.32.6 and v0.34.4 `server/sched.go`).

#### LE-INSTANCE-005

An expired lease MUST NOT be started, renewed, used or committed; a new lease
replaces it.

- Maps to: `work_lease/v1`; `credential_lease/v1` (to version 2); `engine_lease/v1`. The live billing effect leases already refuse use after expiry (`session_reservation_expired`).
- Enforced by: new `an_expired_work_lease_cannot_start_renew_or_commit` (known-wrong: with no claim in between, a holder whose lease expired starts, renews and commits); new `an_expired_credential_lease_is_reissued_never_renewed` (known-wrong: `renew()` on an expired lease returns it live).
- Today: fails for work leases and credential leases (ran [lifecycle line]; confirmed by both verifiers). The credential behavior is tested on purpose by the module's self-test, so the change is `credential_lease/v2`, with the self-test and the S-2.36 evidence updated in the same commit. This is a recorded choice, not a rule every system shares: Kubernetes client-go lets the current leader renew its own expired lease when nobody else took it (source).

#### LE-INSTANCE-006

A revoked held credential MUST issue no new lease until the host holds the
credential again under a new held-credential record.

- Maps to: `held_credential/v1` (to version 2, with a withdrawn state and a withdraw operation of the broker); `credential_lease/v2`.
- Enforced by: new `a_withdrawn_credential_issues_no_new_lease` (known-wrong: `issue()` right after `revoke_credential()` returns a live lease).
- Today: fails by the design of version 1: its self-test asserts the reissue, and the broker has no operation that withdraws a held credential (ran [lifecycle line]; source [both verifiers]). Vault documents that revocation stops renewal and that revoking a token revokes its leases; it does not say that revocation blocks new secrets, so this is a new policy (source).

#### LE-INSTANCE-007

A lease MUST resolve only for the holder instance and the instance fencing
token it was issued to.

- Maps to: `LeaseBroker.resolve` in `core/credential_leases.py`.
- Enforced by: new `a_lease_resolves_only_for_its_holder_and_fencing_token` (known-wrong: a copied lease identifier resolves for another instance).
- Today: fails. `resolve()` takes no holder identity (ran [lifecycle line]; first reported on September 22).

#### LE-INSTANCE-008

A capacity reservation MUST be taken in the same decision that admits its
instance.

- Maps to: `resource_reservation/v1`, `ReservationLedger` and `admit()` in `core/local_resources.py` and `core/instance_hibernation.py`.
- Enforced by: new `admission_and_reservation_are_one_decision` (known-wrong: capacity reserved for an instance that was never admitted).
- Today: fails (ran [lifecycle line]; confirmed by both verifiers). A second live reservation for one instance is also accepted, and refusing it changes a hibernation self-test fixture that reserves twice.

#### LE-INSTANCE-009

Every resource that an attempt or an engine instance acquires MUST have an
owned resource record, written before the acquisition and released only after
an observation confirms the release.

- Maps to: `owned_resource/v1` (new), kept through the existing record store atomic batch, the contract the billing effects already use; states pending, held, releasing, released and unknown, where unknown blocks reuse and capacity release; resource kinds: process, control group, container, run folder, socket, capacity reservation, model residency hold, remote sandbox; a deterministic reconciliation Loop at host start.
- Enforced by: new `a_pending_container_cleanup_survives_a_new_adapter_object` (known-wrong: after an unconfirmed Docker cleanup, a second `DockerWorkspace` object for the same workspace writes files and starts a second container).
- Today: fails on a live path. `execute_generated_project` builds a new `DockerWorkspace` for every manifest command and is the solve runtime's default project executor, so the in-memory block is lost between objects inside one process (ran and source [lifecycle line and both verifiers]).

#### LE-INSTANCE-010

Resource cleanup MUST stay apart from compensation: cleanup is the envelope's
repeatable release of owned resources, while compensation is a new authorized
effect owned by a Loop, with its own idempotency key, and never runs inside a
fallback.

- Maps to: `owned_resource/v1`; the effect records of the owning Loop; `effects_uncertain` in section 8.9 of the design.
- Enforced by: existing `core.engines.selection_records_checks:a_fallback_decision_follows_only_a_declared_failure_with_certain_accounting`; review by the independent reviewer of the owning boundary.
- Today: partly. Cleanup is written per adapter; compensation exists only in the billing effect records (source).

#### LE-INSTANCE-011

An engine session MUST live inside one engine attempt unless a qualified
placement allows it to continue across attempts.

- Maps to: the executor installation setting `placement` (`fresh_process` today; `long_lived_session` and `pooled_sessions` only after product qualification); roadmap S-6.31 and S-6.42.
- Enforced by: designed `a_session_process_never_outlives_its_step_attempt`; designed `a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step`.
- Today: designed. The only placement is `fresh_process`.

#### LE-INSTANCE-012

The envelope Loop MUST measure every engine attempt with its own clock and
keep engine-reported time, tokens and cost apart from its measurement, with
missing usage recorded as unknown, never zero.

- Maps to: `operation_cost_record/v2` (designed); section 9 of the design.
- Enforced by: existing `core.engines.selection_records_checks:consumed_authority_keeps_unknown_apart_from_zero`; designed `every_engine_attempt_writes_one_cost_record_in_its_envelope`; designed `engine_reported_time_never_replaces_the_envelope_clock`.
- Today: partly. The defects of section 9.3 of the design are still in source, for example `GatewayAttempt.elapsed_seconds` defaults to 0.0 (source).

#### LE-INSTANCE-013

An engine that keeps state beyond one attempt MUST refuse, before any effect,
state whose format version or owner fencing token differs from the state
binding it declares: owner, category (cache, index or store), format version,
owner fencing token, permitted lifetime and, for an index, what it is rebuilt
from.

- Maps to: `state_binding` in `engine_descriptor/v2` (new); `format_ref` on `InformationStorageBinding`, naming a validation profile, a canonical form or an embedding space; `EmbeddingSpace`.
- Enforced by: existing `core.retrieval:embedding_space_identity_and_cross_space_refusal` (embedding spaces only, through `require_same_space`); new `an_engine_refuses_state_that_does_not_match_its_state_binding` (known-wrong: an index built under one embedding space read by an engine configured for another; a late writer with an older owner fencing token accepted after a newer owner took over).
- Today: partly. Only embedding spaces carry a format identity, and the `InformationStorageBinding` checks are parked (source).

#### LE-INSTANCE-014

An engine swap at a slot whose swap rule is not "next call" or "next attempt"
MUST have its own swap qualification; two passing engine qualifications do
not make one.

- Maps to: `engine_qualification/v2` gains a `swaps` part (the installation and descriptor digests it replaces, the swap rule, a population reference with its digest, and the in-flight outcome); `swap_rule` in `engine_slot/v2` (LE-LIFETIME-003). The qualification lab's `state_transition` unit stays an advisory case family, because the lab does not import the runtime and holds no population (ran [activation line]).
- Enforced by: new `a_stateful_swap_without_a_swap_qualification_is_refused` (known-wrong: `record_store` swapped from `local.sqlite` to `remote.postgres` on two engine qualifications); new `a_swap_qualification_names_both_installations_and_a_population` (known-wrong: a swap record with only the new installation, or with no population digest).
- Today: not built. `QualificationScope` has an edge contract, a recipe variant and step contracts, no previous installation, and the reader refuses a field that names one (ran [activation line]). One swap already happens in production, the catalogue release swap, and it breaks the retry rule of LE-INSTANCE-021.

#### LE-INSTANCE-015

Expensive preparation, such as loading a model, building an index or starting
a pool, SHOULD happen at the slot's declared binding phase (host start or Loop
start), not in every attempt.

- Set aside when: the slot's placement is a fresh process for each step by design, as for the step executor.
- Maps to: `selection_phase` of each binding in `engine_slot/v1`.
- Enforced by: review by the independent reviewer of the slot record; the measured `setup` phase of each attempt.

#### LE-INSTANCE-016

A lease-like record MUST judge expiry at the moment of use by the clock of the
lease's owner, never by a time that the holder supplies.

- Maps to: `claim`, `start`, `heartbeat` and `terminal` in `core/reactive_scheduler.py` and `loop/reactive_activation.py`; `LeaseBroker` in `core/credential_leases.py`; the live billing path, which already compares with the service's own clock (`billing_effects.py`, `self.runtime._now()`).
- Enforced by: new `lease_expiry_is_judged_by_the_owner_clock` (known-wrong: a start dated one hour before its claim is accepted, because every time comes from the request).
- Today: fails for work leases (ran [lifecycle verifier, September 24]). The reactive scheduler is on no product run path today (examples, checks and development labs only), which lowers the urgency (source [same verifier]).

#### LE-INSTANCE-017

Renewal MUST NOT extend a lease past its declared maximum lifetime.

- Maps to: `max_expires_at` of `engine_lease/v1`; `renew()` of `credential_lease/v2`; `heartbeat()` of the work lease.
- Enforced by: new `renewal_never_extends_a_lease_past_its_maximum` (known-wrong: one heartbeat that moves a work lease to the year 2100; one `renew()` that extends a credential lease by a year).
- Today: fails for both (ran [lifecycle verifier, September 24]). After the heartbeat to 2100, recovery in 2027 recovered nothing and a second worker could not claim the work.

#### LE-INSTANCE-018

A confirmed stop MUST release every capacity reservation of the stopped
instance, and nothing else releases one.

- Maps to: `ReservationLedger` and `hibernate()` in `core/instance_hibernation.py`; `stop_confirmation` in `engine_instance/v1`.
- Enforced by: new `a_confirmed_stop_releases_every_reservation_of_the_instance` (known-wrong: hibernation without the reservation identity, then resume, leaves two live reservations for one instance).
- Today: fails (ran [lifecycle line]; confirmed by both verifiers, 400 bytes held for one instance after resume).

#### LE-INSTANCE-019

A provider-reported count MUST be read by one rule that keeps a non-negative
integer and records any other value as unknown.

- Maps to: `reported_token` in `core/model_gateway.py`; `optional_token` in `core/run_history_usage.py`; `_int_value` and `_float_value` in `core/external_harness_adapters.py`.
- Enforced by: new `a_provider_count_has_one_reader` (known-wrong: a reported `input_tokens` of 12.9 stored as 12, `true` stored as 1 and `"12"` stored as 12 through a harness adapter).
- Today: fails. The gateway and Run History record those values as unknown, while the harness adapters store them as provider-reported; a reported cost of `true` is stored as 1.0, and a reported request count of 1.9 is counted as one physical model call (ran [validation line]; reproduced by its verifier).

#### LE-INSTANCE-020

An engine attempt's declared deadline MUST bound the whole call on the
envelope's monotonic clock, not each blocking read.

- Maps to: `timeout` of `CustomEndpoint` and `timeout_seconds` of the model gateway; the installer's `response_deadline_seconds`, which already bounds the whole response.
- Enforced by: new `a_model_call_ends_by_its_declared_deadline` (known-wrong: a loopback server that answers in small pieces with pauses shorter than the timeout).
- Today: fails on the model path of custom endpoints, which the overnight runner uses. With a declared timeout of 1 second, a trickled answer completed after 8.41 seconds in buffer mode and 11.6 seconds in stream mode, and was accepted as a complete answer (ran, writer, on `3d48a36c` and again on `e6346075`; first found by the qualification tools line at 12.5 seconds through Toxiproxy).

#### LE-INSTANCE-021

A retry that repeats a request identity MUST be answered from the record of
the first result while that result's bytes are still held, and refused with a
definite code when they are not.

- Maps to: `record_usage` and the `service_usage/v1` rows in `core/service_runtime/runtime.py`, which already name the exact item version read (`item_identity`, `body_digest`); `core/provisioning_server.py`.
- Enforced by: new `a_retry_by_identity_across_a_catalogue_swap_returns_the_first_bytes_once` (known-wrong: the same identity refused three times after a swap while a new identity is served and counted again).
- Today: fails on the live service path. Without a swap, three retries of one identity are served and counted once. After a catalogue swap that moves the grant to the new bytes, the same retries are refused with `meter_commit_unknown`, and a new identity is served and counted, so two usage records exist for one body received (ran, writer, with the real release-following grants, a real publish and a real refresher swap; first found by the activation line).

#### LE-INSTANCE-022

A definite refusal MUST NOT be reported to a client as an unknown outcome.

- Maps to: `meter_commit_unknown` in `core/provisioning_server.py` and `core/service_runtime/refusals.py`; `usage_identity_conflict` in `core/service_runtime/runtime.py`.
- Enforced by: new `a_definite_identity_conflict_is_never_reported_as_an_unknown_commit` (known-wrong: the store answers `usage_identity_conflict` and the client receives `meter_commit_unknown`, whose guidance says "Do not repeat the request", while the deadline guidance says to retry with the same request identity).
- Today: fails (ran [activation line]; reproduced by its verifier).

#### LE-INSTANCE-023

Each engine attempt MUST record its request outcome, its task outcome and its
effect state as three separate fields.

- Maps to: the disposition of `operation_cost_record/v2` (designed), split into request outcome (answered, deadline exceeded, cancelled, refused), task outcome (completed, failed, cancelled, unknown) and effect state (none, pending, confirmed, unknown); a cancel request record in the reactive scheduler when its first caller needs one.
- Enforced by: new `request_outcome_task_outcome_and_effect_state_are_separate_fields` (known-wrong: a deadline-exceeded attempt whose effect committed, recorded with no effect).
- Today: not built. The designed disposition list mixes the three, and LE-EDGE-013 shows a request that ends while its effect commits (source and ran [activation line]).

#### LE-INSTANCE-024

The envelope MUST count a model request as a physical model call only when
the request left the host.

- Maps to: `physical_requests` and `response_received` of `ChatResult` in `core/custom_endpoint.py`; the gateway's physical call count.
- Enforced by: new `a_refused_connection_is_not_counted_as_a_sent_model_request` (known-wrong: a refused connection recorded as one physical request and one physical model call).
- Today: fails for plain refused connections (ran, writer); a connection closed before any byte is recorded as `response_received` true (ran [qualification tools line]). A refusal by the new TLS trust contract is already recorded as not sent (source, `f26fa3fa`).

#### LE-INSTANCE-025

A tool call with declared effects whose outcome is lost MUST end with the
status effects uncertain, never as a plain failure that a caller may retry.

- Maps to: `MCP_CALL_STATUSES` in `core/mcp_adapter.py`; `effects_uncertain` in section 8.9 of the design; the `tool_protocol_gateway` slot's planned check.
- Enforced by: designed `a_tool_effect_is_never_replayed_after_an_uncertain_reply`; new `a_lost_effectful_tool_call_is_effects_uncertain` (known-wrong: a transport failure of a tool with a declared effect recorded as `failed` with `transport_failed`).
- Today: fails. The status list has no uncertain value, and a transport exception becomes `failed` with `transport_failed` (source [lifecycle verifiers]). The Model Context Protocol lets a client retry lost stateless requests after a server restart; that permission never covers an external effect (source, revision 2026-07-28, standard input and output transport).

#### LE-INSTANCE-026

Installations that share one model on one model server MUST send that
model's keep time and load options from one shared residency record, never
each from its own declaration.

- Maps to: `residency_seconds` and `context_tokens` of `CustomEndpoint` in `core/custom_endpoint.py`, sent as the Ollama `keep_alive` and `num_ctx`; `overnight_residency/v1` (`ResidencyPolicy` in `code_nodes/overnight_authority.py`), which gains its holders as engine leases; `model_loaded` and `context_limit` of `ModelRouteAvailabilitySnapshot` for the residency observed; `core/local_model_readiness.py`, which already reads `/api/ps`. The keep time sent is the longest among live holders and never 0 while a holder is live, and a call with other load options is refused or sent to another declared server unless the step allows a reload and records its time. No new residency record type is added.
- Enforced by: new `residency_holders_never_send_a_shorter_keep_time_than_a_live_holder` (known-wrong: `keep_alive` 0 sent for a model while another holder's engine lease is live); new `a_call_with_different_load_options_never_silently_reloads_a_shared_model` (known-wrong: `num_ctx` 8192 and then 2048 sent to one resident model, both accepted).
- Today: fails. Two declarations for one server and one model sent `keep_alive` 36000, 0, 36000, 0 and `num_ctx` 8192, 2048, 8192, 2048, every call was accepted, and the module has no residency or conflict check (ran [lifecycle verifier, September 24]; first found by the lifecycle line). Ollama v0.32.6 and v0.34.4 apply the last keep-alive a request carries and reload a model whose load options differ; a keep-alive of 0 cannot unload a model while another request is in flight, so the risk is to a holder that is idle between calls (source). One load at a new context length took 98.04 seconds on this machine (source, `docs/evidence/overnight-command-2026-09-21.md`). The live trial needs local model calls, which the recorded model-call authority does not name; engineering's overnight runs use Ollama Cloud, and this rule protects customers who run their own server.

#### LE-INSTANCE-027

A shared engine instance MUST declare how many engine leases it accepts at
once and how many requests may wait, and a request beyond both is answered as
a capacity refusal, never as an engine failure.

- Maps to: `units` of `engine_lease/v1`; the capacity fact of `engine_availability_snapshot/v1`; `available_concurrency` and `queue_depth` of `ModelRouteAvailabilitySnapshot`; the host configuration of a model route (for a local Ollama server, its `OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_QUEUE`); waiting is measured in the envelope's admission phase, and `core/runtime_capacity.py` stays the one place a limit number comes from.
- Enforced by: new `a_request_beyond_the_declared_concurrency_is_a_capacity_refusal` (known-wrong: a request over the declared limit that is sent anyway, or refused with a failure kind that triggers a fallback).
- Today: not built. The model gateway, the endpoint adapter and route health hold no concurrency limit, semaphore or queue bound, and nothing reads the snapshot's `available_concurrency` or `queue_depth` (source [lifecycle verifier, September 24]). The hosted service has its own limits, `maximum_concurrent_operations` and the refusal `tenant_concurrency_limit_reached` (source [lifecycle verifier, September 23]). Ollama queues up to 512 requests by default and then answers "server busy" (source, Ollama v0.32.6 `envconfig/config.go` and `server/sched.go`).

### 4. Lifecycle profiles, written as call pattern, instance lifetime and instance owner

The outside draft proposes six "lifecycle profiles". The content is adopted
and the name is not: "lifecycle" already names the component lifecycle
(candidate to archived), and "profile" already names role, step, executor and
harness compatibility profiles. Three separate fields replace it, and the
slot's swap rule says when an engine may change.

| Field | Values | Declared by |
|---|---|---|
| `call_pattern` | request_response, session, durable_task, stream, desired_state | the engine descriptor; the slot lists the permitted ones |
| `instance_lifetime` | per_call, per_attempt, per_run, per_host_start, durable, external | the descriptor lists what the engine supports; the installation chooses one; the slot lists the permitted ones |
| `instance_owner` | envelope, host, external | the engine descriptor |
| `swap_rule` | next_call, next_attempt, pinned_until_done, drain_then_switch, replay_by_identity, migrate_with_atomic_pointer | the slot |

```text
The outside "lifecycle profiles", mapped onto the three fields
├── stateless           -> request_response, per_call, envelope
├── managed runtime     -> request_response, per_host_start, host
├── session             -> session, per_attempt, envelope
├── durable task        -> durable_task, durable, host or external (inside a Loop-owned attempt)
├── stream              -> stream, any lifetime
└── persistent resource -> desired_state, durable, host
The step executor's placement setting, in the same fields
├── fresh_process       -> per_call (text relay) or per_attempt (session process)
├── long_lived_session  -> session, per_run, after product qualification
└── pooled_sessions     -> session, per_host_start, after product qualification
```

Operations each call pattern requires of the engine protocol:
request_response needs describe and invoke; session adds open and close
(checkpoint optional); durable_task needs submit, observe, request_cancel and
reconcile; stream needs open, typed events with flow control, and terminate;
desired_state needs inspect, plan, apply, verify and migrate or rebuild. A
managed runtime (per_host_start, host owner) adds prepare, ready, acquire,
release, drain and close. The committed wrapping research gives the matching
change points per state scope (its section 3).

#### LE-LIFETIME-001

Every engine installation MUST choose, as part of its installation digest,
an instance lifetime that its engine supports and its slot permits.

- Maps to: `engine_descriptor/v2` (`call_pattern`, `supported_instance_lifetimes`, `instance_owner`); `engine_slot/v2` (`permitted_call_patterns`, `permitted_instance_lifetimes`); `engine_installation/v2` (`instance_lifetime`, which generalizes the executor's `placement` setting).
- Enforced by: new `an_installation_lifetime_is_permitted_by_its_slot_and_supported_by_its_engine` (known-wrong: a pooled_sessions harness installation in a slot that permits per_attempt only).
- Today: not built. `placement` exists only as a designed executor setting.

#### LE-LIFETIME-002

Registration MUST refuse an engine whose engine protocol lacks an operation
that its call pattern requires.

- Maps to: `engine_protocol` in `engine_slot/v1`; the operation list above; the pattern of `SERVED_EDGE_CONTRACTS` in `core/external_harness_contract.py`.
- Enforced by: new `registration_refuses_an_engine_missing_an_operation_of_its_call_pattern` (known-wrong: a session engine without close; a durable_task engine without reconcile).
- Today: not built.

#### LE-LIFETIME-003

An engine swap MUST wait for the swap rule that its slot declares, a rule
that the slot's permitted call patterns allow.

- Maps to: `swap_rule` in `engine_slot/v2`; `selection_phase` of each binding; the reuse phase of `engine_selection_decision/v1`. Next call fits stateless per-call engines; next attempt fits `step_executor` and `model_access`; pinned until done fits an attempt that holds a native session; drain then switch fits host-start service engines on one machine; replay by identity fits effects keyed by request identity; migrate with an atomic pointer fits `record_store` and persistent indexes.
- Enforced by: new `an_engine_swap_waits_for_the_swap_rule_of_its_slot` (known-wrong: a preference change applied to a running session; a `record_store` swap without a migration).
- Today: not built. Roadmap S-6.74 lists the first known-wrong case as its adversarial line.

#### LE-LIFETIME-004

An engine with the durable_task call pattern MUST keep its durability inside
a Loop-owned attempt, whose stable key reconciles an interrupted external
action instead of running it again.

- Maps to: the proposed `step_attempt_durability` slot of the ecosystem edge map; a durable-workflow library is an engine that a Loop uses, never a second scheduler of steps.
- Enforced by: new `an_interrupted_effect_in_a_durable_engine_is_reconciled_by_its_key` (known-wrong: an interrupted external action that runs again after a restart).
- Today: not built. In the edge map trial, DBOS 3.0.0 ran an interrupted external action again unless a stable key reconciled it (claim [edge map author's trial]).

#### LE-LIFETIME-005

An engine with the stream call pattern MUST end an attempt as incomplete when
the stream carries an error, skips an event or exceeds its declared output
limit, never as a complete answer.

- Maps to: the stream semantics of the edge (LE-EDGE-011); the stream readers `_chat_streamed`, `_sse_lines`, `_ollama_stream_body` and `_ndjson_objects` of `core/custom_endpoint.py`; `completion_invalid` of the gateway.
- Enforced by: new `an_in_band_stream_error_is_never_a_success` (known-wrong: the loopback cases below); new `a_malformed_or_multi_line_stream_event_is_not_silently_lost` (known-wrong: a malformed event between two good ones dropped without an error).
- Today: fails on the model path of custom endpoints, including the cloud route used for counted generation. Through `ModelGateway.invoke`, an error object after some text followed by the end marker returns `ok` with the partial text, and so does Ollama's documented mid-stream error line (ran, writer). Against a loopback server, a malformed event, a two-line event and content sent as typed parts are dropped without an error, carriage-return line endings fail as `model_identity_mismatch`, 5,120,000 characters are accepted for a request that allowed 8 output tokens, and keep-alive comments stretch a 1-second timeout past 3 seconds (ran [validation line]; reproduced by its verifier).

#### LE-LIFETIME-006

A request to pause or checkpoint an engine instance MUST travel through a
channel whose default action does not end the process.

- Maps to: `ProcessTreeController.quiesce` in `core/instance_hibernation.py` (sends SIGUSR1); `run_checkpoint.install_signal_checkpoint`, which writes a checkpoint on SIGTERM, SIGINT or SIGHUP; a typed message on the broker socket, a file or closed input as alternatives.
- Enforced by: new `a_quiesce_request_never_uses_a_signal_with_a_lethal_default` (known-wrong: SIGUSR1 to a process with the default disposition); new `hibernation_runs_the_real_controller_against_a_real_process` (known-wrong: a check whose fake controller records calls instead of sending signals).
- Today: fails. SIGUSR1 has the default action "terminate". Sent to the one process group the harness path owns, it ended Bubblewrap (return code -10), and `--die-with-parent` then ended the sandboxed command; sent to Node.js, it opened the Node.js debugger on `127.0.0.1:9229` (ran [lifecycle verifier, September 24]). The hibernation path has no live caller yet (source).

#### LE-LIFETIME-007

A graceful stop MUST reach the sandboxed process itself, not only the process
group of the program that launched it.

- Maps to: the deadline kill `os.killpg(proc.pid, signal.SIGKILL)` in `core/harness_process.py`; Bubblewrap's `--new-session`; the shutdown order of the Model Context Protocol standard stream transport (close input, wait, then SIGTERM, then SIGKILL).
- Enforced by: new `a_graceful_stop_reaches_the_sandboxed_process` (known-wrong: SIGTERM to the Bubblewrap group ends Bubblewrap while the sandboxed process never runs its SIGTERM handler).
- Today: fails. Because `--new-session` puts the sandboxed command in its own session and group, SIGTERM to the owned group ended Bubblewrap and the handler never ran; sent to the sandboxed process directly, it ran (ran [lifecycle verifier, September 24]). Today's stop is SIGKILL with no graceful step (source).

### 5. Selection (pinned, preferred, automatic) and decision records

Two axes stay separate. The **selection mode**, a slot field, says how many
engines serve an invocation. The **selection basis**, recorded on every
decision, says how much freedom the choice had: pinned, preferred or
automatic. The outside names PIN, PREFER and AUTO map onto the basis, never
onto a new "mode", because "mode" already names the Loop run mode. The
owner's "real time selection of preferences of engine" means that a changed
preference applies at the slot's next selection phase (the next attempt, the
next Loop, the next host start or the next release), and that a stateful
engine changes only under its slot's swap rule.

#### LE-SELECT-001

A host MUST declare, for each slot it binds, the installed engines, the
initial choice and the ordered fallbacks, or an explicit no fallback.

- Maps to: `engine_slot_configuration/v1`; `engine_selection_policy/v1`; `service_host_engines/v1`.
- Enforced by: existing `core.engines.selection_records_checks:every_slot_policy_states_an_initial_choice_and_ordered_fallbacks_or_an_explicit_no_fallback`; existing `core.engines.records_checks:a_slot_configuration_keeps_one_slot_and_names_each_installation_once`.
- Today: partly. Enforced in the records; the service host file accepts 18 top-level keys and refuses an `engines` block, so no host can declare one yet (source).

#### LE-SELECT-002

A slot configuration MUST be refused when it is read if its policy is wider
than its slot record allows.

- Maps to: `engine_slot_configuration/v1` read against `engine_slot/v1`: fallback ceiling, fallback kinds, engine kinds, ranking objectives and evidence floor; design 6.3 already states the rule.
- Enforced by: designed `host_policy_cannot_widen_the_slot_fallback_ceiling`; new `a_policy_stays_within_its_slot_record` (known-wrong: a `record_store` policy with an ordered fallback, although the slot's ceiling is none).
- Today: fails. The known-wrong policy is accepted (ran, writer; wave A problem 2).

#### LE-SELECT-003

A slot MUST use exactly one selection mode: one_of (one engine per
invocation, ordered fallbacks), set_of (one member per invocation, chosen by
the dispatch key, never by preference and never as a fallback), derived
(follows a declared field) or all_of (every eligible member runs, in declared
order inside one envelope Loop, and a declared merge rule combines the
results).

- Maps to: `selection_mode`, `dispatch_key` and `derived_from` in `engine_slot/v1`; all_of and `merge_rule` in `engine_slot/v2`. The parked scheduling vocabulary (`JoinPolicy`: all, first_success, quorum, ensemble) names when a join completes, not how results combine; all_of always waits for every member and adds a merge rule, so the parked names are not reused as merge rules.
- Enforced by: existing `core.engines.slot_checks:every_selection_mode_names_its_dispatch_key_or_its_source`; new `an_all_of_slot_declares_a_merge_rule_and_records_every_member` (known-wrong: library ingestion's format validation and safety scan slots, which run every member while calling themselves set_of).
- Today: partly. Three modes exist; all_of is new. The catalogue's set_of matches stevedore's name dispatch, one member per call; library ingestion's set_of matches its hooks, every member (source).

#### LE-SELECT-004

An all_of merge rule MUST come from a closed list that starts with
every_member_must_pass and union_of_findings and holds no rule that averages
confidence values.

- Maps to: `merge_rule` in `engine_slot/v2`; `selected_set` in `engine_selection_decision/v2`.
- Enforced by: new `an_all_of_merge_rule_is_declared_and_never_averages_confidence` (known-wrong: a merge that averages two scanners' confidence into one pass).
- Today: not built.

#### LE-SELECT-005

Every selection decision MUST record its selection basis, derived from the
policy, the applied overrides and the evidence use, and checked against them:
pinned, preferred or automatic.

- Maps to: `selection_basis` in `engine_selection_decision/v2`. Pinned: a pin applied, or a one-engine policy with no fallback and declared order only. Preferred: the declared order, narrowed or reordered by permitted prefer and exclude. Automatic: approved evidence at or above the floor reordered the choice for the exact scope; in source, a slot can choose automatically only when it has a fallback or ranking objectives (`slots.py`).
- Enforced by: new `a_decision_selection_basis_agrees_with_its_policy_overrides_and_evidence` (known-wrong: automatic recorded while a declared_order_only override applied).
- Today: not built.

#### LE-SELECT-006

A pinned choice MUST run exactly one engine: a pinned engine that is
ineligible, unavailable or changed refuses the request with every reason and
the pinned engine named, and nothing falls back.

- Maps to: the `pin` override kind; the refusal `pin_substituted`; roadmap verification case D-28-T01.
- Enforced by: existing `core.engines.selection_records_checks:a_decision_orders_and_pins_only_eligible_installations`; designed `a_pin_to_an_ineligible_engine_refuses_without_substitution`.
- Today: partly. Inside one decision record, a pinned decision with a fallback is refused with `pin_substituted`; across decisions it is not held (LE-SELECT-021), and no selector runs any of it (ran, writer).

#### LE-SELECT-007

A pin MUST state its scope (installation; exact engine, with descriptor and
installation digests; or exact composition, for a composite engine) and its
lifetime (one decision, one run, or the host policy).

- Maps to: `engine_selection_override/v2` (`pin_scope`, `pin_lifetime`, the expected digests); the new refusal code `pinned_identity_mismatch`. For a remote engine the pin also names the identity that each answer must report: an endpoint address pins a name, not an implementation, and the model gateway's existing refusal `model_identity_mismatch` already compares a reported model with the requested route.
- Enforced by: new `an_exact_pin_refuses_a_changed_descriptor_or_installation` (known-wrong: a pin on `opencode@1.2.3` served by `opencode@1.2.4`).
- Today: fails. Only installation pins exist; the reader refuses the identifier `opencode@1.2.3` itself with `invalid_identifier` (ran, writer).

#### LE-SELECT-008

A run pin MUST be inherited by every nested decision, retry and Spawned Loop
of the run, and none of them may widen it.

- Maps to: `pin_lifetime: run`; `parent_decision_digest`; `predecessor_decision_digest` (LE-SELECT-021).
- Enforced by: new `a_run_pin_is_inherited_by_nested_attempts_retries_and_spawned_loops` (known-wrong: a retry inside a pinned run that picks a newly installed version).
- Today: not built.

#### LE-SELECT-009

A ranking that differs from the host's declared order MUST carry the evidence
that changed it, or a sampled selection path.

- Maps to: the embedded ranking record and the `evidence` part of `engine_selection_decision/v1`; `_require_first_ranked_selection`, which compares the choice only with the embedded ranking's order.
- Enforced by: new `a_ranking_that_differs_from_the_declared_order_needs_evidence_that_changed_it` (known-wrong: the case below).
- Today: fails. A decision whose declared order is `(opencode, goose)` selects `goose` through a declared-order ranking that lists `goose` first, with evidence `not_requested`, and the reader accepts it at propensity 1/1 and 1/2 with a stable digest; evidence marked used with `changed_order: false` over a reordered ranking is accepted too (ran, writer; first found by the selection verifiers).

#### LE-SELECT-010

A preferred choice MUST treat a named engine by its state: an installed but
ineligible engine is skipped with its refusal recorded, and an engine the host
did not install makes the override refuse.

- Maps to: `ExplicitOrderPreference` in `core/configuration_preferences.py`, which is to filter to eligible installations before ranking.
- Enforced by: existing `core.engines.selection_records_checks:an_override_claims_only_the_precedence_of_its_sender`; existing `core.engines.selection_records_checks:a_policy_and_an_override_stay_within_the_kinds_their_sender_may_use`; new `a_preferred_ineligible_engine_is_skipped_and_an_unknown_one_refused` (known-wrong: an unknown identity silently ignored).
- Today: partly. `ExplicitOrderPreference` refuses every identity absent from its eligible snapshot, the installed-but-ineligible case included (source [committed wrapping research, section 5]).

#### LE-SELECT-011

An automatic choice MUST follow the host's declared evidence rule for the
exact scope fingerprint at or above the slot's floor, and below the floor the
declared order stands with the reason `insufficient_matched_reviewed_evidence`.

- Maps to: `ranking_objectives` and `evidence_minimum_floor` in `engine_slot/v1`; `engine_evidence_rule/v1`; sections 8.5 to 8.7 of the design.
- Enforced by: existing `core.engines.slot_checks:evidence_ranks_only_where_a_floor_of_at_least_ten_is_declared`; existing `core.engines.selection_records_checks:ranking_policy_must_end_with_the_declared_order`; designed `below_the_minimum_sample_the_declared_order_stands`; designed `lower_verified_outcome_never_outranks_on_efficiency`.
- Today: designed. Automatic selection is possible in 9 of the 45 slots, the one_of slots with ranking objectives, with floors of 10 and 30 (ran [selection line]; confirmed). No evidence records exist yet.

#### LE-SELECT-012

Anything that transfers evidence across scopes, such as a learned router, a
bandit, a similarity rule or a ramp learned from data, MUST stay closed until
the one-million-run adoption rule admits it.

- Maps to: `HeuristicAdoptionPolicy` and `DEFAULT_MINIMUM_RUNS` in `core/heuristic_adoption.py`; the proposed Constitution rule LE-DATA-001.
- Enforced by: designed `cross_scope_or_learned_ranking_is_refused_below_the_adoption_threshold`.
- Today: designed.

#### LE-SELECT-013

The propensity of a decision MUST follow its selection path: one for a
deterministic path, and the declared fraction, with its hash version and salt
reference, for a sampled path.

- Maps to: `selection_path` in `engine_selection_decision/v2`, a closed list extending the five paths of the measurement record (`first_choice`, `fallback_after:<kind>`, `override_pin`, `comparison_arm`, `frozen_population`) with evidence reorder, override prefer, run pin reuse, cascade after a gate, router rule, partition assignment, race member, noise-control arm, ramp arm, host-start binding and release binding.
- Enforced by: new `propensity_follows_the_selection_path` (known-wrong: a declared-order first choice recorded at 1/2 or 1/1000; `changed_order: true` over a one-engine order).
- Today: fails. Both known-wrong decisions are accepted (ran, writer).

#### LE-SELECT-014

A new policy or preference MUST take effect only at the slot's next selection
phase, never inside a bound attempt.

- Maps to: `selection_phase` of each binding; the terminal failure `engine_changed_after_selection`; roadmap S-6.74.
- Enforced by: new `a_policy_change_does_not_rebind_an_in_flight_attempt` (known-wrong: a preference change that alters a running step).
- Today: designed in section 8.2 of the design; not built.

#### LE-SELECT-015

Selection MUST be a deterministic step without effects whose selection
decision, with every rejection reason, is recorded before any dispatch.

- Maps to: `engine_selection_decision/v1`: the owning Loop's ledger (per attempt and Loop start), the bindings report (host start) or the release record (release). No feature flag service and no network read take part; a flag system may only feed a reviewed new policy version offline.
- Enforced by: existing `core.engines.selection_records_checks:selection_decision_records_every_rejection_reason_and_its_propensity`; designed `a_decision_exists_before_every_dispatch`.
- Today: partly. The record exists; nothing writes it (source).

#### LE-SELECT-016

A Loop's engine preference MUST claim run_override precedence only when the
run's caller supplied it, and loop_profile precedence otherwise, never
explicit_invocation.

- Maps to: `SENDER_SOURCE_KINDS` in `core/engines/selection_records.py`; section 8.4 of the design.
- Enforced by: new `a_loop_preference_cannot_claim_explicit_invocation` (known-wrong: a Loop sender that claims explicit_invocation).
- Today: fails. The claim is accepted (ran, writer; wave A problem 6).

#### LE-SELECT-017

An objective override MUST name one of the slot's ranking objectives that the
host permits for that sender.

- Maps to: `objective` in `engine_selection_override/v1`; `overrides_permitted` in the policy, which holds only override kinds today and gains permitted objectives per sender; design 6.3 already refuses a policy objective the slot does not declare.
- Enforced by: new `an_objective_override_names_a_slot_ranking_objective_the_host_permits` (known-wrong: `tokens` for `workspace_backend`, which ranks only by time; `priced_cost` for `record_store`, which has no objectives).
- Today: fails. Both are accepted, and a per-sender objective permission cannot be written (ran, writer).

#### LE-SELECT-018

A comparison between engines whose outputs are not deterministic MUST measure
the incumbent's disagreement with itself before it spends comparison
allowance, and close as not established while its loss margin is below that
disagreement.

- Maps to: `engine_comparison_policy` (its fields are read by nothing today) gains `noise_control_rate`; the evidence snapshot reports the incumbent's self-disagreement; the configuration dimension "Randomness and reproducibility" already asks for a repeated-trial policy and recorded known nondeterminism.
- Enforced by: new `a_comparison_below_the_measured_noise_spends_no_allowance` (known-wrong: a comparison that keeps spending allowance while the loss margin is below the incumbent's measured self-disagreement).
- Today: not built. In a simulation of the design's paired loss gate (200 subjects, 0.95 confidence), a noisy incumbent made every challenger fail at a loss margin of 0.05, an identical one included, so noise wastes allowance rather than letting a worse engine pass (ran [selection verifier, September 24]).

#### LE-SELECT-019

A deprecated engine SHOULD keep serving the runs pinned to it before its
deprecation until they end, with the open pinned runs listed per deprecated
engine, so that it is archived only after draining.

- Set aside when: the engine is withdrawn for safety; its pinned runs are then interrupted with a recorded reason.
- Maps to: `engine_retirement/v1` stages deprecated and archived, and a proposed stage withdrawn; `engine_bindings_report/v2`. This changes an existing rule: today a deprecated engine is never an initial choice (`engine_deprecated_as_initial`; design 11.5), and per-attempt slots decide again for each attempt, so a run pinned to an engine that becomes deprecated fails at its next attempt. The exception applies only to a decision whose predecessor carried the run pin.
- Enforced by: new `a_deprecated_engine_drains_pinned_runs_and_an_archived_one_refuses_them` (known-wrong: a run pinned to an archived engine that keeps running).
- Today: not built.

#### LE-SELECT-020

The envelope MUST check the bound engine again at use, and a changed engine
ends the attempt with the terminal failure `engine_changed_after_selection`,
never with a fallback.

- Maps to: section 8.8 of the design; `TERMINAL_FAILURE_KINDS` in `core/engines/slots.py`.
- Enforced by: designed `bound_engine_is_revalidated_at_use` (known-wrong: a harness binary replaced between selection and launch).
- Today: designed. The registries recheck their own engines at use today, for example `HarnessProcessSpec.validate_unchanged` (source).

#### LE-SELECT-021

A fallback or reuse decision MUST name the digest of the decision before it
and keep that decision's pin.

- Maps to: `predecessor_decision_digest` in `engine_selection_decision/v2`; `FallbackTransition`, which names only the previous installation and engine today; roadmap D-28-T01, whose negative control is "A pinned selection that falls back must fail".
- Enforced by: new `a_fallback_decision_keeps_its_predecessor_pin` (known-wrong: a fallback-phase decision after `opencode` failed that omits the pin and selects `goose`).
- Today: fails. That decision is accepted and round-trips with a stable digest, and no decision field names the decision before it, so D-28-T01 cannot be checked from records (ran, writer; first found by the selection verifier, September 24).

#### LE-SELECT-022

A pinned decision MUST record an empty fallback list together with
`no_fallback: true`.

- Maps to: `fallbacks` and `no_fallback` in `engine_selection_decision/v1`; the policy reader already refuses the same ambiguity.
- Enforced by: new `a_pinned_decision_records_no_fallback_explicitly` (known-wrong: a pinned decision with an empty fallback list and `no_fallback: false`).
- Today: fails. The decision is accepted (ran, writer).

### 6. Composition, with the declared and the resolved engine composition

Composition happens at two levels. **Selection-level** forms are features of
one slot's policy: ordered fallback, escalation cascade, routing by a typed
field and shadow comparison (a live ramp comes later). **Engine-level** forms
need a composite engine: pipeline, branches and merge, race, partitioned,
fused and router. The outside "logical plan" and "physical plan" are called
the **engine composition** (positions that name nested slots) and the
**resolved engine composition** (the exact installation chosen for every
position), because "plan" already has more than five meanings here.

Before any composition record is added, it is compared with what already
exists: `loop_graph_definition/v2` (single, average, vote, weighted_average,
ordered_fallback, select_best, gating_router; parked with its interpreter) and
the planned `ModelCallStrategy` protocol of the `model_call_strategy` slot,
whose `plan(request, allowance)` and `run(plan, model_access)` already split
the declared from the resolved composition. Where a combination's parts need
their own goal, authority, acceptance or Run History identity, it is a
Solution composition of Loops, never a composite engine.

| Form | Level | Builds on | Needs |
|---|---|---|---|
| Ordered fallback | selection | `initial`, `fallbacks`, `fallback_on`, fallback ceiling | policy checked against the slot (LE-SELECT-002) |
| Escalation cascade | selection | fallback on `semantic_response_rejected` (legal today only in `step_executor` and `model_access`); the live gateway's evaluator-gated route change | the gate named in each transition (LE-COMPOSE-011) and the inconclusive rule kept (LE-COMPOSE-015) |
| Routing by typed field | selection | scope keys; `dispatch_key` of set_of | nothing new |
| Shadow comparison | selection | `engine_comparison_policy/v1` | inherited mark, zero default, noise measurement |
| Pipeline | engine | nested slots | typed port checks and declared conversions |
| Branches and merge | engine | the planned vote strategy of `model_call_strategy` | a versioned merge rule; a live concurrency owner |
| Race or hedge | engine | none live | loser cancellation where harness attempts run; a live concurrency owner |
| Partitioned | engine | none | per-part support and a declared residual |
| Fused | engine | wrapper composition as an installation setting | one Run History record per logical position |
| Router | engine | scope and dispatch keys | a qualified, digested rule |

#### LE-COMPOSE-001

A composite engine MUST belong to a strategy slot above the slots it
combines, with every position naming a slot nested under that strategy slot.

- Maps to: `nested_under` in `engine_slot/v1`; the slot reader refuses a slot nested under itself and the index refuses longer cycles (`nesting_cycle`).
- Enforced by: existing refusal `slot_nested_under_or_joined_with_itself`; new `a_composition_reaches_only_slots_nested_under_its_own_slot` (known-wrong: a strategy composite with a position in `record_store`).
- Today: partly. The nesting rules exist; no composite engine exists.

#### LE-COMPOSE-002

A composite engine MUST declare its engine composition (form, positions,
typed connections, conversions, versioned rules, scheduling and effect
requirement) as the capability record of its descriptor, inside its
implementation digest.

- Maps to: `capability_record` and `capability_record_digest` in `engine_descriptor/v1`; `engine_composition/v1` as a new capability record type, not a new record family; conversions by reference to `conversion_declaration/v1` (section 7).
- Enforced by: new `a_composite_declares_its_composition_in_its_descriptor` (known-wrong: a changed router threshold under an unchanged engine version).
- Today: not built.

#### LE-COMPOSE-003

The decision that chooses a composite engine MUST record the resolved engine
composition, with every nested decision digest and every rule and conversion
digest, before the first nested dispatch.

- Maps to: `resolved_composition` and `composition_position` in `engine_selection_decision/v2`; `parent_decision_digest`. No separate plan record is added.
- Enforced by: existing `core.engines.selection_records_checks:a_nested_decision_names_its_parent`; new `a_resolved_composition_is_recorded_before_the_first_nested_dispatch` (known-wrong: a nested dispatch whose parent decision holds no resolved composition).
- Today: not built.

#### LE-COMPOSE-004

A pin on a composite engine MUST have the scope exact composition, so that a
pinned position that is ineligible or changed makes the composite refuse,
never re-route to an unpinned engine.

- Maps to: `pin_scope: exact_composition` in `engine_selection_override/v2`.
- Enforced by: new `pinning_a_composite_pins_every_position_and_rule` (known-wrong: a pinned composite that still runs after a nested engine upgrade or a changed router threshold); new `a_pinned_composite_never_substitutes_an_unpinned_engine` (known-wrong: a pinned nested engine becomes unavailable and the router picks another engine).
- Today: not built.

#### LE-COMPOSE-005

A composite whose routing depends on state that cannot be frozen and digested
MUST declare itself not pinnable, and a pin on it is refused.

- Maps to: `pinnable` in `engine_composition/v1`; a hosted router whose pool follows the market (the OpenRouter Auto Router, which also "degrades gracefully to a default model set") or a learned router updated online.
- Enforced by: new `an_unpinnable_router_refuses_a_pin` (known-wrong: a pin accepted on a composite whose routing follows a hosted pool).
- Today: not built.

#### LE-COMPOSE-006

A composite engine MUST be qualified on its own, for an exact set of nested
installations, and it loses that qualification when one of them changes.

- Maps to: `engine_qualification/v2` scope gains `nested_installations` (slot to installation digest).
- Enforced by: new `a_composite_is_qualified_on_its_own_and_loses_it_when_a_nested_installation_changes` (known-wrong: a composite counted as qualified because its nested engines are).
- Today: not built. Five `native_*` review engines in `tools/candidate_review` already wrap other engines under new identifiers (source [repository grounding verifier]).

#### LE-COMPOSE-007

A merge of branch results MUST add nothing of its own: it returns only items
that its branches returned, unless it is declared generative, and it averages
no confidence values.

- Maps to: the merge rule of `engine_composition/v1`.
- Enforced by: designed `agreement_among_models_is_evidence_never_acceptance`; new `a_merge_returns_only_items_its_branches_returned` (known-wrong: a fusion that adds an item no branch returned).
- Today: not built.

#### LE-COMPOSE-008

A partitioned composite MUST record, for every part, the position that served
it and a per-part support answer, and unsupported parts refuse unless a
residual position is declared.

- Maps to: the partition assignment in `resolved_composition`.
- Enforced by: new `every_partition_assignment_is_recorded` (known-wrong: a partitioned run with no assignment record); new `a_partition_without_a_declared_residual_refuses_unsupported_parts` (known-wrong: ONNX Runtime 1.30.0's defaults, which send unsupported parts to the CPU execution provider and leave assignment recording off).
- Today: not built.

#### LE-COMPOSE-009

When several logical positions run fused in one engine or one process, Run
History MUST still hold one record per logical position.

- Maps to: `physical_fusion_requires_logical_history` in `architecture.yaml`; `fuses_nested_slots` in `engine_descriptor/v2`.
- Enforced by: new `a_fused_run_keeps_one_history_record_per_logical_position` (known-wrong: three fused positions that leave one record); new `a_fused_engine_matches_its_unfused_composition_on_the_fixed_evaluation_set` (known-wrong: a fused engine that drops one position's filtering).
- Today: partly. The architecture flag exists; no check reads it (source).

#### LE-COMPOSE-010

A race, a hedge or any repeated execution of one request MUST use only
engines declared safe to run several times, cancel the losers where the
attempts run, and count the losers' usage as known or unknown.

- Maps to: the effect requirement of `engine_composition/v1`; the process group kill of `core/harness_process.py`, which is the live cancellation today and whose docstring warns that cancelling a process cannot undo a physical model attempt already sent.
- Enforced by: new `a_race_or_cascade_over_effectful_engines_is_refused_at_composition` (known-wrong: a race over an engine that sends email); new `a_race_is_first_completed_and_cancels_its_losers` (known-wrong: a join that waits for every branch and returns the slower one by branch identifier).
- Today: not built. The parked `first_success` join waits for every branch and picks by branch identifier; a first-completed join over thread branches could not stop the loser (cancel requested at 0.051 seconds, return at 0.801 seconds); and a race gives up the reproducible by-identifier join that design 8.12 relies on (ran [selection line and its verifier, September 24]). Restoring the parked parallel runner is a recorded owner decision under `src/loop_engine/PARKED.md`, and checks in parked suites do not count (design section 17).

#### LE-COMPOSE-011

Each transition of an escalation cascade MUST record the evaluator
installation, its score and the threshold version.

- Maps to: `FallbackTransition` in `engine_selection_decision/v2`; the derived `response_evaluator` slot; the bound `HarnessResponseEvaluator` (contract, implementation digest, qualification digest) whose verdicts the live gateway already records as `harness_response_evaluation/v2`.
- Enforced by: existing `core.engines.selection_records_checks:a_fallback_decision_follows_only_a_declared_failure_with_certain_accounting` (the records already refuse a fallback after an inconclusive evaluation); new `a_cascade_transition_names_its_evaluator_score_and_threshold` (known-wrong: a transition that records no evaluator identity or threshold version).
- Today: partly. The live gateway declares its gate; the shared transition record has no evaluator field (ran, writer; source [selection verifier, September 24]).

#### LE-COMPOSE-012

A shadow comparison MUST run only under a declared comparison policy with a
separately approved allowance, where a missing rate means zero and outputs
are never served, metered or remembered.

- Maps to: `engine_comparison_policy/v1`; sections 6.3 and 10.2 of the design.
- Enforced by: new `a_missing_comparison_rate_means_zero` (known-wrong: an absent rate read as 100 percent, the Istio default for `mirrorPercentage` and the Envoy default for a mirror policy without a runtime fraction).
- Today: designed. The policy's fields are never read (claim [wave A problem 3]).

#### LE-COMPOSE-013

Every nested slot under a comparison arm MUST inherit the comparison mark and
refuse effects and metering.

- Maps to: the comparison arm's Spawned Loop; nested decisions.
- Enforced by: new `a_shadow_mark_is_inherited_and_its_nested_effects_are_refused` (known-wrong: a nested store write under a comparison arm).
- Today: not built.

#### LE-COMPOSE-014

A composite engine MUST NOT start a thread, a process or an event loop; its
positions run as attempt Loops through the Loop runtime.

- Maps to: `subprocess_allowed_modules` in `forbidden_paths.json`, enforced by `_conformance_scan.py`, which already limits the 17 modules that may start processes; the thread and event-loop part is new.
- Enforced by: existing gate `subprocess_outside_declared_adapters`; new `a_composite_engine_starts_no_thread_or_event_loop` (known-wrong: a composite module that imports `concurrent.futures`, `asyncio` or `threading`).
- Today: not built for composites; the process part holds for the package (source).

#### LE-COMPOSE-015

An inconclusive evaluation MUST NOT move a call to another route or engine,
even when evaluator-triggered route change is permitted.

- Maps to: `allow_evaluator_route_failover` of `ModelGatewayConfig` in `core/model_gateway.py`; design 8.9 ("An inconclusive evaluation is never a pass and never permission to try another engine"); the `architecture.yaml` invariant `inconclusive_evaluation_never_becomes_a_pass_or_permission_to_retry`.
- Enforced by: existing `core.harness_response_evaluation:explicit_permission_allows_evaluator_triggered_route_change` (covers a rejected verdict with the permission); new `an_inconclusive_verdict_never_changes_route_even_with_permission` (known-wrong: the gateway's own offline two-route fixture, where an inconclusive verdict with the permission on moved the call to the second route and served its answer).
- Today: fails on the live model gateway: with the permission on, the inconclusive verdict led to two calls, providers alpha then beta, and the second answer was returned; with the permission off it stops correctly (ran, writer; first found by the selection verifier, September 24). No repository check covers an inconclusive verdict with the permission on.

### 7. Support reports and required semantics

A request field is either required or advisory. An advisory field, an
optimization hint in the outside research, may be ignored, and the ignoring is
recorded. A required field that an engine cannot honour refuses before any
effect. Two kinds of answer stay apart: the compatibility verdict (can this
engine honour the request?) and the work split (how much of an advisory
optimization does the engine do itself?). DataFusion's pushdown answers
(exact, inexact, unsupported) are work splits, because all three keep the
query result correct. Validation profiles, conversion declarations and stream
semantics are defined once, in a new version of the interaction catalogue, and
referenced by digest from the rows, the Loop port bindings, the harness wire
codecs and the engine compositions.

#### LE-SUPPORT-001

Each field of an edge request MUST be declared required or advisory.

- Maps to: the request record of each edge; `HarnessExecutionRequirements` gains `optional_features` beside `required_features`.
- Enforced by: new `every_edge_request_field_is_required_or_advisory` (known-wrong: a request record with an undeclared field).
- Today: partly. Required features exist for harnesses only (source).

#### LE-SUPPORT-002

An engine that cannot honour a required field, or cannot say whether it can,
MUST refuse before any effect.

- Maps to: `requirement_comparison` in `engine_slot/v1`, given one shape: a function of the requirements and the declaration that returns the unmet requirement codes, as `unmet_harness_requirements` already does; today 7 of 45 slots name a comparison and only 3 compare a request with a declaration (ran [activation line]).
- Enforced by: new `a_required_field_an_engine_cannot_honour_refuses_before_effects` (known-wrong: an engine that ignores a required filter and returns a wider result); new `a_requirement_comparison_compares_requirements_with_a_declaration` (known-wrong: `WorkspaceBackend.availability`, an observation named as a comparison).
- Today: partly. Enforced for harness features; not for other slots.

#### LE-SUPPORT-003

An advisory field that an engine ignores MUST be recorded in its attempt.

- Maps to: the attempt record; `disabled_optional_features` of the store handshake.
- Enforced by: new `an_ignored_advisory_field_is_recorded` (known-wrong: an ignored hint that leaves no trace).
- Today: partly. Only the store handshake records disabled optional features (source).

#### LE-SUPPORT-004

Eligibility MUST record, for every slot, one compatibility verdict from the
store handshake vocabulary, and an eligible entry never carries incompatible
or unknown.

- Maps to: `catalog.handshake` verdicts (compatible, compatible_with_migration, compatible_with_degradation, compatible_read_only, compatible_export_only, incompatible, unknown, refused_by_policy), with `degraded_behavior` named; `EligibilityEntry` in `engine_selection_decision/v2`.
- Enforced by: new `an_eligible_entry_never_carries_an_incompatible_or_unknown_verdict` (known-wrong: an eligible entry with the verdict unknown); new `a_degraded_verdict_names_its_degraded_behavior` (known-wrong: compatible_with_degradation with no degraded behavior named).
- Today: not built. Engine eligibility is binary, eligible or refused with one of 16 codes (source).

#### LE-SUPPORT-005

An answer about how much of an advisory optimization an engine performs MUST
be recorded as a work split (the engine does all of it, the engine does part
and the envelope completes and checks it, or the envelope does all of it),
never as a compatibility verdict.

- Maps to: the attempt record; partitioned compositions (LE-COMPOSE-008).
- Enforced by: new `a_work_split_answer_is_never_read_as_a_compatibility_verdict` (known-wrong: an inexact pushdown answer recorded as compatible_with_degradation).
- Today: not built. The repository grounding line proposed that mapping; its verifier refuted it from the DataFusion 55.1.0 source (source).

#### LE-SUPPORT-006

Each edge contract MUST name the validation profile that checks its request
and result: the dialect and the rule for an unknown dialect, the rule for
unknown keywords, the asserted formats, the reference rule (local or pinned,
never fetched), the rules for unknown and missing fields, numbers and time,
the match mode and the validator implementation.

- Maps to: `validation_profile/v1` (new), defined once in `component_interaction_catalog/v2`; the policy of model response admission becomes its first instance and the candidate review profile `original_native_package/v1` its second; the 13 JSON Schema call sites build their validators through one helper from a profile.
- Enforced by: new `every_edge_names_a_validation_profile` (known-wrong: a row without a profile); new `a_schema_in_an_unknown_dialect_is_refused` (known-wrong: a schema with an unknown `$schema` validated as 2020-12); new `every_asserted_format_refuses_its_known_wrong_value` (known-wrong: `date-time: "not a date"`).
- Today: not built. `pyproject.toml` requires `jsonschema>=4.20` without a pin, so the service image validates with whatever version resolves at build time (source [validation line]). None of the 13 call sites passes a format checker or a pinned reference registry; an unknown `$schema` falls back to 2020-12 with only a deprecation warning; a schema with the misspelled keyword `requried` passes; `date-time`, `uri` and ten other formats pass even with the checker, because their optional packages are not installed; the continuous integration step "Validate benchmark registry" accepts `as_of: "not a date"` (ran [validation line]; reproduced by its verifier). JSON Schema 2020-12 makes `format` an annotation unless the Format-Assertion vocabulary is required (source).

#### LE-SUPPORT-007

A contract match mode named exact MUST compare type as well as value, so that
true, 1 and 1.0 are three different values.

- Maps to: `MATCH_MODES` and `match_contract` in `core/contract_matching.py`; the blocking keys of `semantic_blocked`.
- Enforced by: new `exact_match_separates_booleans_integers_and_floats` (known-wrong: `{"approved": 1}` accepted as exactly `{"approved": true}`, and `{"n": 0}` as exactly `{"n": false}`).
- Today: fails. The exact and canonical modes use Python equality (ran, writer). Today's callers compare text, so the defect is latent until a contract with Boolean fields uses these modes (source [validation line]).

#### LE-SUPPORT-008

A conversion between two typed ports MUST be a named Adapter Loop or a
declared conversion that states its source and target contracts, its
information class, the losses it permits, its rule for unknown input and for
failure, data ownership, effects and cost class.

- Maps to: `conversion_declaration/v1` (new), with information classes exact, exact_one_way, normalizing, bounded_lossy, dropping and substituting; `LoopPortBinding.adapter_loop_ref` and `validate_loop_connection` in `loop/loop_contract.py`; the conversions of `engine_composition/v1`; decode and encode of each engine adapter.
- Enforced by: new `a_lossy_conversion_cannot_feed_an_exact_port` (known-wrong: a bounded_lossy conversion bound to a port whose profile's match mode is exact; today `validate_loop_connection` accepts any adapter name).
- Today: partly. An Adapter Loop is required for a role conversion; loss, ownership and cost are not declared, and loss is declared in five different ad hoc ways (source [validation line]).

#### LE-SUPPORT-009

A change in a dependency MUST invalidate exactly the derived state and the
qualifications that depend on it.

- Maps to: `EmbeddingSpace` and `require_same_space`; `ParameterDefinition.affects_qualification`; `qualification_invalidated` in `configuration_update/v1`.
- Enforced by: new `a_dependency_change_invalidates_exactly_its_dependents` (known-wrong: an index reused after its embedding space changed; a qualification dropped for an unrelated timeout change).
- Today: partly, for embedding spaces and configuration updates (source).

#### LE-SUPPORT-010

Every loss that a conversion permits MUST be counted in its result.

- Maps to: the permitted losses of `conversion_declaration/v1`; `HarnessProcessResult`.
- Enforced by: new `every_permitted_loss_is_counted` (known-wrong: harness output with two invalid UTF-8 bytes decoded into two replacement characters with no count).
- Today: fails. The output is decoded with `errors="replace"` and nothing counts the replacements; the decoded text can grow to about three times the raw byte cap (ran [validation line and its verifier]).

#### LE-SUPPORT-011

A digest MUST name the canonical form that it was computed under.

- Maps to: `canonical_form` of `validation_profile/v1`; the six canonical JSON functions in `core/configuration_capabilities.py`, `core/record_operations_records.py`, `core/stage_evidence_projection.py`, `core/prompt_experiment.py`, `core/reusable_capability_records.py` and `core/code_intelligence_assets.py`.
- Enforced by: new `a_digest_names_its_canonical_form_and_is_hash_seed_independent` (known-wrong: `prompt_experiment._canonical`, which passes `default=str`, so a set gives a different digest under each of four hash seeds).
- Today: fails. The six functions give two byte forms for "é" and three outcomes for NaN (two refuse, four write `NaN`, which is not JSON); no record says which form a digest used (ran [validation line]; reproduced by its verifier). The repository makes no RFC 8785 claim (source).

#### LE-SUPPORT-012

A record time MUST be parsed by one RFC 3339 grammar that gives the same
answer on every supported interpreter.

- Maps to: `core.engines.records.instant` and the other `datetime.fromisoformat` readers; `time` of `validation_profile/v1`.
- Enforced by: new `one_time_rule_on_every_supported_interpreter` (known-wrong: the same time strings read on Python 3.10 and 3.12).
- Today: fails. On Python 3.10 the rule refuses `2026-09-23T12:00:00.5Z`, a nine-digit fraction and four spellings outside RFC 3339 that 3.11 and later accept, and 3.11 and later cut nine fraction digits to six; continuous integration runs 3.10, 3.11 and 3.12, and the service image runs 3.12 (ran [validation line]; its verifier ran 3.10, 3.11, 3.12 and 3.14).

#### LE-SUPPORT-013

A record reader MUST keep or refuse every field it receives, never drop one
silently or invent a value for one.

- Maps to: the `from_dict` readers under `src/`; `core.engines.records.read_record`, which already refuses another version, an unknown field and a missing field.
- Enforced by: new `a_record_reader_neither_drops_unknown_fields_nor_invents_text` (known-wrong: `EvaluationSuite.from_dict`).
- Today: fails for that reader, which drops unknown fields at two levels, stores `version: null` as the string "None" and accepts a stored population digest that differs from the recomputed one (ran [validation line and its verifier]). Of 142 `from_dict` readers, a pattern scan flags between 34 and 87 as having no visible unknown-field check, depending on the pattern (ran, heuristic).

#### LE-SUPPORT-014

A check that validates the messages of a peer protocol MUST name its
validation profile, schema-strict or reference-lenient, and the exact schema
release that it validates against.

- Maps to: `validation_profile/v1`; the planned Agent Client Protocol step executor (roadmap S-6.31, package X4); the protocol checks of the `protocol_endpoint` slot.
- Enforced by: new `a_peer_protocol_check_names_its_profile_and_schema_release` (known-wrong: an Agent Client Protocol message check pinned to the Rust crate version `v1.9.1` instead of a schema tag, or one that expects the version 1 schema to refuse an extra field).
- Today: not built. The Agent Client Protocol releases its schemas under their own tags, `schema-v1.23.0` and the draft `schema-v2.0.0-alpha.5` (September 18, 2026). The version 1 schema forbids no extra field anywhere (120 `additionalProperties: true`, no `additionalProperties: false`), and the reference Rust crate collapses outer shape errors to defaults and skips invalid items silently (ran and source [validation line; testing verifiers]). So "validates against the pinned schema" and "is accepted by the reference implementation" are two different profiles.

### 8. Status: alive, ready, capacity, qualified, result verified, and binding facts

Five facts about engines stay separate, and none implies another. The
binding facts of a slot are a second group, about configuration rather than
about one instance.

| Fact | Question | Subject | Record |
|---|---|---|---|
| alive | Is the instance there and answering at all? | one engine instance at one fencing token | `engine_availability_snapshot/v1` (new); `ModelRouteAvailabilitySnapshot` for model routes |
| ready | Can it serve this edge now, with its effective configuration loaded? | one engine instance at one fencing token | the same snapshot |
| capacity | How many more engine leases can it take now? | one engine instance at one fencing token | the same snapshot |
| qualified | Did an independent reviewer pass this installation for this scope? | one engine installation | `engine_qualification/v1` (exists) |
| result verified | Did an independent verifier accept this one result? | one result | the independent verdict (exists) |
| binding facts | What is desired, prepared, routable, observed and last rejected? | one slot of one host | `engine_bindings_report/v2` (proposed) |

#### LE-STATUS-001

Alive, ready and capacity MUST be recorded as three separate expiring facts
of one engine instance at one fencing token.

- Maps to: `engine_availability_snapshot/v1` (new), whose facts are `ConfigurationFact` values (source, digest and expiry; unknown after expiry); for model routes the existing `ModelRouteAvailabilitySnapshot` is the snapshot (`reachable`, `model_loaded`, `available_concurrency`, `queue_depth`, with an expiry) and gains the fencing token; `service_health/v2` keeps the service's own alive and ready.
- Enforced by: new `alive_ready_and_capacity_are_separate_facts` (known-wrong: a heartbeat counted as ready; a detected binary counted as ready); designed `workspace_engine_availability_is_not_runtime_verification`.
- Today: partly. The route snapshot exists and the route selector refuses a missing, stale or unusable one, but nothing reads its `available_concurrency` and `queue_depth`; no engine instance snapshot exists (source [lifecycle verifier, September 24]).

#### LE-STATUS-002

The availability fact that selection reads MUST be derived at decision time
from an unexpired availability snapshot.

- Maps to: `availability` in `engine_descriptor/v1`; eligibility screen 5 (`engine_unavailable`).
- Enforced by: new `an_expired_availability_snapshot_makes_an_engine_ineligible` (known-wrong: an engine selected on an expired ready fact).
- Today: partly. The fact type expires correctly; no snapshot feeds it outside model routes.

#### LE-STATUS-003

An engine qualification MUST name a producer, a reviewer and an engine that
are three different identities.

- Maps to: `engine_qualification/v2` gains `producer` and a typed kit reference (LE-TEST-003).
- Enforced by: existing `core.engines.records_checks:a_qualification_is_independent_evidenced_and_bounded_in_time`; new `a_qualification_names_a_producer_other_than_its_reviewer` (known-wrong: the author of an engine signs its qualification).
- Today: partly. The guard compares the reviewer only with the engine reference and name, there is no producer field, and evidence is an untyped reference and digest pair (source [testing verifiers]).

#### LE-STATUS-004

A record MUST NOT mark an engine, an installation or an instance as
verified: verification belongs to one result, and completing an engine
attempt is never acceptance.

- Maps to: `operation_cost_record/v2` has no verified disposition; the independent verdict joins later.
- Enforced by: existing `core.external_harness:contract_only_adapter_completion_does_not_claim_task_acceptance`; new `a_record_that_marks_an_installation_verified_is_refused` (known-wrong: a cost record whose producer writes verified).
- Today: partly. Version 1 of the cost record lets the producer write verified (source; design section 9.3).

#### LE-STATUS-005

A lifecycle record MUST NOT state a step or an observation that was not
performed or observed.

- Maps to: `hibernate()` and `HIBERNATION_STEPS` in `core/instance_hibernation.py`; every record of this section.
- Enforced by: new `hibernation_never_records_a_step_it_did_not_perform` (known-wrong: the case below).
- Today: fails. With the module's own `ProcessTreeController`, which offers neither `verify_checkpoint` nor `fence_publication`, the report lists `checkpoint_verified` and `publication_fenced` and the reason "checkpoint verified, publication fenced, worker confirmed stopped" after only SIGUSR1 and SIGTERM were sent (ran [lifecycle line]; reproduced by both verifiers). The self-test asserts `publication_fenced` as the last step of an unconfirmed stop, so the repair changes a passing check; until a controller offers verification and fencing, a hibernation stops at `checkpoint_written` with a typed reason.

#### LE-STATUS-006

The bindings report MUST record, for each slot, the desired configuration,
whether it is prepared, whether it is routable, what was observed to run, and
the last rejected desired configuration, as five separate facts.

- Maps to: `engine_bindings_report/v2` (desired: digest and sequence number; prepared: evidence or reason, with expiry; routable: true, false or unknown, with an observation time; observed: identities read from the engines' answers; rejected: digest, reason, first failure time and attempts); the health record carries the report digest. The catalogue already works this way: its pointer is desired (with `sequence`), the view build is preparation, the view assignment is the routable switch.
- Enforced by: new `a_bindings_report_keeps_desired_prepared_routable_observed_and_rejected_apart` (known-wrong: a slot reported bound while its preparation failed); new `a_rejected_desired_release_is_named_in_health` (known-wrong: a health answer that names neither the rejected release nor its revision).
- Today: fails. Version 1 of the report refuses the fields `desired_generation`, `observed_generation`, `draining` and `rejected`; the catalogue refresher's status and the health answer name neither the desired nor the rejected release, while the operator status command does name the desired pointer (ran, writer; activation line and its verifier). Envoy's xDS protocol says an acknowledgment "does not mean that the configuration has been applied successfully" (source).

#### LE-STATUS-007

A failed preparation of a desired configuration MUST leave the previous
effective configuration serving, also across a restart.

- Maps to: the bindings report; `CatalogueRefresher` and the start path of `core/service_runtime/http_entrypoint.py`.
- Enforced by: new `a_failed_preparation_keeps_the_previous_effective_configuration` (known-wrong: desired configuration B fails to prepare and A is stopped anyway); new `a_restart_serves_the_last_prepared_release_when_the_desired_one_is_rejected` (known-wrong: the case below).
- Today: partly. While the process runs, the refresher keeps serving the previous view. After a rejected desired release, a restart refuses to start with `body_digest_mismatch`, although the previous release is still stored and verified (ran, writer; first found by the activation verifier). This is a design choice recorded here: NVIDIA Triton keeps the old model after a failed reload only in its POLL mode, which it does not recommend for production (source, Triton 2.72.0).

#### LE-STATUS-008

An unchanged rejected desired configuration SHOULD be prepared again only on
a capped backoff, while a changed one is prepared at the next check.

- Set aside when: one preparation costs less than one check.
- Maps to: `CatalogueRefresher.status()`, which gains desired and rejected; `service_catalogue_view/v2`.
- Enforced by: new `a_rejected_desired_release_is_rebuilt_on_a_backoff` (known-wrong: three checks and three full builds of the same unchanged desired token); new `a_changed_desired_release_is_built_at_the_next_check` (known-wrong: a changed desired release that waits for the backoff of the rejected one; the behavior holds today and the check protects it).
- Today: fails for the backoff. Three checks gave three full builds, with two body reads each and three identical journal rows; a desired release that moves on is built at once (ran, writer; activation line). Envoy warns that resending a rejected set causes "needless work" (source).

#### LE-STATUS-009

A release MUST prepare its packaged grants and billing policy before the new
process accepts requests.

- Maps to: `.github/workflows/fly-pilot.yml`, which deploys with `--strategy immediate` and applies the grants and the billing policy afterwards; `serve` in `core/service_runtime/http_entrypoint.py`; a stored grant application record keyed by the packaged manifest digest, so that a restart without a new manifest prepares nothing.
- Enforced by: new `a_release_prepares_grants_and_billing_before_it_serves` (known-wrong: a fresh start of a new image that answers a read before its packaged grants are applied); new `snapshot_grants_that_name_unserved_bindings_are_reported` (known-wrong: health passes every catalogue check while the item list is empty).
- Today: fails by the release order. The workflow's own comments record that release 12 "offered no item until this command was run by hand" and that release 13 "served for a day" with checkout and the portal unavailable; in that window the health answer passes every catalogue check while the list holds no item (source; ran [activation line]). Fly's `immediate` strategy replaces machines "without waiting for health checks to pass", and its canary and blue-green strategies cannot be used with volumes (source).

#### LE-STATUS-010

A release MUST write only a durable state version that the release before it
can read.

- Maps to: the catalogue state marker and its rollback rule in `core/service_runtime/catalogue_releases.py`; the release record's list of supported state versions.
- Enforced by: new `a_release_writes_only_a_state_version_its_predecessor_reads` (known-wrong: a release that lists and writes catalogue state version 2 at once, so that a rollback to the previous image refuses to start).
- Today: holds so far, unchecked. No release has raised the catalogue state version yet (claim [activation line]).

#### LE-STATUS-011

Every accepted protocol request MUST leave a durable record that names the
protocol revision, the era, the classification rule version and the
implementation it was served under.

- Maps to: a new version of `service_usage` or a protocol decision record, kept outside the usage record's idempotency digest; roadmap D-20-T01 ("each decision names the selected revision").
- Enforced by: new `every_protocol_request_records_its_protocol_terms` (known-wrong: a usage record that names no revision, as every usage record does today).
- Today: fails. `service_usage/v1` holds `at`, `body_digest`, `item_identity`, `quantity`, `record_type`, `request_digest`, `request_id_digest`, `tenant_id` and `unit`, and no stored record names a revision (ran [protocol revisions line]).

#### LE-STATUS-012

A model route that classified failures take out of use MUST be recorded as
an expiring route availability snapshot whose reason is the failure class,
and the one attempt that probes the route afterwards is a counted, authorized
model call.

- Maps to: `ModelRouteAvailabilitySnapshot` and its `usable(at)` in `core/model_routing_records.py`; the route selector, which refuses a missing, stale or unusable snapshot (`core/model_routing_selector.py`); the failure classes of `core/provider_failure_classes.py` (outage, allowance, configuration, request, contract, unclassified); `retry_after_seconds`; section 8.3 of the design, which already says "an open circuit breaker is simply an expiring availability fact". One snapshot covers one downstream authority: provider origin, model and credential reference, never a whole slot.
- Enforced by: new `a_probe_after_a_route_is_set_aside_is_a_counted_authorized_attempt` (known-wrong: the probe call missing from the model-call count).
- Today: not built. Route health is run-local and advisory, with a threshold of three transport failures (`route_health.py`), and no module outside the check modules constructs a route availability snapshot; the selector reads the snapshots its caller supplies (source, writer; lifecycle verifier, September 24).

### 9. Testing at three levels, and containers

Level 1 is a **conformance kit** per slot: every engine passes the same
fixtures alone. Level 2 is a **composition test** per group of joined or
nested slots. Level 3 is a **journey test** of a customer path end to end.
Lifecycle drills, containers, properties, comparisons and mutants are used
inside the levels. The roadmap's names "contract test kit" (S-6.72, S-6.75,
S-6.86, S-6.87 and D-27) and "contract kit" (D-27-T02) mean the conformance
kit.

#### LE-TEST-001

Each engine slot MUST have one conformance kit, parameterized by engine, that
every engine of the slot passes alone through the edge with the same
fixtures.

- Maps to: `conformance_suite` in `engine_slot/v1`; the shared kit runner in `core/engines/` (new); roadmap S-6.72. The engine list comes from the slot's factory table; the step executor kit waits for `core.step_execution.engines`, because `HarnessRegistry` registers nothing on import and has no canonical population.
- Enforced by: existing `core.engines.slot_checks:every_active_engine_slot_conformance_suite_is_collected`; existing gate `modules_whose_self_test_the_suite_never_runs`; new `every_registered_engine_runs_its_slot_kit` (known-wrong: an engine that is registered and never run by the kit).
- Today: fails. 30 slots name a suite, 28 are collected, 15 name none, 8 share `core.service_runtime.http_checks`, and only `run_store_conformance(store)` takes an engine as input (ran, writer). The first kits can start where factory tables already work: library ingestion (for example the two MinHash engines of `library_near_duplicate`) and the candidate review pre-checks, whose run-time calibration already asks every reviewer engine about planted known-wrong and known-good items (`candidate_review_calibration_set/v1`, `candidate_review_calibration_result/v2`) (source [testing verifier, September 24]).

#### LE-TEST-002

Every kit assertion MUST name a broken engine that fails it, and the kit's
own self-test fails when no broken engine fails an assertion.

- Maps to: the kit's broken engines; roadmap verification case D-27-T02.
- Enforced by: new `every_kit_assertion_names_a_broken_engine_that_fails_it` (known-wrong: an assertion that no broken engine fails).
- Today: not built. The pattern exists as the `MUTANTS` table of `tools/test_install_selected_material.py`, 47 entries whose meta-test requires a failure by assertion (source).

#### LE-TEST-003

A kit run MUST write one `conformance_kit_report/v1`, which replaces
`store_conformance/v1` and names the kit version and digest, the engine and
installation digests, the execution mode, the network policy and every
section that ran, was closed by declaration or was not tested for a named
missing dependency.

- Maps to: `conformance_kit_report/v1` (new), cited by `engine_qualification/v2` through a typed kit reference; `store_conformance/v1`, which `run_store_conformance` returns today and which the pre-launch version policy replaces rather than keeps beside the new record.
- Enforced by: new `a_qualification_bound_to_an_older_kit_digest_is_refused` (known-wrong: a qualification that cites a report of an older kit); new `a_section_that_could_not_run_is_never_reported_as_passed` (known-wrong: a section skipped for a missing container daemon reported as passed).
- Today: not built. The self-test already requires NOT_APPLICABLE with the missing dependency named (source).

#### LE-TEST-004

Every joined or nested pair of slots MUST have a composition test over its
typed edges, with all pairs of engines on every push and the full matrix at
night.

- Maps to: `nested_under` and `joined_with` in `engine_slot/v1`; the `interaction` unit of `independent_qualification`.
- Enforced by: new `every_active_interaction_names_a_collected_group_check` (known-wrong: an active interaction row whose verification names no collected check); new `a_nested_model_call_is_counted_once` (known-wrong: a nested model call counted by the parent and the nested envelope).
- Today: not built. 14 slots are nested and 2 are joined (ran [testing line]; confirmed).

#### LE-TEST-005

Each customer journey MUST be tested in process on every push, in containers
at night and live after a release, with offered, fetched, installed,
reported, used and verified kept as separate facts.

- Maps to: the installer and client journeys; the release checks on every hostname.
- Enforced by: designed `offered_fetched_installed_and_used_are_recorded_as_separate_facts`.
- Today: partly. The in-process and container journeys exist; the container drill runs by hand (source).

#### LE-TEST-006

Each released version of a separately deployed client MUST have an
expectation file of the requests it sends and the fields it reads, verified
against every release candidate of the service.

- Maps to: the installer `tools/install_selected_material.py`, the Pi extension `baltor.ts` and later native clients; Pact version 4 files with pact-python 3.4.1 or an in-repository check; no broker is needed for one provider. Third-party harness clients do not write pacts, so Baltor keeps its own expectation files per protocol revision for them, apart from the official conformance runner.
- Enforced by: new `every_released_client_version_has_an_expectation_file` (known-wrong: the Pi extension, downloadable since September 24 with no expectation file).
- Today: not built. A pinned pact trial found the live skew in 0.53 seconds (ran [qualification tools line]); the Pi extension is checked only byte for byte (source [testing verifier, September 24]).

#### LE-TEST-007

A lifecycle drill MUST inject faults at named operations and kill at named
points, and every fault ends in a typed refusal or a typed uncertain state,
with no torn state and no unaccounted file.

- Maps to: the kit's fixture adapters; the recorded command runner of the container drill. Declared seams (clock, file operations, command runner, transport) are the preferred design; replacing most functions also works, and the installer's guard refuses only replaced functions that it inspects (`open`, `link`, `unlink`, `mkdir`, `access`) (ran [testing verifier, September 24]).
- Enforced by: new `a_stopped_run_leaves_no_unaccounted_file` (known-wrong: hidden `.partial` files that no later run removes); new `a_read_back_fault_after_placement_is_typed_per_item` (known-wrong: `read` and `fstat` faults that escape as an untyped `OSError` and stop the whole install run).
- Today: fails. A kill inside the write leaves a hidden `.SKILL.md.<uuid>.partial` that no later run removes; a failed read-back after the file is already placed reports a refusal; a `read` or `fstat` fault after the link ends the run as `unexpected_error` and skips the remaining items; the discovered `SKILL.md` itself is never torn (ran [testing line]; confirmed and widened by both verifiers).

#### LE-TEST-008

An engine that runs code this repository did not write, needs a network
policy or must prove a clean environment MUST run its kit in a container with
a digest-pinned image, a non-root user, a read-only root, all capabilities
dropped, no new privileges, memory and process limits, no network or an
internal network, and an egress probe that must fail.

- Maps to: `tools/check_client_journey_in_containers.py`; roadmap S-6.72.
- Enforced by: new `a_container_run_includes_a_failing_egress_probe` (known-wrong: a containerized engine that reaches the network against its policy); new `a_run_starts_by_removing_labelled_leftovers` (known-wrong: containers of a killed run still present at the next start).
- Today: partly. The client journey drill already labels its resources, uses internal networks, a read-only root, a temporary file system and a non-root user; it lacks `--cap-drop ALL`, `no-new-privileges`, limits, the egress probe and a start-up sweep of labelled leftovers (source [testing verifier, September 24]).

#### LE-TEST-009

A release MUST refuse to bind an engine whose latest nightly kit report
failed or is older than the declared age.

- Maps to: `.github/workflows/fly-pilot.yml`; the scheduled workflow pattern of `.github/workflows/live-pulse.yml`; roadmap S-6.76.
- Enforced by: new `a_release_refuses_a_bound_engine_whose_latest_kit_report_failed_or_expired` (known-wrong: a release that binds an engine whose last nightly kit run failed).
- Today: not built. Two workflows run on a schedule: `live-pulse.yml` (since `3d48a36c`, `cron: "17 */6 * * *"`), a read-only pulse of every hostname and the identity provider, and `research-watch.yml` (since `e6346075`, `cron: "41 7 * * *"`), a read-only check of 17 watched research sources that opens or updates one issue when a source changed. No kit, container drill, harness binary or model journey runs on a schedule, and the roadmap's recurring reviews are all `not_scheduled` (source). A local timer runs the overnight candidate batch from the shared checkout; a nightly test tier runs on an exported tree instead (source [testing verifier, September 24]).

#### LE-TEST-010

A slot whose outputs have no exact expected answer, such as search ranking,
layouts or harness runs, SHOULD test properties and metamorphic relations,
with a repeatable profile on every push and failures found at night pinned as
explicit examples.

- Set aside when: every fixture of the slot has an exact golden answer.
- Maps to: the slot's conformance kit; Hypothesis 6.168.1, whose `ci` profile is derandomized with no example database.
- Enforced by: new `a_request_word_after_the_term_cap_is_read_or_reported` (known-wrong: a request whose only matching word is the thirteenth returns no hits and names no dropped word, in the default lexical mode); new `registration_order_does_not_change_results` (known-wrong: the engine-side full-text search, which breaks score ties by insertion order).
- Today: both known-wrong cases hold for the engine-side search; the served search already sorts by identity before it breaks ties (ran [testing line]; corrected by both verifiers). The engine-side `Retriever` is also built by intelligence layers, user feedback intelligence, runtime settings and `loop/encapsulate.py` (source).

#### LE-TEST-011

A composition test report MUST state the covering strength that an
in-repository counter measured, never the strength that its generator claims.

- Maps to: the composition tests of LE-TEST-004; the configuration grid guide; PICT at a pinned commit for row generation.
- Enforced by: new `a_composition_report_states_its_measured_strength` (known-wrong: a suite from ACTS Basic, which ignores constraints and prints "Coverage has been verified!" while 11 of its 17 pairwise rows break them).
- Today: not built. PICT order 2 covered all valid pairs of 306 valid configurations in 17 rows and order 3 all valid triples in 59, confirmed by NIST CCMCL; PICT's documented `ISPOSITIVE([p])` form is skipped with a warning and exit code 0 (ran [qualification tools line]).

#### LE-TEST-012

An absence rule of an edge, such as no body in search hits, MUST be enforced
by a provider-side check or a strict published response schema, never by a
consumer contract alone.

- Maps to: the published response schemas of LE-EDGE-010; the service's own privacy checks.
- Enforced by: new `an_absence_rule_has_a_provider_side_check` (known-wrong: a service that leaks item bodies into search hits and still passes the installer's consumer contract).
- Today: not built. In that trial the pact passed, the real installer accepted the leak, and only a strict response schema refused it; Pact's documentation says "You cannot expect a field to not be present in a response" (ran [qualification tools line]; source).

#### LE-TEST-013

Every kit MUST run in a scrubbed environment and name every section it
skipped, with the missing dependency.

- Maps to: the kit runner; the tools suite under `tools/`; the self-test's NOT_APPLICABLE records.
- Enforced by: new `a_kit_runs_in_a_scrubbed_environment_and_names_every_skip` (known-wrong: a test that passes only when a real provider key is in the environment).
- Today: fails for the tools suite. Eight consecutive red runs on `main` came from a tools test that needed a real provider key, and the tools suite reports only "skipped=6" without names (source [testing verifier, September 24]). The retrieval self-test downloads model weights from the Hugging Face hub when its cache is empty: with the network blocked it made one or two connection attempts to `huggingface.co`, depending on the cache folder, and then recorded its semantic canary as not tested with the outcome `BLOCKED_ENVIRONMENT` (ran, writer). The skip is named correctly; the download is the part a kit must not make.

#### LE-TEST-014

A property-test profile MUST be calibrated with named mutants and a vacuity
guard before it runs on every push.

- Maps to: the state machines of stateful engines, starting with `resolve_preference` and the catalogue release lifecycle.
- Enforced by: new `every_state_machine_profile_detects_its_named_mutants` (known-wrong: a profile under which a seeded mutant survives); new `a_state_machine_run_that_reaches_no_selection_is_refused` (known-wrong: a run that passes with zero selections).
- Today: not built. At 50 derandomized examples, 2 of 6 seeded mutants of the preference resolver survived; at 200 all six were caught in about 3 seconds (ran [qualification tools line]).

#### LE-TEST-015

A kit section MUST be generated only from a closed field of a record, or from
a reviewed table that maps a free label to an assertion.

- Maps to: the shared kit runner; the closed fields of the slot record (edge record types and versions, the unavailable result, failure kinds); the free labels of the interaction rows in `component_interactions.yaml`; roadmap S-6.72.
- Enforced by: new `every_generated_kit_section_comes_from_a_closed_field_or_the_reviewed_label_table` (known-wrong: a section generated from the free delivery label `synchronous_exactly_once_per_request` with no reviewed mapping).
- Today: not built. The 53 rows use near-unique free labels: delivery has 32 distinct values, privacy 34, verification 39, retry 39, repair 27 and timeout 16; only cancellation (8) and failure (9) are small sets, and a label carries no number, so a timeout of `request_deadline` names no deadline (ran, writer; first found by the testing verifier, September 24).

### 10. Isolation and the choice of execution

"Containerize" in the owner's words means: every engine declares its
isolation, and code that needs isolation runs in a container or sandbox. A
functional component boundary is not by itself a container boundary, and a
vetted pure library gains nothing from a container per call.

#### LE-ISOLATE-001

How an engine is executed MUST be described by separate execution fields,
never by one binding word: invocation mechanism (direct call, supervised
subprocess, local service, remote request), application protocol with its
exact revision, executable format with its runtime, isolation and locality.

- Maps to: `supported_executions` in `engine_descriptor/v2`; `execution` in `engine_installation/v2`; `isolation` and `locality` exist in `engine_descriptor/v1`. For the Model Context Protocol the application protocol names the revision, the era with its classification rule version, the transport, the extension profile, the authorization profile, the implementation revision and the host's served set.
- Enforced by: new `execution_fields_are_declared_separately` (known-wrong: a descriptor that writes `mcp` where the invocation mechanism belongs, or a bare `mcp` as its protocol).
- Today: partly. Isolation and locality exist; the rest is implied by engine kinds. Three vocabularies describe execution today, and the committed wrapping research calls these "composable deployment patterns, not mutually exclusive values of one field" (source). Baltor's own protocol server reports the constant server version `1.0.0` whatever release runs, so a client that pins the service cannot tell releases apart from the answer (ran [protocol revisions line]; reproduced on `e6346075`, ran, writer).

#### LE-ISOLATE-002

An installation MUST choose the lightest execution that meets, in this order,
the isolation required by the step's authority and the code's trust, the
state and lifetime the work needs, the placement of its resources, and then
measured overhead.

- Maps to: `execution` in `engine_installation/v2`; eligibility screen 8 (`permission_not_granted`).
- Enforced by: new `an_execution_weaker_than_the_required_isolation_is_ineligible` (known-wrong: a container-only engine installed in process for untrusted input); review of the installation by an independent reviewer.
- Today: not built. A process started in a median of 10.4 milliseconds and a container in 230.4 milliseconds on this machine (claim [repository measurement of September 18]).

#### LE-ISOLATE-003

Code from an untrusted or unreviewed source MUST NOT run in this process or in
the restricted local workspace.

- Maps to: the `process_confinement` and `workspace_backend` slots. An in-process engine is trusted like the host: dependency injection is a design boundary, not a permission boundary.
- Enforced by: existing gate `subprocess_outside_declared_adapters`; designed `untrusted_code_is_never_placed_in_the_restricted_local_backend`; designed `harness_process_refuses_without_an_available_confinement_engine`.
- Today: partly. The gate limits process starts to the modules in `subprocess_allowed_modules`; the designed checks are not built (source).

#### LE-ISOLATE-004

A slot that allows fallback between engines of different isolation MUST first
define isolation as named axes (file view, network egress, process
visibility, memory safety, kernel attack surface, credential exposure) and
fall back only to an engine at least as strong on every axis the step needs.

- Maps to: `ISOLATIONS` in `core/harness_execution_contracts.py`; `engine_kind_groups: weaker_isolation`.
- Enforced by: existing `core.engines.slot_checks:a_slot_with_weaker_isolation_engines_never_falls_back_automatically`.
- Today: holds, because such slots allow no fallback at all (source [lifecycle verifiers]). One isolation value, `os_sandbox`, covers three engine kinds.

#### LE-ISOLATE-005

A stop MUST be confirmed by an observation (an empty control group, an absent
container, the exit of the sandboxed process itself, or a remote
confirmation), never by the sending of a signal or the exit of a launcher.

- Maps to: `stop_confirmation` in `engine_instance/v1`; `SignalController` and `ProcessTreeController`; the wait in `core/harness_process.py`.
- Enforced by: new `a_stop_is_confirmed_by_observation_never_by_the_signal` (known-wrong: a stop recorded as confirmed after SIGTERM alone, or after the wait for Bubblewrap alone).
- Today: fails for the harness path. The code waits for Bubblewrap only; in 11 of 30 trials the sandboxed process was still listed as running or sleeping right after that wait returned, and none was left 200 milliseconds later (ran [lifecycle verifier, September 24]). The Docker adapter confirms by inspection (source).

#### LE-ISOLATE-006

A limit that the step's budget requires to be preemptive MUST be enforced by
the confinement engine, and an engine that cannot enforce it is ineligible.

- Maps to: `LIMITS` in `core/harness_execution_contracts.py`, which gains memory, process count and writable disk under the names and units that `DockerResourceLimits` already passes to `docker run` (`memory`, `pids`, `temporary_bytes`, beside `cpus`); eligibility screen 9; `core/runtime_capacity.py` stays the one place a limit number comes from.
- Enforced by: designed `missing_preemptive_limit_is_ineligible_under_a_preemptive_budget`.
- Today: partly. The Docker path already enforces memory, processors, process count and temporary disk (`execute_generated_project` sets 4g, 2.0, 256 and 1 GiB); the confined harness path has no such limits (source [lifecycle verifier, September 24]).

#### LE-ISOLATE-007

A WebAssembly engine kind MUST NOT be added without its qualification kit: a
digested grant list of linked imports and opened folders, a fuel or epoch
deadline, a memory limit, a parity test against another engine of the slot,
and network denied unless an address check allows it.

- Maps to: the `custom_plugins_port` slot; `ISOLATIONS` would gain `webassembly_capability` with the kit.
- Enforced by: new `a_webassembly_engine_whose_imports_exceed_the_grant_is_refused_before_instantiation` (known-wrong: a plugin linked with a network import that the step's grant does not hold).
- Today: not built. No WebAssembly engine exists; the edge map lists Extism as a later candidate (source).

#### LE-ISOLATE-008

A tool server process MUST start inside the confinement that its trust
requires.

- Maps to: `McpSdkTransport` in `core/mcp_sdk_transport.py`; the `tool_protocol_transport` slot and the planned `tool_protocol_gateway` slot.
- Enforced by: new `a_tool_server_process_starts_confined` (known-wrong: a standard-stream tool server started as a plain host process).
- Today: fails. The transport starts a new standard-stream server process for every `list_tools` and every `call_tool`, with the server's credential values in its environment and no confinement (source [lifecycle verifier, September 23]; the launch code is unchanged at `e6346075`, source, writer).

### 11. Outside projects: an engine adapter pinned by revision and licence, and a Baltor-native engine track

The owner's rule: every project taken from GitHub is wrapped as a functional
component, and our own variation is built beside it. In this repository that
means one procedure for every outside project:

1. Name the function and find its slot. Add a slot only when none fits
   (LE-SLOT-001).
2. Search existing projects, standards and papers, and record the decision
   (LE-OUTSIDE-006).
3. Pin the project: repository, exact commit or released version, SPDX
   licence and artifact digest (LE-OUTSIDE-002).
4. Write the engine adapter. No outside type crosses the edge (LE-EDGE-007),
   and its decode and encode are declared conversions (LE-SUPPORT-008).
5. Choose the lightest execution its trust allows (LE-ISOLATE-002): a vetted
   pure library in process; an executable tool as a supervised subprocess in
   a disposable staging folder with no network and no secrets; untrusted or
   networked code in a container.
6. Run the slot's conformance kit. The engine enters as a candidate and is
   qualified by an independent reviewer (LE-TEST-001, LE-STATUS-003).
7. Build or confirm the Baltor-native engine when the slot's track requires
   one, and run the same kit (LE-OUTSIDE-003).
8. Compare both under the same contract with the declared evidence rule. Keep
   the other installed as a fallback or a candidate, and record maintenance
   cost, the upstream changes watched, rollback and retirement.

#### LE-OUTSIDE-001

A project taken from outside MUST be imported or started only by the engine
adapter of the slot it serves.

- Maps to: the engine adapter module; roadmap S-6.75, adversarial line "an outside project called directly from a component".
- Enforced by: new `outside_packages_are_imported_only_by_engine_modules` (known-wrong: a neighbour module that imports `datasketch` or `fastmcp` directly).
- Today: not built (source).

#### LE-OUTSIDE-002

An engine adapter's descriptor MUST name every outside project it wraps with
its exact revision (a commit, or a released version with its artifact
digest, never a branch name), its SPDX licence expression, its artifact
digest and its role (library, executable, service or protocol kit).

- Maps to: `engine_descriptor/v2` replaces the free-text `source` with an `upstreams` list and adds `engine_origin`.
- Enforced by: new `every_engine_adapter_names_its_upstream_revision_licence_and_digest` (known-wrong: a revision that is a branch name).
- Today: partly. The `engine_descriptor/v1` reader already refuses an empty licence, upstream or revision; it does not test that the revision is pinned, that the licence is an SPDX expression, or that an artifact digest and a role are named, and it cannot say whether an engine is ours or an adapter (source [rule and names verifier, September 24]). Library ingestion writes the upstream, licence and pinned commit of its outside engines only in module docstrings (source). The `model2vec` vector stage loads `minishlab/potion-base-8M` through `StaticModel.from_pretrained` with no revision and records the revision of its embedding space as the literal `hf-cache-pin`, so the weights are whatever the hub serves when the cache is empty (source, writer).

#### LE-OUTSIDE-003

Every slot MUST declare its Baltor-native engine track as required, optional
or not_applicable with a reason, and a required track names a Baltor-native
engine that passes the slot's kit or the roadmap step that builds one.

- Maps to: `own_engine_track` in `engine_slot/v2`; `engine_origin` (`own_code`, `own_fork`, `outside_project`) in `engine_descriptor/v2`. Not applicable fits hosted providers such as payment, identity, domain records and compute.
- Enforced by: new `a_required_native_engine_track_has_an_engine_or_a_roadmap_step` (known-wrong: a slot holding only an engine adapter, with a required track and no roadmap step).
- Today: not built in the catalogue. Library ingestion already pairs four outside engines with engines written here; for example `library_near_duplicate` declares `datasketch_minhash_lsh` first and `builtin_minhash_lsh` second (ran, writer).

#### LE-OUTSIDE-004

A Baltor-native engine MUST be qualified on its own and never inherits the
qualification, evidence or approval of the outside engine it replaces or
forks.

- Maps to: `engine_qualification/v1` bound to the installation digest.
- Enforced by: existing `core.engines.records_checks:qualification_binds_the_installation_digest`; new `a_native_engine_never_inherits_an_outside_engine_qualification` (known-wrong: a fork counted as qualified through its upstream's record).
- Today: partly, through the digest binding.

#### LE-OUTSIDE-005

Switching between an engine adapter and a Baltor-native engine MUST be a host
configuration change with no call-site change.

- Maps to: `initial` and `fallbacks` in `engine_selection_policy/v1`; roadmap verification cases D-19-T01 to T03.
- Enforced by: designed `adding_an_engine_by_registration_changes_no_call_site`; new `a_host_setting_switches_engines_without_editing_a_caller` (known-wrong: a switch that needs an edit to a call site).
- Today: designed.

#### LE-OUTSIDE-006

Before a new slot, engine kind or engine is built, a dated research record
MUST name the projects, standards and papers searched, with versions and
dates and the decision for each (adopt, adapt or reject), and the slot record
points to it.

- Maps to: `prior_art_records` in `engine_slot/v2`; rule 6 of the commit, push and release authority.
- Enforced by: new `every_slot_names_a_prior_art_record_that_exists` (known-wrong: an empty list, or a path that does not exist).
- Today: partly. Research records exist; no slot points to them (source).

#### LE-OUTSIDE-007

An outside project MUST reach a customer's files only through this
repository's confined writer, which keeps exact bytes and the executable bit.

- Maps to: `write_confined_file` in `tools/install_selected_material.py`, to move into the package; `catalogue_package/v2` gains a per-file `executable` flag (0o755 or 0o644, no other mode bits).
- Enforced by: new `outside_projects_write_customer_files_only_through_the_confined_writer` (known-wrong: an outside project's own apply path writing into a customer folder); new `the_confined_writer_keeps_bytes_and_the_executable_bit` (known-wrong: a shell script that loses its executable bit; a binary asset re-encoded as text).
- Today: fails for the executable bit. The confined writer keeps bytes and creates every file with mode 0o644 (ran [component standard review's writer trial]); the pinned agent-harness audit found binary conversion and unsafe ownership in its own paths (claim [committed research]).

#### LE-OUTSIDE-008

Each retained engine adapter SHOULD record its maintenance cost, the upstream
changes watched, its rollback and its retirement condition.

- Set aside when: the engine is used only in a dated trial.
- Maps to: the engine card; `engine_retirement/v1`; the watch list `tools/research_source_watch.json` (`research_source_watch_manifest/v1`) and its daily workflow `research-watch.yml`.
- Enforced by: review by the integration reviewer.
- Today: partly. Since `e6346075` the research watch checks its 17 sources every day and opens or updates one issue when a source changed. The list holds harness projects, specifications and registries, not the outside projects behind today's engine adapters (datasketch, SkillSpector, the skills-ref validator, model2vec and its weights), and its Model Context Protocol entry names the fixed 2025-11-25 page, not the 2026-07-28 revision that the service also serves (source, writer).

### 12. Names

#### LE-NAME-001

Every term that this standard defines MUST have exactly one vocabulary entry
in `terminology.yaml`, identical in its installed copy, and no name is
defined in both the `terms` and the `vocabulary` sections.

- Maps to: `vocabulary` and `terms` in `terminology.yaml` and `src/loop_engine/data/terminology.yaml`.
- Enforced by: existing `architecture_contract:installed_contract_projections_are_fresh` (the two copies stay identical); new `every_term_the_standard_defines_has_one_entry` (known-wrong: a term of this standard's term table with no vocabulary entry); new `one_name_is_defined_in_one_terminology_section` (known-wrong: a name in both sections with different definitions, which `resolved_terms()` resolves silently in favour of the vocabulary entry).
- Today: partly. The gate `undefined_terms_retired_names_and_misplaced_words` checks definitions, placement and retired names; it does not find a term used without an entry, and in documents it refuses only retired names (source [rule and names verifier, September 24]). The uncommitted terminology hunks in the shared checkout define compiler names in `vocabulary` that `main` defines in `terms`, and its two copies differ (source [same verifier]).

#### LE-NAME-002

A word with a second meaning MUST be written with its qualifier: instance,
session, lease, mode, slot, wrapper, binding, boundary, profile, native,
condition and generation never stand alone for an engine concept.

- Maps to: the terms in the section "Terms and ambiguity entries" below; the ambiguity register.
- Enforced by: new `an_unqualified_reserved_word_in_new_technical_prose_is_refused` (known-wrong: "the session" for an engine session in a new technical document), a ratchet whose baseline only shrinks.
- Today: not built.

#### LE-NAME-003

Every name from outside research that this repository does not use MUST be
registered in `terminology.yaml`: a prose name as a retired vocabulary entry
with its replacement, and a class name in `forbidden_class_names`.

- Maps to: `vocabulary` entries with status retired; `forbidden_class_names` in `terminology.yaml`.
- Enforced by: existing gate `undefined_terms_retired_names_and_misplaced_words`; existing `architecture_contract:live_tree_passes_architecture_contract`, which runs `forbidden_class_violations` over every class in the package.
- Today: not built. The outside names are not registered; a prose pattern does not catch a snake_case identifier in a document, and classes are refused only through `forbidden_class_names` (source [rule and names verifier, September 24]).

#### LE-NAME-004

Each collision between two meanings of one word MUST have one entry in the
[semantic ambiguity register](SEMANTIC-AMBIGUITY-REGISTER.yaml), rendered in
`AMBIGUITY-REGISTER.md` without any difference from its source.

- Maps to: `SEMANTIC-AMBIGUITY-REGISTER.yaml` and `AMBIGUITY-REGISTER.md`.
- Enforced by: new `the_rendered_ambiguity_register_matches_its_source` (known-wrong: today's rendered register, which lacks SEM-025).
- Today: fails. The rendered register lists SEM-001 to SEM-024, the source holds 25 entries, and no code reads either file (ran and source [rule and names line and both verifiers]).

#### LE-NAME-005

One public class name MUST name one class across the package.

- Maps to: the class scanner `_class_names_in_package` of `architecture_contract.py`, which keeps one path per name today.
- Enforced by: new `one_class_name_names_one_class` (known-wrong: the two `EngineSlot` classes), a ratchet with a baseline of 10 names that only shrinks.
- Today: fails for 10 names, among them `EngineSlot`, `ModelInvocationRequest` and `PromotionRefused` (four modules) (ran [rule and names line]; confirmed by both verifiers).

#### LE-NAME-006

The index of functional components, slots and engines MUST be generated from
the slot catalogue, the interaction rows, the folder map, the boundary
registry, the factory tables, the descriptors, the checks and
`terminology.yaml`, and a stale index fails.

- Maps to: the planned pages under `docs/components/engines/` and `engines.json`; roadmap verification case D-27-T01.
- Enforced by: designed `generated_engine_pages_are_current`.
- Today: designed.

#### LE-NAME-007

Internal code identifiers SHOULD be declarative and spelled in full, with
record types in the form `name/vN` and without the brand Baltor.

- Set aside when: an outside protocol fixes the identifier (it then stays inside its engine adapter), or the identifier is customer configuration such as `BALTOR_SERVICE_TOKEN`.
- Maps to: record types and fields of the engine records; the `Baltor` vocabulary entry.
- Enforced by: review by an independent reviewer.

#### LE-NAME-008

Roadmap text MUST use the registered term for every concept that this
standard names.

- Maps to: `docs/roadmap/roadmap.yaml`, which the vocabulary gate does not scan because it reads Markdown only, and the pages generated from it.
- Enforced by: new `roadmap_text_uses_registered_terms` (known-wrong: S-6.75's "wrapper engine").
- Today: fails. S-6.74 says "three modes", S-6.75 says "wrapper engine", S-6.80, D-29 and the weekly job `weekly_harness_profile_refresh` say "Harness File Profile", S-6.72, S-6.75, S-6.86, S-6.87 and D-27 say "contract test kit", and D-27-T02 says "contract kit" (source, writer, on `e6346075`). Roadmap step S-6.73 owns these edits.

### 13. Writing and changing this standard

#### LE-RULE-001

Every statement MUST have a stable identifier, exactly one key word, one
requirement, the field or record it constrains, its enforcement and its state
today.

- Maps to: this document.
- Enforced by: new `every_standard_statement_names_its_enforcement` (known-wrong: a statement with two key words; an existing check that is not a collected check name; a designed check that section 17 of the design and the slots' `planned_checks` do not name; a review line that names no role; an enforcement line that names nothing; a key word outside a statement). It resolves every existing check name against the names that the collected self-tests return, every gate against the conformance report's keys and every designed name against section 17 and `planned_checks`.
- Today: a hardened prototype of this check ran on this draft and refused each planted defect, including the five evasions that passed the first prototype (ran, writer).

#### LE-RULE-002

Every recommendation MUST say when it may be set aside.

- Maps to: this document.
- Enforced by: new `every_should_statement_says_when_it_may_be_set_aside` (known-wrong: a recommendation without a "Set aside when" line).
- Today: the prototype checks it (ran, writer).

#### LE-RULE-003

An exception to a statement MUST be local, name the statement and its
reason, and stay in a baseline that only shrinks.

- Maps to: `known_direct_construction_sites` in `engine_slot/v1`; `quotation_exceptions` and `quotation_reason` in `terminology.yaml`.
- Enforced by: existing `core.engines.slot_checks:existing_slot_checks_and_construction_sites_resolve`; review of each exception by the integration reviewer.
- Today: partly. The two baselines exist.

#### LE-RULE-004

A requirement MUST appear once: other documents link its statement, and
reasons stay in the design or the research records.

- Maps to: this document and the documents that link it.
- Enforced by: review by an independent reviewer.
- Today: holds for rule 6, which links here and repeats no statement.

#### LE-RULE-005

A change to this standard MUST be recorded in its changelog with its date,
and a withdrawn statement keeps its identifier, marked withdrawn.

- Maps to: the changelog below.
- Enforced by: review by the integration reviewer.
- Today: the changelog starts with the first draft.

## Terms and ambiguity entries

### Terms this standard uses

Existing terms keep their entries: engine slot, engine (of an engine slot),
engine kind, engine descriptor, engine installation, executor profile, engine
preference, nested slot. The engine entry changes one phrase: its
"Qualification rule" becomes a "Naming rule", because qualification is the
evidence record. New terms, with their proposed entries in the terminology
proposal beside this standard:

| Term | Meaning in one line | Replaces or is not |
|---|---|---|
| functional component | A part with one job and one owner, reached only through its edge contract | not `LoopComponentDefinition`; the owner's "functional unit" and "functionality component" |
| edge contract | The versioned request and result records of a functional component, with its interaction rows | "versioned component contract", "typed functional boundary" |
| graph edge | A typed connection between two Loop ports (`LoopGraphEdge`) | not an edge contract |
| envelope Loop | The boundary Loop that holds an edge constant while engines change | not a wrapper layer |
| engine protocol | The versioned method surface a slot calls on its engines | not a network protocol |
| engine adapter | An engine that translates to an outside project pinned by revision and licence | "wrapper engine", "external adapter" |
| Baltor-native engine | An engine written here, or a fork kept here; its track is declared per slot | code: `own_code`, `own_fork` |
| wrapper layer | One ordered layer inside one installation, with declared control ownership | not an engine adapter or a container |
| composite engine | An engine whose work passes through nested slots it declares | not a Solution composition |
| engine composition | The declared positions of a composite engine; resolved, the exact engines chosen | "logical plan", "physical plan" |
| engine instance | One started copy of an installation, with an owned handle and a fencing token | "instance" alone |
| harness instance | The engine instance of a step executor engine | "instance" alone |
| fencing token | A number that rises whenever ownership of a work item, an instance or durable state changes; an older holder is refused | "generation" as a counter |
| engine lease | One attempt's expiring hold on a shared engine instance; grants nothing | "lease" alone |
| engine session | State one instance keeps across calls inside one attempt | "session" alone |
| native session | A harness's own conversation state | "harness session" in older text |
| engine attempt | One dispatch of one invocation to one installation | not a physical call |
| execution specification | Everything that fixes what one engine attempt runs, named by one digest | "prepared plan" |
| state binding | Owner, category, format version, owner fencing token and lifetime of durable state | "StateRef" |
| call pattern | How calls reach an instance | part of the retired "lifecycle profile" |
| instance lifetime | How long an instance lives | part of the retired "lifecycle profile" |
| instance owner | Who starts and stops an instance | not who may use it |
| engine swap | A planned change of the engine that serves one slot scope, under the slot's swap rule | "transition"; not a fallback transition |
| swap qualification | The independent record that one engine swap preserves state and work in flight | "transition qualification" |
| selection mode | one_of, set_of, derived, all_of | not a run mode |
| selection basis | pinned, preferred, automatic, recorded on each decision | "preference mode", "PIN, PREFER, AUTO modes" |
| engine qualification | The independent record for one installation, scope and proof level | not availability |
| conformance kit | One shared test kit per slot that every engine passes alone | "contract test kit", "contract kit" |
| composition test | A test of joined or nested slots over their typed edges | |
| journey test | A test of one customer path end to end | |
| lifecycle drill | Faults, kills, timeouts and restarts injected at named points | |
| engine availability snapshot | Expiring alive, ready and capacity facts of one instance at one fencing token | "engine condition", "activation" |
| binding facts | Desired, prepared, routable, observed and rejected configuration of one slot | "activation controller" |
| owned resource record | One record for a resource an attempt or instance must release, from intent to confirmed release | "resource claim" (a Kubernetes object); not compensation |
| advisory field | A request field an engine may ignore, with the ignoring recorded | "optimization hint" |
| work split | How much of an advisory optimization an engine performs | not a compatibility verdict |
| validation profile | How one validator run decides a schema: dialect, formats, references, unknown fields, numbers, time, match mode, implementation | not the schema itself |
| conversion declaration | Source and target contracts, information class, permitted losses, ownership, effects and cost of one conversion | not an Adapter Loop by itself |
| stream semantics | Framing, terminal signal, errors, limits, ordering, acknowledgment, replay and partial results of one stream edge | |
| execution fields | Invocation mechanism, application protocol with its revision, executable format, isolation and locality | "execution binding", "binding specification" |
| harness compatibility profile | Passive data describing one exact harness release and what it loads | "Harness File Profile", "target profile", "harness layout profile" |

Retired outside names: engine definition, engine configuration, logical plan
and physical plan, lifecycle profile, preference mode, wrapper engine,
transition qualification and activation controller. "Execution boundary",
"capability contract", "state reference", "execution binding" and "circuit
breaker" are not retired, because each already has a meaning in current
documents, among them owner requirement documents and the design. "Harness
File Profile" and "contract test kit" are mapped, not yet retired, because the
roadmap still carries them; LE-NAME-008 and roadmap step S-6.73 change the
roadmap first. The owner's "harness component files" keeps the owner's
meaning; in engineering terms a file is a Harness Working Directory File, and
a count of "harness component files" toward 10,000 or 100,000 counts Harness
Working Directory Packages, as roadmap S-6.69 counts them.

### Proposed ambiguity register entries

The existing entries SEM-005, SEM-012 and SEM-016 (lifecycle) and SEM-017
(provider capability hints and binding) gain the new cases instead of new
duplicates. New entries:

| Entry | Word | Collision | Resolution |
|---|---|---|---|
| SEM-026 | component | functional component; `LoopComponentDefinition`; component guide folders; the semantic category `component` (a passive building block) | write "functional component" in full |
| SEM-027 | edge | interaction rows; `LoopGraphEdge`; the `edge_proxy` slot; `release_edge` | "edge contract" and "graph edge"; identifiers unchanged |
| SEM-028 | wrapper | wrapper layers; the owner's verb "wrap"; compatibility wrappers | "wrapper layer"; wrapping an outside project means writing its engine adapter; a container is isolation |
| SEM-029 | binding | `SlotBinding`, bound engine, `BINDING_KINDS`, port and storage bindings; "execution binding" for a searched proposal bound to execution, for the way an invocation reaches its implementation, and in `skill_execution_binding/v1`; `TaskLoopBinding`; the prompt document's "Binding spec" | no general binding type; execution fields; binding facts of the bindings report; state binding |
| SEM-030 | instance | engine instance, harness instance, "an instance of the Loop runtime", `instance_id` of credential leases | always say instance of what |
| SEM-031 | session | native session, engine session, `service_session/v1`, checkout and billing sessions, `administrator_session`, the protocol session that revision 2026-07-28 removed | never bare for engines |
| SEM-032 | lease | work lease, credential lease, engine lease, the billing effect leases, provider machine leases | never bare; one set of lease rules (section 3) |
| SEM-033 | mode | run mode, selection mode, evaluation mode, executor modes, match modes | bare "mode" is the run mode; the selection basis is not a mode |
| SEM-034 | qualification | engine qualification against the grammar sense ("Qualification rule", `qualified_terms`) | the grammar sense becomes "naming rule" |
| SEM-035 | profile | five names for the harness compatibility profile (`native_client_layout_profile`, `harness_file_profile`, "Harness File Profile", "target profile", "harness layout profile"); role, step and executor profiles; "lifecycle profile" | one name bound to the `native_client_layout_profile` record family; three instance fields |
| SEM-036 | plan | price plan, `PlanDefinition`, the kernel `ExecutionPlan`, route plans, the retired `resolved_loop_node_plan`, placement plan, `ModelCallStrategy.plan`, outside logical and physical plans | engine composition and resolved engine composition; the placement plan keeps its compiler meaning |
| SEM-037 | `EngineSlot` | defined in `core/engines/slots.py` and `core/library_ingestion/selection.py`, with `library_engine_selection/v1` | library ingestion adopts the shared records |
| SEM-038 | contract | edge contract; component contract; capability contracts; the category contract | "edge contract" for a functional component's interface |
| SEM-039 | boundary | boundary registry row; "execution boundary" prose; "typed functional boundary" | bare "boundary" is the registry row |
| SEM-040 | activation | `ActivationRecord` against the outside "activation controller" | engine readiness is an availability snapshot; configuration change is recorded as binding facts |
| SEM-041 | native | native declaration, native registry, native session, native control, native protocol harness, native client layout; and "our own" | "Baltor-native engine" in full for our own engines |
| SEM-042 | `set_of` | one member per invocation in the catalogue; every member in library ingestion | set_of is dispatch; all_of runs every member |
| SEM-043 | hint | `repair_hint`, `query_hint`, `root_hint`, `active_step_hint`, protocol tool annotations, `CacheHint`, `order_hint`, the provider capability hints of SEM-017; the outside "optimization hint" | "advisory field" for an edge request |
| SEM-044 | orphan | `orphaned_spawned_loops` against processes and containers left by a stopped attempt | an unreleased owned resource record for processes and containers |
| SEM-045 | circuit | the typed decision engine `circuit`; "circuit breaker" as a failure-rate state machine (resilience4j, Polly) or as concurrency limits (Envoy); the design's own phrase "an open circuit breaker is simply an expiring availability fact" | an expiring route availability snapshot with a reason, and a concurrency limit |
| SEM-046 | condition | Loop condition, exit condition, verification condition, and the retired word that exit condition replaced; Kubernetes conditions | engine readiness facts live in the availability snapshot, never as "conditions" |
| SEM-047 | generation | seeded generation, candidate generation; Kubernetes `generation` and `observedGeneration` | fencing token for ownership, sequence number for desired configuration |
| SEM-048 | claim | `claim()` of the work lease scheduler; the evidence label "claim"; the Kubernetes `ResourceClaim` for devices | owned resource record for resources to release |
| SEM-049 | transition | `FallbackTransition` (failure-driven); the outside "transition" and "transition qualification" (planned change) | engine swap and swap qualification |

## Adoption order

Each step lands on `main` with its checks, each check with the removed-guard
control of the working cycle, and each step's work is finished only when it
is live and wired up. Steps 1 and 2 can run in parallel; step 3 waits for the
catalogue rows of step 2, because rule 6 says every functional component has a
slot.

1. **Repair the live defects that break a stated invariant** (S-2.24, S-2.26,
   S-6.43, S-6.44, S-6.78, D-20, D-30). The gateway stops after an
   inconclusive verdict even with the permission on (LE-COMPOSE-015);
   protocol requests are classified by their body first (LE-EDGE-009); stream
   errors never end as complete answers, and model calls end by a whole-call
   deadline (LE-LIFETIME-005, LE-INSTANCE-020); pure engines and schema
   validation make no network request (LE-ENGINE-011); a retry by identity
   across a catalogue swap returns the first bytes, and a definite conflict
   gets its own code (LE-INSTANCE-021, LE-INSTANCE-022); a restart serves the
   last prepared release, and a release prepares grants and billing before it
   serves (LE-STATUS-007, LE-STATUS-009); the Docker cleanup block becomes an
   owned resource record (LE-INSTANCE-009); exact matching separates types
   (LE-SUPPORT-007); the installer accounts for leftover partial files and
   types read-back faults per item (LE-TEST-007). Hibernation records only
   what it performed and stops using SIGUSR1 before it gets a live caller
   (LE-STATUS-005, LE-LIFETIME-006). Done when: each named check exists with
   its removed-guard control and passes, and the known-wrong case of each
   fails without the repair.
2. **Make the index honest** (S-6.30, S-6.73). Catalogue the four library
   ingestion slots and correct `library_ingestion_source`; add the factory
   table join (LE-SLOT-001), the repository-level identifier test
   (LE-ENGINE-002), the content check of construction sites (LE-SLOT-004), the
   one-class-name ratchet (LE-NAME-005), the interaction row join
   (LE-EDGE-008) and the rendered register check (LE-NAME-004). Correct the
   `protocol_endpoint` row and the design's stale protocol text. Done when:
   the index fails on each planted drift.
3. **Land the words and the rule** (S-6.84, S-6.73). Apply the rule 6 diff to
   the current `AGENTS.md` (never a whole-file copy, which would undo later
   edits), add this standard, the terminology entries in both copies, the
   ambiguity register entries, the route check extension, the hardened
   statement check and the roadmap wording check, in one commit, because the
   route check's link test and the lychee step refuse a link to a missing
   file. Settle the harness data name in the same change; the conflicting
   uncommitted terminology hunks in the shared checkout were written by an
   OpenCode session, so they are saved as a patch before anything folds them
   (nomenclature review, conflict C14). Done when: the route check passes 21
   of 21, the vocabulary gate reports 0 violations, and the statement check
   reports nothing on this standard while refusing its planted defects.
4. **Close the record gaps, then version the records once** (S-6.30). First
   the validation that needs no new field: policy against slot
   (LE-SELECT-002), declared order (LE-SELECT-009), propensity
   (LE-SELECT-013), sender precedence (LE-SELECT-016), objectives
   (LE-SELECT-017), a pinned decision's explicit no fallback (LE-SELECT-022)
   and typed settings (LE-ENGINE-006). Then, in one commit,
   `engine_slot/v2`, `engine_descriptor/v2`, `engine_installation/v2`,
   `engine_selection_override/v2`, `engine_selection_policy/v2`,
   `engine_selection_decision/v2` (selection basis, predecessor, selection
   path, resolved composition), `engine_qualification/v2` (producer, kit
   reference, swaps, nested installations), `engine_bindings_report/v2`
   (binding facts) and `engine_retirement/v2` (withdrawn), with every reader,
   fixture and check, and the first field definitions of
   `engine_comparison_policy`; and `component_interaction_catalog/v2` (retry
   owner, budget scope, validation profiles, conversion declarations, stream
   semantics). Nothing calls the version 1 engine records yet, so this is
   the cheapest moment.
5. **Build the shared selector, pinned and preferred first** (S-6.30, S-6.74).
   `core/engines/selection.py` reuses `resolve_preference` and the rules of
   `select_harness`; the service host file accepts the `engines` block and
   writes the bindings report at start; the health record names its digest.
   Prove it on `library_near_duplicate`, which already pairs a Baltor-native
   engine with an engine adapter, pure and without network; then move hosted
   search to its measured policy (S-6.32), whose gap `SEARCH-QUALITY.md`
   already records as known limitation 3. If the compiler of S-6.44 lands
   earlier, it uses the shared records from its first commit with
   declared-order selection, so that no local selector appears.
6. **Give every slot its conformance kit** (S-6.72, S-6.76, D-27-T02). The
   shared kit runner and `conformance_kit_report/v1`, replacing
   `store_conformance/v1`; first kits where factory tables already work
   (`library_near_duplicate` and the candidate review pre-check kinds, reusing
   the calibration records), then `record_store` on all five engines with
   sparse and extra-key records, search, `step_executor` once
   `core.step_execution.engines` exists, and `material_install_layout` after
   its code moves into the package; expectation files for the installer and
   the Pi extension; a nightly tier that follows the schedule pattern of
   `live-pulse.yml` and `research-watch.yml` and runs on an exported tree; the
   release gate (LE-TEST-009). Kit sections come only from closed fields or a
   reviewed label table (LE-TEST-015); kits run with the network blocked, so
   the retrieval canary uses weights pinned by revision and cached before the
   run (LE-TEST-013, LE-OUTSIDE-002); peer protocol checks name their profile
   and schema release (LE-SUPPORT-014).
7. **Instances, leases, availability snapshots and owned resource records**
   (S-2.22, S-2.24, S-2.26, S-2.36, S-6.8). `engine_instance/v1` with its
   fencing token, `engine_lease/v1`, `engine_availability_snapshot/v1` and
   `owned_resource/v1` with a reconciliation Loop at host start;
   `credential_lease/v2` and `held_credential/v2` (owner clock, maximum,
   withdraw operation); work lease expiry on the owner's clock with a
   maximum; shared model residency through `overnight_residency/v1` and the
   route availability snapshot (LE-INSTANCE-026); declared concurrency and
   queue bounds for shared instances (LE-INSTANCE-027); a route that failures
   set aside written as an expiring route availability snapshot with a
   counted probe (LE-STATUS-012); stops confirmed by observation and graceful
   stops that reach the sandboxed process; preemptive limits under the
   `DockerResourceLimits` names; confined tool servers.
8. **Outside projects in pairs** (S-6.75, S-6.44, D-28). A new one_of slot for
   the Harness Working Directory Compiler with the Baltor-native compiler and
   an agent-harness engine adapter behind the confined writer, which keeps
   bytes and the executable bit (`catalogue_package/v2`); then FastMCP behind
   `tool_protocol_transport`, Harbor behind `response_evaluator` and DBOS
   behind the proposed `step_attempt_durability` slot. The new task
   decomposition and step expansion slots of S-6.86 and S-6.87 follow this
   standard from their first commit.
9. **Composition, sequential forms first** (S-6.60). The pass-through engine
   of `model_call_strategy`, the all_of mode for the library ingestion format
   and safety slots, composite qualification with nested installations;
   concurrent forms only when the Loop runtime has a live concurrency owner.
10. **Automatic selection** (S-6.74, S-6.32, S-6.41). Evidence records and the
    comparison policy with noise measurement; automatic only at or above the
    floors; ramps later; bandits closed until the one-million-run rule.
11. **The generated index** (D-27-T01). Generated engine pages and
    `engines.json`, `loop-engine engines list` and `explain`, and a check
    that fails on a stale index.

## What this standard does not add

- A universal engine registry, an engine store, an event family or a
  scheduler.
- A new runtime type, a graph vertex other than `Loop`, or a class whose name
  ends in `Node`.
- A "mode" for pinned, preferred and automatic selection.
- A general binding record, a separate plan record, an activation controller
  class or an artifact bundle store.
- A feature flag service, a network read or a model call inside selection.
- An outside default that substitutes silently: fallback on any error, 100
  percent mirroring when no rate is set, a default answer after an error,
  silent fallback of unsupported parts, a swallowed plugin exception, a
  schema reference fetched from the network, or a deploy that routes
  customers before its dependencies are prepared.

## Decisions taken, with reasons

| Decision | Reason |
|---|---|
| One standard file that rule 6 links; no second section in `AGENTS.md` | Roadmap S-6.34 asks for one home for rules, and `AGENTS.md` stays short |
| BCP 14 key words for this standard's statements, exactly one key word per statement | RFC 8174 makes capitals unambiguous; the adversarial checks found mixed levels in the earlier drafts |
| Repair live defects before the words land | The gateway, protocol, stream, deadline, network, retry and restart defects break invariants on live paths today; the records that most other statements constrain have no caller yet |
| Catalogue the four library ingestion slots before rule 6 lands | A rule that current code breaks on the day it lands teaches readers to ignore it |
| "Selection basis" for pinned, preferred and automatic | "Mode" already names the run mode and the slot's selection mode; the committed research says PIN, PREFER and AUTO are not three new Loop modes. S-6.74's "three modes" should read "three selection bases" |
| A fourth selection mode, all_of, beside composite engines | Library ingestion already runs every member and merges findings; the catalogue must describe that faithfully. A composite engine is used when the combination rule itself is a swappable, qualified choice |
| The engine composition is the composite's capability record, and the resolved composition is a field of the version 2 decision | The descriptor already has a capability record slot and the decision already links parents; `loop_graph_definition/v2` and the planned `ModelCallStrategy` protocol already hold compositions, so a separate plan record would be one more source of truth |
| Concurrent composite forms wait for a live concurrency owner, and loser cancellation belongs where harness attempts run | The parked `first_success` join is not a race, thread branches cannot be cancelled, and `PARKED.md` makes the return of the parallel runner an owner decision |
| "Engine adapter" for outside projects, "wrapper layer" for layers inside an installation | Roadmap S-6.84 asks for exactly this, so outside projects are not confused with layered harness wrappers |
| "Baltor-native engine" in prose; `own_code` and `own_fork` in code | The roadmap uses "Baltor-native"; the brand does not name contract fields, and bare "native" already means native declarations, registries, sessions and controls |
| "Harness compatibility profile" as the one name, bound to `native_client_layout_profile` | It is the name in the committed compiler design and extends an existing record family; S-6.73 changes the roadmap's "Harness File Profile" |
| "Conformance kit" as the one name; "contract test kit" kept as the roadmap's alias until the roadmap wording changes | Retiring the alias now would flag roadmap text before S-6.73 edits it |
| Three instance fields and a swap rule instead of "lifecycle profile" | "Lifecycle" and "profile" each already have meanings; the split separates how calls arrive, how long an instance lives, who owns it and when it may change |
| "Engine availability snapshot", "owned resource record", "fencing token" and "sequence number" instead of "engine condition", "resource claim" and "generation" | "Condition" is a Loop term, "resource claim" a Kubernetes object and "generation" names content generation; the new names reuse the route availability snapshot, the drill's owned resources, the work lease's fencing token and the catalogue pointer's sequence |
| "Engine swap" and "swap qualification" instead of "transition" | Keeps the failure-driven `FallbackTransition` apart from a planned change; "swap" is the owner's word |
| Binding facts in the bindings report instead of an activation controller | "Activation" is `ActivationRecord`; the refresher, the host loader and the envelope already own these moments, and a controller class would be a second owner |
| Expiry final at use, judged by the owner's clock, with a maximum, for every lease; a revoked credential issues nothing until held again | A lease renewed after expiry, or judged by the holder's clock, can resurrect access for a holder presumed dead; the live billing leases already use the service's clock. Kubernetes client-go lets a leader renew its own expired lease, so this is a recorded choice |
| A failed preparation keeps the previous configuration serving, across restarts | A single machine on one volume has no second machine to fall back to; Triton's similar behavior exists only in a mode it does not recommend, so this is a recorded choice, not a lesson borrowed from Triton |
| Execution fields instead of one binding value | HTTP is a transport, the Model Context Protocol an application protocol, a subprocess a process relationship and WebAssembly an executable format; the committed research reached the same finding |
| Availability snapshots built on `ConfigurationFact` and the route snapshot | The descriptor's availability fact already expires to unknown, and model routes already have the snapshot; one fact type avoids a second status record |
| Shared model residency through `overnight_residency/v1` and the route availability snapshot, with holders as engine leases | Both records exist and have readers (the overnight runner and the route selector); a separate residency record would be a second source of truth for the same fact |
| A route that failures set aside is an expiring route availability snapshot with a reason, and its probe is a counted model call | The design already treats "an open circuit breaker" as an expiring availability fact; a probe spends real model-call authority, so it is recorded like any other call |
| Peer protocol checks name a schema-strict or reference-lenient profile and a schema tag | The Agent Client Protocol schema forbids no extra field and its reference crate substitutes defaults silently, so a bare "valid" would hide which of the two was checked |
| Typed settings records, with a key-name screen only as a backstop | Permissions come from typed fields, never names; `ADAPTER_FACTORIES` already pairs a settings record with each kind |
| New record versions for the engine records, all at once | Readers refuse unknown keys, the pre-launch version policy forbids keeping old readers, and nothing calls the version 1 records yet |
| Validation profiles, conversion declarations and stream semantics defined once in the interaction catalogue | Every edge contract is already a row there; defining them anywhere else would add a parallel source of truth |
| No flag service, OpenFeature default, LiteLLM router or ONNX Runtime default inside selection | Each of them substitutes on error or on missing configuration, which the models and providers rules refuse |

## Changelog

- September 24, 2026 (on `e6346075`), third draft. Every probe of the second
  draft ran again on `e6346075` with the same results. Added LE-INSTANCE-026
  (shared model residency), LE-INSTANCE-027 (declared concurrency and queue
  bounds), LE-SUPPORT-014 (peer protocol profiles and schema releases),
  LE-STATUS-012 (a route that failures set aside, with a counted probe) and
  LE-TEST-015 (kit sections from closed fields), from verified findings that
  the second draft carried only in its adoption order or not at all.
  Corrected the existing check that LE-STATUS-004 names to the name the
  self-test returns. Added the research watch of `e6346075` (LE-TEST-009,
  LE-OUTSIDE-008), the unpinned weights of the model2vec stage and the network
  access of the retrieval self-test (LE-OUTSIDE-002, LE-TEST-013), the
  constant protocol server version (LE-ISOLATE-001), the unpinned JSON Schema
  validator (LE-SUPPORT-006), the remote identity part of a pin
  (LE-SELECT-007) and S-6.75 among the roadmap names (LE-NAME-008). Removed a
  retired word from SEM-046.
- September 24, 2026 (on `3d48a36c`), second draft. Corrections from the
  adversarial verifications of September 24: the live gateway's inconclusive
  route change (LE-COMPOSE-015); pins lost across the decision chain and the
  pinned no-fallback ambiguity (LE-SELECT-021, LE-SELECT-022); the noise
  control re-aimed at wasted allowance (LE-SELECT-018); draining stated as an
  exception to `engine_deprecated_as_initial` (LE-SELECT-019); quiesce by
  SIGUSR1, graceful stop and stop confirmation (LE-LIFETIME-006,
  LE-LIFETIME-007, LE-ISOLATE-005); lease clock and maximum (LE-INSTANCE-016,
  LE-INSTANCE-017); reuse of `ModelRouteAvailabilitySnapshot`,
  `overnight_residency/v1` and `DockerResourceLimits`; "condition",
  "generation" and "resource claim" replaced; the Triton claim corrected;
  enforcement lines that did not test their statements replaced (LE-SLOT-003,
  LE-NAME-001, LE-NAME-003); the scheduled `live-pulse.yml`, the Pi extension
  and the candidate review calibration added to the testing statements.
  Findings of the validation, conversion and streaming line, the selection,
  activation and transition line, the qualification tools line and the
  protocol revisions line added as LE-EDGE-009 to LE-EDGE-013,
  LE-ENGINE-011, LE-INSTANCE-019 to LE-INSTANCE-025, LE-SUPPORT-010 to
  LE-SUPPORT-013, LE-STATUS-006 to LE-STATUS-011, LE-TEST-011 to LE-TEST-014
  and LE-ISOLATE-008. Every statement now carries exactly one key word.
  Identifiers of the first draft keep their meaning, except LE-ENGINE-004
  (now the engine side of the retry owner, whose row side is LE-EDGE-012),
  LE-INSTANCE-008 (split into LE-INSTANCE-008 and LE-INSTANCE-018),
  LE-INSTANCE-014 (swap qualification) and LE-STATUS-006 (binding facts).
- September 24, 2026 (on `f6a7fb2c`), first draft, from the research lines of
  September 23 (repository grounding, testing, selection and composition,
  lifecycle and isolation, rule and names, protocol revisions), their
  verifiers, and the component standard review.

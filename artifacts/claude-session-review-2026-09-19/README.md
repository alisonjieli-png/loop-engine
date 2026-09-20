# Claude Code session recovery and review, September 19, 2026

Kind: local review report. This report records recovered decisions, present
implementation, reproduced defects, and proposed next work. It does not
change the architecture or authorize a deployment, provider call, or purchase.

The latest Claude Code session made substantial progress, but its component
inventory overstates how much of the proposed product works together. The
immediate priority is to complete and verify the connections between existing
components. Several of the newest components also need correctness and
confinement repairs before they are connected to remote callers.

The current source passes all 5,316 existing self-test checks. The independent
probes accompanying this review reproduce failures those checks do not cover.
Green checks establish the tested behaviors, not completion of the first
release.

## What was recovered

The detailed artifact the owner remembered exists:

- [Loop Engine System Map](https://claude.ai/code/artifact/a9e49f80-1fa5-4acc-af02-71e2dfa6786d).
  Its final published update in the transcript is the September 19, 04:53 UTC
  update for Spawned Loop provisioning. The local HTML, measurement JSON,
  component catalogue, and generator scripts survive in the Claude session's
  scratchpad. They were inspected locally; the hosted page was not separately
  fetched during this review.
- [The readable fabric roadmap](../../docs/roadmap/FABRIC-ROADMAP-2026-09-18.md)
  and [its machine-readable steps](../../docs/roadmap/roadmap.yaml).
- [The earlier session digest and research inventory](../../docs/context/AGENT-SESSION-DIGEST-AND-RESEARCH-INVENTORY-2026-09-18.md).
  This covers the preceding Codex, Claude Code, and OpenCode work. It predates
  most of the September 18 implementation and should not be used as its final
  status.
- [The hosting decision and subsequent corrections](../../docs/architecture/HOSTING-SHAPE-AND-THE-FIRST-RELEASE-2026-09-18.md),
  including uncommitted research added just before Claude reached its limit.
- [The measured folder migration proposal](../../docs/architecture/FOLDER-DEPTH-AND-THE-FLAT-CORE-2026-09-18.md),
  [storage decision](../../docs/architecture/INTELLIGENCE-STORAGE-AND-SERVING-2026-09-18.md),
  [dimension inventory](../../docs/architecture/DIMENSION-INVENTORY-2026-09-18.md),
  and [Astra advisory record](../../ASTRA.md).

The source transcript is session `4e77608c-3917-43b6-b2bb-898c778dc7da` in
the local Claude project history. The September 18 to 19 segment contains
13 ordinary text prompts and 38 queued text messages, including repeated
messages and large pasted research conversations. Queued messages contain
important later directions that an ordinary user-message-only extraction
would miss. Unrelated personal material was excluded from this report.
Private prompt bodies have not been copied into this artifact.

The last substantive owner request was at 05:16:18 UTC on September 19
(01:16:18 Eastern time). It asked for continued implementation and research,
an updated architecture artifact, and a plan to reach a working hosted first
release within 24 hours, including version control, environments, and
prepackaged intelligence generated from the classification grid.

Claude launched a six-track workflow at 05:20 UTC. Every track ended at the
weekly limit without a completed findings report:

| Interrupted track | Work still requiring completion |
|---|---|
| Model Context Protocol hosting and authorization | Transport, authorization, resource discovery, pagination, protocol security, and the product's own entitlements. |
| Release, versioning, and environments | Distribution and image releases, environment separation, deployment, rollback, and provenance. |
| Telemetry | Event conventions, privacy, collection, retention, and persistence. |
| Occupation and industry taxonomies | Primary sources, classifications, versions, and redistribution conditions. |
| Hosted first-release audit | The actual path from a remote client through authentication to a delivered skill. |
| Classification-grid audit | The actual path from an uncovered combination to candidate generation, qualification, packaging, and retrieval. |

The last substantive parent-session edit was around 05:21 UTC. Later limit
messages and background notifications do not establish further completed
work. There is no completed six-track launch plan to resume verbatim.

## Checkout and review scope

Observed checkout: `main` at
`48cc954322691e492aad69a465ba470a112730e7`, matching `origin/main` in the
initial status. The September 18 to 19 committed change window is 37 commits,
from `c4def81` through `48cc954`: 190 changed files, including 101 Python
source files, with 39,205 insertions and 449 deletions across the whole window.

Nine tracked files were already modified, and
`src/loop_engine/core/model_call_collection.py` was already untracked. Four
older untracked review artifacts also existed. The runtime and documentation
edits were preserved. No active Claude Code process appeared in the process
inventory. That is evidence of inactivity, not a transfer of ownership.

The unfinished batch contains the model-call collector, its solve-path
injection and checks, generated architecture-map changes, two new roadmap
entries, and extensive hosting corrections. Its saved exported-tree check
logs remain at
`/home/username/.loop-engine-tmp-20260914/batch35.cG12/`.
All 653 compared source/package files, including the new collector, match
that gate export byte for byte. The later hosting document differs from the
export and is not covered by that batch's documentation result.

This review reconstructed the requests and change inventory, inspected the
owning components for the active initiatives, checked current integration,
ran the full offline suite, and added independent reproductions for selected
high-risk boundaries. It is not an exhaustive security audit of all 190
changed files, a live harness qualification, or a new benchmark campaign.

## The latest product direction

The owner consistently wanted the full architecture preserved, with multiple
ways of running kept configurable. The first execution emphasis was a
separately initialized native harness for each atomic reasoning or building
assignment, supplied with the relevant instructions, capabilities, and files.
Custom harnesses and stronger engine control remain supported development
directions.

The launch discussion then distinguished the responsibilities Loop Engine
hosts from those a customer can run. At 03:35 UTC on September 19, the owner
explicitly reopened a first release that serves the intelligence layers and
harness components through the Model Context Protocol while the client starts
the harness instances. This qualifies the earlier full-platform launch
request; it does not remove telemetry, authentication, organized storage,
provisioning, or future hosted execution.

Claude's last hosting recommendation favored DigitalOcean App Platform for
that serving-oriented release, with Render as an alternative. An earlier
argument about creating a production database from one application
specification was corrected: that specification attaches an existing
production cluster. The document then argues that the first serving release
does not need a managed database. These are recovered recommendations, not a
freshly validated hosting selection. The transient catalogue, memory, and
metering implementations described below mean that durable tenant data and
telemetry still need an explicit deployment design, even when packaged
intelligence itself is immutable.

No customer endpoint, billing activation, cloud account selection, or
deployment approval was established by this review.

## Architecture and active initiatives

The current governing classification remains:

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

Harnesses, stores, guardrail records, and services remain resources or
mechanics used by classified Loops. The newer components do not introduce
another executable runtime.

| Initiative | What exists in the checkout | What remains open |
|---|---|---|
| Solutioning space and solutions space | Terminology and `SolutionsSpaceRecord` distinguish the work process from a plural collection of published solutions. | Public solving does not populate that new collection. Iterative publication with exact consumer output references remains proposed. |
| Model calls beyond language models | `ModelProfile`, `ModelCallRequest`, typed input parts, suggested outputs, response contracts, and tool model-placement checks exist. | Non-text calls are explicitly refused by the text conversion path. This is not installed vision, forecasting, or tabular-model execution. |
| Flexible contract matching | Exact, canonical, purpose, semantic with decisive fields, and judged matching have a typed boundary. | Applying the appropriate mode throughout solutioning comparisons remains incomplete. Strict solution-port compatibility must remain distinct. |
| Four persistent intelligence layers | The public solve dependencies now install the four-layer catalogue builder for reference-first search. | Retrieval, materialization, use, qualification, and benefit still need separate evidence. The saved population measurement is small and contains no packaged User Feedback records. |
| Harness Intelligence | A catalogue references reusable code, skills, tools, and instruction files with digests, effects, sizes, and tags. | It is not a fifth canonical query layer or an independently persistent store. Provisioning integration, source qualification, delivery, and loaded-file confirmation remain incomplete. |
| External service intelligence | Passive records describe operators, contracts, credential references, authority, pricing provenance, and independent qualification. | It is not a sixth canonical query layer, an installed connector fleet, or a running service-selection path. |
| Guardrail intelligence | Versioned rules, enforcement levels, scopes, tags, evaluation points, and review records exist. | Only provisioning has a concrete new evaluation hook. Public solve does not install the rules, and unresolved escalation can continue past a blocking rule. |
| Harness initialization | Instruction composition, assignment records, provisioned folders, and an optional Spawned Loop hook exist. | Public solve omits the required catalogue. A written file does not prove a native harness loaded it. Confinement defects need repair. |
| Shared authentication | `credential_leases` separates host-held credentials from scoped leases and use-time resolution. | Provisioning does not issue the leases, and harness use is not integrated. This is not a complete remote authorization service. |
| Classification and generation | Seven dimensions cover role, domain, geography, language, sensitivity, authentication, and lifecycle. Coverage can identify combinations lacking specific material. Six hand-authored occupations produce 327 candidate seeds. | No completed pipeline turns the classification grid into qualified, packaged, remotely searchable harness material. Code seeds are specifications, not generated working implementations. |
| Intelligence storage | Existing catalogue contracts have packaged-file, in-memory, SQLite, and DuckDB implementations; versioning and shared scopes were added. | The chosen DuckDB default, batched writes, search-characteristic sidecar, and hosted server-store integration remain roadmap work. Do not describe the design decision as a migrated default. |
| Detection and correction | Text conformance, duplicate detection, field recovery, malformed-field detection, address extraction, and database-copy components exist. Generic capability dispatch exposes registered pure surfaces. | Deterministic examples do not establish a general unseen-task solver. Confidence signals are not calibrated probabilities, and effectful work needs its separate authority path. |
| Evaluation and optimization | Frozen suites, deterministic graders, parameter enumeration, noise treatments, convergence reporting, and example 27 exist. | Live optimization and general convergence are unqualified. Data used to choose among cells is validation data; confirmatory quality needs a further untouched population. |
| Prompt and resource optimization | Prompt elements, response style, size expectations, alternatives, and efficiency-review records exist. | The public Practitioner does not perform the new efficiency review at every model step or use the new prompt axes throughout its own run. |
| Learning and telemetry | Cost records, reuse evidence, training-record types, specialist training, and an unfinished progress-event collector exist. | The collector has identity and privacy defects and returns aggregate counts instead of persisting the derived records. Automatic cross-task learning is not established. |
| Local and cloud resources | Resource snapshots, admission ledgers, owned process controls, reservations, and a distinct checkpoint-and-release hibernation protocol exist. | The supervisor and hibernation are not connected to ordinary harness execution. Cloud quotas, orphan recovery, cost reservations, and administrator controls remain open. |
| Standalone solutions | Export produces package files, tests, a manifest, and container/scheduling definitions. Example 26 exercises an export outside the original source import path. | A general public solve-to-multiple-exported-solutions lifecycle still needs integration and fresh-input qualification. |
| Hosted product | An authenticated HTTP service and a separate in-process provisioning component exist. The image publication workflow succeeds. | The HTTP service does not expose the provisioning component or a hosted Model Context Protocol endpoint. Durable metering, tenant state, telemetry intake, payment integration, and deployment remain implementation work. |
| Repository organization | Folder charters, a dated-record index, an import-dependency ratchet, a measured layout report, and a migration proposal exist. | The physical reorganization has not happened. The current tree has 362 Python files directly in `core`; creating more catalogue pages will not move them. |
| Competitor and research programme | The feature matrix, SenseLab review, typed-decision research, skill-repository research, deployment studies, and benchmark proposals were recorded. | Feature presence, system integration, production availability, and measured advantage need separate statuses. Vendor claims and old experiment scores remain attributed historical evidence. |

The canonical persistent-layer vocabulary still contains exactly four names.
The owner's fifth-component request was implemented as Harness Intelligence
references, while formal fifth-layer status was left open. The sixth-layer
idea was tentative. Guardrail intelligence was added as a policy component.
None of these should be silently described as a completed five-, six-, or
seven-layer architecture. Conversely, the request for dedicated harness
organization should not be lost simply because the canonical layer decision
remains unresolved.

## Reproduced findings and launch blockers

The following observations use disposable local fixtures. They do not assert
that a vulnerable endpoint is deployed. Full output and source hashes are in
[probe-results.json](probe-results.json); the reproductions are in
[review_probes.py](review_probes.py).

### 1. Provisioning can escape its workspace

Priority: repair before exposing or connecting provisioning.

`NodeAssignment` accepts `../escaped` as an identifier.
`provision_plan` joins it directly to its root and successfully creates the
assignment in a sibling folder. Separately, `provision` follows an existing
`task.json` symbolic link and overwrites a file outside the supplied root.
The second write does not receive the protections used by instruction-file
writing.

Owning code: [node_provisioning.py](../../src/loop_engine/core/node_provisioning.py),
`NodeAssignment.__post_init__`, `provision`, and `provision_plan`.
Required correction: validate identifiers as one safe path component, confine
every destination, reject symlink escape and unsafe overwrite, and make the
whole provisioning write set subject to the same effect decision. Negative
tests must cover traversal, absolute identifiers, existing links, collisions,
and partial failure.

### 2. An unavailable blocking guardrail does not stop provisioning

Priority: repair before treating these rules as enforcement.

A protected permission rule with `level="block"`, `judge="model_judged"`,
and `on_unavailable="escalate"` produces `blocked=false` when no judge is
installed. `provision` checks only `blocked`, then writes the instruction,
assignment, and provisioning files. There is no completed escalation decision
before those writes.

Owning code: [guardrail_intelligence.py](../../src/loop_engine/core/guardrail_intelligence.py),
`evaluate`, and [node_provisioning.py](../../src/loop_engine/core/node_provisioning.py),
`provision`. Escalation must represent unresolved work and prevent dependent
effects until its decision exists. Existing permission and effect contracts
must remain authoritative; a model cannot waive them.

### 3. The public solve path skips the new provisioning

Priority: complete the intended integration.

`solve_dependencies` installs a capability directory and the four-layer
catalogue builder but does not set `harness_catalogue` or `guardrails`.
`provision_spawned` consequently returns `provisioned=false` with
`reason="no_catalogue_installed"`. The new hook is import-reachable, but the
ordinary public dependency construction supplies nothing for it to do.

Owning code: [solve_runtime.py](../../src/loop_engine/code_nodes/solve_runtime.py),
`solve_dependencies`, and
[spawned_provisioning.py](../../src/loop_engine/core/spawned_provisioning.py),
`provision_spawned`. A regression check should start at the public solve
boundary and inspect the actual assignment folder and recorded offer. Testing
only a helper with an injected catalogue misses this failure.

### 4. Repeated model steps corrupt the learning join

Priority: repair before training, optimization, or telemetry export.

`learning_records` keys its intermediate dictionary by step name, format
attempt, and transport attempt. It omits the run and physical call occurrence.
Two ordinary route calls in successive passes overwrite the same dictionary
entry. The resulting list contains the second call twice: expected call
numbers `[1, 2]`, observed `[2, 2]` with duplicate record identities.

Owning code: [model_call_records.py](../../src/loop_engine/core/model_call_records.py),
`learning_records`. Use the existing exact call/occurrence identities on every
event and join by them. Repeated steps, interleaved Spawned Loops, retries,
failed calls, and multiple runs must remain separate.

### 5. The unfinished collector retains response content while denying it

Priority: repair before retaining or exporting these records.

The real completed event carries `output_preview`. When model input/output
logging is enabled, that field holds the entire serialized admitted value;
in quiet mode it still holds up to 480 characters. The collector removes four
other text fields but retains `output_preview`. Its report unconditionally
states `bodies_retained=false`. A synthetic response marker survives retention
while the report says otherwise.

Owning code: [model_call_collection.py](../../src/loop_engine/core/model_call_collection.py),
`LearningEventCollector.__call__` and `report`, and
[adaptive_practitioner_records.py](../../src/loop_engine/core/adaptive_practitioner_records.py),
the completed-event producer. Retain a positive, typed set of approved
metadata fields rather than copying unknown fields and removing a short list.

### 6. Collecting events has not completed the training-data path

Priority: complete before claiming usable accumulated learning data.

The collector can construct records, but `report()` returns the integer
number of records. `solve_task` places only that report in the outcome. The
new path neither saves the derived records through a store nor returns their
references. It also supplies the selected product result to a label function
that expects the enclosing adaptive result's `solved` and
`independent_verification_records` fields.

Owning code: [model_call_collection.py](../../src/loop_engine/core/model_call_collection.py),
[model_call_records.py](../../src/loop_engine/core/model_call_records.py), and
[solve_runtime.py](../../src/loop_engine/code_nodes/solve_runtime.py).
Persist the typed rows through the existing store boundary, label them from
the correct independently verified result, and return exact dataset/version
references. Existing raw Run History is a separate source; this finding is
about the new derived-record path.

### 7. The paid provisioning product still lacks several software connections

Priority: required first-release implementation.

`ProvisioningServer` explicitly has no network transport. The existing HTTP
service exposes health, conformance, evaluation, usage, and memory operations;
it returns 404 for the tested provisioning and Model Context Protocol paths.
The existing `mcp_adapter` is an adapter for consuming external tools, not
the missing product server. A cloud account and a price alone cannot complete
this path.

The service's default shared-memory store and metering ledger are in memory.
The new provisioning catalogue and its example meter are also in memory.
Moreover, a body read returns `metered=true` even when no meter is installed.
The catalogue offers and serves a fixture tagged candidate, regulated, and
operator-authenticated to an ordinary tenant with the generic bodies
entitlement. Tags currently classify material; they are not a tenant-access
or qualification decision. No actual protected user data was used in this
probe.

Owning code: [provisioning_server.py](../../src/loop_engine/core/provisioning_server.py),
[harness_intelligence.py](../../src/loop_engine/core/harness_intelligence.py),
[service_api.py](../../src/loop_engine/core/service_api.py), and
[service_endpoints.py](../../src/loop_engine/code_nodes/service_endpoints.py).
Connect transport, authenticated disclosure scope, source qualification,
durable tenant state, acknowledged metering, and privacy-preserving telemetry
before claiming an operated paid service. Keep candidate inspection an
explicit review operation.

### 8. The architecture artifact measures imports, not exercised behavior

Priority: correct the completion criteria used for further development.

The current static solve import closure contains 350 of 587 shipped modules.
The recovered artifact snapshot contains 349 of 586. Those are useful
inventory measurements. The traversal follows imports inside every function,
including self-tests, and does not establish that a real request invokes the
imported behavior. The generator's `called` field is copied from the curated
catalogue and defaults to true. Its check-count helper counts returned checks
without using their pass/fail values.

The missing provisioning dependency is a direct counterexample to treating
this map as execution evidence. Preserve the artifact, but add separate
evidence for public-path reachability, an observed invocation, successful
verification, and live qualification. Do not label a source import as a
completed integration.

### 9. The roadmap needs reconciliation before automated continuation

Priority: make the next development iteration select the right work.

The current file contains 79 steps: 10 published, 30 offline verified,
7 building, 21 proposed, 6 ready, 4 blocked, and 1 superseded. None is marked
live qualified. Several ready entries still depend on an unverified ready
entry. Some offline-verified entries depend on steps still marked proposed or
building. This may reflect useful partial implementations, but the statuses
do not faithfully implement the documented dependency rule.

The first eligible ready entry is a cluster-placement comparison. The later
launch direction centers on serving intelligence to customer-run harnesses.
An unattended loop following file order would therefore prioritize a task
that is not the immediate serving-release dependency. The six interrupted
launch tracks and a concrete first-release acceptance sequence have not been
integrated into that ordering.

Separate implementation state, public-path integration, offline verification,
live qualification, and publication. Preserve the old statuses as historical
evidence while reconciling the current execution plan.

## Proposed continuation order

This is a proposed implementation order recovered from the latest direction,
not a promise that a production service can be qualified within 24 hours.
All existing execution alternatives remain in scope.

1. Repair provisioning confinement, unresolved guardrail escalation, model-call
   identity, and metadata retention. Add the exact failing cases above to the
   owning checks, then verify the repaired behavior through the public paths.
2. Complete one whole serving path: a client authenticates, searches by typed
   criteria, selects an independently admitted capability, fetches its
   digest-bound body, and receives a durable usage record. Verify refusal,
   revocation, tenant separation, changed bodies, restart, and repeated
   requests. Implement the transport over the existing provisioning boundary.
3. Connect the local harness path to that service and to declared catalogue,
   guardrail, credential, and resource dependencies. Demonstrate one actual
   separately initialized harness loading the intended versioned material,
   producing an artifact, and undergoing independent verification. A folder
   alone is not the acceptance test.
4. Complete the learning path: persist sanitized per-call occurrences and
   outcomes, exact input/output references, provisioning observations, and
   client-reported telemetry with its provenance kept distinct from
   server-verified outcomes. Exercise restart and multi-run joins.
5. Build a bounded classification-grid generation run through existing
   boundaries: declared combinations, coverage gaps, search before building,
   candidate generation, independent qualification, package publication into
   the catalogue, and retrieval by a later assignment. Record rejected and
   empty combinations. Do not equate 327 candidate seeds with 327 usable tools.
6. Put deployment and environment configuration under version control, bind
   releases to exact image and package identities, rehearse health checks and
   rollback, and then run an authorized hosted smoke test. Payment activation,
   prices, cloud account access, and paid model authority remain explicit
   owner decisions wherever not already supplied.
7. Resume the measured folder reorganization one owning family at a time with
   compatibility imports and updates to string-based registries. Choose the
   first move by dependency isolation and reviewer comprehension, not merely
   by the largest filename-prefix count. Keep behavior changes separately
   reviewable.

The one-million-recorded-runs requirement for learned heuristic adoption
remains an owner constraint, with the stated exact atomic fingerprint
exception. Candidate generation, evidence collection, and controlled
experiments can proceed without declaring an unqualified learned policy
active. Preserve the complete initial choices and ordered fallback priorities
in the configuration requirement; prompt length and step count are not
universal optimization objectives.

## Verification and evidence limits

Observed in this review:

- Nine owning-module suites passed 65 of 65 checks before the broad suite.
- The current full offline self-test passed 5,316 of 5,316 checks in about
  312 seconds. Optional `cmaes` and `optuna` adapters were not tested.
- The independent probe script reproduces ten defect or launch-gap
  observations. Its `finding_present` values mean the problem was observed,
  not that the product passed an acceptance check.
- `git diff --check` passed for the pre-existing changes.
- [GitHub continuous integration for the current commit](https://github.com/alisonjieli-png/loop-engine/actions/runs/35422463025)
  and [worker-image publication](https://github.com/alisonjieli-png/loop-engine/actions/runs/35422463022)
  both report success. Those runs cover the committed tree, not the
  uncommitted collector or subsequent hosting-document changes.
- The recovered batch 35 export passed its recorded conformance,
  documentation, tools, self-test, and 32-step acceptance/example battery.
  The source comparison described above makes that evidence relevant to the
  matching files; it does not erase the reproduced defects.

No live model or customer harness call, new cloud deployment, billing change,
benchmark rerun, clean-wheel installation, or vendor-price verification was
performed in this review. Old provider-allowance failures remain historical
observations; present provider readiness was not probed. Research comparison
claims were reviewed as session decisions and provenance, not independently
re-benchmarked vendor performance.

Only this review directory was created. Existing implementation, prompts,
roadmap, managed records, and historical evidence were not rewritten, committed,
or published.

## Complete behavioral explanation retained for continuation

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.

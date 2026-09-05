# Harness and memory hardening

This pass extends the existing Loop boundary and repairs reproduced memory
defects. It does not establish AGI, arbitrary-domain success, automatic
deployment, or the absence of every defect.

## Repository and scope

Work continued on `main` at
`d121379773e46a1255fd3e86436d907dc2a0b4d0`, preserving the preceding uncommitted
record-access changes. The separate showcase worktree was untouched. Existing
Codex and OpenCode processes were left running; no credentials or process
arguments were copied into this report. File ownership was split explicitly
between harness implementation, two memory boundaries, tests, and verification.

No provider task, external harness session, package installation from the
network, deployment, commit, or push was performed by this pass. Tests use
offline fixtures. A base-wheel installation uses the existing local wheelhouse.
OpenCode Go and Zen provider routes are distinct from the quarantined coding
process adapter and were not disabled.

## Implemented changes

| Boundary | Correction | Evidence and limit |
|---|---|---|
| Adapter registration | Accept bounded identifiers for explicitly supplied host adapters; detect registration drift | A previously unknown fixture adapter runs inside the same Loop without changing a name whitelist. No name-triggered import or automatic discovery admission. |
| Mechanics contract | Compare typed requirements with declared features, isolation and preemptive limits before dispatch | Refuse unsupported tools, skills, context, workspace, approvals, routes, and every declared effect family. Capabilities remain declarations, not qualification or authority. |
| Request identity | Digest the full contract, profile, context visibility, inputs, metadata, requirements and authorization | Changed output/effect contracts produce distinct identities. Identity format is `harness_request_identity/v2`; do not reuse old digests as interchangeable controls. |
| Input ownership | Freeze detached finite JSON requests and metadata | Reject cycles, opaque handles and non-finite values without conversion hooks. Reserved credential fields are refused in metadata; this is not general secret detection. |
| SDK prompts | Preserve nested JSON and remove silent 50,000-character truncation | Large input fixture retains its ending. General context-budget compilation remains separate work. |
| Result ownership | Clone the producer's result envelope, capture exact output, reconstruct small JSON bodies | Later producer mutation cannot change returned output or stored bytes. Mutable consumer output is a working copy, not a new verified artifact. |
| Result identity and errors | Check exact provider/model and adapter version; normalize public error categories | Wrong identity cannot report completion. Exception text is not copied into history; call counts after an uncertain exception remain unknown. |
| OpenCode | Remove raw-host execution and retire the unowned client path to a refusal-only shim | Passive adapter information and execution refusal tested without launching a binary. The removed path used prompt argv, ambient credentials/configuration, and raw NDJSON persistence. No replacement sandboxed profile is qualified. |
| Inline information | Snapshot admitted plain values and return defensive copies | Producer/consumer mutation cannot alter stored value. Inline tuples retain their type; process-local data does not become durable. |
| Working memory | Validate restore envelope, digest, run/Loop identity and receiver capacity before state replacement | Failed restore preserves current state. Values and reads are detached; byte accounting is rebuilt. Snapshot/v1 does not preserve all historical eviction metadata. |
| Run notes | Snapshot input references and detach write/read/search results | Changing a returned dictionary no longer changes stored notes without a write event. |

One runtime remains: `Loop`. No domain workflow, new intelligence layer,
database authority, autonomous harness selector, or self-promotion mechanism
was added. The broader [research review](../research/STORAGE-PACKAGES-HARNESSES-AND-MEMORY-2026-09-04.md#alternatives-to-opencode)
compares OpenHands, Codex SDK, Claude Agent SDK, Pi, and the four bounded SDK
families using primary maintainer documentation.

## Focused verification

| Suite | Passed / total |
|---|---:|
| External harness contract | 66 / 66 |
| Four SDK adapter fixtures | 21 / 21 |
| OpenCode process-adapter quarantine | 11 / 11 |
| Deprecated OpenCode client refusal | 5 / 5 |
| Information access | 32 / 32 |
| Working memory | 18 / 18 |
| Runtime note board | 7 / 7 |

These 160 checks exercise local contracts. They do not measure model quality,
provider availability, shell sandboxing, distributed memory, or paid-call
prevention. A separate reviewer reproduced the ownership and error leaks,
checked their fixes, and added eight harness regressions. Severe Ruff checks,
Python 3.10 syntax parsing, and whitespace checks passed for the changed source.
This is not a claim that every historical style warning was removed.

The first broad source run passed 2,678 of 2,680 checks. Two OpenCode fixtures
still assumed a workspace reference imposed no capability requirement. One
expected only filesystem/process refusals; another retained a workspace while
testing an otherwise empty request. Both failures are retained in the
verification log. Final results must come from the corrected checkout, not
from excluding those tests.

## Full verification

The final source suite passed **2,680/2,680** checks in 146.71 seconds. The
clean base-wheel suite passed **2,635/2,635** applicable checks in 131.66 seconds.
Both reported zero provider calls and no changed source bodies during the run.
Source and installed-wheel conformance each passed **27/27**. All **472**
packaged runtime files matched the wheel, source distribution, and installed
wheel byte for byte. Build, installation, and dependency checks passed offline.
The difference is the base installation's explicitly untested optional adapters:
DuckDB, MCP, model2vec, NumPy, OpenTelemetry SDK, pandas, and scikit-learn.
Optional-package omission is not reported as a passing integration.

The initial wheel run also retained the two stale-fixture failures at
2,633/2,635. Both final suites reran the complete applicable population after
the same fixture correction. No failing check was removed from the denominator.
Verification continued across midnight into 2026-09-05 local time.

The [compact verification artifact](../evidence/harness-memory-verification-2026-09-04.json)
records commands, output digests, counts, source identity and build/install
comparison. Raw command output remains in
`/tmp/loop-engine-harness-memory-verification.ZybX3K/`; the compact artifact
does not duplicate every raw test result. Reproduction commands are
`PYTHONPATH=src python3 -m loop_engine --self-test` and
`PYTHONPATH=src python3 -m loop_engine --conformance`; wheel tests run outside
the repository with `PYTHONPATH` removed and provider credentials excluded.
The compact artifact SHA-256 is
`0c5cbff74881ad56572d52f5775fe211e656e40ecf5b57d4caa3c78b8b2bb410`.

## Managed handoff

The host-configured `loop-engine records` command created and then updated
`session.harness-memory-20260904` in namespace `development.sessions`. Each
write used the reviewed exact effect digest; the update required revision 1.
A subsequent tool read materialized revision 2 with artifact digest
`d87e9e716a3be9b7815a405ee49391ec8bec25922906e87e6d382f26a21bac53`.
The prior revision remains linked. No direct database or revision-file edit
was used. Records remain candidate reports and grant no authority.

The local state remains under
`.loop-engine-dev/record-tools/storage-review-20260904/`. The create, update,
and read each reported zero model calls. The CLI persists the managed
record revision chain, not its execution Run History; its result explicitly
reports `run_history_persisted: false`. This Markdown is a hand-authored
verification report, not a claimed generated operational view.

## Files and authority

`core.external_harness` owns request/result contracts, explicit registration,
and canonical Loop invocation. Its existing adapter module owns SDK bindings.
`core.harness_execution_contracts` contains passive capability requirements,
validation, and descriptions; `core.external_harness_output` contains internal
artifact serialization. Neither creates a new service runtime or registry.
`external_harness_checks` holds the focused fixtures.

`information_access` and its checks own storage-neutral materialization.
`memory.working.state` owns activation-local state and snapshots.
`core.runtime_memory` owns the existing run note board. The two OpenCode modules
preserve import compatibility while refusing unqualified execution.

The architecture map registers the two extracted modules. Root and packaged
`architecture.yaml` describe the same invariants. The component guide, contract
index, research note, README and continuation page distinguish implementation
from target behavior. The earlier storage report remains a dated record of its
own checkout and test population.

## Unproven behavior and next action

`HarnessBudget` still describes post-run acceptance limits. A required
preemptive control must be declared by the adapter or execution is refused.
No built-in capability declaration currently qualifies prevention of total
token or cost overruns. This does not repair the separate product-path token
overrun recorded in the unseen-task diagnostic.

No new unseen Kaggle task was solved in this pass. The live assisted/fresh
gate, independent task-quality improvement, and cross-domain generalization
remain open. Runtime grants, expiry/revocation, distributed streams,
cross-process snapshots, generated session views, PostgreSQL substitution,
and migration of all managed file writers are not completed here.
Snapshot digests check content integrity; they do not authenticate a checkpoint
issuer or grant permission to restore externally supplied state.

Next, qualify one pinned full coding adapter on a frozen local task through the
canonical Loop. Require an actual sandbox, restricted environment, reconciled
tools/skills, exact approvals, cancellation, and complete accounting before
launching it. OpenHands is the first research candidate, not an enabled default.
Use the same task and verifier for alternatives; do not add industry routes or
replace the current assisted/fresh proof gate.

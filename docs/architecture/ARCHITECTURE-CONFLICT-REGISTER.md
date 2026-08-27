# Loop Engine architecture conflict register

This register resolves material disagreements found in the current repository,
Git history, relevant OpenCode sessions, historical prompt files, and the
current user mandate. It records the accepted meaning. It does not claim that
every accepted meaning is already verified in the worktree.

The exact source inventory, OpenCode session IDs, content digests, and decision
states are in
[`GUIDANCE-RECONCILIATION-REGISTER.yaml`](GUIDANCE-RECONCILIATION-REGISTER.yaml).
Exact spellings of retired terms are retained only in historical source files
and in `artifacts/verification/conflicts.jsonl`.

## Accepted architecture

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
    │   └── non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

```text
Authoritative reusable graph
└── LoopGraphDefinition
    ├── exact LoopDefinition references
    ├── typed vertices and edges
    ├── graph inputs and outputs
    └── version and content digest

Passive solution construction
└── Solution Canvas
    ├── candidate
    ├── comparison object
    ├── builder
    ├── projection
    └── portable selected specification
```

```text
Persistent intelligence
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence

Non-exclusive functional metadata
├── Ask
├── Horizon
├── Readiness
├── Deliberation
├── Implementation
├── Execution
├── Verification
├── Integration
└── Routing
```

## Conflict summary

| ID | Conflict | Accepted resolution | Current state |
|---|---|---|---|
| LE-CONFLICT-001 | Concrete runtime name versus legacy record spelling | `Loop` is the sole concrete and public runtime. `LoopNode` has no active meaning. Historical `kind: loop_node` records migrate to `LoopDefinitionRecord`. | Runtime source and compatibility reader implemented; full wheel proof pending. |
| LE-CONFLICT-002 | `Loop` was deprecated in the baseline terminology contract | Remove that deprecation. Preserve compatibility only through explicit passive or historical meanings. | Concurrent terminology edit present; compatibility proof pending. |
| LE-CONFLICT-003 | Run History versus older history and query-decision vocabulary | Run History is the public execution history. Event log, record, report, and evidence are precise supporting terms. Historical files remain unchanged evidence. | Baseline GitHub public-documentation job is red; fix in progress. |
| LE-CONFLICT-004 | Four persistent layers versus nine functional domains | Keep four persistent layers. Use the nine functions as many-valued metadata. | Accepted; cross-layer and multi-function proof pending. |
| LE-CONFLICT-005 | Reference nine-step profile versus task compilation responsibility | Keep the versioned profile identity for compatibility. Make task compilation an explicit governed responsibility. Do not impose one stage count on custom profiles. | Kernel responsibility exists; documentation and custom-profile proof pending. |
| LE-CONFLICT-006 | Solution Canvas versus graph authority | Canvas is passive construction and comparison. `LoopGraphDefinition` alone is authoritative for reusable execution. | Implemented in structure; export and reload proof pending. |
| LE-CONFLICT-007 | Role-independent modes versus deterministic-only Solution execution | Role never determines mode. Installed executors, definition policy, permissions, and budget determine eligibility. | Deterministic path exists; model-led Solution execution is concurrent and unproven. |
| LE-CONFLICT-008 | Candidate staging versus complete governed learning | Complete learning requires durable review, promotion, later retrieval and use, measured improvement, and negative-transfer protection. | Baseline stops at staging in the public flow; concurrent lifecycle code is unproven. |
| LE-CONFLICT-009 | Five-step README language versus CLI behavior | The five-step demo may group onboarding, but its fifth step must say that it stages only. Review and promotion remain separate commands and proof. | README discloses staging; full public cycle is incomplete. |
| LE-CONFLICT-010 | Historical success language versus current GitHub state | Current checkout and current GitHub results override old transcripts. | Run `33081066312` is red in public documentation; other required jobs passed. |
| LE-CONFLICT-011 | Large future mandates versus immediate core proof | Preserve useful existing work, but close the earliest incomplete core checkpoint before expanding campaigns. | Accepted sequencing; core completion report not yet proven. |
| LE-CONFLICT-012 | Dedicated model-routing knowledge versus a fifth layer | Use a model-routing record family and portfolio across existing layers. Do not create another layer or runtime. | Required but not yet proven end to end. |
| LE-CONFLICT-013 | Everything is a Loop versus passive typed objects | Every independently governed unit of operational work is a Loop. Records and configuration remain passive. | Accepted; mutation proof must cover new capabilities. |
| LE-CONFLICT-014 | Historical prompts versus current authority | Preserve prompt provenance, but apply current precedence and extract only material decisions. | Eight workspace sessions and three cross-directory message fragments included; unrelated session material excluded. |

## Detailed resolutions

### LE-CONFLICT-001 and LE-CONFLICT-002: runtime identity

Baseline evidence at `6a26978` disagreed internally:

- `README.md` named `Loop` as every executable vertex.
- `docs/architecture/CONSTITUTION.md` named `LoopNode` as the operational
  object.
- `architecture.yaml` pointed to the concrete class
  `loop_engine.loop.recursive_loop.Loop` but labeled its kind differently.
- `terminology.yaml` deprecated `Loop` even though the runtime and README used
  it.

Accepted resolution:

- `Loop` is the sole concrete class and public runtime identity.
- `Node` is a conceptual category and namespace only.
- Historical `loop_node` may name a serialized record kind only; it is not a
  explicit compatibility surface.
- No role, mode, capability, provider, model, or plugin may define another
  runtime class.

This is a resolution target until the dirty worktree passes conformance,
serialization compatibility, clean installation, and current GitHub checks.

### LE-CONFLICT-003: one public history

The baseline public README used Run History while normative and source files
still used older history terms. GitHub run `33081066312` then scanned
historical prompt and source text as current public prose. The public
documentation job failed even though the three suite jobs and distribution
build passed.

Accepted resolution:

- Run History is the public ordered history of Loop execution.
- An event log is the ordered event representation inside that history.
- A record, report, or evidence object is named for its exact role.
- Benchmark, routing, scenario, research, learning, and Studio views read the
  same canonical history.
- Historical prompt files remain preserved evidence and do not govern public
  vocabulary.
- Source terminology is enforced by the machine conformance gate. Public prose
  is enforced by the documentation job.

### LE-CONFLICT-004: layers and functions

The four persistent layers answer where durable intelligence belongs. The nine
functions answer why a record is useful. They are independent dimensions.

One record may support Readiness, Execution, and Routing without being copied
into three physical stores. A current availability snapshot may remain Runtime
Memory rather than becoming persistent intelligence.

### LE-CONFLICT-005: reference profile and flexible procedures

The repository retains `practitioner.reference_nine_step` as a versioned
profile. The kernel also has an explicit `compile_bind_task` responsibility.
These facts are compatible when the profile keeps its stable identity and task
compilation is bound as a governed responsibility rather than hidden.

Custom Practitioner profiles may be atomic, linear, conditional, DAG-shaped,
stateful, cyclic within a bound, dynamic, nested, or parallel. Each still
declares typed contracts, authority, ownership, budgets, stop conditions, and
verification.

### LE-CONFLICT-006: canvas and graph

`SolutionSpec` and Solution Canvas may construct, compare, select, serialize,
and project candidate solutions. They do not execute independently. A selected
candidate must resolve exact Loop definitions and one `LoopGraphDefinition`
before reusable execution.

The unresolved proof is:

```text
candidate canvases
→ explicit selection
→ exact Loop definitions
→ one LoopGraphDefinition
→ validation
→ execution
→ portable export
→ reload
→ equivalent graph and contracts
```

### LE-CONFLICT-007: role and run mode

Practitioner, Intelligence, and Solution are responsibilities. Deterministic,
hybrid, and non-deterministic are per-Loop execution modes. A role-level mode
ban is invalid. A definition may restrict its own supported modes, and a run
may fail because a compatible executor, permission, budget, or provider is
unavailable.

The committed README truthfully says the in-process Solution runner is
deterministic-only. Concurrent edits add a shared model invocation port for
Solution leaves, but no accepted result is recorded until the complete
role-mode matrix and installed-wheel path pass.

### LE-CONFLICT-008 and LE-CONFLICT-009: governed learning

The public fifth demo step stages a candidate. That is honest but incomplete.
Full learning requires:

```text
verified run
→ durable candidate
→ independent review
→ accepted promotion
→ active Learned record
→ later retrieval from empty Working Memory
→ observed use
→ measured comparison with a control
→ negative-transfer check
→ supersession or rollback when needed
```

Concurrent code adds local review and promotion methods. Those methods remain
work in progress until distinct producer and reviewer identities, immutable
versions, scope filters, later use, and rollback behavior are tested through
the public installed path.

### LE-CONFLICT-010: current evidence wins

At the starting SHA, GitHub Actions run `33081066312` reported:

- suite and conformance on Python 3.10: success;
- suite and conformance on Python 3.11: success;
- suite and conformance on Python 3.12: success;
- distribution build: success; and
- public documentation: failure.

Therefore main is not green. Historical transcripts and local passing checks
cannot override that result.

### LE-CONFLICT-011: checkpoint order

Research, scenario, retrieval, benchmark, media, browser, and Kaggle work may
be valuable. None substitutes for this core chain:

```text
input
→ typed task compilation
→ intelligence query
→ mode and executor selection
→ Practitioner, Intelligence, and Solution work
→ selected authoritative graph when needed
→ verified result
→ Run History
→ governed learning
→ later measured reuse
```

The earliest incomplete hard checkpoint remains the priority.

### LE-CONFLICT-012: model-routing intelligence

Model capability, task-conditioned suitability, current availability, hard
policy, user preference, and observed outcomes are separate facts. They may be
queried through one dedicated portfolio across the four layers. This does not
create a Model Intelligence layer, model runtime, or local-model fork.

All model routes use `ModelGateway`. Locality is provider and route metadata.
Deterministic resolution is considered first. Same-tier failover, quality
escalation, abstention, and human review remain separate outcomes.

### LE-CONFLICT-013: operational work boundary

Create a separate Loop only when work needs an independent combination of
goal, typed contract, authority, budget, deadline, retry, placement,
checkpoint, verification, cancellation, return destination, or Run History
identity. Low-level implementation stays inside its owning Loop.

### LE-CONFLICT-014: guidance provenance

The relevant OpenCode corpus contains eight sessions rooted in the Loop Engine
workspace plus three exact message fragments from two sessions rooted
elsewhere. One cross-directory fragment records predecessor naming and public
language decisions. Two fragments repeat the core-proof mandate inside a
newsletter session. All unrelated material from those sessions is excluded.

The session titled `GLM 5.3 not visible in opencode` is excluded because it
changes OpenCode's own model list. A Taedri harness session with only generic
one-Loop language is also excluded because its material task does not govern
this repository.

Seven named mandates were not found as standalone files in the approved roots.
Some of their content appears inside current or OpenCode messages. They remain
`SOURCE_UNAVAILABLE` as standalone artifacts. Their contents are not invented.

## Verification required before closure

No conflict is fully closed merely because this register states a resolution.
Closure requires all of the following:

1. Current code, schemas, contracts, and public documentation express one
   meaning.
2. Positive and negative tests enforce that meaning.
3. The wheel installs and the public path runs outside the source tree.
4. Current main GitHub checks pass.
5. Saved evidence identifies the exact commit and command.

# Adaptive host execution and task generalization

This checkpoint repairs task delegation, artifact delivery, and a stale
verification fixture. It also tests five task shapes through the same host
interface. The runtime remains `Loop`; task knowledge stays in manifests,
capabilities, and verifiers.

The core checks pass, but unattended readiness is not established. The latest
Sales candidate passes its saved tests and still has an independently
reproduced exact-arithmetic failure. Its engine verdict remains recorded;
the later audit invalidates the broader correctness claim.

The [machine-readable checkpoint](../evidence/adaptive-host-generalization-20260906.json)
records attempt identities, source and outcome hashes, accounting completeness,
and audit receipts. The [history review](HISTORY-AND-OVERNIGHT-REVIEW-2026-09-06.md)
summarizes the accessible prior logs and confirms 1,049 entered competitions
on the configured Kaggle account, without exporting its membership list.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when model use is authorized
    └── Run History records
```

## Reproduced defects and repairs

| Boundary | Reproduced defect | Current behavior |
|---|---|---|
| Method admission | A non-spawning action could switch into recursive execution. Malformed assignments and dependency fields could disappear silently. | The planner binds execution shape to the selected action, validates every assignment, and refuses unsupported fields without partially updating the admitted plan. |
| Recursive state | Spawned work shared the spawning task, context, workspace sequence, and accepted results. | Each Practitioner has a separate task scope. The complete objective, constraints, and success criteria reach its model and host verifier. Only explicit result summaries return to the spawning task. |
| Completion | A subproblem's success could be confused with the spawning task's result. | The spawning task needs its own current, issued verification. Completed subproblem summaries survive later failure and cancellation. |
| Progress | Recursive scopes reused progress sequence numbers within one run. | The run shares one progress sequence and names each context's Loop. Physical model usage and effect reconciliation also keep shared authority. |
| Workspace identity | A symlink at the allocated scope path could resolve outside the granted workspace. | Allocation and execution recheck the scope and exact execution path. This is a path check, not operating-system isolation from a hostile host process. |
| Hybrid execution | Kernel construction used a compatibility mode name that the Loop contract rejected. A completed exact resolver could still be followed by unnecessary model work. | Kernel construction derives the execution mode from the contract's existing map. Trusted preparation can return the registered resolver's verified result only after the exact spawned Loop closes successfully. |
| Prepared values | JSON normalization changed a tuple into a list while the independent trace retained the tuple. | The prepared value is detached without changing its in-memory types. Nested mutations cannot change the resolver's original value or trace. |
| Mixed artifacts | A project could produce its data output, delete a declared source file, and pass its mechanical checks. | The result includes authored source and expected outputs. Missing or changed source invalidates mechanical acceptance. Duplicate, colliding, and preexisting output paths refuse before material writes. |
| Source versus rendered output | The expanded artifact check treated a valid HTML template fragment as an incomplete final document. | Mixed-delivery source markup gets byte-integrity and encoding checks. Declared rendered output and code-only HTML keep their completeness checks. |
| Permission proposals | An invented permission name stopped a live run before the host could evaluate the requested operation. | Invalid proposals receive the existing bounded format-repair opportunity before any effect. Actual host denial remains a refusal, and a corrected proposal cannot grant authority. |
| Paired fixture | Both arms used an invented artifact digest, which the required independent verifier rejected. | The fixture executes authored code, records actual digests, and uses counted independent design and review responses. Wrong output and forged identity remain failures. |

The scope helper uses the existing kernel and event history. It does not
create a second task executor, graph authority, memory store, or approval
service. Registered host callbacks remain trusted application code.

## Verification

The final frozen source suite passed 3,246/3,246 checks. The clean base-wheel
installation passed 3,201/3,201. Both completed without runtime source changes
and made no real provider calls. Source and installed conformance each passed
27/27 gates.

All 485 packaged file bodies compared across source, wheel, source archive,
and installation matched. The generated `architecture_conformance.json` was
excluded from that byte comparison because each environment regenerates it.
The code/data snapshot separately covered 444 Python, YAML, JSON, and JSONL
files. Base installation explicitly omits optional adapter checks.

The tested changes were applied to `main` without a commit or push. The base
revision remains `1ea13357c9d46d261fa4164fced0ef0b0249a36e`. All 485 package files
in that checkout match the tested wheel; its independent conformance run
passed 27/27 gates and its probe tests passed 29/29. The five pre-existing
tabular/competition example files retained their original byte digests.

Focused checks passed: planning 37, task scopes 36, kernel runtime 27, Loop
contracts 12, generated projects 88, independent verification 123, adaptive
execution 44, and host integration 33. The probe's separate test module passed
29/29 tests. The paired fixture passed 27 checks and accounts for 18 injected
calls in its comparison, or 27 with calibration. Those are fixture calls.

Earlier verification attempts are preserved as diagnostics. One invocation
used a Python environment without installed distribution metadata. A capture
helper then lacked a real file descriptor required by the MCP test process.
The first completed source suite passed 3,232/3,233; its failing check found
59 new uses of retired source terminology. The names were corrected before
the successful frozen rerun. An initial offline dependency installation lacked
cached wheels. After obtaining the declared dependencies, a separate fresh
offline installation and dependency check passed. Later full-suite checks
also caught an obsolete two-call permission fixture and its direct history
read. The revised fixture verifies bounded proposal repair, no effects, and
history retrieval through the existing Intelligence Loop.

## Live regression population

The [probe guide](../../examples/25_host_runtime/GENERALIZATION-PROBE.md)
defines five authored tasks: duration parsing, CSV aggregation, dependency
scheduling, HTML delivery, and repair of existing source. The original
population had 42 fixed checks; independent counterexamples expanded it to
84. Each uses the same inspect, replace, and run operations.
Only the task contract, initial source, and evaluator cases vary.

The first frozen population returned three `COMPLETED_VERIFIED` results, one
`NO_PROGRESS` result after output-limit failures, and one operator-canceled
attempt. The HTML attempt was canceled after repeated output-limit failures,
with its initial source still unchanged and no execution observation. Its
interrupted call has unknown usage. The population retains all five tasks,
91 known model calls, 1,678,878 known input tokens, and 530,570 known output
tokens. These are lower bounds, not complete totals.

An independent audit then tested the three accepted sources against additional
requirements from their unchanged prompts. All three had counterexamples:

| Artifact | Counterexample |
|---|---|
| Sales aggregation | Quoted newlines disappear; decimal multiplication and cancellation lose precision; a valid long price raises an exception. |
| Dependency schedule | A dependency containing a list or dictionary raises `TypeError` instead of the required `ValueError`. |
| Interval repair | Large finite integer endpoints raise `OverflowError` when converted by `math.isfinite`. |

The audit passed 22 of 28 additional checks. All six nonfinite-float cases
passed. The original fixed-case passes remain recorded, but those three
artifacts cannot be called correct for their complete prompts. No original
source, outcome, or Run History was rewritten.

A separate two-task follow-up clarified the writer's digest precondition in
its JSON Schema and inspection response. The precondition uses the existing
source digest, not a hash of proposed new content. A known mismatch returns
an explicit no-write observation and cannot pass host verification. This is
a field-specific contract change, not a global prompt tutorial.

That follow-up returned verified HTML in 16 calls and stopped the duration
task with `AUTHORITY_REQUIRED` in 12 calls after producing source. The latter
was an invalid proposed permission name, not a new user-authority requirement.
The proposal boundary now permits the existing response-repair attempt before
any effect, while actual host approval denials remain refusals. The HTML
document also rendered in a fresh browser profile with hostile labels shown
as text.

The duration continuation used the existing unverified source and passed its
nine cases in 10 model calls. The three audited repairs passed 18 sales cases,
19 scheduling cases, and 18 interval cases in 21, 23, and 20 calls respectively.
They retained their task prompts and saved new evaluator and source identities.

A second independent sales audit then found a fixed 200-digit Decimal context
in the repaired source. Six of seven valid cases failed through rounding or
`InvalidOperation`. The small control passed. That accepted repair therefore
remains invalidated for its original exact-arithmetic requirement. A new
continuation replaced that representation with integer cents and passed 27
cases in 46 real calls. It did not receive the expected answers. Its task
prompt remained unchanged; failed cases supplied the exact-arithmetic
requirement as targeted feedback.

Across all 14 attempts, seven population reports record 279 known model
calls, 6,515,391 known input tokens, and 1,008,164 known output tokens. The canceled
HTML call leaves the combined totals incomplete; cost is unknown. Summed
attempt time is 4,010.863 seconds, excluding operator review and offline work.
All calls used the configured Ollama Cloud route and exact model
`deepseek-v4-flash:0731`. No failover was enabled. These usage counts cover
engine calls, not the surrounding coding-agent session.

All 14 Run History chains and manifests passed integrity checks, covering
23,695 events. The audit also checked 31 prior-file bindings used by follow-ups.
Chain integrity establishes record consistency, not semantic correctness.

A separate regrade passed all 78 cases then present, but further source review
found an interpreter-specific boundary in duration and Sales. Valid long
numeric text raised `ValueError`, including leading zeros representing one,
large cancellation yielding a small result, and formatting a roughly 5 KB
total. The failures occurred inside the candidate functions, not the audit's
output transport. Six confirmed cases expanded the population to 84. Earlier
acceptances remain invalidated; targeted continuations are recorded separately.

The duration continuation passed 10 cases in 20 real calls. An independent
regrade passed those 10 plus eight padding, range, and exact-arithmetic cases.
Its import disables Python's process-global integer conversion guard inside
the sandbox. That does not violate the original task, but requires review
before sharing the module in a production interpreter. No persistent
capability promotion occurred.

The final Sales continuation passed 32 cases in 20 real calls, but changed
back to Decimal arithmetic with a fixed precision of 20,000. An independent
audit froze the terminal source and found two wrong results: price cancellation
with 20,017 significant digits returned `0.00` instead of `0.01`; quantity
cancellation with 21,031 digits returned quantity zero instead of one and
the same wrong total. Inputs were about 40 KB and 42 KB. The small control
passed. These are bounded wrong-result counterexamples, not resource-exhaustion
tests or failures in the audit's transport.

| Selected artifact | Saved cases | Independent assessment |
|---|---:|---|
| Duration utility | 10/10 | Eight further checks pass; process-global import setting limits production reuse. |
| Sales aggregation | 32/32 | Two additional counterexamples fail. Full-task correctness remains rejected. |
| Dependency schedule | 19/19 | Source review found no further clear violation within the inspected ordinary-input scope. |
| Schedule HTML | 5/5 | Escaped output rendered in a fresh browser profile; source review found no further clear violation. |
| Interval repair | 18/18 | Large integers and nonfinite floats are covered; source review found no further clear violation. |

The selected artifacts pass 84/84 saved cases. That is not five generally
correct solutions. Seven of the eleven engine-accepted attempts were later
invalidated during this 14-attempt development sequence. Selection, new
counterexamples, and continuations were operator-directed, so this is not an
unattended or statistically powered generalization benchmark.

Recovery-call identities also caused some stage-usage joins to refuse;
public call accounting and stage attribution
remain distinct evidence levels.

## Bounded follow-on work

The work below can be scheduled as separate development tasks. It does not
impose one fixed sequence on every future user task. A Practitioner can keep
a task whole, use a qualified deterministic capability, or reconsider its
plan after an observation. Failure classification comes before subdivision:
an unavailable provider, denied effect, or invalid verifier is not evidence
that the task should be divided.

| Development task | Required proof before acceptance |
|---|---|
| Run independent counterexample checks before final acceptance | Bind the original task, exact candidate source, protected base tests, and a separately checked property or counterexample capability. Execute through the existing host verifier and sandbox. Include incorrect-oracle controls, preserve false acceptances, and return unknown when the available verifier cannot establish a material requirement. |
| Bind subproblem outputs to dependencies | Typed ports bind exact result or artifact references. Missing, stale, incompatible, and cross-scope values refuse; successful subproblems cannot complete the spawning task. |
| Admit parallel adaptive work | Use the existing delegation and graph contracts. Test joins, shared budgets, independent workspaces, cancellation, and partial failures without changing the simple serial control. |
| Reconsider granularity after observations | Compare keep, split, repair, escalate, and abstain on frozen simple and complex tasks. Record the failure layer and cost of each attempted strategy; do not force a split solely because a model failed. |
| Resume unattended work safely | Persist leases, checkpoints, exact effect receipts, and unknown outcomes through existing records. Crash after dispatch must not silently repeat a committed effect. |
| Add an Overnight host adapter | Use the actual daemon interface and protect its test commands, worktrees, secret handling, and branch-only review policy. Start with an exported ticket fixture; Jira mutation, deployment, push, and merge stay outside the grant. |
| Test transfer and memory separately | Freeze the source population, treatment assignments, model-visible packets, and independent evaluators. Complete the live paired gate before interpreting more tasks as evidence of learning. |

## Current limits and next work

Adaptive spawning is serial. Unsupported dependency-output bindings and
parallel scheduling require an explicit alternative; they are not silently
discarded. The existing graph compiler and `DelegationSpec` are the extension
points for those capabilities. Physical recursion still has runtime
supervision and host resource limits. A model's declaration that a task is
atomic is not evidence that it can complete it.

The paired fixture remains `mechanism_only`. Canonical trial assignments,
complete treatment-free packet comparison, source freezing at use, qualified
independent evaluator identity, and the public-history-to-projection bridge
remain open. These results do not establish a causal benefit from memory,
automatic persistent promotion, or trained routing policies.

The [research review](../research/ADAPTIVE-DECOMPOSITION-EVIDENCE-2026-09-06.md)
maps primary sources to testable extensions. The immediate next experiment is
an independently seeded, source-frozen counterexample generator before final
acceptance. For exact aggregation, vary magnitude and cancellation within the
declared input limits, preserve every previous regression, and record the
generator policy and seed. Further work on dependency bindings, granularity,
and partial verification needs unchanged simple-task controls and negative cases.

An Overnight integration also needs its host adapter to preserve protected
repository gates, worktree policy, privacy, and human review of proposals.
This checkpoint does not modify that separate project, connect Jira, schedule
a daemon, push a branch, or merge a proposal. A passing finite task population
cannot establish that the framework solves every possible task.

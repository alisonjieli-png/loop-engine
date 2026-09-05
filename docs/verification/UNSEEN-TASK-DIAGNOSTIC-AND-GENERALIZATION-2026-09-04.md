# New-task diagnostics and domain-neutral architecture

No new real Kaggle competition or generated task was verified complete in
this session. One generated case was attempted twice through the real solver.
Both attempts failed before sandbox execution and independent scoring.
The failures produced generic response diagnostics and a reproducible token
budget counterexample. They do not establish a successful learning loop.

## A. Repository state

Repository: `/home/username/loop-engine`, branch `main`.
Tested base HEAD: `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`, with pre-existing
uncommitted changes preserved. Work was performed on 2026-09-04 local time
and continued into 2026-09-05 UTC. The separate showcase worktree was not
changed. Process presence was not treated as file ownership.

All 466 runtime files stayed unchanged during final verification and matched
the built wheel and source distribution. The user subsequently authorized
commit and push. Live histories, generated data, hidden labels, and account
metadata remain private local artifacts, not publication candidates.
The audit metadata file `registered-conversation-sources.json` also remains
local because it contains internal conversation identifiers.

## B. Coverage and comparative synthesis

The [research note](../research/MODEL-ARCHITECTURES-COMPOSITION-AND-DEVICE-MESH-2026-09-04.md)
and [38-source ledger](../research/MODEL-ARCHITECTURES-COMPOSITION-SOURCE-MATRIX-2026-09-04.json)
compare model connectivity, training objectives, serving, semantic compilation,
response constraints, distributed interfaces, and optional triads.
The [coverage index](../research/ARCHITECTURE-COVERAGE-MATRIX-2026-09-04.json)
lists 157 families in 26 groups, including explicit unreviewed entries.
Listing a family is not completed review. No paper result was reproduced.

Borrow typed interfaces, explicit state, narrow effects, immutable identity,
and independent verification. Experiment with compressed context, contract-only
composition, alternative models, and sparse candidate panels. Reject the
inference that a long context is usable memory, valid JSON is a correct answer,
or majority agreement is a trust boundary. A containerized network is not
evidence of AGI.

The Humanizer writing skill kept the report in a neutral technical register.
The Deep Research skill governed source reconciliation and explicit gaps after
the expanded mandate. Its planning tool was unavailable; phase state is saved
in the coverage index. Existing repository-native Markdown is the report
format; no duplicate master prompt or rendered publication was created.

## C. Generalized architecture

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by,
    │                 Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effects
    ├── Model settings when permitted
    └── Run History
```

Domain meaning enters through the existing intelligence layers. The core
receives task requirements, evidence, capabilities, effects, authority,
environment constraints, deployment requirements, and verification.
It must not choose a house, traffic, industry, or competition workflow from a
label. Domain-specific protocol implementations and deterministic rules may
be qualified Code Intelligence; their meaning and applicability remain
explicit. New scenarios should add intelligence and manifests rather than
domain branches in the controller.

Problem/environment/deployment manifests and capability capsules are design
requirements mapped to current types, not newly installed runtime classes.
Packless operation, capsule-only graph composition, cross-target deployment,
and zero core changes for every new scenario remain unproven.

The test cases are benchmark-only data generators. No competition-name branch,
domain-specific solver, device runtime, or mandatory triadic profile was added
to product execution. Existing architecture diagrams were not changed to
imply these capabilities exist.

## D. Real product attempts

Provider: `ollama_cloud`; route: `cloud.default`;
model: `deepseek-v4-flash:0731`. One preliminary live probe succeeded.
No failover was enabled. The requested maximum output was the registered
65,536 tokens, not an invented smaller default.

| Attempt | Calls | Elapsed | Result | Independent score |
|---|---:|---:|---|---|
| Generated A, attempt 01 | 8 | 200.02 s | `NO_PROGRESS`; response admission and later unknown usage | None |
| Generated A, attempt 02 | 16 | 222.02 s | `NO_PROGRESS`; incomplete generated project and token-budget refusal | None |

The first attempt used 18-call, 200,000-token, and 120-second request limits.
The second used 30-call, 400,000-token, and 300-second request limits. Both had
a 900-second outer wall limit, three passes, and a 30,000-token estimated input
budget. Diagnostics and limits changed between attempts; this is not a matched
causal comparison.

The retry validated retained campaign/case digests, exact source-directory
membership, and file bytes before reading the task. It recorded runner,
settings, image, and runtime hashes. Four solver-visible source files remained
unchanged. The hidden evaluator was outside the source and declared workspace.
No workspace was created and no sandbox command ran, so end-to-end mount
isolation was not exercised. A late container sample found none and explicitly
does not prove absence throughout the run.

Run IDs:

- `adaptive-20a3de26abf2fe910aece403`: intact 576-event history.
- `adaptive-3987beb466f0f212136f82ce`: intact 1,132-event history and bound outcome.

The retry loaded zero prior stages in shadow mode. It is not a canonical fresh
arm, randomized control, advisory exposure, or paired-assistance result.
Seventeen saved work packets linked to context manifests; sixteen physical
request prompt digests linked to those manifests. Exact hidden-marker scans
found no matches, which does not prove arbitrary semantic non-contamination.

## E. Incidents, fixes, and preserved work

| Incident | Generalized change or finding | Evidence boundary |
|---|---|---|
| JSON rejection had no useful structural diagnosis | Save normalization strategy, fixed decoder category, offset, line/column, size, and root-shape hint; feed these into bounded format repair | No raw rejected body or private reasoning saved; grammar unchanged |
| Schema diagnostics could contain rejected values | Use content-free constraint categories | Historical traces were not rewritten |
| Accounting refusal hid transport failure | Keep transport outcome separate from accounting refusal | Unknown usage still remains unknown and blocks further bounded calls |
| Provider error text could retain secret content | Save fixed classified transport summaries; prove prompt delivery through typed status and digest | Whole-result malicious-error tests cover the inspected gateway boundary, not every possible logging path |
| Source metadata could be modified before launch | Retain external anchors and reject extra files, directories, or symlinks before disclosure | Diagnostic driver improvement, not completion of canonical paired source freezing |
| Total token ceiling was exceeded before refusal | Reproduced and left open | No additional live calls after discovery |
| Saved candidate code was invalid | `solution.py` fails Python syntax at line 147 | Original candidate preserved; no harness repair or execution |

The retry completed source inspection and role orientation. It checkpointed
`solution.py` and `verify.py`; README generation remained incomplete.
The first script has an unterminated triple-quoted string. The second parses
but trusts self-reported metrics, so it is not an independent task evaluator.
Neither is a verified incumbent or published result artifact.

## F. Token-budget counterexample

Before call 16, usage was 369,870, leaving 30,130 tokens. The complete prompt's
estimate was 27,772, which passed the 30,000-token context check. The estimate
uses approximately one token per four UTF-8 bytes. The provider reported
34,619 input plus 1,120 output tokens, for 35,739 on that call.

Total usage reached **405,609**, exceeding the configured ceiling by **5,609**.
The response was then rejected and subsequent calls refused. The pre-dispatch
check considered estimated prompt plus maximum output against route context,
but did not reserve them against the remaining run token budget.

Therefore the current setting is a post-accounting acceptance/continuation
threshold, not a guaranteed pre-dispatch consumption bound. Raising the budget
would not repair that distinction. Silently lowering the supported maximum
output would violate the current model contract.

The [offline reproducer](../evidence/unseen-task-diagnostic-20260904/budget-preflight-probe.py)
and [saved result](../evidence/unseen-task-diagnostic-20260904/budget-preflight-probe.json)
show one injected dispatch before total-budget rejection, versus zero dispatch
when route context cannot fit. They make zero live provider calls.

## G. Campaign and economics

Three generated cases were frozen: binary probability/AUC, regression/RMSE,
and multiclass labels/accuracy. Only A was attempted. B and C were not run.
The author-side feasibility check used hidden labels before live testing;
none were supplied to the tested LLM. This is a solver-hidden generated case,
not a claim of untouched global holdout or new latent task family.
The generator is included in the user-authorized publication. Its seeds and
formulas make all three cases public reproducible fixtures after publication.
Later runs on them must not count as new hidden or unseen holdouts.

Current funnel: 3 selected generated cases, 1 attempted case, 2 attempts,
0 verified completions, 0 independent grades, 0 new real Kaggle solves,
0 Kaggle submissions. The five-task and 100-task gates remain open.
New real competition candidates remain subject to exact source-use and
provider-disclosure review. No competition data was downloaded this session.

There were 25 live model calls including the probe. The known subtotal is
536,084 tokens; one first-attempt call has unknown usage, so the overall total
is unknown. Monetary cost is unknown; subscription quota may apply.
No performance ranking or model-allocation claim follows from this one route.

## H. Verification

| Check | Final result |
|---|---|
| Source suite | 2,504/2,504 |
| Isolated base-wheel suite | 2,466/2,466 applicable checks |
| Source and wheel conformance | 27/27 gates each |
| Focused parser/accounting/gateway/port/scorer | 79/79 |
| Independent malicious-error probes | 3/3 |
| Parser old/new differential cases | 3,678; zero admission behavior differences |
| Wheel, sdist, dependency and distribution checks | Passed; 466 runtime bodies match |

The base wheel explicitly did not test optional duckdb, MCP, model2vec,
NumPy, OpenTelemetry SDK, pandas, or sklearn adapters. Offline suites made
zero provider calls. An intermediate 2,503/2,504 suite failed because a fixture
expected raw error text; its replacement proves prompt delivery without that
privacy exposure. The failure is superseded, not omitted.

Exact commands and receipts are in the
[verification bundle](../evidence/unseen-task-diagnostic-20260904/final-verification.json).
The source command is `PYTHONPATH=src python3 -m loop_engine --self-test --format json`.
Conformance uses `python3 -m loop_engine --conformance`.
The clean-wheel command runs outside the repository with source imports
removed and exact base dependencies installed from local cache.

## I. Files changed in this session

| Path | Purpose and authority | Verification |
|---|---|---|
| `core/model_response_admission.py` | Passive structural diagnostics and redacted schema errors at existing admission boundary | 10 focused, 3,678 differential |
| `core/adaptive_practitioner_records.py` | Propagate diagnostics into the exact repair packet | Product-shaped offline repair and source suite |
| `core/model_gateway.py` | Separate transport/accounting diagnostics and redact provider errors | 18 gateway plus independent privacy probes |
| `core/model_gateway_accounting_checks.py` | Complete/unknown usage and secret-safety regressions | 11 focused |
| `code_nodes/solution_model_port.py` | Digest-bound prompt-delivery fixture | 9 focused |
| `benchmarks/kaggle_competitions/fresh_shaped_cases.py` | Frozen generated population and independent benchmark grader | 31 focused; not runtime task routing |
| `.gitignore` | Keep private live runs and generated labels local | Publication audit |
| Research note, source ledger, coverage index | Evidence and design gaps, not architecture authority | JSON, links and Markdown checks |
| Verification report, evidence bundle, start-here and benchmark README | Durable continuation and honest denominators | Readback and documentation checks |

The five runtime paths above are relative to `src/loop_engine/`.
Pre-existing changes included in the later user-authorized repository snapshot
are not claimed as newly authored by this session.

## J. Maturity and unproven claims

Diagnostic changes: `IMPLEMENTED_OFFLINE`, with repair diagnostics observed on
a live product attempt. Source inspection executed, but no task was solved.
Current stage-assistance foundation remains `mechanism_only`; no live pair or
causal benefit is established. No distilled model, qualified shortcut,
cross-provider triad, scenario compiler, device mesh, or million-task claim
is made. The failed candidate must not become a positive training label.

## K. Exact next action

Define a source-backed pre-dispatch token reservation contract and replay the
saved counterexample offline. A true hard bound needs a sound input bound plus
the required output maximum, or a provider-enforced equivalent. Unknown bounds
must be explicit. Preserve both failed attempts and code checkpoints.
Only after that gate should another bounded product attempt be authorized.
The separate assisted/fresh source/control proof must still complete before
historical intelligence is credited or campaign expansion claimed.

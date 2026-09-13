# Experiment-driven self-improvement

Loop Engine can use the same task execution and evaluation interfaces to
investigate a solution, a configuration, or a proposed change to its own
procedures. Recursive self-improvement requires a further step: an
independently reviewed change must be used in later work and show a useful
measured effect. Generating a suggestion does not establish that result.

## Shared runtime

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

Self-improvement is a Practitioner responsibility. The reusable profiles
remain those of the existing runtime:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

A hosted model address and a loopback address use the same gateway contract.
The declared protocol, authentication, capabilities, and explicit permissions
determine whether an operation can run. The address does not create a new
runtime type or prove where downstream processing occurs.

## Complete behavioral explanation

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

That complete explanation must remain alongside the full phrase. A shorter
label alone is not an adequate replacement.

## The proposed improvement cycle

The existing components can support this procedure. The complete autonomous
cycle has not been qualified:

1. Select exact tasks and verify the relevant Run History records.
2. Produce a falsifiable improvement hypothesis with an applicability scope.
3. Freeze a baseline, candidate, objective, constraints, and evaluator.
4. Run both through the same governed execution and recording boundaries.
5. Evaluate without exposing protected cases or letting the candidate weaken
   the original obligations.
6. Submit the candidate and the complete results for independent review.
7. Promote only through the existing authorized lifecycle, then measure later
   use, regressions, and negative transfer.
8. Use those later observations as inputs to another improvement task.

The producing Loop cannot approve its own candidate. A different model name
or reviewer label alone does not establish independence. Review must bind the
exact subject, use the required evidence, and keep evaluation and promotion
authority outside the producer's control.

## Experiment targets

| Target | Examples | Required evidence |
|---|---|---|
| A task solution | Software, analysis, a report, research, or a simulated service operation. | Original obligations, actual deliverables, and an appropriate independent evaluator. |
| A procedure | More or fewer steps, different prompts, questions, retrieval, tools, or verification. | Applied treatments, matched controls, recorded failures, and measured effects. |
| A selection policy | Harness, model, context, fallback, or meta-selector choices. | Exact eligibility scope, comparable feedback, and performance on work not used to tune the policy. |
| A reusable implementation | A verified procedure or Code Intelligence candidate. | Provenance, license and dependencies, typed contract, effects, tests, digest, and independent qualification. |

These targets do not require separate runtimes. They do require different
task contracts and evaluators. Source readiness in the task database does
not prove evaluator readiness. A simulated action does not qualify a real
business-system mutation.

## Current review behavior

`run_self_improvement` uses `practitioner.self_improvement@1.0.0`. It reads
selected history, verifies chains, inspects intelligence, and stages candidate
review items. `run_limit=None` selects the full directory population;
`run_limit=0` selects no history. Missing or broken bundles remain excluded
with a reason.

The history miner reads explicit model-response and failure events. Merely
running a model-capable step does not establish that a model answered, that
the answer was correct, or that a deterministic method was unavailable.
Repeated events in one trace do not become several runs. Known copied
histories are not additional observations. Candidate frequency and heuristic
scores remain review aids, not calibrated confidence or improvement evidence.

## Preparation for a configured endpoint

The campaign's `prepare` operation accepts `--route-name` to bind an existing
gateway route. It also accepts a timezone-qualified `--not-before` value.
The worker makes no access probe or task call before that time.

After the gate opens, a new campaign uses a real request through the shared
gateway to check access. The probe has its own Run History and one physical
attempt allowance. It requests the exact sourced model output capacity and
does not permit provider failover. A failed probe leaves the task cursor
unchanged and stops with `provider_access_not_verified`.

An estimated quota reset is not verified availability. A catalog can list
models while the account cannot generate. Unknown model output capacity
also remains a refusal, not a guessed limit.

Each task attempt records the configured treatment and the effective output
allocation, provider attempts, and observed harness attempts. A recovery may
change a request's allocation; the effective record must show that difference.
Keep access probes separate from task executions in the denominator.

## Safety limits before wider execution

Authentication, request, quota, and transport errors are different conditions.
The campaign reads the actual terminal gateway codes. An unknown code does
not become an invented outage. Reaching the configured wait ceiling for a
provider outage or allowance suspends that route without failing the task or
advancing through the remaining queue.

An interrupted trial remains `interrupted_requires_reconciliation`. Its
marker and cursor are preserved. Recording an interruption, clearing a
marker, or choosing a new directory name cannot establish that pending effects
are resolved. The general effect-reconciliation workflow remains incomplete.

Referenced checkpoint histories are not automatically deleted. The current
full-ledger checkpoints can still grow quadratically in stored bytes over a
long task. A scalable canonical append or checkpoint representation remains
necessary for large campaigns. Copying every snapshot is not the finished
storage design.

The trial evidence-summary helper is a gap inventory. File presence, an
artifact count, a cached integrity flag, or an evaluator label is insufficient
for independent acceptance. Referenced artifacts, checkpoints, and evaluator
bindings still need verification before an optimizer treats the record as
successful task evidence.

Read [configuration search](configuration-grid-search-and-optimization.md),
[configuration preferences](configuration-preferences-and-meta-selection.md),
and [self-improvement as a Practitioner task](../components/self-improvement/README.md)
for the owning interfaces. No part of this guide asserts autonomous recursive
self-improvement, broad task success, or an achieved artificial general
intelligence system.

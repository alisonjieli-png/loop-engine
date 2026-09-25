# Astra comments and suggestions for continued development

This is the owner's advisory development note. The current task,
[AGENTS.md](AGENTS.md), the [Constitution](docs/architecture/CONSTITUTION.md),
and typed contracts govern the work. Advice here grants no authority of its
own. The owner's standing rules for committing, pushing, branching and
releasing, and what still needs the owner, are in the
[commit, push and release authority](AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md. Model, network, file, spending and publication authority
comes from that section, never from this note. A current task may narrow that
authority, and only the owner widens it.

## Current work and evidence

The [September 25 session handoff](docs/context/SESSION-HANDOFF-2026-09-25.md)
is the newest dated record of what is live, what the owner asked for, what is
in flight and what remains. The
[September 23 session handoff](docs/context/SESSION-HANDOFF-2026-09-23.md),
the [September 22 session handoff](docs/context/SESSION-HANDOFF-2026-09-22.md)
and the dated records below are earlier snapshots.

The [September 20 checkpoint](docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md)
records the deployed pilot, benefit-led website, administrator access,
recovery exercise and remaining release work. It is a snapshot, not new
authority or a replacement for the roadmap.

The [Fable 5.1 takeover handoff](docs/context/FABLE-5-1-HANDOFF-2026-09-20.md)
records the deployed pilot, simpler public copy and account code whose live
customer integration remains incomplete.
The [takeover checkpoint](docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md)
records the state verified afterwards, the repairs, the private beta
definition and the working cycle. The roadmap's delivery packages carry
explicit code owners, verification levels, negative controls and rollback
procedures, plus evidence requirements for overnight local-model work, token
efficiency and useful expertise. Count them in the roadmap, not in a note that
can go stale. Public pages use Baltor and each step; technical documents
retain exact runtime definitions.

Start with the [continuation plan](docs/roadmap/CONTINUATION-AND-LAUNCH.md),
its [generated status](docs/roadmap/CONTINUATION-STATUS.md), and the
[client and server map](docs/architecture/MVP-CLIENT-SERVER.md).
The product target is a subscription website, dashboard, payments, and an
authenticated intelligence service. Customers run their harnesses. The
internal graph, assignment, intelligence, and verification paths remain
required work even when the first interface does not expose them.

The [architecture audit](artifacts/architecture-audit-2026-09-19/README.md)
records reproduced defects, repairs, source identities, and limits.
A diagram, imported module, passing fixture, or plan status does not prove a
complete product path. Check the exact source and evidence for the task.

No old provider window, worker queue, campaign allowance, or publication
instruction authorizes a new effect. Confirm present authority and exact
provider availability before a separately authorized live trial.

## Pre-launch version policy

The owner confirmed that Loop Engine has not launched and has no users
requiring its unpublished interfaces. Follow the
[accepted version policy](docs/architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md):
remove accidental readers and aliases for unpublished formats with their
callers. Independently deployed component releases still need runtime
version, capability, and schema negotiation. Select an explicitly supported
implementation shared by caller and provider. Do not silently downgrade
security or authority. Continuous integration verifies negotiation behavior;
it does not replace negotiation at runtime.

This policy is not a claim that every removal is complete. The
[record compatibility guide](docs/components/loop-object/RECORD-COMPATIBILITY.md)
separates current contracts from remaining older readers. Preserve original
historical bytes; do not make them active inputs automatically.

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

## Runtime classification

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

## Owner requirements to preserve

| Requirement | Complete owning document |
|---|---|
| Each configuration dimension has an initial choice and ordered fallback priorities. The inventory is a required baseline, not an exhaustive list or maximum. | [Configuration dimensions](docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md) |
| Add or remove steps, prompts, questions, intelligence, actions, and resource combinations according to the task and evidence. Minimal step count or model use is not a universal objective. | [Flexible composition](docs/architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md) |
| Wrapper depth, order, native controls, retry ownership, cancellation, and cumulative authority are separate choices. Native completion cannot accept its own result. | [Layered harness wrappers and native control](docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) |
| Persist within declared authority and classify failures before repair. Preserve useful provisional work, assumptions, questions, and exact blockers without claiming the requested outcome was verified. | [Persistent general solving](docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md) and [public solve contracts](docs/contracts/README.md) |
| Distinguish model response completion, observed process, action output, task outcome, independent acceptance, and safe remaining work. | [Action and outcome vector contracts](docs/contracts/README.md) |
| Keep candidate generation, selection, materialization, execution, evaluation, acceptance, and independent promotion separate. Self-improvement is a Practitioner task. | [Reusable capability admission](docs/components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md) and [self-improvement](docs/components/self-improvement/README.md) |
| Keep the entire task catalogue eligible for admission. Large configuration spaces and adaptive proposal methods do not prove that all configurations ran. Preserve exact populations, failures, exclusions, accounting, and holdouts. | [Configuration search](docs/guides/configuration-grid-search-and-optimization.md) |
| Source-backed model capacity, exact authority, physical call identity, and unknown usage or cost remain distinct. Never replace a failed model call with invented output. | [Model gateway](docs/components/core-architecture/MODEL-GATEWAY.md) and [AGENTS.md](AGENTS.md) |
| Telemetry needs explicit settings and privacy choices. The proposed baseline records metadata only. Raw inputs and outputs require explicit opt-in; credentials are never telemetry. | [Continuation plan](docs/roadmap/CONTINUATION-AND-LAUNCH.md) |
| Imported ideas must fill a verified gap at an existing Loop Engine boundary. Do not copy another repository's authority system or treat its results as local qualification. | [Reference-source boundaries](docs/context/REFERENCE-SOURCES.md) |

Read the linked requirement before changing its behavior. These links preserve
the full owner constraints; the table does not replace them.

## Review and verification

Preserve concurrent work and resolve ownership before editing overlapping
files. Commit and push reviewed work as the
[commit, push and release authority](AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md says. Use only owned process handles for cleanup. Do not
alter historical reports, private session logs, benchmark evidence, managed
records, or failure baselines to make a check pass.

Start with the smallest relevant check, then owning and dependent checks.
Use a known-wrong case to show that a new guard rejects the missing behavior.
Run full source, conformance, clean-installation, example, and browser checks
when the claim requires them. Report observed, inferred, missing, and disputed
facts separately.

The [preserved advisory snapshot](docs/evidence/context-route-snapshot-2026-09-19/ASTRA.md.txt)
retains the previous dated commentary without making it startup instructions.
The [records index](docs/RECORDS-INDEX.md) is the route to historical evidence.

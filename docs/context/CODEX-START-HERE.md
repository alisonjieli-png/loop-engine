# Coding-agent context route

This is the stable entrypoint for Codex and other coding agents after a new or
compacted session. Read [START-HERE.md](START-HERE.md) and
[AGENTS.md](../../AGENTS.md). The current task determines authority and scope.
No standing instruction here authorizes a commit, push, live trial, or
publication.

Remove accidental compatibility for unpublished old formats. Keep runtime
version, capability, and schema negotiation for independently deployed
components. Select a mutually supported implementation explicitly; never
silently downgrade security or authority. Continuous integration verifies
that behavior and does not replace the runtime handshake.

## Reading order

| Need | Current route |
|---|---|
| Verified live state, repairs, open findings, the private beta definition and the working cycle | [Takeover checkpoint](TAKEOVER-CHECKPOINT-2026-09-20.md). Start here after [AGENTS.md](../../AGENTS.md). |
| What runs and where, and where each name may appear | [Current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment) and the table [Names and where they may appear](../guides/product-style-guide.md#names-and-where-they-may-appear). Baltor is the public brand. Loop Engine is the repository, the Python package and the technical name. |
| Product priorities, open decisions, and release gates | [Continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md) and [generated status](../roadmap/CONTINUATION-STATUS.md) |
| Delivery, exact checks, owner actions and handoff of the previous developer session | [September 20 checkpoint](DEVELOPMENT-CHECKPOINT-2026-09-20.md), a dated snapshot that is also embedded in the main development HTML. Recheck the live source and deployment before continuing. |
| Claude Code takeover and broader delivery plan | [Fable 5.1 handoff](FABLE-5-1-HANDOFF-2026-09-20.md), with existing owning boundaries, prepared access and launch-benefit evidence requirements. |
| Owner setup and the saved Baltor Fly credential reference | [Launch setup runbook](../guides/launch-setup-runbook.md#prepared-fly-access-on-the-development-workstation). The token stays in the workstation's system keyring, not this repository. |
| Client/server ownership and observed integration limits | [Client and server map](../architecture/MVP-CLIENT-SERVER.md) and [architecture audit](../../artifacts/architecture-audit-2026-09-19/README.md) |
| Stable architecture and versions | [Constitution](../architecture/CONSTITUTION.md), [architecture.yaml](../../architecture.yaml), [terminology.yaml](../../terminology.yaml), and [pre-launch version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md) |
| Exact contract and implementation | [Contract index](../contracts/README.md), [component map](../components/README.md), and the owning source and checks |
| Owner constraints on atomic assignments | [Complete behavioral explanation](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md) and [complete dimensions](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md). The dimension inventory is a required baseline, not an exhaustive list: read the [dimension discovery addendum](CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md) for proposed refinements, additional choices and ongoing review questions. |
| Composition, experiments, and native harness controls | [Flexible composition](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md), [configuration search](../guides/configuration-grid-search-and-optimization.md), and [layered wrappers](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) |
| Persistent solving and failure review | [Persistent general solving decision](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md) |
| Managed notes and scoped record writes | [Queryable records and storage](../guides/queryable-records-and-storage.md) |
| Advisory development criteria | [ASTRA.md](../../ASTRA.md) |
| Dated evidence or older repository ideas | [Records index](../RECORDS-INDEX.md) and [reference-source boundaries](REFERENCE-SOURCES.md) |

Read each owner requirement in full before changing the behavior it governs.
Do not replace the complete phrase or explanation of a discrete cognitive or
act step Loop node with an abbreviated label.

## Working-directory check

```bash
pwd
git rev-parse --show-toplevel
git remote get-url origin
git branch --show-current
git rev-parse HEAD
git status --short --branch
git diff --name-status
git ls-files --others --exclude-standard
git worktree list --porcelain
ps -eo pid=,ppid=,etime=,stat=,comm=
```

The repository is `/home/username/loop-engine`. Process names, timestamps,
and shared directories do not establish ownership. Resolve overlapping work
with its owner. Preserve dirty paths you do not own.

## Verification and handoff

Run the smallest relevant test, then owning and dependent checks.
Use the [current continuous-integration workflow](../../.github/workflows/ci.yml)
for full source, conformance, packaging, example, documentation, and link
checks. Retain failed and excluded attempts. A known-wrong control must fail
when a required guard is removed.

Bind evidence to the exact source and state what it proves. Distinguish
static reachability, observed invocation, a local fixture, a real protocol
session, a live provider result, and an independently evaluated task.
Unknown calls, tokens, costs, commit outcomes, and deployment status remain
unknown.

A generated [session handoff packet](../contracts/session-handoff.schema.json)
can carry volatile checkout and test facts. Verify its source and worktree
identity before use; do not invent ownership or hand-write a supposedly
generated packet. If no fresh packet exists, inspect the checkout.

For broad development, the [single continuation brief](../prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md)
is optional task guidance. Its older suggested sequence does not override
the current task or continuation plan. Do not concatenate historical prompts.

## What not to load automatically

Do not load model-specific readiness notes, old provider quota windows,
campaign launch instructions, private session logs, copied constitutions,
or the prompt archive as startup context. Dated evidence stays available
through its relevant component and the records index.

The [preserved orientation snapshot](../evidence/context-route-snapshot-2026-09-19/docs__context__CODEX-START-HERE.md.txt)
retains the previous session history without presenting it as current work.

# Start here

Read the current task and [AGENTS.md](../../AGENTS.md) before acting.
Inspect the branch, revision, dirty paths, active processes, and known writers.
Preserve work whose ownership is unresolved. A historical instruction does
not authorize a commit, push, provider call, deployment, or repeated effect.

## Current context route

Start with the [takeover checkpoint](TAKEOVER-CHECKPOINT-2026-09-20.md). It
records the verified live state, the repairs of September 20, the open
findings, the private beta definition and the working cycle for changes,
tests, checkpoints and releases.

The [September 20 development checkpoint](DEVELOPMENT-CHECKPOINT-2026-09-20.md)
and the [Fable 5.1 handoff](FABLE-5-1-HANDOFF-2026-09-20.md) remain valid as
dated snapshots of the previous developer session. The development checkpoint
records the pilot, website direction, evidence, remaining work and handoff at
that time. It is also embedded in the single development HTML. Recheck source
and deployment facts before acting.

The [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section is the current statement of what runs and where. Follow that section
when another document differs from it. Baltor is the public brand, and Loop
Engine is the repository, the Python package and the technical name.
[terminology.yaml](../../terminology.yaml) is the single structured source for
every term and where it may appear, and
[the developer language guide](../guides/developer-language.md) explains how
to read it.

1. Read the [continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md) and its
   [generated status](../roadmap/CONTINUATION-STATUS.md). These separate the
   product target, completed evidence, remaining work, and owner decisions.
2. Use the [client and server map](../architecture/MVP-CLIENT-SERVER.md) and
   [architecture audit](../../artifacts/architecture-audit-2026-09-19/README.md)
   to locate the task boundary. A map is not proof of runtime behavior.
3. Follow the [Constitution](../architecture/CONSTITUTION.md),
   [pre-launch version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md),
   [contract index](../contracts/README.md), and
   [relevant component guide](../components/README.md).
4. Use the [coding-agent route](CODEX-START-HERE.md) for scoped checks and
   evidence handling. Load dated reports only when they answer the active
   question.

The owner requires the complete phrase and explanation of a
[discrete cognitive or act step Loop node](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
Read it in full. Configuration work must also preserve the
[complete initial and fallback dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
[flexible composition direction](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md),
and [layered harness controls](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
These are active owner requirements, not optional historical context.

## Version and evidence rules

Loop Engine has not launched. Remove accidental support for unpublished old
shapes. Preserve runtime version, capability, and schema negotiation between
independently deployed releases. Select only explicitly supported combinations
without weakening authority or security. Continuous integration tests this
logic but does not replace runtime negotiation.

Preserve historical records without turning them into runtime input.
Reader removal is still incomplete at some boundaries. The
[compatibility guide](../components/loop-object/RECORD-COMPATIBILITY.md)
records that distinction.

A passing check applies to its source snapshot and tested behavior. State
the denominator, skipped or untested cases, failures, source identity, and
limits. Local checks do not establish hosted deployment, live model quality,
independent qualification of every intelligence item, or release readiness.

## Safe local checks

Run the owning component's smallest checks before the full suite. Confirm the
repository environment exists before using these commands:

```bash
git status --short --branch
git rev-parse HEAD
git worktree list --porcelain
ps -eo pid=,ppid=,etime=,stat=,comm=

PYTHONPATH=src .venv/bin/python -m loop_engine --self-test
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src .venv/bin/python -m loop_engine --repo-conformance --format json
```

Use the [continuous-integration workflow](../../.github/workflows/ci.yml) for
the full current command scope. A clean installation uses a fresh distribution
outside the source import path. Inspect only owned processes and paths when
cleaning up a check.

## Historical material

The [records index](../RECORDS-INDEX.md) lists dated evidence.
The [preserved entrypoint snapshot](../evidence/context-route-snapshot-2026-09-19/docs__context__START-HERE.md.txt)
retains the previous instructions for review, not execution.
[Reference-source boundaries](REFERENCE-SOURCES.md) govern any older or
separate repository. Do not load old campaigns, prompts, or provider-readiness
notes merely because they mention the model running this session.

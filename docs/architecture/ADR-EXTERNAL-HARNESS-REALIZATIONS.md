# External harnesses as optional Loop realizations

Date: 2026-09-04. Status: implemented offline; live qualification remains open.

## Decision

Extend the existing `HarnessRegistry` and `run_external_harness` boundary.
The host supplies an adapter object with an exact version and typed mechanics
declaration. Identifiers remain open-ended but never trigger imports, package
installation, permissions, or domain routes. Each invocation belongs to one
canonical Loop with the requested exact Practitioner profile.

Requests declare required mechanics, acceptable isolation, and any required
preemptive limits. Contract effects and supplied tool, skill, context, workspace,
approval, and route references add requirements. Missing support causes refusal
before the adapter runs. An adapter declaration is not independent evidence
that a sandbox, approval bridge, or budget controller works.

Inputs are owned plain-data snapshots. Large or reusable bodies keep their
existing artifact/reference path. Outputs remain candidates, are captured by
the existing artifact manager, and cannot mutate the producer through a shared
object. The Loop retains task authority, verification, and history ownership.
Full classification and integration rules remain in the
[component guide](../components/core-architecture/MCP-AND-SKILLS.md#external-harness-boundary)
and `architecture.yaml`; this decision creates no second runtime or authority.

## Alternatives and consequences

A fixed harness-name whitelist would require core changes for every new
adapter. Arbitrary dynamic imports from a model-supplied name would instead
grant code execution during discovery. Explicit host registration avoids both
conditions, but the host remains responsible for reviewing adapter code.

Using a full coding harness for every small task would add tool, context, and
subagent semantics even where one bounded model call or verified transform is
sufficient. The owning Practitioner should choose a realization for the task;
the deterministic boundary only checks compatibility and authority mechanics.

The existing OpenCode raw-host path cannot reconcile native configuration and
automatic approvals with Loop Engine effects. It is quarantined, including its
deprecated direct client. Import compatibility and offline event parsing remain;
execution requires a future qualified implementation. OpenCode provider APIs
are a separate concern and are unchanged.

`HarnessBudget` is explicitly a post-run acceptance contract. Hard prevention
requires declared preemptive controls and a qualification test. This decision
does not prove that legacy callers prevent spending overruns. No full coding
harness is enabled by this change and no task-quality benefit is established.

The [verification report](../verification/HARNESS-AND-MEMORY-HARDENING-2026-09-04.md)
records ownership, refusal, memory integrity, test failures, and remaining work.

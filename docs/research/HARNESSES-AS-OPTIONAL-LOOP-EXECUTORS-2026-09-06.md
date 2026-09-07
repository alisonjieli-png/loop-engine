# Harnesses as optional Loop executors

Loop Engine can use a coding harness for a bounded responsibility while keeping
its own runtime, authority, verification, and records. The current experiment
adds a read-only OpenCode instance builder and a ModelGateway bridge in
[`examples/25_host_runtime/`](../../examples/25_host_runtime/). Native execution
remains the default. This is a source-checkout experiment, not a replacement
for `solve_task`, a fourth run mode, or a production OpenCode qualification.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Exact versioned role profile
    ├── Purpose and domain categories
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile and typed input/output contract
    ├── Loop and exit conditions
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when authorized
    └── Run History

Optional physical execution choice inside a governed responsibility
├── Existing native implementation
├── Explicitly configured harness adapter
│   ├── Pinned core resources and policy
│   ├── Selected step resources
│   └── Fresh isolated instance
└── Unavailable result when the required adapter is not qualified
```

## One core bundle, different step inputs

`CoreBundle` holds an exact version and digest, required resources, permitted
tools, and a hydration ceiling. A separate host-issued `InstanceGrant` names
the optional resources, tool rights, and hydration allowance for one activation
and step. New task context therefore does not require changing the core.
`InstanceSelection` names the activation, step, selected references, tools,
and decision evidence. The compiler checks descriptors before loading bodies.
It refuses changed core or grant identity, wrong grant scope, path collisions, undeclared resources,
expanded tool authority, and changed artifact bytes.

Core immutability means that a running instance cannot rewrite its pinned
bundle. A deliberate core update creates a new reviewed version. It does not
mean prompts guarantee obedience. Effects and acceptance remain outside the
model, and the container keeps staged files read-only.

The model-led selector receives small cards with IDs, versions, kinds, and
descriptions. It returns compact IDs, which the host binds to exact references.
Empty selection is valid. The model does not calculate digests, choose paths,
change the core, or grant permissions. No keyword rule routes a task to a skill.

These descriptors should come from the existing `SkillRegistry`,
`SkillDiscoveryProjection`, `CatalogStore`, and Intelligence queries. The
prototype consumes a host-supplied bounded catalog; it does not install a
second registry. Persistent skill use still requires the existing admission
process. A successful experiment does not promote its resources.

## Loading and exposure

Make essential policy and the active contract part of the core context. Keep
large procedures, examples, and data behind references until selected.
OpenCode discovers skill descriptions and loads instructions when its skill
tool is invoked. A listed skill is not evidence of a successful load.
[OpenCode skills](https://opencode.ai/docs/skills/).

Record the selected references, actual tool outcomes, exact model-visible
packets, provider calls, and final artifact identity. The experiment found a
real OpenCode run that exited successfully while both skill calls failed.
The qualification check therefore requires successful calls and subsequent
request exposure, not just a process exit or an assistant's description.

Keep runtime caches separate from immutable resources. OpenCode startup tried
to create `.opencode/.gitignore` on the read-only mount; staging the expected
metadata resolved that failure. Skill discovery also required a compatible
`rg` binary. The corrected image uses a pinned portable binary instead of
relaxing the read-only mount or temporary-filesystem execution policy.

## Model and transport boundary

The experimental bridge runs OpenCode with no container network, no inherited
personal configuration, and no host credentials. A local endpoint exchanges
framed messages over stdin/stdout with the host's `ModelExecution`. All real
provider calls therefore retain ModelGateway routing, output-capacity checks,
usage accounting, and Loop ownership.

The configured text-only gateway interface cannot be presented as native
provider tool calling. This profile explicitly translates structured text
into tool messages. A closed JSON envelope is preferred. An observed
`tool_calls` XML envelope is accepted only for declared tools and supported
scalar parameter types, then passes the same argument and scope validation.
DTD declarations, unknown tools, duplicate parameters, nested values, and
arbitrary prose are refused. This translation is an experimental variable in
any comparison.

Both the harness's requested output allowance and the gateway's source-backed
capacity remain visible. Missing provider usage is not inferred from zeros
that a harness displays. The gateway records supply accounting authority.
The raw-host `OpenCodeProcessAdapter` remains quarantined.

## Process size and lifetime

Do not start a full harness for every helper call. Use a fresh instance where
a responsibility needs separate context, authority, verification, or retry
identity. Compare per-activation and per-step placement. A warm executable or
dependency cache may reduce startup cost, but must not silently share a
conversation, credentials, or working state.

Current scope is read and skill use inside a confined instance. General write
tools, MCP effects, arbitrary plugin combinations, pooling, and resumable
cross-step sessions need separate qualification. Supervision checks between
bridge frames do not preempt a provider call already in flight. The existing
provider timeout still applies. Do not advertise stronger cancellation.

## Alternatives worth comparing

| Candidate | Relevant mechanism | Qualification question |
|---|---|---|
| OpenCode | Headless runs, skills, plugins, and tool events | Can each selected resource and effect be accounted for without ambient configuration? |
| Kilo CLI | OpenCode-derived CLI and related configuration | Which upstream assumptions still hold for the exact fork version? |
| Pi | Small coding harness, extensions, JSON/RPC modes, and SDK embedding | Can host controls contain extensions and preserve exact tool and model accounting? |
| Goose | CLI/API, MCP extensions, and configurable distributions | Can recipes and extensions be frozen as capabilities without duplicating Loop orchestration? |
| OpenHands SDK | Agent settings, skills, conversations, and separate workspaces | Can a bounded conversation use the local execution and verification policy without importing another top-level runtime? |

Kilo documents its OpenCode lineage and different configuration locations.
Fork ancestry does not establish adapter equivalence.
[Kilo CLI](https://github.com/Kilo-Org/kilocode/blob/7de8f5b87d222cbd82516cbdb10405d49a2ba17b/packages/kilo-docs/pages/code-with-ai/platforms/cli.md).

Pi supports extensions, skills, prompt templates, and process or SDK
integration. Its documentation explicitly requires external containment when
filesystem, process, network, or credential restrictions are needed.
[Pi coding agent](https://github.com/earendil-works/pi/blob/9767ba275f3e9a5ee0f5c5342249b629ab1b2282/packages/coding-agent/README.md),
[Pi containment](https://github.com/earendil-works/pi/blob/9767ba275f3e9a5ee0f5c5342249b629ab1b2282/README.md#permissions--containerization).

Goose provides CLI/API access and MCP extensions. Its custom-distribution
surface is relevant to preconfigured instances; it is not evidence that a
Loop Engine adapter already works.
[Goose](https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/README.md).

OpenHands separates serialized agent settings from conversation and workspace
execution. Its skill guide distinguishes always-loaded context, triggered
context, and progressive disclosure. Those are useful comparison dimensions,
not reasons to replace Loop Engine's memory authority.
[Agent settings](https://docs.openhands.dev/sdk/guides/agent-settings),
[Skills and context](https://docs.openhands.dev/sdk/guides/skill).
The inspected SDK reference is `8ea8e3bc1d5e84542f7702b8813734ef600c9fce`.

Only OpenCode was executed in this experiment. The other rows are research
candidates. Pi, Goose, and Kilo were not found on the inspected command path.

## Comparison and export gates

First compare the same task, provider/model, available information, allowed
effects, and independent evaluator. Freeze every arm before outcomes and
retain failed or unavailable attempts. Measure startup, model calls, tokens,
tool failures, repair, elapsed time, and incorrect acceptance.

A richer OpenCode skill bundle against an unassisted native solver is a
bundled-configuration comparison, not an isolated harness effect. The same
applies to the current text-to-tool-message bridge. Label these differences.
One successful instance proves a working path, not general improvement.

Export independently checked source, dependencies, tests, usage instructions,
and source/verification digests. Do not export a hidden conversation as the
only way to reproduce a solution. Managed experiment state uses
`RecordOperationService`; generated JSON views come from exact revisions
through the [record exporter](../../examples/24_managed_records/README.md#export-an-exact-json-view).
The [TrafficFlowBench plan](../benchmarks/TRAFFICFLOWBENCH-NATIVE-OPENCODE-PLAN.md)
keeps its partial local scoring distinct from the official composite.

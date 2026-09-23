# Container and engine composition research

Kind: dated architecture research and proposed comparisons. Reviewed
September 22, 2026 against main `9cdf99e`. The
[configuration dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
[layered wrapper direction](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md),
[current engine architecture](../architecture/ENGINES-BEHIND-FIXED-EDGES.md)
and [roadmap](../roadmap/roadmap.yaml) remain authoritative for their own
subjects. This report proposes no new runtime type, default sandbox, cloud
spend or model experiment. Performance figures from outside projects are
author claims until reproduced on a matched Loop Engine task.

## Complete classification before the specialized design

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

The default separate harness process for each focused step remains a design
choice inside the canonical Loop. A process, container, micro virtual
machine, warm dependency image, wrapper, tool broker or model strategy is an
implementation mechanic under a fixed typed edge. None is another
executable graph vertex.

## Separate compartments before choosing an engine

The key optimization opportunity is to **reuse clean expensive setup while
discarding old cognitive and secret state**. Freshness and isolation are not
one Boolean. A compiled step configuration should make these axes explicit:

| Axis and existing owner | Initial choice to test | Alternative and refusal condition |
|---|---|---|
| Cognitive context, `harness_implementation_and_process_initialization` | New native process and transcript containing only the selected step material. | Native fresh-context subagent or persistent session is a measured comparison arm, not a substitute for a required fresh process. No prior transcript may leak into the default. |
| Isolation substrate, `workspace_and_execution_environment` | Existing Bubblewrap confinement for a supported text-only harness. | Qualified container, micro virtual machine or remote sandbox only if exact tools, network, resource limits, cancellation and artifacts can be enforced. A failure never falls back to raw host. |
| Task files and cache, workspace/state continuity | New writable step view; approved materials and pinned dependencies are read-only. | A shared cache or clean warm image may be reused by content digest if it holds no task input, secret or writable cross-step state. A live process snapshot is a different state-continuity profile. |
| Model endpoint, provider and route | Parent-side route and model broker; the step's harness process sees a local relay. | Another route requires its own capacity, recipient and spending authority. The model server may persist while each harness process is fresh. |
| Credential and tool lifetime, S-6.8 and S-6.61 | Host-held credential, step-bound lease and exact tool grants. | Native direct credential delivery is an explicit weaker profile; a process with its real key and unrestricted egress cannot claim parent-enforced spending. |
| Resource envelope, local resource and instance reservation | Reserve process, memory, disk and time before start and reconcile at stop. | A warmer or denser placement is eligible only after isolation and cumulative accounting are proved. |
| Evidence and checkpoint fidelity, Run History and hibernation | Preserve exact input/output references and effect outcomes separately from private launch-control files. | A resume or snapshot must name state carried, state discarded and effects still uncertain. Never treat process survival or a restored cache as task acceptance. |

The `HarnessProcessSpec` already digests installed software and validates it
again at launch. Recursive rehashing may be a startup cost for a large
installation; measure it before caching validation and bind any cache to
the exact file tree and revision. One compiled, versioned step manifest could
link the selected harness binary, clean image, workspace view, model route,
credential grants, tool facade and evidence policy through existing
artifacts and Run History. It would be a typed record, not a second plan or
new authority source. A fallback must re-check all of these, not merely
change a harness name.

## What executes now and what does not

| Existing piece | Verified scope and gap |
|---|---|
| [Confined harness process](../../src/loop_engine/core/harness_process.py) | Bubblewrap uses `--unshare-all`, clears the environment, mounts selected read-only software and one Unix model relay, and bounds wall time and captured output. The [gateway adapter](../../src/loop_engine/core/harness_semantic.py) reports native tools disabled and `instruction_loading_observed: False`. The launch path does not impose process memory, process-count or writable-disk quotas. |
| [Docker workspace](../../src/loop_engine/core/workspace_optional.py) | An effect-gated command backend with image and resource controls. It is not wired as the native harness executor; its memory and process limits do not automatically cover Bubblewrap harness launches. |
| [Credential leases](../../src/loop_engine/core/credential_leases.py), [resource ledger](../../src/loop_engine/core/local_resources.py) and [reservations](../../src/loop_engine/core/instance_hibernation.py) | These have offline checks, but ordinary harness launch does not bind them atomically to one process lifetime. S-6.8 owns that integration. |
| [Wrapper composition](../../src/loop_engine/core/harness_layering.py) | Records are typed and digestible. The [availability boundary](../../src/loop_engine/core/harness_layering_availability.py) refuses nonempty wrapper/native-control composition today. A drawn wrapper stack is not running behavior. |
| [Brokered container embodiment](../../embodiments/brokered_container/README.md) | Planned and returns typed unavailable. A container diagram does not prove one native harness per step. |
| [Private launch files](../verification/CONFINED-HARNESS-PRIVATE-LAUNCH-RETENTION-2026-09-22.md) | A bounded fixture found `task.txt` and `config.json` retained after a successful run. Whether to keep, expire or remove these bytes needs an explicit retention/resume rule; preserving task outputs is a separate obligation. |

## Candidate execution placements

| Placement | What it might improve | Cost or eligibility question before use |
|---|---|---|
| Fresh Bubblewrap process | Existing baseline with a clean environment and parent model relay. | Measure complete startup, software rehash, memory/disk, subprocess limits and actual instruction loading. |
| Fresh process in a pinned container image | Portable dependencies and operating-system resource controls. | Prove an exact image digest, new writable view, correct local endpoint reachability, no inherited tenant cache/keys, socket binding and process-tree cancellation. Compare total boot and image storage. |
| Clean prewarmed image or worker that launches a new harness process | Reuse runtime/dependency initialization without retaining prior transcript. | Inspect every inherited file descriptor, cache, model session, secret and writable path. A warm image with customer state fails the fresh profile. |
| Shared trust-group worker | Reduce per-process overhead across low-risk tasks. | A shared process changes isolation. Verify trust grouping, typed tenant scope and no cross-step canary leakage before comparing cost. |
| [forkd](https://github.com/deeplethe/forkd) micro virtual machine snapshot | Branch a live state or start from an immutable prepared image. | Its author-reported 56-millisecond pause is not full harness startup; Linux/KVM and a modified Firecracker are prerequisites. A live branch carries cognitive and writable state, so separate it from clean-image experiments. |
| [Kubernetes Agent Sandbox](https://github.com/kubernetes-sigs/agent-sandbox) | Later warm-pool and claim lifecycle for cluster execution. | Its controller relies on the configured RuntimeClass; identity/network policy at claim time and total cloud cost need qualification. Local invited beta does not need a cluster. |
| [Ephemora Cell](https://github.com/MichaelS1011/ephemora-cell) WebAssembly | Bounded execution of a narrow generated tool or deterministic component. | Test parity, filesystem/network denial, fuel, memory, cancellation and outputs under the workspace or plugin edge. It is not a drop-in native Python or Node coding harness. |
| [HarnessRouter Community Edition](https://github.com/HarnessRouter/harnessrouter) or Cloud | An external product-facing harness interface and hosted task sandbox. | Self-hosted sessions share one container but have separate operating-system users/workspaces; Cloud advertises a sandbox per product task. Neither proves a new process per internal focused step. Its [draft protocol](https://unifiedharnessprotocol.org/) can be compared with Agent Client Protocol as another adapter, with Loop authority and acceptance retained. |

The D-07-T04 roadmap case already requests a comparison of fresh processes,
warm workers and shared trust-group sandboxes. Add exact container and
micro virtual machine candidates only when the same pinned harness and task
can run in each. WebAssembly belongs in a different comparison because it
cannot execute the same general native harness workload.

## Engine layers without duplicated authority

```text
Owning Loop: exact task, contracts, budget, permissions and Run History
├── Step executor edge: eligible native harness implementation and launch
│   ├── Process or container placement engine
│   └── Exact workspace, state and cancellation binding
├── Intelligence search and materialization edge
│   └── Selected, approved source bytes and model-compatible rendering
├── Model-call strategy edge, then ModelGateway physical call edge
│   └── Parent-owned endpoint and cumulative usage
├── Customer-side credential and tool bridge
│   └── Exact per-step capabilities and effect approval
└── Independent evaluator and acceptance
```

Engine selection should first refuse an implementation that lacks required
isolation, protocol, tool control, source-backed model capacity, budget or
effect enforcement. Only eligible engines can be ranked by accepted-task
evidence, complete cost and latency. Wrapper order and native controls are
independent configuration dimensions. A preference from a harness or Loop
cannot broaden its host's grants. A cheaper but weaker sandbox is not a
fallback for a task that requires confinement. Existing
[engine architecture](../architecture/ENGINES-BEHIND-FIXED-EDGES.md)
defines fixed edges; this report identifies experiment variables, not a new
framework.

## A discriminating, bounded experiment

Freeze a task population before choosing a placement. Use the same pinned
native harness, model route, selected intelligence manifest, evaluator and
effect policy. Compare fresh Bubblewrap, fresh container, clean prewarmed
image and, only if eligible, micro virtual machine placements. Record:

1. Accepted, rejected and inconclusive tasks with exact denominator and
   independent evaluator.
2. Cold and warm startup distribution, full elapsed time, software-hash
   time, cache reads/writes, all physical model calls, tokens and known or
   unknown cost.
3. Peak resident memory, writable disk, image/cache size, process count and
   concurrent admission, including the losing attempt of a reservation race.
4. Prompt, instruction, workspace, socket and credential canaries across
   sibling steps and tenants; false and true refusals of file/network/tool
   effects.
5. Cancellation, timeout, unknown provider completion, private launch-file
   retention and restart with named checkpoint fidelity.

Run hard isolation controls before comparing efficiency. A baseline that
cannot execute the same task or that leaks a prior step's bytes is ineligible,
not simply slower or faster. Preserve failed attempts next to successful
ones. Live provider calls or new cloud machines require separate owner
authority. S-6.31 and S-6.8 own first integration; D-07-T04 owns the
placement comparison; D-13 owns confinement; S-6.61 owns customer-side
credential and tool access.

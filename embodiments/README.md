# Loop Engine execution experiments

Current harness integration work belongs in `/home/username/loop-engine/embodiments`.
Dependencies, trial workspaces and reports for this work stay inside
`/home/username/loop-engine`. Start with
[the harness guide](/home/username/loop-engine/embodiments/HARNESS-GUIDE.md).

These are Loop Engine-specific execution experiments. Their launchers share the canonical runtime and lab evaluator. They are not independent codebases.

Read [the harness development instructions](AGENTS.md) and the main advisory
comments in [ASTRA.md](../ASTRA.md). [CLAUDE.md](CLAUDE.md) imports the scoped
instructions for Claude Code. The
[layered harness design](../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
allows an outer Loop to supervise native harness iteration, with wrapper
composition and native controls treated as separate dimensions.

The sibling `/home/username/solver-lab` contains older separately owned
experiments. It remains a read-only reference for this work, not the destination
for new Loop Engine implementations or logs. Those older repositories stay in place.

This directory preserves the earlier local experiments, manifests and results. There is no default winning design.

The source mirrors preserve related projects independently. They are local working copies under `embodiments/mirrors/`, kept out of the repository so that another project's source is never redistributed here; read them on the machine that made them, or clone each project from its own home. The [remix plans](remixes/README.md) combine specific proven mechanisms, and [controlled mutations](mutations/README.md) define experiments that change one axis at a time. [Speculative decoding](speculative_decoding/README.md) is a separate provider-side research direction.

The [related-catalog index](RELATED-CATALOGS.md) also connects Claude's 30 single-axis experiments and the newer whole-architecture catalogs, with their evidence limits and review corrections.

Read the [current build results](BUILD-RESULTS-2026-09-08.md) for the observed comparison, qualification and remaining limits.

The original mechanism study below has six runnable deterministic arrangements
and seven planned designs whose launchers refuse. The newer harness adapters
are a separate, explicitly selected integration through the public solve path.
A folder or successful protocol fixture is not evidence of real task success.
The catalog is extensible; “every possible architecture” is not a finite,
testable promise.

The common classification is:

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, Solution
    ├── Exact versioned role profile
    ├── Purpose and domain categories
    ├── Mode: deterministic, hybrid, non-deterministic
    ├── Ordered step profile
    ├── Typed input and output contract
    ├── Loop and exit conditions
    ├── Graph relationships
    ├── Budget, permissions and effect policy
    ├── Model settings when authorized
    └── Run History
```

| Folder | Current state | What varies |
|---|---|---|
| [native](native/) | Runnable mechanism | In-process execution |
| [process_per_step](process_per_step/) | Runnable mechanism | Fresh process for every packet |
| [long_lived_session](long_lived_session/) | Runnable mechanism | One persistent process, fresh explicit state |
| [session_pool](session_pool/) | Runnable mechanism | Bounded pool of persistent processes |
| [parallel_portfolio](parallel_portfolio/) | Runnable mechanism | Independent candidates, incremental verified portfolio |
| [durable_reactive](durable_reactive/) | Runnable mechanism | Persistent activations, leases and canonical history |
| [adaptive_tree](adaptive_tree/) | Planned, refuses execution | Split only after a verified failure |
| [reuse_first](reuse_first/) | Planned, refuses execution | Qualified capability resolution before generation |
| [opencode_per_step](opencode_per_step/) | Planned, refuses execution | Qualified tool-using harness per action |
| [brokered_container](brokered_container/) | Planned, refuses execution | Container execution and host-brokered model calls |
| [local_agent_host](local_agent_host/) | Planned, refuses execution | Local operator agent under host contracts |
| [transactional_semantic](transactional_semantic/) | Planned, refuses execution | Verified semantic interpretation and state commit |
| [speculative_decoding](speculative_decoding/) | Planned, refuses execution | Provider-side draft and target token verification |

## Run a comparison

Use new output directories; the tooling refuses overwrite. These commands make no provider calls.

```bash
export PYTHONPATH=src:devtools
python3 -m embodiment_lab create --out /absolute/new-study --count 1000 --seed 7301
python3 -m embodiment_lab qualify --study /absolute/new-study --out /absolute/qualification.json
python3 -m embodiment_lab compare --study /absolute/new-study --out /absolute/new-comparison --limit 12 --seconds 60 --concurrency 2
```

Run a single arrangement through its folder:

```bash
python3 embodiments/process_per_step/run.py run --study /absolute/new-study --out /absolute/new-process-run --limit 12
```

Each task has resource-bearing `task.json` and `contract.json`. The manifest binds task digests. The three workload families are sum, histogram and stable unique values. They deliberately qualify execution mechanics with independent positive/negative controls; they do not establish model reasoning, real-repository repair, or broad generalization. Larger/harder task adapters are a separate qualification, not a relabeling of these results.

Each run records the chosen variant, source identities, selected task IDs, time/concurrency grant, actual worker process IDs, packet and output identities, independent verdicts, failures, canonical Run History, and versioned portfolios. Read-only portfolio serving does not run a producer.

Read the current best, all verified candidates, a seeded random verified candidate, or an earlier portfolio version:

```bash
PYTHONPATH=src:devtools python3 -m embodiment_lab view --run /absolute/run --task /absolute/study/case-00000/task.json --view best
PYTHONPATH=src:devtools python3 -m embodiment_lab view --run /absolute/run --task /absolute/study/case-00000/task.json --view random --seed 7
```

Add `--version 1` for an as-of query. These queries never wake a producer or select an unverified candidate.

## Add another embodiment

Add a folder with a manifest, entry point, README and executable qualification cases. Register an exact implementation in the lab's catalog only when it exists. Record its status and failure behavior. Test import, actual invocation, and observable effects, including disabled/unavailable paths. Reuse the existing runtime, event vocabulary, stores, authority and profiles. Do not copy another repository's engine into the folder.

Independent axes include execution placement, decomposition, context transport, model policy, reuse, containment, scheduling/persistence, serving policy and optimization objective. A combination is admissible only when every selected component is compatible and qualified. Changing process placement does not grant network access or change mode.

Read [architecture](ARCHITECTURE.md), [the research review](../artifacts/review-2026-09-07/README.md), and [the lab implementation](../devtools/embodiment_lab/README.md).

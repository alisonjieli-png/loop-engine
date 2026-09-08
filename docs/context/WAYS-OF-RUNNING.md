# Ways of running

This page lists every way the engine can be run today, where each one is set,
and what it changes. It exists because the standing instruction is to add
configurations rather than replace them, and you cannot honor that without
knowing what already exists.

The organising rule: there is one runtime object, and everything below is a
field on it or a policy handed to it. None of these is a separate runtime, a
subclass, or a second executor. If a change would create one, it is the wrong
change.

## The settings on one Loop

Set on `LoopConfig` and the Loop's identity when the Loop is created.

| Setting | Values | What it changes |
|---|---|---|
| role | `practitioner`, `intelligence`, `solution` | what broad responsibility the Loop has |
| relationship | starting, spawned by, queried by, retrieved by, connected from | how the Loop entered the active structure |
| run mode | `deterministic`, `hybrid`, `non_deterministic` | how the Loop may resolve its work; they map to the execution modes `code_only`, `code_with_model_assistance`, `model_led` |
| step profile | `nine_step`, `five_step`, `custom`, `open` | which ordered steps it can run; `custom` takes an explicit tuple, `open` lets a chooser pick |
| exit condition | `steps_complete`, `accepted_success` | whether finishing the steps ends the Loop, or whether one accepted success is required |
| logical kind | `execution`, `task_semantic`, `search_improvement` | what kind of work the Loop represents |
| power | `light`, `standard`, `deep`, `max` | the intelligence pulled per step and the string budget |
| budget | `max_iterations`, `max_model_calls`, `max_depth` | explicit ceilings; unset means the supervision policy decides |
| supervision | `SupervisionPolicy` | the non-progress limits, the escalation ladder and the spawn depth guard |

`SupervisionPolicy` is the place to add a new limit. It currently carries
`identical_failures_before_stop`, `non_progress_passes_before_escalation`,
`unaccepted_passes_before_stop`, `escalation_ladder` and `spawn_depth_guard`,
and it is versioned, so a new field is a minor version and the default keeps
the previous behavior.

## The settings on one solve

Set on `SolveRequest`, which `solve_task` takes.

| Setting | Default | What it changes |
|---|---|---|
| `practitioner_mode` | `non_deterministic` | the run mode the solve asks for; without a model execution it is demoted to `deterministic` and the demotion is recorded |
| `interaction_mode` | `ask_when_material` | whether an unresolved material choice may ask a person, or the run proceeds autonomously |
| `max_passes` | none | the pass ceiling |
| `allow_network_reads` | false | whether the run may read the network |
| `allow_workspace_writes` | false | whether the run may write files |
| `allow_sandbox_commands` | false | whether the run may execute commands |
| `allow_local_execution` | false | whether host execution is permitted when Docker is absent; there is no operating system sandbox on that path |
| `allow_source_materialization_to_model` | false | whether the model may see supplied source |
| `runs_dir` | none | where Run History, the stage store and the learning journal live |
| `save_run_history` | true | whether the outcome is bound into Run History |
| `context_budget` | none | pins a context budget; unset lets the tuner pick from recorded experiments |
| `stage_assistance` | `shadow` | the experiment arm: `shadow` changes no model input, `advisory` supplies candidates, `fresh` carries none |
| `independent_verification_policy` | required | whether acceptance needs independent verification |
| `host_runtime` | none | a `HostRuntimeBinding`, which moves execution and verification to a host you write |
| `deterministic_resolvers` | none | exact resolvers tried before any model call |
| `reuse_observation_port` | none | where reuse opportunities are observed |
| `project_executor` | default | how a generated project is executed |
| `quiet_model_io` | false | whether model input and output are echoed |

Permissions are separate from modes on purpose. A mode never grants file,
network, secret, model, spending or external-effect authority.

## Where work physically runs

| Placement | How | Isolation |
|---|---|---|
| in process | the default | none; the Loop runs inside the calling process |
| a host runtime binding | `SolveRequest.host_runtime` | the host owns the operations, the verifier, the approvals and the completion gates; the model only calls registered operations |
| a Docker workspace | `DockerWorkspace` with a digest-pinned image | no network, read-only workspace, resource limits |
| a restricted local workspace | `RestrictedLocalWorkspace` | path confinement only |
| an OpenCode instance | the bridge under `examples/25_host_runtime/` | a container with no network, a read-only mount, dropped capabilities, and model calls brokered back over framed standard input and output |

The packaged raw OpenCode adapter is quarantined and refuses. Do not restore
its host path to make a smoke test pass. The working path is the bridge.

## Host completion gates

`HostRuntimeBinding` takes `completion_verifiers`, an optional frozen tuple.
After the primary verifier says a task is complete, every configured extra
gate must also pass through its own registered endpoint and its own exact
effect approval. A failure, unavailable evidence, changed state or a malformed
result all prevent completion, and no gate is selectable by the model. A
binding with no extra gates behaves exactly as before.

## Reactive activation

| Setting | Default | What it changes |
|---|---|---|
| profile persistence | per series | `ephemeral`, `checkpointed` or `durable_series`; a durable series refuses a handler binding that carries no history authority |
| `ReactiveHistoryPolicy` | not required | whether canonical Run History is saved and reopened before a success is published |
| `ReactiveWorkerHeartbeatPolicy` | none | when set, the worker renews its lease while the handler runs, and the outcome counts the renewals; without it the lease must outlast the handler |
| attempt policy | per series | attempts per trigger and active activations |

## What earlier runs contribute to a later one

Two projections run before the first model call, both advisory, both recorded
on the outcome under `intelligence.region_evidence`.

- Region evidence reads saved runs in the same task region and produces region
  statistics, a shortcut decision and a tuning decision.
- Learned memory reads the governed learning journal at `<runs_dir>/learning`
  and serves records that a producer staged, an independent reviewer approved
  and an authorizer promoted. Nothing self-promotes.

Because the journal sits beside the run history, several tasks that share one
runs directory share one journal. That is how a campaign accumulates.

## Campaign arms

`examples/25_host_runtime/novel_task_campaign_v2.py` prints its frozen plan
with no model calls and no file writes when run with no flags.

| Flag | What it changes |
|---|---|
| `--shared-runs-dir` | every task uses one Run History root, so the stage store, region evidence and learning journal are shared |
| `--passes N` | the whole population runs N times; the report groups calls, tokens, observations and region evidence per pass |
| `--evidence-out DIR` | the durable subset of each task's work root is copied out of the temporary filesystem |
| `--task` | an explicit subset |
| `--authorize-model-calls`, `--allow-source-to-model` | both are required for a live run, together with a work directory that does not exist |

## Environment

`LOOP_ENGINE_SANDBOX_IMAGE`, `LOOP_ENGINE_RUNS_DIR`, `LOOP_ENGINE_MEMORY_DIR`,
`LOOP_ENGINE_SETTINGS`, `LOOP_ENGINE_STAGE_STORE`, `LOOP_ENGINE_THINKING_POWER`,
`LOOP_ENGINE_LOOP_EFFORT`, `LOOP_ENGINE_DEFAULT_MODES`,
`LOOP_ENGINE_MODEL_ESCALATION`, `LOOP_ENGINE_SEARCH_MODE`,
`LOOP_ENGINE_LEXICAL_BACKEND`, `LOOP_ENGINE_VECTOR_BACKEND`,
`LOOP_ENGINE_EXTENSION_ROOTS`, `LOOP_ENGINE_PLUGIN_ROOTS`,
`LOOP_ENGINE_ENDPOINTS`, `LOOP_ENGINE_CONTEXT_CANDIDATES`,
`LOOP_ENGINE_LEARNED_ROOT`.

Provider credentials are referenced by variable name through settings and are
never written into source, events, reports or exported traces.

## How to add another way of running

1. Decide which boundary owns it. A limit belongs on `SupervisionPolicy`. A
   per-run choice belongs on `SolveRequest`. A placement belongs behind the
   host runtime binding or a workspace backend. An execution surface belongs
   behind an adapter. It never belongs in a new runtime type.
2. Make the existing behavior the default, so nothing changes for a caller who
   does not ask.
3. Give it a typed record rather than loose keyword arguments, and version it
   if it will be serialized.
4. Record the choice on the ledger, so a run can be read back and the option
   can be counted across runs.
5. Add a check that exercises both the default and the new value, and a check
   that the new value is refused when its precondition is missing.
6. If it makes a module reachable that was not, add that module to
   `REQUIRED_REACHABLE` in `reachability_report.py`.
7. Add a row to this page.

## Choosing between designs rather than settings

The table above lists the settings this runtime has. It does not tell you
whether the design behind a setting is the right one, because every row is a
choice someone already made.

`devtools/embodiment_axes/` holds the alternatives, built from scratch and
measured against each other: twenty-two embodiments on five independent axes,
each with what it gives you and what it costs you stated next to each other.
The axes are how information reaches a step, where a step runs, how an answer
gets accepted, what an earlier run contributes to a later one, and who picks
the next unit of work.

Start at `devtools/embodiment_axes/CATALOG.md` to choose one, and
`FINDINGS.md` for what the measurements said. Three results bear directly on
the settings above.

- Constant context is a property of the schema, not of the architecture. A
  record everyone would describe as compact reached ten kilobytes at 1,024
  units because two of its fields held one entry per unit.
- Folding several units into one call cut both the call count and the total
  bytes, by 47 times and 7 times respectively. Bounding the schema and then
  batching are separate wins, and doing only one leaves most of it unclaimed.
- A cross-run answer cache bought one call out of seventeen over a checkpoint
  store, and served an outsider's staged answer as its own. The governed
  journal reached the same saving and refused it.

That folder does not run this runtime and grants no authority. It is a
measured menu, and it is deliberately independent: when the last check here
shared assumptions with what it was checking, it could not see three
contradictions.

See also `embodiments/`, which holds runnable launch surfaces for this
runtime, one folder per execution mechanism.

## Proposed, not built

The improvement plan holds the configurations that are specified and not yet
implemented, with the boundary that owns each one: a step realization setting
so a step can run natively or in a harness instance, node-kind Loop profiles,
partial admission of model responses, a provisioner Loop that proposes per
node grants against a closed catalog, a decomposition strategy setting, a
context slicing policy, a bubblewrap workspace backend, baseline regression
gates, an instruction source policy, and a per-candidate budget partition.

See [the improvement plan](../implementation/IMPROVEMENT-PLAN-2026-09-07.md),
sections 7, 8, 8b and 8c. Anything marked `decision` needs the owner before
work starts.

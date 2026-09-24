# Step execution: one step, any engine

A step is one discrete cognitive or act step Loop node: an independently
governed instance of the Loop runtime responsible for one clearly defined
cognitive step or action. It receives only the context, instructions, skills,
tools and working files its assignment needs; a separately initialized
harness process can perform it, and, when explicitly permitted, another
harness can attempt the same assignment after a failure while its contracts,
permissions, history and remaining authority persist. The complete behavioral
explanation is in [ASTRA.md](../../../ASTRA.md#complete-behavioral-explanation).

This guide covers the step executor slot as it is built today: the step edge
records, the envelope that selects and runs an engine, the one engine class
behind every declared harness, the custom Loop engine, and qualification. It
lives in `src/loop_engine/core/step_execution`. The design, with its reasons,
is section 13 of
[Engines behind fixed edges](../../architecture/ENGINES-BEHIND-FIXED-EDGES.md);
selection itself is in [Engine selection](ENGINE-SELECTION.md). Roadmap steps
S-6.31 and S-6.42 own the work.

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

No part of this component is a runtime type. The owning Loop keeps the task,
its contracts, its authority, its evaluation and its Run History; every
attempt runs in one Spawned Loop of the owning Loop, and the registered
boundary is "delegated step execution".

## The one call

```text
execute_step(request, host, parent=owning Loop)
├── build the selection request from the step's typed fields
│   ├── delegation required: only the slot's delegating kinds, only process isolation
│   ├── the step's grants plus the mechanics grant the owning Loop gives an engine
│   └── the slot's requirement screen, bound to this step
├── select_engine_as_loop: one engine_selection_decision/v2, recorded before dispatch
├── run_step_attempt: one physical attempt in one Spawned Loop
│   ├── the recorded decision is required and the bound engine is revalidated
│   ├── the engine's run_step is called exactly once
│   └── the envelope computes delegated and the executor identity
└── assess the attempt; fall back only as the slot and the host's policy allow
```

The caller never names an engine. Which engine runs, Baltor's own Loop
runtime or an outside harness, is the host's slot configuration. When no
engine is eligible the result is the slot's declared answer: status
`unavailable` with failure kind `engine_unavailable`.

`delegated` is true only when a delegating kind (an agent protocol, native
protocol, text relay or custom Loop harness, or a remote agent) ran with
process isolation, reported a process identity and a sandbox profile digest,
and had every model call counted by the broker. An engine that writes its own
claim into its result is ignored.

## The step edge

| Record | What it holds |
|---|---|
| `step_run_request/v1` | Identity, goal, instructions, typed inputs, output ports, mode, an optional procedure, grants, model authority, the material placed for the step, a preemptive budget and executor requirements |
| `step_run_result/v1` | The same keys for every engine: status, failure kind, outputs, observed effects, the broker's accounting, material evidence, native identities, the executor and the measured time; acceptance is never claimed |
| `executor_profile/v1` | The capability record inside every step executor descriptor, with its compatibility entries |

A deterministic step authorizes no model call. A hybrid or model-led step is
delegated to a harness: its requirements must say so, and the in-process
engine can never serve it.

Material evidence keeps six facts apart for each placed file: resolved (its
exact source), materialized (placed with its digest), available (the harness
listed it), loaded (its text reached a model request), used (an attributable
action used it) and verified (an independent check). An engine claims loaded
only from a request the harness sent.

A compatibility entry is one key: component type, package format and version,
adapter version, harness interface and version, scope, and activation mode,
with a support state of native, translated, embedded, simulated, unsupported
or unverified. `unmet_step_requirements` refuses an engine whose support for a
component the step carries is not native, translated or embedded.

## What a custom harness author writes

One `step_harness_manifest/v1`. The release ships three in
`src/loop_engine/data/step_harness_manifests.yaml`: `pi.print`, the offline
`fixture.step_harness` and `baltor_loop.process`. A host file can carry its
own the same way.

```text
step_harness_manifest/v1
├── identity: harness_id, harness_version, engine_kind, title, source (upstream, revision, licence)
├── launch
│   ├── executable: the program name; the host installation pins its real path and software
│   ├── arguments and environment: templates over a closed list of fields
│   ├── HOME must be {empty_home}; the configuration variable must be {configuration_folder}
│   └── the model credential reaches the harness only through its own environment
├── layout
│   ├── layout_profile: a client kind of native_client_layout_profile/v1, or none
│   ├── instruction_files and skills_directory: where the step's material goes
│   └── global_locations: where the harness reads outside the step, for decoys
├── capabilities: modes, features, native controls, fresh_instance, compatibility entries
├── sandbox: isolation, network, model wire, native tools, placement
└── completion: exit codes, output source, output format and the pointer to the answer
```

The manifest names what a harness needs; it grants nothing. It cannot open
the network, add a writable path, add a credential or raise a budget, and a
need the step does not grant makes the engine ineligible. Only a fresh
process for each step is qualified for a manifest today.

Registration follows one path:

1. Validate the manifest and its layout:
   `tools/register_step_harness.py validate MANIFEST` reads it with the strict
   reader and compares its skill folder with the installer's layout profile.
2. Install it: an `engine_installation/v1` whose settings name the manifest,
   its digest, the program's real path and the read-only software mounts.
   The engine's descriptor is projected from the manifest, the pinned
   software and the engine module.
3. Qualify it: `tools/register_step_harness.py qualify MANIFEST` runs the
   fixture step. Until an `engine_qualification/v1` from `qualify_engine`
   proves a fresh start, loaded material and a read output, the engine stays
   a candidate and selection refuses it with `engine_not_active` and
   `engine_unqualified`.
4. Place it in the host's policy. Nothing else changes; no caller changes.

## The custom Loop engine

Baltor's own runtime is two engines behind the same edge:

| Engine | Kind | Where it runs |
|---|---|---|
| `baltor_loop.in_process` | `in_process_runner` | In this process; never delegation; deterministic steps only |
| `baltor_loop.process` | `custom_loop_harness` | A separate sandboxed process declared by its manifest; counts as delegation |

Both call `run_step_in_loop`: the canonical Loop runs the step with the
compact five-step profile (load the typed inputs, choose the declared
procedure, act, check the output against its port, commit it).

What returns now through this engine is the Loop runtime itself, with its
step profile, loop and exit conditions and ledger, and three pure procedures
over live modules:

| Procedure | What it does |
|---|---|
| `contract.match@1` | Compares an observed value with an expected one under a declared match mode, through the live contract matching module |
| `text.render_template@1` | Fills a declared text template from named inputs; a missing name refuses |
| `json.select_fields@1` | Keeps the declared fields of one JSON object |

What stays parked is named with its checkpoint home, revision `a3bd0f1`, and
refused with `procedure_parked`: the text conformance operations, duplicate
detection, field recovery, address components, database copy, Solution Canvas
execution, the in-process solve runtime, the campaign runner and the Kaggle
executor. A parked capability returns only as a procedure of this engine,
never as an in-process call site, after an owner decision, with its suite
collected again and its own qualification.

## Checks

```bash
PYTHONPATH=src python3 -c "from loop_engine.core.step_execution.harness_manifest_checks import self_test; print(self_test()['all_passed'])"
PYTHONPATH=src python3 -c "from loop_engine.core.step_execution.engines_checks import self_test; print(self_test()['all_passed'])"
```

These start no process. The sandbox scenarios start the fixture harness, the
custom Loop harness process and misbehaving variants for real, and are kept
out of the base self-test like the harness process qualification:

```bash
PYTHONPATH=src:tools python3 -m unittest discover -s tools -p test_register_step_harness.py
PYTHONPATH=src:tools python3 tools/register_step_harness.py demonstrate --output-root DIRECTORY
```

No check calls a model. The only broker a check binds is the fixture broker,
which answers every request with a fixed text.

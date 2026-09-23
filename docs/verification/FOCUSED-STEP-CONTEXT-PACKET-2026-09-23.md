# Focused step context packet, September 23, 2026

Kind: dated candidate implementation and offline verification. Source reviewed:
`abcad4f8ce346e7d0759ccad703e0111574148a6`. The roadmap remains the task
authority. This experiment implements no production record, service or
runtime and claims no task completion.

## The gap the owner identified

A focused harness needs to know the current task and how to begin. A library
of `SKILL.md` procedures alone cannot tell a new process its objective,
current state, supplied input, first actions, output contract and acceptance
conditions. An ephemeral assignment packet carries those facts. Reusable
intelligence is selected for that packet when it is relevant and approved.

The owner named `node_context.md`, `AGENTS.md` and state-like files as examples.
`node_context.md` and `run-state.json` in this experiment are explicit data
files. There is no assertion that clients discover arbitrary `agents.state`
or context filenames. The supported native entrypoint carries the essential
assignment inline, before it points to further material.

## Existing boundaries inspected and reused

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Every packet below is passive input to an existing Loop-owned execution
boundary. It is not an executable vertex.

| Existing source | Reused behavior | Gap remaining for production |
|---|---|---|
| [instance_instructions.py](../../src/loop_engine/core/instance_instructions.py) | `AssignmentBriefing`, sections, composition, byte ceiling, secret scan, `AGENTS.md` and `CLAUDE.md` import writer | Core briefing has goal/authority/reporting, but no structured first-action or current-state fields. Its unlisted-style fallback is not a native compatibility proof; this wrapper uses an explicit allowlist. |
| [node_provisioning.py](../../src/loop_engine/core/node_provisioning.py) | Existing `NodeAssignment` and `node_assignment/v3` serialization | Its native assignment filename is `task.json`. The production `provision` operation also offers catalogue references and writes `provisioning.json`; this candidate does not invoke that operation or fabricate an offered-item record. |
| [semantic_runtime_records.py](../../src/loop_engine/core/semantic_runtime_records.py) | `TrustedStateSnapshot` identity, version, values and digest | The snapshot must come from the owning run's trusted state source. A matching hash cannot establish truth or freshness by itself. |
| [observation_expectations.py](../../src/loop_engine/core/observation_expectations.py) | Self-contained JSON Schema resolution without remote reference reads | Schema compatibility is separate from semantic task acceptance. |
| [skill_state_context.py](../../src/loop_engine/core/skill_state_context.py) | Reviewed as prior implementation input | Explicitly passive and not integrated with the product prompt renderer. It must not be advertised as an active state-driven execution path. |

The [native placement research](../research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
already records client/version paths and inherited configuration risks. This
experiment reuses its Codex no-model discovery approach instead of inventing
another instruction convention.

## The two concrete packets

The source is [the candidate artifact](../../artifacts/focused-step-packet-2026-09-23/README.md).
The first fixture reconciles one inventory row. The second orders incident
observations while refusing an unsupported causal conclusion. Both use
synthetic task inputs.

```text
Fresh step folder
├── AGENTS.md: essential assignment inline in a native instruction entrypoint
├── CLAUDE.md: @AGENTS.md import for the Claude-targeted example only
├── node_context.md: human-readable task context, state and first actions
├── task.json: existing node_assignment/v3 fields
├── run-state.json: passive run-scoped state with version and digest
├── input.schema.json: exact input JSON Schema
├── output.schema.json: exact proposed output JSON Schema
├── input.json: bounded supplied task data
├── checklist.md: first actions and independent acceptance obligations
└── packet-manifest.json: file digests plus run/context/state binding
```

Inventory: eight payload files plus one manifest. Incident: nine payload files
plus one manifest, because it includes the Claude import. Total: **19 packet
files, seven Markdown and twelve JSON**. Excluding manifests, the payloads
are 10,207 bytes and 10,348 bytes respectively. Fixtures, renderer, tests,
probe and reports are development support and are not packet payload.

There are **zero new persistent library items**. A routine run-specific
assignment is not another approved reusable package for the million-file
target. An independently qualified renderer would compose these from typed
task, state and authority fields. Every run does not need three independent
model reviews of its new `task.json`. Reusable scripts, plugins and procedure
bodies retain their own admission requirements, while task outputs retain
their independent acceptance requirement.

## Verification and failed attempts

The 16 initial tests were written before implementation and failed against the
stub. The first renderer passed all 16. An additional known-wrong test then
showed that JSON boolean `true` could compare equal to context version `1`.
It failed before the strict-version repair and passed afterwards. An eighteenth
test then exposed a malformed JSON Schema escaping as the validator's error
instead of the renderer's typed refusal; that failure and its repair were
also saved. The [final test result](../../artifacts/focused-step-packet-2026-09-23/tests-final.txt)
contains 18 passing tests. Failed attempts remain beside their successors.
The [removed-guard record](../../artifacts/focused-step-packet-2026-09-23/removed-guard-checks-20260923T132739.json)
binds the final renderer and tests by digest: the baseline passes and all
seven selected guard removals make a check fail.

The tests cover missing objective, missing first actions, missing output
contract, schema mismatch, remote schema references, unknown fields and
versions, secret-shaped content, bounded context, forbidden authority,
run-bound state, unknown client style, native aliases, detached mutable
caller inputs, stale run/context/state/digest bindings, traversal, overwrite,
ancestor and payload symlinks, edited content, added files and a tampered
manifest whose file hashes were recomputed by the attacker. The last case
fails because the trusted expected payload digest is held outside the packet.

The [native probe record](../../artifacts/focused-step-packet-2026-09-23/CODEX-PICKUP-20260923T132425.json)
records two positive and two negative cases through Codex 0.155.1's
`debug prompt-input`. Both exact `AGENTS.md` files placed the objective,
first action, state identity and output contract in the rendered prompt.
Removing the native entrypoint while retaining the context, state and schema
files removed all four markers. Thus auxiliary files alone did not explain
the task to this tested client configuration.

No model was called. Claude's import mechanism, OpenCode and Pi were not
tested here. The incident fixture's common `AGENTS.md` was tested through
Codex, which does not qualify the fixture's Claude-specific entrypoint.
Debug prompt composition is not proof of model use, beneficial intelligence
or accepted task output.

The first successful native probe tested an earlier formatting of the same
content. A direct Markdown-library check then found missing blank lines in
the generated instructions. The earlier bytes and their bindings are kept
under `failed-attempts/pre-format-packets`; the current bytes were rendered
again and their native pickup was retested. The canonical Claude import
file has no heading, so only that file is exempt from Markdown rule MD041.

## Integration into the existing work

| Existing roadmap step | Recommended integration |
|---|---|
| S-6.31, harness executor | Give the existing assignment/briefing boundary typed current state, initial actions, input/output contracts and acceptance references. Bind them to the owning Loop, run and exact state before native materialization. |
| S-6.44, native layouts | Use each qualified client's instruction entrypoint to bootstrap the packet. Do not rely on reading `node_context.md` by coincidence. Keep essential content inline and verify inherited material separately. |
| S-6.53, generation | Generate reusable procedure/tool packages from distinct tasks while keeping each execution's task inputs and state separate. Do not multiply ephemeral packet versions into the public library count. |
| S-6.61, credential broker | Provide capability and credential references through a host-validated boundary. Never interpolate a raw credential into these files or derive effects from their prose. |
| S-6.62, catalogue releases | Keep reusable approved material in catalogue releases; keep per-run packets in scoped task workspaces and Run History references. Neither is a second copy of the other's authority. |

The example renderer refuses all effect and model authority and supports
preview-only deterministic assignments. A production extension must consume
existing typed host authorization rather than treating the candidate's
JSON fields as a permission grant. It must also preserve cancellation,
resource budgets, state freshness and independent task acceptance across
fresh native processes.

A future state update should create a new host-validated context/state
binding. This prototype performs no state transition, persistence or
resume orchestration. It validates at render/verification time, without a
distributed freshness source or a race-resistant sandbox mount. Concurrent
hostile filesystem mutation, hard-link/mount provenance and arbitrary
untrusted JSON Schema resource behavior remain unqualified. Known secret
patterns are a screen, not a guarantee that every secret is detectable.

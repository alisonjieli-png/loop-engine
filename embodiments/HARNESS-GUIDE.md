# Harness integration in Loop Engine

An embodiment selects an installed external harness for each model-led semantic
step. Loop Engine still owns the task, capabilities, workspace, verification and
Run History. The integration is in the public solve path, not a separate engine.

All paths below are inside `/home/username/loop-engine`. Earlier reference
workspaces are not used as output destinations.

## Runtime ownership

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
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The harness is an internal adapter used by a classified Loop. It is not another
graph vertex. In the qualified text-only profile, native harness tools are
disabled. Model-proposed engine actions still pass through the existing typed
capability and effect boundaries. This is not a claim that every upstream tool,
plugin or interactive feature has been integrated.

For each semantic call, the adapter starts a fresh process in a confined
workspace. The process has no provider credential and no external network
access. Its local HTTP endpoint forwards requests over private IPC to the
canonical gateway. The gateway uses the authorized exact route. For this
campaign that route is `ollama_cloud`, not Ollama local inference.

The original task packet must survive in the actual harness request. A typed
digest mapping records the original packet and the added harness envelope.
Requests that omit the packet, change model identity, or contain native tool
schemas are refused. Exit code zero alone is not success. The delivered text
must equal an actual broker response, and the owning evaluator must accept it.

## Development instructions and nested control

The architecture permits an outer Loop Engine Loop around a native harness
loop. The outer Loop retains task authority and independent acceptance; the
inner harness can plan and execute its permitted internal operations. Read
[the layered design](../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
and the main comments in [ASTRA.md](../ASTRA.md).

| Instruction surface | File | Purpose |
|---|---|---|
| Shared repository instructions | [AGENTS.md](../AGENTS.md) | Canonical development rules and architecture invariants. |
| Main advisory comments | [ASTRA.md](../ASTRA.md) | Owner direction, suggestions, and acceptance criteria for Claude Fable 5.1 and other reviewers. |
| Claude Code project entry | [CLAUDE.md](../CLAUDE.md) | Imports the shared repository rules and advisory note. |
| Harness-directory instructions | [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) | Adds the first-party harness development scope. |
| Development-tool instructions | [AGENTS.md](../devtools/AGENTS.md), [CLAUDE.md](../devtools/CLAUDE.md) | Adds experiment, dependency, and evidence requirements. |

Claude Code supports importing shared instructions with `@path` references
inside `CLAUDE.md`. Codex uses `AGENTS.md` discovery rather than automatically
loading a file merely named `codex.md`. See
[Claude Code instruction imports](https://code.claude.com/docs/en/memory#agentsmd)
and [official OpenAI documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

These files guide development sessions. They do not modify `harness.json`,
launch flags, or runtime permissions. A confined text-response profile may
deliberately disable project instruction loading. Verify the exact profile's
loading behavior before claiming that these instructions reached a runtime
model call. File presence and a resolved import are not a live loading test.

The example and historical results below retain their original campaign
scope. Use the current request and provider authority before running any
provider-backed command.

## Run an installed embodiment

Run from `/home/username/loop-engine`. Use a new workspace and run directory for
each attempt. The command makes real Ollama Cloud calls and runs generated code
under the existing sandbox authority. Provider credentials must already be
configured through the normal Loop Engine provider configuration.

```bash
/home/username/loop-engine/.venv/bin/python -m loop_engine solve \
  --file /home/username/loop-engine/embodiments/qualification/tasks/escaped_fields_tool.txt \
  --quickstart --unattended \
  --compile-provider ollama_cloud --model-id deepseek-v4-flash:0731 \
  --embodiment pi \
  --embodiment-config /home/username/loop-engine/embodiments/pi/harness.json \
  --max-model-calls 30 --max-passes 3 \
  --workspace /home/username/loop-engine/artifacts/my-new-harness-run/workspace \
  --runs-dir /home/username/loop-engine/artifacts/my-new-harness-run/runs \
  --format json --quiet-model-io
```

The example's 30-call limit is an explicit run allocation, not a provider output
capacity. Output capacity comes from the exact source-backed model record.
Missing usage and cost remain unknown. A process deadline, call limit and token
allocation are separate controls. No fallback provider is enabled by selecting
a harness.

The selected manifest records an exact installed version, command and read-only
software paths. Binding content-pins that software. Changed files require a new
binding. Installation is not automatic during discovery or execution. Linux
Bubblewrap and the declared sandbox backend must be available. Unsupported
configurations refuse rather than silently changing execution mode.

## Source and evidence locations

| Purpose | Full filesystem path |
|---|---|
| Explicit configuration loader | `/home/username/loop-engine/src/loop_engine/core/harness_configuration.py` |
| Canonical semantic binding | `/home/username/loop-engine/src/loop_engine/core/harness_semantic.py` |
| Process confinement and cancellation | `/home/username/loop-engine/src/loop_engine/core/harness_process.py` |
| Private protocol relay | `/home/username/loop-engine/src/loop_engine/core/harness_process_relay.py` |
| Exact prompt-envelope accounting | `/home/username/loop-engine/src/loop_engine/core/model_prompt_envelope.py` |
| Complete-solve integration qualification | `/home/username/loop-engine/devtools/embodiment_lab/full_solve_qualification.py` |
| Campaign reports and preserved failures | `/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y` |
| Research catalog | `/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/upstream-catalog-v2.json` |
| Earlier Astra handoff, a dated snapshot | `/home/username/loop-engine/build/astra-harness-blueprint-2026-09-09` |

Protocol fixtures prove request and response handling, not provider integration.
The live comparison uses three frozen function tasks and 34 independent cases.
A complete solve exercises a different, longer workflow and has its own result.
Neither is labeled a full-system benchmark unless it covers the repository's
complete benchmark contract. Failed first attempts remain separate from repaired
adapter retries. The campaign report, not folder presence, determines status.

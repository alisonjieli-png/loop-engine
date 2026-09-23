# External harness adapters

Loop Engine has one typed boundary for optional agent harness packages. Package
detection does not prove that an adapter works. None of the four optional
packages is installed in the verified environment, so no package-backed
adapter has run there.

## Integration and comparison are separate

```text
Loop Engine
├── Normal Loop Engine execution
│   └── Practitioner, Intelligence, and Solution Loops run in Loop Engine
├── Optional external harness integration
│   └── One selected Loop delegates bounded work through a typed adapter
└── Published harness comparison research
    └── Reads source-backed published results and runs no competitor
```

The OpenML-CC18 and DS-1000 case studies used normal Loop Engine execution.
They did not call an external harness adapter.

The published comparison catalog also does not use these adapters. It reviews
results already published by harness authors or benchmark providers. See
[Compare published harness benchmark evidence](../../guides/complex-task-comparisons.md).

An adapter is useful only when a caller explicitly wants one Loop to use an
external package for bounded agent mechanics. Loop Engine still owns the task
contract, mode and effect policy, Intelligence references, provider identity,
model output maximum, physical-call accounting, independent evaluator,
Run History, and acceptance decision.

Today these are integration contracts with local protocol checks. They are not
four completed live integrations. Do not use their presence to claim that an
external package ran, improved a score, or participated in a case study.

Every request names the provider and model separately from the harness. It also
carries the exact provider-backed output maximum. `HarnessRuntimeBinding`
connects that identity to one configured SDK model or client. The binding uses
a non-secret configuration reference. A mismatched provider, model, SDK object
kind, or output maximum fails before package import or model use.

## Current built-in paths

| Adapter | Maximum-output boundary | Current status and wired behavior |
|---|---|---|
| Pydantic AI | `ModelSettings.max_tokens` | The adapter also passes request and total-token limits through `UsageLimits`. It requires a provider-bound SDK model. Package-backed execution remains unproven in the verified environment. |
| Deep Agents | `HarnessRuntimeBinding.output_limit` | Deep Agents has no single run argument for this value. The supplied SDK model must already enforce the exact maximum. The adapter disables application tools, skills, memory, and subagents, then applies a bounded graph recursion limit. Package-backed execution remains unproven. |
| OpenAI Agents SDK | `ModelSettings.max_tokens` | The adapter requires a provider-bound SDK model. It also applies a turn limit, requests usage data, and disables SDK tracing. Package-backed execution remains unproven. |
| Microsoft Agent Framework | `create_harness_agent(max_output_tokens=...)` | The adapter wraps a provider-bound client with a physical call ceiling. It disables web search, file memory, compaction, todos, mode management, and automatic tool approval. Package-backed execution remains unproven. |

The package paths contain current SDK calls, but local tests stop at the typed
boundaries. They do not substitute a fixture response for a real provider run.
An integration claim still needs the optional package, a real configured
provider, recorded usage, and an independently checked task result.

An injected runner is application code. It receives the resolved typed request,
but it is not evidence that the named package works. Normalization records
`max_output_tokens_used` only when a built-in boundary applied the value or an
injected runner returns a matching typed output-limit record.

## Output storage

An available adapter must receive a `ContextArtifactManager` through
`HarnessServices.artifact_store` before execution. Loop Engine stores the raw
text or canonical JSON output by digest first.

- Small output stays inline and retains a `HarnessArtifactRef` to the raw data.
- Large output is removed from the result body. The result contains the typed
  `HarnessArtifactRef` instead.
- An adapter-supplied `HarnessArtifactRef` must resolve in the same context
  artifact store and match its digest-derived object key.
- A missing manager refuses before the adapter runs.
- A storage or serialization failure becomes a typed failed result. It does not
  publish the uncaptured body.

The local contract tests use temporary directories, injected local runners,
provider-binding checks, and SDK argument builders. They do not install an
optional harness, call a model provider, or establish task quality.

```bash
PYTHONPATH=src python3 -c \
  "from loop_engine.core.external_harness import self_test; print(self_test())"
PYTHONPATH=src python3 -c \
  "from loop_engine.core.external_harness_adapters import self_test; print(self_test())"
```

Adapter completion remains separate from independent task acceptance.

## Adapter contract and engine identity

Every adapter is an engine of the step executor slot. Its `info()` declares
three fields under the engine protocol version `external_harness_adapter/v2`:

| Field | Meaning |
|---|---|
| `adapter_contract_version` | The engine protocol the adapter implements. Only `external_harness_adapter/v2` is supported. The first protocol declared nothing, and an adapter written for it is refused. |
| `engine_kind` | One of the ten engine kinds in `STEP_EXECUTOR_ENGINE_KINDS`. A kind is a declaration. It grants no permission, and it does not prove that a step was delegated to a separate process. |
| `supported_edge_contracts` | The edges the adapter serves, named by their request record type. `harness_request_identity/v3` asks for one model response and is served by `run()`. `step_run_request/v1` asks for one step and is served by `run_step()`; its records and envelope arrive in a later package, and no engine serves it yet. |

`HarnessRegistry.register` checks the declaration before any run. A refusal
raises `HarnessAdapterRefused`, which carries every reason as a stable code:

| Code | Refused declaration |
|---|---|
| `adapter_contract_version_missing` | No contract version |
| `adapter_contract_version_unsupported` | A contract version the registry does not serve |
| `engine_kind_missing` | No engine kind |
| `engine_kind_not_in_slot` | A kind the step executor slot does not list, such as a record store kind |
| `no_supported_edge_contract` | None of the edges the registry serves |
| `engine_identifier_already_registered` | A second engine under one identifier without `replace=True` |
| `replacement_registration_digest_unchanged` | A replacement with the same declaration and the same implementation class |

An adapter that declares an edge without its operation is refused with the
code `edge_operation_missing` followed by the operation name. An adapter may
also declare edges the registry does not know; the registry uses only the
edges it serves, which `served_edge_contracts()` returns.

`HarnessRegistry.registration_digest` returns the digest of one registration:
the whole declaration and the implementation class. A replacement always
changes it. No decision record carries this digest yet. The engine selection
decision planned in the engine design is meant to bind it, so that a decision
made before a replacement no longer matches. Until then,
`HarnessSemanticBinding` notices a replacement when it is used, by comparing
the registered adapter object and its declaration.

One engine identifier names one implementation. The parked raw host OpenCode
adapter therefore answers to `opencode.raw_host`, while the OpenCode recipe
engine of `embodiments/opencode/harness.json` answers to `opencode`.

| Adapter | Engine kind | Edge |
|---|---|---|
| The four framework kits in `builtin_harness_adapters()` | `agent_framework_kit` | `harness_request_identity/v3` |
| `GatewayHarnessProcessAdapter`, a brokered process harness | `text_relay_harness` | `harness_request_identity/v3` |
| `UnavailableHarnessAdapter`, standing in for a process harness that is not installed | `text_relay_harness` | `harness_request_identity/v3` |
| `OpenCodeProcessAdapter`, parked and refusal only | `in_process_runner` | `harness_request_identity/v3` |

`run_external_harness` checks the same declaration again when it is used, and
refuses an adapter that does not declare `harness_request_identity/v3`,
before any Loop starts.

## The envelope clock

The `elapsed_seconds` field of `external_harness_result/v3` is measured by the
envelope with its own monotonic clock, from just before the Loop runs the
adapter until the adapter's output is captured. The adapter's own figure is
kept apart as `engine_reported_seconds` in the same ledger event, beside the
safe summary, and nothing ranks it. The post-run time bound reads the
measured value, so an engine cannot pass that bound by reporting less time,
and it cannot make itself look faster or slower than it was.

```bash
PYTHONPATH=src python3 -c \
  "from loop_engine.core.external_harness_contract import self_test; print(self_test())"
```

## Process harness recipes

The process adapter runs a command-line harness inside Bubblewrap and brokers
every model request through the canonical gateway. Which harnesses it can
start is data: the release recipe catalogue
`src/loop_engine/data/harness_recipes.yaml`, record
`harness_recipe_catalog/v1`, read by `loop_engine.core.harness_recipes`.

```text
harness_recipe_catalog/v1
├── wire_codecs: one harness_wire_codec/v1 per model wire the relay translates
│   ├── the request paths it answers and how an answer is framed
│   └── the codec module and its decode and encode functions
│       (none for the OpenAI chat wire, which the relay serves itself)
├── recipes: one harness_recipe/v1 per harness style
│   ├── the module the sandbox mounts, with its SHA-256
│   ├── prepare(style, config, base) and extract(style, stdout, expected)
│   ├── the wires it speaks, its instruction file style and its native controls
│   ├── special cases as data: requires_context_capacity, sandbox_environment
│   └── distribution: the kind, the pinned version and a digest a qualification bound
└── fresh_instance_recipes: one harness_fresh_instance_recipe/v1 per launch
    recipe that starts a harness fresh for one step (see below)
```

A host `harness.json` names a style from this catalogue and cannot name a
module or another catalogue. A style the catalogue does not hold, such as the
`freebuff` embodiment, is refused with the reason `unsupported_style`. When a
style is bound, the runner verifies the recipe's module and the codec module
of each wire it declares against their catalogue digests, mounts exactly
those modules beside the relay, and digests them into the process identity.
The relay reads the recipe record and its wire records from its private
configuration, chooses the wire by request path, and names no style.

To add a command-line harness, write one recipe module in
`src/loop_engine/core` with the two functions above, and add one
`harness_recipe/v1` record with the module's SHA-256. No edit to the runner or
the relay is needed; the check
`adding_a_process_harness_recipe_needs_no_core_dispatch_edit` fails if a style
is spelled in either file. Editing a recipe module without updating its digest
makes that recipe refuse to bind and fails
`every_recipe_names_resolvable_functions_and_its_module_digest`.

```bash
PYTHONPATH=src python3 -c "from loop_engine.core.harness_recipe_catalog_checks import self_test; print(self_test()['all_passed'])"
```

The real sandbox run of a fixture recipe, added as one module and one record,
is part of the Linux process qualification
(`harness_process_checks.qualification_checks`), which starts processes and is
kept out of the base self-test.

## Fresh instance recipes

A fresh instance recipe starts the customer's own harness for one step, in
the customer-side launch mode: a clean environment, an empty home folder, the
harness's own configuration folder, and the step folder as its own git root.
The recipe names the command, the environment, where the step's instruction
file, skills and protocol servers go, and the global locations the harness
reads. `loop_engine.core.harness_fresh_instances` renders a recipe for one
step and assesses what one launch loaded; `render_launch` refuses a candidate.

```bash
PYTHONPATH=src python3 -c "from loop_engine.core.harness_fresh_instance_checks import self_test; print(self_test()['all_passed'])"
```

`tools/check_harness_fresh_instances.py` proves each recipe offline at its
pinned version. It starts the real installed harness inside Bubblewrap with
no network, the real home folder replaced by decoys, and decoy instruction
files in the folder above the step. A loopback endpoint records the harness's
first requests and answers no model, so no model is called. Loading counts
only when a step marker is inside a request the harness sent; an exit, a
session identifier or a listed tool never counts. Two controls run beside
each recipe. With the step's `AGENTS.md` missing, the launch must fail
whenever the recipe claims the instruction file; if it passes, the whole
check fails, because a check that cannot fail proves nothing. With the home
folder kept, the result is recorded, not required to fail: it shows whether
the empty home rule matters for that harness. In the third recorded run of
September 22 (`harness-fresh-instance-isolation-3.json`), Codex and OpenCode
read the decoy skills of a kept home folder, while Pi and both Claude Code
recipes, which take the step's files through explicit flags or read user
files only from their own configuration folder, did not. Each run writes a
new folder and keeps the earlier ones.

What the recorded runs of September 22 found, at Codex 0.155.1, OpenCode
1.18.32, Claude Code 2.1.280 and Pi 0.73.1:

| Recipe | Instruction file | Skills | Protocol servers |
|---|---|---|---|
| `codex.fresh_instance` | loaded | loaded | loaded |
| `opencode.fresh_instance` | loaded | loaded | loaded |
| `claude_code.bare` | loaded | not listed in bare mode | loaded |
| `claude_code.configuration_folder` | loaded | loaded | loaded |
| `pi.fresh_instance` | loaded | loaded | not supported without an extension |
| `zcode.app_server_candidate` | not tested | not tested | not tested |

- Claude Code in bare mode with `--add-dir` loaded the `CLAUDE.md` files of
  the added folder and of every folder above it, including the home folder's
  `.claude/CLAUDE.md` when the step sits below the home folder. The bare
  recipe therefore passes instructions only through
  `--append-system-prompt-file`, and bare mode lists no skills; they resolve
  only by name.
- The Claude Code fallback with its own configuration folder leaked the same
  home folder file until it excluded the instruction files of every folder
  above the step, not only the parent's.
- With `TMPDIR` set to the step's configuration folder, no harness wrote to
  the shared `/tmp` folder.
- ZCode is a candidate at source revision
  `872ad960de7ec172591f7e1952f7849229f94521`. It is not installed here, it is
  never launched, and no support is claimed until its isolation, cancellation
  and native loading are tested.

The step's model credential reaches a harness only as a variable of its own
process. Codex reads it through its provider's `env_key`, OpenCode and Pi
through a reference to `BALTOR_STEP_MODEL_CREDENTIAL` in their configuration,
and Claude Code through `ANTHROPIC_API_KEY`. No recipe writes the credential to
a file or passes it on a command line, and the check
`no_fresh_instance_recipe_writes_the_model_credential_to_a_file_or_a_command_line`
fails if one does. The offline check records only whether each request carried
the probe credential, never its value; every launched recipe delivered it.
Roadmap S-6.61 plans a local broker that gives each step its own short-lived
key in place of the customer's key; a recipe would receive that key through
the same variable.

The brokered text-response runner above goes further: a harness process there
holds no provider credential at all. Its relay forwards every model request
over a private socket to the canonical gateway, which alone holds the
credentials and the model authority.

Loading is proven; use by a model is not. A proof holds for the pinned
version only; a newer installed version is unqualified until the check runs
again.

## SDK references

The package calls follow the current primary documentation:

- [Pydantic AI model settings](https://ai.pydantic.dev/agent/#model-run-settings)
- [Deep Agents model configuration](https://docs.langchain.com/oss/python/deepagents/models)
- [OpenAI Agents `ModelSettings`](https://openai.github.io/openai-agents-python/ref/model_settings/)
- [Microsoft Agent Framework harness](https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/harness)

The [saved ABI check](../../evidence/external-harness-abi-check-2026-08-25.json)
records current package versions, separately checked SDK signatures, failed
combined dependency resolution, and the limits of those checks.

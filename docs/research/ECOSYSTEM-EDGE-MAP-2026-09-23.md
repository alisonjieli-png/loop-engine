# Ecosystem edge map: reusable projects and standards behind Baltor's fixed edges

September 23, 2026. The owner asked for more research, tables, feature
comparisons and evaluations of the projects and standards in an ecosystem map
another assistant wrote. The owner, the same day: "We need to look at this
holistically, while maintaining our wrapped compartmentalization, and other
things."

This record does that. Every candidate is placed behind one of the engine slots
in [engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml): 45 fixed,
typed, versioned edges, each with swappable engines. A new slot is proposed only
where none fits. It separates what was run here, what was read in a project's
own source, and what is only a claim.

## How this was done, and its limits

- **Run here:**
  - the npm package of madebywild/agent-harness 2.1.0 (see [its review](AGENT-HARNESS-MADEBYWILD-2026-09-23.md));
  - FastMCP 4.0.5 and the MCP Python SDK 2.2.0;
  - DBOS 3.0.0, with a process killed in the middle of a step;
  - the official Agent Skills validator at `agentskills/agentskills@69ef37e`, on a Baltor skill;
  - installs of Harbor 0.23.0, Inspect AI 0.3.268, rulesync 17.0.0 and Extism 1.1.1.
  The trial folders are under `/home/username/.le-ci-tmp/research/`.
- **Read in source:** CopilotKit OpenMuse at commit `bb7ce4e` (September 23, 2026), and package metadata from PyPI, read the same day.
- **Not done:** five research lines stopped at the account's weekly usage limit before they could write reports. Their trials that finished are used here. The following are not yet verified: the interface protocols (AG-UI, A2UI, MCP Apps), most distribution formats, the provenance standards beyond package versions, and the end-to-end run inside Claude Code and Codex. Each is marked "not verified" below.

## The frame: compartments that must not leak

The owner's rule of September 21, 2026: every functional unit is wrapped so
that "we can replace the unit engine without impacting functional unit to unit
edge communication". For every candidate:

- **The slot's request and result stay Baltor's own typed records.** An external type, file format or identifier stays inside its engine and is translated at the edge.
- **A standard is a field or an export format of Baltor's record, never its replacement.** This covers PURL, OCI, SPDX, CycloneDX, OpenTelemetry, ATIF, CloudEvents and JSON Schema.
- **One runtime.** Every executable graph vertex is a Loop. A durable-workflow system, an agent application or a harness framework may be an engine a Loop uses, never a second scheduler of steps.
- **The other invariants hold:**
  - effects need typed authority; a hook or plugin that runs commands is an effect;
  - discovery is effect-free;
  - secrets never land in files, events, reports or telemetry;
  - imported material stays a candidate until independent review;
  - versions are negotiated before effects;
  - configured, loaded, used and verified are separate facts;
  - business material stays out of the public repository.

## The edge map

"Evidence" says what supports the decision: **ran** (a trial here), **source**
(read in the project's code or documentation), or **claim** (not verified).

| Slot | What the edge does | Default engine today | Candidate engines or standards | Decision | Evidence |
|---|---|---|---|---|---|
| `material_install_layout` | Places a package's files in a harness's native layout | Baltor's harness layout profiles | agent-harness 2.1.0; rulesync 17.0.0; Ruler | Add an optional engine kind, a configuration compiler, with agent-harness as its first engine. Post-render checks at the edge: no key value in any file, a digest of every written file, and no deleted instruction file | ran (agent-harness); installed only (rulesync); claim (Ruler) |
| `harness_instruction_files` | Instruction files a harness reads | AGENTS.md and harness-specific files | The AGENTS.md convention | Keep. A compiler may write these files, never merge or delete existing ones | ran (the agent-harness importer deleted a copy of AGENTS.md) |
| `customer_client_recipe` | Per-harness connection recipes | `client-recipes.json` | An agent-harness preset; a Claude Code plugin marketplace; MCPB | The recipes stay authoritative. Publish a Baltor preset generated from them, written per harness | ran (key syntax differs per harness) |
| `custom_plugins_port` | Registered capability surfaces and plugin bundles | Registered surfaces and plugin bundles | MCPB; Claude Code plugins; Extism (a new kind, WebAssembly plugin) | Watch MCPB for local distribution. Watch Extism until a capability needs a portable sandboxed binding | installed only (Extism); claim (MCPB) |
| `library_ingestion_source` | Reads outside material into staging | The importer (LS1) and review panel (LS2) | The MCP Registry; skills.sh; Agent Skills repositories | Adopt as registry_reader inputs that only ever create candidates. Map names to the Agent Skills rules at the edge | ran (validator); source (skills.sh code saved) |
| `tool_protocol_transport` and `protocol_endpoint` | Serve and reach MCP tools | MCP Python SDK 2.2.0 | FastMCP 4.0.5; MCP Inspector for conformance | Adopt FastMCP for tool surfaces built from functions or OpenAPI, only with an explicit allowlist and a final exclude rule, checked by name | ran |
| `step_executor` | Runs one step in a separately started harness | External harness adapters | The Agent Client Protocol (agent_protocol_harness kind); A2A (remote_agent kind); harness integrations listed by Harbor | Keep. Use Harbor's integration list as the coverage target: Claude Code, Codex, OpenCode, Pi, Goose, Gemini CLI, OpenHands, Hermes, OpenClaw, Kimi CLI, Terminus 2 and a protocol adapter | ran (Harbor 0.23.0 installed and lists them) |
| `process_confinement` and `workspace_backend` | Isolation and working folders | Restricted local, container | OpenSandbox 1.1.0, E2B 2.51.0, Daytona 0.216.1, Microsandbox 0.7.2, Docker, Dagger 0.21.9, Nix | Keep the container default. Choose one remote kind by a lifecycle test. Nix provisions tools and is never the isolation boundary | source (versions and licences); claim (isolation details) |
| `response_evaluator` | Grades a step's output | Deterministic and model-led evaluators, independent verification | Harbor 0.23.0; Inspect AI 0.3.268 | Adopt Harbor for with-and-without comparisons (initiative 4) after a pinned trial. Keep Inspect for model and tool-choice evaluations | installed only |
| `run_history_export` | Exports runs as traces or trajectories | Kinds declared: trace exporter, trajectory exporter | OpenTelemetry (GenAI conventions, package 0.65b0, still pre-release); ATIF; Phoenix as a viewer | Map later behind the existing kinds, with a versioned mapping. The Run History record stays authoritative | source (package version) |
| `catalogue_body_store` | Stores approved bodies | Image files, private object storage | OCI registries with ORAS | Map later as a kind. Keep per-file digests as the identity | claim |
| `catalogue_qualification_resolver` | Decides whether a body is qualified | Host attestation, independent authority | Sigstore and in-toto attestations | Map later as the independent_authority kind. A signature proves origin, not correctness | claim |
| `usage_export` and `failure_journal` | Export usage and failures | No export; in-service journal | CloudEvents as an envelope | Map later as an export format only | claim |
| New: `step_attempt_durability` (proposed) | Keeps a step attempt's progress across a crash, under the Loop runtime | Run History and saved attempt state | DBOS 3.0.0 (SQLite start); Temporal 1.33.0; Restate 1.0.5; Inngest 0.5.19 | Propose as a roadmap addition. Any engine must reconcile an interrupted effect by a stable identifier before retrying. It is never a second scheduler | ran (DBOS) |
| New: `interaction_stream` (proposed) | Streams a live task and review to a customer interface | None | AG-UI; A2UI; MCP Apps | Watch until the live review interface is built | claim |
| New: `release_inventory_export` (proposed) | Exports a catalogue release as an inventory | None | SPDX 3; CycloneDX | Propose. One export format per release, with PURL where a registered package type applies | source (library versions only) |

## What the trials showed

| Trial | Version | Result | What it proves | What it does not prove |
|---|---|---|---|---|
| agent-harness writes one source for four harnesses | 2.1.0 | 14 files; a Baltor skill placed byte for byte four times. Key references were copied unchanged; `{{NAME}}` wrote the secret into four files; the importer deleted a copy of AGENTS.md | Placement works; three defects for Baltor's use | That any harness loads the files |
| Agent Skills validator on a Baltor skill | `skills-ref` at `69ef37e`; PyPI 0.1.1; npm port 0.1.5 | Valid only as `split-address-lines-into-components` in a folder of the same name. Rejected: the catalogue identity with underscores, a mismatched folder name, and a `version` field (allowed fields: `allowed-tools`, `compatibility`, `description`, `license`, `metadata`, `name`) | Baltor identities must be translated at the placement edge, with version and digest under `metadata` | That a harness loads the skill |
| FastMCP from an OpenAPI document, defaults | 4.0.5 | All five endpoints became tools, including `admin_reset`, and a call really sent `POST /admin/reset` | The claim "every endpoint by default" holds, and the risk is real | |
| FastMCP with an allowlist but no final exclude rule | 4.0.5 | Still five tools | An allowlist alone does not narrow the surface | |
| FastMCP with an allowlist and a final exclude rule, or a route function | 4.0.5 | Two tools; `delete_item` refused as unknown | The safe pattern works | |
| MCP SDK function tool | 2.2.0 | Typed input schema; a wrong type refused with a validation error; an unknown tool refused | The SDK already gives typed ports at this edge | |
| DBOS: a process killed in the middle of an external action, then restarted | 3.0.0, SQLite | The completed step did not repeat. The interrupted step ran again and charged twice. With an idempotency key and a ledger check, the retry was reconciled and charged once | The claim holds: durable workflows retry an interrupted step, so every external effect needs a stable key and reconciliation | Behaviour on PostgreSQL |
| Harbor install | 0.23.0 | Installed; lists 14 agent integrations | The integration list | Its capability fields, which the reader script did not find |

## The ecosystem map's claims, checked

| Claim | Verdict | Evidence |
|---|---|---|
| OpenMuse is MIT licensed, alpha, single owner | Verified | `LICENSE`; `SECURITY.md`: "one owner per deployment ... not multi-tenant" |
| Live deployments require a CopilotKit Intelligence key; sample mode works without it | **Contradicted at the current head.** Commit `bb7ce4e` is titled "require CopilotKit Intelligence in every mode" | `README.md`: "Requirements: Node 24 LTS, pnpm 11.19.0, and a CopilotKit Intelligence project key"; `SECURITY.md`: the key "is needed for the sample walkthrough" |
| OpenMuse uses PGlite or PostgreSQL | Verified for PGlite | `package.json`: `@electric-sql/pglite` |
| Its computer is a bounded nonroot container with a persistent workspace and terminal networking disabled | Verified | `README.md`: nonroot, no host-directory mounts or credentials, named `/workspace` volume, "Terminal networking is disabled", 30-second command limit; `apps/computer/smoke.test.ts` checks that a network command fails; disabled by default |
| Its browser worker is separate | Verified, with a caution | `SECURITY.md`: persistent Chromium with application-enforced public-network checks; Playwright disables Chromium's internal sandbox by default |
| A managed registry for generated tools is unfinished | Verified | `ROADMAP.md`: unchecked item "a managed registry for generated tools" |
| agent-harness: Cursor gets no prompt file; the lock hashes source before substitution | Verified | Its architecture document; our trial |
| agent-harness: unresolved variables warn without stopping apply | Verified in its documentation | "Unresolved placeholders produce `ENV_VAR_UNRESOLVED` warnings but do not block apply" |
| agent-harness: best-effort hooks can suppress unsupported mappings | Verified in its documentation | "`best_effort` suppresses unsupported-provider failures" |
| FastMCP's OpenAPI conversion exposes every endpoint by default | Verified by trial | See the trials above |
| DBOS retries an interrupted step; Python defaults to SQLite | Verified by trial for the retry and the SQLite start | See the trials above |
| OpenTelemetry GenAI conventions are still in development | Consistent with the package version | `opentelemetry-semantic-conventions` 0.65b0 is a pre-release |
| MCPB, the MCP Registry preview status, AG-UI, A2UI, MCP Apps, ORAS, SLSA, Sigstore, ATIF, Phoenix, Microsandbox virtualization, Dagger, Nix | Not verified in this pass | The research lines stopped at the usage limit |

## Feature comparisons

### Configuration compilers behind `material_install_layout`

| Feature | agent-harness 2.1.0 | rulesync 17.0.0 | Ruler | Baltor layout profiles |
|---|---|---|---|---|
| Harnesses | Codex, Claude Code, Copilot, Cursor | Not tested | Not tested | Driven by `client-recipes.json`: Codex, OpenCode, Claude Code and others |
| Instructions, skills, protocol servers, subagents, hooks, commands | All six (Cursor gets no instructions) | Not tested | Not tested | Instructions, skills, protocol configuration, plugins (roadmap S-6.44) |
| Key reference per harness | Copied unchanged; wrong for Cursor, VS Code and Codex | Not tested | Not tested | Written per harness |
| Secrets in generated files | Yes, through `{{NAME}}` | Not tested | Not tested | Never; the recipes reference variables |
| Import of existing files | Deleted a dropped file without a backup | Not tested | Not tested | Not applicable |
| Ownership and drift | Lock, managed index, collision stop, `plan` before `apply` | Not tested | Not tested | Digests per file |
| Content identity | Source hash before substitution | Not tested | Not tested | sha256 of every delivered file |

### Durable execution behind the proposed `step_attempt_durability`

| Feature | DBOS 3.0.0 | Temporal 1.33.0 | Restate 1.0.5 | Inngest 0.5.19 |
|---|---|---|---|---|
| Licence (Python package) | MIT | MIT | Not stated on the package | Not stated on the package |
| Local start | SQLite, run here | Needs a Temporal server (claim) | Needs a Restate server (claim) | Needs the Inngest server (claim) |
| Interrupted step | Runs again; reconciliation needed (ran) | Not tested | Not tested | Not tested |
| Fit | Smallest start for a single machine | Larger footprint | Not tested | Not tested |

### Sandboxes behind `process_confinement` and `workspace_backend`

| Project | Python package version | Licence | Status here |
|---|---|---|---|
| OpenSandbox | 1.1.0 (2026-09-21) | Apache-2.0 | Not tested |
| E2B | 2.51.0 (2026-09-18) | MIT | Not tested; a hosted service |
| Daytona | 0.216.1 (2026-09-23) | Apache-2.0 | Not tested |
| Microsandbox | 0.7.2 (2026-09-17) | Apache-2.0 | Not tested |
| Dagger | 0.21.9 (2026-08-26) | Apache-2.0 | Not tested |

### Evaluation behind `response_evaluator`

| Feature | Harbor 0.23.0 | Inspect AI 0.3.268 |
|---|---|---|
| Harness integrations | 14 listed, including Claude Code, Codex, OpenCode, Pi and a protocol adapter | Its agent bridge (not tested) |
| Licence | Apache-2.0 | Not read in this pass |
| Fit | With-and-without comparisons of real harnesses (initiative 4) | Model and tool-choice behaviour |

## Execution bindings for one capability

The map's design claim is that one capability may have several bindings. Under
the one-runtime rule, this maps onto existing slots without a new runtime type:

| Binding | Slot | Typed ports come from | Main determinism risk | Record in Run History |
|---|---|---|---|---|
| Direct function | A Code Intelligence item run by a Loop | The item's typed contract | Hidden inputs (time, locale, network) | Item digest, inputs, configuration, output digest |
| Subprocess (ripgrep and jq are installed here; DuckDB and FFmpeg are not) | `process_confinement` | Validated arguments and a pinned binary digest | Binary version and environment | Binary digest, argument list, exit status, output digest |
| HTTP | `web_research_port` or an OpenAPI surface | The OpenAPI operation, allowlisted | Remote state | Request identity, response digest, effect key |
| MCP tool | `tool_protocol_transport` and `custom_plugins_port` | The tool's input schema (typed, as the SDK trial showed) | The server's own state | Tool name and version, call arguments, result digest |
| WebAssembly | `custom_plugins_port`, new WebAssembly plugin kind | The plugin manifest | Host functions it is given | Module digest, host permissions, output digest |

An agent may choose the operation while a deterministic Loop calls the same
implementation directly. Only the binding changes, never the capability's
contract.

## Recommended composition

1. Baltor contracts at every slot, unchanged.
2. `material_install_layout`: Baltor's profiles stay the default. agent-harness joins as an optional configuration compiler, behind post-render checks.
3. `tool_protocol_transport`: the MCP SDK stays. FastMCP is added for generated surfaces, always with an allowlist and a final exclude rule.
4. `step_executor`: the existing harness adapters stay, with Harbor's integration list as the coverage target.
5. `response_evaluator`: Harbor runs the with-and-without acceptance trials after a pinned trial.
6. Durability, sandboxes beyond the container, registry distribution and live interfaces come later, each through its slot and only when a requirement is concrete.

## The next discriminating test

The end-to-end run stopped at the usage limit before it reached a harness. It
remains the next test:

1. Take one Baltor transformation with fixed test data and one verifier.
2. Bind it two ways: a direct function and a FastMCP tool with an allowlist.
3. Render it for Claude Code 2.1.280 and Codex 0.155.1 with the compiler, and compare expected with generated files.
4. Record four facts per harness separately: configured, loaded (its tool inventory), used (one real call) and verified (graded by the same verifier).
5. Keep the trajectory separate from the Run History record.
6. Interrupt one attempt and reconcile it by its stable identifier before retrying.

Success justifies the compiler engine and the adapters. A failure becomes a
named gap tied to the tested versions.

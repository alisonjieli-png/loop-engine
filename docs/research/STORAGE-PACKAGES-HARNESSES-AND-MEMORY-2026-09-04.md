# Storage packages, external harnesses, and memory boundaries

Research date: 2026-09-04. This is a bounded repository and primary-documentation
review. It does not claim that every package, file writer, or possible memory
architecture has been reviewed. Package availability is not integration proof.

## Repository inventory

At clean base `d121379773e46a1255fd3e86436d907dc2a0b4d0`, the inventory covered
1,454 tracked files. The selected JSON, JSONL, YAML, and Markdown population
contained 678 files and 62,633,155 bytes:

| Format | Files | Bytes |
|---|---:|---:|
| JSON | 278 | 10,613,271 |
| JSONL | 69 | 49,104,750 |
| YAML | 39 | 607,082 |
| Markdown | 292 | 2,308,052 |

No tracked database-suffix file was found in that scan. It did not traverse
external default instance directories or inspect private data bodies. The
larger requested CSV/Parquet/TOML/extensionless collection census remains
unfinished. File extension is a discovery clue, not authority.

All 531 tracked Python files were AST-parsed. The heuristic inventory found
285 JSON/YAML load sites, 212 serializer/write-text-or-bytes sites, 87 write-open
sites, and 11 database connects. These are syntax sites, not unique effects
or a complete caller-to-owning-Loop graph. Tests and wrappers affect counts.

Two historical hardcoding-audit JSONL files account for about 36 MB. Much of
the volume is development evidence, not an operational catalog. Immutable
exports should not be treated as repeatedly mutable session state.

## Storage findings and migration priorities

The corrected catalog queries share namespace and attribute semantics before
pagination. File reads bind paths rather than interpolate SQL, and capability
declarations no longer advertise unsupported joins, formats, or order.
SQLite managed writes check expected revision inside the transaction.

Other risks remain in established owners: independent JSONL append paths in
`StageStore`, `AdviceStore`, `SolverStore`, and `persistence`; silent malformed
row skipping in some old readers; partial-directory exposure in `RunHistory.save`;
and direct rewrite-oriented development exporters. Migrate one collection at a
time. Do not replace canonical Run History or Git authority with a query cache.
The inspected SQLite runtime is 3.46.1, affected by the documented WAL reset
race. `SQLiteRecordStore` refuses affected WAL writes inside each transaction;
other established WAL stores remain unqualified. No corruption was observed.
See the [storage compatibility boundary](../guides/queryable-records-and-storage.md).

The [record-operation ADR](../architecture/ADR-SCOPED-RECORD-OPERATIONS.md)
and [storage guide](../guides/queryable-records-and-storage.md) describe the
implemented local slice and its remaining limits.

## Package reuse decisions

These are proposed adaptations unless marked existing. No new runtime
dependency was added during this implementation.

| Package group | Decision and useful responsibility | Failure mode and qualification test |
|---|---|---|
| [PyArrow Dataset](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html) | Candidate for bounded columnar batches, interchange, and Parquet scans | Test schema/filter parity and actual memory; do not treat dataset writes as database transactions |
| [fsspec](https://filesystem-spec.readthedocs.io/en/latest/features.html) | Candidate behind authorized local/object-store bindings | Backend transaction guarantees differ; test credentials, cache lifetime, path/protocol allowlists and failure recovery |
| [SQLAlchemy Core](https://docs.sqlalchemy.org/en/20/core/connections.html) and [Alembic](https://alembic.sqlalchemy.org/en/latest/) | Candidate for a direct server adapter and reviewed migrations | Do not expose raw SQL or automatic migrations to model output; test transactions, pools and schema upgrades |
| [Pydantic](https://docs.pydantic.dev/latest/concepts/strict_mode/) | Narrow adapter-ingress use if it removes duplicated parsing | Default coercion can change meaning; require explicit strictness and preserve current dataclass/JSON Schema authority |
| [Portalocker](https://portalocker.readthedocs.io/en/latest/) or filelock | Choose at most one if a measured file-publication gap needs advisory locking | Locks do not replace database transactions or distributed leases; test contention, timeout and crash behavior |
| [DuckLake](https://ducklake.select/docs/stable/duckdb/usage/choosing_a_catalog_database) | Research target for larger Parquet-backed analytical history | Multi-client use needs suitable catalog authority; do not install several competing lakehouse authorities |
| [LanceDB](https://docs.lancedb.com/faq/faq-oss) | Existing optional derived retrieval projection | Test concurrent commit retries, freshness, embedding version, recall and namespace isolation |
| [Qdrant](https://qdrant.tech/documentation/security/) | Defer until a network vector workload justifies it | New service/credentials/security surface; require TLS, access controls and tenant tests |
| [OpenTelemetry](https://opentelemetry.io/docs/languages/python/) | Extend existing safe Run History exports | Exporter failure must not alter authority; never put secrets in propagated baggage |
| [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) / [Structurizr](https://docs.structurizr.com/dsl/language) | Generated diagram formats and optional validation | Pin tools; forbid uncontrolled includes/scripts/plugins; a diagram remains a projection |

Polars, Ibis, DataFusion, sqlite-utils, SQLModel, DiskCache, DVC, lakeFS,
Delta/Iceberg, msgspec, and orjson remain candidates or exclusions for later
workload-specific review. Do not add them for vocabulary coverage. In
particular, serialization replacements must preserve digest/canonicalization
semantics before any speed claim matters.

## OpenCode inside a Loop

`run_external_harness` creates one canonical Loop and invokes one adapter.
The OpenCode process adapter is quarantined: discovery is passive and execution
returns a typed refusal. Its event parser remains available for offline checks.
An external harness is a realization inside that Loop, not a second runtime. OpenCode's
internal subagents are not automatically canonical Spawned Loops, and its
tool events do not become independently authorized Solution Loops.

A dated repository smoke record reports one completed clamp task with an
independent unittest. It omits exact provider/model identity and does not
qualify today's binary. The archived smoke record names 1.18.25; no fresh binary
version is qualified by the saved evidence for this pass. No model/session run
was performed in this audit. Other SDK harness adapters have implementation
and offline contracts, but their packages were absent in this environment.

The removed raw-host execution path did not freeze or reconcile native tools, skills,
MCP, plugins, global/project configuration, or environment credentials with
Loop Engine admission. OpenCode documents automatic skill discovery and merged
configuration. Its `--auto` behavior can approve requests not explicitly denied.
A working directory and changed-file snapshot are not an operating-system
sandbox. [OpenCode permissions](https://opencode.ai/docs/permissions/),
[skills](https://opencode.ai/docs/skills/),
[configuration](https://opencode.ai/docs/config/).

The removed path also put the full prompt in process arguments, inherited
ambient credentials/configuration, and persisted raw NDJSON. A replacement
needs a private prompt channel, credential/configuration isolation, and a
reviewed raw-event privacy policy before execution is enabled.

The older `opencode_client.py` wrapper remains mapped as a refusal-only
compatibility shim and has no observed non-test caller. It cannot provide a
second live path around canonical harness contracts. Broad use requires a pinned
hermetic execution profile, approved configuration and tools, environment
allowlisting, sandboxed mounts/network, cancellation of descendants, bounded
accounting, and private/redacted raw events. Native discovery is not admission.
This follow-up removes unsafe execution; it does not qualify a replacement.

## Alternatives to OpenCode

Primary maintainer documentation was reviewed on 2026-09-04. The entries below
describe upstream interfaces, not installed Loop Engine capabilities or a fair
performance comparison. Recheck and pin package, CLI, and server versions before
implementation. Documentation retrieval does not establish binary qualification.

| Option | Useful integration surface | Boundary to test |
|---|---|---|
| [OpenHands SDK](https://docs.openhands.dev/sdk/getting-started) | Python coding delegate, tools, MCP, skills, persistent conversations, local/container/remote workspaces | Use an actual sandboxed workspace. Direct `execute_tool()` bypasses conversation confirmation; do not expose it as an approval escape. [Workspace](https://docs.openhands.dev/sdk/arch/workspace), [security](https://docs.openhands.dev/sdk/guides/security) |
| [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) | Python and TypeScript thread/session integration for coding work | Bind streamed command/file approvals to exact Loop effects. App-server permissions and session grants need explicit translation. [App server](https://learn.chatgpt.com/docs/app-server) |
| [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) | Python/TypeScript tools, hooks, skills, MCP, subagents and resumable sessions | Freeze setting sources and MCP configuration. `allowed_tools` auto-approval is not a security allowlist; qualify sandbox and escape policy separately. [Permissions](https://code.claude.com/docs/en/agent-sdk/permissions), [sandbox](https://code.claude.com/docs/en/sandboxing) |
| [Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md) | TypeScript SDK or JSONL RPC, model-provider choices, extensions, skills and sessions | The core does not supply an MCP or permission system. Supply and test the host security boundary; pin the current package identity. |
| [Pydantic AI](https://pydantic.dev/docs/ai/overview/) | Typed tools/results, dependency injection and deferred approvals | Keep typed validation separate from semantic correctness. Its local shell is not an OS sandbox. [Shell boundary](https://pydantic.dev/docs/ai/harness/shell/) |
| [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) | Longer work with filesystem context, delegation and durable LangGraph state | Virtual files alone do not isolate command execution; test the selected [sandbox backend](https://docs.langchain.com/oss/python/deepagents/sandboxes). |
| [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents) | Agent/tool loops, handoffs and application state | Distinct from Codex SDK. The host still supplies tool authority, deployment and approvals. |
| [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/) | Typed workflows, sessions, MCP and human approval patterns | Map workflow state and checkpoints without creating a second canonical Loop graph. Workflow support is not OS isolation. |

The proposed first full coding-adapter experiment is OpenHands because the
Python and Docker workspace interfaces fit the current repository. This is an
integration-cost inference, not a model-quality ranking. Codex SDK and Claude
Agent SDK are useful controlled alternatives. Pi is a smaller extensibility
experiment with more host-side security work.

Do not put a full coding harness inside every small responsibility. A direct
provider call, qualified deterministic capability, or bounded SDK delegate may
be sufficient. Selection remains task-conditioned semantic work. Industry names
and harness names do not select a predefined solution graph.

The local follow-up makes adapter registration open-ended while keeping one
`Loop`. Requests carry typed mechanics requirements and capability checks refuse
unsupported work before dispatch. The existing four SDK adapters remain bounded
subsets. No OpenHands, Codex SDK, Claude Agent SDK, or Pi integration was added,
installed, or run in this pass.

Qualification must falsify each proposed benefit: replay the same frozen task
and approved capabilities, inject denied writes/network and cancellation, check
all model/tool attempts and output bytes, then independently verify the result.
Changing the harness must not change task authority, hidden fixtures, or the
assisted/fresh control population. Report unsupported guarantees as refusals.

## Memory ABI: compose existing contracts

Memory meaning, storage location, reference identity, grants, communication,
and model-visible context are different dimensions. The repository already
implements parts of this separation:

| Concern | Existing authority | Missing or incomplete enforcement |
|---|---|---|
| Value versus location | `LoopValueRef`, `InformationStorageBinding`, `InformationResolver` | Immutable materialization across every boundary; opaque-handle rejection |
| Memory meaning | Working, episodic, semantic and procedural memory contracts | Additional roles should be facets, not a new combined enum or registry |
| Scope and lifetime | `InformationScope`, `InformationDurability`, memory lifecycle | Project identity, grant issuance, expiry and revocation are incomplete |
| Communication | `LoopPortValue`, delegation, reactive outputs | Live ports permit arbitrary Python objects; durable rejection can occur only at checkpoint serialization |
| Context | Work packets, context manifests and artifact references | Model exposure still requires exact hydration/packet evidence, not a reference alone |
| Trusted mutation | Semantic snapshots, verification, authorization and CAS | Adapter-wide prohibition on holding transactions across model calls is not established |

In-memory probes reproduced three gaps in the initial storage review: mutable
inline aliases, working-memory restore without digest/capacity revalidation,
and run-note dictionaries that could change through returned aliases. The
follow-up closes those bounded gaps with owned plain-data snapshots, defensive
reads, and transactional restore validation before state replacement. Opaque
handles, cycles and non-finite JSON values are refused at these boundaries.
The current snapshot/v1 format still lacks historical eviction priorities and
ordering metadata, so restored contents do not prove exact execution replay.

Do not pass live database connections or ORM sessions as durable data. Keep
services in internal runtime bindings. Pass small admitted exact values,
revision-bound record references, immutable artifacts, or bounded query
results. A future stream token needs schema, ownership, lease, ordering,
checkpoint and cancellation semantics; a Python cursor is not that token.

PostgreSQL exported snapshot identifiers are importable only while the
exporting transaction remains open. They are not durable portable bookmarks.
For a no-transaction-across-LLM rule, materialize selected immutable data during
a short read transaction, close it, reason, then check expected revisions in a
new commit transaction. [PostgreSQL snapshot synchronization](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).

Arrow C Data is a same-process interface with explicit buffer ownership and
release callbacks. Zero-copy is a physical optimization, not a transferable
machine address or proof of immutability. Cross-process/machine use needs an
appropriate transport and lifetime contract.
[Arrow C Data](https://arrow.apache.org/docs/format/CDataInterface.html),
[Arrow IPC](https://arrow.apache.org/docs/format/Columnar.html).

The next memory proof should test granted, revision-bound materialization across
process boundaries before introducing broader frame/grant/stream abstractions.
Do not present the proposed
full Memory ABI, distributed information protocol, or universal storage
migration as implemented.

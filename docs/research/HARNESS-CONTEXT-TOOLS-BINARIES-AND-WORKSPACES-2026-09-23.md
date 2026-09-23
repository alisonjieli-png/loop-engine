# Context, tools, binaries and generated harness directories

Kind: research and integration decisions, September 23, 2026. This extends
the [interoperability review](TASK-PACKAGE-INTEROPERABILITY-AND-QUALIFICATION-2026-09-23.md)
with the owner's wider file inventory and newly checked interfaces. Native
observations, documentary support and proposed behavior remain separate.
The existing roadmap is the task authority.

## The distinctions the package needs to preserve

A file has a role, a format, an activation mechanism and an authority scope.
Those are separate fields. Python can implement a pure calculation or make a
model call. Markdown can be passive reference material or a native startup
instruction. JSON can be ordinary data, a schema or executable-plugin
configuration. None of these extensions establishes the execution mode or
permissions.

| Role | What it contributes | What makes it operational |
|---|---|---|
| Information and reference material | Facts, source extracts, examples, domain definitions | Selected text or media enters context, or an authorized retrieval tool reads it. |
| Procedure or skill | Applicability, method, checks and references | The selected harness discovers and activates the procedure. |
| Contract | Input/output shape, preconditions and acceptance obligations | A named validator and the owning host enforce the applicable rules. |
| Deterministic implementation | A repeatable transformation under declared inputs and environment | A qualified executor invokes it with explicit inputs, limits and effects. |
| Tool interface | A callable name, input contract and result contract | A native tool registry, protocol adapter or explicit process invocation binds that interface. |
| Plugin or extension | Distribution and activation of several components | A qualified native loader interprets its manifest and activates supported components. |
| Run state and output | Current facts, proposed changes and results | The host validates provenance, version and acceptance before making a change current. |

A tool can be implemented by a script, compiled program, library function,
WebAssembly component, container or remote service. A plugin can contain several
of these. A skill may instruct the model to call a tool. The relationships do
not make the package types interchangeable.

## Expanded file inventory

The suggested directories below describe generated workspaces, not new
top-level repository components. Actual native paths belong to a qualified
client profile.

| File or package | Suggested placement | Native handling and required checks |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md` | Selected native entrypoint at the step root | Verify scope, precedence, imports and effective context budget. Generate only the selected client's needed views. |
| `node_context.md` | Read-only context beside the assignment | Explicit launch context or reference. No universal filename discovery. |
| `SKILL.md` with resources | One selected native skill directory | Check frontmatter, name collisions, invocation and all referenced resources. |
| `.mdc`, `.instructions.md`, native rule files | Client-specific rule directory | Match the client's scope/glob rules; ordinary Markdown elsewhere is not equivalent. |
| Agent and command definitions | Native agent/command directories | Profile schema, tool semantics, model authority and actual invocation need separate qualification. |
| Hook configuration and implementations | Native hook registration plus immutable code | Verify event, handler type, interpreter, timeout, trust, invocation and output behavior. |
| Plugin manifests | Native or portable package root | Validate the exact manifest version and refuse unsupported required extensions. |
| Protocol server configuration | Isolated client configuration | Translate the configuration schema; bind executable or remote endpoint and credentials by reference. |
| JSON Schema, OpenAPI, Protocol Buffers | Read-only `contracts/` | Bind the dialect, resolver and actual validator or generated adapter; a schema file alone enforces nothing. |
| CSV, JSON, JSONL, Parquet, SQLite | Read-only `inputs/` or selected reference store | Keep data distinct from instructions. Select a compatible bounded reader or query engine. |
| PDF, office documents, images, audio | Read-only input/reference view | A compatible extractor or multimodal interface must expose useful content; file presence is insufficient. |
| Python, JavaScript, shell or PowerShell scripts | Immutable package `scripts/` or `tools/` | Pin interpreter and dependencies; declare effects and exact invocation. Shell syntax is not portable across operating systems. |
| Native executable (`ELF`, `PE`, `Mach-O`) | Platform-specific immutable package `bin/` | Check operating system, CPU, binary interface, loader, linked libraries and execution policy. |
| Shared library (`.so`, `.dll`, `.dylib`) | Qualified runtime environment | Loading it is code execution. Use the correct calling convention and dependency closure. |
| Python wheel, Java archive, npm package | Prepared immutable environment or cache | Match runtime/ABI and inspect installation/build behavior. A dependency lock does not authorize installation. |
| WebAssembly module/component | Immutable tool package | Bind runtime, interface/world, imports, memory and instruction/time limits. |
| Container image reference | Content-addressed image store | Pin image digest and platform. Materialize only the task's input/output mounts. |
| Lockfiles and dependency manifests | Package root and host preparation record | Verify transitive artifacts, not merely the lockfile's existence. Keep generated environments separate from authored packages. |
| Templates, SQL, notebooks and build files | Declared resource or executable component | Classification depends on how the component is invoked. A notebook or build file can execute code. |
| Tests, fixtures and expected results | Package review materials, selected when needed | Do not confuse passing author-written tests with independent semantic acceptance. |
| Runtime state and candidate outputs | Separate task-state view and writable output paths | Bind run/attempt identity and expected state version; reject stale or foreign results. |
| Credentials and private machine configuration | Host credential manager or scoped broker | Exclude raw secrets from shared packages, prompts, locks and public search metadata. |

For the active catalogue, map these to the existing `CataloguePackageFile`
roles and harness item kinds. Where a role is missing, add a reviewed typed
extension. A descriptive category must never grant execution authority.
The existing package limit is 64 files and 32 MiB; larger runtime environments
need a separately qualified pinned dependency mechanism rather than silent
limit expansion.

## Executable compatibility is broader than harness compatibility

For a compiled tool, record the source identity, build recipe and toolchain,
artifact digest, target operating system and CPU, required CPU features,
runtime/ABI, dynamic dependencies, entrypoint, input/output protocol, effects
and independent tests. The package can be compatible with a harness's tool
interface while incompatible with the machine that runs it.

Python wheel tags explicitly distinguish interpreter, binary interface and
platform. A generic Python tag does not make an included native extension
portable. [Python packaging compatibility tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/).
Container manifests and indexes also distinguish specific platform images
from multi-platform collections. Pin the selected manifest digest, not just
a mutable image tag. [OCI image manifest](https://github.com/opencontainers/image-spec/blob/main/manifest.md),
[image configuration](https://github.com/opencontainers/image-spec/blob/main/config.md).

WebAssembly is worth a bounded comparison for small deterministic tools.
Wasmtime's filesystem interface uses explicit capabilities. The host still
owns the imports it supplies and the resources it exposes.
[Wasmtime security model](https://docs.wasmtime.dev/security.html).
Proposed qualification should compare the same operation in a Python process,
a native executable and WebAssembly, including cold start, warm start,
serialization, accepted results and cleanup. No speed advantage is asserted
before those measurements.

Reproducible build controls can help establish where a binary came from.
For example, `SOURCE_DATE_EPOCH` standardizes a build timestamp input.
It does not prove identical runtime results or make an unreviewed executable
safe. [Timestamp specification](https://reproducible-builds.org/specs/source-date-epoch/).
Likewise, signatures establish signed artifact identity, and a bill of
materials describes dependencies; neither substitutes for task acceptance.

## Workspace ownership and lifecycle

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

Use the existing persistent task working folder with scoped attempt views.
Fresh writable outputs do not require deleting useful task artifacts between
attempts. Conversation identity, process identity, workspace identity and
committed state identity must remain separate.

```text
Host-controlled task space
├── selected immutable packages and input artifacts
├── committed state and exact selected input versions
├── preparation and execution records outside worker write access
└── attempt views
    ├── native instructions and configuration: read only
    ├── inputs/ and contracts/: read only
    ├── selected package resources: read only
    ├── outputs/ and scratch/: bounded writable space
    └── optional source checkout: separately writable work product
```

The filesystem policy must enforce those views. Merely placing a lock file
in a sibling directory or marking a file read-only in prose does not create
that boundary. Use separate mutable outputs for parallel attempts. Share
immutable packages by verified content identity; do not depend on an
uncontrolled symlink into a mutable user directory.

The owner's suggested manifest, lock and execution record answer useful
different questions. Map them onto existing assignment/provisioning,
package/placement and Run History contracts. The proposed `.baltor/step.json`
and `baltor.step/v1` examples are not active native or Loop Engine formats.
Avoid introducing a second task authority merely to copy those filenames.

A deterministic tool may run through the existing deterministic executor when
it satisfies the task contract. It remains owned by a canonical Loop. There
is no need to add a model call for graph symmetry, nor to discard the existing
runtime and create a second orchestration system.

## Version-specific findings that update the earlier comparison

### OpenCode V1 and V2 need distinct profiles

The earlier local observation used OpenCode 1.18.32, and the source review
inspected its V1 implementation paths. Official V2 documentation now describes
different behavior: `AGENTS.md` without a Claude fallback, and an accepted
`instructions` array whose references are not currently loaded. Keep mandatory
context in the active entrypoint or explicit task input.
[V2 instructions](https://opencode.ai/v2/docs/instructions).

V2 protocol servers live under `mcp.servers`; `disabled` replaces the earlier
enablement field. A same-name higher-precedence server entry replaces the
whole server object. The connection protocol is explicitly configurable.
[V2 protocol servers](https://opencode.ai/v2/docs/mcp-servers).
These are documentary findings, not a V2 native run. Reject a V1 rendering
for an unqualified V2 profile rather than guessing equivalent fields.

### Claude's bare mode changes both discovery and authentication

Bare mode skips automatic discovery and permits explicit additions, but does
not use subscription OAuth or the system keychain. Normal print mode has
different startup behavior, including repository hooks and server setup.
Therefore, keep separate API-backed bare and subscription-backed profiles;
do not select bare mode as a universal isolation shortcut.
[Programmatic Claude Code](https://code.claude.com/docs/en/headless).
Neither profile by itself proves filesystem or network confinement.

Gemini also exposes an explicit upward-memory boundary setting; an empty
`context.memoryBoundaryMarkers` list disables parent traversal. It does not
remove every global configuration, built-in tool or managed policy.
[Gemini configuration](https://geminicli.com/docs/reference/configuration/).

### Completion is a versioned protocol contract

Agent Client Protocol version two acknowledges prompt acceptance and later
reports foreground completion through an idle state update. Version one's
prompt response follows a different lifecycle. Keep the negotiated version
and terminal rule in the adapter; a successful submission is not an accepted
task result. [Version two lifecycle](https://agentclientprotocol.com/protocol/v2/overview),
[version one lifecycle](https://agentclientprotocol.com/protocol/v1/prompt-turn).
Background work and unresolved external effects still need explicit handling.

## Reuse candidates and decisions

| Candidate | Useful contribution | Decision and qualification needed |
|---|---|---|
| Codex Python SDK | Local application-server control and a pinned runtime dependency | Evaluate as a native engine behind the existing Python host boundary; record both SDK and bundled binary versions. |
| Native Agent Client Protocol clients and adapters | Session input, permissions, updates and cancellation | Preserve the existing protocol-first direction where the required capabilities are available; use native alternatives when necessary. |
| `openclaw/acpx` | Common headless client and session handling | Evaluate a pinned one-shot path; default persistent sessions are not the fresh-step policy. |
| Vercel `HarnessAgent` | A shared harness interface and multiple adapters | Track as a swappable integration engine, with runtime/sandbox/authentication assumptions tested explicitly. |
| Skill installers | Existing native placement knowledge | Reuse qualified layout logic while retaining Baltor's exact versions, complete tree and admission policy. |

The official Codex documentation confirms stable `openai-codex` Python builds
with a pinned command-line runtime and application-server transport.
[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk).
`acpx` describes itself as pre-1.0 and offers both persistent sessions and
one-shot execution. [Project documentation](https://github.com/openclaw/acpx).

The original Vercel announcement called the harness packages experimental.
A later September 10 update lists more adapters, including Copilot through
Agent Client Protocol; the earlier three-adapter list is no longer complete.
[Initial announcement](https://vercel.com/changelog/program-agent-harnesses-with-ai-sdk),
[adapter update](https://vercel.com/changelog/github-copilot-ai-sdk-harness-adapter).
Its September 14 authentication update also makes credential-source ordering
an explicit comparison point for our scoped broker design.
[Authentication update](https://vercel.com/changelog/ai-sdk-harness-native-subscription-authentication).

## Decisions for the 10,000-file initiative

1. Generate complete useful packages across file roles. Keep logical methods,
   native renderings, physical paths and unique byte digests as separate counts.
2. Start qualification with text and bounded standard-library tools. Compiled
   binaries, plugin hooks and binary assets need their own review and execution
   engines; unsupported required components remain candidates.
3. Extend the current package and native-layout contracts with activation,
   platform/runtime requirements and observed evidence. Keep harness identity
   separate from model-provider identity.
4. Preserve exact original source, dependency and build records. Automatic
   extraction, installation or compilation must occur under declared authority.
5. Let search expose applicability and compatibility facts without loading every
   body into a harness. Materialize only the complete selected dependency set.
6. Keep requirements, native resolution and evidence separate. A capability may
   be native, translated or externally enforced, with documented, observed or
   missing evidence. Required unknown behavior must not be presented as ready.
7. Test negative cases: unsupported CPU/ABI, missing interpreter, ignored
   configuration, unselected global material, stale state, changed executable,
   missing helper, invalid output and cancellation with unfinished effects.

The research supports these decisions. It does not certify a new runtime,
binary, SDK or complete customer journey. Current source, native version and
independent task evidence remain the admission and deployment gates.

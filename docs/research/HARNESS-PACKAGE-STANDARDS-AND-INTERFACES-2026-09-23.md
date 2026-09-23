# Task packets and harness packages: standards and interfaces

Research date: September 23, 2026. Source checkout:
`abcad4f8ce346e7d0759ccad703e0111574148a6`, with the separately recorded
September 23 candidate artifacts. This is an engineering proposal and source
review. It changes no runtime, installs nothing and calls no model. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority.

## Recommendation

Keep one typed assignment and one reviewed identity for each reusable package.
Generate a native view for the exact harness and interface being used. Put the
objective, first actions, constraints and output requirements into a channel
that the selected harness demonstrably receives at startup. Keep larger
material behind explicit, digest-bound references. A filename alone does not
establish discovery, loading, execution or usefulness.

Task packets carry the current work. Library packages supply reusable
capabilities. They can travel together, but should retain separate identities,
review lifecycles and counts. An instance-specific state snapshot is not a new
approved library package.

## What the standards actually cover

All external pages below were opened on September 23, 2026. Documentation is
evidence of a declared interface; installed-client qualification is separate.

| Interface | Verified status and purpose | What Baltor must still supply |
|---|---|---|
| [AGENTS.md](https://agents.md/) | Open Markdown instruction convention; no required fields. The site describes root and nested instructions. | Exact client discovery behavior, hierarchy, limits and whether user or ancestor instructions changed the effective briefing. The public convention is not an execution permission mechanism. |
| [Agent Skills](https://agentskills.io/specification) | A skill is a directory with `SKILL.md`; optional scripts, references and assets carry supporting material. Metadata precedes activation; full instructions and resources are loaded as needed. | Native placement, invocation, dependencies, execution permission, applicability and output acceptance. A valid skill does not prove its scripts run on the target. |
| [Agent Plugins 1.0.0](https://agent-plugins.org/specification) | Published portable package format. Root `plugin.json`, `skills/` and `mcp.json`; portable components are skills and Model Context Protocol server entries. | Hooks, commands and agent definitions need client-specific adaptation. Package conformance does not grant execution authority. |
| [Model Context Protocol 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) | Current protocol for resources, prompts and tools. | Local file placement, package installation and host activation. A returned file or resource is not automatically written into a harness folder. |
| [Skills over Model Context Protocol](https://modelcontextprotocol.io/extensions/skills/overview) | Published official extension, `io.modelcontextprotocol/skills`; implementation support is still developing. | The client must implement its loading path. It covers skills and their files, not arbitrary task-packet or plugin installation. |
| [Agent Client Protocol version 1](https://agentclientprotocol.com/protocol/v1/session-setup) | Session creation with a working directory and server connections; conversation continuation is separately capability-controlled. | Process freshness, sandboxing, actual instruction discovery and exact selected package identity. A new protocol session alone does not prove a new operating-system process. |
| [Agent2Agent 1.0.0](https://a2a-protocol.org/v1.0.0/specification/) | Released remote delegation protocol with tasks, messages and artifacts. | Map remote results into existing task contracts and independently evaluate them. An external task identifier does not introduce a second Loop Engine runtime. |
| [JSON Schema 2020-12](https://json-schema.org/draft/2020-12) | Published JSON Schema dialect suitable for explicit data contracts. | Semantic acceptance, authorization and effect controls. Schema validation alone cannot establish that a result solves the task. |

### Agent Plugins is useful, but its scope is small

Version 1.0.0 validates the declared schema locally, confines package paths,
and defines fixed discovery locations. It isolates invalid components and
requires clients to ignore unsupported component types. Client extensions use
namespaces. The specification does not make plugin subprocesses sandboxed.
`PLUGIN_ROOT` and `PLUGIN_DATA` distinguish supplied files and client-managed
writable data. Secret values are not portable package configuration.
[Published specification](https://agent-plugins.org/specification).

The upstream [1.1.0 document](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.1.0.md)
is explicitly a working draft. Do not silently target it. The project's
[compatible-client directory](https://agent-plugins.org/compatible-clients)
lists Visual Studio Code, Cursor, GitHub Copilot, ChatGPT and Codex, Kiro,
Hermes Agent and OpenClaw, with different transport support. This is a
documentation inventory, not a qualification result for our package.

The practical proposal is two deliverables from the same approved source:
a portable skills/server package where applicable, and explicit native views
for additional behaviors. A package requiring a startup hook must be refused
for an adapter that cannot run that hook. Silently ignoring it would satisfy
some generic discovery rules while breaking the task's required semantics.

### Native plugin formats and distribution are distinct

Claude Code documents `.claude-plugin/plugin.json` and native components such
as skills, agents, hooks and server configurations. Its manifest and paths
are not interchangeable with the portable root manifest.
[Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference).

OpenAI's current package guide uses the portable root `plugin.json` and
`extensions.com.openai`. When that extension is an object, it replaces the
entire compatibility `.codex-plugin/plugin.json` overlay rather than merging
fields. Hooks require their own trust review and an execution environment
containing their scripts. Enabling a plugin does not establish that trust.
[OpenAI package guide](https://developers.openai.com/plugins/build/plugins).

OpenAI's Claude-plugin submission guide converts reusable command and agent
behavior into skills. Its skills-only upload does not preserve server
configuration; its remote-server route requires a separately submitted
reachable service. Command hooks require adaptation; prompt and agent hook
handlers are unsupported by that Codex runtime.
[Conversion guide](https://developers.openai.com/plugins/guides/submit-claude-plugin).

Therefore, preserve the current native Claude candidate as its own rendering.
Do not flatten its review agent into a skill and call the behavior unchanged.
For a second rendering, specify whether isolation, tool restrictions, turn
limits and the startup event are preserved. Measure any losses. A public
directory submission is an additional distribution gate; a local working
package does not require us to submit it there first.

## Protocol delivery without guessing

### Model Context Protocol

Resources expose text or binary content under a URI, and the host chooses how
to include that content. A `file://` resource need not map to a real local
file. Consequently, Baltor's client still needs an authorized materializer
that verifies bytes and writes the selected native layout.
[Resources specification](https://modelcontextprotocol.io/specification/2026-07-28/server/resources).

Prompts are templated messages; tools are functions. A search or download tool
can return our package reference, while a resource can expose its selected
files. None of these primitives by itself installs a plugin. Tool input and
output schemas support structural validation, while tool annotations must not
be treated as independent proof of trust.
[Protocol overview](https://modelcontextprotocol.io/specification/2026-07-28),
[tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools).

The current protocol revision is **2026-07-28**, verified on the official
[versioning page](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning).
It uses request-level protocol metadata and `server/discover`. The
[change record](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
removes the earlier initialization handshake and protocol-level HTTP session
identifier. This is a real semantic change. Updating a version string inside
an existing handshake-based adapter would be wrong. Baltor has already shipped
both revisions: [roadmap step S-6.43](../roadmap/roadmap.yaml) records live
qualification in Fly release 15, and the [service protocol implementation](../../src/loop_engine/core/service_runtime/README.md#model-context-protocol-versions)
selects their distinct semantics. Preserve that distinction during future
adapter changes. Qualify only explicitly supported deployed combinations and
refuse a binding that loses required semantics. Native-client coverage at each
revision remains separate from the hosted service checks. The new Skills
extension below is not established by the shipped base-protocol support.

### Skills over Model Context Protocol deserves an experiment

The official extension defines `skills/list`, `skills/get` and optional
`resources/directory/read`; it supplies file manifests and digests while
reusing `resources/read`. It targets base revision 2026-07-28. A plain read
does not activate a skill: the host must verify and load it through the
appropriate path. The source describes its stable specification as a released
snapshot. [Extension specification](https://github.com/modelcontextprotocol/ext-skills/blob/main/specification/stable/skills.mdx),
[repository status](https://github.com/modelcontextprotocol/ext-skills).

The official [extension support matrix](https://modelcontextprotocol.io/extensions/client-matrix)
currently marks ChatGPT, fast-agent and Model Context Protocol Inspector as
partial implementations. Blank cells do not establish unsupported behavior.
The matrix itself is community maintained. This path should initially be an
opt-in interoperability experiment, with the existing authenticated download
and local placement path retained for explicitly eligible clients.

There is also a distinct distribution workflow: OpenAI's plugin submission
portal imports server-hosted skills when the publisher selects Scan Tools.
The imported files become a draft snapshot; that workflow does not fetch them
from the server at runtime. Later source changes require another scan and
plugin release. This does not establish live extension support in a particular
ChatGPT or Codex session. [OpenAI skill import workflow](https://developers.openai.com/plugins/build/skills).
Qualify server capability declaration, method behavior and host loading
separately from this submission process.

Proposed comparison: serve the same approved skill package through both paths,
hold its bytes and task fixed, and record discovery, retrieval, activation,
script invocation and acceptance independently. The extension can reduce
custom delivery work for supporting hosts. It cannot replace delivery of a
tool-only package, task state or an arbitrary native plugin.

### Agent Client Protocol

After compatibility initialization, `session/new` accepts the session working
directory and Model Context Protocol server configurations. Optional session
loading or resuming preserves prior context; it should not be selected for a
fresh-step experiment by accident.
[Session setup](https://agentclientprotocol.com/protocol/v1/session-setup).

`session/prompt` can send a text briefing. Text is mandatory; embedded resources
require the `embeddedContext` capability. Resource links are references, not
proof the receiver fetched them. The content shape's relationship to Model
Context Protocol does not imply that every revision of the two protocols is
wire-compatible. [Content specification](https://agentclientprotocol.com/protocol/v1/content),
[prompt turn](https://agentclientprotocol.com/protocol/v1/prompt-turn).

Proposed initial route: send the compact essential assignment as a text block,
then use embedded selected context when advertised, or a verified readable
reference when it is sufficient. Materialize executable and dependency files
separately. Before dispatch, bind the session identifier, process instance,
working directory, package digests, state version and effective authority in
the existing run records. Reject unsupported required capabilities before
starting model work. Native discovery is a separate qualification probe.

### Agent2Agent

Agent2Agent transports messages, task status and output artifacts between
independent agents. Its released 1.0.0 specification distinguishes task output
artifacts from messages and warns that transient messages need not survive
reconnection. It identifies protocol compatibility by major/minor version.
[Versioned specification](https://a2a-protocol.org/v1.0.0/specification/).

Use this later for delegating bounded work to a separately operated agent
service. A remote service can receive task material and return files or data
without sharing its private session memory. Our adapter must still validate
artifact digests, schema, tenant/run association, external effects and
acceptance. Do not introduce Agent2Agent just to copy local files into a
working directory; the existing local placement boundary is enough.

## Existing architectural owners

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

The following are passive records and internal mechanics, not additional
execution vertices:

```text
Assignment material and delivery
├── Existing assignment and instruction composition
│   ├── current task, first actions and acceptance requirements
│   └── native entrypoint or explicit prompt rendering
├── Existing catalogue package and body-store contracts
│   ├── reviewed reusable files, exact versions and dependencies
│   └── per-file and whole-package integrity
├── Existing provisioning and harness adapter boundary
│   ├── confined placement and qualified discovery
│   └── native launch or Agent Client Protocol delivery
└── Existing state, authority and run records
    ├── immutable input snapshot and bounded candidate updates
    └── output validation, effects and independent acceptance
```

| Responsibility | Existing owner to extend | Observed limit or proposed addition |
|---|---|---|
| Assignment | `NodeAssignment` in [node_provisioning.py](../../src/loop_engine/core/node_provisioning.py) | Preserve its versioned task identity. First actions and full context are demonstrated in the candidate renderer, not automatically integrated into every production launch. |
| Native instructions | `AssignmentBriefing`, `InstructionSection`, `compose`, `write`, `verify` in [instance_instructions.py](../../src/loop_engine/core/instance_instructions.py) | Extend the style data and tests; do not create a second instruction writer. Unknown-style fallback must not count as qualified discovery. |
| Multi-file package identity | `CataloguePackage`, `CataloguePackageFile`, `CatalogueBodyStore` in [catalogue_packages.py](../../src/loop_engine/core/service_runtime/catalogue_packages.py) | Already represents declared roles, paths, media types, sizes and digests. Add only missing required-capability or adapter bindings through the existing package/admission contracts. |
| Native placement | [Harness-instance layout guide](../guides/harness-instance-context-layout.md) and the existing provisioner | Keep preparation authority separate from execution authority. Empty folders and offered references do not establish installed bodies. |
| Harness execution | [External harness adapter edge](../components/core-architecture/EXTERNAL-HARNESS-ADAPTERS.md) | Select engines by exact version, capabilities and evidence; process recipes and Agent Client Protocol remain behind the same owning edge. |
| State | `TrustedStateSnapshot` and existing semantic runtime records | Keep `run-state.json` as a read-only view of host state. Candidate updates need expected-version checks; no model-controlled file can expand authority. |
| Tools and connections | [Model Context Protocol and skill adapters](../components/core-architecture/MCP-AND-SKILLS.md) | Bind explicit endpoints, credentials by reference and effects. Package metadata never authorizes a server launch. |

The [focused-step packet](../../artifacts/focused-step-packet-2026-09-23/README.md)
and [native plugin candidate](../../artifacts/harness-plugin-context-2026-09-23/README.md)
are concrete starting material. Their existing tests should become fixtures
for adapter qualification, not evidence of every harness's behavior.

## Improvements to specify before broad generation

1. **Separate essential briefing from optional material.** Keep the objective,
   current input, first action, stopping condition and required output visible
   without a search. Add larger context when a task needs it. Compare compact
   and expanded variants on acceptance, cost and latency; do not impose one
   universally smallest briefing.
2. **Declare activation, not just placement.** Each required component needs a
   typed activation method: startup instruction, explicit skill invocation,
   named tool registration, command, hook event or plain supporting file.
   Store unsupported and skipped outcomes explicitly.
3. **Distinguish readable from executable files.** A schema is data; a hook can
   execute. A plugin containing both cannot become eligible merely because
   its Markdown passed review. Bind runtime, interpreter, platform,
   dependency versions, network needs and time limits.
4. **Preserve package root and source identity.** Resolve all file references
   from their declared root, verify exact bytes before placement, reject
   traversal and case-colliding paths, and keep writable work outside immutable
   reviewed content. A failed helper download must not leave an apparently
   installed skill.
5. **Keep state explicit and scoped.** `node_context.md`, `agents.state` and
   `run-state.json` have no universal loading semantics in the standards
   reviewed. Use an explicit input contract and adapter. Carry unresolved
   external effects forward so a fresh process cannot accidentally repeat one.
6. **Make selection aware of requirements.** Rank eligible packages using task,
   domain, harness version, platform, model evidence and budget. Keep required
   dependencies intact when condensing wording. A model-specific rewrite is a
   new candidate digest and requires its own review.
7. **Record effective inherited context.** User configuration, ancestor
   instructions, plugin trust and default tools can alter a supposedly fresh
   step. Qualification should record them or use a declared isolated profile.
   Do not erase customer project instructions to make a test pass.
8. **Validate independently of the model's output mode.** The candidate packet
   uses JSON Schema 2020-12. Pin its dialect and validator; do not assume a
   provider's structured-output subset supports every keyword. `format` can
   be annotation rather than assertion, so required semantic checks need
   explicit enforcement. [Core](https://json-schema.org/draft/2020-12/json-schema-core),
   [validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation).

## Configuration choices and discriminating tests

These proposed dimensions extend the existing
[configuration requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
and [layered-control direction](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
They are not new permission grants or a second roadmap.

| Dimension and owner | Initial choice | Ordered eligible alternatives | Test that distinguishes failure |
|---|---|---|---|
| Essential briefing, instruction composer | Explicit launch text for API-controlled steps; verified native entrypoint for manual folder entry | Embedded context if advertised; a verified explicit file read only when the essential launch assignment is already available; typed refusal | Remove the native entrypoint or prompt block while leaving `node_context.md`; the observed briefing must lose the planted task marker. |
| Reusable package delivery, provisioner | Complete approved native folder, exact digests | Supported portable plugin; qualified Skills over Model Context Protocol for a skill; typed refusal | Omit a referenced helper, change a byte or escape the root; no installed/ready result. |
| Required native behavior, harness adapter | Exact supported command, hook or agent definition | An independently qualified equivalent engine under the same contract; typed refusal | Disable the required hook or agent component; package must not be reported fully ready. |
| Task state, existing state owner | Bound immutable snapshot | Authorized fresh snapshot after version conflict; bounded candidate continuation; refuse stale commit | Two harnesses submit from the same state version; only the permitted next revision can become current. |
| Protocol revision, connection adapter | Exact qualified revision and capabilities | Explicit mutually supported revision preserving required semantics; fail closed | New-protocol metadata sent to old handshake engine, or missing required extension, fails before tools execute. |
| Context quantity, selection/framing | Task-specific selected evidence | More evidence, a different representation or qualified model-specific rendering within authority | Expanded and compact forms must retain critical constraints; measure task acceptance and total cost for both. |
| Failure ownership, wrapper boundary | One owner for retries and cancellation | Explicit handoff carrying remaining budget and unresolved effects | Cancel during startup or disconnect after an effect; no hidden second retry and no duplicate effect. |

Add positive, negative, ambiguous and unrelated tasks to each native-client
qualification. A client should not trigger an unrelated skill merely because
the package is installed. Use a controlled tool invocation or required output
to distinguish listed, loaded and used. Keep no-model discovery tests separate
from provider-backed task trials and independent result acceptance.

## Research limits

No new client was installed or launched during this standards review. No
claim here establishes service deployment, universal plugin portability or
support by a particular installed binary. Several official pages use rolling
URLs, so release qualification must pin source revisions and observed client
versions. Recheck these pages when protocol or client versions change; record
changed semantics before updating adapters. Source metadata for this review is
in the [standards source inventory](../../artifacts/harness-package-interoperability-2026-09-23/standards/sources.json).

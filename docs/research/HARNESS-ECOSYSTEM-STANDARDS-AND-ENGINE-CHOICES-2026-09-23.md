# Harness ecosystem standards and engine choices

Research checked September 23, 2026. This extends the
[OpenMuse source audit](OPENMUSE-COMPONENT-ENGINE-REUSE-2026-09-23.md),
[Agent Harness source audit](MADEBYWILD-AGENT-HARNESS-ARCHITECTURE-AND-OWNERSHIP-2026-09-23.md)
and [Harness Working Directory Compiler hierarchy](HARNESS-MATERIAL-HIERARCHY-AND-COMPILER-ENGINES-2026-09-23.md).
The classification tree and existing component ownership in those reports apply.
These documentary findings do not certify installed integrations or authorize
external effects. The roadmap remains the task authority.

## Decisions that change our integration work

**Use distinct standards for distinct jobs.** File packaging, tool invocation,
session control, deployment, provenance, user interaction and task acceptance
have different contracts. Reusing one does not satisfy the others.

**Keep a typed capability with several execution bindings.** One deterministic
operation may be a direct Python function, an executable, an HTTP endpoint, an
MCP tool or a WebAssembly plugin. The wrapper translates an invocation; the
operation's input/output, effects and independent acceptance remain explicit.
A reasoning workflow can select that same operation without rewriting it as
prompt prose or making its implementation model-dependent.

**Wrap external engines at the existing boundary.** A reused library, process
or service and Baltor's own engine implement the same supported contract and
run the same conformance cases. The native engine need not reproduce unrelated
features from the whole upstream application. Required semantic differences
must appear as capabilities or refusals, not hidden defaults.

## Standards map

| Question | Standard or project | Baltor treatment |
| --- | --- | --- |
| How is a reusable procedure packaged? | [Agent Skills](https://agentskills.io/specification) | Preserve `SKILL.md` metadata and resources; qualify native discovery/activation separately |
| How are portable plugins described? | [Agent Plugins 1.0.0](https://agent-plugins.org/specification) | Published portable core covers skills and MCP; required native extensions need host-specific qualification |
| How is a local protocol server distributed? | [MCP Bundles](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md) | Archive plus manifest for compatible loaders, with explicit server type, runtime and configuration |
| How does an agent invoke tools or read resources? | [MCP specification](https://modelcontextprotocol.io/specification/2026-07-28) | Negotiate the actual supported revision and capabilities; record transport/authentication independently |
| How is an agent session controlled? | [Agent Client Protocol](https://agentclientprotocol.com/protocol/v2/overview) | Keep version-specific acceptance, completion, cancellation and permissions in executor adapters |
| How are independent agents contacted? | [Agent2Agent](https://a2a-protocol.org/latest/) | Service discovery and task/artifact exchange; remote skill descriptions are not installed Skill packages |
| How is a dependency named? | [Package URL](https://github.com/package-url/purl-spec) | Package identity complements exact version, repository identity and content digest |
| How are arbitrary artifacts distributed? | [OCI and ORAS](https://oras.land/docs/concepts/artifact/) | Blob/manifests plus media types; no assumption that every artifact is a runnable container |
| What is in a release? | [SPDX](https://spdx.dev/use/specifications/) and [CycloneDX](https://cyclonedx.org/specification/overview/) | Export dependency/license inventory through adapters; inventory does not prove rights clearance or correctness |
| Where did a build come from? | [SLSA provenance](https://slsa.dev/spec/v1.2/provenance) | Record source/build lineage and evaluate the trusted builder and predicate |
| Who signed the artifact? | [Sigstore](https://docs.sigstore.dev/about/overview/) | Verify expected identity, issuer and artifact digest; a valid signature is not functional admission |
| How does the interface exchange events? | [AG-UI](https://docs.ag-ui.com/introduction) | Presentation transport over existing authoritative run records |
| How is a generated interface described? | [A2UI](https://github.com/a2ui-project/a2ui) | Declarative user-interface description for supporting renderers; actions still need authorization |
| How does a tool show an interactive interface? | [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) | Optional embedded application surface; qualify host support and data boundaries |
| How are agent trajectories exchanged? | [Harbor ATIF](https://docs.harborframework.com/core-concepts/agents/atif) | Export normalized history with losses reported; importing history is not portable executable session restoration |
| How is work observed? | [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai) | Versioned telemetry mapping, with sensitive bodies excluded by default; preserve canonical Run History |

The MCP Bundles repository has moved from `anthropics/mcpb` to
`modelcontextprotocol/mcpb`. It describes bundles as archives containing a local
server and manifest, including binary server forms. The binary must implement
the protocol or be wrapped by an implementation that does. Dropping an arbitrary
`.mcpb` into a working directory does not imply automatic CLI discovery.
[Bundle project](https://github.com/modelcontextprotocol/mcpb).

Agent Plugins specifies local selection of supported schemas; conforming loaders
must not fetch schema URLs during plugin loading. This is a useful pattern for
Baltor: a schema identifier selects a locally qualified interpretation. Unknown
required behavior must be refused before effects. Native namespaces remain
separate from portable guarantees.
[Plugin specification](https://agent-plugins.org/specification).

The former OpenTelemetry GenAI documentation page now points to a separate
repository and says the old page is no longer maintained. Track the exact
convention revision used by an exporter. A familiar documentation URL can be
stale even when it still returns a page.
[Moved documentation](https://opentelemetry.io/docs/specs/semconv/gen-ai/).

## Reusable engines with concrete qualifications

### FastMCP: selective tool exposure

FastMCP's OpenAPI conversion exposes every endpoint as a tool by default. Its
ordered route maps can change or exclude operations. Names are normalized and
can be truncated or suffixed to resolve collisions. Baltor should select exact
operations, bind resulting names back to operation identities, and apply the
step's authority before exposing tools. A GET operation is not automatically
safe merely because it uses GET. Test omitted endpoints and names that normalize
to the same value.
[OpenAPI integration](https://gofastmcp.com/integrations/openapi).

### Harbor: a useful compatibility and acceptance lab

Harbor documents separate capabilities for native configuration, skills, protocol
server configuration, trajectory export, native session restoration and resume.
Its documentation explicitly says passing MCP configuration does not guarantee
server connectivity. Reuse this separation in Baltor's evidence records. A
configured endpoint requires a separate authenticated tool-list/invocation test.
[Agent capability matrix](https://docs.harborframework.com/core-concepts/agents/pre-integrated-agents).

Use a frozen package/task population and independent verifiers to compare direct
compilation with Agent Harness rendering. Preserve the native event stream and
an ATIF projection. A trajectory can assist debugging or later context loading;
it cannot restore a missing filesystem, remote credential or committed effect.
[ATIF](https://docs.harborframework.com/core-concepts/agents/atif).

### Inspect AI: make the bridge part of the experiment

The agent bridge defaults `forward_generation_config` to false: client generation
settings can be replaced by Inspect model settings and provider defaults.
Enable faithful forwarding only when it matches the experiment's authority,
and record the effective model settings. Structural fields have different
handling. Also account for provider-side tools: a provider web-search tool can
reach the network despite a sandbox's local network restriction. The bridge
withholds such tools unless granted.
[Inspect agent bridge](https://inspect.aisi.org.uk/agent-bridge.html).

### OpenSandbox and Extism: different execution boundaries

OpenSandbox provides sandbox lifecycle and execution interfaces and supports
deployment through its own server/runtime architecture. It is a candidate
execution engine when those lifecycle APIs are needed. Pin the server, client,
runtime image and policy together; test network, filesystem, cancellation and
cleanup behavior. A common API does not prove equal isolation across deployments.
The repository has moved to `opensandbox-group/OpenSandbox`.
[Current project](https://github.com/opensandbox-group/OpenSandbox).

Extism provides WebAssembly plugins and host functions. A host function lets a
plugin call host code, so it is an authority boundary. An ostensibly contained
plugin can gain broad effects through a permissive host function. Register only
the approved imports and bind every host callback to the same input/output and
effect contract as a native tool. Compare acceptance and startup/resource costs
with the direct subprocess engine before selecting a default.
[Host functions](https://extism.org/docs/concepts/host-functions/).

### DBOS: recovery does not remove effect uncertainty

DBOS documents recovery from completed checkpoints, at-least-once step attempts
and separate transaction guarantees. Cancellation may take effect at the next
step unless an asynchronous step is explicitly preemptible. A resumed workflow
must retain the original task budget and must reconcile an external action whose
outcome was unknown at interruption. Test the crash after remote success but
before local checkpoint. This is the critical case for payments, notifications
and other non-transactional systems.
[Workflow semantics](https://docs.dbos.dev/python/tutorials/workflow-tutorial).

## Engine qualification population

For each candidate component, require a small fixed population that includes:

1. A successful declared operation with independently checked output.
2. An unsupported mandatory capability and useful typed refusal.
3. An incompatible protocol/schema/runtime binding.
4. A changed source, dependency or rendered artifact digest.
5. A timeout, cancellation and interrupted operation with unknown outcome.
6. A cross-scope or unauthorized request refused at the claimed boundary.
7. A stale cached profile or index refused when its binding changed.
8. An equivalent task through the Baltor engine and the external engine,
   comparing accepted results and separately reporting costs and limitations.

These are component checks, not a full-system Loop Engine benchmark. Add a
component to an actual customer workflow only after the complete selected path
has evidence. Keep the human-readable compatibility report and machine-readable
negotiation result together so an LLM cannot mistake documentation for a grant.

Decision: use the Harness Working Directory Compiler as the first
cross-project comparison boundary. Add evaluation adapters and selected tool
bindings next. Durable workflow, interface and sandbox engines enter when a
specific requirement and conformance population justify them.

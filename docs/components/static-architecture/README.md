# Static Architecture

Static Architecture has three public capability groups. Practitioner,
Intelligence, and Solution Loops may use these capabilities when their
contracts and permissions allow the operation.

```text
Static Architecture
├── Intelligence Search and Retrieval
├── Web Research
└── Custom Plugins
```

These groups describe reusable capabilities. They are not executable graph
vertices. The work that searches, researches, or invokes a plugin must still
belong to a classified Loop.

## Intelligence Search and Retrieval

The Retrieval Engine searches the four persistent intelligence layers. It
returns small typed references before it loads a selected body.

| Current feature | Status |
|---|---|
| Lexical, vector, and hybrid search behind one interface | Implemented. |
| Built-in selectable backends | Implemented for the documented backend set. |
| Typed references, digest checks, and separate materialization | Implemented. |
| Open external retrieval-backend registration | Not shipped. |

Read [Search and storage choices](SEARCH-AND-STORAGE.md) and
[Intelligence is returned through Loops](../intelligence-layers/INTELLIGENCE-AS-LOOPS.md).

## Web Research

Web Research covers permitted source discovery, fetching, extraction, and
source checking. Discovery remains separate from a network effect. The
current Brave example registers one typed capability and can run against an
offline fixture.

The package does not claim that one search provider solves all Web Research.
A research Loop may use a custom plugin, compare sources, download a selected
document, or spawn another research Loop under its own contract.

Read [Brave Web Search plugin](BRAVE-SEARCH-PLUGIN.md).

## Custom Plugins

Custom Plugins add typed capabilities through `CapabilityHandshake` and
`CapabilityDirectory`. Local discovery is effect-free. Invocation begins only
after a Loop selects a capability and passes contract, permission, and effect
checks.

The current package supports manual registration. It does not auto-discover
Python entry points, install plugins, or provide a plugin marketplace.

MCP tools and skills can enter through typed adapters. They remain plugin
inputs used by Loops, not new runtime types. Read
[MCP and skills](MCP-AND-SKILLS.md).

## Internal runtime mechanics

The following mechanisms support Loop execution but are not peer Static
Architecture capability groups:

- model gateway and provider adapters;
- typed settings and model tiers;
- workspaces and sandboxes;
- effect approvals;
- stores and large-context references;
- Runtime Memory;
- Run History and the event log;
- reports, live viewing, playback, and trace export.

These pages document the mechanics:

- [Model gateway](MODEL-GATEWAY.md)
- [Runtime settings](../../guides/settings.md)
- [Custom model endpoints](../../guides/custom-endpoints.md)
- [Effect approvals](EFFECT-APPROVALS.md)
- [Workspace backends](WORKSPACE-BACKENDS.md)
- [Context artifacts](CONTEXT-ARTIFACTS.md)
- [OpenTelemetry export](OPENTELEMETRY.md)
- [External harness adapters](EXTERNAL-HARNESS-ADAPTERS.md)

## Extension boundary

Add a capability to one of the three groups. Do not create a fourth peer group
for a provider, store, viewer, event system, or internal adapter. The
[taxonomy and class map](../../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
defines the extension rules.

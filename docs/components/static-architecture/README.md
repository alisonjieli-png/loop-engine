# Static Architecture and extensions

Static Architecture is the shared service layer used by Practitioner and
Solution loops. A self-improvement task uses it through the same Loop
Practitioner. A loop calls these services instead of rebuilding search,
storage, provider access, validation, or reporting for each task.

## Main services

| Service | What it provides |
|---|---|
| Capability Directory | Searches local capability cards and checks the selected handshake before execution. |
| Retrieval Engine | Provides one search interface with lexical, vector, and hybrid modes. |
| Provider adapters | Connects supported model providers and custom endpoints. |
| Runtime settings | Loads typed loop defaults, search choices, provider references, model tiers, operating permissions, and history paths. |
| Stores | Holds intelligence records and saved solution information. |
| Chronicle | Saves run events and verifies their chain. |
| Runtime Memory | Shares temporary notes inside the current run. |
| Studio | Shows loop trees, playback, intelligence, and solution views. |

## Two searches used by loops

| Search | Question | Result |
|---|---|---|
| Retrieval Engine | What relevant context, code reference, past work, solution, or user guidance already exists? | Ranked intelligence `LoopRef` objects. |
| Capability Directory | What registered service or capability can execute this operation under the loop's contract and permissions? | Ranked Code Intelligence `LoopRef` objects for local handshake cards. |

A loop can use both searches. Search is a loop. Search results are loops. The
caller selects one reference, verifies its digest and contract, and then runs
the selected intelligence or capability loop.

Effectful capabilities are never executed during discovery. A network search
plugin is found from its local handshake card. Its network call begins only
after explicit selection and permission checks.

## What is swappable today

| Area | Status | Current way to change it |
|---|---|---|
| Model provider | Yes | Supply `ProviderSpec` objects to `ModelGateway`, or create one from `CustomEndpoint`. |
| Model route and fallback | Yes | Replace `RouteRegistry`, `RoutePolicy`, or `ModelGatewayConfig` for one gateway instance. |
| Decision method | Yes | Register a resolver or regime. |
| Executable capability | Yes, manual | Register a typed endpoint in `CapabilityDirectory`. The Brave example uses this boundary. |
| Retrieval backend | Partial | Select `store`, `fts5`, or `lancedb` for lexical search and `hash` or `model2vec` for vector search. External backend registration is not shipped. |
| Intelligence store | Partial | Supply supported store and catalog adapters. There is no common external store plugin protocol yet. |
| Chronicle storage | Partial | Choose the local run directory. Cloud and team storage adapters are not shipped. |
| Report renderer | No plugin protocol | Use the built-in text, Markdown, HTML, and JSON renderers. |
| Loop Template | Manual | Add and validate a template in the package library. |

The table is intentionally mixed. Static Architecture is not uniformly
pluggable yet. Model routing, decision methods, and capabilities have explicit
interfaces. Retrieval, storage, Chronicle persistence, and report rendering
still need stronger external plugin contracts.

Loop Engine includes one manually registered plugin example for Brave Web
Search. The package does not auto-discover it. Importing the module makes no
request and changes no global registry.

- [Search and storage choices](SEARCH-AND-STORAGE.md)
- [Model gateway and provider configuration](MODEL-GATEWAY.md)
- [Runtime settings and model tiers](../../guides/settings.md)
- [Brave Web Search plugin example](BRAVE-SEARCH-PLUGIN.md)

## Plugins and future packaging

Today, a plugin is a module with an explicit registration function. It can add
a capability only after the caller gives it a `CapabilityDirectory`. The
Brave example proves this manual path with an offline fake transport.

A future packaging layer could auto-discover approved modules that provide a
model provider, retrieval backend, store adapter, report renderer, or tested
capability set.

That future work still needs a discovery contract, version checks, permission
checks, install and removal behavior, and clear failure reporting. The current
package does not auto-discover Python entry points and does not provide a
plugin marketplace.

## Settings stay separate

Static Architecture keeps five controls separate:

- A Loop profile defines purpose and required capabilities.
- A step profile changes the steps a loop follows.
- An effort setting changes bounded work limits.
- Model thinking power selects a configured model tier for a model-using loop.
- Operating settings change permissions, access, and preferences.

An effort or model-tier increase never grants a new tool, provider, permission,
or external effect.

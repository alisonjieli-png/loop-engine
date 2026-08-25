# Static Architecture and extensions

Static Architecture is the shared service layer beneath Practitioner loops,
Solution loops, and Self-Improvement loops. A loop calls these services instead
of rebuilding search, storage, provider access, validation, or reporting for
each task.

## Main services

| Service | What it provides |
|---|---|
| Capability Directory | Searches local capability cards and checks the selected handshake before execution. |
| Retrieval Engine | Provides one search interface with lexical, vector, and hybrid modes. |
| Provider adapters | Connects supported model providers and custom endpoints. |
| Configuration | Applies operating settings, permissions, and limits. |
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

## Current configuration and extension points

| Area | Current way to extend it |
|---|---|
| Model provider | Configure a `CustomEndpoint` or use provider registration. |
| Decision method | Register a resolver or regime. |
| Executable capability | Register a typed endpoint in the Capability Directory. The included Brave example uses this boundary. |
| Retrieval | Select `store`, `fts5`, or `lancedb` for lexical search and `hash` or `model2vec` for vector search. This is a fixed built-in set. |
| Storage | Use the supported store and Chronicle adapters. |
| Loop Template | Add a validated built-in template in the package library. |

Providers, decision methods, and capabilities have explicit adapter or
registration points. Retrieval currently has selectable built-in backends, not
dynamic backend registration.

Loop Engine includes one manually registered plugin example for Brave Web
Search. The package does not auto-discover it. Importing the module makes no
request and changes no global registry.

- [Search and storage choices](SEARCH-AND-STORAGE.md)
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

Static Architecture also keeps three controls separate:

- A step profile changes the steps a loop follows.
- An effort setting changes bounded work limits.
- Operating settings change permissions, access, and preferences.

An effort increase never grants a new model, tool, provider, or external
effect.

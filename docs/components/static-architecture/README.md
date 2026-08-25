# Static Architecture and extensions

Static Architecture is the shared service layer beneath Practitioner loops,
Solution loops, and Self-Improvement loops. A loop calls these services instead
of rebuilding search, storage, provider access, validation, or reporting for
each task.

## Main services

| Service | What it provides |
|---|---|
| Capability Directory | Finds an executable capability and checks its handshake. |
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
| Retrieval Engine | What relevant context, code reference, past work, solution, or user guidance already exists? | Ranked classified intelligence records. |
| Capability Directory | What registered service or capability can execute this operation under the loop's contract and permissions? | A typed capability handshake and endpoint. |

A loop can use both searches. It can retrieve context first, search the
Capability Directory for an executable method, complete the handshake, and
then call the selected Static Architecture service.

## Current configuration and extension points

| Area | Current way to extend it |
|---|---|
| Model provider | Configure a `CustomEndpoint` or use provider registration. |
| Decision method | Register a resolver or regime. |
| Executable capability | Register a typed endpoint in the Capability Directory. |
| Retrieval | Select `store`, `fts5`, or `lancedb` for lexical search and `hash` or `model2vec` for vector search. This is a fixed built-in set. |
| Storage | Use the supported store and Chronicle adapters. |
| Loop Template | Add a validated built-in template in the package library. |

Providers, decision methods, and capabilities have explicit adapter or
registration points. Retrieval currently has selectable built-in backends, not
dynamic backend registration. These boundaries can support future plugins, but
an external plugin system is not shipped today.

## Potential plugins

A future plugin layer could package one or more current extension points. For
example, a plugin could provide a model provider, retrieval backend, store
adapter, report renderer, or set of tested capabilities.

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

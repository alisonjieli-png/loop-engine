# Documentation

Start with the [main README](../README.md). Its first diagram shows how a task,
Practitioner loops, a Solution Canvas, Core Architecture, and the four
intelligence layers fit together.

The [architecture showcase](../showcase/) explains the same system as a linear
slide deck, browser player, and exported video.

## Learn the system in order

| Order | Page | What it explains |
|---:|---|---|
| 1 | [Repository organization](REPOSITORY-ORGANIZATION.md) | Which directory owns runtime code, contracts, guides, examples, benchmarks, case studies, and presentation assets. |
| 2 | [Contract index](contracts/) | Current definition, start, runtime-context, graph, intelligence, Solution, and event contracts. |
| 3 | [Taxonomy, ontology, and class map](architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md) | One complete classification tree, exact registered profiles, public classes, and current limits. |
| 4 | [Component guide](components/) | The complete map and the recommended reading order. |
| 5 | [The Loop object and step profiles](components/loop-object/) | Modes, steps, limits, loop conditions, exit conditions, and spawning. |
| 6 | [Loop profile ontology](components/loop-object/LOOP-PROFILE-ONTOLOGY.md) | Versioned Practitioner, Intelligence, and Solution profiles with inheritance and handshakes. |
| 7 | [Loop Practitioner](components/practitioner/) | How Practitioner Loops build and test work. |
| 8 | [Solution Canvas](components/solution-canvas/) | How Solution Loops represent and run finished work. |
| 9 | [Core Architecture](components/core-architecture/) | Intelligence Search and Retrieval, Web Research, and Custom Plugins. |
| 10 | [The four intelligence layers](components/intelligence-layers/) | Ontology, Code templates, Loop-bound retrieval, and Runtime Memory. |

## Practitioner workflows

| Page | What it explains |
|---|---|
| [Self-improvement as a Practitioner task](components/self-improvement/) | Run History review, intelligence audits, candidates, and domain seeds. |
| [Adaptive Practitioner architecture](architecture/ADAPTIVE-WORK-APPROACH-ARCHITECTURE.md) | Generic orientation, typed actions, research, construction, repair, and completion rules. |
| [Component glossary](architecture/COMPONENT-GLOSSARY.md) | Static components, executable Loops, atomic primitives, packets, values, and neighboring terms. |
| [Component data dictionary](architecture/COMPONENT-DATA-DICTIONARY.md) | Fields and invariants for the first universal component contracts. |
| [Component interaction dictionary](architecture/COMPONENT-INTERACTION-DICTIONARY.md) | Exact context, packet, prompt, model, Solution, and Spawned-work interactions. |
| [Component extension rules](architecture/COMPONENT-EXTENSION-AND-PARAMETERIZATION-RULES.md) | When to parameterize, compose, adapt, add a component, or create another Loop. |
| [Context handoff ontology](architecture/CONTEXT-HANDOFF-ONTOLOGY.md) | Global-to-local task hierarchy, references, materialization, demand pull, and isolation. |
| [Prompt and invocation encapsulation](architecture/PROMPT-AND-INVOCATION-ENCAPSULATION.md) | LLMWorkPacket, deterministic atomic prompt assembly, ModelGateway, repair, and evidence. |
| [Five-problem campaign](guides/campaigns.md) | Bounded provider and mode comparison with saved playback histories. |
| [Benchmark candidate registry](benchmarks/) | Cataloged tracks with source, evaluator, access, cost, and eligibility fields. |

## Start using Loop Engine

| Page | Purpose |
|---|---|
| [Getting started](getting-started.md) | Install from GitHub and run useful examples. |
| [Examples](../examples/) | Numbered example folders with their own instructions and effect notes. |
| [Case studies](../case-studies/) | Completed full-system runs, failures, accounting, and limitations. |
| [Loops and modes](guides/loops-and-modes.md) | A shorter runtime guide. |
| [Spawned Loop delegation](guides/spawned-loop-delegation.md) | Typed spawned tasks, private request context, runtime ports, updates, and cancellation. |
| [Providers and keys](guides/providers-and-keys.md) | Provider checks, failover, and cost attribution. |
| [Runtime settings and model tiers](guides/settings.md) | Typed YAML settings, environment precedence, providers, model tiers, and escalation. |
| [Custom endpoints](guides/custom-endpoints.md) | Connect a server you control. |
| [Reports](guides/reports.md) | Read, export, watch, and play back a run. |

## Architecture detail

These pages are deeper implementation references. They are not the recommended
starting point.

| Page | Purpose |
|---|---|
| [Generated architecture map](../src/loop_engine/ARCHITECTURE-MAP.md) | Current module inventory generated from the package. |
| [Architecture conformance](architecture/ARCHITECTURE_CONFORMANCE.md) | Automated architecture checks and their purpose. |
| [Design language](architecture/DESIGN-LANGUAGE.md) | Naming and visual rules. |
| [Typed API design](architecture/API-DESIGN.md) | Request objects, typed loop ports, compatibility wrappers, and the public parameter cap. |
| [Design guidance](architecture/DESIGN-GUIDANCE.md) | Applying the design language. |
| [Architecture visual guidance](architecture/ARCHITECTURE-VISUAL-GUIDANCE.md) | Required diagram order and content. |
| [Architecture navigation](architecture/ARCHITECTURE.md) | Short current map and links to the authoritative contract and component pages. |

## Current research notes

| Page | Purpose |
|---|---|
| [Model routing and gateway options](research/MODEL-ROUTING-AND-GATEWAY-OPTIONS.md) | Primary-source comparison of gateways, routers, overhead, and integration choices. |

## Reference

| Page | Purpose |
|---|---|
| [Universal Loop standard](reference/UNIVERSAL-LOOP-STANDARD.md) | Conformance rules for a loop. |
| [Product nomenclature](reference/PRODUCT-NOMENCLATURE.md) | Public terms and their current code mappings. |

## Design history

These files preserve earlier specifications and migration decisions. They are
not onboarding pages or a statement that every described feature is shipped.

| Page | Purpose |
|---|---|
| [Superseded master specification](reference/MASTER-SPECIFICATION.md) | Pointer to current sources and the earlier Git history. |
| [Intelligence retrieval plan](reference/INTELLIGENCE-RETRIEVAL-PLAN.md) | Earlier retrieval plan and migration detail. |
| [External reference sources](context/REFERENCE-SOURCES.md) | Paths to older Taedri material that may be inspected but never imported or copied in bulk. |

## Evidence and internal history

[`evidence/`](evidence/) contains dated run evidence. Each record states what
was measured and what the result does not establish.

[`internal/`](internal/) contains build prompts, handoffs, migration logs, and
design history. These files preserve provenance, but they are not current user
documentation.

[`context/CODEX-START-HERE.md`](context/CODEX-START-HERE.md) is the compact
entry point for a new Codex session. Repository-wide coding-agent rules are in
[`AGENTS.md`](../AGENTS.md).
[The older reference-source map](context/REFERENCE-SOURCES.md) explains how to
consult Taedri and preserved design history without copying their structure
into Loop Engine.

If you are taking over development, read
[HANDOFF.md](internal/HANDOFF.md) after the current component and architecture
pages.

## Writing templates

- [Documentation style](STYLE.md)
- [Example README template](templates/example-readme.md)
- [Concept page template](templates/concept-page.md)

## Coding-agent prompts

- [Governing OpenCode and Codex development prompt](prompts/LOOP-ENGINE-GOVERNING-DEVELOPMENT-PROMPT.md)
- [Self-orienting Code Intelligence master prompt](prompts/LOOP-ENGINE-SELF-ORIENTING-CODE-INTELLIGENCE-MASTER-PROMPT.md)
- [Architecture showcase and video prompt](prompts/LOOP-ENGINE-ARCHITECTURE-VIDEO-BUILD-PROMPT.md)
- [Generalized self-tuning Loop-node guidance](prompts/GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md)

Public prose also follows the repository's
[`humanizer-context.md`](../humanizer-context.md) file. It defines the reader,
technical voice, product terms, and punctuation rules for editing tools and
future contributors.

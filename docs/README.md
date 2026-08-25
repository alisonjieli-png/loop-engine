# Documentation

Start with the [main README](../README.md). Its first diagram shows how a task,
Practitioner loops, a Solution Canvas, Static Architecture, and the four
intelligence layers fit together.

## Learn the system in order

| Order | Page | What it explains |
|---:|---|---|
| 1 | [Component guide](components/) | The complete map and the recommended reading order. |
| 2 | [The Loop object and step profiles](components/loop-object/) | Modes, steps, limits, stopping, and loops that start loops. |
| 3 | [Loop Practitioner](components/practitioner/) | How Practitioner loops build and test work. |
| 4 | [Solution Canvas](components/solution-canvas/) | How Solution loops represent and run finished work. |
| 5 | [Self-improvement and domain seeding](components/self-improvement/) | Chronicle review, intelligence audits, candidates, and domain seeds. |
| 6 | [Static Architecture and extensions](components/static-architecture/) | Shared services, adapters, and future plugin boundaries. |
| 7 | [The four intelligence layers](components/intelligence-layers/) | Categories, classification, search, and Runtime Memory. |

## Start using Loop Engine

| Page | Purpose |
|---|---|
| [Getting started](getting-started.md) | Install from GitHub and run useful examples. |
| [Examples](../examples/) | Eleven realistic example folders with their own instructions. |
| [Loops and modes](guides/loops-and-modes.md) | A shorter runtime guide. |
| [Providers and keys](guides/providers-and-keys.md) | Provider checks, failover, and cost attribution. |
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
| [Design guidance](architecture/DESIGN-GUIDANCE.md) | Applying the design language. |
| [Architecture visual guidance](architecture/ARCHITECTURE-VISUAL-GUIDANCE.md) | Required diagram order and content. |
| [Historical architecture note](architecture/ARCHITECTURE.md) | Earlier architecture context. It is not the current onboarding map. |

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
| [Master specification](reference/MASTER-SPECIFICATION.md) | Earlier full-system specification and open work. |
| [Charter lineage](reference/TAEDRI-LOOP-CONSTITUTION-AND-AUTONOMOUS-CAMPAIGN-CHARTER.md) | Earlier governing principles retained for provenance. |
| [Intelligence retrieval plan](reference/INTELLIGENCE-RETRIEVAL-PLAN.md) | Earlier retrieval plan and migration detail. |

## Evidence and internal history

[`evidence/`](evidence/) contains dated run evidence. Each record states what
was measured and what the result does not establish.

[`internal/`](internal/) contains build prompts, handoffs, migration logs, and
design history. These files preserve provenance, but they are not current user
documentation.

If you are taking over development, read
[HANDOFF.md](internal/HANDOFF.md) after the current component and architecture
pages.

## Writing templates

- [Documentation style](STYLE.md)
- [Example README template](templates/example-readme.md)
- [Concept page template](templates/concept-page.md)

Public prose also follows the repository's
[`humanizer-context.md`](../humanizer-context.md) file. It defines the reader,
technical voice, product terms, and punctuation rules for editing tools and
future contributors.

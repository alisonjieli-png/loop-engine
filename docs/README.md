# Documentation

## Start here

| | |
|---|---|
| [Getting started](getting-started.md) | install, first loop, first problem — 15 minutes, no API key |

## Guides

| | |
|---|---|
| [Loops and modes](guides/loops-and-modes.md) | the runtime: nesting, stop conditions, mode permissions, the four intelligence pillars |
| [Providers and keys](guides/providers-and-keys.md) | discovery, failover, cost attribution, what "verified by use" means |
| [Custom endpoints](guides/custom-endpoints.md) | your own server, a friend's, or a third party's |
| [Reports](guides/reports.md) | reading and exporting what a run did |

## Architecture

How the system is built and why. Start with `ARCHITECTURE.md`.

| | |
|---|---|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | the four top-level abstractions |
| [ARCHITECTURE-MAP.md](architecture/ARCHITECTURE-MAP.md) | generated module census (lives with the code) |
| [ARCHITECTURE_CONFORMANCE.md](architecture/ARCHITECTURE_CONFORMANCE.md) | the zero-tolerance gates and what each protects |
| [DESIGN-LANGUAGE.md](architecture/DESIGN-LANGUAGE.md) | the visual and naming rules |
| [DESIGN-GUIDANCE.md](architecture/DESIGN-GUIDANCE.md) | applying the design language |
| [ARCHITECTURE-VISUAL-GUIDANCE.md](architecture/ARCHITECTURE-VISUAL-GUIDANCE.md) | diagram conventions |

## Reference

| | |
|---|---|
| [MASTER-SPECIFICATION.md](reference/MASTER-SPECIFICATION.md) | the full specification |
| [UNIVERSAL-LOOP-STANDARD.md](reference/UNIVERSAL-LOOP-STANDARD.md) | what makes something a conforming loop |
| [PRODUCT-NOMENCLATURE.md](reference/PRODUCT-NOMENCLATURE.md) | every term, defined in plain English |
| [Charter](reference/TAEDRI-LOOP-CONSTITUTION-AND-AUTONOMOUS-CAMPAIGN-CHARTER.md) | the governing principles |
| [INTELLIGENCE-RETRIEVAL-PLAN.md](reference/INTELLIGENCE-RETRIEVAL-PLAN.md) | how the four pillars are retrieved |

## Evidence

[`evidence/`](evidence/) holds dated receipts from real runs — what was
measured, under what controls, and explicitly what each result does **not**
establish. Read these rather than trusting a summary; several record negative
or inconclusive outcomes, which is the point.

## Internal

[`internal/`](internal/) holds development artifacts: build prompts, harness
handoffs, migration ledgers, design lineage. Kept for provenance. You do not
need any of it to use the library, and none of it is current documentation.

---

## Picking this project up

[**HANDOFF.md**](internal/HANDOFF.md) — where everything is, current verified
state, the machine-enforced rules, the non-obvious conventions, and the open
work ranked. Start there if you are taking over.

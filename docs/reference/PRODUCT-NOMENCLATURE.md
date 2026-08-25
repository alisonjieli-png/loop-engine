# Product Nomenclature — the public words

Status: CURRENT (registered in `conformance_report.CURRENT_DOCS`).
Source: the owner's SaaS/architecture correction directive (2026-08-24).
Rule: internal tokens stay stable in code; every HUMAN surface uses the
words on this page. Where this page and older design notes disagree,
this page wins.

## Product-facing terms (use prominently)

PractitionerLoop · Reference Nine-Step Loop · Custom Loop · Child Loop ·
Deterministic · Hybrid · Model-backed · String Intelligence · Code
Intelligence · **Previous Run & Solution Intelligence** (short UI label:
Run & Solution Intelligence) · Runtime Memory · Solution Canvas ·
Candidate Solution · Final Solution · Improvement Flywheel ·
Intelligence Library · Loop Engine Studio · **Code Intelligence Search** ·
Solution Library.

> **"Code loop", not "capability" (vocabulary rule).** The asset in Code
> Intelligence is a **code loop** (a reusable, invokable loop); the former
> public phrase "Code Intelligence Search" is superseded — the surface serves Code
> Intelligence.  The **Capability Directory** is a separate, load-bearing
> internal surface that answers a different question — "what can EXECUTE
> this under these permissions?" (invocation governance) — and it is not a
> headline noun for the intelligence content.  So: pillar = Code
> Intelligence; a reusable unit = a **code loop**; the lookup/governance
> surface = the Capability Directory (searched via Code Intelligence
> Search).  These are deliberate, distinct nouns, not synonyms for the
> same thing.

## The nine steps (public labels)

1 Orient · 2 Reconcile · 3 Assess · 4 Decide · **5 Determine How** ·
6 Act · 7 Verify · 8 Integrate · 9 Route. Always marked with the
custom-loop footnote: *the nine-step loop is Loop Engine's recommended
default; teams can use custom Loop Templates with different steps,
orders, repetitions, and stopping rules.*

## The three modes (always in this order, loop-specific)

- **Deterministic** — reusable code, rules, calculations, search, and
  tested capabilities; fast, repeatable, no language model required.
- **Hybrid** — code first; a model only where interpretation,
  generation, or repair adds value.
- **Model-backed** — a model guides the current loop's reasoning while
  Loop Engine controls tools, permissions, validation, memory, execution.

Mode is set per loop. A model-backed loop may start a deterministic
child; never present mode as inherited.

## Plain-English translations (technical term → public words)

| Internal | Public |
|---|---|
| receipt | verified run record |
| digest | exact version fingerprint |
| evidence gate | independent review before promotion |
| manifest | capability description |
| admission | tested and approved for execution |
| candidate maturity | not yet promoted — under review |
| `non_deterministic` (token) | Model-backed |
| `past_run_intelligence` (token) | Previous Run & Solution Intelligence |
| a reusable code asset (token) | code loop |
| finding a code loop | Code Intelligence Search |

Secondary technical terms (docs/inspectors/tooltips only, never
headlines): manifest, digest, span, trace, content-addressing,
admission, runtime contract, evidence gate, semantic invocation,
fallback route.

## Template intelligence

Template STRING intelligence (Loop Templates, prompt/context/blueprint/
evaluation/output templates) lives in String Intelligence. Template
CODE intelligence (node starters, solution-component/graph/test/adapter
templates) lives in Code Intelligence; candidate source stays a String
until tested and admitted. A cross-cutting "Templates" view may present
both.

## User Intelligence (the fourth layer)

Advice humans leave on loops, tasks, runs, and solution components —
written like a Slack message to a coworker. Loops may check for
guidance before deciding, and every check is recorded. Guidance, never
truth: it bypasses no gates. Public label: **User Intelligence**.

## Every Solution component is a loop

There are no "nodes": each component of a Solution Canvas is itself a
PractitionerLoop — usually deterministic and one-pass, always with the
loop envelope's fallback capability. "Node" may appear as drawing
shorthand; the runtime object is a loop.

## Runtime Memory (distinct from the pillars)

The shared working notebook for loops active in the CURRENT run —
notes, findings, questions, warnings, references, temporary summaries.
Useful notes may later be curated into a pillar; nothing auto-promotes.
State today: BUILT run-scoped (RunNoteBoard; every write and read is a
ledger event); ambient writes without a run's board still refuse.

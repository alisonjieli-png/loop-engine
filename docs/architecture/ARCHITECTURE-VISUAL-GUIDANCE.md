# Architecture Visual Guidance — the canonical figures

Status: CURRENT (registered in `conformance_report.CURRENT_DOCS`).
Source: the correction directive (2026-08-24 §6-§13). These are the
ONLY approved topologies; freehand variants fail review.

## V1 — the two-row loop rail (default loop figure)

Top row left→right: 1 Orient · 2 Reconcile · 3 Assess · 4 Decide ·
5 Determine How; bottom row right→left: 6 Act · 7 Verify · 8 Integrate ·
9 Route; a connector drops 5→6 and rises 9→1. Identical card widths,
aligned labels, centered connectors, tooltips + keyboard focus on every
step. Marked "Reference Nine-Step Loop*" with the custom-loop footnote
and a Reference/Custom toggle whose custom example is a genuinely
different sequence (Research → Research → Compare → Prototype → Test →
Diagnose → Repair → Verify) — never silently re-rendered as nine-step.
A polygon is acceptable ONLY with mathematically aligned nodes,
horizontal labels, no crossing connectors, and clean mobile collapse.

## V2 — the spawn tree (loop-by-loop)

Root PractitionerLoop → Research child (→ Source Review grandchild) +
Validation child. Every card: goal, mode, status, iterations, calls,
cost, confidence. Mode colors per DESIGN-GUIDANCE (det deep teal, hyb
blue-teal, mod amber). The copy states mode is loop-specific — a
model-backed loop may start deterministic, hybrid, and model-backed
children. Spawn/return animation must explain behavior (subproblem →
child appears → works → result returns), respect reduced motion.

## V3 — the intelligence pillars + capability search

Current PractitionerLoop → Code Intelligence Search → the pillar cards
(String Intelligence · Code Intelligence · Previous Run & Solution
Intelligence · **User Intelligence** — the fourth layer, owner
2026-08-24: advice humans leave on loops/tasks/runs/components,
consulted before decisions) → selected context/capability/prior
solution/guidance. Search visibly spans ALL the pillars. In Studio,
clicking any loop opens its input/expected-output and an advice box.

## V4 — the Runtime Memory rail

All active loops connect down to one shared rail: "Shared Runtime
Memory — Notes · Findings · Questions · References". The capability is
BUILT run-scoped in the runtime (`static_architecture/runtime_memory`,
2026-08-24: writes and reads are ledger events); the Studio rail
RENDERING is the queued piece — label it accordingly. Promotion note
unchanged: useful notes may be curated into a pillar; nothing
auto-promotes.

## V5 — practitioner authors Solutions

PractitionerLoop Tree → writes and revises → Candidate Solution Canvas
A/B/C (stacked cards; different topology/mode mix/cost) → compares,
selects, or combines (select-best / ordered fallback / average /
weighted blend / vote / bagging / boosting / stacking / gating /
mixture of experts) → Final Solution Canvas. Every component carries a
mode chip — and every component IS a loop (the loop-node rule): drawn as
a card for legibility, executed as a PractitionerLoop with fallbacks. Caption: **"The PractitionerLoop shows how Loop Engine builds.
The Solution Canvas shows what Loop Engine ships."**

## V6 — the Improvement Flywheel

RUN → REVIEW (what worked, failed, cost time, needed a model) → CURATE
(reusable questions, capabilities, prior-solution lessons) → IMPROVE
THE THREE INTELLIGENCE PILLARS (named explicitly) → NEXT RUN STARTS
STRONGER.

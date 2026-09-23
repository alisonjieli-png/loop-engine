---
name: explain-engine-selection-from-eligible-evidence
description: Audit why one engine was selected from registered alternatives. Use when a planner must separate capability eligibility, evidence ranking, and a permitted fallback.
---

# Explain engine selection from eligible evidence

## Use

Use to review a proposed component-engine choice from a supplied registry and task contract. This is an explanation and gap-finding method; it does not route or execute work.

## Inputs

- The typed task contract, required capabilities, authority, budget, and preferences.
- Registered engine versions, declared capabilities, preconditions, and fallback order.
- Evidence for quality, latency, cost, and failures on comparable tasks, with dates and denominators.

## Procedure

1. List discovered engines without ranking them. Record exact versions and the evidence available for each.
2. Eliminate engines that do not satisfy the typed input and output contract, required capability, effect authority, or hard budget. A hard spending limit requires a certified conservative cost bound; unknown cost cannot pass it. State the exact failing or unresolved requirement.
3. Rank only eligible engines by the declared decision rule. Keep missing quality and latency evidence as unknown; do not turn it into a favorable zero. Never use fallback order to waive a hard constraint.
4. State the selected engine and the evidence supporting it. If evidence is too weak to distinguish eligible engines, apply the declared fallback order and mark the selection unproven.
5. Walk one expected failure path: which failure class permits retry, fallback, or refusal, and who owns the decision. A fallback must pass eligibility again under the same authority.
6. Return a trace with discovered, eligible, ranked, selected, and fallback states, plus any missing evidence.

## Completion check

The selected engine is eligible under the original task contract, including any hard spending limit. Every exclusion, tie, and fallback cites a declared rule or evidence record. The trace allows another reviewer to reproduce the choice.

## Stop

If the registry, authority, or decision rule is absent, report selection as unresolved. Do not invent a capability or let a preference override a hard constraint.

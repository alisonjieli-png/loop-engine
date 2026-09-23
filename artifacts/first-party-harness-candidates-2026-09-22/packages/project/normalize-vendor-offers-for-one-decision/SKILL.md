---
name: normalize-vendor-offers-for-one-decision
description: Compare supplied vendor offers for one purchasing decision by making units, exclusions, assumptions, and unanswered terms explicit.
---

# Normalize vendor offers for one decision

## Use case

Use when a buyer has two or more written offers for the same intended use and needs a comparison that another person can audit. This skill produces an analysis, not a purchasing recommendation or authority to contact a vendor.

## Required inputs

- The intended workload, time horizon, required capabilities, and decision rule supplied by the buyer.
- Each offer's source, date, currency, price unit, included quantity, limits, support terms, and exclusions, where stated.
- Any buyer-supplied assumptions, such as expected usage or conversion rate. Mark each assumption separately from offer terms.

## Steps

1. Give every offer an identifier and preserve its exact source reference. Do not merge a marketing page with a contract without marking the difference.
2. Choose one comparison period and workload. Convert a quoted price only when its unit and conversion inputs are known; show the calculation. Keep currency and tax treatment visible.
3. For each required capability, record `stated present`, `stated absent`, `conditional`, or `unknown`, with the supporting offer passage. These are claims in the offer, not verified product behavior. A feature named in an offer does not imply a usable allowance for the workload.
4. Separate one-time charges, recurring charges, usage charges, required add-ons, and possible overages. Show an interval or formula when usage or terms are uncertain.
5. List unanswered terms that could reverse the ordering. Compare offers under the same assumptions and show which assumptions cause a different result.
6. Return a table with source references, normalized cost or unresolved formula, capability status, exclusions, and decision blockers. State only the conclusion supported by the buyer's stated rule.

## Completion check

Every displayed number can be traced to an offer term or a labeled calculation. Every required capability has an offer-stated status for every vendor. A missing price unit, usage term, or mandatory add-on is visible as unknown rather than treated as free or zero.

## Stop or hold

Hold any ranking that depends on an unstated exchange rate, volume, contract term, legal interpretation, or undisclosed quote. Do not purchase, negotiate, send vendor messages, or invent a buyer policy.

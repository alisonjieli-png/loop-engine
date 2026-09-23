---
name: reconstruct-a-buyer-decision-path
description: Map evidence for an organizational purchase decision, separating evaluators, approvers, blockers, and unknown gates without inferring authority from job titles.
---

# Reconstruct a buyer decision path

## Use case

Use when a prospective organization has expressed interest but its actual buying process is unclear. Produce a read-only path of evidence and unanswered questions for a sales or product team.

## Required inputs

- A bounded set of authorized conversation notes, requested requirements, and supplied process documents with dates and source references.
- The proposed purchase or trial scope and the date at which the path should be evaluated.
- Any supplied privacy and recipient rule for names, roles, and account details in the output.

## Procedure

1. List observed participants and the actions each has actually taken. Use role labels and deidentified references by default; include names only when needed and permitted for the intended recipient. Distinguish a user, evaluator, recommender, budget owner, procurement contact, legal or security reviewer, and signer only when evidence supports that role.
2. Record each stated gate, its owner if known, evidence required, current state, and source. Keep an individual's opinion separate from an organization's approval.
3. Order the gates only where the records establish an order. Mark dependencies that are inferred rather than stated.
4. Identify objections by the decision they could block, the evidence behind them, and whether the objection is resolved. Do not convert a planned meeting or verbal enthusiasm into an approved budget.
5. Flag missing authority, conflicting accounts of the process, expired evidence, and steps that require the buyer's own policy or signature.
6. Return a decision-path table, minimally identified participants and roles, confirmed and unresolved gates, intended sharing scope, and the smallest questions needed to validate the path.

## Completion check

A reader can identify the source for each assigned role and gate, and can see which actions remain before the organization could decide. A senior title alone never proves budget or signature authority.

## Stop or hold

Hold a claim that the purchase is approved when an approval gate or its owner is unknown. Hold sharing beyond the authorized recipient scope. Do not contact the organization, create a quote, bind commercial terms, or invent its procurement policy.

---
name: qualify-a-partner-integration-proposal
description: Evaluate a proposed partner integration against bilateral value, data boundaries, responsibilities, and failure handling before implementation commitments.
---

# Qualify a partner integration proposal

## Use case

Use when two organizations are considering a product or data integration. Produce a feasibility and decision packet from supplied evidence, without claiming the partnership is agreed.

## Required inputs

- The customer task and proposed integration behavior, including which party supplies each capability.
- Current versioned product and interface evidence, candidate data fields, and any supplied data-use or security rules.
- Proposed operational owners, commercial assumptions, and agreement status if known.

## Procedure

1. Describe the user outcome and the minimum exchange needed to produce it. Separate a working product capability from a roadmap promise or partner assertion.
2. Draw the proposed data and action flow in words: initiator, sender, receiver, fields, storage, retention, and who may authorize each transfer or action. Mark unknown rules rather than assuming consent.
3. Assign responsibility for setup, authentication, support, version changes, failure notification, and disconnection. Mark each responsibility as accepted, proposed, or ownerless.
4. Check compatibility against supplied interface versions and limits. Name one normal path, one refusal, one partial failure, and one termination path that each party would need to handle.
5. Separate technical feasibility from commercial agreement, distribution rights, privacy approval, and customer demand. An interface that can connect does not settle those gates.
6. Return a boundary map, evidence table, conditional feasibility finding, unresolved owner and authority questions, and a smallest authorized validation proposal.

## Completion check

A reviewer can identify every data transfer and effect, its stated authority source, both parties' responsibilities, and the unresolved gates. A missing partner commitment remains missing even if a demo API call works.

## Stop or hold

Hold implementation or customer claims when a data right, authentication route, owner, interface contract, or agreement state is unknown. Do not call a partner endpoint, exchange data, contact the partner, or accept terms.

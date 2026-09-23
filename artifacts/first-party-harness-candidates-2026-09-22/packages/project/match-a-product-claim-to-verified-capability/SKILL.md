---
name: match-a-product-claim-to-verified-capability
description: Check one proposed product claim against versioned capability and customer-journey evidence before it appears in public material.
---

# Match a product claim to verified capability

## Use case

Use when a product page, sales note, or release announcement says the service can do something specific. Produce an internal claim disposition based on the exact release and journey evidence. This skill does not publish copy.

## Required inputs

- The exact proposed sentence and intended audience or placement.
- The product release identifier and relevant capability contract or implementation reference.
- Current evidence for the path the sentence implies, including attempted customer journeys and failures.
- The team's claim policy, if one is supplied.

## Steps

1. Break the sentence into claims a reader could test: availability, who can use it, operation, outcome, number, or comparison. Preserve words such as `all`, `automatic`, `faster`, and `verified` because they change the burden of evidence.
2. For each claim, name the exact release, account type, input conditions, and path that would make it true. Separate `offered`, `fetched`, `loaded`, `used`, and `verified` when the path includes harness material.
3. Map the strongest available evidence and every known counterexample to that path. Mark old-release evidence, local-only checks, missing data, and partial journeys as such.
4. Assign `supported`, `narrower wording supported`, `planned only`, or `unsupported` to each claim. Draft the narrowest accurate sentence if the original overreaches.
5. Return a claim ledger with evidence references, release scope, unresolved test, and proposed wording. Include failures alongside successes.

## Completion check

Each factual clause can be checked against a current release and evidence record. A reader cannot mistake a catalogue entry for a file loaded and used by a customer harness, or a planned feature for a live one.

## Stop or hold

Hold publication when a material number, comparison, availability statement, or outcome lacks current evidence. Do not publish, alter the website, invent a customer, or infer consent from an internal test.

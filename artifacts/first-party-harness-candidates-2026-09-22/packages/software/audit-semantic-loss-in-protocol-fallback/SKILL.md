---
name: audit-semantic-loss-in-protocol-fallback
description: Check whether a proposed protocol or adapter fallback loses required meaning. Use before accepting a lower version or alternate representation at a typed system boundary.
---

# Audit semantic loss in a protocol fallback

## Use

Use this for a proposed fallback between separately deployed components. Analyze the supplied contracts; do not configure, negotiate, or invoke the connection.

## Inputs

- The consumer's required operations, fields, error meanings, integrity checks, and authority rules.
- The producer's proposed protocol, schema, capability set, and adapter mapping.
- Examples of accepted, refused, and partially completed work at the current boundary.

## Procedure

1. Turn each required behavior into an observable obligation: what must arrive, what must be refused, and what the caller must be able to distinguish.
2. For every obligation, identify the exact field, capability, or adapter rule that carries it in the proposed fallback.
3. Mark each mapping as preserved, transformed with an explicit proof obligation, missing, or ambiguous. A matching field name is insufficient when units or error semantics differ.
4. Trace authorization, integrity, cancellation, partial failure, and retry meaning separately; these are easily lost behind a successful response shape.
5. Create one known-good and one known-wrong interaction for every transformed or ambiguous obligation. State the observable result expected on both sides.
6. Return an obligation matrix and a decision proposal: eligible as specified, eligible only after a named adapter check, or ineligible because a required meaning is lost.

## Completion check

Each required obligation has a cited mapping and an expected observable behavior. No missing or ambiguous required obligation is marked eligible.

## Stop

If either contract is absent, mark the decision unknown and request the missing contract. Do not guess compatibility from version numbers, shared field names, or a successful connection alone.

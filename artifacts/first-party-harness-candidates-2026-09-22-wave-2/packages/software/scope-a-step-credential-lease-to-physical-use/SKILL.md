---
name: scope-a-step-credential-lease-to-physical-use
description: Check that a fresh harness's credential reference is bound to one step, recipient, operation class, lifetime, and physical-use limit.
---

# Scope a step credential lease to physical use

## Use case

Use when a local broker is proposed to serve model or tool calls for a newly started harness. Produce a lease-binding review without requesting or exposing a secret.

## Required inputs

- Owning step identity, exact endpoint or tool recipient, permitted operations, expiry, call or spend ceiling, and cancellation rule.
- Broker and process identity design, credential reference metadata, route selection, and declared fallback policy.
- A proposed physical-use request and available broker decision record, if one exists.

## Procedure

1. Separate the library client, model provider, and external tool identities. Identify which principal needs the credential and which process should never receive its value.
2. Bind the lease to the owning step and a specific recipient audience, route, operation class, and allowed period. Treat an unauthenticated local endpoint as a separate route with no credential requirement.
3. Check how the broker authenticates the calling process and verifies the request at physical use. A lease record with only a scope label does not prove the caller owns it.
4. Check cumulative calls or spending, expiry, cancellation, and what happens if the process restarts or the selected route changes. A fallback recipient needs a separately eligible binding.
5. Identify any direct-key fallback as a different trust profile with its own explicit authority and egress limits; do not silently substitute it when broker access fails.
6. Return a binding matrix with principal, recipient, operation, ceiling, expiry, verification point, refusal case, and unresolved design gap.

## Completion check

The proposed broker would refuse a request from another step, after expiry, beyond the ceiling, or to a different recipient. The matrix contains no credential value and no general-purpose key handoff.

## Stop or hold

Hold a security or spending guarantee when caller authentication, physical-use checking, endpoint audience, or accounting is unproven. Do not resolve a credential, call a provider, create a lease, or run a harness.

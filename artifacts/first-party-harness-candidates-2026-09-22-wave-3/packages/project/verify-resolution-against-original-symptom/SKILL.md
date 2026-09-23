---
name: verify-resolution-against-original-symptom
description: Compare a proposed support resolution with the customer's original failing path and authorized after-change observations.
---

# Verify resolution against the original symptom

## Use

Use when a support case is proposed for closure after a fix, workaround, or configuration change. Assess supplied before-and-after evidence for the original symptom. This skill does not close the case or perform a live test.

## Inputs

- Case reference, original symptom, affected path, environment, and supplied acceptance rule.
- Before-change observation, remediation identity and version, and authorized after-change observations.
- Scope of affected accounts or releases and any known remaining failures.

## Procedure

1. Restate the original user action and observable failure without replacing it with the team's proposed fix description.
2. Match the remediation to the environment and release in which the symptom occurred. A merged or deployed change proves only that a change was delivered.
3. Compare after-change evidence on the same path and relevant account or data state. Mark differences in version, permissions, or setup that prevent a like-for-like comparison.
4. Evaluate the supplied acceptance rule against the observed result. Separate `resolved on tested path`, `still failing`, and `unverified` from any wider rollout claim.
5. Return a resolution-evidence table, remaining gaps, and a bounded next check for the case owner.

## Completion check

The original failing action has a relevant after-change observation and meets the supplied acceptance rule before a resolution recommendation. A deployment record with the customer's path still failing must not support closure.

## Stop

If authorized after-change evidence or the original acceptance rule is missing, say `unverified`. Do not access an account, run an unapproved reproduction, change ticket state, or promise the customer a result.

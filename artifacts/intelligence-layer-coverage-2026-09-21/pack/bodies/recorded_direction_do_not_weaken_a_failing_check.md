# Recorded direction: do not weaken a failing check

Kind: recorded guidance from a person, held in User Feedback Intelligence.

| Field | Value |
|---|---|
| Guidance type | `instruction` |
| Scope | `organization` |
| Strength | `instruction` |
| Timing | before verification, and again when a check fails |
| Recorded | 2026-09-14, by the repository owner |

## The guidance as recorded

When a check fails, first decide whether the work, the check, or the
environment is wrong, and record why. Do not weaken a check to make it pass. A
revised check must still reject a known-wrong answer.

## What it asks a step to do

Three things, in order. Classify the failure before editing anything. Write
down the classification and the evidence for it. If the check itself was
wrong, correct it and then show that the corrected check still refuses the
answer everyone agrees is wrong.

The last part is the one that is usually skipped. A check that was corrected
and no longer rejects anything has been removed, not corrected, and the suite
is now smaller in a way that nothing records.

## Response expected from a step

A step that receives this guidance should return the classification it chose,
the reason, and, when it changed a check, the known-wrong input it ran and
what the corrected check did with it.

## Limits

This is guidance, not permission and not proof. It cannot waive a safety,
legal, security, permission, secret, network, spending, sandbox, or external
effect rule, and it does not decide whether any particular check was right.

## Source

`AGENTS.md`, section "Persistent general solving", and
`docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md`.

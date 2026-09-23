---
name: prepare-a-support-escalation-packet
description: Turn a bounded support case into a reproducible, privacy-scoped escalation packet for an engineering or operations owner.
---

# Prepare a support escalation packet

## Use case

Use after support has identified a case that needs technical or operational investigation. This skill prepares evidence for the receiving owner; it does not decide a policy entitlement or change the case.

## Required inputs

- A case reference, reported behavior, expected behavior, impact, and supplied timestamps or environment details.
- Authorized logs, screenshots, prior troubleshooting, and a rule for what case data may enter the recipient's scope.
- The receiving team's required fields and any supplied priority or incident criteria.

## Procedure

1. State the customer's blocked task and the observed difference from expected behavior. Keep customer statements separate from observations reproduced by staff.
2. Build a minimal reproduction from supplied steps, environment, versions, account state that may be shared, and expected and actual results. If no reproduction exists, say so and identify the missing condition.
3. Add a compact sequence of relevant times, case identifiers, prior attempts, and outcomes. Do not mark an attempted workaround as successful without an observed result.
4. Classify impact and priority only under the supplied rule. Count affected users, accounts, or transactions only when the evidence supports that denominator.
5. Remove secrets and unnecessary personal data from the packet. Reference restricted artifacts through an authorized access path rather than copying them into general notes.
6. Return the escalation packet with recipient, desired technical question, evidence links, reproduction status, impact basis, unresolved facts, and next update owner if supplied.

## Completion check

The receiving owner can tell what failed, what has already been tried, what evidence is accessible, and what remains unknown without asking support to rediscover the case. The packet carries no raw secret or unneeded personal data.

## Stop or hold

Hold transfer when the proposed recipient lacks permitted access to needed case data or a mandatory recipient field cannot be supplied. If priority rules are missing, mark priority unknown and hold only a severity claim; an otherwise authorized packet may transfer. Do not change ticket state, page a team, promise a resolution time, or execute a reproduction that requires an unapproved effect.

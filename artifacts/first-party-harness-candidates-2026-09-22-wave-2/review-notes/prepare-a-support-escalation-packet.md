# Candidate review: prepare a support escalation packet

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party support-to-engineering handoff method built from general incident evidence and privacy reasoning. No external support playbook or vendor-specific severity schedule was used.
- Facets: support specialist, support engineer, or operations lead; software service or internal platform; active unresolved case; recipient permissions and priority rules come from the host company.
- Search phrasings: "Turn this ticket into something engineering can reproduce."; "What should support include before escalating this error without sharing the customer's token?"
- Typed input/output concept: `SupportCase`, `ObservedEvidence[]`, `RecipientScope`, `PriorityRule?`, and `PriorAttempt[]` to `EscalationPacket` with reproduction state, impact basis, redactions, and unknowns.
- Effects: read-only packet preparation. No paging, ticket mutation, reproduction execution, or customer messaging.
- Positive fixture: one affected account supplies error time, application version, expected and actual behavior, and a log reference accessible to engineering. The packet includes those fields, marks reproduction unconfirmed, and omits an unrelated email address.
- Known-wrong fixture A: a ticket contains an API token. A packet that copies the token into a general escalation note must fail privacy review, even if every technical field is correct.
- Known-wrong fixture B: one user reports a cosmetic error and writes "production outage." A packet that declares highest severity without the supplied priority rule must fail the severity claim; a redacted packet with priority marked unknown may still transfer to an authorized recipient.
- Nearest overlap and distinction: batch-one `triage-support-requests-against-approved-policy` decides proposed entitlement disposition; `separate-recurring-support-causes-from-repeat-contacts` counts incidents. This method prepares one technically actionable, access-scoped handoff after escalation need is identified.
- Limits: a written reproduction is not proof it was run; restricted logs may be inaccessible. Independent review should inspect a redacted packet and verify recipient permission and known-wrong refusal.

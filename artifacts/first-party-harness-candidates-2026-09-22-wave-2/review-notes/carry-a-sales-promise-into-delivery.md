# Candidate review: carry a sales promise into delivery

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party handoff method for mismatches among customer-facing statements, approved scope, and delivery evidence. It does not reuse a contract template or make a legal judgment.
- Facets: sales lead, implementation manager, customer success, or delivery owner; service or business-to-business software company; contracting-to-onboarding handoff; only supplied company approval rules apply.
- Search phrasings: "What did we tell this customer we would deliver, and who owns each item?"; "Find promises in the proposal and email thread that onboarding may have missed."
- Typed input/output concept: `CustomerFacingStatement[]`, `ApprovedScope`, `CapabilityEvidence`, `AuthorityRule?`, and `HandoffDate` to `CommitmentHandoff`, `Conflict[]`, and `OwnerGap[]`.
- Effects: read-only internal packet. No contract change, customer assurance, provisioning, or message send.
- Positive fixture: a dated signed order lists a standard export; an earlier email offers a custom connector conditionally; an approved scope lists only the export. The handoff records the export owner and holds the connector as unresolved rather than silently promising it.
- Known-wrong fixture: the output treats the earlier conditional connector email as an accepted committed feature, assigns no owner, and tells delivery to promise it. This must fail classification and owner checks. Deleting the email from the record also fails conflict visibility.
- Nearest overlap and distinction: starter `hand_over_a_result_its_consumer_can_use` shapes any handoff; batch-one `build-a-project-decision-provenance-map` maps approved decisions. This method reconciles what a customer may believe was promised against authorized delivery scope and acceptance evidence.
- Limits: document priority and legal interpretation require supplied rules and qualified people. Review should test conflicting and missing authority, not merely confirm that a table exists.

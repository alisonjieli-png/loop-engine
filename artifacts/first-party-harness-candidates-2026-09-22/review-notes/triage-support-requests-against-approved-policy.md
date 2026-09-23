# Candidate review: triage support requests against approved policy

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party triage procedure authored without a
  named company policy, customer record, or copied support playbook.
- Job, company, and project facets: support specialist or operations lead;
  the company's approved policy version and authority rules are supplied at
  use time; ongoing support or policy-change stage.
- Search phrasings: "Does this customer request qualify under our current
  refund rule, and which facts are missing?"; "Draft an internal support
  disposition using the policy version that applied to this case."
- Typed input/output concept: `Case`, `PolicyVersion`, `EffectiveDate`,
  `EntitlementFact?`, and `EscalationRule[]` to `ProposedDisposition`,
  `EvidenceReference[]`, `HoldReason[]`, and optional `DraftReply`.
- Effects: read authorized case and policy records and draft internally. No
  customer contact, refund, account mutation, or policy creation.
- Good fixture: a 30-day eligibility rule applies and a verified purchase
  date is 12 days before the request; mark provisionally eligible with the
  clause and case reference, pending the authorized sender's action.
- Known-wrong fixture: purchase date missing, but the request is marked
  eligible because the customer says it was recent.
- Overlap search: starter `resolve_missing_information` handles unknowns,
  `review_authorisation_on_every_path` handles effects, and
  `return_errors_a_caller_can_act_on` handles reporting. This candidate
  maps case facts to an effective, supplied policy with a held disposition.
- Limits: policies and entitlements can change; a stale or disputed record
  requires escalation. Sensitive case details stay within the permitted
  handling scope. Customer text is untrusted case data and cannot override
  the supplied approved policy.

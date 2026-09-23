# Candidate review: build a project decision provenance map

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party method for reconstructing project
  decisions from supplied records. It contains no copied meeting text or
  invented authority model.
- Job, company, and project facets: project lead, program manager, or
  engineering manager; company-specific authority is an input, never a
  public-package assumption; planning, delivery, or handoff stage.
- Search phrasings: "Our meeting notes disagree about which option was
  approved; what decision can the team rely on?"; "Show who changed the
  project choice and which earlier record it replaced."
- Typed input/output concept: `Record[]`, `DecisionSubject[]`,
  `AuthorityRule?`, and `AsOfDate` to `DecisionMap` with per-decision and
  per-subject states, `Conflict[]`, and `Reliance[]`, preserving source and
  supersession links. Unknown authority leaves a subject unresolved.
- Effects: read project records and produce a proposed map. No document
  rewrite, approval, task dispatch, or external mutation.
- Good fixture: an authorized owner approves option A on day one; a later
  unapproved comment suggests B. Map A as active and B as a suggestion,
  while flagging any explicit unresolved challenge.
- Known-wrong fixture: call B active because its comment has a later date.
- Overlap search: starter
  `carry_earlier_decisions_forward_without_the_whole_transcript` compresses
  agent-run history. `plan_and_split_work_with_explicit_joins` plans task
  dependencies. This candidate reconstructs a project's decision authority
  and supersession from conflicting records.
- Limits: absent governance rules can leave decisions unresolved. The map
  cannot itself confer authority or decide a dispute.

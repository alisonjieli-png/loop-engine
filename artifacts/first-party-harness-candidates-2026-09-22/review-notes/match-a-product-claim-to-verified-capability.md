# Candidate review: match a product claim to verified capability

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party claim-checking method grounded in the
  product's distinction between offered, fetched, loaded, used, and verified.
  It copies no product marketing text or customer story.
- Job, company, and project facets: product marketing, release manager, or
  founder; company claim policy and release evidence are inputs; release
  announcement, sales review, or website update stage.
- Search phrasings: "Can our release evidence support saying customers use
  these skills in their harnesses?"; "Which sentences in this launch update
  need narrower wording based on what was actually verified?"
- Typed input/output concept: `ClaimSentence`, `Audience`, `Release`,
  `CapabilityReference[]`, and `JourneyEvidence[]` to `ClaimLedger[]`,
  `Disposition`, `NarrowerWording?`, and `MissingTest[]`.
- Effects: inspect existing records and propose wording. No publication,
  website edit, customer quote, or release.
- Good fixture: 43 items are offered and fetchable in a release, but no
  independent native-load journey is recorded. Support a retrieval claim
  scoped to that release; hold a claim that all items are used by harnesses.
- Known-wrong fixture: infer successful customer use from the catalogue
  manifest count alone.
- Overlap search: starter `reproduce_the_evidence_a_report_claims` checks
  report evidence, and `verify_a_release_after_it_is_live` checks release
  operation. This method decomposes public product wording into capability
  stages and exact release-scoped evidence.
- Limits: internal evidence may be incomplete or private. Human editorial
  and legal review remain separate where required; the skill cannot approve
  its own public claim.

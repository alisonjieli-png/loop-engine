# Candidate review: gate a product launch across teams

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party cross-team launch reasoning based on the customer action promised by an offer. No launch template or third-party checklist was copied.
- Facets: product launch manager, founder, operations, support, or marketing lead; software or service company; preannouncement and limited-rollout stage; actual launch authority is supplied privately.
- Search phrasings: "The site is live; are we really ready to announce signups?"; "Check the whole launch path across product, billing, docs, and support."
- Typed input/output concept: `LaunchIntent`, `Audience`, `JourneyObservation[]`, `GateRule[]`, and `Owner[]` to `LaunchGateMap`, `Hold[]`, and `ScopeRecommendation`.
- Effects: read-only recommendation. No release, registration opening, payment, announcement, or legal publication.
- Positive fixture: the application journey works for invited accounts, public registration is off by design, support owns invited-user response, and billing is not offered to the public. Recommend only the invited scope if that is the stated authority and claim.
- Known-wrong fixture: marketing plans "anyone can sign up today," but the public signup endpoint refuses registration while health checks pass. A go recommendation based only on deployment health must fail the customer access gate.
- Nearest overlap and distinction: starter `run_a_release_check_list_before_deploying` checks deployment readiness; batch-one `match-a-product-claim-to-verified-capability` checks a single public claim. This method links product, access, billing, support, documentation, and communication gates to an end-to-end launch audience and sequence.
- Limits: gates are only as current as their evidence; a passing local path does not prove production. Independent review should test a failing customer journey and a legitimate limited-scope alternative.

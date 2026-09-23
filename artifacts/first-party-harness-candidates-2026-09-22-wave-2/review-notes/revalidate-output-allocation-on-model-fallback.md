# Candidate review: revalidate output allocation on model fallback

Status: candidate only. No independent approval, model call, or measured benefit.

- Original basis: first-party route-change reasoning from this repository's model-capacity and authority contracts. It uses no provider-specific capacity number.
- Facets: model gateway engineer or harness operator; bring-your-own-endpoint agent platform; fallback decision stage; exact provider, interface, model revision, and context variant are required inputs.
- Search phrasings: "The chosen model failed; can we keep the same output limit on the backup?"; "Check the remaining budget before switching this step to another provider."
- Typed input/output concept: `FailureClass`, `PrimaryRoute`, `FallbackRoute`, `CapacityEvidence`, `ModelOutputAllocation`, `RemainingAuthority`, and `VariantEligibility?` to `FallbackEligibility`.
- Effects: read-only decision packet. No route change, provider call, spending, or settings mutation.
- Positive fixture: fallback is permitted, the backup route has source-backed capacity, previous usage is complete, the approved context fits, and a typed fallback-route allocation is explicitly authorized within remaining authority. Return eligible with that newly bound allocation.
- Known-wrong fixtures: (1) The backup model has unknown output capacity and the previous call's usage is missing. Copying the primary model's limit and counting missing usage as zero must fail even if the fallback has the same friendly name. (2) The backup capacity is known, but no typed fallback allocation exists and the full capacity exceeds remaining run authority. Requesting an invented smaller answer-length allowance to make the call fit must fail; hold for a separately authorized allocation or more authority.
- Nearest overlap and distinction: starter `set_an_output_size_from_a_known_limit` defines a limit for one route. This method re-evaluates route eligibility after failure, including prior usage, cumulative authority, context variant, and exact fallback model capacity.
- Limits: static source evidence may become stale and provider billing can be unknown. A reviewer should test semantic fallback permission separately from numerical capacity.

# Candidate review: explain a service charge from effective rules

Status: candidate only. No independent approval, native-load check, customer licence, or measured benefit. Review the exact `packages/project/explain-a-service-charge-from-effective-rules/SKILL.md` bytes before admission.

- Source and original basis: O*NET® 31.0 Database, occupation `43-4051.00`, task ID `2583`, supplied by the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); [database and licence](https://www.onetcenter.org/database.html), [pinned source inventory](../../occupation-grid-research-2026-09-22/README.md). The task reference suggested the opportunity. The charge-reconstruction method and wording are original first-party drafting, not copied task prose or an endorsed O*NET method. Source ZIP SHA-256: `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
- Facets: customer billing explanation or support review; supplied company price schedule and account eligibility; quote before collection. No invented pricing or contractual term.
- Typed concept: `ServiceRequest`, `PriceScheduleVersion[]`, `EligibilityEvidence`, `QuantityEvidence`, `QuoteLine[]` to `ChargeExplanation`, `DifferenceLine[]`, `UnknownInput[]`.
- Effect class: read-only calculation; no invoice, payment, account change, or legal determination.
- Good fixture: the schedule effective at service time says 12 currency units per hour, authorized evidence shows two hours, and a 24-unit line follows the supplied rounding rule.
- Known-wrong fixture: the supplied rule selects the rate at service time, but a quote uses a higher rate effective later. The quote must be flagged despite correct multiplication.
- Nearest overlap: no close starter item binds a service charge to a versioned price rule; starter `verify_the_requested_output` checks an output against supplied criteria in general. Wave one `trace-numeric-rounding` explains arithmetic differences; wave two `reconstruct-service-clock-from-status-intervals` determines counted time. This method joins service, eligibility, effective price version, quantity, and rounding into an itemized charge explanation.
- Limits: missing terms, taxes, or adjustments remain unknown. The result cannot certify what the customer legally owes or authorize collection.
- Search phrasings: "Why does this service quote use today's rate for last week's work?"; "Explain each line of this charge from the price schedule and usage."

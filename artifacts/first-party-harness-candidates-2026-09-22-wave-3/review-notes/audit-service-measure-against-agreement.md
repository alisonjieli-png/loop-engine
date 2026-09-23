# Candidate review: audit-service-measure-against-agreement

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `8937`, occupation `13-1081.00` (Logisticians), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: logistics service analyst; carrier, marketplace, or fulfillment operator; periodic agreement review for a named customer and agreement version.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `ServiceMeasureDefinition`, `AgreementVersion`, `ReportingPeriod`, `EventPopulation`, `PublishedMeasure`.
- Conceptual typed output: `ServiceMeasureAudit` containing a keyed eligibility ledger, recomputed counts, target comparison, and unresolved events.
- Effect class: read-only analysis of supplied records. No agreement edit, case mutation, contact, or legal certification.
- Good fixture: An agreement says a shipment without timely proof counts as missed. Of 100 eligible shipments, 96 have timely proof, two are late, and two lack proof. The result is 96 of 100, with the four failures separately identified.
- Known-wrong fixture: A report omits the two shipments without proof and calls 96 of 98, rounded to 98%, an attained target. Reject the attainment claim because the supplied rule retains those two in the denominator.
- Nearest starter item: `write_acceptance_criteria_a_reviewer_can_check.md` defines a check before delivery; this method applies an existing versioned service definition to population evidence.
- Nearest wave 1 item: `check-rate-denominators` checks population and numerator compatibility; this method additionally tests event dispositions, agreement exclusions, and target attainment.
- Nearest wave 2 item: `reconstruct-service-clock-from-status-intervals` reconstructs counted time for one case; this method audits a population-level measure under the supplied service definition.
- Limits: The candidate must not invent service terms or a legal interpretation. Test changed agreement versions, duplicated shipment identities, late corrections, and unknown scan states in independent review.
- Customer search phrasings: "Our carrier says the monthly target passed; did they drop missing scans?"; "Can you tie each excluded delivery back to the service rule and recalculate the score?"

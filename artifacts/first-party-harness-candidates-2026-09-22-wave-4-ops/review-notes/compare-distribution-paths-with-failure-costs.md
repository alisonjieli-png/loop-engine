# Candidate review: compare-distribution-paths-with-failure-costs

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `8949`, occupation `13-1081.00` (Logisticians), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Wording and example are original; the agency has not endorsed or tested them.
- Applicability: distribution network analyst comparing shipment paths, not supplier offers; route and service evidence must share an evaluation horizon. Model performance is unmeasured.
- Conceptual typed input: `ShipmentConstraint`, `PathHandoffs`, `ChargeBasis`, `TransitEvidence`, `ConsequenceRule`.
- Conceptual typed output: `PathComparison` with eligibility, direct cost, scenario burden and uncertainty.
- Effect class: read-only comparison; no booking or contract change.
- Good case: A route's lower line-haul charge is offset by an evidenced transfer fee and late-arrival consequence, both displayed separately before a conditional choice.
- Known-wrong case: Declare the lowest carrier quote cheapest while omitting a mandatory transfer leg and counting a late path as meeting a hard arrival promise.
- Nearest starter item: `forecast_an_action_then_compare.md` sets up a prospective comparison; this method reconstructs path handoffs and quote basis before scenario-based logistics comparison.
- Nearest earlier candidate: `normalize-vendor-offers-for-one-decision` compares offers from vendors; this method compares end-to-end movement paths and disruption consequences.
- Limits: Historical disruption data may be sparse; do not invent probabilities or recovery costs. The customer supplies valuation and constraints.
- Customer search phrasings: "The carrier quote is low but the route has an extra transfer. Compare the real options."; "Could a cheaper path miss our delivery window?"

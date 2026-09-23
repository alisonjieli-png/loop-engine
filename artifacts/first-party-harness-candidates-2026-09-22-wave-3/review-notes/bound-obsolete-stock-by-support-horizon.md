# Candidate review: bound-obsolete-stock-by-support-horizon

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `8951`, occupation `13-1081.00` (Logisticians), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: parts planner or inventory analyst; manufacturer, repair network, or distributor; revision changeover and support-horizon review.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `RevisionStock`, `CompatibilityRules`, `SupportHorizon`, `DemandEvidence`, `AllocationRule`.
- Conceptual typed output: `RevisionExposureTable` and `DemandAllocationLedger` with firm-covered, compatible but uncovered, unsupported, and unresolved quantities by revision.
- Effect class: read-only analysis. No reservation, sale, transfer, write-off, or disposal.
- Good fixture: Revision A has 12 units and a supported repair program with six uniquely identified firm demand units in the horizon. The ledger covers six units and leaves six compatible but uncovered and at risk when no other demand is supplied. It does not call the uncovered six obsolete without a supplied rule.
- Known-wrong fixture: A planner labels all 12 older-revision units obsolete solely because revision B exists. Reject the blanket classification while the supported repair use remains valid. Also reject a report that calls all 100 units of an older revision covered because one supported use exists when that use has only five uniquely assigned demand units; at most five are firm-covered, and 95 remain uncovered or unresolved.
- Nearest starter item: `check_a_table_join_before_trusting_it.md` catches stock-to-compatibility multiplication; it does not interpret revision support and future use.
- Nearest wave 1 item: `validate-aggregate-grain` prevents double-counting stock snapshots; it does not classify revision-level exposure across a support horizon.
- Nearest wave 2 item: `reconcile-inventory-availability` computes current sellable quantity at one cutoff; this method tests future usability of each revision under supplied support and demand rules.
- Limits: Demand can be shared by revisions, forecasts may be wrong, and a support cutoff may change. Independent review should test missing compatibility, overlapping demand allocations, quantity greater than uniquely assigned demand, and a revision with no known stock identity. This is not an accounting write-off decision.
- Customer search phrasings: "Are our old spare parts really stranded after the new model ships?"; "Which revision quantities still have a supported customer use next quarter?"

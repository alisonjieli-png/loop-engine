# Candidate review: normalize vendor offers for one decision

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party procedure written for this batch from the
  buyer's explicit comparison problem and ordinary arithmetic. No offer text,
  vendor policy, or third-party skill was imported.
- Job, company, and project facets: procurement, finance, or technical buyer;
  any company with a declared workload and decision rule; vendor selection or
  renewal stage. Vendor names are input values, not prewritten rules.
- Search phrasings: "Which of these service quotes fits our monthly usage
  once limits and add-ons are counted?"; "Compare these offers when one uses
  seat pricing and the other charges for each request."
- Typed input/output concept: `Offer[]`, `Workload`, `DecisionRule`, and
  `Assumption[]` to `NormalizedOffer[]`, `UnknownTerm[]`, and
  `ConditionalConclusion` with source references.
- Effects: read supplied documents and calculate. No vendor contact, quote
  request, purchase, contract commitment, or account change.
- Good fixture: Offer A is 100 dollars monthly for 1,000 uses with unstated
  overage; Offer B is 12 cents per use. At 1,200 uses the result shows B as
  144 dollars and A as `100 dollars plus unknown overage`, so no total ranking.
- Known-wrong fixture: report A as 100 dollars and cheaper without stating
  that 200 uses exceed its allowance.
- Overlap search: compared with starter `choose_metrics_by_task_type_and_industry`,
  `freeze_the_success_metric_before_measuring`, and
  `report_observed_derived_assumed_and_unknown`. This candidate applies a
  specific offer-unit normalization and requirement matrix; it should be
  rejected as redundant if independent review finds the same method elsewhere.
- Limits: tax, legal terms, exchange rates, and vendor capability claims are
  not verified. A human buyer supplies and owns the decision rule.

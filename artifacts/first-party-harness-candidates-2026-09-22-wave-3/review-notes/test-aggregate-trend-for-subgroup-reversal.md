# Candidate review: test-aggregate-trend-for-subgroup-reversal

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `21832`, occupation `15-2051.00` (Data Scientists), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: data scientist or analyst; any organization comparing outcomes across groups; analytical claim review before reporting a trend.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `AggregateClaim`, `OutcomeDefinition`, `ComparableGroups`, `GroupCounts`, optional `ReferenceMix`.
- Conceptual typed output: `StratifiedClaimReview` with aggregate and group rates, weight changes, reversal verdict, and unresolved confounders.
- Effect class: read-only analysis. No dataset edit, policy change, or external publication.
- Good fixture: In period one, group A has 90 successes of 100 and group B has 90 of 900, yielding 180 of 1,000 overall. In period two, A has 720 of 900 and B has zero of 100, yielding 720 of 1,000 overall. The aggregate rises from 18% to 72% while both group rates fall; report a composition reversal and the changing weights.
- Known-wrong fixture: A report says performance improved for both groups because the total rose. Reject the subgroup inference and avoid a causal explanation from the reversal alone.
- Nearest starter item: `check_that_a_result_is_stable_and_generalizes.md` checks broad stability across runs and populations; this method computes a specific within-group versus aggregate reversal.
- Nearest wave 1 item: `validate-aggregate-grain` checks whether a measure can be summed; this method tests how group weights change a correctly computed rate across conditions.
- Nearest wave 2 item: `compare-acquisition-channels-for-one-segment` compares channel evidence within one segment; this method challenges a pooled analytical relationship across changing segments.
- Limits: Groups need stable meaning and comparable observation windows. Independent review should test overlapping groups, zero denominators, sparse cells, and an apparent reversal caused by changed outcome definitions. This method is distinct from survey-specific response-mix review because it applies to any grouped outcome relationship and does not audit invitation frames.
- Customer search phrasings: "Why did the total improve when every segment got worse?"; "Is the apparent lift just a shift toward a high-performing group?"

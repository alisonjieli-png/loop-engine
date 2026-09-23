# Candidate review: compare acquisition channels for one segment

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party decision method for choosing a bounded channel test using comparable funnel stages and unknown costs. No platform playbook, rate benchmark, or outside conversion estimate was used.
- Facets: founder, growth lead, or marketing analyst; early business-to-business software or service; channel selection before spend; company budget and channel permission are supplied.
- Search phrasings: "Should we try developer communities or search ads for this buyer?"; "Compare these acquisition options without calling clicks paying customers."
- Typed input/output concept: `SegmentDefinition`, `Offer`, `ChannelEvidence[]`, `BudgetAuthority?`, and `OutcomeRule` to `ChannelComparison`, `TestOrder`, and `Uncertainty[]`.
- Effects: read-only analysis. No ad purchase, scraping, contact, or publication.
- Positive fixture: one channel has 40 eligible trial starts from a stated spend; another has 200 clicks but unknown account eligibility and spend. Report the first channel's observed trial starts, mark the second noncomparable, and propose a bounded measurement test if authorized.
- Known-wrong fixture: two channels claim 50 conversions each but use the same attribution window and the same people; one counts clicks, the other counts paying accounts. Summing them to 100 acquired paying customers or ranking by raw totals must fail stage and deduplication checks.
- Nearest overlap and distinction: batch-one `design-a-bounded-product-experiment` specifies random assignment and outcomes for a product change; `normalize-vendor-offers-for-one-decision` compares purchasing quotes. This method evaluates acquisition channel access and evidence for a single segment and proposes a bounded test, without running one.
- Limits: selection bias and incomplete attribution remain; the method cannot promise cost per customer. Independent review should check cohort, time window, funnel stage, and source dates.

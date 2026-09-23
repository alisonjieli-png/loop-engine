# Candidate review: map system output to permitted consumers

Status: candidate only. No independent approval, native load, licence assignment, or measured benefit.

- Source and originality: Original procedure written for this batch. Need inspiration is task `15-1211.00 / 3484` in the pinned [O*NET® 31.0 Database inventory](../../occupation-grid-research-2026-09-22/README.md) by the U.S. Department of Labor, Employment and Training Administration, under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). No task prose or third-party skill text was copied; the agency did not approve or test this candidate.
- Facets: Systems analyst, privacy engineer, data product owner; new report or event-stream design; company policy and retention rule supplied by the customer.
- Typed input/output concept: `OutputField[]`, `Consumer[]`, `Purpose[]`, `AccessRule[]`, `RetentionRule[]` to `FieldDistributionMatrix` and `UnresolvedGrant[]`.
- Effects: Read-only design review. No actual field export, grant, deletion or retention change.
- Good fixture: An operations dashboard needs a customer count, while its source feed includes a person-level identifier. The matrix proposes a permitted aggregate only if the supplied rule supports it and holds the identifier for that consumer.
- Known-wrong fixture: A configured recipient can technically subscribe to the feed, so a design sends every field to it despite an absent purpose grant. The method must mark those cells unknown or prohibited and omit them from proposed delivery.
- Search phrasings: “Who is allowed to receive each field in this new event?”; “This report is technically reachable, but which teams may retain its customer data?”
- Nearest overlap and distinction: Starter `review_authorisation_on_every_path` checks code paths; wave two `qualify-a-partner-integration-proposal` checks a partner integration. This method maps each output field to consumer purpose, minimization and retention for one proposed distribution.
- Limits: Source classifications and access rules are supplied, not inferred by the skill. An approved matrix would still require a separate access decision and runtime enforcement test.

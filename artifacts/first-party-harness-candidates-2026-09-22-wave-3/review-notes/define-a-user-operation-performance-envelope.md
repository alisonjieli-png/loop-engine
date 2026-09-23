# Candidate review: define a user operation performance envelope

Status: candidate only. No independent approval, native load, licence assignment, or measured benefit.

- Source and originality: Original procedure written for this batch. Need inspiration is task `15-1252.00 / 21668` in the pinned [O*NET® 31.0 Database inventory](../../occupation-grid-research-2026-09-22/README.md) by the U.S. Department of Labor, Employment and Training Administration, under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). No task prose or third-party skill text was copied; the agency did not approve or test this candidate.
- Facets: Software developer, reliability engineer, product acceptance; one user operation and deployment class; workload and deadline supplied by owner.
- Typed input/output concept: `UserOperation`, `WorkloadClass[]`, `DeadlineRule[]`, `ResourceLimit[]`, `FailureAccounting` to `PerformanceEnvelope` and `ProbePlan`.
- Effects: Read-only test design. No traffic generation, load test, deployment or limit change.
- Good fixture: A checkout operation has a 99th-percentile deadline for a low-volume large-cart class and a resource ceiling. The envelope keeps that class separate and counts timed-out requests as failures.
- Known-wrong fixture: A test passes because overall mean latency is low after excluding timeouts, while the large-cart class misses its declared deadline. The envelope must reject the pass despite the attractive mean.
- Search phrasings: “What does fast enough mean for this exact user action under peak load?”; “Our average latency looks fine, but which important request class is failing?”
- Nearest overlap and distinction: Starter `use_percentiles_not_averages_for_response_time` chooses a statistic; `build_a_repeatable_performance_test` concerns a run. This method defines the versioned operation, workload, failure and resource acceptance contract before any run.
- Limits: No target or workload is invented. The method cannot claim actual performance or run a load test; the environment and sample rule need independent review.

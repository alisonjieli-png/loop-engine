# Candidate review: reconcile native material use evidence

Status: candidate only. No independent approval, native client run, or measured benefit.

- Original basis: first-party evidence-chain method for one selected material item. It follows the repository's distinction among offered, fetched, loaded, used, and verified without copying catalogue text.
- Facets: evaluator, harness integrator, or customer success engineer; developer-tool or agent-service company; post-run evidence review; exact harness and model run identity required.
- Search phrasings: "Did the agent actually use the skill we installed?"; "The run says it used this context file; what evidence do we have?"
- Typed input/output concept: `ApprovedItemIdentity`, `RunIdentity`, `HostEvent[]`, `NativeObservation[]`, and `AcceptanceRecord?` to `MaterialUseEvidenceChain` and `UnresolvedLink[]`.
- Effects: read-only record comparison. No re-execution, fetch, install, or claim publication.
- Positive fixture: host records offer and fetch of digest A; placement and native load events for the same run name digest A; a trace cites the loaded instruction; an independent evaluator accepts the task artifact. Report each state with its separate source.
- Known-wrong fixture: a skill file exists and is listed by native discovery, but no load or use event exists and the producer says "skill applied." Reporting used and verified from those facts must fail.
- Nearest overlap and distinction: first-batch `map-independent-acceptance-evidence` maps general task claims and provenance. This method reconciles exact harness material identity across the client loading sequence and preserves unobservable use as unknown.
- Limits: instrumentation may be too weak to observe use directly; task acceptance does not prove causation by the item. A paired task comparison is separate.

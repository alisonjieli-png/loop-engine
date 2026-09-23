# Candidate review: map observed customer journey friction

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party procedure drafted around the distinction
  between a session observation and a causal product hypothesis. No session
  data or outside skill text was imported.
- Job, company, and project facets: product researcher, designer, or customer
  success analyst; company type is irrelevant unless it changes consent and
  privacy requirements; onboarding or task-completion research stage.
- Search phrasings: "Where did people get stuck in these observed sign-up
  sessions?"; "Map the steps users took to connect our tool and suggest what
  we should investigate next."
- Typed input/output concept: `ConsentedSession[]`, `Task`, and
  `InterfaceVersion` to `JourneyStage[]`, `Obstacle[]`, `Denominator`, and
  `DiagnosticTest[]`, each linked to session evidence.
- Effects: read supplied observations and draft an internal map. No user
  contact, telemetry collection, interface edit, or personal-data sharing.
- Good fixture: four observed sessions, two with the same confirmation-link
  reversal, one unrelated error, and one clean completion. Report two of
  four observed sessions with that reversal, and ask whether link delivery
  or explanation caused it.
- Known-wrong fixture: claim that half of all customers cannot sign up and
  that email delivery is the cause, based only on those four sessions.
- Overlap search: starter `report_observed_derived_assumed_and_unknown`,
  `analyse_errors_by_segment_and_cluster`, and
  `choose_metrics_by_task_type_and_industry` cover general evidence or
  metrics. This method orders an observed task path and connects obstacles
  to stage, denominator, and a discriminating next observation.
- Limits: small and selected sessions cannot estimate population prevalence;
  participant statements may be incomplete; consent scope governs sharing.

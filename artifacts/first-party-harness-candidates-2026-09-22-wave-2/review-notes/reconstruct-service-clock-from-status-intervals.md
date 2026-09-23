# Candidate review: reconstruct-service-clock-from-status-intervals

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general event-interval reasoning after inspecting the 123 starter bodies and first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No service-level promise, contract, or external taxonomy was imported.
- Job, company archetype, and project facets: support operations analyst or service manager; a company measuring case response or resolution time; timer discrepancy investigation or policy migration.
- Model applicability: general text-capable harnesses; no model-specific proof.
- Conceptual typed input: `CaseEvents`, `PolicyVersion`, `WorkingCalendar`, `Cutoff`, `DisplayedTimer`.
- Conceptual typed output: `ServiceClockReconstruction` with classified intervals, counted and wall durations, unresolved events, and timer difference.
- Effect intent: read-only analysis. It does not authorize case-status changes, external communications, or a service commitment.
- Positive fixture: A case starts at 09:00, pauses at 10:00, resumes at 11:00, and completes at 12:00. Under a supplied policy that excludes the pause, wall time is three hours and counted time is two hours.
- Known-wrong fixture: A report counts all three wall hours as policy time without applying the supplied pause rule, or silently treats an undocumented status as a pause. Neither result is justified.
- Nearest overlap: Starter `build_an_incident_timeline_from_evidence.md` orders events. First-batch `define-time-zone-reporting-window` computes report boundaries. This candidate turns one case's status intervals into a policy-counted clock with explicit pause and calendar rules.
- Limitations: This is not legal or contractual advice. A reviewer should test simultaneous events, a missing resume, working-hours calendars, and corrected timestamps.
- Customer search phrasings: "Why does the support timer show two hours when this ticket was open for three?"; "Rebuild the service clock from status changes and show exactly which intervals counted."

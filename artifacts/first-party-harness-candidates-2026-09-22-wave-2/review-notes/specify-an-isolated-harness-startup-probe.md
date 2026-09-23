# Candidate review: specify an isolated harness startup probe

Status: candidate only. No independent approval, probe execution, native-load test, or measured benefit.

- Original basis: first-party isolation-test design informed by this repository's native harness instance research. No external test suite, real customer material, or credential is copied.
- Facets: harness engineer, security tester, or platform operator; local-first developer tool; executor qualification stage; exact client version required; model route irrelevant to source discovery.
- Search phrasings: "Could this new agent still read my global skills?"; "Design a check that catches an instruction inherited from the parent folder."
- Typed input/output concept: `ClientDiscoveryProfile`, `SelectedManifest`, `InstanceRoots`, and `ObservationInterface` to `StartupProbeMatrix` with positive and negative canaries.
- Effects: read-only probe specification. No canary write, launch, model call, or environment change.
- Positive fixture: the chosen skill appears under the isolated project path; a synthetic unselected skill sits in an ancestor for a later authorized fixture. The matrix expects the chosen skill and a refusal on the ancestor skill.
- Known-wrong fixture: the work directory contains only selected files, but the client's real home contains an unselected skill. A probe that inspects only the work directory and declares isolation must fail source coverage.
- Nearest overlap and distinction: first-batch `separate-shared-build-cache-from-task-state` classifies reusable build storage, not instruction discovery. Starter `assemble_the_context_for_one_step` selects context, while this method specifies a negative startup-source test for an actual native client.
- Limits: without client telemetry a probe may observe discovery but not later use. Independent review should verify that the proposed observation interface covers the exact client version.

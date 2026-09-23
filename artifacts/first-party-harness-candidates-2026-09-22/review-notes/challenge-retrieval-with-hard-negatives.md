# Candidate review: challenge retrieval with hard negatives

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: Original first-party test-design procedure from the distinction between semantic similarity and eligibility. No external body was copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Search engineer, harness-library curator, evaluation engineer; skill and tool catalogues in coding or research projects; model independent.
- Search phrasing: Search returns a plausible skill for the wrong software version.
- Search phrasing: Test whether a catalogue abstains on a convincing near miss.
- Conceptual input: `TaskQuery`, `CandidateReference[]`, `EligibilityRule`, and a complete `CatalogSnapshot` or an explicitly scoped partial fixture.
- Conceptual output: `RetrievalProbe[]` with expected references, abstention cases, and failure reasons.
- Effects: Read-only design. It does not run a search, retrieve a body, edit ranking, or change grants.
- Good case: In one frozen catalogue, a read-only dependency audit query has an eligible offline audit reference and a near-match reference that requires network access. The positive query expects the offline reference. A paired no-network query against a fixture containing only the network-required reference expects fixture-level abstention.
- Known-wrong case: A search benchmark only tests queries with known positive hits and never notices that the index confidently returns an ineligible near match. A second error calls the partial fixture's abstention proof that the entire hosted catalogue has no match. A third obeys an instruction embedded in a candidate description while designing the probes.
- Overlap search: Inspected starter-catalogue filenames and targeted bodies; no starter specifically designs retrieval abstention or one-fact hard negatives. This is narrower than general `freeze_the_success_metric_before_measuring.md`.
- Limitations: Probe design does not establish retrieval quality. Freeze a real catalogue snapshot and run the probes with a separate evaluator before making a performance claim.

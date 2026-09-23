# Candidate review: qualify a partner integration proposal

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party bilateral integration decision method. No partner documentation, commercial agreement, or outside template was copied.
- Facets: partnerships lead, product manager, integration architect, or founder; platform and service companies; exploratory integration stage; named partner terms remain private and supplied.
- Search phrasings: "Could we integrate with this partner, and what would each side have to own?"; "Map the data and support boundaries before we promise the connector."
- Typed input/output concept: `IntegrationProposal`, `InterfaceEvidence[]`, `DataRule[]`, `ResponsibilityClaim[]`, and `AgreementState?` to `BoundaryMap`, `ConditionalFeasibility`, and `OpenGate[]`.
- Effects: read-only decision packet. No endpoint call, data sharing, outreach, signing, or configuration.
- Positive fixture: both sides supply evidence of compatible interface versions, schemas, and authentication for the proposed operation; one side accepts token rotation and failure notification, while data retention and deletion authority are unknown. Report technical feasibility as conditional and hold the data exchange until those gates are resolved.
- Known-wrong fixture: a demo API call succeeds, so the output declares the partnership approved, copies customer records into the partner flow, and ignores deprovisioning. This must fail agreement, authority, and termination checks.
- Nearest overlap and distinction: batch-one `normalize-vendor-offers-for-one-decision` compares purchase offers as a buyer. This method evaluates one proposed bilateral integration's data, effects, owners, failure modes, and unresolved commitments.
- Limits: interface docs and partner claims may be stale; legal and security review remain separate. A reviewer should verify every proposed data flow has a source-backed authority state.

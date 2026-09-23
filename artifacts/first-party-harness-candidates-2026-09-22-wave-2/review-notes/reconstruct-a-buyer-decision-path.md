# Candidate review: reconstruct a buyer decision path

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party mapping of an organizational decision from observed communications and supplied process records. No sales playbook or third-party prose was copied.
- Facets: account executive, founder, sales engineer, or partnership lead; organization buying a developer tool or service; evaluation and procurement stage; the prospect's own rules are private inputs.
- Search phrasings: "Our champion likes the product, but who actually has to approve the purchase?"; "Turn these meeting notes into the remaining buying steps without assuming the VP can sign."
- Typed input/output concept: `AccountEvidence[]`, `OfferScope`, `DecisionDate`, and `RecipientScope?` to a minimized `ParticipantRoleMap`, `DecisionGate[]`, `Blocker[]`, and `ValidationQuestion[]`.
- Effects: read-only internal analysis. No outreach, quote generation, or agreement.
- Positive fixture: an engineer confirms technical fit, a manager schedules a security review, and a procurement note names an approver. An internal path distinguishes recommendation, security gate, and purchasing decision with exact sources while displaying role labels unless a recipient needs names.
- Known-wrong fixture: a vice president says "looks good" but a supplied procurement guide requires a separate signer and no approval exists. Marking the deal approved because of the senior title must fail.
- Nearest overlap and distinction: batch-one `build-a-project-decision-provenance-map` reconstructs project decisions already made. This method maps the prospect's not-yet-complete organizational buying path, participants, objections, and gates without declaring an approval.
- Limits: informal notes may omit a gate; the method cannot certify a buyer's internal authority. A reviewer should check each assigned role against evidence, the output's recipient scope, and whether unnecessary identity or invented company policy appears.

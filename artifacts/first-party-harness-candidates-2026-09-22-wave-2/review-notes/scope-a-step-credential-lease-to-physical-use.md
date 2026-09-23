# Candidate review: scope a step credential lease to physical use

Status: candidate only. No independent approval, credential use, or measured benefit.

- Original basis: first-party broker-binding design from the repository's credential-delegation research and least-authority principle. It contains no credential value or copied provider procedure.
- Facets: local agent-platform engineer or security reviewer; customer-owned endpoint and tool connections; per-step launch design; provider/model/recipient supplied exactly.
- Search phrasings: "How does a fresh agent use my local model without getting my API key?"; "Check whether this one-step token lease can call a different tool server."
- Typed input/output concept: `StepIdentity`, `CredentialReferenceMetadata`, `Recipient`, `AllowedOperation[]`, `LeaseEnvelope`, and `PhysicalRequest?` to `LeaseBindingMatrix` and `RefusalCase[]`.
- Effects: read-only review. No secret lookup, lease creation, model call, or tool use.
- Positive fixture: a step has a broker capability for one named provider route, a fixed expiry, and two calls. The proposed broker authenticates the step for each physical call and refuses a third call or another route.
- Known-wrong fixture: the child process presents only an unverified lease identifier; the broker accepts it for a different endpoint. A review declaring exact scoping from the lease record alone must fail caller and recipient binding.
- Nearest overlap and distinction: starter `scope_a_credential_to_the_smallest_permission` governs the grant on a credential. This method checks the *delegation path* from a fresh process through a broker at physical use, including caller identity, endpoint audience, cumulative ceiling, and fallback trust profile.
- Limits: paper design cannot prove isolation or broker enforcement. Independent review should challenge spoofed caller identity, route change, expiry, and direct-key fallback.

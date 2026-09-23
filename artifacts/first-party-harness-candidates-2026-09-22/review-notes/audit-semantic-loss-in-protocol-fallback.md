# Candidate review: audit semantic loss in protocol fallback

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party wording and obligation-matrix method drafted for this batch from common interface reasoning. No third-party body was used. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Platform engineer, integration engineer, plugin maintainer; rolling-upgrade and multi-adapter projects; independent of model size.
- Search phrasing: An older plugin protocol parses but loses a required rejection reason.
- Search phrasing: Check whether an adapter carries the permission receipt during downgrade.
- Conceptual input: `RequiredObligation[]`, `ProposedBinding`, and `InteractionExample[]`.
- Conceptual output: `SemanticFallbackAssessment` with obligation status, proposed checks, and eligible or ineligible conclusion.
- Effects: Read-only contract analysis; no handshake, provider call, deployment, or record mutation.
- Good case: A fallback omits an approval receipt; the matrix marks its required audit obligation missing even though requests parse successfully.
- Known-wrong case: An adapter maps two distinct failure states to one generic success code and is declared compatible because the JSON fields still match.
- Overlap search: Compared with starter bodies `negotiate_a_supported_version_at_connection_time.md` and `version_an_interface_so_older_callers_keep_working.md`. Those cover negotiation and version rollout; this candidate maps semantic obligations before approving a particular fallback.
- Limitations: A matrix cannot prove that implementation follows the mapping. Independent contract and interaction checks must be run before eligibility becomes an implementation claim.

# Candidate review: adjudicate a protocol tool effect request

Status: candidate only. No independent approval, tool call, or measured benefit.

- Original basis: first-party exact-effect review informed by typed tool boundaries and the repository's effect rules. No server tool description or credential is copied.
- Facets: harness operator, tool-broker engineer, or security reviewer; agent platform; immediately before a proposed tool call; model identity does not confer effect authority.
- Search phrasings: "Can this agent use the connected tool to send this message?"; "Review this MCP tool request against the approval and recipient it was given."
- Typed input/output concept: `RegisteredTool`, `TypedCall`, `EffectAuthority`, `ApprovalRecord?`, and `CredentialAudience` to `EligibilityDecision` tied to exact parameters.
- Effects: read-only adjudication. No protocol connection, token resolution, send, write, or purchase.
- Positive fixture: an approved read of one project record uses a registered read-only tool and exact target. Return eligible for that request alone, subject to broker execution checks.
- Known-wrong fixture: an approval covers reading project A, but the proposed tool parameters write project B; schema validation passes. An eligibility decision based only on schema or server name must fail effect, target, and approval binding.
- Nearest overlap and distinction: starter `review_authorisation_on_every_path` audits application paths generally; first-batch `audit-semantic-loss-in-protocol-fallback` checks adapter-version meaning. This method decides one exact proposed protocol-tool operation through typed effect, recipient, and approval boundaries.
- Limits: a read-only packet cannot prove the remote server enforces its declared effects. Independent review should test parameter changes, unknown completion, and credential audience mismatch at the broker boundary.

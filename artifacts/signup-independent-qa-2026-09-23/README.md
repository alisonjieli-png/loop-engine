# Independent signup QA evidence

September 23, 2026. Read-only source review and local fixture replay of the frozen
`signup-flow` candidate. No real provider, email, model, signup, setting change
or deployment operation occurred.

- `source-bindings.json`: all hashes match the author's frozen source set.
- `account-email-replay-2.json`: 87 owning checks pass.
- `session-boundaries-replay.json`: six real-browser checks pass using local
  identity/mail stand-ins, including stale-account and delayed-response controls.
- `password-policy-replay.txt`: two local policy checks pass.
- `initial-run-note.txt`: records the first incorrect test entrypoint.

The documentation sources independently opened on this date were Supabase's
generateLink, verifyOtp, password-security and signout references. The full
[QA report](../../docs/verification/SIGNUP-INDEPENDENT-QA-2026-09-23.md) separates
local results from live deployment prerequisites. The source/fixture methods are
not a penetration test, distributed rate-limit proof or live provider acceptance.

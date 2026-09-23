# Independent hardcoding exception QA

Only this QA folder and its report were written. Integration source, allowlist,
generator, baseline and audit implementation were not changed.

- `inventory-and-bindings.json`: first snapshot, 36 new exact entries, two exact
  exclusions, unchanged old entries/baseline, full 139-finding reconciliation and
  credential-shape check of the evidence bodies.
- `independent-focused-audit.json`: deterministic audit over the original triage paths
  and new prompt resource, zero new high/critical blockers. Medium findings remain.
- `generation-resource-controls.txt`: five focused fixture-only resource/credential
  checks pass. No provider calls.
- `nonweakening-canaries.json`: original HEAD allowlist restores 137 blockers; changed
  evidence bytes in memory invalidate that exact exclusion and reject verification.
- `signup-successor-and-reconciliation.json`: final 37th entry for the separate new
  browser signup checkout assertion; zero new high blocker and exact original-ID
  reconciliation.
- `source-bindings.json`: final hashes of every inspected source and governing input.

The original root triage and intermediate failed audits remain at
`artifacts/consolidated-hardcoding-triage-2026-09-23/` in integration. They were read,
not modified or relabeled.

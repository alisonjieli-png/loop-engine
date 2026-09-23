# Signup restoration evidence

See [the implementation handoff](../../docs/verification/SIGNUP-FLOW-RESTORED-2026-09-23.md)
for scope, sources, failures, repairs and release prerequisites.

The current large runs are `http-owning-suite-final.json` and
`browser-final.json`. The former has 587 passing checks. The latter has 589
passing checks and detects 105 mutation controls, including the new account
switch and asynchronous confirmation controls.

The original archived patch, merge inputs, failed browser runs and failed
session probes remain available. `session-boundary-before.json` has a fixture
status mistake; `session-boundary-before-corrected-fixture.json` is the valid
account-switch counterexample. `docs-delta` holds exact proposed text for the
separate restored-guide delta, not another canonical documentation source.

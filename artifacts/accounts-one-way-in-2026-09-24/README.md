# Evidence for the accounts release of September 24, 2026

Kind: dated evidence folder for
[the accounts release record](../../docs/verification/ACCOUNTS-ONE-WAY-IN-2026-09-24.md).
Local checks only. No provider, mailbox, host file or secret was used.

Each file is a summary written from a run on the committed tree after it was
rebased onto release 23. Check names, counts and outcomes are kept; details
that can carry fixture tokens, page text or test addresses stay out, and the
screenshots stay in the scratch folder of the session.

| File | What it holds |
|---|---|
| `owning-checks.json` | The two new check modules and the browser identity checks, each check by name |
| `service-smoke.json` | The service smoke suite, which runs every service check module |
| `browser-suite-summary.json` | The workspace browser suite: every check and every removed-guard control |
| `suite-results.json` | The self-test, conformance, tools suite and hardcoding gate outcomes |

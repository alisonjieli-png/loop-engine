# Candidate review identity and process-exit successor, September 23, 2026

Independent review found two additional known-wrong cases after the
[first integrity repair](CANDIDATE-REVIEW-INTEGRITY-REPAIR-2026-09-23.md).
The first patch and its failed and passing evidence remain unchanged.

1. Claude's reader accepted success-shaped JSON after a nonzero process exit.
   It now treats a nonzero exit as failure and preserves any reported usage.
2. The fixed panel accepted an `ANSWERED` result from a substituted engine
   without checking its reported model. It now requires that reported model
   to exactly equal the configured reviewer model before parsing a verdict.
   Missing and different identity become `model_identity_mismatch` with no
   verdict, while the actual usage and physical-call observations remain.

The generic fixture responses in the test harness are explicitly bound to
their configured fixture model. Deliberately missing or different identities
are preserved so the new negative cases exercise the production panel guard.
No production engine substitutes requested identity for reported identity.

## Evidence

- [Before successor](../../artifacts/candidate-review-integrity-2026-09-23/tests-before-successor.txt):
  both named checks failed.
- [After successor](../../artifacts/candidate-review-integrity-2026-09-23/tests-after-successor.txt):
  237 owning-component tests passed, with one existing optional dependency skip.
- [Removed guards](../../artifacts/candidate-review-integrity-2026-09-23/removed-guards-20260923T141619395533.json):
  eight baselines passed and all eight removed guards caused assertion failures.

The fixed panel guard applies to newly answered calls. Version-one persisted
verdicts lack serialized answering-model identity. This successor does not
reinterpret or modify those historical records. The planned native package
review record must preserve reported identity and exact package binding in a
new version before it can support admission.

No model/provider calls, catalogue approvals, commits or deployments occurred.
The integrating session owns composed-tree checks and the release.

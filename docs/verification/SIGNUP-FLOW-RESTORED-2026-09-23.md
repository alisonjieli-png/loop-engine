# Email-first signup and Get started restoration

Kind: dated implementation and verification handoff. Candidate, not deployed.

## Scope and source

This work uses detached `signup-flow` at
`1920296c00ced18e47992ae05237f4a2923666f0`. It restores the archived
`signup-81256882.patch` and completes the local verification and repairs below.
The [original handoff](HANDOFF-signup-2026-09-23.md) stays historical.

No live signup, mail send, model call, provider setting change, registration
activation, commit, push or deployment occurred in this lane. Identity and mail
calls in the tests go to the existing local stand-in and its outbox. They do
not establish live Supabase or Resend qualification.

## Implemented flow

```text
Account access
├── Get started and signup
│   ├── Open registration: email-only request and approved consent text
│   ├── Closed registration with a waiting list: invitation link
│   └── Closed registration without a waiting list: sign-in for existing accounts
├── Confirmation and recovery
│   ├── Clear token parameters from the address and history
│   ├── On submit, verify the link, then set the chosen password
│   ├── Keep verification bound to that page's identity and connection generation
│   └── Activate only after password acceptance and a current connection
└── Plan and setup
    ├── Read the recorded source of account access
    ├── An operator invitation or promotion can cover the plan
    └── Offer the existing checkout only when available, then the setup guide
```

The signup request is `service_account_signup_request/v2`. Version 1 and a
caller-supplied password are refused before the account-email attempt is
counted or a provider is called. The service generates the temporary password
inside its identity request, retains no copy, and sends its own message. The
browser collects the person's password on the confirmation page, typed twice.
The service signup endpoint never receives it.

The hosted registration capability is true only when browser identity and the
account-email adapter both allow signup. Deployment has an additional required
prerequisite: the identity provider's public signup must be closed. This lane
does not change that setting or assert that it is already closed.

## Findings and repairs

### A pending confirmation could change another account's password

Reproducer: start confirmation for account A, pass link verification but fail
the email-as-password rule, then sign into B in the same document and return to
A's pending confirmation. The archived patch retained A's session reference
while the identity SDK now held B's session. The next password update changed
B's password, and the following service activation used A's token.

The corrected local record shows the original B password changing from HTTP
200 to HTTP 400, with the replacement becoming accepted, before the repair.
The repair invalidates a pending confirmation whenever the service connection
changes and clears its password controls. Each asynchronous stage captures and
rechecks the same confirmation object, identity client and connection generation.
The successor keeps B's password unchanged.

### Late responses could reconnect a disconnected page

The added tests hold a verification response and, separately, a password-update
response, then invoke the page's existing disconnect action. The repair prevents
a password update after a cancelled verification and prevents activation after
either disconnect. A password update already accepted by the local identity
provider before the disconnect remains an observed write; the code does not
claim cancellation undoes it.

The disconnect action is invoked programmatically in these two controls because
a confirmation page has not yet exposed signed-in navigation. That substitution
is explicit. The account-switch reproducer uses the actual sign-in form and
normal application navigation.

### Closed access could offer a form that did not exist

The saved funnel always offered an invitation, even when the service reported
no waiting list. It now uses that capability to choose the invitation path or
sign-in. The closed fallback also removes the duplicate secondary sign-in link.

### Generated passwords did not cover every admitted host minimum

The archived generator returned 47 ASCII bytes while host settings admit a
minimum through 72. A provider configured with a higher minimum could reject
new signup. The generator now encodes 51 random bytes plus four required
character groups, producing 72 ASCII bytes. Two focused checks cover the
supported maximum and detect restoring the old byte count. The provider's own
password policy still requires live qualification.

### Merge and browser checks

The merge preserved the current header, footer, terms, logo, cache behavior and
existing guards. It resolved the email-form and route-title conflicts, removed
duplicate served-route entries and two duplicate test declarations. Older
browser expectations that the header action went straight to the waiting-list
form now exercise Get started followed by the invitation link. The desktop
padding mutant previously lost to phone CSS; it now displaces the content at
both widths and the corresponding checks detect it.

## Evidence

Reports and failed attempts live under
[`artifacts/signup-flow-restoration-2026-09-23`](../../artifacts/signup-flow-restoration-2026-09-23/).

| Verification | Result | Evidence |
| --- | --- | --- |
| Archived backend checks before further repairs | 87 passed | `account-email-before-finishing.json` |
| Complete owning HTTP checks on the successor | 587 passed | `http-owning-suite-final.json` |
| Complete browser checks | 589 passed, 105 of 105 mutants detected | `browser-final.json` |
| Generated password policy | Two passed | `password-policy-after.txt` |
| Initial session-binding defect | Reproduced | `session-boundary-before-corrected-fixture.json` |
| Session switch and cancellation successors | Passed | `session-boundaries-shared-helper.json` and integrated browser run |
| New session guard removals | Both detected by their named checks | `session-mutation-omit-invalidation.json`, `session-mutation-omit-async-guards.json` |
| Closed fallback and duplicate-link failures | Reproduced before repairs | `closed-fallback-before.json`, `duplicate-signin-before.json` |
| Markdown | Six active guides/source notes passed | `markdown-frozen.txt` |
| Fatal Python syntax/name lint and new tests | Passed | `ruff-fatal-errors.txt`, `ruff-new-tests.txt` |

The new `signup_session_boundary_checks.mjs` is imported and run by the existing
workspace browser suite, including its two removed-guard controls. It is not an
optional uncalled regression file. The standalone wrapper reuses the same local
fixture program for focused replay. Tests verify unknown/known email response
shape, consent, generated-secret nondisclosure, token/action/address binding,
quotas, account access sources, closed states and the confirmation journeys.

The first focused session attempt incorrectly expected HTTP 200 from signup;
this endpoint answers 202. Its corrected fixture is the valid counterexample.
Failed syntax and merge attempts remain beside the passing runs. Raw logs keep
their original bytes.

The open and closed funnel screenshots at 1440 and 390 pixels were inspected.
The form or access action fits in the first screen, consent stays beside account
creation, and the five-step explanation follows the form on a phone. Screenshots
are ignored by the repository and remain in the worktree alongside the reports.

## Reuse and source limits

This work reuses `AccountEmailAdapter`, `BrowserIdentityAdapter`, the existing
provider SDK, service access records and HTTP routes. No second identity store,
authentication system or executable runtime was introduced.

The primary [generateLink reference](https://supabase.com/docs/reference/javascript/auth-admin-generatelink)
documents custom email delivery and signup's email/password inputs. The
[password policy documentation](https://supabase.com/docs/guides/auth/password-security)
describes provider constraints and reauthentication settings. These inform the
implementation; they do not replace a live deployment test.

The [session documentation](https://supabase.com/docs/guides/auth/sessions) and
[signout documentation](https://supabase.com/docs/guides/auth/signout) distinguish
provider session termination from access-token expiry. The local identity
stand-in is not evidence that every old provider JWT becomes invalid immediately.
The report claims page/session binding and cancellation behavior, not universal
provider-session revocation.

## Integration and release prerequisites

Apply the implementation patch and the separate
`signup-restored-guide-delta.patch`. The guide delta is based on the restored
customer pages in the root integration tree; its before/after hashes are in
`docs-delta/binding.json`. Rebuild the served documentation and records index.

Retain the root's new documentation routes and rendering call in the one-line
`service.js` route function while adding the `start` and `confirm` titles.
Preserve the root's newer retrieval request version, asset versioning, badge
changes and hosted-documentation checks. The added hosted checks only read the
funnel and an invalid confirmation URL; they submit no signup or provider call.
They were not run against a live host because this candidate is not deployed.

Run the combined tree's full required integration gates and independent review
before release. The scoped suites above do not claim that the combined main
line has passed CI. The root session owns review and integration; the independent
agent slot was occupied by calibration/compiler work during this lane.

Before opening registration, verify the provider's public signup is closed and
that its administration link generation and password-change policy still permit
this flow. Then qualify the real sender, message, confirmation, password, service
activation and account journey under the standing authority. Preserve rollback
and the operator procedure in the account-email guide. Nothing in the local
fixture results authorizes skipping those deployment checks.

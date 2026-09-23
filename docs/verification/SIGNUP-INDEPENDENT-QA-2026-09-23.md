# Email-first signup: independent QA

September 23, 2026. Read-only review of the frozen `signup-flow` candidate at
base `1920296c00ced18e47992ae05237f4a2923666f0`. No source edits, real signup,
provider request, email send, model call, registration activation or deployment.

**GO for integration of the scoped candidate.** No material blocker was found
in the examined signup/backend/confirmation changes. This is not approval to
skip the documented live provider prerequisites or combined-tree CI.

## Independently reproduced evidence

All source hashes match the author's frozen source set. Replays used the
qualified worktree environment, temporary service records and loopback identity
and email stand-ins:

| Check population | Result |
| --- | --- |
| Account-email owning checks | 87 pass |
| Focused real-browser confirmation/session checks | 6 pass |
| Generated temporary-password policy checks | 2 pass |

[Source binding](../../artifacts/signup-independent-qa-2026-09-23/source-bindings.json),
[account email](../../artifacts/signup-independent-qa-2026-09-23/account-email-replay-2.json),
[browser session replay](../../artifacts/signup-independent-qa-2026-09-23/session-boundaries-replay.json),
[password checks](../../artifacts/signup-independent-qa-2026-09-23/password-policy-replay.txt).

The initial backend command incorrectly requested a nonexistent `self_test`
entrypoint and ran no checks. The successor called the owning
`account_email_checks.run_checks`; its report is the valid observation.

## Boundary findings

- **Public response equivalence:** new, existing and address-specific definite
  refusal cases return the same accepted status/body in the local tests.
  Provider service/authentication/rate failures remain generic service refusals.
  This establishes response shape/content equivalence, not constant-time behavior
  across real provider accounts.
- **Email-first contract:** signup v2 contains only record type and email. The
  retired password-carrying request and extra fields refuse before account-email
  attempt counting or identity dispatch. The host generates a fresh temporary
  secret inside the identity request; no caller chooses or receives it.
- **Link binding:** returned token syntax, action and address are checked before
  composing the local confirmation URL. The provider's arbitrary `action_link`
  is not forwarded. Mismatched or missing binding data cannot produce a message
  that confirms a different account.
- **Quota and failure boundaries:** the owning tests cover per-address and
  per-email limits, retry intervals, disabled/network-forbidden states, provider
  errors and unknown outcomes. Identity/mail requests are not automatically
  repeated. This replay is not a distributed concurrency or load-limit proof.
- **Credential handling:** rejected signup bodies remain excluded from body
  capture even though the current valid body contains no password. The generated
  secret nondisclosure tests pass. The temporary password is 72 ASCII bytes,
  satisfying the range admitted by this local configuration; live provider
  policy acceptance remains a separate check.
- **Account access:** `access_source` is read from the authenticated account's
  entitlement source and effective state. The new UI description is not an
  entitlement grant or a way to select another tenant.

## Confirmation/session replay

The browser binds each pending confirmation to its object identity, identity
client and connection generation. Switching accounts or disconnecting clears
that pending state. Each asynchronous verification/password step checks the
binding before proceeding.

The account-A confirmation followed by account-B sign-in replay left B's old
password working and the proposed replacement refused; no extra password write
occurred. Disconnecting during link verification caused no password write and
no activation. Disconnecting while a password request was already accepted
caused no activation, while honestly retaining the one completed provider-side
write. Cancellation is not represented as undoing that write.

The browser uses the real page and local stand-in. The two cancellation controls
invoke the existing disconnect action programmatically because confirmation
has not yet exposed signed-in navigation. No external browser requests occurred.
The missing-waitlist fallback also passed: closed access offers sign-in rather
than a nonexistent invitation form.

## Primary-source and release limits

Supabase documents administration-generated signup/recovery links for custom
email delivery and the signup email/password input. Its OTP verification API
separately verifies the token/action. Those interfaces support the chosen
boundary; documentation is not evidence that this deployed project has the
required settings. [generateLink](https://supabase.com/docs/reference/javascript/auth-admin-generatelink),
[verifyOtp](https://supabase.com/docs/reference/javascript/auth-verifyotp).

The provider's password restrictions and password-change settings still apply.
Signout/refresh-session revocation does not make every already issued access JWT
immediately invalid. The candidate correctly limits its claims to the page's
session binding rather than promising universal token revocation.
[Password security](https://supabase.com/docs/guides/auth/password-security),
[signout semantics](https://supabase.com/docs/guides/auth/signout).

Before opening this flow on the live deployment, retain the documented checks:
close the provider's direct public signup path, qualify administration link
generation and actual password-change policy, and exercise the real sender,
confirmation, password and service-activation journey. The local stand-in does
not prove these settings or mail deliverability. Registration/provider settings
were unchanged in this QA run. The integrating session owns those actions and
the final combined CI/release gates.

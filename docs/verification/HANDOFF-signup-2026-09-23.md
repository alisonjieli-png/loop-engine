# Handoff: email-first sign-up and the Get started funnel, September 23, 2026

Kind: work-in-progress status for the next session. Line: `signup`, worktree
`/home/username/.le-integration/signup`, based on `main` at `243a8811`
(live as Fly release 20). Nothing here was pushed, deployed or changed on a
live service or a provider.

## Why

The owner approved opening registration on September 23, 2026. A live probe
of the identity project, saved as
[identity-unconfirmed-signup-probe-1.json](../../artifacts/architecture-audit-2026-09-19/identity-unconfirmed-signup-probe-1.json),
showed that a second sign-up link for an address that is not confirmed keeps
the first password and makes the first link unusable. Whoever registers an
address first therefore sets its password, and the owner confirming later
activates it. The website's sign-up form also called the provider's own
`signUp`, and no view handled `/auth/confirm`.

## What is done

- `account_email.py`: `service_account_signup_request/v2` carries the email
  address alone. Version 1 and any request with a password field are refused
  with `invalid_account_signup` before anything is counted or asked of a
  provider. The adapter generates a new password for each sign-up with
  `generated_signup_password` (32 random bytes plus one character from each
  character group, 47 characters) inside the one identity request, and keeps
  it nowhere. `availability()` also publishes `minimum_password_length`.
  The confirmation message says the person chooses a password on the page.
- `http.py`: `registration_available` is true only when the browser identity
  opens email sign-up and the account email adapter has sign-up open, because
  the website has no other way to create an account. The session record
  carries `access_source` (`subscription`, `operator_grant`,
  `promotion_code` or `none`), read by `paid_access_source` in `access.py`
  from the recorded entitlement source. `runtime.py` is at its 800-line cap,
  so the reader lives in `access.py`.
- Website (`index.html`, `service.js`, `service.css`, `web_pages.py`):
  - `/signup`: email-only form with the release 21 consent sentence, the
    exact markup release 21 uses.
  - `/auth/confirm`: reads `token_hash` and `type`, removes them from the
    address bar and the history at once, asks for a password typed twice
    (the host's minimum, 12 by default, at most 72 bytes, not the address),
    and on submit calls `verifyOtp`, then `updateUser`, then activates. A
    used or replaced link shows a plain message and a way to ask for a new
    one. The link is used only on submit, so a mail scanner that opens it
    does not use it up. After sign-up it opens `/get-started`; after
    recovery it opens `/account`.
  - `/login`: a "Forgot your password?" form that posts to
    `/api/v1/account/recovery`, shown while the service reports recovery.
  - `/get-started`: the funnel the coordinator asked for, one contiguous
    view (`data-view="start"`): five steps on the left, the card for the
    current step on the right, one primary action per state, 64 pixel band
    padding on a wide screen and 40 on a phone, no dark band. Registration
    open: the email form with the consent sentence. Closed: "Request an
    invitation" to `/waitlist`. Signed in: step 4 reads the session's
    `access_source`; an operator grant says "Your invitation covers Baltor
    Pro", no paid access with checkout open offers "Subscribe for $29 a
    month" through the existing checkout, and checkout closed says payment
    is not open.
  - `web_pages.py` serves `/get-started`, `/setup` and `/terms`. The `/terms`
    lines are identical to release 21's, so that hunk merges cleanly.
- Checks, in `account_email_checks.py`, 87 of 87 pass. New checks, each with
  a removed-guard control that fails it:
  - `a_sign_up_request_carrying_a_password_is_refused_before_anything_is_counted`,
    control `removed_no_password_field_rule_is_detected`;
  - `each_sign_up_gets_a_new_password_that_no_caller_sent`, control
    `removed_random_password_rule_is_detected`;
  - `an_address_registered_first_through_this_service_never_opens_with_a_password_the_registrant_knows`,
    played against `IdentityProjectStandIn`, a stand-in project that follows
    the probe; control `removed_unguessable_password_rule_lets_the_first_registrant_in`;
  - `the_generated_password_is_never_answered_stored_printed_or_logged`, over
    the real route with every log record at every level, standard output and
    error, every stored file with body capture on, and the adapter's printed
    state searched; controls `a_generated_password_written_to_a_log_is_found`
    and `a_generated_password_put_in_the_answer_is_found`;
  - `registration_is_reported_open_only_when_this_service_can_send_the_sign_up_link`,
    control `removed_sign_up_link_rule_for_registration_is_detected`;
  - `a_recovery_link_opens_the_same_page_and_ends_at_a_password_the_owner_chooses`;
  - `with_the_provider_public_sign_up_open_a_password_chosen_first_lasts_until_the_owner_chooses_one`,
    which records the remaining provider-side path and why the provider's
    public sign-up must close.
- `observability_checks.py` now posts the retired password-carrying record to
  prove its refused body is never captured: 45 of 45 pass.
- Documentation: `docs/guides/account-email-operations.md` (flow, probe
  result, switch-on steps with closing the provider's public sign-up), the
  service runtime README section, and `component_interactions.yaml` (request
  contract version 2).

## What is left, in order

1. Run the browser check and make the new block pass. The block (after the
   customer sign-out checks in `tools/check_service_workspace.mjs`) was
   written after a scratch run showed every flow working, but the check file
   itself was not run with it. It adds a seventh fixture service
   (`confirm_base`) whose identity project is the stand-in served by
   `serving_identity_project`, gives `signup_base` and `checkout_signup_base`
   an account email adapter so they still report registration open, grants
   `beta` on the billing service an operator entitlement, and adds nine
   named checks, four funnel first-screen checks and twelve removed-guard
   controls. Expect some iteration on waits and selectors.
2. Run the full CI set on the commit and fix what it finds. Likely places:
   `tools/test_service_documentation.py`, the component guide documented
   checks, conformance, and the hardcoding audit on the new strings.
3. Record before-fix failures: run the new Python checks against the base
   `account_email.py` through a small shim for the new names, and the
   browser block against the base web assets. The controls already show each
   guard's removal is detected; this step shows the checks fail on the old
   code itself.
4. Merge with release 21 (committed in `/home/username/.le-integration/r21`
   as `eedd9fcb` and `90f48653`, not yet on `main` when this was written).
   Conflicts to expect: `index.html` line of the `/signup` form (take this
   line; it holds the same consent sentence), the page title line in
   `service.js` (keep both `terms` and `start`/`confirm`), and
   `tools/check_service_workspace.mjs`. Merge with the `/connect` to
   `/setup` rename and the header "Get started" work: the three new route
   names are separate assignments after the route table, so they merge on
   their own; drop the `/setup` route here if that work adds it.
5. Update `docs/guides/public-website-content-and-domain.md` (it still says
   `/get-started` is not served) and the web assets README, and the getting
   set up guide once registration opens.

## Checks run and results

| Check | Result |
|---|---|
| Full CI set on the base `243a8811` | Every stage exit 0 except self-test: 3224 of 3225, `a_request_in_flight_finishes_on_the_view_it_started_with` failed. That check passed 3 of 3 alone at the same revision, so it is load dependent and not from this work. The browser stage passed 495 of 495 with 76 of 76 controls. |
| `account_email_checks.run_checks` on the work | 87 of 87, about 8 seconds |
| `observability_checks.run_checks` on the work | 45 of 45 |
| `node --check` on `service.js` and the browser check | Both parse |
| markdownlint on the two edited Markdown files | 0 issues |
| Scratch browser run (`/home/username/.le-ci-tmp/signup-work/explore.mjs`, not a CI check) | Funnel in both states at 1440 by 900 and 390 by 844 with the first step in the first screen (open: button ends at 592 of 900 and 539 of 844; closed: action ends at 469 and 416; steps end at 642 of 900); sign-up posted only to `/api/v1/account/signup`; the confirmation page cleared the token; a password set first through the provider's public sign-up answered 400 afterwards and the owner's 200; an invited account saw "Your invitation covers Baltor Pro"; an account without paid access reached a checkout link; no page errors |
| Full CI on the work | Not run |

## Commands to continue

```bash
cd /home/username/.le-integration/signup
PYTHONPATH=src .venv/bin/python -c "import tempfile; from pathlib import Path; \
from loop_engine.core.service_runtime.account_email_checks import run_checks; r=[]; \
d=tempfile.mkdtemp(dir='/home/username/.le-ci-tmp'); run_checks(lambda n,p: r.append((n,p)), Path(d)); \
print(sum(bool(p) for _,p in r), len(r), [n for n,p in r if not p])"
PYTHON=.venv/bin/python node tools/check_service_workspace.mjs /home/username/.le-ci-tmp/browser-signup-1.json
PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  /tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh <full sha>
```

## Live steps to open registration, for the session that deploys

Do these in order. None was done here.

1. The owner closes the identity provider's own public sign-up ("Allow new
   users to sign up" off for project `qfzxmjznlwiopgvfgtsw`). Setting the
   provider's own minimum password length to 12 is also advised.
2. Set two Fly secrets: `BALTOR_IDENTITY_SERVICE_KEY` (the project's
   `sb_secret_` key) and `BALTOR_MAIL_API_KEY` (the mail provider's `re_`
   key).
3. Release this work through the guarded workflow. The live website still
   calls the provider's own `signUp`, so registration must not open before
   this release.
4. Add this block to `/data/host.json` after a backup. `http.request_limits`
   already states `Fly-Client-IP`. `identity_origin` must equal
   `browser_identity.project_url` exactly.

   ```json
   "account_email": {
     "record_type": "service_account_email_configuration/v1",
     "provider_profile": "supabase_generate_link_and_resend_send/v1",
     "identity_origin": "https://qfzxmjznlwiopgvfgtsw.supabase.co",
     "identity_service_key_ref": "env:BALTOR_IDENTITY_SERVICE_KEY",
     "mail_origin": "https://api.resend.com",
     "mail_api_key_ref": "env:BALTOR_MAIL_API_KEY",
     "sender_address": "accounts@mail.baltor.ai",
     "sender_name": "Baltor",
     "signup_enabled": true,
     "recovery_enabled": true,
     "allow_network": true,
     "minimum_password_length": 12,
     "attempts_for_each_address": 10,
     "attempts_for_each_email": 3,
     "attempt_window_seconds": 3600,
     "tracked_addresses": 4096,
     "tracked_emails": 4096,
     "timeout_seconds": 10.0,
     "maximum_response_bytes": 65536
   }
   ```

5. In the same file set `browser_identity.registration_enabled` and
   `browser_identity.email_signup_enabled` to true; the loader refuses open
   sign-up without them. Restart the Machine.
6. Before announcing: send one sign-up to a reserved address and read the
   message. It must hold an `/auth/confirm` link. If it holds the "already
   has an account" notice instead, closing the provider's public sign-up also
   stopped the administration interface from creating users; set
   `signup_enabled` false again and report it.
7. Confirm `GET /api/v1/account/identity` reports `signup_available` and
   `recovery_available` true and `GET /api/v1/capabilities` reports
   `registration_available` true, then finish one journey end to end on the
   live site.
8. The links carry `http.public_base_url`, which is still
   `https://baltor-pilot.fly.dev`. This path does not use the provider's
   redirect list, so moving the base address to `https://app.baltor.ai` is
   now possible for these messages; the invitation tool and `/auth/callback`
   still use the redirect list.

## Addresses the funnel uses, end to end

`GET /get-started`, `GET /api/v1/capabilities`, `GET /api/v1/account/identity`;
step 1 `POST /api/v1/account/signup` (open) or `/waitlist` and
`POST /api/v1/waitlist` (closed), with `/terms` and `/privacy` in the consent
sentence; step 2 the message from `accounts@mail.baltor.ai` linking to
`/auth/confirm?token_hash=...&type=signup`; step 3 `GET /auth/confirm`, then
the identity provider's `POST /auth/v1/verify` and `PUT /auth/v1/user`, then
`POST /api/v1/account/activate` and `GET /api/v1/session`; step 4
`GET /api/v1/billing/plans`, `POST /api/v1/billing/checkout` and the checkout
page at `checkout.stripe.com`; step 5 `/setup`. Returning people use `/login`
(the provider's `POST /auth/v1/token`) and recovery,
`POST /api/v1/account/recovery`, which leads to
`/auth/confirm?token_hash=...&type=recovery` and then `/account`.

## Live or external effects made

None. No provider was called, nothing was pushed, deployed or published, and
no host file, secret or provider setting was changed. The probe record was
copied from `/home/username/.le-ci-tmp/identity-probe/probe-1.json`, which
the main session made.

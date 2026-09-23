# Signup live readiness: read-only audit

Observed September 23, 2026, 17:58–18:02 UTC (1:58–2:02 p.m. Eastern).
No configuration writes, accounts, registrations, logins, emails, charges,
credential changes, OAuth refreshes or TLS exceptions occurred.

**Do not activate public signup yet.** Supabase's public signup is still open,
and the live Baltor host has no account-email configuration or its two required
runtime secrets. Password policy and sender qualification remain partly unknown.
These are deployment prerequisites, separate from the locally reviewed code.

## Observed current state

| Area | Read-only observation | Meaning |
| --- | --- | --- |
| Baltor public capability | `registration_available: false` | Public service registration remains closed |
| Browser identity | `registration_enabled: false`, `email_signup_enabled: false` | Account admission and email signup are disabled in the live browser-identity configuration |
| Public account-email availability | `signup_available: false`, `recovery_available: false`; minimum password length absent | The new email flow is not configured as available |
| Supabase public settings | HTTP 200; `disable_signup: false` | The provider's direct public signup is **open**, so the specified prerequisite is unmet |
| Supabase confirmation settings | `mailer_autoconfirm: false`; email provider enabled | Email is enabled and is not publicly reported as automatically confirmed; this does not establish the whole new journey |
| Live host configuration | `/data/host.json` has no `account_email` block | No sender, administrative link-generation profile, password minimum or email quotas are configured there |
| Live host secret names/environment | `BALTOR_IDENTITY_SERVICE_KEY` and `BALTOR_MAIL_API_KEY` absent | The names required by the documented email configuration are not deployed |
| Existing host address limiter | Header source `Fly-Client-IP` | The current host already has the required client-address source for email attempt limits |
| Host public origin | `https://baltor-pilot.fly.dev` | Link construction from this value would use the Fly hostname; select and qualify the intended customer-facing origin during configuration |

Sources: [public endpoint snapshot](../../artifacts/signup-live-readiness-2026-09-23/public-state-1.json),
[allowlisted host read](../../artifacts/signup-live-readiness-2026-09-23/host-state-1.json),
[Fly secret names](../../artifacts/signup-live-readiness-2026-09-23/fly-secret-names.json).
No secret values or raw host configuration were saved.

## Credentials and the exact unavailable gates

The named helper reports valid-format local references for Fly,
`supabase-publishable`, `supabase-secret` and `resend-send`. Local presence does
not establish provider permission or deployment. The new identity and sender
secrets are not present on the live Machine.

The named `supabase-auth-settings` API-token reference reports
`credential_missing_or_ambiguous`; this audit did not find a usable authentication
settings management credential through that helper. The saved
`supabase-management` OAuth reference is expired. Its reference describes the
project's docs/database/development/storage MCP connection; it does not prove
authorization for authentication-setting changes. The helper can refresh an
OAuth grant, but refreshing persists state and was outside this read-only task,
so it was not invoked. The saved Resend management OAuth grant is also expired.

[Credential-presence inventory](../../artifacts/signup-live-readiness-2026-09-23/credential-presence-1.json).
No user reauthorization or credential replacement request was made. No broader
scope was inferred from a key's existence or a credential's label.

## Sender and password policy: what remains unknown

One authenticated `GET /domains` through the named Resend sending-key reference
returned HTTP 401. No message was sent. This did not establish domain-configuration
read access, and it does not by itself prove whether the key can send mail.
The current verification status of a Baltor sender domain therefore remains
unknown in this audit. More fundamentally, no live host sender address is
configured yet. [Read result](../../artifacts/signup-live-readiness-2026-09-23/sender-domain-readiness-1.json),
[official domain-list API](https://resend.com/docs/api-reference/domains/list-domains).

Supabase's public settings response did not expose minimum password length,
required characters or password-update reauthentication policy. The successful
public settings read therefore cannot qualify the generated temporary password
or the `verifyOtp` → `updateUser` journey against this project's full policy.
The local candidate's 72-byte generated password and its tests are separate
evidence. No administration link was generated to test this, since that would
change provider state. The provider's administration signup-link API expects
an email/password input; actual configured-policy acceptance still needs its
authorized live qualification. [generateLink](https://supabase.com/docs/reference/javascript/auth-admin-generatelink),
[password policy](https://supabase.com/docs/guides/auth/password-security).

## Authority and activation order

The integration checkout's `AGENTS.md` records the owner's September 23 approval
to open registration **after** email-first signup is live and provider public
signup is closed. The shared main checkout's instruction file still contains
the earlier closed-registration wording. These source versions are bound in
the [inventory](../../artifacts/signup-live-readiness-2026-09-23/source-bindings.json).
This task was explicitly narrower—read-only inspection—and performed no
activation regardless of that documentation difference.

The integrating session should retain this order under its actual authority:

1. Finish combined CI and deploy the reviewed email-first implementation while
   service registration remains closed.
2. Obtain a legitimately authorized authentication-settings management path;
   close provider public signup and verify the resulting public setting is
   `disable_signup: true`. No such usable path was established by this audit.
3. Configure the existing host account-email block and deploy its named identity
   and mail secrets, with the intended public origin/sender, explicit quotas and
   network authority. Preserve the established backup/rollback procedure.
4. Qualify administration link creation, actual message delivery, token/action/
   address binding, password selection, service activation and the account
   journey against the real provider policies.
5. Only then open the service's registration/email flags and verify the live
   advertised capability and complete user journey.

This is a readiness report for the existing roadmap, not a new task list or
permission grant. A reviewed patch can be integrated while these external gates
remain open; a local fixture result cannot replace them.

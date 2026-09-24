# Account email operations

Kind: operator instructions for public sign-up and password recovery email.
Provider documentation checked on September 21, 2026. Reading this guide
creates no account, sends no message and changes no provider setting.

The service creates the confirmation or recovery link through the identity
provider's administration interface, which generates a link and sends nothing,
and then sends its own message through the mail provider. The link points at a
page of this service. Nothing in the identity provider's own email templates,
sender settings or redirect list has to change, which matters because
engineering has no permission to change them.

Sign-up is email first since September 23, 2026. The website sends the
address alone; a request that carries a password is refused. The provider's
interface needs a password to create a user, so the service generates a new
random one for each request, from 51 random bytes, sends it in that one
request and keeps it nowhere. The temporary password is 72 ASCII bytes, covering
every minimum this configuration accepts. The person chooses their own password on the page
the link opens, `/auth/confirm`, before that page opens the account:

```text
Sign-up journey
├── /signup or /get-started: the person types an email address
├── POST /api/v1/account/signup {record_type: service_account_signup_request/v2, email}
│   └── the service asks the provider for a link with a generated password, then mails its own message
├── The message links to /auth/confirm?token_hash=...&type=signup
├── /auth/confirm reads the token, removes it from the address bar and the history at once
├── The person chooses a password (at least minimum_password_length, typed twice)
│   └── on submit: verifyOtp(token_hash, type), then updateUser(password), at the identity provider
└── Only then: POST /api/v1/account/activate and the signed-in Get started page
```

Recovery uses the same page: the sign-in page asks
`POST /api/v1/account/recovery` for a link, and the message leads to
`/auth/confirm?token_hash=...&type=recovery` and the same choose-a-password
step. The link is used only when the person submits the form, so a mail
scanner that opens the link does not use it up.

The code is `src/loop_engine/core/service_runtime/account_email.py`. Its
behavior, its refusals and its two allowances are described in the
[service runtime README](../../src/loop_engine/core/service_runtime/README.md#public-sign-up-and-password-recovery-email).
The shape of a route and its result record follows the
[service interface conventions](../standards/SERVICE-INTERFACE-CONVENTIONS.md).

## Current behavior and planned behavior

Current behavior, checked in this repository with injected provider transports
and with loopback listeners for the two real transport functions:

- The two routes, the two allowances, the result records, the refusals, and
  the two Booleans on `GET /api/v1/account/identity`.
- The host configuration block, including its refusal of an unknown key,
  another record version, another provider pair, a host that installs account
  email without the browser identity of the same project, a host that opens an
  operation without a stated client address source, a host that opens sign-up
  while account creation is closed, and an installed adapter that declares a
  boundary other than `account_email/v1`.
- One request to each provider for one accepted call, with no second request
  after an uncertain answer.
- The same status and the same answer bytes for an address that has an account
  and one that does not, driven through the real route, including a refusal
  body that this release does not read.
- A generated link that names another address or another action is refused
  and never put in a message.

- Email-first sign-up: request version 2 carries the address alone, version 1
  and any request with a password are refused before any provider request, and
  the generated password never appears in an answer, a log record, a stored
  file, the printed form of a record or a message. Each has a removed-guard
  control in `account_email_checks.py`.
- The website's `/auth/confirm` view, the recovery form on the sign-in page and
  the Get started funnel at `/get-started`, driven in a real browser against the
  identity project stand-in in `tools/check_service_workspace.mjs`. Its shared
  `signup_session_boundary_checks.mjs` scenarios cover account switching and
  disconnects before and after the password update. The pending confirmation
  is invalidated when the service connection changes; late replies cannot
  activate a different or disconnected page.

Planned behavior, not done here:

- A live send through the mail provider. The sender domain checks and the
  domain mail policy are separate work, recorded in the roadmap.
- Any record that a message was asked for or sent. The service stores none.

## What is not established

These statements are about the identity provider, not about this repository's
code. No check here can settle them, because a check makes no provider call.
Read them before switching sign-up on.

- The same answer for a registered and an unregistered address is proved in
  this repository against chosen provider answers, including refusal bodies
  written in several shapes. It is not proved against a live provider, because
  no refusal body from this endpoint has been observed and saved. The code
  reads no field of a refusal body, so the property does not depend on which
  shape the provider uses; what is unverified is the list of statuses the
  provider really answers with.
- Observed on September 23, 2026, no longer open: for an address that has
  never been confirmed, a second sign-up link from the administration interface
  keeps the first password and makes the first link unusable (`otp_expired`).
  The record is
  [identity-unconfirmed-signup-probe-1.json](../../artifacts/architecture-audit-2026-09-19/identity-unconfirmed-signup-probe-1.json).
  So whoever registers an address first sets its pending password, and the
  owner confirming later would activate it. Email-first sign-up removes the
  first path: the service never takes a password from a caller, and the one it
  generates is random and kept nowhere. The choose-a-password step replaces
  whatever password the account held before the account opens. The provider's
  own public sign-up is the remaining path, because it takes a password from
  anyone who holds the public key. Since the accounts release of September 24,
  2026 the service closes that path itself: it honours only an account that
  carries the provider mark and its own record, and Baltor's sign-up archives
  and replaces any other account under the address. The
  [service component guide](../components/service-runtime/README.md#one-way-in)
  explains it. Closing the provider's public sign-up as well remains advised,
  and is no longer a condition for opening registration.
- Whether closing the provider's public sign-up also stops the administration
  interface from creating a user is not established. If it did, every sign-up
  would be answered like an ineligible address and receive the notice message
  instead of a link. Check it with a reserved address after closing the route
  and before opening registration: the message must hold an `/auth/confirm`
  link.
- A refusal that this release cannot explain, such as a password the provider's
  own password policy rejects, is answered exactly like an address that is not
  eligible: status 202 and the notice message. This is deliberate, because
  telling the two apart would tell a caller who is registered. Set
  `minimum_password_length` at or above the provider's own minimum so that the
  password case does not arise.

## The host configuration block

Add one `account_email` block to the host configuration file on the volume,
beside the existing `http`, `authentication` and `browser_identity` blocks.
Every field below is exact. An unknown field stops the service before it
serves anything.

```json
{
  "account_email": {
    "record_type": "service_account_email_configuration/v1",
    "provider_profile": "supabase_generate_link_and_resend_send/v1",
    "identity_origin": "https://PROJECT.supabase.co",
    "identity_service_key_ref": "env:BALTOR_IDENTITY_SERVICE_KEY",
    "mail_origin": "https://api.resend.com",
    "mail_api_key_ref": "env:BALTOR_MAIL_API_KEY",
    "sender_address": "accounts@mail.baltor.ai",
    "sender_name": "Baltor",
    "signup_enabled": false,
    "recovery_enabled": false,
    "allow_network": false,
    "minimum_password_length": 12,
    "attempts_for_each_address": 10,
    "attempts_for_each_email": 3,
    "attempt_window_seconds": 3600,
    "tracked_addresses": 4096,
    "tracked_emails": 4096,
    "timeout_seconds": 10.0,
    "maximum_response_bytes": 65536
  }
}
```

| Field | Meaning |
|---|---|
| `record_type` | This release reads `service_account_email_configuration/v1` and refuses any other version. |
| `provider_profile` | The pair of provider interfaces whose field names this release speaks. Another value is refused. |
| `identity_origin` | The origin of the identity provider project. It must equal the `project_url` of the `browser_identity` block. |
| `identity_service_key_ref` | Environment reference to the identity provider's server secret key. Its value must start with `sb_secret_`. |
| `mail_origin` | The origin of the mail provider. This release carries no default, so the file shows every address the service can reach. |
| `mail_api_key_ref` | Environment reference to the mail provider key. Its value must start with `re_`. |
| `sender_address` | The address the message comes from. It must be on a sender domain the mail provider has verified. Use `accounts@mail.baltor.ai`, for the reason in the next paragraph. |
| `sender_name` | Short plain text shown before the address. Leave it empty to send the address alone. |
| `signup_enabled` | Switches `POST /api/v1/account/signup` on. Default false. |
| `recovery_enabled` | Switches `POST /api/v1/account/recovery` on. Default false. |
| `allow_network` | Network authority for both operations. Both stay closed while it is false. |
| `minimum_password_length` | From 8 to 72. The shortest password the `/auth/confirm` page accepts; `GET /api/v1/account/identity` publishes it. The page also refuses more than 72 bytes and the address itself. The identity provider applies its own minimum as well. |
| `attempts_for_each_address` | Attempts allowed from one client address inside the window. |
| `attempts_for_each_email` | Attempts allowed for one email address inside the window. |
| `attempt_window_seconds` | The window both allowances use, from 1 second to one day. |
| `tracked_addresses`, `tracked_emails` | How many keys each table holds before the oldest leaves. |
| `timeout_seconds` | The deadline for one provider request, at most 30. |
| `maximum_response_bytes` | The ceiling for one provider answer, at most 262,144. |

The sender address is `accounts@mail.baltor.ai`, not the `auth.baltor.ai`
address that the original task described. The saved probe
[account-email-path-probe-1.json](../../artifacts/architecture-audit-2026-09-19/account-email-path-probe-1.json),
observed on September 21, 2026, records `auth.baltor.ai` at the mail provider
as `partially_failed`, with a send attempt refused by status 403 because the
domain is not verified, and reads that as a stuck verification state at the
provider. The same record shows `mail.baltor.ai` verified on all four records
with a delivered test send from `accounts@mail.baltor.ai`. A deployment that
sends from the first address gets `account_mail_refused` on every message.

The allowance for the client address follows the address source that the host
states in `http.request_limits`. The service refuses to start when
`signup_enabled` or `recovery_enabled` is true and no source is stated, with
the code `account_email_needs_a_stated_client_address_source`. The sign-in
limit may run with no stated source, because what an inactive table costs
there is bounded guessing. Here an inactive table would leave only the
allowance for each email address, and one caller could then send a message to
as many different addresses as it chose, at the cost and the sender reputation
of this deployment. On the current platform the socket peer is the platform's
own proxy, so state the header source and the exact header that the proxy
overwrites on every request:

```json
{
  "http": {
    "request_limits": {
      "record_type": "service_request_limits/v1",
      "client_address_source": "header",
      "client_address_header": "Fly-Client-IP"
    }
  }
}
```

The allowance for the email address is always active.

## The environment references the deployment must set

Both values are secrets. They are set on the platform, never written into the
repository, a report or a log. The names below are the ones in the block above.

| Environment name | Value | Where it comes from |
|---|---|---|
| `BALTOR_IDENTITY_SERVICE_KEY` | The identity provider project's server secret key, starting with `sb_secret_` | The identity provider's project API keys page |
| `BALTOR_MAIL_API_KEY` | The mail provider's key, starting with `re_` | The mail provider's API keys page |

The service refuses a key whose text does not start with the prefix that slot
needs, so a publishable browser key pasted into the server slot stops the
request before it leaves the machine. The refusal names no key value.

## Switching sign-up on and off

Both operations are closed until three Booleans are true together:
`allow_network`, and `signup_enabled` or `recovery_enabled`. Read the current
state without signing in:

```bash
curl -s https://app.baltor.ai/api/v1/account/identity | python3 -m json.tool
```

The `result` object reports `signup_available` and `recovery_available`.

To switch one operation on:

1. Confirm at the mail provider that the sender domain `mail.baltor.ai` is
   still verified on all four records and that the domain mail policy allows
   `accounts@mail.baltor.ai`. Do not use `auth.baltor.ai`; the saved probe
   records it as unverified with a refused send. Until the domain is verified
   a message is accepted by the service and refused or filtered later.
2. State the client address source in `http.request_limits`, as shown above.
   Without it the service refuses to start with either Boolean true.
3. For sign-up only: run `loop-engine service mark-accounts` on the host,
   read the plan, then run it again with `--apply` and the printed
   `--expected-plan` digest, so that accounts from before the one way in keep
   working. Then send one sign-up to a reserved address through the service
   and confirm that the message holds an `/auth/confirm` link. Closing the
   identity provider's own public sign-up ("Allow new users to sign up" off in
   the project's authentication settings, which only the owner can reach) is
   advised and not required; if it is closed, repeat the reserved sign-up, as
   "What is not established" explains.
4. For sign-up only: set `browser_identity.registration_enabled` and
   `browser_identity.email_signup_enabled` to true. The service refuses to
   start when sign-up is open and account creation is closed.
5. Set both environment references on the platform.
6. Set `allow_network` to true and set the one Boolean you want.
7. Restart the service so that it reads the host file again.
8. Read `/api/v1/account/identity` and confirm the Boolean.

To switch one operation off, set its Boolean to false and restart. A request
then answers status 503 with the stable code `account_signup_unavailable` or
`account_recovery_unavailable`, and no provider is contacted. Removing the
whole block answers status 404 with `account_email_unavailable`.

A release from before this block refuses a host file that contains it. Remove
the `account_email` block from the host file before starting such a release,
for example during a rollback.

## What a caller sees

```text
POST /api/v1/account/signup
  {"record_type": "service_account_signup_request/v2", "email": ...}
  -> 202 {"record_type": "service_http_result/v1", "operation": "account_signup",
          "result": {"record_type": "service_account_signup_result/v1",
                     "status": "confirmation_sent"}}

POST /api/v1/account/recovery
  {"record_type": "service_account_recovery_request/v1", "email": ...}
  -> 202 result {"record_type": "service_account_recovery_result/v1",
                 "status": "recovery_sent"}
```

The 202 answer is the same for an address that already has an account and for
one that does not, so the interface never says who is registered. That holds
for every definite refusal the identity provider can give, not only the two
this release expects, because the service reads no field of a refusal body.
Only a refusal of this service itself, status 401, 403 or 429 at the identity
provider, changes what the caller sees, and those answer the same way for
every address.

A malformed request answers 400. A request over either allowance answers 429
with `Retry-After`. A provider that fails, redirects, answers too much or
answers too late gives status 503 with a stable code, and nothing is sent
again. A request that waits longer than the service deadline gives status 504,
and that one answer does not say whether a message was sent.

## Reading a failure

Every refusal is `service_http_error/v1` with `error.code`. No code carries an
address, a password, a link, a token hash, a provider message or a key.

| Code | Status | What it means | What the operator does |
|---|---|---|---|
| `account_email_unavailable` | 404 | The host file has no `account_email` block. | Add the block and restart. |
| `account_signup_unavailable`, `account_recovery_unavailable` | 503 | The operation is switched off, or `allow_network` is false. | Set the Booleans and restart. |
| `invalid_account_signup`, `invalid_account_recovery` | 400 | The request body is not the exact record this release reads, including a sign-up that carries a password or uses version 1. | The caller sends the documented record. |
| `invalid_email_address` | 400 | The address is refused by the rules above. | Nothing. The caller corrects the input. |
| `failed_attempt_limit_reached` | 429 | The client address or the email address is over its allowance. | Nothing, or raise the allowance in the host file. |
| `account_email_secret_unavailable` | 503 | An environment reference is not set. | Set it on the platform and restart. |
| `account_email_secret_unusable` | 503 | The value does not start with the prefix that slot needs. | Put the right kind of key in that slot. |
| `identity_link_unavailable` | 503 | The identity provider could not be reached, redirected, answered too much, or answered too late. The outcome is unknown. | Read the provider's status. Nothing was sent twice. |
| `identity_link_refused` | 503 | The identity provider refused this service: the server key was not accepted, this service may not use the interface, or it is over the provider's own rate. The refusal is about this service, never about the address. | Read the provider's logs and the key in `identity_service_key_ref`. |
| `identity_link_unusable` | 503 | The provider answered without a token hash this service can put in a link, or the answer named another address or another action. | Confirm the project is the one named in `identity_origin`. |
| `account_mail_refused` | 503 | The mail provider refused the send, for example an unverified sender address. | Verify the sender domain and the sender address. |
| `account_mail_unavailable` | 503 | The mail provider could not be reached or did not answer in time. The outcome is unknown. | Read the provider's status. Nothing was sent twice. |
| `unsupported_media_type` | 415 | The request did not declare `application/json`. | The caller sends the documented content type. |
| `request_limit_exceeded` | 413 | The request body was larger than `maximum_request_bytes`. | Nothing. The caller sends the documented record. |
| `request_body_deadline` | 408 | The caller did not finish sending its body inside `request_timeout_seconds`. | Nothing. The caller sends the whole body. |
| `service_busy` | 503 | Every concurrent operation slot was held. | Raise `maximum_concurrent_operations` or add a machine. |
| `deadline_exceeded` | 504 | The work did not finish inside `request_timeout_seconds`. The answer does not say what happened. | See the paragraph below. Do not assume nothing was sent. |

The 504 answer needs care. The transport stops waiting, but it does not cancel
the work, so the identity request and the message send can still finish after
the caller has been answered. A 504 therefore means the outcome is unknown in
both directions: a message may have been sent and may not. The service never
repeats the operation by itself. Treat a 504 as a possible send, and read the
mail provider's own log for that window before telling anyone that nothing
arrived.

## Checks to run before and after a change

```bash
PYTHONPATH=src .venv/bin/python -m loop_engine service smoke
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
```

The smoke command runs the account email checks with injected provider
transports and with loopback listeners for the two real transport functions.
It contacts no identity provider and no mail provider, and it sends no
message. A passing run is not evidence that a live send works.

# Private beta operations

Kind: operator procedure for the Baltor private beta. It explains how to
switch on browser sign-in for accounts that the operator prepares, how to
invite a person without outgoing email, how to issue a link again and how to
disable an account. Reading this guide changes nothing. Every command here
that changes something asks for an explicit confirmation.

Written on September 20, 2026 for revision `381efec` plus the invitation
command. Check the current source and the current provider state before you
rely on a dated statement. The private beta itself is defined by package D-17
in [roadmap.yaml](../roadmap/roadmap.yaml) and in the
[takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md).

```text
Private beta account procedure
├── 1. Enable browser sign-in for prepared accounts (once, by deployment)
│   ├── browser_identity block: a first sign-in activates a tenant that the service owns
│   ├── client_access block: a signed-in person creates and revokes personal keys
│   └── Registration stays closed on the website and at the identity provider
├── 2. Invite a person (each time, with one command)
│   ├── Create the confirmed user, or find the user that this command created earlier
│   ├── Generate one recovery link, with no email
│   └── Show the link once and keep a report that does not hold the link
├── 3. The invited person sets a password and signs in
├── 4. Reissue a link when it expired or was used by accident
└── 5. Disable an account
    ├── Identity provider: no new browser sessions
    └── Service: subject revocation, which also stops personal keys
```

Two systems hold account state. Keep them apart when you read a result or
disable an account.

```text
Where account state lives
├── Identity provider (the Supabase project)
│   ├── Address, password and confirmation time
│   ├── Recovery link: single use and short lived
│   └── Browser sign-in tokens
└── Baltor service (the durable store on the host)
    ├── Subject binding: one issuer and subject to one tenant
    ├── The tenant that the service owns, with its grants and usage records
    └── Personal client keys, each bound to the subject that created it
```

## Current behavior

These statements describe the source at the revision named above.

- The host configuration accepts the two blocks in
  [Enable browser sign-in](#enable-browser-sign-in-for-prepared-accounts).
  A check loads the blocks from this guide through the real host loader, so
  the guide cannot drift from the typed configuration.
- [`tools/invite_beta_user.py`](../../tools/invite_beta_user.py) prepares an
  invited account and shows one recovery link. It sends at most two requests
  and repeats nothing.
- Browser sign-in and personal client keys are switched on for the hosted
  pilot. A separate operator change added the two blocks to the host
  configuration on September 21, 2026 without building a new image. The
  applied record is
  [`pilot-configuration-signin-1.json`](../../artifacts/architecture-audit-2026-09-19/pilot-configuration-signin-1.json).
  That record, not this guide, states what runs. It also records that no
  person has signed in through this path yet. The
  [takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md) names
  the running release and its image digest.
- The website cannot complete the invited person's journey yet. Its callback
  view removes the returned session from the address bar and shows the
  sign-in form. It has no form for a new password. A link that is opened
  today is used up and no password is set. Do not send a link to an invited
  person until the view in [Planned behavior](#planned-behavior) exists.
- The service can revoke a subject, and that stops the subject's personal
  keys. There is no operator command for it and there is no way to restore a
  revoked subject. See [Disable an account](#disable-an-account).
- A first sign-in activates a tenant for any confirmed user of the identity
  project. The service does not check that the user was invited. See
  [Keep registration closed](#keep-registration-closed).

Evidence level of the invitation command: local contract only.

| Fact | State |
|---|---|
| Checks | The checks in [`tools/test_invite_beta_user.py`](../../tools/test_invite_beta_user.py) pass. They use an injected transport and the HTTP library's in-memory transport. No socket is opened. |
| Removed guards | The 42 removals listed in `RemovedGuardControls` in the checks file were made in memory, one at a time. Each removal makes its named check fail. Three of them remove a guard for the link request only. A guard that is not in that list is not proven in this way. |
| Real provider | Not contacted by this command. The request and answer shapes come from the provider's published source code and documentation for user creation, link generation and error answers, read on September 20, 2026. |
| Answer shape, observed separately | A separate probe called `POST /auth/v1/admin/generate_link` on September 21, 2026 and recorded the answer in [`account-email-path-probe-1.json`](../../artifacts/architecture-audit-2026-09-19/account-email-path-probe-1.json): status 200, one flat object, with `action_link`, `hashed_token`, `email_otp`, `verification_type`, `id`, `email` and `redirect_to` at the top level and no `properties` object. This command reads exactly those fields at the top level, so that part of its reading is observed rather than inferred. |
| Answer fields still unobserved | The probe did not record the user fields that this command also checks: `email_confirmed_at`, `app_metadata`, `aud`, `role`, `banned_until`, `deleted_at` and `is_anonymous`. If the provider leaves one of them out, the command withholds the link and reports `user_is_not_confirmed`, `existing_user_was_not_created_by_the_invitation_command` or `user_cannot_sign_in_at_the_provider`. It never issues a link it could not check. |
| First real use | It is also the first provider qualification of this command. Use an address that you control, and compare the result with the provider's user list. |

## Planned behavior

None of the following exists at the revision named above. Each item needs
work outside this guide.

- A set-password view on the website. It reads the session that the provider
  returns to the callback address, asks for a new password, sends it to the
  provider, removes the session from the address bar and never logs it.
- An operator command that disables and restores an account on the hosted
  service, with a report. The runtime has subject revocation but no restore.
- Admission of invited subjects only, enforced by the service itself. Two
  designs are open, and neither is chosen or built:
  - Keep `registration_enabled` as `false` and let the operator prepare the
    tenant for each invited subject. The runtime method for this exists and
    the hosted identity qualification uses it for disposable test identities.
    An operator command for it does not exist. The issuer and the user
    identity in the invitation report are its inputs.
  - Keep `registration_enabled` as `true` and refuse activation for a user
    without the invitation mark. The invitation command marks each user that
    it creates with `baltor_invitation` in the provider's administrator-owned
    metadata, and it withholds the link for a user that it only finds without
    that mark. Every account that this command invites therefore carries the
    mark. The service does not read the mark today.
- Addresses on a `baltor.ai` hostname as redirect addresses. The owner must
  first add the exact callback address to the provider's redirect allow list.
- Email confirmation and recovery by email, after the sender domain is fully
  verified (package D-02).
- A browser session that survives a reload (package D-10).

## Enable browser sign-in for prepared accounts

A separate operator change already applied these blocks to the hosted pilot on
September 21, 2026, on the same image digest. Read
[`pilot-configuration-signin-1.json`](../../artifacts/architecture-audit-2026-09-19/pilot-configuration-signin-1.json)
for the exact applied record, which also sets the allowed scopes and the key
limits for each account. Follow the steps below for another release, after a
rollback, or for a second service.

Do this once for a release, through the release procedure in the
[takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle).
Use release 8 or a later release that was built from a committed revision.
Do not add these blocks to release 7. Release 7 does not know the rule that
binds a personal key to the subject that created it.

The block below uses the same `namespace_prefix` as the applied record,
`customer`. The prefix is the first part of every tenant identity that a
first sign-in creates. Do not change it on a service where accounts already
exist. A different prefix makes a different tenant for the same person, and
the earlier tenant keeps the material and the usage records.

The applied record also writes out the allowed scopes and the key limits.
Those are the values that the block below gets from the defaults, so the two
grant the same access. Read the applied record when you need the exact
values.

### Before you start

| Need | Who | State |
|---|---|---|
| New sign-ups switched off in the identity provider's settings | Owner, in the provider's dashboard | Still open. A probe on September 21, 2026 read the provider's public settings and recorded `signup_disabled` as `false` and automatic confirmation as `false`. See [Keep registration closed](#keep-registration-closed). |
| The callback address on the provider's redirect allow list | Owner, in the provider's dashboard | The owner confirmed `https://baltor-pilot.fly.dev/auth/callback`. No `baltor.ai` address is confirmed. |
| The publishable key as a deployment secret named `SUPABASE_PUBLISHABLE_KEY` | Operator, through the platform's secret settings | Staged for the hosted pilot on September 21, 2026. Its value never appeared in a command line or a report. |
| A copy of the current host configuration for rollback | Operator | Make it before the change. |

The publishable key identifies the application to the identity provider. It
is not the administration credential. The service refuses a value that does
not start with `sb_publishable_`, so a server secret cannot reach a browser
by mistake.

### The two blocks

Add these two members to the host configuration record
(`service_http_host_configuration/v1`, the file `/data/host.json` on the
volume). Keep every other member as it is.

```json
{
  "browser_identity": {
    "record_type": "browser_identity_configuration/v1",
    "provider_profile": "supabase_user/v1",
    "project_url": "https://qfzxmjznlwiopgvfgtsw.supabase.co",
    "publishable_key_ref": "env:SUPABASE_PUBLISHABLE_KEY",
    "namespace_prefix": "customer",
    "registration_enabled": true,
    "email_signup_enabled": false,
    "allow_network": true,
    "starter_identities": []
  },
  "client_access": {
    "record_type": "service_client_access/v1",
    "writes_authorized": true
  }
}
```

| Field | Meaning |
|---|---|
| `registration_enabled` is `true` | A first sign-in activates a tenant. The service derives the tenant from the issuer and the subject. The browser cannot choose a tenant, a namespace or a scope. A later sign-in finds the same tenant. |
| `email_signup_enabled` is `false` | The website shows no account form, and the capabilities record says that registration is not available. |
| `publishable_key_ref` | An environment reference. The key value is never written into the file. |
| `allow_network` is `true` | The service reads the current user from the provider for every browser request. Without this authority every sign-in is refused with `identity_network_authority_required`. |
| `namespace_prefix` | The first part of each activated tenant identity and namespace. At most 32 characters. |
| `starter_identities` | Catalogue items that a new tenant may read. Leave it empty until the owner has approved starter items. An identity that is not in the manifest stops the service at start with `invalid_starter_identities`. |
| `writes_authorized` is `true` | A signed-in person can create and revoke personal client keys. With `false` the account page lists keys and refuses each change with `access_writes_not_authorized`. |

The other `client_access` fields keep their defaults: at most ten active
personal keys for an account at a time, a lifetime of one day by default and
seven days at most. The `client_access` block needs the `browser_identity`
block. The service refuses to start when `client_access` is present and
`browser_identity` is absent.

### Keep registration closed

`registration_enabled` does not open public registration by itself, but it
admits every confirmed user of the identity project. Registration is closed
only while all three parts below hold.

```text
Registration is closed only when
├── Website: email_signup_enabled is false, so no account form is shown
├── Identity provider: new sign-ups are switched off in its settings
└── Operator: users are created only with the invitation command
```

The second part does not hold today. A probe on September 21, 2026 read the
provider's public settings and recorded them in
[`account-email-path-probe-1.json`](../../artifacts/architecture-audit-2026-09-19/account-email-path-probe-1.json):
`signup_disabled` is `false` and automatic confirmation is `false`. New
sign-ups are open at the provider, and the provider requires email
confirmation before it counts an address as confirmed.

The publishable key is public by design, so a visitor can ask the provider
directly for an account. Only the confirmation step stands between that
request and a confirmed address, and a confirmed address activates a tenant
on its first sign-in. What limits this today is the provider's built-in
sender, which its documentation says delivers only to addresses of the
project's team and only two messages each hour. A connected sender for
authentication email removes that limit, so this gap must be closed before
that work lands.

Treat registration as open to anyone who can get a confirmed address at the
provider. Ask the owner to switch new sign-ups off. User creation through the
administration interface keeps working when sign-ups are off, so the
invitation command is unaffected.

### Apply, check and roll back

1. Set the deployment secret and change the host configuration with the
   release procedure. Restart the service so that it reads the file.
2. Read the public capabilities. Both requests are read-only.

   ```bash
   curl --silent --max-time 10 https://baltor-pilot.fly.dev/api/v1/capabilities
   curl --silent --max-time 10 https://baltor-pilot.fly.dev/api/v1/account/identity
   ```

   Expect `browser_identity_available` and `client_access_available` to be
   `true` and `registration_available` to be `false`. The identity record
   must show `registration_enabled` as `true`, `email_signup_enabled` as
   `false` and a key that starts with `sb_publishable_`.
3. To roll back, remove both blocks and restart. The service returns to
   operator-issued keys only.

The hosted mode of
[`tools/check_identity_customer_access.py`](../../tools/check_identity_customer_access.py)
requires `registration_enabled` to be `false`. It refuses to run against this
beta configuration until that tool is changed.

## Invite a person

The command does two things at the identity provider and nothing at the
Baltor service.

1. It creates a user for the address with a confirmed address and no
   password, and marks the user with `baltor_invitation` in metadata that
   only the administration interface can write. If the address already has a
   user, the provider refuses with its typed code for an existing address,
   and the command continues with that user.
2. It asks for a recovery link for that address. This interface returns the
   link and sends no email.

Before it shows the link, the command checks that the answer describes the
invited user, that the user is confirmed and can sign in, that the link
points at the identity project, that it is a recovery link, and that the
provider kept the requested redirect address.

A user that the command only found must carry the `baltor_invitation` mark
of an earlier run. Without the mark the link is withheld with
`existing_user_was_not_created_by_the_invitation_command`. Someone else
registered that account and chose its password. That person may also hold
browser sessions and personal client keys for it, and a new password ends
neither of them. The command has no option to accept such an account.

### Run it

Create a private folder for reports once. Reports hold a user identity, so
they stay out of Git. The folder below is ignored by Git.

```bash
mkdir -m 700 -p .loop-engine-dev/private-beta
```

Run the command from the repository root through the credential wrapper. The
wrapper takes the administration credential from the workstation keyring and
gives it to this one process in the environment variable that
[`operator_credentials.json`](../../tools/operator_credentials.json) names
for `supabase-secret`. The command refuses a project reference that differs
from the project recorded for that credential.

```bash
/usr/bin/python3 tools/operator_credentials.py run --ref supabase-secret --timeout 120 -- \
  .venv/bin/python tools/invite_beta_user.py \
  --project-ref qfzxmjznlwiopgvfgtsw \
  --email person@example.com \
  --service-origin https://baltor-pilot.fly.dev \
  --redirect-to https://baltor-pilot.fly.dev/auth/callback \
  --report .loop-engine-dev/private-beta/invitation-2026-09-21-01.json \
  --acknowledge-identity-account-effects
```

| Argument | Rule |
|---|---|
| `--project-ref` | Twenty lower case letters. The provider host is built from it and from nothing else. |
| `--email` | One plain address. It is used in lower case, as the provider stores it. |
| `--service-origin` | The exact HTTPS origin of the website: no path, no port, no user information. A name with one label and a numeric address are refused. |
| `--redirect-to` | An address inside that origin, with a path and without a query or a fragment. It must be on the provider's redirect allow list. |
| `--report` | A new file in an existing folder. An existing path is never overwritten. |
| `--credential-ref` | Optional. The reference name in the manifest. The default is `supabase-secret`. |
| `--acknowledge-identity-account-effects` | Required. Without it nothing is requested and nothing is written. |

The link appears once, alone, on standard output. Everything else goes to
standard error as one line of JSON. To keep the link out of the terminal's
history, send standard output to the clipboard. The exit status of a
pipeline is the status of its last command, so switch on `pipefail` first.
Without it you see the status of `wl-copy`, which is 0 also after a refusal.
After a refusal or an unknown outcome the clipboard holds no link, because
nothing was written to standard output. In every case the `outcome` field on
standard error is authoritative.

```bash
set -o pipefail
/usr/bin/python3 tools/operator_credentials.py run --ref supabase-secret --timeout 120 -- \
  .venv/bin/python tools/invite_beta_user.py \
  --project-ref qfzxmjznlwiopgvfgtsw \
  --email person@example.com \
  --service-origin https://baltor-pilot.fly.dev \
  --redirect-to https://baltor-pilot.fly.dev/auth/callback \
  --report .loop-engine-dev/private-beta/invitation-2026-09-21-02.json \
  --acknowledge-identity-account-effects | wl-copy
```

Anyone who holds the link can set the password of that account until the
link is used or expires. Do not run the command in a chat tool, in a recorded
session or in continuous integration. A clipboard manager that keeps a
history also keeps the link, so clear it after delivery. Deliver the link
through a channel that does not open links by itself. A message preview that
fetches the link uses it up. The address of the invited person is a command
argument, so it appears in the shell history and in the process list of this
workstation. The credential and the link never do.

### Read the result

The exit status and the `outcome` field of the summary line on standard
error say what you may conclude.

| Exit status | `outcome` | Meaning |
|---|---|---|
| 0 | `link_issued` | The report is on disk and the link was shown. |
| 1 | `refused` | The provider or a guard refused, or the link was withheld. The `failure` field says why. No link was shown. |
| 1 | `link_issued` with `link_displayed` as `false` | The link was generated and recorded, but standard output could not take it. Nobody has the link. Reissue one. |
| 2 | none | Refused before any request. Nothing was created and no report exists. Standard error holds one code from the table of early refusals. |
| 3 | `outcome_unknown` | A request may have taken effect and its answer was lost or unusable. Nothing was repeated. |

The report (`beta_invitation_report/v1`) holds these fields: the time, the
project address and the issuer, the redirect address, a digest of the address
(`email_sha256`), the provider's user identity (`user_id`), whether this run
created the user (`user_created`), whether the link answer carried the
invitation mark (`invitation_mark_present`, which is `null` when no link
answer was read), whether the provider generated a link
(`link_generated`), a digest of the displayed link (`link_sha256`), the
outcome, the failure and its detail, the last provider status, the number of
requests, and `email_requested`, which is always `false`. It never holds the
link, its one-time code, the credential or the address in plain text. The
address digest is a plain SHA-256 digest without a key. It is a pseudonym:
a person who holds the report and can guess the address can confirm the
guess. Keep reports as private as the address itself. As a second guard,
the command refuses to write a report or a summary that contains the link,
its token, its one-time code or the credential. The file is readable by its
owner only. The issuer and the user identity are what you need to
[disable the account](#disable-an-account) later.

The report is written before the link is shown. A report with `link_issued`
therefore does not prove that anybody saw the link. Only the summary line on
standard error does, in its `link_displayed` field. Note that field beside
the report when you keep the report as evidence.

`user_created` as `false` is expected only when an earlier report in your
folder shows that this command created the same `user_id`. On a first
invitation it means that someone else created the account. The command then
withholds the link unless the account carries the invitation mark. If you
see `user_created` as `false` on a first invitation together with a link,
do not deliver the link. Stop and report it.

A report file that exists and is empty means that the run was interrupted or
met a defect after the report file was created. Standard error then holds
`unexpected_error` and the error type, without a message. Treat it like
`outcome_unknown`.

Failures after the first request:

| `failure` | What happened | What to do |
|---|---|---|
| `user_creation_outcome_unknown_do_not_repeat` | The answer to the creation request was lost, too large, malformed or unexpected. The user may exist. | Follow the steps for an unknown outcome below. |
| `link_outcome_unknown_do_not_repeat` | The same, for the link request. A link may exist that nobody has seen. | Follow the steps for an unknown outcome below. A new link replaces the unseen one. |
| `provider_redirect_refused` | The provider answered with a redirect. It was not followed, and the credential was not sent anywhere else. | Treat as unknown. Check the project reference and the provider's status. |
| `credential_refused_by_provider` | The provider refused the administration credential. | Check the keyring reference with the inventory command of the credential tool. Do not try another credential. |
| `user_creation_refused_by_provider` | The provider refused to create the user for a reason other than an existing address. | Check the address. Read the provider's log for the refusal. |
| `user_not_found_at_the_provider` | The provider reported an existing address and then found no user for the link. | The address may belong to another sign-in method or the user was removed. Inspect the provider's user list. |
| `link_refused_by_provider` | The provider refused to generate the link. | Read the provider's log. Wait before another attempt if it reports a rate limit. |
| `existing_user_was_not_created_by_the_invitation_command` | The address already has a user, and that user does not carry the `baltor_invitation` mark. Someone else registered it and chose its password. The link was withheld. | Ask the owner to remove that user in the provider's dashboard. If the person has signed in before, also [disable the account](#disable-an-account) at the service with the `user_id` from the report. Then run the command again, so that the command creates the user. |
| `user_is_not_confirmed` | The user has no confirmed address. The link was withheld. | Ask the owner to remove that user in the provider's dashboard. Never confirm it: a confirmed account keeps the password that it already has. Then run the command again, so that the command creates the user. |
| `user_cannot_sign_in_at_the_provider` | The user is banned, removed, anonymous or has another role. The link was withheld. | A disabled account stays disabled. Lift the ban at the provider first if the account should return. |
| `user_identity_mismatch` | The link answer describes another user or another address than the request. The link was withheld. | Stop and report it. Do not deliver any link for this address. |
| `redirect_replaced_by_the_provider` | The provider replaced the redirect address, which happens when the address is not on its allow list. The link was withheld. | Use an address that is on the allow list, or ask the owner to add the exact address. |
| `link_shape_refused` | The link does not point at the identity project's verification path with exactly one token, one kind and one redirect address. | Stop and report it. The provider's answer shape may have changed. |
| `link_kind_mismatch` | The provider returned another kind of link than a recovery link. | Stop and report it. |
| `secret_in_output_refused` | The report or the summary would have contained the link, the code or the credential. The link was withheld. | Stop and report it. This is a defect in the command. |
| `report_not_written_link_withheld` | The report could not be written, for example because the disk is full. The link was withheld. | Free space and run the command again with a new report path. |
| `unexpected_error` | A defect after a request. The detail names the error type only. | Treat as unknown and report it. |

The `detail` field narrows an unknown outcome: `timeout`,
`connection_failed`, `response_too_large`, `response_encoding_refused` (the
command asks for an answer without compression and refuses a compressed one
before reading it, so that the byte limit is also a memory limit),
`transport_error`,
`transport_contract_violation`, `malformed_response`, `unexpected_status` or
`response_does_not_describe_the_invited_user`.

Early refusals, with exit status 2:

| Code | Cause |
|---|---|
| `project_reference_shape_refused` | The project reference is not twenty lower case letters. |
| `invited_address_refused` | The address is not one plain address. |
| `https_origin_required` | The service origin does not use HTTPS. |
| `service_host_shape_refused` | The service host is a single label, a numeric address or not a plain lower case name. |
| `exact_https_origin_required` | The service origin has a path, a port, user information, a query or a fragment. |
| `redirect_must_stay_inside_the_named_origin` | The redirect address has another origin than the service origin. |
| `redirect_address_refused` | The redirect address has no path, or has a query, a fragment, a dot segment or an encoded character. |
| `explicit_confirmation_required_nothing_was_created` | The confirmation flag is missing. |
| `credential_manifest_unavailable` | The reference manifest could not be read, or it has a record version that this command does not support. |
| `credential_reference_is_not_an_identity_administration_key` | The reference does not name a secret key of the identity provider with a declared value shape. |
| `credential_is_recorded_for_another_project` | The project reference differs from the project recorded for the credential. |
| `administration_credential_missing_or_malformed` | The environment variable is absent, masked or has another key type. Run the command through the credential wrapper. |
| `report_folder_must_exist` | The report folder does not exist. |
| `report_path_must_not_exist` | The report path exists already, also as a link that points nowhere. |
| `report_path_refused` | The report file could not be created. |
| `invalid_administration_limits` | A request limit is outside its allowed range. |

### When the outcome is unknown

1. Do not run the command again at once. Keep the report.
2. Look for the address in the provider's user list and note what you see.
3. Run the command again with a new report path. If the first run created
   the user, the command finds it by its invitation mark. If not, the
   command creates it. A new link replaces an earlier link for the same
   user.
4. Keep both reports side by side. Never delete the first one.

The credential wrapper also stops the command after its own timeout. The
commands above give it 120 seconds, which is longer than two requests can
take. If the wrapper stops the command, the wrapper reports an unknown
outcome as well, and the report file may be empty.

### The first real use

No real provider call was made while this command was written. Qualify it
with an address that you control before you invite anyone.

1. Run the command for your own address.
2. Confirm exit status 0, one line on standard output, and a report whose
   `link_sha256` equals the SHA-256 digest of that line without the line
   break.
3. Confirm in the provider's user list that the user exists, is confirmed
   and carries the `baltor_invitation` mark, and that no email was sent.
4. Run the command again for the same address. Expect `user_created` to be
   `false`, `invitation_mark_present` to be `true` and a different link. If
   the second run is refused for a missing mark, the provider did not keep
   or did not return the mark. Stop and report it.
5. A refusal on the first run with `user_is_not_confirmed` or
   `user_cannot_sign_in_at_the_provider`, for an address that has no user
   yet, means that the link answer did not carry the user field that the
   guard reads. The command is right to withhold the link. Record the
   failure and its detail, and report it, rather than removing the guard.
6. Record what you observed beside the two reports.

## What the invited person does

The planned journey, which needs the set-password view:

1. The person opens the link once. The identity provider checks it, marks it
   as used and sends the browser to the redirect address with a short
   session in the address fragment.
2. The website asks for a new password and sends it to the identity
   provider. It removes the session from the address bar.
3. The person signs in on the sign-in page with the address and the new
   password. The website asks the service to activate the account. The
   service creates the tenant on this first sign-in only.
4. On the account page the person creates a personal client key, copies it
   once and uses the shown connection settings for a supported client.

What happens at the revision named above: step 1 is the provider's documented
behavior and does not depend on the website. In step 2 the website removes
the session and shows the sign-in form with a notice. It offers no password
form, so the journey ends there and the link is used up. The takeover
checkpoint records that steps 3 and 4 were checked against the real identity
provider with disposable accounts that had a password. Nobody has observed
them with an invited person.

The browser keeps the session in page memory only. A reload signs the person
out, and the sign-in token lasts one hour.

## Reissue a link

Run the same command again with a new report path. The provider reports the
existing address, `user_created` is `false`, `invitation_mark_present` is
`true`, and a new link is shown. Before you deliver it, find the earlier
report in which this command created the same `user_id`. Without such a
report, treat the account as created by someone else.

- Reissue when the link expired, when a message preview used it up, or when
  the person forgot the password. Recovery by email is not available.
- A reissued link sets a new password for an existing account. Confirm
  through a channel that you already trust that the request comes from the
  invited person.
- The provider keeps one recovery token for each user, so a new link
  replaces the earlier one. This follows the provider's published source
  code. It was not observed against the real provider in this work.
- The link expires after the period for email links in the identity
  provider's authentication settings. The current grant cannot read that
  value. Deliver a link soon after you create it.
- The command withholds a link for a user that is banned or removed at the
  provider, so a disabled account cannot get a new link by this route.

## Disable an account

Disable both sides. The order below stops new sessions first.

1. At the identity provider, ban the user in the dashboard's user list. The
   provider's published source code refuses a password sign-in for a banned
   user. This was not observed in this work. A browser token from before the
   ban may stay valid until it expires, at most one hour later. A ban does
   not stop personal client keys, because the service checks those itself.
2. At the service, revoke the subject. The service then refuses browser
   requests for that subject at once, and it refuses every personal client
   key that the subject created, on the next request. Each personal key
   record is bound to the subject that created it, and an older release
   refuses such a record, so a rollback cannot bring a disabled person's key
   back. The owning check is
   `revoked_customer_subject_disables_its_existing_client_tokens` in the
   service's access checks.

Subject revocation has these limits:

- It does not remove material that was already downloaded.
- It does not stop a key that the operator issued for the same tenant. To
  stop everything in a tenant, disable the tenant. That runtime method has no
  operator command either.
- It cannot be undone at this revision. Account activation never restores a
  revoked subject, and a subject record cannot be bound a second time.

There is no operator command for step 2 yet. The only current route is the
typed runtime method, called from a Python process on the service host that
loads the host configuration. This is the route that
[`tools/identity_qualification_host.py`](../../tools/identity_qualification_host.py)
uses for disposable test identities. A check runs the snippet below against
a temporary local service. It has not been run on the hosted service in this
work. Ask the owner before you use it on the hosted service, and record the
printed result.

Take `SUBJECT` from the `user_id` field of the invitation report.

```python
from loop_engine.core.service_runtime.http_entrypoint import load_host_application
from loop_engine.core.service_runtime.records import (
    ServiceRuntimeError, SubjectBindingRequest, SubjectTenantRegistration)

HOST_CONFIGURATION = "/data/host.json"
SUBJECT = "the user_id field of the invitation report"

application, _configuration = load_host_application(HOST_CONFIGURATION)
identity = application.browser_identity.configuration
issuer = identity.project_url + "/auth/v1"
account = SubjectTenantRegistration(issuer, SUBJECT, identity.namespace_prefix)
try:
    print(application.runtime.revoke_subject(SubjectBindingRequest(account.tenant_id, issuer, SUBJECT)))
except ServiceRuntimeError as refusal:
    raise SystemExit("refused: " + refusal.code)
```

| Printed line | Meaning |
|---|---|
| `{'committed': True, 'revoked': True}` | The revocation is stored. |
| `refused: not_found` | The person never signed in, so the service holds nothing to revoke. The ban at the identity provider is then the whole action. |
| `refused: commit_unknown` | The store did not confirm the write. Run the snippet again. Revoking a subject that is already revoked succeeds and changes nothing else. |

Any other refusal code means that nothing was revoked. Stop and report it.

## What this procedure does not cover

| Subject | State |
|---|---|
| Email confirmation | Not covered. The command confirms the address through the administration interface. No confirmation email is sent, so nothing proves that the person controls the mailbox. The operator's own knowledge of the person replaces that proof during the beta. |
| Recovery by email | Not covered. The sender domain is only partially verified and the provider's email settings cannot be changed with the current grant. The operator reissues a link instead. |
| Payment | Not covered. The beta has no checkout, no subscription and no billing block in the host configuration. |
| Public registration | Not offered. See [Keep registration closed](#keep-registration-closed) for what keeps it closed. |
| Restoring a disabled account | Not possible at this revision. |
| Request limits for each address | Separate work in package D-17. |
| Model calls | The service makes none. |

## Checks

Run the checks of the invitation command and of this guide from the
repository root. They contact no provider.

```bash
PYTHONPATH=src:tools .venv/bin/python -m unittest tools/test_invite_beta_user.py
```

The checks fail when one of the guards listed in `RemovedGuardControls` is
removed, when the number of removals stated in this guide differs from that
list, when this guide names an option that the command does not accept, when
the two host blocks above no longer load, when the snippet for subject
revocation stops working against a local service, or when the command can
report a code that this guide does not explain.

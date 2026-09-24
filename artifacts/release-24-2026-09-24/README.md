# Release 24 live evidence, September 24, 2026

Kind: release evidence. The release record is
[`pilot-release-24.json`](../architecture-audit-2026-09-19/pilot-release-24.json).

Fly release 24 serves main revision `961dc906` as image
`sha256:e538318deef9ab06aeb34f591d2617aae7296879b0efdbaf72f54a69bdf1c7ab`.
Continuous integration run 35998911942 passed on that exact revision, and the
guarded workflow run 36001057951 deployed it at 12:47 UTC. The deployment
setting was switched back to false afterwards. Rollback is Fly release 23, but
only after closing registration and removing the two new host blocks, because
release 23 predates the account guard.

## What the release changed

- One way in: an account exists only when Baltor's own sign-up created it.
  Any other account under the same address is refused at sign-in, then
  archived and replaced when the owner of the address signs up through Baltor.
- Staff roles fixed in code: superadmin, developer and analytics. The host
  file names the owner's two addresses as superadmin.
- Administration for a superadmin: every account, with grant or revoke of free
  monthly Baltor Pro and switching an account off or on, each audited.
- The first 10 accounts from Baltor's sign-up hold Baltor Pro free each month.
- Public registration opened at 13:00 UTC, after the checks below.

## Operations on the live service, in order

1. Two Fly secrets were staged from the workstation keyring, never shown:
   `BALTOR_IDENTITY_SERVICE_KEY` and `BALTOR_MAIL_API_KEY`.
2. Release 24 deployed through the guarded workflow.
3. After a backup, the host file gained `account_email` (sign-up closed,
   recovery open) and `accounts` (the owner's two superadmin entries). The
   Machine restarted and answered ready.
4. The marking command planned no change: the identity provider held two
   users, neither created by Baltor's sign-up.
5. The accounts release re-anchored the starter catalogue, which changes every
   body digest, and the homepage printed the new digests while the service still
   served catalogue release `74d3c075`. Catalogue release `69da7ead` (the same 43
   items, bundle `df669af5`) was published to the body store, and the homepage
   digests now match the service. A new check in
   `tools/check_hosted_catalogue.py` compares them from now on.
6. After a backup, registration opened: `account_email.signup_enabled`,
   `browser_identity.registration_enabled` and
   `browser_identity.email_signup_enabled` set to true.
7. The live account journeys ran (below). One checking account was a
   superadmin for the dashboard check and was removed from staff afterwards.

## Checks on the live service

| Check | Result | Files |
|---|---|---|
| Fifteen public addresses on eight hostnames | 120 of 120 answered 200 | `http-surfaces.tsv` |
| Hosted browser acceptance, before registration opened | 163 of 163 on each hostname | `browser-*.json` |
| Hosted browser acceptance, registration open | 163 of 163 on each hostname | `browser-*-registration-open.json` |
| Catalogue, with the homepage digest guard | 7 of 7 | `catalogue-check-with-homepage-guard-2.json` |
| Service transport and isolation | 19 of 19 | `service-check-2.json` |
| Sign-up journeys with disposable inboxes | 11 of 11 | `live-account-journeys-4.json` |
| Superadmin dashboard | 10 of 12; the two failures are the checking script's, see below | `live-staff-journey-3.json` |

The sign-up journeys show the whole path working: the message comes from
`accounts@mail.baltor.ai`, the link opens the confirmation page, and the
provider's verify, the password update, Baltor's activation and the session
each answer 200. The first account lands on "Your account includes Baltor
Pro". An address first registered through the identity provider's own public
sign-up, with a password the script chose, was taken over by Baltor's sign-up:
afterwards the provider refused that first password (400) and accepted the one
chosen on Baltor's page.

The dashboard check showed the superadmin role and granted, revoked, switched
off and switched on free monthly and access for another account, and a switched
off account was refused at sign-in. Its two failures are mistakes of the
script: it expected unconfirmed checking accounts, which have no Baltor
account, to be switched off, and it read a summary that each action's message
replaces. The list read afterwards showed 0 of 10 founding places used.

## Failed first attempts, kept beside their successors

- `service-check.json`: the digest came from the wrong manifest field, so the
  check ran with no digest. `service-check-2.json` passed 19 of 19.
- `live-account-journeys.json` and `live-account-journeys-diagnostic-2.json`:
  the script clicked Confirm before the page had loaded its sign-in settings,
  and the page refused with the link unused. `-diagnostic-3` retried the click
  and passed. A person who clicks that fast sees the same refusal, so the page
  should keep the button disabled until the settings load.
- `live-staff-journey.json` and `live-staff-journey-2.json`: loading `/admin`
  by address signs the in-memory session out, and then a slow network
  handshake stopped the run. `live-staff-journey-3.json` opened Administration
  inside the page.

## Limits and open items

- The emailed links point to `baltor-pilot.fly.dev`, the host file's public
  base address. That address also sets the protocol resource and the identity
  redirect address, so moving it to a brand hostname is a separate change.
- From this workstation, handshakes to Fly's edge stalled for 3 to 7 seconds or
  failed on about a third of requests around 13:15 UTC, including `fly.io`
  itself, while other sites connected normally and Fly reported no incident.
  The inference is the network path from this workstation, not the service.
- The identity provider's own public sign-up is still open at the provider,
  because its authorization could not be renewed from here. The service
  refuses every account it did not create, as the journeys show.
- Five checking accounts with `baltor-check-` addresses remain: two never
  confirmed, two switched off, and one on with no plan. None holds a founding
  place.

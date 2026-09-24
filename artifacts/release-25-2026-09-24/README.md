# Release 25 live evidence, September 24, 2026

Fly release 25 runs main `c93c201f` (image `sha256:f129ea56…1d7b`), deployed at 18:34 UTC through the guarded workflow run 36041898386 after continuous integration run 36039453053 passed. The rollback target is release 24. The [release record](../architecture-audit-2026-09-19/pilot-release-25.json) holds every identifier.

## What the release changed

- A superadmin sends Baltor's own sign-up links, with optional free monthly Baltor Pro that takes no founding place.
- The confirmation page keeps Confirm disabled until its sign-in settings load.
- The library inventory record and the September 24 persona journeys record.

## Checks on the live service

| Check | Result | Files |
|---|---|---|
| Fifteen public addresses on nine hostnames | 135 of 135 answered 200, one set of capabilities | `http-surfaces.tsv`, `capabilities-*.json` |
| Pi extension served byte for byte | 9 of 9 | `pi-extension-digests.tsv` |
| Hosted browser acceptance | 163 of 163 on each of the nine hostnames | `browser-*.json` |
| Catalogue, with the homepage digest guard | 7 of 7 | `catalogue-check.json` |
| Service transport and isolation | 19 of 19 | `service-check.json` |
| Superadmin sign-up link journey, live, with a disposable inbox | 14 of 14 | `live-sign-up-link-journey.json` |
| Superadmin dashboard | 13 of 13 | `live-staff-journey.json` |

The sign-up link journey shows the new feature working end to end. A superadmin sent one link with free monthly Baltor Pro. The person showed as pending, and the message named the sender and linked to the confirmation page. Choosing a password opened the account with the staff grant, and the founding count did not change. A second link to the same address was refused, and no second message arrived. The checking account then gave its grant back and was switched off.

## Failed first attempts, kept beside their successors

- `deploy-attempt-1-failed.json`: the first deploy run timed out authenticating with Fly's image registry during a Fly incident in another region; nothing was deployed.
- Deploy run 36038136103 was refused by the stale-revision guard, because a workflow pushed an inventory record to main during the build. The guard worked as designed.
- `browser-app.baltor.ai-attempt-1-timeout.json`: one page load timed out from this workstation to Fly's edge; the rerun passed.

## Account housekeeping

Three persona test accounts from the September 24 journeys held founding places. They gave the places back and were switched off (`persona-founding-places-released.json`). The account list reads 0 of 10 founding places used. The temporary checking superadmin was removed afterwards, with the host file backed up before each change.

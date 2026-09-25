# Release 34 evidence, September 25, 2026

Fly release 34 of `baltor-pilot` went live at 21:17 UTC from main
`ea2bc508e79db2893f9c19b5f3a26c3f6c1c9611` after continuous integration run
36188082095 passed, through deployment run 36190472613. The image is
`sha256:a914f340558115a940de44eed8712037f887744867adf3e47517ed5150868936`;
the rollback target is release 33. The record is
[`pilot-release-34.json`](../architecture-audit-2026-09-19/pilot-release-34.json).

## What a person sees now

- A public library page at `/library`, open without an account: every
  Verified item with its purpose, identity, kind, licence, size, digest and
  a link to its review record; the Community items counted by kind and tier;
  what the two labels mean, in the words the service publishes; one item in
  full; and what the served release added, changed and withdrew.
- The Library link in the header and in the footer opens that page.
- The emailed sign-up and recovery links, the identity record's redirect
  address and the published protocol address now name baltor.ai instead of
  the Fly hostname (roadmap S-6.182): the host file's `http.public_base_url`
  was moved at 21:15 UTC, after a dated backup, and this release's restart
  loaded it.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 45 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 310 links checked |
| The customer's search and download, with Verified and Community searches and the homepage digest guard | 9 of 9 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, the Pi extension matches on all nine
hostnames, and 216 of 216 detailed browser rules pass on baltor.ai. The
browser suite on GitHub (run 36188086164) passed on this revision.

A first push of the same page, `5642c8cf`, failed continuous integration:
the self-test's zero-tolerance scan counts an import of `urllib` outside the
model gateway as a network call, and the page parsed the repository address
with `urllib.parse`. It now splits the address as text. The push had skipped
the self-test after its last source change; the fix ran every gate first.

The screenshots are kept outside the repository.

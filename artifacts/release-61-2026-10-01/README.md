# Release 61: Public Good discovery and Dot working interfaces

The goal-first Public Good page, Dot briefs and feedback interfaces are live.
The [release record](../architecture-audit-2026-09-19/pilot-release-61.json)
binds source `117d43fc`, the deployed image and the release-60 rollback.
CI 36888149782 and guarded deployment 36889262009 passed. The deployment
gate is off. Catalogue and free-access policy are unchanged.

## Working interfaces

- `/public-good` explains the free-account route and shows all seventeen
  goals, including honest empty categories, before the advanced search.
- `/dot-context` and `/dot-feedback`, with matching `.json` views, provide
  dated public briefs and content revisions. They are unlisted, not private.
- Customers can submit ratings and material requests through the existing
  records over MCP, HTTP or the standalone feedback command.
- Staff can read a counts-only summary; detailed notes remain restricted.
  Browser staff authority and ordinary OAuth delegation stay separate.
- The owner-requested staff assignment was verified against the confirmed
  stable account identity. Existing account access and billing were preserved.
  The owner's actual Dot session was not available for an end-to-end check.

Reading a brief does not reserve a task or start a timer. No ten-minute
schedule, direct database connection, automatic upload or unreviewed public
feedback feed was activated by this release. The
[feedback guide](../../docs/guides/customer-feedback-and-requests.md) names
exact operations, permissions, retention limits and unfinished work.

## Fresh checks

All ten hostnames pass the existing read-only browser acceptance suite:
2,118 assertions, with no reported browser errors or unexpected external
requests. This is a bounded journey check, not an uptime guarantee.

Public Good and Dot pass 60 live checks, including all 1,011 useful file
digests, filters, desktop/phone layouts, revision checks and anonymous
refusal. Homepage task/harness selection passes 259 live checks.

All six published client files match the pinned 0.4.1 package. The downloaded
stock copy passes fifty supplied tests, ten independent filesystem checks
and fifteen local TLS/CONNECT proxy controls without a test transport adapter.
The package digest is
`b1e61714cf272e413833e7a2d1d9bd3314e0e37fbcb107461c4536619a442d4a`.

Local evidence includes 3,689 self-tests, 958 website assertions with 197
known-wrong controls, 42 Dot/consent checks and 45 independent staff-browser
checks. These are separate populations, not a replacement for the owner's
57-case baseline or an end-to-end pass for every harness. The chart example
and project-output confinement retain their open qualification work.

## Failure and recovery

After deployment, the staff configuration update retained root ownership
while setting the host file to mode `0600`. The service runs as UID 65534,
so the subsequent restart could not read its configuration. This was an
operator error. Earlier successful deployment checks do not erase it.

The repair changed only that exact file's filesystem metadata and checked
unchanged bytes. Its final root ownership, service group and mode `0640`
permit the application to read and parse it but not write it. The original backup remains
private. Fresh account verification confirms the requested role and unchanged
plan; service health and the provider health check pass after startup.

The operator now tests staged configuration as the service identity before
replacement. A synthetic root-owned `0600` file fails that check, while the
service-readable file passes. Cold startup still took about ten minutes on the
existing shared CPU and volume; startup measurement and safe caching are
follow-up work, not justification for weakening catalogue checks.

The first Public Good/Dot test had 51 successful assertions followed by a
screenshot-driver filename error. The corrected run passes all sixty.
Client-fetch timeouts during the restart and the failed preceding CI remain
saved. A web-reader tool could not access the Dot URLs even after recovery;
direct HTTP and normal browser checks succeeded. Dot's actual browser or
connected HTTP route needs its own verification.

Private evidence is under `release61-20261001-fCSKXw`,
`release61-client-public-20261001-R0OM0I` and
`owner-staff-20261001-qDpwu8` in the authorized private workspace. No account
identity, credential or host configuration is included in this public record.

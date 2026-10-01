# Release 57

Fly release 57 deployed `24bd2482` after CI `36794461488` passed. Deployment
`36795042426` passed, and the deployment gate is off. The
[release record](../architecture-audit-2026-09-19/pilot-release-57.json)
names the image, exact source and release-56 rollback image. The UTC image
step completed October 1 at 00:15:52, still September 30 in the owner's timezone.

The guided examples now identify their recorded starter catalogue and bind its
exact manifest. They no longer present old hashes as current live search
results. A separate check confirms current availability; harnesses must still
search and verify the selected current bytes.

CI exposed a real download failure under contention. SQLite read errors could
be reported as unauthorized or as an unknown meter commit. Tenant lookup also
lost its typed refusal. Worse, the generic callable wrapper could replay a
failed effect, succeed on its second call and return the first error. The
repair preserves typed read failures and one callable execution. After a
committed write, only confirmation reads are retried; exhaustion remains
unknown and never claims nothing was recorded. Forty-one customer-delivery
tests and separate deterministic phase probes cover these distinctions.

## Verification and remaining work

The image passed 22 container checks and 744 service checks. Live checks passed
50 public requests across ten hosts, 2,118 browser checks, all 11 catalogue
checks, seven existing-customer delivery checks and seven game checks. The
rollback image passed six owner-aware checks using synthetic state. Grant
confirmation took 52.737 seconds and billing 0.72 seconds; billing changed no
policy or paid access. These timings are deployment observations, not a search
or model-benefit benchmark.

The separate live documentation suite passed 146 of 147 checks. Its remaining
failure is the documentation index height at desktop width: 2,426 pixels
against the 1,800-pixel bound. The index order is correct. This is recorded
housekeeping, not an entirely passing layout suite.

Three failed candidate CI revisions remain recorded. The final correction
regenerated the records index; no guard was removed to make CI pass.

The [Public Good candidate report](../../docs/verification/PUBLIC-GOOD-CANDIDATES-2026-09-30.md)
records nine tested packages and their limits. They are not yet admitted or
served. The latest owner request makes the account-required free-access policy,
top-header collection browser and all-SDG population the next product work.
The active catalogue remains at 30,746 packages and 96,064 distinct files.

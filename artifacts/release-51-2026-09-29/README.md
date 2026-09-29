# Release 51

The [release record](../architecture-audit-2026-09-19/pilot-release-51.json)
is the authority for the deployed revision, image, rollback image and exact
checks. It records the application release separately from catalogue updates.

The first written copy accidentally named an unsupported `v2` record despite
using the existing `v1` fields. CI run `36645253101` correctly refused it.
The corrected record uses `pilot_release_record/v1`; no reader or unknown-version
guard was weakened. The [original copy](unsupported-record-preserved.json) is
preserved byte for byte, SHA-256
`3cb8fb4e52a1e5e528a30c821b5c2ca1e8c6d4f95854e3a81a54c25655b7382f`.

Source `081d8e24` passed CI run `36638264614` and deployed through guarded
workflow run `36639204067`. The deployment setting was read back as false.
The existing one-CPU, two-GB Machine and 25-GB volume were retained.

Anonymous live browser checks passed 218/218. All nine declared website
hostnames answered HTTP 200. Private evidence is in
`/home/username/baltor-private/project-review-20260929-LWR6IQ/`:
`release-51-live.json` and `release-51-hostnames.json`.

The complete local browser run remains recorded as 945/946, with all 195
removed-guard controls detected. The sole stale wording assertion was repaired
and checked separately. The hosted checks do not prove live payment, every
native harness, artistic quality or completion of the million-file target.

The separate [catalogue publication](../catalogue-publication-2026-09-29/programs-3910.json)
added 3,910 program packages and 19,551 distinct files. The live totals are
27,811 packages and 88,373 distinct files. The first-party client retrieved
all seven files of one new package with matching digests using a short-lived,
one-item-scoped operator identity. No downloaded code was executed.

The 35 original creative seed packages remain candidates. The million-file
target is still open. See the [session reconciliation](../../docs/context/SESSION-RECONCILIATION-2026-09-29.md)
for remaining work and qualification limits.

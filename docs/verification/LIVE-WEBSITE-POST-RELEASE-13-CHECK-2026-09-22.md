# Live website check after the reported release 13

Kind: read-only public-site observation. The owner reported that release 13
was live and checked. This report independently read public responses on
September 23, 2026 from 00:22 to 00:23 UTC, the evening of September 22 in
America/New_York. The public response did not expose a release number or
image digest to this unauthenticated check, so attribution to release 13 is
the owner's report rather than an independently established deployment
identity. No credential, form submission or paid operation was used.

This succeeds the earlier
[live homepage and invitation observation](LIVE-HOMEPAGE-AND-INVITATION-OBSERVATION-2026-09-22.md).
Keep both records because the site changed between their checks.

## Observed public responses

Unauthenticated GET requests to `/` and `/signup` on `baltor.ai`,
`www.baltor.ai` and `app.baltor.ai` each returned HTTP 200 with the same
72,901-byte initial application HTML body, SHA-256
`c5bcb2b565f044b551c9b5fe3cecc96dca0e77440bfcc90f34f0cedc928e52cc`.
The old `solution-preview` aside was absent. This supports that the repaired
homepage source has reached all three public hostnames tested; equal initial
HTML is expected for this client-routed application and does not prove the
rendered pages are identical after JavaScript runs.

The same live HTML still contains waiting-list placeholder copy. At 00:22
UTC, the unauthenticated
[capabilities response](https://app.baltor.ai/api/v1/capabilities)
reported `website.registration_available: false`,
`website.waitlist_available: false`, and
`website.access_profile: operator_provisioned`. The public invitation
journey therefore remains closed; a visible “Join the waiting list” link is
not evidence that a visitor's email can be submitted. A root `HEAD` request
to `https://baltor.ai/` still returned HTTP 404, while `GET` returned 200.
The public health response reported `readiness_checked: true` and
`deployed_provider_qualification: false`. This is a health observation,
not proof of a complete customer task, provider integration, payment or
native harness loading.

## Next discriminating check

S-6.33 and S-6.35 in the [roadmap](../roadmap/roadmap.yaml) still own the
invitation, `HEAD` and per-hostname route checks. After the next committed,
checked release, verify an unaffiliated visitor can submit an invitation
request and see a confirmation, with the request recorded exactly once;
verify `HEAD` succeeds on the intended root route and each hostname serves
the correct content. A page that merely includes a hidden form or returns
the application shell does not pass those checks. Save the source revision,
image digest and release identifier with the next live result.

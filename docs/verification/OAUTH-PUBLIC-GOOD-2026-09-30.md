# OAuth and Public Good qualification

Kind: September 30 engineering evidence; deployment is recorded separately.

The owner prioritized OAuth after their dot QA refused manual API-key
transfer, and asked for account-required free Public Good files with a main
header page. The implementation reuses the existing Supabase browser account,
CatalogStore and pinned MCP 2.2.0 handlers. It does not transfer a browser
credential to a harness or treat a general identity token as an MCP token.

## What was tested locally

- Twenty-three provider tests and eight independent real-loopback HTTP tests
  pass. These cover signed local-JWKS browser identity, explicit consent,
  dynamic public-client registration, PKCE, exact resource/redirect checks,
  code replay, refresh downscoping and rotation, account disabling, revocation,
  real MCP calls, admin-scope refusal and preservation of unknown commits.
- A real Chromium sequence passes twenty checks: desktop/phone Public Good
  layout, seventeen goal choices, query and empty results, normal sign-in
  resuming consent, explicit approval and denial, exact-component navigation
  and an unpaid synthetic account's explicit free download. No real identity
  provider, model or production credential was used in that test.
- The independent Public Good HTTP suite passes sixteen methods, including
  the deliberately restored early-completion defect as a known-wrong control,
  no-billing assertions, host/account caps, exact binary file and MCP delivery,
  cache/cursor invalidation and late-worker/retry isolation.
- The documentation browser passes 162 checks after the long index's
  auxiliary guides and technical setup became expandable. All cards, links,
  installation instructions and complete runtime explanation remain present.
- The public Library sample is now metadata-only. A negative test supplies a
  body reader that raises if invoked and confirms public rendering never
  calls it. The known-wrong first anonymous body is rejected.

These checks do not establish a connection from the owner's real dot, a
marketplace approval, field effectiveness, or 1,000 published Public Good files.

## Defects found and retained

The SDK's revocation model required an omitted public-client secret field.
The adapter supplies an empty field for this profile and refuses supplied
credentials. Its metadata is corrected to advertise `none`, and its token
handler receives the missing exact-resource validation before processing.
The first failing integration attempt and its succeeding rerun are preserved.

Independent Public Good checks found that ratings consulted only paid usage,
and that response completion ran before the full HTTP/MCP envelope cap. A
subsequent deadline test found raw download completion still inside a worker
that could outlive its response. Ratings now share the exact-version delivery
predicate. All transports defer free-delivery completion until their timed
read returns and final size checks pass. Reservations still count attempts;
an already-started uncertain commit is never described as rolled back.

## Supply is a separate gate

The read-only supply audit inspected 23 packages and rehashed 143 files. Its
initial selection is ten already-admitted packages with fourteen useful
payload files, not 1,000. The selection request is bounded to the existing
catalogue release and expires on November 1, 2026. It is not applied merely
because its file was prepared. Metadata, licence notices, wrappers and tests
do not inflate the useful-file or capability count.

Nine original candidate tools passed 132 producer tests and native loading
checks, but their first independent Kimi pass rejected them. Supporting
material defects are being repaired with lineage; rejected candidates remain
unpublished until a new independent admission approves their exact bytes.

## Evidence location and remaining limits

Private attempts and screenshots are under
`/home/username/baltor-private/oauth-20260930-QGXZyh`.
Independent HTTP suites are under `oauth-http-integration-20260930-P2KyEF`
and `public-good-http-review-20260930-LRJmsY` beside it. Credentials are not
included in this report or test outputs.

The initial OAuth profile has retained-record ceilings and no automatic
expired-row cleanup. The Public Good authorized-response record is monthly
per item/account, not the requested event-by-event customer history.
Research/file uploads, a dot work queue, media delivery, demanding comparative
tasks and the 1,000-useful-file target remain subsequent delivery gates in
[the linear plan](../roadmap/DELIVERY-SEQUENCE.md).

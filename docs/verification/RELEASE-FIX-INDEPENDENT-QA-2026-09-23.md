# Independent release-fix review

Date: September 23, 2026. Reviewer: Codex standards research agent, independent
of the repair author. Reviewed worktree:
`/home/username/.le-codex-build/release-fix`, based on
`d2e204133b241c3659118df493f4e4aa1e63821e`.

**Result: no release blocker found within the requested repair scope.** The
exact-tree continuous-integration run, guarded deployment and live checks
remain separate gates. The reviewer made no edits in the release worktree,
no provider calls and no deployment changes.

## Independently verified

- The seven public-asset delivery tests pass.
- All 15 declared cacheable assets pass additional real loopback HTTP checks:
  exact-byte strong entity tag, GET content, HEAD metadata and empty body,
  and weak-validator conditional HEAD returning 304 without a body.
- Authenticated session, capabilities and health responses return 200 with
  `Cache-Control: no-store`, even with an `If-None-Match` wildcard. The
  author's tests separately cover errors, untrusted hosts, account pages and
  non-GET asset operations.
- Cache eligibility is limited to declared packaged non-HTML assets,
  GET/HEAD and status 200/304. Protocol responses keep their separate
  `no-store` path. No private response or error becomes cacheable through the
  changed predicate.
- Python 3.11.15 imports the repaired configuration; all 48 configuration
  tests pass. Two newly constructed criteria records have equal but distinct
  empty mapping proxies, and mutation still raises `TypeError`.
- The source retains the eight-operation worker pool/semaphore default and
  per-account shares. The HTTP fixture reports eight. Only the Fly proxy
  request thresholds change, to soft 64 and hard 128.
- The homepage source removes the category badge and starts the opening with
  its heading. The category explanation remains in the page and footer; the
  badge-specific CSS is removed. The author reports 551 browser checks and
  91 removed-guard controls; this independent review did not rerun that broad
  browser suite.

The [fixture evidence](../../artifacts/release-fix-independent-qa-2026-09-23/fixture-observations.json)
binds exact hashes for the changed transport, page module, deployment settings,
configuration and homepage/style files. It records only response metadata and
digests, without fixture credentials or private response bodies.

## Validator and release semantics

The weak comparison used for GET/HEAD `If-None-Match` agrees with
[HTTP Semantics, section 13.1.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.2).
Matching validators return 304 with the current entity tag and cache policy;
stale validators return the current body. HEAD preserves the GET content length
while sending no content. HTML itself remains uncacheable.

Version queries in directly embedded HTML references force a different cache
key when the packaged asset bytes change. The version inventory is cached
inside one process, which assumes an immutable release image and a process
restart for a new release. Editing packaged files inside a running process
would violate that assumption.

Two limits should remain explicit:

1. The query value is a cache-busting hint, not a validated content address.
   A request with an incorrect `v` still returns current bytes and status 200.
   Do not claim digest-enforced delivery or compatibility across mixed old/new
   processes during a rolling release. This is a bounded five-minute cache
   policy, not an immutable-asset policy.
2. Font URLs inside `architecture.css` are unversioned and may retain up to
   five minutes of prior cached bytes after a font change. The JavaScript
   request for `client-recipes.json` explicitly uses `cache: no-store`, so it
   does not depend on this indirect-reference cache behavior.

These are freshness and rollout limitations, not observed privacy leaks. A
future move to longer-lived immutable caching should qualify transitive asset
references and old/new release coexistence first.

The raised proxy thresholds are a configuration response to an asset-request
burst, not proof that the application can sustain 128 expensive operations.
The separate application admission controls remain essential; the live release
checks should verify errors and latency without changing that interpretation.

# Release 44: the knowledge radar and one-command release tooling

Fly release 44 completed on September 28, 2026 at 11:10:55 UTC from
`d4542e93c702dbb529be057ee9f480d40217691c`. It carries the fifth
consolidation train of September 27, which was stopped overnight by a usage
limit and pushed the next morning after one documentation fix.

## Release identity

The [sanitized release record](release.json) binds source tree
`e3ce544706f1d882fe4350716a8e2ea98ff87fd8`, the running image and the rollback
image to the checks. The image is
`registry.fly.io/baltor-pilot@sha256:0b3e6782d9a96482a8264e7bda1d3a50eefcd81a1d094590016f5e7a5edaa188`.
Rollback is release 43, image
`sha256:1746b97fd5f19a0076144a18bd074f803d8a702c15aa45a51f993e7a0bfc3374`.

Continuous integration
[36413186206](https://github.com/alisonjieli-png/loop-engine/actions/runs/36413186206)
and deployment
[36413843751](https://github.com/alisonjieli-png/loop-engine/actions/runs/36413843751)
completed successfully. The deployment gate was read back as false.

## What changed

- The knowledge radar: a question registry, source contracts and source
  engines, a planner, a feed, an hourly model release watch and a staged
  daily run. Its guards are checked against known-wrong cases.
- Release tooling: one command regenerates every generated view in
  dependency order, a pristine check exports the commit, one command builds a
  release train, and tools test modules are placed in shards at run time, so
  a new test changes no committed file.
- The pre-push check chooses its interpreter from the checkout and says when
  a local run is not equivalent to continuous integration.
- The hardcoding findings that turned main red on September 28 are cleared.
- The release 43 record, the September 27 session handoff and the cited Codex
  research evidence are committed.

## Live evidence

- The visitor check passed 57 pages, 237 views, 9 hostnames and 351 links
  with zero reported problems and 114 screenshots.
- Authenticated catalogue checks passed nine of nine, including search and
  the exact download.
- The hosted service check passed nineteen of nineteen on its first attempt.
- Advice: 135 public addresses answered with no failure; the served Pi
  extension matched the committed files nine of nine; the detailed browser
  rules passed 214 of 216. The two failures are the same hero rules as in
  releases 41 to 43, written before the September 26 hero.

The release record holds aggregate results and exact report hashes only.
Private reports remain under
`/home/username/baltor-private/releases/release-44-2026-09-28`. No
credentials, account identifiers or account state are copied here.

# Release 41: the first consolidation train

Fly release 41 completed on September 27, 2026 at 19:39:38 UTC from
`389fe7c6c553a035e810b1173bee9e70edf766df`. It carries the first
consolidation train of that day: work that had waited in separate worktrees,
Codex's handed-off integration work and the updated north star.

## Release identity

The [sanitized release record](release.json) binds source tree
`07d37dccb159aeb9e660f419addcb795de436dcb`, the running image and the rollback
image to the checks. The image is
`registry.fly.io/baltor-pilot@sha256:73ee31a4f7fddb9c7a2fa22f4e0166749fbaca93e4eb47cc35a0f9a343f9f31c`.
Rollback is release 40, image
`sha256:be98a37bb29c1ae48c62c18d87c8fea5e9f0ba278ef546a217e245e277d8629e`.

Continuous integration
[36344591966](https://github.com/alisonjieli-png/loop-engine/actions/runs/36344591966)
and deployment
[36345000680](https://github.com/alisonjieli-png/loop-engine/actions/runs/36345000680)
completed successfully. The deployment gate was read back as false.

An earlier revision of the same train, `f4979336`, was refused by continuous
integration for two links to files that did not exist; `389fe7c6` turned both
into plain mentions. Nothing from `f4979336` was deployed.

## What changed for a visitor or customer

- Pages served before scripts run show the live library count instead of a
  fixed 43, so link previews carry the real number.
- The homepage example folder lists only the files the download delivers.
- Three customer guides: component concepts, updates and withdrawals, and
  common questions.
- Two service page claims were repaired and are now held to the source.
- The first-party Baltor library skill 0.3.0 ships under `integrations/` for
  Claude Code, Codex, OpenCode and Pi, and the install tool compiles packages
  into OpenCode tools and Pi extensions.

## Live evidence

- The visitor check passed 57 pages, 237 views, 9 hostnames and 322 links
  with zero reported problems and 114 screenshots.
- Authenticated catalogue checks passed nine of nine, including search and
  the exact download.
- The hosted service check was interrupted by a network error on its first
  request to the machine address, minutes after the deploy, so it measured
  nothing; the rerun passed nineteen of nineteen. Both results are recorded.
- Advice: 135 public addresses answered with no failure; the served Pi
  extension matched the committed files nine of nine; the detailed browser
  rules passed 214 of 216. The two failures are hero rules written before the
  September 26 hero, which expect no search demonstration in the hero band.
  They are recorded for the rules flexibility audit and are not a visitor
  problem.

The release record holds aggregate results and exact report hashes only.
Private reports remain under
`/home/username/baltor-private/releases/release-41-2026-09-27`. No
credentials, account identifiers or account state are copied here.

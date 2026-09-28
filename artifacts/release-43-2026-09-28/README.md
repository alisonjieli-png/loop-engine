# Release 43: rules flexibility and the one million file goal

Fly release 43 completed on September 28, 2026 at 00:23:02 UTC from
`d874a09397ac8def29bbdd140b4960c59d6da6e5`. It carries the fourth
consolidation train of September 27: the rules flexibility changes, the
catalogue writer flush repair, the release 42 record and the owner's one
million file goal.

## Release identity

The [sanitized release record](release.json) binds source tree
`1c5a3f4ebfa099a91139ef43b3d556785131a1de`, the running image and the rollback
image to the checks. The image is
`registry.fly.io/baltor-pilot@sha256:1746b97fd5f19a0076144a18bd074f803d8a702c15aa45a51f993e7a0bfc3374`.
Rollback is release 42, image
`sha256:7818f73a1d8f53b594b6175adab9338efdc1a63b8cd9abf1e7f14efa7a5b7625`.

Continuous integration
[36361405152](https://github.com/alisonjieli-png/loop-engine/actions/runs/36361405152)
and deployment
[36361858710](https://github.com/alisonjieli-png/loop-engine/actions/runs/36361858710)
completed successfully. The deployment gate was read back as false.

## What changed

- The catalogue body writers flush only the files they wrote before a
  release becomes active. They no longer flush every disk of the machine, a
  call that stalled for hours on the development workstation while another
  disk was busy. The next catalogue publish on the live service is the first
  to use the new flush.
- The public changelog lists release 42.
- The north star says that agents are swappable and that each step's supply
  comes from Baltor.
- The roadmap carries the owner's goal of one million served harness
  component files as step S-6.215.
- The records index no longer carries a totals line that changed with every
  record, and a documentation folder can state its kind in each file.
- The rules flexibility audit and the decisions on the private registry, the
  front door, the research worker and meta-harnesses are recorded.

## Live evidence

- The visitor check passed 57 pages, 237 views, 9 hostnames and 351 links
  with zero reported problems and 114 screenshots.
- Authenticated catalogue checks passed nine of nine, including search and
  the exact download.
- The hosted service check passed nineteen of nineteen on its first attempt.
- Advice: 135 public addresses answered with no failure; the served Pi
  extension matched the committed files nine of nine; the detailed browser
  rules passed 214 of 216. The two failures are the same hero rules as in
  releases 41 and 42, written before the September 26 hero.

The release record holds aggregate results and exact report hashes only.
Private reports remain under
`/home/username/baltor-private/releases/release-43-2026-09-28`. No
credentials, account identifiers or account state are copied here.

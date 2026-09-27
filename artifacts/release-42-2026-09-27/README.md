# Release 42: the model directory licence repair and release tooling

Fly release 42 completed on September 27, 2026 at 20:51:48 UTC from
`f477aa6e9ea64dd9f4e19f6d8bd4744f98845ad2`. It carries the second and third
consolidation trains of that day: the model directory repair, provider
settings and release tooling fixes, and the release 41 record.

## Release identity

The [sanitized release record](release.json) binds source tree
`88e4cc8e865355ca9dae98f19b2f10ba4a41faba`, the running image and the rollback
image to the checks. The image is
`registry.fly.io/baltor-pilot@sha256:7818f73a1d8f53b594b6175adab9338efdc1a63b8cd9abf1e7f14efa7a5b7625`.
Rollback is release 41, image
`sha256:73ee31a4f7fddb9c7a2fa22f4e0166749fbaca93e4eb47cc35a0f9a343f9f31c`.

Continuous integration
[36349035044](https://github.com/alisonjieli-png/loop-engine/actions/runs/36349035044)
and deployment
[36349428058](https://github.com/alisonjieli-png/loop-engine/actions/runs/36349428058)
completed successfully. The deployment gate was read back as false.

An earlier revision of the second train, `6ad91b12`, was refused by
continuous integration because a generated status view was built before the
release 41 record was committed. The third train regenerated every view after
its last commit. Nothing from `6ad91b12` alone was deployed.

## What changed for a visitor or customer

- The model directory no longer republishes values copied from OpenRouter or
  Artificial Analysis, whose terms do not allow it. Model pages link to both
  services instead, and scores from LMArena are credited under its licence.
- Every model directory address that stopped being served now answers a
  permanent redirect (30 addresses, each checked to lead to the same model)
  or 410 Gone (103 addresses) instead of 404.
- The model directory records that Ollama Cloud does not support structured
  outputs.
- Settings refuse a custom provider that takes a built-in provider name.
- `--compile-provider` can select a keyless local provider, and the run
  checkpoint records a task that came from `--file`.
- The overnight guide no longer names the undefined
  `--allow-sandbox-commands` option.
- Release tooling never empties a folder that the manifest generator did not
  write, and the workflow checks reach a conclusion before they report
  success.

## Live evidence

- The visitor check passed 57 pages, 237 views, 9 hostnames and 351 links
  with zero reported problems and 114 screenshots.
- Authenticated catalogue checks passed nine of nine, including search and
  the exact download.
- The hosted service check passed nineteen of nineteen on its first attempt.
- Advice: 135 public addresses answered with no failure; the served Pi
  extension matched the committed files nine of nine; the detailed browser
  rules passed 214 of 216. The two failures are the same hero rules as in
  release 41, written before the September 26 hero. The rules flexibility
  audit covers them; they are not a visitor problem.

The release record holds aggregate results and exact report hashes only.
Private reports remain under
`/home/username/baltor-private/releases/release-42-2026-09-27`. No
credentials, account identifiers or account state are copied here.

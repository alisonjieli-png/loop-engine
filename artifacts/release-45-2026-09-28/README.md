# Release 45: the customer delivery train, live

Fly release 45 completed on September 28, 2026 at 23:12:55 UTC from
`3e6064bd7dd64249925c97784f1cf10e0d067d11`. It carries the September 28
customer delivery train, the delta catalogue publisher, the capacity guard, and
the harness list and copy change.

## Release identity

The [sanitized release record](release.json) binds the source revision, the
running image and the rollback image to the checks. The image is
`registry.fly.io/baltor-pilot@sha256:0c08fcd3e1e8cb0689a5ea6bc2db688e0e85c6bec58f11b48e93dc1e68356063`.
Rollback is release 44, image
`sha256:0b3e6782d9a96482a8264e7bda1d3a50eefcd81a1d094590016f5e7a5edaa188`.

Continuous integration
[36495706574](https://github.com/alisonjieli-png/loop-engine/actions/runs/36495706574)
and deployment
[36496410671](https://github.com/alisonjieli-png/loop-engine/actions/runs/36496410671)
completed successfully. The deployment gate was read back as false.

## Why the previous sessions ended without a release

The September 28 handoff ended with main four commits ahead and nothing pushed,
because the full gate suite had not run green. The reason was recorded as
compute; it was not compute.

- The twenty gate runs and the two that produced no output died because the
  session that started them was reaped, not because the machine ran out of
  memory. `/tmp` was 38 MB against 31 GB and 39 GB of swap was free. A gate run
  started from an interactive shell dies with that shell; started detached it
  completes in about seven minutes.
- The hardcoding gate was flapping between exit 0 and exit 1 on an identical
  tree because two sessions were editing the allowlist and the audit's own
  source while scans ran.
- With the writers stopped, the gate had exactly two failures. One was
  crash residue in `devtools/hardcoding-allowlist.yaml`: twenty-three entries
  for the shell variables of `tools/heavy.sh` and `tools/reap_leached_temp.sh`
  that the classifier added in `eeabbbc0` had already made non-blocking, each
  carrying a classification the audit no longer reported, plus six findings
  placed in `excluded_paths`, which requires a path and a digest, where they
  belong in `entries`. The other was `record_demonstration_steps.py`, which has
  a check mode and was never registered, so the registry rule failed.

Both are fixed in `d15b5743`. The check was not changed to pass: the audit
still refuses an allowlist whose entries or exclusions do not match what it
reports.

## What changed

- The two gates the September 28 sessions left failing are repaired. The
  `demonstration-steps` view now writes the homepage's recorded demonstration
  facts from the release manifest, so the digests, sizes, kinds and licences
  the page prints are regenerated from the release it describes instead of
  being written by hand. Two runs on an unchanged library are a no-op.
- The customer delivery train is live. A locked store answers with a retryable
  refusal rather than a wrong one, the refusal-wording check reads key prefixes
  at the start of a word, the starter catalogue is re-anchored at the revision
  holding its cited bytes, and the hardcoding gate's new high finding carries a
  named decision.
- `tools/publish_catalogue_delta.py` publishes a catalogue release by uploading
  only the blobs the volume lacks.
- The homepage names the harnesses that were tested and no longer counts the
  library in "reviewed" units.

## Live evidence

- The visitor check passed 57 pages, 237 views, nine hostnames and 353 links
  with zero reported problems and 115 screenshots.
- The hosted service check passed nineteen of nineteen. The metered read
  recorded exactly one usage unit, and an exact retry of the same request
  retained that one durable acknowledgment.
- Catalogue checks passed seven of nine. The two failures are the
  demonstration pages printing digests from the repository's manifest, which
  follows the latest anchor, while the served catalogue still serves the
  release it was published from. `tools/record_demonstration_steps.py` and the
  `demonstration-steps` view now own that class, so each publish rewrites the
  printed facts from the release the service actually serves. The seven
  disclosure checks that read the service, including search, the rejected-item
  refusals and the served set, all pass.

## What this release does not claim

One Machine holds the catalogue store, the bodies and the release pointer, so a
code release still takes the site down for the length of one machine's
replacement. The zero-downtime shape the owner approved on September 28 needs
the on-disk serving engine, which is built and audited but not yet merged. The
recorded budget for it, about 43 dollars a month against the 50 dollar ceiling,
is unchanged.

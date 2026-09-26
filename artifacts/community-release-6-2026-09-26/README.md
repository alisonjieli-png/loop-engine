# Community release 6: the first slot that cron started, 6,398 packages served

Kind: dated record of one catalogue release, published by the daily job's
10:17 UTC slot on September 26, 2026 (roadmap S-6.197). The bytes of the
release live outside this repository; this record names them by digest.

| Fact | Value |
|---|---|
| Slot | `2026-09-26-10`, started by cron at 10:17 UTC, the first slot no person started |
| Export | 2,000 packages from the import store (the ranked order, the last export before the balanced mix of S-6.205) |
| Prechecks | 1,660 passed, 340 refused |
| Calibration | qualified at the first attempt, 10:33 UTC |
| Review | 139 Tactical calls (`gemma-4-coding-abliterated`), 10:33 to 11:37 UTC, 45 rejected |
| Write | 1,586 approved, 45 rejected, 29 left out, 11:52 UTC |
| Snapshot | `~/baltor-library/release-folders/daily-2026-09-26-10`, 6,398 approved rows |
| Bundle | digest `0d7edf75842e662f859353622de201bf5d8c345fe0b00ce233dc4f9294a278dd` |
| Release | `856bff51fac2bf8f4d70b181a8b129d4fdaa5624dffe020db06ce5239724053f`, active at 11:55 UTC |
| Live check | 6 of 6 as a customer: search finds a Community item, the hit shows the tier, a Verified-only search leaves it out, the download digest matches, the download names the tier, the withdrawn item is not served |
| Served | 6,398 packages: 42 Verified, 6,356 Community |

The job ran every stage itself: export, prechecks, calibrate, review, write,
combine, bundle, publish, check and counts, from 10:17 to 11:55 UTC. Its
journal is `~/baltor-library/daily/2026-09-26-10/journal.jsonl` and its counts
are `counts.json` beside it.

## What changed in the job after this slot

- The export draws every kind a harness picks up in a declared share
  (`--kind-mix balanced`, the default since this afternoon), so the next slot
  is the first with hooks, plugin manifests, rules, subagents, commands,
  protocol server configurations, contract schemas and skills with scripts in
  their shares (S-6.205).
- A package with code passes the format rules when the reviewer reads every
  executable line under the new executable-code criterion; the sandbox-tests
  route stays the Verified route for code.
- The writer tags every approved item with its harness kind and the kinds of
  step it supports, as served attributes (S-6.206), and the counts record
  carries the mix and the tags (`daily_library_release_counts/v2`).

## Limits

- This release was written before the tags: none of its 6,398 rows carries
  `harness_kind` or `step_functions`; the pages place them by their styles.
- The served count is the bundle's item count, checked by one customer
  request; it is not a measurement of serving at 10,000 (S-6.203).

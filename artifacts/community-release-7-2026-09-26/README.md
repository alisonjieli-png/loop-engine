# Community release 7: the first balanced mix and the first tags, 7,806 packages served

Kind: dated record of one catalogue release, published by the daily job's
16:17 UTC slot on September 26, 2026 (roadmap S-6.197, S-6.205 and S-6.206).
The bytes of the release live outside this repository; this record names them
by digest.

| Fact | Value |
|---|---|
| Slot | `2026-09-26-16`, started by cron at 16:17 UTC |
| Export | 2,000 packages drawn in the balanced kind mix: 822 skills (205 with scripts), 246 subagents, 246 commands, 164 rules, 164 instruction files, 122 plugin manifests, 102 hooks, 60 protocol server configurations, 40 marketplaces, 19 code modules and 15 contract schemas |
| Prechecks | 1,529 passed, 471 refused |
| Calibration | the Tactical reviewer (`gemma-4-coding-abliterated`) qualified at 17:22 UTC |
| Review | 128 Tactical calls, 17:22 to 18:38 UTC |
| Write | 1,408 approved, 72 rejected, 49 left out, 18:57 UTC |
| Snapshot | `~/baltor-library/release-folders/daily-2026-09-26-16`, 7,806 approved rows (7,764 Community, 42 Verified) |
| Bundle | digest `00023d3d08132e655dfdc657fd08dfd028a62418049dfd9be03da1b4c13d67bc`, 7,806 items, 28,572 files, 105,166,563 bytes |
| Release | `add9254335460d5b87d458f9c448792fe688b4ccd5502f794fde4160dc1caca7`, active at 21:38 UTC |
| Live check | 6 of 6 as a customer: search finds a Community item, the hit shows the tier, a Verified-only search leaves it out, the download digest matches, the download names the tier, the withdrawn item is not served |
| Served | 7,806 packages: 42 Verified, 7,764 Community |

## What the release adds

Approved in this slot, by the kind of file a harness picks up: 597 skills,
214 subagents, 208 commands, 127 rules, 108 instruction files, 81 hooks,
71 plugin manifests, 27 protocol server configurations, 26 marketplaces,
18 code modules and 3 contract schemas. Every approved row carries the
`harness_kind` and `step_functions` served attributes; the step functions of
the slot's approvals are acting 1,153, building 646, verification 478,
analysis 408, writing 342, reviewing 292, operating 285, planning 281,
reasoning 251 and research 197, with 83 items untagged. The tags come from the
rules engine version 1.0.0; version 1.1.0, with better measured precision, is
on the integration tree for the next slots.

## What went wrong on the way, and the repairs

1. The export failed at 16:17 UTC: a code module package named the
   `harness_local` layer, which the harness intelligence rule refuses for
   reusable code. Code modules now travel as the tool kind (main `3a6c5f08`).
2. The prechecks refused the export report at 16:29 UTC because its new
   fields (`mix`, `with_scripts`) were unknown to version one. The report is
   now version two and the reader serves both versions (main `c3db3408`); the
   job checkout moved to that revision and the slot resumed from the prechecks.
3. The publish timed out at 18:59 UTC while uploading the 105 MB archive, and
   the retry at 21:22 UTC stopped because the upload tool never overwrites a
   file. The private publish script now reuses an archive already on the
   volume when its checksum matches the bundle, and sets it aside under a
   dated name when it does not; the second retry published at 21:38 UTC.

The slot took 5 hours 21 minutes from start to served, against a median of
100.6 minutes for the three earlier slots, because of these three stops and
because the machine ran above a load of 60 while the prechecks ran.

## Seed wave 1 in the same folder list

The reviewed folder of seed wave 1 (the owner's Expansion drive as seed
material, S-6.207) was in the folder list, but it added nothing: the Claude
Code reviewer approved 0 of its 197 packages. The reasons are recorded in the
S-6.207 evidence.

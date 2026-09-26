# Community catalogue release 4: 3,276 packages, the first unattended daily run, September 26, 2026

Kind: dated release record for the fourth Community catalogue release and
the first run of the daily job (roadmap S-6.197, S-6.119 and S-6.69).
Bodies stay outside the repository.

## What was published

| Fact | Value |
|---|---|
| Release identity | `04a69e0b18d350889f5a562e8fc40e0be73e263de09bbf210c590b7ffef5cc80`, the eighth release in the store, based on `11a2974d…` |
| Bundle digest | `e8c023e4d6b1c884cc1d13d4b12f334ed4f3bb677c3d977bac52756dd520ff53` (46 MB) |
| Items | 3,276: 42 Verified and 3,234 Community; 1,647 added by this release (import batch 2), 1,629 changed (re-anchored by the combine step), 0 withdrawals |
| Published | 00:58:18 UTC, about a minute after the 46 MB upload; the running service swapped to it at 01:00 UTC on the refresher's next tick (one swap, 1.8 seconds) and the library page lists 3,276 |
| Review | Import batch 2 (2,000 packages, `review-batches/2026-09-26`): the prechecks refused 293 and passed 1,707; the Tactical reviewer qualified on the imported controls in a batch of 12 (after one retry of an incomplete batch answer), then reviewed the 1,707 in 143 calls (142 answered, one `model_identity_mismatch`) over 63 minutes with 9.6 million input and 259 thousand output tokens: 1,647 approved, 29 rejected, 31 left out with reasons |
| Job stages | export (skipped, the batch was exported earlier), prechecks, calibrate, review, write, combine, bundle, then publish and check; the whole run from 23:39 to 01:00 UTC with two restarts before the review, both for defects in the job script |
| Live retrieval check | `live-retrieval-1.json` failed because it ran before the refresher had swapped; `live-retrieval-2.json` passed 6 of 6 for `import_rules_cpp_programming_guidelines_cursorrules_p_026a2f23ba94` |
| Volume | 74 MB of 974 MB used after the uploaded bundle was removed from `/data/incoming` |

## What the run found in the job

1. A symlinked export folder is refused by the review root check
   (`native_root_invalid`); the batch folder was moved under the day's name.
2. The exclusion reasons carried spaces and were word-split into
   arguments; they now carry none.
3. An incomplete batch calibration (one control without a verdict) ended
   the day; the job now asks once more, and the retry qualified.
4. The publish command writes every new body to the store before it moves
   the active pointer (about a minute for 1,647 packages), and the Machines
   API exec call gives up in about the same time, so the job reported a
   failure while the command completed on the Machine and the pointer moved
   at 00:58:18 UTC. The publish script now starts the command in the
   background on the Machine and polls the store's active release, so a
   larger release cannot produce the same false failure.
5. The live check must sample an item a read-only request may receive; the
   job now chooses an approved instruction file or skill whose declared
   effects are covered by `reads_fs`.

## How the count moved

93 packages served at 16:38 UTC on September 25; 316 at 22:35; 1,629 at
23:22; 3,276 at 01:00 UTC on September 26. Tactical reviewed 3,323
packages in 279 calls across the night.

## What this does not establish

Every imported package was approved by one family under the full imported
criteria, so all are Community. The serving measurement at 5,000 and 10,000
items (S-6.203) has not been run; this release is the first live point above
3,000 and health reports the view current with a 1.8 second swap. No
customer has yet retrieved one of these packages in their own harness.

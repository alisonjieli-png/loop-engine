# Community catalogue release 5: 4,812 packages, the first slot run with an unattended export, September 26, 2026

Kind: dated release record for the fifth Community catalogue release, the
daily job's run for the 04 slot (roadmap S-6.197, S-6.119 and S-6.69).
Bodies stay outside the repository.

| Fact | Value |
|---|---|
| Release identity | `a7451e0688c0b2cef393a5477c93e34c8e259404f503af1caa698ba5204fdab4`, the ninth release in the store, based on `04a69e0b…` |
| Bundle digest | `4da2faea9253abadbf039530645c7c02106cef73ecc6087ae50fd412c0774b7c` |
| Items | 4,812: 42 Verified and 4,770 Community; 1,536 added by this run, the rest re-anchored |
| Published | 06:18:54 UTC by the job's publish stage, started in the background on the Machine and polled; the service swapped at 06:19:07 UTC (its second swap since the release 36 restart) |
| Run | `daily/2026-09-26-04`: export at 04:38 UTC (2,000 packages from the import run of September 24, the export stage's first unattended run), prechecks 1,630 passed, calibration qualified on a fresh batch of twelve at 04:58 UTC after the first attempt is recorded under `attempt-1`, review in 136 calls over 67 minutes (9.9 million input and 246 thousand output tokens), write 1,536 approved, 50 rejected, 44 left out, combine 4,812, bundle, publish, check, counts, all without a person after the start command |
| Live retrieval check | passed 6 of 6 for `import_rules_fastapi_production_architecture_cursorrules…` (an instruction file a read-only request may receive) |
| Start | The 04:17 UTC cron slot failed to start (the script was not executable and the entry called it directly); the tools are executable, the entry calls `bash`, and this run was started by hand at 04:40 UTC. The 10:17 UTC slot is the first run cron starts itself. |

## How the count moved

93 at 16:38 UTC on September 25; 316 at 22:35; 1,629 at 23:22; 3,276 at
01:00 UTC on September 26; 4,812 at 06:19 UTC. Tactical reviewed 4,953
packages in 415 calls across the night and morning.

## What this does not establish

Every imported package was approved by one family under the full imported
criteria, so all are Community. The serving measurement at 5,000 and 10,000
items (S-6.203) has not been run; the service serves 4,812 with the view
current and a swap of about two seconds, on a 2 GB Machine with the volume
well under a tenth full. No customer has yet retrieved one of these packages
in their own harness.

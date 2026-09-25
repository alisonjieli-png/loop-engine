# Community catalogue release 3: 1,629 packages, September 25, 2026

Kind: dated release record for the third Community catalogue release
(roadmap S-6.119, S-6.196, S-6.197 and S-6.69). Bodies stay outside the
repository.

## What was published

| Fact | Value |
|---|---|
| Release identity | `11a2974d9550779747440697eaeeb32a50c3b239d53dd604a429787caace2306`, the seventh release in the store |
| Bundle digest | `38f2503ed7685b388e4d467301fa6577f9a01d857b0fe81a3c7893787c18b3f1` |
| Content digest | `8a6e4a5269ab7f190fc9dbbe901ceaf0c41dd5d415eb6b13e65799ff9ed50615` |
| Items | 1,629: 42 Verified and 1,587 Community; 1,313 added by this release (the rest of import batch 1), 316 changed (every earlier item re-anchored by the combine step), 0 durable withdrawals; 5,662 files, 19.8 MB in the bundle, 3,553 bodies written to the store |
| Published | 23:22:18 UTC, without a redeploy, by the pipeline `~/.le-ci-tmp/imported-calibration/release3.sh` that waited for the batch review to end (the 20 MB upload took most of the four minutes after the bundle); the release 36 restart at 23:23 UTC then built the view from the store with the same 1,629 items |
| Review | The remaining 1,376 precheck-passed packages of import batch 1, reviewed by the Tactical reviewer under the written imported criteria in 115 calls of 12: 1,313 approved, 46 rejected, 17 left out with their reasons (`reviewed-2026-09-25/imported-batch001-rest/writer-report.json`) |
| Source folders | `release-folders/community-release-3` (combine report: 1,981 rows, 1,629 approved, 267 relabelled sources) from `reviewed-2026-09-25/community-overnight-v2`, `imported-pilot-1` and `imported-batch001-rest`, on the starter base |
| Live retrieval check | `live-retrieval-1.json`: passed 6 of 6 for `import_command_cloud_recon_6ca8b0cce02a` (an imported instruction file a read-only request may receive; digest `e71445ce…`): search, the Community label, the Verified-only filter, the download digest, the tier header, the withdrawn item |

## How the day's count moved

93 packages served in the afternoon (release 1, 16:38 UTC), 316 after the
licence policy of Fly release 35 (release 2, 22:35 UTC), 1,629 after batch
1's review (this release, 23:22 UTC). Tactical reviewed 1,616 packages tonight in 136 calls
(20 pilot, 115 batch, and the calibration), about 52 seconds a call.

## What this does not establish

Every imported package here was approved by one family (Tactical, Google)
under the full imported criteria, so all are Community. The serving
measurement at 1,000, 5,000 and 10,000 items (S-6.203) has not been run;
this release is the first live point above 1,000 and health reports the
view current. No customer has yet retrieved one of these packages in their
own harness; the check above is engineering's own account.

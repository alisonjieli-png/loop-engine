# Session handoff, September 25, 2026, night

Kind: dated handoff. It records what went live between 21:00 UTC and the
end of the session, the owner's directions of the evening and the decisions
made under them, what is running unattended, and the order of the next
steps. The [ninety-day plan](NINETY-DAY-PLAN-2026-09-25.md) of the same
evening holds the measured cycle times and the dated marks. The roadmap
remains the task authority.

## What is live

| Fact | State at the end of the session |
|---|---|
| Fly release 35 | `2cc06eb7`, image `sha256:2778dce4…`, live 22:22 UTC: the imported-package review reader (S-6.196) and the wording reconciliation (S-6.181). Record [`pilot-release-35.json`](../../artifacts/architecture-audit-2026-09-19/pilot-release-35.json). |
| Fly release 36 | started by the train for `cd079477` (the request screening station, the text model engine, the decision red team and the conformance manifest); its record is the next session's first check if the train's log at `~/.le-ci-tmp/release-36-train.log` does not say it is live. |
| Catalogue | release `c7208dc8…` since 22:35 UTC: 316 packages (42 Verified, 274 Community, 223 of them imported), published without a redeploy; the customer retrieval check passed 6 of 6 ([record](../../artifacts/community-release-2-2026-09-25/README.md)). The host file's `license_policy` accepts MIT, Apache-2.0, BSD, ISC, CC0 and CC-BY since the release 35 restart. |
| Public base | `https://baltor.ai` since the release 34 restart. |
| Revenue | 0 paying subscribers, 0 customers, 2 checkout sessions started and none finished, 18 accounts (9 confirmed), measured with a counts-only script through the operator credentials. |

## The owner's directions of the evening, and the decisions

1. "Take a step back" over the next 90 days towards 100,000 in monthly or
   yearly revenue, with the measured time of each kind of step and
   aggressive efficiency: the [ninety-day plan](NINETY-DAY-PLAN-2026-09-25.md)
   (artifact "Ninety-Day Plan"), recorded on main `5b3bfd6d` with roadmap
   steps S-6.199 to S-6.204 and the dated library marks (10,000 served by
   October 5, 30,000 by October 31, 100,000 by December 24).
2. "Change the review process, maybe make the review before publication
   simpler, but allow an ongoing feedback based process to unpublish
   certain things, flag them for additional review": decided as the
   "Approval of intelligence items" row of the AGENTS.md decision table
   (publish after prechecks, pinned provenance and one four-question
   screening call; a report button, a nightly rescan, a weekly upstream
   check and second-family reviews withdraw or upgrade afterwards). The
   screen profile is on main `a0599691`; the rest is S-6.199.
3. "Use your best judgement to resolve all of these 'your decisions'": every
   row of the decision table is now engineering's decision with its reason,
   under a new "Delegated decisions" row; changed rows are Approval of
   intelligence items, Price (annual Baltor Pro at 290), Hosting plans
   (volume and memory within the allowance), A library of 100,000 harness
   files (dated marks) and Library tiers.
4. The decision red team of the owner's CC0 modern slavery write-up
   (S-6.198): on main `9f791ca1` with three recorded runs
   ([case study](../../case-studies/decision-red-team-modern-slavery/README.md)).
   The rules engine 15 of 15; Tactical (Gemma 4) 14 of 15 with the policy's
   patterns in the state and 9 of 15 with one recorded failure with them
   withheld (it refused the worker seeking help instead of referring her);
   the station held every model-answered request; Jev is not answered
   until a TypeSafe credential is in the environment (`env:TYPESAFE_API_KEY`).

## Running unattended at the end of the session

- The Tactical review of the remaining 1,376 precheck-passed packages of
  batch 1 (`~/.le-ci-tmp/imported-calibration/batch001-rest.log`, ledger
  `~/baltor-library/reviewed-2026-09-25/imported-batch-001/ledger-tactical.jsonl`,
  identities `identities-batch001-rest.txt`). When it ends: write the
  reviewed folder with `tools/write_reviewed_catalogue.py --identities-file`,
  combine, bundle with the accepted licence list, publish as
  community-release-3 through `baltor-private/tools/publish_catalogue.sh`,
  wait 75 seconds, run the live retrieval check with a read-only imported
  item and a fresh request identity, record it.
- The release 36 train and the browser nightly (run 36199031805) on
  `cd079477`.

## Next steps, in order

1. Record release 36 (`pilot-release-36.json`, its README, the client and
   server map) and update the board.
2. Publish community-release-3 from tonight's batch review; record it.
3. Measure the four-question screen against the pilot's ten rejections on
   Tactical (`community_campaign.py review --content-profile screen`
   on the same 240 identities into a separate ledger); ship it as the
   Community screen only if it rejects every one.
4. Dry-run `baltor-private/tools/daily_library_release.sh 2026-09-26`
   (export, prechecks, calibrate, review, write, combine, bundle), then
   `--publish`, then the cron entry every six hours (S-6.197).
5. Build the report route, flag records and withdrawal rules (S-6.199),
   then the serving measurement at 1,000, 5,000 and 10,000 (S-6.203).
6. Continuous integration sharding and the pre-push hook (S-6.200); the
   page and demo generators (S-6.201) starting with the red-team page on
   its own hostname; the quickstart nightly checks (S-6.202); the weekly
   number (S-6.204).

## Traps found tonight

- A shell redirect or a Write into the `/tmp` scratchpad creates an empty
  file with no error: keep scratch files under `~/.le-ci-tmp/<topic>/`.
- The endpoint adapter refuses an output ceiling below the binding's
  declared maximum; a text call without an allocation asks for the maximum.
- The live retrieval check reused one request identity across runs and
  received 503 `meter_commit_unknown` on purpose; it now derives the
  identity from the item and the time. An item that declares effects beyond
  `reads_fs` cannot be received by a read-only request.
- The continuation status builder refuses a step that is not in a
  workstream and in `launch_order` or `improvement_order`.
- The gateway kept only four provider access codes; a missing credential
  now passes through as `configured_secret_unavailable`.

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
| Fly release 36 | `cd079477`, image `sha256:b1198bff…`, live 23:23 UTC: the request screening station, the text model engine kind, the rules engine's screening answerer, the gateway's credential passthrough and the decision red team; nothing a visitor sees changed. Record [`pilot-release-36.json`](../../artifacts/architecture-audit-2026-09-19/pilot-release-36.json). |
| Catalogue | release `a7451e06…` since 06:19 UTC on September 26: 4,812 packages (42 Verified, 4,770 Community), published by the daily job's 04 slot, the first run with an unattended export ([record](../../artifacts/community-release-5-2026-09-26/README.md)). Before it, `04a69e0b…` (3,276) from 01:00 UTC, the job's first run on batch 2 ([record](../../artifacts/community-release-4-2026-09-26/README.md)). Before it, `11a2974d…` (1,629) from 23:22 UTC ([record](../../artifacts/community-release-3-2026-09-25/README.md)) and `c7208dc8…` (316) from 22:35 UTC ([record](../../artifacts/community-release-2-2026-09-25/README.md)). Every release passed the customer retrieval check 6 of 6. The host file's `license_policy` accepts MIT, Apache-2.0, BSD, ISC, CC0 and CC-BY since the release 35 restart. |
| The four-question screen | measured on the 240-package pilot: it approved 7 of the 10 packages the full imported review rejected, so the one call before publication asks the written criteria; recorded on main `ba0d6245` in the decision row, the plan record, the screen sheet and S-6.199. |
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

## The daily job's first run, and what runs unattended now

The daily job ran on import batch 2 (2,000 packages, moved to
`~/baltor-library/review-batches/2026-09-26`) from 23:39 UTC: prechecks
(1,707 passed), calibration (qualified after one retry of an incomplete
batch answer), review (143 Tactical calls, 63 minutes), write (1,647
approved, 29 rejected, 31 left out), combine (3,276 approved), bundle
(46 MB), publish (release `04a69e0b…` at 00:58 UTC, served from 01:00 UTC)
and the customer check 6 of 6 ([record](../../artifacts/community-release-4-2026-09-26/README.md)).
Four defects in the job were fixed on the way and are listed in that record;
the publish script now starts the publish in the background on the Machine
and polls the store's active release.

A cron entry now runs the job every six hours (`17 */6 * * *` in the
machine's Eastern time: 04:17, 10:17, 16:17 and 22:17 UTC) with `--publish`,
`REPOSITORY=/home/username/.le-import-review-20260925` (a detached
worktree on main; move it to a permanent checkout before that worktree is
retired) and `RUN_FOLDER=/home/username/.le-library/import-2026-09-24/run-1`
(the import run whose `leads.jsonl` the export stage reads). Each slot has
its own run name, `<date>-<hour>` in UTC (for example `2026-09-26-10`), so
every slot exports and reviews its own 2,000 packages; the reviewed records
carry the calendar date. Its log is `~/.le-ci-tmp/daily-cron.log`; each
run's journal is `journal.jsonl` under `~/baltor-library/daily/<run>/`. The
first cron slot at 04:17 UTC on September 26 failed to start because the
script was not executable and the entry called it directly; the tools are
executable now, the entry calls `bash`, and the 04 slot was started by hand
at 04:40 UTC as the first run of the export stage (2,000 exported, 1,630
passed the prechecks). Its first calibration attempt was incomplete and the
retry reused the first attempt's ledger, so it re-asked only the one
missing control on its own, where this reviewer is known to fail; the retry
now writes its own ledger and asks the whole batch of twelve again, and the
fresh attempt qualified at 04:58 UTC (the first attempt is kept under
`daily/2026-09-26-04/attempt-1`).

## Next steps, in order

1. Read the first cron runs; raise `EXPORT_TARGET` and give each six-hour
   slot its own run name once the export stage is proven (S-6.197).
2. Build the report route, flag records and withdrawal rules (S-6.199),
   then the serving measurement at 1,000, 5,000 and 10,000 (S-6.203); the
   live service already serves 1,629 with the view current.
3. Continuous integration sharding and the pre-push hook (S-6.200); the
   page and demo generators (S-6.201) starting with the red-team page on
   its own hostname; the quickstart nightly checks (S-6.202); the weekly
   number (S-6.204).
4. Jev runs when a TypeSafe credential is in the environment as
   `TYPESAFE_API_KEY`; an Ollama Cloud model when the weekly allowance
   returns; Codex reviews from September 29.

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

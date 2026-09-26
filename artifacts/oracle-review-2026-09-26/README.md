# Oracle second look of served items, September 26, 2026

This folder records the first real run of `tools/oracle_review_served.py`, the
continuous second look at the items the library serves, and the decisions made
while building it. Roadmap package: oracle-review. The owner asked on
September 26, 2026 for "oracles that can run server side to review our files
and double check them", assuming the model access already wired up on the
server, and that nothing breaks. The server that runs jobs is the owner's
machine. The Fly Machine makes no model call and holds no model key, and this
work keeps it that way.

## What runs now

```text
tools/oracle_review_served.py, one run
├── reads the active release bundle (the newest daily bundle with items.jsonl)
├── finds each served item's reviewed folder and the licensed import export it
│   was reviewed from, and rebuilds the review request from that export; the
│   rebuilt request must name the reviewed package digest (the exact bytes the
│   first reviewer read) and is judged under the current criteria
├── samples up to N items not yet double-checked, oldest first, every harness
│   kind in turn (default 24)
├── chooses one reviewer for each item in the preference order given: never the
│   producer's family, a family not yet on record first, and only a reviewer the
│   daily calibration qualified within the last 36 hours
├── runs the deterministic prechecks again in this process, with no model call
├── asks the reviewer through the review panel the way the daily job does: the
│   campaign's review command, every other installation excluded, batches of
│   twelve, a call ceiling and a token ceiling for the run
├── appends every verdict, and every attempt without one, to the oracle ledger
├── writes each rejection and each precheck refusal as a withdrawal candidate
└── writes an approval by a second family as an upgrade candidate
```

The tool withdraws nothing, publishes nothing and changes no tier. The
withdrawal path of the feedback-withdrawal package consumes the withdrawal
candidates; the full review (a Verified folder written by
`tools/write_reviewed_catalogue.py --tier verified` naming both reviewers)
consumes the upgrade candidates.

Records, all under `/home/username/baltor-library/oracle/`:

| Path | Record | Meaning |
|---|---|---|
| `review-ledger.jsonl` | `oracle_review_ledger_row/v1`, one a line | Which served digests were double-checked, by which reviewer and family, with which verdict, reasons, findings and panel call. An item is double-checked when a row holds `approve` or `reject` at its served digest. |
| `withdrawals/IDENTITY--DIGEST12--STAMP.json` | `oracle_withdrawal_candidate/v1` | One rejection or precheck refusal of a served item, with the identity, served digest, package digest, tier, the first review on record, the reviewer and family, the decision (`reject` or `precheck_refused`), reasons, findings and the panel call reference. `status` is `candidate`. |
| `upgrades/IDENTITY--DIGEST12--STAMP.json` | `oracle_upgrade_candidate/v1` | An approval by a family that had not judged the item, beside the first family's approval, so the full review can make the item Verified. |
| `runs/RUN/` | `oracle_review_run/v1` report, identities asked, panel ledgers and logs | One folder a run. The report counts the served items, every skipped reason with examples, the sample, the calls and tokens, and every record written. |
| `review-journal.jsonl` | one line a stage | Written by `oracle_review.sh`, the same shape as the daily job's journal. The parallel variations job keeps its own journal and lock beside it. |

The withdrawal file shape the feedback-withdrawal package is expected to read:
every file matching `oracle/withdrawals/*.json` whose `record_type` is
`oracle_withdrawal_candidate/v1`, keyed by `identity` and `digest` (the served
digest of the active bundle), with `decision`, `reasons`, `findings`,
`reviewer.installation_id`, `reviewer.family`, `first_review`, `call_ref`,
`panel_ledger` and `run_id`. The consumer records its own decision elsewhere;
the oracle never edits or removes a candidate file.

## The smoke run: 12 imported items on the Tactical reviewer

Run `oracle-smoke-2026-09-26-2`, started from this worktree at revision
`76e14faa` plus the new tool, with `--sample 12 --call-ceiling 4
--authorize-model-calls`, reviewer `tactical.gemma-4-coding-abliterated`
(family google), qualified by the daily calibration of slot 2026-09-26-10.

| Count | Value |
|---|---|
| Served items in the active bundle `daily-2026-09-26-10` | 6,398 |
| Skipped, reviewed folder not found (starter items) | 42 |
| Skipped, candidate export not found (original items of September 25) | 51 |
| Sampled | 12 (all from `reviewed-2026-09-25`, catalogued on September 25, the oldest served) |
| Harness kinds in the sample | marketplace, plugin_manifest, instruction_file, skill, subagent, command, protocol_server_configuration, rules, contract_schema (9 kinds in turn, then the oldest kinds again) |
| Precheck refusals (no model call) | 0 |
| Panel calls | 1 (one batch of twelve; the second call the ceiling allowed was not needed) |
| Charged tokens | 82,609 as reported by the endpoint |
| Verdicts: approve, reject, none | 11, 1, 0 |
| Withdrawal candidates written | 1 |
| Upgrade candidates written | 0 (the first review was by the same family, google, so `second_family` is false on every row) |
| Stop reason | completed |

Ledger: `/home/username/baltor-library/oracle/review-ledger.jsonl`.
Run folder: `/home/username/baltor-library/oracle/runs/oracle-smoke-2026-09-26-2/`.

The one rejection is `import_command_design_plan_3a0e3a61e8b9` (a command, served digest
`a28b44a3d3ee34ca1e14fedd54e23091425378d8f265cb26373b983a9bf96341`). The
reviewer's reason: "The command instructs the agent to run a python script
which implies filesystem reads to resolve paths, but the declared effects only
list 'spawns_process'." Its finding is blocking under the criterion
`declared_effects`. The withdrawal candidate is
`withdrawals/import_command_design_plan_3a0e3a61e8b9--a28b44a3d3ee--20260926T125733Z.json`;
the item stays served until the withdrawal path decides. Every row records
`same_criteria_as_first_review` false, because the imported criteria changed at
revision `edcc77a3` after the first review; the second look judged the same
bytes under today's criteria.

The first attempt, `oracle-smoke-2026-09-26`, asked nobody: all 12 sampled
items were skipped as `request_rebuild_mismatch`, because the tool then bound
the rebuilt request on the reviewed request digest. That digest covers the
criteria and the reviewer instructions of the day, and the job checkout moved
to revision `edcc77a3` at 08:15 Eastern time, after the 07:52 write of the
newest reviewed folder; that revision changed the imported criteria, the review
sheet and the instructions. Every reviewed row therefore names a request digest
that today's code cannot rebuild. The tool now binds on the reviewed package
digest, which names the exact bytes, and records on every row whether the
current criteria are the first review's (`same_criteria_as_first_review`). The
failed attempt's report stays at `runs/oracle-smoke-2026-09-26/report.json`.

## The hourly job

`/home/username/baltor-private/tools/oracle_review.sh` (journaled, one run at
a time under a lock, exits with a journal note when the tool is not in the job
checkout yet) and this cron entry, installed on September 26, 2026:

```text
40 21,22,23,3,4,5,9,10,11,15,16,17 * * * DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus REPOSITORY=/home/username/.le-library-job bash -lc 'bash /home/username/baltor-private/tools/oracle_review.sh 24 >> /home/username/.le-ci-tmp/oracle-review-cron.log 2>&1'
```

The hours are machine time (America/New_York), the same clock as the daily
job's entry `17 */6 * * *`, so the two entries keep their distance when
daylight time ends. While Eastern daylight time holds they are 01:40, 02:40,
03:40, 07:40, 08:40, 09:40, 13:40, 14:40, 15:40, 19:40, 20:40 and 21:40 UTC:
hourly at minute 40 except the two hours after each daily slot starts. The
script guards the same hours itself. The cap is 24 items a run, at most 8 panel
calls and 4,000,000 charged tokens a run. The log is
`/home/username/.le-ci-tmp/oracle-review-cron.log`.

The job checkout `/home/username/.le-library-job` holds revision `edcc77a3`
and does not hold the tool until the integrating session fast-forwards it with
`main`; until then each hourly run writes one journal line and exits.

## Decisions made and their reasons

| Decision | Reason |
|---|---|
| The cron asks the Tactical reviewer only. | It is the one reachable reviewer today: the Ollama Cloud allowance is spent until October 1, 2026 at 13:00 Eastern, Codex is available from September 29, and the Claude Code command line shares the session's subscription and is for small numbers. The tool takes `--reviewer` more than once, in preference order, and prefers a family not yet on record, so adding Codex or an Ollama Cloud reviewer is one flag in the script. |
| A family already on record may look again (`second_family` false on the row). | Every imported item was approved by the google family, and no other family is reachable today. A second look by the same model in a different batch still surfaces rejections, which the withdrawal path needs now. `--second-family-only` turns this off. An approval by the same family is never an upgrade candidate. |
| The second look binds on the reviewed package digest, not the request digest. | See the smoke run: the request digest changes with the criteria of the day. The bytes are what a customer receives. |
| A reviewer is asked only when the daily calibration qualified it within 36 hours. | The daily job refuses to review with an unqualified reviewer; the oracle keeps that rule without spending seven calibration calls of its own. |
| A precheck refusal becomes a withdrawal candidate with no model call. | The prechecks are deterministic and cheap; a served item that fails today's rules is exactly what a second look should surface. |
| An item is set aside after three attempts that reached a reviewer and produced no verdict. | A repeatedly unanswerable item must not block the queue; the rows stay in the ledger, and a reviewer that was never asked (an outage) does not count. |
| Starter items and the original items of September 25 are skipped, with counts. | Their review requests cannot be rebuilt from a licensed import export; reading a native candidate folder and the starter catalogue is planned work. |

## Checks

- `tools/test_oracle_review_served.py`: 10 checks over fixture folders (a
  three-package export, a reviewed Community folder the real writer wrote from
  a real panel ledger, a bundle the real bundle tool wrote) and a scripted
  fixture reviewer answering batch prompts. Known-wrong cases: a reviewer of the
  producer's family is never chosen, an unqualified reviewer is never asked, a
  same-family approval writes no upgrade candidate, a double-checked digest is
  not sampled again, a run without model call authority writes nothing.
- The owning suites `test_write_reviewed_catalogue_imported.py`,
  `test_write_reviewed_catalogue.py`, `test_candidate_review_imported.py` and
  `test_candidate_review_batching.py` still pass with it: 81 checks, all passing, in 23.6 seconds.
- The full `tools` discovery that continuous integration runs did not finish
  in this session: four discoveries from parallel agents shared the machine and
  it was stopped after 62 tests. The first eight modules, run on their own: 126
  tests, 3 errors, all three in `tools.test_architecture_audit.StructureTests`,
  each `FileNotFoundError` for
  `tools/architecture_report/node_modules/elkjs/package.json`, a node module
  the fresh worktree does not hold; unrelated to this package.

## Planned, not built

- Original items (the 51 served rows of `reviewed-2026-09-25/community-overnight-v2`)
  and the 42 starter items: their candidate folders are not licensed import
  exports, so the oracle counts them under `candidate_export_not_found` and
  `reviewed_folder_not_found`.
- The withdrawal itself: the feedback-withdrawal package's path reads the
  candidate records.
- The Verified folder from an upgrade candidate: the full review, run by hand
  or by a later job, from both ledgers.
- Reviewers of other families in the cron: Codex from September 29 and Ollama
  Cloud from October 1, each first qualified by a calibration.

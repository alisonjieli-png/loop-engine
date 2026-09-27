# Factory scheduling and economics of the library job

Kind: dated research record with a working increment, September 26, 2026.
It reports what the daily job's own records show, compares operating
designs, and names the two operator tools it adds. It changes neither the
daily job nor the live service, and the [roadmap](../roadmap/roadmap.yaml)
remains the task authority.

Package factory-economics of the research wave of that day: what each stage of the daily library job costs for each admitted
package, how busy the review server is, how far the stock goes, and which
operating design reaches 10,000, 30,000 and 100,000 served packages soonest
without breaking the review rules or the host.

The numbers come from one record, written by the new measurement tool over
the job's own journals and ledgers at 21:40 UTC, after the 16 UTC slot
finished:
[factory-report-2026-09-26T214010Z.json](../../artifacts/factory-economics-2026-09-26/factory-report-2026-09-26T214010Z.json)
with its [plain table](../../artifacts/factory-economics-2026-09-26/factory-report-2026-09-26T214010Z.md).
The first report of 17:10 UTC, written while that slot was running and
before the tool's corrections, stays beside it, with the queue plans of both
times, in the same [folder](../../artifacts/factory-economics-2026-09-26/README.md).

## Decision in one paragraph

The review server is busy 15.0 percent of the six-hour cadence, a clean slot
takes 105.4 minutes by the stage means, and three of the four slots of
September 26 needed a person to restart them. The binding limits on the way
to 100,000 are not review speed: they are the stock (a ceiling of 43,891
served packages at the measured yield), the serving host (10,000 today, the
gate of the 1 GB volume and the unpaged listing; 25,000 on the 2 GB Machine
once the volume is extended), and the supply of candidates that another model
family can review. The chosen increment is a slot queue that runs the
unchanged daily job back to back, stops at the stock and at a declared
serving capacity, moves a failed calibration aside and runs it again at most
three times, stops for a person on every other failure, and refuses to start
beside a daily job it did not start. It raises the planned rate from 6,040 to
about 20,000 approved packages a day while the stock and capacity allow, and
it turns the two measured causes of lost time that a re-run can clear into
recorded, bounded actions.

## A. Current reality

What exists, what is enabled, what is deployed and what is only documented,
as read on September 26, 2026 between 16:50 and 21:45 UTC.

```text
Daily library job (private: /home/username/baltor-private/tools/daily_library_release.sh)
├── Trigger: cron at minute 17 of every sixth hour, machine time (04, 10, 16, 22 UTC)
├── Stages, each with a done marker so a restart skips finished work
│   ├── export       import store to a review batch of EXPORT_TARGET (default 2,000), 15 per repository
│   ├── prechecks    deterministic refusals, no model
│   ├── calibrate    seven or eight calls on known-wrong controls; the job stops when not qualified
│   ├── review       batches of 12 on tactical.gemma-4-coding-abliterated (family google, from the ledger)
│   ├── write        the reviewed Community folder, appended to the folder list
│   ├── combine      the full snapshot of every folder in the list
│   ├── bundle       the release bundle
│   ├── publish      upload and publish without a redeploy, then a 75-second wait
│   ├── check        live retrieval as a customer; rollback on failure
│   └── counts       daily_library_release_counts, written only after the live check
├── Journals: /home/username/baltor-library/daily/SLOT/journal.jsonl, ledgers, counts.json
└── Beside it on the same review server
    ├── oracle second look, hourly at minute 40 except the two hours after each cron slot start
    │   (the guard reads the machine hour), at most eight calls a run
    └── the overnight generation batch (complete since 11:54 UTC)
```

Observed in the journals:

| Slot | First run (UTC) | Late start | Wall | Stops that needed a person | Approved |
|---|---|---|---|---|---|
| 2026-09-26 | 23:25 on September 25 | not scheduled | 96.3 min | prechecks failed, calibration failed to run, not qualified, publish failed and was finished by hand without a stage note | 1,647 |
| 2026-09-26-04 | 04:38 | 21.4 min (the cron log holds one start that failed with `Permission denied`) | 102.7 min | not qualified after the in-job retry | 1,536 |
| 2026-09-26-10 | 10:17 | none | 98.6 min | none | 1,586 |
| 2026-09-26-16 | 16:17 | none | 321.5 min | export failed and prechecks failed (contract drift); the publish timed out with an unknown outcome, and its re-run at 21:22 failed because the upload does not overwrite a file already on the host | 1,408 |

The 16 UTC slot was the first balanced export (every harness file kind in
one export of 2,000). The prechecks refused 471 of its items against 370 and
340 in the two slots before it, the review took 76.1 minutes against 66.6
and 64.2, and it approved 1,408, a yield of 0.704 for each exported
candidate against 0.795 for the three earlier slots. Its publish finished at
21:38 UTC and its counts record says the live check passed; its bundle
(`00023d3d`) holds 7,806 packages, which this record takes as the served
count from then on.

Stage means over the three most recent slots, with every stage a person
restarted left out because its minutes hold the wait for the repair, in
minutes: export 0.4, prechecks 16.2, calibrate 1.1, review 69.0 (of which
15.6 is the review's own startup, when the panel rebuilds every request),
write 15.3, combine 0.2, bundle 0.2, publish 3.0, check 0.0, counts 0.0;
105.4 in all. The review server's busy time is 54.1 minutes a slot: 2.019
seconds an item, 23.8 seconds a call of 12, 1,782.9 items an hour of busy
time, 7,309.0 reported tokens for each approved package. The yield over the
three slots is 0.755 approved for each exported candidate (4,530 of 6,000),
and 94.0 percent of reviewed packages were approved (4,530 of 4,819).

Waste in the journals: seven failed stage notes, two calibration stops that
said the reviewer was not qualified, one calibration attempt moved aside by
hand into `attempt-1` (35.4 seconds of review server time), 21.4 minutes of
late start, 5.98 minutes a person spent publishing and checking the first
slot by hand, 242.97 minutes inside restarted stages (160.87 of them the 16
UTC publish), six unanswered review calls, 153 items left without a verdict,
and no slot lost, because a person restarted every stop.

The overnight generation batch (10,000 ideas, complete) produced 8,904
candidates; the Tactical lane wrote 8,495 of them in 14,494 dispatches (4,974
dispatches were repeats of an idea, 1,020 answers had the wrong shape). A
generation call took 5.7 seconds alone and 23.0 seconds when it landed inside
a review window (286 calls), which is one review call's length: the server
answers one request at a time. Those 8,904 candidates wait for a reviewer of
another model family; Ollama Cloud's weekly allowance is spent until
October 1 and Codex returns on September 29.

The stock: 58,787 stored candidates, 10,000 exported, 991 not reviewable by
the newest export's count, 47,796 eligible. Simulating the export policy (at
most 15 from each repository per export, 2,000 per export) over the candidate
index by repository gives 18 full exports (36,000 candidates), then 1,791,
then about 300 an export, because the rest sits in a few large repositories;
45,568 are drawable within 80 exports.

Enabled and deployed: the fixed cadence job, its publish path, and the served
catalogue of 7,806 packages by the 16 UTC slot's checked publish. Documented
only: the plan's dated marks in the
[decision table](../../AGENTS.md#decisions-that-stand-until-the-owner-changes-them)
(10,000 by October 5, 30,000 by October 31, 100,000 by December 24, 2026),
where each mark waits for the serving measurement at that size, not for a
date; the queue's capacity gate is that rule in code. Tested before this
package: nothing measured the factory as a whole.

## B. First principles

- **User outcome.** More approved, served and working packages each day, each
  reviewed by a model family that did not produce it, never more than the host
  can serve.
- **Essential information.** The stock by repository, the clean stage times,
  the review server's busy time, the yield, and the serving capacity.
- **Required effects.** Starting the unchanged daily job, which makes its own
  model calls through the review panel and publishes through the existing
  path. The scheduler itself makes no model call and approves nothing.
- **Constraints.** One review in progress on the Tactical server. A producer
  family never approves its own output; the owner added on September 26 that
  every model can take any role and the factory adjusts roles for throughput
  and accuracy, which makes measured throughput per lane and family an input,
  not a report, so the report reads the lane and its family from the ledger.
  Infrastructure within 50 dollars a month. No model spending beyond the
  recorded lanes. An external effect whose outcome is unknown is inspected,
  never repeated blindly.
- **Acceptance.** Approvals a day up, no slot lost to a stop a re-run can
  clear, no publish past the declared capacity, never two daily jobs at once,
  never a repeated publish.
- **Is a model needed?** No. Scheduling is arithmetic over measured times, and
  the qualification of the reviewer stays inside the job.

## C. Alternatives

Screened at the level of the package's main decision: how to operate the
factory. Deeper work went only where it changed the decision.

1. **Four fixed slots (present).** Simple and proven; the reviewer sits idle
   85.0 percent of the cadence, and every stop waits for a person. A stuck
   publish is carried by the next slot's snapshot, which is also a publish
   made while the earlier outcome is unknown.
2. **Back-to-back queue with stock and capacity gates (chosen).** Start the
   next slot a margin after the last one finished; stop at the stock, at the
   serving capacity, and at any stop a re-run cannot clear.
3. **Pipelined queue with work-in-progress limits per stage.** Start the next
   export and prechecks while the previous review runs. Saves about 16.6
   minutes a slot more, but the next combine would then rely on predicted
   timings to include the previous reviewed folder; a late write would publish
   a catalogue without it.
4. **Persistent review worker.** Keep prepared requests warm to remove the
   15.6 minutes of review startup (21.0 on the balanced export). Needs a
   change inside the review campaign.
5. **Fresh process for each assignment (present inside the job).** Isolation
   is good; the cost is the startup above.
6. **Event-driven runs.** Start a slot when stock, capacity and an idle
   reviewer are all present, like a sensor. Same effect as the queue once the
   queue is triggered by a timer; adds a polling service.
7. **A second Tactical review worker.** Measured against: a call beside a
   review took four times as long, so two review streams share one server.
8. **Resource classes per model family.** Assign import review, generation and
   the oracle to lanes by measured throughput and accuracy, never letting a
   family review its own candidates. Right direction; only one family is
   available until September 29.
9. **Caching prechecks and review requests by item digest.** Prechecks take
   16.2 minutes and the review startup 15.6 minutes of a 105-minute slot;
   caching helps only when the same items come back, which the export's
   exclusions prevent today.
10. **Staged cheap-to-expensive evaluation.** Already present: prechecks
    refuse 15 to 24 percent before any model call.
11. **Adaptive slot size and repository ceiling.** A larger export saves only
    the fixed stages (about 5 minutes a slot by the means); a larger repository
    ceiling after the 18th full export would drain the candidates left in a few
    large repositories faster.
12. **Human escalation only for unresolved stops.** Part of the chosen design:
    re-run what a re-run clears, stop with the job's own last note for the rest.
13. **Backfill between the cron slots.** Keep the cron line and fit queued
    slots into the gap after each cron slot finishes: two slots of 105.4
    minutes and their margins fit in the 254.6 minutes left of each six hours,
    so 12 slots a day against 13.7, with no host change. It needs a guard for a
    cron slot that starts late or not at all (the 04 UTC start failed and ran
    21.4 minutes late by hand) and a margin for slow slots (the balanced
    export's review ran 11 minutes longer).
14. **Do less.** Keep the cadence; the factory is not the limit to 100,000.

## D. External research

Primary documentation read on September 26, 2026. Marketing statements were
not used.

- [systemd.timer manual page](https://man7.org/linux/man-pages/man5/systemd.timer.5.html)
  (page dated August 4, 2026): `OnUnitInactiveSec=` defines a timer relative
  to when the triggered unit was last deactivated. That is exactly the back to
  back rule and a candidate trigger for the queue with `--slots 1`.
- [Ollama frequently asked questions](https://docs.ollama.com/faq):
  `OLLAMA_NUM_PARALLEL` is the number of parallel requests each model
  processes, default 1, and memory scales with it; `OLLAMA_MAX_QUEUE` queues up
  to 512. The Tactical endpoint's serving engine is not documented in the
  repository; the measured queueing matches a server that answers one request
  at a time.
- [Apache Airflow pools](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html)
  (version 3.3.2): pools limit parallelism on sets of tasks with slots and
  priority weights.
- [Dagster sensors](https://docs.dagster.io/guides/automate/sensors) and
  [Dagster concurrency](https://docs.dagster.io/guides/operate/managing-concurrency)
  (version 1.13.24): sensors poll for events with a minimum interval and
  deduplicate runs by run key; pools protect a shared resource across runs.
- [Slurm scheduling configuration](https://slurm.schedmd.com/sched_config.html)
  (version 26.05): backfill starts lower priority jobs only when they do not
  delay the expected start of any higher priority job, and needs accurate time
  limits.
- [GitHub Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency):
  at most one running job in a concurrency group.
- [Little's law](https://en.wikipedia.org/wiki/Little%27s_law), from J. D. C.
  Little, "A Proof for the Queuing Formula: L = λW", Operations Research 9(3),
  1961: lead time equals work in process divided by throughput.
- The serving measurement of September 26, 2026, commit `13347218` in the
  serving-measurement worktree, not yet on `main` at this record's base
  revision `43b421f8`: memory grows linearly with the library; the
  recommendation keeps 2 GB through 25,000 packages, asks for a 3 GB volume
  before 10,000 and 4 GB of memory before 50,000. The listing is not paged:
  the full list of a release-following account is 6.75 MB at 6,398 packages
  and 27.9 MB at 25,592, and a response above the host's
  `maximum_response_bytes` (default 262,144 bytes) is refused, so the list
  already depends on a raised host limit or on the paged listing. This record
  therefore declares 10,000 as today's serving capacity and 25,000 as the
  capacity after the volume change.

## E. Analogies

| Analogy | What transfers | What does not | Experiment that would test it |
|---|---|---|---|
| Manufacturing work in process and a drum that sets the pace (Little's law) | The review is the constraint of a slot (69.0 of 105.4 minutes), yet the fixed release schedule starves it; release work when the constraint is ready | Our other stages share one host processor, so they are not independent stations | Run four queued slots and compare reviewer use with the predicted share of wall time and 13.7 slots a day |
| High-performance computing backfill (Slurm) | Other work on the review server (the oracle, generation) can fill gaps if the queue publishes predicted review windows; queued slots can fill the gaps between cron slots | No preemption, and a review's length varies from 63.5 to 76.1 minutes, so the margin must absorb it | Let the oracle's guard read the queue's plan instead of fixed hours, then compare oracle call latency inside and outside windows |
| Continuous integration concurrency groups (GitHub Actions) | One running daily job at a time as a named group; the foreign-job guard | A pending release must never be cancelled or replaced, unlike a pending build | Start the queue while a cron slot runs and confirm the queue stops with `another_daily_job_is_running` (checked by the fixture) |

## F. Comparable products and projects

| Product | Journey and abstraction | Distribution and maintenance | Fit here |
|---|---|---|---|
| Apache Airflow 3.3.2 | Directed acyclic graphs of tasks, pools with slots | A scheduler service with a database | Documented behaviour fits; a service and a database for one host job is more than the need |
| Dagster 1.13.24 | Assets, sensors with run keys, concurrency pools | A daemon and a web server | Sensors match event-driven runs; the same adoption friction as Airflow |
| Slurm 26.05 | Batch jobs with time limits, backfill | A cluster manager | The backfill rule transfers; the software does not |
| systemd timers | A unit started relative to the last run | Already on the machine | The best trigger to reuse for back to back runs; no stock or capacity gate of its own |
| GitHub Actions concurrency | One running job per group | Hosted | The rule transfers; the job is private and local, so the product does not |

Inference, not documented behaviour: none of these would remove the need for
the stock gate, the capacity gate or the calibration move, because those read
this factory's own records. Reuse decision: keep the job as it is, build the
gates as a small operator tool, and adopt a systemd timer as its trigger in
the next wave instead of writing a daemon. The daily job's command line and
settings (the slot name, `--publish`, `EXPORT_TARGET`, `REPOSITORY`,
`RUN_FOLDER`) are the fixed edge; the cron line and the queue are two
engines that start it, and a backfill engine can join them without a change
to the job.

## G. Comparison and choice

| Design | Measured or computed gain | Risk and cost | Evidence | Verdict |
|---|---|---|---|---|
| Four fixed slots | 6,040 approved a day | Stops wait for a person; idle reviewer | Three recent slots | Baseline |
| Back to back with gates and bounded re-runs | 13.7 slots and 20,630 approved a day by the clean stage means (8.3 slots and 12,479 with the observed walls, restarts included); planned 20,028 a day to the 25,000 capacity | Drains stock sooner; needs the cron line paused while it runs | Report and two plans | Chosen |
| Backfill between cron slots | 12 slots a day, no host change | A late or failed cron start; slow slots | Stage means, cron log | Next wave |
| Pipelined work-in-process limits | About 16.6 more minutes a slot | Publish ordering hazard | Stage times | Later, after a publish lock |
| Persistent review worker | Up to 15.6 minutes a slot | Change inside the campaign | Review startup | Queue |
| Second Tactical worker | None measured | Slows both streams | 5.7 against 23.0 seconds | Rejected |
| Resource classes per family | Unlocks the 8,904 generated candidates | One family until September 29 | Batch status | Next wave |
| Caching by digest | Small today | Invalidation | Exclusions | Queue |
| Adaptive repository ceiling | After 18 full exports the draw falls to about 300 an export; a larger ceiling keeps it higher | Less variety per export | Draw simulation | Queue |
| Do less | None | None | Report | Rejected: the gates are needed at any cadence |

A prototype was not needed for the choice: the gain follows from measured
stage times, and the queue's behaviour is checked on a fixture job and in a
dry run over the real library.

## H. Increment, results and plan

### What was built

- `tools/factory_report.py` writes a dated `factory_report/v1` record and a
  plain table: stage minutes per slot from the done markers, the job's first
  run from the birth time of its own temporary folder (so the 04 UTC slot
  shows a 21.4-minute late start and a 0.37-minute export instead of a
  21.8-minute export), stages a person restarted marked and kept out of the
  means, a gap without a stage note attributed to no stage, the review split
  into startup, calls and tail, review lanes by installation and family read
  from the ledger, reviewer busy time and use, stage seconds and reviewer
  seconds for each approved package, tokens, waste, slots that wrote their
  reviewed folder but stopped at the publish (counted, because the next
  combine carries them), unfinished and abandoned slots, the stock and the
  export policy's draw curve, generation lane throughput inside and outside
  review windows, and the projection with the declared serving capacity, back
  to back both at the clean stage means and at the observed walls.
- `tools/factory_schedule.py` plans and runs the queue: `factory_schedule_plan/v1`,
  `factory_schedule_event/v1` and `factory_schedule_run/v1`. It passes
  `EXPORT_TARGET`, `REPOSITORY` and `RUN_FOLDER` to the unchanged job, starts
  each slot a margin after the previous one really ended, names queued slots
  by date, hour and minute so none takes a cron slot's folder, adds the
  approvals each slot wrote in its counts and shrinks or stops the next slot
  from that actual total, moves calibration files into the next `attempt-N`
  folder before a re-run (the job resumes a ledger it finds), recognises a
  calibration stop only when the verdict is the journal's last note, gives up
  after three calibration stops, stops on any other failure with the job's
  last journal note, never repeats a publish, stops on missing counts, stops
  before a daily job it did not start, refuses more than one unpublished slot
  (the job writes no counts without `--publish`), and refuses `run` without a
  declared serving capacity. `--dry-run` starts nothing.
- 36 checks in `tools/test_factory_report.py` and
  `tools/test_factory_schedule.py`, with the known-wrong case first for each
  guard: a running slot reported as lost, a folder time later than the first
  journal event, a gap given to the next stage, a restart inside a mean, a
  fixed reviewer name, a slot stopped at the publish left out of the rates, a
  plan past the stock, a plan past the serving capacity, a run that trusts
  predicted approvals over written counts, a queued slot in a cron slot's
  folder, a re-run that would resume the failed ledger, an unbounded re-run,
  an older verdict read as a new calibration stop, a queue of unpublished
  slots, and a queue beside a foreign job. Eighteen mutants, each removing
  one guard, were each caught by the named check, and the unmutated copies
  passed the same checks; the
  [mutant script](../../artifacts/factory-economics-2026-09-26/factory_mutants.py)
  and its [result](../../artifacts/factory-economics-2026-09-26/mutants-1.txt)
  are kept with the records.

### Observed results

- The report over the real library ran in 2.3 to 15.1 seconds on the shared
  machine.
- The corrections changed the numbers of the 17:10 UTC report: without them
  the counts stage held 5.98 minutes a person spent publishing by hand, the
  prechecks and calibration means held restart waits, and the back-to-back
  rate would now be taken from walls that include the 16 UTC slot's three
  hours of repairs.
- The plan at today's volume gate (10,000 packages, from the 7,806 served,
  as if the queue replaced the 22:17 UTC cron slot) holds two slots, 2,000 and
  905 candidates, 2,193 approvals in 2.65 hours, and ends at the serving
  capacity.
- The plan at the memory gate (25,000) holds twelve slots, 17,193 approvals
  in 20.6 hours, 20,028.5 a day, and ends at the serving capacity with 25,023
  of the stock left.
- The dry run over the real library printed both commands with the cron
  line's settings and started nothing.
- On the 16 UTC slot the queue would have stopped at the timed-out publish
  with the job's note "External outcome is unknown; inspect state before
  retrying", instead of starting the upload again.

### Projection to 100,000, with its assumptions

Assumptions: the yield stays 0.755 approved for each exported candidate, the
mean of the three recent slots, although the balanced export alone gave
0.704 and every export is balanced from now on; the serving host is extended
as the serving measurement recommends; the stock of 58,787 is all the import
stock there is; generated candidates are reviewed by another family from
September 29 at a yield not yet measured.

1. **Import stock, now to about October 2.** At four slots a day, 10,000 is
   reached on September 27 and the stock ceiling of 43,891 in 6.0 days; back
   to back, 1.7 days at the clean stage means or 2.9 days at the observed
   walls. At the balanced yield the ceiling is 41,454. The volume must reach
   3 GB before 10,000: the 22 UTC slot tonight is predicted to take the
   served count to about 9,316, and the 04 UTC slot of September 27 would pass
   10,000.
2. **Serving gates.** 10,000 is the gate of the 1 GB volume and the unpaged
   listing; 25,000 is the memory gate of the 2 GB Machine; 4 GB before
   50,000; the paged listing and a release retention rule before 100,000.
3. **Beyond the stock.** 56,109 more approved packages are needed, 74,317
   candidates at the measured yield (83,162 at the balanced yield). From
   October 3 to December 24 (82 days) that is 684 approved or 906 candidates
   a day (714 and 1,014 at the balanced yield), about a ninth of the factory's
   present rate of 6,040 approved a day. The limit is supply and cross-family
   review: the source-volume package's new discovery, the owner's drive
   seeds, and generation at 236 candidates an hour of Tactical time, reviewed
   by Codex or Ollama Cloud models.

The review factory is therefore not the constraint for the December 24 mark.
The first constraints are the serving host, this week, and candidate supply
from the first week of October.

### Host settings this needs

- Pause the six-hourly cron line of the daily job while the queue runs, or run
  the queue with `--slots 1` from that line.
- Extend the Fly volume to 3 GB before the 04 UTC slot of September 27, as the
  serving measurement recommends, within the recorded allowance.
- While the queue runs, pause the oracle review's cron line or let its guard
  read the queue's plan: the guard protects only the two hours after each
  cron slot start, and a call beside a review took about four times as long.

## Untouched ideas

- A systemd user timer with `OnUnitInactiveSec=` as the queue's trigger.
- Backfill between the cron slots (alternative 13) as a second engine of the
  queue, with a guard for late or failed cron starts.
- Predicted review windows published for the oracle's guard.
- A publish that checks the host's copy by digest before uploading, so a
  timed-out upload can be finished without a person (the 16 UTC slot waited
  160.87 minutes).
- A publish lock so the pipelined design can overlap export and prechecks.
- Caching of prepared review requests to remove the review startup.
- A larger repository ceiling once full exports end.
- Per-family throughput and accuracy records feeding the dynamic role choice.
- Reading the served count from the newest checked slot's bundle instead of
  an argument.
- Measuring the Tactical endpoint's own parallel setting with two small calls.

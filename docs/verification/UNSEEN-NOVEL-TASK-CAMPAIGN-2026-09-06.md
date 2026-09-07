# Unseen novel-task campaign, 2026-09-06

This is the first campaign in the repository's history where a sealed
population of novel tasks was executed end to end through the engine with no
prior exposure, one attempt per task, and an independent post-hoc audit.

## Question and method

Can the engine solve tasks it has never seen? Ten tasks were authored across
ten domains deliberately different from the five regression shapes: grid
pathfinding, run-length decoding, ledger reconciliation, Josephus ranking,
polynomial hashing, Markdown outline depth, calendar free-minute intervals,
a command state machine, spiral matrix summation, and word-square checking.

Each task has a precise contract with edge cases and rejection rules. The
campaign reused the frozen generalization-probe host machinery exactly: the
same manifest-driven operations, Docker sandbox, and host-only oracle. The
population and all 109 fixed cases were verified against independently
written reference implementations before dispatch, and every evaluator was
shown to reject a deliberately wrong solution.

The default invocation printed the frozen plan with zero model calls. The
live run used the configured `cloud.default` / `deepseek-v4-flash:0731`
route with no invented ceilings, no failover, and one autonomous attempt per
task. No repair, continuation, or operator selection touched any task during
the campaign. Failed tasks would have been recorded as failures.

## Result

| Metric | Value |
|---|---|
| Tasks selected, attempted, and in the denominator | 10 |
| First-attempt host-verified completions | 10 |
| Model calls (complete accounting) | 283 |
| Known input tokens | 7,636,923 |
| Known output tokens | 961,827 |
| Elapsed engine time | 4,903 s |
| Cost | unknown |

Per-task detail: the nine straightforward tasks completed in 15 to 40 calls
and 150 to 474 seconds each. The first task, `grid_path_cost`, required 106
calls and 2,634 seconds; its progress log shows repeated repair loops before
the host verified it.

## Independent post-hoc audit

The audit generated 60 seeded random inputs per accepted solution, beyond
the frozen case set, and compared each candidate against the independent
references. The audit itself found and fixed one defect in its own grid
reference (a crash when the start cell is a wall). One accepted solution was
then invalidated:

- `word_square`: the accepted source raises `ValueError` whenever any word
  is shorter than the list length. The task contract rejects that only when
  the list length exceeds every element length. A 500-input boundary stress
  found 109 inputs where the contract-correct answer is `False` and the
  candidate raises `ValueError` instead. The engine-accepted artifact is
  therefore not correct for its full prompt, exactly like the earlier Sales
  case.

The other nine accepted solutions passed all 540 audit inputs.

## Honest reading

Observed: ten novel-by-construction tasks were all completed on the first
autonomous attempt, with complete call and token accounting, and nine of the
ten accepted solutions survived an independent random-input audit.

Inferred: the engine can solve text, data, algorithmic, and structural
tasks of roughly this size and precision without prior exposure, using real
model calls and independent host verification.

Not established: correctness beyond the sampled audit inputs; performance on
tasks outside this size band; any claim that these tasks are outside model
pretraining (novel to this repository is not novel to the model); unattended
operation (the batch was started by an operator, though no task outcome was
directed); and speed (2,634 seconds on the hardest task).

Known failure: one of ten accepted solutions is invalidated for its exact
prompt. The false-acceptance rate on first-verification is therefore 10
percent on this population, and 90 percent survived the independent audit.

The population, campaign, and audit modules are
`examples/25_host_runtime/novel_task_population.py`,
`novel_task_offline_check.py`, `novel_task_campaign.py`, and
`novel_task_audit.py`. Evidence lives in `/tmp/novel-campaign-20260906/`
(report, per-task outcomes, frozen population) and
`/tmp/novel-campaign-audit.json`. The tasks in this population must not be
reused as untouched evidence for future runs.

## Corrections recorded on 2026-09-07

The execution-verified review in
[`CODE-REVIEW-2026-09-07.md`](CODE-REVIEW-2026-09-07.md) rechecked this
campaign. Everything above is left as written; the following corrects it.

Three prompts contradicted their own hidden cases. The `grid_path_cost`
prompt said period-separated cells while every case used commas; the model
failed five observations parsing on periods and succeeded on the sixth after
switching to commas, at a cost of 106 calls. The `calendar_slots` prompt
bounded the day at minute 1439 and required an error for times outside it,
while two cases required `24:00` to be accepted; one failed observation. The
`state_machine` prompt allowed any optionally signed integer while one case
required an error for a leading zero; one failed observation. Together these
three tasks took 172 of the campaign's 283 calls. Their accepted solutions
satisfy the cases by contradicting the prompt text, so by the standard this
report applies to `word_square` they are not correct for their exact prompts
either; here the defect is on the case side.

The offline references were not independent of the cases: they split on
commas, accepted `24:00`, and refused a leading zero, so the check could not
have caught the three contradictions.

The `word_square` invalidation rests on an order-dependent reference:
`ref_is_word_square(['ab', 'a'])` returns `False` while
`ref_is_word_square(['aa', 'a'])` raises `ValueError`, the same shape with two
verdicts. The nine audit mismatches in `audit.json` (60 cases per task) are
the inputs where an early column mismatch preempts the short-word check. No
saved record holds a 500-input stress or 109 mismatches. The 10 percent
false-acceptance figure is therefore not established by this evidence; the
prompt was ambiguous and the reference inconsistent.

Each task ran with its own runs directory, so no task could see another's
stage records or region evidence; the campaign measured solving without
cross-task learning by construction.

The version 2 variation lives beside these modules:
`novel_task_population_v2.py`, `novel_task_offline_check_v2.py`,
`novel_task_campaign_v2.py`, `novel_task_audit_v2.py`, and
`test_novel_task_v2.py`. It repairs the prompts, replaces the spiral sum with
an order-sensitive weighted sum, tests a real non-ASCII code point, records
every prompt-versus-case resolution, runs the campaign evaluator against a
wrong solution per task as its control, binds the population and runner
sources by digest, offers a shared runs directory and repeated passes for a
learning arm, copies evidence off tmpfs, and audits candidates only inside
the pinned container. No version 2 campaign has run yet.

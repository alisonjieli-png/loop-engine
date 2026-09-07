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

# Continue the unseen-task work: handoff brief

Audience: the next coding-agent session (Claude Code Fable 5.1 or any agent).
Scope: everything needed to continue building on the unseen novel-task
campaign of 2026-09-06 without re-deriving it. This is the single brief for
this work; do not concatenate it with other continuation prompts.

## Read these first, in order

1. [`AGENTS.md`](../../AGENTS.md) and
   [`CODEX-START-HERE.md`](../context/CODEX-START-HERE.md) for repository
   rules, the concurrent-writer policy, and the working-directory check.
2. The [execution-verified review](../verification/CODE-REVIEW-2026-09-07.md)
   — 31 findings, 29 reproduced by running code. Several correct this
   campaign's original claims; its findings register (C1-C9, R1-R2, W1-W10,
   B1-B7, H1-H4) is the defect map for this whole area.
3. The [improvement plan](../implementation/IMPROVEMENT-PLAN-2026-09-07.md)
   — the fix for each finding, its status (`done`/`proposed`/`decision`),
   and the experiment arms the version 2 modules support.
4. The original [campaign report](../verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md).

Check for concurrent writers before touching any file: more than one agent
has worked this repository in the same hours. Treat dirty files as another
session's work unless ownership is explicit.

## What exists right now

The repository is at `main` `14153a1`. Everything described here is committed
and pushed. Work in `/home/username/loop-engine` using the repository rules in
`AGENTS.md` and `docs/context/CODEX-START-HERE.md`.

The unseen-task campaign files (originals preserved as the 2026-09-06
record; version 2 modules from the improvement plan sit beside them):

```text
examples/25_host_runtime/
├── novel_task_population.py      # burned population, 10 tasks, 109 cases
├── novel_task_population_v2.py   # corrected population (plan section 5)
├── novel_task_offline_check.py   # original check (circular, see C2)
├── novel_task_offline_check_v2.py  # prompt-first references, real-evaluate controls
├── novel_task_campaign.py        # original runner
├── novel_task_campaign_v2.py     # digest-bound, --shared-runs-dir, --passes, --evidence-out
├── novel_task_audit.py           # original audit (host-import defect, see C7)
└── novel_task_audit_v2.py        # sandboxed audit, invalid inputs, argument root
docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md   # the campaign report (see corrections)
docs/evidence/novel-campaign-20260906/                      # report.json, population.json, audit.json
```

The campaign reused the existing generalization-probe host machinery
(`generalization_probe.py`) without modifying it: same `make_host`, Docker
sandbox, host-only oracle, and `solve_task` entry point. The novel modules
add no runtime type, capability, or store.

## What the campaign established — read the corrections first

> **Corrections, 2026-09-07.** A later execution-verified review
> ([CODE-REVIEW-2026-09-07](../verification/CODE-REVIEW-2026-09-07.md),
> findings C1 through C9) confirmed defects in this campaign that its report
> originally understated, and a companion
> [improvement plan](../implementation/IMPROVEMENT-PLAN-2026-09-07.md) and
> version 2 module set (`novel_task_population_v2.py` and companions)
> repair them. The record below preserves the original campaign claims; do
> not cite them without the corrections.

Ten novel-by-construction tasks (textbook domains with contract twists: grid
pathfinding, run-length decoding, ledger reconciliation, Josephus ranking,
polynomial hashing, Markdown outline depth, calendar intervals, a command
state machine, spiral matrix summation, word squares) each got one
autonomous attempt with the configured `cloud.default` /
`deepseek-v4-flash:0731` route.

Observed results, all with complete call and token accounting:

- 10/10 host-verified completions on first attempt.
- 283 model calls, 7,636,923 known input tokens, 961,827 known output
  tokens, 4,903 engine seconds, cost unknown.
- Nine tasks finished in 15 to 40 calls. `grid_path_cost` needed 106 calls
  and 2,634 seconds.
- The independent post-hoc audit (60 seeded random inputs per task)
  invalidated one accepted solution (`word_square`: raises `ValueError`
  where its contract requires `False`).

The review then confirmed three further defects the campaign report missed:

- **Three prompts contradicted their own oracles** (C1). `grid_path_cost`
  said "period-separated cells" while every case used commas;
  `calendar_slots` rejected 24:00 as outside the day while two cases
  required it; `state_machine` never mentioned leading-zero rejection while
  a case required it. The three accepted artifacts pass the oracle by
  contradicting the written prompt — by the campaign's own `word_square`
  standard, they are not correct for their exact prompts either. About 61
  percent of the campaign's calls went to these three tasks.
- **The offline check was circular** (C2). Its references and its cases
  came from the same authoring pass, so it encoded the same contradictions
  and could not catch them; its evaluator control tested the reference, not
  the real `evaluate()` path.
- **The audit had its own defects** (C4, C5, C7): an order-dependent
  reference behind the single invalidation, references that deviate from
  their prompts, and candidate code executed on the host interpreter
  instead of the sandbox.

So the honest campaign summary is: first-attempt oracle verification
10/10, but three of those ten were verified against contradictory
contracts, and the post-audit survival figure of 9/10 understates the true
defect count. Version 2 exists to repair exactly this; see the next
section.

## Known defects found by the campaign (superseded by the review)

The campaign report recorded two authoring defects. Both lessons stand, but
the review found more on both sides; treat this section as history.

1. The `grid_path_cost` prompt said "period-separated cells" while its cases
   use commas. The engine recovered through host test feedback alone, but at
   roughly 7x the cost of its peers (106 calls vs 15-40). Lesson: author
   prompts and cases mechanically against each other before dispatch. The
   review confirmed two more contradictions of the same kind
   (`calendar_slots`, `state_machine`) that the campaign report missed.
2. The audit's own grid reference crashed on a start-corner wall
   (`TypeError` from `None + int`). The audit process caught it because it
   compares candidate and reference on identical inputs. Lesson: the audit
   oracle is code too; it needs the same evaluator-control discipline as
   the task evaluator. The review additionally found the audit imported
   candidate code on the host interpreter and used a hardcoded `/tmp` path
   (C7); version 2 runs candidates in the sandbox and takes its root as an
   argument.

## The version 2 repair set (from the improvement plan)

The improvement plan's section 5 built a version 2 module set that repairs
every campaign finding. The originals stay untouched as the record of the
2026-09-06 run; the version 2 modules live beside them:

- `novel_task_population_v2.py`: prompts and cases agree (commas, 24:00 as
  the named end-of-day sentinel, leading zeros stated), a spiral task whose
  visited order matters, a real code point above 127, and the ambiguous
  `word_square` rule stated in one sentence.
- `novel_task_offline_check_v2.py`: references written from the prompt text
  before reading the cases, disagreements resolved by changing the case or
  prompt, and evaluator controls that run the real `evaluate()` against
  deliberately wrong solutions through the probe `WORKER`.
- `novel_task_campaign_v2.py`: digest-binds its own source, the population,
  and the offline check (re-checked before each task), adds
  `--shared-runs-dir` so pass two can consult pass one's stages, `--passes`
  for repeated-population runs, and `--evidence-out` to copy evidence off
  tmpfs.
- `novel_task_audit_v2.py`: takes its campaign root as an argument, runs
  every candidate inside the pinned container, generates invalid inputs as
  well as valid ones, and never imports candidate code on the host.

Before dispatching any v2 campaign, re-verify the plan's claimed `done`
statuses by running the v2 offline check and its unit tests yourself.

## The population is burned as evidence

The ten tasks, their cases, and the audit seeds are now public in the
repository. No future run may cite them as unseen or untouched. Any new
generalization claim requires a freshly authored sealed population, new
seeds, and the same offline verification before dispatch.

## Task 1: run the version 2 campaign (highest value)

The improvement plan repaired the population, check, runner, and audit. The
next information gain is running the repaired instrument: a live version 2
campaign on the corrected population, with digest binding and sandboxed
audits, then an honest comparison against the 2026-09-06 result. Watch for
the plan's own open question: with the three contradictions removed, does
the hardest-task cost drop from the 106-call outlier to the 15-40 band of
its peers?

If a pre-acceptance counterexample gate is still wanted (the original
Task 1 below), build it on the version 2 runner, not the burned originals.

## Task 2: repair-loop failure classification for contradictory specs

The `grid_path_cost` log shows many `verify -> route -> orient -> how`
cycles where each candidate failed the same way before the format confusion
resolved. The history review
(`docs/verification/HISTORY-AND-OVERNIGHT-REVIEW-2026-09-06.md`) already
requires classifying failures before choosing to split or retry.

The work: after a run, classify each failed candidate observation into a
typed failure kind (for example: contract contradiction, oracle mismatch,
implementation error, infrastructure). The engine's own event history
contains everything needed; this is post-run analysis first, not a runtime
change. A runtime signal could follow later if the classification earns it.

Acceptance test: replay the saved `grid_path_cost` run history from the
campaign evidence and produce a typed failure sequence. Check whether the
classification would have flagged the spec contradiction earlier than the
106th call. Do not modify the recorded history.

## Task 3: the live paired-assistance gate (still open since 2026-09-04)

Nothing in this campaign touched the memory/assistance causal question. The
paired fixture remains `mechanism_only`; the documented open items are
canonical trial assignments, treatment-free packet comparison, source freezing
at use, qualified independent evaluator identity, and the public-history to
projection bridge. Do not cite the novel campaign as assistance evidence; it
used no prior material. The v2 runner's `--shared-runs-dir`/`--passes` flags
are the plan's arm B for measuring second-pass behavior, but they are not a
controlled assistance comparison and must not be described as one.

## Tasks deliberately deferred (with reasons already on record)

```text
Deferred work
├── Parallel adaptive spawning
│   ├── Extension point: existing graph compiler + DelegationSpec
│   └── Reason: serial control first; joins/cancellation semantics designed but untested
├── Dependency-output bindings beyond the serial plan
│   ├── Extension point: DelegationSpec typed ports
│   └── Reason: needs unchanged simple-task controls and negative cases
├── Overnight daemon / Jira integration
│   ├── Entry: exported-ticket fixture in examples/25_host_runtime/
│   └── Reason: needs its own host adapter, protected gates, and human review policy
└── Kaggle graded submission
    ├── Entry: prepare_kaggle.py + configured account (1,049 entered)
    └── Reason: external spend + submission rules; requires explicit user authorization
```

## Rules for any new campaign

1. Author a fresh sealed population. Never reuse the burned ten tasks or
   seeds as unseen evidence.
2. Verify every case against a reference written from the prompt text BEFORE
   reading the cases; resolve any disagreement by changing the case or the
   prompt, and record the resolution. Run evaluator controls through the
   real `evaluate()` path against deliberately wrong solutions. Zero model
   calls until the whole population passes this.
3. One autonomous attempt per task, no operator repair or continuation, no
   invented call/token ceilings, no failover. Record failures as failures.
4. Digest-bind the population, offline check, and runner; re-verify before
   each task. Keep campaign evidence off tmpfs (`--evidence-out` or
   equivalent).
5. Run the independent seeded audit afterward, audit your own audit
   reference, and report survival honestly. Audit candidates inside the
   sandbox, never by importing them on the host.
6. Report the exact denominator, per-task calls/tokens/elapsed, accounting
   completeness, cost state, false acceptances, prompt-oracle consistency,
   and limitations.
7. Cite the CI run for the commit; local green is not CI green (review
   finding R1: CI has been red on the hardcoding delta gate since
   2026-09-02).
8. Update `CODEX-START-HERE.md` and `CHANGELOG.md` when the checkpoint lands.

## Environment facts a fresh session needs

- Python: `.venv/bin/python` is 3.10; `requires-python >= 3.10`. Use the
  `tomli` fallback pattern for `tomllib` (see
  `src/loop_engine/core/live_model_verification.py`).
- The pinned sandbox image is already present locally; a missing image is a
  hard stop, not a download trigger.
- The configured live route is `cloud.default` with
  `deepseek-v4-flash:0731` (65,536 declared output tokens). Live runs spend
  real calls; a new session needs the user's explicit authorization before
  a new spend.
- CI is currently red (finding R1): the hardcoding delta gate has failed on
  every push since 2026-09-02 and local green is not CI green. Triage order
  is in the improvement plan's section 6; do not weaken the gate or refresh
  its baseline silently.
- Campaign evidence on tmpfs is volatile; use `--evidence-out` or copy to
  `docs/evidence/` before the machine restarts.
- Entry checks for any session are in `docs/context/CODEX-START-HERE.md`.
- Verification: run the example suite
  (`python -m unittest discover -s examples/25_host_runtime -p 'test_*.py'`)
  and the self-test aggregator
  (`loop_engine._self_test.self_test()`); record both results and the CI
  run for your commit.

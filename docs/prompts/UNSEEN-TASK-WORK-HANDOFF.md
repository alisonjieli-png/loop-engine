# Continue the unseen-task work: handoff brief

Audience: the next coding-agent session (Claude Code Fable 5.1 or any agent).
Scope: everything needed to continue building on the unseen novel-task
campaign of 2026-09-06 without re-deriving it. This is the single brief for
this work; do not concatenate it with other continuation prompts.

## What exists right now

The repository is at `main` `14153a1`. Everything described here is committed
and pushed. Work in `/home/username/loop-engine` using the repository rules in
`AGENTS.md` and `docs/context/CODEX-START-HERE.md`.

The unseen-task campaign files:

```text
examples/25_host_runtime/
├── novel_task_population.py     # 10 sealed tasks, 109 cases, author-frozen
├── novel_task_offline_check.py  # independent references + evaluator controls
├── novel_task_campaign.py      # live runner (reuses frozen probe machinery)
└── novel_task_audit.py         # seeded random-input post-hoc audit
docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md   # the campaign report
docs/evidence/novel-campaign-20260906/                      # report.json, population.json, audit.json
```

The campaign reused the existing generalization-probe host machinery
(`generalization_probe.py`) without modifying it: same `make_host`, Docker
sandbox, host-only oracle, and `solve_task` entry point. The novel modules
add no runtime type, capability, or store.

## What the campaign established

Ten novel-by-construction tasks (authored domains: grid pathfinding,
run-length decoding, ledger reconciliation, Josephus ranking, polynomial
hashing, Markdown outline depth, calendar intervals, a command state machine,
spiral matrix summation, word squares) each got one autonomous attempt with
the configured `cloud.default` / `deepseek-v4-flash:0731` route.

Observed results, all with complete call and token accounting:

- 10/10 host-verified completions on first attempt.
- 283 model calls, 7,636,923 known input tokens, 961,827 known output
  tokens, 4,903 engine seconds, cost unknown.
- Nine tasks finished in 15 to 40 calls. `grid_path_cost` needed 106 calls
  and 2,634 seconds.
- The independent post-hoc audit (60 seeded random inputs per task, plus a
  500-input boundary stress) invalidated one accepted solution:
  `word_square` raises `ValueError` where its contract requires `False`
  (109 of 500 boundary inputs). Nine of ten accepted solutions survived.

So: first-attempt verification rate 10/10, post-audit survival 9/10,
false-acceptance rate 10 percent on this population. The campaign report is
the authoritative record; keep its observed/inferred/not-established
distinctions when citing it.

## Known defects found by the campaign (both fixed, keep the lessons)

1. The `grid_path_cost` prompt said "period-separated cells" while its cases
   use commas. The first generated solution split on `.` and failed; the
   engine recovered through host test feedback alone, but at roughly 7x the
   cost of its peers (106 calls vs 15-40). Lesson: author prompts and cases
   mechanically against each other before dispatch. The population module
   now has this fixed, but the campaign evidence in
   `docs/evidence/novel-campaign-20260906/` preserves the original run.
2. The audit's own grid reference crashed on a start-corner wall
   (`TypeError` from `None + int`). The audit process caught it because it
   compares candidate and reference on identical inputs. Lesson: the audit
   oracle is code too; it needs the same evaluator-control discipline as
   the task evaluator.

## The population is burned as evidence

The ten tasks, their cases, and the audit seeds are now public in the
repository. No future run may cite them as unseen or untouched. Any new
generalization claim requires a freshly authored sealed population, new
seeds, and the same offline verification before dispatch.

## Task 1: pre-acceptance counterexample gating (highest value)

The campaign's headline defect is the 10 percent false-acceptance rate. The
repo already names the fix in
`docs/verification/ADAPTIVE-HOST-GENERALIZATION-2026-09-06.md`: run
independently seeded, source-frozen counterexample checks BEFORE final
acceptance instead of only after.

Today the pieces exist but are split:

- `make_host(..., completion_policy=...)` in `generalization_probe.py`
  already supports a `workspace_completion` verifier that runs extra
  generated cases in the sandbox before `task_complete` is granted.
- `counterexample_checks.py` implements this for exactly one task
  (`sales_aggregation`), selected via `--counterexample-seed`.
- `novel_task_audit.py` already generates seeded random inputs per task and
  compares against independently written references.

The work: generalize the completion-policy path so any task can carry a
host-owned, seeded random-input gate with an independent reference oracle.
Constraints to respect:

- The reference oracle must be written independently from the prompt, and
  the gate must include an evaluator control (a deliberately wrong solution
  the gate must reject), matching the discipline in
  `novel_task_offline_check.py`.
- The gate is a completion requirement, not a hint channel: generated inputs
  and expected answers stay host-side. Only bounded failure summaries reach
  the model, exactly like the existing completion record format.
- The counterexample generator and its seed are part of the frozen task
  contract; changing either is an evaluator revision requiring the existing
  `--allow-evaluator-revision` flow.
- A gate that cannot establish a material requirement must return an
  explicit unknown, not a pass.

Acceptance test: author a fresh sealed population (5 to 10 tasks, any
domains except the burned ten), run the live campaign with the gate enabled,
and require zero post-audit invalidations with at least one deliberately
wrong solution rejected by the gate in a fixture. Preserve any failures.

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

Acceptance test: replay the saved `grid_path_cost` run history from
`/tmp/novel-campaign-20260906/grid_path_cost/runs/` (copy it into the
repository evidence directory first if you need it durable) and produce a
typed failure sequence. Then check whether the classification would have
flagged the spec contradiction earlier than the 106th call. Do not modify the
recorded history.

## Task 3: the live paired-assistance gate (still open since 2026-09-04)

Nothing in this campaign touched the memory/assistance causal question. The
paired fixture remains `mechanism_only`; the documented open items are
canonical trial assignments, treatment-free packet comparison, source freezing
at use, qualified independent evaluator identity, and the public-history to
projection bridge. Do not cite the novel campaign as assistance evidence; it
used no prior material.

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
2. Verify every case against an independent reference offline, with
   evaluator controls, before any dispatch. Zero model calls until the
   whole population passes this.
3. One autonomous attempt per task, no operator repair or continuation, no
   invented call/token ceilings, no failover. Record failures as failures.
4. Run the independent seeded audit afterward, audit your own audit
   reference, and report survival honestly.
5. Report the exact denominator, per-task calls/tokens/elapsed, accounting
   completeness, cost state, false acceptances, and limitations.
6. Update `CODEX-START-HERE.md` and `CHANGELOG.md` when the checkpoint lands.

## Environment facts a fresh session needs

- Python: `.venv/bin/python` is 3.10; `requires-python >= 3.10`. Use the
  `tomli` fallback pattern for `tomllib` (see
  `src/loop_engine/core/live_model_verification.py`).
- The pinned sandbox image is already present locally; a missing image is a
  hard stop, not a download trigger.
- The configured live route is `cloud.default` with
  `deepseek-v4-flash:0731` (65,536 declared output tokens). Live runs spend
  real calls; the user has authorized campaign-scale live runs in this
  thread, but a new session should confirm before a new spend.
- Entry checks for any session are in `docs/context/CODEX-START-HERE.md`.
- Verification: run the example suite
  (`python -m unittest discover -s examples/25_host_runtime -p 'test_*.py'`)
  and the self-test aggregator
  (`loop_engine._self_test.self_test()`); the merged tree passes 127 example
  tests and 3,384 self-test checks as of `14153a1`.

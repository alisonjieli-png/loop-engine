# Task-database campaign runner review, September 13, 2026

A read-only review of `devtools/embodiment_lab/task_database_campaign.py`
at `d806759`, the revision the detached worker under
`.loop-engine-dev/live-task-database-20260913-sQvDZL/controller/` runs
(identical bytes). The parallel Codex session changed the working copy
during the review (`e32d742` generalizes the provider key and adds
`CampaignTrialServices`); the two decisive probes were re-run against that
working copy and every defect below still reproduced. Probe scripts and
their outputs are under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-campaign/`.
Nothing was edited, no worker was started or stopped, and no provider or
network call was made; sockets and openers were replaced by fixtures.

The worker is alive, sleeping, at cursor round 0, task position 0, zero
completed trials, waiting for the provider (errno 113, no route to host).

## Defects

1. **High. Any `PROVIDER_UNAVAILABLE` terminal is treated as an outage,
   and the same cell is re-run without bound, multiplying real model
   calls.** `task_database_campaign.py:408-416` keys its only recovery
   branch on `engine_terminal == "PROVIDER_UNAVAILABLE"`, but
   `solve_terminal.py:47-54,71-72` folds `authentication_failed`,
   `payment_required`, `model_not_found`, `missing_credential`,
   `rate_limited`, `timeout`, `context_window_exceeded`, and a bare
   `RuntimeError` into that terminal (`probe8_terminal_breadth.out`). Each
   such attempt already made physical calls (the Practitioner retries
   transport up to three times per step), and the worker restarts the whole
   trial with the next attempt number after sixty seconds, forever
   (`probe3_worker_control_flow.out`: `('T-001','0-attempt-0')`,
   `('T-001','0-attempt-1')`, `('T-001','0-attempt-2')`, identical
   configuration, no cap). A wrong key or a renamed model after recovery
   would loop indefinitely, each loop consuming calls and creating a new
   trial cell. Fix: branch on the underlying failure code (only
   `network_unreachable`, `provider_unavailable`, and `gateway_timeout`
   are outages), add a per-cell attempt ceiling, and record the retry
   reason. `core.provider_failure_classes.decide` now does exactly this
   from the attempt's error codes: it returns wait for recovery, wait for
   the allowance, stop the route, or fail the cell, with a stated attempt
   ceiling bounding every wait, so the worker can call it instead of
   keying on the folded terminal.

2. **High. No durable resume: a crash mid-trial bricks the campaign, and
   manual reconciliation then crashes the worker on a directory
   collision.** After a simulated crash `active_trial` stays `running`;
   restart is refused (`an interrupted trial requires explicit
   reconciliation before resume`) and the module has no reconciliation
   helper. Clearing the marker by hand resumes with the same occurrence
   id, and `run_trial` then raises `FileExistsError` from
   `cell.mkdir(exist_ok=False)` before its try block, so no record is
   written and the marker is set again
   (`probe5_run_trial_failure_and_collision.out`). A `SIGTERM` or a reboot
   during any of the 566,720 cells produces this; the `finally` does not
   run on default `SIGTERM`. Fix: on resume, mark the interrupted
   occurrence in `trial_projection`, bump the attempt, move `mkdir` inside
   the recorded try, and add a `reconcile` operation to `main()`.

3. **Medium. Counts are not kept separate.** `completed_trials` increments
   before the outage check (`:407`), so outage-terminated attempts count as
   completed (`finished cells 32 | outage attempts 2 | completed_trials
   counter 34`), and the manifest has only `raw_task_configuration_cells`
   with `valid_task_configuration_cells: null`. Fix: separate dispatched,
   outage-terminated, failed, finished, evaluated, and verified counters in
   the cursor and the status export.

4. **Medium. Per-step checkpoints re-save the whole shared ledger, so
   checkpoint bytes grow quadratically, and the setter Loop inflates the
   task's own Run History.** `:227-233` calls `RunHistory.from_ledger` on
   the parent ledger, which spawned Loops share (`recursive_loop.py:597`).
   `probe4_checkpoint_growth.out`: checkpoints of 37, 71, 105, ... 275
   events over eight calls, cumulative 1,145,961 bytes against 252,328 for
   the last checkpoint alone, and about 34 ledger events added per model
   call by `apply_configuration_as_loop`. Fix: checkpoint only the events
   since the last checkpoint, and record the setter run in the campaign
   projection rather than the task ledger.

5. **Medium. The readiness probe misclassifies in both directions and
   never exercises the generation URL.** `probe2_readiness_probe.out`: a
   plain `http` base without a port probes 443; a model id with a tag
   suffix reads as unreachable; 401, 404, and 503 all read as unreachable,
   so an authentication failure or a missing route waits forever as an
   outage; for the Ollama wire the probe opens `/models` while the product
   adapter uses `/api/tags`; the generation URL `<base>/chat/completions`
   is never opened. Fix: default the port by scheme, reuse the adapter's
   own model listing, classify 401, 402, and 404 as configuration failures
   that stop the worker with a distinct status, and consider a bounded
   one-token generation probe.

6. **Medium. Adding a provider cannot reach this campaign.** At `d806759`
   the provider, model, and route are hard-coded and the provider file is
   digest-frozen, so adding a route makes the worker refuse to start
   (`frozen campaign inputs changed`) and the probe only ever checks the
   one provider. `e32d742` generalizes the provider key; whether the
   frozen queue can adopt a second route without a new campaign root, and
   without new occurrence identities, still needs a stated rule.

7. **Medium. The engine's identity is recorded but not frozen.** The
   manifest digests the catalog, population, provider file, harness
   manifests, and configuration space; the package digest map is written
   per worker start (two revisions already) but never compared, and the
   harness `runtime/` scripts named by `command_prefix` are not digested.
   Fix: put the package and harness-runtime digests in the manifest and
   refuse a mismatch unless a typed override is recorded.

8. **Medium. `output_allocation_tokens` is applied only as the initial
   gateway allocation.** A Practitioner recovery can replace it per request
   (`solution_model_port.py:335-336`,
   `adaptive_practitioner_records.py:2028, 2556-2557`), and the recorded
   session binds only `temperature` (`probe1` output: `settings bound:
   [parameter_id 'temperature']`). Fix: include the effective allocation
   and the harness actually used in `applied_configuration`.

9. **Low. Failures keep only the exception class** (`:308`): no message,
   chain, or stage, and a crash that escapes `run_trial` leaves no row.

10. **Low. `harness_fallback="registered_alternatives"` switches on every
    failure kind**, including semantic and response rejection, so one
    rejected answer can chain through nineteen harnesses inside one
    semantic call under this cell's configuration. State the intended kinds
    per axis value.

11. **Low. The published `population-index.json` cannot reproduce
    `population_digest`** (`probe7_population_digest.out`): the digest
    covers private rows including absolute task directories.

12. **Low. Not-ready tasks are iterated every round**: 165 tasks awaiting
    source admission times 320 rounds is 52,800 no-op iterations, each
    writing a projection row and a status export.

## Test honesty

The module's six tests pass in under a second and cover the confined
name, the fair order, space enumeration, the diagonal schedule, and the
recorded setting session against a fixture. They do not exercise
`prepare`, `worker`, `run_trial`, `task_intake`, `provider_available`,
`endpoint_reachable`, resume, or outage accounting. The receipt's initial
real attempt came from a separate script with a different prompt, no
recorded setting session, no per-step checkpoints, and no configuration;
`run_trial` has never executed end to end, and the live database holds no
trial, applied-configuration, or step-history rows. The commit title's
"outage gating" describes untested code.

## Verified sound

- The outage gate preserves the cursor exactly and dispatches nothing
  while the provider is unreachable (twenty-four identical live log
  entries).
- After an outage-terminated attempt the same task and configuration are
  retried.
- Temperature is genuinely applied and recorded (asked 0.2, delivered 0.0
  and 0.7 in the fixture), and context delivery is applied at intake.
- Path containment refuses attachment and dataset-symlink escapes and
  accepts an in-database symlink.
- Population, catalog, provider file, harness manifests, and the
  configuration space are digest-frozen and re-checked; the diagonal
  schedule is exhaustive per task.
- The sixty-second poll is bounded and signal-interruptible; cells are
  enumerated by index, not materialized.
- All nineteen external harness executables resolve on this host.

## Not verifiable offline

Whether the provider's model listing carries the exact configured model
id; real `run_trial` behaviour, checkpoint sizes, and harness fallback with
a live provider; availability of the pinned sandbox image; and any
completion estimate, since one sequential worker with no pass or call
ceilings faces 566,720 cells.

# Campaign activation and safety review, September 13, 2026

A read-only, offline review of the Codex session's `65593c7` ("Prepare
governed Ollama experiments and evidence-based self-improvement"): the
activation gate, the gateway-based access check, the worker's handling of
classified provider failures, crash and restart, checkpoint retention,
engine identity, the self-improvement history interpretation, and the
`encapsulate` accounting change. Probe scripts and outputs are under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-activation/`;
the definitive runs used the launched worker's own frozen snapshot. The
worker that waits for 00:23:46 UTC runs that snapshot, which predates every
fix below; a relaunch from a snapshot at or after this commit is needed for
any of them to apply.

## Defects, and what was fixed the same night

1. **High. Per-trial step history was quadratic.** Every invocation saved a
   full copy of the whole owner ledger (24 invocations, 9.4 MB; about 0.8 GB
   for a 226-call trial). **Fixed in `fbddd7c`:** one history per trial,
   grown by extension and checkpointed into the append-only store.

2. **High. A page in the provider's place drained the queue.** A 200 body
   with an error field or a non-JSON page during a trial ended with
   `model_calls: None`, no usage, and no provider code: the gateway attempt
   normalised the provider's two zero counters to unknown while the ledger
   event kept them as zero, the harness accounting check read the
   difference as "identity, status or usage mismatch", the session marked
   accounting uncertain, `terminal_provider_codes` returned nothing, and
   `decide([])` failed the cell and advanced the cursor (six cells in six
   rounds in the probe). **Fixed:** the accounting check accepts the pair
   as one description of one response (the ledger keeps a received
   response's reported zero, the gateway reads two zeros as absent usage,
   and both stay as they are), and a missing or untyped `response_received`
   on a failure is unknown usage in the ledger; so the typed code flows:
   the trial ends `PROVIDER_UNAVAILABLE` with `invalid_response_body`, one
   counted call, complete accounting, and the worker waits for recovery.
   Pinned by an offline trial test.

3. **Medium. A reference id inside a 200 error body read as a status.** The
   `provider_error_body:` prefix carries no status, so `(ref: 401abcd)`
   became `authentication_failed` and an operator would rotate a valid
   key. **Fixed:** hexadecimal reference and request ids are dropped before
   any bare-digit rule reads the text.

4. **Medium, left open (the Codex session's reconciliation design).**
   Nothing in the CLI clears the `active_trial` marker after a SIGTERM,
   reboot, or OOM; `reconcile` only re-records it, so the campaign stays
   parked until the projection is edited by hand, and a hand-cleared
   occurrence is scored as a failed cell and never re-run. A typed
   `reconcile --acknowledge` that records the decision is the fix.

5. **Medium, left open.** `engine_identity` digests only the package's
   Python sources and the harness executables; the controller,
   `campaign_activation.py`, the systematic modules, and 63 package resource
   files are outside it, `controller_digest` is recorded but never compared,
   and the check runs once before the loop.

6. **Medium, left open.** A generic 400 or 422 (`invalid_request`) stops the
   route after one attempt, and a restart skips that cell as failed and
   stops again on the next 400; the honest policy is to fail the cell and
   stop the route only on repetition across cells.

7. **Low. A restarted worker suspended again after one attempt** because
   the suspension left `trial_attempt` at the ceiling. **Fixed:** the
   suspension records `suspended_after_attempts` and `suspensions` and
   resets the per-cell counter, so a restarted worker waits its full
   ceiling.

8. **Low. `not not_before` opened the gate for a null or zero.** Only
   reachable through a hand-edited manifest. **Fixed:** an absent gate
   opens; any non-text value is refused.

9. **Low.** The self-improvement population counted non-run directories,
   and the same ledger re-projected under a new run id counted as an
   independent run, since the run id is in every event body. **Fixed:**
   the population is the directories holding a manifest (saved runs and
   checkpoint stores, which now load as their latest checkpoint); an
   artifact sibling is reported as ignored and no longer consumes a run
   limit slot; `RunHistory.content_digest()` drops the run id, the chain
   links, and the start event's projection time, and a later copy of an
   already loaded content is excluded naming the run it repeats. The miner
   deduplicates on that digest as well.

10. **Low. The `encapsulate` guard was `is False` only**, so a failed
    result lacking the flag or carrying `None` recorded zero usage as
    complete. **Fixed** with finding 2.

11. **Low, launch path.** The untracked launch script opens `worker.log`
    exclusively, so it cannot relaunch after the expected
    `provider_access_not_verified` exit without deleting the log.

## Verified sound

The gate refuses naive datetimes on both sides and compares other-timezone
instants to the second; a malformed value fails closed with zero probes; the
worker sleeps sixty seconds per poll and proceeds within one interval. The
access check makes exactly one physical request in fourteen scenarios with
failover off and no key in any record; 429 weekly-limit is
`usage_limit_reached`, 401 `authentication_failed`, 404 `model_not_found`,
NDJSON or HTML `invalid_response_body`, and a failed check exits
`provider_access_not_verified` with the cursor unchanged. Allowance codes
wait three times and suspend with the position unchanged and no failed
cells; `context_window_exceeded` fails the cell and keeps the route. SIGTERM
unwinds every finally block; a restart records
`interrupted_requires_reconciliation` with zero dispatches;
`--refuse-interrupted` raises; `--allow-engine-change` cannot bypass the
marker; the interrupted occurrence is never replayed; a second worker is
refused by the lock. Every revision is retained and `RunHistory.save`
refuses overwrite. The snapshot's engine digest equals the frozen one. An
all-failed run yields only failure-pattern candidates; twenty repeated
failures in one run count once; renamed copies are excluded.

## Not verifiable offline

Whether the allowance resets at 00:23:46; whether `deepseek-v4-flash:0731`
accepts `think: false`; the real 200-error and page shapes Ollama Cloud
emits; marker durability under power loss; real event sizes.

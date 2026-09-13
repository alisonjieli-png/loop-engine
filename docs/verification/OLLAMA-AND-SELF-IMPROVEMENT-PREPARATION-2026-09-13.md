# Ollama and self-improvement preparation

The shared campaign interface is prepared for an Ollama Cloud route, with
an explicit activation-time gate and a real gateway access check. The
primary worker is waiting until September 14 at 00:23:46 UTC. That time
comes from the owner's estimate, not a verified provider reset.

The [saved summary](../../artifacts/ollama-preparation-20260913-N207rU/summary.json)
identifies the checked snapshot, prepared routes, and launched worker.
The [experiment-driven self-improvement guide](../guides/experiment-driven-self-improvement.md)
explains how the same machinery can support broader experiments and a
reviewed improvement cycle without granting self-approval.

## Corrections verified

| Finding | Result |
|---|---|
| A folded `PROVIDER_UNAVAILABLE` terminal hid authentication and request failures. | The trial records actual terminal gateway codes. A full offline trial through a denied transport preserves `authentication_failed`, and the worker stops that route. |
| Unknown codes became invented outages. | Unknowns remain unclassified failures. |
| Exhausted provider waits consumed task positions. | An outage or allowance wait ceiling suspends the provider and preserves the task cursor. |
| Restart cleared an interrupted trial without resolving effects. | The marker stays pending; no task or probe is dispatched. General effect reconciliation remains open. |
| Checkpoint retention removed files referenced by earlier records. | Automatic deletion is refused and histories are preserved. Scalable checkpoint storage remains open. |
| Initial allocation and effective allocation could differ. | Each invocation records its effective request allocation and observed provider and harness attempts. |
| Failed invocations became successful model decisions in the improvement miner. | Only explicit response, failure, and fallback events determine those review signals. |
| Repeated events or copied histories became independent runs. | Frequency counts supplied traces once per pattern; known run identities and history digests are deduplicated. Independence is not asserted. |
| `run_limit=None` crashed, while zero selected all directories. | None and zero keep their distinct meanings; invalid limits refuse. |
| Self-improvement used the reference Practitioner profile implicitly. | It uses `practitioner.self_improvement@1.0.0` and its registered boundary. |
| Unanswered requests inherited zero token counters. | A failed request with no response records unknown usage instead. |

## Real-history review

The existing reviewer read the saved `SWE-001` failure history and verified
its chain. One valid history was reviewed; the adjacent artifact directory
was excluded because it is not a Run History bundle. Source files remained
unchanged.

With an explicitly selected minimum trace frequency of one, the reviewer
staged two candidate review items about the failed model invocation. It
made zero model calls and promoted nothing. The earlier output had described
failed requests as resolved work and two events as two runs. Those claims
are no longer produced by this control.

The [review record](../../artifacts/ollama-preparation-20260913-N207rU/self-improvement-review.json)
contains the source digests, candidate items, exact profile evidence, and
review-history identity. Its priorities are heuristic, not calibrated
confidence. This is not demonstrated recursive improvement or a task-quality
gain.

## Ollama preparation

Six model configurations have prepared campaigns using the same interfaces:

- `deepseek-v4-flash:0731`
- `deepseek-v4-pro:0813`
- `glm-5.3-flash`
- `gpt-oss:20b`
- `nemotron-3-nano:30b`
- `gemma4:31b`

Each configuration retains the 1,771-task population and declares 320 raw
configurations per task. Neither source readiness nor a raw configuration
count establishes runtime compatibility, evaluator qualification, or
completed testing. The six routes have existing exact-model output-capacity
records; their live access and task quality remain unqualified here.

Only `cloud.default`, bound to `deepseek-v4-flash:0731`, has a delayed worker
launch. The other five routes are prepared but not launched. The worker
uses the same gateway and campaign implementation, with no separate
provider-specific runtime. It will make no probe or task call before the
declared time. A failed access check stops without advancing the task queue.
Provider failover is disabled.

The [worker launch record](../../artifacts/ollama-preparation-20260913-N207rU/worker-launch.json)
records the process, exact command, source location, route, and time gate.
Live status is at
`.loop-engine-dev/ollama-review-preparation-20260913-OFLZBE/ready-flash/status.json`.
This worker is not configured to restart after a reboot. Tactical monitoring
remains stopped and its earlier records remain unchanged.

## Verification scope

The final isolated snapshot contains committed base `dd49ca3` plus this
session's owned changes. Concurrent working-tree edits were not used for the
launch snapshot. The [source manifest](../../artifacts/ollama-preparation-20260913-N207rU/source-manifest.json)
binds the package and build inputs.

| Check | Result |
|---|---|
| Source self-test | 4,643/4,643 reported suite records. |
| Clean-wheel self-test | 4,608/4,608 reported suite records. |
| Source and clean-wheel architecture conformance | 27/27 gates in each environment. |
| Repository conformance | Passed, 520 indexed files, no reported problems. |
| Development laboratory | 72 offline tests passed, including activation, interruption, quota, and full trial-boundary controls. |
| Documentation | Markdown and prose checks passed. |

The suite totals include explicit records for unavailable optional adapters.
Read `optional_adapters_not_tested` in the saved summaries before making an
adapter-coverage claim. The [command records](../../artifacts/ollama-preparation-20260913-N207rU/verification-commands.json)
preserve exit codes, elapsed times, and output. An earlier isolated baseline
also passed; its local evidence remains separate.

No new model inference was performed by this preparation work. The separate
[adapter review](OLLAMA-ADAPTER-REVIEW-2026-09-13.md) reports an earlier
Ollama quota refusal, not a successful generation. The scheduled worker has
not yet established provider availability or solved tasks.

## Remaining limits

Full-ledger checkpoints still have a storage-growth problem. The evidence
summary is not a substitute for checking artifact contents and exact
independent-evaluator bindings. Task-specific campaign acceptance remains
unqualified, and unresolved effects cannot be automatically replayed.

The broader model universe, complete dimension interactions, adaptive live
optimizer policies, and autonomous promotion require further work and
measurement. The current result is safer experiment preparation and
candidate-only improvement review, not an achieved general self-improving
system.

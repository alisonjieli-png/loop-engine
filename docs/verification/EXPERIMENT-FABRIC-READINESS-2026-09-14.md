# Experiment readiness, September 14, 2026

The owner requested resolution of the readiness defects and a flexible system
for broad experiments and independently reviewed improvement. General
intelligence remains a research objective, not an achieved capability or a
new runtime type.

## Required release checks

| Area | Required behavior | Current evidence or remaining work |
|---|---|---|
| Source identity | Bind task instructions, attachments, datasets, and directory membership before comparing configurations. Check the contents again before and after a trial. | The content audit froze all 1,606 source-ready tasks in the 1,771-task catalog. The other 165 tasks retain source-admission gaps. These counts do not qualify evaluators. |
| Token accounting | Preserve missing, partial, and real-zero usage. Keep known subtotals separate from unknown totals. | Focused report, Studio, and provider controls exercise these cases. Frozen-source and base clean-installation suites pass. |
| Physical requests | Record actual request counts and refuse hidden extra requests at a single-attempt adapter boundary. | Focused offline controls cover a proxy timeout and an adapter that reports two requests. No live-provider claim follows from those controls. |
| Access checks | Declare probe frequency and count access probes separately from task trials. | New campaigns declare `campaign_access_policy/v1`. The default is one successful check per worker activation, invalidated by provider outage or allowance failure. |
| Invocation records | Preserve repeated invocations without overwriting their identities. Match every model invocation to settings and a checkpoint. | Each invocation has a separate occurrence key. The report compares occurrence counts and identities, not only the presence of some records. |
| Artifact and outcome identity | Verify artifact bytes and the exact product outcome bound to Run History. | Missing digests, conflicting digests, changed bytes, and altered outcome bodies must refuse. The solver's exact post-binding self-reference is a permitted projection. |
| Evaluation | Bind a qualified independent evaluator to the exact task, inputs, and delivered subject. | A verdict label is insufficient. The evidence reader requires an independently supplied host resolver. Broad task-specific qualification remains open. |
| Adaptive search | Use admitted measurements to choose subsequent configurations; exclude protected final evaluations and duplicate measurements. | Existing proposal mechanisms remain separate from dispatch. Live campaign integration and measured selection quality are not complete. |
| Recovery and scheduling | Preserve unresolved effects, reconcile before retry, and keep long tasks from preventing other admitted work. | The old delayed worker was stopped before a task. A replacement was cancelled for repeated unaccepted work. Per-cell call and pass limits are selectable grid levels and reach execution. General reconciliation, fair continuation, and distributed qualification remain open. |
| Reporting at scale | Read bounded pages, distinguish trial completion from task acceptance, and retain failed and excluded attempts. | Integer-range axes retain bounds without allocating every level; a trillion-level range is covered by a component test. Large-population viewer and query-load qualification remain open. |
| Reuse and improvement | Independently review candidates, measure later use and regressions, and support withdrawal of unsuitable changes. | Candidate staging does not establish recursive improvement or authorize promotion. |

## Launch state

The original delayed worker, process 2999422, was stopped with its process
identity verified. Its cursor remained at zero completed trials. The queue
and previous records were preserved. Its old paths cannot be reused blindly:
the task database moved to `/home/username/loop-engine/task_database` during
this work.

Ollama subsequently answered a real access probe. Two replacement reference
workers and four compact composition trials made real model calls. The pro
reference worker was cancelled at 01:56 UTC after hundreds of calls on one
unaccepted support task. Its occurrence requires effect reconciliation and
has no replay authority. The flash worker received `usage_limit_reached` at
02:04 UTC and stopped. Neither worker was active at the later process check.
No next reset time is established by these observations.

The [first reference-cell report](LIVE-CAMPAIGN-FIRST-CELLS-2026-09-14.md)
records 13 flash cells: seven executed and six failed during harness setup.
The regenerated campaign report counts 817 task calls as a known subtotal,
plus two access-probe calls. It retains 21,203,050 observed task tokens as a
known subtotal, not an exact total. Missing setup accounting and unanswered
provider usage keep complete totals unknown. One reference cell reached the
engine's `COMPLETED_VERIFIED` terminal; no cell in this campaign has a qualified
independent task-evaluator binding in the evidence report.

The compact composition produced two executable analytics candidates and two
manifest failures. Each used one real model call. Independent development
evaluation found 6 of 8 checks passing for the first executable candidate.
After feedback, its revision passed those 8 checks but failed an additional
open-ended-date check. On the expanded nine-check set, the original passed 7
and the revision passed 8. Neither is independently accepted. The added check
was informed by source review, so it is an adversarial development check,
not a protected final evaluation.

The four-layer self-improvement review verified 12 finalized source histories.
A separate cross-run composition produced one coarse recurring-work
hypothesis. It made no model calls and promoted nothing. That observation is
not a learned general procedure or a qualified harness patch.

Do not relaunch on a changing working tree. Bind a checked source snapshot,
the current task location, exact provider configuration, source identities,
and the declared experiment policy. Keep access checks out of task-success
denominators while including their calls and usage in total consumption.

## Declared per-cell work limits

`campaign_space` accepts explicit `model_call_limits` and `pass_limits` tuples.
Non-default levels become independent axes in the existing version 1.0.0
configuration-space contract, with a distinct content digest. `run_trial`
passes the selected values to `ModelExecution` and
`SolveRequest`. The worker reads the exact frozen `ConfigurationSpace` rather
than rebuilding it from current defaults.

The preparation command accepts repeated `--model-call-limit` and
`--pass-limit` options. Each accepts a positive integer or `unbounded`.
Omitting them preserves the legacy unbounded levels; the tool does not invent
a new spending authority. Worker invocations cannot override the frozen
levels with these flags. Future live campaigns need an explicit reviewed
resource policy rather than inheriting the old expensive configuration.

## Verification and private artifacts

Release `078fffc8da632a321e86d8660301ac633773bbb4` passed 4,710 of 4,710
checks from its exact committed source. A fresh wheel installation with the
optimization extra passed 4,664 of 4,664 checks. Neither source changed during
verification, and both runs made zero provider calls. The installed wheel
still excludes optional data and integration adapters listed in its command
record.

The final development laboratory passed 103 tests, including a later
checkpoint-binding correction: a valid prefix must actually contain each
claimed model-call occurrence. An earlier intact checkpoint cannot account
for a later call, including repeated semantic call identifiers. The regenerated
`flash-report-bound.html` applies this check to the real reference campaign.

The frozen source snapshot is based on `1a18e105acf17647cb02c953612cfa9c59215e6e`
plus this session's owned changes. Its full offline suite passed 4,709 of
4,709 checks with no source changes during the run. A wheel built from that
snapshot passed 4,664 of 4,664 checks in a fresh base installation. Both made
zero provider calls. The base installation omitted optional integration,
data, and optimization dependencies; those omitted adapters are not qualified
by its result.

The earlier working-tree suite failed two checks while another session edited
the adaptive request. One failure was the new unavailable-harness reason
code's old expected message, which was corrected. The other came from the
concurrent staged request change making frozen-source validation unreachable.
That staged version is excluded from the passing frozen snapshot. The owning
session corrected the validation before committing
`ba05d472c248d56689d008a88719a16938ea0d9e`; all 20 solve-adaptation checks
passed on the corrected source. The failed command remains preserved.

The development laboratory passed 101 tests after the per-cell work-limit
extension. A subsequent focused report check verifies a trillion-level
integer-range axis without enumerating its levels. This verifies the
projection, not a trillion executed experiments. An isolated installation
with Optuna 5.0.0 and cmaes 0.12.0 passed
15 optimizer controls covering Bayesian, evolutionary, and covariance
proposals, reproducibility, task-bound evidence, multiple objectives, and
unsupported categorical inputs. These are actual installed optimizer tests
with fixture observations, not live task-performance experiments. The first
optimizer command used the wrong summary key and failed after its checks;
the corrected command result is `optimization-extra-verified.json`.

A later full-suite attempt on the shared working tree encountered another
concurrent edit: the history checks expected `RunHistory.content_digest`
after an older class definition had already loaded. Its command record lists
the three changed source files. This mixed-source failure is preserved and
does not replace the isolated verification above.

Private artifacts are under
`.loop-engine-dev/fabric-readiness-20260913-N8fyhI/`:

- `source-audit-current-location/`: the complete prepared task population and
  source identities;
- `live-flash/`, `live-pro/`, and `live-pro-cancellation.json`: real reference
  attempts and the operator cancellation;
- `compact-flash-AE-001/`, `compact-flash-CS-001/`,
  `compact-pro-AE-001/`, and `compact-pro-AE-001-feedback/`: real compact trials;
- `independent-temporal-retest-v2/`: exact candidate and evaluator identities,
  sandboxed checks, and verified evaluation histories;
- `intelligence-review/` and `intelligence-review-cross-run/`: review records,
  selected history identities, exclusions, and the unpromoted hypothesis;
- `flash-report.html` and `flash-report-data.json`: the regenerated campaign
  grid, evidence gaps, unknown totals, and known subtotals;
- `flash-report-bound.html` and `flash-report-bound-data.json`: the same
  campaign after exact checkpoint-occurrence binding;
- `committed-source-self-test.json`, `committed-install-self-test.json`, and
  `laboratory-checkpoint-binding.json`: the final committed-source,
  installed-wheel, and development-laboratory checks;
- `frozen-self-test.json`, `clean-install-self-test.json`,
  `laboratory-final-v2.json`, `conformance-final.json`, and
  `repo-conformance-final.json`: command records and their source identities.

The report renderer passed offline checks and generated the real campaign
page. Browser visual inspection could not run because the computer-use
service reported that no browser was available. No visual qualification is
claimed. Historical failed verifier setup and verification commands remain
in the private artifact directory; they were not rewritten as successes.

## Evidence boundaries

Tests using an injected transport establish local contracts. They do not
establish provider integration, model quality, task success, or evaluator
independence. A successful real access check establishes access only. A task
needs its actual deliverables, independent evaluation, and verified history
before it contributes success evidence to configuration selection.

The [experiment-driven improvement guide](../guides/experiment-driven-self-improvement.md)
describes the intended review cycle. The [main advisory file](../../ASTRA.md)
preserves the complete behavioral explanation and the owner's dimension
requirements. Both remain subordinate to typed runtime contracts.

# Autonomous task feedback and current limits

Loop Engine can generate executable feedback and use it without a caller
supplying repair instructions. One live task completed this path, including
automatic recovery from a provider output-limit failure. Full autonomous,
general-purpose self-improvement is not established.

The [architecture decision](../architecture/ADR-INDEPENDENT-TASK-FEEDBACK.md)
defines the policy and ownership. The [structured evidence](../evidence/autonomous-task-feedback-2026-09-05.json)
references exact saved outcomes, histories, failures, and package verification.
It is a historical export, not a second operational store.

## Implemented behavior

`IndependentVerificationPolicy(required=True)` is the default for generated
projects through `SolveRequest` and the CLI. It remains separate from user
interaction mode and authority. A caller cannot obtain accepted generated
work by having the producing model call an unavailable checker advisory.

The verifier receives an isolated task and artifact packet. It plans probes,
generates their files, reviews the oracle in a separate call, and executes in
a read-only Docker workspace with no network. Expected values are compared
in the controller, outside the candidate process. Recorded failures enter the
existing verification, integration, and routing path. They are not fabricated
user feedback.

Operational checker failures stay separate from task defects. `RETURN_RESULT`
rechecks the existing project without regenerating files. A failed observation
completes one verifier activation; it does not replay that activation's effects.
Retained tests keep their code, arguments, inputs, and expected results.

Model calls use the existing shared accounting and reasoned recovery service.
No model-call, pass, total-token, or monetary ceiling was imposed on these live
launches. Provider capacity and exact effect authority remained enforced.

## Live observations

All four diagnostic runs used
`ollama_cloud / cloud.default / deepseek-v4-flash:0731`.

| Run | Outcome | Calls | Seconds | Observation |
|---|---|---:|---:|---|
| `adaptive-4afc171da4600f462bf191ef` | Operator-cancelled | Unknown total; 24 known | 608.770 | Checker output failure was followed by project rebuilding. |
| `adaptive-170c7c8259626a67e57f7e98` | Operator-cancelled | Unknown total; 21 known | 621.674 | Engine rechecked the same project, but checker generation repeatedly exhausted output capacity. |
| `adaptive-c5daa1227334a792a0a454c3` | Operator-cancelled | Unknown total; 30 known | 848.885 | Checker planning succeeded, but one file response used a Python fence where JSON was expected. Further provider failures remained. |
| `adaptive-b3adcefbff5a2c0f8f7bc5c0` | `COMPLETED_VERIFIED` | 13 | 231.192 | Engine-generated checker, automatic provider recovery, and independent execution completed without supplied feedback. |

The canceled runs remain intact and are not counted as autonomous successes.
They were stopped while reproduced runtime defects were being corrected,
not at a numeric call ceiling.

The completed seconds-conversion task used one pass and one project attempt.
Its own three unit tests passed. The independent checker imported the actual
function and observed `(0,0) -> 0`, `(1,0) -> 3600`, `(1,30) -> 5400`, and
`(2,15) -> 8100`. Its one batched comparison also checked file presence,
assertion count, and unittest exit status. No solution-code repair was needed
in this completed live case.

The checker initially exhausted the actual 65,536-token provider output
capacity. The engine's Recovery Loop chose a retry, which retained the full
65,536-token capacity and succeeded. The verifier used five physical calls:
failed design, recovery decision, successful design, file generation, and
oracle review. Total run usage was 121,034 input and 84,269 output tokens,
205,303 total, with complete accounting. Invoiced cost was not retrieved.

The canonical saved-run verifier confirms 1,017 events, an intact chain, and
a bound `COMPLETED_VERIFIED` outcome. The event head is
`2ff12e833801d5361e800e40c34df260aaa82ead43e9ab8b5d6dc3a2f7652895`.
The bound product digest is
`3a4fcfbfceee8cea535c3749ca4fe9a908a9dd3aa8395cb52fa4c9ba1f2a2754`.
Embedded history snapshots were captured before final binding and still say
unbound; use the canonical saved-run verification rather than those stale
snapshots. This reporting limitation remains open.

The [exact implementation, tests, and generated checker](../evidence/autonomous-feedback-20260905/README.md)
are published for inspection. They are not promoted capabilities or unseen
holdout tasks.

## Offline proof and fixes

The public two-pass fixture supplies no `TaskFeedback`. Producer tests pass
on a defective implementation; the independent probe observes a counterexample;
the next model fixture sees that actual failure and repairs the implementation;
the retained probe then passes. A second fixture rechecks unchanged artifacts
after checker unavailability, without another project execution. These use
injected model responses and do not establish live semantic-repair quality.

Focused verifier checks pass 123/123. They cover malformed or forged output,
empty checks, wrong paths, changed source, scope drift, exact report binding,
isolated context, shared accounting, reasoned retry, and retained probes.
Real Docker checks also confirmed that attempts to overwrite the subject and
checker fail with `EROFS`, while the disposable `/tmp` remains writable.

Final frozen verification passed 3,043/3,043 source tests, 2,998/2,998 applicable
clean-base-wheel tests, and 27/27 conformance gates in each environment.
Build, offline installation, dependency checks, CLI help, and all 478 runtime
file comparisons passed. Seven optional adapter families were explicitly
untested in the base installation. These checks made no provider calls.

The completed live run loaded the earlier unbounded file-read implementation.
A final guard limits a snapshot read to its stated file size plus one byte.
That guard and later test additions were verified in the final frozen package;
the live run is not claimed to have executed those later bytes. No generated
solution or checker file was manually edited.

Earlier package checkpoints and conformance failures remain separate from
final evidence. The verifier's ambiguous instruction boundary was corrected,
but a normal planning call also exhausted output capacity. These observations
do not establish that the prompt change alone caused better model behavior.

## What remains unproven

Task-local repair is not persistent self-improvement. Automatic capability
qualification and promotion, safe core self-modification, restart-safe
continuation, and broad held-out improvement still need their own execution
and acceptance paths. A proposer cannot approve its own permanent changes.

The oracle is model-generated and fallible. Same-model calls with isolated
context do not prove statistical independence. A wrong oracle or genuinely
changed interface still needs independent requalification. Partial checker
files survive as artifacts, but failed multi-file generation does not yet
resume automatically from a structured pending checkpoint.

The separate CI hardcoding audit remains unresolved; its baseline was not
replaced. No Kaggle data was downloaded or submitted and no Kaggle grade was
obtained. The next useful proof is a frozen mixed-task population in which
engine-generated counterexamples cause live solution repairs, followed by
independent holdout evaluation and restart recovery.

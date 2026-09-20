# SemIf, Circuit and typed decision readouts

Kind: dated primary-source review, not a local model benchmark. Inspected
`TheoLeeCJ/SemIf` at `ca3ba65f142967030ecb453346e94d6f476a69df` on September 19,
2026. This is the formerly OpenJev project matching the supplied 21-decision
timing claim. Several unrelated repositories also use OpenJev in their names;
their interfaces and evidence must not be combined.

## Answer

Much of the interface can be achieved with an existing model and a different
readout. SemIf demonstrates that approach. It does not establish a new
transformer architecture, reproduce Jev's private training, or turn uncalibrated
scores into reliable decision confidence.

The engineering distinction is useful: score the permitted alternatives and
return typed data, without making the model generate an answer string. Model
quality, training, calibration, serving efficiency and operational correctness
remain separate questions. A model can emit a perfectly valid distribution
and still choose an inappropriate action.

## What the implementation does

SemIf's direct path uses a frozen causal language model. It renders the state,
criterion and option descriptions, assigns options to uppercase answer slots,
runs the model, selects those slots' final-position logits and normalizes them.
It checks that each slot is one exact token and that appending it does not
change boundary tokenization. Oversize input is refused rather than truncated.
[Direct scorer](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/src/semif_phase1/direct.py).

For allowed options A and B, the conceptual readout is:

```text
score(A) = exp(logit(A)) / (exp(logit(A)) + exp(logit(B)))
score(B) = 1 - score(A)
```

This is conditional on the supplied alternatives. If both are wrong, one
still wins. Adding an insufficient-evidence choice can help express abstention,
but does not prove that the model uses it correctly. The score is also not a
replacement for a deterministic permission or safety check.

The inspected input validator supports 2 to 16 described options. Semantic
option identities remain outside the displayed letter mapping. Prompt wording,
option ordering, tokenizer behavior and exact model revision are therefore
part of the implementation being evaluated, not irrelevant formatting.
[Input and prompt contract](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/src/semif_phase1/core.py).

Its shared-state path verifies an identical state and matching token prefix,
prefills once, replicates the native cache across branches and evaluates the
question suffixes together. That is not one free decision over unlimited
context: prefill, branch memory, padding and suffix computation still cost
resources. It is more precise to say it avoids autoregressive answer decoding.
[Shared scorer](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/src/semif_phase1/shared.py).

## What the reported timing means

The author reports a median 1.023 seconds for 21 binary decisions, against
5.332 seconds and 111 generated tokens for a compact answer array, with the
same frozen Qwen3.5-4B on one RTX 3090. The paths agree on 18 of 21 choices.
The faster result is therefore not proof of equivalent semantics or accuracy.

On the separate 777-decision shared-state workload, parallel suffix scoring
reports 20.03 decisions per second versus 2.33 for fresh scoring. Five to six
argmax decisions change in the cache-reuse variants. The author labels them
experimental. Published Jev results were reused for a selected 102-row
comparison; the author did not call Jev live. That subset does not establish
general equivalence to Jev.
[Results](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/docs/RESULTS.md).

The documented timed region includes prompt preparation, tokenization,
transfers, inference and readout, but excludes model loading and result-file
writes. It is a warm-loaded systems experiment. Do not compare it directly
with another vendor's endpoint latency, startup time, throughput or price.
[Method](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/docs/METHOD.md).

## Compare the three decision approaches

| Axis | Jev | Circuit | SemIf |
|---|---|---|---|
| Inspected availability | Closed provider service | Open adapter and decision head over an open base | Open scoring code over existing frozen models |
| Readout | Provider's typed decisions; internals not established here | Trained pointer head scores declared alternatives | Existing final-position vocabulary logits restricted to answer slots |
| Training assumption | Provider claims; not reproduced here | Published supervised adapter/head recipe | Direct baseline does not require task-specific fine-tuning |
| Confidence | Provider-reported; still needs workload validation | Distribution and entropy-derived concentration need validation | Explicitly labeled conditional, uncalibrated option scores |
| Integration reviewed | Hosted System One API | System One-compatible service | Python library, command-line scorer and browser demonstration |
| Our current state | Client adapter with local checks | Configured compatible client with local checks | Research candidate; no SemIf service adapter or quality trial |

The [Circuit review](CIRCUIT-DECISION-ENGINE-REVIEW-2026-09-19.md) retains its
separate source pins. SemIf's own description says it reproduces an interface
pattern, not Jev's undisclosed model or training. Its code is MIT licensed;
the selected models retain their own licenses.
[SemIf repository](https://github.com/TheoLeeCJ/SemIf/tree/ca3ba65f142967030ecb453346e94d6f476a69df).

A different readout is not the same as a decision policy trained from
environmental rewards or a model that plans multiple future actions. It can
be one implementation inside a larger reasoning system. Generative reasoning
remains useful when the alternatives or required evidence have not yet been
constructed, and independent checks remain necessary after acting.

## Implications for our wrappers

SemIf belongs behind the existing decision-provider interface, not inside each
harness as an independently loaded model. The customer or service operator
owns its model process. Loop Engine would consume a supported endpoint and
authentication reference, as the owner requested.

The inspected package exposes `semif-score` and Python functions; this review
did not find a hosted HTTP service or a System One route in the declared
package. Its records differ from Jev: option identities, raw logits,
probabilities, prompt identity and model metadata, rather than the same
question-batch answer envelope. Do not advertise that changing a URL alone
connects the upstream package to our current System One adapter.
[Package](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/pyproject.toml),
[command boundary](https://github.com/TheoLeeCJ/SemIf/blob/ca3ba65f142967030ecb453346e94d6f476a69df/src/semif_phase1/cli.py).

A future adapter needs an actual externally operated service contract. It
must preserve the uncalibrated-score designation, not invent a confidence
value from the highest probability. Our current Choice and Score admission
expects a confidence scalar, which is a known generalization gap for this
provider. Represent absent confidence and its basis explicitly in a reviewed
contract update before admitting SemIf, rather than forcing it into a misleading
field. Existing callers must negotiate that contract version.

Keep serving strategy independent from provider selection. Fresh scoring,
serial prefix reuse, parallel branches and precision are configurations that
can alter both cost and results. A cache must be bound to exact state, model,
tokenizer, prompt, tenant and authority. Never share context across tenants
merely because a semantic fingerprint is similar.

## Qualification proposal

Use the same fixed tasks across Jev, Circuit, SemIf and a generative baseline.
Include precise routing, insufficient evidence, plan coverage, compatibility
selection and misleading retrieval candidates. Keep deterministic eligibility
and authorization outside model discretion.

Test reversed options, semantically equivalent descriptions, distractor
context, contradictory evidence, an absent correct choice, near ties,
multilingual inputs and long states. Compare fresh scoring with shared-state
paths and changed batch sizes. Quantized browser models need their own quality
evaluation; native-precision results do not transfer automatically.

Measure task success, calibration where meaningful, abstention errors, ranking
quality, drift, warm and cold latency, memory, aggregate endpoint costs and
physical requests. Do not collapse retrieval ranking and categorical judgment
into one accuracy metric. Keep failed, unavailable and uncalibrated outcomes.

The initial recommendation is a research baseline and later optional endpoint
adapter. It is not a release blocker and not a reason to replace all reasoning
with forced-choice scoring. No model weights were downloaded, no service was
started, and no reported timing was reproduced during this review.

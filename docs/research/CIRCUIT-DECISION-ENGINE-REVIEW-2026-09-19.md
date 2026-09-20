# Circuit decision-engine review

Kind: dated primary-source review, not an installed model or a local benchmark.
Checked September 19, 2026. The forwarded LinkedIn short link could not be
opened. The model card, model metadata and upstream implementation were read
directly instead. No weights were downloaded and no model was executed.

Implementation follow-up: the [decision endpoint guide](../guides/jev-and-harness-decision-tools.md)
describes the configured Circuit-compatible client adapter. Direct and protocol
tool paths have local fixture checks. This does not change the model-quality
findings below. Customers supply existing endpoints and authentication;
Loop Engine does not operate or launch model services.

## Recommendation

Trial Circuit-8B as a separately configured local decision provider behind
the existing typed gateway. Also evaluate Circuit-1.7B for machines where the
larger model is impractical. Keep Jev and other registered implementations as
alternatives. Do not make either Circuit model a production default from these
published results alone.

This is a close interface match: the project implements Choice, Score and
Noul questions through `POST /v1/systemone`. Its implementation uses a
low-rank adapter and a pointer readout head rather than generating an answer
token by token. That makes it more directly relevant than a generic language
model with a request to emit JSON. [Project](https://github.com/Barneyjm/circuit/tree/91117b9a23e27af87c2810f8265ed1da32211e92).

## Exact sources

| Source | Inspected revision |
|---|---|
| `jbarney/circuit-8b` | `7ade75db53428a960c7f0d0caa98f528dcc23346` |
| `Barneyjm/circuit` | `91117b9a23e27af87c2810f8265ed1da32211e92` |
| Base named by the adapter | `Qwen/Qwen3-8B-Base`; the adapter configuration does not identify an exact base revision |

The model repository declares Apache 2.0 for the adapter and head and names
Qwen3-8B-Base as its dependency. The small adapter download is not the complete
model. The author reports about 17 gigabytes for the base in bfloat16, or use
of four-bit loading on a 12-gigabyte graphics card. Those are author-reported
resource statements, not measurements on our machines.
[Model card](https://huggingface.co/jbarney/circuit-8b/blob/7ade75db53428a960c7f0d0caa98f528dcc23346/README.md),
[base model](https://huggingface.co/Qwen/Qwen3-8B-Base).

## Evidence limits

The author's comparison reports both accuracy and calibration error, with
failures and earlier experiments retained. It reports better Circuit-8B
accuracy on some classification tasks and better Jev results on other tasks.
Several public task families are present in Circuit's training mix, so those
rows do not establish equal generalization conditions. The 546-question
production comparison measures agreement with Jev, not independent correctness.
The timing rows mix API latency, different hardware and batched per-item
measurements; they are not a deployment-cost comparison.
[Evaluation record](https://github.com/Barneyjm/circuit/blob/91117b9a23e27af87c2810f8265ed1da32211e92/docs/cold-eval.md).

The model card explicitly identifies overconfidence on undecidable inputs and
limits its intended use to research and evaluation, not production decisions
affecting people. Training probabilities with cross-entropy is not proof that
they remain calibrated for planning, code selection, or our task population.
It is also not a system that learns from our later outcomes automatically.
The released recipe is supervised decision and classification training. It
does not establish a learned multi-step planning policy or general reasoning
ability from environment rewards.

## Integration findings from source

| Finding | Implication for Loop Engine |
|---|---|
| `service.py` selects its scorer at startup; the request's `model` field does not select it. | Verify the returned model identity and bind the endpoint to a pinned deployment. Do not assume a requested name selected the intended weights. |
| The server accepts a bearer header without verifying its value when `S1_API_KEY` is absent. | Require configured authentication and keep the service on a controlled interface. Never expose that default as an authenticated public service. |
| The server sums input-token counts across separately rendered questions. | Preserve its reported accounting; do not assume Jev's batching costs or billing units apply. |
| Confidence is computed from normalized distribution entropy. | Preserve the stated confidence basis. Do not equate that scalar with independently measured correctness probability. |
| The request schema caps Choice at 255, despite broad wording about the pointer head having no option cap. | Negotiate actual service limits, not an architectural claim about the neural head. |
| The scorer defaults to `fake` when no model is configured. | Refuse unconfigured and synthetic deployments before admitting results as model evidence. |
| The adapter scorer defaults to 4,096 tokens and left truncation. Training metadata records 1,024 tokens. | Detect or refuse omitted context. Do not advertise Jev-sized context or assume the base model's nominal window establishes reliable long-context decisions. |
| The scorer loads a base model, adapter and `head.pt`, while the package includes training, audio and vision dependencies. | Pin and review the serving environment separately. Do not install the entire research stack into the lightweight Loop Engine service. |

Sources: [service](https://github.com/Barneyjm/circuit/blob/91117b9a23e27af87c2810f8265ed1da32211e92/s1proto/service.py),
[schema and confidence](https://github.com/Barneyjm/circuit/blob/91117b9a23e27af87c2810f8265ed1da32211e92/s1proto/schema.py),
[scorer](https://github.com/Barneyjm/circuit/blob/91117b9a23e27af87c2810f8265ed1da32211e92/s1proto/scorer.py),
[training configuration](https://huggingface.co/jbarney/circuit-8b/blob/7ade75db53428a960c7f0d0caa98f528dcc23346/config.json),
[package dependencies](https://github.com/Barneyjm/circuit/blob/91117b9a23e27af87c2810f8265ed1da32211e92/pyproject.toml).

## Proposed qualification

Connect to an existing customer- or provider-operated service. Its operator
owns capacity, model loading, context handling and service lifecycle. Do not
load an eight-billion-parameter model into the engine process or once per
harness instance. Give the Circuit endpoint its own credential reference. Never redirect a TypeSafe
credential to a different provider merely because its wire format is similar.

Keep Loop Engine's existing route, effect, budget and independent-acceptance
rules. Adopt only the provider interface initially, not the upstream workflow
language as another runtime. Self-improvement remains a Practitioner task
that proposes candidates for independent review.

Freeze real cases for choosing a continuation, selecting Code Intelligence,
ranking context, identifying insufficient evidence and reviewing plan coverage.
Include ambiguous cases, absent correct alternatives, contradictory sources,
long states and changed option order. Compare the same cases through direct
and harness-tool paths. Measure downstream success, calibration, refusals,
latency, memory, total cost and missing accounting separately.

A passing protocol test is only the first gate. Do not infer broad reasoning
quality, production suitability, privacy, model availability or useful learning
from a compatible response schema.

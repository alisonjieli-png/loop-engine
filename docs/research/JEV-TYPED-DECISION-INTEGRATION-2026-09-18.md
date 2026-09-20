# Could a typed-decision model such as Jev help, and does the architecture admit it?

Date: 2026-09-18. Owner question: if we wanted to implement Jev to help
with reasoning and decisions, could that help, and do we have the
architecture to integrate other models, endpoints, and model types?

Current implementation follow-up, September 19: the
[decision-tool operating guide](../guides/jev-and-harness-decision-tools.md)
now describes the implemented typed adapter, gateway, session and local
protocol tool. These paths have local contract checks, not live Jev quality
evidence. The original September 18 observations below remain historical.

## What Jev is, as verified on 2026-09-18

TypeSafe describes Jev as a "System One Model, optimized for automation"
that accepts "structured questions" and returns "typed decisions with
probabilities and confidence that your software can act on," so that
software can "act when confidence is high and escalate when it is not."
The published price is $42 per billion input tokens with output free; the
landscape record read the version `jev-1.13.0` behind the aliases
`jev-latest` and `jev-preview`, a 64,000 token context, text only, and no
open weights. Access is early access; the interface details were not on
the page read. The vendor's speed and cost comparisons are the vendor's
claims and were not measured here.

## Where it would fit

```text
Places a typed-decision model serves
├── the efficiency review judge: rank alternatives with a confidence (S-2.1)
├── the implementation decision judge when ledger evidence is thin (S-1.6)
├── the escalation answer for a low-confidence conformance cell (bounded candidates)
├── the criterion judgment when a rubric is a closed choice
├── route and step selection: which registered method next, with a probability
└── a calibrated probability source for the reuse rung: reuse, modify, or fresh
```

Each of these is a bounded question with a closed answer shape and a
confidence, which is what the engine already asks for through
`SuggestedOutput` (ranked list, unit-interval confidence, abstention
allowed) and the registered response contracts. That is the case for it:
a model built to return a typed decision matches contracts the engine
already declares, at a lower input price than a text model, without the
engine changing what it asks.

## Whether the architecture admits it

| Boundary | What it needs | Present |
|---|---|---|
| Model ontology | A kind for judgment and classification, an output kind of probability or label, a remote endpoint placement, vendor provenance, a qualification state | Yes: `ModelProfile` with `MODEL_KINDS`, `OUTPUT_KINDS` including probability and label, `PLACEMENTS` including remote endpoint, `QUALIFICATION_STATES` starting at candidate |
| Model call boundary | One typed request naming purpose, kind, contract, suggested output, and determinism expectation | Yes: `ModelCallRequest`; a text-servable request becomes the text invocation and any other kind is refused by name until a route serves it |
| Provider adapter | A client for the vendor endpoint declared in the network allow list, with secrets by reference | Pattern exists: `core/custom_endpoint` for OpenAI-compatible endpoints and the provider clients; a Jev adapter would be one more, added to `network_allowed_modules` |
| Route declaration | A `ModelRoute` with the profile, purposes, and tier | Yes: `ModelRoute.profile` is the typed field added on 2026-09-18; no route declares a judgment profile yet |
| Contract matching | The decision compared by purpose or blocked semantics, not bytes | Yes: `core/contract_matching` modes |
| Judge kinds | The efficiency review and implementation decision record who judged | Yes: `judge_kind` in both records, with specialist and model values |
| Evidence and cost | Every call recorded with digests and cost, unknown counts unknown | Yes: learnable call records and operation cost records; gateway cost capture is a follow-up |
| Qualification | A candidate until independent review | Yes: the candidate state and the heuristic adoption policy for any learned routing |

So the answer is yes on both counts. The architecture was built so that a
model is a route with a profile behind a typed call, and a typed-decision
model is the easiest kind to admit because its output is already the shape
the contracts ask for. What is missing is work, not design:

1. A provider adapter for the vendor endpoint (network-allowed, secrets by
   reference, usage preserved).
2. A route declaring a `ModelProfile` of kind judgment with output kinds
   label and probability, placement remote endpoint, provenance vendor.
3. A gateway path for non-text output kinds, so a probability response is
   admitted against its contract rather than parsed from prose.
4. A fixture suite of bounded decisions with known answers, so the model
   is evaluated with exact denominators before any live use.
5. Cost capture on gateway calls, so the avoided-model-call meter can
   compare a typed decision against a text call honestly.

## What would count as help

Help is measured, not assumed: on the efficiency review and the escalation
answer, a typed-decision route must reach the same verified outcomes as
the text route on the frozen suite with fewer tokens or less time, judged
by the evaluation product, before the implementation decision may prefer
it. The heuristic adoption policy applies if any learned routing follows.

## Beyond Jev

The same five pieces admit any model type the ontology names: an
extractor, a reranker, an embedding model, a tabular foundation model, or a
custom-trained specialist served as a local endpoint. The specialist
trained on 2026-09-18 is the first in-house instance: it is a candidate
resolver today and becomes a route with a profile when it is served.

## Addendum, later on 2026-09-18: Jev Ultrafast and typed action decisions

The owner pointed at Jev Ultrafast from browser-use and asked whether the
engine needs out-of-the-box core support for it. Facts read from the
repository on 2026-09-18 (`https://github.com/browser-use/jev-ultrafast`,
created 2026-09-16, MIT license, 5,345 stars at the time of reading):

- The model receives an element table of indexed controls, one line per
  control with the index, the control type, the label, and the current
  value, for example `[3] combobox  Where to?  · empty`, instead of a
  screenshot.
- One network round trip returns the operation (click, type text, select,
  scroll up, scroll down, wait, done, or blocked) and the target element;
  when the operation types text, a small text model produces the text.
- Waits are adaptive: up to 200 milliseconds for suggestions after typing
  into a combobox, otherwise at most two animation frames or 50
  milliseconds.
- The timing claim reads, in the authors' words, "Zürich → London on Google
  Flights in 7.1 seconds. One natural-language goal, actual text
  generation, and loading waits included." The authors also state that the
  measurement is "three repeats of one task on one browser profile, not a
  general reliability benchmark."
- It needs a TypeSafe API key, a text model key, and Chrome with remote
  debugging; it does not handle shadow roots, frames, canvas, file uploads,
  pop-up tabs, nested scrolling, or arbitrary keyboard widgets; and the
  authors state that the done choice "requires independent outcome
  verification".

What Loop Engine holds after this addendum:

- `core/typed_action_decision.py`: an element table with indexed rows and
  the same text rendering, a declared action vocabulary (the browser
  vocabulary above is the packaged default, and a caller declares its
  own), a bounded request that refuses a table above its declared row
  ceiling, admission under the registered `typed_decision.action` contract
  that refuses an operation outside the vocabulary, a target outside the
  table, a typing operation without text, and a finishing operation with a
  target, and a decision record whose confidence is the weaker of the
  operation and target confidences and which marks a done or blocked
  decision as still needing independent verification. The judge is
  injected exactly as for typed decisions, the call passes the same route
  screen, and one model call record and one cost record are written per
  decision. Nothing in the engine performs the action.
- The typed-decision route from earlier the same day (`core/typed_decision`)
  for bounded choices of at most ten candidates; the action contract exists
  because an element table is far wider than a choice.

What stays open, and what only the owner can supply:

- A live TypeSafe adapter behind the gateway needs a key the owner
  authorizes; until then the route is exercised with fixture judges only.
- Performing the chosen action is an effect: a browser act adapter with
  declared effects, a page reader that builds the element table, and the
  adaptive waits belong to a harness adapter (roadmap S-2.21), not to core.
- The done decision is a claim; Loop Engine's independent verifier owns
  acceptance, which matches the authors' own statement.

# Typed decisions behind the model call boundary

A typed decision answers one bounded question: which of these candidates,
with what probability for each, and how confident overall. Loop Engine
serves such answers through the same model call boundary as every other
model kind, so a small in-process specialist, a remote judgment service
such as a Jev-class provider, or a fixture judge in a check all enter the
same way and leave the same records.

```text
Typed decision
├── TypedDecisionRequest
│   ├── question, at most ten unique candidates, evidence parts
│   └── response contract typed_decision.choice
├── Route
│   └── a ModelRoute with a judgment profile declaring label and probability outputs
├── Judge (injected)
│   ├── SpecialistJudge: a trained naive Bayes specialist in process
│   └── EndpointJudge: a provider body mapped through an injected transport
├── Admission
│   ├── rows name exactly the declared candidates and sum to one
│   ├── the choice is the top row, or an abstention names no choice
│   └── a request that did not name the contract is refused
└── Records
    ├── ModelCallRecord: digests, counts, the suggested output check
    └── OperationCostRecord when a ledger is given
```

## Ask a question

```python
from loop_engine.core.model_routes import ModelRoute
from loop_engine.core.typed_decision import TypedDecisionRequest, SpecialistJudge, decide

request = TypedDecisionRequest(
    "Which column holds the invoice total?",
    candidates=("total", "amount", "sum"),
    evidence=("columns: id, amount, total, note",))
judge = SpecialistJudge(specialist_model)
outcome = decide(request, judge.route("judge.specialist"), judge)
print(outcome.decision.chosen, outcome.decision.probabilities, outcome.decision.confidence)
```

`decide` validates the route, passes the same route screen as every model
call, calls the judge, admits the answer, and returns the decision with its
model call record and, when a cost ledger was given, its cost record. A
refused admission ends the cost capture as failed and raises a typed error.

## Connect a provider

A provider that returns typed decisions enters as an `EndpointJudge` whose
transport is a callable the caller supplies. The transport is a declared
network adapter outside this module; the module itself never opens a
connection. The field map that turns the provider's body into the contract
shape is data, so a new provider is a new map, not a new branch.

```python
from loop_engine.core.typed_decision import EndpointJudge

judge = EndpointJudge(transport, provider="typesafe", model="jev-1.13.0")
outcome = decide(request, judge.route("judge.remote"), judge)
```

No live provider route is declared on 2026-09-18. Declaring one needs a
key the owner authorizes and a network adapter under the existing gateway
rules; the record shapes do not change.

## Score a judge

```python
from loop_engine.core.typed_decision import TypedDecisionCase, TypedDecisionSuite, evaluate_judge

suite = TypedDecisionSuite("invoice-columns", "1.0.0", (TypedDecisionCase("case-1", request, "total"),))
report = evaluate_judge(suite, route, judge)
print(report.total, report.decided, report.correct, report.wrong, report.abstained, report.errored)
```

The report keeps exact denominators: total equals decided plus abstained
plus errored, decided equals correct plus wrong, accuracy over decided
cases is unknown when nothing was decided, and a judge that raises is
errored, never correct.

## What this does not claim

The specialist judge is a candidate until the admission ladder qualifies
it, and its probabilities are normalized scores, not calibrated
probabilities. No vendor's accuracy or speed is assumed. Where a typed
decision should replace a text judgment in the Practitioner's route,
verify, or criterion steps is roadmap work under the model-versus-not
decision, measured with the typed decision suite before any step changes.

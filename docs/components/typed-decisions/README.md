# Typed decision engines

Kind: component explanation for `src/loop_engine/core/decisions`.

A model call that returns free text and a model call that returns one label
from a closed set are different operations. This component owns the second one.
It sends typed judgment requests to a configured decision endpoint and admits
the answers against the question identities that were asked.

The registered operational boundaries are `typed decision provider invocation`,
whose envelope is `core.decisions.gateway.invoke_decisions`, and
`decision station judgment`, whose envelope is
`core.decisions.stations.decide_station`. The provider adapter and the passive
request are not graph vertices. The model gateway's model attempt Loop owns
each physical invocation, a station decision is owned by the step's
Practitioner Loop, and the application facing tool in
`code_nodes/decision_tools.py` owns its request through a Practitioner Loop.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

## What this component owns

```text
Typed decision execution
├── Contracts
│   ├── decision_batch_request/v1, explicit question identities
│   ├── decision_batch_result/v1, normalized typed answers
│   └── typed_decisions/v1, the negotiated provider capability
├── Configuration
│   ├── decision_host_configuration/v2, named engines and ordered routes
│   └── secret references resolved at use, never at discovery
└── Transport
    ├── one bounded endpoint request for each attempt
    └── the shared question wire serialization
```

Decision stations sit on top of the same contracts. In a coding step one
station builds: the harness that writes code. The others are typed judgments
with a small answer space, asked at fixed loop points and answered by
swappable engines of the `typed_decision` slot.

```text
Step loop and its stations
├── before_step: does this request carry the indicators of a written
│   screening policy, which action follows, how severe? (built: request
│   screening)
├── before_step: which files to read, which model gets the step (planned)
├── build: the step executor writes code (the step_executor slot)
├── before_command: may this command run without a person? (built)
├── after_step: is the task done, read from fresh test output (planned)
└── at_compaction: keep or drop each tool output (planned)
```

Three engine kinds sit behind the slot: `decision_endpoint` (the TypeSafe
Jev and System One adapters), `deterministic_rules` (the in-process rules
engine) and `text_model_json` (a text model that answers the typed questions
as one JSON object, read strictly and admitted like any other answer).

The package must not import the application tools, the command dispatcher or
`code_nodes`. It contains no provider discovery registry, no permission store,
no task scheduler and no Run History of its own.
`loop_engine.core.model_gateway.ModelGateway` remains the provider registry and
route policy boundary, and the existing model session owns cumulative call
accounting.

## Typed inputs and outputs

`decision_batch_request/v1` carries explicit question identities and one
immutable input snapshot. `decision_batch_result/v1` returns normalized typed
answers. `typed_decisions/v1` is the provider capability the gateway
negotiates. A provider must declare the question kinds it supports and
implement both preparation and one attempt invocation.

The command reads `decision_host_configuration/v2`: named engines, their
settings, ordered route names, a session allowance and explicit failover. The
shipped profiles are `jev`, `circuit` and `system_one`. The last two use the
same standard question wire contract and differ only in the reported engine
label. An embedded host may supply its existing model gateway instead.

Endpoint settings name the exact address, the reported model identity, a
separate credential reference, request and response byte allowances, and an
optional operator supplied deployment digest. Secure transport is required
except for an explicitly allowed numeric loopback address.

## The command safety station

`decide_command_safety` asks two typed questions about one command: may it run
without a person, and could it cause an effect that cannot be undone. The
answering engine is taken from a `StationPolicy` in declared order. The
built-in engine is `RulesDecisionEngine`, which reads the command risk policy
in process and counts no model call.

The station then applies its own guards from `assess_command`, whatever the
engine answered:

| Guard | When it holds the command for a person |
|---|---|
| `irreversible_waits_for_a_person` | The policy sees an effect that cannot be undone, such as a delete without a declared snapshot, a forced push or publishing. |
| `effect_not_granted` | The command has an effect the step does not hold, such as network access under a workspace grant. |
| `command_not_fully_readable` | The program is computed at run time or the command does not parse. |
| `engine_judged_not_safe` | The engine's probability that it may run is below the station threshold. |
| `engine_judged_irreversible` | The engine's probability of an irreversible effect reaches the station floor. |
| `no_engine_answer` | No engine returned an admitted answer, so the safe default binds. |

An engine can therefore only make the station stricter. A result carries
`authority_granted` and `task_accepted` as false, and any advisory guidance an
engine returns stays in `advisory`, apart from the binding decision.

Judge one command from a shell, or from a harness hook:

```bash
loop-engine decisions command-safety --command "git push --force origin main"
loop-engine decisions command-safety --hook claude_code < pre-tool-event.json
```

The first form prints `decision_station_result/v1` and exits 0 for a command
that may run and 2 for one that must wait. The hook form reads a pre-tool
event and only ever narrows: it answers "ask" for a command that must wait and
nothing for one that may run, so the harness's own permission rules still
apply.

## The request screening station

`decide_request_screening` asks three typed questions about one request a
step received, from a written `request_screening_policy/v1`: the probability
that the request carries the policy's indicators, the next action from the
policy's closed set, and the harm severity on the policy's ordered levels.
The policy is data: the questions, the actions, the levels, the thresholds
and bounded written patterns. The station holds no domain knowledge, so the
same station screens for any harm a policy describes.

The binding decision is `proceed` or `hold`, and `hold` is the safe default.
The station only narrows, whatever the engine answered:

| Guard | When it holds the request |
|---|---|
| `engine_judged_indicators_present` | The engine's own indicator probability reaches the policy threshold. |
| `engine_chose_not_to_proceed` | The engine chose an action other than the policy's proceed action; that action binds. |
| `engine_judged_harm_at_or_above_floor` | The engine's severity score reaches the policy's floor. |
| `no_engine_answer` | No engine returned an admitted answer; the policy's default action binds. |

When the request is held, the bound next action is the engine's own when it
is not proceed, and the policy's default action otherwise. The rules engine
answers this station from the policy's written patterns alone; a text model
engine answers from the state; Jev answers through its endpoint. The decision
red team of `tools/red_team_decisions.py` scores every engine on the same
frozen scenarios (`case-studies/decision-red-team-modern-slavery`).

The text model engine, `TextModelDecisionEngine`, wraps one bound text call
and reads the last JSON object of the reply. Level labels become level
indexes, a choice or level left out of a distribution gets zero mass, and a
distribution whose sum drifts by rounding is renormalized; each repair is
named on the engine. Anything else the model got wrong is refused at
admission with the contract's own code, and a failed call is a typed failure.
The text beside the answer stays on the engine as `last_text`; it never
binds. A text model engine serves only in a declared trial until a measured
comparison qualifies it.

Run the checks:

```bash
PYTHONPATH=src python -c \
  'from loop_engine.core.decisions.screening_station import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src:tools python -m unittest tools.test_red_team_decisions -v
```

## Refusals

`invoke_decisions` refuses before contacting a provider. Each refusal is an
exact code on the returned `ModelGatewayResult`, or a raised
`DecisionProtocolError`.

| Code | What it means |
|---|---|
| `typed_decision_request_and_configuration_required` | The call did not supply a typed request and a gateway configuration. |
| `owning_loop_required` | No canonical Loop owns the invocation. |
| `typed_decision_token_bound_unavailable` | The caller set a token bound that this structured protocol has no field for. The bound is never silently dropped. |
| `explicit_decision_route_required` | The configuration did not select the decide purpose and an explicit route. |
| `no_eligible_route` | No configured route survived the gateway's route policy. |

The third one is the important one. The structured protocol carries no
generation allocation field. Rather than invent an output capacity or ignore a
caller's hard token bound, the call refuses and says which it was.

## How to check it

```bash
PYTHONPATH=src python -c \
  'from loop_engine.core.decisions.contracts import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src python -c \
  'from loop_engine.core.decisions.jev import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src python -c \
  'from loop_engine.core.decisions.system_one import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src python -c \
  'from loop_engine.core.decisions.stations import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src:tools python -m unittest tools.test_decision_engine_boundary -v
PYTHONPATH=src:tools python -m unittest tools.test_decision_station_cli -v
```

The station checks run every guard twice: against the real code, where the
check must pass, and with that guard removed, where the same check must fail.

The three self tests exercise the local contracts, the real serializer, real
protocol messages and the canonical gateway with injected provider fixtures.
The unit test enforces the package's dependency direction, so application code
cannot be imported from inside the core package.

Inspect a host configuration without resolving a key or calling a provider:

```bash
loop-engine decisions inspect --config /absolute/path/to/decision-host.json
```

## Current behaviour and what is not established

Inspection resolves no credential and makes no provider call. Evaluation
requires a versioned request file. Serving exposes decision tools over standard
input and output for a host launched harness integration.

No local fixture establishes live endpoint availability, model quality, native
harness loading, global credential isolation or budget sharing across
processes. Context truncation, token capacity and deployment identity remain
unverified unless the provider establishes them; a transport byte limit is not
a token limit.

## What it deliberately does not do

- It does not install, download, launch, restart or supervise a model server.
  It connects to an endpoint that already exists, under the supplied authority.
- It does not treat a text generation endpoint as a decision endpoint because
  of its model name.
- It does not let configuration import code or construct an unknown adapter.
- It does not retry or fail over unless the run contract says so explicitly.
- It does not let a prompt, a confidence value or a preferred engine grant an
  effect or accept a task outcome.

## Related reading

- [Model gateway](../core-architecture/MODEL-GATEWAY.md) for routing, capacity
  and accounting.
- [Model Response Admission](../core-architecture/MODEL-RESPONSE-ADMISSION.md)
  for the separate structural admission of a free text response.
- The package's own architecture contract at
  `src/loop_engine/core/decisions/README.md`.

# Typed decision engines

Kind: component explanation for `src/loop_engine/core/decisions`.

A model call that returns free text and a model call that returns one label
from a closed set are different operations. This component owns the second one.
It sends typed judgment requests to a configured decision endpoint and admits
the answers against the question identities that were asked.

The registered operational boundary is `typed decision provider invocation`,
whose envelope is `core.decisions.gateway.invoke_decisions`. The provider
adapter and the passive request are not graph vertices. The model gateway's
model attempt Loop owns each physical invocation, and the application facing
tool in `code_nodes/decision_tools.py` owns its request through a Practitioner
Loop.

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
PYTHONPATH=src:tools python -m unittest tools.test_decision_engine_boundary -v
```

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

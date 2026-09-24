# Typed decision engines

Kind: internal model-gateway component and architecture contract.

This package owns typed judgment requests, response admission and configured
decision endpoint adapters. Keeping these files together prevents another flat family in
`core`. ModelGateway remains the provider registry and route-policy boundary.
The existing model session owns cumulative call accounting.

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
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Provider adapters and passive requests are not graph vertices. The gateway's
model-attempt Loop owns each physical invocation. The application-facing tool
in `code_nodes/decision_tools.py` owns its request through a Practitioner Loop.

## Files and dependency direction

```text
Existing model execution
├── core/decisions/contracts.py: provider-independent requests and admission
├── core/decisions/configuration.py: host settings compiled into existing routes
├── core/decisions/credentials.py: secret reference resolution at use
├── core/decisions/wire.py: shared question serialization and admission
├── core/decisions/http_transport.py: bounded endpoint transport
├── core/decisions/jev.py: explicitly authorized TypeSafe wire adapter
├── core/decisions/system_one.py: Circuit and compatible external endpoints
├── core/decisions/gateway.py: ModelGateway's typed dispatch implementation
├── core/decisions/command_risk_policy.py: the written command risk policy, read without running
├── core/decisions/command_risk_programs.py: the policy's per-program readers
├── core/decisions/stations.py: decision stations, declared engine order, guards and records
├── core/decisions/rules_engine.py: in-process engine for the stations' written policies
├── core/decisions/station_engines.py: the station engine factory table
└── code_nodes/decision_tools.py: application tool over ModelExecutionSession
```

The core package must not import the application tools, command dispatcher or
`code_nodes`. Application code depends on the lower contracts and gateway.
The package contains no provider discovery registry, permission store, task
scheduler or separate Run History. Host registrations remain trusted code;
configuration cannot import arbitrary modules or activate a candidate plugin.

## Stable contracts

`decision_batch_request/v1` carries explicit question identities and one
immutable input snapshot. `decision_batch_result/v1` returns normalized typed
answers. `typed_decisions/v1` is the provider capability negotiated by the
gateway. A provider must declare supported question kinds and implement
preparation and one-attempt invocation. Unknown versions or shapes refuse.

The TypeSafe adapter does not generate text. Another implementation may serve
the same typed contract without changing its caller. A provider swap still
needs compatible capabilities, explicit routes, authority and evaluation.
The command reads `decision_host_configuration/v2`: named engines, their
settings, ordered route names, a session allowance and explicit failover.
The shipped profiles are `jev`, `circuit` and `system_one`. The last two use
the same standard question wire contract and differ only in the reported
engine label. Embedded hosts may also supply their existing ModelGateway.
Configuration cannot import code or construct an arbitrary unknown adapter.

Users or providers operate all model servers. Loop Engine does not install,
download, launch, restart or supervise Jev, Circuit, Ollama or another model
service. It connects to an existing endpoint under the supplied authority.
Adding another wire protocol requires a tested adapter, not a model-name branch
in the caller. A text-generation endpoint is not automatically a System One
decision endpoint.

Endpoint settings include the exact URL, reported model identity, separate
credential reference, request and response byte allowances, and optional
operator-supplied deployment digest. HTTPS is required except for explicitly
allowed numeric loopback HTTP. Different provider origins cannot share one
configured credential reference. Discovery reads no key. Context truncation,
token capacity and deployment identity remain unverified unless established
by the provider; transport byte limits are not substitutes for token limits.

Protocol field names, version identities, security validation and the fixed
TypeSafe origin are contract constants. Exact model, credential reference,
network/model permission, transport allowances, call allowance and timeout
are settings. Retry and provider fallback must be explicit. A prompt, confidence
value or preferred engine never grants an effect or accepts a task outcome.

## Decision stations

A step has one build station, where a harness writes code, and judgment
stations around it. A station asks typed questions on
`decision_batch_request/v1` at a fixed loop point and binds the admitted answer
with its own guards. The command safety station is asked before a command
runs. Its guards come from the command risk policy and hold whatever an
engine answers: an irreversible command, an effect the step does not hold,
or a command the policy cannot fully read waits for a person.

```text
Decision station
├── StationDefinition: loop point, typed questions, binding rule, safe default
├── StationPolicy: declared engine order, fallback failure kinds, trial permission
├── StationEngine: one installed engine of a typed_decision slot kind
│   ├── in process (rules): answers directly and counts no model call
│   └── provider (decision endpoint): answers through ModelGateway
└── DecisionStationResult
    ├── decision and binding: what the owning Loop acts on
    └── advisory: guidance that never binds
```

Engines are tried in the declared order after an eligibility screen: the
protocol, availability, the station and question kinds, and qualification. A
model-backed engine needs a measured proof level before it is served by
default; deterministic code is served on its contract checks. After a typed
failure the next engine answers only when the policy declares that failure
kind. When no engine answers, the station's safe default binds. Until the
run-time engine selector reaches main, the declared order is the whole
selection, and no evidence reorders it.

Each decision is written to the owning Loop's ledger with digests only, and,
when the run keeps them, as a semantic decision record joined forward through
the run's outcome ledger. A station never grants authority and never accepts a
task. The harness hook form only narrows: it answers "ask" for a command that
must wait and nothing for one that may run, so a harness's own permission
rules still apply.

## Verification and limits

The owning checks exercise local contracts, the actual serializer, real
protocol messages and the canonical gateway with injected provider fixtures.
`tools/test_decision_engine_boundary.py` enforces package dependency direction.
No local fixture establishes live Jev availability, model quality, native
harness loading, global credential isolation or cross-process budget sharing.

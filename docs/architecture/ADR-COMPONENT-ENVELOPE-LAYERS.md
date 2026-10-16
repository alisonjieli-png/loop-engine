# Envelope layers around every functional engine

Kind: architecture decision. Date: 2026-10-16. Status: decided by engineering
under the owner's direction of October 16, 2026. The rules are section 14 of
the [functional component standard](FUNCTIONAL-COMPONENT-STANDARD.md#14-envelope-layers-around-every-functional-engine)
(LE-LAYER-001 to LE-LAYER-028), and adoption is an incremental ratchet that
changes no customer path before the October 27 launch.

The functional component standard gives every functional component one
envelope Loop: the registered boundary Loop that holds its edge contract
constant while its engines change. A planned slot gets its envelope Loop with
its first package. This decision gives that envelope Loop the same ordered
envelope layers in every component: a typed carrier, a handshake, an account check, tracking and
resync, a preflight self-check, and frustration avoidance on every answer. The
same layers run again around each nested slot, within a depth and cost bound.
Shared records for four of the layers live in `src/loop_engine/core/engines/`,
every engine slot declares which layers it implements, and a baseline makes
sure that coverage only rises.

## The owner's words, October 16, 2026

> "I'm thinking we may want to further enforce our infrastructure layering and
> rules so we have functional components, which are wrapped in multiple layers
> including flexible edges with objects, pointers, etc that can change,
> compatibility/handshake layer, and other functionality/components within
> these layers wrapping the functional engines so that handshakes, updates,
> ideas, and other things can be tracked, resynced, things like account check,
> and account triggers and resyncs and frustration avoidance tools can be done
> and implemented as well as self troubleshooting and self resolving things
> before the functional engine, and even functional engine component should
> have these same layers and wrappers of best practices"

The owner's words keep the owner's meaning. The layer names below are
engineering's reading of them.

## Decision

1. The owner's "multiple layers" are the envelope layers of the envelope Loop
   that the standard gives each functional component. An envelope layer is code that
   the envelope Loop runs for one request. It is not a Loop, a runtime type, a
   graph vertex, a registry, a store or a scheduler, and it is not a wrapper
   layer, which sits inside one engine installation.
2. There are six envelope layers in one fixed order, and one rule for nested
   slots. Each layer owns named responsibilities, has things it must never do,
   and already has partial code in the repository.
3. Four layers get shared, typed and versioned records with pure functions:
   the handshake verdict, the attempt journal with its resync decision, the
   refusal record with its recovery bound, and the preflight runner. The
   nesting frame and the envelope trace complete them.
4. Every slot of `engine_slots.yaml` declares, for each layer, full, partial,
   none, or not applicable with a named reason. The declarations of October 16
   are the recorded baseline, and a declaration may rise but never fall.
5. `ontology_change_planning` adopts the layers as the reference, because it
   has a complete conformance kit and no customer reaches it.
6. The account email, catalogue retrieval and billing webhook boundaries come
   next, each through the owner of that boundary.

## Where the layers sit

The complete Loop classification comes first, as `AGENTS.md` requires.

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

The envelope layers are internal structure of one envelope Loop, which is a
Loop of the classification above. None of the parts below is a graph vertex, a
runtime type or a scheduler.

```text
Functional component (one job, one owner, reached only through its edge contract)
└── Envelope Loop, for one request, outermost first
    ├── 1 frustration_avoidance  every answer leaves through it; every refusal becomes envelope_refusal/v1
    ├── 2 carrier                exact name/vN records; flexible fields and pointer carriers
    ├── 3 handshake              envelope_handshake_verdict/v1 for each engine, from declarations
    ├── 4 account                principal, entitlement, account-triggered events and resyncs
    ├── 5 tracking               envelope_journal_entry/v1: intent, outcome, replay, reconciliation, resync
    ├── 6 preflight              declared self-checks and bounded self-repairs before the engine
    └── Engine slot              selection, binding and one engine (or a composite engine)
        └── nested slot          entered through its own envelope layers (nested_envelopes),
                                 with the parent's remaining deadline and recovery allowance
```

A request passes the inbound layers in order, from the carrier to the
preflight, and reaches the engine only after every one of them accepted it or
did not apply. A layer that refuses, or that answers from a record, ends the
request there. Frustration avoidance is outermost because it shapes every
answer that leaves, whichever layer or engine produced it.

## The layers

| Order | Layer | The owner's words | Statements |
|---|---|---|---|
| 1 | `frustration_avoidance` | "frustration avoidance tools" | LE-LAYER-019 to LE-LAYER-022 |
| 2 | `carrier` | "flexible edges with objects, pointers, etc that can change" | LE-LAYER-007 to LE-LAYER-009 |
| 3 | `handshake` | "compatibility/handshake layer" | LE-LAYER-010, LE-LAYER-011 |
| 4 | `account` | "account check, and account triggers and resyncs" | LE-LAYER-012 to LE-LAYER-014 |
| 5 | `tracking` | "handshakes, updates, ideas, and other things can be tracked, resynced" | LE-LAYER-015 to LE-LAYER-018 |
| 6 | `preflight` | "self troubleshooting and self resolving things before the functional engine" | LE-LAYER-023 to LE-LAYER-026 |
| Rule | `nested_envelopes` | "even functional engine component should have these same layers" | LE-LAYER-027, LE-LAYER-028 |

LE-LAYER-001 to LE-LAYER-006 hold the order, the structure and the coverage
declarations. The owner's "other functionality/components within these
layers" is read this way: where a layer needs work of its own, such as the
identity provider behind the account check, that work is another functional
component with its own slot (`browser_identity_provider`, `payment_provider`),
reached through its own envelope Loop. A layer never hides an engine of its
own.

### Frustration avoidance

Owns: the one shape of every refusal that leaves the envelope, and the bounded
automatic recovery of steps that wrote nothing. An `envelope_refusal/v1` holds
a stable code, a sentence that says what happened, a plain next action, who
acts on it (the caller, the account owner or the operator), and one retry rule
from a closed list with its own sentence: retry now with the same request
identity, retry after a wait, retry after a fix, reconcile before any retry,
or do not retry. An `envelope_recovery_policy/v1` names the codes a component
may retry itself and how often, and a `RecoveryAllowance` shares at most three
automatic attempts among every envelope that one request passes.

Never: leave a dead end, such as a bare exception or a code alone; tell a
caller to retry now when an effect may have happened; retry automatically
after an effect; let nested layers multiply retries; reflect request text or
name a secret value.

Existing code that already does part of it: `service_http_error/v1`, built by
`_error_record` in `src/loop_engine/core/service_runtime/http.py`, carries the
code, the message, the next action, the effect commitment and
`automatic_retry: false`; `guidance` in
`src/loop_engine/core/service_runtime/refusals.py` words every code a customer
meets and every status the transport chooses. Retry advice sits inside the
next action's words there, not in a closed rule. `BEGIN_ATTEMPTS` in
`src/loop_engine/core/service_runtime/billing.py` starts a webhook delivery
that lost a race again, at most three times, because the refused batch wrote
nothing. `src/loop_engine/core/action_fence.py` refuses an identical failed
call after its declared number of failures, and the harness fallback never
resets the call allowance.

### Carrier

Owns: reading every request and result as an exact `name/vN` record before
anything else; reading flexible fields only through the schema that declares
them; and resolving pointer carriers only through the owner of the content
they name. A flexible field is an attribute map whose keys a schema declares
as data, such as the catalogue attributes. A pointer carrier is a reference
by identity and digest to content that another owner holds, such as a body
digest, the active catalogue release pointer or a `LoopDefinitionRef`. The
S-6.30 rule in the [delivery sequence](../roadmap/DELIVERY-SEQUENCE.md)
applies here: flexible fields and pointer carriers negotiate supported
versions and authority before use, and cannot infer compatibility, create a
competing runtime or widen model access.

Never: infer meaning from a field's name; let a flexible field set an effect,
a licence, a permission, a route or an engine choice; follow a pointer
without its owner and its digest check; fetch a remote reference; fall back
to another version when a pointer does not resolve.

Existing code: `read_record` in `src/loop_engine/core/engines/records.py`
refuses another version, an unknown field and a missing field for every
engine record, and library ingestion has its own `read_record`.
`_parse_json` in the service transport refuses duplicate fields, non-finite
numbers and deep nesting. `catalogue_attribute_schema/v1` declares the
catalogue's attributes as data, and no attribute can set an effect, licence or
permission. `catalogue_release_pointer/v1` moves only under an
expected-version guard. A body read is bound to its expected digest before
metering (`selected_body_digest_mismatch`), and `OntologyStore.triples`
checks a graph's digest on every read.

### Handshake

Owns: one `envelope_handshake_verdict/v1` for each caller and each engine,
computed from declarations alone. The verdict uses the store handshake's
vocabulary. A missing declaration gives `unknown`; no version in common gives
`incompatible`; a declared effect that the caller did not grant gives
`refused_by_policy`; an advisory capability the engine lacks gives
`compatible_with_degradation` and names what is ignored; and only an exact
declared match gives `compatible`. The selected version is the first entry of
the caller's preference order that the engine declares exactly. The record
computes its verdict again from its own fields, so a record that claims
compatibility without a declared match is refused when it is built or read.

Never: infer compatibility from a version order, a prefix or a missing
declaration; treat unknown as compatible; downgrade silently; grant model,
file, network, secret, spending or external-effect authority, which stays with
the owning Loop's grants.

Existing code: `negotiate` and its eight verdicts in
`src/loop_engine/catalog/handshake.py`, the Capability Directory's
`CapabilityHandshake`, `select_protocol_binding` and the
`unsupported_protocol_version` refusal of the protocol endpoint,
`catalogue_state_gate` (an image refuses catalogue state it cannot read),
`unmet_harness_requirements` of the step executor, and `require_same_space`
for embedding spaces. The [pre-launch version decision](ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
already requires negotiation with an explicit refusal.

### Account

Owns: reading the principal and its entitlement from the service's own records
before the engine runs; refusing an unknown, pending or unreadable account
state with its own code; and applying account-triggered events and resyncs
once each. The events today are the payment provider's notifications, a
sign-in created outside Baltor's own sign-up (identity-provider drift), and
the founding-offer counter.

Never: reveal to a caller who has not proven an address whether it has an
account; read an unknown or pending entitlement as granted; order account
events by their timestamps; act on a provider without that effect's own
authority.

Existing code: `ServiceHttpAuthenticator` checks the principal again at every
use, and revoking a key invalidates principals already issued.
`StripeEventProcessor` deduplicates notifications by event identity, never
orders updates by event time, first removes paid access and then resolves the
provider's current state under a revision guard, and keeps a pending event
resumable after a restart. The account origin marks refuse a sign-in that
Baltor's sign-up did not create (`account_origin_unverified`). The founding
offer in `src/loop_engine/core/service_runtime/free_monthly.py` commits every
grant against the exact version of one counter record, so two sign-ups at the
last place yield one holder. `AccountEmailAdapter` answers the same way
whether or not an address has an account, limits attempts per client address
and per address, and stays closed until the host opens it.

### Tracking

Owns: identities for requests, updates and ideas, and what happened to each.
An `envelope_journal_entry/v1` records an attempt's intent before dispatch and
its outcome after, under the digest of the request identity, with the request
outcome, the task outcome and the effect state as three fields
(LE-INSTANCE-023). Before any new dispatch the journal decides from the
entries of that identity alone: answer from the first result when the effect
is confirmed, refuse when that answer is no longer held, reconcile first when
an effect is pending, unknown or interrupted, and dispatch otherwise. A
reconciliation records an observation of the effect's owner, never an
assumption. Updates, such as a new catalogue release or a changed policy, are
desired states: the resync decision compares the desired, observed and last
rejected identities, prepares a changed desired state at the next check, and
waits out a capped backoff for an unchanged rejected one. Ideas, the candidate
outputs and proposals an engine returns, are named by their result digest, so
that a consumer can say exactly which one it used, as
[ASTRA.md](../../ASTRA.md#complete-behavioral-explanation) requires.

Never: repeat an effect whose outcome is unknown; settle an outcome without an
observation; keep a caller's raw request identity, only its digest; add a
journal store, because each entry lives in the owning component's existing
store.

Existing code: `src/loop_engine/code_nodes/overnight_journal.py` writes an
effect's intent before the effect and repeats one only where it was declared
repeatable. `record_usage` in the service runtime keys metering by request
identity. The billing notifications stay pending until they are reconciled,
and `BillingSessionEffectStore` reserves each checkout effect under an exact
identity within a reconciliation window. `CatalogueRefresher.check_once`
probes the desired catalogue state, builds the new view to one side, swaps it
in and journals a failed build. `ServiceFailureJournal` keeps a searchable
reference for every refusal. LE-INSTANCE-021 records where this breaks today:
a retry across a catalogue swap.

### Preflight

Owns: self-checks and self-repairs before the engine, within declared bounds.
A check reads and compares; it answers nothing or an envelope refusal whose
code it declares. A self-repair declares the diagnoses it fixes, its effects
and how often it may run in one attempt, at most twice. The runner refuses,
before it runs, a repair whose effects other than pure the attempt's grant
does not hold, runs the check again after every repair, and records every
check, diagnosis, repair and verdict in `envelope_preflight_report/v1`.

Never: perform an effect without that effect's own grant; produce its own
evidence or approve its own work; change a policy or a grant; repeat an
effect; loop past its bound; hide a check that still fails.

Existing code: `loop-engine doctor` (`run_doctor` in
`src/loop_engine/cli_operations.py`) checks the installation, settings,
Docker, extensions and provider references without a provider call.
`src/loop_engine/core/model_token_preflight.py` fails closed on an unknown
token bound before dispatch, and `local_model_readiness.py` reads which models
a server holds. `HarnessProcessSpec.validate_unchanged` checks a harness
again at use. The catalogue search index refuses at start an engine that
cannot run on this machine and never replaces it, and the serve command stops
before it serves the public without request limits.

### Nested envelopes

Owns: the rule that a call into a nested slot passes through that slot's own
envelope layers, with the parent's remaining deadline and the same recovery
allowance object, never fresh ones. Depth is bounded: four levels below the
first envelope of a request. The catalogue's deepest slot today sits three
levels down (`step_executor`, `model_call_strategy`, `model_access`,
`local_credential_source`), so one level is left for a composite engine. An
envelope entered past the bound, on a slot already on the path, or after the
inherited deadline is refused before any layer runs. Cost is bounded the same
way: the automatic attempts of one request are shared, so nesting adds
attempts to one count instead of multiplying them.

Never: give a nested envelope a fresh deadline or allowance; pass the depth
bound; enter a slot already on the path; widen the parent's grants
(LE-PERM-001).

Existing code: `nested_under` and `nesting_scope_rule` in `engine_slot/v1`,
the slot index's cycle check, `parent_decision_digest` on selection
decisions, LE-SLOT-007, and the layered wrapper rule that retry layers must
not multiply attempts
([layered harness wrappers](LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)).
LE-ENGINE-005, the remaining deadline for a nested call, is not built yet.

## Coverage and the ratchet

`src/loop_engine/data/component_envelope_coverage.yaml`
(`component_envelope_coverage/v1`) holds one entry for every slot of the
catalogue and one declaration for each layer. A full or partial declaration
names its evidence: dotted symbols or `module:check` references that resolve
in source without import, and a full declaration names at least one check. A
not applicable declaration names one of six reasons; the release-time reason
and the no-nested-slot reason are checked against the catalogue. A none may
name the roadmap step that closes it, and a slot added after the baseline
must name one for each of its gaps.

`src/loop_engine/data/component_envelope_coverage_baseline.yaml` records the
level of every slot and layer on October 16, 2026. The coverage check refuses
a declaration below its recorded level, so none may rise to partial or full,
partial to full, and not applicable only to partial or full. Declaring a gap
not applicable counts as a fall. `RECORDED_BASELINE_FLOOR` in
`src/loop_engine/core/engines/envelope_coverage.py` pins the baseline's own
totals, so lowering a row is a reviewed change to both files together. The
check runs in the main self-test (`core.engines.envelope_checks`) and in the
tools tests (`tools/test_component_envelope_layers.py`).

| Layer | Full | Partial | None | Not applicable |
|---|---|---|---|---|
| frustration_avoidance | 1 | 14 | 34 | 6 |
| carrier | 1 | 20 | 26 | 8 |
| handshake | 1 | 17 | 29 | 8 |
| account | 0 | 5 | 1 | 49 |
| tracking | 0 | 10 | 32 | 13 |
| preflight | 1 | 9 | 37 | 8 |
| nested_envelopes | 0 | 0 | 7 | 48 |
| All 385 declarations of 55 slots | 4 | 75 | 166 | 140 |

The table is the recorded baseline of October 16, after the reference
adoption. The survey before it found 0 full, 79 partial, 166 none and 140 not
applicable declarations; the adoption raised four layers of
`ontology_change_planning` from partial to full, and the baseline row and its
floor rose with them. The survey is conservative: a layer is partial only
where it named code on the slot's own path. The check proves that the named
code exists; whether that code does everything a layer asks is a question for
review.

## The reference adoption: ontology change planning

`ontology_change_planning` was chosen because it is a complete functional
component (an edge contract, an envelope, two engines, a conformance kit that
each engine passes alone, and its own tools test), and because it is planned:
no Loop and no customer calls it, so nothing on the launch path can change.
Its engines' implementation digests stay as they were, because the adoption
changes neither the contract nor an engine.

| Layer | What the slot now does | Declared |
|---|---|---|
| frustration_avoidance | Every one of its 19 closed failure codes has an `envelope_refusal/v1` with a next action and a retry rule, and a declared recovery policy says it never retries a step itself | full |
| carrier | The request is read strictly, and the base digest, a pointer to the base state, is checked against the ontology it carries before any engine runs | full |
| handshake | Each screened installation gets a handshake verdict from its declaration and the host's granted effects; an engine whose effects the host does not grant is refused by policy and never selected | full |
| account | No account reaches the slot | not applicable |
| tracking | A retried apply of the same plan and approval is answered with its first result and writes nothing, decided by the shared journal decision over the store's journal and observed state | partial |
| preflight | The selected engine is checked again just before each dispatch; no self-repair is declared, because none of its diagnoses has a repair without effects | full |
| nested_envelopes | No slot is nested under it | not applicable |

The outcome record became `ontology_change_outcome/v2`, which adds the
refusal, the handshake verdicts, the preflight reports and the trace beside
the plan, the failure and the decisions. Tracking stays partial for two
recorded reasons. A retried rollback is still refused as `stale_rollback`,
which the kit asserts. A commit interrupted between its journal line and its
state write leaves a journal line whose sequence number the next commit
repeats (`_commit` in `src/loop_engine/core/ontology_change/store.py`); the
replay never answers from such a line, because it requires the store state to
be the one that line wrote.

## The next three adoptions

Each one changes a boundary that another session may be changing now, so each
waits for that boundary's owner and lands after the launch unless its owner
schedules it sooner.

1. **Account email** (`account_email_delivery`, `src/loop_engine/core/service_runtime/account_email.py`).
   Give each refusal the closed retry rule beside its existing next action,
   and record the open-operation checks as an `envelope_preflight_report/v1`.
   It closes LE-LAYER-019 and LE-LAYER-023 for the slot and keeps the answer
   the same for known and unknown addresses (LE-LAYER-014).
2. **Catalogue retrieval** (`catalogue_body_store` and
   `catalogue_search_index`). Answer a retry by request identity across a
   catalogue swap from the record of the first bytes (LE-LAYER-016 and
   LE-INSTANCE-021), use the resync decision in `CatalogueRefresher` so that
   an unchanged rejected release waits for its backoff (LE-LAYER-018 and
   LE-STATUS-008), and record the client's request version as a handshake
   verdict (LE-LAYER-010 and LE-EDGE-006).
3. **Billing webhook** (`payment_provider`,
   `src/loop_engine/core/service_runtime/billing.py`). Map each
   `BillingEventResult` diagnostic code to an envelope refusal, declare
   `BEGIN_ATTEMPTS` as an `envelope_recovery_policy/v1` whose code is
   `concurrent_update`, and project the stored notification records onto the
   journal decision so that a resumed event is decided by the shared rule
   (LE-LAYER-013, LE-LAYER-016 and LE-LAYER-021).

## Alternatives considered and rejected

| Alternative | Why it was rejected |
|---|---|
| A new component or wrapper class that owns the layers, or one Loop for each layer | One Loop runtime: a layer has no goal, authority or Run History identity of its own, so it stays inside its owning Loop (`AGENTS.md`, LE-NODE-001). Spawned Loops for each layer would multiply records and, for model-led modes, model calls |
| Wrapper layers inside every engine installation | Each engine would carry its own copy and its own order, the edge would differ by engine, and a new engine could arrive without them. Wrapper layers stay for engine-specific mechanics inside one installation |
| A middleware chain configured per request | Order would become data that a request could change; the order is fixed so that no request reaches the engine past a layer that would refuse it |
| A new field on `engine_slot/v1` for the declarations | The slot reader refuses unknown keys, and adoption step 4 of the standard versions every engine record once and together. A separate file joined by slot identifier follows the folder map and the interaction rows |
| A universal handshake service or registry | LE-SLOT-003 forbids a registry of the engine framework, and the pre-launch version decision keeps handshakes at their owning boundaries. The shared verdict record reuses the store handshake's vocabulary |
| Compatibility from semantic version ranges | Version order does not prove two schemas compatible (pre-launch version decision); equality with the caller's preference order is the only selection |
| A generic retry around every engine | Retries at several layers multiply; an effect may already have happened. Retry is owned once (LE-EDGE-012) and bounded by one shared allowance |
| Self-repairs with effects by default, such as installing a missing binary or running the kit to create missing evidence | Effects need their own authority, and a component that produced its own evidence would approve its own work (LE-GOV-001) |
| A fresh budget for each nested envelope | Nesting would multiply attempts and time (LE-ENGINE-005); the frame passes the same allowance and deadline down |

## Prior art

These were consulted from engineering knowledge and were not rechecked
against their sources on October 16, 2026 (evidence label: claim).

| Source | What it offers | Decision |
|---|---|---|
| RFC 9457, Problem Details for HTTP APIs | A typed error body with a type, title, status, detail and instance | Adapted: the refusal keeps a stable code and its sentences, and adds a next action, who acts and a closed retry rule, which RFC 9457 does not define |
| The idempotency key pattern (Stripe's idempotent requests and the IETF draft Idempotency-Key header) | A retry under the same key returns the first result | Adopted for the journal decision; the billing effects already follow Stripe's 24-hour key retention |
| Kubernetes controllers | Reconcile a desired state with an observed state, retrying with backoff | Adapted for the resync decision, with sequence numbers instead of generation counters (SEM-047) |
| Retry guidance of the AWS Builders' Library and the Google SRE book chapter on overload | Retry at one layer only, with a small bounded count, so that layers do not multiply attempts | Adopted: one retry owner, at most three automatic attempts for one request, shared by nested envelopes |
| Envoy filter chains and gRPC interceptors | An ordered chain of request handlers around a call | Adapted: the order is fixed by this decision, not configured per request |
| Temporal activities | Durable steps that must be idempotent, with a recorded history | Not adopted here; a durable engine belongs behind the proposed `step_attempt_durability` slot of the ecosystem edge map |

## Consequences

- Every refusal of an adopted component carries the same fields, so a person
  and an agent can act on any of them without reading the component's code.
- Compatibility, account state, effect state and readiness become records
  with stable codes instead of exceptions and log text.
- The coverage file makes each slot's gaps visible and owned, and the
  baseline stops a regression from landing silently.
- Cost: each adoption adds records to an outcome, as the
  `ontology_change_outcome/v2` change shows, and the coverage file must be
  kept current when a slot is added. A declaration is a claim that review
  must read; the check proves only that its evidence exists.
- The baseline undercounts what exists, because the survey marked partial
  only where it named code. A later survey raises a none with its evidence.

## Migration

1. The shared records, the coverage file, its baseline and the checks landed
   first, changing no behaviour.
2. The reference adoption changed only `ontology_change_planning`, which no
   customer path reaches.
3. Each further adoption goes through the owner of its boundary, raises that
   slot's row in the baseline in the same change, and adds the checks its
   statements name.
4. The coverage declarations move into `engine_slot/v2` when adoption step 4
   of the standard versions the engine records together; until then the
   separate file is the one source.
5. Roadmap S-6.30.01 records the acceptance, the evidence and the next action.

## What this decision does not add

- A new runtime type, a graph vertex other than `Loop`, or a class whose name
  ends in `Node`.
- A registry, a store, a journal store, an event family or a scheduler.
- Authority of any kind: a handshake verdict, a refusal, a journal entry, a
  preflight report and a coverage declaration grant nothing.
- A change to any customer path, provider, release or catalogue before the
  launch.

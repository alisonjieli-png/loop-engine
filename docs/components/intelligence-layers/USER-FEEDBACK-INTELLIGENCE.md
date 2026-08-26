# User Feedback Intelligence

User Feedback Intelligence is guidance supplied by a person. It can advise a whole
organization, one project, one task, one run, one loop, one iteration, one
Solution, or one loop inside a Solution.

The guidance is not hidden inside a prompt. It has identity, scope, target,
type, strength, timing, status, author, and time. A loop can find it, consult
it, respond to it, and record what happened.

User Feedback Intelligence is guidance. It is not truth, permission, or proof. It
cannot bypass safety, legal, security, organization, project, or task rules.

## Categories

The closed guidance-type vocabulary is:

| Guidance type | Use |
|---|---|
| `advice` | A general suggestion about how to approach the work |
| `correction` | A statement that an assumption or result needs correction |
| `context` | Background information relevant to the target |
| `source_suggestion` | A source that may help the loop |
| `package_suggestion` | A software package that may help the loop |
| `priority_change` | A requested change in order or importance |
| `constraint` | A boundary the loop must evaluate against higher policy |
| `instruction` | A direct request from the user |
| `approval` | Approval for a defined choice or boundary |
| `veto` | A request not to take a defined choice |

The shared intelligence classification uses the same values as category
groups, plus `other` for items that cannot yet be classified reliably.

## Scope, strength, and timing

### Scopes

`AdviceStore` accepts these scopes:

```text
organization
project
task
run
loop
iteration
solution
solution_loop
```

The legacy input `solution_component` is accepted and stored as
`solution_loop`.

The `target` is the identity inside the selected scope. For example:

```text
scope=project, target=customer-risk
scope=task, target=import-2026-08-25
scope=loop, target=loop-17
scope=solution_loop, target=country-code-validator
```

### Strengths

The strength vocabulary is:

```text
suggestion
preference
instruction
constraint
approval
veto
```

Strength, not forceful wording, decides the guidance rung. An item stored as a
suggestion remains a suggestion even if its text uses strong language.

### Timings

The timing vocabulary is:

```text
immediately_if_safe
next_safe_boundary
before_next_retry
before_verification
future_runs_only
```

Timing describes when the loop should consider the item. It does not make an
unsafe action safe.

## Storage and lifecycle

`AdviceStore` uses one append-only JSONL file. The unified catalog uses this
default path when no path is supplied:

```text
~/.loop-engine/studio/user-advice.jsonl
```

You can pass another file with `advice_path` when you build the intelligence
catalog.

The lifecycle is append-only:

```text
user_advice
  -> advice_consulted
  -> advice_response
  -> advice_retired
```

These are separate rows. The original guidance row is not rewritten.

- `user_advice` stores the guidance.
- `advice_consulted` records which loop checked which target and what it
  found.
- `advice_response` records accepted, partially accepted, deferred, or
  rejected, with a reason.
- `advice_retired` is a tombstone. Retired guidance is removed from the
  active search view, but its prior rows remain in the file.

Create a store and add guidance:

```python
from loop_engine.core.user_feedback_intelligence import AdviceStore

store = AdviceStore("./state/user-advice.jsonl")

guidance = store.leave_advice(
    "Check the carrier status page before retrying the shipment request.",
    scope="task",
    target="shipment-recovery",
    author="operations-team",
    guidance_type="source_suggestion",
    strength="suggestion",
    timing="before_next_retry",
)

print(guidance["advice_id"])
```

Empty text and unknown vocabulary values are refused.

## Make every boundary a loop

Use the loop wrappers when guidance crosses into or out of the runtime:

```python
from loop_engine import LoopLedger
from loop_engine.loop.intelligence_loops import (
    consult_guidance_as_loop,
    leave_guidance_as_loop,
)
from loop_engine.core.user_feedback_intelligence import AdviceStore

ledger = LoopLedger()
store = AdviceStore("./state/user-advice.jsonl")

created = leave_guidance_as_loop(
    store,
    "Use the approved country-code source for this import.",
    scope="task",
    target="customer-import",
    guidance_type="instruction",
    strength="instruction",
    timing="before_verification",
    ledger=ledger,
)

consulted = consult_guidance_as_loop(
    store,
    "task",
    "customer-import",
    loop_id="validation-loop",
    ledger=ledger,
)

print(created["loop_id"])
print(consulted["value"])
```

`leave_guidance_as_loop()` runs the write as a Guidance Loop.
`consult_guidance_as_loop()` runs the read as a Guidance Loop and also adds an
`advice_consulted` row. With a ledger, it records the consultation on the
active run.

`guidance_for_as_loop()` reads active guidance through a loop without adding a
consultation row. Use it for display. Use `consult_guidance_as_loop()` when a
loop is actually checking guidance before a decision.

## Search User Feedback Intelligence with all four layers

`advice_records_for_search()` converts active advice into the shared
`StoreRecord` form. `build_intelligence_catalog()` does this automatically.

```python
from loop_engine.loop.loop_capsule import LoopRef
from loop_engine.core.intelligence_layers import (
    build_intelligence_catalog,
    materialize_intelligence_ref,
    query_intelligence,
)

catalog = build_intelligence_catalog(
    advice_path="./state/user-advice.jsonl",
)

search = query_intelligence(
    "has the user suggested a source for country codes",
    catalog,
    mode="lexical",
    top_n=5,
    ledger=ledger,
)

user_hits = [
    item for item in search["hits"]
    if item["layer"] == "user_feedback_intelligence"
]

if user_hits:
    selected = LoopRef.from_dict(user_hits[0]["loop_ref"])
    loaded = materialize_intelligence_ref(
        selected,
        catalog,
        ledger=ledger,
    )
    print(loaded["value"])
```

The search loop returns body-free `LoopRef` objects. The selected guidance is
then loaded through a separate User Feedback Intelligence loop.

```text
search loop
  -> ranked LoopRefs
  -> choose one reference
  -> User Feedback Intelligence access loop
  -> selected guidance
```

The searchable card contains scope, target, author, guidance type, strength,
timing, status, time, classification facets, and tags. Retired advice is not
placed in the active search population.

## Resolve several applicable scopes

A working loop may need guidance from several scopes. Use
`resolve_user_feedback_intelligence()` to consult those targets through one thin,
deterministic Practitioner Loop and rank the combined snapshot.

```python
from loop_engine.core.user_feedback_intelligence import (
    resolve_user_feedback_intelligence,
)

snapshot = resolve_user_feedback_intelligence(
    store,
    {
        "organization": "example-company",
        "project": "customer-risk",
        "task": "customer-import",
        "loop": "validation-loop",
    },
    loop_id="validation-loop",
    ledger=ledger,
    policy_floor=(
        {
            "rung": "organization_policy",
            "rule": "Do not send customer records to an external service.",
        },
    ),
)

print(snapshot["ordered"])
print(snapshot["conflicts"])
assert snapshot["model_calls"] == 0
```

The result contains:

- `snapshot`, the active advice rows found across the supplied targets
- `resolver_loop_id`, the identity of the deterministic resolution loop
- `ordered`, the policy and user records in precedence order
- `conflicts`, opposed guidance that must remain visible
- `highest_rung`, the leading authority rung
- `model_calls`, which is zero for this resolver

Within the same guidance rung, a narrower scope leads a broader scope. More
recent guidance leads older guidance at the same rung and scope width.

## Precedence and conflicts

The ranking order is:

1. platform safety, legal, and security rules
2. organization policy
3. project hard constraints
4. user instructions, approvals, vetoes, and constraints
5. task or Solution requirements
6. loop template defaults
7. learned routing preferences
8. exploratory suggestions

The first three rungs are not User Feedback Intelligence. Supply them through
`policy_floor`. `rank_guidance()` refuses a policy-floor item that claims a
lower rung.

The current conflict detector preserves both sides when opposed guidance
types target the same item. For example, it reports a veto paired with an
approval. It does not silently delete one side.

After a loop decides what to do, record its response:

```python
store.respond(
    guidance["advice_id"],
    "deferred",
    reason="The status source is unavailable. Retry at the next safe boundary.",
    loop_id="shipment-loop",
    ledger=ledger,
)

responses = store.responses_for(guidance["advice_id"])
```

Valid responses are `accepted`, `partially_accepted`, `deferred`, and
`rejected`.

Retire guidance only when it should no longer appear in active consultation
or search:

```python
store.retire_advice(
    guidance["advice_id"],
    reason="The carrier replaced this status page.",
)
```

## Optional model reframing

Normal guidance access is deterministic. An application may explicitly ask
an authorized model adapter to restate a selected item for the current task.
The model work is a second loop. It is not hidden inside retrieval.

```python
from loop_engine.loop.loop_capsule import reframe_ref_with_model

reframed = reframe_ref_with_model(
    selected,
    resolver=resolve_selected_guidance,
    task="review the failed customer import",
    reframe=authorized_model_adapter,
    ledger=ledger,
)

assert reframed["source_unchanged"] is True
assert reframed["access_loop_id"] != reframed["reframe_loop_id"]
assert reframed["workflow_mode"] == "hybrid"
```

The result keeps the original value and the reframed value separate. The
source guidance remains unchanged.

## Exact API map

| API | Purpose |
|---|---|
| `AdviceStore(path)` | Open one append-only JSONL guidance store |
| `leave_advice(text, scope=..., target=..., ...)` | Append one guidance item |
| `advice_for(scope, target)` | Read active guidance without recording a consultation |
| `consult(scope, target, loop_id=..., ledger=...)` | Read active guidance and record the consultation |
| `respond(advice_id, response, reason=..., ...)` | Append the loop's response to guidance |
| `responses_for(advice_id)` | Read all response rows for one guidance item |
| `retire_advice(advice_id, reason=...)` | Append a retirement tombstone |
| `rank_guidance(advices, policy_floor=...)` | Order guidance and surface recognized conflicts |
| `resolve_user_feedback_intelligence(store, targets, ...)` | Consult several scopes through one deterministic loop |
| `advice_records_for_search(store)` | Build active search records for this layer |
| `leave_guidance_as_loop(...)` | Add guidance through a Guidance Loop |
| `consult_guidance_as_loop(...)` | Consult guidance through a Guidance Loop |
| `guidance_for_as_loop(...)` | Display active guidance through a Guidance Loop |
| `query_intelligence(...)` | Search supplied intelligence layers and return LoopRefs |
| `materialize_intelligence_ref(...)` | Load one selected guidance item through its loop |
| `reframe_ref_with_model(...)` | Access guidance, then reframe a copy in a separate model loop |

## Current limitations

- `AdviceStore` trusts the supplied `author` string. It does not authenticate
  a person or organization.
- The store is one local JSONL file. It has no built-in multiwriter locking,
  remote synchronization, or tenant access-control service.
- `policy_floor` is supplied by the caller. The guidance store does not load
  organization or platform policy automatically.
- The conflict detector recognizes a small structural set of opposed guidance
  types. It does not understand every possible contradiction in free text.
- Timing is stored and searchable, but the store does not schedule work or
  enforce a safe execution boundary.
- Search cards include the original submitted status. Response history is
  available through `responses_for()`, but it is not joined into each search
  card today.
- Retirement removes guidance from the active view. It does not erase the
  append-only history.
- Model reframing needs a caller-supplied resolver and model adapter. The
  helper does not choose a provider or grant model permission.
- Guidance can shape a decision, but acting on it still needs normal effects,
  authorization, contracts, and verification.

These boundaries keep User Feedback Intelligence useful without treating a human note
as automatic authority or hidden runtime state.

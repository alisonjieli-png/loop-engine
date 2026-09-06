# Independent executable feedback for task repair

Status: implemented; task-local evidence only.

The public solve path requires independent executable checks before accepting
a generated project. The engine creates the checks and feeds their observed
failures into its existing repair loop. A caller does not need to supply
`TaskFeedback` for this cycle.

## Ownership

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, Solution
    ├── Versioned role profile
    ├── Mode: deterministic, hybrid, non-deterministic
    ├── Step profile and typed input/output contract
    ├── Loop and exit conditions
    ├── Graph relationships, budget, permissions, effect policy
    ├── Model settings when authorized
    └── Run History

Task execution
└── Starting Practitioner
    ├── selects and executes the next permitted action
    ├── spawns a Practitioner with practitioner.verifier@1.0.0
    │   ├── proposes contract checks with isolated model context
    │   ├── reviews the proposed oracle in another isolated call
    │   └── executes checks and records actual observations
    ├── adjudicates the result under the required verification policy
    └── repairs, investigates, continues, or returns a terminal result
```

The verifier is not a second runtime. Its policy, request, check bundle, and
report are passive data. Provider invocations and workspace effects keep their
existing Loop owners, permission checks, and shared accounting.

## Feedback and acceptance

The verifier receives the original task, registered acceptance criteria, a
digest-bound artifact inventory, and generated source needed to understand
the interface. It does not receive the producer's plan or conversation history.
Supplied data and computed output are copied into the sandbox without being
silently added to the model packet.

The model proposes Python probes and exact expected JSON or text values. A
separate model call reviews the oracle against the task. The probe prints
observations; the controller compares those observations outside the candidate
process. An empty response, an exit code alone, a forged `passed` field,
truncated output, or an unavailable verifier cannot satisfy acceptance.

Probe planning and file generation use separate requests. For a predeclared
Python file, the response may contain the planned JSON `path`/`content` object
or one exact Python source fence. The latter is a file-content representation,
not an instruction to run anything. The adapter keeps the planned path,
validates syntax, and records raw and source digests before oracle review.
Other response types cannot use this alternative.

Checks run in a separate Docker workspace. The prepared subject and checker
files are mounted read-only. Network access and host-process fallback are
refused. The exact image, mount policy, and resource declaration are bound to
command approval. Temporary output may use the existing disposable `/tmp`.

```text
candidate execution
  -> frozen subject and contract
  -> engine-generated checks and oracle review
  -> sandbox observations
  -> controller comparisons
  -> recorded verification findings
  -> next model-selected action or verified completion
```

Failure completes the verifier's observation responsibility. It does not cause
the same verifier activation to rerun effects. The parent receives the report
through `last_verification` and owns the next repair decision.
Operational checker failures remain separate from task gaps. The model sees
the runtime-owned `RETURN_RESULT` recheck action, which evaluates existing
artifacts without regenerating them. Provider failures use the existing
reasoned recovery service and shared accounting; the verifier adds no fixed
retry ceiling or output-token fallback.

## Retained regressions

The same check program runs on later candidate revisions. The engine retains
its inputs, commands, comparison rules, and expected values. A renamed or
missing subject interface cannot erase a failing check. If orientation merely
restates criteria, an isolated scope review may rebind criterion references;
it cannot edit the executable check or its expected result.

Acceptance checks the current source bytes again and validates the exact
report, probe bundle, execution artifact, and issuing Loop event. A historical
pass cannot approve changed files or a different task.

## Configuration and limits

`IndependentVerificationPolicy(required=True)` is the public default and is
independent of interaction mode. Legacy contract fixtures explicitly select
`required=False`; the runtime does not detect mocks or weaken real runs.
The policy and resulting reports appear in saved and public verification data.

This adds no model-call, pass, token-total, or spending ceiling. Calls use the
same authorized model session as the task, without copying its conversation.
The provider's source-backed capacity and explicit user budgets still apply.

The checker model can make mistakes. Isolated calls to the same model do not
establish statistical independence, exhaustive test coverage, or a correct
oracle for every possible task. Candidate code can still return values that
happen to match a test. Successful checks provide scoped evidence, not a proof
of unrestricted correctness.

Wrong-oracle requalification, arbitrary interface migrations, external-system
evaluation, durable cross-process continuation, and learned capability
promotion are separate work. The current path preserves unknowns rather than
silently weakening its checks. Required independent verification needs Docker,
even when a caller permits weaker host execution for the producer.

Task repair does not approve permanent self-modification. Persistent
intelligence remains candidate-only until a separately authorized qualification
process accepts it. A proposer cannot create reviewer authority by inventing
another actor name or changing its own acceptance policy.

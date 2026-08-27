# Governed learning cycle verification

## Result

The local governed learning vertical slice is verified working with an offline
deterministic fixture.

The proof covers candidate staging, independent review, explicit promotion,
later retrieval, observed use, a matched no-memory control, negative-transfer
blocking, rollback, and supersession. It does not prove production
effectiveness or external-provider behavior.

## Architecture used

    Operational runtime type
    └── Loop
        ├── Relationship
        │   ├── Starting
        │   ├── Spawned by
        │   ├── Queried by
        │   ├── Retrieved by
        │   └── Connected from
        ├── Role: Practitioner, Intelligence, or Solution
        ├── Mode: deterministic, hybrid, or non-deterministic
        ├── Typed input and output contract
        ├── Loop condition and exit condition
        ├── Budget, permissions, and effects
        └── Run History events

The learning proof uses the same runtime:

    Accepted Run A Practitioner Loop
    └── candidate staging Practitioner Loop
        └── append-only candidate record
            └── independent verifier Loop
                └── promotion-authority verifier Loop
                    └── active Learned intelligence
                        └── Run B queries an Intelligence Loop
                            └── selected item is materialized by an Intelligence Loop
                                └── Run B records observed use

Records, policies, decisions, references, and journal entries are passive typed
objects. They are not executable graph vertices.

## Current contract

The compatibility import remains
loop_engine.memory.storage.repository.CandidateJournal.

Candidate staging now requires:

- an actual completed canonical Loop object;
- an accepted Practitioner result;
- a typed LearningPolicy;
- an allowed MemoryScope; and
- at least one evidence reference.

The repository derives the durable producer identity from the Loop definition
and its definition-bound initialization event. A caller cannot submit an
arbitrary producer or reviewer string.

Review runs the supplied evaluator inside a new practitioner.verifier Loop.
Promotion runs its authorization check inside a second verifier Loop.
Producer, reviewer, and promotion identities must be non-empty and distinct.

Every transition binds:

- record ID;
- semantic version;
- content digest;
- producer Loop identity;
- reviewer Loop identity where required;
- operation Loop definition and event evidence;
- policy version;
- scope;
- evidence;
- decision and reason;
- prior journal-entry digest; and
- exact review-entry digest for promotion.

One JSONL line contains the transitioned record and governance record together.
The journal is append-only and hash-chained. Historical versions remain
available for audit. Normal retrieval materializes only the latest governed
state for each record ID.

## Legal lifecycle behavior

The implementation uses the existing lifecycle transition table.

    candidate
    ├── under_review
    │   ├── active
    │   └── rejected
    └── rejected

    active
    ├── revoked by rollback
    └── deprecated by explicit supersession

A stale version or digest is rejected before review or promotion. A rejected
candidate cannot be promoted. A revoked or deprecated latest version prevents
an older active version from leaking back into retrieval.

Supersession requires an exact active replacement. The replacement must name
the record it supersedes, keep the same scope, and have its own promotion
record.

## Two-run proof

Run A learned one bounded normalization:

    adress field -> address

The candidate retained fixture evidence, passed an independent exact-output
check, and was explicitly promoted.

The matched control used the same input and exact evaluator with fresh working
state but no retrieval. It returned adress, for a score of 0.0.

Run B also started with fresh working state. It queried Learned intelligence,
materialized the exact promoted version through Intelligence Loops, stored the
selected reference in the recalled compartment, applied the mapping, and
returned address, for a score of 1.0.

The saved use record binds the selected version and digest, query Loop,
evaluator evidence, result score, control score, and observed fixture delta.

| Measure | Offline fixture result |
|---|---:|
| No-memory control score | 0.0 |
| Learned-reuse score | 1.0 |
| Observed fixture delta | 1.0 |

This delta is a deterministic fixture result. It is not a production
benchmark.

## Negative transfer

A user-scoped spelling preference was reviewed and promoted. A project-scoped
query rejected that record before ranking. The same record remained available
to a user-scoped query.

The proof therefore shows scope isolation for this fixture. It does not claim
that every future applicability dimension is implemented.

## Rollback and supersession

Rollback appended a revoked version and left all earlier versions intact.
The revoked record stopped appearing in active retrieval.

Supersession appended a deprecated version of the old record, preserved the
replacement reference, and served only the active replacement.

## Verification

Focused command:

    PYTHONPATH=src python3 -c "from loop_engine.memory.storage.repository import self_test; r=self_test(); assert all(x['passed'] for x in r['tests']); print(len(r['tests']))"

Observed result on 2026-08-27:

    17

The focused checks include:

- actual Loop identity derivation;
- refusal of an arbitrary producer string;
- exact independent review;
- stale-reference refusal;
- exact review binding during promotion;
- terminal rejection;
- fresh no-memory control;
- later retrieval and observed use;
- measurable fixture improvement;
- fresh Run B working state;
- incompatible-scope negative-transfer blocking;
- append-only rollback;
- explicit supersession;
- journal hash-chain and record-digest validation; and
- read-back through a fresh repository object.

The repository-wide self-test passed 1,297 of 1,300 checks during this slice.
The three remaining failures named concurrent n-gram module classification,
collection of the n-gram module check, and shared architecture-map freshness.
No learning-cycle check failed.

## Files

- src/loop_engine/memory/storage/repository.py
- src/loop_engine/memory/storage/learning_records.py
- src/loop_engine/memory/storage/learning_cycle.py
- src/loop_engine/memory/storage/learning_cycle_checks.py

The implementation did not add Python code under governance/. That folder
remains a passive-record boundary as required by its local contract.

## Integration requirement

Older callers that use CandidateJournal.stage(record) must be migrated. They
now need an actual completed producer Loop, LearningPolicy, and
evidence-bearing candidate. Staging returns LearningTransitionResult. The
record ID is available as result.ref.record_id.

CLI and package-export changes are outside this slice and must use this strict
contract. They must not restore string-based producer or reviewer identities.

# Reactive Loop foundation verification report

## Result

The local reactive foundation is implemented and verified for one-machine
execution.

```text
Storage-neutral Loop values
→ verified

Reactive policy and output contracts
→ verified

Append-only candidate and portfolio serving
→ verified

Durable trigger, lease, fencing, and recovery state
→ verified

Concurrent canonical Loop activations through thread placement
→ verified

Distributed, process, remote-worker, and external subscription behavior
→ not yet verified
```

## Repository state

- Starting commit: `a7db02f25167a68c4d1e0b64b2fe57730fa35e80`
- Branch: `main`
- Provider calls during verification: `0`
- Remote actions: none
- Commit or push: none

## Focused evidence

| Component | Passed | Total |
|---|---:|---:|
| Storage-neutral information access | 9 | 9 |
| Reactive policy and output contracts | 9 | 9 |
| Reactive output store | 11 | 11 |
| Reactive scheduler | 12 | 12 |
| Asynchronous canonical Loop worker | 4 | 4 |
| Total focused checks | 45 | 45 |

The worker proof starts three independent activations. Each activation creates
one exact canonical Loop. All three blocking handlers start before any handler
finishes. The normal observed elapsed time is about 0.21 seconds for three
handlers that each block for 0.20 seconds.

The proof records activation-namespaced Loop IDs, such as:

```text
activation.<digest>.loop1
```

This prevents separate Run History trees from each calling their first Loop
only `loop1`.

## Full repository evidence

- Source-tree self-test: `1504/1504` passed.
- Source-tree conformance: every zero-tolerance gate passed.
- Focused parameter-boundary scan: zero findings in the new files.
- Repository-wide parameter-boundary debt remains: `175` unapproved findings.
  This work does not claim to repair that pre-existing population.
- Python compilation: passed.
- Ruff: unavailable in the source environment, so no Ruff result is claimed.
- YAML parsing and packaged contract equality: passed.
- Generated architecture map equality: passed.
- `git diff --check`: passed.

## Distribution evidence

The package was built into a fresh temporary output directory.

```text
wheel:
  loop_engine-0.1.0-py3-none-any.whl
  SHA-256: be16efd5d2ff43e92e8e71d097dce93cfc047c6af152b14f0f85c4088b532756

source distribution:
  loop_engine-0.1.0.tar.gz
  SHA-256: 865db031fa3145d76717222677d7639576053a2630dc7198dbce253c1a37596a
```

A fresh virtual environment installed the wheel and all declared dependencies.

- `pip check`: no broken requirements.
- Public reactive exports: present.
- Installed focused checks: `45/45` passed.
- Installed complete self-test: `1503/1503` passed.
- Installed provider calls: `0`.

## Behaviors proved

- One exact `LoopValueRef` resolves through inline memory, a
  content-addressed file, and SQLite.
- Public descriptors do not expose physical locator tokens.
- A reference does not grant project or cross-run access.
- Process-local information does not claim restart durability.
- Changed stored values fail digest verification.
- Reactive policies keep activation, admission, input scheduling,
  exploration, ranking, emission, serving, retention, and liveness separate.
- Candidate rank does not mutate the candidate.
- The same candidates can produce different policy-versioned rankings.
- Candidate and portfolio records are append-only and survive restart.
- A candidate producer cannot be its sole verifier.
- Duplicate or unchanged trigger input creates no new activation.
- Two scheduler workers cannot claim the same activation.
- Heartbeats extend only the current fenced lease.
- Expired leases recover within the attempt budget.
- A stale worker cannot commit after recovery.
- Exhausted work enters an explicit dead-letter terminal state.
- Three claimed activations run as three distinct canonical Loops with real
  wall-clock overlap.
- Reactive state changes project through the existing canonical Run History
  event vocabulary.

## Exact limitations

- Existing `LoopDefinition` records do not yet contain a reactive profile
  reference. The series definition currently binds the exact profile.
- The adaptive Practitioner does not yet compile reactive series automatically.
- The public task-build path still executes planned spawned Practitioner work
  serially.
- The local worker uses thread placement. CPU-bound process placement is not
  proved.
- Polling, webhooks, external brokers, subscriptions, acknowledgments,
  retractions, and transactional outbox delivery are not implemented.
- Durable information binding discovery after restart is not implemented.
- Cancellation propagation from a reactive series to running activations is
  not implemented.
- Remote workers, distributed leases, network partitions, and Kubernetes
  placement are not implemented.
- Studio does not yet show active series, leases, candidate archives, or
  portfolio evolution.
- Task-conditioned topology elasticity across unrelated task families remains
  unproved.
- CI was not run for the uncommitted local changes.

# Controlled mutations and ablations

A mutation changes one declared mechanism while preserving the task population, evaluator, backend identity and resource grant. The comparison manifest records the change. A deliberately broken control remains labeled as a fault injection, never a candidate implementation to ship.

| Mutation family | Variants to compare | Required observation |
|---|---|---|
| Context | Full bounded push, horizon slices, scoped pull on miss | Delivered bytes and identities, missing information, quality, latency |
| Process lifetime | Fresh process, persistent session, bounded pool | Actual process identities, no cross-request state, startup and queue time |
| Decomposition | Single attempt, adaptive split, divide first | Explicit task dependencies, accepted output per subtask, complete failed attempts |
| Model route | Fixed model, exact per-kind tier, bounded diverse models | Actual physical provider/model identity and complete accounting |
| Reuse | Cold, qualified reuse, drifted asset, wrong-shape asset | Eligibility, refusal, independent fresh-input verification, transaction integrity |
| Persistence | No durable state, durable admission, interrupted activation | Recorded outcome, reconciliation and non-replay of committed effects |
| Portfolio | First verified, best verified, Pareto, seeded random verified | Versioned independent evaluations; provisional output cannot become verified implicitly |
| Containment | Trusted host, bubblewrap, pinned container, stronger VM isolation | The actual code-running process, mounts, network, limits and cancellation |

The runnable lab already compares process lifetimes and candidate portfolios. Other mutations require their planned adapters. Use the catalog to retain this distinction instead of generating thousands of empty folders for an unqualified Cartesian product.

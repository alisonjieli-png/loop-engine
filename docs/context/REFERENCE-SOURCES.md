# Older sources are references, not dependencies

Loop Engine is developed from `/home/username/loop-engine`. Its remote is
`https://github.com/alisonjieli-png/loop-engine.git`.

The old local directory for the previous repository name is absent. Do not
recreate it. Earlier project history remains available through the Loop Engine
Git history and the clearly labeled design-history documents.

## Current Loop Engine context

The development context that belongs in this repository is already present:

```text
Loop Engine development context
├── AGENTS.md
│   └── coding-agent rules and architecture invariants
├── docs/context/CODEX-START-HERE.md
│   └── short new-session entry point
├── humanizer-context.md
│   └── public writing rules
├── README.md and docs/components/
│   └── current architecture from high level to component detail
├── src/loop_engine/strings/core_seed_intelligence_v2.jsonl
│   └── active seed Context Intelligence
├── src/loop_engine/strings/generated_candidates.jsonl
│   └── candidate-only generated Context records
├── Intelligence Search and Retrieval
│   └── classification, retrieval, materialization, and lifecycle rules
├── Code Intelligence registrations
│   └── typed callable, package, repository, and large-system references
├── benchmarks/
│   └── frozen task populations and independently checked run artifacts
└── case-studies/
    └── admitted full-system results, failures, accounting, and limits
```

Runtime History and Solution Intelligence and User Feedback Intelligence may
be empty for a new installation. Empty layers remain visible. Runtime Memory
remains temporary and is not copied into a persistent layer automatically.

## Reference locations

| Location | Status | Useful design input | Do not import |
|---|---|---|---|
| `/home/username/taedri.dev` | Separate active repository | Evidence discipline, typed task capsules, result-state separation, idempotent effects, independent verification, and reusable capability admission | Its authority registry, campaign system, business claims, task queues, file layout, product names, or whole modules |
| `/home/username/taedri-loop-v2-runtime-20260824` | Isolated candidate worktree, not Taedri main | Candidate designs for versioned Loop specifications, attempt identity, exact effect binding, and candidate-only Runtime Memory curation | Any file copied without reimplementation, isolated status claims, unmerged assumptions, or Taedri-specific names |
| Other `/home/username/taedri-loop-v2-*` worktrees | Experimental branches with different scopes | A specific contract only after its branch, commit, tests, and relationship to Taedri main are rechecked | Cross-worktree bulk merges, registries, generated evidence, or an assumption that an isolated result reached main |
| `docs/reference/` and selected `docs/architecture/` files in Loop Engine | Preserved design history | Earlier questions, rejected designs, and provenance | Current product behavior unless a current component guide and code path confirm it |
| `docs/internal/` in Loop Engine | Internal history and handoffs | Why a current decision was made | Public claims or runtime authority |

These paths can change. Inspect their current revision and dirty state before
using them as design input.

## Semantic integration rule

Do not move an old file into Loop Engine merely because part of it is useful.
Move one verified invariant at a time:

```text
Older source idea
├── State the invariant in plain English
├── Identify the exact Loop Engine gap
├── Map it to one existing component
├── Reuse Loop Engine public terms
├── Design the smallest typed contract change
├── Add positive and adversarial tests
├── Run it through the universal Loop runtime
├── Verify the real integrated behavior
└── Record source repository and revision as design provenance
```

Reject the transfer when it would create:

- another operational runtime;
- another event history or source of truth;
- a parallel registry or intelligence layer;
- a second approval, provider, workspace, or retrieval abstraction;
- Taedri-specific authority levels or business rules in the open package;
- old product terms in public documentation;
- unverified benchmark, cost, provider, or performance claims;
- copied data, credentials, caches, environments, or generated run output.

## High-value semantic candidates

The current audit identified these candidates. They are not all implemented
yet.

| Invariant to reimplement | Existing Loop Engine boundary |
|---|---|
| One immutable task capsule binds source, license, files, schemas, evaluator, leakage boundaries, budgets, and ambiguities. | `LoopContract`, `DelegationSpec`, `HarnessRunRequest`, and benchmark manifests |
| Attempted, artifact-valid, score-valid, accepted, paired, selected, promoted, and invalidated are separate result states. | benchmark evaluators, `HarnessRunResult`, case studies, and comparison reports |
| Retry identity and idempotency are explicit before any effect can repeat. | `EffectApprovalService`, MCP, workspaces, external harnesses, and `SpawnedTaskManager` |
| A role-neutral Loop profile binds worker, independent verifier, environment digest, permissions, effects, and budget. | `LoopProfileRef`, `LoopContract`, and `DelegationSpec` |
| Runtime Memory curation is scoped, candidate-only, and cannot claim promotion. | Runtime Memory, `SkillRegistry`, Context Intelligence, and the harness intelligence bridge |

Each row requires its own implementation and verification. This table is not
evidence that the transfer is complete.

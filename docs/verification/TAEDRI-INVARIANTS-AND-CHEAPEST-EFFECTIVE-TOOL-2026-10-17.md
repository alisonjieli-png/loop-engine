# Taedri-provenance semantic invariants and six-tier cheapest-effective-tool escalation ladder (2026-10-17)

This report records the design provenance, implementation, 24-task head-to-head
benchmark, and adversarial verification of the two-slot, nine-engine hybrid
suite in
[tools/taedri_invariants_and_cheapest_tool_ladder_engines.py](../../tools/taedri_invariants_and_cheapest_tool_ladder_engines.py)
and
[tools/test_taedri_invariants_and_cheapest_tool_ladder_engines.py](../../tools/test_taedri_invariants_and_cheapest_tool_ladder_engines.py).

## Design provenance and scope

Following [docs/context/REFERENCE-SOURCES.md](../context/REFERENCE-SOURCES.md)
at Loop Engine revision `b3001c15`, no files, registries, authority tables, or
product names were copied from older repositories. Instead, the five semantic
invariants listed in the reference audit table were re-implemented in native
Loop Engine contracts (`LoopContract`, `DelegationSpec`, `HarnessRunRequest`,
`HarnessRunResult`, `EffectApprovalService`, `LoopProfileRef`, and scoped
`RuntimeMemory`) and paired with the six-tier cheapest-and-most-effective tool
escalation ladder inside the seven-layer component envelope defined in
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py)
and
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py).

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Task capsules,
result-state transition records, idempotency bindings, static embedding
indices, and escalation tier adapters are passive data or swappable engine
adapters used by a `Loop`, never separate graph vertices or secondary runtimes.

```text
Loop
├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Category: organization and search taxonomy across library components
└── Settings: contract, loop condition, exit condition, budget, and permissions
    ├── Discrete cognitive or act step Loop node behavioral guarantees:
    │   ├── Narrowly scoped assignment with selected context and resources
    │   ├── Separately initialized harnesses and permitted harness changes
    │   ├── Expectation checks and iteration until declared completion conditions
    │   ├── Continued production of alternative outputs when configured
    │   ├── Protection against repeated external effects before retry
    │   └── Separation of output publication from Loop completion
    └── Swappable engine slots wrapped in 7-layer ComponentEnvelope:
        ├── Slot Family 1: taedri_semantic_invariants_slot
        │   ├── Engine 1A: immutable_task_capsule_engine
        │   ├── Engine 1B: eight_stage_result_state_machine_engine
        │   └── Engine 1C: idempotent_effect_and_profile_binding_engine
        └── Slot Family 2: cheapest_effective_tool_ladder_slot
            ├── Tier L0: tier0_deterministic_code_and_math_engine ($0.00000, 0.08 ms)
            ├── Tier L1: tier1_cpu_simd_lsh_and_static_embedding_engine ($0.00000, 0.65 ms)
            ├── Tier L2: tier2_jev_system_one_and_classifier_engine ($0.00002, 4.20 ms)
            ├── Tier L3: tier3_specialized_timeseries_and_tabular_engine ($0.00008, 18.50 ms)
            ├── Tier L4: tier4_cheap_local_or_ollama_coding_engine ($0.00045, 380.00 ms)
            └── Tier L5: tier5_frontier_reasoning_escalation_engine ($0.01200, 2100.00 ms)
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Slot Family 1: Five semantic invariants (`taedri_semantic_invariants_slot`)

The three engines in `taedri_semantic_invariants_slot` enforce all five
semantic candidates from
[docs/context/REFERENCE-SOURCES.md](../context/REFERENCE-SOURCES.md):

| Invariant | Owning engine | Loop Engine types bound | Enforced check |
| :--- | :--- | :--- | :--- |
| 1. Immutable task capsule | `immutable_task_capsule_engine` | `LoopContract`, `DelegationSpec`, `HarnessRunRequest`, `TaskCapsule` | Computes a canonical SHA-256 digest over source revision, SPDX license, allowed file paths, holdout leakage paths, input/output schemas, deterministic evaluator digest, token/dollar/memory budgets, and ambiguity rules; refuses holdout path overlap |
| 2. Eight-stage result-state separation | `eight_stage_result_state_machine_engine` | `HarnessRunResult`, `ResultStateTransitionRecord` | Separates `attempted`, `artifact_valid`, `score_valid`, `accepted`, `paired`, `selected`, `promoted`, and `invalidated`; enforces monotonic single-step progression and refuses promoting syntax-only or unverified candidates |
| 3. Explicit retry identity and outcome reconciliation | `idempotent_effect_and_profile_binding_engine` | `EffectApprovalService`, `IdempotentEffectAndProfileBinding` | Requires a non-empty idempotency key and refuses any retry unless prior external effect state is reconciled as `confirmed_absent` (`reconcile_before_retry`) |
| 4. Role-neutral Loop profile separation | `idempotent_effect_and_profile_binding_engine` | `LoopProfileRef`, `LoopContract`, `DelegationSpec` | Binds worker profile, independent verifier profile, environment digest, and declared effects; refuses `worker_id == independent_verifier_id` |
| 5. Candidate-only Runtime Memory curation | `idempotent_effect_and_profile_binding_engine` | `RuntimeMemory` | Enforces `curation_status == "candidate_only"` and `claims_promotion == False` so temporary runtime notes never claim persistent admission |

## Slot Family 2: Six-tier cheapest-and-most-effective tool escalation ladder (`cheapest_effective_tool_ladder_slot`)

The ladder begins at the lowest-cost deterministic tier capable of solving the
task class, runs a deterministic verifier and calibrated confidence gate at
each tier, and escalates only when a lower tier's check fails or epistemic
uncertainty exceeds the tier ceiling:

| Tier | Engine ID | Unit cost (USD) | Nominal latency (ms) | Nominal tokens | Confidence gate | Qualified tools and methods |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `L0` | `tier0_deterministic_code_and_math_engine` | $0.00000 | 0.08 | 0 | 0.99 | Exact AST transforms, unit conversions, JSON schema validation, financial and physics formulas, SQL and regex rules |
| `L1` | `tier1_cpu_simd_lsh_and_static_embedding_engine` | $0.00000 | 0.65 | 0 | 0.92 | `Model2Vec` static embeddings, 64-bit Binary Matryoshka Hamming distance, MinHash LSH, `FlashRank` CPU reranking |
| `L2` | `tier2_jev_system_one_and_classifier_engine` | $0.00002 | 4.20 | 16 | 0.88 | `Jev /v1/systemone`, `Laya` fast router, `GLiClass` zero-shot boolean, enum, and safety classifiers |
| `L3` | `tier3_specialized_timeseries_and_tabular_engine` | $0.00008 | 18.50 | 32 | 0.86 | `Chronos-Bolt`, `TimesFM-2.0` time-series forecasting, and tabular group cross-validation scoring |
| `L4` | `tier4_cheap_local_or_ollama_coding_engine` | $0.00045 | 380.00 | 140 | 0.84 | `gemma4:31b` and `qwen3-coder:30b` guided by Baltor contract cards under 200 tokens plus a deterministic verifier gate |
| `L5` | `tier5_frontier_reasoning_escalation_engine` | $0.01200 | 2100.00 | 1850 | 0.80 | Frontier reasoning models (`Claude Opus/Sonnet`, `GPT-5-Codex`, `GLM-5.3`, `DeepSeek-R1`) invoked only on L0-L4 verifier failure or high uncertainty |

### Closed-loop telemetry utility adjuster

`ClosedLoopTelemetryUtilityAdjuster` updates empirical pass probabilities after
every trial and computes tier utility as:

```text
ExpectedUtility(tier) = P(pass | tier, task_class) - lambda_cost * Cost - lambda_lat * (Latency_ms / 1000.0)
```

When a tier fails verification on a task, the adjuster tightens that tier's
confidence gate (`+0.015`, bounded at `0.995`) and routes subsequent high-risk
tasks up the escalation ladder automatically.

## 24-task head-to-head benchmark results

`run_head_to_head_benchmark()` evaluates 24 diverse tasks across all six task
classes (five `L0` exact math/schema tasks, five `L1` SIMD/LSH retrieval tasks,
four `L2` classifier tasks, four `L3` time-series/tabular tasks, four `L4`
contract-card coding tasks including one high-uncertainty task that escalates
from `L4` to `L5`, and two `L5` multi-constraint reasoning tasks):

| Strategy | Total cost (USD) | Total tokens | Mean latency (ms) | p95 latency (ms) | Verified pass count | Verified pass rate |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `always_frontier_llm_baseline_without_baltor` | $0.28800 | 44,400 | 2100.000 | 2100.000 | 23 / 24 | 95.83% |
| `unverified_cheap_only_baseline` | $0.00008 | 64 | 2.602 | 4.200 | 14 / 24 | 58.33% |
| `baltor_6tier_cheapest_effective_ladder` | $0.03820 | 6,282 | 329.769 | 2100.000 | 24 / 24 | 100.00% |

Observed tier distribution for `baltor_6tier_cheapest_effective_ladder`:
`L0: 5`, `L1: 5`, `L2: 4`, `L3: 4`, `L4: 3`, `L5: 3` (86.74% dollar cost
reduction and 85.85% token reduction compared to the always-frontier baseline,
while raising verified pass rate from 58.33% on the unverified cheap-only
baseline to 100.00%).

## Known-wrong and adversarial controls

The unit test suite in
[tools/test_taedri_invariants_and_cheapest_tool_ladder_engines.py](../../tools/test_taedri_invariants_and_cheapest_tool_ladder_engines.py)
verifies six explicit refusal controls:

1. **Holdout leakage in task capsule (`holdout_leakage_boundary_intact`)**:
   Intersecting `allowed_file_paths` and `holdout_leakage_paths` is refused at
   Layer 6 (`preflight`).
2. **Skipped result states (`non_monotonic_or_skipped_state_transition`)**:
   Attempting to promote an `artifact_valid` candidate directly to `promoted`
   without passing `score_valid`, `accepted`, `paired`, and `selected` is
   refused at Layer 6.
3. **Unverified acceptance (`acceptance_requires_passing_score_and_independent_verifier`)**:
   Transitioning from `score_valid` to `accepted` when
   `independent_verifier_passed=False` is refused.
4. **Unreconciled effect retry (`effect_retry_requires_prior_outcome_reconciliation`)**:
   Retrying an effect when `reconciliation_state == "unknown"` is refused at
   Layer 5 (`tracking`) with `retry=reconcile_before_retry`.
5. **Worker self-verification (`worker_cannot_be_own_independent_verifier`)**:
   Binding a profile where `worker_id == independent_verifier_id` is refused,
   as is any `RuntimeMemory` record claiming direct promotion
   (`runtime_memory_must_remain_scoped_candidate_only`).
6. **Unnecessary frontier spend (`refuse_unnecessary_frontier_spend_when_tier0_solves`)**:
   Forcing Tier `L5` frontier execution on a task that Tier `L0` deterministic
   math/unit verification solves is refused at preflight before any model spend
   occurs.

## Reproduction commands and limits

Run the unit test suite and benchmark self-test from the repository root:

```bash
PYTHONPATH=src:tools /home/username/loop-engine/.venv/bin/python -m unittest -v tools/test_taedri_invariants_and_cheapest_tool_ladder_engines.py
PYTHONPATH=src:tools /home/username/loop-engine/.venv/bin/python tools/taedri_invariants_and_cheapest_tool_ladder_engines.py
```

Current limits:

- All tier engines execute against deterministic in-memory verifiers and
  recorded cost/latency profiles so continuous integration remains reproducible
  and offline without external model spend.
- Live Ollama Cloud or external provider calls require explicit customer or
  session model authority under `HarnessRunRequest`.

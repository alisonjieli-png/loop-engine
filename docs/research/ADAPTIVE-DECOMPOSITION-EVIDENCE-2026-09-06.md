# Adaptive decomposition and independent verification

Decomposition is a candidate decision with a cost. The reviewed experiments
support trying different amounts of structure for different tasks and
executors. They do not establish one best step sequence or unlimited physical
recursion. Loop Engine keeps the shared runtime and existing authority:

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
    ├── Model settings when model use is authorized
    └── Run History records
```

## Verified primary-source findings

All results below are author-reported. This review checked the primary sources
but did not reproduce their experiments. Percentages from different models,
task populations, or evaluators are not a comparison between Loop Engine and
another system.

| Source | Tested evidence | Candidate adaptation and falsifier |
|---|---|---|
| Prasad et al., [ADaPT](https://arxiv.org/html/2311.05772v2), 2024 | Attempts execution before recursively decomposing failures. GPT-3.5 achieved 71.6% success on 134 ALFWorld games; the ReAct comparison achieved 43.3%. Its intermediate success judgment uses an LLM heuristic, and its experiments use maximum depths. | Consider splitting after a valid failed attempt. Reject the adaptation if mistaken success prevents useful splitting or infrastructure failures cause pointless recursive work. |
| Khot et al., [Decomposed Prompting](https://arxiv.org/html/2210.02406v2), 2023 | Delegates generated subquestions to prompts, learned models, or symbolic functions. The tasks include symbolic operations, recursive list reversal, CommaQA, and retrieval QA. Handlers and decomposition examples are task-designed. | Reuse qualified capabilities for subproblems. Reject replacements whose local correctness changes the downstream result. |
| Yao et al., [ReAct](https://arxiv.org/html/2210.03629v3), 2023 | Interleaves reasoning, actions, and observations. In the PaLM-540B table, FEVER accuracy increases from 56.3% to 60.9%, while HotpotQA exact match decreases from 29.4% to 27.4%. | Replan after informative observations. Measure repeated actions and unsuccessful retrieval as well as gains. |
| Xu et al., [ReWOO](https://arxiv.org/html/2305.18323v1), 2023 | On 1,000 HotpotQA examples, tokens decrease from 9,795.1 to 1,986.2. GPT-4-scored semantic accuracy increases from 40.8% to 42.4%; exact match decreases from 32.2% to 30.4%. | Plan ahead when later choices do not need new observations. Reject the adaptation when repair after unexpected observations removes its savings. |
| Kim et al., [LLMCompiler](https://arxiv.org/html/2312.04511v3), 2024 | Separates dependency planning, dispatch, and execution. GPT HotpotQA latency was 3.95 seconds versus 7.12 for an adjusted ReAct baseline; accuracy was 62.00% versus 62.47%. | Use existing graph and concurrency contracts. Parallel execution must preserve state, effects, and acceptance relative to the same serial plan. |
| Guo et al., [TYGAR](https://arxiv.org/abs/1911.04091v1), 2019 | Type-guided synthesis evaluated 44 Haskell query types over 291 components. An interesting solution appeared among the first five for 33 queries. | Reject incompatible compositions before execution. Type correctness still needs behavioral verification, including units and error behavior. |
| Zhou et al., [Self-Discover](https://arxiv.org/html/2402.03620v1), 2024 | Selects and adapts reasoning modules. GPT-4 BBH aggregate accuracy was 81% versus CoT's 75%; the 200-example MATH evaluation was 73% versus 71%. Structure discovery has extra calls. | Keep reasoning structures as optional candidates. Include discovery cost and minimal-structure controls. |
| Gunasekara and Ratnayake, [Effects of structure on reasoning in instance-level Self-Discover](https://arxiv.org/abs/2507.03347), 2025 | Reports up to 18.90% relative improvement on MATH for unstructured reasoning compared with dynamically generated JSON reasoning in its open-source-model experiments. | This concerns the tested reasoning format. It does not justify removing typed tool, authority, or result envelopes. |
| Huang et al., [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/html/2310.01798v2), 2024 | GPT-4 accuracy on 200 sampled GSM8K questions decreased from 95.5% to 91.5% after one intrinsic correction round. Oracle stopping reached 97.5%. These are particular historical models and prompts. | Prefer evidence-backed repair. Test whether correction reduces false acceptance and preserves valid work with the configured current model. |
| [SWE-ContextBench](https://arxiv.org/html/2602.08316v3), 2026 | Its 99-task related-task Lite experiment with Claude Sonnet 4.5 reports 34.34% for oracle-selected summaries, 26.26% without experience, and 22.22% for freely selected summaries. | Keep the option to ignore retrieved material. Test retrieval precision, cost, and negative transfer on separate task lineages. |

## Repository decisions

The current adaptive planner is the admission boundary for keep-versus-spawn
choices. The canonical kernel executes admitted work. Task scope, verification,
and state must remain separate when a Practitioner spawns another Practitioner.
No completion flag from one subproblem can certify the whole task.

`development_planning.compile_plan_to_loop_graph` already compiles typed task
slices into the canonical graph. `DelegationSpec` already supplies visibility,
permissions, budgets, and returned ports. Further dependency-output bindings
should extend those contracts. A second task graph or memory store would leave
the existing authorities in conflict.

The current `InformationResolver`, `LoopValueRef`, `MemoryRef`, and
`RecordOperationService` already cover parts of the proposed memory and record
interfaces. Remaining work includes revocable access grants, explicit
model-disclosure policy at materialization, and durable mutation retry
identities. [SpiceDB's consistency documentation](https://authzed.com/docs/spicedb/concepts/consistency)
helps distinguish snapshot identity from permission freshness.
[DuckDB's security documentation](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview)
supports controlled query construction; arbitrary SQL can access external
resources and must not become an implicit write authority.

## Next experiments

Freeze tasks, source revisions, capabilities, verifiers, and inclusion rules
before running comparisons. First compare direct execution with optional
decomposition on simple tasks, dependent subproblems, and tasks where an
observation changes the next action. Report false acceptance, retained valid
work, calls, tokens, elapsed time, and cost completeness for every attempt.

A second experiment should compare the same task with selected prior material
and a fresh context. The current paired fixture remains `mechanism_only`.
Canonical assignments, exact treatment-free packet comparison, source freezing,
independent evaluator identity, and public-history-to-projection reconstruction
are still required before a live causal-assistance claim.

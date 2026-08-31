# Reusable Capability Flywheel authority and research map

This document records what the repository already owned, what was missing,
and how the implementation uses the cited research. Live source and enforcing
tests remain authoritative.

## Repository authority map

| Concern | Existing authority | Existing behavior | Gap before this change | Integrated change |
|---|---|---|---|---|
| Canonical execution | `src/loop_engine/loop/recursive_loop.py:Loop` | One sealed runtime for Practitioner, Intelligence, and Solution roles. | Reuse stages were not connected. | Every new operation enters through `Loop` by `as_loop`, the reactive executor, or a hybrid Loop. |
| Role profiles | `src/loop_engine/loop/loop_profile_catalog.py:LoopProfileSpec` | Registered role, mode, step, and capability policy. | Hybrid reuse variations had no shared profile data. | Assistance presets are passive stage profiles under the existing hybrid mode. |
| Exact definitions | `src/loop_engine/loop/loop_definition.py:LoopDefinition` | Immutable version and content digest for runnable Loops. | Harvest work had no registered reactive definition in one circuit. | The async proof binds a `ReactiveSeriesDefinition` to one exact definition. |
| Code Intelligence | `src/loop_engine/core/code_intelligence_assets.py:CodeAssetSpec` | Small search card plus immutable external body reference. | No exact independent Code asset admission record. | `CodeAssetAdmissionRecord` binds artifact, dependency, contract, and effect digests. |
| Candidate discovery | `src/loop_engine/core/solution_library.py:SolutionLibrary` | Typed task compatibility and candidate discovery. | It did not govern generated Code asset lifecycle. | The flywheel uses the same separation of discovery, eligibility, selection, and execution. |
| Catalog authority | `src/loop_engine/catalog/protocol.py:CatalogStore` | One backend-neutral record contract with declared capabilities. | No reusable-capability authority record family. | Candidate, admission, lifecycle, transition, alias, and projection records use the supplied catalog store. |
| Search projection | `src/loop_engine/catalog/query.py:IntelligenceQuery` | Typed structured query across backends. | No rebuildable promoted-capability projection. | `rebuild_capability_projection_as_loop` derives an active view from current authority records. |
| Reactive work | `src/loop_engine/core/reactive_scheduler.py:SQLiteReactiveScheduler` and `src/loop_engine/core/reactive_worker.py:AsyncReactiveWorker` | Idempotent triggers, leases, fencing, retries, recovery, and exact Loop execution. | Accepted results did not emit a reuse activation. | `dispatch_reuse_opportunity_as_loop` publishes an exact `LoopValueRef` and admits a reactive trigger. |
| Information access | `src/loop_engine/core/information_access.py:InformationResolver` | Storage-neutral values with scope, permission, size, and digest checks. | Queue work needed a body-free event reference. | The reuse event is published separately and the trigger stores only its exact reference. |
| Independent evaluation | `src/loop_engine/core/reactive_output_store.py:SQLiteReactiveOutputStore` | Refuses a producer as the sole verifier. | Code asset qualification did not reuse the same rule. | Code admission and promotion enforce producer separation. |
| Run evidence | `src/loop_engine/core/run_history.py:RunHistory` | Immutable hash-chained event history. | Flywheel transitions were not represented in one run. | All operational stages run as Loops, and lifecycle transitions are also immutable catalog records. |
| Effects and workspaces | `src/loop_engine/loop/effect_approval.py:EffectApprovalService` and `src/loop_engine/core/workspace_operations.py:WorkspaceOperationService` | Exact effect approval and confined execution. | The first flywheel slice needed a safe execution scope. | The demonstrated artifact is pure and in memory. Effectful and untrusted-code promotion still requires these existing boundaries. |
| Context Intelligence | `src/loop_engine/intelligence/context/core` | Packaged candidate and registered context records. | The Practitioner portfolio lived outside its named layer, with no explicit outage record. | The full portfolio moved into Context Intelligence and a separate minimum fallback was added. |
| Canonical semantic identity | `src/loop_engine/loop/loop_definition.py:LoopDefinition` | Exact role, modes, contract, conditions, capabilities, configuration facts, version, and digest. | No complete implementationless behavior contract was bound into the definition. | `SemanticLoopContractDraft` is digested into exact definition configuration facts, then bound back to that exact definition. |
| Semantic realization | `src/loop_engine/core/semantic_runtime.py:select_semantic_realization` | The repository already separates mode, profile, and executor availability. | One contract could not compare qualified code and interpreter realizations. | Hard eligibility selects deterministic code, hybrid interpretation, or direct interpretation without adding a mode or runtime. |
| Model boundary | `src/loop_engine/loop/encapsulate.py:as_model_loop` and `src/loop_engine/core/model_gateway.py:ModelGateway` | Model calls run inside a Loop and configured providers preserve identity and usage. | There was no contract-level interpreter profile or effective ProgramID. | `SemanticInterpreterProfile` and `SemanticProgramIdentity` bind model/runtime, context, tools, verification, and effects. The fixture transport is injected and does not prove a live provider. |
| Trusted state and effects | `src/loop_engine/loop/effect_approval.py:EffectApprovalService` and `src/loop_engine/catalog/protocol.py:CatalogStore` | Exact external-effect approval and optimistic catalog writes already exist. | Model proposals were not represented as explicit deltas with a commit gate. | `ProposedStateDelta`, issued verifier/effect records, and `CatalogTrustedSemanticState` require exact compare-and-swap commit. External effects still require the existing approval service. |
| Semantic materialization | `src/loop_engine/core/reusable_capability_harvest.py:harvest_reuse_opportunity_as_loop` | Accepted code can enter candidate review. | Repeated semantic behavior could not become a realization under the same contract. | The routing proof harvests a semantic procedure into a Code Intelligence candidate, qualifies and promotes it, then binds it back to the unchanged semantic contract. |

## Similar code that is not the authority

`IntelligenceRegistry` and `Resource` contain older lifecycle adapters. They
remain compatibility layers and do not become a second flywheel registry.
`SkillAdmissionRecord` is exact and independently reviewed, but it is specific
to Agent Skill manifests. The Code asset admission record follows its trust
pattern without treating a function as a skill.

`SolverStore` supports a useful deterministic search path. The new authority
uses the backend-neutral `CatalogStore` because it already defines the current
unified catalog contract and rebuildable projections.

## Architecture contradictions resolved

The term “loop node” is colloquial. The current concrete runtime is `Loop`.
Passive policies, records, and projections must not inherit from it.

The three modes are not three classes, and hybrid variations are not new
modes. They are assistance stage profiles under `hybrid`.

The reuse resolver can try exact deterministic capability resolution for a
typed `CapabilityNeed`. This does not replace the product solve rule that a
new open-ended task may begin with model-led orientation. A local resolver
ordering is not a universal product ordering.

The 1 to 10 reuse score is stored as a summary. It cannot create, qualify, or
promote a capability by itself.

## Primary research synthesis

| Source | Relevant pattern | Limit for Loop Engine | Decision supported |
|---|---|---|---|
| [Large Language Models as Tool Makers](https://arxiv.org/abs/2305.17126) | A costly tool-making step can be amortized through later tool use. | Its tool maker and user split does not provide Loop Engine lifecycle authority. | Treat generated functionality as a candidate functional cache, then qualify it separately. |
| [Voyager](https://arxiv.org/abs/2305.16291) | Executable skills can accumulate, retrieve, improve from errors, and compose. | Minecraft feedback is narrower than general software effects and tenant policy. | Keep executable artifacts, descriptions, error evidence, and composition available as separate records. |
| [CRAFT](https://arxiv.org/abs/2309.17428) | Generate, validate, abstract, deduplicate, then retrieve tools. | Training-example validation is not enough for production admission. | Put abstraction and deduplication before promotion, and keep validation exact. |
| [CREATOR](https://arxiv.org/abs/2305.14318) | Tool creation separates abstract reasoning from concrete execution. | Query-time creation alone does not build a durable governed library. | Preserve a novel-build path, but send accepted outputs into asynchronous harvesting. |
| [ToolLibGen](https://arxiv.org/abs/2510.07768) | Growing libraries need clustering, shared-logic extraction, and review. | Multi-agent consolidation cannot approve itself. | Keep offline consolidation as a separate reviewed plane. The current slice implements exact duplicate consolidation only. |
| [ToolGate](https://arxiv.org/abs/2601.04688) | Preconditions gate invocation and postconditions gate trusted state changes. | Its symbolic state model is not the Loop Engine catalog and Run History model. | Recheck hard eligibility before invocation and accept output only after an independent postcondition. |
| [Auto-Dreamer](https://arxiv.org/abs/2605.20616) | Fast online acquisition should be separate from slower cross-session consolidation. | Its learned memory bank is not executable Code Intelligence authority. | Keep source completion fast, make harvesting async by default, and consolidate offline. |
| [AllocBench](https://arxiv.org/abs/2607.23332) | Models can perform well on abstract allocation but fail to transfer that choice to script construction. | The benchmark does not define Loop Engine promotion policy. | Keep model reuse scores advisory and require structured evidence plus independent qualification. The current arXiv title is AllocBench, not AlloBench. |
| [AIOS Compiler and CoRE](https://arxiv.org/abs/2405.06907) | An LLM can interpret structured natural-language and pseudo-code programs. | Natural-language ambiguity and interpreter identity change behavior. | Treat semantic execution as one possible resolver behind a typed, versioned contract, not as trusted state. |
| [Agent JIT Compilation](https://arxiv.org/abs/2605.21470) | Generated executable plans can reduce repeated sequential model calls, with preconditions and postconditions. | It compiles to code, so it is adjacent to direct specification interpretation rather than the same model. | Allow generated plans or code as candidate artifacts, while keeping the specification and verification policy authoritative. |

## Semantic execution research matrix

The implementation decisions below are repository design inferences. The
linked papers and official repositories do not prove Loop Engine behavior.

| Source or system | Primary link | Execution model | Canonical artifact | Online or offline | Verification boundary | State and effect model | Reuse and indexing | Runtime version handling | Measured strength | Measured limitation | Loop Engine decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AIOS Compiler and CoRE | [paper](https://arxiv.org/abs/2405.06907) | LLM interprets structured natural language, pseudo-code, and flow programs. | Structured program plus interpreter. | Online execution with memory and tools. | Mainly task results in the reported experiments. | External memory and tool calls, not Loop Engine authority. | Program reuse is possible, but governed promotion is outside its scope. | Results depend on the selected interpreter model. | Unifies several natural-language program styles. | Natural-language ambiguity and interpreter dependence remain. | Use direct interpretation as one realization behind an exact contract, verifier, and commit gate. |
| Agent JIT | [paper](https://arxiv.org/abs/2605.21470) | Compiles a task to executable code plans and schedules tool calls. | Generated plan or code. | Online planning and execution. | Tool specifications, preconditions, postconditions, and plan selection. | Invariant-enforcing tool protocol. | Generated plans can remove repeated model calls. | Planner, tool protocol, and latency model affect behavior. | Reports lower latency and higher accuracy on its web-agent evaluation. | It is code/plan generation, not pure spec-to-result interpretation. | Benchmark it as a separate realization and keep generated plans candidate-only until qualified. |
| Marvin | [official repository](https://github.com/PrefectHQ/marvin) | Typed structured-output functions and agent tasks delegate work to models. | Type/result declaration plus instructions. | Online. | Structured result parsing through the library interface. | Tool and task behavior depend on application configuration. | Current public surface focuses on reusable structured-output utilities and tasks. | Provider and library versions may change behavior. | Shows a practical typed function-like developer surface. | The surface alone does not provide Loop Engine lifecycle, effect, or independent commit authority. | Do not copy a decorator runtime. A future decorator may only register the canonical Loop contract. |
| DSPy | [paper](https://arxiv.org/abs/2310.03714), [official repository](https://github.com/stanfordnlp/dspy) | Declarative LM modules with typed signatures in ordinary control flow. | Signature, module graph, demonstrations, and compiled parameters. | Online execution plus offline or development-time optimization. | User metric and structured parsing guide compilation. | Application-controlled tools and state. | Compilers bootstrap demonstrations and optimize programs. | Compiled program, LM, metric, and demonstrations jointly matter. | Demonstrates concise declarative programs and automatic optimization. | It intentionally compiles/optimizes, so it is not pure specification-as-runtime. | Treat compilation as an optional realization/materialization backend, not the canonical contract. |
| PLSEMANTICSBENCH | [paper](https://arxiv.org/abs/2510.03415), [official repository](https://github.com/EngineeringSoftware/PLSemanticsBench) | Models predict final state, rules, and traces from supplied operational semantics. | Formal semantics plus program. | Evaluation. | Exact benchmark answers under standard and mutated semantics. | No production effect-commit system. | Not a reuse system. | Model choice and supplied semantics affect results. | Shows promise on coarse execution tasks. | Performance drops under deliberately altered semantics, so models may rely on familiar priors. | Hash interpreter semantics and regression-test changed profiles. Never trust a model as an exact CPU. |
| ToolGate | [paper](https://arxiv.org/abs/2601.04688) | Forward tool execution under Hoare-style contracts. | Tool contract and explicit symbolic state. | Online. | Preconditions gate calls and postconditions gate state updates. | Typed trusted state changes only after verified execution. | Not primarily a tool-library construction system. | Contract and verifier changes alter guarantees. | Directly targets verifiable state evolution. | Its state model is not the Loop Engine catalog and Run History model. | Use candidate, verification, effect authorization, and compare-and-swap commit as distinct transitions. |

## Research conclusion

The sources support the compounding thesis, but they also show why one model
opinion is not sufficient. The implemented path combines an accepted source
result, a structured assessment, exact artifact identity, deduplication,
independent qualification, explicit promotion, and result verification.

The research does not prove that every generated implementation should become
reusable. It supports measuring when the construction cost is recovered and
when the system can detect a wrong result before trusting it.

The semantic research also does not prove that a model can serve as a stable
CPU. The repository therefore uses one coherent model transaction, strict
typed output, independent verification, explicit abstention, exact ProgramID
components, and state commit only after authorization. A conventional
implementation may be absent. Evidence and contracts may not be absent.

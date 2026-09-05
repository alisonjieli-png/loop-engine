# Loop Engine guidance audit

Read-only review of the dirty `/home/username/loop-engine` worktree on `main`, initially observed at `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`. No repository files were edited, embedded historical instructions executed, external sources consulted, or behavioral/provider qualification runs performed. Files may include uncommitted concurrent work; this report is not a frozen-build receipt.

## Prompt and reference findings

All 25 Markdown files in `docs/prompts/` and all four in `docs/reference/` were fully read: 29 files and 19,780 lines. The main unresolved issue is guidance drift: the new continuation brief resolves old contradictions, but currently routed component prompts and normative glossaries still repeat retired rules.

### Current guidance contradictions

| ID | Evidence | Finding and implication |
|---|---|---|
| G01 | `docs/prompts/UNIVERSAL-COMPONENT-IMPLEMENTATION-MANDATE.md:149`, `docs/prompts/ADVERSARIAL-COMPONENT-ARCHITECTURE-REVIEW.md:75`, `docs/prompts/CONTINUOUS-COMPONENT-CONFORMANCE.md:63` | All three require every semantic value exposure/transformation, including constants, formatting, JSON and paths, to become a logical Loop. This contradicts LE-NODE-008, which keeps low-level primitives inside an owning Loop unless independently governed. These are still routed component workflows, not merely archived files. |
| G02 | `docs/prompts/UNIVERSAL-COMPONENT-PROMPT-SUITE.md:31` | The suite index explicitly removes the strict primitive mandate because it conflicts with LE-NODE-008, while its implementation/review/conformance children retain the same rule. |
| G03 | `docs/architecture/GLOSSARY.md:13`, `docs/architecture/COMPONENT-GLOSSARY.md:39` | Both preserve the strict every-value/transformation Loop rule and native-operation ban. `GLOSSARY.md:3` also claims normative authority alongside the Constitution. The generated semantic dictionary instead permits typed stateless functions and reserves another Loop for independently governed work. |
| G04 | `docs/reference/PRODUCT-NOMENCLATURE.md:73`, `docs/reference/UNIVERSAL-LOOP-STANDARD.md:64` | Reference Practitioner is described as nine stages, with Standardize Task missing from the nomenclature list at line 78. Current reference profile has ten stages under a historical ID. The loop-object component README and implementation mandate correctly show ten. |
| G05 | `docs/reference/UNIVERSAL-LOOP-STANDARD.md:85`, `docs/architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md:301`, `docs/prompts/LOOP-ENGINE-ARCHITECTURE-VIDEO-BUILD-PROMPT.md:173` | Current reference/presentation guidance says only deterministic Solution leaves execute. Current authority permits hybrid and non-deterministic execution when a compatible executor and exact model authority are supplied; otherwise typed unavailable failure. |
| G06 | `docs/architecture/GLOSSARY.md:139` | Core Architecture is equated with shipped Core Code Intelligence. Current architecture defines three public capability groups and distinct internal mechanics. Reusable code can implement them, but the concepts are not interchangeable. |
| G07 | `src/loop_engine/loop/loop_doctrine.py:3`, `:52`, `:69` | Doctrine says everything is a PractitionerLoop, any code Loop has a model-fallback seam, and deterministic is always tried first. These universal statements conflict with separate roles, supported-mode/executor requirements, and the public LLM-led path that skips the deterministic attempt. Baseline machinery has active compatibility consumers at `recursive_loop.py:496`, `recursive_loop.py:718`, and `loop_handoff.py:100`; it should be scoped as preset/compatibility machinery. |
| G08 | `docs/architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md:256`, `:276` | `LoopRef`/`LoopCapsule` are still presented as current reference names. Generated semantic dictionary identifies `IntelligenceItemRef`/`IntelligenceItemPackage`, with the old names as compatibility aliases. |

### Historical contradictions that must not become implementation instructions

| ID | Evidence | Finding and current interpretation |
|---|---|---|
| H01 | `docs/prompts/LOOP-ENGINE-LOOPNODE-SPEC-MANDATE.md:149`, `:322`, `:801` | The same file defines active LoopNode runtime classes and later says LoopNode is an at-rest record. Preserve canonical Loop and exact legacy migration readers. |
| H02 | `docs/prompts/LOOP-ENGINE-LOOPNODE-SPEC-MANDATE.md:1471` | Maps both effort `power` and `llm_thinking_power` to `ModelPolicy.thinking_power`, incorrectly collapsing distinct settings. |
| H03 | `docs/prompts/LOOP-ENGINE-LOOPNODE-SPEC-MANDATE.md:1380` | Permits bounded cyclic graphs. Preserve recurrent intent through Loop iteration, later activations/state revisions, and bounded spawning; do not introduce cycles into the reusable DAG authority. |
| H04 | `docs/prompts/LOOP-ENGINE-ADVERSARIAL-INTELLIGENCE-SEEKING-MANDATE.md:1586` | Proposes migrating old four-layer fields into multidimensional metadata. Functions, perspectives, provenance, and lifecycle supplement rather than replace the four persistent layers. |
| H05 | `docs/prompts/LOOP-ENGINE-PLANE-INTERACTION-MANDATE.md:61` | Introduces seven Core planes and a new shared configuration engine. These may describe internal concerns but cannot become seven public groups or parallel authority. Its lines 157-169 correctly say planes are not runtimes. |
| H06 | `docs/prompts/LOOP-ENGINE-UNIVERSAL-EVOLUTION-PROMPT.md:374` | Equates Core Architecture, Core Code Intelligence, and `intelligence/code/core`. This absorption proposal is retired; map useful invariants to current boundaries. |
| H07 | `docs/prompts/LOOP-ENGINE-CLEANUP-AND-INTELLIGENCE-ACCESS-PROMPT.md:232`, `:241`, `:765`, `:769` | Orders renaming core to itself, requires a tree containing core, and simultaneously requires no core string anywhere. Text is internally impossible. A past mechanical replacement is a plausible cause, not a verified historical fact. |
| H08 | `docs/prompts/LOOP-ENGINE-CLEANUP-AND-INTELLIGENCE-ACCESS-PROMPT.md:197` | Historical deletion list includes current canonical `loop/spawned_practitioner.py` wrapper. Its static import script also ignores relative imports without `node.module`; absence from this graph alone is insufficient deletion evidence. |

The prompt index explicitly demotes these historical sources at `docs/prompts/README.md:48`. Their embedded permission claims do not authorize present actions.

### Valuable surviving intent

- Independent builder/verifier authority and private contexts: `LOOP-ENGINE-DEVELOPMENT-ENGINEERING-ASSURANCE-PLANES-MANDATE.md:471` and `:476` require independent snapshot collection and context separation. The planes are applications on one engine, not new runtimes.
- Assurance is an application domain, not a fifth intelligence layer: `LOOP-ENGINE-DEVELOPMENT-ASSURANCE-INTELLIGENCE-MANDATE.md:71`. Its line 707 distinguishes finding definition, occurrence, and reviewed pattern.
- Audit the auditor: the engineering/assurance mandate at line 689 and assurance-plane mandate at line 401 require baseline/proposed rule review and self-exemption detection.
- Flexible procedures were longstanding intent: assurance-plane mandate at line 238 treats nine steps as replaceable; AGI food-for-thought at line 169 proposes a cycle grammar and asks for evidence before multiplying profiles.
- Mesh work needs typed state and transitions: `AGI-LOOPNODE-NETWORK-SELF-ORIENTING-FOOD-FOR-THOUGHT.md:240` validates transition proposals against state, graph, authority, and budget; line 387 asks for branch isolation and context per responsibility.
- Distribution is a separately provable claim: `LOOP-ENGINE-EVERYTHING-IS-A-LOOP-ADVERSARIAL-AUDIT.md:692` asks for addressing, messages, leases, crash recovery, partitions, and backpressure and warns against calling a single-process design a fabric.
- Learning needs demonstrated later use and controls: `GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md:224` says to test the second run; lines 164-177 reject whole-run success as stage credit; lines 319-323 explicitly say operational use and complete contribution are not established.
- One authority, several materializations: cleanup prompt lines 619-648 remain useful despite its broken rename recipe.
- The new continuation brief reconciles these most clearly: `LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md:124` defines the primitive boundary, line 247 separates memory meanings, line 366 defines maturity labels, and line 419 rejects mechanism-only fixtures as valid paired comparison evidence.

Per-stage small-model discussion at `GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md:271` is design guidance, not evidence that the public solver implements stage-level model allocation.

## Exact prompt/reference coverage

All listed files were fully read; no file in these two current directories was omitted or only sampled.

| Path | Lines | Coverage |
|---|---:|---|
| `docs/prompts/ADVERSARIAL-COMPONENT-ARCHITECTURE-REVIEW.md` | 215 | full |
| `docs/prompts/AGI-LOOPNODE-NETWORK-SELF-ORIENTING-FOOD-FOR-THOUGHT.md` | 528 | full |
| `docs/prompts/COMPONENT-IDEATION-AND-CONFORMITY.md` | 191 | full |
| `docs/prompts/CONTINUOUS-COMPONENT-CONFORMANCE.md` | 80 | full |
| `docs/prompts/GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md` | 323 | full |
| `docs/prompts/LOOP-ENGINE-ADVERSARIAL-INTELLIGENCE-SEEKING-MANDATE.md` | 1985 | full |
| `docs/prompts/LOOP-ENGINE-ARCHITECTURE-VIDEO-BUILD-PROMPT.md` | 352 | full |
| `docs/prompts/LOOP-ENGINE-CLEANUP-AND-INTELLIGENCE-ACCESS-PROMPT.md` | 795 | full |
| `docs/prompts/LOOP-ENGINE-DEVELOPMENT-ASSURANCE-INTELLIGENCE-MANDATE.md` | 1239 | full |
| `docs/prompts/LOOP-ENGINE-DEVELOPMENT-ASSURANCE-PLANE-MANDATE.md` | 805 | full |
| `docs/prompts/LOOP-ENGINE-DEVELOPMENT-ENGINEERING-ASSURANCE-PLANES-MANDATE.md` | 900 | full |
| `docs/prompts/LOOP-ENGINE-EVERYTHING-IS-A-LOOP-ADVERSARIAL-AUDIT.md` | 1132 | full |
| `docs/prompts/LOOP-ENGINE-FOUNDRY-AND-CAMPAIGN-MANDATE.md` | 486 | full |
| `docs/prompts/LOOP-ENGINE-GOVERNING-DEVELOPMENT-PROMPT.md` | 503 | full |
| `docs/prompts/LOOP-ENGINE-LOOPNODE-SPEC-MANDATE.md` | 1869 | full |
| `docs/prompts/LOOP-ENGINE-PARALLEL-EXECUTION-MANDATE.md` | 553 | full |
| `docs/prompts/LOOP-ENGINE-PLANE-INTERACTION-MANDATE.md` | 1405 | full |
| `docs/prompts/LOOP-ENGINE-SELF-ORIENTING-CODE-INTELLIGENCE-MASTER-PROMPT.md` | 783 | full |
| `docs/prompts/LOOP-ENGINE-UNIVERSAL-EVOLUTION-PROMPT.md` | 3851 | full |
| `docs/prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md` | 472 | full |
| `docs/prompts/OLLAMA-COMPONENT-QUALIFICATION-LAB.md` | 350 | full |
| `docs/prompts/README.md` | 84 | full |
| `docs/prompts/STRICT-EVERYTHING-IS-A-LOOP-PRIMITIVES.md` | 103 | full |
| `docs/prompts/UNIVERSAL-COMPONENT-IMPLEMENTATION-MANDATE.md` | 319 | full |
| `docs/prompts/UNIVERSAL-COMPONENT-PROMPT-SUITE.md` | 33 | full |
| `docs/reference/INTELLIGENCE-RETRIEVAL-PLAN.md` | 108 | full |
| `docs/reference/MASTER-SPECIFICATION.md` | 18 | full |
| `docs/reference/PRODUCT-NOMENCLATURE.md` | 134 | full |
| `docs/reference/UNIVERSAL-LOOP-STANDARD.md` | 164 | full |

Additional files fully read: `docs/architecture/GLOSSARY.md` (227 lines), `docs/architecture/COMPONENT-GLOSSARY.md` (63), `docs/architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md` (306), `docs/architecture/SEMANTIC-IDENTITY-DICTIONARY.md` (149), and `src/loop_engine/loop/loop_doctrine.py` (279).

Sampled or automatically scanned, not claimed fully read: `docs/architecture/GUIDANCE-RECONCILIATION-REGISTER.yaml`, `architecture.yaml`, `terminology.yaml`, root `README.md`, `adaptive_practitioner.py`, `adaptive_practitioner_records.py`, `recursive_loop.py`, `loop_handoff.py`, `delegation_runtime.py`, `reactive_worker.py`, `solution_graph.py`, and `solution_graph_validation.py`.

## Component review extension

All 27 current Markdown documents under `docs/components/` and `src/loop_engine/core/README.md` were fully read: 28 files, 4,703 lines. The component index, loop-object README, and Practitioner README had already been read during the initial source audit; their full reading is included in this coverage. No tests, provider calls, or repository edits were performed for this extension.

### Residual component drift

| ID | Evidence | Finding and implication |
|---|---|---|
| C01 | `docs/components/intelligence-layers/INTELLIGENCE-PORTFOLIOS.md:36`, `:43`, `:59` | The example calls `select_intelligence_portfolio()` without selected refs, and prose says selection deterministically rotates by consuming Loop identity. Current `src/loop_engine/core/intelligence_portfolio.py:679` validates explicit model selection; lines 685-687 raise when `request.selected_refs` is absent. The example is inconsistent with the current function contract, and the claimed decision owner is wrong. Source inspection establishes the mismatch; the example was not executed. |
| C02 | `docs/components/solution-canvas/README.md:92` versus `docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md:119` | The Solution component says hybrid and non-deterministic execution adapters are unimplemented and always refused. The profile component correctly says all three modes are supported when a gateway-backed executor and exact model-call authority are supplied. This is a direct contradiction between current component guides, also matching G05. |
| C03 | `src/loop_engine/core/README.md:3` versus `docs/components/core-architecture/README.md:3` | The source package README equates Core Architecture with shipped Core Code Intelligence. The component README defines three capability groups and separately identifies internal mechanics at line 66. The distinction should be preserved even where shipped code implements those capabilities. |
| C04 | `docs/components/intelligence-layers/README.md:134` and `:119` | Heading says "Search results are loops," while the documented result is a body-free reference. Stored records and returned references are passive; search, selected materialization, invocation and interpretation are Loop operations. The heading blurs the distinction the body otherwise explains. This is terminology drift, not evidence of a second runtime. |
| C05 | `docs/components/intelligence-layers/INTELLIGENCE-AS-LOOPS.md:4`, `docs/components/core-architecture/SEARCH-AND-STORAGE.md:16`, and examples across the intelligence component | Public prose and examples continue presenting `LoopRef`/`LoopCapsule` as canonical names, although the generated semantic dictionary identifies `IntelligenceItemRef`/`IntelligenceItemPackage` and marks old spellings as compatibility aliases. Existing alias-based calls need not fail; documentation should identify the compatibility status. |
| C06 | `docs/components/intelligence-layers/CONTEXT-HIERARCHY.md:57` and `src/loop_engine/core/context_ontology.py:229` | The guide openly normalizes lifecycle `core` to `registered`. The current general normalization table also maps `committed` to `registered`. This mixes source/provenance or commit status with lifecycle. The documentation agrees with code, so this is an architectural compatibility concern rather than stale prose. It needs an exact legacy-reader scope and downstream admission review; this audit does not prove a full activation or permission bypass. |
| C07 | `docs/components/intelligence-layers/USER-FEEDBACK-INTELLIGENCE.md:362` and `src/loop_engine/loop/loop_capsule.py:407` | Example asserts aggregate `workflow_mode="hybrid"` for retrieval plus model reframing; source returns it. This can imply a workflow-wide execution mode despite the per-Loop mode rule. It is a descriptive-result ambiguity, not evidence that a Canvas mode controls execution. Prefer explicit access/reframe Loop modes in a future versioned result change. |

### Current limitations correctly documented, not defects inferred from file presence

- **Public reuse requires deployment wiring.** `REUSABLE-CAPABILITY-FLYWHEEL.md:144` says the optional `ReuseObservationPort` must be configured with approved stores and a reactive series. A base installation does not create that persistent infrastructure. Lines 190-197 scope the verified slice to pure Python, SQLite persistence/reactivity and an injected model transport; they explicitly exclude remote-worker, production-sandbox, and live-provider evidence.
- **The third intelligence layer is only partly integrated.** `RUNTIME-HISTORY-AND-SOLUTION-INTELLIGENCE.md:338` says `SolutionLibrary` assets are not joined to `build_intelligence_catalog()`, history search currently emits run summaries, general retrieval does not reject `chain_intact=False`, and other typed resolution origins still need adapters. The broad existence of four layers must not be described as complete reuse of every record kind.
- **Self-improvement is not automatically continuous.** `self-improvement/README.md:30` describes a bounded scan and in-memory candidate staging; lines 57-59 say the function neither schedules itself nor writes candidate files. Separate Foundry staging has its own candidate-output path at line 121. These are distinct entry paths, not contradictory persistence claims.
- **User feedback is not an authority service.** `USER-FEEDBACK-INTELLIGENCE.md:391` explicitly notes unauthenticated author strings, no built-in multiwriter locking or tenant service, caller-supplied policy, a structural conflict detector, timing that does not schedule work, and response history not joined into search cards. Acting on guidance still needs real authorization.
- **Skill state is passive research work.** `MCP-AND-SKILLS.md:270` describes an offline state-context candidate. Lines 278-282 explicitly say it is not connected to the product prompt renderer and does not resolve Run History, update state, execute tools, or grant authority. This must stay distinct from the separate public stage-assistance fixture.
- **Semantic runtime evidence is fixture-scoped.** `loop-object/SEMANTIC-RUNTIME.md:205` states injected offline transports, four routing cases, no production reliability bound, and unproven live quality, distributed compare-and-swap and external effects. Lines 96-97 correctly limit deterministic-first to the local resolver policy.
- **External harness packages are not proven live integrations.** `EXTERNAL-HARNESS-ADAPTERS.md:33` and lines 77-79 distinguish typed/injected protocol checks from installed SDK execution and live task quality. The dated saved ABI evidence should not be treated as an automatically current environment census.
- **Local and remote workspace limits are clear.** `WORKSPACE-BACKENDS.md:138` says local command execution is not an OS sandbox; lines 176-185 say E2B and Modal declarations need real executing adapters. Docker evidence at line 167 links a specific saved local check.
- **Trace export evidence is local SDK integration.** `OPENTELEMETRY.md:82` proves real SDK projection and parent links with an in-memory exporter, not connection to an external collector. Run History remains authority; raw ledger input is explicitly unverified.
- **MCP discovery distinguishes tool effects from connection effects.** `MCP-AND-SKILLS.md:3` and lines 29-33 require explicit policy for stdio process spawning and remote connections even though discovery never invokes a tool. The phrase "effect-free discovery" elsewhere should be read as passive local capability discovery, not an exemption for transport setup.
- **Code templates describe boundaries, not general software safety.** `CODE-INTELLIGENCE-TEMPLATES.md:201` requires separate admission, exact digest, effects, dependency/license review, sandbox and result checks. Body locator support or a template record alone does not demonstrate production materialization of every advertised source kind.

### Exact component coverage

| Path | Lines | Coverage |
|---|---:|---|
| `docs/components/README.md` | 61 | full |
| `docs/components/core-architecture/BRAVE-SEARCH-PLUGIN.md` | 130 | full |
| `docs/components/core-architecture/CONTEXT-ARTIFACTS.md` | 92 | full |
| `docs/components/core-architecture/EFFECT-APPROVALS.md` | 147 | full |
| `docs/components/core-architecture/EXTERNAL-HARNESS-ADAPTERS.md` | 101 | full |
| `docs/components/core-architecture/MCP-AND-SKILLS.md` | 294 | full |
| `docs/components/core-architecture/MODEL-GATEWAY.md` | 234 | full |
| `docs/components/core-architecture/MODEL-RESPONSE-ADMISSION.md` | 68 | full |
| `docs/components/core-architecture/OPENTELEMETRY.md` | 87 | full |
| `docs/components/core-architecture/README.md` | 97 | full |
| `docs/components/core-architecture/SEARCH-AND-STORAGE.md` | 122 | full |
| `docs/components/core-architecture/WORKSPACE-BACKENDS.md` | 192 | full |
| `docs/components/intelligence-layers/CODE-INTELLIGENCE-TEMPLATES.md` | 210 | full |
| `docs/components/intelligence-layers/CONTEXT-HIERARCHY.md` | 290 | full |
| `docs/components/intelligence-layers/EXTERNAL-HARNESS-IMPORTS.md` | 89 | full |
| `docs/components/intelligence-layers/INTELLIGENCE-AS-LOOPS.md` | 144 | full |
| `docs/components/intelligence-layers/INTELLIGENCE-PORTFOLIOS.md` | 101 | full |
| `docs/components/intelligence-layers/README.md` | 157 | full |
| `docs/components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md` | 201 | full |
| `docs/components/intelligence-layers/RUNTIME-HISTORY-AND-SOLUTION-INTELLIGENCE.md` | 360 | full |
| `docs/components/intelligence-layers/USER-FEEDBACK-INTELLIGENCE.md` | 412 | full |
| `docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md` | 271 | full |
| `docs/components/loop-object/README.md` | 225 | full |
| `docs/components/loop-object/SEMANTIC-RUNTIME.md` | 218 | full |
| `docs/components/practitioner/README.md` | 138 | full |
| `docs/components/self-improvement/README.md` | 128 | full |
| `docs/components/solution-canvas/README.md` | 112 | full |
| `src/loop_engine/core/README.md` | 22 | full |

Additional source sampled for these findings, not claimed fully read: `core/intelligence_portfolio.py`, `core/context_ontology.py`, `core/facets.py`, `core/model_gateway.py`, `core/reasoning_call.py`, `code_nodes/solution_model_port.py`, and `loop/loop_capsule.py`. No external API documentation linked from component pages was fetched. A failed search against nonexistent `core/providers.py` and `core/prompt_assembly.py` was followed by inspection of the actual `model_gateway.py` and `reasoning_call.py` definitions; no absence claim relies on those guessed paths.

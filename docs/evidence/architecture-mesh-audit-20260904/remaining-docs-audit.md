# Remaining documentation audit

All 111 assigned Markdown files were read in full, totaling 17,958 source lines. Every current SHA-256 matches the root audit's /tmp/loop-engine-architecture-audit.UBvdFH/files.jsonl baseline. The files were captured individually, checked for truncation, then read through consecutive complete text chunks. No embedded document instructions were executed. The checkout was not edited. Source HEAD remained 22ee44052b027ba96ce50c37e4cc6a659e1b91c8 with 107 dirty status entries.

This allocation excludes docs/prompts, docs/reference, docs/components, and the four previously allocated glossaries (GLOSSARY, COMPONENT-GLOSSARY, TAXONOMY-ONTOLOGY-AND-CLASS-MAP, SEMANTIC-IDENTITY-DICTIONARY). All other current docs/**/*.md files, including untracked Sep-4 research and verification, are included.

Machine coverage: /tmp/loop-engine-markdown-coverage-history.json. This full-text documentation review is separate from the commit-history inventory. It does not imply full semantic review of every historical commit diff, reexecution of historical tests, or fresh external verification of every cited paper/provider.

## Main assessment

The recent Sep-4 research and evidence notes largely separate proposals, offline mechanisms, live probes, valid comparisons, and unproven benefit. The largest documentary drift is concentrated in older pages still presented as current architecture or operating guidance. Readers can encounter incompatible descriptions of the same implemented component without any source change.

## Confirmed current-document drift

| Document and lines | Finding | Current evidence |
|---|---|---|
| docs/architecture/CURRENT-ARCHITECTURE-MAP.md:426-462 | Advertises five memory types, including social, and a one-to-one layer-to-memory mapping. The page calls itself the current implemented/generated map at lines 3-8. | memory/model/memory_type.py:14 defines working, episodic, semantic, procedural; core/intelligence_layers.py:55-56 imports those definitions. There is no current LAYER_MEMORY_TYPE constant. The map is stale. |
| docs/contracts/README.md:103; docs/architecture/ARCHITECTURE-VISUAL-GUIDANCE.md:103-105 | Both say the in-process Solution runner is deterministic-only and semantic leaves fail preflight. The contract index was modified in the current worktree yet retains this old row. | code_nodes/solution_model_port.py:26 declares hybrid and non_deterministic leaf modes; solution_canvas.py:416-424 supplies the model invocation port for these modes. Required executor and authority can still be absent, but the product is not categorically deterministic-only. |
| docs/architecture/CURRENT-ARCHITECTURE-MAP.md:362-364 | Lists a nine-step Practitioner kernel with no task-standardization or newer optional stages. | loop/kernel.py:73-90 currently lists 13 steps, with six required and seven optional. The stable reference_nine_step profile name is not a count of the current kernel procedure. |
| docs/architecture/DESIGN-LANGUAGE.md:73,85-88; docs/guides/settings.md:73 | Says effort selects bounded iteration/model-call limits; lists 17 templates, 15 registered. | recursive_loop.py:121-129 has no implicit iteration/model-call limit at any effort. Passive inspection counted 18 templates, 16 registered and 2 candidate. User-configured limits remain separate fields. |
| docs/architecture/DESIGN-LANGUAGE.md:104 | Says 'Mode is a permission' without the later distinction between allowed resolution and effect authority. | AGENTS and the Constitution explicitly separate mode from network, file, secret, model, spending, and external-effect authority. The sentence should use precise resolution-mode language. |
| docs/context/REFERENCE-SOURCES.md:24-27 | Names strings/core_seed_intelligence_v2.jsonl and strings/generated_candidates.jsonl as current active development context. | Both named paths are absent. The packaged seed corpus exists under intelligence/context/core/records/part-00000.jsonl. This can misdirect a new session to deleted authorities. |
| docs/architecture/PLUGIN-BUNDLE-DISTRIBUTION.md:35-37 | Says no Claude Code or Codex wrapper is packaged yet. | integrations/claude-code and integrations/codex contain thin plugin bundles and skills; docs/guides/plugins-and-integrations.md:20 expressly says those packages are maintained. Marketplace publication remains a separate unproven gate. |
| docs/STYLE.md:15-17,83-84; docs/architecture/ARCHITECTURE-VISUAL-GUIDANCE.md:10 | Require the main README to begin with a complete diagram and say CI renders that diagram. | README begins with the product quickstart; f9bd2bc removed the README diagram requirement. Current CI renders component-document diagrams. |
| docs/verification/COGNITIVE-ARCHITECTURE-AUDIT-2026-09-02.md:106-114,203-205 | Says there are 28 transitions, while stating 18 realized and 13 unrealized. | Current core.cognitive_grammar.TRANSITIONS has 31 entries, exactly 18 realized and 13 not_realized. This is internally inconsistent arithmetic, not new cognitive functionality. |
| docs/research/SKILL-STATE-EXECUTION-AND-CACHE-ECONOMICS.md:33-36 | Says patch validation means 'the model cannot corrupt the state'. | Its own lines 124-127 report state-overwrite errors, and the newer long-horizon review at lines 200-204 separates schema validity from safe updates. Structural admission cannot support the categorical semantic claim. |

The API parameter count needs explanation rather than an unsupported accusation of a wrong number. docs/architecture/API-DESIGN.md:32 states nine, and forbidden_paths.json:158 really uses a nine-parameter hard cap. The newer parameter_boundary.py:27 independently uses three, documented in THREE-PARAMETER-BOUNDARY-REPORT.md. Two actual checks coexist with different scope/migration maturity. A guide should identify the nine-parameter legacy gate and the stricter three-parameter development target instead of leaving readers to infer one universal limit.

## Architecture explanations that exceed their exact path

CURRENT-ARCHITECTURE-MAP.md:306-308 promises no parent goal, private history, sibling context, or shared ledger for every Spawned Loop. The precise SpawnedTaskManager guide scopes its isolation to its public request/runtime port and explicitly disclaims arbitrary-reflection sandboxing. The adaptive recursive branch currently passes _adaptive_impls(services) at adaptive_practitioner.py:505-507; it is a different path that reuses services. A universal isolation statement needs proof for both, or a scope restriction.

ARCHITECTURE-DIAGRAMS.md has useful implemented/partial/shadow/target labels, but several arrow labels are stronger than the element status: allocation 'orders the routes' at line 129 despite being shadow; verification 'closes or reopens' the frontier at 138 despite the frontier being a post-run projection; the Practitioner 'records every choice' at 168 despite partial decision instrumentation; and choice 'may negotiate the shape with' templates at 171 despite explicitly unwired template negotiation. These are explanatory relationships, not proof that a realized call path exists. The dynamic diagram separately and correctly labels trusted adaptive state transition partial at line 200.

The Sep-4 stage-assistance report correctly says mechanism_only, same-Practitioner verification, unknown causal benefit, no canonical paired outcomes, no current SQLite rebuild from product histories, and six unresolved control dimensions. Its exact-lineage wording at lines 148-167 nevertheless needs the newly demonstrated evaluation-subject qualification: a real evaluation of B can currently grant credit to different old result A. See /tmp/loop-engine-lineage-subject-audit.md and its saved reproduction. The issue is not whether delayed verification is forbidden; it is missing exact subject binding between the evaluation and the action/result being credited.

## Historical reports and supersession

Several old reports are valuable as history but should not be used as live work queues:

- ARCHITECTURE-CONFLICT-REGISTER.md still introduces itself as current and carries Aug-27 CI-red, pending model-led Solution execution, pending graph reload, and pending learning fields. Later rows in CODEX-5.6-MAX-EXECUTION-LEDGER.md record successful commits and CI. The first half of that ledger likewise retains obsolete 'current exact blocker' language before its later successful updates. Interpret the records chronologically.
- LIVE-KAGGLE-DIAGNOSTIC-2026-09-02.md:3 says current tree and supersedes earlier audits, but lines 192-194 still call workspace read-back absent. d5519a4 added core.workspace.read, and the subsequent cognitive audit explains the completed fix. Its section 5.2 also says 'failed for one reason' at 146 before explicitly admitting at 190-191 that it is not established as the only reason. The latter is the defensible attribution.
- BENCHMARK-AND-RETRIEVAL-REPORT.md records a then-absent NgramSpaceDefinition and frozen retrieval judgments. Those contracts and benchmark files were subsequently added. This does not invalidate its precise old observation; it makes it a dated baseline.
- ONBOARDING-CLI-USABILITY-REPORT.md:91-93 says the base package still installs all data/model dependencies. Later package work split optional adapters, and current README/clean-wheel evidence distinguishes the lightweight base. Preserve the old proof, do not copy its current-limit paragraph into onboarding.
- The Aug-27 research-to-Intelligence, Solution Factory, Kaggle RSI, alignment, parameter-boundary, and release reports identify larger incomplete checkpoints. Later web fetch, adaptive execution, local artifact, and stage-mechanism work closes some subparts. Nothing in the reviewed reports proves those entire broad checkpoints now complete.

The older EVERYTHING-IS-A-LOOP and CODE-REVIEW reports have useful point-in-time banners. Several older reports without banners are equally historical. Their passing counts describe the exact sampled checks at their revision, not a durable guarantee. The history shows errors surviving green suites and later finding-specific fixes.

## What the evidence legitimately establishes

- The Aug-27 core completion report labels its role/mode, graph, and learning proof offline and fixture-backed. Its heading is broader than its content, but its scope is explicit. It does not claim live provider quality or full product completion.
- The learning-cycle report demonstrates a narrow governed normalization fixture with one no-memory control, scope refusal, promotion, rollback, and read-back. It disclaims production effectiveness and universal applicability.
- The flywheel evaluation separates an injected cold-to-warm mechanism from a later real Ollama interval-normalization run with independently checked local cases and explicit resolver wiring. It expressly says automatic public CLI harvesting/resolver discovery remain open.
- Twelve Kaggle tasks produced structurally valid outputs, but two probability tasks produced hard labels. Eleven runs were mixed infrastructure/semantic evidence and only one was comparison-eligible. The report does not establish an assistance, prompt, profile, or model superiority claim. Its final-success denominator must not erase the documented earlier failed/cancelled attempts and reruns.
- The 120-competition Sep-4 preflight is metadata access only: 117 nonempty lists, three empty, 49 potentially truncated, and 71 reused earlier results plus 49 corrected reads. The current hardened three-source canaries are distinct from that historical 120-member continuation. Zero sources in the qualification canary passed every gate. It is not a 100-task solve campaign.
- Astra readiness is hard-quarantined offline adapter/policy evidence, not a configured paid route or successful OpenAI invocation. A separate Ollama canary is explicitly labeled as such.
- The Sep-4 mesh, long-horizon, and procedural-memory papers are research syntheses, not installed policies. They identify unbound template cards, conditional sufficiency, source/holdout/evaluator requirements, future distillation, and unreproduced author-reported results. External citations were read as document content; this audit did not freshly verify their web sources.

## Exact full-text coverage

Each file below was fully read and retained the root audit's source hash. 'Current contract/guide' is a document role, not a claim that every sentence is correct. 'Historical verification' is evidence tied to its stated date/revision. The JSON coverage artifact holds every exact SHA-256.

| Path | Lines | Document role | Review |
|---|---:|---|---|
| docs/ARCHITECTURE-DIAGRAMS.md | 555 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/README.md | 143 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/REPOSITORY-ORGANIZATION.md | 42 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/STYLE.md | 88 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/TROUBLESHOOTING-LADDER.md | 176 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ADAPTIVE-WORK-APPROACH-ARCHITECTURE.md | 190 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ADDED-FILE-EXTENSIONS.md | 244 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ADR-REUSABLE-CAPABILITY-FLYWHEEL.md | 173 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ADR-SELF-ORIENTING-ABSTRACTION-GOVERNANCE.md | 125 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ADR-TRANSACTIONAL-SEMANTIC-RUNTIME.md | 184 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/AMBIGUITY-REGISTER.md | 38 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/API-DESIGN.md | 55 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ARCHITECTURE-CONFLICT-REGISTER.md | 302 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ARCHITECTURE-MAP.md | 18 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ARCHITECTURE-VISUAL-GUIDANCE.md | 136 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ARCHITECTURE.md | 53 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/ARCHITECTURE_CONFORMANCE.md | 66 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/COMPONENT-DATA-DICTIONARY.md | 145 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/COMPONENT-EXTENSION-AND-PARAMETERIZATION-RULES.md | 72 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/COMPONENT-INTERACTION-DICTIONARY.md | 142 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/CONSTITUTION.md | 237 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/CONTEXT-HANDOFF-ONTOLOGY.md | 92 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/CURRENT-ARCHITECTURE-MAP.md | 492 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/DATA-DICTIONARY.md | 15 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/DESIGN-GUIDANCE.md | 54 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/DESIGN-LANGUAGE.md | 204 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/EXECUTION-CONTEXT-FINGERPRINTS.md | 8 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/HCF-CONCEPT-FIT.md | 22 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/LIFECYCLE-EXTENSION-CONTRACT.md | 8 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md | 317 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/PLAN-EXECUTION-BOUNDARY.md | 22 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/PLUGIN-BUNDLE-DISTRIBUTION.md | 41 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/PROMPT-AND-INVOCATION-ENCAPSULATION.md | 98 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/REACTIVE-LOOP-ACTIVATION-AND-OUTPUT-SERVING.md | 214 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/RESOLVE-ONCE-PASS-EXACT.md | 9 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/REUSABLE-CAPABILITY-AUTHORITY-AND-RESEARCH.md | 102 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/SELF-HOSTING-BOUNDARY.md | 11 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/SEMANTIC-DECISION-RULES.md | 90 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/architecture/WORK-APPROACH-INSTRUMENTATION.md | 426 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/benchmarks/FIRST-LOOP-ENGINE-PORTFOLIO-SOURCE-REVIEW.md | 190 | Benchmark catalog/protocol | FULL_TEXT_READ |
| docs/benchmarks/README.md | 176 | Benchmark catalog/protocol | FULL_TEXT_READ |
| docs/context/CODEX-START-HERE.md | 147 | Session context/handoff | FULL_TEXT_READ |
| docs/context/GPT-6-ASTRA-READINESS-2026-09-04.md | 193 | Session context/handoff | FULL_TEXT_READ |
| docs/context/REFERENCE-SOURCES.md | 98 | Session context/handoff | FULL_TEXT_READ |
| docs/contracts/README.md | 110 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/getting-started.md | 107 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/campaigns.md | 122 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/complex-task-comparisons.md | 125 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/custom-endpoints.md | 122 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/how-it-works.md | 26 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/install-macos/README.md | 76 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/install-windows/README.md | 83 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/llm-first-universal-solver.md | 146 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/loops-and-modes.md | 133 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/model-routing-intelligence.md | 262 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/ngram-retrieval.md | 189 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/plugins-and-integrations.md | 37 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/provider-endpoint-landscape.md | 142 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/providers-and-keys.md | 310 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/quick-start.md | 69 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/reports.md | 137 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/settings.md | 158 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/spawned-loop-delegation.md | 363 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/studio-runtime-views.md | 98 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/guides/typed-loop-connections.md | 127 | Current contract/guide or architecture history | FULL_TEXT_READ |
| docs/implementation/CODEX-5.6-MAX-EXECUTION-LEDGER.md | 450 | Historical execution ledger | FULL_TEXT_READ |
| docs/internal/HANDOFF.md | 31 | Session context/handoff | FULL_TEXT_READ |
| docs/internal/README.md | 13 | Session context/handoff | FULL_TEXT_READ |
| docs/research/ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md | 766 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/CODING-HARNESS-ARCHITECTURE-COMPARISON.md | 226 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/GRAPHIFY-CODE-INTELLIGENCE-EVALUATION.md | 201 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/HCF-PATTERN-REVIEW.md | 59 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md | 984 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/MODEL-ROUTING-AND-GATEWAY-OPTIONS.md | 175 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md | 592 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/PUBLISHED-HARNESS-BENCHMARKS.md | 156 | Dated research/proposal | FULL_TEXT_READ |
| docs/research/SKILL-STATE-EXECUTION-AND-CACHE-ECONOMICS.md | 202 | Dated research/proposal | FULL_TEXT_READ |
| docs/templates/concept-page.md | 34 | Writing template | FULL_TEXT_READ |
| docs/templates/example-readme.md | 56 | Writing template | FULL_TEXT_READ |
| docs/verification/BENCHMARK-AND-RETRIEVAL-REPORT.md | 163 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/CLEAN-INSTALL-REPORT.md | 77 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/CODE-REVIEW-2026-09-02.md | 216 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/COGNITIVE-ARCHITECTURE-AUDIT-2026-09-02.md | 215 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/CORE-ENGINE-COMPLETION-REPORT.md | 24 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/EVERYTHING-IS-A-LOOP-AUDIT-2026-09-01.md | 208 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/FILE-BY-FILE-ALIGNMENT-REPORT.md | 34 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/GENERALIZATION-OPPORTUNITY-REPORT.md | 51 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md | 342 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/KAGGLE-RSI-REPORT.md | 117 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/KAGGLE-TWELVE-COMPETITION-CAMPAIGN-2026-09-03.md | 143 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/LEARNING-CYCLE-REPORT.md | 205 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/LIVE-KAGGLE-DIAGNOSTIC-2026-09-02.md | 224 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/LIVE-OLLAMA-TEXT-SCENARIO-REPORT.md | 90 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/MODEL-ASSISTED-TASK-COMPILE-REPORT.md | 91 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/MODEL-ROUTING-REPORT.md | 129 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/NOMENCLATURE-AND-ARCHITECTURE-REGRESSION-REPORT.md | 95 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/ONBOARDING-CLI-USABILITY-REPORT.md | 93 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md | 326 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/REACTIVE-LOOP-FOUNDATION-REPORT.md | 141 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/RELEASE-READINESS-REPORT.md | 12 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/RESEARCH-TO-INTELLIGENCE-REPORT.md | 113 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/REUSABLE-CAPABILITY-FLYWHEEL-EVALUATION.md | 201 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/REUSABLE-CAPABILITY-FLYWHEEL-IMPLEMENTATION-LEDGER.md | 133 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/REUSE-RESOLUTION-REPORT.md | 152 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/SELF-ORIENTING-ABSTRACTION-EVALUATION.md | 196 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/SELF-ORIENTING-ABSTRACTION-IMPLEMENTATION-LEDGER.md | 191 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/SEMANTIC-RUNTIME-EVALUATION.md | 168 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/SOLUTION-FACTORY-REPORT.md | 122 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/STAGE-ASSISTANCE-INTEGRATION-AUDIT-2026-09-04.md | 186 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/THREE-PARAMETER-BOUNDARY-REPORT.md | 172 | Historical/scoped verification | FULL_TEXT_READ |
| docs/verification/UNIVERSAL-COMPONENT-AND-STRICT-PRIMITIVE-REPORT.md | 228 | Historical/scoped verification | FULL_TEXT_READ |

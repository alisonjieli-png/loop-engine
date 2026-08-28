# Component glossary

This glossary explains the shared component model. The canonical term registry
remains [`terminology.yaml`](../../terminology.yaml). Component kinds are
registered in
[`component_ontology.yaml`](../../src/loop_engine/data/component_ontology.yaml).

| Term | Kind | Static or executable | Plain definition | Authority | Never means |
|---|---|---|---|---|---|
| `Loop` | runtime | executable | The sole concrete runtime and executable graph vertex. | Its exact definition, context, permissions, budget, and services. | A passive record, setting, question, or prompt block. |
| Loop component | ontology category | static or definition | A versioned, typed, digest-pinned semantic building block that participates in the shared component contract. | None unless an executable definition explicitly declares governed authority. | Another runtime. |
| `LoopComponentDefinition` | definition | static | The passive envelope for component identity, kind, payload contract, provenance, compatibility, scope, lifecycle, and refs. | None by itself. | A `LoopDefinition` or live `Loop`. |
| `LoopComponentRef` | reference | static | An exact component ID, version, digest, expected kind, scope, and compatibility requirement. | None. | The component body. |
| `LoopDefinition` | definition | static | The immutable description that permits one kind of Loop work. | Declared permissions and effects only when a Loop starts with it. | A catalog projection or runtime instance. |
| `LoopGraphDefinition` | definition | static | The sole reusable executable graph contract. Every vertex resolves to `Loop`. | Declared graph and vertex contracts. | A Solution Canvas or procedure draft. |
| `LoopValue` | result | static | A typed value with producer Loop, producer definition, source refs, digest, lineage, privacy, materialization, and verification state. | None. | A raw value crossing an architectural boundary. |
| `LoopValueRef` | reference | static | A body-free reference to one `LoopValue`. | None. | A cache entry or unverified value. |
| atomic primitive | operation definition | static definition, executable through `Loop` | A small registered semantic operation such as text combination or JSON serialization. | Only its declared pure input and output contract. | A runtime subclass or domain procedure. |
| intrinsic kernel | runtime substrate | native implementation | The finite audited Python operations that physically implement atomic deterministic Loops. | No task, provider, storage, policy, permission, routing, or domain authority. | A shortcut around Loop execution. |
| `LLMWorkPacket` | invocation contract | static | One provider-neutral, content-addressed packet for a bounded semantic model step. | None. | A prompt string, final task answer, or model runtime. |
| `WorkDirective` | procedure step | static | The one semantic responsibility, allowed action kinds, prohibited outputs, completion condition, failure condition, and return schema for a model call. | None. | Tool or permission authority. |
| `LLMContextBlock` | context block | static | One selected, versioned, digested context component with source, reason, position, cost, and content. | None. | An untracked prompt fragment. |
| `PromptAssemblyProfile` | profile | static | A data record that selects one registered provider-neutral block-layout policy. | None. | A prompt renderer or model route. |
| `PromptAssemblySnapshot` | snapshot | static | Exact evidence of selected block refs, order, digests, rejected blocks, estimated size, packet digest, and prompt digest. | None. | The raw prompt or a second source of task truth. |
| Practitioner stall signal | diagnostic record | static | Deterministic evidence that governed state or research is no longer making useful progress. | None. It activates diagnosis but cannot select a route. | A terminal decision. |
| failure diagnosis | semantic result | static | One bounded model proposal describing evidenced causes, failed strategy, missing context, and invalid assumptions. | None. | A repair action or permission. |
| recovery proposal | semantic result | static | One candidate changed strategy with an expected state change, capability requirements, risks, and follow-up budget. | None. | An executed repair. |
| recovery directive | decision record | static | The independently selected, runtime-validated proposal carried into the next Practitioner decision. | None until a later action is validated and executed. | A new runtime, direct tool call, or success claim. |
| qualification case | test definition | static | One versioned black-box component, interaction, state-transition, or classification proof obligation. | None. | Self-proving evidence about Loop Engine. |
| Context Intelligence | intelligence layer | static records, accessed through Loops | Questions, personas, guidance, principles, examples, failure patterns, and context profiles. | Reviewed record scope only. | One giant prompt or executable role. |
| capability | capability component | static definition, invoked through `Loop` | A registered operation with typed input, output, compatibility, permissions, effects, and verification. | Only after runtime authorization. | A provider, model, or runtime. |
| setting | settings component | static | One scoped, validated configuration value or cohesive settings record. | None by itself. | A policy override or permission grant. |
| policy | policy component | static | A hard constraint on permission, eligibility, effect, budget, or retention. | Its declared constraint. | A preference. |
| preference | preference component | static | A soft selection input. | None. | Permission or policy. |
| `SolutionCanvas` | builder and candidate | static | A candidate, comparison object, and portable projection that resolves to `LoopGraphDefinition`. | None. | An executor or graph authority. |
| `RunHistoryEvent` | event | static | One chronological fact produced by governed work. | None. | A result, report, memory record, or raw reasoning trace. |
| Run History | history | passive append-only evidence | The canonical chronological record for one run. | Persistence and replay under its policy. | Working Memory or active intelligence. |

## Strict operation rule

```text
semantic value is created or exposed
→ logical Loop

semantic value is transformed
→ logical Loop

compound work
→ graph of Loops

native Python operation
→ intrinsic kernel only
```

Logical atomic Loops default to deterministic mode. A physical executor may
later fuse compatible pure Loops, but Run History must retain every logical
identity, definition, input digest, output digest, failure location, fusion
decision, and cache decision.

A repeated-state detector follows the same static/executable distinction. It
creates a passive stall signal. Separate model-attempt Loops diagnose, propose,
challenge, and select a recovery. The normal Practitioner later validates and
executes the selected action.

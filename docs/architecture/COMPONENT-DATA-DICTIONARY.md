# Component data dictionary

This page describes the first implemented component contracts. Fields marked
as references carry identities, versions, and digests rather than hidden live
objects.

## LoopComponentDefinition

| Field | Type | Meaning |
|---|---|---|
| `identity` | `ObjectIdentity` | Component ID, semantic version, and definition digest. |
| `component_kind` | registered string | One kind from the component ontology. |
| `operationality` | enum | `static`, `executable_definition`, `capability`, or `adapter_binding`. |
| `payload_contract_ref` | contract ref | Schema or typed payload contract. |
| `payload_digest` | SHA-256 | Digest of the exact payload represented by the envelope. |
| `provenance` | string | Core, Learned, Plugin, or exact runtime source. |
| `role_affinities` | role IDs | Roles likely to use the component. This does not grant access. |
| `mode_support` | mode IDs | Modes compatible with operations on the component. |
| `input_contract_refs` | contract refs | Accepted inputs for executable definitions or capabilities. |
| `output_contract_refs` | contract refs | Produced outputs. |
| `settings_refs` | component refs | Exact settings dependencies. |
| `policy_refs` | component refs | Exact hard-policy dependencies. |
| `intelligence_refs` | component refs | Exact intelligence dependencies. |
| `capability_refs` | component refs | Exact capability dependencies. |
| `verification_refs` | component refs | Exact verification contracts or procedures. |
| `scope` | scope ID | Global, organization, workspace, project, user, or run scope. |
| `permissions` | permission IDs | Explicit authority. Must be empty for static components. |
| `effects` | effect IDs | Declared effects. Must be empty for static components. |
| `lifecycle` | lifecycle ID | Candidate, review, active, deprecated, rejected, or archived. |
| `compatibility` | requirements | Version and consumer compatibility. |
| `extension_points` | refs | Approved parameter, strategy, adapter, or plugin seams. |

## LoopValue

| Field | Type | Meaning |
|---|---|---|
| `value` | typed body | Materialized value. Omitted from body-free projections. |
| `value_contract_ref` | contract ref | Exact value schema and semantic type. |
| `semantic_role` | string | Why the value exists in the current operation. |
| `producer_loop_id` | Loop ID | Logical Loop that produced or exposed the value. |
| `producer_definition_ref` | definition ref | Atomic primitive or other producer definition. |
| `source_refs` | value or artifact refs | Exact inputs. |
| `content_digest` | SHA-256 | Digest of the canonical value. |
| `transformation_lineage` | primitive refs | Ordered semantic operations applied. |
| `privacy_class` | policy value | Persistence and rendering classification. |
| `materialization_state` | enum | Reference-only, materialized, or offloaded state. |
| `verification_state` | enum | Current contract-verification state. |

## AtomicPrimitiveDefinition

| Field | Type | Meaning |
|---|---|---|
| `primitive_id` | registered ID | Exact logical operation. |
| `input_contract_refs` | contract refs | Accepted LoopValue contracts. |
| `output_contract_ref` | contract ref | Returned LoopValue contract. |
| `intrinsic_id` | intrinsic ref | Exact finite native implementation. |
| `purity` | enum | Currently `pure` for the registered atomic family. |
| `idempotent` | boolean | Whether identical input may be replayed safely. |
| `cacheable` | boolean | Whether content-addressed acceleration is permitted. |
| `fusion_allowed` | boolean | Whether a physical executor may fuse the operation. |
| `default_mode` | mode | `deterministic`. |

## LLMWorkPacket

| Field | Type | Meaning |
|---|---|---|
| `packet_id` | component ID | Exact packet identity for one semantic step attempt. |
| `packet_version` | semantic version | Packet contract version. |
| `purpose` | string | Why a model is being called. |
| `phase` | procedure step ID | Orient, decide, verify, route, or another registered step. |
| `persona_context` | typed section | Primary and supporting personas with authority limits. |
| `task_context` | typed section | Original, normalized, horizon, state, input, output, unknown, and provenance data. |
| `loop_context` | typed section | Run and Loop IDs, relationship, role, profile, mode, checkpoint, authority, budget, and terminal contract. |
| `context_intelligence` | component projections | Selected guidance and evidence. |
| `question_portfolio` | component projection | Selected questions and output contract. |
| `capability_context` | snapshot | Capabilities actually available under current authority. |
| `attempt_history` | snapshot | Deterministic trace, failures, and bounded event projection. |
| `work_directive` | `WorkDirective` | One bounded semantic responsibility. |
| `output_contract` | contract projection | Required schema and no-extra-text rule. |
| `policy_context` | policy projection | Interaction mode and hard authority limits. |
| `token_budget` | accounting snapshot | Remaining calls and future token policy fields. |
| `source_refs` | refs | Original input sources. |
| `context_blocks` | `LLMContextBlock[]` | Versioned selected block components. |
| `content_digest` | SHA-256 | Digest of the complete packet without self-reference. |

## PromptAssemblySnapshot

| Field | Type | Meaning |
|---|---|---|
| `assembly_id` | component ID | Content-derived assembly identity. |
| `definition_ref` | profile ref | Selected prompt assembly profile. |
| `run_id`, `loop_id` | runtime IDs | Owning run and semantic Loop. |
| `ordered_block_refs` | block IDs | Exact provider-neutral order. |
| `rendered_block_digests` | SHA-256 list | Exact rendered block bodies. |
| `selected_blocks` | block IDs | Materialized blocks used. |
| `rejected_blocks` | block IDs | Available blocks omitted by policy. |
| `selection_reasons` | strings | Why each used block was selected. |
| `estimated_tokens` | integer | Pre-call byte-derived estimate. Actual provider usage remains separate. |
| `prompt_digest` | SHA-256 | Digest of the rendered prompt value. |
| `packet_digest` | SHA-256 | Exact source packet. |

## Static Context Intelligence components

`PractitionerPersona`, `PractitionerGuidance`,
`PractitionerStepQuestions`, `PromptAssemblyProfile`, and
`PractitionerContextPortfolio` each provide a passive
`LoopComponentDefinition`. Their payloads remain in installed YAML and their
selection runs through an Intelligence-role Loop.

## PractitionerStallSignal

| Field | Type | Meaning |
|---|---|---|
| `code` | registered ID | `RECOVERY_DIAGNOSIS_REQUIRED`. |
| `unchanged_snapshots` | integer | Consecutive snapshots with no governed state change. |
| `research_actions_since_intervention` | integer | Research actions since the last project or recovery panel. |
| `reasons` | strings | Exact deterministic activation reasons. |
| `progress_snapshot` | counts and digests | Unique evidence, project attempts, and artifact state. |

The signal has no route, capability, permission, or terminal authority.

## PractitionerRecoveryDirective

| Field | Type | Meaning |
|---|---|---|
| `recovery_round` | integer | Ordered panel activation in the current run. |
| `stall_signal` | signal | Exact activation evidence. |
| `diagnosis` | typed result | Root causes and evidence refs from the diagnosis call. |
| `proposals` | recovery proposals | Model-proposed, materially different candidate changes. |
| `selected_proposal_id` | proposal ID | Adjudicator selection. |
| `route` | route ID | Validated route carried into the next pass. |
| `reason` | string | Evidence-based selection reason. |
| `directive` | string | Instruction for later next-action selection. |
| `required_capabilities` | capability refs | Available capabilities required by the proposal. |
| `expected_progress` | string | State change that the next pass must demonstrate. |
| `confidence` | float | Advisory confidence from zero through one. |

The directive is passive. It does not execute the repair.

## QualificationCase

The independent lab stores a case ID, version, subject kind, goal,
preconditions, inputs, outputs, invariants, questions, positive and adversarial
cases, mutation cases, deterministic oracles, evidence requirements, budget,
and content digest. It never imports private Loop Engine implementation state.

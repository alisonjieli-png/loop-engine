# Product nomenclature

Status: current public naming guidance.

Use the terms on this page in the README, guides, examples, Studio, command
output, and diagrams. Internal code tokens may remain stable when renaming
them would break compatibility.

## Product and package names

| Surface | Name |
|---|---|
| Product and repository | Loop Engine |
| README title | Building with Loops |
| Python distribution | `loop-engine` |
| Command-line program | `loop-engine` |
| Python import | `loop_engine` |

## Main architecture terms

| Term | Meaning |
|---|---|
| Loop | The shared runtime object for one executable graph vertex. |
| Loop Practitioner | The role that builds and verifies a solution. |
| Practitioner Loop | One Loop instance acting in the builder role. |
| Practitioner Loop graph | The Loops and relationships used to build the work. |
| Solution Canvas | The declarative finished solution. |
| Solution Loop | One executable Loop represented in the Canvas. |
| Self-improvement Practitioner task | A task that reviews history and intelligence, seeds domains, and stages candidates. |
| Core Architecture | Intelligence Search and Retrieval, Web Research, and Custom Plugins. |
| Retrieval Engine | One search interface with lexical, vector, and hybrid modes. |
| Intelligence Library | One searchable view across the four persistent layers. |
| Runtime Memory | Temporary notes shared inside the current run. |
| Run History | Saved event history for reports and playback. |
| Loop Engine Studio | The local interface for live runs, playback, intelligence, and solutions. |

Use Loop Practitioner for the public role. The package API does not expose a
bare `Practitioner` class or another role-specific runtime alias. Internal
decision algorithms use service and algorithm names because they are Code
Intelligence, not runtime types.

## Three run modes

Always show the modes in this order.

| Mode | Meaning |
|---|---|
| Deterministic | Uses code, rules, calculation, and search. It does not call a language model. |
| Hybrid | Uses code first and may call a language model for one unresolved step. |
| Non-deterministic | A language model leads the step while the loop controls tools, limits, logging, and verification. |

A Loop profile may allow more than one mode. A Loop instance selects one mode
for its run. A spawning Loop cannot grant permissions that it does not have.

## Three settings that must not be confused

| Public term | Current code | Meaning |
|---|---|---|
| Role profile | `LoopProfileSpec` | Versioned purpose, required fields, capabilities, and mode support. |
| Step profile | `framework`, `custom_steps`, Loop Template | Number, order, and repetition of steps. |
| Effort setting | `power` | Bounded work limits. Public values are light, standard, deep, and max. |
| Operating settings | `OperatingProfile` | Permissions, access, providers, and optimization preferences. |

Use "step profile" only for the sequence a loop follows. Do not use "profile"
alone when the meaning could be effort or operating settings.

## Step profile labels

| Public label | Current built-in template | Steps |
|---|---|---:|
| Atomic code | `atomic_code_only` | 1 |
| Compact | `compact_five_beat` | 5 |
| Reference Practitioner | `reference_nine_step` | 9 |
| Custom | `custom_user_supplied` or a validated custom configuration | 1 to 200 |

The nine-step labels are:

1. Orient
2. Reconcile
3. Assess
4. Decide
5. Determine How
6. Act
7. Verify
8. Integrate
9. Route

Always state that this is a reference profile. A team can use different steps,
orders, repetitions, loop conditions, and exit conditions.

## Four intelligence layers

| Layer | Contents |
|---|---|
| Context Intelligence | Questions, methods, checklists, templates, personas, evaluations, context, instructions, and warnings. |
| Code Intelligence | Software for transformation, analysis, decisions, retrieval, execution, validation, reporting, and integration. |
| Runtime History and Solution Intelligence | Runs, solutions, decisions, failures, repairs, measurements, and comparisons. |
| User Feedback Intelligence | Advice, corrections, context, sources, package suggestions, priorities, constraints, instructions, approvals, and vetoes. |

Runtime Memory is not a fifth layer. It is temporary and belongs to the
current run.

The persistent layer keys are `context_intelligence`, `code_intelligence`,
`runtime_history_solution_intelligence`, and `user_feedback_intelligence`.
Use the public titles in headings and diagrams.

Candidate Context is excluded from normal retrieval. Use
`include_candidates=True` only on an explicit review path.

## Extensions and plugins

Use "built-in adapter" or "extension point" for current functionality.

Use "potential external plugin" only for future packaging around those
extension points. Do not say that Loop Engine ships plugin discovery, plugin
installation, or a plugin marketplace today.

## Plain-English replacements

| Avoid in public prose | Use instead |
|---|---|
| internal mode token `non_deterministic` | Non-deterministic |
| internal layer token `runtime_history_solution_intelligence` | Runtime History and Solution Intelligence |
| internal layer token `context_intelligence` | Context Intelligence |
| digest | exact version fingerprint, unless the technical detail matters |
| manifest | capability description, unless referring to the actual file format |
| admission | tested and approved for execution |
| candidate maturity | under review and not yet available to run |
| node as a second runtime type | Loop or Solution Loop |
| internal class name `LoopLedger` | event log or Run History, unless documenting the Python API |

Choose report, log, contract, event history, or run record according to the
actual object. Do not use a generic proof-sounding label when one of these
specific words is clearer.

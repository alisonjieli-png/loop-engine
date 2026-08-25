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
| Loop | The shared runtime object for one operational node. |
| Loop Practitioner | The role that builds and verifies a solution. |
| Practitioner loop | One Loop instance acting in the builder role. |
| Practitioner loop tree | The history of loops used to build the work. |
| Solution Canvas | The declarative finished solution. |
| Solution loop | One Loop instance represented by a node in the Canvas. |
| Self-Improvement Loop | One Loop instance that reviews history and intelligence, seeds domains, and stages candidates. |
| Static Architecture | Shared services used by Practitioner, Solution, and Self-Improvement loops. |
| Retrieval Engine | One search interface with lexical, vector, and hybrid modes. |
| Intelligence Library | One searchable view across the four persistent layers. |
| Runtime Memory | Temporary notes shared inside the current run. |
| Chronicle | Saved event history for reports and playback. |
| Loop Engine Studio | The local interface for live runs, playback, intelligence, and solutions. |

Use Loop Practitioner for the public role. Avoid the bare class name
`Practitioner` because that shorter name refers to a different internal class.
`PractitionerLoop` remains the public compatibility alias for `Loop`.

## Three run modes

Always show the modes in this order.

| Mode | Meaning |
|---|---|
| Deterministic | Uses code, rules, calculation, and search. It does not call a language model. |
| Hybrid | Uses code first and may call a language model for one unresolved step. |
| Non-deterministic | A language model leads the step while the loop controls tools, limits, logging, and verification. |

A loop may allow more than one mode. A loop that starts another loop cannot
grant permissions that it does not have.

## Three settings that must not be confused

| Public term | Current code | Meaning |
|---|---|---|
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
orders, repetitions, and stopping rules.

## Four intelligence layers

| Layer | Contents |
|---|---|
| Context Intelligence | Questions, methods, checklists, templates, personas, evaluations, context, instructions, and warnings. |
| Code Intelligence | Software for transformation, analysis, decisions, retrieval, execution, validation, reporting, and integration. |
| Previous Run & Solution Intelligence | Runs, solutions, decisions, failures, repairs, measurements, and comparisons. |
| User Intelligence | Advice, corrections, context, sources, package suggestions, priorities, constraints, instructions, approvals, and vetoes. |

Runtime Memory is not a fifth layer. It is temporary and belongs to the
current run.

The human-facing layer key is `context_intelligence`. The stable compatibility
token is `string_intelligence`. Do not expose the compatibility token in a
headline or diagram.

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
| internal layer token `past_run_intelligence` | Previous Run & Solution Intelligence |
| internal layer token `string_intelligence` | Context Intelligence |
| digest | exact version fingerprint, unless the technical detail matters |
| manifest | capability description, unless referring to the actual file format |
| admission | tested and approved for execution |
| candidate maturity | under review and not yet available to run |
| node as a second runtime type | loop node or Solution loop |

Choose report, log, contract, event history, or run record according to the
actual object. Do not use a generic proof-sounding label when one of these
specific words is clearer.

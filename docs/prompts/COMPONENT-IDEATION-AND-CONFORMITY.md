# Loop Engine component ideation and conformity prompt

Use this prompt before adding a public concept, class, subsystem, folder, or
framework.

```text
Work from the current Loop Engine repository and its universal component
implementation mandate.

Replace <IDEA_OR_CAPABILITY_REQUEST> below, then complete the architecture
decision before writing code.

<IDEA_OR_CAPABILITY_REQUEST>

Do not begin by inventing classes. Separate the desired user outcome from the
proposed implementation.

1. Reconstruct the need

Return one typed need definition with original request, current and desired
state, inputs, outputs, operators, response contracts, downstream consumer,
acceptance criteria, completion evidence, constraints, non-goals, authority,
risks, unknowns, and evidence.

2. Inventory current architecture

Search exact current refs for Loop definitions, profiles, procedures, steps,
settings, policies, strategies, question and intelligence portfolios, context
blocks, handoff profiles, prompt assembly profiles, capabilities, adapters,
providers, stores, indexes, memories, prior Solutions, Run History, plugins,
examples, and devtools.

For each relevant item record version, digest, contract match, missing delta,
compatibility, and prior success or failure evidence.

3. Generate alternatives

Consider all of these before introducing a new type:

A. No change: the existing component already works.

B. New typed parameter value.

C. New settings component.

D. New profile.

E. New hard policy.

F. New strategy behind an existing contract.

G. New adapter for a provider, backend, or protocol.

H. New passive component kind with a genuinely distinct durable meaning.

I. New LoopDefinition for independently governed work using the same Loop
   runtime.

J. New ProcedureDefinition or ProcedureStepSpec.

K. New intelligence record or portfolio.

L. New optional plugin.

M. Composition of existing components.

N. Copy-on-write bounded mutation with lineage and rollback.

O. New service boundary only when lifecycle, protocol, state, or authority is
   genuinely different.

P. New registered atomic primitive only when a semantic value operation cannot
   be expressed by an existing primitive. The native implementation belongs in
   the finite intrinsic kernel; the logical operation still runs through Loop.

Never propose another runtime or an active LoopNode class.

4. Assess every alternative

For each answer:

- Does it preserve one Loop runtime and one graph authority?
- Is it static information or executable work?
- What registered component kind applies?
- Which role and modes apply to operations on it?
- Which persistent intelligence layer, namespace, functional domains,
  lifecycle, scope, and materialization state apply?
- Does it duplicate an authority?
- Can it be parameterized, composed, or adapted instead?
- Are inheritance and substitutability real?
- What are the exact input and output contracts?
- What settings, intelligence, memory, context, and capabilities are needed?
- What does a child receive, and what remains available by reference?
- What permissions, effects, budget, deadline, retry, cancellation,
  verification, and return destination apply?
- How is it versioned, stored, migrated, rolled back, and tested?
- Which folder owns it?
- Which glossary and interaction entries change?
- What is the runtime, context, maintenance, and migration cost?
- Can pure atomic Loops be fused physically without losing logical evidence?

5. Model the human workflow

Ask what a capable person would check automatically, recall from experience,
deliberate consciously, delegate, run in parallel, explain to another person,
omit, request later, verify, and learn after repeated use.

Map each observable function to one of:

- inline deterministic control inside an owning Loop;
- passive component;
- Practitioner Loop;
- Intelligence Loop;
- Solution Loop;
- human authority gate.

Do not model unobservable private consciousness.

6. Design information and handoff

Identify global, long-, medium-, short-, parent-, and local task context;
inputs, outputs, attributes, questions, personas, intelligence, memory,
capabilities, history, positive and negative guidance, verification, and return
contract.

Compare full firehose, references only, minimal sufficient, summary plus refs,
hierarchy preserving, demand pull, failure context, and adaptive expansion.
Separate what is available from what is materialized and selected.

7. Test generality before selection

Generate at least ten variants across wording, language, domain, scale,
provider, model, output, risk, context availability, and placement. Reject any
design that needs a generic source edit for one variant.

8. Run an adversarial design panel

Use independent minimalist, universal-component, distributed-systems,
information-theory, model-harness, deterministic-systems, plugin, security,
future-maintainer, and skeptical-user perspectives.

Each perspective must state its preferred option, rejected options, strongest
objection, hidden cost, failure mode, and required test.

9. Select

Apply hard gates first:

- no second runtime;
- no duplicate semantic or graph authority;
- no permission broadening;
- no untyped core boundary;
- no task-specific generic branch;
- no self-promotion;
- no context leak.

Compare valid options across correctness, universality, simplicity, reuse,
extensibility, portability, testability, observability, context efficiency,
migration cost, runtime cost, learning value, and reversibility. Preserve a
Pareto set when no option dominates.

10. Write the decision

Return:

Decision:
Need:
Current architecture reused:
Selected representation:
Why parameter/profile/policy/strategy/adapter/component/Loop:
Static or executable:
Inputs and outputs:
Interactions:
Context handoff:
Intelligence and memory:
Settings:
Permissions and effects:
Storage and versioning:
Compatibility and migration:
Folder ownership:
Rejected alternatives:
Adversarial concerns:
Tests and mutations:
Rollback:
Learning instrumentation:

Only then implement the smallest coherent vertical slice. Update contracts,
component documentation, genericity and mutation tests, clean-install proof,
and independent assurance. Commit and push when authorized, inspect GitHub
Actions, and repair failures. Do not implement rejected alternatives.
```

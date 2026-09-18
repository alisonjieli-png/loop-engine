# Adaptable policies and lifecycle applicability

Status: design direction recorded on September 16, 2026, at the owner's
request. The owner asked for more flexible rules: the ability to adjust
rules when they are too tight, to solve problems under them, and to apply
different rules to development versus production runs. This document maps
the requested behavior to existing boundaries, records the smaller set of
genuine gaps, and restates earlier over-rigid formulations as conditional
defaults. It grants no authority and changes no invariant. Where a proposal
would revise an existing governing requirement, the authoritative contract
and its tests are revised first; changing this document alone implements
nothing.

## The principle

Be strict about what was authorized, what was promised, and what the
evidence establishes. Be flexible about the methods used to achieve them.
Development discovers better methods and better rules. Production adapts
through declared alternatives. Neither is trapped obeying an accidental
restriction the system has no way to question.

## What exists already, verified in source

- **A rule-challenge path with proportionate effort.** The independent
  failure review classifies a failed check as a correct failure, a wrong
  expectation, a check stricter than the task, an environment defect, or an
  ambiguous requirement, before any repair is forced. A disputed check is
  replaced only by a revised check that still rejects a known-wrong subject.
  This is the generalized "question the rule" mechanism; it already separates
  the rule's applicability, its implementation, and the work.
- **Scoped exceptions with recorded rationale and expiry semantics.** The
  module size cap has twenty-seven declared exceptions, each recording its
  authority and a split plan, and conformance fails an undeclared exception.
  When no exception applies, the original policy resumes; the system does not
  become ungoverned.
- **Shadow evaluation.** Stage assistance runs in shadow (changes no model
  input), advisory (supplies candidates), or fresh arms, so a candidate
  policy can be observed without controlling the live decision. The
  configuration search space runs offline proposal computation the same way.
- **Production adaptation ranges.** The supervision policy's escalation
  ladder (soft reset, cold restart, honest stop), budget phases, harness
  fallback alternatives under shared authority, and the provisioning decision
  after a typed insufficiency are all preauthorized adaptations within a
  declared range. A local limit ends that method's sequence, not the task.
- **Development versus release separation.** The offline self-test and
  conformance gates with zero tolerance govern the release boundary;
  exploratory work may be partial, and unfinished development never
  masquerades as a release because completion requires the full gates.
- **Policy identity bound into fingerprints.** Harness bindings are
  digest-pinned, the work packet records its render digest, and stage
  evidence separates configuration from occurrence identity, so a policy
  change never silently changes the meaning of an in-flight instance.
- **Rules removable, not only addable.** Retired terms, retired topology
  fields, and demoted mechanisms exist in the record; the documentation
  checks refuse retired vocabulary in public prose.

## Rule categories

Every rule that carries a "must" belongs to exactly one category, and its
category decides who can change it and how. The classification of the
repository's existing rules is the first action item below; the categories
are:

1. **Authority and evidence boundaries.** Access permissions, permitted
   spending, external effects, history preservation, verified success. A
   running instance cannot waive these for itself; additional authority
   comes from the owner or a delegated mechanism. A spending allocation can
   be increased by an authorized decision, never invented by an instance.
2. **Task commitments.** Required output, acceptance criteria, compatibility,
   user-pinned choices. The system may identify ambiguity and propose a
   change, but never silently substitute an easier task.
3. **Architectural decisions.** One runtime, record formats, component
   ownership, supported interfaces. Revised through explicit versioned
   development and migration, never improvised as incompatible behavior
   during a run.
4. **Working policies and heuristics.** Context size, decomposition, call
   strategy, search breadth, method ordering, retry approach. Adapt
   automatically within a declared range; propose a scoped exception outside
   it.
5. **Development and release conventions.** Style checks, module-size targets,
   documentation completeness. Applied at the appropriate boundary with
   declared exceptions, as the size exceptions already do.

"Hard for this running instance" never means "unchangeable forever." Even an
architectural decision is revisable by the owner through a versioned change.
What never happens is a running harness silently rewriting its own governing
assumptions.

## Lifecycle applicability

Lifecycle is a policy profile, separate from execution mode. A deterministic
operation can run in development or production; so can a model-led one.
The profile decides what incomplete work means, what checks run, and what
adaptation is preauthorized:

| Concern | Development | Qualification | Production |
|---|---|---|---|
| Incomplete work | Legitimate intermediate state | Explicit failure or limitation | Never presented as verified completion |
| Context | Broader diagnostic context to discover dependencies | The exact strategy under evaluation | Focused packet, recorded authorized expansion |
| Checks | Fast targeted checks guide edits | Applicable qualification gates | Task execution and acceptance checks |
| Policy change | Compare alternatives, including looser ones | Benefits and regressions both | Within approved adaptation ranges |
| Learning | Generate and revise methods | Assess transfer and applicability | Use qualified knowledge; promotion stays separate |
| Effects | Only those authorized for the environment | Controlled or explicitly authorized | Exact effect policy and reconciliation |

The boundary derives from the actual workspace, credentials, data
sensitivity, effects, and release status, never from a `development=true`
label. A process named development that holds production credentials and
writes a customer database is performing production-impacting actions.

## Enforcement levels

A rule advises, warns, or blocks. Advisory states the preferred choice;
warning records the deviation and its implications while continuing;
blocking refuses the operation until the obligation is met or an authorized
alternative is admitted. Experimental observation evaluates what a candidate
rule would have decided while the existing policy retains control, which the
shadow arm already does for stage assistance. The enforcement level must
respect the rule's category: security checks never become warnings because
they are inconvenient, and module-size and other conventions already carry
declared exceptions at the release boundary.

## The challenge path

The existing failure review is the model. Generalized beyond verifier
checks, a blocked operation first determines what actually went wrong: the
rule does not apply here; an input is missing; another permitted method
satisfies it; the implementation is stricter than its purpose; the requested
change alters the user's objective or authority; or several rules conflict.
A rule blocking work is evidence of a conflict, not proof the rule is wrong;
a rule's presence in a file is not proof it is well designed.

A proposed adjustment records compactly: which rule and version; what is
blocked, with evidence; the smallest proposed change; which obligation must
remain satisfied; who can authorize it; where and for how long; how its
result is evaluated. Three kinds of change stay distinct: a local exception
(a task, artifact, region, or period), a policy revision (the reusable
default), and a contract revision (what was promised). A successful local
exception never silently becomes permanent policy. Common adjustments do not
need repeated human approval: an owner preauthorizes an adaptation policy
and a deterministic controller admits changes within it, while model-led
work proposes and assesses candidates.

## Conditional defaults, replacing over-rigid formulations

The earlier atomic-profile rules become conditional defaults, aligned with
what the constitution already permits:

| Over-rigid | Conditional default |
|---|---|
| Every instance as small as possible | Prefer the smallest independently meaningful operation; permit a larger declared variant when splitting loses essential relationships. When two interpretations cannot be judged independently because their relationship is the task, keep the comparison together and give the larger variant its own definition and fingerprint. |
| Exactly the right context up front | Start with a justified packet; expand through recorded authorized provisioning when a missing dependency is found; learn better packets. |
| Exactly one model call per reasoning atom | One-call profile where it works; separately recorded repair, clarification, or alternative realization under the owning policy; never compound work hidden behind an atomic label. |
| Only qualified code executes | Operational reuse requires qualification; candidate code executes as a test subject through an authorized sandboxed executor so it can become qualified. |
| Every check passes before development continues | Check failures guide development; required acceptance and release gates pass before the corresponding acceptance or release. |
| A failed check means the artifact changes | First determine whether the artifact, input, check, environment, or interpretation is defective, as the failure review already does. |
| Never any task-specific material | Generalize mechanisms while allowing legitimate task-specific outputs, parameters, examples, and fixtures; never hidden benchmark-answer shortcuts. |
| The configuration never changes | Freeze each effective invocation; permit explicit transitions to a newly bound configuration at appropriate boundaries, each with its own fingerprint. |
| A local limit ends the task | A local limit ends that method's sequence; the owning Loop changes approach, obtains information, or returns the honest unresolved state within remaining authority, as the ladder and persistent solving already require. |

## Production-initiated development

When production meets an unsupported representation, the authorized path is:
production identifies the capability gap; authorized development constructs
a candidate adapter in a confined environment; an independent process
assesses the exact candidate; an admission decision makes it eligible;
production resumes on the admitted version. The candidate never enters the
live catalog merely because the task needs it. Task-scoped admission is a
possible narrow contract, but one-task use and persistent promotion remain
separate decisions.

## Evaluator improvement

The literal-phrase probe failures already documented the failure mode: a
check too strict about wording and too weak about meaning. The recorded
response was correct: replace the defective checking method while preserving
the requirement (criterion judgment with grounding now does this), with
review effort proportional to consequence. Change the means of establishing
correctness when necessary; never silently change correctness itself.

## Fingerprint compatibility

Every effective configuration is identifiable; configurations may change
across invocations. A local exception is part of the effective policy
identity. An evaluator revision binds to the evaluations it produces.
Historical results stay attached to the rules under which they were
obtained. A policy update never invisibly changes an in-flight instance,
which execution-bound digests already enforce.

## Progressive introduction

A policy revision moves by risk: sandbox comparison, shadow observation,
limited introduction on a bounded population with monitoring and recovery,
then broader use only on supporting evidence. Shadow evaluation never
duplicates side effects and needs its own data and computation authority.
Reverting a policy does not undo a committed effect; software rollback stays
distinct from effect reconciliation, which the constitution already requires.

Rules are judged by both failure kinds: whether they prevent genuinely
unacceptable behavior, and whether they block valid work unnecessarily;
whether review costs more than the problem warrants; whether a scoped
exception transfers; whether a revision preserved the obligation. A
permissive system can look productive by accepting defective work; a
restrictive one can look safe by accomplishing nothing. Both measurements
accompany every policy change.

## Keep the policy system smaller than the problem solver

The common path stays: the operation fits the policy, so execute it. Only
meaningful conflicts enter the challenge path. Shared policy records carry
rationale, authority, applicability, and permitted alternatives; each atomic
harness receives only its relevant instructions and bindings. Rules support
removal, consolidation, and demotion, not only addition. Repeated
exceptions indicate a poorly scoped default. A rule with no clear purpose or
useful evidence is reviewed, not preserved because it exists.

## First actions

1. **Classify the existing rules.** Walk the Constitution, the atomic
   profile, and the inter-step rules, assigning each to one of the five
   categories with its change authority. No behavior changes from
   classification alone.
2. **Declare lifecycle applicability.** State for each rule whether it
   governs development, qualification, release, production, or several, and
   what enforcement means at each point. The supervision policy and stage
   assistance arms are the existing surfaces that already carry parts of
   this; a lifecycle field would be a versioned extension of the same
   records.
3. **One common policy-challenge record.** The failure-review record shape
   generalizes to any blocked operation: rule version, blocking evidence,
   smallest proposed change, preserved obligation, authorizer, scope,
   evaluation. Reuse the existing Loop, configuration, evidence, and
   approval boundaries; create no parallel authority system.

These are three actions, not a new framework. Each maps to an existing
boundary, each has a discriminating test (a misclassified rule is refused by
its category's change authority; a lifecycle violation is refused by the
profile; a challenge record without a preserved obligation is refused), and
none changes what the constitution requires before it becomes binding.

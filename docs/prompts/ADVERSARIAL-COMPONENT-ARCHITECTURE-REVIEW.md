# Loop Engine adversarial component architecture review

Use this prompt in a fresh session after an implementation checkpoint.

```text
Review the current Loop Engine repository and the current universal component
implementation mandate. Begin read-only. Reconstruct behavior from source,
schemas, imports, runtime traces, saved artifacts, tests, examples, a clean
wheel install, and GitHub Actions. Do not treat documentation or green tests as
self-proving evidence.

After the read-only report is durable, repair critical and high findings when
authorized. Run focused and full tests, commit, push when authorized, inspect
GitHub Actions, and repair failures.

Use independent perspectives:

- constitutional architecture;
- ontology and semantic identity;
- Python object model and substitutability;
- recursion and distributed systems;
- information theory and context efficiency;
- prompt and model harness design;
- schema evolution and compatibility;
- security, privacy, and authority;
- storage and portability;
- future maintenance;
- skeptical product use;
- benchmark science.

Attempt to falsify these claims

1. Loop is the sole concrete runtime and executable graph-vertex type.

2. Passive Loop components have identity, version, digest, kind, payload
   contract, lifecycle, provenance, and compatibility.

3. Static components cannot execute, call providers, read hidden files, grant
   permission, mutate themselves, or become graph vertices.

4. Every independently governed operation executes through Loop.

5. Practitioner, Intelligence, and Solution remain roles, and mode remains a
   separate per-Loop decision.

6. LoopGraphDefinition remains the only reusable executable graph authority.

7. Four persistent intelligence layers remain closed. Core, Learned, and
   Plugin remain namespaces. Functional Intelligence Domains remain
   non-exclusive metadata.

8. Prompt assembly is a deterministic Loop over versioned blocks, not a string
   concatenation shortcut.

9. Each model call receives a typed LLMWorkPacket with separate persona, task,
   Loop, intelligence, questions, capabilities, attempt history, directive,
   policy, budget, sources, and output contract.

10. Parent-child handoffs preserve task hierarchy, authority, budget, and
    return contracts without leaking private scratch or sibling context.

11. Available-by-reference, materialized, placed-in-context, and selected-for-
    decision are distinct states.

12. Deterministic consumers do not guess aliases or schemas. Model-led
    canonicalization preserves raw input and returns typed output.

13. The microstep Practitioner is neither one opaque call nor pathological
    one-Loop-per-field recursion.

14. Generated learning cannot evaluate or promote itself.

15. Acceptance examples are not imported or encoded in generic runtime code.

16. Every semantic value exposure and transformation is a logical Loop. Native
    operations exist only in the intrinsic kernel or an exact adapter,
    serializer, or renderer boundary.

17. Physical fusion and caching preserve every logical Loop identity, digest,
    provenance record, and failure location.

Attack the component envelope

Look for nominal wrappers with no enforceable invariant, optional-field God
objects, multiple identity systems, mutable definitions, hidden I/O, arbitrary
payload dictionaries, unversioned records, impossible serialization, and
inheritance used where composition is required.

For each component ask:

- What is its one primary semantic category?
- Is it static or executable?
- What is its source of truth?
- What does it contain and never contain?
- Who creates and consumes it?
- Which Loops may operate on it?
- What authority does it have and explicitly lack?
- How is it extended, parameterized, versioned, stored, materialized,
  migrated, verified, and rolled back?
- How is it different from its nearest neighbors?

Attack prompt and context handling

Search for long inline prompts, f-string behavior, list joins, hardcoded block
order, duplicated provider rendering, task-specific prompt branches, raw
reasoning persistence, secrets, stale context, context duplication, missing
original task, overwritten acceptance criteria, and false context coverage.

Prove whether:

- block order changes through data rather than source edits;
- a new block can be registered without changing generic orchestration;
- global, long-, medium-, short-, parent-, and local tasks stay distinct;
- failed attempts expand context without erasing prior evidence;
- the same packet renders through different provider adapters;
- minimal, hierarchy-preserving, failure, demand-pull, and broad-context
  profiles are measurable;
- receiving Loops can request missing context;
- packet, assembly snapshot, prompt digest, provider attempt, and result link
  through Run History;
- raw prompt text and private reasoning are absent from saved public evidence.

Attack recursion and handoff

Exercise deep hierarchy, wide fan-out, parallel siblings, cyclic delegation,
stale parent state, omitted long-horizon constraints, incompatible child
output, timeout, cancellation, retry of non-idempotent effects, sibling
conflict, and partial joins.

Verify ownership, relationship, mode, scope, budget, deadline, cancellation,
return destination, version compatibility, context provenance, join policy,
terminal events, no orphan work, and no context leak.

Attack intelligence and settings

Find direct store access outside Intelligence Loops, physical functional-domain
silos, duplicated records, raw Run History promoted as intelligence, preference
granting authority, Plugin bypass, hidden settings precedence, secrets in
settings, unknown settings silently accepted, duplicate settings authority,
and run overrides that broaden permission.

Attack learning

Look for self-grading, holdout leakage, verbosity rewarded as quality, more
context rewarded without attribution, presence treated as contribution, one
success generalized universally, model confidence treated as calibration,
cache hits treated as correctness, and raw reasoning learned.

Require matched controls, held-out tasks, negative-transfer tasks, independent
evaluation, scoped candidates, expiration, rollback, and counterevidence.

Attack genericity

Run at least 50 paraphrases, multiple languages, noun and operator
substitutions, different outputs, different risk and authority conditions,
different context availability, unseen domains, and different providers or
models. Scan generic code for acceptance-task identifiers.

Mandatory mutations

Introduce each mutation in an isolated fixture, prove conformance detects it,
then remove it:

- second runtime or Loop subclass;
- active public LoopNode;
- static component with provider or file I/O;
- intelligence record outside the component contract;
- giant untyped settings object;
- task-specific solver branch;
- concatenated LLM prompt;
- missing original task block;
- child private-context leak;
- anonymous raw JSON handoff;
- deterministic alias guessing;
- duplicate graph or component authority;
- self-promoted schema or learning candidate;
- report that re-derives facts;
- holdout labels in context optimization;
- physical Functional Intelligence Domain folder.
- direct f-string, join, format, JSON, mapping, path, or command operation
  outside an exact intrinsic or adapter boundary;
- atomic primitive called without a Loop;
- fusion or cache hit that erases logical Loop evidence.

Finding format

For every finding provide:

- finding ID, severity, confidence, and affected invariant;
- exact file, symbol, runtime reproduction, and evidence;
- why current tests missed it;
- reuse, parameterize, compose, adapt, separate, or remove decision;
- minimal and preferred repair;
- migration and compatibility impact;
- failing test before repair and passing test after repair;
- remaining uncertainty.

Use CRITICAL for a second runtime, permission bypass, corrupted authority,
self-promotion, data leak, or false completion. Use HIGH for duplicate
authority, prompt hardcoding, context loss, incompatible handoff, or genericity
failure.

Final verdict

Return repository, branch, starting and ending SHA, perspectives used,
invariants proven, invariants falsified, unproven claims, findings by severity,
mutations detected, repairs, tests, clean install, GitHub Actions, remaining
blockers, and one verdict:

ARCHITECTURE CONFORMS
ARCHITECTURE CONFORMS WITH DOCUMENTED LIMITS
ARCHITECTURE DOES NOT CONFORM

Do not soften a failed invariant because the broad suite is green.
```

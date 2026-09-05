# Strict everything-is-a-Loop primitive mandate

Status: superseded design history. Do not use this file as a current
implementation mandate.

This prompt predates Architecture Constitution rule LE-NODE-008. The current
rule is narrower: independently governed work executes as a Loop. A low-level
value or transformation stays inside its owning Loop unless it needs an
independent goal, contract, authority, budget, retry, verification, scheduling
decision, cancellation behavior, or Run History identity.

The historical prompt follows for provenance.

```text
Read the current Loop Engine repository and universal component mandate before
editing.

Strengthen the architecture so every first-party semantically meaningful value
is produced or exposed by a logical Loop, every semantic transformation is a
Loop, and every compound workflow is a graph of Loops.

The concrete runtime remains Loop. Do not create LoopNode or a primitive
subclass per operation.

Implement one finite audited intrinsic kernel. Native Python string, mapping,
sequence, JSON, path, command, and schema operations may exist only there or in
an exact final adapter, serializer, or renderer boundary. The intrinsic kernel
must not import task, domain, provider, storage, permission, policy, routing,
or example logic.

Register parameterized atomic primitive definitions for at least:

text.constant
text.combine
text.normalize
text.utf8_size
number.ceil_divide
record.project
record.merge
sequence.order
json.serialize
json.deserialize
schema.validate
context.select
context.materialize
prompt.assemble
path.compose
command.compose

Each logical primitive defaults to deterministic mode and returns LoopValue or
LoopValueRef with value contract, semantic role, producer Loop, producer
definition, source refs, content digest, lineage, privacy class,
materialization state, and verification state.

Static strings, settings, questions, personas, guidance, policies, prompt
blocks, templates, intelligence, examples, counterexamples, and output
contracts cross architectural boundaries by component reference. A
deterministic constant or read Loop exposes their value.

Hybrid primitive repair is permitted only after a complete deterministic
attempt and typed failure exist. The model proposes a canonical repair, a
schema validator accepts or rejects it, the deterministic primitive reruns,
and another Loop verifies the output. Never call a model to combine known
strings.

Separate logical and physical execution. Compatible pure deterministic Loops
may be fused or cached physically only when no permission, effect, retry,
cancellation, checkpoint, verification, or return boundary is crossed. Fusion
and cache hits must preserve all logical Loop IDs, definition refs, input and
output digests, provenance, failure location, and Run History.

Add AST and call-graph checks for f-strings, string addition, join, format,
percent formatting, direct templates, JSON calls outside the canonical
serializer, mapping merges, path and command concatenation, prompt and context
concatenation, direct settings or intelligence reads, raw str/dict/list/bytes
or Path across component boundaries, and direct intrinsic calls.

Exceptions must be exact file and symbol entries. Never exempt a folder. Record
operation, reason, owner, test, introduced version, and removal version or
permanent justification.

Required tests include:

- string constants and combination run through deterministic Loops;
- f-strings and join are rejected outside exact boundaries;
- prompt assembly is a Loop graph;
- static intelligence and settings reads are Loops;
- LoopValue preserves provenance;
- raw str and dict cannot cross protected component boundaries;
- hybrid repair preserves the deterministic attempt;
- fusion and cache hits preserve logical histories;
- the intrinsic kernel has no forbidden imports;
- mutations introducing direct operations are detected;
- clean wheel and installed public CLI retain the same behavior.

Measure the current repository first. Enforce zero immediately in new strict
modules and the canonical task-build path. Produce an exact file/symbol/line
migration inventory for the remaining baseline. Refactor it in bounded batches
without broad allowlists or blind replacement.

Do not report strict migration complete while any unapproved native semantic
operation remains.
```

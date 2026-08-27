# Semantic decision rules

`terminology.yaml` is the machine-readable authority for these rules. This
document explains how to apply them when adding or changing Loop Engine code.

## Preserve typed contracts

A cohesive data or configuration class is an architectural asset. Keep it when
it carries a stable contract, invariant, injectable behavior, lifecycle, or an
independent semantic dimension. Consolidation must not replace typed objects
with generic dictionaries, long signatures, or strings.

```text
Different values, roles, modes, budgets, steps, or preferences
→ parameterize one typed definition or profile

Different algorithm behind one contract
→ compose a Strategy

Different backend, provider, protocol, or framework
→ compose an Adapter

Different persistent meaning or lifecycle
→ retain a distinct Record

Different service state, authority, or protocol
→ retain a distinct Service

Independently governed operational work
→ start another Loop instance

Stateless implementation detail
→ use a typed function
```

The sole runtime class is `Loop`. It is sealed. Practitioner, Intelligence,
Solution, Orient, Verify, Audit, Research, model use, storage choice, and task
domain are parameters or composed contracts, not runtime subclasses.

## Before introducing a class or module

Answer these questions in order:

1. Can an existing typed field represent the variation?
2. Does an existing ontology need one new validated value?
3. Can a Profile, Procedure, Policy, Portfolio, Strategy, or capability
   reference represent it?
4. Can composition behind an existing port represent it?
5. Is it a backend or protocol Adapter?
6. Does it have a genuinely different persisted meaning?
7. Does it have a genuinely different service lifecycle or authority?
8. Does the work need its own Loop identity, budget, cancellation, and Run
   History?

Only a remaining, evidenced distinction justifies a new class or stable source
boundary.

## Invocation boundary

A hand-written public or cross-module callable normally accepts no more than:

```python
def execute(request, context, services):
    ...
```

Each object must be cohesive and capability-scoped. A request is passive data.
It does not become a Loop merely because it has many fields. A services object
must not become a global service locator.

## Strings and serialized data

Strings are appropriate for human text, paths, URLs, external opaque IDs, and
the serialized projection of typed values. Code must parse a string into a
typed value before branching on it as a role, mode, relationship, lifecycle,
permission, effect, scope, event kind, provider purpose, or internal identity.

Persisted definitions use versioned references. They do not serialize Python
classes, lambdas, closures, bound methods, or live service objects.

## Compatibility

An old name may exist only in an exact reader or migration. It cannot own
runtime, graph, storage, promotion, or settings authority. The historical
serialized `kind: loop_node` value maps to `LoopDefinitionRecord`; new records
never emit it.

Changing the public runtime name or another constitutional authority requires
an explicit ADR and explicit user approval. General cleanup requests are not
approval for a constitutional rename.

# Loops and modes

## Everything is a loop

Not a metaphor — a single runtime. A search, a stored string, a past run, a
model call, an adapter, a validator, and an entire solution all execute inside
the same envelope.

The reason is practical rather than aesthetic: because they are the same kind
of object, any of them can be nested, retried, budgeted, replaced, paused, or
inspected without a special case for each. A system with six execution
mechanisms needs six retry stories, six budget stories, and six ways to be
observed.

## A loop always has a stop condition

```python
LoopConfig(stop_condition="run_to_completion")   # work until the goal is met
LoopConfig(stop_condition="success_once")        # one successful iteration is enough
```

`success_once` matters more than it looks. A great deal of real work is "try
until something works" — a retrieval, a parse, a provider call. That is a loop
whose stopping rule is *one iteration succeeded*, and saying so explicitly
means the runtime can account for it like any other loop.

## Three modes, granted rather than chosen

| Mode | Calls a model | Use |
|---|---|---|
| `deterministic` | never | the default rail |
| `hybrid` | for steps needing judgement | escalation |
| `non_deterministic` | leads with the model | exploration |

```python
LoopConfig(allowable_modes=("deterministic", "hybrid"),
           preferred_modes=("deterministic", "hybrid"))
```

**Permission, not preference.** A loop cannot exceed the modes it was granted,
and a child cannot exceed its parent — `spawn()` clamps a child's modes to the
intersection with the parent's and refuses a disjoint request. So "can this
call a model?" is answerable before you run it, by reading the config.

A deterministic loop stays on the code rail *even when a live model is wired
up*. Wiring a provider grants a capability; it does not spend it.

## Nesting

```python
root = Loop("prepare a quarterly plan", config, ledger=ledger)
child = root.spawn("gather last quarter's numbers")
grandchild = child.spawn("check one assumption")
```

Depth is unbounded in principle and bounded by `max_depth` in practice. The
parent records its children as they return, which is what lets a report
reconstruct the tree.

## The nine-step practitioner kernel

The standard template. Steps are configurable — nine is a useful default, not a
law:

```
orient → research → decide → act → verify → commit
```

```python
LoopConfig(framework="custom",
           custom_steps=("orient", "research", "decide", "act",
                         "verify", "commit"))
```

`loop-engine --map` prints the full kernel with what each step owns.

## The four intelligence pillars

A loop can consult four kinds of intelligence, and each is itself a loop:

| Pillar | What it serves |
|---|---|
| string | task framings, questions, strategies |
| code | registered executable capabilities |
| past runs | what happened before |
| user | guidance you have left |

Cheapest first. **A store hit outranks a model call by design** — which is
worth knowing when you are testing whether a model helps: a warm store will
serve the step and the model will never be reached. Vary what serves the step,
not just whether a model is available.

## What a loop returns

```python
result["value"]         # the answer
result["mode"]          # which mode actually ran
result["model_calls"]   # how many semantic calls it spent
```

And the ledger holds the rest: every step, every mode decision, every
retrieval, every model call with provider-reported tokens — over a closed
vocabulary of 59 event families, hash-chained so tampering is detectable.

See [reports](reports.md) for reading it back.

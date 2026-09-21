# An unavailable backend must not look like an empty result

Kind: recorded failure and its repair, from Runtime History and Solution
Intelligence.

## When to use this record

Use it when a search, a lookup, or a retrieval step returns nothing, and you
cannot tell from the return value whether the store was searched and held no
match, or whether the store could not be reached at all.

## What was recorded

The SQLite and the LanceDB retrieval paths caught their own exceptions and
returned an empty list. A caller received the same value for two different
facts: "I searched and found nothing" and "I could not search".

The repair raises a typed unavailable error instead. The boundary over the
four persistent intelligence layers preserves that unavailability after the
canonical search records its failure, so the failure reaches the caller and
also reaches the event history. A search that ran and matched nothing still
returns a normal empty result, because that is a real answer.

## Why this matters more than it looks

A step that treats an unreachable store as an empty store will decide it has
no prior work to reuse and will redo the work. The redone work looks correct.
The cost, the duplicated result and the lost prior decision are invisible,
because nothing ever reported an error.

## The known-wrong case

The wrong repair is to log the exception and keep returning the empty list.
The log satisfies the person reading logs. The calling step still cannot tell
the two facts apart, because the return value is still the same. The
distinction has to be in the value the caller receives, not only in a message
beside it.

## What to record

Record which of the two facts the step observed, the typed error when the
store was unavailable, and the event that carries the failure into the run
history.

## Source

`artifacts/architecture-audit-2026-09-19/intelligence-access-repairs.md`,
section "Retrieval behavior", and
`src/loop_engine/core/retrieval.py`.

# A short candidate pool can hide an eligible match

Kind: recorded repair from Runtime History and Solution Intelligence.

## When to use this record

Use it when a filtered search returns nothing, or returns a weak result, and
you can point at an item in the store that should have matched.

## What was recorded

Search over the four persistent intelligence layers took a small pool of
top-ranked results from the backend and then applied the caller's filters to
that pool. When every item in the short pool failed the filter, an eligible
item further down the ranking was never considered. The search reported an
empty result that looked like a genuine absence.

Three changes were made together:

1. Required facets now establish the eligible set before rank fusion, so
   filtering happens against the whole ranking rather than against a slice.
2. A filtered search now considers the complete local backend ranking, so a
   short initial pool cannot hide an eligible match.
3. The requested result count now limits the combined result list across the
   four layers, and it must be a positive whole number when supplied.

## The cost, stated plainly

Considering the complete local ranking can be more work than scanning a small
pool. The recorded repair states this as a correctness tradeoff and claims no
performance improvement. Pushing the filter down into the backend is a
separate optimisation that has to be qualified against the same result
contract before it is used.

## The known-wrong case

The wrong repair is to enlarge the pool from ten to one hundred. That makes
the failure rarer and harder to reproduce without removing it. A rare wrong
answer in a search is worse than a frequent one, because nobody investigates
it.

## What to record

Record the item that should have matched, the filter that excluded the pool,
the ordering of filter and fusion after the repair, and the cost you accepted.

## Source

`artifacts/architecture-audit-2026-09-19/intelligence-access-repairs.md`,
section "Retrieval behavior".

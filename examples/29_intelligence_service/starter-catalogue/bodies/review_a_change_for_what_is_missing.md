# Review a change for the work it leaves out

Look for the work that is absent rather than the work that is present, because absent work leaves no line to comment on.

## When to use it

Use it after a correctness review, and always for a change written by an agent, which tends to satisfy the words of a request and skip the parts that were implied.

## Steps

1. List everything the request asked for, including anything implied by the words used, such as a list needing paging or a write needing a permission check.
2. Compare that list with the files the change touches. Mark each request item as done, partly done or absent.
3. Ask which callers of the changed code were not updated. Search for every use, not only the ones in the same folder.
4. Ask what documentation, settings, migration or alarm the change needs and does not have.
5. Ask what happens on the paths that were not changed: the old version of the record, the failure branch, the empty result.
6. Ask who else must act before this change is safe to release.
7. Turn each absent item into either a required change now or a written follow up with an owner.

## Checks

- Every item of the request is marked done, partly done or absent.
- Every caller of a changed function was found and judged.
- Absent items are either fixed or written down with an owner, never silently dropped.
- The change does not leave two ways of doing the same thing without a reason.

## Known-wrong example

An agent is asked to add a new field to an order and does so in the create path. The review approves it. The update path, the export and the search filter never learned about the field, so orders edited after creation silently lose it. Nothing in the change shows this, because the missing work is in files the change never touched. Searching for every use of the order record would have found all three.

## What to record

- The request list with a state for each item.
- The callers found and the ones deliberately left alone.
- The follow up items with owners.

## Source

- `src/loop_engine/strings/ask_strategies.py`: this repository registers several named ways of asking the same question, including asking again with part of the material hidden and asking whether the first answer still holds, so a single phrasing does not decide the result.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision db18890.

# Version an interface so older callers keep working

Change an interface in a way that does not break the programs already calling it, and make the breaking change visible when it is unavoidable.

## When to use it

Use it for any interface someone else calls: an endpoint, a message format, a stored record shape, a library function or a file format.

## Steps

1. Sort each proposed change into two groups. Adding an optional field, adding a new value a caller may ignore, or accepting a wider input is compatible. Removing a field, renaming one, narrowing what is accepted, changing a type, changing a unit or changing a default is not.
2. Make compatible changes without a new version, and announce them.
3. For a change that is not compatible, add the new form beside the old one and give it an explicit version identifier.
4. Carry that version in the record itself, in the path or in a header. Never decide by guessing from the fields present.
5. Refuse a version you do not support, with a clear message, instead of reading it as the nearest one you know.
6. Measure who still uses the old version before planning its removal, and tell them with a date.
7. Keep the old version working until the measurement shows no traffic, then remove it in its own release.
8. Write down, for each version, what changed and what a caller must do to move.

## Checks

- Every change is classified as compatible or not, and the classification is written down.
- The version travels with the record or the request and is never inferred.
- An unsupported version is refused, not reinterpreted.
- The old version has measured traffic before it is removed.

## Known-wrong example

A team changes a duration field from seconds to milliseconds and keeps the same name and version. Callers that were not updated schedule work a thousand times too early. Nothing refuses the old caller, because the field still holds a number. A new field name, or a new version that refuses the old shape, would have turned a silent wrong answer into a visible refusal.

## What to record

- The classification of each change.
- The version identifier and the differences from the previous one.
- The measured traffic on each version and the removal date.

## Source

- `src/loop_engine/catalog/protocol.py`: an adapter in this repository declares which operations it really supports in a handshake, and refuses an operation it cannot support instead of quietly doing something weaker.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.

# Supply the files and facts an assignment needs

Give the worker the material itself, or an exact reference it can fetch, instead of a description of where something might be.

## When to use it

Use it with every assignment handed to an agent or a separate process, and whenever an attempt failed because the worker looked in the wrong place.

## Steps

1. List what the work must read: files, records, examples of the expected output, and the rules that apply.
2. Give each one an exact identity: a path with a revision, a record identifier, or a reference addressed by digest.
3. Include small essential material in full. A worker should not have to search for the one paragraph that defines correct.
4. For large material, give a reference the worker can resolve, and say how to resolve it.
5. Check that each reference resolves before you send the assignment. A broken path costs a whole attempt.
6. Say which material is authoritative when two sources disagree, because they will.
7. Put everything for one assignment in one place that persists across attempts, so a second attempt starts from the same material.
8. Say what is deliberately not supplied, and whether the worker may go and find it.

## Checks

- Every reference resolves at the moment the assignment is sent.
- The material that defines correct is present in full.
- One source is named authoritative for each question.
- The material stays available for a second attempt.

## Known-wrong example

An assignment says to follow the existing style in the repository. The worker reads three files, two of which are old and inconsistent, and follows the wrong one. The review sends it back, and the second attempt reads three different files. Naming one file as the authoritative example, with its revision, would have made both attempts the same.

## What to record

- The material list with exact identities and which is authoritative.
- The references checked before sending.
- What was deliberately left out and whether the worker may fetch it.

## Source

- `src/loop_engine/core/information_access.py`: this repository gives a produced value a logical identity and resolves it through a check on scope, permissions, size and contract identity, so a consumer asks for the value rather than for a location.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision d893bba.

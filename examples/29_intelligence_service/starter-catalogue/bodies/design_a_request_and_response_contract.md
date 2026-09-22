# Design a request and response contract

Decide what an interface accepts and returns before writing the handler, and write it down where both sides can read it.

## When to use it

Use it when you add an endpoint, a message, a job input or a function that another team, another service or an agent will call.

## Steps

1. Name the one thing the call does, in a verb and a noun. If you need the word "and", it is probably two calls.
2. List the inputs. For each, give the type, whether it is required, the allowed values or range, and the unit.
3. Decide what identifies the subject of the call, and whether the caller supplies that identity or the service creates it.
4. Describe the successful result: its fields, their types and their units. Return an object, not a bare list or a bare string, so that fields can be added later.
5. List the failures the caller must handle, each with a stable code and a message meant for a developer.
6. Say what is guaranteed: ordering, uniqueness, what happens when the same call arrives twice, and what is only promised at some later time.
7. Use one naming style and one date and time format across the whole interface, and state the time zone.
8. Write an example request and an example response, and keep them in the tests so they cannot drift.

## Checks

- Every input has a type, a requirement state and a unit or allowed set.
- The result is an object with room for new fields.
- Each failure has a stable code that the caller can branch on.
- The examples in the document are executed by a test.

## Known-wrong example

An endpoint returns a plain list of orders. Six months later the team needs to add paging, so they change the result into an object with a list inside it. Every caller breaks at once, and the change cannot be released gradually. Returning an object from the start, with the list as one field, would have made paging a new field instead of a new shape.

## What to record

- The contract: inputs, result, failures and guarantees.
- The example request and response used in the tests.
- The decisions about identity, ordering and repeated calls.

## Source

- `src/loop_engine/core/workspace_contracts.py`: this repository passes typed request, result and policy objects across a boundary, so a caller supplies one named object rather than a long list of positional arguments.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision e2898c7.

# Write a data contract for a table or a feed

Write down what a data set promises, so that a change on the producing side is a visible decision rather than a surprise for its readers.

## When to use it

Use it when one team produces data another team consumes: a table, an export, a message stream, an interface response used for reporting, or a file delivered on a schedule.

## Steps

1. Name the owner of the data and the people who read it.
2. Describe each field: name, type, unit, whether it can be empty, allowed values, and what it means in the real world.
3. Describe the set as a whole: what one row represents, which fields identify a row, and how many rows to expect.
4. State the promises about time: how often it is produced, how late it may be, and how far back it can change.
5. State the quality rules you will check: no repeated identifiers, totals inside a range, a share of empty values below a limit, values matching a reference list.
6. Check the rules where the data is produced, and refuse or quarantine a delivery that breaks them rather than passing it on.
7. Version the contract and treat a removed or narrowed field as a change that needs agreement, as with any interface.
8. Publish the rule results beside the data, so a reader can see that today's delivery passed.

## Checks

- Every field has a type, a unit and a meaning in words.
- The identifying fields are named and their uniqueness is checked.
- A delivery that breaks a rule is stopped, not passed on with a note.
- The latest rule results are visible to the readers.

## Known-wrong example

A reporting team builds on a column called status, reading the values active and closed. The producing team adds the value pending and stops setting closed. No contract exists, so nothing fails. The monthly report quietly undercounts for a quarter, and the error is found by a customer. A declared set of allowed values, checked at production, would have refused the first delivery.

## What to record

- The contract: fields, meanings, promises and rules.
- The rule results for each delivery.
- Each contract version and what changed between versions.

## Source

- `src/loop_engine/core/observation_expectations.py`: this repository checks an observation against a declared shape as a separate, passive step, and treats matching that shape as a check on structure rather than proof that the value is right.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.

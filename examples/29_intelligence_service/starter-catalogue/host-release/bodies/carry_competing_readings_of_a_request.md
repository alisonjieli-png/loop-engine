# Carry competing readings of a request until an observation separates them

When a request can mean different things, keep the readings that would produce different results. Separate them with a cheap observation, not with an early choice.

## When to use it

Use it when the wording of a request and its evident purpose point in different directions, or when two reasonable people would build different things from the same sentence.

## Steps

1. State the materially different readings that are still open.
2. For each reading, say what it would actually build and how the results would differ.
3. Say which reading the literal wording supports and which reading the evident purpose supports.
4. Ask whether there is a reading under which the work is already done, or is not worth doing.
5. Look for one cheap observation that separates the readings. Prefer it to an argument about the readings.
6. Decide which readings can be carried together at little extra cost and which exclude each other.
7. Carry the open readings until an observation separates them. Then record which reading was dropped and why.

## Checks

- The readings differ in what they produce, not only in wording.
- The text of the task supports each reading.
- No reading was chosen before an observation or an answer separated them.
- The person who decides can see the difference between the readings.

## Known-wrong example

The request says: remove duplicates from the orders table. Reading one deletes rows that are exactly equal. Reading two merges orders from the same customer on the same day. Reading three reports the duplicates and deletes nothing. An agent picks reading one and deletes rows. A count of exactly equal rows costs one query. When the count is zero, reading one is already done, and the real question is between reading two and reading three.

## What to record

- The readings, what each would build, and the support for each.
- The observation that separated them and its result.
- The readings that were dropped, with the reason.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the step that frames alternatives, and the guidance record about carrying competing readings.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for framing alternatives, with its checks.

Licence: MIT. Compiled from revision e2898c7.

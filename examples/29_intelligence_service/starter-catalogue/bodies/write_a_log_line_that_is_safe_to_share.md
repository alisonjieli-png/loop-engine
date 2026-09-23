# Write a log line that is safe to share

Write the record so that it helps whoever reads it at three in the morning, and so that it can be handed to a support engineer without leaking anything.

## When to use it

Use it whenever you add or change a log line, and when you review a change that adds one.

## Steps

1. Write one event per line, as structured fields rather than a sentence with values glued into it.
2. Include the fields a reader needs to act: the time with its zone, the level, the operation, the identifier of the work, the outcome and the duration.
3. Refer to data by identifier rather than by content. Log the order identity, not the customer address.
4. Never log a password, a key, a token, a card number, an authorisation header, a full request body or a model prompt.
5. Keep an allowed list of fields that may be recorded, and add to it deliberately. An allowed list is safer than a list of forbidden words.
6. Say what happened and what the program did about it: retrying, giving up, using a default.
7. Keep the text stable and put the changing parts in fields, so the same event can be counted.
8. Read your own lines from the point of view of someone who does not know the code. If a line cannot be acted on, change it or remove it.

## Checks

- A sample of real lines contains no secret and no personal content.
- Every line has time, level, operation, work identifier and outcome.
- The message text is stable and the variable parts are fields.
- A new field must be added to the allowed list before it appears.

## Known-wrong example

A service logs the whole request body when validation fails, to make debugging easier. The body holds names, addresses and card details. The logs are shipped to a third party search tool that many people can read, and the data is kept for a year. An allowed list of fields, with the failing field name and no value, would have given the same help with none of the exposure.

## What to record

- The allowed field list and who may change it.
- The retention period for each log stream and who can read it.
- The sample review that showed no secret content.

## Source

- `src/loop_engine/core/otel_export.py`: when this repository projects a saved run into spans for a tracing system, it copies only a named list of safe keys and leaves raw prompts, tool output, secrets and material bodies out.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.

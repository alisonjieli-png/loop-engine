# Remove personal data before it reaches a log

Stop sensitive values at the place they are written, rather than trying to clean them out of storage afterwards.

## When to use it

Use it for logs, traces, error reports, analytics events, support exports and any copy of production data used for testing.

## Steps

1. List the fields that count as personal or secret in your system. Include the ones that identify a person together, such as a postal code with a birth date.
2. Decide for each field what a reader really needs: nothing, a stable identifier that cannot be reversed, a shortened form such as the last four characters, or the value itself with an approval.
3. Apply the decision in one shared place that every writer passes through, so a new log line is safe by default.
4. Prefer an allowed list of fields to a search for forbidden patterns. A pattern search misses the field nobody thought of.
5. Handle nested structures and free text, where values hide inside messages and stack details.
6. Do the same for error reporting tools, which often send local variables and request content by default.
7. Test with a record containing every sensitive field and check that none of them appears in the output.
8. Set retention and access rules for what remains, and delete on schedule.

## Checks

- A test record with every sensitive field produces output containing none of them.
- The removal happens in one shared place, not in each call site.
- Error reporting is included, not only the main log.
- The retention period and the readers are written down.

## Known-wrong example

A team adds a filter that removes any field called password. An error report later includes a local variable holding the whole form, where the key is spelled differently, and the value is sent to an external service. An allowed list of fields, applied in the shared writer, would have sent the field names and no values whatever they were called.

## What to record

- The field list and the decision for each field.
- The place the removal happens and the test that proves it.
- Retention, access and deletion for each stream.

## Source

- `src/loop_engine/core/semantic_event_history.py`: this repository builds the view a model is given from an allowed list of event kinds and fields, so a record that was not named for that view cannot reach it.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.

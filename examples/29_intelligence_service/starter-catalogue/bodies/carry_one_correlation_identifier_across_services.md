# Carry one correlation identifier across services

Give each piece of work one identifier that travels with it, so the records of five services can be read as one story.

## When to use it

Use it as soon as a request touches more than one service, one queue or one background job, and before the first investigation that needs it.

## Steps

1. Create one identifier at the outermost entry point, or accept the one the caller sent if you trust the caller.
2. Put it in every log line, every record written and every outbound request.
3. Use a standard header so tools and other teams understand it without agreement.
4. Pass it through queues in the message, not only in the request, so background work stays connected.
5. Keep a second identifier for the current step, and record which step it came from, so an ordered view can be rebuilt.
6. Return the identifier to the caller in the response and in any failure, so a user can quote it in a report.
7. Make the identifier meaningless in itself. It must not carry a customer name, an account number or anything private.
8. Check the chain end to end: start a request, then find every record for it with one search.

## Checks

- One search by the identifier returns records from every service involved.
- Background work started by a request carries the same identifier.
- The identifier appears in the response and in failures.
- The identifier holds no personal or secret content.

## Known-wrong example

Each service generates its own request number. An investigation into one slow checkout takes two days of matching timestamps by hand across four log systems, and the match is never certain. One identifier created at the entry and passed on would have made it one search.

## What to record

- The identifier, where it is created and the header that carries it.
- The step identifier and the step it came from.
- The result of the end to end check.

## Source

- `src/loop_engine/core/otel_export.py`: when this repository projects a saved run into spans, each span names the span it belongs to, and the projection validates that the resulting structure is complete before it is exported.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 390643e.

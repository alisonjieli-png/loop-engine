# Bound a list endpoint with paging and limits

Make sure no single call can ask for an unbounded amount of work, data or time.

## When to use it

Use it for any endpoint, query or export that returns many records, and for any input whose size the caller controls.

## Steps

1. Set a maximum page size and a default page size. Apply the maximum even when the caller asks for more, and say so in the response.
2. Choose a paging method. Paging by a stable key and a limit is steadier than paging by offset when rows are being inserted.
3. Return the position to continue from as an opaque value the caller passes back, so you can change the method later.
4. Give the listing a fixed order, including a tie breaker such as the identifier, or paging will repeat and skip records.
5. Set a maximum request body size and refuse larger bodies before reading them into memory.
6. Set a time limit for the query and a limit on the rows it may examine, not only on the rows it returns.
7. Rate limit per caller, and return the limit, the remaining count and the reset time.
8. Provide a separate path for a genuinely large export, such as a background job that produces a file, and point callers to it.

## Checks

- Asking for a page larger than the maximum returns the maximum, not the request.
- Paging through a table that is being written does not repeat or skip records.
- A body larger than the limit is refused before it is fully read.
- The query has both a row limit and a time limit.

## Known-wrong example

A reporting endpoint accepts a page size chosen by the caller. A script asks for one million rows, the service builds the whole result in memory, and the process is killed for using too much memory. The restart drops every other request in progress. A maximum page size and a row limit would have turned one bad request into one refusal.

## What to record

- The default and maximum page size and the paging method.
- The body size, row and time limits.
- The rate limits and what the response tells the caller about them.

## Source

- `src/loop_engine/core/service_api.py`: the hosted surface in this repository declares its endpoints and refuses a request body larger than a fixed maximum, and it records a metering entry for the work it did.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.

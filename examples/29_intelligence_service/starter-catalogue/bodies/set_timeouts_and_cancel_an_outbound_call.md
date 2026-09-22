# Set timeouts and cancel an outbound call

Give every call to another system a deadline you chose on purpose, and make sure the work really stops when the deadline passes.

## When to use it

Use it for every network call, database query, subprocess and job that can wait: in other words, all of them. A call with no deadline will one day wait forever.

## Steps

1. Set the deadline for the whole operation first, from what the caller can wait for.
2. Divide that deadline among the calls the operation makes, leaving room for the work between them.
3. Set separate limits where the tool allows: time to connect, time to the first byte, time for the whole call.
4. Base the numbers on a measurement of normal and slow responses, not on a round number. Record the measurement.
5. Pass the remaining time down with the request, so a service that is called can stop work it can no longer deliver.
6. Cancel properly: close the connection, cancel the task, and check that the work on the other side actually stops.
7. Decide what the caller receives when the deadline passes: a clear failure, a partial result, or a cached value. Say which.
8. Make sure a timeout is not silently treated as an empty answer. Empty and unknown are different.

## Checks

- Every outbound call has an explicit deadline.
- The sum of the inner deadlines fits inside the outer one.
- Cancellation stops the work, and a test shows it.
- A timeout produces a distinct failure, never an empty result.

## Known-wrong example

A page calls three services with no deadline set. One of them slows to sixty seconds under load. Every request thread waits, the pool fills, and the whole site stops answering, including pages that never use that service. A two second deadline would have degraded one part of one page instead.

## What to record

- The measured normal and slow response times.
- The chosen deadlines and how they divide.
- What the caller receives when a deadline passes.

## Source

- `src/loop_engine/core/runtime_capacity.py`: this repository takes a limit from something measured, such as memory or disk, rather than allowing a part of the system to declare a number of its own.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision f29bddc.

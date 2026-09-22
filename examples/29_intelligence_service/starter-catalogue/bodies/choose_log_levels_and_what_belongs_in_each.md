# Choose log levels and what belongs in each

Agree once what each level means, so that a level can be used to decide whether to wake somebody.

## When to use it

Use it when you set up logging for a service, and whenever a review finds the same event recorded at three different levels in three places.

## Steps

1. Write one sentence for each level that says who acts on it. A level nobody acts on is decoration.
2. Use error for a failure that a person must look at, with enough detail to start. Do not use it for a failure the code handled.
3. Use warning for something that is working now but will fail if it continues, such as a retry that succeeded or an allowance nearly spent.
4. Use information for the events that describe normal progress: started, finished, decided, with the identity and the outcome.
5. Use debug for detail that helps during investigation, and make it possible to turn on for one part without turning it on everywhere.
6. Do not log the same failure at several levels as it travels up the call chain. Record it once, where it is handled.
7. Decide which levels are shipped, which are kept and for how long, and what each costs.
8. Review the error volume regularly. An error nobody reads is a broken level, not a busy system.

## Checks

- Each level has a written sentence about who acts on it.
- A handled failure does not appear as an error.
- One failure produces one record, not one per frame.
- The error volume is small enough that each one is read.

## Known-wrong example

A service records every failed request as an error, including the ones a retry fixes a second later. The error stream reaches thousands a day, the team stops reading it, and the one real error, a database running out of disk, sits unread among them. Recording the successful retry as a warning and only the final failure as an error would have kept the stream readable.

## What to record

- The meaning of each level and who acts on it.
- The volume per level and the retention for each.
- The review of the error stream and what changed after it.

## Source

- `src/loop_engine/core/event_vocabulary.py`: this repository keeps one closed set of event families and maps every recorded kind into it, so a reader can group events without knowing every producer.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.

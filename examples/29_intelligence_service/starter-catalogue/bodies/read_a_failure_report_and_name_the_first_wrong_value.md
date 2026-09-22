# Read a failure report and name the first wrong value

Work from the reported failure back to the earliest place where a value was already wrong, instead of patching where the failure surfaced.

## When to use it

Use it for any crash, exception or failed assertion where you have a call trace, a log or an error message with a location.

## Steps

1. Read the last line of the trace first. It names the operation that could not continue.
2. Read the message and turn it into a sentence about a value: what was expected, what was there instead.
3. Walk up the frames and find the first one in code you own. Frames inside a library usually report a value your code passed in.
4. At that frame, write down the value that is wrong and the value that should have been there.
5. Ask where that value came from. Follow it back one step at a time until you reach the place where it was created or read.
6. Check whether the wrong value was already wrong when it was created, or became wrong on the way.
7. Repair at the earliest point where the value is wrong and the code is yours.
8. Confirm that the original failure is gone and that no other caller depended on the old behaviour.

## Checks

- The first frame in owned code is identified, not only the last frame overall.
- The wrong value and the expected value are both written down.
- The repair is at the origin of the wrong value, not at the place where it finally broke something.
- The original failure no longer reproduces.

## Known-wrong example

A service fails with a message about a missing key deep inside a formatting library. A developer adds a default value at that point. The report now prints the word unknown for thousands of records, because the real cause was an earlier lookup that silently returned nothing when the database was slow. The failure was the only visible sign of a data problem, and the default removed it.

## What to record

- The full trace or error text.
- The first owned frame and the wrong value there.
- The origin of the value and the reason it was wrong.

## Source

- `src/loop_engine/core/capability_rejection.py`: this repository records a refusal as typed data that names which part refused, one closed reason code and the arguments involved, and it can report the underlying cause of a wrapped failure.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision f29bddc.

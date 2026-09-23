# Review generated output before anything executes it

Treat code, queries and settings produced by a generator or a model as material to inspect, never as something to run because it arrived.

## When to use it

Use it whenever a program turns text into behaviour: loading a module by name, evaluating an expression, decoding a serialised object, applying a settings file, or running a script an agent wrote.

## Steps

1. Decide whether the text needs to execute at all. A lookup table, a registered name or a declared shape is usually enough and is always safer.
2. If execution is needed, keep the list of what may be executed in your own code, and select from it by name. Do not build the name from the input.
3. Read the generated text before the first run. Look for network calls, file writes outside the working folder, credential reads and long running work.
4. Run it in a confined place first: a separate process, a clean folder, no credentials, no network unless the task needs it, with limits on time and memory.
5. Compare what it did with what it declared it would do. Investigate any difference.
6. Use safe decoding for serialised data. Never decode a format that can construct arbitrary objects from an untrusted source.
7. Keep the exact text and its digest, so the thing reviewed is the thing that ran.
8. Require a separate approval for any effect outside the confined place.

## Checks

- Nothing is executed whose name or body came straight from input.
- The first run happened in a confined place with limits.
- The digest of the reviewed text matches the digest of what ran.
- Declared effects and observed effects agree.

## Known-wrong example

A reporting tool lets users store a formula that it evaluates with the language's general evaluation function. A user stores a formula that reads the process environment and posts it to a web address. Every credential the service holds leaves the building. A small parser for the four arithmetic operations, or a registered set of named functions, would have given the same feature with none of the risk.

## What to record

- The exact generated text and its digest.
- The limits of the confined run and what was observed.
- The approval for any effect that left the confined place.

## Source

- `src/loop_engine/core/service_runtime/http_entrypoint.py`: this repository serves only a host reviewed manifest of material, checks the size and digest of each file again at load time, and loads no code named by the request.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.

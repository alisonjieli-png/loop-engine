# skip_and_continue

Record the failure, skip the unit, finish the run.

Family: `failure-handling`  |  Status: measured

## How it works

- Attempt each unit a small number of times.
- On exhaustion, record the unit as lost and move past it.
- Answer from the units that worked, and return the lost ones as a field.

## What it gives you

- The only policy here that finishes a run containing a failure nothing could fix.
- Partial results are the right answer for plenty of work, and this is the only arm that can produce one.
- Returns the lost units as a field rather than a log line, so a caller can decide rather than discover.

## What it costs you

- Returns an answer that is quietly wrong. In the permanent-failure scenario it answered rather than stopping, and the answer did not match the truth.
- The wrongness is proportional to what was skipped and there is nothing in the answer itself that shows it.
- Needs a verifier beside it to be safe. Alone it converts a visible failure into an invisible one.

## Pick this when

- Partial results have value and the caller can see what was lost.
- You are pairing it with independent verification, which together give a finished run and an honest refusal.

## Avoid it when

- Anything consumes the answer without reading the lost list.

## Run it

```bash
python3 failure-handling/04-skip-and-continue/embodiment.py        # its own self-check
python3 registry.py run --family failure-handling
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

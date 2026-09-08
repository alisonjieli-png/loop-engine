# retry_same

Send the same request again, up to a budget.

Family: `failure-handling`  |  Status: measured

## How it works

- Attempt each step up to a fixed number of times.
- Any usable reply ends the retries.
- Exhausting the budget stops the run.

## What it gives you

- Handles the most common real failure: one that goes away.
- One number to set, and its meaning is obvious.
- No change to the request, so nothing about the run's semantics shifts when it retries.

## What it costs you

- Cannot fix a failure whose cause is the request itself. Against that shape it spends the entire budget learning nothing.
- Multiplies cost on exactly the runs that were already going badly.
- A budget large enough to ride out a real outage is a budget large enough to hide one.

## Pick this when

- Failures are transient and independent.
- A retry is cheap relative to losing the run.

## Avoid it when

- The failure is deterministic in the request. Escalate instead.

## Run it

```bash
python3 failure-handling/02-retry-same/embodiment.py        # its own self-check
python3 registry.py run --family failure-handling
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

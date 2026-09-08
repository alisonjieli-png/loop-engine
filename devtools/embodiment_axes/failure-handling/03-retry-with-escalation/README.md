# retry_with_escalation

Retry plainly first; when that stops helping, change the request.

Family: `failure-handling`  |  Status: measured

## How it works

- Spend a plain retry budget first, because most failures clear on their own and escalation costs more.
- When it runs out, mark the request escalated and try again.
- Exhausting the ladder stops the run.

## What it gives you

- The only policy here that recovers a failure caused by the request itself, which no amount of retrying can fix.
- Escalates only after plain retries fail, so a transient failure costs zero escalations.
- The ladder is a field, not a subclass, which is the same shape as this runtime's own escalation ladder.

## What it costs you

- More expensive than plain retry on every failure it does not fix, because it pays the plain budget and then the escalated one.
- Escalating changes the request, so the successful attempt is not the attempt that was specified. That has to be recorded or the run is not reproducible.
- Two budgets to set instead of one.

## Pick this when

- Failures have more than one cause and some are request-shaped.
- You can express a stronger version of the same request.

## Avoid it when

- Every failure is transient. The ladder is then pure overhead.

## Run it

```bash
python3 failure-handling/03-retry-with-escalation/embodiment.py        # its own self-check
python3 registry.py run --family failure-handling
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

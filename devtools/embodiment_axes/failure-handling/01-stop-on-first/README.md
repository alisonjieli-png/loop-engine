# stop_on_first

The first failed step ends the run.

Family: `failure-handling`  |  Status: measured

## How it works

- Attempt each step once.
- Treat a raised error and an unparseable reply alike.
- Stop, and say which unit it stopped on.

## What it gives you

- Spends nothing on a failure it cannot fix, which is the right answer when the failure is permanent.
- Never returns a partial result dressed as a complete one.
- Counts a reply that does not parse as a failure, so confident prose cannot pass as a completed step.
- Simplest possible policy; nothing to tune.

## What it costs you

- Loses the whole run to a failure that would have cleared on the next attempt, which is the most common kind.
- Wastes all the work already done, unless a checkpoint store is paired with it.
- Turns a rate limit into an outage.

## Pick this when

- Failures are rare and meaningful, and a human is watching.
- Partial results are worse than no result.

## Avoid it when

- The transport or the provider is flaky, which is most of the time.

## Run it

```bash
python3 failure-handling/01-stop-on-first/embodiment.py        # its own self-check
python3 registry.py run --family failure-handling
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

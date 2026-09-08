# one_at_a_time

One unit of work per call, in an order code decides.

Family: `control-flow`  |  Status: measured

## How it works

- Hold a cursor.
- Read the unit it names.
- Send one observation per call.

## What it gives you

- Smallest possible prompt per call.
- The order costs nothing to communicate, because it is never sent.
- A failure loses one unit of work.

## What it costs you

- Call count equals the horizon. This is the dominant cost at scale.
- The order is fixed, so it cannot react to what a unit contained.
- Per-call overhead is paid the maximum number of times.

## Pick this when

- Per-call cost is low and prompt size is the constraint.
- Units are independent and order does not matter.

## Avoid it when

- Calls are the expensive thing. Batch instead.

## Run it

```bash
python3 control-flow/01-one-at-a-time/embodiment.py        # its own self-check
python3 registry.py run --family control-flow
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

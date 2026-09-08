# bounded_state

A state schema with no field proportional to the horizon.

Family: `context-transport`  |  Status: measured

## How it works

- Carry five scalars, a mapping over a fixed account vocabulary, and a cursor naming the next shard.
- The cursor replaces the list of what is left; the count replaces the list of what is done.
- Everything else is identical to state_patch.

## What it gives you

- Peak prompt moves from 949 bytes at 4 shards to 986 at 1,024. That is 37 bytes across a 256-fold increase in horizon.
- One tenth the total bytes of state_patch at 1,024 shards: 1,000,925 against 10,409,501, for identical answers.
- No horizon in reach. Nothing in the record grows with the input.

## What it costs you

- Requires a closed vocabulary. The account mapping is bounded only because the accounts are known in advance.
- The cursor imposes an order, so it cannot express work that jumps around or runs out of order.
- Still one call per shard; it fixes bytes, not call count.

## Pick this when

- The horizon is large or unbounded.
- You can name a closed schema and prove no field grows with input.

## Avoid it when

- You cannot bound the vocabulary. Then measure rather than assume.

## Run it

```bash
python3 context-transport/06-bounded-state/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

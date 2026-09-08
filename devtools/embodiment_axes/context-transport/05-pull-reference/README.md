# pull_reference

Send an identifier and a list of keys; the node fetches what it needs.

Family: `context-transport`  |  Status: measured

## How it works

- The step gets a context identifier and the names of what is available, not the values.
- The node replies with a pull request naming the keys it wants.
- The ledger serves those keys and the step runs again with them.

## What it gives you

- The prompt seed is O(1) regardless of how large the stored context is.
- The pull log is a direct record of what the node believed it needed, which no push design produces.
- Access can be checked per key at serve time.

## What it costs you

- Two calls per step where a push arm needs one: 2,050 against 1,025 at 1,024 shards.
- Sends more total bytes, not fewer: 10,880,374 against 10,409,501. A seed plus a served payload is bigger than the payload alone.
- At 256 shards with a 400-step ceiling it ran out of steps and failed where the push arms solved.

## Pick this when

- Each step needs a small and different slice of a large body.
- You need per-key authorisation or an audit of what was requested.

## Avoid it when

- Every step needs essentially the whole accumulator, as here. Then the fraction pulled is one and pull is strictly worse.

## Run it

```bash
python3 context-transport/05-pull-reference/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

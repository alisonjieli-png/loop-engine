# hybrid_push_pull

Push the bounded state every step, pull only what is missing.

Family: `context-transport`  |  Status: measured

## How it works

- Every step gets the bounded state pushed, so the common case needs no fetch.
- The step may still name keys it wants from the ledger.
- A pull is only paid when it is actually asked for.

## What it gives you

- Keeps the bounded arm's flat prompt and adds the pull escape hatch.
- Measured slightly cheaper than the bounded arm at every horizon, 951 bytes against 979 at 256 shards, because it carries no remaining count.
- Pays the second call only on steps that use it, unlike pure pull which pays it always.
- The budget is a single dial between the two designs: above the state size it is a push arm, below it a pull arm, and the same code is both.

## What it costs you

- Two mechanisms to maintain and two ways for the same fact to arrive.
- On this task nothing is ever missing, so the pull path costs nothing and buys nothing. It needs a task with rare deep lookups to earn out.
- A node can pull what it was already pushed, so the ledger has to detect that or the design quietly degrades to pure pull.

## Pick this when

- Most steps need the same small state and a few need something rare and large.
- You want an audit trail of exceptional access without paying for it on every step.

## Avoid it when

- Every step needs the same thing. Then push alone is simpler and cheaper.

## Run it

```bash
python3 context-transport/08-hybrid-push-pull/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

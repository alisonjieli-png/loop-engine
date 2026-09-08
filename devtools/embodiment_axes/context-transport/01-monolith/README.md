# monolith

Put the whole world in one prompt and take one answer.

Family: `context-transport`  |  Status: measured

## How it works

- Read every shard up front through the tool.
- Inline all of it into a single prompt.
- Make exactly one model call and grade what comes back.

## What it gives you

- One call. No state, no protocol, no partial failure to reason about.
- Cheapest per unit of work below its horizon: 1,023 bytes at 4 shards, the second lowest of the eight arms.
- Nothing can be lost between steps because there are no steps.

## What it costs you

- Prompt grows about 117 bytes per shard, so a 16,000-byte window puts the wall near 136 shards. Measured: fine at 128, refused at 256.
- No intermediate result survives a failure. The run is all or nothing.
- Cannot use a tool result to decide what to read next.

## Pick this when

- The whole input provably fits the window with room to spare.
- The task is one shot and latency matters more than anything else.
- You want a baseline the other arms have to beat.

## Avoid it when

- Input size is unbounded or set by a user.
- You need progress to survive a crash.

## Run it

```bash
python3 context-transport/01-monolith/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

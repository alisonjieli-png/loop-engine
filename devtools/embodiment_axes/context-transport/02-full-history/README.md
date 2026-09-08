# full_history

Resend the entire transcript on every step.

Family: `context-transport`  |  Status: measured

## How it works

- Keep every prompt and every observation in a growing list.
- Render the whole list into each new prompt.
- The model re-derives the running total from raw history each time.

## What it gives you

- Nothing is ever summarised, so nothing can be lost by summarising.
- The transcript is the audit log. What the model saw is exactly what you can read back.
- Simplest correct multi-step design; no schema to get wrong.

## What it costs you

- Same growth rate as the monolith and the same wall, just reached later in the run. Refused at step 123 of 256 shards.
- Total bytes are the worst of any arm that gets close: 749,460 at 1,024 shards while failing.
- Re-reads the same facts every step, so cost is quadratic in steps.

## Pick this when

- Runs are short and bounded, under a few dozen steps.
- Full replayability of model input matters more than cost.
- You are debugging and want to see everything the model saw.

## Avoid it when

- Step count is set by input size.
- You are paying per token.

## Run it

```bash
python3 context-transport/02-full-history/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

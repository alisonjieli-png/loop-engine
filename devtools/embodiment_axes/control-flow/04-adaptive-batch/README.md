# adaptive_batch

Grow the batch until the window pushes back, then hold.

Family: `control-flow`  |  Status: measured

## How it works

- Double the batch while the last prompt used less than a target share of the window.
- Halve it on a refusal and retry the same units.
- Never needs to be told the window size.

## What it gives you

- Collapsed 256 units into 10 calls with no knob set by anyone.
- A window refusal is recoverable rather than fatal. It is the only arm here with that property.
- At a half-window target it never overshot at all, so a careful target buys a run with zero refusals.
- Adapts to a window it was not told about, which is what makes it portable across models.

## What it costs you

- Peak prompt is deliberately near the target share, so it uses most of the window by design.
- A greedy target trades refusals for speed: at 0.99 it absorbed five refusals on a run that had none at 0.5.
- More moving parts than a fixed K, and the batch history is another thing to record and read.

## Pick this when

- The window, the model or the unit size can change.
- You want the call saving without owning the tuning.

## Avoid it when

- You need a fixed, auditable prompt size per call.

## Run it

```bash
python3 control-flow/04-adaptive-batch/embodiment.py        # its own self-check
python3 registry.py run --family control-flow
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

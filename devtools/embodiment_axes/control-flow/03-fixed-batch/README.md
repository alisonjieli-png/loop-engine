# fixed_batch

Fold a fixed number of units per call.

Family: `control-flow`  |  Status: measured

## How it works

- Read K units.
- Put all K in one prompt.
- Advance the cursor by K.

## What it gives you

- Calls fall by a factor of K, which is the whole point.
- One knob, and its effect is exactly what you would predict.
- No extra mechanism over the cursor arm.

## What it costs you

- Somebody has to choose K, and the right K depends on the window, the observation size and the state size.
- A K that is too large is a refused prompt and a failed run, not a slow one.
- A K that is too small leaves most of the saving on the table.

## Pick this when

- You know the window and the unit size and they are stable.

## Avoid it when

- Unit sizes vary, or the window is not yours to know. Use the adaptive arm.

## Run it

```bash
python3 control-flow/03-fixed-batch/embodiment.py        # its own self-check
python3 registry.py run --family control-flow
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

# model_chosen_next

The reply picks the next unit from a list of what is left.

Family: `control-flow`  |  Status: measured

## How it works

- Send the list of remaining units.
- The reply names one.
- Remove it and repeat.

## What it gives you

- Order can react to what was just seen, which a cursor cannot.
- Natural fit when units are not interchangeable.
- The chosen order is itself a record of what the run thought mattered.

## What it costs you

- The remaining list has one entry per unit, so the prompt is proportional to the horizon and the arm inherits a wall.
- Nothing stops a repeat request, so the loop needs its own guard.
- Pays for flexibility on every call, including the calls that would have taken the cursor's answer anyway.

## Pick this when

- Order genuinely depends on content.
- The horizon is small enough that the list is cheap.

## Avoid it when

- Units are interchangeable. Then this is a cursor with a bill attached.

## Run it

```bash
python3 control-flow/02-model-chosen-next/embodiment.py        # its own self-check
python3 registry.py run --family control-flow
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

# summarised_history

Keep the transcript, but compact the oldest part once it crosses a threshold.

Family: `context-transport`  |  Status: measured

## How it works

- Append raw observations like full_history.
- When the rendered history crosses a byte threshold, fold the oldest entries into a summary line and drop their raw text.
- Recent observations stay raw, so the newest facts are never lossy.

## What it gives you

- Removes the transcript arm's wall without asking anyone to design a state schema.
- The recent window stays verbatim, which is where a reader usually looks.
- One knob. The threshold trades fidelity against bytes directly.

## What it costs you

- Summarising is where facts get silently dropped. Here the fold is arithmetic and lossless; with a model writing the summary it is not.
- Peak is set by the threshold, not by the task, so it wastes bytes at small horizons and only saves at large ones.
- Two representations of the same history exist at once.

## Pick this when

- You have an existing transcript loop hitting a wall and cannot restructure it into a state schema.
- The task genuinely needs recent raw detail.

## Avoid it when

- The summary would be model-written and correctness is required. Measure what the fold loses before trusting it.

## Run it

```bash
python3 context-transport/07-summarised-history/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

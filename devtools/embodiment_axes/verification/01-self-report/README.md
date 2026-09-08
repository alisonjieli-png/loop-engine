# self_report

The run is done when it says it is done.

Family: `verification`  |  Status: measured

## How it works

- Check that a reply arrived and claims to be an answer.
- Accept it.

## What it gives you

- Free. No second pass, no second implementation.
- Never rejects a correct answer.
- It is what a system does by default, so measuring it prices doing nothing.

## What it costs you

- Caught nothing. All five injected faults were accepted.
- The confident wrong answer is exactly the case it cannot see.
- Gives an acceptance signal that carries no information.

## Pick this when

- Wrong answers are cheap and visible downstream.
- You are prototyping and know this is the baseline.

## Avoid it when

- Anything acts on the answer without a human reading it.

## Run it

```bash
python3 verification/01-self-report/embodiment.py        # its own self-check
python3 registry.py run --family verification
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

# portfolio

Split by approach, not by work: run several, publish the first that verifies.

Family: `decomposition`  |  Status: measured

## How it works

- Run the whole task through several different designs.
- Verify each result independently.
- Publish the first that passes and stop the rest.

## What it gives you

- The only arm in the catalogue that survives one of its designs being wrong for the input. At 256 units two candidates hit their horizon and it still answered correctly.
- Refuses when no candidate verifies, rather than publishing the least bad one.
- Stops as soon as one is accepted, so the cheap candidate costs nothing extra when it works.
- Builds nothing of its own: the candidates and the checker are other folders in this catalogue, loaded as they are. It is the composability claim actually executing.

## What it costs you

- Pays for every candidate it runs before one verifies, and it cannot know in advance which that is.
- Needs a verifier good enough to tell the candidates apart. With a weak checker it publishes the first plausible answer rather than the first correct one.
- A portfolio of similar designs buys nothing but cost; the candidates have to fail differently to be worth running.
- Ordering the candidates is a real decision, because it decides what the common case costs.

## Pick this when

- No single design covers the whole input range you see.
- You have an independent checker and being wrong is expensive.

## Avoid it when

- One design covers the range, or you cannot verify a result independently.

## Run it

```bash
python3 decomposition/04-portfolio/embodiment.py        # its own self-check
python3 registry.py run --family decomposition
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

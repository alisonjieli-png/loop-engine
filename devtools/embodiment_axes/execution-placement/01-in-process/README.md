# in_process

The step runs inside the calling process.

Family: `execution-placement`  |  Status: measured

## How it works

- Call the step body as a function.
- There is no boundary.

## What it gives you

- Nothing to pay. The fastest possible placement.
- Simplest to debug: one stack, one process, one log.
- No serialisation, so a step can be handed any Python object.

## What it costs you

- No containment at all. A step that exits, exhausts memory or writes a file takes the host with it.
- A step can reach anything the host process can reach, including credentials in the environment.
- Hidden shared state makes a broken transport look like it works.

## Pick this when

- The step body is your own trusted code.
- You are measuring something else and want no noise.

## Avoid it when

- The step body is generated, or comes from a model, or touches anything you would not run as yourself.

## Run it

```bash
python3 execution-placement/01-in-process/embodiment.py        # its own self-check
python3 registry.py run --family execution-placement
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

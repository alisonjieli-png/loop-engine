# container_per_step

Each step runs in a container with no network and no writes.

Family: `execution-placement`  |  Status: measured

## How it works

- Start a container per step with the network off, the mount read-only and every capability dropped.
- Apply memory and process limits.
- Remove the container when the step ends.

## What it gives you

- The only arm here that contains a hostile step: no network, no host filesystem, no capabilities, bounded memory and processes.
- Leaves nothing behind, so one step cannot set a trap for the next.
- Refuses when no runtime is present rather than falling back to a weaker placement, so the containment claim stays true.

## What it costs you

- Container start dominates everything else, by two to three orders of magnitude over a function call.
- Needs a runtime and an image, which is operational weight.
- Image pinning is a real obligation; a tag is not a pin.

## Pick this when

- The step body is generated or untrusted.
- A step may run commands, and you need it to fail closed.

## Avoid it when

- Steps are short and numerous, and the body is your own code. Then the start cost is the whole run.

## Run it

```bash
python3 execution-placement/03-container-per-step/embodiment.py        # its own self-check
python3 registry.py run --family execution-placement
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

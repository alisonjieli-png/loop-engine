# subprocess_per_step

Each step runs in a fresh interpreter, talking over pipes.

Family: `execution-placement`  |  Status: measured

## How it works

- Spawn an interpreter per step.
- Send the prompt on standard input, read the reply on standard output.
- Nothing survives the step but what was sent back.

## What it gives you

- A step cannot accumulate hidden state, so a transport defect shows up instead of being masked by shared memory.
- A crashing step is a non-zero exit code, not a dead run.
- Costs milliseconds, not the hundreds a container costs.

## What it costs you

- Same filesystem, same network, same user. This is a memory boundary and nothing more.
- Everything crossing it has to serialise.
- Spawn cost is paid on every step, so it multiplies by the horizon.

## Pick this when

- You want the transport boundary to be real without paying for containment.
- Steps are long enough that spawn cost disappears.

## Avoid it when

- The step body is untrusted. This stops nothing it does to the filesystem or the network.

## Run it

```bash
python3 execution-placement/02-subprocess-per-step/embodiment.py        # its own self-check
python3 registry.py run --family execution-placement
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

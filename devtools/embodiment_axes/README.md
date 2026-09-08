# Embodiment axes: every design choice, with both sides stated

This folder answers one question: if someone does not want the design this
project happens to have shipped, what are their options, and what does each
one actually cost?

Twenty-two runnable embodiments across five independent axes. Every one has a
manifest that states what it gives you and what it costs you next to each
other, a self-check that runs in under a second, and where a measurement is
possible, numbers from having run it.

```bash
cd devtools/embodiment_axes
python3 registry.py list        # every embodiment, by family
python3 registry.py check       # manifests, imports, self-checks
python3 registry.py run         # all five families through their harnesses
python3 registry.py catalog     # regenerate CATALOG.md and every README
```

Read [CATALOG.md](CATALOG.md) to choose. Read [FINDINGS.md](FINDINGS.md) for
what the measurements said, including the three defects they found in this
folder's own code.

## The five axes

| Folder | The question | Answers |
|---|---|---:|
| `context-transport/` | If a step runs elsewhere, how does information reach it? | 8 |
| `execution-placement/` | Where does a step physically run? | 3 |
| `verification/` | How does an answer get accepted? | 3 |
| `memory/` | What does an earlier run contribute to a later one? | 4 |
| `control-flow/` | Who picks the next unit of work, and how much per call? | 4 |

They are independent, and that is the point. A design is one choice from each,
and the choices compose without a bundle being forced on anyone.

## How this relates to the rest of the repository

`embodiments/` holds runnable launch surfaces for the canonical runtime, one
folder per execution mechanism, with its own qualification plan.
`devtools/embodiment_lab/` is the comparison machinery those use.

This folder is a different cut. It does not run the canonical runtime at all.
It implements each design choice from scratch against a shared task so the
choices can be measured against each other without the engine's own
assumptions being present in both the thing under test and the test. When the
last check here shared assumptions with what it was checking, it could not see
three contradictions.

Nothing here is authoritative for product execution, and nothing here grants
any authority. It is a measured menu.

## What it costs to run

Everything except the container placement runs in seconds and calls no model.
The fixture reader is a pure function that plays perfectly on whatever the
prompt contains, so the comparisons measure structure and not reasoning. The
container placement needs a container runtime and records a skip with its
reason when none is present.

`--backend local` sends the same arms to a real model. Those models are cloud
proxies on this machine, so that run spends money and should be asked for
rather than assumed.

## Adding one

1. Make `<family>/<NN-name>/`. A new question is a new family, which needs its
   own `family.json` and `harness.py`.
2. Write `embodiment.py` with an `ARM` dict and a `self_check()`.
3. Write `manifest.json`. Both `cons` and `avoid_when` are required and must
   be non-empty; `registry.py check` refuses a manifest without them, because
   an option with no stated cost is an advertisement rather than a choice.
4. Run `python3 registry.py check`, then `python3 registry.py catalog`.

Discovery is by folder, so nothing has to be added to a list and the catalogue
cannot go stale against what is on disk.

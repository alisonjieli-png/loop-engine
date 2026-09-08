# Embodiment axes: every design choice, with both sides stated

This folder answers one question: if someone does not want the design this
project happens to have shipped, what are their options, and what does each
one actually cost?

Thirty runnable embodiments across seven independent axes. Every one has a
manifest that states what it gives you and what it costs you next to each
other, a self-check that runs in under a second, and where a measurement is
possible, numbers from having run it.

```bash
cd devtools/embodiment_axes
python3 choose.py --units 5000 --workers 8 --untrusted-steps --stakes high
python3 registry.py list        # every embodiment, by family
python3 registry.py check       # manifests, imports, self-checks, chooser rules
python3 registry.py run         # all seven families through their harnesses
python3 registry.py catalog     # regenerate CATALOG.md and every README
```

`choose.py` is the fastest way in. Describe the situation and it names one
embodiment per axis with the measurement behind each choice, what it would
have picked instead, and which pairs are only safe together. `--explain`
prints the whole rule table instead of one path through it. Every rule it can
return is checked against what is on disk, so a rule cannot outlive its
folder.

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
| `failure-handling/` | What does the loop do when a step fails? | 4 |
| `decomposition/` | How is the work divided before any of it is done? | 4 |

They are independent, and that is the point. A design is one choice from each,
and the choices compose without a bundle being forced on anyone. The portfolio
embodiment under `decomposition/` is that claim executing rather than asserted:
it implements nothing of its own, and runs the context-transport folders
against the verification folder as its checker.

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

## Axes not yet cut

Named here so the menu is honest about its own edges. Each is a question this
project answers today by default rather than by choice, and none has arms in
this folder yet.

- **Which model runs a step.** One fixed model, a ladder that escalates on
  failure, or an ensemble whose disagreement is the signal. The failure family
  escalates the request; it does not escalate the model.
- **What a step is allowed to do.** Authority is a separate axis from
  placement: a container decides what a step *can* reach, a grant decides what
  it *may*. This folder varies only the first.
- **What gets recorded.** Everything, sampled, or only what a later run can
  use. The memory family varies what is kept between runs, not what is written
  during one.

A folder with no arms would be worse than this list, because the catalogue
would then claim coverage it does not have.

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

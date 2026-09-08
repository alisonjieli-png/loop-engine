# governed_journal

Stage, review, promote, recall. Nothing promotes itself.

Family: `memory`  |  Status: measured

## How it works

- A record enters as a candidate carrying who produced it.
- A reviewer that did not produce it re-derives the answer.
- Only a promoted record is ever served.
- Position is checkpointed alongside, so it also resumes.

## What it gives you

- Gets the repeat saving without the blast radius: an unreviewed record is staged and never served.
- The gate is a second derivation, not a policy string, so it catches what a policy string cannot.
- Refuses to serve anything at all when no reviewer is configured, which is the correct default.
- Superset of resume: it checkpoints too.

## What it costs you

- The most machinery of any arm here: two stores, a reviewer, a journal and a promotion rule.
- The saving only arrives after review, so the first run pays for both the work and the check.
- A wrong reviewer promotes wrong records, so the reviewer is now the thing that has to be right.

## Pick this when

- You want runs to accumulate and more than one thing can write.
- Being wrong is expensive enough to pay for a review.

## Avoid it when

- Nothing repeats, or you cannot write an independent reviewer.

## Run it

```bash
python3 memory/04-governed-journal/embodiment.py        # its own self-check
python3 registry.py run --family memory
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.

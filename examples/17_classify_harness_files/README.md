# Classify real harness files

This example classifies four files and directories already present in the
Loop Engine repository. It shows why a Markdown file, a code package, saved
history, and a user writing guide do not belong in one generic memory bucket.

## Install

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

## Run it

From a repository checkout:

```bash
python examples/17_classify_harness_files/run.py
```

The import is deterministic. It does not call a model, use the network, or
change an active intelligence store.

## Expected result

The example places each source in one layer:

| Real source | Layer |
|---|---|
| `humanizer-context.md` | Context Intelligence |
| `src/loop_engine/` | Code Intelligence |
| one saved Run History under `docs/evidence/runs/` | Runtime History and Solution Intelligence |
| the writing rules in `humanizer-context.md` when explicitly typed as a user instruction | User Feedback Intelligence |

Every result remains a candidate. The raw source stays at its original path.
The candidate record carries a digest and a bounded preview.

Read [Import files and history from another harness](../../docs/components/intelligence-layers/EXTERNAL-HARNESS-IMPORTS.md).

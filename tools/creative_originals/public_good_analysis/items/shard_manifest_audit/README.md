# Audit of a sharded dataset against its manifest

Compare the shards a release manifest or shard index declares with the shards found (SHA-256 and row counts computed from their bytes): missing, unexpected, digest mismatches and row count mismatches, and whether the release is complete.

## What it does

The declared list is what a release promises; the observed list is what was found, with each file's SHA-256 and row count computed by whatever read the files. A declared path not observed is missing, an observed path not declared is unexpected, a path in both with another SHA-256 is a digest mismatch, and one whose row counts both sides state and disagree is a row count mismatch. A path passing both comparisons is matched, and the release is complete when nothing is missing, unexpected or mismatched.

## Run it

As a library:

```python
from shard_manifest_audit import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 shard_manifest_audit.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `declared` (array of object, required): the shards the index or manifest declares
- `observed` (array of object, required): the shards found, with the SHA-256 and rows computed from their bytes

## Output

- `complete` (boolean, required)
- `matched` (integer, required)
- `missing` (array of string, required): declared paths not observed
- `unexpected` (array of string, required): observed paths not declared
- `digest_mismatch` (array of object, required): declared and observed SHA-256
- `row_count_mismatch` (array of object, required): declared and observed rows

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_path`: one list names a path twice

## Checks

`examples/known_good.json` and the 4 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `shard_manifest_audit.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare measured review curriculum and measured response corpus (CC BY 4.0, Gemma 4 Good Hackathon), each released as dozens of JSON lines shards listed in a shard index with their digests.

Built for:

- [`taylorsamarel/duecare-measured-review-curriculum-200k`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k)
- [`taylorsamarel/duecare-measured-response-training-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)

Dataset shape: shard-index.json and release-manifest.json entries: path, sha256, rows.

No SDG goal is proposed. A data-integrity step with no SDG target of its own; it was built for the DueCare corpora, whose release files are listed with their SHA-256 in shard-index.json and release-manifest.json. The association is a proposal for reviewers, not a grant.

## Limits

The function compares the facts it is given; computing each found file's SHA-256 and row count is the caller's step. Paths compare exactly, so a renamed shard is one missing and one unexpected path. Row counts are compared only where both sides state one.

This item is a candidate component. Generating it did not approve or qualify it.

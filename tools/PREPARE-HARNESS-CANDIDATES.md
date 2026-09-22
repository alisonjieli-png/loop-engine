# Prepare offline harness skill candidates

`prepare_harness_candidates.py` turns authored proposals into a new candidate
folder. It reads only local, committed Loop Engine source files. It makes no
network or model call. It does not stage, approve, install, serve or publish an
item.

The source revision must equal `git rev-parse HEAD`. Every cited source and
the repository `LICENSE` file must have the same bytes in the checkout and at
that revision. The first version accepts only the root MIT licence record.
This is a byte and declaration check, not an independent rights review of
each source file or a check that the authored procedure is correct.

## Input

Write one UTF-8 JSON file with this shape. Replace the example revision and
digests with the exact values from `git rev-parse HEAD` and `sha256sum`.

```json
{
  "record_type": "harness_candidate_batch_proposals/v1",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "license": {
    "expression": "MIT",
    "path": "LICENSE",
    "sha256": "<64 lowercase hexadecimal characters>"
  },
  "sources": {
    "src/loop_engine/core/example.py": "<64 lowercase hexadecimal characters>"
  },
  "proposals": [
    {
      "id": "inspect_example_input",
      "title": "Inspect example input",
      "purpose": "Inspect example input before changing it. Use when its shape is unknown.",
      "body": "# Inspect example input\n\nDescribe the procedure and its checks here.\n",
      "sources": ["src/loop_engine/core/example.py"],
      "layer": "code",
      "family": "code_reference",
      "search_tags": ["input inspection"],
      "tags": {"language": ["en"]},
      "symbols": ["inspect_input"],
      "declared_effects": []
    }
  ]
}
```

The title must be the first Markdown heading. A proposal may cite several
declared sources. It cannot set its own lifecycle. The tool adds the candidate
lifecycle through the existing typed tag contract. Identity words use lower
case letters, digits and single underscores, with at most 64 characters. The
body has at most 12,000 characters, and a batch has at most 5,000 proposals.

## Prepare and inspect

```bash
PYTHONPATH=src python3 tools/prepare_harness_candidates.py \
  --repository . --proposals proposals.json --output candidate-batch-001 \
  --authorize-preparation

PYTHONPATH=src python3 -m unittest tools.test_prepare_harness_candidates -v
```

The output folder is created exclusively. An existing path is refused. It
contains `items.json`, `bodies/<identity>.md`, numbered specification files
with at most 50 rows each, and `preparation-report.json`. The items and
specifications use the current starter catalogue record versions. The
existing refresh reader and candidate compiler accept the generated files;
the test verifies this for a temporary 1,000-item fixture.

There is no review record or host release folder. A later producer-independent
review must check each item's meaning, licence, safety and usefulness against
its exact body digest. The existing host release builder is the only current
path from an approved item to a served body. A partial output left by a write
failure remains visible and cannot be overwritten by a retry. Use a new output
name after investigating the failure.

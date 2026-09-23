# Prepare offline harness candidates

`prepare_harness_candidates.py` turns authored proposals into a new candidate
folder. It reads authored payloads from the proposal document and verifies their
cited, committed Loop Engine source files. It makes no network or model call.
It does not stage, approve, install, serve or publish an item.

Version two of the proposal contract prepares complete original native packages.
Use it for instruction files, scripts, tools, contracts, plugins, commands,
hooks, configuration and binary supporting assets. It preserves their bytes and
relative folders. It does not turn each file into a separate library item.

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

## Complete native packages

`harness_candidate_batch_proposals/v2` keeps the same outer fields as version one.
Each proposal keeps `id`, `title`, `purpose`, `sources`, `layer`, `family`,
`search_tags` and `tags`. It removes `body` and requires all the following fields:

- `kind`: an existing harness item kind, normally `tool`, `skill` or
  `instruction_file`. A plugin is a `tool` package with native file roles; this
  does not create another runtime type or intelligence layer.
- `symbols`, `declared_effects`, `styles`, `dependencies`: explicit string lists,
  empty when none are declared. Dependencies are declarations, not installed or
  independently resolved requirements.
- `producer`: `producer_identity`, model `family` and a versioned
  `method_identity`, for example `codex_original_native_authoring/v1`.
- `files`: one to 64 records, each with `path`, `digest`, `size_bytes`,
  `media_type`, `role`, and `content_base64`. The content is strict base64 of the
  exact bytes. Paths, digests, bounds and roles use the existing
  `CataloguePackageFile` contract. Hidden native paths such as
  `.claude-plugin/plugin.json` are allowed; `.git`, traversal, symlinks,
  case collisions and file/directory collisions are refused.

The existing package bounds are 8 MiB per file and 32 MiB per package. The
proposal document remains bounded to 64 MiB, so smaller batches should be used
for larger packages. A declared executable role requires `spawns_process` in
the item effects, but still grants no permission to execute it. Roles and
effects are authored declarations; independent review must catch misleading
declarations and undeclared behavior. Known secret patterns are refused in
payload bytes, but this cannot detect every secret.

The [worked input shape](../artifacts/native-candidate-preparation-2026-09-23/proposal-contract-example.json)
uses placeholder source bindings. Replace the revision and digests with exact
values before running it. The root MIT licence and every cited grounding source
must still match the current committed revision. The producer declaration and
rights metadata remain pending independent review; they are not approval.

Output uses `starter_catalogue_candidate_items/v3` and
`candidate_intelligence_specifications/v3`. Each item has one canonical
`CataloguePackage` document in `bodies/<identity>.package.json` and its complete
tree under `packages/<identity>/`. The package document binds every file's bytes
and role. Exact duplicate package digests in a batch are refused even when the
proposed identity or title differs. Near duplicates still require the independent
review pipeline; this check is not a semantic novelty test.

The existing candidate staging tool accepts the population with an explicit
`--package-root` pointing to the prepared folder. It checks the complete file
inventory, bytes, canonical package document and source provenance again before
the existing atomic catalogue write. It stores candidate metadata and references
to that immutable tree; keep the prepared folder with the staging database.

```bash
PYTHONPATH=src python3 tools/stage_intelligence_candidates.py \
  --specifications candidate-batch-001/specifications-001.json \
  --package-root candidate-batch-001 \
  --database candidate-review-001.sqlite --namespace original.batch001 \
  --authorize-isolated-staging --export candidate-export-001.json \
  --report candidate-staging-001.json
```

Old readers refuse the new record version. The existing single-body reviewer
must be extended to review all package files, producer method and dependencies
before these native items can be admitted. A package manifest alone is not the
tool's contents. Preparation and staging do not generate review records or
publish the package. Concurrent hostile filesystem mutation and a native harness
loading the output are outside this preparer's qualification.

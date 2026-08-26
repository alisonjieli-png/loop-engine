# Code Intelligence templates

Code Intelligence describes software that a loop can select and use. The
search record is a small card. The runnable body may be a function, file,
package, repository, container, service, notebook, workflow, or large system.

The card and the body are separate. This is what makes large code practical.

## Built-in templates

| Template | Use |
|---|---|
| `pure_function` | One bounded callable with typed input, output, and tests. |
| `single_file_component` | One selected source file and entry point. |
| `multi_file_module` | A module manifest with several files and entry points. |
| `pypi_package` | A pinned Python distribution, imports, license, and dependency lock. |
| `github_repository` | A repository pinned to one commit with a manifest and named entry points. |
| `template_repository` | A parameterized repository template with variables, files, and validation. |
| `service_adapter` | A local or remote service behind request, response, effect, and authorization contracts. |
| `dataset_backed_system` | Code and datasets stored separately and joined by immutable references. |
| `large_framework` | A top-level manifest plus independently searchable subsystem cards. |
| `worker_system` | Preflight, execution, postflight, diagnostics, logging, and configuration loops. |
| `llm_harness` | A model harness with tool contracts, model policy, effects, and verification. |
| `command_line_tool` | A pinned command, arguments, environment, effects, and tests. |
| `core_plugin` | A manual registration function and complete capability handshake. |
| `agent_skill_bundle` | Context references, optional Code references, assets, triggers, permissions, and tests. |
| `workflow` | A multi-step manifest whose selected steps run as loops. |
| `notebook` | A pinned notebook, environment lock, inputs, outputs, effects, and tests. |

These templates are starting contracts. A project can create a custom
`CodeAssetSpec` when none fits.

## What a search card contains

A useful card identifies the software without copying its body into the index.

```text
stable asset ID and version
plain-language name and description
asset kind and source kind
immutable body locator and SHA-256 digest
body size, file count, and line count
named entry points
input and output contracts
allowed loop modes
effects and locality
dependencies and separate dataset references
load strategy
license and provenance
lifecycle and independent admission reference
keywords, symbols, blocking keys, and namespaced metadata
```

Normal search returns this card as a Code Intelligence `LoopRef`. Loading and
execution happen later.

## A function

A small pure function may resolve directly to a callable. It still runs inside
a component loop.

```python
from loop_engine.loop.loop_capsule import ExternalPayloadRef
from loop_engine.core.code_intelligence_assets import (
    code_asset_capsule,
    execute_code_ref,
    spec_from_template,
)

spec = spec_from_template(
    "pure_function",
    asset_id="code.invoice.normalize_currency",
    name="Normalize invoice currency",
    description="Convert an invoice amount using a supplied rate table.",
    source_kind="local_path",
    body_ref=ExternalPayloadRef(
        "file:///opt/company/invoice_tools.py",
        "a" * 64,
        size_bytes=18_400,
        media_type="text/x-python",
    ),
    entrypoints=("normalize_currency",),
    input_contract="invoice_and_rate_table/v1",
    output_contract="normalized_invoice/v1",
)

ref = code_asset_capsule(spec).to_ref(source="code_intelligence")
```

The example digest is a fixture. Production registration must use the digest
of the exact selected bytes.

## A PyPI package

Do not copy a whole package into a database row. Store:

```text
distribution name
exact version and package digest
license
dependency lock
supported Python and platform versions
selected imports or entry points
typed adapter contract
known failure conditions
verification results
```

The materialization loop installs or resolves the pinned distribution in an
approved environment. The component loop calls only the selected entry point.

## A GitHub or GitLab repository

Use a commit-pinned repository locator. Add one top-level card and smaller subsystem
cards.

```text
repository card
  commit and repository digest
  top-level manifest
  dependency lock
  license and provenance
  subsystem references

subsystem cards
  preflight
  execution
  postflight
  diagnostics
  logging
  configuration
```

Every subsystem card points to the same immutable repository body but keeps its
own entry points and contracts. A digest-keyed cache can check out the
repository once. Selecting diagnostics does not load every source file into
the model context or search result.

## A million-line system

Treat a large system as a referenced body plus a map, not one monolithic code
record.

1. Store a top-level locator, digest, manifest, dependency lock, and license.
2. Index body-free cards for packages, services, subsystems, public symbols,
   commands, schemas, tests, and operational roles.
3. Search cards first.
4. Select one subsystem `LoopRef`.
5. Materialize the shared body once into a digest-keyed cache.
6. Bind the selected entry point.
7. Run it as a component loop with its own contract and effects.

The card can stay below a few kilobytes even when the repository has forty
files or one million lines.

## Code with datasets or large assets

Datasets, weights, indexes, generated files, and test fixtures use separate
`ExternalPayloadRef` objects. Each reference carries a locator, digest, size,
media type, storage type, and immutability flag.

The code card contains only those references. A dataset mount or object-store
adapter loads the selected asset when the loop needs it. This supports local
files, object storage, databases, package resources, and future storage
adapters without placing large bodies in the catalog database.

`load_knowledge(..., content_mode="auto")` uses the same rule for large
Context files. The default threshold is 8 MB. It checks file size before text
decoding and emits a compact digest card for files at or above the threshold.

## Repository templates

A template repository should declare:

```text
template variables and types
required and optional files
conditional files
render order
expected output tree
validation commands
license and source version
upgrade and merge policy
secrets that must be supplied outside the template
```

Rendering the template is a loop. Validating the rendered project is another
loop. The original template remains unchanged.

## Tools and skills

A tool normally belongs in Code Intelligence because it executes. A skill
normally contributes Context Intelligence because it supplies instructions,
examples, decision rules, or question patterns.

Some published skills contain both. Store a skill bundle as a manifest that
references Context records and Code assets. Do not merge both bodies into a
new intelligence layer. Each selected Context or Code item still returns
through its own loop.

## Admission and safety

Registration is not proof that code is safe or useful. A registered
`CodeAssetSpec` requires an independent `admission_ref`. Loading must verify the
selected payload digest. Execution must declare effects such as file reads,
file writes, network access, secret reads, or subprocesses.

Untrusted repositories still need license review, dependency review,
sandboxing, tests, and an independent result check. The Code Intelligence
template records describe the boundary. They do not grant execution authority.

# Supply lines of executable library components

Kind: tool component. It serves the owner's direction of September 27, 2026:
"We need to increase our goal to 100K library components, and a diverse well
balanced library, not overweighted with skills.md, we should have more
functions, tools, programs, binaries, plugins, etc". The command is
[`tools/build_library_supply.py`](../build_library_supply.py).

The licensed import copies harness files that already exist in public
repositories, and that supply is mostly skills and instruction files. A
supply line instead writes new packages from licensed facts: a registry
entry, an API specification, a package formula or a data file. Every line is
deterministic and makes no model call. Every package is a review candidate in
the import store and is approved by nothing here.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A supply run is a Starting Practitioner task of the code execution profile
that an operator starts with the command above. It runs deterministically.
The fact readers, generators, static checks and the store writer are
adapters the run uses: none is a graph vertex, a role, a mode or a runtime
type, and choosing one grants no authority. Network reads need
`--authorize-network-reads`, and store writes need `--authorize-store-writes`.

## The lines

```text
Supply lines (each writes library_supply_candidate/v1 records)
├── mcp_registry: one protocol server connection per server of the official registry
│   ├── kind protocol_server_configuration, form mcp_server
│   ├── files for Claude Code, Codex, OpenCode and Cursor, written from the entry's facts
│   └── an upstream GitHub licence on the allowlist and an npm or PyPI version that is published
├── openapi_operations: one client function per operation of a licensed OpenAPI specification
│   └── kind code_module, form api_operation
├── program_installs: one install recipe and typed wrapper per command-line program
│   └── kind code_module, form binary_install
└── data_tables: one reference data table with its schema, loader and tests
    └── kind code_module, form data_table
```

## One package

```text
One supplied package (catalogue_package/v1)
├── generated files, each marked generated in the candidate's file list
├── upstream files copied byte for byte only where the licence allows it, marked upstream_verbatim
├── LICENSE (and UPSTREAM-LICENSE where the upstream licence governs copied facts)
└── ATTRIBUTION.md: the generator, its version and code revision, every fact source with its
    address, retrieval time, SHA-256 and licence, and every file's origin and digest
```

The candidate record carries the served harness kind, a declared
`component_form/v1` record (a line may declare only its own forms), the
declared effects with the rule behind each, credentials by environment
variable name only, the documented placements, the tests and their result,
and the evidence states: resolved and materialized are true, available,
loaded, used and verified are false.

## Where candidates live, and why

Candidates are written to the import store (`tools/licensed_import/storage.py`)
through the importer's own write path: bodies through `put_bodies`, records
through `apply` in atomic batches, candidate records built by
`candidate_store_record`. They live in their own namespace, `library.supply`,
because the review panel's imported profile reads only packages copied byte
for byte: its reader refuses a whole export when one package was generated,
so a generated package must never reach an export that reads `library.import`.
One state record per line lists the current version of every component; a
changed package supersedes its earlier version and a complete run withdraws
what it no longer supplies.

## Existing work: adopted, adapted and rejected

| Project | Decision and reason |
|---|---|
| core/library_ingestion `mcp_official_registry` engine, `render_connection`, `connection_builtin_rules`, `PackageResolver` idea | Adopted for the protocol server line: paging, status and latest-version rules, link-only provenance, the three harness files and their shape checks. Adapted: licence reads only for servers the line can package; Cursor's file added here. |
| tools/licensed_import storage, static checks, media types | Adopted: the store, the write path and the checks every imported package passes. |
| Official registry `server.json` | Adopted as the source of facts; its text is never copied (link mode). |

## Commands

```bash
PYTHONPATH=src:tools python tools/build_library_supply.py mcp-registry \
  --run-folder /home/username/baltor-library/supply/mcp-registry/DATE \
  --authorize-network-reads --authorize-store-writes --stars
```

Run folders hold every fetched fact and stay outside the repository. A run
refuses to store packages while the generator code has uncommitted changes,
so every stored package names a revision its generator can be read from.

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_supply_lines
```

## Limits

- No review profile for generated packages exists yet, so the export holds
  these candidates and counts them as `held_for_review_profile`.
- A protocol server's own effects are not declared by its registry entry.
  The package declares that the harness starts a process and downloads the
  pinned package, and says in its README that the server is third-party code.
- Nothing here was loaded by a harness.

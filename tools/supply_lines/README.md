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
│   ├── kind code_module, form api_operation; sources in openapi_sources.json
│   ├── the file at the branch's head commit, proven by git blob identity, licence text agreed
│   ├── the specification's own info.license (declared_licences.py): off the allowlist refuses the
│   │   specification; a second allowlisted licence travels beside the repository's
│   ├── directory mode (openapi_directory.py): every APIs.guru specification whose own declared licence,
│   │   declared licence file or origin repository licence is allowlisted, minus what a curated source
│   │   supplies, one package per host, method and path, in its own line state
│   ├── bodies: JSON (plain, a merge patch, another +json type, or any media type) and URL-encoded forms
│   │   by their declared style (deepObject brackets, exploded or comma lists); Swagger 2 is converted first
│   ├── a self-hosted API with no public HTTPS address gets a client that sends nothing until the caller
│   │   names one (base_url or the environment variable)
│   ├── discovery mode (google_discovery.py): Google's discovery documents from its Apache-2.0 client
│   │   repository, one version per API, resource names ({+name}) sent with their slashes
│   ├── a stdlib client with argument checks, the credential by variable name, ApiError, and
│   │   generated tests against a local mock that must pass before the package is kept; the
│   │   credential never follows a redirect, and a redirect to another origin is refused (tested
│   │   in every package with two local servers on different ports)
│   └── beside it (javascript_clients.py) an ES module with TypeScript declarations and node:test
│       tests repeating the Python ones, kept only when they pass
├── api_tool_servers: one Model Context Protocol tool server per curated OpenAPI specification file
│   ├── kind protocol_server_configuration, form mcp_server; the API line's sources, licence and refusals
│   ├── tools: the file's operations the API operation line builds (its maximum and duplicate rules, a
│   │   constructible example), each with a name of at most 64 characters, an input schema of the
│   │   client's own argument checks, and annotations from the method (read-only for GET, HEAD and
│   │   OPTIONS; destructive for DELETE, PUT and PATCH; idempotent but for POST and PATCH; open world)
│   ├── server.py: standard library only, newline-delimited JSON-RPC 2.0 over standard input and output
│   │   (protocol versions 2025-06-18, 2025-03-26 and 2024-11-05); the tool table is JSON data and one
│   │   request function sends with the generated client's helpers, copied from its template; tools.json
│   ├── test_server.py: the server started as a subprocess, every request sent to a local mock by a shim;
│   │   every tool is called once before the package is built and the whole file must pass to keep it,
│   │   a redirect from the mock to a second mock on another port among its known-wrong cases
│   ├── files for Claude Code, Codex, OpenCode and Cursor that start python3 with the server and pass the
│   │   credential variable by name, by the registry line's template
│   └── its own line state; prose the publication checks would refuse is replaced by the tool's request,
│       and a server above the review bound keeps shorter descriptions, then the first tools that fit
├── program_installs: one install recipe and typed wrapper per command-line program
│   ├── kind code_module, form binary_install; programs in program_sources.json
│   └── Homebrew bottles and source archive by published SHA-256, release assets by GitHub's
│       published digests; no binary re-hosted; a smoke test skipped when not installed
├── data_tables: one reference data table with its schema, loader and tests
│   ├── kind code_module, form data_table; tables in data_table_sources.json (JSON shapes, and CSV
│   │   or TSV files keyed by a field or by their row number)
│   └── the upstream file byte for byte, its licence text beside it, a loader that refuses a
│       changed file or a row that breaks the schema
├── publisher_tables: one data table per series, table or chart a publisher serves at its own address
│   ├── kind code_module, form data_table; collections in publisher_table_sources.json; the table half
│   │   (shapes, schema, loader, tests) is data_tables.py's, the fact half is publisher_tables.py's
│   ├── facts: the exact bytes at an HTTPS address on the collection's declared hosts (an archive member
│   │   the declaration names), their SHA-256 and retrieval time; GitHub is never read
│   ├── licence bound to the exact series, release or chart with its evidence address: a World Development
│   │   Indicators series by its own metadata's License_Type ("CC BY-4.0" alone maps, to CC-BY-4.0; SIPRI
│   │   terms and CC BY 3.0 IGO refuse the series by name); the O*NET 31.0 Database by its licence page and
│   │   the release's own Read Me together; an Our World in Data chart by its own page's licence statement
│   │   and every origin of every indicator stating CC BY 4.0 in that indicator's metadata; the legal code
│   │   from creativecommons.org as UPSTREAM-LICENSE
│   ├── one package per series, table or chart, never per country or year; the job key is the publisher
│   │   and the series (schema.json), so a series retrieved again is the same job; a chart that only
│   │   republishes World Development Indicators series is refused as a duplicate (covered_by)
│   ├── SDG goals by a rule that is data (wdi_sdg_goals.json: the longest code prefix, else the series'
│   │   topic, each with its reason; O*NET: goals 4 and 8 for the release; Our World in Data: the
│   │   publisher's own SDG Tracker pages that list the chart), in the candidate's repository record and
│   │   in the run's sdg-goals.json; proposals for reviewers, nothing granted
│   ├── held, never read: the UN SDG Global Database (UNdata's terms are not an allowlisted licence) and
│   │   FAOSTAT (its manifest names no licence per dataset)
│   └── a data file above the 256 KiB file bound kept as parts cut at record ends that join to the exact
│       bytes; a table whose package would pass the 2 MiB bound refused as table_above_review_bound
├── function_extracts: one documented function of a permissive library with exactly the code it needs
│   ├── kind code_module, form function; libraries in function_sources.json; generator 1.2.0; a
│   │   library row that says withheld, with the measured reason, is declared and not read
│   ├── the function and its closure copied whole statement by statement across the package's own
│   │   modules, names only annotations read among them; standard library imports written as imports;
│   │   any other dependency refuses it
│   ├── refused by name as well: a module's own test or demonstration, a docstring without words, a
│   │   copied module that states a licence other than the repository's
│   ├── effects read from the syntax tree of the code and of its docstring examples, never from words
│   └── its docstring examples run as doctests, and the same function raising NotImplementedError
│       under its own docstring must fail them
└── json_schemas: one JSON Schema with schema_check.py (a small validator) and tests
    ├── kind contract_schema, form schema
    ├── SchemaStore mode (json_schemas.py): the latest version of each schema family with the
    │   repository's own valid and invalid examples beside it
    ├── curated mode (json_schemas.py, generate_curated): each schema json_schema_sources.json declares
    │   (open standards: STAC extensions, GBFS, Frictionless, World Bank, NASA CMR and others), copied byte
    │   for byte with the repository's own examples, or else generated instances and known-wrong values;
    │   a reference to a sibling file or another address refuses it by name; its own line state
    └── API component mode (api_schemas.py): every named object of a curated OpenAPI specification,
        with the specification's example, generated instances and known-wrong values
└── manim_scenes: one tested animation scene per example scene of Manim Community's documentation
    ├── kind code_module, form code_example; ManimCommunity/manim at a pinned release tag (MIT, both
    │   licence files carried), read as one archive at the tag's commit, every file proven by blob identity
    ├── every `.. manim::` directive outside literal blocks, in the library's docstrings and pages: the
    │   scene's code as the documentation's directive runs it, one package per scene (never per quality
    │   or output format), the same code at two locations kept once
    ├── LaTeX scenes refused by name while no LaTeX is installed; a name nothing binds, a missing file or
    │   module, a failure or a timeout refused by name
    └── a test that renders every frame at low quality with nothing written, run in bubblewrap with the
        network closed by an interpreter that has Manim; the scene's construct raising must fail it
```

Beside the lines, `verbatim_code_sources.json` and
`verbatim_code_sources_2.json` declare MIT code repositories for the licensed
import itself (`--sources`): those modules are byte-for-byte copies in
`library.import`, which the imported review profile reads today.

## One package

```text
One supplied package (catalogue_package/v1)
├── generated files, each marked generated in the candidate's file list
├── upstream files copied byte for byte only where the licence allows it, marked upstream_verbatim
├── LICENSE (and UPSTREAM-LICENSE where the upstream licence governs copied facts)
├── UPSTREAM-NOTICE: the NOTICE file of each repository the package is derived from, when
│   that repository has one, copied verbatim (Apache-2.0 section 4(d) asks a derivative work
│   to carry those attribution notices); listed under licence.notices, never as a licence text
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
| OpenAPI generators (openapi-generator, openapi-python-client) | Rejected as engines here: they write whole client libraries with runtime dependencies, not one self-contained function per operation that a reviewer reads in one file. The line keeps the standard's own rules (local references, security schemes, servers). |
| Homebrew formula JSON and analytics (formulae.brew.sh) | Adopted as facts: versions, licences, bottles and source archives with their SHA-256, install counts. homebrew-core's BSD-2-Clause text travels with each recipe. |
| GitHub release asset digests (GraphQL `digest`) | Adopted: GitHub publishes a SHA-256 per asset; assets without one are left out. |
| Manim Community's `manim_directive.py` (the documentation's own runner) | Adopted for the scene line: a scene's code is exactly what the directive executes (`from manim import *`, then the content, doctest prompts removed its way). Not adopted: its shared `globals()`, which let a later example use a name an earlier one or the directive module bound; such a scene is refused as `name_unresolved`. |
| Manim's own renderer (`tempconfig`, `dry_run`) | Adopted as the test engine: every frame is computed at low quality and nothing is written, so a test checks the scene runs without producing video files. Rendering the documented output (`manim render -s` or a video) stays the README's command. |
| MCP generators from OpenAPI (Stainless, openapi-mcp-generator, FastMCP's OpenAPI provider) and the official MCP Python SDK | Rejected as engines for the tool server line: each writes a server with runtime dependencies (an SDK, an HTTP client, a web framework), and Stainless is winding its generator down. The line keeps the protocol's own rules (newline-delimited JSON-RPC over standard input and output, version negotiation, tool annotations) in one standard-library module, and reuses the API operation line's operations, licence decisions and client helpers. The SDK's client is used to check the servers by hand. |
| Redirect handling of CPython's urllib.request, requests, urllib3 and fetch (Node's undici) | Adapted for the API clients and tool servers (October 5, 2026): urllib's own unredirected headers carry the credential, and a subclass of its redirect handler refuses another origin, as the repository's own tools already refuse redirects (core/custom_endpoint.py, the knowledge radar's check_service_status). Rejected as they stand: urllib copies every header but Content-Length and Content-Type to any host; on a change of host requests strips Authorization (and rebuilds cookies), urllib3 Authorization, Cookie and Proxy-Authorization, and fetch Authorization and Cookie, so a custom credential header such as X-Api-Key, and a query credential, travel on with each of them. |

## Commands

```bash
PYTHONPATH=src:tools python tools/build_library_supply.py mcp-registry \
  --run-folder /home/username/baltor-library/supply/mcp-registry/DATE \
  --authorize-network-reads --authorize-store-writes --stars
PYTHONPATH=src:tools python tools/build_library_supply.py openapi \
  --run-folder /home/username/baltor-library/supply/openapi-operations/DATE \
  --authorize-network-reads --authorize-store-writes --stars [--source ID]
PYTHONPATH=src:tools python tools/build_library_supply.py programs \
  --run-folder /home/username/baltor-library/supply/program-installs/DATE \
  --authorize-network-reads --authorize-store-writes [--formula NAME]
PYTHONPATH=src:tools python tools/build_library_supply.py data-tables \
  --run-folder /home/username/baltor-library/supply/data-tables/DATE \
  --authorize-network-reads --authorize-store-writes [--table ID]
PYTHONPATH=src:tools python tools/build_library_supply.py publisher-tables --collection world_bank_wdi \
  --run-folder /home/username/baltor-library/supply/publisher-tables/DATE \
  --authorize-network-reads --authorize-store-writes [--series CODE] [--maximum-series N]
  # --collection onet_database (--series names a table) or our_world_in_data (--series names a chart)
PYTHONPATH=src:tools python tools/build_library_supply.py curated-schemas \
  --run-folder /home/username/baltor-library/supply/json-schemas/DATE \
  --authorize-network-reads --authorize-store-writes [--source ID]
PYTHONPATH=src:tools python tools/build_library_supply.py manim-scenes \
  --run-folder /home/username/baltor-library/supply/manim-scenes/DATE \
  --authorize-network-reads --authorize-store-writes \
  --manim-python /path/to/an/environment/with/manim/bin/python [--scene NAME] [--workers 3]
PYTHONPATH=src:tools python tools/build_library_supply.py api-tool-servers \
  --run-folder /home/username/baltor-library/supply/api-tool-servers/DATE \
  --authorize-network-reads --authorize-store-writes --stars [--source ID]
PYTHONPATH=src:tools python tools/build_library_supply.py report \
  --library-bundle /home/username/baltor-bundles/RELEASE --output REPORT.json [--admission-folder ADMISSION]
```

Run folders hold every fetched fact and stay outside the repository. A run
refuses to store packages while the generators' own code has uncommitted
changes, so every stored package names a revision its generator can be read
from. `--materialize` also writes every package under the run folder for
inspection. A run limited to some sources (`--source`, `--formula`,
`--table`) is not complete, so it withdraws nothing.

The report counts the served library and the import store's supply by
composition family and form, and projects the composition mix slot by slot
with the export's per-repository ceiling; see
`docs/research/LIBRARY-SUPPLY-LINES-2026-09-27.md` for the first report. A
candidate whose exact package the bundle serves, or an approved row of an
admission folder given with `--admission-folder` names, is counted as
`already_served` or `already_admitted` and not as supply, although the store
keeps it a candidate.

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_supply_lines
```

## Generator 1.2.0 of function_extracts

The sampled review of September 30, 2026 withheld
`function_extracts/1.1.0@8ebc4a99e5a6` with 21 of its 58 sampled packages
defective (the tolerance is 5 percent), so the decision ledger refuses to
sample version 1.1.0 into acceptance again. Each of the 21 packages was read
from the import store and each reviewer finding from the review ledger, and
every factual claim was checked by running the extracted code. The primary
root causes:

| Root cause | Packages | Of 21 |
|---|---|---|
| Generator defect | `decorator` (NLTK's copy of Michele Simionato's BSD decorator module, labelled Apache-2.0 without its notice); `predecessor`, `is_json`, `inverse` (names only annotations read left unbound); `update_header` (file effects it does not have); `validate` (another function's parameter list as its only text); `encrypt` (an example as its description, and test counts that disagreed); `test_rabin_karp`, `test_motion` (a module's own tests packaged as jobs) | 9 |
| Source library | `first_molar_mass` (returns the exception), `find_unit_clauses` (ignores its model argument), `secant_method` (bound to one equation), `find_median` (wrong for an unsorted list), `simplify_kmap` (lists minterms and does not simplify), `calculate_pi` (names the wrong algorithm), `rank_of_matrix` (wrong for 340 of 3,000 random matrices, and changes its input), `perfect_cube` (wrong for 97 of the first 100 cubes), `is_valid_email_address` (accepts a domain that ends in a hyphen), `chose_rws` (never selects past `population_size`) | 10 |
| Reviewer error | `quantile` (the `start - 1` the reviewer called a bug is guarded, and every interval of 201 arrays answers correctly); `standardization` (`statistics.stdev` refusing a single value is its documented behaviour, and `round` is exact) | 2 |

Besides its primary cause, 10 of the 21 packages declared a file effect they
do not have (5 rejections cite it), and 15 had a README that misdescribed the
function. All 10 source-library defects come from TheAlgorithms/Python.

What 1.2.0 changes, each with a known-wrong control in
`tools/test_supply_lines.py` that fails on 1.1.0, measured on the cached
sources of the September 28 and October 1 runs (read offline on October 5:
1.1.0 writes 3,067 packages from them and 1.2.0 writes 2,795):

- Effects come from the syntax tree of the code and of its docstring
  examples. 1.1.0 read the module's words with the instruction-file rules:
  868 of its packages declared a file effect and none holds a file call.
  1.2.0 declares one, for `load_chemical_preferences`, which reads files.
- The README holds the whole signature (1.1.0 cut 301 at their first line),
  the docstring's own description (498 summaries held examples), shortened
  only between sentences or words, and test counts as doctest counts them.
- Names only annotations read are bound. `typing.get_type_hints` failed for
  312 of 1.1.0's packages and fails for 19 of 1.2.0's, each a name the
  upstream binds only under `TYPE_CHECKING`, as in the upstream module.
- New named refusals: `not_a_reusable_job` (11 of 1.1.0's packages),
  `no_description` (232) and `module_licence_differs` (17), with their
  measured rules beside the constants in `function_extracts.py`.

A dry run of 1.2.0 on October 5, 2026 over the three libraries the defective
samples came from (TheAlgorithms/Python at `35ccb2c`, pydash, NLTK) wrote
1,349 packages where 1.1.0 writes 1,599 from the same commits. Of the 21
defective samples, 3 are fixed (`predecessor`, `is_json`, `update_header`),
8 are refused by the new rules, the 2 wrongly rejected are written as before,
and 8 are still defective: each is TheAlgorithms' own code. Of the 51 sampled
TheAlgorithms packages, 1.2.0 still writes 42, and 8 of those are these
defects, 19 percent against the 5 percent tolerance. No generator rule can
see a wrong algorithm that passes its own examples, so `function_sources.json`
withholds TheAlgorithms/Python: the row keeps its curated modules and states
the measured reason, and the line refuses it as `source_withheld` without
reading it.

keon/algorithms, the largest other collection of teaching implementations
(434 of the 2,795 packages 1.2.0 writes from the cached sources), was never
sampled. Of 24 of its functions drawn at random, read by hand and run against
references, 2 break their own documented contract (`pacific_atlantic` fails
on every matrix that is not square; `longest_increasing_subsequence_optimized`
is wrong for negative numbers), so its row is withheld too: the first 1.2.0
batch is sampled with acceptance number 0, and this rate alone would make a
clean sample unlikely. The smaller teaching collections (aima-python,
simplestatistics, al-go-rithms, about 90 packages) stay; their rate is not
measured.

## Limits

- The daily licensed-import export has no review profile for generated
  packages, so it holds these candidates and counts them as
  `held_for_review_profile`. Generated packages reach the library by their
  own route: deterministic qualification of every package, one calibrated
  sampled review by a model family that did not write the generators,
  Community admission of accepted batches, and a decision ledger that records
  every batch decision ([component qualification](../component_qualification/README.md),
  command `tools/qualify_generated_components.py`). That route admitted 3,910
  `program_installs` packages on September 29, 2026, served since app release
  51. Admission does not change a stored candidate's lifecycle; the export and
  the report leave out a candidate whose exact package the served bundle or an
  approved row of an admission folder names, as described above.
- A protocol server's own effects are not declared by its registry entry.
  The package declares that the harness starts a process and downloads the
  pinned package, and says in its README that the server is third-party code.
- API clients are Python only, and no specification of the first eight
  declares pagination, so no client pages through results.
- Redirects, a defect found on October 5, 2026: urllib copies every request
  header but Content-Length and Content-Type to whatever host a redirect
  names, so every API client up to generator 1.7.0 (directory mode 1.2.0,
  discovery mode 1.1.0) and every tool server of 1.0.0 sent its credential
  header to any host a hostile or compromised API redirected to. Their
  JavaScript modules let fetch follow, which drops Authorization on the way to
  another origin but keeps a custom header such as X-Api-Key and a query
  credential. From API operations 1.8.0 (directory 1.3.0, discovery 1.2.0)
  and tool servers 1.1.0 the credential is an unredirected header (in
  JavaScript, dropped before a redirect is followed), a redirect is followed
  only within the API's origin (scheme, host and port), and one to another
  origin ends in `ApiError` naming that origin (a tool error in a server)
  before anything is sent there. Every generated test file proves it with
  two local servers on different ports, so the generated tests now reach the
  loopback interface; nothing else (`run_tests` closes every other host to
  urllib, the server tests' shim likewise, and the JavaScript tests close
  fetch but for that test). Packages stored by the earlier versions are
  superseded when the lines run again. Remaining limit: an API that
  redirects within its origin to an address that needs the credential gets
  that request without it and answers with its own refusal.
- A tool server is one process per harness; it answers up to four tool calls at
  once, gives no structured output schema, and returns one page of each answer.
  Its connection files start it from the project root (`tools/<key>/server.py`);
  a harness that starts servers elsewhere needs the absolute path.
- Program recipes cover macOS and Linux through Homebrew; no Windows recipe.
- Scenes render only in an interpreter that has Manim. On Linux, `pip install manim` needs the Cairo and
  Pango development files, because pycairo and ManimPango publish no Linux wheels; conda-forge's pycairo
  and manimpango builds with `pip install manim` on top work without them (PyAV's wheel brings FFmpeg).
  The component qualification sandbox runs `/usr/bin/python3` with no Manim, so these candidates fail its
  sandbox until it has a declared Manim runtime.
- Scenes that typeset with LaTeX (`MathTex`, `Tex` and the classes built on them) are refused while no
  LaTeX is installed; Typst scenes need the `typst` extra (`manim[typst]`), which their requirements name.
- Nothing here was loaded by a harness.

### Publisher tables, measured in the October 5, 2026 dry runs

Dry runs with `--materialize` and no store write; the run folders are under
`/home/username/baltor-library/supply/publisher-tables/2026-10-05-*`.

- World Development Indicators: 1,483 of the catalogue's 1,498 series kept,
  104 of them in two parts. Refused: 9 by their own `License_Type` (6 under
  SIPRI terms, 3 under CC BY 3.0 IGO); 4 Worldwide Governance Indicators
  scores and estimates whose download repeats every economy, so the key
  cannot be unique; 2 that the World Bank serves only from its Health
  Nutrition and Population database. Reading every series' metadata and
  download took 2,989 requests in 53 minutes at one a second (the World
  Bank publishes no numeric rate). Values stay text as published; regional
  and income-group aggregates are rows beside economies, and the World
  Bank's country metadata (region, income group) is not packaged.
- Proposed goals of the kept series: 1: 45, 2: 57, 3: 139, 4: 169, 5: 21,
  6: 32, 7: 32, 8: 410, 9: 73, 10: 65, 11: 30, 12: 33, 13: 59, 14: 6,
  15: 26, 16: 28, 17: 354; 67 series (population by age and sex, armed
  forces) have no goal of their own.
- O*NET 31.0 Database: 32 of 45 tables kept (goals 4 and 8). The 13 whose
  package would pass 2 MiB are refused, not sampled or split across
  packages: Abilities, Job Titles, Knowledge, Occupation Level Metadata,
  Software Skills, Specific Interest Areas, Task Ratings, Task Statements,
  Training and Experience, Transferable Skills, Work Activities, Work
  Context and Work Styles. The release is one 13 MB archive, byte for byte
  the copy in `/home/username/loop-engine-data/onet/31.0`.
- Our World in Data: 18 of the 499 charts its 17 SDG Tracker pages list are
  kept, covering 11 goals. 274 are refused by licence: 198 name an origin
  "(c) United Nations", and the rest CC BY 3.0 IGO, CC BY-NC-SA, CC0, a
  copyright notice or an indicator the publisher marks non-redistributable.
  90 more are refused because the chart's page carries only the site footer,
  not the chart's own licence statement, 55 as republished World
  Development Indicators series, 11 for an origin with no licence, and 51
  are unreadable (44 slugs redirect and the reader follows no redirect; 7
  charts name no indicator). Because of those redirects no Our World in
  Data run is complete, so none withdraws anything. CC0 origins are refused
  until the CC0 legal code travels beside the data.
- Held, never read: the UN SDG Global Database (UNdata's terms are not an
  allowlisted licence) and FAOSTAT (no licence named per dataset); see
  `held` in `publisher_table_sources.json`.
- The goals are proposals in the candidate's repository record and the
  run's `sdg-goals.json`; no PublicGoodGrant is written here.

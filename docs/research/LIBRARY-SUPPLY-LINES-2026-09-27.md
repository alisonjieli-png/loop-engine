# Library supply lines and composition, September 27, 2026

Kind: research record. It reports what was built, read and measured on
September 27, 2026 to grow the library toward the owner's new goal, and the
composition the library can reach with the supply that exists. It approves
nothing: every package it counts is a review candidate.

## The owner's direction

The owner, September 27, 2026: "We need to increase our goal to 100K library
components, and a diverse well balanced library, not overweighted with
skills.md, we should have more functions, tools, programs, binaries, plugins,
etc".

## Where the library stood

The served release `daily-2026-09-27-16` held 13,643 packages. They are
counted by composition family here, with the harness kind derived the way
the library page derives it and the component form (`component_form/v1`)
derived from that kind, the file roles and the native format.

| Family | Packages | Share | Target at 100,000 | Bound |
|---|---:|---:|---:|---|
| Executable code | 15 | 0.1% | 35% | target |
| Protocol servers, plugins, marketplaces and hooks | 1,975 | 14.5% | 20% | target |
| Skills | 5,723 | 41.9% | 20% | cap |
| Subagents and commands | 3,909 | 28.7% | 10% | target |
| Instruction files and rules | 1,920 | 14.1% | 8% | cap |
| Data tables, contracts, schemas and settings | 101 | 0.7% | 7% | target |

The import store held 58,205 imported candidates that were not yet exported
and that the imported review profile can read. They were mostly skills
(32,772) and subagents or commands (12,622), with 11 executable modules. A
mix of kind shares cannot balance the library from that supply: new supply
was needed.

## What was built

```text
Library supply, September 27, 2026
├── composition targets: src/loop_engine/data/library_composition.json
│   ├── six families of component forms with target shares and two caps
│   └── the export's composition mix, with supply-aware shares and a library-level cap
├── component_form/v1: a served choice attribute beside the harness kind
└── supply lines (tools/supply_lines), each generating packages from pinned licensed facts
    ├── mcp_registry: protocol server connections from the official registry
    ├── openapi_operations: one client function per operation of licensed specifications
    ├── program_installs: install recipes with published checksums and typed wrappers
    ├── data_tables: licensed reference tables with schema, loader and tests
    └── verbatim code modules: MIT algorithm repositories through the licensed import
```

The component guides are [the supply lines README](../../tools/supply_lines/README.md)
and [the licensed import README](../../tools/licensed_import/README.md).

## The new supply

| Line | Source read | Candidates stored | Refused | Form | Package licence |
|---|---|---:|---:|---|---|
| Protocol servers | 36,672 registry entries, a complete pass | 5,592 | 31,080 | `mcp_server` | MIT |
| API operations | 6 specifications, 19 files | 1,339 | 52 | `api_operation` | MIT (1,050), MIT AND Apache-2.0 (289) |
| Program install recipes | 200 declared programs | 189 | 11 | `binary_install` | MIT AND BSD-2-Clause |
| Reference data tables | 46 declared tables | 46 | 0 | `data_table` | MIT (37), CC0-1.0 AND MIT (7), Unlicense AND MIT (2) |
| Verbatim code modules | 6 declared MIT repositories | 2,459 | 0 | `library_module` | MIT |

The generated candidates (7,166) are stored in the import store's
`library.supply` namespace. The verbatim code modules are byte-for-byte
copies, stored by the licensed import in `library.import`, where the imported
review profile reads them today.

### Protocol servers

Refusals by reason, of 36,672 registry entries:

| Reason | Entries |
|---|---:|
| `remote_only_server` (no npm or PyPI package to pin) | 20,599 |
| `licence_unknown` | 4,909 |
| `no_npm_or_pypi_package` (container or other registries) | 2,127 |
| `upstream_repository_unreadable` | 1,612 |
| `upstream_repository_not_on_github` | 710 |
| `registry_status_not_active` | 391 |
| `licence_not_on_allowlist` | 232 |
| `licence_signals_disagree` | 222 |
| `duplicate_package` | 141 |
| `required_arguments_not_rendered` | 83 |
| `package_licence_not_on_allowlist` | 25 |
| `package_version_not_published` | 20 |
| other (invalid files, unrendered package types, unknown version) | 9 |

Part of `licence_unknown` is the run's ceiling of 8,000 upstream licence
lookups: entries beyond it were not looked up. A second run with a higher
ceiling would decide more of them. Every kept package pins the exact npm or
PyPI version, carries files for Claude Code, Codex, OpenCode and Cursor, and
names its credentials by environment variable only; 2,420 of them read a
secret input.

### API operations

| Specification | Repository | Licence | Operations packaged | Refused |
|---|---|---|---:|---:|
| Resend | `resend/resend-openapi` | MIT | 112 | 1 |
| Discord | `discord/discord-api-spec` | MIT | 243 | 3 |
| OpenAI | `openai/openai-openapi` | MIT | 341 | 11 |
| Box | `box/box-openapi` | Apache-2.0 | 289 | 8 |
| Twilio SendGrid (14 files) | `twilio/sendgrid-oai` | MIT | 141 | 7 |
| Xero accounting | `XeroAPI/Xero-OpenAPI` | MIT | 213 | 22 |

The refusals: 43 request bodies that are not JSON (file uploads), 5 repeated
operation names, 3 parameters the client cannot send (a required cookie or a
query object) and 1 package that a static check blocked. The first run
refused 77 more: path keys that carry a fragment or a fixed query, and
schemas above the review bound. Generator version 1.1.0 sends those path keys
correctly and compacts large schemas, and its generated tests pass for every
one of the 1,339 packages. None of the six specifications declares a
pagination extension, so no client pages through results; each README says
so.

### Program install recipes

189 of 200 declared programs were packaged. Seven were refused for their
licence (EUPL-1.2 twice, GPL-3.0-or-later, the Ruby licence, and three mixed
expressions with a non-allowlisted part), two formulae were not found and two
are deprecated or disabled. Each recipe names, per platform, the Homebrew
command and the bottle's published SHA-256, the source archive and, where the
latest release matches the version, the GitHub release assets with their
published digests. No binary was downloaded or re-hosted. The smoke tests ran
for the 15 programs installed on the generating machine and were skipped for
the other 174.

### Reference data tables

All 46 declared tables were packaged: country, currency, language, locale,
continent and top-level domain tables, time zones, MIME types, HTTP status
codes, file extension tables, HTML tags, Node.js modules, ISO 639 languages,
CSS units, types, at-rules, selectors, functions and syntaxes, Web API
inheritance and 13 country fact tables. Two declarations were corrected
after the first trial: the time zone table repeats a value, so it is keyed
by its unique text, and one country file is a mapping, not a list.

### Verbatim code modules

The licensed import read the six repositories of
`tools/supply_lines/verbatim_code_sources.json` at their head commits, one
module per package with the tests that name it:

| Repository | Modules | Language |
|---|---:|---|
| `TheAlgorithms/Python` | 1,127 | Python |
| `TheAlgorithms/Rust` | 394 | Rust |
| `keon/algorithms` | 382 | Python |
| `TheAlgorithms/Go` | 272 | Go |
| `trekhleb/javascript-algorithms` | 181 | JavaScript |
| `TheAlgorithms/TypeScript` | 105 | TypeScript |

The licence gate copied every file, the static checks blocked none, and two
modules merged as duplicates, so 2,459 were written. Project Euler solutions
and web scrapers were left out by the declaration.

## Supply by family, not yet exported

| Family | Imported, reviewable today | Generated, held for a review profile |
|---|---:|---:|
| Executable code | 2,470 | 1,528 |
| Protocol servers, plugins, marketplaces and hooks | 6,726 | 5,592 |
| Skills | 32,772 | 0 |
| Subagents and commands | 12,622 | 0 |
| Instruction files and rules | 5,398 | 0 |
| Data tables, contracts, schemas and settings | 676 | 46 |

## Projected composition

The projection runs the composition mix slot after slot: 2,000 packages a
slot, supply-aware shares, the library-level cap on skills and on
instruction files and rules, and no refill. Every family is approved at
0.754, the share of 14,000 exported packages that seven daily slots approved
(10,557). No new supply arrives in it.

| Scenario | 25,000 reached after | Families at 25,000 | Where it stops |
|---|---|---|---|
| Imported only (today's review path) | 51 slots | subagents and commands 31.0%, connectors 28.2%, skills 22.9%, instructions 8.0%, executable 7.5%, data 2.4% | 27,427: executable, connector and data supply run out |
| With a review profile for generated packages | 21 slots | connectors 31.5%, subagents and commands 23.4%, skills 22.6%, executable 12.0%, instructions 8.0%, data 2.6% | 34,607: executable, connector and data supply run out |

Before the verbatim code modules were stored, the same projection needed
138 slots (imported only) and 27 slots (with generated packages) to reach
25,000, with executable code at 0.1 and 4.7 percent.

Neither scenario reaches 50,000 or 100,000 with the supply on hand. Skills
stay above 20 percent at 25,000 only because the library already held 5,723
of them: the cap lets no skill in until the library passes 28,615.

Target families fill toward their goal counts, so the 25,000 milestone is
heavy in subagents and commands (imported only) or in connectors (with the
generated supply). Holding every family at its target share of the current
library would stop the library's growth until executable and data supply
arrives, because the families over their share could add nothing and the
families under it have almost no supply. That choice is left to the owner: a
maximum share per family would be one more field of the targets record.

## Needs and gaps

Candidates needed at the 0.754 approval share, against the supply on hand
(imported and generated together):

| Family | At 25,000 | At 50,000 | At 100,000 | Supply | Gap at 100,000 |
|---|---:|---:|---:|---:|---:|
| Executable code | 11,584 | 23,187 | 46,394 | 3,998 | 42,396 |
| Protocol servers, plugins, marketplaces and hooks | 4,012 | 10,642 | 23,903 | 12,318 | 11,585 |
| Skills | 0 | 5,672 | 18,933 | 32,772 | 0 |
| Subagents and commands | 0 | 1,447 | 8,078 | 12,622 | 0 |
| Instruction files and rules | 107 | 2,759 | 8,063 | 5,398 | 2,665 |
| Data tables, contracts, schemas and settings | 2,187 | 4,508 | 9,149 | 722 | 8,427 |

The remaining gaps, largest first:

- Executable code. The generated lines hold 1,528 packages and need a review
  profile; the 2,459 verbatim algorithm modules are the first executable
  supply the imported profile reads today. About 42,400 more candidates are
  needed at 100,000.
- A review profile for generated packages. Without it, 7,166 generated
  candidates wait (see the proposal below).
- Plugins beyond GitHub repositories: extension marketplaces (the Gemini CLI
  gallery, VS Code extensions under an allowlisted licence) and npm packages
  that declare themselves as harness plugins.
- Data and contracts: about 8,400 more. Larger licensed datasets (Our World in
  Data and FiveThirtyEight data under CC-BY-4.0, MDN browser compatibility data
  under CC0-1.0 split by feature group) and evaluation sets.
- WebAssembly components and compiled binaries beyond Homebrew: WASI
  component registries, and Windows recipes (winget or Scoop manifests under an
  allowlisted licence). Every program recipe today covers macOS and Linux only.
- TypeScript clients beside the Python ones: Node 22 can run the tests with
  its type stripping, so the generator could be tested the same way.

Sources that would close the executable gap fastest:

| Source | Licence | Reachable operations or modules | What the line needs first |
|---|---|---|---|
| `Azure/azure-rest-api-specs` | MIT | tens of thousands of operations | Swagger 2.0 reading (refused today as `specification_version_unsupported`) |
| `aws/api-models-aws` | Apache-2.0 | about 15,000 operations | a Smithy model reader |
| `github/rest-api-description` | MIT | about 1,100 operations | none |
| `stripe/openapi` | MIT | about 600 operations | none |
| `twilio/twilio-oai` | MIT | about 1,000 operations | none |
| `cloudflare/api-schemas` | BSD-3-Clause | about 1,600 operations | none |
| more MIT, BSD and Apache code repositories | as declared | thousands of modules | a declaration per repository |

## A review profile for generated packages

The panel reads two profiles today. The imported profile's reader refuses a
whole export when one package was not copied byte for byte, and its criteria
state that meaning. The original profile expects assistant-authored packages
bound to sources in this repository. A supply line's package is neither: a
deterministic generator wrote it from pinned licensed facts. The criteria
and the reviewer instructions affect the review prompt, so this record only
proposes the profile.

```text
generated_from_licensed_facts/v1 (proposed)
├── reader: library_supply_candidate/v1 fields read strictly; each fact source pinned by address,
│   time and SHA-256; each file marked generated, upstream_verbatim, licence_text or attribution;
│   licence texts and ATTRIBUTION.md present; the generator named by identity, version and revision
├── producer: the generator, a family no reviewing model belongs to
└── criteria, beside the executable-code criterion
    ├── read every generated line; the code does only what its README says
    ├── the facts bind the package: the operation, server, formula or table it names is the one in
    │   the pinned source
    ├── declared effects cover every operation; credentials are named, never valued
    └── the generated tests exist and passed; upstream-verbatim files match their recorded digests
```

## Limits

- No harness loaded any of these packages. The protocol server files were
  checked against each harness's documented shape, not started.
- The API clients ran only against local mocks built from the specifications'
  examples; no API was called.
- The install recipes were not executed; only 15 smoke tests ran, on the
  programs this machine already had.
- The projection assumes one approval share for every family. Generated
  packages have no approval history yet.

## Files

- [Run summaries](../../artifacts/library-supply-2026-09-27/run-summaries.json):
  counts, refusal reasons, licences, effects and requests of each line's run.
- [Supply report](../../artifacts/library-supply-2026-09-27/supply-report.json):
  the library, the supply, the approval share, the projection and the needs.

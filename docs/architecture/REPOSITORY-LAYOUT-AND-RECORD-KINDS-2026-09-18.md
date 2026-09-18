# Repository layout and record kinds

Date: 2026-09-18. Owner question: it is not clear what the difference is
between the different folder paths and structures, the trees, and the
files. This record answers that question from the checkout as observed
today, states the charter every folder now carries, and lists the changes
made and the changes proposed. Nothing was moved or deleted; the changes
add a declaration to each folder, an index that shows every version of a
dated record in one place, and a gate that keeps new folders declared.

## Three different things that are all called structure

```text
Structure as the word is used in this repository
├── Folder path
│   Where bytes live: a Python package or a documentation folder.
│   Answers: where do I find this, and where do I put a new one?
├── Classification tree
│   A taxonomy drawn in a document: the Loop hierarchy, the role
│   profiles, the component tree in the roadmap, the model ontology.
│   Answers: what kind of thing is this, and how is it classified?
│   It is never mirrored by folders, and it must not be.
└── Record file
    One typed thing: a module, a data file with a record_type, or a
    document of a declared kind. Several records of one kind share one
    folder. Answers: what is the authoritative content of this one thing?
```

The confusion comes from the three being read as one. A tree in a
document (for example the four intelligence layers) suggests four folders;
the runtime keeps those layers as typed records served by a few modules in
`core`, and the four folders under `src/loop_engine/intelligence` are
declared boundaries that hold only their contracts. The folder answers
where, the tree answers what kind, and the record answers what.

## What the checkout looks like today (observed)

- The top level of the working directory holds 34 tracked entries and 47
  untracked scratch, worktree, and reference directories from earlier
  sessions (`taedri-*`, `loop-engine-release-audit-*`, `overnight*`,
  `solver-lab`, `vigil`, and others). They are ignored by git, so they are
  not part of the repository, but they sit beside it and are the first
  source of confusion when reading the folder listing.
- `src/loop_engine` holds twelve packages. `core` holds 340 of the roughly
  540 modules. Six packages hold README contracts and data but no code:
  `intelligence`, `kernel`, `governance`, `runtime`, `skills`, `node`.
  Their behavior is implemented by modules in `core`, `catalog`, `memory`,
  and `strings`.
- `docs` holds 17 folders and 14 loose files at its root. Ten folders had
  no README before this record. Dated records live in five folders
  (`architecture`, `research`, `verification`, `context`, `roadmap`) and
  the evidence folder uses a compact date in its file names.

## The charter: folder, kind, naming, versions

Every tracked top-level entry and every documentation folder now has a
declared kind. A documentation folder states it in the first lines of its
README as `Kind:`, and the conformance gate
`docs_folders_without_a_charter_readme` counts any folder with files but no
such README.

| Path | Kind | What belongs there | Naming and versions |
|---|---|---|---|
| `src/loop_engine/` | The Python package and executable runtime | Runtime classes, typed contracts, adapters, checks shipped with the package, packaged data | Modules are registered in `architecture_map.py`; the generated `ARCHITECTURE-MAP.md` is the current census |
| `src/loop_engine/core/` | Internal runtime services and component operations | Settings, policies, strategies, capabilities, adapters, routes, records, checks | One module per boundary; a `*_checks.py` module holds a boundary's checks |
| `src/loop_engine/intelligence/`, `kernel/`, `governance/`, `runtime/`, `skills/`, `node/` | Declared boundaries with README contracts and data only | Folder contracts, packaged candidate data, manifests | Implementation lives in `core`, `catalog`, `memory`, `strings`; the component interface record names the modules |
| `src/loop_engine/data/` | Installed static component and policy data | Personas, guidance, question portfolios, catalogs, seeds, terminology projections | Read only through typed readers; never edited by a run |
| `docs/architecture/` | Architecture and decision records | The Constitution, decision records, current design records, dated design records | `UPPER-KEBAB.md`; a dated record is `STEM-YYYY-MM-DD.md`; a newer date on the same stem supersedes the older one; undated files are living documents kept current |
| `docs/research/` | Research records | External reading, comparisons, landscapes, source reviews | Always dated; a research record never claims implemented behavior |
| `docs/verification/` | Verification reports | Checks run at a named commit with their results and limits | Always dated; point in time; corrected only by a dated note, never rewritten |
| `docs/evidence/` | Raw evidence artifacts | JSON, logs, transcripts, and folders a verification report cites | Compact or dashed dates in names; excluded from the live-language lint because reports quote what they found |
| `docs/guides/` | Operating guides | How to install, configure, run, view, verify, deploy, and package | Undated `kebab-case.md`; kept current; superseded guidance is rewritten, not dated |
| `docs/components/` | Component explanations | One guide per architecture component in the reading order the README gives | Undated; kept current with the code they explain |
| `docs/contracts/` | The contract index | Pointers to the Python objects that define behavior | One README; never a second definition |
| `docs/roadmap/` | The plan | `roadmap.yaml` is the machine-readable authority; the Markdown mirrors it with the status log | The Markdown record is dated by the day the program was set; the YAML is the current state |
| `docs/context/` | Session orientation and handoffs | Start-here files, handoff notes, session digests for agents | Dated handoffs; undated start-here files kept current |
| `docs/prompts/` | Prompt records | Point-in-time prompts loaded into agents | Dated where they were used once; excluded from the live-language lint |
| `docs/benchmarks/` | Benchmark registry and plans | The cataloged track registry, its schema, native evidence, and plans | Registry validated in continuous integration |
| `docs/reference/` | Standing reference specifications | The master specification, the universal Loop standard, product nomenclature, the retrieval plan | Undated; revised in place with a changelog entry |
| `docs/implementation/` | Implementation plans and execution logs | Improvement plans, backlogs, execution logs of a build program | Dated when they describe one program |
| `docs/templates/` | Document templates | The concept page and example README templates | Undated |
| `docs/internal/` | Maintainer handoff pointers | A stable handoff pointer and historical development notes | Not a checkout snapshot |
| `docs/` root files | Entry points and living overviews | The documentation index, repository organization, style, getting started, diagrams, troubleshooting, and a few specifications that predate the folders | Proposed step S-2.19 moves the specifications into their kind folders |
| `examples/` | Runnable examples | Numbered folders, one boundary each, a README each | `NN_snake_case/` |
| `benchmarks/` | Frozen task populations and evaluators | Populations, runners, fixed evaluators, raw outputs | One folder per population |
| `case-studies/` | Reports of complete measured runs | Plain-language reports linked to their evaluator and history | Undated stems with the population in the name |
| `artifacts/` | Review and study artifacts | Dated audit outputs, checkpoints, study records | `subject-YYYYMMDD-suffix/` |
| `checkpoints/` | Saved checkpoints of the tree state | Outputs of the checkpoint tool | Dated |
| `embodiments/` | Harness recipes and their guide | Registered harness recipes, catalog, architecture, build results | Guide in `HARNESS-GUIDE.md` |
| `devtools/` | Development tooling | The hardcoding audit, the qualification lab, the embodiment lab, allowlists, baselines | Its own `AGENTS.md` |
| `tools/` | Development commands with tests | Command scripts and their `test_*.py` | Tests run in continuous integration |
| `integrations/` | Host integrations | Claude Code and Codex integration material with tests | Its own README |
| `kaggle/` | Kaggle campaign scripts | Provider quickstarts and the cell check | Its own README |
| `showcase/` | The architecture presentation | Slides, player, video export, visual audits | Its own README |
| `graphify-out/` | Generated graph cache | Cache only | Regenerated |
| Root files | Governance and packaging | `AGENTS.md`, `ASTRA.md`, `CLAUDE.md`, the Constitution pointer, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `Dockerfile`, `terminology.yaml`, `architecture.yaml` | One file each; no dated copies at the root |

## Versions of one record in one place

The owner asked whether each record kind should have its own folder so
that every version of a file appears in one folder with its dates. The
folder already is the kind. What was missing is the per-subject view: all
versions of one stem, in date order, without moving anything. The records
index gives that view:

```text
python tools/build_records_index.py
```

writes `docs/RECORDS-INDEX.md`, grouping every dated record under its
folder and subject stem with the versions in date order, newest first, and
`python tools/build_records_index.py --check` fails when the committed
index is stale. The tools test suite runs that check, so a dated record
added without regenerating the index fails continuous integration.

The dated-file convention stays. A dated record is a point-in-time
statement; an undated file is a living document. Renaming dated records
into per-subject folders would break several hundred links and the
evidence citations inside verification reports, and would give no
information the index does not.

## Changes made in this record's batch

- A README with a `Kind:` line in every documentation folder that holds
  files, and a `Kind:` line added to the five READMEs that existed.
- The conformance gate `docs_folders_without_a_charter_readme`, with a
  canary in the conformance self-test that plants a folder without a
  README and expects it to be reported.
- The records index tool, its test, and the committed `docs/RECORDS-INDEX.md`.
- A pointer table in `src/loop_engine/intelligence/README.md` from each of
  the four intelligence layers to the modules that implement it, so the
  declared boundary and the implementation can be read together.

## Proposed next steps

- S-2.18 (proposed): move the implementation of each declared boundary
  into its package one boundary at a time, behind the dependency-direction
  ratchet and with import-boundary tests, starting with the four
  intelligence layers. The relayering question in `ASTRA.md` is the same
  question.
- S-2.19 (proposed): move the specifications at the `docs` root
  (`COMPLETE-PROJECT-CONSTITUTION.md`, `OVERNIGHT-SPEC-AND-EVIDENCE.md`,
  the two build prompts, the OpenCode notes) into their kind folders with
  redirect stubs, so the root holds only entry points.
- Housekeeping the owner decides: the 47 untracked directories at the top
  level belong to earlier sessions and reference projects. Moving them to a
  folder outside the checkout (for example a scratch folder under the home
  directory) makes the listing readable; this session did not move them
  because other sessions may still write to them.

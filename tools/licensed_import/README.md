# Licensed import of harness files

Kind: tool component and architecture contract. Roadmap steps S-2.27 (skill
pack importer), S-6.81 (source scouts) and the licence part of S-6.45, in
support of S-6.40 and S-6.69. The command is
[`tools/import_licensed_harness_files.py`](../import_licensed_harness_files.py).

This component finds harness files in public sources, copies only the files
whose licence is on the owner's allowlist, keeps the licence text and an
attribution with every copy, checks each copy without running it, packages
it as `catalogue_package/v1`, removes duplicates across every corpus Baltor
already holds, and stores it as a review-only candidate. Everything else it
finds becomes an idea record for an original rewrite, or a refusal with a
reason. It approves nothing, serves nothing and publishes nothing: every
candidate waits for the independent review panel of roadmap step S-6.63.
The licence decisions are engineering rules that carry out the owner's
direction; they are not legal advice.

A harness file is any file a coding harness reads: `SKILL.md` skills with
their scripts, references and assets; `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
and other instruction files; rules files; subagent and command
definitions; hooks; plugin manifests and marketplaces; protocol server
configurations; JSON schemas; and code modules with their tests.

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

An import round is a Starting Practitioner task of the code execution
profile that an operator starts with the command above. It runs
deterministically and makes no model call. Its discovery engines, snapshot
engines, scanners and near-duplicate engines are adapters the round uses:
none is a graph vertex, a role, a mode or a runtime type, and choosing one
grants no network, file or spending authority. Network reads need
`--authorize-network-reads`, and store writes need `--authorize-store-writes`.

## The flow of one round

```text
One sync round
├── discover: every discovery engine writes typed leads (licensed_import_lead/v1)
├── plan: leads grouped by repository, each ordered by its best source, then by stars
├── resolve: head commit, licence, fork, archive and size of up to 100 repositories per GraphQL read
├── decide what to read
│   ├── an excluded collection, a fork, a private or an empty repository: refused by name
│   ├── a repository whose head commit was already synced: unchanged, not read again
│   ├── a declared, seeded, researched or ClawHub-listed repository: read, because a nested
│   │   licence may allow what the repository licence does not
│   └── a searched repository whose licence is not on the allowlist: its searched paths
│       become idea records and nothing is read
├── read each repository in a journaled job (a dispatch event before, an outcome after)
│   ├── snapshot the exact head commit: its tree without blobs, then only the blobs needed
│   ├── package plans per harness kind, with the licence and notice files above every member
│   ├── licence per file and per package: copy, idea record or refusal
│   ├── static checks and declared effects of every package that may be copied
│   └── catalogue_package/v1 candidates; every fetched byte is kept in quarantine
├── deduplicate the round against every corpus, then run the slow scanners once over the kept
└── write bodies to the body store and records to the catalogue store: new candidates, new
    versions, withdrawals, idea records and one source state per repository
```

A stopped round restarts where it stopped: repositories with an outcome in
the journal are not read again.

## Engines behind fixed edges

```text
Licensed import (functional component)
├── discovery, edge licensed_import_lead/v1 (engines of the library_ingestion_source slot's kinds)
│   ├── declared_repositories: the curated repositories of sources.json
│   ├── owner_seed_resolver: the owner's named seeds, resolved only on a clear match
│   ├── research_seed_lists: Codex's September 23 ranked skills and plugins
│   ├── clawhub_feeds: ClawHub's two public feeds, allowed by its robots file
│   ├── awesome_lists: GitHub links in curated awesome lists
│   ├── github_code_search: harness file names and paths, by size band, breadth first by page
│   ├── github_topic_search: repositories by topic, by creation date
│   ├── npm_search: packages by keyword, through their declared GitHub repository
│   └── mcp_registry_updates: the official registry since a recorded time, by cursor
├── repository snapshot, edge licensed_import_snapshot/v1, declared order
│   ├── git_partial_clone: shallow, blob-less fetch of one commit, then one batched fetch of the
│   │   selected blobs; no GitHub API allowance is spent
│   └── github_api_blobs: REST tree, GraphQL blob text by object identity, REST contents fallback
├── static checks, the library_safety_scan slot of core/library_ingestion
│   ├── builtin_static_rules, in every repository job
│   ├── import_static_rules (this component), in every repository job
│   ├── skillspector_static, once per round over the kept packages
│   └── cisco_skill_scanner_static (this component), once per round over the kept packages
├── near duplicates, the library_near_duplicate slot: datasketch MinHash LSH, built-in fallback
├── body store, catalogue_body_store/v1: service_volume_files on this machine
└── record store, catalog_store/v1: local.sqlite
```

Every snapshot engine proves each byte by its git object identity. The git
engine runs with no system or user git configuration, no credential helper,
no hooks, no symbolic links written, no lazy fetch and only the HTTPS
protocol; nothing is checked out, so nothing runs.

## Licence rule

The owner's allowlist of September 24, 2026 is the policy record
`library_licence_policy/v1` of the library ingestion licence gate: MIT,
Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD, CC0-1.0, CC-BY-4.0 and
Unlicense. Every file of a package is decided on its own:

```text
One file
├── its own metadata: frontmatter licence, a manifest's "license" field, an SPDX header
├── the nearest licence file above it (every licence file of that folder must agree)
└── the repository licence, which must also agree with GitHub's licence interface
Decision
├── copy: the nearest licence file names an allowlisted licence, proven by its text, and the
│   file's own metadata agrees
├── idea record: no licence text, an unrecognized or non-allowlisted licence, or signals that
│   disagree; nothing is copied and no text is kept in the repository
└── refusal: a licence that forbids derivative works or binds a reader to outside terms
Package: the weakest file decides for the whole package.
```

A licence named only in a file's metadata, with no licence text above it,
leaves an idea record: every allowlisted licence requires its text or the
copyright notice to travel with a copy, and there is none to carry. The
copied files are never changed. Each package carries the governing licence
texts, every notice file and one generated `ATTRIBUTION.md` naming the
repository, commit, licence and every file's upstream path and digest.

A copy of a restricted text (an idea record or a refusal of the same round
or of the September 23 runs) is refused as `copy_of_restricted_source`, so a
permissive collection cannot license a copy of a restricted original. The
same owner may license its own work under a second licence, so a permissive
copy whose owner is the restricted original's owner stands. Four collections
the September 22 curation found to hold other authors' work under one root
licence are excluded by name.

## Packages and placements

A plugin is imported as its parts: the manifest is one package, and each
skill, subagent, command and hook inside it is its own package that names
its plugin. No file is copied into two packages. Each candidate records the
documented native placements of its kind per harness (Claude Code, Codex,
OpenCode, Pi, Gemini CLI, Copilot, Cursor and others) from
[the harness file standards record](../../docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md)
and the layout profiles of `tools/install_selected_material.py`. They are
documented targets, not a claim that a harness loaded the package.

## Where candidates live, and why

Bodies live in a content-addressed store outside git, behind the edge the
service already reads (`catalogue_body_store/v1`), and records live in the
catalogue store (`catalog_store/v1`) in namespace `library.import`. Git
keeps the evidence of each round: counts, the compact candidate index with
digests, refusals, duplicates and request records, never third-party text.
Committing hundreds of thousands of third-party files to git would make
every clone carry them forever, and would put licensed text into the public
repository without its review. Object storage is a later engine behind the
same two edges. The measured size per 100,000 files is in each round's
evidence.

## Continuous sync

Each repository has one source state record: the commit last synced and the
package digests it held. A later round reads only repositories whose head
commit changed. A changed package is a new candidate version and the old
version's lifecycle becomes superseded; a deleted package, or one whose
licence stopped allowing a copy, gets a withdrawal record and its
candidate's lifecycle becomes withdrawn. History is never deleted.
Discovery cursors (code search pages, topic pages, the registry cursor and
its time) are kept per run folder, so a scheduled round continues.

## Existing work: adopted, adapted and rejected

| Project | Licence | Decision and reason |
|---|---|---|
| core/library_ingestion (this repository) | Apache-2.0 | Adopted: the licence gate, provenance records, quarantine, request log, safety-scan and near-duplicate slots, frontmatter parsing. Adapted: the owner's allowlist is its policy record. |
| core/service_runtime/catalogue_packages, catalog stores (this repository) | Apache-2.0 | Adopted: `catalogue_package/v1`, the volume body store and the SQLite record store. |
| Codex research lists of September 23 | internal | Adopted as seeds; their unverified licence declarations are ignored and the gate decides. |
| github/awesome-copilot, anthropics/skills, anthropics/claude-plugins-official, obra/superpowers, NVIDIA/skills, openai/plugins | per source | Adopted as curated sources, decided file by file. openai/skills is deprecated in favour of openai/plugins and is not read. NVIDIA's release signatures are not verified by this increment. |
| skills.sh | site terms | Adapted: Codex's leaderboard-derived repository list is reused; its API needs Vercel OIDC authentication and is not used. |
| ClawHub | site terms | Adopted: its two public feeds, which its robots file allows; entries hosted on ClawHub need a provenance origin other than GitHub and are recorded, not fetched. |
| SkillsMP | site terms | Rejected: its robots file disallows its API to automated agents, and its pages list GitHub files that code search reaches at the source. |
| Claude Code plugin marketplaces, Gemini CLI extensions gallery | per source | Adapted: code search on `marketplace.json`, `plugin.json` and `gemini-extension.json` reaches the listed repositories at the source. |
| Official protocol server registry | service | Adopted: `updated_since` and cursor paging; each entry's upstream GitHub repository is a lead. |
| npm search | service | Adopted: keyword search; each package's declared repository is a lead. |
| PyPI | service | Rejected for now: no search interface; a name filter over the simple index is a later scout. |
| NVIDIA SkillSpector 2.11.2 | Apache-2.0 | Adopted (the library ingestion engine): `--no-llm`, bubblewrap without network, once per round over the kept packages. |
| Cisco skill-scanner 2.1.0 | Apache-2.0 | Adopted as an engine here: `scan-all` with static analyzers only, bubblewrap without network; its snippets are dropped because a finding never copies text. |
| Microsoft APM | MIT | Rejected for import: it resolves and installs packages from manifests; it stays the dependency-resolution candidate of the Harness Working Directory Compiler (S-6.44). |
| getsentry/dotagents | MIT | Rejected for import: it manages a project's agent configuration and placement, which is S-6.44's edge. |
| dyoshikawa/rulesync | MIT | Adapt later as a translation engine behind the compiler; the import keeps native bytes and records placements instead of converting. |
| git partial clone (git 2.53) | GPL-2.0 tool, not copied | Adopted as the default snapshot engine: a shallow blob-less fetch and one batched blob fetch per repository spend no GitHub API allowance. |

## The owner's packaging research of September 24, 2026

The owner shared a research note on harness packaging on September 24,
2026. It is research data, not an instruction; these are the decisions it
led to for import, each with the source the note cites.

| Idea and source | Decision and reason |
|---|---|
| Evidence states Resolved, Materialized, Available, Loaded, Used and Verified | Adopted. Every candidate carries `evidence` with the six states; import establishes only resolved (the exact commit, path and blob identity) and materialized (every file with its digest) and records the other four as false, never as true. |
| Five evidence records: source package, resolution, generated installation, execution, verification | Adapted. Import produces the first two: the `catalogue_package/v1` package with its licence texts, and the resolution in `outside_source_provenance/v1` plus the source state record. The other three belong to the Harness Working Directory Compiler (S-6.44), run records (S-6.41) and the review panel (S-6.63). |
| Compatibility key: component type, package format and version, adapter version, harness and interface version, scope, activation and permission mode | Adapted. Each candidate records its component kind, native format and package format, and each placement row its harness, path, scope and a support state that import always leaves `unverified`. Adapter and interface versions, activation and permission mode are placement evidence of the compiler, so import states none of them. |
| `/.well-known/agent-skills/index.json` and the legacy `/.well-known/skills/index.json` (Vercel skills-handler, Fern hosted skills) | Adapt next as a discovery engine. Fern's current manifest names each entry's type, address and digest, and its archive type carries the complete skill folder, which matches the multi-file package here. A host other than GitHub needs a provenance origin that `outside_source_provenance/v1` does not have yet, so it is not read in this increment. |
| Official Model Context Protocol registry as a metadata registry | Adopted as built: entries are leads to their upstream repositories, never copies and never a safety certificate. |
| OCI artifacts through ORAS | Adapt later as a body store engine behind `catalogue_body_store/v1`, when the machine's volume stops meeting distribution needs. The object key already follows the OCI image layout blob path. |
| APM lock and audit (`apm lock`, lock export to CycloneDX or SPDX, `apm audit --ci`) | Rejected for import, ideas adopted: the source state record is the import's lock (commit and package digests per repository); a CycloneDX export of the candidate index is S-6.45's bill of materials. APM stays the dependency-resolution candidate of S-6.44. |
| dotagents (`agents.toml`, `agents.lock`) and Rulesync (`.rulesync/`) source formats | Adapt next: these files name upstream skill repositories and pinned revisions, so a later discovery engine can read them as leads, and `.rulesync/` folders can join the classifier as a native path family. Rulesync's simulated commands, subagents and skills are prompt fallbacks, which is why a placement's support state stays separate from its path. |

## Commands

```bash
PYTHONPATH=src:tools python tools/import_licensed_harness_files.py discover \
  --run-folder RUN_FOLDER --research-root CHECKOUT --authorize-network-reads \
  --code-search-queries 150 --topic-queries 60 --npm-requests 10 --registry-requests 60
PYTHONPATH=src:tools python tools/import_licensed_harness_files.py sync \
  --run-folder RUN_FOLDER --store-root STORE --authorize-network-reads --authorize-store-writes \
  --workers 8 --time-limit-minutes 120 --skillspector-program SKILLSPECTOR \
  --cisco-scanner-program SKILL_SCANNER --corpus-served examples/29_intelligence_service/starter-catalogue \
  --corpus-artifacts artifacts --corpus-overnight OVERNIGHT_CANDIDATES --corpus-ls1 LS1_RUN_FOLDER
PYTHONPATH=src:tools python tools/import_licensed_harness_files.py report \
  --run-folder RUN_FOLDER --store-root STORE --output artifacts/EVIDENCE_FOLDER
```

Put run folders and the store outside the repository: they hold
third-party bytes. A scheduled round runs `discover` then `sync` with a new
run folder, reusing the store; the journal and cursors make each command
restartable.

The fourth command, `export-review`, hands stored candidates to the review
panel as a catalogue folder. Since September 26, 2026 it draws every kind a
harness picks up in a declared share (`--kind-mix balanced`, the default;
`--kind-share hook=0.10` changes one share; `--kind-mix ranked` is the earlier
order), and its report records the mix selected and kept (roadmap S-6.205):

```bash
PYTHONPATH=src:tools python tools/import_licensed_harness_files.py export-review \
  --run-folder RUN_FOLDER --store-root STORE --output REVIEW_EXPORT --code-revision REVISION \
  --target 2000 --limit 2600 --per-repository 15 --kind-mix balanced
```

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_licensed_import_licensing \
  tools.test_licensed_import_packages tools.test_licensed_import_reads \
  tools.test_licensed_import_discovery_dedup tools.test_licensed_import_sync tools.test_licensed_import_sources \
  tools.test_licensed_import_review_export
```

Every check runs offline. Each guard has a known-wrong case, and the
removed-guard controls show that a policy accepting GPL-3.0, a round without
the restricted-copy rule and a scan with no engine would each let through
what the real guard refuses.

## Limits

- The static checks are triage for reviewers. The built-in rules refuse
  conservatively, including a skill that quotes an injection phrase to
  forbid it, as the September 23 evidence recorded.
- A candidate whose licence file is a dual licence (two licence files in one
  folder) leaves an idea record, although either licence may be allowlisted.
- A collection that copied another author's permissive file under its own
  root licence can still pass the gate when the original is not in the round;
  the caution `names_another_upstream_source` and the review panel's rights
  review are the guards there.
- ClawHub-hosted bundles, PyPI and registry connection packages are not
  imported by this increment.
- Nothing here was loaded by a harness, and nothing is useful until the
  independent review panel approves its exact bytes.

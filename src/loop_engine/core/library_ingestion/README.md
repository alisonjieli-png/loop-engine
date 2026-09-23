# Library ingestion: outside harness material with provenance

Kind: internal component and architecture contract. Roadmap step S-6.40,
first increments, and the engine slot `library_ingestion_source` of the
[engine design](../../../../docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md).

This component brings harness material from outside this repository into
the library as review-only candidates. It reads Agent Skills files
(`SKILL.md`), GitHub Copilot instruction files, Cursor rule files and entries
of the official Model Context Protocol registry. For every item it keeps the
exact fetched bytes, records where they came from and what their licence
evidence permits, renders the item into the file a harness loads, checks the
format, scans for unsafe instructions, declares the effects the item asks
for, merges duplicates, and writes specification rows that the existing
candidate staging tool stages as candidates.

It approves nothing, serves nothing and publishes nothing. Every staged row
stays a candidate until an independent review approves its exact bytes, and
the producer of a row never approves it. Licence decisions here are
engineering rules that carry out the owner's direction of September 22,
2026. They are not legal advice.

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

An ingestion run is a Practitioner task of the code execution profile that
an operator starts with `tools/ingest_outside_material.py`. It runs
deterministically, except that the optional model outline engine may call
one model per outline under explicit model authority. The source readers,
validators, scanners and outline writers are engines: adapters and
strategies that the run uses. None of them is a graph vertex, a role, a mode
or a runtime type, and choosing one grants no network, file, model or
spending authority. The component adds no runtime type and no intelligence
layer.

## The fixed edge and its records

Every record is written `name/vN`. Each reader refuses another version, an
unknown field and a missing field before anything is built from the record.

| Record | What it holds | Reader |
|---|---|---|
| `library_outside_sources/v1` | The curated source list: each GitHub repository at an exact commit with its expected licence, how its content was curated and the paths to select; the registry host and its entry ceiling; the pinned connection schemas. | `source_declarations.read_sources` |
| `library_candidate_request/v1` | One request to one source engine: the source, the resume cursor, the ceilings and the explicit network read authority. | `candidates.read_candidate_request` |
| `library_candidate_batch/v1` | The one answer shape of every source engine: candidates, refusals, whether the source was read completely and the cursor to resume from. | `candidates.read_candidate_batch` |
| `library_source_candidate/v1` | One fetched item: its stable key, kind, native format, name, provenance and the other files of its package. | `candidates.read_source_candidate` |
| `outside_source_provenance/v1` | Where the exact bytes came from: origin and host, repository or registry entry, immutable revision, path, source digest and size, git blob identity, the digest of the fetch response and of the request record, the fetch time and the licence evidence. | `provenance.read_outside_provenance` |
| `outside_licence_evidence/v1` | An SPDX expression, the decision it permits, the reason, the detector, the repository licence with its digest, the governing licence file with its digest, and every file-level notice. | `provenance.read_licence_evidence` |
| `library_candidate_refusal/v1` | Why a candidate or a whole source was refused, with a stage and a reason from a closed vocabulary. | `candidates.read_refusal` |
| `library_candidate_outline/v1` | For a source without a permissive licence: the abstract purpose and the source identity, never the text. | `candidates.read_outline` |
| `library_engine_selection/v1` | Which engine of a slot was chosen and why each other one was not, recorded before anything runs. | `selection.select_engines` |
| `library_network_request/v1` | One read-only request: transport, host, target, status, byte count and digest of the answer, time, outcome and the provider's remaining allowance. | `request_log.RequestLog` |
| `library_model_call/v1` | One model call of the outline engine: the model asked for and the model that answered, the route, the prompt digest, the provider-reported usage (unknown stays unknown) and the outcome. | `outline_model.ModelOutline` |
| `candidate_intelligence_specifications/v2` | Staging rows of outside material: the rendered text, every provenance record, how the text was authored, its licence, its declared effects, its package files with digests and the triage notes. | `tools/stage_intelligence_candidates.py` |

`require_provenance` refuses a candidate without provenance, and the
staging tool refuses a version two row without provenance, a row whose
authoring disagrees with the licence evidence of any of its sources, and a
row whose text is not one of its package files.

## Engine slots

```text
Library ingestion (functional component)
├── library_ingestion_source, set_of
│   ├── github_pinned_repositories: curated repositories at exact commits, through the gh login
│   └── mcp_official_registry: the official registry, latest entries, link mode
├── library_format_validation, set_of
│   ├── agent_skills_builtin_rules: the Agent Skills specification, written here
│   ├── agent_skills_reference_validator: skills-ref, beside the built-in rules
│   ├── connection_builtin_rules: each harness's documented connection shape
│   └── connection_schema_validator: the published Codex and OpenCode schemas
├── library_safety_scan, set_of
│   ├── builtin_static_rules: blocking and caution rules with a fixed regression set
│   └── skillspector_static: NVIDIA SkillSpector without its model stage, in a sandbox
├── library_near_duplicate, one_of
│   ├── datasketch_minhash_lsh: the adopted library
│   └── builtin_minhash_lsh: the declared fallback that needs no library
└── library_outline, one_of
    ├── model_outline: one model sentence per outline, under model authority only
    └── deterministic_outline: a template sentence that needs no authority
```

`engines.py` is the factory table and the only module that names the
concrete engine classes. `selection.py` removes every engine that is
switched off, lacks its dependency, is not configured or lacks authority,
keeps the declared order among the rest, and records the decision before
any engine runs. Adding an engine is one module, one row in the factory
table and its checks; no neighbour changes. When the shared engine
framework of roadmap step S-6.30 lands, these records can move behind it
without changing an engine.

## Licence decisions

```text
One fetched file
├── the governing licence file is the nearest one, from the file's folder up to the root
├── the licence text is compared with stored word sets of the canonical texts
│   └── recognized only at 98 percent similarity or more, clearly ahead of the next licence
├── a repository licence must also agree with GitHub's licence interface at the pinned commit
├── every file-level notice (a frontmatter licence field, an SPDX header) must agree
└── decision
    ├── verbatim_permitted: an accepted licence, proven by its file; the bytes may be copied
    │   with the licence file and the attribution
    ├── link_only: a registry entry; Baltor writes the connection files from its facts
    ├── outline_only: no licence, an unrecognized or unaccepted licence, disagreeing
    │   signals, or a source curated for outlines; only the abstract purpose and the
    │   source identity are kept
    └── refused: a licence or notice that forbids derivative works; nothing is kept
        but the refusal
```

The accepted licences are MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC,
CC0-1.0 and CC-BY-4.0. A host may replace the list with a
`library_licence_policy/v1` record; a list that names no licence, an unknown
name, an expression or a repeated name is refused. Share-alike and copyleft
licences are recognized but not accepted, so their files are read for
outlines only. The stored word sets come from `github/choosealicense.com`
(MIT) at a pinned commit; the licence texts themselves are not stored.

## What a candidate passes before it is staged

```text
One candidate
├── quarantine: bytes kept read-only under their own digest, never executed
├── licence decision, above
├── copy rule: a verbatim item whose text repeats a refused or outline-only file of
│   the same run, exactly or at the near-duplicate threshold, is refused as
│   copy_of_restricted_source, so a permissive collection cannot license a copy of
│   a restricted original
├── rendering into the native file
│   ├── skill: SKILL.md with the Agent Skills fields; the body byte for byte; the
│   │   source, commit, path, digest and a change note in metadata; the licence
│   │   file beside it
│   ├── instruction file: copied verbatim to its native path, the licence file beside it
│   └── registry entry: .mcp.json, a Codex config.toml table and opencode.json, written
│       from facts, with a package document carrying the upstream identity and licence
├── format engines on the rendered file
├── size and body bounds, and the bundled-file rule: a skill that points at a
│   bundled file, folder or module is refused until multi-file packages exist
├── package check: an npm or PyPI package must exist at its exact version
├── safety engines: a blocking finding refuses the item by name; a caution finding
│   becomes a note for the reviewer
├── declared effects, each with the rule that declared it
└── exact and near duplicates merged into one row whose provenance lists every source
```

Every candidate is counted exactly once: staged, merged as a duplicate,
refused with a reason, or kept as an outline. The curated source order is
the duplicate order, and it lists original authors before collections, so
the original of a copied text is the one kept. The reasons are the closed
vocabulary `REASONS` in `candidates.py`.

## Files and dependency direction

```text
core/library_ingestion
├── records: record_rules.py, provenance.py, candidates.py, source_declarations.py,
│   staging_rows.py, rendering_types.py
├── rules: licences.py (with licence_templates.json), effects.py, topics.py (with
│   topic_words.json), duplicates.py, registry_sync.py
├── transports: https_transport.py (the one module that imports urllib),
│   github_reader.py, processes.py (the one module that starts a process),
│   request_log.py, quarantine.py, package_resolver.py
├── rendering: skill_rendering.py, connection_rendering.py
├── engines, one module each: source_github.py, source_mcp_registry.py,
│   format_builtin.py, format_skills_ref.py, format_connection.py,
│   format_json_schema.py, scan_builtin.py, scan_skillspector.py,
│   near_duplicate_datasketch.py, near_duplicate_builtin.py,
│   outline_model.py, outline_deterministic.py
├── selection and the factory table: selection.py, engines.py
├── the pipeline: pipeline.py
├── the curated sources: outside_sources.yaml
└── checks: provenance_checks.py, licence_checks.py, source_checks.py,
    render_checks.py, scan_checks.py, pipeline_checks.py, optional_engine_checks.py
```

The component depends on its own records and on three core modules only:
`facets` for the effect names, `model_call_records` for the repository's
secret patterns and `ollama_client` for the model outline engine. It never
reaches the serving, approval or release code, and it keeps no store: the
staging tool writes candidates through the existing catalogue contract.
`tools/test_library_ingestion_boundary.py` holds these rules.

## Existing work: adopted, adapted and rejected

| Project | Licence | Decision and reason |
|---|---|---|
| datasketch 1.6.5 | MIT | Adopted as the near-duplicate engine (MinHash with locality-sensitive hashing). An optional dependency; the built-in engine is the declared fallback and finds the same pairs on the fixture. |
| skills-ref 0.1.0 from agentskills/agentskills | Apache-2.0 | Adopted as a second format engine on the rendered file. Its own guide calls it a demonstration, so it runs beside the built-in rules, never instead of them. It needs Python 3.11 or later. |
| NVIDIA SkillSpector 2.11.2 | Apache-2.0 | Adopted as a static scanner, with its model stage off, over many skills per run, inside a bubblewrap sandbox without network. |
| licensee | MIT | Adapted: its method (the Sorensen-Dice coefficient over distinct normalized words, 98 percent confidence) is written here in Python. The gem itself is rejected, because it would add a Ruby runtime. |
| github/choosealicense.com | MIT | Adopted as the canonical licence texts; only their normalized word sets are stored, with each file's digest and the pinned commit. |
| GitHub licence interface | Service | Adopted as the second signal for a repository licence; it must agree with the text. |
| Official Model Context Protocol registry, list interface v0.1 | Service | Adopted as the link-mode source. The registry is a metadata directory; a listing is never admission. |
| jsonschema | MIT | Adopted, a base dependency, to apply the published Codex (Apache-2.0) and OpenCode (MIT) configuration schemas, each pinned by digest. |
| scancode-toolkit | Apache-2.0, data CC-BY-4.0 | Rejected for this increment as a heavy dependency; the per-file rule here reads nested licence files, frontmatter licence fields and SPDX headers. It stays the candidate engine for full file-level scans. |
| Snyk agent-scan | Proprietary service | Rejected: it sends material to a remote analysis service, needs an account token and starts protocol servers to read their tool lists. |

## Checks

```bash
PYTHONPATH=src python -c "from loop_engine.core.library_ingestion import pipeline_checks as m; print(m.self_test()['all_passed'])"
PYTHONPATH=src:tools python -m unittest tools.test_ingest_outside_material tools.test_library_ingestion_boundary
```

The seven check modules run offline against recorded fake transports. They
hold the known-wrong cases: a candidate without provenance, verbatim import
without an accepted licence, a proprietary licence, a nested licence file, a
licence answer that is not the pinned blob, a source curated for outlines,
tampered bytes, symbolic links and submodules, a truncated tree, request
ceilings and allowance pauses, registry status changes and vanished entries,
secrets and plain addresses in connection files, the malicious and benign
regression set of the scanner, duplicates, bundled files and outlines that
repeat source words.

## Limits

- A skill that needs its scripts, references or assets is refused until the
  multi-file package contract exists; a skill whose extra files it never
  mentions is staged without them, and its triage notes say how many.
- A registry entry is link-only: its upstream code is not read, and a remote
  server may change without a package digest.
- The scanners are triage for reviewers. A clean scan is not safety proof,
  and a rendered file has not been loaded by a harness here.
- Candidate counts are internal. A public library number counts approved,
  active packages only.

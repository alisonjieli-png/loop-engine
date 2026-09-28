# Local research search and exact-ID lookup

This helper indexes metadata from the four final ranked research lists. It does
not index or return third-party instruction bodies, manifests, executable code
or callable tool schemas. The JSONL files remain authoritative; the SQLite file
is a derived local artifact outside the repository and public service.

## Current result

The index holds exactly 4,000 records: 1,000 skills, 1,000 plugins, 1,000 contracts
and 1,000 tool-provider integrations. All 4,000 payloads were read back byte for
byte after the acknowledged atomic write. Their 1,291 distinct referenced source
snapshots were verified against local quarantined bytes. Every record has
`lifecycle: candidate` and `execution_available: false`.

Active catalog queries returned zero rows. The existing intelligence search with
its default candidate exclusion returned zero hits and excluded all 4,000 rows.
This CLI explicitly requests candidates for research search; that choice does
not approve, publish, load or execute them.

The database is:

```text
/home/username/.le-codex-research-cache/four-catalogues-20260923/research-index.db
```

[research-index-manifest.json](research-index-manifest.json) binds every input
file digest, the database digest, the helper and the pinned runtime source.
[research-index-build-successor.json](research-index-build-successor.json)
records the atomic acknowledgment, complete readback, source checks and active
query controls. The database is not a new production catalogue or source of
approval authority.

## Search

Run from this directory with the repository's qualified environment:

```bash
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py search --category skill --query testing --limit 5
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py search --category plugin --query memory --limit 5
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py search --category contract --query "agent permissions" --limit 5
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py search --category tool --query postgres --limit 5
```

Omit `--category` to search all four lists. `--limit` is 1–100; the default is 10.
Query text is capped at 512 characters. Results contain the research identity,
name, category, source URL and digest, original research rank/priority, lexical
query score, evidence level and unverified rights/compatibility status. No
external URL is opened. Source material is not automatically materialized.

## Exact identity

```bash
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py search --lookup tool-7a3efee6b3238eff2a414321
```

Lookup uses the existing store's exact record identity. It is not a fuzzy name
match. A missing identity returns an empty hit list. A category supplied with
lookup must match the record. Lookup has no lexical score.

## What search means here

The helper uses `SQLiteRecordStore`, `CatalogWriteBatch` and `IntelligenceQuery`,
then the existing `query_intelligence(IntelligenceSearchRequest(...))` with
`mode="lexical"` and `include_candidates=True`. The first-party runtime source is
explicitly pinned to `231f51bb1facab517fbe915b08ea9ac85f913347`; changes to that
source or to this helper cause an integrity refusal until a new index is built.
No model, learned embedding service or upstream program is called.

The lexical engine tokenizes ASCII letters/digits and uses up to the first 12
tokens with OR matching. Quoting a multi-word CLI argument does not turn it into
an exact phrase search. Results follow existing FTS5/BM25 order and its
reciprocal-rank query score. That score differs from the editorial research
`priority_score` and original list `rank`; neither establishes usefulness or
safety. The ephemeral lexical view is built from the derived records for each
invocation, using the existing retrieval implementation.

Searchable text includes names, repositories, declared method ideas, categories,
topics and format patterns present in the ranked metadata. Upstream description
bodies absent from those records are not fetched or guessed. For example, the
retained tool-category `sqlite` probe returned no hits, while the `postgres`
probe found declared-name matches. The absent result is a metadata coverage
limitation, not proof that no listed service can work with SQLite. Semantic
equivalence, synonym recall and task success remain unmeasured.

## Integrity and rebuild procedure

Every search/lookup verifies the current four JSONL digests, runtime/helper
fingerprints and database digest before reading. It opens the database read-only
and rechecks source/database digests before returning. Drift fails closed; the
helper does not silently rebuild, rewrite a source file or continue against an
outdated snapshot.

Building requires the explicit isolated-index flag:

```bash
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py build --authorize-isolated-index
```

That command now refuses because the current database/manifest already exist.
For an intentional successor, preserve the current artifacts and pass a new
`.db` filename under the same isolated cache root plus a new manifest filename:

```bash
/home/username/.le-codex-build/integration/.venv/bin/python research_index.py build --authorize-isolated-index --database /home/username/.le-codex-research-cache/four-catalogues-20260923/research-index-2.db --manifest research-index-manifest-2.json
```

Use the same `--database` and `--manifest` options on searches for that successor.
Existing databases and manifests are never overwritten. No production database
path is admitted. The current SQLite adapter uses its existing atomic contract
and rollback journal; it does not enable WAL or change runtime security settings.

The builder requires exactly 1,000 rows per category, unique identities across
the whole population, contiguous ranks, finite consistent priority scores,
supported record types and unreviewed/unverified flags. It checks snapshot
digest shape and actual quarantined bytes. Primary navigation URLs must be
HTTPS without credentials, credential-bearing query parameters, literal
whitespace, local hostnames or non-global IP literals. These syntactic checks
perform no DNS lookup and are not a network sandbox. Preserved provenance fields
and reported licence objects remain inert metadata, never fetch instructions.

## Checks and preserved attempts

Fifteen offline controls pass in
[research-index-controls-final.txt](research-index-controls-final.txt). They
cover exact 4,000-row readback, active exclusion, category search, lookup,
authorization, overwrite refusal, duplicate IDs, rank gaps, forged approval
flags, invalid digests, private/credential URLs, source drift, database drift,
missing quarantine objects, encoded path spaces and structured licence metadata.
Some tests cover several related assertions.

The first real build refused before creating a database. It exposed a reader
assumption about string-only licences and one literal-space URL in the contracts
list. The index now preserves the upstream licence object as unverified data.
The contracts owner preserved and repaired the invalid navigation URL using a
verified encoded address. The original refusal and the two failing adapter
controls remain beside their passing successors. No source-list bytes were
changed by the index helper.

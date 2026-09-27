# Bounded source discovery

This is the source and local evidence for the operator's recurring research
collector. It finds public source records and writes private research outputs.
It makes no model calls, executes no downloaded code, approves no components,
and publishes nothing to the hosted catalogue.

The existing library ingestion transport supplies bounded HTTPS reads. The
collector uses the same source, licence and candidate boundaries described in
[library ingestion](../../src/loop_engine/core/library_ingestion/README.md).
These command-line adapters are internal tools used by a Practitioner task.
They introduce no runtime type or persistent intelligence layer. Roadmap
steps S-6.81 and S-6.214 own the continuing work.

## Current operation

The installed user timer runs four times daily. Each run has at most 20 public
requests, a 12-second request timeout, and a two-mebibyte response limit.
The service has a 384-mebibyte memory bound and a four-minute deadline.
The current configuration schedules 18 requests. It preserves the earlier
repository watches, papers, skills, plugins, package sources and news feed,
and selects two of the 40 searches in `coverage-topics-v1.json` each time.

The topic list covers APIs, data cleaning, quality, lineage, change data
capture, central storage, federation, decentralized storage, local-first
software, privacy, science, media, developer tools and other builder tasks.
Two topics per run visit all 40 in five days when all scheduled runs complete.
This describes the configured search rotation, not complete coverage of those
fields. The list can grow through a reviewed configuration revision.

Registry pagination carries the opaque next cursor into a later run. A partial
or failed page keeps the previous cursor. A terminal page starts a new bounded
traversal next time. A repeated cursor is recorded and resets the traversal.
The source can change during a traversal, so reaching its last page never
establishes a complete historical catalogue.

## Commands and records

Run the offline checks from the repository:

```bash
python3 -m unittest tools/test_source_discovery_rotation.py
```

Preview a configuration without effects:

```bash
python3 artifacts/source-discovery-2026-09-26/run_discovery.py \
  --core-configuration artifacts/source-discovery-2026-09-26/sources-core-v3.json \
  --extended-configuration artifacts/source-discovery-2026-09-26/extended-sources-v2.json \
  --rotation-configuration artifacts/source-discovery-2026-09-26/coverage-topics-v1.json \
  --state /absolute/private/research-state
```

Actual execution requires the two explicit network-read and local-write flags.
The state directory must already exist. The installed service file records
the operator's machine-specific paths; copying it alone is not an installation.
Its engine and transport files are pinned in `installation-v5-validated.json`.
Earlier installed engines are retained for rollback.

The scheduling configuration is `source_discovery_rotation/v1`; its completion
pointer is `source_discovery_coverage_state/v1`. A changed configuration refuses
the old pointer. Resolve that change through an explicit new traversal while
preserving the previous state. The combined run with coverage information is
`combined_source_discovery_run/v2`. These are private research records. They
are not catalogue admission records or a second task authority.

## Evidence and limits

The local suite passes 36 checks. Five deliberately broken implementations
are rejected: a stuck rotation, advancing after a partial registry page, and
ignoring the configuration identity, ignoring an overfull page, and accepting
malformed registry metadata. The installed engine also passes the same
36 checks. The first installed version-four run completed and collected
290 extended-source observations, including 40 from its two selected topic
queries. See `installed-run-v4.json`. Independent review found two response-handling
defects after that run. Both are repaired in installed version five. Its live
run used the saved registry cursor and visited the next two topic searches;
see `installed-run-v5.json`.

The failed first installed-test attempt is retained: its test fixture
`sources.json` was missing from the copied engine. The succeeding run includes
that fixture. Source descriptions and abstracts are omitted from extended
metadata exports. Public summaries still need source reading and original
authorship. Source discovery has no continuous language-model generation
dispatcher attached yet.

GitHub search has a per-query result ceiling and can return incomplete results.
The collector retains the returned coverage facts. It does not label a query's
first page as every repository. See the
[official search documentation](https://docs.github.com/en/rest/search/search).
Registry cursors follow the
[official registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/generic-registry-api.md).

New sources enter the existing source interrogation and candidate preparation
process. A directory listing, a captured schema, an executed operation and an
accepted task outcome remain separate evidence.

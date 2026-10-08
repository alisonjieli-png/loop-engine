# MCP discovery and Earth embedding source review

Kind: source review and candidate integration record. October 8, 2026 UTC.
No MCP connection, authentication, tool invocation, cloud-project change,
model call, dataset download or publication was performed for this review.

## MCP discovery

Four documentation resources were inspected: the official registry API
specification, Cloudflare's MCP documentation, Google's embedding catalog
and Earth Engine authentication guide. One unauthenticated registry GET used
`search=cloudflare`, `version=latest` and `limit=3`. It returned three rows and
a next cursor. The cursor was not followed; this was a bounded sample, not a
complete registry scan. Two name matches were third-party services, not the
Cloudflare publisher.

The registry's Cloudflare entry still listed old SSE declarations. The
[publisher documentation](https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/)
describes its `/sse` addresses as Streamable HTTP aliases and directs new
connections to `/mcp`. The four publisher-source entries use the latter
addresses. They are metadata declarations, not locally tested tools.

The directory's absent-auth case remains unknown. Only an explicit source
declaration may describe anonymous access. Source freshness and connection
qualification remain separate, including when an official registry verifies
a namespace. Existing daily directory refresh owns acquisition; no competing
registry, store or scheduler was created.

## Customer skill candidate

The [setup skill](../../tools/knowledge_radar/assets/plan_mcp_service_setup/SKILL.md)
and standard-library helper prepare a scoped plan from a dated table. The
table preserves the publisher file's review date and expires after one day;
regenerating from unchanged records does not renew it. Filtering is lexical,
not a service-quality ranking. No credential value is an accepted parameter.

The [candidate builder](../../tools/build_mcp_setup_candidate.py) reuses the
radar asset reader and native proposal contract. It labels this new source's
producer family `openai`, overriding the generic radar builder's historical
family default. Do not use that default to let an OpenAI producer review its
own skill. Passing helper tests is not admission.
The helper keeps one stable job identity when its source table changes;
dated copies must not inflate the capability count.

From a clean committed checkout, create a new private output folder:

```text
PYTHONPATH=src:tools python tools/build_mcp_setup_candidate.py --output /absolute/new/private/folder --write
```

Then use the existing native preparation, deterministic qualification,
non-producer review and catalogue publication owners. Preparation needs the
exact reviewed public revision and its cited bytes. The skill and source
table do not configure a client or give it permission to call a service.

## Google source

The exact source facts and access references are in
[the geospatial source table](../../tools/resources/satellite-embedding-source-table.json).
It describes annual feature data, not real-time imagery or a confirmed MCP
service. No tile or model weight was fetched.

Use that record to scope candidate helpers for bounded area/year selection,
version checks, vector comparison and spatial holdout evaluation. Verify
actual image properties before combining years or tiles. Pixels, vector
axes and parameter variations are not new harness components.

The [dataset catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL)
owns dataset terms; the
[authentication guide](https://developers.google.com/earth-engine/guides/auth)
owns account and project setup. An existing account or public dataset does
not authorize exports, billing or resource creation.

## Verification and remaining work

Owning checks exercise absent versus explicit authentication, each publisher
entry, exact package files, schemas, source dates, unsafe addresses, stale
tables, conflicting transports and false connection/effect claims. The
skill-creator validator checks its frontmatter; an independent behavioral
evaluation and native admission remain separate work.

The public MCP directory assets have not been rebuilt here. The existing
directory build must incorporate the reviewed source records before those
rows change on the website. Neither this source review nor the new skill
adds to the served component count until the normal release path completes.

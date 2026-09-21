# Searching and retrieving from the Baltor service

Kind: operating guide for a paying customer. It explains what a search
returns, why it returns short references instead of whole bodies, how to
choose one, how to download it, and what you are charged for.

Every request and answer below was run on 2026-09-21. Each one is marked
**deployed** when it was run against `https://app.baltor.ai` and **local**
when it was run against a local instance started from this repository, because
a download records service usage and a local instance keeps that record local.

## The shape of the work

```text
Search and retrieve
├── Search        small typed references, never a body, free
│   └── /api/v1/retrieval, or the intelligence_search tool
├── List          every item this account may see, free
│   └── /api/v1/provisioning, operation list
├── Manifest      one item's digest, size, licence and permissions, free
│   └── /api/v1/provisioning, operation manifest
└── Download      the body itself, measured
    ├── /api/v1/download, operation read, returns bytes
    └── /api/v1/provisioning, operation read, returns the body inside JSON
```

Search, list and manifest are free. Only a body read is measured. The service
says this itself: the discover answer carries `never_metered`, which lists
listing authorized items, a manifest with digests and sizes, a refusal before
metering, and reading the tenant's own usage.

## Why search returns references and not bodies

A step in a task needs to decide which material is worth loading before it
spends context on it. So search returns a small typed reference for each hit:
what the item is, where it came from, how large it is, under which licence,
and whether this account may download it. The answer states
`bodies_loaded` as false and the backend reports `returns_bodies` as false.

This also keeps the permission decision in one place. The reference tells you
whether a download would be allowed. The download itself is checked again, at
the moment it happens, against the account, the scope and the grant.

## A real search

**Deployed.** The account below is an operator-issued pilot account.

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/retrieval \
  -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"record_type": "service_retrieval_request/v1",
       "query": "review", "mode": "lexical", "top_n": 3}'
```

The answer, exactly as returned:

```json
{
 "record_type": "service_http_result/v1",
 "operation": "retrieval",
 "result": {
  "record_type": "service_retrieval_result/v1",
  "hits": [
   {
    "reference": {
     "identity": "example.review_inputs",
     "source_layer": "context_intelligence",
     "source_ref": "example:review-inputs@1",
     "body_digest": "9b0922f2dc282cf0101f78f00d307567b4d098f8fd3ca99bf76559dfb6bb9bd8",
     "descriptor_digest": "6b9fb64805be1f4167eb88d686b39c2071010a4a2f701e2b90a74fc6b27631c1",
     "record_type": "provisioning_item_binding/v1"
    },
    "purpose": "Review supplied material and preserve missing evidence",
    "kind": "instruction_file",
    "size_bytes": 336,
    "license": "MIT",
    "declared_effects": [],
    "harness_styles": [],
    "score": 0.1,
    "modes": ["lexical"],
    "qualification_basis": "host_attested",
    "body_allowed": true
   }
  ],
  "mode": "lexical",
  "bodies_loaded": false,
  "backend": {
   "modes": ["lexical", "hybrid"],
   "lexical_backend": "sqlite_fts5",
   "vector_backend": "deterministic_character_hash",
   "semantic_embedding_model_installed": false,
   "scope": "authorized_catalogue_metadata",
   "returns_bodies": false
  },
  "limitations": [
   "Hash vectors measure character similarity, not learned semantic understanding.",
   "Distribution references do not grant local code execution or independent Code admission."
  ]
 },
 "execution": {
  "runtime_type": "Loop",
  "loop_id": "loop1",
  "profile": "intelligence.search@1.0.0",
  "mode": "deterministic",
  "model_calls": 0,
  "definition_digest": "74156e87dfc1676e5b6b97871711734c9ca1a7e6177c6ff1451bd07055c87bbf"
 }
}
```

### The request fields

| Field | Required | Meaning |
|---|---|---|
| `record_type` | yes | Exactly `service_retrieval_request/v1`. Another value is refused. |
| `query` | yes | Text, at most 4096 bytes after encoding, not only spaces. |
| `mode` | no | `lexical` or `hybrid`. Default `lexical`. |
| `top_n` | no | A whole number from 1 to the published `search_results` limit, 50 on the deployed service. Default 10. |

Any other field is refused, so a typing mistake fails loudly instead of being
ignored.

### How to read a hit

| Field | What it tells you |
|---|---|
| `reference` | The exact identity of the item. Keep the whole object. |
| `identity` | The name you pass to manifest and read. |
| `source_layer` | Which of the four persistent intelligence layers the item belongs to. |
| `source_ref` | Where the material came from, with its version. |
| `body_digest` | The SHA-256 digest of the body you would download. |
| `descriptor_digest` | The digest of the descriptor, so a changed description is visible. |
| `size_bytes` | How large the body is, before you fetch it. |
| `license` | The licence the item declares. The host serves only licences it accepts. |
| `declared_effects` | What the material says it does. An empty list means none declared. |
| `qualification_basis` | `host_attested` or `authoritative`. It never means independently qualified. |
| `body_allowed` | Whether this account, with this token, may download the body. |
| `score` and `modes` | The ranking value and which retrieval modes contributed. |

`score` orders the hits within one answer. It is not a quality measurement and
it is not comparable between queries.

### What the two modes do

`lexical` uses the SQLite full text index. `hybrid` adds a character hash
vector. The backend section is explicit that
`semantic_embedding_model_installed` is false, so neither mode is a learned
semantic match. The answer repeats that limitation in every result.

## Selecting one item

Ask for its manifest before you download. A manifest is free and it tells you
what a download would cost you in bytes and whether it is permitted.

**Deployed.**

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/provisioning \
  -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"record_type": "service_provisioning_request/v1",
       "operation": "manifest", "identity": "example.review_inputs"}'
```

```json
{
 "record_type": "service_http_result/v1",
 "operation": "manifest",
 "result": {
  "record_type": "provisioning_manifest/v2",
  "tenant_id": "pilot-owner",
  "identity": "example.review_inputs",
  "kind": "instruction_file",
  "purpose": "Review supplied material and preserve missing evidence",
  "digest": "9b0922f2dc282cf0101f78f00d307567b4d098f8fd3ca99bf76559dfb6bb9bd8",
  "source_layer": "context_intelligence",
  "source_ref": "example:review-inputs@1",
  "size_bytes": 336,
  "license": "MIT",
  "declared_effects": [],
  "styles": [],
  "tags": {"record_type": "intelligence_tags/v1"},
  "exposure": "metadata_only",
  "availability": "remote",
  "body_included": false,
  "qualification_basis": "host_attested",
  "metering_policy": "required",
  "body_allowed": true,
  "verify_before_use": true,
  "metered": false
 }
}
```

Two fields decide what happens next. `body_allowed` says whether the download
is permitted. `metering_policy` is `required` when a successful download
records one measured unit, and `unmetered` when it does not.

You may also pin the exact bytes you selected. Add `expected_digest` with the
`body_digest` from the search hit, on a `manifest` or a `read`. If the item has
changed since you selected it, the service refuses instead of quietly giving
you different material. Verified **local** on 2026-09-21: a manifest with a
digest that does not match answered status 404 with `item_unavailable`, the
same answer the service gives for an item you may not see, because a refusal
never reveals more than it must.

## Downloading a body

`/api/v1/download` returns the bytes themselves, with the digest in a header.
This is the endpoint the capabilities record names in `download_endpoint`.

**Local.** This request was run against a local instance, because a download
on the deployed service records a usage row.

```bash
curl -sS -X POST http://127.0.0.1:8099/api/v1/download \
  -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"record_type": "service_provisioning_request/v1",
       "operation": "read", "identity": "example.review_inputs",
       "request_id": "documentation-download-1789995512"}' \
  --output review-inputs.md --dump-header -
```

The answer headers, exactly as returned:

```text
content-type: application/octet-stream
x-loop-engine-record-type: service_download/v1
x-content-sha256: 9b0922f2dc282cf0101f78f00d307567b4d098f8fd3ca99bf76559dfb6bb9bd8
content-disposition: attachment; filename="intelligence.txt"
```

The body was 336 bytes of UTF-8 text, and its SHA-256 digest matched both the
header and the `body_digest` from the search hit. Always compare the two
before you use the material. The manifest says `verify_before_use` for exactly
this reason.

`request_id` is required and it is yours to choose. It identifies one download
attempt. Repeating the same `request_id` for the same item does not record a
second measured unit, which is what makes a retry safe.

### The same read inside JSON

`/api/v1/provisioning` with `operation` set to `read` returns the body inside
the answer instead of as bytes, together with the metering acknowledgment.
It refuses with `download_required` when the body is larger than the published
`inline_body_bytes` allowance, which is 16384 bytes on the deployed service.

**Local.** The interesting part of the answer:

```json
{
 "record_type": "provisioning_body/v2",
 "tenant_id": "demo",
 "identity": "example.review_inputs",
 "digest": "9b0922f2dc282cf0101f78f00d307567b4d098f8fd3ca99bf76559dfb6bb9bd8",
 "size_bytes": 336,
 "body": "# Review supplied material\n...",
 "qualification_basis": "host_attested",
 "metered": true,
 "metered_unit": "provisioned_item",
 "metering_acknowledgment": {
  "committed": true,
  "durability": "durable",
  "record_type": "provisioning_meter_acknowledgment/v1"
 }
}
```

## What is free, what is measured, and what one unit is

One measured unit is **one downloaded item**: one body read that the service
accepted and recorded. The unit is named `provisioned_item` in every record
that reports it.

| Operation | Measured |
|---|---|
| Search, at `/api/v1/retrieval` or through `intelligence_search` | No |
| Discover and list, at `/api/v1/provisioning` | No |
| Manifest, at `/api/v1/provisioning` | No |
| Reading your own usage, at `/api/v1/usage` | No |
| A refusal, at any address, before the body is released | No |
| A body read, at `/api/v1/download` or `/api/v1/provisioning` | Yes, one unit, when `metering_policy` is `required` |
| A repeat of a body read with the same `request_id` | No |

Check what you have used at any time. This costs nothing.

**Deployed.**

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  https://app.baltor.ai/api/v1/usage
```

```json
{
 "record_type": "service_http_result/v1",
 "operation": "usage",
 "result": {
  "record_type": "durable_tenant_usage/v1",
  "tenant_id": "pilot-owner",
  "records": 10,
  "totals": {"provisioned_item": 10.0},
  "durability": "durable"
 }
}
```

`records` is how many body reads were recorded. `totals` is the same count by
unit. `durability` is `durable` when the count is written to durable storage.

### The same read twice, measured once

**Local.** Verified on 2026-09-21, in this order:

1. Usage before: `records` 0.
2. Download `example.review_inputs` with a new `request_id`: 200, 336 bytes.
3. Usage after: `records` 1, `totals` `{"provisioned_item": 1.0}`.
4. Download again with the **same** `request_id`: 200, the same 336 bytes.
5. Usage after the repeat: `records` still 1.

That is the safety rule to build on. If a download times out or your process
restarts, retry with the same `request_id` and you are not charged twice. Use
a new `request_id` only when you genuinely want another item or another
measured read.

Reading your own usage is free, and the service says so in `never_metered`.
There is no overage billing at launch.

## Searching through your harness instead of curl

A connected client sees five tools. Their names come from the service, not
from this page: `intelligence_search`, `provisioning_discover`,
`provisioning_list`, `provisioning_manifest` and `provisioning_read`.

`intelligence_search` takes `query`, and optionally `mode` and `top_n`. It
returns exactly the record shown above. `provisioning_read` takes `identity`
and `request_id`, and it is the only tool the server marks as not read only,
because it is the only one that records a measured unit.

## Related pages

- [Getting set up](service-getting-set-up.md)
- [Serving and connections](service-serving-and-connections.md)
- [Troubleshooting](service-troubleshooting.md)
- [Intelligence layers](../components/intelligence-layers/README.md), for what
  the four layers hold

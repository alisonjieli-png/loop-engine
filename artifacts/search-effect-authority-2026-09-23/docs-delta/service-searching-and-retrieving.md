# Searching and retrieving

Kind: customer guide to selection, references, manifests and exact-byte downloads.

Search returns small references so a step can choose useful material before
loading its body. Download only the items the task needs, then verify their
bytes and how the harness uses them.

## Search the authorized catalogue

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/retrieval -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Content-Type: application/json" -d '{"record_type":"service_retrieval_request/v2","query":"split address lines","mode":"lexical","top_n":3}'
```

The result is `service_retrieval_result/v1`. It holds `hits` and states
`bodies_loaded` as false. The items and scores depend on your account, the
current catalogue and the query; this example does not assume a particular hit.

| Request field | Meaning |
| --- | --- |
| `record_type` | Exactly `service_retrieval_request/v2`. |
| `query` | Nonempty search text, at most 4096 UTF-8 bytes. |
| `authority_effects` | Optional unique array of declared effect names already permitted for your step. Omitted or empty means no declared effects. This selects metadata, not execution permission. |
| `mode` | `lexical` or `hybrid`; default `lexical`. |
| `top_n` | Positive whole number within the advertised `search_results` limit; default 10. |
| `filters` | Up to eight declared, public, filterable catalogue attributes. Conditions include `equals`, `any_of`, `at_least` and `at_most`. |

Unknown fields and unsupported filter shapes are refused. `lexical` uses the
full-text index. The current `hybrid` mode adds character-hash similarity;
`semantic_embedding_model_installed` is false. A score orders hits within that
answer. It is not a correctness score or a cross-query quality measurement.

### Material that declares effects

A search can name `authority_effects` to include material whose declared effects
fit the step's existing permissions. Omit it or send an empty array to consider
only material with no declared effects. For example, a step already authorized
to read files and run a local process can search with:

```json
{"record_type":"service_retrieval_request/v2","query":"validate a local data file","mode":"lexical","authority_effects":["reads_fs","spawns_process"]}
```

Read the current request version from `/api/v1/capabilities`. Version 1 requests
are refused; update the client rather than removing its selection fields. The
protocol tool publishes its current shape through the tool list.

This selects material; it does not grant execution permission. A manifest or
read must carry the appropriate selection fields too. A metadata `filters`
condition does not replace this selection or your harness's own permissions.

## Read the reference

Keep the complete `reference` returned for the item.

| Field | Meaning |
| --- | --- |
| `identity` | The selected item identity. |
| `source_layer` | Where its source belongs. Harness material uses `harness_local`; this is not one of the four persistent engine layers. |
| `source_ref` | The source reference and its version. |
| `body_digest` | SHA-256 of the body to be downloaded. |
| `descriptor_digest` | Identity of the accompanying descriptor. |
| `size_bytes` | Body size. |
| `license` | Declared licence. |
| `declared_effects` | Operations the material declares. |
| `qualification_basis` | The service's reported qualification basis, such as `host_attested`. |
| `body_allowed` | Whether this credential may read the body. |
| `package` | File inventory when the item belongs to a catalogue package. |

A catalogue release is named in `catalogue_release`. Retain it when reporting
an unexpected result. A new search can return a different release or digest.

## Inspect the manifest

Send a `manifest` operation to `/api/v1/provisioning` with the selected
`identity`. Add `expected_digest` using the reference's `body_digest`, so a
changed body is refused rather than substituted. The following is a request
shape: replace the two example strings with values from your search.

```json
{"record_type":"service_provisioning_request/v1","operation":"manifest","identity":"item-identity","expected_digest":"selected-digest"}
```

The manifest reports the digest, licence, size, `body_allowed`,
`metering_policy` and `verify_before_use`. A manifest is not a body download and
is not metered. Permission is checked again when the body is requested.

## Download exact bytes

For bytes, send the `read` operation to `/api/v1/download`. Supply the identity,
expected digest and a new `request_id` for this logical read. Keep the request
identity if you retry an uncertain outcome.

The response carries `X-Content-SHA256` and `X-Loop-Engine-Record-Type` headers.
Compute SHA-256 over the downloaded bytes and compare it with the selected
manifest. The download endpoint returns bytes, not a JSON usage acknowledgment.

### One file of a package

A package body is a `catalogue_package/v1` document listing its files. A file
entry names `path`, `digest`, `size_bytes`, `media_type` and `role`. Retrieve one
file through `/api/v1/download` by adding that exact `path` to the read request.

```json
{"record_type":"service_provisioning_request/v1","operation":"read","identity":"item-identity","expected_digest":"selected-digest","request_id":"one-package-read","path":"scripts/tool.py"}
```

These are example identity and path values, not a promise that such an item is
in your account. Use values from the actual package. The response digest must
match the file entry, while `expected_digest`, when supplied, binds the selected
item body. Reuse the same `request_id` across that package's files to share its
item-level metering unit. A missing path returns `package_file_not_found`.

### Inline reads

An inline `read` through `/api/v1/provisioning` returns the body inside
`provisioning_body/v2`, with metering fields. Bodies above `inline_body_bytes`
require the download endpoint. Package file paths also require that endpoint;
they are not accepted as inline reads.

## Finish the step

A body may need a native directory, explicit plugin activation or declared
dependencies before a harness can use it. Preserve the package's relative
paths. A download does not grant local process, network or model authority.
Verify loading and check the resulting work against your task.

See [Usage and what you pay for](service-usage-and-what-you-pay-for.md) for retries
and [Serving and connections](service-serving-and-connections.md) for the wire
protocol, limits and refusal codes.

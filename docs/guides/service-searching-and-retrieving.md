# Searching and retrieving

Kind: customer guide to selection, references, manifests and exact-byte downloads.

Search returns small references so a step can choose useful material before
loading its body. Download only the items the task needs, then verify their
bytes and how the harness uses them.

## Find free Public Good files

The [Public Good collection](https://baltor.ai/public-good) is free to download
with an enabled account. No subscription or nonprofit status is required.
Connect an OAuth-capable harness to `https://baltor.ai/mcp` using the
[account-linking steps](service-serving-and-connections.md#oauth-connections).
Metadata uses `provisioning:metadata`; downloads also need `provisioning:read`.

Call the `public_good_files` protocol tool with a goal number as a string:

```json
{"goal":"6","page":1,"page_size":20}
```

Optional filters are `query`, `media_type`, `initiative` and `package`.
Leave `goal` empty to include all goals, or use `related` for material without
an explicit SDG association. `page_size` is at most 50. The same body-free
result is available at `GET /api/v1/public-good/files` without signing in;
protocol calls still require a valid connection.

The `public_good_file_collection/v1` result keeps each file's SHA-256 and
all its eligible package placements. Select a placement with `matches_filters`
set to true. Inspect its package with `provisioning_manifest`, then pass that
placement's `identity`, `body_digest` as `expected_digest`, and `path` to
`provisioning_read`, with a new `request_id` for the logical download. Verify
the exact returned bytes against `file_sha256`. A file can require other
files in its package; retain its instructions, dependencies and relative paths.

Counts distinguish useful files from support files and repeated placements.
Goal counts overlap. Follow `has_next` and increase `page` to browse further;
if `eligible_fingerprint` changes, restart pagination rather than combining
different collection snapshots. Eligibility, scopes and declared step effects
are checked again at download. Free downloads have separate request and byte
limits, add no paid usage, and do not authorize running the downloaded code.

## Recorded demonstrations

The guided data-cleanup and competition examples reproduce the packaged
starter catalogue. They are not live searches. Their displayed hashes and
ordering belong to the
[recorded catalogue](https://github.com/alisonjieli-png/loop-engine/blob/e089582cb50d0bc4e5b28c915ac22edcb3f74f62/examples/29_intelligence_service/starter-catalogue/host-release/manifest.json),
whose SHA-256 is
`246bd27c8beeed4c84ad878c452646dc6333aacf3974e67560a3b7ecaeb2cf52`.
Each example declares that snapshot in its metadata and visible description.

The active catalogue can contain newer versions and different search results.
Your harness must make a fresh authorized search, choose its reference, inspect
the manifest and verify the downloaded bytes against that selected digest.
Do not copy a hash from a recorded example into a current download request.
Publication checks verify both the recorded source and current availability;
they do not replace the customer's own permission and integrity checks.

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
| `authority_effects` | Optional unique array of declared effect names already permitted for your step. When present, the search shows only material whose declared effects are all in it, and a read is checked against it. Omitted, the search shows every item your account may use, each marked with the effects your step would still have to declare; your step's effects are then the ones your client configuration states in the `Baltor-Step-Effects` header, or reading files (`reads_fs`) when it states none. An empty array shows only material with no declared effects. This selects metadata, not execution permission. |
| `mode` | `lexical` or `hybrid`; default `lexical`. |
| `top_n` | Positive whole number within the advertised `search_results` limit; default 10. |
| `filters` | Up to eight declared, public, filterable catalogue attributes. Conditions include `equals`, `any_of`, `at_least` and `at_most`. |

Unknown fields and unsupported filter shapes are refused. `lexical` uses the
full-text index. The current `hybrid` mode adds character-hash similarity;
`semantic_embedding_model_installed` is false. A score orders hits within that
answer. It is not a correctness score or a cross-query quality measurement.

### Material that declares effects

Seeing an item is not permission to use it, so the two are separate. A search,
a list or a manifest that does not name `authority_effects` shows every item your
account may use. Each hit and each listed row names its `declared_effects` and
its `effects_to_declare`: the effects the item declares that your step did not
declare. The answer names your step's effects as `step_effects`. Your step
declares them in the `Baltor-Step-Effects` header of your client configuration,
for example `Baltor-Step-Effects: reads_fs, writes_fs, spawns_process, network`,
or holds reading files (`reads_fs`) when the configuration states none.

A read or a download checks the item's declared effects against your step's.
When the step did not declare all of them, the service refuses the read with
`step_effects_required` (403) before anything is read or counted. The refusal's
`details` record, `service_step_effects_refusal/v1`, names the item's
`declared_effects`, the `step_effects` the request held, the
`effects_to_declare`, the `header` to set and a `header_value` that would
declare them. An item that declares effects therefore never reaches a step that
did not declare them.

A search can still name `authority_effects` to see only material whose declared
effects fit the step's existing permissions; the named effects are then the
step's effects for a read as well. Send an empty array to consider only material
with no declared effects. For example, a step already authorized to read files
and run a local process can search with:

```json
{"record_type":"service_retrieval_request/v2","query":"validate a local data file","mode":"lexical","authority_effects":["reads_fs","spawns_process"]}
```

Read the current request version from `/api/v1/capabilities`. Version 1 requests
are refused; update the client rather than removing its selection fields. The
protocol tool publishes its current shape through the tool list.

This selects material; it does not grant execution permission. A metadata
`filters` condition does not replace this selection or your harness's own
permissions.

### Filter by the kind of step

Each served item carries the kinds of step it supports as the `step_functions`
attribute, from a fixed list: `acting`, `analysis`, `building`, `operating`,
`planning`, `reasoning`, `research`, `reviewing`, `verification` and `writing`.
Rules write the tags from the item's own words and file roles, so a tag says
what the item is about, not that a reviewer judged it good at that. An item
whose words name no function has no tag. The `harness_kind` attribute names the
kind of file a harness picks up, such as `skill`, `hook` or `subagent`. A step
about to verify a change can ask for verification and reviewing material:

```json
{"record_type":"service_retrieval_request/v2","query":"run the tests before merging","mode":"lexical","filters":{"step_functions":{"any_of":["verification","reviewing"]}}}
```

### Filter by job title, industry, level, language and geography

A reviewed catalogue that `tools/write_reviewed_catalogue.py` writes also
carries five facet attributes, each a keyword list from a declared vocabulary
in `src/loop_engine/data/library_facets.yaml`: `job_titles`
(the pinned occupation grid and the packaged occupation seeds, such as
`Software Developers`), `industries` (a declared list of thirty-four, such as
`healthcare`), `levels` (`student`, `junior`, `mid`, `senior`, `lead`,
`executive`), `languages` (`english` by default, else one of twelve found by
script or stopwords) and `geographies` (countries and regions, such as
`United States` or `European Union`). Rules write them from the item's own
words, and an item whose words name nothing has no value for that facet. The
signed-in library table filters on them and each search result lists them;
the public pages show none of them. A release built from an older reviewed
catalogue does not carry them until that catalogue is written again. On
September 26, 2026 no served release declares them, so a filter on them is
refused with `search_filter_not_allowed`. A release that
`tools/combine_reviewed_catalogues.py` combines after this change declares
them, and its items carry values only when their reviewed catalogue was
written after this change.

```json
{"record_type":"service_retrieval_request/v2","query":"summarize clinical notes","mode":"lexical","filters":{"industries":{"any_of":["healthcare"]},"levels":{"equals":"senior"}}}
```

Every hit returns its shown attributes under `attributes`, the tags among
them. A release whose schema does not declare an attribute refuses a filter on
it with `search_filter_not_allowed`; read the active release's schema from the
capabilities answer before filtering on it.

## List the library in pages

A `list` operation of `service_provisioning_request/v2` names every item your
account is offered, as descriptions only. The library holds thousands of items,
more than one answer carries, so ask for it in pages: add `page_size`, then send
each `next_cursor` back unchanged until it is null.

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/provisioning -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Content-Type: application/json" -d '{"record_type":"service_provisioning_request/v2","operation":"list","page_size":500}'
```

| Request field | Meaning |
| --- | --- |
| `page_size` | Whole number from 1 to 1000. A page holds at most this many items, and fewer when more would not fit the service's answer size. |
| `cursor` | The `next_cursor` of the previous page, unchanged. Leave it out for the first page. |

Keep every other field the same from page to page, including
`authority_effects` and `library_tiers`, because a cursor continues only the
list it was issued for. A page is `provisioning_list_page/v1`:

| Field | Meaning |
| --- | --- |
| `items` | The items of this page, in the same form and order as a whole list. |
| `next_cursor` | Send it back to read the next page. It is null after the last page. |
| `total_offered` | How many items this list offers your account in the served library. |
| `catalogue_release` | The served library release, or null for a library served without one. |
| `withheld_count` | How many items this request held back. Every page states it. |
| `withheld` | The held-back items with their reasons, at most 200, on the first page only. Later pages list none. |

A list without `page_size` is still answered in one `provisioning_list/v3`
answer while it fits. When it does not fit, the service refuses it with
`response_limit_exceeded`, and the refusal's next action names `page_size`.

| Code | Status | Meaning |
| --- | --- | --- |
| `list_page_size_invalid` | 400 | The page size is missing beside a cursor, not a whole number, or outside 1 to 1000. |
| `list_cursor_invalid` | 400 | The service did not issue that cursor for your account and this list, or it restarted since. Ask again without a cursor. |
| `list_release_changed` | 409 | The library served to your account changed after the first page. Ask again from the first page and use only the new pages. |

The library table on the signed-in pages reads the library this way. A list is
descriptions only, so the table asks with every step effect the capabilities
record names under `step_effects`, and it lists every file your account may use
with the effects the file declares. Before it checks or fetches a file that
declares more than reading files, it names those effects in plain words and
asks you to confirm. It then asks for that one file with exactly its declared
effects. The search on the same page asks with every step effect too. Your
harness keeps its own rule: the `Baltor-Step-Effects` header, or reading files
when it states none, decides which items it may read.

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
{"record_type":"service_provisioning_request/v2","operation":"manifest","identity":"item-identity","expected_digest":"selected-digest"}
```

Use version 2, as the search does. It asks with the same step effects and your
account's library setting, so an item the search offered can be checked with
the same selection. The library presents all permitted components together.
Source, licence, declared effects and review evidence describe each component.
The protocol still carries `library_tier` and `library_tier_label` as internal
review metadata. Clients should not turn them into customer-facing classes.
Version 1 selects a narrower review profile and is not the current onboarding
path. Without `authority_effects`, it receives no item that declares an effect.

The manifest reports the digest, licence, size, review metadata, `body_allowed`,
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
{"record_type":"service_provisioning_request/v2","operation":"read","identity":"item-identity","expected_digest":"selected-digest","request_id":"one-package-read","path":"scripts/tool.py"}
```

These are example identity and path values, not a promise that such an item is
in your account. Use values from the actual package. The response digest must
match the file entry, while `expected_digest`, when supplied, binds the selected
item body. Reuse the same `request_id` across that package's files to share its
item-level metering unit. A missing path returns `package_file_not_found`.

### Inline reads

An inline `read` through `/api/v1/provisioning` returns the body inside
`provisioning_body/v3` for a version 2 request (`provisioning_body/v2` for
version 1), with metering fields. Bodies above `inline_body_bytes`
require the download endpoint. Package file paths also require that endpoint;
they are not accepted as inline reads.

### Package files through the protocol tool

The protocol tool `provisioning_read` delivers a package's files, not only the
document that lists them. A single-file item still answers `provisioning_body/v3`
with its text in `body`. A package answers `provisioning_package_read/v1`:

- `package` is the item's package listing, with its `package_digest`. The
  SHA-256 of the canonical `catalogue_package/v1` document built from `files` is
  that digest, and it equals the `body_digest` the search returned.
- `files` holds as many whole files as fit in one protocol answer, in path
  order. Each file names `path`, `digest`, `size_bytes`, `media_type`, `role`,
  `encoding` and `content`. Valid UTF-8 travels as its own text with the
  encoding `utf-8`; any other file travels as base64 of its exact bytes with the
  encoding `base64`. The SHA-256 of the decoded bytes must equal `digest`.
- `next_file_offset` names the first file of the next page. Send the same read
  again with `file_offset` set to it, and the same `request_id`. It is `null` on
  the last page.
- `omitted` names a file that cannot fit in any protocol answer, with the reason
  `too_large_for_one_protocol_answer`, or `larger_than_the_download_limit` for a
  file this service does not deliver. Fetch the first kind through
  `/api/v1/download` by its `path`.

Add `path` instead of `file_offset` to read one file. A read names one or the
other; both answer `package_selection_conflict`, and an offset past the last
file answers `file_offset_out_of_range`. A wrong path answers
`package_file_not_found`. These three refusals are not counted.

One answer, counting its structured copy and its text copy, stays within the
`response_bytes` limit that `/api/v1/capabilities` reports under `limits`. The
capabilities record names this delivery under `delivery.protocol_package_files`
and its record under `delivery.protocol_package_record_type`.

## Finish the step

A body may need a native directory, explicit plugin activation or declared
dependencies before a harness can use it. Preserve the package's relative
paths. A download does not grant local process, network or model authority.
Verify loading and check the resulting work against your task.

## Report a problem with an item

Every served item can be reported. Send the `report` operation to
`/api/v1/provisioning` with the item's `identity`, the `expected_digest` you
were served and a `reason` of up to 400 characters of plain text. The signed-in
pages offer the same report from the detail panel of the library table and from
each search result card. A harness sends it through the protocol tool
`provisioning_report`, with the same three fields.

```json
{"record_type":"service_provisioning_request/v2","operation":"report","identity":"item-identity","expected_digest":"selected-digest","reason":"The steps delete files outside the project."}
```

The answer is `service_catalogue_report_result/v1`. Its `state` is `withdrawn`
when the report withdrew the item and `recorded` when it did not yet; `withdrawn`
says the same as a Boolean, `reports` counts the accounts that reported this
exact item version, `reports_to_withdraw` gives the applicable withdrawal threshold,
`flags` counts staff flags, and `review_state` is `queued`, because every
report queues the item for the full review.

The service chooses the withdrawal rule from the component's recorded review
profile. Read `reports_to_withdraw` and `withdrawn` from its answer; the caller
does not choose the threshold. Every report queues the component for review.
A staff flag withdraws the item version immediately.

A report counts once for each account and item version. Sending it again is the
same record. A withdrawn item leaves search, listing and download within the
service's refresh interval, one minute on the hosted service, and a read of it
answers `item_withdrawn` at once. The withdrawal keeps the item's record and the
reason, both shown on the public library page. A withdrawn item version is never
served again by a later release; a new review of new bytes is needed. Only a
staff member can send the `flag` operation, which withdraws the item version at once.

| Code | Status | Meaning |
| --- | --- | --- |
| `report_reason_invalid` | 400 | The reason is empty, longer than 400 characters or holds control characters. |
| `selected_body_digest_mismatch` | 400 | The service serves other bytes than the report names. Search again and report the digest you now see. |
| `item_unavailable` | 404 | No served item has that identity. |
| `item_withdrawn` | 404 | The item version is already withdrawn. |
| `staff_role_required` | 403 | Only a staff member can flag. Your report still counts. |
| `catalogue_reports_unavailable` | 503 | This host does not refresh its catalogue, so it takes no reports. |

See [Usage and what you pay for](service-usage-and-what-you-pay-for.md) for retries
and [Serving and connections](service-serving-and-connections.md) for the wire
protocol, limits and refusal codes.

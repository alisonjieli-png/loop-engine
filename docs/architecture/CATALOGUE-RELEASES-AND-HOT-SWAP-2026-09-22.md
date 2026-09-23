# Catalogue releases without a redeploy

Kind: dated design record for roadmap step S-6.62. It records the owner's
question, the prior art that was read, what this repository already had, the
decision, and the limits measured on one workstation. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. The
[service runtime guide](../../src/loop_engine/core/service_runtime/README.md#catalogue-releases)
describes the current behaviour, and the
[operations runbook](../guides/launch-setup-runbook.md#publish-and-roll-back-a-catalogue-release)
holds the operator procedure.

## The question

The owner asked on September 22, 2026: "In the future how can we add harness
intelligence files and have their attributes/searchable columns/details
without having to redeploy the entire system". Until this change one new item
needed a commit, a continuous integration run, an image build and a deploy:
the reviewed manifest was copied into the image, read once at start, and
served search built a new full-text table and new hash vectors for every
request. Every account's grants were a copied list, refreshed only by
`loop-engine service apply-grants` after a release.

The owner added two directions the same evening. A harness intelligence item
is any file a harness picks up from its working directory, not only Markdown:
instruction files such as `AGENTS.md`, skills with scripts, references and
assets, subagent definitions, commands, hooks, protocol server configurations,
plugin manifests and executable tools. And the library target is 100,000
files, with 10,000 as the first milestone.

## The answer in one tree

```text
Catalogue release, published while the service runs
├── Body store edge: catalogue_body_store/v1
│   ├── first engine: immutable files on the service volume, sha256/<first two>/<digest>
│   └── later engine: object storage behind the same edge, not built
├── Records in the existing service store, through the existing atomic batch
│   ├── catalogue_state/v1              marker; an image that does not understand it refuses to start
│   ├── catalogue_attribute_schema/v1   attributes declared as data
│   ├── catalogue_item_version/v1       one immutable record for each item version digest
│   ├── catalogue_release/v1            items, schema digest, added, changed and withdrawn, notes
│   ├── catalogue_release_pointer/v1    the active release, moved under an expected-version guard
│   └── catalogue_withdrawal/v1         honoured by every later release, rollback and image
├── Operator commands in `loop-engine service`
│   ├── publish-catalogue, rollback-catalogue, withdraw-catalogue-item
│   ├── catalogue-status (reads only)
│   └── follow-catalogue-release (grants that follow the active release)
└── Serving
    ├── one immutable view for each release, with one reusable search index
    ├── a refresher in the application lifespan that verifies every body, then swaps
    └── search over declared attributes, filters over public filterable ones
```

## Prior art that was read

The reading was bounded to the question: how a search engine declares its
fields, how a registry stores content by digest, and how a schema changes
without breaking readers.

| Source | What it does | What this design takes from it |
|---|---|---|
| [Meilisearch index settings](https://www.meilisearch.com/docs/reference/api/settings) | `searchableAttributes`, `filterableAttributes`, `sortableAttributes` and `displayedAttributes` are declared settings. Filtering on an attribute that is not declared filterable returns `invalid_search_filter` ([error codes](https://www.meilisearch.com/docs/reference/errors/error_codes)). Two indexes can be swapped. | Adopted: the four flags and the typed refusal of an undeclared filter. Adapted: the swap is one assignment of an immutable view. |
| [Typesense collections](https://typesense.org/docs/29.0/api/collections.html) | A schema names each field with a type and `facet`, `index`, `sort` and `optional` flags, rejects documents whose values do not match the declared types, changes a field only by dropping and adding it, and points an alias at a new collection for reindexing without downtime. | Adopted: a closed type set and refusal of mistyped values. Adapted: the active release pointer plays the alias. |
| [Elasticsearch dynamic mapping](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dynamic) | With `dynamic: strict`, a document with an unknown field is rejected; new fields must be added to the mapping explicitly. | Adopted: an item that names an undeclared attribute is refused before publishing. |
| [OCI image layout](https://github.com/opencontainers/image-spec/blob/main/image-layout.md) | Blobs live at `blobs/<alg>/<encoded>` and their content must match the digest; `index.json` is the entry point. | Adopted: content addressing for bodies, and a package digest over the file list, the way a manifest lists layers. |
| [npm unpublish policy](https://docs.npmjs.com/policies/unpublish) | A published version can never be used again for other content, and deprecation is preferred to removal. | Adopted: immutable item versions and releases. Adapted: a durable withdrawal record instead of deletion. |

## What this repository already had

AGENTS.md forbids a parallel store or a second source of truth, so each
existing contract was checked first.

| Existing contract | Decision | Reason |
|---|---|---|
| `ServiceCatalogBinding` and the `catalog_atomic_write_batch/v1` contract in `core/service_runtime/storage.py` | Adopted | Every catalogue record is a service record in the same collection and namespace, written with exact read-set guards. The pointer move, the release record, the withdrawals and the marker commit in one batch. |
| `ContextArtifactRef` and `ContextArtifactStore` in `core/context_artifacts.py` | Adapted | The object key `sha256/<first two>/<digest>` is reused. The class is not, because it creates folders when constructed, follows symbolic links in its root and object folders, and has no read-only mode; changing those defaults would change context compaction for its callers. |
| `load_host_manifest` and the host licence and family policies in `http_entrypoint.py` | Adopted | The bundle reader applies the same rules in the same order: family, then licence, then approval, then exact digest and size. Two rules are added: the approval names the digest it covers, and a package with a runnable file declares the process effect. |
| `tools/build_host_catalogue_manifest.py` and its review index | Adopted | The bundle builder reads the review record through the same functions, so a rejected, unreviewed or changed item is refused the same way. |
| `HarnessIntelligenceItem`, `ProvisioningQualification` and `ProvisioningServer` | Adopted | The served item, the approval and every disclosure decision are unchanged. Search asks the provisioning list about its candidates. |
| `core.retrieval.Retriever` | Adapted | The text, tokens, hash features and reciprocal rank fusion are the same. The class is not reused, because its SQLite connection belongs to one thread and its vectors are Python lists; at 10,000 items it took 11.2 seconds and 166 megabytes to build on this workstation, and a hybrid query took about one second. |
| `PreparedCatalogueSearch` in `core/harness_intelligence_search.py` | Not wired | Its measured default ranks better on held-back queries, but the served ranking must stay comparable with the recorded baseline in this change. Serving the measured policy is a separate step under S-6.32. |
| `RecordOperationService` and managed records | Rejected | It governs note and report collections, with a human-approved effect digest for each write. Catalogue records need machine-verified content addresses and one atomic pointer move, which the service store binding already provides. |

## Decisions

1. **Bodies are content-addressed on the volume.** A host-declared folder, never
   inside the image, holds each file once under its SHA-256 digest. Reading opens
   the object without following a symbolic link and checks its size and digest.
   Writing uses a temporary file and a hard link, so an existing name is never
   replaced, and every folder on the way must be a real folder. A bulk writer
   flushes once with `sync()` before any record names its bodies.
2. **An item is a package.** One to 64 files, each with a placement path, digest,
   size, media type and one of thirteen roles. A path never names `..`, `.` or a
   `.git` folder, and two paths that differ only in letter case are one
   placement. A one-file UTF-8 text package serves the file itself, so current
   clients read it unchanged. Any other package serves its canonical package
   document, and each file is downloaded by path with its own digest, charged
   once under the same request identity.
3. **A release is a record, not an image.** Its identity is the digest of its
   canonical content. Publishing the same content again changes nothing. A
   release is active only after its schema, every item version and every body
   read back, in the batch that moves the pointer.
4. **Attributes are data and never authority.** A new attribute of an existing
   type is a schema change in the bundle. A name that is a typed field, or whose
   word begins with a stem such as `effect`, `licen`, `permi`, `grant`, `approv`
   or `review`, is refused. Internal attributes are stored and never searched,
   filtered, sorted or shown. `sortable` is recorded; no route sorts on it yet.
5. **Grants can follow the release.** Version 2 of the grants record gives an
   account every approved item of the served view minus explicit denials.
   Version 1, the snapshot, stays the other engine. `apply-grants` never writes
   a snapshot over a following account.
6. **Withdrawals outlive releases, rollbacks and images.** A withdrawal names an
   item identity and the exact body digest. A release that lists a withdrawn
   version is refused, a rolled-back view leaves it out, and every manifest and
   body read checks the withdrawal record first, so a withdrawal recorded after a
   view was built is refused at once.

## Rolling back the image is a separate rollback

Moving the pointer back is one rollback. Deploying an older image is another,
and an older image that does not understand a withdrawal could serve the item
again. Two guards make that impossible or explicit.

```text
Image rollback across catalogue state
├── The store marker catalogue_state/v1 names a state version
│   ├── an image refuses to start on a version it does not list
│   └── a later release that adds a record an older image must not ignore raises it
├── Every catalogue command needs the host file's catalogue section
│   └── an image that predates this change refuses a host file with that section
└── An image that understands the marker refuses to start when the store holds
    catalogue state and the host file hides its section
```

Release 15 (revision `a51ac96`) predates these records. Before the operator
adds the `catalogue` section to `/data/host.json`, nothing changes for it.
After that, release 15 refuses the host file at start with
`unsupported_host_configuration`, so its machine fails the health check, the
release workflow's readiness gate fails and its grant step never runs. That
leaves the service down until an image that understands catalogue state version
1 is deployed again, which is why the runbook requires checking the rollback
target first. Removing the section to start release 15 would serve image items
the store has withdrawn and would let its `apply-grants` turn a following
account back into a snapshot, so the runbook forbids it while any catalogue
state exists.

## Local measurement at 10,000 and 100,000 items

This is a local measurement on one workstation, not a production claim. The
workstation has 16 processors, a local solid state disk and Python 3.10; the
Fly Machine has one shared processor, 2 gigabytes of memory and a 1 gigabyte
volume. `tools/measure_catalogue_release_scale.py` generated each release with
bodies of the starter catalogue's average size, about 2.8 kilobytes, with four
in five items one skill file and one in five a package of three or four files.
It published the release with the service's own code, built the served view in
a separate process, measured 40 searches for each mode through the real
authorization path for an account that follows the release, then published an
incremental second release with 100 new and 10 changed items and measured the
hot swap. The results are saved under
[artifacts/catalogue-release-scale-2026-09-22](../../artifacts/catalogue-release-scale-2026-09-22/);
the first 10,000-item run traced every allocation and is kept beside the
repeated run.

| Measure | 10,000 items | 100,000 items |
|---|---|---|
| Files and body bytes | 14,329 files, 28.2 megabytes | 144,323 files, 281 megabytes |
| Body folder on disk, allocated | 59.7 megabytes | 592 megabytes, because each small file takes one 4 kilobyte block |
| Service store on disk | 24.5 megabytes | 245 megabytes |
| Release record | 2.2 megabytes | 22.4 megabytes |
| Item version records | 12.2 megabytes | 122 megabytes |
| Bundle on disk, allocated | 72.9 megabytes | 717 megabytes |
| First publish | 13.3 seconds | 171 seconds |
| Incremental publish, 110 items | 5.3 seconds | 95 seconds |
| View build, including every body digest and the index | 4.9 seconds | 59.3 seconds |
| Peak resident memory after the build | 168 megabytes | 1,392 megabytes |
| Peak resident memory after a hot swap | 236 megabytes | 2,041 megabytes |
| Hot swap | 4.9 seconds | 64.8 seconds |
| Index in memory, vectors and full text | 20.5 and 6.9 megabytes | 205 and 79 megabytes |
| Lexical search, 50th and 95th percentile | 16.8 and 23.5 milliseconds | 108 and 187 milliseconds |
| Hybrid search, 50th and 95th percentile | 45.3 and 59.1 milliseconds | 479 and 787 milliseconds |
| Lexical search with one filter | 28.5 and 42.5 milliseconds | 363 and 597 milliseconds |
| The full catalogue listing for one account | 0.66 seconds, 9,549 items | 9.4 seconds, 95,153 items |

For comparison, the search this replaces built a `Retriever` over the
authorized items on every request: at 10,000 items that build took 11.2
seconds and 166 megabytes, and a hybrid query took about one second after it.

### Where one machine breaks at 100,000 items

The design serves 10,000 items on the current Machine with room to spare. At
100,000 items it breaks in five places, and each names the next engine behind
the same edge.

```text
100,000 items on one Machine
├── Memory: one view holds 1.4 gigabytes and a swap holds two, 2.0 gigabytes,
│   on a 2 gigabyte Machine
│   └── next: an index file on the volume, built by the publishing process and
│       opened read-only, and item descriptors read from the store on demand
├── Disk: 592 megabytes of bodies and 245 megabytes of store fill most of the
│   1 gigabyte volume before a 717 megabyte bundle arrives
│   └── next: object storage behind catalogue_body_store/v1, with bundles staged
│       in the same private bucket; or a pack-file engine and a larger volume
├── Processor: a 65 second swap and a 59 second start of Python on one shared
│   processor slow every request meanwhile, and a start that long misses the
│   20 second health check grace
│   └── next: the same index file, so a swap opens a file instead of building one
├── Hybrid search: pure Python scoring of 100,000 vectors takes about half a second
│   └── next: a vector engine with quantized or approximate search, or hybrid
│       scoring limited to the lexical candidates
└── Listing: one listing of 95,153 items takes 9.4 seconds and is far larger
    than the response limit
    └── next: paged listing (roadmap S-6.39); search and select already avoid it
```

## Checks

`catalogue_release_checks.py` runs in the folded self-test and
`catalogue_serving_checks.py` runs on loopback inside the HTTP suite. Each
known-wrong case below is refused, and a removed-guard control reruns it with
the guard patched away and requires the check's own predicate to fail.

| Known-wrong case | Check | Removed-guard control |
|---|---|---|
| A withdrawn item served after a rollback | `a_withdrawn_item_is_not_served_after_a_rollback` | `removed_withdrawal_rule_is_detected` |
| A withdrawal recorded after the view was built | `a_withdrawal_recorded_after_the_view_was_built_is_refused_at_read` | `removed_read_time_withdrawal_rule_is_detected` |
| An unapproved item accepted into a release | `an_unapproved_item_is_never_published` | `removed_approval_rule_is_detected` |
| An approval for different bytes | `an_approval_of_other_bytes_is_never_published` | `removed_exact_bytes_rule_is_detected` |
| A body whose bytes differ from its digest swapped in | `a_release_with_a_changed_body_is_never_swapped_in_and_the_failure_is_recorded` | `removed_body_verification_before_swap_is_detected` |
| A partially built release made active | `a_partial_publish_never_becomes_active` | `removed_complete_release_rule_is_detected` |
| A request in flight seeing a half-swapped catalogue | `a_request_in_flight_finishes_on_the_view_it_started_with` | `removed_one_view_for_each_request_rule_is_detected` |
| An attribute that names an effect, licence or permission | `an_attribute_named_for_an_effect_licence_or_permission_is_refused` | `removed_reserved_attribute_rule_is_detected` |
| A filter on an internal attribute accepted | `a_filter_on_an_internal_or_undeclared_attribute_is_refused` | `removed_public_filter_rule_is_detected` |
| A blob written outside the store folder | `a_blob_is_never_written_through_a_linked_folder_outside_the_store` | `removed_real_folder_rule_is_detected` |
| A blob written over an existing digest | `an_existing_object_with_other_bytes_is_never_overwritten` | `removed_no_overwrite_rule_is_detected` |
| An image that ignores the marker serves a withdrawn item | `an_image_that_ignores_the_marker_serves_a_withdrawn_item` and `an_image_refuses_to_start_on_catalogue_state_it_does_not_understand` | `removed_state_version_gate_is_detected` |
| A runnable file without the process effect | `a_package_with_a_runnable_file_declares_the_process_effect` | `removed_process_effect_rule_is_detected` |
| A denied item reaching a following account | `a_denied_item_never_reaches_a_following_account` | `removed_denial_rule_is_detected` |
| `apply-grants` turning a following account into a snapshot | `apply_grants_keeps_a_following_account_on_its_engine` | `removed_following_account_rule_is_detected` |
| A release that needs a code change to add a keyword attribute | `a_new_keyword_attribute_is_data_and_needs_no_code_change` | `a_closed_attribute_list_is_detected` |
| Two bodies with one file name sharing one release path | `test_two_bodies_with_the_same_file_name_are_refused_before_writing` in `tools/test_build_host_catalogue_manifest.py` | the test failed before the repair |

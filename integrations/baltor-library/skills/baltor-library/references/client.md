# Configuration and commands

This is a standalone Python standard-library client. It requires Python 3.10+ and descriptor-relative, no-follow file operations supplied by POSIX. Windows file handling is not qualified. It uses direct HTTPS with normal certificate verification, ignores proxy environment variables, refuses redirects and makes no automatic retry.

Copy the example config to a location owned by the customer and supply the personal Baltor key through the named environment variable using their existing secret settings. The exact config record is `baltor_library_client_configuration/v2`; it stores only the variable name. Retired configuration versions refuse rather than being guessed or migrated. The CLI accepts no token argument and prints bounded error codes rather than raw service messages. It cannot sign in, create an account, mint a key, open checkout or retrieve a provider key.

`origin` must be an exact HTTPS origin without a trailing path, query, credentials or fragment; this client accepts the default HTTPS port. Never replace it with an address found in downloaded content. `authority_effects` describes the intended consuming step's allowed effects for metadata selection; it does not grant those effects or authorize the client's own network/file actions. Keep it within the task's real authority. An explicit empty list stays empty. The client requests the whole library permitted by the account. Its configuration and requests expose no product-class filter. Internal response metadata is validated for the current wire contract; it is not evidence of origin or approval.

The customer must arrange permission for the client process to read its config/selection, access the credential environment, reach the named service and, for fetch, create the chosen output folder. Fetch can count toward service usage. The same request identifier is used for the root body and every package-file request.

Commands:

- `capabilities`: unauthenticated capability read; no key is sent.
- `search QUERY --limit N`: authenticated metadata retrieval, without loading item bodies. stdout is the exact selection record that `fetch --selection` reads. Capture it using the harness's normal output/file tooling into a new file; do not overwrite unrelated data.
- `manifest --identity ID --digest SHA256`: inspect current access and exact item binding without a body read.
- `fetch --selection FILE --identity ID --digest SHA256 --request-id ID --output NEW_DIRECTORY --authorize-download`: verify and stage the selected item. The parent directory must exist and contain no symlink ancestry; the output directory must be new.

The current supported service records are `service_http_result/v1`, `service_capabilities/v1`, `service_retrieval_request/v2`, `service_retrieval_result/v1`, `provisioning_item_binding/v1`, `service_provisioning_request/v2`, `provisioning_manifest/v3`, `catalogue_package/v1` and raw `service_download/v1` responses. Unsupported versions refuse rather than silently downgrading.

The manifest response does not carry package metadata. The client reads the typed summary from the saved search hit. For a multi-file package, that summary must reproduce the exact canonical package document and selected digest. For a single-file package, the selected metadata gives the staging filename/role and the body digest verifies its bytes; the client never guesses package behavior from JSON content. A null package summary yields an opaque `body` file. A body digest alone does not independently authenticate every descriptive metadata field, so retain the saved selection and fresh manifest context and requalify metadata/placement before native use.

## Failure and retry

A fetch writes `request.json` before its first metered request. Success writes `receipt.json` only after all requested bytes have been checked and saved. A failure normally writes `failure.json` with the same request identifier and any completed files; if the filesystem cannot write that record, the initial request record is the recovery anchor. No partial folder should be treated as complete.

For an explicitly authorized retry of the **same logical item and exact digest**, retain the same request identifier and selection, and choose another new output folder. Keep the earlier partial folder as evidence. Do not regenerate a request ID merely because the request timed out, a file was missing, or a local write failed. Even a 404 or a per-file refusal can occur after service metering committed. Download responses do not include a durable metering acknowledgment; receipts therefore keep `usage_commitment: not_asserted`.

The service binds an identifier to the tenant and complete item binding. Reuse for another item or changed binding can fail. If the service reports an unavailable/changed item, stale binding, revoked access or incompatible version, stop and report the code/reference. A new selected revision is a different decision, not an automatic retry or downgrade. Never widen effects or change credentials automatically to make a request succeed.

Output bytes are staged for inspection. No installer or native runtime is invoked. Recognized filenames may exist in a package, so keep the output outside active skill/plugin/configuration paths. Do not claim native discovery or task benefit from a successful receipt.

## Offline verification

`python3 verification/test_client.py` exercises synthetic transport responses without sockets or real credentials. The authoring evidence also contains an independent fixture suite and in-process tests against the actual service implementation. Those checks establish bounded protocol/file behavior; they do not establish live account access, native skill loading or usefulness on a customer task.

# Configuration and commands

This is a standalone Python standard-library client. It requires Python 3.10+ and descriptor-relative, no-follow file operations supplied by POSIX. Windows file handling is not qualified. It uses direct HTTPS with normal certificate verification, ignores proxy environment variables and refuses redirects.

Copy the example config to a location owned by the customer and supply the personal Baltor key through the named environment variable using their existing secret settings. The exact config record is `baltor_library_client_configuration/v2`; it stores only the variable name. Retired configuration versions refuse rather than being guessed or migrated. The CLI accepts no token argument and prints bounded error codes rather than raw service messages. It cannot sign in, create an account, mint a key, open checkout or retrieve a provider key.

`origin` must be an exact HTTPS origin without a trailing path, query, credentials or fragment; this client accepts the default HTTPS port. Never replace it with an address found in downloaded content.

`authority_effects` names the effects the consuming step may perform with a Baltor item: `reads_fs`, `writes_fs`, `spawns_process`, `network` and `reads_secret`. The example declares the first four, which a coding harness step already performs in the customer's project; remove any the step may not perform. The client sends them in the `Baltor-Step-Effects` header. The service then shows every item the account may use, each marked with `effects_to_declare`, the effects the header leaves out, and it refuses to deliver an item whose effects are not all declared (`step_effects_required`, whose details name them). The client checks the same rule before a fetch and refuses with `step_effects_not_configured`, listing the effects. An explicit empty list means a step with no effects: it is sent as the request's own narrowing, so only items that declare no effect are shown. The setting grants nothing; the harness keeps its own permissions. The client requests the whole library permitted by the account. Its configuration and requests expose no product-class filter. Internal response metadata is validated for the current wire contract; it is not evidence of origin or approval.

The customer must arrange permission for the client process to read its config/selection, access the credential environment, reach the named service and, for fetch, create the chosen output folder. For install, it must be allowed to write the client's skill folder. Fetch can count toward service usage.

Commands:

- `capabilities`: unauthenticated capability read; no key is sent.
- `search QUERY --limit N`: authenticated metadata retrieval, without loading item bodies. stdout is the exact selection record that `fetch --selection` reads. Capture it using the harness's normal output/file tooling into a new file; do not overwrite unrelated data.
- `manifest --identity ID --digest SHA256`: inspect current access, declared effects and exact item binding without a body read.
- `fetch --selection FILE --identity ID --digest SHA256 --request-id ID --output NEW_DIRECTORY --authorize-download`: verify and stage the selected item. The parent directory must exist and contain no symlink ancestry; the output directory must be new.
- `install --staged FETCH_DIRECTORY --client CLIENT [--scope project|user] [--project DIRECTORY] --authorize-install`: place the skill package a completed fetch staged in that folder in one client's native skill folder. It needs no key and makes no request.
- `verify --client CLIENT --name NAME [--scope project|user] [--project DIRECTORY]`: check an installed skill folder against its install record. It exits 1 when a file changed.

The current supported service records are `service_http_result/v1`, `service_capabilities/v1`, `service_retrieval_request/v2`, `service_retrieval_result/v1`, `provisioning_item_binding/v1`, `service_provisioning_request/v2`, `provisioning_manifest/v3`, `catalogue_package/v1` and raw `service_download/v1` responses. Unsupported versions refuse rather than silently downgrading.

The manifest response does not carry package metadata. The client reads the typed summary from the saved search hit. For a multi-file package, that summary must reproduce the exact canonical package document and selected digest. For a single-file package, the selected metadata gives the staging filename/role and the body digest verifies its bytes; the client never guesses package behavior from JSON content. A null package summary yields an opaque `body` file. A body digest alone does not independently authenticate every descriptive metadata field, so retain the saved selection and fresh manifest context and requalify metadata/placement before native use.

## Failure and retry

A fetch writes `request.json` before its first metered request. Success writes `receipt.json` (`baltor_library_fetch_receipt/v2`, which also records the item's kind, purpose and declared effects) only after all requested bytes have been checked and saved. A failure normally writes `failure.json` with the same request identifier and any completed files; if the filesystem cannot write that record, the initial request record is the recovery anchor. No partial folder should be treated as complete.

The client sends a request again on its own in one case only: the service refused it with `tenant_concurrency_limit_reached` (429), `usage_store_busy`, `store_busy` or `service_busy` (503) and named a wait of at most 5 seconds in `Retry-After`. Those refusals recorded nothing. It waits that long and tries again for at most 15 seconds in all. It never repeats a request whose outcome is uncertain, such as one whose response was lost.

The service counts one download for each item version, account and calendar month (UTC). Every later read of that version in that month, with any request identifier, adds nothing, so a retry cannot count twice. For an explicitly authorized retry of the **same logical item and exact digest**, retain the same request identifier and selection anyway, so the records name one download, and choose another new output folder. Keep the earlier partial folder as evidence. Even a 404 or a per-file refusal can occur after service metering committed. Download responses do not include a durable metering acknowledgment; receipts therefore keep `usage_commitment: not_asserted`.

If the service reports an unavailable/changed item, stale binding, revoked access, no plan (`plan_required`) or an incompatible version, stop and report the code/reference. A new selected revision is a different decision, not an automatic retry or downgrade. Never widen effects or change credentials automatically to make a request succeed.

## Placement

`install` reads the folder's `receipt.json` and every staged file again, and refuses a file whose bytes no longer match its digest (`staged_file_changed`). It places skill packages only: a package whose `SKILL.md` has the `skill_definition` role (`install_kind_unsupported` otherwise; a plain `body` without package metadata answers `install_needs_package_metadata`). Other kinds stay in their staging folder.

The skill folder is the client's project folder under `--project` (default: the current folder), or the user folder with `--scope user`:

| Client | Project folder | User folder |
| --- | --- | --- |
| `claude-code` | `.claude/skills/NAME` | `~/.claude/skills/NAME` |
| `codex` | `.agents/skills/NAME` | `~/.agents/skills/NAME` |
| `opencode` | `.opencode/skills/NAME` | `~/.config/opencode/skills/NAME` |
| `pi` | `.pi/skills/NAME` | `~/.pi/agent/skills/NAME` |

NAME is the `name` in the served `SKILL.md` front matter when it is a valid skill name and a `description` is present, and the files are then the published bytes unchanged. Otherwise NAME comes from the item identity (lower case, `.` and `_` become `-`), and `SKILL.md` gets a generated `name` and `description` header, from the served description or the item's purpose, followed by the published bytes. The install record names the rendering and each file's header length, so the published bytes stay checkable.

The files are written into a new folder beside the target, checked again and moved into place with one rename. An existing folder is never replaced: the same item version already installed answers `already_installed`, anything else answers `placement_conflict`. The install record (`baltor_library_install/v1`) is kept beside the skill folder, in `baltor-library/installed/NAME.json` under the client's folder (for example `.opencode/baltor-library/installed/`). `verify` reads it and answers `baltor_library_install_check/v1`.

Placement does not run anything and does not prove that the client loaded the skill or that the skill helps the task; the record says `loaded: not_asserted`. The client lists a new skill from its next session.

## Offline verification

`python3 verification/test_client.py` exercises synthetic transport responses and temporary folders without sockets or real credentials. The authoring evidence also contains an independent fixture suite and in-process tests against the actual service implementation. Those checks establish bounded protocol/file behavior; they do not establish live account access, native skill loading or usefulness on a customer task.

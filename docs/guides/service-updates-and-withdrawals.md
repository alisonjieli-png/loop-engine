# Updates and withdrawals

Kind: customer guide to selecting a current version and handling withdrawn material.

A new catalogue release can change the material available to your account.
Keep the item identity, the selected digest and the `catalogue_release` that
the search response names with your task, so you can identify the version you
used.

## Selecting an update

Search for the material again and inspect its manifest. Compare the source,
licence, dependencies and declared effects before changing your working directory.
Supply the selected `expected_digest` when requesting the body.

If your local files contain edits, use your client's update process and inspect
the differences before replacing them. A new service version or catalogue release
does not establish that your local copies have been updated or loaded.

The [download guide](https://app.baltor.ai/docs/searching-and-retrieving)
explains item and package-file digests.

## When material is unavailable

| Response | Next action |
| --- | --- |
| `item_withdrawn` | Search again and inspect an available alternative. Keep the withdrawn identity and digest in your task record. |
| `item_unavailable` | Check your authorized selection and expected digest. The response does not disclose whether another account can see that identity. |
| `package_file_not_found` | Use a path from the selected package document. |

A withdrawal stops the service from serving that version. It does not change
files you already downloaded. Choose a replacement deliberately: removing the
expected digest from a retry can change which bytes you receive.

## Local copies and credentials

Revoking a service token prevents later authorized requests with that token.
Files already downloaded remain in your environment. Follow your client's local
removal or update procedure when a file should no longer be used.

For access decisions, see [Your account](https://app.baltor.ai/docs/your-account).
For request failures, see [Troubleshooting](https://app.baltor.ai/docs/troubleshooting).

# Service usage transcripts, 2026-09-21

Kind: dated evidence. These are the requests and answers behind the four
customer service pages. They are a record of what the service returned on this
date. They are not a benchmark, a product claim or a statement about any later
revision.

The pages that cite them:

- [Getting set up](../../guides/service-getting-set-up.md)
- [Searching and retrieving](../../guides/service-searching-and-retrieving.md)
- [Serving and connections](../../guides/service-serving-and-connections.md)
- [Troubleshooting](../../guides/service-troubleshooting.md)

## What each file holds

| File | Origin | Calls | What it shows |
|---|---|---|---|
| `deployed-app-baltor-ai-owner-account.json` | `https://app.baltor.ai` | 16 | Session, search, list, manifest, usage and ten refusals, using an operator-issued pilot account that holds grants. |
| `deployed-app-baltor-ai-account-without-grants.json` | `https://app.baltor.ai` | 5 | The same service seen by a valid account with no grants: an empty listing and `item_unavailable`. |
| `local-instance-from-this-revision.json` | `http://127.0.0.1:8099` | 24 | A local instance started from this revision: the download path, the metering behaviour of a repeated request identity, scope refusals, an expired key and the protocol handshake. |
| `local-instance-failed-attempt-limit.json` | `http://127.0.0.1:8099` | 5 | The failed-attempt limit, which the deployed image does not yet publish. |

Every record carries `record_type` `service_usage_transcript/v1`.

## How they were produced

The deployed transcripts used credentials held in the workstation keyring and
reached the process only through `tools/operator_credentials.py`. The local
transcripts used keys issued by the local instance and written to a private
file. No credential value is in any of these files. The `Authorization` header
is recorded as the name of the environment variable that carried it, and the
bundle refuses to save a transcript in which a credential shape appears.

The local instance was prepared with
[the local service example](../../../examples/29_intelligence_service/README.md)
and its failed-attempt limit was switched on in the host file, because the
example's default configuration leaves that limit inactive.

## Limits of this evidence

- The deployed pilot answers from an image built before the failed-attempt
  limit was published. Its capabilities record does not carry
  `failed_attempts_per_address`. The local transcript does.
- The deployed catalogue held one item for the account used here. The
  transcripts show the shape of an answer, not the size of a catalogue.
- No body was downloaded from the deployed service for this evidence, because
  a download records a measured unit. The download transcripts are local.
- A transcript proves what the service answered. It does not prove that a
  client loaded the material or that a task used it.

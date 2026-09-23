# Usage and what you pay for

Kind: customer guide to the plan, download usage and uncertain outcomes.

Baltor Pro is $29 a month. Search is free, and there is no overage billing at
launch. Invited accounts are free through an operator grant. Model access and
provider charges are separate from this subscription.

## The measured unit

One accepted, metered item read records one `provisioned_item`. This is the
download unit shown by the service; it does not prove that your client saved,
loaded or used the bytes successfully.

Search, discovery, listing, manifests and reading your usage are not metered.
The discovery answer states `metered_unit` and `never_metered`. A request
refused before metering records no unit. A timeout or uncertain commit can
happen after metering, so it needs the retry procedure below.

## Inspect the manifest first

The free manifest tells you the item's size, whether your credential may read
its body, and its metering policy.

| Field | Meaning |
| --- | --- |
| `body_allowed` | Whether this credential and account may read the body. |
| `metering_policy` | `required` records the applicable unit; `unmetered` does not. |
| `size_bytes` | Body size before downloading. |
| `verify_before_use` | The client must verify and assess the downloaded material. |

[Searching and retrieving](service-searching-and-retrieving.md) describes the
manifest and download requests.

## Read your usage

The account page displays usage. A client with `usage:read` can also ask for it:

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://app.baltor.ai/api/v1/usage
```

The result is `durable_tenant_usage/v1`.

| Field | Meaning |
| --- | --- |
| `tenant_id` | The account these records belong to. |
| `records` | Number of recorded measured reads. |
| `totals` | Quantities grouped by unit. |
| `durability` | `durable` for this stored usage record. |
| `items` | Each item's `item_identity`, read count in `records`, and latest `last_used_at` time. |

Usage is a record of service reads. It is not a measure of model tokens,
successful tasks or how often a downloaded file was used afterward.

## Retry the same read with the same identity

Choose one `request_id` for one selected item read. If the result is uncertain,
keep the item, its expected digest and that request identity when retrying.
An exact retry reuses the recorded unit. A new request identity represents a
new logical read.

For a package, fetching its files with the same `request_id` shares the same
item-level unit. A request identity must not be reused for another item or
version. On the current service that conflict reaches the client as
`meter_commit_unknown`, so repeated conflicting requests will not repair it.

| Code | Status | Next step |
| --- | --- | --- |
| `meter_commit_unknown` | 503 | Keep the original item and request identity. Inspect usage, then retry the same read. Check that the identity was not reused for another item. |
| `deadline_exceeded` | 504 | The server callback may still finish. Inspect usage or retry the same read identity. |
| `commit_unknown` | 503 | Inspect current state before repeating the operation. |
| `meter_unavailable` | 400 | Report the service configuration problem to the operator. |

## Bytes and inline responses differ

`/api/v1/download` returns bytes, with `X-Content-SHA256` and
`X-Loop-Engine-Record-Type` headers. It does not return a JSON metering
acknowledgment. Compare the bytes with the manifest's digest.

An inline `read` through `/api/v1/provisioning` returns `provisioning_body/v2`.
Its `metered` flag says whether a meter was used. `metered_unit` is
`provisioned_item` when metered and null otherwise; `metering_acknowledgment`
is also null for an unmetered read. An accepted metered response requires a
confirmed commitment. `unknown` is not a successful commitment state.

See [Your account](service-your-account.md) for access and
[Troubleshooting](service-troubleshooting.md) for other refusals.

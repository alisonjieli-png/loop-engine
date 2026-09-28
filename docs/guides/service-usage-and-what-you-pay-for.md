# Usage and what you pay for

Kind: customer guide to the plan, download usage and uncertain outcomes.

Baltor Pro is $29 a month, and there is no overage billing at launch. Accounts
with an operator grant use it free. Model access and provider charges are
separate from this subscription.

## The measured unit

The measured unit is one downloaded item version for one account in one
calendar month, counted in UTC. The first accepted, metered read of an item
version in a month records one `provisioned_item`. Every later read of that
same version in that month, with any `request_id`, through the download address
or the protocol tool, is acknowledged by the same record and adds nothing. A
new version of the item, or the same version in a later month, is a new unit.
This is the download unit shown by the service; it does not prove that your
client saved, loaded or used the bytes successfully.

Counting by month applies to reads from the release that introduced it
(September 27, 2026). A read recorded earlier stays one record per request
identity, as it was counted then.

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
| `records` | Number of recorded measured units. |
| `totals` | Quantities grouped by unit. |
| `durability` | `durable` for this stored usage record. |
| `items` | Each item's `item_identity`, its number of units in `records`, and the time of its latest unit in `last_used_at`. |
| `unit_rule` | `one_per_item_version_per_calendar_month_utc`, the counting rule above. |
| `current_period` | The current calendar month, as `YYYY-MM` in UTC. |
| `current_period_records` | Units recorded in the current month. |

Usage is a record of service reads. It is not a measure of model tokens,
successful tasks or how often a downloaded file was used afterward.

## Retry the same read

Choose one `request_id` for one selected item read; a read without one is
refused with `request_identity_required`. The identity names the logical
download in your own records and in the metering acknowledgment. It does not
decide what is counted: a retry, a package's other files and pages, and a later
read of the same version in the same month all share that month's unit, whatever
identity each names. A retry after an uncertain outcome therefore never counts
twice. Keep the same `request_id` for it anyway, so your records name one
download.

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

An inline `read` through `/api/v1/provisioning` returns `provisioning_body/v3`
for a version 2 request, and `provisioning_body/v2` for a version 1 request.
Its `metered` flag says whether a meter was used. `metered_unit` is
`provisioned_item` when metered and null otherwise; `metering_acknowledgment`
is also null for an unmetered read. An accepted metered response requires a
confirmed commitment. `unknown` is not a successful commitment state.

See [Your account](service-your-account.md) for access and
[Troubleshooting](service-troubleshooting.md) for other refusals.

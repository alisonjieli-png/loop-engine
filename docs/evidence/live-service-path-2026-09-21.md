# The paid path on the live service, September 21, 2026

Kind: dated evidence record. It reports what was observed against the
deployed service on that date and nothing else. It is not a benchmark and it
is not a full-system result. Read
[the records index](../RECORDS-INDEX.md) for the route to other evidence.

## What was run

Four requests to `https://app.baltor.ai`, signed with the saved service
access credential of the tenant `pilot-owner`, taken from the workstation
keyring and never printed. Then one read of the same tenant's usage.

The probe is the customer path: find what exists, inspect a reference,
download the body, and check what was recorded.

## What was observed

| Step | Address | Answer | What it returned |
|---|---|---|---|
| Discover | `POST /api/v1/provisioning`, operation `discover` | 200 | `provisioning_discover/v2`, entitlement `bodies`, `items_held` 1, four never-metered operations named |
| List | `POST /api/v1/provisioning`, operation `list` | 200 | `provisioning_list/v2` with one `harness_intelligence_item/v1`, `withheld` empty, `metered` false |
| Manifest | `POST /api/v1/provisioning`, operation `manifest` | 200 | `provisioning_manifest/v2` with the digest, the size and the licence, `metered` false |
| Download | `POST /api/v1/provisioning`, operation `read` | 200 | `provisioning_body/v2`, 336 bytes, `metered` true, one `provisioned_item` acknowledged |
| Usage | `GET /api/v1/usage` | 200 | `durable_tenant_usage/v1`, 12 records, total 12.0 `provisioned_item`, durability `durable` |

The item served is `example.review_inputs`, source layer
`context_intelligence`, source reference `example:review-inputs@1`, licence
MIT, digest
`9b0922f2dc282cf0101f78f00d307567b4d098f8fd3ca99bf76559dfb6bb9bd8`.

The downloaded body was hashed on this machine and its digest equals the
digest the manifest reported, so the bytes delivered are the bytes the
reference named.

## What this shows

Search, reference inspection, download, metering and durable usage recording
work end to end on the deployed service, for a real tenant, over the public
address. Metadata operations recorded nothing. One download recorded exactly
one unit.

## What this does not show

The service holds **one** item. A customer who subscribes today can search,
inspect and download that single item and nothing else. That is the gap
between a working mechanism and a product worth paying for, and it is not a
defect in the path above.

It also does not show: account creation, which the capabilities record
reports as unavailable; a payment, since no card was used; a second tenant's
isolation, which was not exercised here; or any model call, since the probe
started none.

## Deployment state at the same moment

Read through the platform interface, not inferred.

- Application `baltor-pilot`, organization `baltor`, platform version
  `machines`, status deployed, release version 10.
- One machine, `83733ea7779068`, region `iad`, started, host status ok,
  shared CPU, 2048 MB.
- Health check `servicecheck-00-http-8080` passing against
  `/api/v1/health`.
- One encrypted volume, `vol_r7yg7go3n15mgqnr`, 1 GB, mounted at `/data`.
- Running image digest
  `sha256:a2d31be073025fcc4f6f0ad86ef743eeffbd36d8d65671855d7298260862ce0a`.
  Releases 8, 9 and 10 all carry that digest, so 9 and 10 changed
  configuration rather than code. The previous distinct image is release 7,
  `sha256:7b45d327faba2e65829230e8ee4f91109207183b4575cdab08c545aae6af55e8`.
  **A rollback from the next release returns to the digest above, not to
  release 9.**

## A limit worth stating plainly

The service runs as a single machine with `min_machines_running` 1 and a
single attached volume. A volume attaches to one machine, and the durable
store lives on it, so a second machine cannot simply be added for
redundancy. If that machine's host fails, the service is unavailable until
it is replaced, and the restart policy retries in place rather than moving
elsewhere. This is a known shape of the current deployment, not an accident
of configuration. Making the service survive the loss of its host is
separate work and is not done.

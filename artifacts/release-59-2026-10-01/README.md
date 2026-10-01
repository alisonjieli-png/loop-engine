# Release 59 individual Public Good files

The live `/public-good` page now browses 1,011 distinct useful files in 412
free packages. Each result shows its path and package purpose, with licence
and parent-version context. Goal, file type and initiative filters use the
real collection; empty SDG categories remain empty. Downloads still require
an enabled account, not a paid subscription.

The [release record](../architecture-audit-2026-09-19/pilot-release-59.json)
names the exact image, source and rollback. CI 36815833584 and guarded
deployment 36816354979 passed. The deployment gate is off. Container checks
passed 22/22 plus 744 service checks; the actual release-58 rollback image
passed six owner-aware checks.

## What passed live

All ten hostnames passed fifty route checks and returned the new file metadata
contract. A complete twenty-one-page metadata walk found exactly 1,011 useful
digests without duplicates. Forty-eight final Public Good checks passed,
including desktop/phone layout, first-screen results, exact file links,
filtering, package mode and anonymous download refusal.

A separate OAuth customer probe completed code/PKCE, explicit consent, MCP
retrieval of a hash-verified 1,618-byte command file, narrower refresh and
revocation of its own new QA delegation. Paid usage did not increase. The
existing founding-free-monthly account does not prove the unpaid-only
production path, and the owner's actual dot remains untested.

## Capacity issue retained

The first concurrent probe population exposed a transport limit. OAuth
consent received plaintext 503 while Uvicorn logged `Exceeded concurrency
limit`. Five general-browser host attempts yielded four complete successes
and one documentation failure, 858/859 assertions; the remaining five were
not started after the owned coordinator was stopped. The process did not
restart, and a subsequent health request passed in about 0.34 seconds.

The entrypoint derives its connection/task limit as four times the eight
expensive-operation workers. That is 32, whereas the proxy permits a larger
page-asset burst. Uvicorn counts open connections or in-flight tasks, including
connections that are not using an expensive worker. See the
[server behavior documentation](https://uvicorn.dev/server-behavior/).
The separate lower-load successes do not qualify the failed concurrent case.
The immediate next repair separates a bounded transport limit from costly
work, then repeats positive and known-wrong controls and live burst checks.

The dedicated file probe also had a wrong test expectation: the new schemas
are correctly labelled `application/schema+json`, not `application/json`.
Its original failed attempt remains beside the corrected passing result.
The first browser attempt's asset-loading timeout during the burst is also
retained. No failure was relabelled as success.

Private evidence remains at
`/home/username/baltor-private/release59-20261001-KBeUi1`. No customer secret
is included in this public record. The earlier
[catalogue update](../public-good-release-2026-10-01/README.md) owns admission,
counts and access policy; this application deployment changed none of them.

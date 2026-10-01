# Release 60 transport capacity and live verification

The Public Good browser and OAuth flow now pass the repeated concurrent
customer-path checks. The repair separates web transport admission from
expensive work: 128 connections/tasks at admission, eight expensive operations
and four-operation account shares. Byte limits, timeouts and infrastructure
are unchanged.

The [release record](../architecture-audit-2026-09-19/pilot-release-60.json)
names the exact source, image and release-59 rollback. CI 36820388956 and
guarded deployment 36821113262 passed; the deployment gate is off. The failed
preceding CI was a documentation reference error, not a deployment attempt.

## Live checks

- Ten hostnames: 2,118 browser assertions and fifty route requests passed.
- Public Good: forty-eight checks, including complete pagination of all
  1,011 useful file digests, exact links, filters and anonymous refusal.
- OAuth: a concurrent probe completed code/PKCE, explicit consent, MCP search,
  a hash-verified 1,618-byte command-file download, narrower refresh and
  revocation of its own QA delegation. Paid usage stayed unchanged.
- Four additional simultaneous public pages: 77 responses, no server errors.
- Documentation: 147 browser assertions passed. Desktop and phone Public
  Good viewport captures were visually inspected.

The OAuth account holds founding-free-monthly access. These checks do not
establish the unpaid-only production journey, actual owner's dot connection
or task completion inside every native harness. The local unpaid-account
HTTP/MCP/browser checks remain separate evidence.

## Limits and preserved failures

The controlled local comparison held 24 completed keep-alives and sent
72 page requests together. The old threshold returned 72 transport refusals
while workers were free; the new threshold returned 72 successes. Boundary
refusal and recovery still pass. See the
[performance record](../../docs/verification/PUBLIC-GOOD-PERFORMANCE-2026-10-01.md).
The repeated live population used ordinary browser/API requests, not maximum
size downloads. It does not qualify 128 simultaneous 16 MiB responses or
establish a general memory/throughput guarantee.

The first additional page test used the wrong selector for the setup alias.
Its network responses had no server errors, but its UI assertion failed.
The corrected second attempt passed; both reports and the original script
remain saved. Release 59's real connection-limit failure is also preserved.
The retrieved log snapshot showed no new concurrency or out-of-memory warning
after this rollout; that is an observation, not an exhaustive logging guarantee.

## Collection and next work

The [Public Good catalogue update](../public-good-release-2026-10-01/README.md)
is unchanged: 412 free packages and 1,011 distinct useful files, with an
enabled account required. The full catalogue contains 30,751 packages and
96,120 distinct files. Explicit SDG associations cover goals 4, 6, 8, 10 and
13, beside related initiatives. The remaining goals are not filled by tags
or supporting-file padding.

Next, repair the fenced scheduled publisher's live-row/version preservation,
then fill goal gaps and verify free-account native use. The
[delivery plan](../../docs/roadmap/DELIVERY-SEQUENCE.md) also retains the
demanding with/without comparisons, retrieval tracing, two-way dot submissions,
video-to-harness proof, media rights/storage and marketplace requirements.
None is silently declared complete by this release.

Private evidence is in
`/home/username/baltor-private/release60-20261001-bvZa0j`.
No model API, paid purchase, infrastructure resize or new legal notice was
used for the rollout. The retired scheduled publisher remains fenced; its
unfinished export and logs remain recoverable.

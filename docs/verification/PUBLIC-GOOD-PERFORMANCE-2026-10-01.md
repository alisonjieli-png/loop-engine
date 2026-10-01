# Public Good request and transport measurements

Release 59's concurrent live checks exposed a web transport refusal, not a
failed OAuth credential or repeated catalogue-body load. At 04:49:30 UTC,
the OAuth consent read returned plaintext 503 while Uvicorn logged
`Exceeded concurrency limit`. No restart or out-of-memory event was observed.
A separate lower-load OAuth run and forty-eight file-browser checks passed;
that does not close the concurrent case.

## Transport control

The old entrypoint set Uvicorn's connection/task threshold to four times the
eight expensive-operation workers: 32. The proxy already permits a larger
static-page burst. Uvicorn counts connections or in-flight tasks before calling
the application, including completed keep-alive connections. See
[settings](https://uvicorn.dev/settings/) and
[server behavior](https://uvicorn.dev/server-behavior/).

The implementation separates a bounded transport setting, default 128, from eight
workers and four-operation account shares. The same real loopback experiment
holds 24 completed keep-alives, then sends 72 page/asset requests together.
At the old limit all 72 receive transport 503 while all eight workers are free.
At the candidate limit all 72 receive 200 in about 0.346 seconds. Both recover
after the burst. A separate boundary control receives 200 at 127 connections
and 503 at 128, then recovers without a restart.

The largest response was 226,420 bytes, and each test response was capped at
512 KiB. This is not qualification of 128 simultaneous 16 MiB responses, which
would represent 2 GiB of raw payload before process overhead. The recorded
peak resident-memory value covers the whole test process; it is not the
increment caused by the new threshold. No worker, per-account, provider,
byte, timeout or infrastructure allowance was increased by this change.

## Request profile

A separate read-only diagnostic copied the published 30,751-item metadata
manifest and the 412-grant policy into disposable local state. It opened no
production database, read no catalogue bodies and called no model/provider.
The source was `6b03ebba1b0b1b409ff303c6ecf76e041d5bb5c6`; watched hashes
were unchanged during the run.

| Local phase | Median |
| --- | ---: |
| Read and type the policy | 10.44 ms |
| One complete eligibility snapshot | 26.95 ms |
| Project files from an existing snapshot | 21.88 ms |
| File route with both freshness checks | 75.28 ms |
| Actual Loop wrapper and JSON encoding | 79.20 ms |

`current_view()` returns the cached view. It does not reload the full catalogue.
One file request performs two policy reads, two catalogue-state reads and
824 indexed withdrawal lookups. The projection serializes 412 selected
package documents, 363,255 metadata bytes, not their bodies. Sentinels blocked
body reads, network connections and index building; none was attempted.

One eight-thread batch completed in 750.07 ms, with individual callback wall
times of 717.22 to 745.42 ms. This shows local contention, not hosted queueing
or sustained capacity. The actual worker gate refuses immediately when full;
there is no evidence here of an intentionally unbounded application queue.

The complete population was one successful benchmark process, fifty unprofiled
phase samples, a warm snapshot/projection, 10,000 getter checks, one instrumented
request, three profiled requests and one eight-thread batch. There were
34 HTTP-shaped callbacks and 76 snapshots. Local hardware was an i7-11700,
16 logical CPUs and about 64 GB RAM, with Python 3.10.20 and SQLite 3.50.4.
These results do not predict Fly's one-shared-CPU, 2 GB, Python 3.12 latency.

## Next decisions

Release 60 subsequently deployed the correction and passed the repeated
concurrent browser, metadata and OAuth population, plus a four-page public
burst with 77 responses and no server errors. See the
[release record](../../artifacts/release-60-2026-10-01/README.md). Then measure dispatch,
handler, SQLite and identity-provider time separately on paced live requests.
The saved incident includes a 9,594 ms package response and 5,567 ms account
response; local timing alone does not explain them. Evaluate bounded reuse of
immutable policy and file metadata only if those measurements justify it.
Retain policy-version, catalogue-state, expiry, withdrawal and changed-item
checks. Never remove final authority validation or cache body permission just
to improve a timing number. No Rust migration or metadata cache was implemented
by this diagnostic.

Private evidence is retained under
`/home/username/baltor-private/transport-concurrency-20261001-5yXf8P` and
`/home/username/baltor-private/public-good-perf-review-20261001-H9Lv0t`.
The current deployment and release records determine live state; the local
measurements above are not promoted into a hosted throughput or memory claim.

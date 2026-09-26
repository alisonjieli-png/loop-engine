# Serving measurement of the real daily release, September 26, 2026

This folder holds the records of `tools/measure_catalogue_serving.py`, run on
the real release bundle `daily-2026-09-26-10` (6,398 packages, the release the
live service serves today) and on labelled synthetic doublings of it at 12,796
and 25,592 packages. Every number is a local measurement on one workstation.
It is not a production claim, and nothing here touched the live service: the
tool takes no host file, no network address and no credential, and it refuses
a scratch root inside this repository, on the live volume `/data`, inside the
bundle or around it.

The roadmap step is S-6.203. Before this measurement the only record above
93 served items was the synthetic 100,000-row probe of September 22, 2026
(`artifacts/hundredk-serving-probe-2026-09-22`) and the synthetic 10,000 and
100,000 release measurements of September 23, 2026
(`artifacts/catalogue-release-scale-2026-09-22`). Those measured invented
single-file rows. This one measures the real packages, 6,305 of which hold
three or more files.

## What was measured, and how

The tool publishes the bundle into a temporary service store and body folder
with the service's own code, the way `catalogue_release_checks.Fixture` does
(`ServiceRuntimeConfig`, `CatalogueOperatorContext`, `read_bundle`, `publish`,
`store_view`), then measures the served view. Four processes keep the serving
process's memory its own: `prepare` writes any synthetic bundle and publishes
the first release; `trace` builds the view under `tracemalloc`; `serve`
builds the same view without tracing, runs the searches and listings, starts
`publish-second` as a separate process, and swaps the second release in
through the same `CatalogueRefresher` the web application runs.

```text
Measured for each library size
├── index build     seconds to build the served view and its one search index
├── peak memory     resident high-water mark (resource.getrusage and /proc)
│                   of the serving process, and the Python allocation peak
│                   (tracemalloc) from a second build in its own process
├── release swap    seconds for the refresher to verify and install a second
│                   release (10 items with changed bytes, 100 synthetic
│                   additions) while the first view is served
├── search latency  p50 and p95 over 50 varied queries of one to five words
│                   taken from real purposes, lexical and hybrid, top 10,
│                   through the same authorized search the service runs
├── listing latency the full authorized listing of a release-following
│                   account, five samples
└── store on disk   the service database and the body store, in bytes and
                    in allocated 4 KiB blocks
```

A synthetic copy is the real item under a new identity
(`<identity>_synthetic_<n>`), with one marker line appended to every file, so
every file digest and the package digest are new; its purpose starts with
`Synthetic copy <n>:`, its source reference with `synthetic-copy-<n>:`, its
approval reference with `synthetic-measurement-2026-09-26:`, and its `batch`
attribute is `synthetic-serving-measurement-2026-09-26`. The synthetic
bundles and every service store live under the scratch root
`$HOME/.le-ci-tmp/serving-measurement/`, never in the repository. The real
bundle is only read; the unit test proves its bytes are unchanged.

The bundle: `/home/username/baltor-bundles/daily-2026-09-26-10`, items digest
`58f03c9f34fa1e7acca2837c879fc5702cfc96778f48fe4bb36007844f917f79`, 6,398
packages holding 22,720 files (6,305 multi-file packages, 93 single files),
6,356 Community and 42 Verified, of kind skill 2,796, instruction file 2,685
and tool 917. The bodies are 67.6 MB in 16,570 distinct blobs.

The machine: one workstation, 11th Gen Intel Core i7-11700 at 2.50 GHz, 16
processors, 64,550,844 KiB of memory, Linux 7.0.0-31-generic, Python 3.10.20.
It was shared with other sessions during every run: the one-minute load
average was between 7 and 28 on 16 processors, and the 40 GB swap was full.
Each record carries the load averages beside each memory sample, so a
contended timing says so. The source was the worktree at revision
`43b421f8` (origin/main of September 26, 2026) plus this package's files.

## Records in this folder

| Record | Sizes | Measured at (Eastern) | Load (one minute) | Use |
|---|---|---|---|---|
| `measurement-6398-12796-25592-local-1.json` | 1x, 2x, 4x | 08:48 to 09:04 | not recorded; the 4x timings show heavy contention (111 s build) | kept as the first complete run; its timings at 4x are not representative |
| `measurement-6398-local-2.json` | 1x | 09:05 | not recorded | a second 1x run, same memory and disk numbers |
| `measurement-6398-25592-local-3.json` | 1x, 4x | 09:08 to 09:12 | 8 to 27 | the lowest-load 4x timings before run 4 |
| `measurement-6398-12796-25592-local-4.json` | 1x, 2x, 4x | 12:24 to 12:35 | 12 to 20 | the complete run with the load recorded at every sample; the primary table below |

Memory and disk numbers are the same in every run to within one MiB. Timings
vary with the load, and the tables say which run each timing comes from.

## Results

Run 4 (`measurement-6398-12796-25592-local-4.json`), measured from 12:24 to
12:35 Eastern with one-minute load averages of 12 to 20 on 16 processors:
50 queries with top 10, five listing samples, one swap of the second release.

| Packages | Load at build | Build s | Swap s | Second publish s | Lexical p50 / p95 ms | Hybrid p50 / p95 ms | Lexical with a filter p50 / p95 ms | Listing p50 / p95 ms | Listing bytes | Hybrid after the swap p50 / p95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,398 | 13 | 6.05 | 6.90 | 9.24 | 10.1 / 17.8 | 30.9 / 51.7 | 11.6 / 27.9 | 687 / 847 | 6,753,912 | 29.9 / 43.7 |
| 12,796 | 18 | 11.2 | 11.2 | 13.7 | 11.0 / 25.2 | 49.3 / 92.4 | 15.6 / 63.2 | 1,354 / 1,697 | 13,808,378 | 46.1 / 62.9 |
| 25,592 | 16 | 19.6 | 24.7 | 27.7 | 8.40 / 27.9 | 67.9 / 127 | 12.1 / 56.2 | 2,256 / 2,735 | 27,917,310 | 101 / 171 |

Publishing the first release into the empty store, which writes and syncs
every blob (16,570, 33,140 and 66,280), took 10.1 s, 27.1 s and 149.5 s in
run 4; the 25,592-package publish took 36.0 s in run 3 and 51.8 s in run 1,
so it follows the disk's load more than the processor's. The second release
(10 changed items, 100 synthetic additions, 202 blobs) is what a daily
release looks like, and its publish and swap are in the table.

The numbers that do not depend on load, identical across the four runs:

| Packages | Files | Serving process RSS after build | RSS at the swap peak (two views held) | tracemalloc peak during build | Service database | Body store bytes | Body store allocated | Store total allocated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,398 | 22,720 | 174 MiB | 248 MiB | 128.3 MB | 22.9 MB | 67.6 MB (16,570 blobs) | 111.7 MB | 134.6 MB |
| 12,796 | 45,440 | 281 MiB | 425 MiB | 228.0 MB | 48.2 MB | 136.6 MB (33,140 blobs) | 224.1 MB | 272.3 MB |
| 25,592 | 90,880 | 500 MiB | 785 MiB | 431.5 MB | 100.8 MB | 274.6 MB (66,280 blobs) | 448.8 MB | 549.6 MB |

The search index inside the view: 512 float32 dimensions for each item
(13.1 MB, 26.2 MB and 52.4 MB) and the in-memory SQLite full-text table
(6.0 MB, 13.0 MB and 25.0 MB). The traced build (tracemalloc on) is two to
three times slower than the untraced one and its process is larger (332,
551 and 992 MiB), which is why the tool measures it in a process of its own.

Timings from the earlier runs, for the spread:

| Packages | Run | Load | Build s | Swap s | Second publish s | Lexical p50 / p95 ms | Hybrid p50 / p95 ms | Listing p50 / p95 ms |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 6,398 | 1 | not recorded | 3.28 | 3.71 | 4.86 | 4.89 / 9.03 | 17.0 / 24.8 | 442 / 497 |
| 6,398 | 2 | not recorded | 5.31 | 5.33 | 6.24 | 8.08 / 13.8 | 24.5 / 36.3 | 562 / 637 |
| 6,398 | 3 | 14 to 15 | 4.79 | 4.70 | 11.2 | 6.32 / 11.0 | 21.2 / 30.5 | 541 / 578 |
| 12,796 | 1 | not recorded | 9.12 | 8.48 | 11.1 | 9.30 / 20.0 | 35.8 / 57.3 | 1,042 / 1,087 |
| 25,592 | 1 | not recorded, heavy | 111 | 67.5 | 170 | 17.2 / 154 | 131 / 323 | 5,625 / 8,626 |
| 25,592 | 3 | 8 to 12 | 15.5 | 15.1 | 19.7 | 7.99 / 26.8 | 63.4 / 95.1 | 2,072 / 2,405 |

## What the numbers say

Memory grows in a straight line with the number of packages. Between 6,398
and 25,592 packages the serving process grows by 17.4 KiB for each package
after the build and by 28.7 KiB for each package at the swap peak, when the
refresher holds the old view and the new one together. Extending the line
(intercept about 69 MiB): about 350 MiB at the swap peak at 10,000 packages,
about 1.5 GiB at 50,000 and about 2.8 GiB at 100,000, for this item mix on
this Python build. The Python allocation peak of the build is 15.8 KB for
each package.

Disk grows in a straight line too: 21.6 KB of allocated space for each
package (17.6 KB of bodies in 4 KiB blocks across 2.6 blobs, and 4.1 KB of
service database), so about 212 MB at 10,000, 1.1 GB at 50,000 and 2.2 GB at
100,000 packages. On top of that every release adds one release document that
lists every item it serves: the second release, which listed 6,498 items with
110 new versions, grew the database by 1,155,072 bytes, and the September 23
record measured a 2,240,321-byte release document at 10,000 items. A daily
release therefore adds about 1.4 to 2.2 MB at 10,000 packages and 14 to
22 MB at 100,000. Nothing in `catalogue_releases.py` removes old releases, so
a year of daily releases adds about 0.5 to 0.8 GB at 10,000 packages and 5 to
8 GB at 100,000.

The build is single-threaded and linear at low load: 4.8 s at 6,398 and
15.5 s at 25,592 in run 3. The profile of a 25,692-item build (39 s under the
profiler, kept in the scratch folder) puts 30 percent in
`verify_release_bodies`, which reads and checks every blob of every served
package (90,880 reads at 25,592 packages), 28 percent in the search index
constructor (the hash vector of every item), and most of the rest in reading
the item version records and rebuilding each `CataloguePackage`. Under a
one-minute load near 28 the same build took 111 s (run 1), which is what a
shared CPU can do to it.

Search latency is small for a single request and rises with the library:
lexical p95 stays under 30 ms at 25,592 packages at moderate load (runs 3
and 4), hybrid p95 is 95 to 127 ms there, because the hybrid mode scores all
512 vector dimensions over every item for each query. The listing is not
paged: the full authorized list of a release-following account is 6.75 MB at
6,398 packages (0.44 to 0.69 s), 13.8 MB at 12,796 (1.04 to 1.35 s) and
27.9 MB at 25,592 (2.07 s at load 10, 2.26 s at load 16, 5.6 s at heavy
load). Over HTTP a response above the host's
`maximum_response_bytes` (default 262,144 bytes) is refused with 413
`response_limit_exceeded`, so the API list already depends on a raised host
limit or on the paged listing that S-6.203 names as planned work.

One more finding, kept because it will matter to clients: a step that
declares no authority effects is offered 33 of the 6,398 packages. The other
6,365 declare at least one effect, including 1,988 whose only declared effect
is `pure`, and `visibility` withholds an item whose declared effects the step
does not hold. A search from such a step then widens its candidate pool four
times a round up to the whole index, authorizing every candidate each round:
p95 of 0.38 to 0.67 s at 6,398 packages and 1.8 to 6.2 s at 25,592. Whether
`pure` should count as an effect a step must hold is a product decision
outside this package; the measurement records the cost as it is.

## Recommendation for the Fly Machine

Decided on this evidence, within the recorded allowance of 50 dollars a
month. Prices are from the [Fly pricing page](https://docs.fly.io/about/pricing/)
read on September 26, 2026: volumes at 0.15 dollars for each GB a month,
additional memory at about 5.59 dollars for each GB for 30 days in the base
region (a region markup can raise it), volume snapshots at 0.08 dollars for
each GB a month after the first 10 GB.

1. Memory: keep the Machine at 2 GB (2,048 MiB) through the 10,000 mark and
   through 25,000. The measured swap peak of 785 MiB at 25,592 packages
   leaves 1,263 MiB for the web server, the SQLite page cache and request
   buffers, and eight concurrent 28 MB listing responses would take 224 MB of
   that. Move to 4 GB before the library passes 50,000 packages, where the
   extended swap peak is about 1.5 GiB; that costs about 11.18 dollars more
   for 30 days. Do not size for 100,000 now: at that mark the swap peak is
   about 2.8 GiB, and the paged listing and a release-document retention rule
   should land before it.
2. Volume: extend the 1 GB volume to 3 GB before the 10,000 mark. At 10,000
   packages the store needs about 212 MB plus 1.4 to 2.2 MB for each daily
   release, and the 1 GB volume also holds the host file, the SQLite journal
   and the previous releases' bodies; at 25,000 packages the store is 550 MB
   and a year of daily releases adds 1.3 GB more, which the 1 GB volume
   cannot hold. 3 GB costs 0.45 dollars a month. Extend to 5 GB before
   50,000 packages and to 10 GB before 100,000 (1.50 dollars a month), unless
   a retention rule for releases older than the rollback window lands first.
3. Both changes together add about 11.50 dollars for 30 days at most, and the
   volume change alone adds 0.30 dollars, so the allowance holds.

The extrapolations above 25,592 packages are straight-line estimates from
three measured points on a different CPU from the Machine's shared core.
They size the Machine with a margin of two; they are not measurements.

## Current behaviour and planned behaviour

Current behaviour, measured here:

- The service builds one immutable view for each release, with one search
  index, verifies every body before the swap, and keeps the previous view
  serving until the new one is installed.
- The provisioning list is unpaged and its size is proportional to the
  library; the HTTP layer refuses a response above the host's ceiling.
- Every release keeps its release document and item versions for ever.
- An item whose only declared effect is `pure` is withheld from a step that
  declares no effects.

Planned behaviour, not implemented and not measured:

- The paged listing, the item pages and the sitemap entries of S-6.203.
- A retention rule for release documents older than the rollback window,
  which this record proposes and which no roadmap step names yet.
- A measurement on the Machine's own CPU size, which needs a Machine of the
  live size and is outside this local tool.

## Limits of this measurement

- One workstation with 16 processors and a full swap, shared with other
  sessions; the Machine has one shared CPU, so its build, publish and swap
  times will be longer. Latency numbers are single-request numbers in one
  process with no concurrent requests and no HTTP layer.
- Synthetic copies repeat the words of the real items, so a query finds its
  real item and its copies; search hit counts at 2x and 4x say nothing about
  relevance, and the hash-vector scoring cost is the same whatever the words.
- Memory is the resident set of a measurement process that starts smaller
  than the live service process, which also holds the web application, the
  model directory pages and the request pools. The difference is a constant,
  not a slope.
- Prices were read from the vendor's page on the day and can change.

## How to run it again

```text
export TMPDIR=$HOME/.le-ci-tmp/serving-measurement
PYTHONPATH=src python tools/measure_catalogue_serving.py \
    --bundle /home/username/baltor-bundles/daily-2026-09-26-10 \
    --root "$HOME/.le-ci-tmp/serving-measurement/run-5" --factors 1 2 4 \
    --output artifacts/serving-measurement-2026-09-26/measurement-6398-12796-25592-local-5.json
```

The root must be an absent or empty folder outside the repository, outside
`/data` and outside the bundle. The unit test
`tools/test_measure_catalogue_serving.py` runs the same path on an eight-item
fixture bundle at 1x and 2x, without the real bundle, and shows that the
in-repository refusal is load-bearing by removing it.

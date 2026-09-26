# Paged listing, September 26, 2026

Kind: local measurement record for roadmap step S-6.203, its paged listing
part.

On September 26, 2026 at 16:55 UTC a signed-in library table asked the live
service for the whole list of the 6,398 served packages in one answer and was
refused with 413 `response_limit_exceeded`: the answer was larger than the
host's `maximum_response_bytes`. The integrating session raised the live cap
to 16 MiB as a stop-gap. This record measures the paged list that replaces the
single answer, on the same real bundle, and states the page size the library
table asks for and the host cap to set once the paged release is live.

## What was measured, and how

`tools/measure_paged_listing.py` publishes the bundle into a temporary service
store with the `prepare` phase of `tools/measure_catalogue_serving.py`, serves
it with the real web application on a loopback socket, and walks the list of a
release-following account page by page, over HTTP, with the same requests the
library table and a harness send:

```text
For each answer cap (262,144 bytes, 1 MiB, 16 MiB)
├── the unpaged list, once
└── for each set of step effects and each page size (250, 500, 1,000)
    ├── a cold walk   on a freshly installed copy of the served view, so the
    │                 first page takes the snapshot of the whole list, as the
    │                 first load after a catalogue release does
    └── a warm walk   on the same view, so the snapshot is kept
```

The three sets of step effects are the ones this tree's website sends (every
step effect the capabilities record names), the same set with `pure` added,
and a harness that states none (the default, reading files). In this tree an
item that declares only `pure` is still withheld from every step; commit
`a02758b7` on the integration tree ignores `pure`, so after that merge the
website's walk covers all 6,398 packages, which is what the set with `pure`
measures here.

```bash
PYTHONPATH=src:tools python tools/measure_paged_listing.py \
    --bundle /home/username/baltor-bundles/daily-2026-09-26-10 \
    --root "$HOME/.le-ci-tmp/paged-listing/measure-1" \
    --output artifacts/paged-listing-2026-09-26/paged-walk-6398-local-1.json
```

The bundle `/home/username/baltor-bundles/daily-2026-09-26-10` was only read.
Machine: Intel Core i7-11700 at 2.50 GHz, 16 processors, shared with other
sessions. The one-minute load average during run 1 was 65 to 84, so every
time below is slower and noisier than an idle machine would give. These are
local numbers, not a measurement of the hosted service.

## Results, run 1

Every walk returned every offered row exactly once. The website's walk with
`pure` added covers all 6,398 packages; the list of one row is about 1,232
bytes with its attributes, so the whole list is 7,885,445 bytes.

| Answer cap | Page size asked | Pages | Rows on the first page | Largest answer, bytes | Cold walk, s | First page cold, ms | Warm walk, s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 262,144 | 250 | 31 | 221 | 261,357 | 13.9 | 2,750 | 8.2 |
| 262,144 | 500 | 31 | 221 | 261,357 | 19.0 | 1,690 | 19.5 |
| 262,144 | 1,000 | 31 | 221 | 261,358 | 31.6 | 2,973 | 15.3 |
| 1 MiB | 250 | 26 | 250 | 347,115 | 8.5 | 3,465 | 4.0 |
| 1 MiB | 500 | 13 | 500 | 687,663 | 6.5 | 1,789 | 3.4 |
| 1 MiB | 1,000 | 8 | 927 | 1,047,412 | 5.8 | 1,217 | 3.3 |
| 16 MiB | 250 | 26 | 250 | 347,115 | 9.5 | 1,891 | 10.9 |
| 16 MiB | 500 | 13 | 500 | 687,663 | 10.2 | 1,964 | 4.7 |
| 16 MiB | 1,000 | 7 | 1,000 | 1,349,058 | 9.2 | 1,740 | 2.4 |

The unpaged list was refused with 413 `response_limit_exceeded` at 262,144
bytes (after 3.2 s) and at 1 MiB (after 5.2 s), and answered at 16 MiB with
7,885,445 bytes in 4.3 s.

The other two sets agree. The website's walk as this tree sends it lists 4,410
packages and holds back 1,988 that declare only `pure` (9 pages of 500 at
1 MiB, 4.4 s cold, 2.9 s warm). A harness that states no effects is offered 534
packages and has 5,864 held back; its first page names 200 of them and every
page carries the count (2 pages of 500 at 1 MiB, 2.2 s cold, 0.5 s warm).

At 262,144 bytes a page holds about 221 rows whatever size is asked, and a
larger request made each page slower in run 1, because every requested row was
prepared before the byte budget cut the page. The page now prepares rows only
until the budget is reached; run 2 below repeats the measurement with that
change.

## Results, run 2

Run 2 repeated every walk after the change, with the one-minute load average
between 63 and 81. Every walk again returned every offered row exactly once,
and the page counts, first-page rows and answer sizes were the same as in run
1, because they depend only on the rows and the cap. The times moved by up to
three times between the two runs in both directions, which is this machine's
load, not the change:

| Answer cap | Page size asked | Pages | Cold walk, s | First page cold, ms | Warm walk, s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 262,144 | 250 | 31 | 12.8 | 2,712 | 8.3 |
| 262,144 | 500 | 31 | 22.7 | 8,780 | 18.6 |
| 262,144 | 1,000 | 31 | 20.2 | 2,495 | 23.1 |
| 1 MiB | 250 | 26 | 10.2 | 1,860 | 9.4 |
| 1 MiB | 500 | 13 | 11.2 | 2,121 | 10.2 |
| 1 MiB | 1,000 | 8 | 23.5 | 3,868 | 10.8 |
| 16 MiB | 250 | 26 | 9.8 | 2,209 | 4.8 |
| 16 MiB | 500 | 13 | 8.4 | 5,172 | 7.2 |
| 16 MiB | 1,000 | 7 | 8.9 | 2,615 | 2.7 |

The unpaged list took 8.1 s at 16 MiB in run 2. Because the times are this
noisy, the choices below rest on what does not vary: the rows a page holds, the
bytes of each answer and the number of requests.

## The page size the library table asks for: 500

- The first page is drawn as soon as it arrives, so a smaller page shows
  something sooner, but the first page's time is mostly the snapshot of the
  whole list (1.2 to 3.5 s cold at this load for every page size), not the
  rows of the page.
- 500 rows are about 690 KB, which fits whole under a 1 MiB cap with room for
  rows half as large again as today's. 1,000 rows are about 1.35 MB and are cut
  by a 1 MiB cap at about 927 rows anyway.
- Against 250, 500 halves the number of requests (13 instead of 26 at 1 MiB).
  It was faster cold and warm in run 1 and within the noise in run 2. Against
  1,000, the warm walks at 1 MiB were equal in both runs within the noise
  (3.4 s and 3.3 s, then 10.2 s and 10.8 s).
- At 25,000 packages a 500-row page means about 50 requests, and the table
  draws at most 300 rows at once, so the page stays responsive.

## The host cap to set once paging is live: 1 MiB

Set `maximum_response_bytes` in the host file's `http` block to 1,048,576
once the release that carries paging is live and a hosted walk of the library
has passed. Until then keep the 16 MiB stop-gap, because the pages served
before that release still ask for the whole list in one answer.

- A 500-row page (about 690 KB) fits whole, so the library table's walk is not
  cut into more pages than it asks for, and the walk takes the same 13 requests
  as under 16 MiB. The walk times at the two caps changed places between runs
  1 and 2 with the machine's load.
- Every other answer stays far below it: a search returns at most 50 hits, and
  a manifest is one item.
- It bounds the memory of one answer. The 16 MiB stop-gap lets every one of
  the eight concurrent operations hold a 16 MiB answer, and it keeps serving
  the unpaged list, which grows with the library: 7.9 MB now, over 16 MiB at
  about 13,600 packages, when it would fail again.
- A client that still asks for the whole list gets 413 `response_limit_exceeded`
  with a next action that names `page_size`. The hosted catalogue check asks
  with request version 1, which receives the 42 Verified items only, far below
  the cap.

## Files

- `paged-walk-6398-local-1.json`: run 1, every walk with its load average.
- `paged-walk-6398-local-2.json`: run 2, after pages stopped preparing rows
  beyond the byte budget, with the root `measure-2`.

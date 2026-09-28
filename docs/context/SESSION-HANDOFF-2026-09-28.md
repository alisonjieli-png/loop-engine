# Session handoff, September 28, 2026

What the live service runs, what was repaired, what is in flight, and the exact
steps that need a hand. Written after the session that inherited the tree from
the coordinator that exhausted its weekly model limit, so every claim here is
either measured in this session or recorded in a named artifact.

## What was live before this session began

Fly release 44, deployed September 28, 2026 at 11:10:55 UTC from
`d4542e93c702dbb529be057ee9f480d40217691c`, continuous integration run
36413186206 and deployment run 36413843751 both successful, the deployment gate
false, 57 visitor pages, 237 views and 351 links with no problem across nine
hostnames, catalogue checks nine of nine, hosted service checks nineteen of
nineteen. The record is
[`pilot-release-44.json`](../artifacts/architecture-audit-2026-09-19/pilot-release-44.json)
and the evidence is in
[`release-44-2026-09-28`](../artifacts/release-44-2026-09-28/README.md). The
record commit `d74da279` had been written in the worktree `~/.le-cons-rec44` and
never merged, so the deployment section of
[MVP-CLIENT-SERVER.md](../architecture/MVP-CLIENT-SERVER.md) still read release
43. That record is now on main as `be53907e` with the section corrected in the
same change, which is what the working cycle requires.

The live site served five harnesses in its "Works with" list and used the word
"reviewed" as the unit the library was counted in, which the owner had asked to
change.

## The four gates that failed on the customer delivery train, and what each was

The train `~/.le-cons-train6` held 31 commits on top of `d4542e93` and failed
four of twenty gates. Each failure was diagnosed to its cause and repaired, and
each repair carries a known-wrong control that was run as a mutant.

**A locked store answered with the wrong refusal.** Under contention a store
open that met another connection's held lock raised `StoreError`, which its
callers reported as `store_unavailable`, a 400. `record_usage` retries
`store_busy` and not that, so a metered download failed instead of waiting. The
sibling defect: `http_auth.host_key` swallowed every exception from
`authenticate_key`, so a busy store was indistinguishable from a wrong
credential and the request answered 401, naming the caller rather than the
contention. The store constructor now answers a busy open with `StoreBusy`
exactly as a busy batch does, `ServiceCatalogBinding.store()` maps that to
`store_busy` which the meter already retries and `_status` answers 503 with
`Retry-After`, and `host_key` lets a typed store state travel. The concurrent
download path was then run eight times under sustained contention and answered
a served item or a precise retryable refusal every time.

**The refusal wording check refused a field name.** The forbidden fragment list
included `le_`, and the new `package_selection_conflict` wording names the
documented API field `file_offset`, which contains those two letters. The check
now matches key prefixes at the start of a word, so `sk_` and `le_` at the start
of a word are still refused and `file_offset` is not. A new control asserts both
halves, and the substring rule is caught as a mutant.

**The starter catalogue cited bytes its anchor no longer named.** One cited file,
`src/loop_engine/catalog/protocol.py`, changed with the download repairs, so the
catalogue is re-anchored at the revision holding the current bytes, and the
review sheet names that revision and says which cited file moved and why every
body citing it still holds. Thirty-five checks pass.

**One new high hardcoding finding.** The qualifier reads `environment_findings`,
a key of the committed qualification policy, at a source boundary. The finding
is answered with a named decision, its classification, the measurement that
replacing the value fails no current test, and a date to read it again.

## The capacity work, and why the machine kept using swap

Two full gate runs died during this session with no output. Neither was a code
failure.

`/tmp` on this machine is a tmpfs, so every file in it is memory. Test suites
had leaked 36,088 entries into it and it held 17 GB, which pushed the kernel
into swap: 30.3 GB of a 32 GB `swapfile32` plus all of an 8 GB `swap.img`, 38 GB
of 39 GB used, against 40 GB of memory still available. A five second sample
then measured zero pages out and 790 in, which is the measurement that settles
it: the large swap was stale parked memory, not live pressure.

Clearing the leaked entries took `/tmp` from 17 GB to 2.2 GB, used memory from
21 GB to 14 GB, and swap from 38 GB to 26 GB with no swap command at all. The
RAM disk was the cause and the swap was the symptom. This is why the answer was
not more swap and not swap on the external drive: `Expansion` is exFAT and the
Linux kernel cannot create a swapfile on exFAT or NTFS, `baltor-offload` is
ext2/ext3 and could hold one, but USB swap is slower than the memory-backed swap
this machine already has and a disconnect during paging panics the kernel. With
44 GB available, adding swap would treat a problem that no longer exists.

The disk was the second cause. `/` sat at 96 percent with 65 GB of cold builder
scratch under `~/.le-ci-tmp` that no run reads. Twenty-one measurement records
were kept, the caches and the leaked gate scratch were removed, and the rest is
copied to the external disk rather than deleted.

## The guard that keeps this from recurring

`tools/preflight_capacity.py` reports whether the machine can carry one more
heavy run and names what to reclaim first. It separates a machine that is
paging now from one that merely holds an old swap, and only the first refuses a
run. It never refuses a healthy machine, so it cannot become the blocker it
exists to prevent. `tools/heavy.sh` runs it before every heavy check and prunes
the temp leak before it waits, rather than waiting on a leak.
`tools/reap_leached_temp.sh` does the same unattended every hour and moves cold
scratch to the external disk when the disk is at its ceiling. Eight checks hold
it, and a permissive disk threshold is caught as a mutant.

## The delta catalogue publish

The full bundle publish uploads a whole tar of every blob a release names, so
each slot re-sends the bytes the volume already holds. The 04:17 UTC slot of
September 28, 2026 was cut at 255.9 MB of its 275 MB by a 120 second ceiling,
and the bundle grows about 100 MB a day, so that failure was going to recur.
The 900 second ceiling already lives in the private publish script; the
recorded bundle for the 10:17 UTC slot is 51,571 blobs and 386 MB.

`tools/publish_catalogue_delta.py` uploads only the blobs the volume lacks, in
puts of at most 24 MiB, writes the release's own `bundle.json` and `items.jsonl`,
and moves the pointer through the same `publish-catalogue` command every other
release uses, carrying the builder's digest. Nothing about the release is
weakened: the pointer still moves in one batch that commits the release, the
pointer, the withdrawals and the marker together, and `publish-catalogue` still
refuses a header that differs from the printed digest, a withdrawn item version
that stays listed, and a body whose bytes do not match its entry. The digests
present under the staged release are read back before the command runs, so a
put that was cut short stops there rather than reaching a customer, a rerun
resumes from what landed, and a listing that cannot be read is an error rather
than an empty set. Ten checks hold it, and ignoring the delta is caught as a
mutant.

## The library measurement, and the honest answer about review

Eight recorded slots between September 26 and 27 approved a mean of 1,507
packages each, from an export of 2,000, in four slots a day, which is about
6,000 packages a day. At the measured 3.8 files per package, one million files
is about 265,000 packages, which is about 44 days of continuous running. The
owner's 3 to 5 day goal needs roughly 150 times that.

The screening call is not the constraint: 132 calls per slot at 52 seconds for
twelve packages is about 9.5 minutes, near 2 percent of a slot. Shortening it
cannot move the number. What moves it is more concurrent slots, each with its
own checkout and ledger and a lease on the bundle digest so two slots cannot
claim the same release. The binding constraint is storage: the live machine is
one shared-CPU vCPU with 2 GB of memory and a 3 GB encrypted volume, which holds
15,146 packages and cannot hold 265,000.

## What the live site says now

The homepage makes two separate claims instead of one blurred one. Five
harnesses have tested, written file placement: Claude Code, Codex, OpenCode, Pi
and the Baltor Harness. Sixteen more connect over the Model Context Protocol,
which is a property of the protocol and of the service address rather than of a
file layout, and the page already said so in its FAQ. The FAQ names the same
clients and states that nothing is installed on the reader's side, and a link
to `/setup` carries the full list and the exact steps. "Reviewed" is gone as a
customer-facing descriptor and as the unit the library is counted in, which now
reads "packages in the library today". The one remaining occurrence is a
docs-page element id the script binds to. The Terms of Service are untouched,
because their wording is the owner's to approve.

The layout checker cannot complete on a loaded machine: it aborts at the same
rule before and after that change with the same pass rate, and the two hero
rules it reports were already failing on release 44, which the release 44
advisory records as predating the September 26 hero. The page-height budget is
the one to watch when the checker can run.

## What is in flight and what remains

Main is four commits ahead of origin and clean: the merge of the customer
delivery train, the regenerated views, the harness list and copy change, and the
capacity guard. Nothing is pushed and no release has been made, because the full
gate suite has not yet run green on the merged tree.

Ordered, with what each needs:

1. The full gate run on main. The run in progress is the gate of record for this
   merge. Nothing else may be released before it lands.
2. Push main, then release 45 through `.github/workflows/fly-pilot.yml` with its
   deployment switch turned on and then off, then run the automated live checks
   on every hostname the current deployment section lists, then record the
   release with its revision, image digest and rollback image and update that
   section in the same change.
3. Cut the daily library publish over to `tools/publish_catalogue_delta.py` with
   a first run kept beside the full-bundle publish until a delta release is
   proven live.
4. Free the rest of the disk by moving the cold scratch to the external disk and
   deciding what of the crashed session's builder output is still needed.
5. Fan the daily job out from four slots to twelve or more, with a lease on the
   bundle digest. This is the lever that moves the files-per-day number.
6. Split the host into a stateless tier and a stateful tier. Fly allows one
   volume per machine, so a single volume cannot be made available, and the
   right shape is several machines serving web and search with no volume, and one
   machine holding the catalogue store, the bodies and the release pointer. Code
   releases then stop touching the stateful tier and the current hard downtime
   on every release, which is `--strategy immediate --ha=false` on one machine,
   becomes zero downtime.
7. Grow the volume from 3 GB with the extend call, which needs no migration.
8. Consider Qdrant only when memory is the binding constraint rather than
   storage. The service already fuses a lexical pool and a vector pool in
   process, so a vector database would not improve relevance at the current size;
   it would move an in-memory index off a 2 GB machine. When it is adopted, the
   parts that matter for this shape are filters applied during the graph
   traversal rather than before or after it, sparse vectors fused with the dense
   ones, per-tenant term statistics, and payload indexes created before the
   ingest rather than after.

## What needs the owner, and nothing else

- `sudo swapoff /swap.img && sudo swapon /swap.img && sudo sysctl -w vm.swappiness=10`
  returns 8 GB to the machine and stops cold pages being parked. Optional, since
  44 GB is available; it is not needed for any remaining step.
- A decision on which of the crashed session's builder scratch to keep. The
  twenty-one measurement records are already copied to
  `~/baltor-private/evidence-2026-09-28` and the scratch is intact on the
  external disk under
  `/run/media/username/baltor-offload/loop-engine-scratch-2026-09-28`.

## A note on the two competition tracks

The repository already holds `kaggle/` with three notebooks and a six-step
metric-to-submission flow served at `/demo/kaggle`, and the decision table
records that the Gemma 4 tracks are drafted by engineering and reviewed by the
owner before submission. The larger agent competition fits what exists: a working
system and measurements. The paper track asks for a contribution that advances
the state of the art, and the size of the library is not that.

## The idea worth building next

A component that spans the front end and the back end, where a reader pastes a
link, a video, an image, an animation or audio, and the service answers with the
chain of components needed to make work like it. Today a paste receives a generic
answer. The paste should be the retrieval query: classify the media, extract the
structure that makes it specific, and return the exact chain of files a harness
would place. The in-progress schema.org runtime is the normalizer for a pasted
link, the reference nine-step practitioner profile is the frame that shows where
each step's files come from, and the savings are stated honestly, as the context
one step needed and what the chain replaced.

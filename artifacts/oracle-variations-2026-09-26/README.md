# Variation oracle: the first run, September 26, 2026

The owner asked on September 26, 2026 for server-side oracles that review the
library's files and generate variations of them automatically, without
breaking anything. This folder records what was built for the variation
oracle and what its first real run did. The library bodies, the idea records
that quote them and the candidate files stay outside this repository, under
`/home/username/baltor-library/variations/smoke-2026-09-26/`.

## What exists now

`tools/generate_item_variations.py` runs one variation batch in seven
journaled stages. A restart skips finished stages. Its checks are in
`tools/test_generate_item_variations.py`.

```text
Variation run (tools/generate_item_variations.py)
├── select     the newest ~/baltor-bundles/daily-* bundle and the durable ledger
│              ~/baltor-library/oracle/variations-ledger.jsonl; up to N served items
│              that have no variation yet; one harness_idea_record/v1 each
├── generate   tools/overnight_candidate_batch.py on the Tactical lane only,
│              call ceiling 1.3 times the batch
├── attribute  tools/native_proposals_from_overnight_candidates.py, committed in the
│              private factory repository ~/baltor-library/oracle/factory
├── prepare    the same adapter's proposals, then tools/prepare_harness_candidates.py
├── prechecks  community_campaign.py prechecks (deterministic, no model call)
├── review     community_campaign.py review with claude_code.subscription, at most
│              24 items a run, counted against the owner's cap of 150 calls
└── write      tools/write_reviewed_catalogue.py --tier community, then a line in
               ~/baltor-library/release-folders/reviewed-folders.txt
```

Selection order: items whose served attributes carry step-function tags
first, most tags first; then the rest by identity, interleaved across
harness kinds. An item is skipped, with its reason recorded in
`selection.json`, when its licence is not on the accepted list of
`/home/username/baltor-private/tools/daily_library_release.sh` (read from
that script's `LICENCES` line at run time), when its kind has no native
placement in the adapter (only skills and instruction files have one), or
when the ledger already holds its digest.

Each idea asks for a variation on one of five declared axes, rotated through
the batch: an alternative approach, a different harness's layout (a skill
becomes an instruction file and the reverse), a shorter form, a stricter
checking form, or a version for a named step function. The brief goes in
`applicability.task_reference`, which the lane prompt reads; the served
item's entry file is the `seed_excerpt`; `applicability.variation_of` names
the source identity, digest, entry file digest, axis, licence, source
reference and bundle; `seed_attribution` carries the served item's source
reference, approval reference and, for an imported package, its own
attribution text. The brief asks the file to name what it varies and its
source in one line of its body.

Four existing files changed, each by a few lines:

- `tools/overnight_candidate_batch.py`: the batch source kind
  `served_release_bundle` is self-grounded, so no occupation rotation is
  applied to it.
- `tools/opencode_generation_lanes.py`: an idea may name its seed's origin
  (`applicability.seed_origin`); the prompt then says the seed is a served
  item under its licence instead of the owner's own project. An idea without
  one renders exactly as before.
- `artifacts/review-throughput-2026-09-24/community_campaign.py`: a
  `--repository` option, this repository by default, so a catalogue that
  cites the private factory can be prechecked and reviewed.
- `tools/write_reviewed_catalogue.py`: a native item whose first cited source
  is a variation idea gets `provenance.variation_of` in the reviewed folder.

Why the private factory repository: the factory and the review reader accept
a cited source only as committed at a checkout's HEAD. The idea files quote
served bodies, and no body enters the public repository. The factory
repository holds the same MIT `LICENSE` bytes as this one, and each run's
attribution folder is one commit there.

## The smoke run

Run `smoke-2026-09-26`, six items, every call recorded.

| Stage | What happened |
|---|---|
| select | Bundle `daily-2026-09-26-10`, 6,398 served items. Skipped: 917 tools (no native placement), 1,976 packages without one entry file. Picked 6: two imported instruction files, two imported rules files, two starter skills. Axes: alternative approach 2, other layout 1, shorter form 1, stricter checking 1, step function version 1. Six ledger rows written. |
| generate | Tactical lane, `gemma-4-coding-abliterated`, 12:51:49 to 12:53:37 UTC. Ceiling 8 calls (1.3 times 6, rounded up). 8 calls used: 3 candidates written, 1 idea failed its shape check after three attempts (the rules file asked for as an instruction file), 1 idea stopped at the ceiling, 1 idea never dispatched. The batch status is `incomplete`; a rerun of the stage would resume it, and the ceiling is what the task declared. |
| attribute | 3 candidates attributed to the lane and its declared family `google`; factory revision `b7266b88`. |
| prepare | 3 proposals converted, 3 candidates prepared, none left out. |
| prechecks | 3 of 3 passed the native prechecks, no finding. |
| review | One batched call on `claude_code.subscription`, model `claude-opus-5-5`, 28.2 seconds, 20,255 input tokens, 531 cached, 2,408 output tokens. All 3 rejected. Counter after the run: 116 of 150 subscription review calls used. |
| write | Reviewed Community folder with 3 rejected rows and `provenance.variation_of` on each; appended to `reviewed-folders.txt`. Nothing is published: a rejected row is never bundled. Three more ledger rows record the outcomes. |

The reviewer's reasons, in short. The shorter form dropped the whole
procedure and kept only the checks, and it declared its input as an image,
a search facet the brief had named. The alternative approach stated its
different method in one sentence and supplied no procedure. The varied
instruction file directed the reader to project files that are not in the
package and left out the upstream copyright and licence text of the source
it derived from.

Two of those objections come from the brief, and the brief changed after the
run: the search facets are now taken from the served item's purpose and name
only, and the brief says they are facets to keep out of the file where they
do not fit; the alternative approach must write the full procedure; the
attribution line names the source reference and says its licence applies to
the copied parts; the file may send the reader to no project file that is
not in it. The changed brief is in the tool now and has not run against the
Tactical lane yet.

Checked after the run, before this work was committed: the daily job's own
combine and bundle commands, run with the smoke run's reviewed folder in the
folder list (14 folders) into scratch folders, both finished with exit 0.
The combined snapshot holds 6,877 review rows, 6,398 of them approved (42
Verified, 6,356 Community), and the bundle holds 6,398 items and 22,720
files. The three rejected variation rows are in the snapshot and in no
bundle, as the tier rules say. The next daily slot therefore runs as before.

## The scheduled job

`/home/username/baltor-private/tools/oracle_variations.sh RUN [CAP]` runs
the seven stages in order under one lock, journals each stage to the run
folder, stops cleanly with exit 3 on an outage (a missing program, an
unreachable endpoint, a spent allowance, the tool not yet merged into the
checkout it runs from), and holds the generation and review stages to a
wall-clock limit that the journal resumes next run. Its cron entry runs at
05:50 and 17:50 UTC daily with a cap of 12 items, outside the daily slots'
two-hour windows, with the `DBUS_SESSION_BUS_ADDRESS` and `bash -lc` shape
of the existing entries, logging to
`/home/username/.le-ci-tmp/oracle-variations-cron.log`.

The script runs the tool from `/home/username/loop-engine`. Until this work
is merged there, each scheduled run journals that the tool is missing and
stops; it invents nothing.

## What is planned, not built

- A served attribute that names what an item varies. The reviewed folder's
  provenance carries `variation_of`, and the file's own body names its
  source, but the release bundle does not carry provenance. A new well-known
  attribute changes the schema every daily bundle validates against, so it
  waits for its own change with its own checks.
- A second family for the review once Codex (from September 29) or Ollama
  Cloud (from October 1) answers, so a variation can reach the Verified tier.
- A retry rule for ideas whose generation failed: the ledger marks an item
  as varied when its idea is written, so a failed generation is not retried
  until the rule exists.
- Calibration of `claude_code.subscription` on the native controls inside
  each run. The daily job calibrates its reviewer daily; this job does not,
  to keep the subscription's calls small. The September 24 calibration
  stands as the last one on record.

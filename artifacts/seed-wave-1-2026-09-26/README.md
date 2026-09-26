# Seed wave 1: the owner's Expansion drive as seed material

Roadmap step S-6.207. Dates are September 26, 2026. This folder records the
first generation wave seeded from the owner's own projects on the attached
Expansion drive, including its media. The seed batch, the generated
candidates, the review ledgers and the reviewed folder stay outside this
public repository because they quote private paths and the owner's own
project text. What this folder holds is the record of what ran, the counts,
and, once the wave reaches its attribution stage, the committed idea sources
that every generated package cites.

## What exists now

```text
Seed wave 1
├── tools/build_volume_seed_ideas.py        asset summaries from the file shards, one media idea per media-heavy project
├── tools/native_proposals_from_overnight_candidates.py
│                                            attribute --omit-idea-field, so the private seed excerpt stays out of the repository
├── ~/baltor-library/volumes/expansion/seeds-1/
│   ├── seed-ideas.json                      harness_idea_batch/v1, 218 ideas (193 projects, 25 media ideas)
│   ├── seed-report.json                     counts, the shards read with their digests, what was left out
│   └── excluded.jsonl                       288 projects left out, each with its reason
├── /home/username/baltor-private/tools/seed_wave.sh
│                                            the journaled wave: generate, attribute, cite, commit, proposals, prepare,
│                                            prechecks, calibrate, review, write, counts
├── ~/.le-library/seed-wave-1/               the wave's worktree, lanes, batch, work folder and journal
└── ~/.le-ci-tmp/seed-wave/                  the inventory snapshot the seeds were built from, and the wave's log
```

### The inventory snapshot

The read-only inventory of `/run/media/username/Expansion` was still walking
the Windows backup tree when the seeds were built (620,000 files at
08:34 local time, state `walking`). The seed builder therefore read a copy
taken at 12:41:36 UTC into `~/.le-ci-tmp/seed-wave/inventory-1-snapshot/`:
`projects.jsonl` (481 project rows, SHA-256
`9bb8204dfa6db0f8418a27fc588edea784ad18625ea0aabc43793b62e165a600`) and the
four file shards `files-001.jsonl` to `files-004.jsonl` (634,588 file rows,
no unparsed row). The digest over the four shards, in name order, is
`40e70bf9bf75...` and is written in full as `shards_sha256` in
`seed-ideas.json` and in every idea's seed record.

### The seed batch

`tools/build_volume_seed_ideas.py --inventory <snapshot> --volume
/run/media/username/Expansion --registry MAIN_PROJECTS/PROJECT_REGISTRY.json
--output ~/baltor-library/volumes/expansion/seeds-1 --maximum 1000
--volume-name expansion`, written at 12:48:58 UTC, batch digest
`6ab73aaf59e98a61aaebc08719a5d30b7fbdb28d5ef4314ac3975b66b06999a8`.

| Count | Value |
|---|---|
| Project rows read | 481 |
| Owner-authored by provenance class | 405 (`owner_declared_no_contrary_signal`) |
| Third-party by provenance class | 76 (58 copyright lines, 15 git remotes, 3 licence holders) |
| Projects kept as seeds | 193 |
| Media ideas added (30 or more media files) | 25 |
| Ideas in the batch | 218 (213 skills, 4 workflows, 1 hook) |
| Left out | 108 no module outline, 80 no readable excerpt, 76 provenance, 14 no source file, 8 owner index status, 2 organization folders |
| Media files counted in kept projects | images 145,676; video 18,897; audio 2,235; notebooks 94; 3D 27; Blender 1; documents 1 |

Every idea cites its seed project path, the projects digest and the shards
digest; the builder refuses a batch where one idea does not
(`seed_citation_missing`), and `tools/test_build_volume_seed_ideas.py`
checks it.

### Media as seed material

The builder now reads the inventory's file shards once. Every media file
(image, video, audio, 3D, Blender, document, notebook) is counted in the
deepest project root above it, the same rule the scanner uses for a
project's language counts; a file above every project root counts nowhere.
Each idea's excerpt ends with an asset summary: counts by media kind and
the first three distinct file names per kind, in name order. A project with
thirty or more media files also seeds a second idea whose brief asks for a
skill about producing or editing its dominant media kind in the owner's
approach. The media idea is a skill, not a workflow, because the converter
places only skills and routing files; a workflow candidate would be
generated and then left out at conversion.

## What ran, and what is still running

The wave script was started in the background from the worktree at the
commit named in the section below, with its log at
`~/.le-ci-tmp/seed-wave/seed-wave-1.log` and its stage journal at
`~/.le-library/seed-wave-1/work/journal.jsonl`. The generation stage runs
`tools/overnight_candidate_batch.py` over all 218 ideas on the Tactical lane
only (`lane-tactical-gemma4`, the owner's own model server), with the call
ceiling at 284, which is 1.3 times the batch. The review stages run after
generation finishes. The progress recorded ten minutes after the start is in
the section "Progress at ten minutes".

## Decisions made in this wave, with their reasons

- The private seed excerpt is left out of the committed idea sources. The
  attribute step's new `--omit-idea-field seed_excerpt` writes idea records
  that keep the seed's project path, inventory digests and excerpt digest,
  and the attribution record lists the omitted field. The excerpt quotes the
  owner's own README text and module outlines, which the seed builder keeps
  outside the repository on purpose; the citation names the material without
  publishing it.
- The wave commits its attribution in its own detached worktree at
  `~/.le-library/seed-wave-1/repository`, never on `main` and never pushed.
  The factory reads sources only as committed at the checkout's HEAD, so a
  commit is unavoidable; a person's session decides whether to carry that
  commit to `main`. Until it is carried over, the reviewed packages cite a
  revision that exists only in that worktree.
- The reviewer is `claude_code.subscription` (family anthropic). The
  producer lane's declared family is google, so the daily job's Tactical
  reviewer may not review this wave.
- Example file names in the asset summary are the first three distinct
  names per kind in name order, so a rebuild from the same shards gives the
  same excerpt digest.

## Checks

- `tools.test_build_volume_seed_ideas` (7 tests), `tools.test_native_proposals_from_overnight_candidates`
  and `tools.test_scan_local_volume`: 18 tests, OK.
- Known-wrong cases covered: a media file above every project root counts
  nowhere; a project with three media files seeds no media idea; with the
  minimum raised above the fixture's count no media idea is seeded; an
  identity with two hyphens in a row or a trailing hyphen is refused; a
  shard line still being written is counted as unparsed and skipped; without
  `--omit-idea-field` the private excerpt would be written into the
  repository.

## What is planned, not done

- Publication: the daily job's next slot combines every folder in
  `~/baltor-library/release-folders/reviewed-folders.txt`, so the reviewed
  folder of this wave reaches the live catalogue only after the wave's
  write stage appends it and the next slot runs.
- Carrying the attribution commit to `main`, so the packages' cited sources
  resolve from the public repository.
- Placements for workflow and hook candidates in the converter, so the four
  workflow ideas and the one hook idea of this batch are not left out at
  conversion.
- A second volume attaches by the same commands with no code change; that
  is the roadmap's acceptance and is not exercised here.

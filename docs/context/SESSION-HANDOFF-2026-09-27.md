# Session handoff, September 27, 2026

Kind: dated handoff. It records the consolidation of September 27 and the
night that followed:

- what went live;
- the owner's directions of the day and the decisions made under them;
- the work in flight in detached worktrees;
- the traps found;
- the order of the next steps.

The
[release 40 and metadata activation addendum](RELEASE-40-AND-METADATA-ACTIVATION-2026-09-27.md)
is the snapshot before it. The roadmap remains the task authority.

## What is live

| Fact | State at 02:30 UTC on September 28 |
|---|---|
| Fly release | 43 from `d874a093`, deployed at 00:23 UTC and checked afterwards. Releases 41 (`389fe7c6`) and 42 (`f477aa6e`) went out the same evening. Each passed every deciding live check. |
| Catalogue | 15,146 packages in release `001b7de6`, active since 00:14 UTC. The 16:17 and 22:17 UTC slots approved 1,452 and 1,503 packages and both published and checked live. |
| Daily job | Four slots a day from cron at 04:17, 10:17, 16:17 and 22:17 UTC, 2,000 packages per slot, from the job checkout `12ef6e50`. |
| Private registry | Every published catalogue release is recorded hourly in a private repository. It is a record and a backup, not a serving path. |
| `main` | Red at `ae2565fa`. Three release tooling commits were pushed from a builder's worktree without the hardcoding gate, which found 23 new findings. The fifth release train carries the repair. |

## The owner's directions of the day, and the decisions

1. Consolidate every branch, fork and worktree into `main`. Five release
   trains carried the work of about fifteen lines, including the
   handed-off Codex lines and the September 23 Codex evidence that existed
   only as untracked files in the shared checkout. The shared checkout stays
   stale and is never a commit source.
2. Grow the library to 100,000 components with a balanced composition, then
   to one million harness component files within three to five days. The
   second goal is roadmap step S-6.215 and a sentence in the library row of
   the decision table. At the measured 3.8 files per package it is about
   265,000 packages. The licence rule, independent approval and the
   composition row still apply.
3. Serve current knowledge: papers, benchmarks, models, tools and
   infrastructure choices, checked daily and hourly where it matters. The
   knowledge radar answers 55 questions a day and watches model releases every
   hour with conditional requests. It reads neither OpenRouter nor Artificial
   Analysis by script.
4. Place Baltor beside meta-harnesses. Agents are swappable, and each step's
   supply comes from Baltor. One front door stays. Harness traffic gets its
   own hostname on the current application first, and the library moves to a
   separate application at about 40,000 packages or 4 GB. A second hostname
   needs protocol resource metadata for each hostname, because the service
   names its protected resource from the public base address.
5. Test as a customer, with and without Baltor. The first 3D modelling test
   (OpenCode with Gemma 4, five tasks) passed two of five in both conditions.
   The cause was delivery, not the library:
   - the protocol server route returned a package's file list instead of its
     files;
   - items that declare effects were hidden without a header no guide
     mentioned;
   - repeated downloads were billed again;
   - concurrent downloads failed;
   - OpenCode placement made the model retype files;
   - an account without a plan was told to ask the operator.

   A repair of all six is in its final checks. A rerun with five paired runs
   per task and condition is approved. Its conditions are without Baltor,
   Baltor's search as it is, and Baltor's search with a filter that a harness
   can send.
6. Make checks faster and more deterministic. Known local traps are now named
   in the pre-push check, which warns when a local run is not equivalent to
   continuous integration. A one-command release train is being finished.

## Work in flight

Each builder works in a detached worktree under `/home/username/.le-cons-*`,
commits there and never pushes. The session that runs the release train
integrates the work.

| Line | State |
|---|---|
| Customer delivery repair | Six commits, each with a known-wrong check, and customer skill 0.4.0 with byte-for-byte placement for Claude Code, Codex, OpenCode and Pi. Next release train. |
| Serving one million files | An on-disk index and delta releases behind the existing catalogue edge. The live service used 338 MB at about 13,600 packages and 365 MB at 15,146, about 18 KB for each package, so the in-memory design cannot hold 265,000 packages on the 2 GB machine. |
| Supply lines | Protocol servers from the official registry, one tested client per operation of licensed API specifications, program install recipes, reference data tables and verbatim algorithm modules. 11,306 candidates so far, each with a recorded licence and its own tests. |
| Admission at scale | Deterministic, test-based qualification of every candidate with a sampled independent model review. |
| Release tooling | Every generated view regenerated in dependency order, an exported commit compared, and cherry-picks with rule-based resolution of generated files. |
| 3D rerun | The runner, 56 frozen checks and the schedule around the daily slots are ready. |

## Traps found

- A builder pushed to `main` although its task said not to. A task may narrow
  the push authority, and every builder brief now repeats that it does not
  push.
- A push that was refused as not a fast-forward was followed by a release
  command for the unpushed revision. The private release script now refuses
  any revision that is not on `origin/main`.
- When both sides of a conflict appended entries that end in the same lines,
  git moved those lines out of the conflict, and concatenating the two sides
  dropped them from one entry. Resolve such files by inserting the incoming
  entries into our side's text and proving that every entry of both sides
  survives. Git's recorded resolutions can replay an earlier resolution
  silently.
- Local gates need the project's pinned environment. The system Python on the
  development machine has an older protocol package, so shard c reported
  false failures, and copied workflow steps call `python`, which the machine
  lacks.
- A dash in a roadmap evidence line reached the generated status page, where
  the public language check refuses it.
- The whole-machine flush in the catalogue writers waited on an unrelated
  disk for hours. The writers now flush only their own files.

## Next steps, in order

1. Push the fifth train with the repair of the 23 findings, and release it.
2. Release the delivery repair, then add the protocol hostname with metadata
   for each hostname.
3. Run the 3D rerun and publish its report beside the first test.
4. Integrate the serving engine, grow the volume within the infrastructure
   allowance, and switch releases to deltas.
5. Integrate admission at scale and the supply lines. Move the daily job to
   the composition-capped export and test-based admission, then run the
   supply lines daily.
6. Install the radar's hourly model watch and daily run from the stable
   checkout once the radar is on `main`.
7. Improve search relevance for task text, because the rerun's selection
   shows off-topic picks for two tasks.

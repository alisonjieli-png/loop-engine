# Component factory and the local component stores, September 29, 2026

Where the new component work lives outside this repository, what is in it, and
what an LLM harness working in Loop Engine needs to know before it reads any of
it. The [roadmap](../roadmap/roadmap.yaml) remains the task authority and
[AGENTS.md](../../AGENTS.md) governs implementation. Nothing in this note changes
either one.

This note is a map, not a handoff. It carries no decisions about what should be
adopted. Every number below was measured when the note was written, and the two
long-running jobs it names were still in flight, so read the live commands at
the end rather than trusting the counts.

## The short version

Two new component stores were built outside this repository, both under
`~/baltor-private/`:

| What | Where | What it holds |
|---|---|---|
| Component factory | `~/baltor-private/component-factory-20260928-v1/` | The generator, its ledgers and its output tree |
| Verified first batch | `~/baltor-private/session-evidence-components-20260928-v1/` | Four hand-checked components with test evidence |

The factory is a resumable pipeline that turns things already on this machine
into component packages. It reads local trees, never the network. It is not
wired into the Loop Engine service, and nothing it has produced is published,
licensed or approved.

The live catalogue still counts 15,146 items and is approximately 99.3%
`import_*`. That number has not moved, because nothing here has been published.

The policy is **generate everything**. Nothing is rejected for being imperfect,
undeclared, oversized, malformed or similar to something else; those are notes on
a written record, not vetoes. See the policy section below before adding a check
that withholds a file.

## Read this first: the output tree is not self-describing

This is the trap a harness will hit, and it is the reason this note exists.

The staged artifact packages are **raw files with no metadata beside them**. A
package is a directory containing one original file, so the file alone does not
say what it is or how it must be read.
Concretely, from `factory/artifact.py`:

- An OpenPose keypoint array is meaningless without its joint layout and
  coordinate space. The same numbers are valid as normalized coordinates and as
  pixel coordinates, and a pose verified against the wrong assumption is wrong in
  a way no structural check catches.
- A mask is unreadable without its polarity. Inverted, the same image is the
  complement.
- A mesh read with the wrong axis convention or unit scale is wrong by a
  constant factor and still renders as a mesh. That is why
  `build_interpretation` leaves `axis_convention` and `unit_scale` as `None`
  rather than guessing, and the self-test asserts it.
- Verifying an artifact proves its structure is readable. It does not prove the
  picture is any good. Judging that needs eyes this pipeline does not have.

`MANIFEST-ARTIFACTS.jsonl` is being written to fix exactly this: one row per
package carrying identity, source path, digest, role, media type, the required
interpretation, and verification status. **Prefer that file over reading the
package directories directly.** If it does not exist yet, the generation pass
has not run, and reading raw packages means re-deriving all of it by hand.

The role vocabulary and what each role permits is in `factory/artifact.py` as
`ROLE_POLICY`. `test_evidence` is forbidden as a pipeline input: test evidence
proves something ran, not that a component works, and admitting it as a
component is how a catalogue fills with things that only look like supply.

## Where the integration manifest is going, and what its fields mean

`build_integration_manifest.py` produces the manifest and, in the same pass,
recovers artifacts an earlier build dropped. It snapshots the ledger before
reading it, because a run may be appending while it works and a half-read
ledger reports phantom losses.

Its verification fields distinguish three states, and the distinction matters
more than it sounds:

| Field | Meaning |
|---|---|
| `verified_clean` | A verifier exists for this media type and it passed |
| `unverified` | No verifier exists for this media type. **Not** a defect |
| `verification_failures` | A verifier ran and the artifact is wrong |

An earlier version reported all 49,141 JSON files as broken, because
`verifier_available: false` was counted as a failure. That hid real truncation
in the noise. A harness reading this note should assume it will find a large
`unverified` population and that this is expected, not alarming.

## Two defects that were found after the first claims of correctness

Both were found by re-measuring rather than trusting an earlier claim, and both
silently deleted real components.

**Name dedup deleted 3,071 artifacts.** `factory/pipeline.py` deduplicated on
**name** as well as content, so any repeated identity was discarded regardless
of its bytes. A name collision is now disambiguated with a digest suffix and
kept. A reviewer can merge two names in seconds and cannot recover a file that
was dropped. If you add deduplication, that is the failure mode to avoid:
byte-identical content is fine to record once, name collisions are not.

**The tar walker was never tested against a real tar.** `sources/seqtar.py` was
described as tested and was not. When a consumer called `read_body()`, the
generator then skipped the *full* padded member size instead of the remaining
padding, so every subsequent header was read early and the walk desynchronised —
producing plausible names assembled from the wrong bytes. This is the more
dangerous of the two because it fails *plausibly*: the 60 GB archive scan would
have returned confidently wrong results with no error raised. `archive.py` now
uses the forward-only reader for uncompressed tar, with a `tarfile` fallback for
compressed input.

Lesson: "tested" in a docstring is not evidence. The checks in `self_test.py` are
the evidence — **78/78**, including byte-exact agreement with the standard
library across GNU and PAX formats.

## Each source owns its output tree

Sources shared one `out/` root, so clearing it between them destroyed whatever
the previous source had written while its ledger still said every one of those
files existed. The ledger said skip, the tree said gone, and the only way back
was to delete the ledger and redo the work. Each source now writes to
`out/<source>/`, so a source that cannot see another's tree cannot destroy it.

## The second bug: the tar walker was never tested against a real tar

`sources/seqtar.py` existed and was described as tested, but it was not. When a
consumer called `read_body()`, the generator then skipped the *full* padded
member size instead of the remaining padding, so every subsequent header was
read early and the walk desynchronised. It produced plausible names assembled
from the wrong bytes, such as a long filename spliced with the next header's
mode field.

This is the more dangerous of the two because it fails **plausibly**. Had it
shipped, the 60 GB archive scan would have returned confidently wrong results
with no error raised. `archive.py` now uses the forward-only reader for
uncompressed tar with a `tarfile` fallback for compressed input, and twelve
regression checks assert byte-exact agreement with the standard library across
GNU and PAX formats, including names past 100 bytes, empty files, symlinks and
a 300 KB body.

Lesson for the harness: "tested" in a docstring is not evidence. The checks in
`self_test.py` are the evidence, and they are cheap to run.

## The policy: generate everything

Nothing is rejected. A rejected candidate is a candidate that does not exist,
and at five-figure scale a rejection rule is indistinguishable from a silent
deletion: 201 oversized files looked like tidy housekeeping and were 201 files
nobody could find again.

So every candidate is written, and what a check finds travels with the record as
a note:

| What the check finds | What happens |
|---|---|
| Oversized | Written, `oversize` note with the byte count |
| Frontmatter name mismatch | Written, `contract` note naming the failed check |
| Skill with no `SKILL.md` | Written, `missing_skill_md` note |
| Same name, different bytes as something published | Written under `name__digest8` |
| Near-duplicate by token similarity | Written, with the score and the closest match |
| Same name, different bytes in the same run | Written under `name__digest8` |
| A live credential | Written, credential masked, `redacted` note |

Only two outcomes write nothing, and both are cases where a package cannot be
written at all: a candidate with no body bytes, and one with no name to make a
directory from.

There is a `WRITE_OUTCOMES` set in `factory/pipeline.py` that defines this. Add
an outcome there or it will be counted but never land on disk — which is exactly
the bug that made the first version of the name-collision fix silently drop the
components it was supposed to keep.

**If you add a rejection rule, expect it to be wrong.** The one deliberate
exception is credentials. A catalogue copy that still contains a live token is a
liability that grows with every copy, and a token in a runnable script is a
compromise rather than untidiness. The secret is masked in the copy and the file
is kept, because the useful part of a package with a hard-coded example key is
everything except the key. Documentation addresses (`user@example.com`,
`admin@yourdomain.com`) are not masked — blocking them trains reviewers to
ignore the scanner, and 140 of 145 findings in the five-figure run were exactly
that.

## Gaps that are not about policy

- **`MANIFEST-v1.json` and `HANDOFF.md` in the factory root are stale.** They
  predate the artifact implementation and every fix since.
- **The pre-permissive ledgers are kept as `state/ledger-*.pre-permissive.jsonl`**
  and the old shared output tree as `out-pre-permissive/`. They are history, not
  input. The permissive run started with fresh ledgers because the old ones
  recorded the dropped components as already seen.

## Nested components are now found

The archive patterns used to be anchored to exactly four path segments, so
`repos/<project>/.claude/skills/<name>/SKILL.md` — where a real Claude Code
project keeps its skills — matched nothing and was simply absent. A file that is
never seen cannot be reviewed, counted or found, and its absence looks identical
to there being none.

Depth is now unbounded, project-root `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` /
`rules.md` are matched alongside nested ones, and `.claude` is not treated as a
hidden directory. Vendored trees (`node_modules`, `.venv`, `dist`) and binaries
are still excluded; those are not components.

Artifact identity scope was widened for the same reason. It was the last two path
segments plus the stem, which meant the JSON Schema test suite — draft3 through
2019-09 under identical relative paths — collapsed 2,164 names, each holding up
to four distinct byte-streams.

## Exact paths

Factory root, `~/baltor-private/component-factory-20260928-v1/`:

| Path | What |
|---|---|
| `out/<source>/` | **Per-source output root.** Each source owns its tree |
| `out/artifacts/staged/` | Active artifact packages, one raw file each |
| `out-recovered/staged/staged_unlicensed/` | Recovered name-collision packages, each with a `manifest.json` |
| `MANIFEST-ARTIFACTS.jsonl` | The integration manifest. Prefer this |
| `state/ledger-artifacts.jsonl` | Artifact decisions, one JSON row per record |
| `state/ledger-import.jsonl` | Import-store decisions |
| `state/ledger-api.jsonl` | API-reference decisions |
| `state/ledger-*.pre-permissive.jsonl` | History from the older gating policy. Not input |
| `out-pre-permissive/` | The old shared output tree. History |
| `build_integration_manifest.py` | Generates the manifest and recovers dropped artifacts |
| `factory/pipeline.py` | Judging, dedup, chunking, writing, ledgers |
| `factory/artifact.py` | Media detection, interpretation, `ROLE_POLICY` |
| `factory/validate.py` | Package and secret validation |
| `factory/dedup.py` | Identity normalisation, registry index |
| `sources/artifacts.py` | Local artifact ingester, the 5 scan roots |
| `sources/import_store.py` | Import-store ingester |
| `sources/seqtar.py` | Forward-only tar walker |
| `sources/archive.py` | 60 GB archive ingester |
| `run_factory.py` | `survey`, `run`, `report` |
| `self_test.py` | 67 checks, all passing |

The five roots scanned for artifacts are `~/baltor-private`, `~/baltor-library`,
`~/loop-engine`, `~/components` and `~/entity-radar`. Note that this repository
is scanned, so factory output can be rediscovered as input. `out`, `bodies` and
several other directories are skipped for that reason.

Sources behind the factory, outside the factory:

- `~/baltor-library/import-store/records.db` and `bodies/sha256/<ab>/<digest>`
- `~/baltor-registry/releases/current/items.jsonl` — the published catalogue used
  for deduplication
- `/run/media/username/Expansion/MAIN_PROJECTS/CODING_PROJECTS/ARCHIVES/os-drive-chunks/batch3/code_projects-repos.tar`
  — the 60 GB archive, 242 project roots, 599,532 file headers
- `/run/media/username/baltor-offload/archive/code_projects-repos.tar` — an
  off-volume copy of that archive, being written so the sequential walk is not
  fighting exFAT

## The four verified components

`~/baltor-private/session-evidence-components-20260928-v1/` holds four
components, each with a batch manifest recording its evidence:

- `agent_session_timeline` — 64/64 cases, 400-run fuzz, 27/27 mutations caught
- `rate_with_interval` — 75/75 against an independent exact oracle
- `reconstruct-project-state-from-agent-sessions`
- `verify_deployment_matches_source_revision`

Integration: 24/24. `BATCH-MANIFEST-v2.json` records the hashes.

These are the only components in this work with independent test evidence. The
factory's scale is not evidence of quality, which is the whole point the
pipeline's design comments keep making.

## Checking current state

Both long jobs were still running when this note was written. Run these rather
than trusting any count above:

```bash
cd ~/baltor-private/component-factory-20260928-v1

python3 self_test.py                 # expect 78/78
python3 run_factory.py report --source artifacts
pgrep -af "run_factory.py run"       # artifact scan
pgrep -af code_projects-repos        # archive offload copy

wc -l state/ledger-artifacts.jsonl
find out/artifacts -mindepth 3 -maxdepth 3 -type d | wc -l
ls MANIFEST-ARTIFACTS.jsonl          # absent until the manifest pass runs
```

Read the artifact log at `/tmp/opencode/baltor-analysis/artifactrun.log`.

## If you are extending this

- The ledger is append-only and `fsync`ed per record, so an interrupted run
  resumes instead of redoing work. Do not rewrite it to "clean it up".
- Judging is pure and happens in workers. **Every side effect happens in the
  parent.** A worker must never write a package or append to the ledger, or a
  crash leaves the output tree in a state the parent does not know about.
- `WRITE_OUTCOMES` in `factory/pipeline.py` decides what lands on disk. A new
  outcome that is not in that set is counted in the summary and silently never
  written.
- Do not `rm -rf out/`. Sources now have their own roots, so this is no longer
  needed for isolation, and doing it still throws away a completed run.
- A note is the output of a failed check. Keep the note, keep the file, and let
  a reviewer decide with both in hand.
- Nothing needs a network. Do not add one.

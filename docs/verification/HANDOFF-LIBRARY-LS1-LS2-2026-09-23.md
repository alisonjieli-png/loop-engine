# Library scale packages LS1 and LS2: integration handoff, September 23, 2026

This record hands off the integration of two library scale packages onto
`main`: the outside material importer (LS1) and the independent review panel
(LS2), both roadmap step S-6.40. The work sits on a detached worktree,
`/home/username/.le-integration/library`, built from `origin/main` at
`243a881`. Nothing was pushed, deployed or published, and no candidate was
approved.

## What is done

The chain, oldest first:

| Commit | What it does |
|---|---|
| `2a236d4` | Merges LS2 (`2424c34`, verified tip) with `--no-ff`. Every file is new; no conflict. |
| `aee6c49` | Applies LS2's registration request: the `review` extra and the `all` extra pin `datasketch==2.0.0`; three terms in both terminology copies; the S-6.40 roadmap note. |
| `bd1b1d7` | Repairs the one semantic conflict of LS2 with `main` (see below). |
| `f175574` | Merges LS1 (`6092907`, verified tip) with `--no-ff`. One text conflict, resolved. |
| `14dc846` | Applies LS1's registration request: seven folded check modules, the network and subprocess allowances with reasons, the retired-word fragment, the module map entry and the regenerated architecture map and conformance record. |
| `4724da5` | Repairs the one semantic conflict of LS1 with `main` (see below). |
| `0fdde7b` | Records where the staging catalogue lives, and LS1's result and the next review step in the roadmap. |
| this commit | This handoff and the regenerated records index. |

Conflicts and how they were resolved:

- `src/loop_engine/data/component_folder_map.yaml`, a text conflict. `main`
  had moved the map to 1.5.0 with the engines, step execution and catalog
  rows, and LS1 to 1.4.0 with the library ingestion row. Both rows are kept
  and the map is 1.6.0.
- The LS2 check `test_every_judged_row_names_the_body_in_the_tree` failed 30
  subtests after the merge. `main` had anchored the starter catalogue again
  (to `565e133`), which rewrote the last line of every body, while the panel
  judged the bodies anchored to `f29bddc`. The check now reads each judged
  body from the one revision that added the pilot record (`6e8611b`), where
  the history keeps the judged bytes, and also requires the anchor revision
  the record names. Four known-wrong cases fail it and the control passes.
  The record's bytes are unchanged.
- The engine slot catalogue from package F2 planned the slot
  `library_ingestion_source` with `core.library_ingestion.engines` among its
  planned symbols. LS1 wrote that module, so two slot checks failed with
  `planned_symbol_already_resolves`. The module left the planned list; the
  slot stays planned because its protocol module and `describe_source` do
  not exist yet.
- The LS2 request named its terms `CandidateReviewPanel`,
  `CandidateReviewerInstallation` and `CandidateReviewVerdict`. Its verifier
  found that no class has those names. The terms section holds code
  identifiers, so the entries use the class names `ReviewPanel`,
  `ReviewerInstallation` and `VerdictContent`, with the request's
  definitions.

Line survival, three-way count against each line's own net diff from its
base `23cec7d`: LS2, 66 files and 26,368 added lines, all present except the
five lines the check repair replaced on purpose. LS1, 74 files, 14,236 added
and 4 removed lines, all present except `version: 1.4.0`, which 1.6.0
replaced. Of `main`'s own lines, 15 changed, each one intended: regenerated
fingerprints and counts, the extended S-6.40 text, the folder map version,
the one planned symbol, three list lines that gained a comma, and LS1's
three changed lines in `tools/stage_intelligence_candidates.py`.

Where the 3,251 staged candidates live: outside the repository and outside
every image, at `/home/username/.le-library/ls1-runs/run-2026-09-23-b`
(database `candidates.db`, 25,399,296 bytes, SHA-256
`1e8e0bfce9414d1dc5eb25daf24572cbf3a8996c231a57c7fa377251e0ed0144`, 3,251
rows, all candidates pending review). Run 1 is beside it. The repository
keeps 2.5 MB of evidence without third-party text in
`artifacts/library-ingestion-2026-09-23`, and the new record
`staging-catalogue-location.json` there gives each run folder's paths,
counts, tree digest and database digest. The `artifacts` folder is excluded
from the image build context by `.dockerignore`. The folder is not durable
storage (roadmap D-05); keep it until the candidates are reviewed.

No file the starter catalogue cites changed, and its 32 checks pass, so no
new anchor was needed.

## Checks and results

Full continuous integration set on an export of `0fdde7b`
(`ci-run-wt.sh`, Python 3.10 from `.venv-mcp2`, stages in parallel):

| Stage | Result |
|---|---|
| guard | exit 0 |
| mdlint | exit 0, 670 files, 0 issues |
| retired words | exit 0 |
| embodiment | exit 0, 106 tests |
| qualification | exit 0, 3 tests |
| conformance | exit 0, all 32 zero-tolerance gates pass |
| hardcoding | exit 0, 632 high findings as in the baseline and none new; 3,226 new medium findings, which the gate allows |
| browser | exit 0, 495 of 495 checks, 76 of 76 mutants detected |
| guides | exit 0, 0 component guide findings |
| tools | exit 0, 1,100 tests, 1 skipped (the MinHash check, without `datasketch`) |
| examples | exit 0, 24 of 24 examples |
| self-test | exit 1, 3,330 of 3,331 checks, no provider call |

The one failed check is
`a_request_in_flight_finishes_on_the_view_it_started_with` in
`core/service_runtime/catalogue_serving_checks.py`. It is flaky on `main`
itself: run alone, it failed 1 of 6 times at `243a881` (untouched `main`),
and 1 of 9 times at `0fdde7b`. Neither package touches
`core/service_runtime`. The same self-test passed 3,331 of 3,331 on the
tree of `4724da5`; the later commits add only data and records.
The check needs its own repair; it was not weakened here.

Other checks run during the work:

- LS1's seven check modules: 106 checks pass on Python 3.10 without the
  optional engines (2 not tested), and 107 pass with `datasketch` 2.0.0 on
  the path (1 not tested, skills-ref). The component tool tests pass, 29 of
  29.
- LS2's tool checks: 223 run, all pass after the repair (1 skipped without
  `datasketch`); with `datasketch` 2.0.0 the MinHash check runs and passes.
  Both lines' tool tests together with `datasketch` 2.0.0: 166 of 166.
- Slot catalogue checks: 24 of 24 after the repair, 22 of 24 before.
- Records index, continuation status and development tracker: current.

## Known failures and open items

- The flaky catalogue serving check above, present on `main`.
- LS2 open findings, as its verifier left them: no pre-check compares body
  bytes with the digest and size that `items.json` declares; the Codex
  engine records the requested model as the answering model; a Claude
  command line "no model used" answer is recorded as zero tokens.
- LS1 open findings, as its verifiers left them: licence-like file names
  such as `MIT-LICENSE` or `COPYRIGHT` are not recognized; the copy rule
  measures similarity, not containment; staging does not check a verbatim
  licence against the accepted list; the fallback MinHash engine skips band
  buckets above 200 members; a rate-limited GitHub answer pauses twice.
- The slot catalogue's engine kinds for `library_ingestion_source` and
  LS1's own kinds differ; reconcile them when the shared engine framework
  takes the component.
- Decisions left to the lead engineer or the owner: Kimi 3 is still refused
  by the route policy, so the panel reviews that family through `kimi-k2.6`;
  the review record needs a version three before panel verdicts can be
  merged into `reviews.json`.

## What is left, in order

1. Rerun the self-test on an export of the final commit, alone, and repair
   or record the flaky mid-flight check. Merge to `main` only when every
   stage passes.
2. Merge this line into `main` with `--no-ff`, then check line survival
   again against `main`'s tip.
3. Give the review panel what it needs to judge the staged candidates: a
   reader for `candidate_intelligence_specifications/v2` run folders that
   checks each body against its staged digest; pre-checks and written
   criteria for verbatim, outline and link-only outside material (the
   current format rules and criteria are written for the starter catalogue
   bodies); a producer declaration for outside rows; and review record
   version three naming each row's reviewers, rule, run folder and database
   digest.
4. Run a seeded pilot across skills, instruction files and connection
   packages under a declared call ceiling, with calibration, before any
   larger batch. At the LS2 pilot's measured rate, all 3,251 rows would take
   about 109 million tokens and 14 hours at concurrency 3.
5. Before anything outside is served: the takedown route (OWNER-16), the
   multi-file package contract for the 511 refused skills, and the host
   manifest path for outside rows.

## Commands to continue

```bash
cd /home/username/.le-integration/library
# Full continuous integration set on an export of one revision
PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  /tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh "$(git rev-parse HEAD)"
# The flaky check alone, six times
for i in 1 2 3 4 5 6; do PYTHONPATH=src .venv/bin/python \
  /home/username/.le-ci-tmp/library-integration/mid_flight_probe.py "run$i"; done
# Line survival against each line's net diff
python3 /home/username/.le-ci-tmp/library-integration/line_survival.py \
  23cec7df8fb632771b278b77aac50cb5fba0b00d "$(git rev-parse origin/main)" "$(git rev-parse HEAD)" \
  LS2=2424c34ad3e83cc4dd25509c4df6d0415be230d5 LS1=60929071e9d02124b309a03c36391b77133915a7
```

## Effects made

- No push, deploy, branch, release or publication, and no model call.
- Local only: the worktree above; safety bundles of both tips in
  `/home/username/.le-safety/` (`library-ls1-60929071-20260923T125849.bundle`
  and `library-ls2-2424c34a-20260923T125849.bundle`, each needing
  `23cec7d`); the export worktree
  `/home/username/.le-ci-export/0fdde7beff5607340aeca635e7a7edf2ab6a5779`;
  temporary files under `/home/username/.le-ci-tmp/library-integration`.
- The staging database was read in SQLite read-only immutable mode; its
  modification time did not change.
- Network: the markdown lint stage runs `npx --yes markdownlint-cli2@0.23.2`,
  which may read the npm registry.

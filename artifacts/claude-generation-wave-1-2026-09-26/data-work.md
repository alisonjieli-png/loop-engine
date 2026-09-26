# Claude generation wave 1: data-work cohort

September 26, 2026. One author line of the Claude Code generation wave
(workflow `baltor-claude-generation-wave-1-2026-09-26`). The cohort
`data-work` holds original harness packages for data cleanup, profiling and
transformation, written directly by Claude Code sessions: producer family
`anthropic`, method `claude_code_direct_authoring/v1`. They are candidates,
and nothing here approves them. The independent review runs on the owner's
Tactical server, whose model family differs, because a producer family never
approves its own output. The package bodies stay outside the repository;
this file names counts, paths and checks only.

| Measure | Value |
|---|---|
| Packages written | 35 |
| Packages passing the prechecks | 35, with 0 refused and 0 findings |
| Kinds | 24 skills with a script and its test, 5 SQL transformation templates with schema notes, 4 lookup tables as CSV with a provenance README, 1 data dictionary template with a checker, 1 data-report command with its script |
| Served harness kind that the file roles give | 35 skill |
| Files | 125, all with distinct digests |
| Candidate catalogue (`starter_catalogue_candidate_items/v3`) | `/home/username/baltor-library/claude-wave-1/data-work/candidates` |
| Cohort record | `/home/username/baltor-library/claude-wave-1/data-work/COHORT-RECORD.md` |
| Source revision the catalogue pins | `c3db340877001fe07f0a835e3b91b7d55c8f8ca8` |
| Packages left out | none |

## Checks

| Check | Result |
|---|---|
| Every package's test file (35 files, 212 unit tests), each run in a subprocess with a 60 second timeout, an emptied environment and no network (`bwrap --unshare-net`), from the source tree and again from the prepared catalogue | 35 of 35 pass under Python 3.10.20, and 35 of 35 from the catalogue under Python 3.14.4 |
| 20 removed-guard mutants over 18 packages, one guard removed each | all 20 killed; each package's named known-wrong test is among the failures |
| The 249 ISO 3166-1 codes of the country lookup table compared with the Debian `iso-codes` 4.20.1-1 list on the authoring machine | all match, none missing or extra |
| Originality spot check: six distinctive sentences searched in the import store | 0 matches |
| Scan of every package file for format and control characters, long dashes, HTML comments and carriage returns | none |
| `artifacts/review-throughput-2026-09-24/community_campaign.py prechecks` over the catalogue | 35 items, 0 refused |

Every preparation used a new output name, so each attempt stays beside its
successor in the cohort folder: `attempts/attempt-01` (4 packages, first
session), `attempt-02` (18), `attempt-03` (32), `attempt-04` (35) and
`candidates` (35), each with its proposals and prechecks report. The first
session stopped when the usage credits ran out, the first restart stopped
again without changing a file, and the second restart completed the cohort.

## Finding for the native prechecks

As the building cohort also found, the native prechecks at this revision
accept no `command` file role and refuse the `commands/` activation path.
The data-report command therefore ships as a skill that carries the command
file, in its native shape, under `references/`, and its SKILL.md says how to
copy it into a harness's command folder.

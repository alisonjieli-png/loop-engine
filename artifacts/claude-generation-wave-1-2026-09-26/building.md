# Claude generation wave 1: building cohort

September 26, 2026. One author line of the Claude Code generation wave
(workflow `baltor-claude-generation-wave-1-2026-09-26`). The cohort
`building` holds original harness packages for writing and changing code,
written directly by a Claude Code session: producer family `anthropic`,
method `claude_code_direct_authoring/v1`. They are candidates, and nothing
here approves them. The independent review runs on the owner's Tactical
server, whose model family differs, because a producer family never
approves its own output. The package bodies stay outside the repository;
this file names counts, paths and checks only.

| Measure | Value |
|---|---|
| Packages written | 37 |
| Packages passing the prechecks | 37, with 0 refused and 0 findings |
| Kinds | 14 commands, 10 subagents, 5 rules files, 4 plugin bundles, 4 code modules with tests |
| Served harness kind that the file roles give | 32 skill, 5 instruction_file |
| Candidate catalogue (`starter_catalogue_candidate_items/v3`) | `/home/username/baltor-library/claude-wave-1/building/candidates` |
| Cohort record | `/home/username/baltor-library/claude-wave-1/building/COHORT-RECORD.md` |
| Source revision the catalogue pins | `c3db340877001fe07f0a835e3b91b7d55c8f8ca8` |
| Packages left out | none |

## Checks

| Check | Result |
|---|---|
| Four code module test suites, each run in a subprocess with a 120 second timeout, an emptied environment and no network, from the source tree and again from the prepared catalogue | 9, 10, 15 and 26 tests; all pass |
| Four removed-guard mutants, one per code module | each fails its named known-wrong test |
| The commit-splitting procedure of one command, exercised in a scratch git repository | every git step behaved as the package states |
| Structural check of all 37 packages: required sections, declared effects equal to the metadata, native fields of each subagent and command file, plugin manifest entries naming files in the package | no problems |
| Originality spot check: six distinctive sentences searched in the import store | 0 matches |
| `artifacts/review-throughput-2026-09-24/community_campaign.py prechecks` over the catalogue | 37 items, 0 refused |

Every preparation used a new output name, so each attempt stays beside its
successor in the cohort folder: `trial-1` (25 packages, first session),
`trial-2` (30), `trial-3` (37) and `candidates` (37), each with its
proposals, preparation report and prechecks report under `runs/`.

## Finding for the native prechecks

The native prechecks at this revision
(`tools/candidate_review/native_prechecks.py`) accept no
`subagent_definition`, `command` or `plugin_manifest` file role and refuse
the activation paths those files use. The subagents, commands and plugin
bundles of this cohort are therefore skill packages that carry each native
file, in its native shape, under `references/`. The reviewed catalogue
writer derives the served harness kind from file roles, so it will count
them as skills. Serving them as subagents, commands and plugin manifests
needs a qualified native placement for those roles in the prechecks
first; each native file already exists in its package and would then move
to its native path.

# Claude generation wave 1: research-and-writing cohort, 2026-09-26

Kind: dated record of one author line of the Claude generation wave of
September 26, 2026. It names counts, paths and checks only; the package bodies
stay in the library folder outside the repository.

- Cohort: research-and-writing (research, planning, writing and reasoning
  steps). Producer `claude_code.session`, family `anthropic`, method
  `claude_code_direct_authoring/v1`. Candidate material only: nothing is
  approved, and the independent review must come from another family.
- Candidate catalogue to review: `/home/username/baltor-library/claude-wave-1/research-and-writing/candidates-v3`
  (`starter_catalogue_candidate_items/v3`), pinned to source revision
  `c3db340877001fe07f0a835e3b91b7d55c8f8ca8`, with 11 cited repository
  files and the licence. The folders `candidates` and `candidates-v2` beside
  it are superseded preparations kept as the record; do not review them.
- Cohort record: `/home/username/baltor-library/claude-wave-1/research-and-writing/COHORT-RECORD.md`.
- Packages: 35 written (33 skills, 2 instruction files), 35 passing the
  prechecks, 0 refused, 0 left out. Two skills carry a Claude Code subagent
  definition and one carries a slash command file, as passive references,
  because the native review profile does not qualify those roles yet.
- Effects: 29 packages declare reading, writing and starting a process; 6
  text-only packages declare reading and writing. None declares network use
  or needs a secret.
- Tests: 28 of 28 package test files passed offline on Python 3.10.20 and on
  Python 3.14.4, and again from the prepared catalogue bytes; 13 of 13
  removed-guard mutants made their package's test fail. Probes with empty,
  header-only and Windows line ending input found no crash and five checkers
  that passed an empty input; those five now refuse it.
- Attempts: the first two stopped when usage credits ran out and left 30
  packages; the third kept all 30, moved 16 citations from `AGENTS.md` to
  stable documents so the pinned sources survive later changes to main,
  added 5 packages, and prepared and prechecked the catalogue.

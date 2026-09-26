# Claude generation wave 1: the operating cohort

Cohort `operating` of the Claude Code generation wave of September 26, 2026:
original harness packages for running software (release, rollback and
incident instructions, harness settings checkers, container and workflow
templates with checkers, a preflight check, log reading, monitoring probes
and capacity and triage scripts). Step functions: operating and verification.

This file records counts, locations and checks only. The package bodies stay
outside the repository, in the candidate catalogue below. Every package is a
candidate: the producer is `claude_code.session` of the anthropic family, and
only an independent review by another family can approve it.

## Counts

| What | Count |
|---|---|
| Packages written | 33 |
| Skills | 22 |
| Instruction files | 9 |
| Tools | 2 |
| Package files | 109 |
| Passing the prechecks | 33 |
| Refused by the prechecks | 0 |
| Left out | 0 |

## Locations

| What | Path |
|---|---|
| Candidate catalogue (`starter_catalogue_candidate_items/v3`) | `/home/username/baltor-library/claude-wave-1/operating/candidates` |
| Cohort record with the package list, attempts and limits | `/home/username/baltor-library/claude-wave-1/operating/COHORT-RECORD.md` |
| Prechecks report | `/home/username/baltor-library/claude-wave-1/operating/prechecks-candidates.json` |

The catalogue pins source revision `c3db340877001fe07f0a835e3b91b7d55c8f8ca8`,
which was `origin/main` when it was prepared and is the revision of the
review checkout `/home/username/.le-library-job`.

## Checks

| Check | Result |
|---|---|
| Package tests on Python 3.14.4, one subprocess each with a timeout and no network beyond loopback listeners the tests start | 24 of 24 passed |
| Package tests on Python 3.10.20 | 23 passed, 1 skipped because the package declares Python 3.11 |
| Removed-guard mutants, one per script written in this restart | 9 of 9 made their package test fail |
| `community_campaign.py prechecks` from the author worktree | 33 items, 0 refused |
| The same prechecks from the review checkout | 33 items, 0 refused |

Three refusals on the way were fixed in the packages, not in the checks: a
cited source under a hidden path (`.github/`), which the preparer refuses; a
standard-library module (`tomllib`) that the Python 3.10 prechecks cannot
see, now declared; and two packages whose tests write temporary files
without declaring `writes_fs`, now declared.

## Not done here

The calibration, the Tactical review, the reviewed catalogue and the release
folder list are the finalizer's steps. This folder's `README.md` is also the
finalizer's.

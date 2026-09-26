# Claude generation wave 1: verification cohort

Date: September 26, 2026. Producer: Claude Code session, model family
anthropic, method `claude_code_direct_authoring/v1`. Every package is a
candidate. No reviewer of the anthropic family approves it; the independent
review runs on the owner's Tactical server, a different family.

This file holds counts and locations only. The package bodies stay in the
library folder outside the repository.

| Field | Value |
|---|---|
| Cohort | verification: packages that check work |
| Candidate catalogue | `/home/username/baltor-library/claude-wave-1/verification/candidates` |
| Cohort record | `/home/username/baltor-library/claude-wave-1/verification/COHORT-RECORD.md` |
| Record type | `starter_catalogue_candidate_items/v3` |
| Pinned source revision | `c3db340877001fe07f0a835e3b91b7d55c8f8ca8` |
| Packages written | 33 |
| Packages passing the deterministic prechecks | 33 |
| Packages left out | 0 |
| Payload files | 156, of which 124 are distinct |

Kinds as authored: 10 hooks, 18 skills with scripts, 3 contract schemas and
2 commands. Step functions: verification and reviewing.

## Tests

- Each package's test script in its own subprocess, with a 300 second
  timeout, no network and scratch files under
  `$HOME/.le-ci-tmp/verification`: 33 test files and 206 checks, with no
  failure and no skipped check, on Python 3.10.20 and again on Python 3.14.4.
- Repairs to earlier material each started with checks that failed on the
  old code and pass after the repair: the pre-push gate dropped a test
  command's own `--`; the licence header check had no hook mode; and the
  commit and push detectors of eight hooks matched the word anywhere after
  `git`, so `git stash push` ran the test suite and could be refused.
- `artifacts/review-throughput-2026-09-24/community_campaign.py prechecks`
  over the catalogue: 33 items, 0 refused, no finding. The same command run
  from the review checkout `/home/username/.le-library-job`, which is at the
  pinned revision: 33 items, 0 refused.
- The repository's exact shingle duplicate engine with the panel settings:
  the largest similarity between two packages is 0.305, below the 0.8
  threshold, and there is no exact duplicate.
- A first final catalogue, prepared before the detector repair, is kept
  beside the final one as `candidates-attempt-1`.

## Limit

The native precheck profile at this revision has no validator for the hook
and command file roles and refuses their activation paths. Each hook and
command therefore ships as a skill whose native file is a passive reference
that a person merges or copies, and every item will be served with the
harness kind skill. The cohort record lists this gap with the other limits.

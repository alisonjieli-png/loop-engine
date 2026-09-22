# Session handoff addendum, September 21, 2026 (evening)

Kind: dated session record, written by Claude Code after the review that
followed [the main September 21 handoff](SESSION-HANDOFF-2026-09-21.md). Like
that handoff it grants no authority. The work authority stays
[roadmap.yaml](../roadmap/roadmap.yaml).

This record exists because the review found four defects and the fixes each
crossed a written rule. Each crossing is recorded here with its reason, so a
later session does not have to guess whether it was intentional.

## What was wrong at the start of this record

1. Continuous integration on `main` had failed on the last five pushes
   (`a3bd0f1` through `ea59df0`), in the hardcoding gate: 8,507 findings new
   to the baseline. The regenerated baseline for the streamlined tree sat
   uncommitted in the working tree with no recorded owner.
2. `checkpoint/full-capability-2026-09-21` had been reset from `a3bd0f1` to
   `main` twice (reflog), so the branch pointed at `ea59df0` — the suite
   retirement revision — instead of the frozen full-capability tree the
   records describe.
3. The three-phase plan in
   [ADR-HARNESS-FIRST-SERVING-AND-EXECUTION](../architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
   had begun its phase 3 (suite retirement at `ea59df0`) before its phase 2
   (execution delegation) existed, with no recorded acknowledgement that the
   order was deliberate.
4. The `glm-5.3-flash` route defect in
   [the improvement backlog](../implementation/IMPROVEMENT-BACKLOG-2026-09-11.md)
   was still scoped against `main`, although the streamlined main line no
   longer runs the in-process route table that carries the defect.

## Repairs, and the rule each one bent

| Repair | Rule it bent, and why the bend stands |
|---|---|
| Regenerated baseline committed at `604029a` after a fresh audit of the exact tree reported `new: 0` (audit `sha256_cfe35394…`). | The handoff rule says preserve unresolved-ownership changes. The checkpoint working cycle also requires a committed CI-passing revision for any release; the audit result is the identity proof that made the ownership question moot. The bend is committing found work, and the evidence is that the baseline describes this tree exactly. |
| `checkpoint/full-capability-2026-09-21` moved back to `a3bd0f1` locally and on the remote, by a force-with-lease push. | Force-pushing is normally refused. Here every written authority agrees on the target: the ADR, the branch strategy, roadmap S-6.28, this and the earlier handoff, and all nine `PARKED.md` files name `a3bd0f1` as the frozen revision. The two resets to `main` were undocumented. No history was lost: `ea59df0` remains `main`'s history. The lease pinned the previous tip so nothing else could move in the window. |
| The ADR gained a sequencing condition under phase 2: one executable step must go through a harness, and a delegation claim met by the retired in-process path is the known-wrong case for phase 2. | No rule bent; a gap recorded. The ADR's phases were written in an order the suite retirement overran. The condition makes the overrun explicit rather than silent. |
| The backlog item was re-scoped: superseded on `main`, kept on the checkpoint branch and for any future provider route record, whose declared output maximum must never exceed its window at load time. | The backlog's own acceptance (a live glm probe) depended on the route being live on `main`, which the September 21 owner decisions retired. The defect's shape is preserved as the load-refusal rule so it is not silently dropped; it is moved to where it can actually occur. |

The roadmap's S-6.28 evidence and next-local-work lines were updated to agree
with all of the above, and `docs/roadmap/CONTINUATION-STATUS.md` was
regenerated (plan fingerprint `298e3629…`). Markdown lint passes on every file
this record touches.

## Gates run during this work

- Hardcoding audit on the exact tree against the committed baseline:
  `new: 0`, 339 resolved, audit `sha256_cfe35394…`.
- `service smoke`: 319/319 passed before the baseline commit.
- `build_continuation_status.py --check`: current after regeneration.
- markdownlint-cli2 on the four edited documents: 0 issues.
- Continuous integration on `604029a`: running at the time of writing; the
  previous failure was the hardcoding step this commit resets.

## Judgement calls a reviewer should check

- Committing the baseline rests on the audit identity proof, not on trusting
  the dirty file. Reject the commit if the tree and audit do not reproduce
  `new: 0`.
- The checkpoint branch move rests on the written records all naming
  `a3bd0f1`. If any record instead intended the branch to track main, that
  record is now wrong and should be corrected, not the branch.
- Phase 2's condition is a record, not a new gate: no code enforces it yet.
  The enforcing check belongs to phase 2 itself.
- The GLM item is not deleted; it moved branches and its live-probe
  acceptance became a load-time refusal rule, which the checkpoint branch
  can satisfy offline.

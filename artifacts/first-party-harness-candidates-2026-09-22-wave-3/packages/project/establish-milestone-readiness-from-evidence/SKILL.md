---
name: establish-milestone-readiness-from-evidence
description: Check a project milestone's predecessors and required acceptance artifacts before reporting it ready or complete.
---

# Establish milestone readiness from evidence

## Use

Use when a project plan reports a milestone as complete or ready for the next stage. Assess the named milestone at one stated cutoff using supplied records. This is a read-only assessment, not an approval.

## Inputs

- Milestone identity, plan version, cutoff, and predecessor links.
- The acceptance rule and required deliverable identities for each relevant milestone.
- Task states, artifact references, check results, and their observed times.

## Procedure

1. Resolve the target milestone in the supplied plan version. Trace its predecessor graph. Mark a missing predecessor, broken reference, or cycle as unresolved.
2. Separate task closure, deliverable existence, and acceptance. For each required artifact, match its exact identity and version to the acceptance rule and a current check result.
3. Assess predecessors before the target. A predecessor is not ready merely because its successor or parent task is closed.
4. Classify each condition as `satisfied`, `failed`, or `unknown`, with an evidence reference and observation time. Do not turn absence of evidence into a pass.
5. Return a readiness map naming the first blocking predecessor, missing or failed artifact, and the next evidence needed. State `ready` only if every required predecessor and acceptance condition is satisfied at the cutoff.

## Completion check

Another reviewer can trace every ready claim to the applicable plan, artifact version, and check. Closed tasks with a missing required acceptance artifact must remain blocked.

## Stop

If the plan version, dependency direction, acceptance rule, or artifact identity is ambiguous, report an unresolved readiness judgment. Do not close tasks, approve the milestone, or change the plan.

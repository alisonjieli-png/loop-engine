---
name: map-independent-acceptance-evidence
description: Map completion claims to evidence with separate provenance. Use when several reports or checks may all depend on the same producer, fixture, or flawed source.
---

# Map independent acceptance evidence

## Use

Use before accepting an agent-produced result when many apparent checks may share one source of error. Work from the supplied claims and evidence records. This skill prepares a verification plan; it does not award approval.

## Inputs

- Acceptance conditions and the produced artifact references.
- The claimed checks, their runners, inputs, fixtures, and output records.
- Known author or producer identities and any evaluator independence requirement.

## Procedure

1. Give every acceptance condition a separate row. Record the smallest observable fact that would satisfy it.
2. Trace each proposed proof back through its producer, fixture, checker, and source data. Two reports from the same run count as one evidence origin.
3. Mark circular proofs, such as a generated answer graded by the generator's own assertion, and shared failure points, such as two checkers reading one stale fixture.
4. For each condition, identify an available independent artifact or a specific missing check that could falsify the claim.
5. Keep artifact presence, successful execution, and accepted behavior separate. A clean exit or a producer summary is never a substitute for the required artifact or outcome.
6. Return an evidence map with condition, claimed proof, provenance chain, independence finding, and next verification action.

## Completion check

Every condition has an independent evidence path or an explicit gap. Shared evidence origins and conflicts are visible. The map distinguishes proposed verification from verification actually performed.

## Stop

If the evidence provenance cannot be established, mark the claim unverified. Do not label agreement among dependent reports as independent confirmation.

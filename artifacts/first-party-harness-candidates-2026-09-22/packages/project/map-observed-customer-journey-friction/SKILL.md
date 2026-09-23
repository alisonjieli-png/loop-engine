---
name: map-observed-customer-journey-friction
description: Turn consented session observations into a customer journey map that separates observed obstacles from possible causes and fixes.
---

# Map observed customer journey friction

## Use case

Use after observing real attempts to complete one customer task, such as connecting a tool or finding an item. The output helps a product team decide what to investigate or test. It does not claim to represent unobserved users.

## Required inputs

- One named task and its intended completion event.
- Consented session notes or recordings with session identifiers, timestamps, and the path each participant took.
- The interface version and any task instructions participants received.
- The allowed scope for handling personal information.

## Steps

1. Define the journey stages from the task, not from the site's navigation menu. Record the start and the observable completion event.
2. For each session, place actions, hesitations, reversals, errors, and completion in order. Attach a time and source reference to each entry. Use anonymized identifiers in the shared map.
3. Group repeated obstacles by the specific point and user intent. Count affected sessions over the sessions actually observed; do not treat missing telemetry as success.
4. For every obstacle, distinguish the observed behavior, the participant's stated reason if available, and the team's inferred explanation. Record competing explanations when evidence cannot decide.
5. Propose the smallest diagnostic change or follow-up observation that could distinguish the explanations. Mark proposed interface changes as hypotheses.
6. Return the journey map, denominator, obstacle table, evidence references, unknowns, and next test. Keep successes and smooth paths in the map too.

## Completion check

Another reviewer can trace every obstacle to at least one session and locate the stage and interface version. The map reports the number of observed sessions and the number that completed, without generalizing to a population that was not sampled.

## Stop or hold

Hold a causal claim when only behavior is observed. Hold a frequency claim without a known denominator. Do not create fictional participants, expose personal data, edit the interface, or contact a participant.

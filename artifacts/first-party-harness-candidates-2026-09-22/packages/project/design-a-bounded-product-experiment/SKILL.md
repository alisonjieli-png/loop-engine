---
name: design-a-bounded-product-experiment
description: Specify a product experiment with assignment, primary outcome, guardrails, exposure, and stop rules before any users are enrolled.
---

# Design a bounded product experiment

## Use case

Use when a team proposes a product change and wants a test that can answer one decision. This skill writes an experiment specification for review. It does not launch the experiment or enroll users.

## Required inputs

- The proposed change, target user task, current experience, and decision the result will inform.
- The available population and any consent, privacy, safety, or rollout constraints.
- Existing measurement definitions, baseline data, and event coverage, if available.

## Steps

1. State the hypothesis as a change in an observable outcome for a named eligible population. Name the alternative explanation the test must rule out.
2. Define the unit of assignment and exposure. Explain how the same person or team avoids crossing groups, and when an enrolled unit counts as exposed.
3. Choose one primary outcome, its direction, observation window, and decision threshold before viewing treatment results. Give exact event definitions and denominator.
4. Add guardrails for relevant harm: task failures, support burden, accessibility, privacy, spending, or latency. Give a pause trigger for each guardrail that can be measured.
5. State how baseline and treatment receive comparable measurement. Identify missing instrumentation and what a dry run must verify before enrollment.
6. Define the analysis, minimum analyzable sample or precision target, and stop rule, including handling of noncompliance, missing events, multiple looks, and excluded units. State when a result must remain inconclusive. Return the specification with open approvals and launch prerequisites.

## Completion check

An independent reviewer can decide from the written specification whether a measured result would pass, fail, or remain inconclusive. Assignment, exposure, denominator, and pause triggers are defined before results exist.

## Stop or hold

Hold launch if consent, assignment, event integrity, guardrail measurement, the sample or precision rule, or required approval is missing. Do not expose users, change feature flags, send messages, or describe the proposed experiment as completed evidence.

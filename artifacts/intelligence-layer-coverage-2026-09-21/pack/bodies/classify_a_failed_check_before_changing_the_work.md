# Classify a failed check before changing the work

Kind: recorded decision from Runtime History and Solution Intelligence.

## When to use this record

Use it the moment a check fails and you are about to edit the code the check
points at. The first question is not how to make the check pass. The first
question is which of three things is wrong: the work, the check, or the
environment the check ran in.

## What was recorded

A container startup probe for the hosted service reached its timeout and the
run was recorded as a failed check. The saved record classifies the cause as
`check_defect`, not a defect in the service. The probe looked for the health
fields at the top level of the response. The service wraps the health payload
inside a versioned result field, so the fields the probe wanted were one level
down and the probe never saw them.

The same record notes what had already passed before the failure: the
installed service smoke checks passed 48 of 48. That fact is what made the
`check_defect` classification credible rather than convenient.

## The repair

The probe was corrected to read the health value and the readiness value from
inside the result field. The refusal check for unauthenticated access was kept
exactly as it was, so the correction did not remove a control. The same
correction was applied to the post-deployment health step in the workflow, so
the two places that ask the same question agree.

## The known-wrong case

The wrong repair is to make the service return the health fields at the top
level as well. That would satisfy the probe, break the versioned result
envelope that every other reader depends on, and hide the real fault. A
corrected check must still reject a service that is genuinely unhealthy.

## What to record

Record the classification, the evidence that supports it, what passed before
the failure, the correction, and the control you deliberately kept.

## Source

`artifacts/architecture-audit-2026-09-19/fly-service-container-attempt-1.json`,
record type `fly_service_container_failure_note/v1`, and the later passing
record `fly-service-container-attempt-3.json`.

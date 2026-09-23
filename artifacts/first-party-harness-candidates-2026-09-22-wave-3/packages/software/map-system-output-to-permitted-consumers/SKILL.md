---
name: map-system-output-to-permitted-consumers
description: Map each output field to its authorized consumers, purpose, retention, and disclosure boundary. Use before proposing a new feed, report, or event stream.
---

# Map system output to permitted consumers

## When to use

Use before a system exposes a new report, event, or data feed. This is a read-only distribution design review; it does not grant access, send data, or set retention policy.

## Inputs

- The exact output fields, meanings, source and sensitivity classifications, and intended release version.
- Consumer identities and purposes, supplied access rules, allowed transformations, retention periods, and deletion obligations.
- Existing grants and delivery routes, if a change to a current feed is proposed.

## Procedure

1. List each output field separately. Do not infer that a whole report has one sensitivity or one permitted purpose.
2. For each proposed consumer and purpose, cite the rule that permits the field, the required minimization or transformation, and the allowed retention. Technical reachability is not authorization.
3. Identify fields that could reveal another field through a join, identifier, small group, or repeated release. Mark an unreviewed inference risk as unresolved rather than declaring de-identification.
4. Compare the proposed route with existing grants. Distinguish an already approved use from a new recipient, purpose, location, or retention period that needs a separate decision.
5. Return a field-by-consumer matrix with `permitted`, `prohibited`, or `unknown`, the evidence for each state, and a minimal proposed output for each permitted purpose.

## Completion check

Every proposed delivered field has a named consumer, purpose, rule, transformation if required, and retention bound. Unknown or prohibited cells are absent from the proposed delivery; an existing broad grant does not silently cover a new purpose.

## Stop

Hold distribution if a consumer identity, purpose, classification, governing rule, or retention decision is unknown. Do not create a grant, export records, or treat a draft matrix as legal or security approval.

---
name: reconcile-native-material-use-evidence
description: Reconcile offered, fetched, placed, discovered, loaded, used, and independently verified harness material from separate records.
---

# Reconcile native material use evidence

## Use case

Use when a run report says a skill or instruction helped a task and the actual native client path must be checked. Produce a state-by-state evidence record for the selected item.

## Required inputs

- Item identity, exact approved digest, selected run and client version.
- Available host offer and fetch records, placement manifest, native discovery or load observations, run trace, and independent task acceptance record.
- The event definitions used by that client to distinguish discovery, load, and use.

## Procedure

1. Identify the same item and digest across every record. Do not join events by a friendly title when revisions or rendered variants differ.
2. Mark `offered`, `fetched`, `placed`, `discovered`, `loaded`, `used`, and `verified` separately as observed, missing, disputed, or inapplicable. Name the producer and time of each observation.
3. Check ordering and scope: a later task cannot inherit proof from an earlier process, and a selected file on disk is not a model load event.
4. Examine traces for direct evidence that the client consumed the material. A discovery listing, a token count, or a producer's summary alone does not prove use. If client instrumentation cannot observe use, keep it unknown.
5. Compare the independent acceptance rule and artifact with the claimed result. A successful model call or passing local format check is not task verification.
6. Return a compact evidence chain, missing links, conflicts, and the narrowest statement the records support.

## Completion check

Every affirmative state names its own evidence and exact run identity. An item that was placed and discovered but never demonstrably loaded cannot be reported as loaded, used, or beneficial.

## Stop or hold

Hold a use or benefit claim when instrumentation, digest identity, or independent acceptance is missing. Do not rerun the task, fetch an item, or infer use from a plausible answer.

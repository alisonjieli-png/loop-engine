---
name: design-catalogue-withdrawal-checks
description: Specify negative checks for withdrawing a harness item across search, grants, body reads, cached manifests, and older release images.
---

# Design catalogue withdrawal checks

## Use case

Use before a catalogue release changes an item's active state. Produce a read-only check matrix for the release owner; do not withdraw or delete the item.

## Required inputs

- Item identity and version, exact approved body digest, current release manifest and grants, and the proposed withdrawal record.
- Search/index refresh behavior, body-read authorization path, cache rules, and eligible rollback images or record versions.
- The release's account classes and stated retention or audit policy.

## Procedure

1. Separate withdrawing an item from search, refusing its body read, removing new grants, handling existing grants, and retaining historical evidence. Name which record controls each state.
2. Specify a before-and-after check for an authorized account and an account without a grant. The after state must not offer or materialize the withdrawn body even when a stale reference is supplied.
3. Add a race case: withdrawal occurs after ranking but before body retrieval. Require authorization and active-state checks at the final read.
4. Add stale-cache and rollback cases. Name the oldest eligible host image and whether it understands the new withdrawal record; an old image that ignores it must be ineligible for rollback.
5. Preserve the withdrawn exact bytes and reason as historical evidence under the supplied retention rule, without making them active search material.
6. Return a matrix of check, setup, expected refusal or visibility, record version, and evidence the release owner must capture.

## Completion check

The check design would catch a withdrawn item returned by search, fetched through an old grant, served after a race, or restored by an older host. Historical retention is not confused with public availability.

## Stop or hold

Hold a safe-withdrawal claim if any grant, cache, final-read, or rollback behavior is unknown. Do not mutate a manifest, revoke access, delete bytes, deploy, or run the checks without separate authority.

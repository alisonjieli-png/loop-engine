---
name: audit-a-published-guide-against-a-release
description: Audit a multi-section guide and its examples against one shipped product revision. Use when documentation may describe development behavior instead of the released interface.
---

# Audit a published guide against a release

## When to use

Use before publishing or updating a guide tied to a product release. This is a claim-by-claim review of supplied documentation and release evidence; it does not edit or publish the guide.

## Inputs

- The guide, its audience and language version, and the exact product or interface revision it claims to describe.
- Released configuration defaults, command or interface contracts, feature flags, and tested examples for that revision.
- The distinction between publicly shipped, private preview, planned, and unsupported behavior.

## Procedure

1. Break the guide into checkable claims: setup prerequisites, defaults, commands, paths, output shapes, limits, permissions, and troubleshooting outcomes.
2. For each claim, name the exact released artifact, contract, or observed test that supports it. A development checkout or unreleased branch is not evidence for a shipped default.
3. Walk each worked example in dependency order against the release. Identify a missing prerequisite, changed command, unavailable feature, or result that cannot occur under stated permissions.
4. Mark each section `supported`, `stale`, `future`, or `unknown`, and propose the smallest correction with its evidence. Keep historical versions labeled rather than rewriting them as current.
5. Return a section-level drift report with claim location, release evidence, reader consequence, and proposed edit for human review.

## Completion check

Every actionable example and stated default is tied to the named release or visibly marked unverified. The report identifies any statement that would send a reader down a path the released product cannot complete.

## Stop

Hold a current-behavior claim if the release revision or a required artifact cannot be identified. Do not run production commands, change documentation, or treat a successful development example as public release proof.

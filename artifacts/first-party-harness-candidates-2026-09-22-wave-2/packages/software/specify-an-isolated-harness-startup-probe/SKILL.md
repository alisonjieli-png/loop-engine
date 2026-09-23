---
name: specify-an-isolated-harness-startup-probe
description: Design a source-discovery probe for a fresh harness that can detect selected material and unexpected inherited instructions before a task run.
---

# Specify an isolated harness startup probe

## Use case

Use when a new harness process is expected to see only selected step material, while its client may also read ancestor, user, bundled, or compatibility locations. Produce a probe specification, not a launched process.

## Required inputs

- Client identity and version with documented or observed discovery locations.
- The selected item manifest, proposed work, home, and configuration roots, and the startup observation interface.
- A declared policy for built-in material and for any unavoidable client source.

## Procedure

1. Enumerate every plausible instruction, skill, configuration, and extension source for the exact client version, including ancestors and isolated versus real home. Mark unverified discovery rules as unknown.
2. Name one harmless selected canary and one harmless unselected canary that a future authorized fixture can place at distinct sources. Use synthetic text, never a credential or customer material.
3. Specify the expected observed source set before startup. A selected skill listed in discovery is evidence of discovery only; plan separate evidence for loading and use.
4. Identify where a parent process, inherited environment, shared cache, symlink, or client built-in could carry prior task material into this step. Give each a negative observation that would reveal it.
5. Define a refusal when the probe sees an extra source, misses a required source, cannot inspect a source, or resolves a path outside the scope.
6. Return a probe matrix with source, canary, expected observation, unexpected observation, and the later authorization needed to run it.

## Completion check

The planned probe can distinguish an exact selected source set from one with an added ancestor or user skill. It does not mark a clean directory alone as proof of a clean harness.

## Stop or hold

Hold an isolation claim when discovery behavior or observation coverage is unknown. Do not launch a client, write canaries, change a home directory, or run a model under this read-only skill.

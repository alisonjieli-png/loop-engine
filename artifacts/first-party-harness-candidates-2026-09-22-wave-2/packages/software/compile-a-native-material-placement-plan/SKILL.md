---
name: compile-a-native-material-placement-plan
description: Plan exact native destinations for selected harness material under a stated client layout, refusing collisions and unsupported file kinds before installation.
---

# Compile a native material placement plan

## Use case

Use when a fresh harness step has selected intelligence packages but their native locations differ by client and version. Produce a read-only placement plan for a qualified installer.

## Required inputs

- Selected approved item identities, package files, relative resource paths, and exact digests.
- The target client and version, a source-backed layout profile, workspace and isolated configuration roots, and the step's material scope.
- Any native name, path-length, trust, or activation restrictions in that profile.

## Procedure

1. Classify each selected item as instruction, skill, task reference, protocol declaration, or executable extension. A reference is task data unless an approved contract explicitly makes it an instruction.
2. Derive each proposed destination from the exact client layout profile, never from a guessed portable folder name. Keep skill resources under their package relative paths.
3. Check for duplicate native names, case-folding collisions, reserved names, unsupported kinds, absolute or parent paths, and resource links that could escape the scoped root. Mark a conflict rather than choosing the last writer.
4. Bind every planned output path to the source item identity and digest. Record any deterministic rendering and its expected output digest separately; a rendered byte change needs its own qualification.
5. Keep task materials and outputs outside instruction and extension locations. Identify the isolated home and configuration sources that the later launch must inspect for inherited material.
6. Return the path map, refused or unresolved entries, exact client profile, and discovery observations a later authorized installer must collect.

## Completion check

Every planned path has one eligible source item and one exact byte expectation. No selected package is silently dropped, no unselected item is added, and no two files claim the same native destination.

## Stop or hold

Hold placement when the client version, layout profile, item approval, digest, resource path, or collision rule is unknown. Do not create files, install a plugin, activate a protocol server, or treat placement as proof of native loading.

---
name: separate-shared-build-cache-from-task-state
description: Classify files and cache keys before parallel agents share build storage. Use when separate worktrees or sandboxes reuse dependencies but must not share task outputs or credentials.
---

# Separate shared build cache from task state

## Use

Use when a plan proposes one cache for several isolated workers. This is a design review of supplied paths and cache rules, not a command to mount, copy, delete, or share anything.

## Inputs

- The proposed worktree or sandbox boundaries and worker identities.
- The paths, volumes, and cache keys each worker can read or write.
- The build inputs, toolchain versions, task-specific outputs, and any secret references.

## Procedure

1. Classify every shared path as immutable dependency input, rebuildable cache, task artifact, mutable source, or secret-bearing state. Mark unknown paths as unqualified for sharing.
2. For each cache, identify the exact inputs that determine its contents: source revision, lockfile, toolchain, platform, build flags, and environment-sensitive values.
3. Check who may create the first cache entry, who may overwrite it, and how a receiving worker verifies producer trust and entry integrity. A key and an immutable flag cannot make an untrusted first write safe. Separate cache identity from task output identity; a successful cache hit must not act as proof that a task's output is correct.
4. Check whether absolute paths, user-specific data, or credentials can enter a cache entry or its metadata. Require a separate private location for those values.
5. Describe one stale-key case, one concurrent-writer case, and one cross-worker disclosure case, with the observable signal that should reject each.
6. Return a path classification and a sharing proposal: safe read-only reuse, qualified keyed reuse, private per-worker state, or unresolved.

## Completion check

Every proposed shared path has a class, an ownership rule, and a trusted-producer or integrity rule. Mutable and secret-bearing state is not proposed for shared reuse. Each cache hit still requires the receiving task's own acceptance check.

## Stop

If a path's contents or key dependencies are unknown, do not label it safe to share. Request an inventory before a mount or cache policy is approved.

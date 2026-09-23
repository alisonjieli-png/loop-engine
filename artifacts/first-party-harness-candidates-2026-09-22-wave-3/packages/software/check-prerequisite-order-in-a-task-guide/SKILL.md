---
name: check-prerequisite-order-in-a-task-guide
description: Check that an ordered task guide supplies every prerequisite before its first use and has a defined stop or recovery path. Use before a reader follows procedural documentation.
---

# Check prerequisite order in a task guide

## When to use

Use for an ordered procedure that a reader will follow from a stated starting condition. Every individual step can be correct while the guide is impossible to follow in its written order.

## Inputs

- The draft steps, intended reader, starting state, required permissions, files, tools, and expected result.
- The dependency and failure condition for each step, including decisions that branch or require approval.
- The exact environment or product version if a prerequisite depends on it.

## Procedure

1. For each step, list what must already exist: input, identity, permission, configuration, prior output, and decision. Mark the step that first establishes each requirement.
2. Compare first use with first establishment. Draw a dependency edge from the establishing step to the consuming step; flag any edge that points backward in the written order.
3. Walk the guide from the stated starting state. At each step, record the state change or artifact it promises and whether the next step can actually use it.
4. Check the first failure at each branch: what the reader can inspect, whether retry is safe, and when a missing permission or external effect requires a separate decision.
5. Return an ordered prerequisite table and proposed reorder or missing step. Do not fix one branch by silently assuming a more privileged starting state.

## Completion check

Every input and authority requirement exists before its first use or is explicitly requested at that point. The success path reaches the stated result, and each important failure has a stop or recovery instruction supported by the guide's authority.

## Stop

Hold a usable-guide verdict when the reader's starting state, permission, version, or prerequisite source is unknown. Do not execute the guide or create access on the reader's behalf.

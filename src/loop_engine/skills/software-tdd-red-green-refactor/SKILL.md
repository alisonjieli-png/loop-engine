---
name: software-tdd-red-green-refactor
title: Software TDD red green refactor
description: Implement one bounded software requirement by proving failure, making the minimum change, refactoring while green, and rerunning required verification.
version: 1.0.0
tags:
  - software
  - testing
  - evidence-first
---

# Software TDD red green refactor

Use only for software task slices with an exact requirement verification
contract, confined workspace, permitted write scope, and registered test
capability.

1. Preserve the original requirement and current baseline.
2. Run or add the smallest test that proves the requirement is not satisfied.
3. Record the exact failing signature.
4. Make the minimum implementation change within the assignment write scope.
5. Run the focused test and require it to pass.
6. Refactor only while the focused test remains green.
7. Run the required interaction and full verification suites.
8. Return changed artifacts, test outputs, limitations, and exact evidence.

Do not commit, push, publish, broaden permissions, change unrelated files, or
mark completion from test text alone. The requested artifact must exist and
independent verification must pass when the task contract requires it.


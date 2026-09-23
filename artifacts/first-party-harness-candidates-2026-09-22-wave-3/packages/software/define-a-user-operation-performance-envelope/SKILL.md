---
name: define-a-user-operation-performance-envelope
description: Define a testable latency, throughput, reliability, and resource envelope for one user operation. Use before claiming an application is fast enough in production.
---

# Define a user operation performance envelope

## When to use

Use before accepting one user-visible operation under an expected workload. The output is a measurement contract, not a performance result or permission to run a load test.

## Inputs

- The operation's start and end events, user-visible deadline, important request classes, and expected workload mix.
- The deployment class, concurrency range, resource ceilings, data volume, and allowed failure or degradation behavior.
- A baseline distribution or an explicit statement that no baseline exists, plus the independent acceptance rule.

## Procedure

1. Define the exact user operation and its measurement boundaries. Separate client wait, queueing, server work, and background completion if they affect the promised experience.
2. Partition the workload into classes that must not be hidden in one average, including large inputs, cold starts, and permitted fallback paths.
3. For each class, state the measured quantity, target, percentile or tail rule, sample requirement, error allowance, and resource ceiling supplied by the owner. Keep an unspecified threshold unknown.
4. Specify workload generation, warm-up and observation windows, environment version, clock basis, and how aborted or timed-out requests count.
5. Give one boundary case that must fail the envelope even if the aggregate mean passes. Return the exact data and artifacts a later authorized test must collect.

## Completion check

The envelope names every measured class and its acceptance rule. A future evaluator can reject a slow important class, excess resource use, or missing responses without changing the rule after seeing the result.

## Stop

Hold a pass/fail claim if the user deadline, workload, sample rule, environment, or failure accounting is missing. Do not run a load test, increase traffic, or invent a service objective.

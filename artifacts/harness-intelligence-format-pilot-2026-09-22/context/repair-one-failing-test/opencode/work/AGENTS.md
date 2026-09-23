# Repair one failing test

This file is a step template. If any required input remains unfilled, stop and report
`unrendered_step_input`. These instructions do not grant file, shell, network,
model, or spending authority.

## Assignment

Investigate the failure recorded in `{{FAILURE_EVIDENCE_PATH}}` for the test
`{{TEST_IDENTIFIER}}`. Work only within `{{CHANGE_SCOPE}}`. The expected
behavior and acceptance rule are `{{ACCEPTANCE_RULE}}`.

## Method

1. Read the failure evidence and the smallest relevant test and implementation.
   Identify whether the implementation, test, or environment is wrong. Record
   the reason before changing anything.
2. If the implementation is wrong, make the smallest change that addresses the
   cause. Preserve unrelated behavior. If the test or environment is wrong,
   explain the evidence; do not weaken an assertion merely to obtain a pass.
3. Run `{{APPROVED_TEST_COMMAND}}` only if the runtime separately authorizes
   that exact command. Record its exit status and relevant output. If it cannot
   run, report the reason and leave verification unclaimed.
4. Finish with the cause, changed paths, test result, remaining uncertainty,
   and whether the stated acceptance rule was met. Never describe an unrun
   check as passing.

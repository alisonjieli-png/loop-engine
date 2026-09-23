# Apply, hold or escalate each correction by its confidence

Give every proposed correction a confidence and named reasons. Let two thresholds decide whether it is applied, held for review or escalated. The source value is never lost.

## When to use it

Use it for any automatic data correction where some proposals are certain and others are guesses: names, suffixes, phones, emails, websites and similar fields.

## Steps

1. Make every operation return four things: the proposed output, a confidence from 0 to 1, the named reasons, and whether the value changed.
2. Set the confidence to the weakest named signal. Do not average signals.
3. Declare two thresholds. The defaults are apply at or above 0.9 and escalate below 0.6. The escalation threshold cannot exceed the apply threshold. A single rule may carry its own thresholds.
4. Classify each proposal:
   - changed and at or above the apply threshold: applied;
   - below the escalation threshold, changed or not: escalated;
   - changed and between the two thresholds: held;
   - not changed and at or above the escalation threshold: unchanged.
5. Write only applied corrections into the output row. A held or escalated value keeps its input, and the proposal stays in the correction record.
6. Run the rules a second time over the output. Zero new corrections proves that the pass is idempotent.
7. Report outcome counts for each rule and overall, a confidence histogram with ten bins, counts for each reason, and a digest of the rules and of the exception lists.
8. Call the run complete only when nothing is held, nothing is escalated and the pass is idempotent.

## Checks

- With a capitalisation rule, `ACME CORPORATION` is applied at 0.92. `AA CAREERS` (0.75) and `MACHINE TOOLS INC` (0.8) are held and keep their input.
- An invalid phone number is unchanged at 0.35, so it is escalated and reaches review.
- The outcome counts add up to the number of recorded corrections.

## Known-wrong example

A cleaner averages its signals. A whitespace repair at 0.99 and an ambiguous suffix at 0.5 average to 0.745, and with a loose threshold the rewrite is applied. With the weakest signal rule the confidence is 0.5, so the value is escalated. A second wrong design writes held proposals into the data and keeps only a log. The reviewer can then no longer see the original value.

## What to record

- Each correction: row reference, column, rule, operation, input, output, confidence, reasons and outcome.
- The thresholds, the report and its digests.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `correction`, `classify`, `apply_rules_to_row` and `summarize`.
- `src/loop_engine/code_nodes/text_conformance.py`: `ConformancePolicy`, `ConformanceReport`, `run_conformance` and `second_pass_changes`.

Licence: MIT. Compiled from revision 1700841. The operations module uses only the Python standard library.

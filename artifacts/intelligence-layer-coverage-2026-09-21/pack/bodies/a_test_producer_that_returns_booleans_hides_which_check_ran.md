# A test producer that returns booleans hides which check ran

Kind: recorded failure and its repair, from Runtime History and Solution
Intelligence.

## When to use this record

Use it when a test collector refuses the output of a suite that reports itself
as passing, and you are tempted to relax the collector.

## What was recorded

One self-test producer returned a mapping from check names to boolean values.
The aggregate that collects results requires an explicit, non-empty sequence
of identified test records. The mapping was refused.

The producer was changed to return all 35 existing checks as records, each
carrying its original boolean value and its counts. The collector was not
changed and was not relaxed.

## The repair and its control

After the change, the unchanged collector accepted all 35 passing records. Two
controls were run to prove the repair was a repair and not a way around the
rule:

1. An in-memory mutation restoring the old return shape made the collector
   raise the error it is supposed to raise. The guard still works.
2. A separate output extractor that is known to be wrong still failed four
   positive checks. A formatting correction did not turn wrong behaviour into
   passing evidence.

## The known-wrong case

The wrong repair is to teach the collector to accept a mapping of names to
booleans. It would pass, and the suite would permanently lose the ability to
say which check ran, on what input, and how many times. A collector that
accepts an unidentified result cannot tell a full run from an empty one.

## What to record

Record which side you changed and why, the control that shows the guard still
rejects the old shape, and a second control that shows genuinely wrong work
still fails.

## Source

`artifacts/architecture-audit-2026-09-19/runtime-regression-repairs.md`,
section "Test record producer".

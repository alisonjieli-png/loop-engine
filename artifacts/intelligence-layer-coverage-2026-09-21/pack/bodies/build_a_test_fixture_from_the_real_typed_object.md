# Build a test fixture from the real typed object

Kind: recorded failure and its repair, from Runtime History and Solution
Intelligence.

## When to use this record

Use it when a test fails with a missing attribute after someone added a
required field to a request type, and the production code is not at fault.

## What was recorded

A self-test supplied a hand-built stand-in object to a function that assembles
solve dependencies. A newly required field on the real request type was not
present on the stand-in. The test raised a missing attribute error. The
production path was correct. The fixture had drifted away from the type it was
imitating.

Both dependency assembly checks were changed to build one real request object
from typed intake, instead of a stand-in. The existing assertions about the
family surfaces and the learning event collector were kept unchanged.

## The repair and its control

All ten records passed through the unchanged collector after the change.
Restoring the old fixture reproduced the original missing attribute error, so
the fixture was the cause and the repair addressed it. No production fallback,
invented default value, or new public behaviour was added to make the test
pass.

## The known-wrong case

The wrong repair is to give the production code a default for the missing
field so the stand-in keeps working. The field was made required on purpose.
A default would make every caller that forgot it silently take a path nobody
chose. Another wrong repair is to add the one missing attribute to the
stand-in, which fixes today and leaves the same drift to be discovered again
at the next required field.

## What to record

Record the drifted fixture, the real type it was imitating, the field that
exposed the drift, and the fact that no production default was added.

## Source

`artifacts/architecture-audit-2026-09-19/runtime-regression-repairs.md`,
section "Public request fixture".

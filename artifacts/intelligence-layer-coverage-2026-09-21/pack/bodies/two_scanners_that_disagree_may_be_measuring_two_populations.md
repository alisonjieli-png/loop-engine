# Two scanners that disagree may be measuring two populations

Kind: recorded decision from Runtime History and Solution Intelligence.

## When to use this record

Use it when two checks that appear to ask the same question return different
answers, and someone proposes a waiver for the one that fails.

## What was recorded

A public report returned zero findings for retired wording while a package
scanner returned eighteen for what looked like the same rule. The first
explanation offered was test pollution: that an earlier check in the same
process had left state behind.

That explanation was tested and rejected. A fresh interpreter, importing a
frozen copy of the source, reproduced all nineteen findings before running any
other test. Running the 28 checks that normally come first left both the count
and the cached policy value unchanged.

The real reason was that the two tools measure different populations. The
public report selects a configured subset of terms and applies them to an
explicit public file scope. The package scanner checks every configured term
against the whole package source. Zero was the correct answer for the first
question. Eighteen was the correct answer for the second. Neither result
justified a waiver.

The working tree showed eighteen rather than nineteen because one occurrence
had already been corrected by hand. The wording was then cleaned up at its
owner, and current consumers were updated in the same change with no
forwarding alias left behind.

## The known-wrong case

The wrong move is to waive the failing scanner because a neighbouring report
is green. Before that, compare the two scopes and the two term lists. If they
differ, the disagreement is information, not noise.

## What to record

Record both populations, both term lists, the pollution test and its result,
and the reason no waiver was taken.

## Source

`artifacts/architecture-audit-2026-09-19/runtime-regression-repairs.md`,
section "The conformance discrepancy was not test pollution".

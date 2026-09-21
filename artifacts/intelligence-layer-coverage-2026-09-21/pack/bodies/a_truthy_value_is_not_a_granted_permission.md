# A truthy value is not a granted permission

Kind: recorded repair from Runtime History and Solution Intelligence.

## When to use this record

Use it when a permission, a capability, or a feature switch is read from
configuration, from a record, or from a request, and the code tests the value
for truth rather than comparing it to a value.

## What was recorded

Operation capabilities across three catalogue store adapters were changed to
require the boolean value true. A truthy string or a non-zero number now
grants nothing.

The same repair brought the in-memory adapter and the DuckDB adapter up to the
absence and version guards that the SQLite adapter already had, so the three
adapters answer the same question the same way. In-memory checks and writes
are protected by a reentrant lock. DuckDB checks and writes share a
transaction. Guarded writes across all three adapters reject a record version
that did not change.

## Why a truth test is the wrong test here

Almost every value that reaches a permission field from a file, a form, or a
wire format is a string. The string "false" is true when tested for truth. So
is "no", "0" as text, "disabled", and an error message that arrived where a
flag was expected. A truth test converts every one of those into a granted
permission, and the grant is silent.

## The known-wrong case

The wrong repair is to add a list of strings that count as false. The list is
never complete, and the next unexpected value still grants the permission.
Compare to the value you mean and refuse everything else.

## What to record

Record the exact accepted value, the refusal for every other value, and the
adapters you checked for the same defect. A guard fixed in one adapter and
missing in a second is not fixed.

## Source

`artifacts/architecture-audit-2026-09-19/storage-write-repairs.md`,
paragraph beginning "The in-memory and DuckDB adapters now understand the same
exact absence and version guards as SQLite".

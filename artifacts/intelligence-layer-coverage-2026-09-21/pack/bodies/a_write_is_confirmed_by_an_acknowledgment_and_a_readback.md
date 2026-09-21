# A write is confirmed by an acknowledgment and a readback

Kind: recorded repair from Runtime History and Solution Intelligence.

## When to use this record

Use it when a step reports that it saved something, and you want to know what
that report is actually based on.

## What was recorded

Shared-memory and catalogue writes were changed so that a successful write
requires two things together: a valid acknowledgment from the store, and a
readback that matches what was sent. Either one alone is not enough.

Three outcomes are now kept apart:

1. Written. The store acknowledged and the readback matched.
2. Refused. A named rule rejected the write, for example a version that did
   not advance, a scope identity that did not match, or a namespace that did
   not match.
3. Unknown. A backend failure or an intervening change prevented
   confirmation.

An unknown outcome is reported as unknown. It is not reported as a successful
write, and it is not turned into an invented stale-version result.

## The known-wrong case

The wrong behaviour is to treat "no exception was raised" as "written". A
store that accepts a write and drops it raises nothing. So does a store that
accepts a write, applies it, and is then overwritten by another writer between
the write and the next read. The first case needs the readback to catch it.
The second case needs the version rule to catch it.

The second wrong behaviour is to resolve an unknown outcome by guessing. A
step that reports a stale version it never observed has invented a fact, and
every later decision built on it inherits the invention.

## What to record

Record the acknowledgment, the readback comparison, the version that was
required, and which of the three outcomes occurred. An unknown commit is not
a success.

## Source

`artifacts/architecture-audit-2026-09-19/storage-write-repairs.md`.

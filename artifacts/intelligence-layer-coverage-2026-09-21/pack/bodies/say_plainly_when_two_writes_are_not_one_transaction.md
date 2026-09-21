# Say plainly when two writes are not one transaction

Kind: recorded decision from Runtime History and Solution Intelligence.

## When to use this record

Use it when a change writes a history copy and then updates a current record,
and you are about to describe the pair as atomic in a comment, a document, or
a name.

## What was recorded

Saving a new revision writes the immutable predecessor first, then writes the
guarded current record. The recorded decision states that these two writes are
deliberately not described as one transaction, and it states the exact
consequence: if the current update fails, an identical copy of the
still-current version may remain behind.

That consequence is handled rather than hidden. The history view does not
report the leftover copy as a second version. A later valid revision can
confirm an already-superseded committed version through its exact preserved
predecessor.

## Why write it down

The risk of the quiet version is not the leftover row. It is the next reader,
who sees two writes next to each other, assumes they succeed or fail together,
and builds a recovery path on that assumption. Writing the limit next to the
code is what stops the assumption forming.

## The known-wrong case

The wrong move is to name the pair atomically, for example calling the helper
a transactional save, when the store gives no such guarantee across the two
writes. A name is read far more often than the implementation under it, and a
name that promises more than the store delivers is a defect that costs nothing
to introduce and is expensive to find.

## What to record

Record which writes share a guarantee and which do not, the exact state that
can remain after a partial failure, and what reads that state afterwards.

## Source

`artifacts/architecture-audit-2026-09-19/storage-write-repairs.md`,
paragraph beginning "The immutable predecessor is written before the guarded
current record".

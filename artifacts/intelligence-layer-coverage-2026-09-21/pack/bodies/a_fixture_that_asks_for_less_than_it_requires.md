# A fixture that asks for less than it requires

Kind: recorded decision from Runtime History and Solution Intelligence.

## When to use this record

Use it when a test starts failing after a limit was corrected, and the test
was passing for a reason nobody checked.

## What was recorded

One test asked a search for three results and then required that all four
persistent intelligence layers appear in the answer. It passed only because
the requested count was being applied per layer rather than to the combined
answer, which multiplied the limit. When the limit was corrected to mean what
it says, the test failed.

The test was corrected to request four results, because four is the smallest
number that can carry four layers. The correctness requirement was not
weakened. A separate check that requests one result was added, and that new
check still rejects the old multiplied-limit behaviour.

## The known-wrong case

The wrong repair is to restore the per-layer meaning of the limit so the old
test passes again. A caller who asks for three results and receives twelve has
paid for twelve. The second wrong repair is to correct the fixture and stop
there, leaving nothing in the suite that would catch the multiplied limit if
it came back. That is why the one-result check exists.

## What to record

Record why the old test passed, the corrected expectation, and the new check
that rejects the behaviour the old test was accidentally tolerating. A
corrected test that no longer rejects the known-wrong case is not a corrected
test.

## Source

`artifacts/architecture-audit-2026-09-19/intelligence-access-repairs.md`,
section "Retrieval behavior".

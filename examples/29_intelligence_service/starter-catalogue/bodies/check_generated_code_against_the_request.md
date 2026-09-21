# Check generated code against the request

Test generated code with something the generator did not write, because code and its tests from one source agree with each other by construction.

## When to use it

Use it whenever code and its tests come from the same generator in the same attempt, and whenever a generated result is about to be used by somebody else.

## Steps

1. Take the expected results from the request, an existing implementation or a reference data set. Do not take them from the generator's own tests.
2. Run the generated code against inputs you chose, and compare with those expected results.
3. Where no expected result exists, compare two independent implementations on the same inputs and investigate every difference.
4. Use relationships that must hold whatever the answer is: sorting twice gives the same list, reversing twice gives the original, a total equals the sum of its parts.
5. Check the shape and meaning of the output, not only that it parses. An empty list of the right type is not a result.
6. Read the code for the things tests rarely catch: a hard coded value that matches the example, a branch that only handles the sample, an exception swallowed.
7. Run it on an input larger and stranger than the example, and see whether it still behaves.
8. Record which expectations came from outside the generator, because those are the ones that carry weight.

## Checks

- At least one expected result came from outside the generated work.
- The output is checked for meaning, not only for format.
- A value or path specific to the example is not present in the code.
- The code was run on an input it was not shown.

## Known-wrong example

A model writes a date parsing function and a test suite for it. Every test passes. The function returns the current date whenever parsing fails, and the tests only use valid dates from the same model. A single case taken from the request, with a malformed date and the required behaviour, would have failed at once.

## What to record

- The expectations used and where each came from.
- The differences found between two implementations.
- The inputs tried beyond the examples.

## Source

- `src/loop_engine/core/differential_verification.py`: this repository verifies a generated artifact without trusting values the same model wrote, by comparing independent implementations, checking relationships that must hold and recording each divergence.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision eb757bc.

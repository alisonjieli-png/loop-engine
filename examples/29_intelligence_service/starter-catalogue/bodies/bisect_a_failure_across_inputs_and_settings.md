# Find the setting or input that causes a failure by halving

Apply the same halving search to settings, feature switches, data columns and dependency versions, not only to revisions.

## When to use it

Use it when the code has not changed but the behaviour differs between two environments, two customers, two data sets or two machines.

## Steps

1. Write down the working case and the failing case as two complete lists of settings, versions and inputs.
2. Compute the difference between the lists. If it is empty, you have not captured everything that matters.
3. Change half of the differing values from the working case to the failing case. Run the test.
4. Keep the half that reproduces the failure and repeat until one value remains.
5. Confirm by changing only that value on the working case, and only that value back on the failing case.
6. If two values cause the failure only together, split them apart and test each pair.
7. Explain how the value causes the failure before you change any code.

## Checks

- Both cases were captured completely, including versions, locale, time zone and environment variables.
- The single value reproduces the failure on the working case.
- Reversing the single value repairs the failing case.
- A pair was tested when no single value explained the result.

## Known-wrong example

A service works for one customer and fails for another with the same data. The team spends a week reading the parsing code. The difference was the server time zone, which changed how dates near midnight were grouped. It was never written down because nobody thought of the environment as an input. A complete list of both environments would have shown one differing value on the first day.

## What to record

- The two complete environment and input lists.
- The values tried at each round and the result.
- The single value or the pair that explains the failure.

## Source

- `src/loop_engine/core/route_health.py`: this repository keeps observations about one provider route as facts of the current run only, and never turns them into settings, so a new run starts from the declared values again.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 379c271.

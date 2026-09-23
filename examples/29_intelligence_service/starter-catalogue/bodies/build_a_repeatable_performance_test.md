# Build a performance test that gives the same answer twice

Make a measurement you can trust by fixing the data, the machine and the method, and by reporting how much the result moves on its own.

## When to use it

Use it when you want to compare two versions, watch for a slow decline over time, or prove that a change actually helped.

## Steps

1. Freeze the input: a fixed data set of a stated size, with a stated shape, stored where the test can find it.
2. Fix the environment: the same machine class, the same settings, the same versions, nothing else running.
3. Warm up first, then measure. The first runs include work that will not repeat, such as loading and compiling.
4. Run the measurement several times and report the spread, not only the middle value.
5. Measure the same version twice before comparing two versions. The difference between two runs of the same code is the noise floor.
6. Call a difference real only when it is larger than that noise floor.
7. Record everything alongside the number: revision, data set, machine, settings, date and the raw values.
8. Run it on a schedule as well as on demand, so a slow decline is visible before it becomes a complaint.

## Checks

- Two runs of the same version differ by less than the change you want to detect.
- The input size and shape are fixed and stored.
- The report carries the spread and the raw values, not only an average.
- The environment is recorded with the result.

## Known-wrong example

An engineer measures before and after on a laptop, gets nine percent faster, and merges the change. The laptop was charging during the second run, which lifted the processor speed. The service gets slower in production. Running the unchanged version twice first would have shown a twelve percent difference from nothing at all.

## What to record

- The frozen input, the environment and the method.
- The raw values, the spread and the noise floor.
- The revision each measurement belongs to.

## Source

- `src/loop_engine/core/ngram_benchmark.py`: this repository runs a frozen benchmark against judgments kept in source control, records retrieval quality, timing and size together, and keeps model calls and network access out of the measurement.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.

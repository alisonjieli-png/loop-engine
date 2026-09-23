# Use percentiles, not averages, for response time

Describe how slow the slow requests are, because the average hides exactly the users who are suffering.

## When to use it

Use it for every response time number you publish, promise or alarm on: a service level target, a dashboard, a performance comparison, or a claim that one version is faster than another.

## Steps

1. Record the duration of each individual request, not a running average.
2. Give the middle value, the ninety fifth and the ninety ninth, and the largest seen.
3. Say over which window and how many requests the numbers were computed. A high percentile over a hundred requests is mostly noise.
4. Measure where the user is, or at the outermost entry, so queueing and connection time are included.
5. Split by the things that change the answer: endpoint, customer size, region, cold or warm start.
6. Never average percentiles from different periods or different machines together. That number means nothing.
7. Set alarms on a percentile and a duration, both stated, rather than on an average.
8. Keep the raw durations long enough to compute a different percentile when a question changes.

## Checks

- Every published number names its percentile, its window and its sample count.
- The measurement point includes queueing, not only handler time.
- Percentiles come from raw durations and are never averaged together.
- The split shows at least the endpoint and the region.

## Known-wrong example

A dashboard shows an average response time of 120 milliseconds and everyone is satisfied. One customer with ten times the data waits eleven seconds on every page. Their requests are a fraction of a percent of the traffic, so the average never moves. The ninety ninth percentile would have shown the problem the day it appeared.

## What to record

- The percentile, window and sample count for each number.
- The measurement point and the splits used.
- The raw durations, kept so another percentile can be computed later.

## Source

- `src/loop_engine/core/ngram_benchmark.py`: this repository computes percentile values from the measured query times of a frozen benchmark and keeps them beside the quality numbers and the size of the index.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.

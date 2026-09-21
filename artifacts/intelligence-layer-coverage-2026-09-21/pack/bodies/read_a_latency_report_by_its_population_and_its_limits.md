# Read a latency report by its population and its limits

Kind: recorded measurement from Runtime History and Solution Intelligence.

## When to use this record

Use it when someone quotes a response time at you, and before you quote one
yourself.

## What was recorded

One saved report measures a hosted service from a development workstation. Its
own fields state the population exactly: seven request profiles, 12 samples
for each profile, a maximum of 84 requests, one request at a time, a fixed
pause between requests, and no automatic retries. The query text is recorded
by its digest and its character count, so the same query can be identified
again. Percentiles are taken by nearest rank over successful samples only.
Every individual sample is kept, not just the summary.

Open the report for the timings. This record deliberately does not copy them,
because a number copied out of its report loses the population it came from
and becomes a claim.

## What the report states it does not establish

Its own limits list says: these are network round trip and client processing
times, not isolated server execution time; new connections include name lookup
and transport security setup and are reported separately from reused
connections; the catalogue searched is a small diagnostic one, so this is not
a capacity, availability, geographic, or competitor benchmark; and no bodies
were downloaded, no model was called, and nothing external was changed.

## The known-wrong case

The wrong use is to take the fastest recorded value, present it as the typical
response time, and leave out that connections were reused and that the
catalogue was small. Reporting first-connection and reused-connection timings
separately exists precisely so that the two cannot be blended into one
flattering number.

## What to record

Record the vantage point, the sample count per profile, the concurrency, the
retry policy, the percentile method, whether connections were new or reused,
and the size of the data searched.

## Source

`artifacts/architecture-audit-2026-09-19/service-latency-1.json`, record type
`service_latency_report/v1`.

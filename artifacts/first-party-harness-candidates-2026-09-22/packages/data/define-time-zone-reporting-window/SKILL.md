---
name: define-time-zone-reporting-window
description: Translate a local reporting period into exact event-time boundaries. Use for daily or hourly metrics that cross time zones or daylight saving transitions.
---

# Define a time zone reporting window

## When to use

Use this when a report groups timestamped events by a business day or hour in a named location. A fixed offset is insufficient when the zone can change offset.

## Inputs

- A named time zone, local reporting start and end, and the rule for including each boundary.
- Event timestamp format, precision, any truncation rule, and whether each timestamp identifies an unambiguous instant.
- The time zone database or runtime version used for the calculation, when reproducibility requires it.

## Procedure

1. State the supplied inclusion rule for each boundary. Use a half-open interval only when the rule calls for it or an equivalent normalization is proved for the event timestamp representation. Flag overlap or gaps between adjacent windows.
2. Resolve the start and end independently in the named time zone, then convert both to absolute instants. Do not add a fixed number of hours to the first boundary to obtain the second.
3. Select events using those absolute boundaries and the supplied inclusion rules. Convert selected instants back to the named zone for display.
4. Check events immediately before, at, and after both boundaries at the available timestamp precision. If a local timestamp is ambiguous or nonexistent, apply only a supplied resolution rule.
5. Report the actual elapsed duration and counts for the window. A local day can differ from 24 elapsed hours.

## Completion check

Return the local interval, named zone, absolute boundaries, inclusion rules, timestamp precision, elapsed duration, and boundary-event classification. Recounting by the same rules must reproduce the result.

## Stop conditions

Stop if the zone is only an unexplained abbreviation, event times lack an interpretable zone, an ambiguous or nonexistent local time has no resolution rule, or timestamp precision or truncation leaves a boundary event's instant indeterminate. Do not silently choose a fixed offset or change boundary inclusion.

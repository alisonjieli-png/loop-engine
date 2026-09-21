# Build an incident timeline from evidence

Put the events in order from records that carry times, so the review argues about causes rather than about what happened.

## When to use it

Use it during and after any outage or security event, starting while it is still going on, because the evidence is easiest to collect then.

## Steps

1. Open one shared place to write while the event is happening, and record each action with the time it was taken.
2. Fix the time zone for the whole timeline, and convert everything into it as you add it.
3. Take each entry from a source that can be quoted: a log line, a deployment record, an alarm, a message, a query result.
4. Separate what was observed from what someone believed at the time. Both belong in the timeline, marked differently.
5. Mark the four moments that matter: when the cause was introduced, when the effect began, when a person first noticed, and when service returned.
6. Go back further than the alarm. The change that caused it is often days earlier and looked harmless.
7. Note the gaps where there is no evidence, rather than filling them from memory.
8. Have someone who was not involved read the timeline and say where it stops making sense.

## Checks

- Every entry has a time in one zone and a quotable source.
- Belief and observation are marked apart.
- The four moments are identified.
- The gaps without evidence are shown as gaps.

## Known-wrong example

A review builds its timeline from what people remember a week later. Two people place the same deployment on different days, and the conclusion blames a change that went out afterwards. The real cause was a settings edit nobody wrote down. Recording actions as they were taken, with times, would have cost minutes and given a true order.

## What to record

- The timeline with sources, times and one time zone.
- The four moments and the durations between them.
- The gaps in the evidence and what could make them visible next time.

## Source

- `src/loop_engine/code_nodes/run_playback.py`: this repository replays a saved record of a run into an ordered readable transcript, so what happened can be read step by step rather than reconstructed.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 7ed4e85.

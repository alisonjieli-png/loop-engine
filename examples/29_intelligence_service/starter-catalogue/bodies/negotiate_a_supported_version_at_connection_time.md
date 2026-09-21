# Agree on a supported version when the connection opens

Let the two sides state what they support and choose one shared form at the start, instead of discovering the mismatch in the middle of the work.

## When to use it

Use it when two parts are released separately: a client and a server, a worker and a queue, a plugin and a host, or two services that exchange records.

## Steps

1. Give each side a list of the exact versions and features it supports, not a single number.
2. At the start of the connection, exchange the lists and select the highest version that both sides support.
3. Record the selected version and the selected features, and use only those for the rest of the session.
4. If no shared version exists, refuse with a message naming both lists. Do not fall back to a guess.
5. Refuse a downgrade that would lose a required behaviour, such as an integrity check or a permission check, even when both sides support the older form.
6. Check the selection again at the point of use, so a later message cannot quietly use something outside the agreement.
7. Keep the agreement in the record you write, so a reader later knows which form produced it.
8. Test the three cases: an exact match, an overlap where the older side wins, and no overlap at all.

## Checks

- The selected version is recorded and used consistently.
- No shared version produces a refusal with both lists named.
- A downgrade that removes a safety behaviour is refused.
- All three negotiation cases have tests.

## Known-wrong example

A worker is upgraded and starts writing records in a new shape. The reader, still on the old release, does not recognise a field and ignores it, so approvals are silently dropped. Nothing fails, and the loss is found weeks later during an audit. An agreement at connection time, with the reader refusing a shape it does not support, would have stopped the first message instead of losing hundreds.

## What to record

- Both supported lists and the selected version.
- The refusals, with the lists that did not overlap.
- The selected version stored beside every record written in the session.

## Source

- `src/loop_engine/core/template_negotiation.py`: this repository marks which parts of a requested answer shape the other side may argue with and which parts it may not, so a reply that changes a required part is refused rather than accepted.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 7ed4e85.

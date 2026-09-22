# Validate input at the boundary and refuse early

Check what comes in at the edge of your system, turn it into your own types there, and refuse what does not fit before anything acts on it.

## When to use it

Use it at every place data enters: an endpoint, a message consumer, a file import, a form, a settings file and any answer from a model.

## Steps

1. Draw the boundary. Inside it, values are already valid; outside it, nothing is trusted.
2. Write the shape the input must have: fields, types, required or optional, allowed values, ranges, formats and units.
3. Convert at the boundary into your own types, so the rest of the code never handles raw text.
4. Refuse unknown fields rather than ignoring them. An ignored field hides a spelling mistake that silently changes nothing.
5. Refuse on the first complete check and return every problem at once, so the caller can fix them together.
6. Check the relationships between fields as well as each field alone: an end after its start, a total matching its parts.
7. Validate in one place per boundary. Scattered checks disagree with each other over time.
8. Test the refusals as carefully as the acceptances, including the empty value, the missing field and the extra field.

## Checks

- A value inside the boundary never needs checking again.
- An unknown field causes a refusal with a clear message.
- All the problems in one input are reported together.
- Refusal cases have tests, including missing and extra fields.

## Known-wrong example

A settings reader ignores keys it does not know. Someone writes the retry limit with a spelling mistake, and the service silently keeps the default of zero retries. Weeks later a brief outage becomes a full one, and the settings file looks correct to everyone who reads it. Refusing the unknown key at start would have reported the mistake in one second.

## What to record

- The declared shape for each boundary.
- The refusal messages and the tests that produce them.
- Any field deliberately accepted and ignored, with the reason.

## Source

- `src/loop_engine/core/settings_loader.py`: this repository refuses a settings key it does not know, so a misspelled setting cannot quietly change how a run behaves.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.

# Procedure: Personal data masker for free text

Follow this procedure to do the activity with the helper `personal_data_masker.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Who will read the masked text, and what do they need to keep (dates, ages, places)?
2. Which identifiers appear in this text type: record numbers, claim numbers, student ids?
3. Is there a list of names (patients, students, staff) for this batch?
4. Which law or policy applies (for example health or education privacy rules)?

## Steps

1. Add custom patterns for local identifiers before the first run.
2. Run the helper on a sample and read the masked text line by line.
3. Add missed names to the names list and rerun.
4. Check the inventory counts against expectations for the text type.
5. Release the masked text only; keep the original in its controlled location.

## Decision points

### Placeholder style

- numbered: choose when readers need to follow who is who across the text
- label: choose when even linking within a text is too revealing

Default when nothing settles it: numbered

Evidence that settles it: what the reader's task needs

### Dates

- mask: choose when dates can identify a person (birth, admission)
- keep: choose when dates are only schedule dates; remove date from categories

Default when nothing settles it: mask

Evidence that settles it: the privacy rule that applies

## Quality checks

- Read the masked text in full on a sample; pattern masking misses things.
- Search the masked text for each listed name: none should remain.
- Confirm no placeholder replaced text that is needed and harmless (product codes).

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: default categories; thorough: custom patterns and names lists per batch | thorough catches local identifiers |
| Tools | free: this helper, Microsoft Presidio; paid: data loss prevention suites | same purpose |
| Strength | numbered or label placeholders | label hides links between mentions |

## Stop and ask, or hand to a person

- Images, scanned documents and audio.
- Formal anonymization or re-identification risk assessment: a privacy officer decides.

# Procedure: Duplicate record finder with blocking and weighted similarity

Follow this procedure to do the activity with the helper `duplicate_record_finder.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. What makes two records the same real thing (person, company, product, location)?
2. Which fields are reliable, and which are often empty or mistyped?
3. What does a false merge cost compared with a missed duplicate?
4. Who decides on possible duplicates, and how will merges be applied?

## Steps

1. Validate and normalize the records first with record_entry_validator.
2. Choose two or more blocking keys so a true duplicate shares at least one.
3. Choose fields, methods and weights; reliable identifiers get more weight.
4. Run on a sample with known duplicates and adjust thresholds until the known pairs are found.
5. Run on the full set; send duplicates for bulk approval and possible pairs for one-by-one review.
6. Apply merges in the system of record, keeping the surviving id and a merge log.

## Decision points

### Thresholds

- high precision (0.9 and 0.8): choose when a false merge is costly (patients, accounts)
- balanced (0.85 and 0.7): choose when general contact or vendor lists
- high recall (0.75 and 0.6): choose when a later person checks every pair

Default when nothing settles it: 0.85 and 0.7 with every pair checked by a person before merging

Evidence that settles it: precision and recall on a labelled sample

### Blocking strength

- strict keys: choose when the record set is large and the pair limit is reached
- loose keys: choose when duplicates are known to differ in spelling

Default when nothing settles it: postal code plus a phonetic name key

Evidence that settles it: candidate_pairs and missed known duplicates

## Quality checks

- Known duplicate pairs from the sample appear as duplicates or possible.
- No cluster is large without reason; a large cluster often means a too generic value.
- Every record id is distinct before matching.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one blocking key; thorough: two or three keys | more keys find more pairs |
| Tools | free: this helper, OpenRefine clustering, Splink; paid: master data management suites | same idea |
| Domain | people, companies or products | changes fields and weights, not code |

## Stop and ask, or hand to a person

- Merging records: the system of record does it after approval.
- Legal identity checks.

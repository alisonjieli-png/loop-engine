# Duplicate record finder with blocking and weighted similarity

Find likely duplicate records by comparing only pairs that share a blocking key, scoring weighted field similarities (exact, normalized, token overlap, edit distance, digits, date) and grouping duplicates into clusters.

## What it does

Blocking keys (normalized value, first three characters, Soundex, digits, last four digits) limit comparisons to plausible pairs. Each compared pair gets a weighted average of field similarities; a field missing on either side is left out and the weights renormalized. Pairs above the duplicate threshold are duplicates, pairs above the review threshold are possible, and duplicates are merged into clusters with union-find.

## Run it

As a library:

```python
from duplicate_record_finder import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 duplicate_record_finder.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `records` (array of object, required): records as objects; each has the id field
- `id_field` (string): field holding the record id (default id)
- `fields` (array of object, required): compared fields with a weight and a method (exact, normalized, token_jaccard, edit_ratio, digits, date)
- `blocking` (array of object, required): keys that candidate pairs must share: a field and a transform (normalized, prefix3, soundex, digits, last4_digits)
- `duplicate_threshold` (number): score at or above which a pair is a duplicate (default 0.85)
- `review_threshold` (number): score at or above which a pair is a possible duplicate (default 0.7)
- `max_pairs` (integer): refuse when blocking yields more candidate pairs (default 200000)

## Output

- `summary` (object, required): records, candidate pairs, duplicates, possible, clusters
- `pairs` (array of object, required): pairs at or above the review threshold, best first
- `clusters` (array of object, required): groups of duplicates with the first id as representative

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two records share an id
- `field_absent`: a compared or blocking field appears in no record
- `weights_invalid`: the field weights sum to zero
- `thresholds_out_of_order`: the review threshold is above the duplicate threshold
- `too_many_pairs`: the blocking keys produce more than the pair limit; use stricter blocking

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `duplicate_record_finder.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 31 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.a.2.a.1` | Verify accuracy of records. | 13 | 115 |
| `4.A.3.b.6.h.9` | Maintain records, documents, or other files. | 17 | 71 |
| `4.A.3.b.6.h.15` | Maintain records of customer accounts. | 3 | 749 |

Occupations with the most of these activities: Court Reporters and Simultaneous Captioners (`27-3092.00`); Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products (`41-4011.00`); Administrative Services Managers (`11-3012.00`); Fitness and Wellness Coordinators (`11-9179.01`); Compliance Managers (`11-9199.02`); Claims Adjusters, Examiners, and Investigators (`13-1031.00`).

Example O*NET task statements linked to these activities:

- "Preserve and maintain digital forensic evidence for analysis." (Digital Forensics Analysts, task `21799`)
- "Maintain student records, including special education reports, confidential records, records of services provided, and behavioral data." (School Psychologists, task `5455`)
- "Maintain records and files of work and revisions." (Technical Writers, task `3967`)
- "Verify and analyze data used in settling claims to ensure that claims are valid and that settlements are made according to company practices and procedures." (Claims Adjusters, Examiners, and Investigators, task `21428`)

## Limits

Pairs that share no blocking key are never compared, so weak blocking misses duplicates. Edit distance uses the first 200 characters. Similarity weights and thresholds are judgment; tune them on a labelled sample. Clusters chain pairs, so A like B and B like C puts A and C together even when A and C differ. The helper never merges records; it only proposes.

This kit is a candidate component. Generating it did not approve or qualify it.

# Audit data splits for errors and leakage

Check the training, test and cross-validation data for errors, and for information that crosses from one split into another. Do this before trusting any score.

## When to use it

Use it before training, after every change to the way the data is split, and whenever a score looks better than expected.

## Steps

1. Split errors: run the same audit on every split. Check the schema, the value ranges, the types and the duplicates, and check a sample of the labels by hand.
2. Label errors: ask whether any labels are wrong and whether fixing them would change the conclusion. Compare a labelled sample with the source and estimate the label error rate.
3. Leakage across splits: ask whether an identity, a time or a proxy of the target crosses between the splits. Audit the split with respect to groups and to time, and search for near duplicates across the splits.
4. Look for information that would not exist at the moment the result is needed: identifiers, future values, and any split whose parts share a source.
5. Simplification: ask whether the data can be simplified without losing the signal. Measure how the result changes when redundant columns, constant columns and duplicate rows are dropped.
6. Report every difference between parts of the data that are supposed to match: missing values, duplication and inconsistent encoding.

## Checks

- No entity, such as a customer, a patient or a device, appears in more than one split, unless the task allows it and the report says so.
- For data with a time order, every training row is earlier than every test row.
- The number of near duplicates across the splits is reported, even when it is zero.
- The label error rate has a sample size.

## Known-wrong example

A readmission model reaches an area under the curve of 0.97. The rows were split at random, so visits of the same patient sit in the training data and in the test data. The model recognizes patients. It does not predict readmission. A split by patient drops the score to a believable level, and that score is the honest one.

## What to record

- The audit of each split, with counts.
- The rule for groups and for time that the split follows, and the number of violations.
- The near duplicates that were found and what was done with them.
- The estimated label error rate, with its sample.

## Source

- `src/loop_engine/strings/interrogation.py`: the question bank, category `data_quality`.
- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the perspectives of the leakage hunter and the data quality auditor.

Licence: MIT. Compiled from revision 565e133.

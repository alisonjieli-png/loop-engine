# Finding kinds of the drift audit

Read this file only when a finding in the JSON is unclear. Each kind names what the script measured, the option that sets its limit, and the usual responses. The responses are choices for the step result, not changes the script makes.

| Kind | What it means | Limit option (default) | Usual responses |
|---|---|---|---|
| `missing_rate_shift` | The share of missing cells differs between the files by at least the limit. | `--missing-gap` (0.10) | Add a missing flag feature; check whether the test file uses another missing token; ask whether the column is collected the same way. |
| `unseen_categories` | At least the limit share of test values never occurs in training. `examples` shows up to 5 of them. | `--unseen-share` (0.01) | Map the new values to an "other" group; check for spelling or case differences; drop the column if most values are new. |
| `outside_train_range` | At least the limit share of test numbers is below the training minimum or above the training maximum. | `--outside-share` (0.01) | Expect tree models to treat these values like the nearest training value; consider a ratio or a difference feature; report the shift. |
| `distribution_shift` | The population stability index is at or above the limit. A common rule of thumb reads 0.1 to 0.25 as a moderate shift and above 0.25 as a large one. Numbers are compared in up to 10 buckets of about equal training rows (`buckets`); a value with many rows, such as 0, has a bucket of its own. | `--psi-limit` (0.25) | Compare the train and test means in the finding; check whether the test period or source differs; consider validation that imitates the shift. |
| `type_mismatch` | Training values are all numbers, but some test values are text. `test_examples` shows up to 3. | none | Look for a decimal comma, a unit suffix or a placeholder word; fix the parsing in the feature code, not in the raw files. |
| `constant_in_train` | The column has one value in training. | none | Drop it as a feature. |
| `empty_in_train` | Every training cell is missing. | none | Drop it as a feature. |
| `identifier_like` | No training value repeats and nearly every test value is new, as with a row number or a key. | none | Leave it out of the features and pass it with `--id` next time. If it is a real measure, say so in the step result. |

Top-level fields:

- `columns_only_in_train`: the model cannot use these columns on test rows. The target is not listed here when you pass `--target`.
- `columns_only_in_test`: new columns; they cannot be learned from training.
- `target_in_test`: true means the test file holds the label column. Stop and report.
- `notes`: checks that were skipped, with the reason. A note is not a finding.

Missing cells are the texts in `settings.missing_tokens`, compared after removing surrounding spaces. Pass `--missing-token` one or more times to use your own list instead.

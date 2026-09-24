# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file or field you read. Put every no or unknown in the report as an open point.

- [ ] Each prediction came from a model that did not train on that row's fold. The script cannot see how the predictions were made.
- [ ] Every step that learns from data, such as scaling, filling missing values or target encoding, was fitted inside the training folds only.
- [ ] The metric, its settings and the positive label are the ones the task or the competition names.
- [ ] The claimed score was copied with all its decimals, and your report names where the claim is written.
- [ ] The fold file is the one the training step used, and its `sha256` is in your report.
- [ ] A local score is not a leaderboard score. Your report does not promise a leaderboard result.

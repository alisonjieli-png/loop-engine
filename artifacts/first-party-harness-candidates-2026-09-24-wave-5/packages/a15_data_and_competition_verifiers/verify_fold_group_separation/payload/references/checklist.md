# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file or field you read. Put every no or unknown in the report as an open point.

- [ ] The group column is the entity the task says must not be in training and validation together, not only a column that looks like an id.
- [ ] No other column links rows of different groups, such as one household with several customers or one device shared by patients. The script checks only the column you named.
- [ ] If the rows have a time order that the task cares about, the folds respect it. This script does not check time.
- [ ] The fold file you checked is the one the training step reads, and its `sha256` is in your report.
- [ ] The tolerance and the number of folds come from the task or the plan, not from this result.

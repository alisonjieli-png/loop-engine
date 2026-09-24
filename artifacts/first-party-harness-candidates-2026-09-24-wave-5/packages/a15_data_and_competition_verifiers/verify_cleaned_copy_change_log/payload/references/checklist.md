# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file or field you read. Put every no or unknown in the report as an open point.

- [ ] The source table is the raw input the task names. When a digest was recorded before cleaning, you passed it with `--source-sha256`.
- [ ] The key columns identify one real record per row, as the task describes the data.
- [ ] Each logged change follows a rule that the task or a reviewed plan allows. A matching entry shows that a change was written down, not that it was right.
- [ ] Every removed or added row has a reason that the task allows, such as a reviewed duplicate.
- [ ] You opened one reported row in both tables and saw the values the script reports.
- [ ] If `--no-values` was used for private data, your report quotes no cell values.

---
name: check-csv-columns
description: Check that a CSV file has the columns a pipeline stage expects, in order.
---

# Check CSV columns

Read the header line of the file and compare it with
[the expected columns](assets/columns.json). Report every missing, extra or
reordered column by name.

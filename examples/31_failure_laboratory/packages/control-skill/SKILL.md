---
name: count-csv-rows
description: Count the data rows of a CSV file before and after a cleaning step, so that a lost or repeated row shows at once.
---

# Count CSV rows

Run [the row counter](scripts/count_rows.sh) on the input file before the
cleaning step and on the output file after it.

1. Pass the path of the file as the only argument.
2. Compare the two counts. A difference that the step does not explain is a
   finding to report, not a result to accept.

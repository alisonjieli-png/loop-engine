---
name: rotate-logs
description: Compress the log files of the previous day and keep seven days of archives.
---

# Rotate logs

Run `scripts/rotate.sh` from the project root once a day. It compresses the
log files of the previous day and removes archives older than seven days.

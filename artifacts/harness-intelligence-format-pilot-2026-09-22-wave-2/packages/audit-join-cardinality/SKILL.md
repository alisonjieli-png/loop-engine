---
name: audit-join-cardinality
description: Measure duplicate and unmatched keys plus projected row expansion before joining two comma-separated tables.
---

# Audit join cardinality

Use this skill before joining two user-supplied tables when duplicate keys could multiply rows or a missing match could silently drop records. It measures the complete bounded input, returns counts without key values, and compares those counts with the declared join shape. It does not run the join or decide whether unmatched rows are acceptable for the business task.

## Invoke

The owning runtime must authorize an exact absolute materials root and both relative input paths. From this skill directory:

```bash
python3 -B scripts/audit_join_cardinality.py \
  --approved-root /approved/materials \
  --left-relative orders.csv --right-relative customers.csv \
  --left-key customer_id --right-key customer_id \
  --expect many-to-one --require-left-match
```

The expectation can be `one-to-one`, `one-to-many`, `many-to-one`, or `many-to-many`. The default is `one-to-one`. Require matches on either side only when the task contract calls for them. The maximum is 20,000,000 bytes and 100,000 data rows per input, and 1,000,000 projected joined rows. Each ceiling can be lowered by its command argument, not raised.

## Result and scope

The command prints one `join_cardinality_audit/v1` JSON object. It returns `pass` with exit 0, `fail` with exit 1, or `refused` with exit 2. The report includes input byte digests, row counts, duplicate-key row counts, blank keys, unmatched rows and projected joined rows. An empty or whitespace-only key fails the audit and never matches another blank key. Whitespace around a nonblank key remains significant; the script does not normalize business identifiers. A table with a missing or duplicate header, malformed records, invalid UTF-8 or unequal field counts fails before cardinality is reported.

The script reads only the selected regular files, follows no symbolic links in the approved path, writes no files, uses no network or credentials, and returns no data rows or key values. The owning Loop supplies file-read authority and a stable input snapshot. The result does not authorize a later join, upload or write. It also does not determine whether the join keys mean the same thing, and it does not inspect non-comma delimiters.

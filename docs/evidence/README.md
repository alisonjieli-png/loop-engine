# Evidence artifacts

Kind: raw evidence artifacts.

This folder holds the JSON files, logs, transcripts, and folders that a
verification report cites. Names carry a date, compact (`20260906`) or
dashed (`2026-09-06`). An artifact is never edited after the report that
cites it is written. Because artifacts quote what a run produced, this
folder is excluded from the live-language lint.

What does not belong here: the reports themselves (see
`../verification/`) and anything that contains a provider key,
authorization header, private prompt, or raw secret.

The [records index](../RECORDS-INDEX.md) lists every dated artifact by
subject.

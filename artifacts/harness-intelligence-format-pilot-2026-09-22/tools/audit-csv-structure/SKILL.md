---
name: audit-csv-structure
description: Audit a user-supplied CSV or TSV file for malformed rows, duplicate headers and inconsistent field counts before an ingest step.
---

# Audit CSV structure

Use this skill when a task depends on loading a delimited table and a silent row shift would corrupt downstream work. It checks the whole bounded file, including quoted delimiters and multiline quoted values. It does not infer types or validate business meaning.

## Input and command

The owning runtime must supply an exact approved absolute materials root and a relative path below it. Run `python3 -B scripts/audit_csv_structure.py --approved-root /approved/materials --input-relative table.csv` from this skill directory. The default `--header-mode absent` treats the first row as data and returns no raw field names. Use `--header-mode present` only when a header row is part of the declared input contract. Supply `--delimiter $'\t'` for tab-separated input. The 20,000,000-byte ceiling may be lowered with `--max-bytes` but cannot be raised by this script.

## Output and effects

The script reads the input and writes one `csv_structure_audit/v1` JSON object to standard output. It writes no files, sends no network requests and reads no credentials. Status `pass` exits 0, `fail` exits 1 and `refused` exits 2. The report binds to the observed input bytes with a SHA-256 digest. A failure gives counts and at most 20 issue locations, without data row values. Header names appear only in `present` mode. The parser uses the declared byte ceiling as its field-character ceiling, so a valid field above Python's smaller default limit is not mislabeled malformed. `pass` means structural checks passed, not that data are correct or safe to publish.

The owning Loop decides whether to continue after the audit. This file does not grant permission to read arbitrary files or execute a later ingest. The script requires POSIX no-follow descriptor operations and opens the selected file nonblocking before rejecting FIFOs and other non-regular files. It refuses symbolic links or traversal in every path component. The owning runtime must still authorize the root and prevent concurrent mutation of the material while the audit runs.

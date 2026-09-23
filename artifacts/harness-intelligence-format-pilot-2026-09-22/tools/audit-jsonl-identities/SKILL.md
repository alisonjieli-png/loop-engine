---
name: audit-jsonl-identities
description: Check a user-supplied JSON Lines event file for missing identities, repeat deliveries and one identity carrying conflicting payloads.
---

# Audit JSON Lines event identities

Use this skill before replaying or aggregating an event file when an exact top-level event identity is declared. The audit distinguishes identical repeat delivery from a changed payload under the same identity. It does not decide whether a repeated delivery is acceptable to the business process.

## Input and command

The owning runtime must supply an exact approved absolute materials root, a relative path below it, and a declared top-level string or integer identity key. Run `python3 -B scripts/audit_jsonl_identities.py --approved-root /approved/materials --input-relative events.jsonl --id-field event_id` from this skill directory. The fixed ceilings are 20,000,000 bytes and 100,000 lines; `--max-bytes` and `--max-records` may lower them.

## Output and effects

The script reads the file and writes one `jsonl_identity_audit/v1` JSON object to standard output. It sends no network requests, reads no credentials and writes no files. It records the observed input SHA-256 digest, line numbers and counts, never event bodies or identities. Decimal and exponent values are parsed without binary-float rounding before payload comparison. A finite exponent within the Decimal parser's range is classified without evaluating its magnitude; an exponent outside that range becomes an invalid-record result. Status `pass` exits 0, `fail` exits 1 and `refused` exits 2. A pass permits further evaluation but does not prove event order, signature validity, ownership, completeness or safe replay.

The owning Loop supplies file-read authority and decides how to handle identical repeats. This skill does not authorize replay or any external effect. The script requires POSIX no-follow descriptor operations, opens the selected file nonblocking before rejecting FIFOs and other non-regular files, and refuses symbolic links or traversal in every path component. The owning runtime must prevent concurrent mutation of the input while the audit runs.

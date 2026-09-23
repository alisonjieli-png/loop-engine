---
name: audit-text-encoding
description: Check a bounded text input for invalid UTF-8, mixed newlines, NUL characters and oversized lines before ingest.
---

# Audit text encoding

Use this skill before a text ingest, conversion or diff when invalid encoding or mixed line endings could change parsing. It reports structural facts without returning the text.

## Invoke

The owning runtime must authorize an exact absolute materials root and one relative input path. From this skill directory:

```bash
python3 -B scripts/audit_text_encoding.py \
  --approved-root /approved/materials --input-relative notes.txt
```

The default line limit is 10,000 Unicode characters. Use `--max-line-chars` to lower or raise that threshold up to the fixed 100,000-character ceiling. The file ceiling is 20,000,000 bytes and may only be lowered with `--max-bytes`.

## Result and scope

The command prints one `text_encoding_audit/v1` JSON object. It returns `pass` with exit 0, `fail` with exit 1, or `refused` with exit 2. Invalid UTF-8, a NUL character, mixed carriage-return and line-feed styles, or a line over the declared limit fails. A UTF-8 byte-order mark and trailing whitespace are reported without failing. It returns a byte digest, byte and physical-line counts and issue counts, never source lines.

The script reads only one regular file under the approved root, follows no symbolic links in its path, writes no files, and uses no network or credentials. The owning Loop provides read authority and a stable input snapshot. A passing encoding audit does not prove that the content is factually correct, safe to execute, or suitable for the next transformation.

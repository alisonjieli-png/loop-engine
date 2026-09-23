---
name: audit-zip-package
description: Inspect a bounded ZIP package for unsafe entry paths, duplicate paths, symbolic links and declared expansion before extraction.
---

# Audit a ZIP package before extraction

Use this skill when a supplied ZIP archive may contain a skill, tool, dataset or project bundle. Run the metadata audit before any extraction or installation. A pass permits a later, separately authorized inspection; it does not mean the archive is trusted.

## Invoke

The owning runtime must authorize an exact absolute materials root and the relative archive path. From this skill directory:

```bash
python3 -B scripts/audit_zip_package.py \
  --approved-root /approved/materials --input-relative bundle.zip
```

The built-in limits are 20,000,000 archive bytes, 5,000 entries, 100,000,000 declared expanded bytes and a per-entry expansion ratio of 100. An entry name may have at most 32 path components, 1,024 UTF-8 bytes overall and 240 UTF-8 bytes per component. Lower the configurable limits with `--max-bytes`, `--max-entries`, `--max-expanded-bytes` and `--max-ratio`. The script refuses any attempt to raise its ceilings.

## Result and scope

The command prints one `zip_package_audit/v1` JSON object. It returns `pass` with exit 0, `fail` with exit 1, or `refused` with exit 2. It reports an archive digest, entry count when available, claimed expanded bytes when completely inspected, and bounded issue counts. It rejects traversal and absolute entry paths, Windows separators and reserved device names, colons and trailing dots or spaces in every component, Unicode compatibility and casefold path collisions, symbolic links, unsupported special files, privileged Unix modes, encrypted entries, files used as parent directories and excessive declared expansion. It does not echo entry names.

Before invoking the ZIP parser, the script counts central-directory entry signatures in the bounded archive bytes. More than 5,000 matching byte sequences returns `refused` with an unknown screening result, without loading the entry list. Member payload bytes can also contain that sequence; the prefilter does not establish that the archive has too many entries or is unsafe. The exact entry count and expanded size remain unknown rather than being reported as zero. The script reads one regular file without following symbolic links, writes no file, extracts nothing, and uses no network or credentials. It examines central-directory metadata only. It does not decompress content, verify checksums, find malware, establish a licence or test a tool. The owning Loop must separately authorize and sandbox any later extraction or execution.

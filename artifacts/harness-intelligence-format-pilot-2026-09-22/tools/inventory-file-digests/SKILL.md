---
name: inventory-file-digests
description: Build a bounded, exact SHA-256 inventory of files in an authorized directory before comparing, transferring or reviewing a package.
---

# Inventory file digests

Use this skill when a task needs to name the exact bytes of a local package or source set. It reports relative paths, byte counts, SHA-256 digests and groups of paths with the same digest. A matching digest is evidence of equal bytes; it is not proof of source rights or safety.

## Input and command

The owning runtime must supply an exact approved absolute materials root. Run `python3 -B scripts/inventory_file_digests.py --approved-root /approved/materials` from this skill directory. Select a subtree with `--tree-relative package` when needed; the default `.` scans the approved root. The fixed ceilings are 1,000 files, 50,000,000 file bytes, 32 nested directory levels and 5,000 directory entries. `--max-files` and `--max-total-bytes` may lower their ceilings. Symbolic links, traversal and special files cause refusal.

## Output and effects

The script reads file bytes and writes one `file_digest_inventory/v1` JSON object to standard output. It writes no files, sends no network requests and reads no credentials. Status `pass` exits 0; `refused` exits 2. The output may reveal names and digests of private files, so keep it under the same access policy as the input. The script requires POSIX no-follow descriptor operations, opens candidate files nonblocking before checking their type, and checks file metadata for change while hashing. A pass is an inventory observation, not an approval of package content or a consistent snapshot of a concurrently changing tree.

The owning Loop decides whether the inventory is useful and whether any later comparison or installation is authorized. The command-line root is an input selector, not permission to read it; the owning runtime must enforce the exact authority separately.

"""Read-only SHA-256 inventory of a bounded, symlink-free directory tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat

from confined_input import ConfinedInputError, open_approved_directory, relative_parts

DEFAULT_MAX_FILES = 1_000
DEFAULT_MAX_BYTES = 50_000_000
MAX_DEPTH = 32
MAX_ENTRIES = 5_000


class InventoryInputError(ValueError):
    """The requested tree cannot be inventoried under this contract."""


def inventory(
    approved_root: str,
    tree_relative: str = ".",
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_BYTES,
) -> dict:
    if (
        not 1 <= max_files <= DEFAULT_MAX_FILES
        or not 1 <= max_total_bytes <= DEFAULT_MAX_BYTES
    ):
        raise InventoryInputError("resource_limits_outside_supported_range")
    files: list[dict] = []
    used_bytes = 0
    visited_entries = 0

    def digest_file(directory: int, name: str) -> tuple[int, str]:
        if not hasattr(os, "O_NONBLOCK"):
            raise InventoryInputError("nonblocking_file_open_unavailable")
        try:
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
        except OSError:
            raise InventoryInputError("file_missing_or_symlinked_during_scan") from None
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise InventoryInputError("non_regular_entry_in_tree")
            if before.st_size > max_total_bytes - used_bytes:
                raise InventoryInputError("tree_exceeds_max_total_bytes")
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                while chunk := handle.read(65_536):
                    size += len(chunk)
                    if size > max_total_bytes - used_bytes:
                        raise InventoryInputError("tree_exceeds_max_total_bytes")
                    digest.update(chunk)
                after = os.fstat(handle.fileno())
            if (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ):
                raise InventoryInputError("file_changed_during_scan")
            return size, digest.hexdigest()
        finally:
            if descriptor != -1:
                os.close(descriptor)

    def visit(directory: int, prefix: tuple[str, ...], depth: int) -> None:
        nonlocal used_bytes, visited_entries
        if depth > MAX_DEPTH:
            raise InventoryInputError("tree_exceeds_max_depth")
        names = []
        with os.scandir(directory) as entries:
            for entry in entries:
                visited_entries += 1
                if visited_entries > MAX_ENTRIES:
                    raise InventoryInputError("tree_exceeds_max_entries")
                names.append(entry.name)
        for name in sorted(names):
            details = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(details.st_mode):
                try:
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory,
                    )
                except OSError:
                    raise InventoryInputError(
                        "directory_missing_or_symlinked_during_scan"
                    ) from None
                try:
                    visit(child, (*prefix, name), depth + 1)
                finally:
                    os.close(child)
                continue
            if not stat.S_ISREG(details.st_mode):
                raise InventoryInputError("symlink_or_non_regular_entry_in_tree")
            if len(files) >= max_files:
                raise InventoryInputError("tree_exceeds_max_files")
            size, digest = digest_file(directory, name)
            used_bytes += size
            files.append(
                {
                    "path": "/".join((*prefix, name)),
                    "bytes": size,
                    "sha256": digest,
                }
            )

    try:
        relative_parts(tree_relative, allow_root=True)
        with open_approved_directory(approved_root, tree_relative) as directory:
            visit(directory, (), 0)
    except ConfinedInputError as error:
        raise InventoryInputError(str(error)) from None
    except OSError:
        raise InventoryInputError("tree_unreadable_or_changed_during_scan") from None
    files.sort(key=lambda item: item["path"])
    by_digest: dict[str, list[str]] = {}
    for record in files:
        by_digest.setdefault(record["sha256"], []).append(record["path"])
    duplicate_groups = [paths for paths in by_digest.values() if len(paths) > 1]
    duplicate_groups.sort(key=lambda paths: paths[0])
    return {
        "record_type": "file_digest_inventory/v1",
        "status": "pass",
        "file_count": len(files),
        "total_bytes": used_bytes,
        "files": files,
        "same_digest_groups": duplicate_groups,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--tree-relative", default=".")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        report = inventory(
            args.approved_root, args.tree_relative, args.max_files, args.max_total_bytes
        )
    except (InventoryInputError, OSError) as error:
        report = {
            "record_type": "file_digest_inventory/v1",
            "status": "refused",
            "reason": str(error)
            if isinstance(error, InventoryInputError)
            else "tree_unreadable",
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

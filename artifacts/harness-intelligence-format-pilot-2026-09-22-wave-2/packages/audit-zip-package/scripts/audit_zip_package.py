"""Inspect ZIP metadata before any extraction or tool installation."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import unicodedata
import zipfile
from collections import Counter

from confined_input import ConfinedInputError, open_approved_file

MAX_ARCHIVE_BYTES = 20_000_000
MAX_ENTRIES = 5_000
MAX_EXPANDED_BYTES = 100_000_000
MAX_RATIO = 100
MAX_FINDINGS = 20
MAX_PATH_DEPTH = 32
MAX_ENTRY_NAME_BYTES = 1_024
MAX_COMPONENT_BYTES = 240
CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    *(f"COM{number}" for number in range(10)),
    *(f"LPT{number}" for number in range(10)),
}
WINDOWS_FORBIDDEN = set('<>:"|?*')


def _entry_path(name: str) -> tuple[tuple[str, ...] | None, str | None]:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return None, "unsafe_entry_path"
    clean = name.removesuffix("/")
    if clean.count("/") + 1 > MAX_PATH_DEPTH:
        return None, "entry_path_depth_exceeds_ceiling"
    if len(name.encode("utf-8")) > MAX_ENTRY_NAME_BYTES:
        return None, "entry_name_bytes_exceeds_ceiling"
    parts = tuple(clean.split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None, "unsafe_entry_path"
    for part in parts:
        if len(part.encode("utf-8")) > MAX_COMPONENT_BYTES:
            return None, "entry_component_bytes_exceeds_ceiling"
        if (
            part.startswith(" ")
            or part.endswith((" ", "."))
            or any(ord(char) < 32 or char in WINDOWS_FORBIDDEN for char in part)
        ):
            return None, "unsafe_entry_path"
        device_stem = unicodedata.normalize("NFKC", part.split(".", 1)[0]).upper()
        if device_stem in WINDOWS_RESERVED:
            return None, "unsafe_entry_path"
    return parts, None


def _portable_path(parts: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", part).casefold())
        for part in parts
    )


def audit(args: argparse.Namespace) -> dict[str, object]:
    if not 0 < args.max_bytes <= MAX_ARCHIVE_BYTES:
        raise ConfinedInputError("max_bytes_outside_supported_ceiling")
    if not 0 < args.max_entries <= MAX_ENTRIES:
        raise ConfinedInputError("max_entries_outside_supported_ceiling")
    if not 0 < args.max_expanded_bytes <= MAX_EXPANDED_BYTES:
        raise ConfinedInputError("max_expanded_bytes_outside_supported_ceiling")
    if not 0 < args.max_ratio <= MAX_RATIO:
        raise ConfinedInputError("max_ratio_outside_supported_ceiling")
    with open_approved_file(args.approved_root, args.input_relative) as handle:
        if os.fstat(handle.fileno()).st_size > args.max_bytes:
            raise ConfinedInputError("archive_exceeds_byte_ceiling")
        raw = handle.read(args.max_bytes + 1)
    if len(raw) > args.max_bytes:
        raise ConfinedInputError("archive_exceeds_byte_ceiling")

    issue_counts: Counter[str] = Counter()
    findings: list[dict[str, object]] = []

    def issue(code: str, index: int | None = None) -> None:
        issue_counts[code] += 1
        if len(findings) < MAX_FINDINGS:
            finding: dict[str, object] = {"code": code}
            if index is not None:
                finding["entry_index"] = index
            findings.append(finding)

    total_expanded = 0
    entries: int | None = None
    metadata_complete = False
    seen_exact: set[tuple[str, ...]] = set()
    seen_portable: dict[tuple[str, ...], tuple[tuple[str, ...], bool]] = {}
    signature_count = raw.count(CENTRAL_DIRECTORY_SIGNATURE)
    if signature_count > MAX_ENTRIES:
        return {
            "schema": "zip_package_audit/v1",
            "status": "refused",
            "reason": "entry_signature_prefilter_ambiguous",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "archive_bytes": len(raw),
            "entries": None,
            "central_directory_signature_count": signature_count,
            "claimed_expanded_bytes": None,
            "metadata_complete": False,
            "issue_counts": {},
            "findings": [],
            "findings_truncated": False,
        }
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos = archive.infolist()
                entries = len(infos)
                if entries > args.max_entries:
                    issue("entry_count_exceeds_ceiling")
                else:
                    for index, info in enumerate(infos):
                        path, path_error = _entry_path(info.filename)
                        if path_error:
                            issue(path_error, index)
                        elif path is not None:
                            portable = _portable_path(path)
                            if path in seen_exact:
                                issue("duplicate_entry_path", index)
                            elif portable in seen_portable:
                                issue("portable_path_collision", index)
                            else:
                                seen_exact.add(path)
                                seen_portable[portable] = (path, info.is_dir())
                        mode = info.external_attr >> 16
                        file_type = stat.S_IFMT(mode)
                        if file_type == stat.S_IFLNK:
                            issue("symbolic_link_entry", index)
                        elif file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                            issue("unsupported_special_file_entry", index)
                        if mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                            issue("privileged_mode_entry", index)
                        if file_type == stat.S_IFDIR and not info.is_dir():
                            issue("entry_type_mismatch", index)
                        if file_type == stat.S_IFREG and info.is_dir():
                            issue("entry_type_mismatch", index)
                        if info.flag_bits & 1:
                            issue("encrypted_entry", index)
                        if info.is_dir() and info.file_size:
                            issue("directory_has_payload", index)
                        total_expanded += info.file_size
                        if (
                            total_expanded > args.max_expanded_bytes
                            and issue_counts["expanded_size_exceeds_ceiling"] == 0
                        ):
                            issue("expanded_size_exceeds_ceiling")
                        if info.file_size and (
                            info.compress_size == 0
                            or info.file_size > info.compress_size * args.max_ratio
                        ):
                            issue("entry_expansion_ratio_exceeds_ceiling", index)
                    for portable in seen_portable:
                        for length in range(1, len(portable)):
                            parent = portable[:length]
                            if parent in seen_portable and not seen_portable[parent][1]:
                                issue("file_used_as_parent")
                                break
                    metadata_complete = True
        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError):
            issue("invalid_zip")
        except MemoryError:
            issue("zip_parser_memory_unavailable")
    return {
        "schema": "zip_package_audit/v1",
        "status": "fail" if issue_counts else "pass",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "archive_bytes": len(raw),
        "entries": entries,
        "central_directory_signature_count": signature_count,
        "claimed_expanded_bytes": total_expanded if metadata_complete else None,
        "metadata_complete": metadata_complete,
        "issue_counts": dict(sorted(issue_counts.items())),
        "findings": findings,
        "findings_truncated": sum(issue_counts.values()) > len(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--input-relative", required=True)
    parser.add_argument("--max-bytes", type=int, default=MAX_ARCHIVE_BYTES)
    parser.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
    parser.add_argument("--max-expanded-bytes", type=int, default=MAX_EXPANDED_BYTES)
    parser.add_argument("--max-ratio", type=int, default=MAX_RATIO)
    args = parser.parse_args()
    try:
        result = audit(args)
    except (ConfinedInputError, OSError) as error:
        result = {
            "schema": "zip_package_audit/v1",
            "status": "refused",
            "reason": str(error),
        }
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "refused": 2}[str(result["status"])]


if __name__ == "__main__":
    sys.exit(main())

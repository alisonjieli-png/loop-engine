"""Effects: reads the step packet manifest, the files it lists and the names in the packet folder under the workspace root; writes nothing.

Checks, before work starts, that a focused step packet is exactly the packet
the host placed. The host writes a manifest (default
.baltor/step/packet-manifest.json) with the fields of the
focused_step_packet_candidate/v1 records that the Codex packet renderer
writes: run_id, step_id, context_version, state_version, brief_sha256,
harness_style, state, persistent_library_items_added, packet_content_sha256
and files, a map from a workspace-relative path to its sha256 and size_bytes.
Two differences from that renderer are accepted: a path may hold folders,
because these packets live under .baltor/step/, and any short harness style
name is read. contracts/packet-manifest.schema.json describes the fields.

Failure codes (exit 1):
  file_missing             a listed file is absent, a link or not a regular file
  size_differs             a listed file has another size
  digest_differs           a listed file has other bytes
  file_too_large           a listed file is above the byte limit, so it was not read
  content_digest_differs   packet_content_sha256 does not match the listed files
  not_the_expected_packet  the digest the host gave outside the packet does not match
  task_not_listed          the manifest lists no task.json
  task_unreadable          the listed task.json is not a JSON object with a node_id
  step_id_differs          the manifest step_id is not the node_id in task.json
  unlisted_file            the packet folder holds a file the manifest does not list

The check judges identity only. Whether the packet is complete and ready is
a separate readiness check. A manifest can be rewritten together with the
files, so a packet is bound to the host only when the host digest is given
with --expect-content-sha256.

Exit status: 0 pass, 1 a check failed, 2 the manifest is missing or refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

MANIFEST_DEFAULT = ".baltor/step/packet-manifest.json"
MANIFEST_TYPE = "focused_step_packet_candidate/v1"
MANIFEST_FIELDS = {"record_type", "run_id", "step_id", "context_version", "state_version", "brief_sha256",
                   "harness_style", "state", "persistent_library_items_added", "packet_content_sha256", "files"}
ROOT_VARIABLES = ("GEMINI_PROJECT_DIR", "CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_MANIFEST_BYTES = 256 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_FILES = 64
MAX_TEXT = 200
MAX_UNLISTED = 50
MAX_SCANNED = 2000


class Refused(Exception):
    """A manifest or argument this check will not judge. The code is a fixed word."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def strict_json(data: bytes):
    """Parse UTF-8 JSON, refusing duplicate keys and NaN or Infinity."""

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise Refused("duplicate_key", str(key)[:80])
            seen[key] = value
        return seen

    def constant(name):
        raise Refused("nonstandard_number", name)

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError:
        raise Refused("not_utf8") from None
    except json.JSONDecodeError as error:
        raise Refused("invalid_json", f"line {error.lineno}") from None
    except RecursionError:
        raise Refused("too_deep") from None


def workspace_root(explicit) -> Path:
    """The --root argument, else the first harness project variable that is set, else the current folder."""
    if explicit:
        return Path(explicit).resolve()
    for name in ROOT_VARIABLES:
        value = os.environ.get(name, "")
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def safe_relative(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT or value.startswith("/"):
        return False
    if "\\" in value or any(ord(character) < 32 for character in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def inside(root: Path, relative: str) -> Path | None:
    """The joined path, or None when a link would lead it outside the root."""
    base = root.resolve()
    candidate = base.joinpath(*relative.split("/"))
    resolved = candidate.resolve()
    return candidate if resolved == base or base in resolved.parents else None


def short_text(value) -> bool:
    return isinstance(value, str) and 0 < len(value) <= MAX_TEXT and not any(ord(c) < 32 for c in value)


def whole(value, low: int) -> bool:
    return type(value) is int and value >= low


def content_digest(files: dict) -> str:
    """SHA-256 of the file map as canonical JSON: sorted keys, no spaces, UTF-8."""
    text = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_manifest_shape(manifest) -> dict:
    """Refuse a manifest whose fields this check cannot trust; return the file map."""
    if not isinstance(manifest, dict) or manifest.get("record_type") != MANIFEST_TYPE:
        raise Refused("unsupported_manifest_record_type")
    if set(manifest) != MANIFEST_FIELDS:
        missing, extra = sorted(MANIFEST_FIELDS - set(manifest)), sorted(set(manifest) - MANIFEST_FIELDS)
        raise Refused("manifest_fields_differ", f"missing {missing}, extra {extra}")
    for name in ("run_id", "step_id", "harness_style", "state"):
        if not short_text(manifest[name]):
            raise Refused("manifest_value_invalid", name)
    for name, low in (("context_version", 1), ("state_version", 1), ("persistent_library_items_added", 0)):
        if not whole(manifest[name], low):
            raise Refused("manifest_value_invalid", name)
    for name in ("brief_sha256", "packet_content_sha256"):
        if not isinstance(manifest[name], str) or not DIGEST.match(manifest[name]):
            raise Refused("manifest_value_invalid", name)
    files = manifest["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise Refused("manifest_files_invalid", f"a map of 1 to {MAX_FILES} files")
    for name, row in files.items():
        if not safe_relative(name):
            raise Refused("manifest_path_unsafe", str(name)[:120])
        if not isinstance(row, dict) or set(row) != {"sha256", "size_bytes"} or not isinstance(row["sha256"], str) \
                or not DIGEST.match(row["sha256"]) or not whole(row["size_bytes"], 0):
            raise Refused("manifest_row_invalid", name[:120])
    return files


def load_manifest(root: Path, relative: str) -> dict:
    if not safe_relative(relative):
        raise Refused("manifest_path_unsafe", str(relative)[:120])
    path = inside(root, relative)
    if path is None:
        raise Refused("manifest_path_leaves_root", relative)
    if path.is_symlink() or not path.is_file():
        raise Refused("manifest_missing", relative)
    with open(path, "rb") as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        raise Refused("manifest_too_large")
    return strict_json(data)


def unlisted_files(root: Path, manifest_relative: str, files: dict) -> tuple[list[str], bool]:
    """Files in the manifest's folder that the manifest does not list. Links are listed, never followed."""
    folder_relative = manifest_relative.rsplit("/", 1)[0] if "/" in manifest_relative else ""
    folder = inside(root, folder_relative) if folder_relative else root.resolve()
    if folder is None or not folder.is_dir():
        return [], False
    base = root.resolve()
    found, scanned, truncated = [], 0, False
    for current, directories, names in os.walk(folder):  # links to folders are not followed
        directories.sort()
        for name in sorted(names) + [entry for entry in directories if (Path(current) / entry).is_symlink()]:
            scanned += 1
            if scanned > MAX_SCANNED:
                return found, True
            relative = (Path(current) / name).relative_to(base).as_posix()
            if relative != manifest_relative and relative not in files:
                if len(found) < MAX_UNLISTED:
                    found.append(relative)
                else:
                    truncated = True
    return found, truncated


def read_task_node_id(path: Path) -> str | None:
    try:
        with open(path, "rb") as stream:
            task = strict_json(stream.read(MAX_FILE_BYTES))
    except (Refused, OSError):
        return None
    node = task.get("node_id") if isinstance(task, dict) else None
    return node if isinstance(node, str) and node else None


def verify(root: Path, manifest, expected: str | None = None, manifest_relative: str = MANIFEST_DEFAULT) -> dict:
    """Check one parsed manifest against the packet under root. Raises Refused for an unusable manifest."""
    files = check_manifest_shape(manifest)
    if expected is not None and not DIGEST.match(expected):
        raise Refused("expected_digest_invalid")
    failures, total, task_paths = [], 0, []

    def fail(code: str, path: str = "", detail: str = "") -> None:
        failures.append({"code": code, "path": path, "detail": detail})

    for name, row in sorted(files.items()):
        path = inside(root, name)
        if path is None or path.is_symlink() or not path.is_file():
            fail("file_missing", name, "the path leaves the root" if path is None else "")
            continue
        size = path.stat().st_size
        if size != row["size_bytes"]:
            fail("size_differs", name, f"{size} bytes, manifest {row['size_bytes']}")
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            fail("file_too_large", name, f"limit {MAX_FILE_BYTES} bytes per file, {MAX_TOTAL_BYTES} in total")
            continue
        total += size
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            digest.update(stream.read(MAX_FILE_BYTES + 1))
        if digest.hexdigest() != row["sha256"]:
            fail("digest_differs", name)
        if name.rsplit("/", 1)[-1] == "task.json":
            task_paths.append((name, path))
    if not task_paths:
        fail("task_not_listed", "", "the manifest lists no task.json")
    else:
        name, path = task_paths[0]
        node_id = read_task_node_id(path)
        if node_id is None:
            fail("task_unreadable", name, "not a JSON object with a node_id")
        elif node_id != manifest["step_id"]:
            fail("step_id_differs", name, "the manifest step_id is not the task node_id")
    computed = content_digest(files)
    if manifest["packet_content_sha256"] != computed:
        fail("content_digest_differs", manifest_relative)
    if expected is not None and expected != computed:
        fail("not_the_expected_packet", manifest_relative, "the host digest does not match this packet")
    unlisted, truncated = unlisted_files(root, manifest_relative, files)
    for name in unlisted:
        fail("unlisted_file", name)
    return {"check": "step_packet", "passed": not failures, "manifest": manifest_relative,
            "step_id": manifest["step_id"], "run_id": manifest["run_id"], "files_checked": len(files),
            "packet_content_sha256": computed, "bound_to_host_digest": expected is not None,
            "failures": failures, "unlisted_scan_truncated": truncated}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a focused step packet against its manifest before work starts.")
    parser.add_argument("--root", help="workspace root; default GEMINI_PROJECT_DIR, CURSOR_PROJECT_DIR, "
                                       "CLAUDE_PROJECT_DIR or the current folder")
    parser.add_argument("--manifest", default=MANIFEST_DEFAULT, help="manifest path relative to the root")
    parser.add_argument("--expect-content-sha256", dest="expected",
                        help="the packet digest the host gave in the first message, outside the packet")
    options = parser.parse_args(argv)
    root = workspace_root(options.root)
    try:
        report = verify(root, load_manifest(root, options.manifest), options.expected, options.manifest)
    except Refused as error:
        print(json.dumps({"check": "step_packet", "passed": False, "error": error.code, "detail": error.detail}))
        return 2
    except OSError as error:
        print(json.dumps({"check": "step_packet", "passed": False, "error": "os_error",
                          "detail": type(error).__name__}))
        return 2
    print(json.dumps(report, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

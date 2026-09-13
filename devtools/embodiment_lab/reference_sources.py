"""Immutable reference-source archives with exact provenance and safe preparation.

Archives are research inputs, not imports, runtime registrations, or executable
authority. Dirty work and runtime records are excluded rather than adopted.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from .storage import confined_root, write_new

EXCLUDED_PARTS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "artifacts",
        "runs",
        "compare",
        "bench",
        "outbox",
        ".overnight",
        ".opencode-data",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".cache",
    }
)
EXCLUDED_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".pyc", ".pkl", ".pickle", ".joblib")
MAX_SOURCE_BYTES = 100 * 1024 * 1024

# Git's own tree-entry vocabulary: the object kind and the two regular-file modes.
GIT_BLOB = "blob"
GIT_REGULAR_FILE_MODES = frozenset({"100644", "100755"})


def included(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and "\\" not in name
        and ":" not in name
        and ".." not in path.parts
        and not set(path.parts) & EXCLUDED_PARTS
        and not path.name.startswith(".env")
        and not path.name.endswith(EXCLUDED_SUFFIXES)
        and path.name not in {"credentials.json", "auth.json", "id_rsa", "id_ed25519"}
    )


def snapshot(source: Path, destination: Path) -> dict:
    """Archive committed regular files, or regular Markdown for a notes source."""
    source = confined_root(source, create=False)
    destination = confined_root(destination, create=True)
    git = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    committed = git.returncode == 0 and Path(git.stdout.strip()) == source
    files, exclusions, revision, dirty = [], [], None, ""
    if committed:
        revision = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(source), "status", "--short"], text=True
        )
        tree = subprocess.check_output(
            ["git", "-C", str(source), "ls-tree", "-r", "-l", "-z", revision]
        )
        selected, total_size = [], 0
        for item in tree.split(b"\0"):
            if not item:
                continue
            metadata, raw_name = item.split(b"\t", 1)
            mode, kind, object_id, size_text = metadata.decode().split()
            name = raw_name.decode("utf8")
            if kind != GIT_BLOB or mode not in GIT_REGULAR_FILE_MODES or not included(name):
                exclusions.append(name)
                continue
            size = int(size_text)
            total_size += size
            if total_size > MAX_SOURCE_BYTES:
                raise ValueError("source exceeds reference archive limit")
            selected.append((name, object_id, size, int(mode, 8) & 0o777))
        # One bounded Git batch instead of a process per source file.
        objects = subprocess.check_output(
            ["git", "-C", str(source), "cat-file", "--batch"],
            input="".join(row[1] + "\n" for row in selected).encode(),
        )
        position = 0
        for name, object_id, size, mode in selected:
            end = objects.index(b"\n", position)
            if objects[position:end].decode().split() != [object_id, "blob", str(size)]:
                raise ValueError("Git source object binding mismatch")
            body = objects[end + 1 : end + 1 + size]
            if objects[end + 1 + size : end + 2 + size] != b"\n":
                raise ValueError("Git source object framing mismatch")
            position = end + 2 + size
            files.append((name, body, mode))
    else:
        for path in sorted(source.glob("*.md")):
            if path.is_file() and not path.is_symlink() and included(path.name):
                files.append((path.name, path.read_bytes(), 0o644))
    total = sum(len(body) for _, body, _ in files)
    if not files or total > MAX_SOURCE_BYTES:
        raise ValueError("source is empty or exceeds reference archive limit")
    archive_path = destination / "source.tar.gz"
    archive_fd = os.open(archive_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with (
        os.fdopen(archive_fd, "wb") as stream,
        tarfile.open(fileobj=stream, mode="w:gz") as archive,
    ):
        for name, body, mode in files:
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(body), mode, 0
            archive.addfile(member, io.BytesIO(body))
    manifest = {
        "record_type": "embodiment_reference_source/v1",
        "source": str(source),
        "revision": revision,
        "source_kind": "committed_git_snapshot"
        if committed
        else "markdown_reference_collection",
        "dirty_state_at_snapshot": dirty,
        "dirty_work_included": False,
        "archive": "source.tar.gz",
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "files": [
            {
                "path": name,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
            for name, body, _ in files
        ],
        "excluded": exclusions,
        "uncompressed_bytes": total,
        "execution_qualified": False,
        "runtime_registration": False,
    }
    write_new(destination / "provenance.json", manifest)
    return manifest


def prepare(reference: Path, destination: Path) -> dict:
    """Validate every member before extracting into a new private workspace."""
    repository = Path(__file__).resolve().parents[2]
    if destination.absolute().is_relative_to(repository):
        raise ValueError(
            "prepare reference workspaces outside Loop Engine; frozen archives stay in embodiments/mirrors"
        )
    reference = confined_root(reference, create=False)
    manifest = json.loads((reference / "provenance.json").read_text())
    if (
        manifest.get("record_type") != "embodiment_reference_source/v1"
        or manifest.get("archive") != "source.tar.gz"
    ):
        raise ValueError("invalid reference manifest")
    archive_path = reference / "source.tar.gz"
    if archive_path.is_symlink():
        raise ValueError("archive symlink refused")
    if archive_path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("compressed archive limit exceeded")
    data = archive_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("reference archive drift")
    expected = {row["path"]: row for row in manifest["files"]}
    if len(expected) != len(manifest["files"]):
        raise ValueError("duplicate manifest identity")
    validated, seen, total = [], set(), 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            if (
                not member.isfile()
                or not included(member.name)
                or member.name not in expected
                or member.name in seen
            ):
                raise ValueError("unsafe or unexpected archive member")
            total += member.size
            if total > MAX_SOURCE_BYTES:
                raise ValueError("archive expansion limit exceeded")
            body = archive.extractfile(member).read()
            row = expected[member.name]
            if (
                len(body) != row["bytes"]
                or hashlib.sha256(body).hexdigest() != row["sha256"]
            ):
                raise ValueError("reference member digest mismatch")
            seen.add(member.name)
            validated.append((member, body))
    if seen != set(expected):
        raise ValueError("reference member missing")
    if any(
        str(parent) in seen
        for name in seen
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    ):
        raise ValueError("file/directory collision in reference archive")
    destination = confined_root(destination, create=True)
    for member, body in validated:
        path = destination / member.name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o700 if member.mode & 0o111 else 0o600,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
    return {
        "status": "prepared_unqualified_reference",
        "directory": str(destination),
        "files": len(validated),
        "revision": manifest["revision"],
        "executed": False,
    }

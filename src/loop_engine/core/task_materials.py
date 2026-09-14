"""Task materials: supplied archives unpacked into one run's materials folder.

A person handed a project unpacks its archives before starting work. This
module does the same for one Practitioner run. It finds archives among the
supplied sources by their content, not their names, and unpacks each one into
the run's materials folder beside its workspace. The run's source inventory
then walks that folder, so a text file inside an archive is inspected,
profiled, selected, and delivered to a project like any other supplied file.
Archives found inside unpacked material are unpacked in turn.

Unpacking is a write, so it needs the run's declared workspace write
authority. It is bounded by what this machine can later deliver to a project,
measured now. It refuses entries that would leave their folder, links, and
devices, and it skips an archive whose exact bytes were already unpacked. What
it unpacks and what it refuses are both recorded. It reads no body into a model
context and grants no authority.
"""
from __future__ import annotations

import bz2
import gzip
import hashlib
import lzma
import os
import stat
import tarfile
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .adaptive_practitioner_source import (
    SECRET_FILE_SUFFIXES, _IGNORED_SOURCE_DIRECTORIES, _PROTECTED_SOURCE_NAMES,
    _open_source)
from .capability_rejection import ADMITTED_VALUES_LIMIT
from .runtime_capacity import supplied_input_ceiling

TASK_MATERIALS_RECORD = "task_materials/v1"

#: The folder inside a run's materials root that holds unpacked archives. It is
#: the first component of every unpacked path the source inventory reports, so
#: a reader can tell unpacked material from an original source.
ARCHIVE_CONTENTS_FOLDER = "archive-contents"

#: Appended to an archive's path to name the folder its entries unpack into,
#: so an archive file and its unpacked entries never share one path.
UNPACKED_FOLDER_SUFFIX = ".unpacked"

#: Entry and archive dispositions recorded for every observation.
UNPACKED = "unpacked"
NOT_UNPACKED = "not_unpacked"

#: Why an entry or an archive was not unpacked.
UNSAFE_ENTRY_PATH = "unsafe_entry_path"
LINK_OR_DEVICE_ENTRY = "link_or_device_entry"
ENTRY_CONFLICT = "entry_conflict"
UNREADABLE_ENTRY = "unreadable_entry"
CAPACITY_EXCEEDED = "capacity_exceeded"
REPEATED_ARCHIVE = "repeated_archive"
UNREADABLE_ARCHIVE = "unreadable_archive"
WRITE_AUTHORITY_ABSENT = "workspace_write_authority_absent"

_HEADER_BYTES = 512
_STREAM_CHUNK_BYTES = 1 << 20
_DECOMPRESSION_ERRORS = (
    OSError, EOFError, RuntimeError, ValueError, zipfile.BadZipFile,
    tarfile.TarError, lzma.LZMAError, zlib.error)


@dataclass(frozen=True)
class ArchiveKind:
    """How one archive format is recognized from its first bytes."""

    name: str
    magic: tuple[bytes, ...]
    offset: int = 0


ZIP_ARCHIVE = ArchiveKind("zip", (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
TAR_ARCHIVE = ArchiveKind("tar", (b"ustar",), 257)
GZIP_STREAM = ArchiveKind("gzip", (b"\x1f\x8b",))
BZIP2_STREAM = ArchiveKind("bzip2", (b"BZh",))
XZ_STREAM = ArchiveKind("xz", (b"\xfd7zXZ\x00",))
ARCHIVE_KINDS = (ZIP_ARCHIVE, TAR_ARCHIVE, GZIP_STREAM, BZIP2_STREAM, XZ_STREAM)

#: Readers for a single compressed file that is not a tar archive, with the
#: suffixes removed to name the decompressed file.
_STREAM_READERS = {
    GZIP_STREAM: (lambda stream: gzip.GzipFile(fileobj=stream, mode="rb"),
                  (".gz", ".gzip")),
    BZIP2_STREAM: (bz2.BZ2File, (".bz2",)),
    XZ_STREAM: (lzma.LZMAFile, (".xz",)),
}


@dataclass(frozen=True)
class TaskMaterialsRequest:
    """Where the supplied sources are, where materials go, and the authority.

    ``byte_ceiling`` of None measures this machine; a caller may declare a
    smaller ceiling, which is recorded as declared rather than measured.
    """

    source_refs: tuple[str, ...]
    materials_root: Path
    write_allowed: bool
    byte_ceiling: "int | None" = None


@dataclass(frozen=True)
class TaskMaterials:
    """Inventory roots for unpacked material and the complete record."""

    roots: tuple[str, ...]
    record: dict


class _CapacityExceeded(Exception):
    """One more chunk would pass the unpacking ceiling."""


@dataclass
class _Budget:
    """Bytes this run may still unpack, or None when nothing was measured."""

    remaining: "int | None"

    def admits(self, size: int) -> bool:
        return self.remaining is None or size <= self.remaining

    def spend(self, size: int) -> None:
        if self.remaining is not None:
            self.remaining -= size


def archive_kind(path: Path) -> "ArchiveKind | None":
    """The archive format a file's first bytes show, or None."""
    try:
        with os.fdopen(_open_source(path), "rb") as stream:
            header = stream.read(_HEADER_BYTES)
    except OSError:
        return None
    for kind in ARCHIVE_KINDS:
        window = header[kind.offset:]
        if any(window.startswith(magic) for magic in kind.magic):
            return kind
    return None


def gather_task_materials(request: TaskMaterialsRequest) -> TaskMaterials:
    """Unpack every supplied archive, and each archive found inside one."""
    root = Path(request.materials_root).expanduser().resolve()
    found = [(relative, path, kind)
             for source_ref in request.source_refs
             for relative, path in _supplied_files(source_ref)
             for kind in (archive_kind(path),) if kind is not None]
    record = {"record_type": TASK_MATERIALS_RECORD,
              "materials_root": str(root),
              "write_authority": request.write_allowed, "archives": [],
              "unpacked_files": 0, "unpacked_bytes": 0}
    if not found:
        return TaskMaterials((), record)
    if not request.write_allowed:
        record["archives"] = [{
            "source_path": relative, "format": kind.name,
            "disposition": NOT_UNPACKED, "reason": WRITE_AUTHORITY_ABSENT}
            for relative, _path, kind in found]
        return TaskMaterials((), record)
    if request.byte_ceiling is None:
        measured = supplied_input_ceiling(root.parent)
        budget, record["byte_ceiling"] = _Budget(measured["bytes"]), measured
    else:
        budget = _Budget(request.byte_ceiling)
        record["byte_ceiling"] = {"bytes": request.byte_ceiling,
                                  "basis": "declared by the caller"}
    contents = root / ARCHIVE_CONTENTS_FOLDER
    contents.mkdir(parents=True, exist_ok=True)
    seen: dict[str, str] = {}
    queue = list(found)
    while queue:
        relative, path, kind = queue.pop(0)
        observed = {"source_path": relative, "format": kind.name}
        try:
            observed["digest"] = _digest(path)
        except OSError as exc:
            record["archives"].append({
                **observed, "disposition": NOT_UNPACKED,
                "reason": UNREADABLE_ARCHIVE, "error_type": type(exc).__name__})
            continue
        if observed["digest"] in seen:
            record["archives"].append({
                **observed, "disposition": NOT_UNPACKED,
                "reason": REPEATED_ARCHIVE,
                "same_as": seen[observed["digest"]]})
            continue
        seen[observed["digest"]] = relative
        folder = relative + UNPACKED_FOLDER_SUFFIX
        destination = contents.joinpath(*PurePosixPath(folder).parts)
        try:
            destination.mkdir(parents=True, exist_ok=True)
            entries = _unpack(path, kind, destination, budget)
        except _DECOMPRESSION_ERRORS as exc:
            record["archives"].append({
                **observed, "disposition": NOT_UNPACKED,
                "reason": UNREADABLE_ARCHIVE, "error_type": type(exc).__name__})
            continue
        unpacked = [item for item in entries
                    if item["disposition"] == UNPACKED]
        refused = [item for item in entries
                   if item["disposition"] != UNPACKED]
        unpacked_bytes = sum(item["byte_count"] for item in unpacked)
        record["archives"].append({
            **observed, "disposition": UNPACKED,
            "unpacked_folder": f"{ARCHIVE_CONTENTS_FOLDER}/{folder}",
            "unpacked_files": len(unpacked), "unpacked_bytes": unpacked_bytes,
            "refused_entry_count": len(refused),
            "refused_entries": refused[:ADMITTED_VALUES_LIMIT]})
        record["unpacked_files"] += len(unpacked)
        record["unpacked_bytes"] += unpacked_bytes
        for item in unpacked:
            nested = destination.joinpath(*PurePosixPath(item["path"]).parts)
            nested_kind = archive_kind(nested)
            if nested_kind is not None:
                queue.append((f"{folder}/{item['path']}", nested, nested_kind))
    roots = (str(contents),) if record["unpacked_files"] else ()
    return TaskMaterials(roots, record)


def gather_run_materials(services, owner, runs_dir) -> None:
    """Gather one run's task materials and record them on the owning Loop."""
    request = services.request
    try:
        materials = gather_task_materials(TaskMaterialsRequest(
            tuple(request.source_refs),
            Path(runs_dir) / f"{services.run_id}-materials",
            request.allow_workspace_writes is True))
    except (OSError, ValueError, RuntimeError) as exc:
        # Unpacking is a convenience the run can work without; a failure is
        # recorded and the run continues with the sources as supplied.
        services.task_materials = {
            "record_type": TASK_MATERIALS_RECORD,
            "error_type": type(exc).__name__, "error": str(exc)[:300]}
        owner.ledger.record(loop_id=owner.loop_id, event="custom",
                            custom_kind="task_materials_unavailable",
                            error_type=type(exc).__name__)
        return
    services.task_material_roots = materials.roots
    services.task_materials = materials.record
    if materials.record["archives"]:
        owner.ledger.record(
            loop_id=owner.loop_id, event="custom",
            custom_kind="task_materials_gathered",
            archives=len(materials.record["archives"]),
            unpacked_files=materials.record["unpacked_files"],
            unpacked_bytes=materials.record["unpacked_bytes"],
            write_authority=materials.record["write_authority"])


def _supplied_files(source_ref: str) -> list:
    """Regular supplied files as (inventory-relative path, absolute path)."""
    source = Path(source_ref).expanduser()
    if source.is_symlink() or not source.exists():
        return []
    source = source.resolve()
    if source.is_file():
        return [(source.name, source)]
    files = []
    for directory, folders, names in os.walk(source, followlinks=False):
        folders[:] = sorted(
            name for name in folders
            if name not in _IGNORED_SOURCE_DIRECTORIES
            and not name.startswith(".")
            and name.casefold() not in _PROTECTED_SOURCE_NAMES)
        for name in sorted(names):
            path = Path(directory) / name
            if (name.startswith(".") or path.is_symlink()
                    or name.casefold() in _PROTECTED_SOURCE_NAMES
                    or path.suffix.casefold() in SECRET_FILE_SUFFIXES):
                continue
            files.append(((Path(source.name) / path.relative_to(source))
                          .as_posix(), path))
    return files


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with os.fdopen(_open_source(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(_STREAM_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unpack(archive: Path, kind: ArchiveKind, destination: Path,
            budget: _Budget) -> list[dict]:
    """Unpack one archive into ``destination``; one record per entry."""
    with os.fdopen(_open_source(archive), "rb") as stream:
        if kind is ZIP_ARCHIVE:
            return _unpack_zip(stream, destination, budget)
        if kind is TAR_ARCHIVE or _is_compressed_tar(stream):
            return _unpack_tar(stream, destination, budget)
        return _unpack_stream(stream, kind, archive.name, destination, budget)


def _is_compressed_tar(stream) -> bool:
    try:
        with tarfile.open(fileobj=stream, mode="r:*") as archive:
            return archive.next() is not None
    except _DECOMPRESSION_ERRORS:
        return False
    finally:
        stream.seek(0)


def _unpack_zip(stream, destination: Path, budget: _Budget) -> list[dict]:
    entries = []
    with zipfile.ZipFile(stream) as archive:
        for info in archive.infolist():
            relative = _safe_entry_path(info.filename)
            file_type = stat.S_IFMT(info.external_attr >> 16)
            if relative is None:
                entries.append(_refused(info.filename, UNSAFE_ENTRY_PATH))
            elif info.is_dir():
                continue
            elif file_type and file_type != stat.S_IFREG:
                entries.append(_refused(info.filename, LINK_OR_DEVICE_ENTRY))
            else:
                entries.append(_extract(
                    destination, relative, lambda: archive.open(info), budget,
                    info.file_size))
    return entries


def _unpack_tar(stream, destination: Path, budget: _Budget) -> list[dict]:
    entries = []
    with tarfile.open(fileobj=stream, mode="r:*") as archive:
        for member in archive:
            relative = _safe_entry_path(member.name)
            if relative is None:
                entries.append(_refused(member.name, UNSAFE_ENTRY_PATH))
            elif member.isdir():
                continue
            elif not member.isreg():
                entries.append(_refused(member.name, LINK_OR_DEVICE_ENTRY))
            else:
                entries.append(_extract(
                    destination, relative,
                    lambda: archive.extractfile(member), budget, member.size))
    return entries


def _unpack_stream(stream, kind: ArchiveKind, archive_name: str,
                   destination: Path, budget: _Budget) -> list[dict]:
    reader, suffixes = _STREAM_READERS[kind]
    stem = next((archive_name[:-len(suffix)] for suffix in suffixes
                 if archive_name.casefold().endswith(suffix)
                 and len(archive_name) > len(suffix)),
                archive_name + ".decompressed")
    relative = _safe_entry_path(stem)
    if relative is None:
        return [_refused(stem, UNSAFE_ENTRY_PATH)]
    return [_extract(destination, relative, lambda: reader(stream), budget,
                     None)]


def _safe_entry_path(name: str) -> "PurePosixPath | None":
    """The entry's path inside its folder, or None when it could escape."""
    if not name or "\\" in name or "\x00" in name:
        return None
    candidate = PurePosixPath(name)
    if (candidate.is_absolute() or not candidate.parts
            or any(part == ".." for part in candidate.parts)
            or ":" in candidate.parts[0]):
        return None
    return candidate


def _refused(name: str, reason: str, byte_count: "int | None" = None) -> dict:
    return {"path": name, "disposition": NOT_UNPACKED, "reason": reason,
            "byte_count": byte_count}


def _extract(destination: Path, relative: PurePosixPath, opener,
             budget: _Budget, declared_size: "int | None") -> dict:
    name = relative.as_posix()
    if declared_size is not None and not budget.admits(declared_size):
        return _refused(name, CAPACITY_EXCEEDED, declared_size)
    try:
        with opener() as source:
            written = _write_entry(destination, relative, source, budget)
    except _CapacityExceeded:
        return _refused(name, CAPACITY_EXCEEDED, declared_size)
    except (FileExistsError, NotADirectoryError, IsADirectoryError):
        return _refused(name, ENTRY_CONFLICT, declared_size)
    except _DECOMPRESSION_ERRORS:
        return _refused(name, UNREADABLE_ENTRY, declared_size)
    return {"path": name, "disposition": UNPACKED, "byte_count": written}


def _write_entry(root: Path, relative: PurePosixPath, source,
                 budget: _Budget) -> int:
    """Stream one entry to a new file inside ``root``; return its size."""
    target = root.joinpath(*relative.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    real_root = os.path.realpath(root)
    if os.path.commonpath([real_root, os.path.realpath(target.parent)]) != real_root:
        raise NotADirectoryError("entry folder left the unpacked folder")
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    written = 0
    try:
        with os.fdopen(descriptor, "wb") as output:
            while True:
                chunk = source.read(_STREAM_CHUNK_BYTES)
                if not chunk:
                    return written
                if not budget.admits(len(chunk)):
                    raise _CapacityExceeded()
                output.write(chunk)
                budget.spend(len(chunk))
                written += len(chunk)
    except BaseException:
        # A partial file is removed and its bytes return to the budget.
        budget.spend(-written)
        target.unlink(missing_ok=True)
        raise


def self_test() -> dict:
    """Unpack adversarial fixtures and prove the inventory sees the result."""
    import io
    import tempfile
    from types import SimpleNamespace

    from .adaptive_practitioner_source import inspectable_source_files

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def zip_bytes(members) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for info, body in members:
                archive.writestr(info, body)
        return buffer.getvalue()

    inner = zip_bytes([(zipfile.ZipInfo("deep.txt"), "nested text\n")])
    link = zipfile.ZipInfo("link")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    outer = zip_bytes([
        (zipfile.ZipInfo("table.csv"), "a,b\n1,2\n"),
        (zipfile.ZipInfo("nested/inner.zip"), inner),
        (zipfile.ZipInfo("../escape.txt"), "escaped\n"),
        (zipfile.ZipInfo("/absolute.txt"), "absolute\n"),
        (link, "table.csv")])
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        supplied = base / "supplied"
        supplied.mkdir()
        (supplied / "data.zip").write_bytes(outer)
        # Named to sort after data.zip, so data.zip is the one unpacked first.
        (supplied / "zcopy.zip").write_bytes(outer)
        (supplied / "fake.zip").write_text("not an archive\n", encoding="utf-8")
        (supplied / "values.csv.gz").write_bytes(gzip.compress(b"x\n1\n"))
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            body = b"tar notes\n"
            member = tarfile.TarInfo("notes.txt")
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
            symbolic = tarfile.TarInfo("link")
            symbolic.type = tarfile.SYMTYPE
            symbolic.linkname = "notes.txt"
            archive.addfile(symbolic)
        (supplied / "bundle.tar.gz").write_bytes(buffer.getvalue())
        materials = gather_task_materials(TaskMaterialsRequest(
            (str(supplied),), base / "run-materials", True))
        contents = base / "run-materials" / ARCHIVE_CONTENTS_FOLDER
        by_source = {item["source_path"]: item
                     for item in materials.record["archives"]}
        data = by_source.get("supplied/data.zip", {})
        refused = {item["path"]: item["reason"]
                   for item in data.get("refused_entries", ())}
        check("supplied_zip_entries_unpack_into_the_materials_folder",
              (contents / "supplied/data.zip.unpacked/table.csv").read_text(
                  encoding="utf-8") == "a,b\n1,2\n", str(data))
        check("an_archive_inside_an_archive_is_unpacked_in_turn",
              (contents / "supplied/data.zip.unpacked/nested/inner.zip"
               ".unpacked/deep.txt").is_file())
        check("entries_that_would_leave_their_folder_are_refused",
              refused.get("../escape.txt") == UNSAFE_ENTRY_PATH
              and refused.get("/absolute.txt") == UNSAFE_ENTRY_PATH
              and not any(base.rglob("escape.txt"))
              and not any(base.rglob("absolute.txt")), str(refused))
        check("link_entries_are_refused_in_zip_and_tar_archives",
              refused.get("link") == LINK_OR_DEVICE_ENTRY
              and not (contents / "supplied/data.zip.unpacked/link").exists()
              and (contents / "supplied/bundle.tar.gz.unpacked/notes.txt"
                   ).read_bytes() == b"tar notes\n"
              and not os.path.lexists(
                  contents / "supplied/bundle.tar.gz.unpacked/link"),
              str(by_source.get("supplied/bundle.tar.gz")))
        check("identical_archive_bytes_are_unpacked_once",
              by_source.get("supplied/zcopy.zip", {}).get("reason")
              == REPEATED_ARCHIVE
              and by_source["supplied/zcopy.zip"].get("same_as")
              == "supplied/data.zip")
        check("a_single_compressed_file_is_decompressed",
              (contents / "supplied/values.csv.gz.unpacked/values.csv"
               ).read_bytes() == b"x\n1\n")
        check("archives_are_recognized_by_content_not_by_name",
              "supplied/fake.zip" not in by_source)
        services = SimpleNamespace(
            request=SimpleNamespace(
                source_refs=(str(supplied),),
                allow_source_materialization_to_model=True),
            task_material_roots=materials.roots)
        admitted = dict(inspectable_source_files(services))
        check("the_source_inventory_admits_text_from_unpacked_archives",
              "archive-contents/supplied/data.zip.unpacked/table.csv" in admitted
              and "archive-contents/supplied/bundle.tar.gz.unpacked/notes.txt"
              in admitted, str(sorted(admitted))[:400])
        refused_services = SimpleNamespace(
            request=services.request, task_material_roots=())
        check("without_unpacked_roots_the_inventory_sees_only_supplied_text",
              not any(path.startswith(ARCHIVE_CONTENTS_FOLDER)
                      for path in dict(inspectable_source_files(
                          refused_services))))
        from .adaptive_practitioner_project import _local_project_inputs
        selected = "archive-contents/supplied/data.zip.unpacked/table.csv"
        project_services = SimpleNamespace(
            request=SimpleNamespace(
                source_kind="dataset", source_refs=(str(supplied),),
                allow_source_materialization_to_model=True),
            task_material_roots=materials.roots,
            source_inspections=[{"source_manifest": [], "selected": [{
                "path": selected,
                "digest": hashlib.sha256(b"a,b\n1,2\n").hexdigest()}]}])
        delivered = {item.path: item.content
                     for item in _local_project_inputs(project_services)}
        check("a_selected_unpacked_file_is_delivered_to_the_project_inputs",
              delivered.get("inputs/" + selected) == b"a,b\n1,2\n",
              str(sorted(delivered))[:300])
        unauthorized = gather_task_materials(TaskMaterialsRequest(
            (str(supplied),), base / "unauthorized", False))
        check("unpacking_requires_declared_write_authority",
              unauthorized.roots == ()
              and not (base / "unauthorized").exists()
              and {item["reason"] for item in unauthorized.record["archives"]}
              == {WRITE_AUTHORITY_ABSENT})
        bounded = gather_task_materials(TaskMaterialsRequest(
            (str(supplied / "data.zip"),), base / "bounded", True,
            byte_ceiling=4))
        bounded_refused = {
            item["path"]: item["reason"]
            for archive in bounded.record["archives"]
            for item in archive.get("refused_entries", ())}
        check("unpacking_stops_at_the_byte_ceiling_and_removes_partial_files",
              bounded_refused.get("table.csv") == CAPACITY_EXCEEDED
              and not (base / "bounded" / ARCHIVE_CONTENTS_FOLDER
                       / "data.zip.unpacked/table.csv").exists(),
              str(bounded.record["archives"])[:400])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "task_materials_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}

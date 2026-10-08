"""Passive reading-profile files with canonical native package metadata and confined writes.

The writer creates only a new child folder under an explicit existing root.
Descriptor-relative, no-follow operations keep symlinks and path traversal
out of the write boundary. Existing folders and files are never overwritten.
"""
import hashlib
import json
import os
from pathlib import Path
import re

from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
from .feed_profiles import FeedProfileError, MAXIMUM_BYTES, build, instructions, read_profile, read_request, validate

PROFILE_FILE, GUIDE_FILE = "profile.json", "READING.md"
OUTPUT_FILES = (PROFILE_FILE, GUIDE_FILE)
_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def compile_files(request, directory=None):
    profile = build(request, directory)
    bodies = {PROFILE_FILE: (json.dumps(profile, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
              GUIDE_FILE: instructions(profile)}
    total = sum(map(len, bodies.values()))
    if total > request.max_bytes:raise FeedProfileError("feed_profile_bundle_byte_limit")
    entries = [CataloguePackageFile(name, hashlib.sha256(body).hexdigest(), len(body),
        "application/json" if name == PROFILE_FILE else "text/markdown",
        "configuration" if name == PROFILE_FILE else "instruction_file").to_dict() for name, body in bodies.items()]
    package = CataloguePackage.from_dict({"body_form": "package", "files": entries})
    return profile, bodies, {"package": package.to_dict(), "package_digest": package.package_digest,
                            "payload_files": len(bodies), "payload_bytes": total, "executable": package.executable,
                            "approved": False, "published": False}


def _open_directory(path):
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or os.open not in os.supports_dir_fd:
        raise FeedProfileError("feed_profile_posix_filesystem_required")
    absolute = Path(path).absolute()
    if ".." in absolute.parts:raise FeedProfileError("feed_profile_path_traversal")
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for segment in absolute.parts[1:]:
            next_descriptor = os.open(segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor);descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def write_new(root, name, bodies, *, authorized=False):
    if authorized is not True:raise PermissionError("local_write_grant_required")
    if type(name) is not str or not _NAME.fullmatch(name):raise FeedProfileError("feed_profile_folder_name_invalid")
    if set(bodies) != set(OUTPUT_FILES) or any(type(body) is not bytes for body in bodies.values()) or sum(map(len, bodies.values())) > MAXIMUM_BYTES:
        raise FeedProfileError("feed_profile_output_files_invalid")
    profile = read_profile(bodies[PROFILE_FILE])
    request = read_request(profile.get("request"))
    validate(profile, as_of=request.as_of)
    if sum(map(len, bodies.values())) > request.max_bytes:raise FeedProfileError("feed_profile_bundle_byte_limit")
    if bodies[GUIDE_FILE] != instructions(profile):raise FeedProfileError("feed_profile_instructions_changed")
    root = Path(root).absolute()
    if root in (Path(root.anchor), Path.home()):raise FeedProfileError("feed_profile_explicit_root_required")
    parent_fd = _open_directory(root)
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        output_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            for filename, body in bodies.items():
                fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=output_fd)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(body);stream.flush();os.fsync(stream.fileno())
            os.fsync(output_fd)
        finally:os.close(output_fd)
        os.fsync(parent_fd)
    finally:os.close(parent_fd)
    return root / name


def check_folder(folder, *, as_of, directory=None):
    descriptor = _open_directory(folder)
    try:
        names = set()
        with os.scandir(descriptor) as entries:
            for entry in entries:
                names.add(entry.name)
                if len(names) > len(OUTPUT_FILES):break
        if names != set(OUTPUT_FILES):raise FeedProfileError("feed_profile_unexpected_files")
        bodies = {}
        for filename in OUTPUT_FILES:
            fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            with os.fdopen(fd, "rb") as stream:
                import stat
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise FeedProfileError("feed_profile_file_not_regular")
                bodies[filename] = stream.read(MAXIMUM_BYTES + 1)
                if len(bodies[filename]) > MAXIMUM_BYTES:raise FeedProfileError("feed_profile_input_byte_limit")
        profile = read_profile(bodies[PROFILE_FILE])
        report = validate(profile, as_of=as_of, directory=directory)
        if sum(map(len, bodies.values())) > profile["request"]["max_bytes"]:
            raise FeedProfileError("feed_profile_bundle_byte_limit")
        if bodies[GUIDE_FILE] != instructions(profile):raise FeedProfileError("feed_profile_instructions_changed")
        return {**report, "payload_bytes": sum(map(len, bodies.values())), "profile_files_checked": list(OUTPUT_FILES)}
    finally:os.close(descriptor)

"""Open selected task material below an explicit root without following symlinks."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO


class ConfinedInputError(ValueError):
    """The requested input is outside the declared, no-follow read scope."""


def _flags(directory: bool) -> int:
    if (
        os.name != "posix"
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
    ):
        raise ConfinedInputError("no_follow_file_operations_unavailable")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    else:
        if not hasattr(os, "O_NONBLOCK"):
            raise ConfinedInputError("nonblocking_file_open_unavailable")
        flags |= os.O_NONBLOCK
    return flags


def relative_parts(
    relative: str | os.PathLike[str], *, allow_root: bool = False
) -> tuple[str, ...]:
    try:
        raw = os.fspath(relative)
    except TypeError:
        raise ConfinedInputError("input_path_must_be_relative") from None
    if raw == "." and allow_root:
        return ()
    if not isinstance(raw, str) or not raw or raw.startswith("/"):
        raise ConfinedInputError("input_path_must_be_relative")
    parts = tuple(raw.split("/"))
    if any(part in {"", ".", ".."} or "\x00" in part for part in parts):
        raise ConfinedInputError("input_path_contains_traversal_or_empty_component")
    return parts


def _root_parts(approved_root: str | os.PathLike[str]) -> tuple[str, ...]:
    try:
        raw = os.fspath(approved_root)
    except TypeError:
        raise ConfinedInputError("approved_root_must_be_absolute") from None
    if not isinstance(raw, str) or not raw.startswith("/"):
        raise ConfinedInputError("approved_root_must_be_absolute")
    parts = tuple(raw.split("/")[1:])
    if not parts or any(part in {"", ".", ".."} or "\x00" in part for part in parts):
        raise ConfinedInputError(
            "approved_root_must_be_a_normalized_directory_below_slash"
        )
    return parts


@contextmanager
def open_approved_directory(approved_root: str, relative: str = ".") -> Iterator[int]:
    parts = _root_parts(approved_root)
    children = relative_parts(relative, allow_root=True)
    flags = _flags(directory=True)
    opened: list[int] = []
    try:
        opened.append(os.open("/", flags))
        for part in (*parts, *children):
            opened.append(os.open(part, flags, dir_fd=opened[-1]))
    except OSError:
        for descriptor in reversed(opened):
            os.close(descriptor)
        raise ConfinedInputError("directory_missing_or_symlinked") from None
    try:
        yield opened[-1]
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


@contextmanager
def open_approved_file(approved_root: str, relative: str) -> Iterator[BinaryIO]:
    parts = relative_parts(relative)
    parent = "/".join(parts[:-1]) or "."
    with open_approved_directory(approved_root, parent) as directory:
        try:
            descriptor = os.open(parts[-1], _flags(directory=False), dir_fd=directory)
        except OSError:
            raise ConfinedInputError("file_missing_or_symlinked") from None
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ConfinedInputError("input_must_be_regular_file")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                yield handle
        finally:
            if descriptor != -1:
                os.close(descriptor)

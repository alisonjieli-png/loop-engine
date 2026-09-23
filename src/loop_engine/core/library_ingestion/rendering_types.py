"""The typed result of rendering one outside item into its native files.

A rendered package names its folder, its main file and every file with its
exact bytes, and lists each change rendering made to the source bytes, so a
reviewer can see that a body was kept byte for byte and what else moved.
A connection package also carries its generated document and its key.
RenderRefused carries a reason from the closed refusal vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .record_rules import bytes_digest

RENDERED_PACKAGE_RECORD_TYPE = "library_rendered_package/v1"


class RenderRefused(ValueError):
    """An item cannot be rendered into a valid native file; the code names why."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail or code


@dataclass(frozen=True)
class RenderedPackage:
    """One item as native files: the folder, the main file and every file's exact bytes."""

    folder: str
    main_path: str
    files: tuple
    changes: tuple = ()
    title: str = ""
    key: str = ""
    document: dict = field(default_factory=dict)

    @property
    def main_text(self) -> str:
        return dict(self.files)[self.main_path].decode("utf-8")

    def manifest(self) -> list:
        return [{"path": path, "sha256": bytes_digest(data), "size_bytes": len(data)}
                for path, data in self.files]

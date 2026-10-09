"""Media types of creative package files, and the suffixes the line refuses.

Qualification reads a file as text when its media type starts with ``text/`` or is in its text list, and refuses a
binary file it cannot verify. Every suffix here is therefore either a UTF-8 text format or a binary format with a
strict verifier (PNG, through pngio). Opaque binaries (.blend, .fbx, .exr, .jpg, audio) are refused by name: a
family ships the script that rebuilds them instead.
"""
from __future__ import annotations

from pathlib import PurePosixPath

from .records import CreativeRecordError

MEDIA_TYPES = {
    ".gd": "text/x-gdscript", ".gdshader": "text/x-gdshader", ".gdshaderinc": "text/x-gdshader",
    ".tscn": "text/x-godot-scene", ".tres": "text/x-godot-resource", ".godot": "text/x-godot-project",
    ".cfg": "text/plain", ".import": "text/plain", ".py": "text/x-python", ".md": "text/markdown",
    ".txt": "text/plain", ".json": "application/json", ".gltf": "model/gltf+json", ".obj": "model/obj",
    ".mtl": "model/mtl", ".svg": "image/svg+xml", ".png": "image/png", ".csv": "text/csv", ".toml": "application/toml",
    ".yaml": "application/yaml", ".yml": "application/yaml", ".xml": "application/xml", ".urdf": "application/xml",
    ".glsl": "text/x-glsl", ".wgsl": "text/x-wgsl", ".mjs": "text/javascript", ".js": "text/javascript",
    ".html": "text/html", ".css": "text/css", ".gpl": "text/x-gimp-palette", ".scad": "text/x-openscad",
    ".osl": "text/x-osl", ".ase": None, ".blend": None, ".fbx": None, ".exr": None, ".hdr": None, ".jpg": None,
    ".jpeg": None, ".webp": None, ".wav": None, ".ogg": None, ".mp3": None, ".glb": None, ".ttf": None, ".otf": None,
}
#: Binary media types that have a strict verifier in the line and in qualification.
VERIFIED_BINARY = ("image/png",)
#: Text media types that do not start with "text/"; qualification's text list must hold each of them.
TEXT_TYPES_OUTSIDE_TEXT_PREFIX = ("application/json", "model/gltf+json", "model/obj", "model/mtl", "image/svg+xml",
                                  "application/toml", "application/yaml", "application/xml")


def media_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    name = PurePosixPath(path).name
    if name in ("README", "LICENSE", "NOTICE") or not suffix:
        return "text/plain"
    value = MEDIA_TYPES.get(suffix)
    if value is None:
        raise CreativeRecordError("suffix_not_supported", f"{path}: ship text or a verified PNG, or the script that "
                                                          "writes the binary")
    return value


def refuse_unsupported(path: str) -> None:
    media_type(path)


def is_text(media: str) -> bool:
    return media.startswith("text/") or media in TEXT_TYPES_OUTSIDE_TEXT_PREFIX


__all__ = ["MEDIA_TYPES", "VERIFIED_BINARY", "TEXT_TYPES_OUTSIDE_TEXT_PREFIX", "media_type", "refuse_unsupported",
           "is_text"]

"""Bounded public-preview projection owned by the existing gallery.

The gallery's recorded renders are already approved for public display. Their
source-package licence does not establish separate preview reuse rights. Additional media needs
an explicit reviewed preview record tied to a public gallery item and its exact
version. Neither a source licence nor a paid body becomes public by inference.
This passive reader uses packaged files only, checks their bytes once, and
never opens a catalogue, account, provider or model connection.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
from importlib.resources import files
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import Path as ZipPath

from . import gallery_records as gallery

RECORD_TYPE = "website_gallery_media/v1"
FOLDER = "gallery-media"
PREFIX = "/assets/gallery-media/"
KINDS = ("image", "video", "music")
MAX_EXTRA_ITEMS = 64
MAX_RECORD_BYTES = 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
FORMATS = {
    "image/webp": ("image", "webp"), "image/png": ("image", "png"), "image/jpeg": ("image", "jpg"),
    "video/mp4": ("video", "mp4"), "video/webm": ("video", "webm"),
    "audio/mpeg": ("music", "mp3"), "audio/ogg": ("music", "ogg"), "audio/wav": ("music", "wav"),
}
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_FIELDS = {"id", "kind", "title", "summary", "source_slug", "source_version", "preview_licence",
           "provenance", "review", "preview"}


def _require(condition, reason):
    if not condition:
        raise gallery.GalleryRecordError(reason)


def _text(value, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def parse_media(text: str) -> dict:
    """Validate the closed companion record; approval remains a separate review."""
    _require(type(text) is str and len(text) <= MAX_RECORD_BYTES, "media record exceeds its byte bound")
    try:
        _require(len(text.encode("utf-8")) <= MAX_RECORD_BYTES, "media record exceeds its byte bound")
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                _require(key not in result, "duplicate media JSON field")
                result[key] = value
            return result
        def finite_json(_value):
            raise gallery.GalleryRecordError("non-finite media JSON number")
        value = json.loads(text, object_pairs_hook=unique_object, parse_constant=finite_json)
    except (UnicodeError, RecursionError, json.JSONDecodeError):
        raise gallery.GalleryRecordError("media record is not bounded UTF-8 JSON") from None
    _require(isinstance(value, dict) and set(value) == {"record_type", "items"}
             and value["record_type"] == RECORD_TYPE, f"this reader reads {RECORD_TYPE}")
    _require(isinstance(value["items"], list) and len(value["items"]) <= MAX_EXTRA_ITEMS, "too many media previews")
    seen = set()
    for item in value["items"]:
        _require(isinstance(item, dict) and set(item) == _FIELDS, "unknown or missing media fields")
        _require(_text(item["id"], 160) and _SLUG.fullmatch(item["id"]) and item["id"] not in seen,
                 "media identities must be unique slugs")
        seen.add(item["id"])
        _require(item["kind"] in KINDS, "unknown media kind")
        _require(_text(item["source_slug"], 160) and _SLUG.fullmatch(item["source_slug"])
                 and isinstance(item["source_version"], str) and _SHA.fullmatch(item["source_version"]),
                 "media must name an exact gallery source")
        _require(all(_text(item[key]) for key in ("title", "summary", "preview_licence", "provenance")),
                 "media descriptions, licence and provenance are required")
        review = item["review"]
        _require(isinstance(review, dict) and set(review) == {"status", "reference", "reviewer"}
                 and review["status"] in ("approved", "pending", "rejected")
                 and _text(review["reference"]) and _text(review["reviewer"]), "explicit preview review is required")
        preview = item["preview"]
        _require(isinstance(preview, dict) and set(preview) == {"file", "sha256", "bytes", "media_type",
                                                              "width", "height", "duration_seconds"},
                 "unknown or missing media preview fields")
        media_type = preview["media_type"]
        _require(isinstance(media_type, str) and media_type in FORMATS
                 and FORMATS[media_type][0] == item["kind"], "media kind and format must agree")
        extension = FORMATS[media_type][1]
        _require(isinstance(preview["sha256"], str) and _SHA.fullmatch(preview["sha256"])
                 and _text(preview["file"], 200)
                 and re.fullmatch(r"[a-z0-9-]+-" + preview["sha256"][:12] + r"\." + extension, preview["file"]),
                 "preview must have a safe content-addressed filename")
        _require(type(preview["bytes"]) is int and 0 < preview["bytes"] <= MAX_FILE_BYTES, "preview size exceeds its bound")
        if item["kind"] == "music":
            _require(preview["width"] is None and preview["height"] is None, "music has no pixel dimensions")
        else:
            _require(all(type(preview[key]) is int and 0 < preview[key] <= 8192 for key in ("width", "height")),
                     "image and video dimensions must be positive bounded integers")
        duration = preview["duration_seconds"]
        _require(duration is None if item["kind"] == "image" else
                 type(duration) in (int, float) and math.isfinite(duration) and 0 < duration <= 300,
                 "only audio and video have a positive duration, at most five minutes")
    _require(sum(item["preview"]["bytes"] for item in value["items"]) <= MAX_TOTAL_BYTES,
             "media preview inventory exceeds its byte bound")
    return value


@lru_cache(maxsize=1)
def media_record():
    try:
        return parse_media(_read_packaged(FOLDER + "/media.json", MAX_RECORD_BYTES).decode("utf-8"))
    except UnicodeError:
        raise gallery.GalleryRecordError("media record is not UTF-8") from None


def _plain_resource(resource):
    """Refuse aliases/special files without treating zip-backed resources as filesystem paths.

    Packaged releases are immutable during use; this is not a sandbox against
    a privileged concurrent writer changing the installed release's files.
    """
    if isinstance(resource, Path):
        try:
            plain = resource.resolve() == resource.absolute() and resource.is_file()
        except (OSError, RuntimeError):
            plain = False  # A broken or looping link is still not a packaged file.
        _require(plain, "media resource must be a plain packaged file")
    elif isinstance(resource, ZipPath):
        path = PurePosixPath(resource.at)
        _require(not path.is_absolute() and ".." not in path.parts and resource.is_file(),
                 "media resource must be a plain zip member")
        names = {str(path), *(str(parent) for parent in path.parents if str(parent) != ".")}
        seen = set()
        for entry in resource.root.infolist():
            name = entry.filename.rstrip("/")
            if name not in names:
                continue
            _require(name not in seen, "duplicate media zip member")
            seen.add(name)
            directory = name != str(path)
            kind = stat.S_IFMT(entry.external_attr >> 16)
            _require(entry.is_dir() == directory and kind in (0, stat.S_IFDIR if directory else stat.S_IFREG),
                     "media zip members must not be links or special files")
    else:
        raise gallery.GalleryRecordError("unsupported packaged media resource backend")


def _read_packaged(name, maximum):
    parts = name.split("/")
    _require(len(parts) == 2 and parts[0] in (FOLDER, gallery.RECORD_FOLDER)
             and re.fullmatch(r"[a-zA-Z0-9_.-]{1,200}", parts[1]) and parts[1] not in (".", ".."),
             "media reads stay in the declared packaged folders")
    resource = files("loop_engine").joinpath("core", "service_runtime", "web_assets", *parts)
    _plain_resource(resource)
    with resource.open("rb") as source:
        body = source.read(maximum + 1)
    _require(len(body) <= maximum, "packaged media resource exceeds its byte bound")
    return body


def _read_asset(name):
    return _read_packaged(name, MAX_FILE_BYTES)


def _matching_bytes(name, preview, reader):
    try:
        body = reader(name)
    except (OSError, gallery.GalleryRecordError):
        return False
    return len(body) == preview["bytes"] and hashlib.sha256(body).hexdigest() == preview["sha256"]


def project(value, extra, reader):
    """Pure projection with an injected bounded asset reader for offline controls.

    Missing, changed, unapproved or nonpublic records are excluded. An exact
    old selection therefore becomes unavailable; it never selects a new body.
    """
    _require(len(value["items"]) <= 1000, "random previews use a curated gallery, not a full catalogue scan")
    sources = {item["slug"]: item for item in value["items"] if item["tier"] in gallery.PUBLIC_TIERS}
    _require(sum((item.get("preview") or {}).get("bytes", 0) for item in sources.values())
             + sum(item["preview"]["bytes"] for item in extra["items"]) <= MAX_TOTAL_BYTES,
             "combined public preview inventory exceeds its byte bound")
    approved_gallery_assets = gallery.preview_assets(value)
    results = []
    for item in sources.values():
        preview = item.get("preview")
        if not preview or gallery.ASSET_PREFIX + preview["file"] not in approved_gallery_assets:
            continue
        if not _matching_bytes(gallery.RECORD_FOLDER + "/" + preview["file"], preview, reader):
            continue
        results.append({
            "id": item["slug"] + "-" + preview["sha256"][:12], "kind": "image", "title": item["title"],
            "summary": item["summary"], "url": gallery.ASSET_PREFIX + preview["file"], "media_type": "image/webp",
            "format": "WebP", "bytes": preview["bytes"], "width": preview["width"], "height": preview["height"],
            "duration_seconds": None, "sha256": preview["sha256"], "preview_licence": None,
            "source_licence": item["licence"], "source_page": "/gallery/" + item["slug"],
            "source_identity": item["identity"], "source_version": item["version"],
            "provenance": "Baltor native-check render, converted to WebP. Source PNG SHA-256: "
                          + preview["source_png_sha256"],
        })
    for item in extra["items"]:
        source = sources.get(item["source_slug"])
        if item["review"]["status"] != "approved" or source is None or source["version"] != item["source_version"]:
            continue
        preview = item["preview"]
        if not _matching_bytes(FOLDER + "/" + preview["file"], preview, reader):
            continue
        results.append({
            "id": item["id"] + "-" + preview["sha256"][:12], "kind": item["kind"], "title": item["title"],
            "summary": item["summary"], "url": PREFIX + preview["file"], "media_type": preview["media_type"],
            "format": FORMATS[preview["media_type"]][1].upper(), "bytes": preview["bytes"],
            "width": preview["width"], "height": preview["height"], "duration_seconds": preview["duration_seconds"],
            "sha256": preview["sha256"], "preview_licence": item["preview_licence"],
            "source_licence": source["licence"], "source_page": "/gallery/" + source["slug"],
            "source_identity": source["identity"], "source_version": source["version"], "provenance": item["provenance"],
        })
    _require(len({item["id"] for item in results}) == len(results), "duplicate projected media identity")
    return tuple(sorted(results, key=lambda item: item["id"]))


@lru_cache(maxsize=1)
def public_previews():
    return project(gallery.record(), media_record(), _read_asset)


def media_assets():
    """Only reviewed, byte-checked companion previews enter the public asset table."""
    return {item["url"]: (FOLDER + "/" + item["url"].rsplit("/", 1)[1], item["media_type"])
            for item in public_previews() if item["url"].startswith(PREFIX)}

"""Bounded public-preview projection owned by the existing gallery.

The gallery's recorded renders are already approved for public display. Their
source-package licence does not establish separate preview reuse rights. Additional media needs
an explicit reviewed preview record tied to an exact public gallery item or a
separately labelled original website example and its checked source-only ZIP.
Neither a source licence nor a paid body becomes public by inference.
This passive reader uses packaged files only, checks their bytes once, and
never opens a catalogue, account, provider or model connection.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import io
from importlib.resources import files
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zlib
from zipfile import BadZipFile, Path as ZipPath, ZipFile, ZIP_DEFLATED, ZIP_STORED

from . import gallery_records as gallery

RECORD_TYPE = "website_gallery_media/v2"
FOLDER = "gallery-media"
PREFIX = "/assets/gallery-media/"
KINDS = ("image", "video", "music")
MAX_EXTRA_ITEMS = 64
MAX_RECORD_BYTES = 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SOURCE_ZIP_BYTES = 256 * 1024
MAX_SOURCE_FILES = 32
MAX_SOURCE_FILE_BYTES = 128 * 1024
MAX_SOURCE_UNPACKED_BYTES = 512 * 1024
FORMATS = {
    "image/webp": ("image", "webp"), "image/png": ("image", "png"), "image/jpeg": ("image", "jpg"),
    "video/mp4": ("video", "mp4"), "video/webm": ("video", "webm"),
    "audio/mpeg": ("music", "mp3"), "audio/ogg": ("music", "ogg"), "audio/wav": ("music", "wav"),
}
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_FIELDS = {"id", "kind", "title", "summary", "source", "preview_licence",
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


def _source_name(name):
    if not _text(name, 200) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){0,4}", name):
        return False
    parts = name.split("/")
    if any(part in (".", "..") or part.startswith(".") or part.lower() in ("node_modules", "__pycache__") for part in parts):
        return False
    return parts[-1] == "LICENSE" or PurePosixPath(name).suffix.lower() in (".md", ".txt", ".json", ".mjs", ".js", ".py", ".html", ".css")


def _parse_source(source):
    _require(isinstance(source, dict), "media source must be an explicit provenance record")
    if source.get("kind") == "gallery_item":
        _require(set(source) == {"kind", "slug", "version"} and _text(source["slug"], 160)
                 and _SLUG.fullmatch(source["slug"]) and isinstance(source["version"], str)
                 and _SHA.fullmatch(source["version"]), "media must name an exact gallery source")
        return
    _require(source.get("kind") == "website_example" and set(source) == {"kind", "identity", "version", "licence", "archive", "files"},
             "unknown media source form")
    _require(_text(source["identity"], 160) and re.fullmatch(r"website-example\.[a-z0-9]+(?:-[a-z0-9]+)*", source["identity"])
             and source["licence"] == "MIT", "website examples use a distinct identity and the original-work licence")
    archive = source["archive"]
    _require(isinstance(archive, dict) and set(archive) == {"file", "sha256", "bytes"}
             and isinstance(archive["sha256"], str) and _SHA.fullmatch(archive["sha256"])
             and source["version"] == archive["sha256"] and _text(archive["file"], 200)
             and re.fullmatch(r"[a-z0-9-]+-" + archive["sha256"][:12] + r"\.zip", archive["file"])
             and type(archive["bytes"]) is int and 0 < archive["bytes"] <= MAX_SOURCE_ZIP_BYTES,
             "website source archive must be bounded and content-addressed")
    members = source["files"]
    _require(isinstance(members, list) and 1 <= len(members) <= MAX_SOURCE_FILES, "website source file count exceeds its bound")
    seen = set()
    for member in members:
        _require(isinstance(member, dict) and set(member) == {"path", "sha256", "bytes"}
                 and _source_name(member["path"]) and member["path"].casefold() not in seen
                 and isinstance(member["sha256"], str) and _SHA.fullmatch(member["sha256"])
                 and type(member["bytes"]) is int and 0 < member["bytes"] <= MAX_SOURCE_FILE_BYTES,
                 "source archive needs unique safe text files with exact digests and bounded sizes")
        seen.add(member["path"].casefold())
    _require(sum(member["bytes"] for member in members) <= MAX_SOURCE_UNPACKED_BYTES,
             "unpacked source archive exceeds its byte bound")
    _require(any(member["path"].split("/")[-1] == "LICENSE" for member in members)
             and any(member["path"].split("/")[-1].casefold() == "readme.md" for member in members),
             "source archive needs a licence and instructions")


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
        _parse_source(item["source"])
        _require(item["source"]["kind"] != "website_example" or item["preview_licence"] == "MIT",
                 "original website preview and source rights must both be explicit")
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


def _read_source(name):
    return _read_packaged(name, MAX_SOURCE_ZIP_BYTES)


@lru_cache(maxsize=1)
def _source_secret_patterns():
    """Reuse the installed repository secret patterns; never accept patterns from an archive."""
    resource = files("loop_engine").joinpath("forbidden_paths.json")
    _plain_resource(resource)
    with resource.open("rb") as stream:
        body = stream.read(MAX_RECORD_BYTES + 1)
    _require(len(body) <= MAX_RECORD_BYTES, "source-safety policy exceeds its byte bound")
    return tuple(re.compile(pattern) for pattern in json.loads(body)["secret_patterns"])


def valid_source_archive(body, source):
    """Check a source-only ZIP without extracting or running any member.

    Pattern detection does not establish the absence of every possible secret;
    an independent source review still binds the exact archive before release.
    """
    archive = source["archive"]
    if len(body) != archive["bytes"] or len(body) > MAX_SOURCE_ZIP_BYTES or hashlib.sha256(body).hexdigest() != archive["sha256"]:
        return False
    if not body.startswith(b"PK\x03\x04") or body[-22:-18] != b"PK\x05\x06":
        return False
    expected = {row["path"]: row for row in source["files"]}
    try:
        with ZipFile(io.BytesIO(body)) as bundle:
            entries = bundle.infolist()
            if len(entries) != len(expected) or len(entries) > MAX_SOURCE_FILES or bundle.comment:
                return False
            # A simple source ZIP has no executable prefix, extra payload, data
            # descriptor, split disk or trailing body hidden outside its members.
            end = struct.unpack("<4s4H2IH", body[-22:])
            if end[1:3] != (0, 0) or end[3] != len(entries) or end[4] != len(entries) or end[7] != 0:
                return False
            cursor = 0
            for entry in sorted(entries, key=lambda row: row.header_offset):
                if entry.header_offset != cursor:
                    return False
                local = struct.unpack_from("<4s5H3I2H", body, cursor)
                encoded_name = entry.filename.encode("utf-8" if entry.flag_bits & 2048 else "cp437")
                if (local[0] != b"PK\x03\x04" or local[2] != entry.flag_bits or local[3] != entry.compress_type
                        or local[6:9] != (entry.CRC, entry.compress_size, entry.file_size)
                        or local[9] != len(encoded_name) or local[10] != 0
                        or body[cursor + 30:cursor + 30 + local[9]] != encoded_name):
                    return False
                cursor += 30 + local[9] + entry.compress_size
            if cursor != bundle.start_dir or end[6] != cursor or end[5] != len(body) - 22 - cursor:
                return False
            seen = set()
            for entry in entries:
                name = entry.filename
                if name != entry.orig_filename or not _source_name(name) or name not in expected or name.casefold() in seen:
                    return False
                seen.add(name.casefold())
                kind = stat.S_IFMT(entry.external_attr >> 16)
                wanted = expected[name]
                if (kind not in (0, stat.S_IFREG) or entry.is_dir() or entry.flag_bits & 9 or entry.comment or entry.extra
                        or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED)):
                    return False
                if entry.file_size != wanted["bytes"] or entry.file_size > MAX_SOURCE_FILE_BYTES:
                    return False
                # ZipExtFile truncates to the header's file_size and can ignore
                # trailing compressed bytes. Inspect the entire bounded raw
                # stream instead, without an unbounded decompress or flush.
                encoded_name = name.encode("utf-8" if entry.flag_bits & 2048 else "cp437")
                start = entry.header_offset + 30 + len(encoded_name)
                compressed = body[start:start + entry.compress_size]
                if entry.compress_type == ZIP_STORED:
                    if entry.compress_size != entry.file_size:
                        return False
                    payload = compressed
                else:
                    decoder = zlib.decompressobj(-zlib.MAX_WBITS)
                    payload = decoder.decompress(compressed, wanted["bytes"] + 1)
                    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                        return False
                if zlib.crc32(payload) & 0xffffffff != entry.CRC:
                    return False
                if len(payload) != wanted["bytes"] or hashlib.sha256(payload).hexdigest() != wanted["sha256"] or b"\0" in payload:
                    return False
                text = payload.decode("utf-8")
                if any(pattern.search(text) for pattern in _source_secret_patterns()) or "PRIVATE KEY-----" in text:
                    return False
        return True
    except (BadZipFile, OSError, ValueError, RuntimeError, KeyError, UnicodeError, re.error, struct.error, zlib.error):
        return False


def _matching_bytes(name, preview, reader):
    try:
        body = reader(name)
    except (OSError, gallery.GalleryRecordError):
        return False
    return len(body) == preview["bytes"] and hashlib.sha256(body).hexdigest() == preview["sha256"]


def project(value, extra, reader, source_reader=None):
    """Pure projection with an injected bounded asset reader for offline controls.

    Missing, changed, unapproved or nonpublic records are excluded. An exact
    old selection therefore becomes unavailable; it never selects a new body.
    """
    source_reader = reader if source_reader is None else source_reader
    _require(len(value["items"]) <= 1000, "random previews use a curated gallery, not a full catalogue scan")
    sources = {item["slug"]: item for item in value["items"] if item["tier"] in gallery.PUBLIC_TIERS}
    _require(sum((item.get("preview") or {}).get("bytes", 0) for item in sources.values())
             + sum(item["preview"]["bytes"] for item in extra["items"])
             + sum(item["source"]["archive"]["bytes"] for item in extra["items"]
                   if item["source"]["kind"] == "website_example") <= MAX_TOTAL_BYTES,
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
            "source_kind": "gallery_item",
            "provenance": "Baltor native-check render, converted to WebP. Source PNG SHA-256: "
                          + preview["source_png_sha256"],
        })
    for item in extra["items"]:
        if item["review"]["status"] != "approved":
            continue
        origin = item["source"]
        if origin["kind"] == "gallery_item":
            source = sources.get(origin["slug"])
            if source is None or source["version"] != origin["version"]:
                continue
            source_fields = {"source_kind": "gallery_item", "source_licence": source["licence"],
                             "source_page": "/gallery/" + source["slug"], "source_identity": source["identity"],
                             "source_version": source["version"]}
        else:
            try:
                body = source_reader(FOLDER + "/" + origin["archive"]["file"])
            except (OSError, gallery.GalleryRecordError):
                continue
            if not valid_source_archive(body, origin):
                continue
            source_fields = {"source_kind": "website_example", "source_licence": origin["licence"],
                             "source_page": PREFIX + origin["archive"]["file"], "source_identity": origin["identity"],
                             "source_version": origin["version"]}
        preview = item["preview"]
        if not _matching_bytes(FOLDER + "/" + preview["file"], preview, reader):
            continue
        results.append({
            "id": item["id"] + "-" + preview["sha256"][:12], "kind": item["kind"], "title": item["title"],
            "summary": item["summary"], "url": PREFIX + preview["file"], "media_type": preview["media_type"],
            "format": FORMATS[preview["media_type"]][1].upper(), "bytes": preview["bytes"],
            "width": preview["width"], "height": preview["height"], "duration_seconds": preview["duration_seconds"],
            "sha256": preview["sha256"], "preview_licence": item["preview_licence"],
            **source_fields, "provenance": item["provenance"],
        })
    _require(len({item["id"] for item in results}) == len(results), "duplicate projected media identity")
    return tuple(sorted(results, key=lambda item: item["id"]))


@lru_cache(maxsize=1)
def public_previews():
    return project(gallery.record(), media_record(), _read_asset, _read_source)


def media_assets():
    """Only reviewed, byte-checked companion previews enter the public asset table."""
    projected = public_previews()
    result = {item["url"]: (FOLDER + "/" + item["url"].rsplit("/", 1)[1], item["media_type"])
              for item in projected if item["url"].startswith(PREFIX)}
    result.update({item["source_page"]: (FOLDER + "/" + item["source_page"].rsplit("/", 1)[1], "application/zip")
                   for item in projected if item["source_kind"] == "website_example"})
    return result

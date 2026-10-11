"""Read the versioned public gallery record and its content-addressed previews.

Kind: passive data validation owned by the existing web presentation boundary.
This leaf checks item identities, kinds, visibility, related links and preview
digests without importing HTTP or page renderers. It reads packaged metadata,
performs no provider call, grants no access and creates no executable runtime.
Both the asset registry and gallery renderer consume the same checked record.
"""
from __future__ import annotations

from functools import lru_cache
import json
import re

RECORD_TYPE = "website_gallery/v1"
RECORD_FOLDER = "gallery"
RECORD_FILE = "gallery.json"
ASSET_PREFIX = "/assets/gallery/"
TIERS = ("showcase", "listed", "private")
TIER_LABELS = {"showcase": "Free download", "listed": "In your harness", "private": "Private"}
PUBLIC_TIERS = ("showcase", "listed")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PREVIEW = re.compile(r"^[a-z0-9-]+-[0-9a-f]{12}\.webp$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
ITEM_FIELDS = {"slug", "identity", "version", "family", "kind", "title", "summary", "tier", "licence", "tags", "dimension",
               "engine", "files", "bytes", "contract", "limits", "techniques", "related", "checks", "declared_effects"}


class GalleryRecordError(ValueError):
    """A gallery record this reader refuses, with the reason."""


def _require(condition, reason):
    if not condition:
        raise GalleryRecordError(reason)


def parse_record(text: str) -> dict:
    """Refuse an unknown version, a missing or unknown field, a duplicate or reserved address, an unknown tier or kind,
    a related item that is not public, and a preview that is not a content-addressed WebP name."""
    record = json.loads(text)
    _require(record.get("record_type") == RECORD_TYPE, f"this reader reads {RECORD_TYPE}")
    _require(set(record) == {"record_type", "built_from", "preview_format", "kinds", "items"}, "unknown or missing fields")
    kinds = {kind["id"]: kind for kind in record["kinds"]}
    _require(len(kinds) == len(record["kinds"]) and all(_SLUG.match(kind) for kind in kinds), "kind ids are unique slugs")
    slugs = set()
    for item in record["items"]:
        missing = ITEM_FIELDS - set(item)
        _require(not missing and set(item) <= ITEM_FIELDS | {"preview"}, f"item fields: {sorted(missing) or sorted(item)}")
        slug = item["slug"]
        _require(_SLUG.match(slug) and slug not in slugs and slug not in ("guide", "collections", "sitemap", "kinds"),
                 f"/gallery/{slug} is not a unique item address")
        slugs.add(slug)
        _require(item["tier"] in TIERS, f"{slug}: the tier {item['tier']!r} is not one of {TIERS}")
        _require(item["kind"] in kinds, f"{slug}: the kind {item['kind']!r} is not in the record")
        _require(_DIGEST.match(item["version"]) is not None, f"{slug}: the version is not a SHA-256 digest")
        preview = item.get("preview")
        if preview is not None:
            _require(set(preview) == {"file", "sha256", "bytes", "width", "height", "source_png_sha256"},
                     f"{slug}: unknown or missing preview fields")
            _require(all(type(preview[field]) is int and preview[field] > 0 for field in ("width", "height", "bytes")),
                     f"{slug}: preview dimensions and size must be positive integers")
            _require(_DIGEST.fullmatch(preview["source_png_sha256"]) is not None,
                     f"{slug}: preview source digest is invalid")
            _require(_PREVIEW.match(preview["file"]) and _DIGEST.match(preview["sha256"])
                     and preview["file"].endswith(preview["sha256"][:12] + ".webp"),
                     f"{slug}: the preview is not named by its own digest")
    public = {item["slug"] for item in record["items"] if item["tier"] in PUBLIC_TIERS}
    for item in record["items"]:
        _require(set(item["related"]) <= slugs, f"{item['slug']}: a related item is not in the record")
        item["related"] = [slug for slug in item["related"] if slug in public]
    return record


@lru_cache(maxsize=1)
def record() -> dict:
    from importlib.resources import files
    path = files("loop_engine").joinpath("core", "service_runtime", "web_assets", RECORD_FOLDER, RECORD_FILE)
    return parse_record(path.read_text(encoding="utf-8"))


def preview_assets(value=None) -> dict:
    """Names and media types for public, content-addressed preview images."""
    value = record() if value is None else value
    return {ASSET_PREFIX + item["preview"]["file"]: (RECORD_FOLDER + "/" + item["preview"]["file"], "image/webp")
            for item in value["items"] if item.get("preview") and item["tier"] in PUBLIC_TIERS}

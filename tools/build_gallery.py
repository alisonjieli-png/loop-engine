"""Write the website gallery record and its preview images from a published creative release.

Kind: development tool. It reads three local inputs that stay outside the repository: the published additions of one
creative publication (`items.jsonl`, the exact identities, versions, licences and file lists the catalogue serves), the
admission packages of the same release (`component.json`, the contract card, and `preview.png`, the render the native
check recorded), and the publication's confirmation record (the release that served them). It writes
`web_assets/gallery/gallery.json` and one WebP preview per item with a render. It needs Pillow with WebP support, which
only this tool uses; `tools/test_gallery_page.py` checks the written record and every preview without it.

Why WebP: the 329 recorded renders are 13.4 MB as PNG and 2.1 MB as WebP at quality 82, the same 256 by 256 pixels.
The record keeps the SHA-256 of the PNG the native check recorded beside the SHA-256 of the served WebP, so a preview
is traceable to the exact render. The renders are pictures of what a file makes, drawn by Baltor's own checks; the
files themselves reach a customer only through a harness download.

Usage (October 9, 2026, the creative release 29a2bc33):

    python3 tools/build_gallery.py \\
      --additions ~/.le-creative-3d/out/supply/additions-creative-d25e6cb4 \\
      --packages ~/.le-creative-3d/out/supply/admission-d25e6cb4/packages \\
      --publication ~/baltor-private/creative-publication-20261009-dd8349/publication-01-reconciled.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src/loop_engine/core/service_runtime/web_assets/gallery"
RECORD_TYPE = "website_gallery/v1"
WEBP_QUALITY = 82
#: The creative families the gallery shows, in the order of its kind filters: id, label, one item's label, description.
KINDS = (
    ("godot_shaders", "godot-shaders", "Godot shaders", "Godot shader",
     "Spatial, canvas and particle shaders, compiled and rendered in Godot 4.7.2 with the Compatibility renderer."),
    ("procedural_textures", "procedural-textures", "Procedural textures", "Procedural texture",
     "Tileable PBR texture generators with presets, a Godot material and a Blender builder."),
    ("mesh_algorithms", "mesh-algorithms", "Mesh algorithms", "Mesh algorithm",
     "Pure Python mesh and geometry algorithms whose glTF output loads in Godot."),
    ("blender_tools", "blender-tools", "Blender tools", "Blender tool",
     "Blender Python tools, run in Blender 5.2.1 in background mode."),
    ("geometry_4d", "geometry-4d", "4D geometry", "4D geometry tool",
     "Four-dimensional geometry tools that project into glTF scenes."),
    ("godot_components", "godot-components", "Godot components", "Godot component",
     "GDScript components for Godot 4, run headless in Godot 4.7.2."),
    ("asset_contracts", "asset-contracts", "Asset contracts", "Asset contract",
     "Checkers and procedures that catch 3D and 2D pipeline mistakes before export."),
)
FAMILIES = {family: (kind, label, single, description) for family, kind, label, single, description in KINDS}
#: Addresses below /gallery/ that an item slug may never take.
RESERVED = {"guide", "collections", "sitemap", "kinds"}
LIMIT = 8


def _short(value, limit=160):
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit - 1].rsplit(" ", 1)[0] + "…"


def _value(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_value(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key} {_value(item)}" for key, item in value.items())
    return " ".join(str(value).split())


def _names(rows, key="name"):
    names = [row.get(key) if isinstance(row, dict) else row for row in rows or ()]
    names = [str(name) for name in names if name]
    shown = ", ".join(names[:LIMIT])
    return shown + (f" and {len(names) - LIMIT} more" if len(names) > LIMIT else "")


def _uniforms(rows):
    parts = []
    for row in rows[:LIMIT]:
        default = "" if row.get("default") is None else f" = {_value(row['default'])}"
        parts.append(f"{row.get('name')} ({row.get('type')}{default})")
    return ", ".join(parts) + (f" and {len(rows) - LIMIT} more" if len(rows) > LIMIT else "")


def _methods(rows):
    parts = [f"{row.get('name')}({', '.join(row.get('arguments') or [])}) -> {row.get('returns')}" for row in rows[:LIMIT]]
    return "; ".join(parts) + (f"; and {len(rows) - LIMIT} more" if len(rows) > LIMIT else "")


def contract_rows(family: str, contract: dict) -> list:
    """What an item takes and gives, as label and text rows a page can show without code."""
    c, rows = contract or {}, []

    def add(label, value):
        if value not in (None, "", [], {}):
            rows.append([label, _short(value if isinstance(value, str) else _value(value), 400)])
    if family == "godot_shaders":
        add("Shader type", c.get("shader_type"))
        add("Render modes", c.get("render_modes"))
        add("Parameters", _uniforms(c.get("uniforms") or []))
        add("Use it on", c.get("inputs"))
        add("Result", c.get("outputs"))
        add("Renderers", ", ".join(f"{name.replace('_', ' ')}: {state.replace('_', ' ')}"
                                   for name, state in (c.get("renderers") or {}).items()))
        add("Placement", c.get("placement"))
    elif family == "procedural_textures":
        add("Entry point", c.get("entry_point"))
        add("Maps", _names(c.get("maps")))
        add("Parameters", _names(c.get("parameters")))
        add("Presets", _names(c.get("presets")))
        add("Tileable", c.get("tileable"))
        add("Command line", c.get("command_line"))
        add("Godot material", c.get("godot_material"))
        add("Blender builder", c.get("blender_builder"))
    elif family == "blender_tools":
        points = c.get("entry_points") or {}
        add("Operator", points.get("operator") if isinstance(points, dict) else None)
        add("Parameters", _names(c.get("parameters")))
        outputs = c.get("outputs") or {}
        add("Result", outputs.get("description") if isinstance(outputs, dict) else outputs)
        add("Blender", f"{c.get('blender_minimum')} or later" if c.get("blender_minimum") else None)
        add("Axes", c.get("axes"))
        add("Units", c.get("units"))
    elif family in ("mesh_algorithms", "geometry_4d"):
        add("Entry points", _names(c.get("entry_points")))
        add("Parameters", _names(c.get("parameters")))
        outputs = c.get("outputs")
        add("Outputs", _names(outputs, "path") if isinstance(outputs, list) else outputs)
        add("Coordinates", c.get("coordinates"))
        add("Complexity", c.get("complexity"))
        add("Axes", c.get("axes"))
    elif family == "godot_components":
        add("Class", f"{c.get('class_name')}, extends {c.get('extends')}" if c.get("class_name") else None)
        add("Methods", _methods(c.get("methods") or []))
        add("Signals", _names(c.get("signals")))
        add("Exports", _names(c.get("exports")))
        add("Placement", c.get("placement"))
    elif family == "asset_contracts":
        add("Entry points", _names(c.get("entry_points")))
        add("Proves", c.get("proves"))
        add("Does not prove", c.get("does_not_prove"))
        add("Catches", _names(c.get("failures_detected")))
    return rows


def _slug(identity: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", identity.lower()).strip("-")


def _webp(png: bytes) -> tuple:
    from PIL import Image
    image = Image.open(io.BytesIO(png))
    image.load()
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    out = io.BytesIO()
    image.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue(), image.size


def build(additions: Path, packages: Path, publication: Path, output: Path = OUTPUT) -> dict:
    confirmation = json.loads(publication.read_text("utf-8"))
    final = confirmation.get("publisher_final") or {}
    if confirmation.get("publication_confirmed") is not True or not final.get("bundle_digest"):
        raise SystemExit("the publication record does not confirm a published bundle")
    published = [json.loads(line) for line in (additions / "items.jsonl").read_text("utf-8").splitlines() if line.strip()]
    staged = output.with_name(output.name + ".building")
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    items, revisions, slugs = [], set(), {}
    for row in published:
        reference = row["reference"]
        identity = reference["identity"]
        folder = packages / identity
        card = json.loads((folder / "component.json").read_text("utf-8"))
        family = card["generator"]["family"]
        if family not in FAMILIES:
            continue
        source = card.get("source") or {}
        revisions.add(source.get("revision"))
        name = card["job"]["identity"]
        slug = _slug(name)
        if slug in RESERVED or slug in slugs:
            slug = _slug(family + "-" + name)
        if slug in slugs:
            raise SystemExit(f"two gallery items would share the address /gallery/{slug}")
        slugs[slug] = identity
        files = [{"path": entry["path"], "bytes": entry["size_bytes"]} for entry in row["package"]["files"]]
        native = (card.get("verification") or {}).get("native") or {}
        engine = native.get("engine") or {}
        item = {
            "slug": slug, "identity": identity, "version": reference["digest"], "family": family,
            "kind": FAMILIES[family][0], "title": card["title"], "summary": card["purpose"],
            "tier": "listed", "licence": reference.get("license") or "Not stated",
            "tags": list(card.get("tags") or [])[:LIMIT], "dimension": card.get("dimension") or "none",
            "engine": card.get("engine") or {}, "files": files, "bytes": sum(entry["bytes"] for entry in files),
            "contract": contract_rows(family, card.get("contract") or {}), "limits": card.get("limits") or "",
            "techniques": list(card.get("technique_references") or [])[:LIMIT],
            "related": list(card.get("related") or []),
            "checks": {"engine": " ".join(str(part) for part in (engine.get("name"), engine.get("version")) if part),
                       "renderer": engine.get("renderer") or "", "names": list(native.get("checks") or [])},
            "declared_effects": list(reference.get("declared_effects") or []),
        }
        preview = folder / "preview.png"
        if preview.is_file():
            png = preview.read_bytes()
            webp, size = _webp(png)
            digest = hashlib.sha256(webp).hexdigest()
            file_name = f"{slug}-{digest[:12]}.webp"
            (staged / file_name).write_bytes(webp)
            item["preview"] = {"file": file_name, "sha256": digest, "bytes": len(webp), "width": size[0],
                               "height": size[1], "source_png_sha256": hashlib.sha256(png).hexdigest()}
        items.append(item)
    job_names = {}
    for row in published:
        card_path = packages / row["reference"]["identity"] / "component.json"
        card = json.loads(card_path.read_text("utf-8"))
        job_names[card["job"]["identity"]] = row["reference"]["identity"]
    slug_of = {item["identity"]: item["slug"] for item in items}
    for item in items:
        item["related"] = [slug_of[job_names[name]] for name in item["related"]
                           if name in job_names and job_names[name] in slug_of and slug_of[job_names[name]] != item["slug"]]
    # Within a kind, four renders lead: the ones with the most detail (the largest WebP), taking at most one from each
    # category tag so the first row is not four variations of one effect. Every other item follows by title.
    def detail(item):
        return -(item.get("preview") or {}).get("bytes", 0)

    def category(item):
        tags = item["tags"]
        return tags[2] if len(tags) > 2 else (tags[-1] if tags else "")
    ordered = []
    for family, *_rest in KINDS:
        group = [item for item in items if item["family"] == family]
        lead, used = [], set()
        for item in sorted((item for item in group if item.get("preview")), key=lambda item: (detail(item), item["title"])):
            if len(lead) < 4 and category(item) not in used:
                lead.append(item)
                used.add(category(item))
        rest = sorted((item for item in group if item not in lead), key=lambda item: item["title"].lower())
        ordered += lead + rest
    record = {
        "record_type": RECORD_TYPE,
        "built_from": {"catalogue_release": final.get("active_release_id") or confirmation.get("release_id"),
                       "bundle_digest": final["bundle_digest"], "line": "creative_originals",
                       "repository_revisions": sorted(revision for revision in revisions if revision),
                       "published_items": len(published)},
        "preview_format": {"media_type": "image/webp", "quality": WEBP_QUALITY,
                           "from": "the 256 by 256 PNG render each native check recorded"},
        "kinds": [{"id": kind, "family": family, "label": label, "single": single, "description": description,
                   "items": sum(1 for item in items if item["family"] == family)}
                  for family, kind, label, single, description in KINDS],
        "items": ordered,
    }
    (staged / "gallery.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", "utf-8")
    if output.exists():
        shutil.rmtree(output)
    staged.rename(output)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--additions", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    record = build(args.additions.expanduser(), args.packages.expanduser(), args.publication.expanduser(),
                   args.output)
    shown = sum(1 for item in record["items"] if item.get("preview"))
    print(json.dumps({"items": len(record["items"]), "previews": shown,
                      "preview_bytes": sum(item["preview"]["bytes"] for item in record["items"] if item.get("preview")),
                      "kinds": {kind["id"]: kind["items"] for kind in record["kinds"]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

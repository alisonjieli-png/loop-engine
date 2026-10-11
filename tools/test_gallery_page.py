"""Gallery provenance, visibility and exact preview bytes; no provider calls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from loop_engine.core.service_runtime import gallery_page as gallery

ASSETS = Path(__file__).resolve().parents[1] / "src/loop_engine/core/service_runtime/web_assets"


class GalleryTests(unittest.TestCase):
    def test_native_scene_terms_are_scoped_and_unrelated_runtime_terms_still_fail(self):
        """Native Godot hierarchy and method parameters do not rename Loop runtime relationships."""
        from loop_engine.nomenclature_conformance import retired_nomenclature_violations
        source = ASSETS.parents[2]
        policy = json.loads((source / "forbidden_paths.json").read_text())["retired_source_nomenclature"]
        relative = "core/service_runtime/web_assets/gallery/gallery.json"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / relative
            target.parent.mkdir(parents=True)
            native = (source / relative).read_text()
            target.write_text(native)
            self.assertEqual(retired_nomenclature_violations(folder, policy), [])
            target.write_text(native + '\n"unrelated": "child runtime"\n')
            findings = retired_nomenclature_violations(folder, policy)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["file"], relative)
            target.write_text(native)
            missing = copy.deepcopy(policy)
            del missing["allowed_fragments"][relative]
            self.assertTrue(retired_nomenclature_violations(folder, missing))

    def test_previews_have_the_recorded_digest_and_every_page_has_a_source_identity(self):
        record = gallery.record()
        self.assertEqual(record["built_from"]["catalogue_release"],
                         "29a2bc33c3132a97466e79c18350f3574624f2ef7967b07241029e269b92e742")
        for item in gallery.public_items():
            self.assertTrue(item["identity"])
            self.assertTrue(item["files"])
            if item.get("preview"):
                preview = item["preview"]
                self.assertEqual(hashlib.sha256((ASSETS / "gallery" / preview["file"]).read_bytes()).hexdigest(),
                                 preview["sha256"])
            self.assertIsNotNone(gallery.item_at(gallery.PREFIX + item["slug"]))

    def test_private_items_are_absent_from_tiles_links_and_preview_routes(self):
        record = copy.deepcopy(gallery.record())
        chosen = next(item for item in record["items"] if item.get("preview"))
        chosen["tier"] = "private"
        with patch.object(gallery, "record", return_value=record):
            self.assertIsNone(gallery.item_at(gallery.PREFIX + chosen["slug"]))
            self.assertNotIn('href="/gallery/' + chosen["slug"] + '"', gallery.index_body())
            self.assertNotIn(gallery.ASSET_PREFIX + chosen["preview"]["file"], gallery.preview_assets())

    def test_unknown_versions_tiers_paths_and_digests_are_refused(self):
        original = gallery.record()
        for field, wrong in (("record_type", "website_gallery/v999"),):
            value = copy.deepcopy(original)
            value[field] = wrong
            with self.assertRaises(ValueError):
                gallery.parse_record(json.dumps(value))
        for mutation in (lambda row: row.update(tier="download_anything"),
                         lambda row: row.update(version="f" * 63),
                         lambda row: row.update(slug="../account"),
                         lambda row: row["preview"].update(file="../private.webp"),
                         lambda row: row["preview"].update(width='256" onload="bad'),
                         lambda row: row["preview"].update(height=0),
                         lambda row: row["preview"].update(source_png_sha256="unknown")):
            value = copy.deepcopy(original)
            mutation(next(row for row in value["items"] if row.get("preview")))
            with self.assertRaises(ValueError):
                gallery.parse_record(json.dumps(value))

    def test_external_strings_are_escaped_and_counts_describe_display_items(self):
        item = copy.deepcopy(gallery.public_items()[0])
        item["title"] = '<script>alert("bad")</script>'
        body = gallery.item_body(item)
        self.assertNotIn(item["title"], body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("creative tools and assets", gallery.index_body())
        self.assertNotIn("stops bulk copying", gallery.index_body())


if __name__ == "__main__":
    unittest.main()

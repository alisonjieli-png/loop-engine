"""Offline controls for the gallery's random public-preview view and future media.

Media fixture bytes exercise record and access rules, not native playback or
music quality. They are not published assets or rights evidence.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
import warnings
from unittest.mock import patch
from zipfile import Path as ZipPath, ZipFile, ZipInfo

from loop_engine.core.service_runtime import gallery_media as media
from loop_engine.core.service_runtime import gallery_page, gallery_random, gallery_records, web_pages
from loop_engine.core.service_runtime.static_site_export import static_addresses

ASSETS = Path(__file__).resolve().parents[1] / "src/loop_engine/core/service_runtime/web_assets"


def fixture(kind="video", status="approved"):
    source = copy.deepcopy(next(item for item in gallery_records.record()["items"] if item.get("preview")))
    body = b"test-only record fixture, not a playable or published asset"
    digest = hashlib.sha256(body).hexdigest()
    mime, extension = {"video": ("video/mp4", "mp4"), "music": ("audio/mpeg", "mp3"),
                       "image": ("image/png", "png")}[kind]
    row = {"id": "fixture-" + kind, "kind": kind, "title": "Test preview", "summary": "Record fixture only.",
           "source": {"kind": "gallery_item", "slug": source["slug"], "version": source["version"]}, "preview_licence": "MIT",
           "provenance": "Synthetic parser fixture, not playback qualification.",
           "review": {"status": status, "reference": "test-only", "reviewer": "test-fixture"},
           "preview": {"file": "fixture-" + digest[:12] + "." + extension, "sha256": digest,
                       "bytes": len(body), "media_type": mime, "width": None if kind == "music" else 256,
                       "height": None if kind == "music" else 256, "duration_seconds": None if kind == "image" else 2}}
    value = {**gallery_records.record(), "items": [source]}
    extra = {"record_type": media.RECORD_TYPE, "items": [row]}
    return value, extra, lambda name: body


class RandomGalleryTests(unittest.TestCase):
    def test_duplicate_approval_and_version_fields_are_refused(self):
        _, extra, _ = fixture()
        raw = json.dumps(extra)
        wrong = (
            raw.replace('"status": "approved"', '"status": "rejected", "status": "approved"'),
            raw.replace('"review": {', '"review": {"status":"pending","reference":"pending",'
                        '"reviewer":"fixture"}, "review": {'),
            raw.replace('"record_type": "website_gallery_media/v2"',
                        '"record_type": "website_gallery_media/v99", "record_type": "website_gallery_media/v2"'),
        )
        for text in wrong:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "duplicate"):
                media.parse_media(text)

    def test_media_json_size_is_checked_before_parse_and_nonfinite_json_is_refused(self):
        with patch.object(media, "MAX_RECORD_BYTES", 128, create=True), \
                patch.object(media.json, "loads", side_effect=AssertionError("oversized JSON was parsed")):
            for raw in (" " * 129, "é" * 65):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    media.parse_media(raw)
        for raw in ('{"record_type":"website_gallery_media/v2","items":NaN}',
                    '[' * 1500 + ']' * 1500, '\ud800'):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                media.parse_media(raw)

    def test_packaged_record_read_is_bounded_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "package/core/service_runtime/web_assets/gallery-media"
            folder.mkdir(parents=True)
            path = folder / "media.json"
            path.write_text(" " * 4096 + json.dumps({"record_type": media.RECORD_TYPE, "items": []}))
            try:
                with patch.object(media, "files", return_value=root / "package"), \
                        patch.object(media, "MAX_RECORD_BYTES", 128, create=True):
                    media.media_record.cache_clear()
                    with self.assertRaises(ValueError):
                        media.media_record()
                path.unlink()
                outside = root / "outside.json"
                outside.write_text(json.dumps({"record_type": media.RECORD_TYPE, "items": []}))
                path.symlink_to(outside)
                with patch.object(media, "files", return_value=root / "package"):
                    media.media_record.cache_clear()
                    with self.assertRaises(ValueError):
                        media.media_record()
                path.unlink()
                path.symlink_to(path)
                with patch.object(media, "files", return_value=root / "package"):
                    media.media_record.cache_clear()
                    with self.assertRaises(ValueError):
                        media.media_record()
            finally:
                media.media_record.cache_clear()

    def test_packaged_record_reads_only_the_bound_plus_one_bytes(self):
        reads = []
        class BoundedStream(io.BytesIO):
            def read(self, size=-1):
                reads.append(size)
                if size != 129:
                    raise AssertionError("packaged metadata used an unbounded read")
                return super().read(size)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "package/core/service_runtime/web_assets/gallery-media/media.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"record_type": media.RECORD_TYPE, "items": []}))
            try:
                with patch.object(media, "files", return_value=root / "package"), \
                        patch.object(media, "MAX_RECORD_BYTES", 128, create=True), \
                        patch.object(Path, "open", return_value=BoundedStream(b" " * 4096)):
                    media.media_record.cache_clear()
                    with self.assertRaises(ValueError):
                        media.media_record()
                self.assertEqual(reads, [129])
            finally:
                media.media_record.cache_clear()

    def test_symlinked_preview_and_directory_do_not_enter_projection(self):
        value, extra, reader = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "package/core/service_runtime/web_assets"
            folder = assets / media.FOLDER
            folder.mkdir(parents=True)
            outside = root / "outside-preview"
            outside.write_bytes(reader("fixture"))
            path = folder / extra["items"][0]["preview"]["file"]
            path.symlink_to(outside)
            with patch.object(media, "files", return_value=root / "package"):
                self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), media._read_asset), ())
            path.unlink()
            folder.rmdir()
            outside_folder = root / "outside-folder"
            outside_folder.mkdir()
            (outside_folder / path.name).write_bytes(reader("fixture"))
            folder.symlink_to(outside_folder, target_is_directory=True)
            with patch.object(media, "files", return_value=root / "package"):
                self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), media._read_asset), ())

    def test_regular_and_zip_packaged_resources_use_the_same_bounds(self):
        value, extra, reader = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prefix = "loop_engine/core/service_runtime/web_assets/gallery-media/"
            record = json.dumps(extra).encode()
            filename = extra["items"][0]["preview"]["file"]
            with ZipFile(root / "package.zip", "w") as archive:
                archive.writestr(prefix + "media.json", record)
                archive.writestr(prefix + filename, reader("fixture"))
            with ZipFile(root / "package.zip") as archive, \
                    patch.object(media, "files", return_value=ZipPath(archive, "loop_engine/")):
                try:
                    media.media_record.cache_clear()
                    parsed = media.media_record()
                    self.assertEqual(parsed, extra)
                    projected = media.project(value, parsed, media._read_asset)
                    self.assertEqual(len(projected), 1)
                    self.assertEqual(projected[0]["sha256"], extra["items"][0]["preview"]["sha256"])
                    with patch.object(media, "MAX_RECORD_BYTES", len(record) - 1):
                        media.media_record.cache_clear()
                        with self.assertRaises(ValueError):
                            media.media_record()
                finally:
                    media.media_record.cache_clear()

    def test_zip_alias_special_and_duplicate_members_are_refused(self):
        _, extra, reader = fixture()
        prefix = "loop_engine/core/service_runtime/web_assets/gallery-media/"
        with tempfile.TemporaryDirectory() as temp:
            for index, mode in enumerate((stat.S_IFLNK, stat.S_IFIFO, "duplicate", "parent-link")):
                path = Path(temp) / f"fixture-{index}.zip"
                with ZipFile(path, "w") as archive:
                    entry = ZipInfo(prefix + "media.json")
                    entry.create_system = 3
                    entry.external_attr = ((mode if type(mode) is int else stat.S_IFREG) | 0o600) << 16
                    archive.writestr(entry, json.dumps(extra))
                    if mode == "duplicate":
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", UserWarning)
                            archive.writestr(prefix + "media.json", json.dumps(extra))
                    if mode == "parent-link":
                        entry = ZipInfo(prefix.rstrip("/"))
                        entry.create_system = 3
                        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(entry, "outside")
                with ZipFile(path) as archive, \
                        patch.object(media, "files", return_value=ZipPath(archive, "loop_engine/")):
                    try:
                        media.media_record.cache_clear()
                        with self.subTest(mode=mode), self.assertRaises(ValueError):
                            media.media_record()
                    finally:
                        media.media_record.cache_clear()

    def test_zip_preview_symlink_is_not_public_even_with_matching_bytes(self):
        value, extra, reader = fixture()
        prefix = "loop_engine/core/service_runtime/web_assets/gallery-media/"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr(prefix + "media.json", json.dumps(extra))
                entry = ZipInfo(prefix + extra["items"][0]["preview"]["file"])
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(entry, reader("fixture"))
            with ZipFile(path) as archive, patch.object(media, "files", return_value=ZipPath(archive, "loop_engine/")):
                self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), media._read_asset), ())

    def test_wrong_id_review_types_and_overlong_file_names_are_refused(self):
        _, original, _ = fixture()
        for field, values in (("id", (None, True, [], {}, "../private", "bad\n")),
                              ("review", (None, False, [], "approved"))):
            for value in values:
                record = copy.deepcopy(original)
                record["items"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    media.parse_media(json.dumps(record))
        record = copy.deepcopy(original)
        record["items"][0]["preview"]["file"] = "x" * 201 + "-" + record["items"][0]["preview"]["sha256"][:12] + ".mp4"
        with self.assertRaises(ValueError):
            media.parse_media(json.dumps(record))
        for field in ("title", "provenance"):
            record = copy.deepcopy(original)
            record["items"][0][field] = "escaped non-UTF-8: \ud800"
            with self.subTest(field=field), self.assertRaises(ValueError):
                media.parse_media(json.dumps(record))

    def test_public_asset_reader_boundary_checks_include_the_new_passive_reader(self):
        from loop_engine.core.service_runtime.http_boundary_checks import _web_pages_boundary
        checks = []
        _web_pages_boundary(lambda name, passed: checks.append((name, passed)))
        self.assertIn(("served_address_table_does_not_import_the_transport_application", True), checks)
        self.assertIn(("served_address_guard_rejects_a_module_that_imports_the_application", True), checks)
        self.assertTrue(all(passed for _name, passed in checks), checks)

    @unittest.skipUnless(shutil.which("node"), "JavaScript selection checks need Node")
    def test_browser_selection_controls_run_in_the_owning_suite(self):
        result = subprocess.run([shutil.which("node"), "--test", str(Path(__file__).with_suffix(".mjs"))],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_packaged_population_has_exact_public_bytes_and_declared_reviewed_media(self):
        items = media.public_previews()
        gallery_items = [item for item in items if item["source_kind"] == "gallery_item"]
        self.assertEqual(len(gallery_items), 329)
        approved = [item for item in media.media_record()["items"] if item["review"]["status"] == "approved"]
        self.assertEqual(len(items), 329 + len(approved))
        self.assertEqual(len({item["sha256"] for item in items}), len(items))
        self.assertTrue({row["id"] + "-" + row["preview"]["sha256"][:12] for row in approved} <= {row["id"] for row in items})
        for item in items:
            name, mime = web_pages.WEB_ASSETS[item["url"]]
            body = (ASSETS / name).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), item["sha256"])
            self.assertEqual(len(body), item["bytes"])
            self.assertEqual(mime, item["media_type"])
            if item["source_kind"] == "gallery_item":
                source = gallery_page.item_at(item["source_page"])
                self.assertEqual(source["version"], item["source_version"])
                self.assertEqual(item["source_licence"], "MIT")
                self.assertIsNone(item["preview_licence"])

    def test_current_projection_is_bounded_cached_and_never_reads_catalogue_bodies(self):
        names = []
        def reader(name):
            names.append(name)
            return (ASSETS / name).read_bytes()
        result = media.project(gallery_records.record(), media.media_record(), reader)
        self.assertEqual(len(result), len(media.public_previews()))
        self.assertTrue(all((name.startswith("gallery/") and name.endswith(".webp")) or
                            (name.startswith("gallery-media/") and name.endswith((".mp4", ".mp3", ".zip"))) for name in names))
        self.assertIs(media.public_previews(), media.public_previews())
        with self.assertRaises(ValueError):
            media.project({"items": [{}] * 1001}, {"items": []}, reader)
        value = copy.deepcopy(gallery_records.record())
        next(item for item in value["items"] if item.get("preview"))["preview"]["bytes"] = media.MAX_TOTAL_BYTES + 1
        with self.assertRaises(ValueError):
            media.project(value, {"items": []}, reader)

    def test_private_source_and_unreviewed_preview_never_enter_public_projection(self):
        for kind in media.KINDS:
            for status in ("pending", "rejected"):
                value, extra, reader = fixture(kind, status)
                self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), reader), ())
            value, extra, reader = fixture(kind)
            value["items"][0]["tier"] = "private"
            self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), reader), ())

    def test_future_reviewed_media_uses_the_same_projection_and_public_asset_owner(self):
        for kind in media.KINDS:
            value, extra, reader = fixture(kind)
            items = media.project(value, media.parse_media(json.dumps(extra)), reader)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["kind"], kind)
            self.assertTrue(items[0]["url"].startswith(media.PREFIX))
            self.assertTrue(items[0]["source_page"].startswith("/gallery/"))
            with patch.object(media, "public_previews", return_value=items):
                self.assertEqual(len(media.media_assets()), 1)
                body = gallery_random.body(kind)
                self.assertIn("Test preview", body)
                self.assertIn("Source and editable files", body)
                self.assertNotIn("/api/v1/download", body)
                if kind != "image":
                    self.assertIn(" controls preload=\"none\"", body)
                    self.assertNotIn("autoplay", body)

    def test_stale_source_missing_bytes_and_changed_bytes_are_excluded(self):
        value, extra, reader = fixture()
        extra["items"][0]["source"]["version"] = "0" * 64
        self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), reader), ())
        value, extra, _ = fixture()
        def missing(_name):
            raise FileNotFoundError("test-only")
        for bad_reader in (missing, lambda _name: b"changed"):
            self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), bad_reader), ())

    def test_source_licence_alone_does_not_approve_a_new_preview(self):
        value, extra, reader = fixture(status="pending")
        self.assertEqual(value["items"][0]["licence"], "MIT")
        self.assertEqual(media.project(value, media.parse_media(json.dumps(extra)), reader), ())
        body = gallery_random.body("image")
        self.assertIn("Preview reuse licence", body)
        self.assertIn("Not separately recorded", body)
        self.assertIn("Source files licence", body)
        self.assertIn("Public display does not grant reuse rights", body)

    def test_schema_refuses_unknown_versions_unsafe_paths_formats_and_unbounded_media(self):
        _value, original, _reader = fixture()
        mutations = (
            lambda value: value.update(record_type="website_gallery_media/v99"),
            lambda value: value.update(private_key="not-a-real-key"),
            lambda value: value["items"].append(copy.deepcopy(value["items"][0])),
            lambda value: value["items"][0].update(kind="document"),
            lambda value: value["items"][0]["source"].update(slug="../account"),
            lambda value: value["items"][0]["source"].update(version="stale"),
            lambda value: value["items"][0].update(preview_licence=""),
            lambda value: value["items"][0]["review"].update(status="publisher-claims-approved"),
            lambda value: value["items"][0]["review"].update(reviewer=""),
            lambda value: value["items"][0]["preview"].update(file="../private.mp4"),
            lambda value: value["items"][0]["preview"].update(file="https://example.test/movie.mp4"),
            lambda value: value["items"][0]["preview"].update(media_type="text/html"),
            lambda value: value["items"][0]["preview"].update(media_type="audio/mpeg"),
            lambda value: value["items"][0]["preview"].update(bytes=media.MAX_FILE_BYTES + 1),
            lambda value: value["items"][0]["preview"].update(width=0),
            lambda value: value["items"][0]["preview"].update(duration_seconds=301),
        )
        for mutate in mutations:
            value = copy.deepcopy(original)
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                media.parse_media(json.dumps(value))

    def test_extra_item_and_aggregate_byte_caps_refuse(self):
        _, value, _ = fixture()
        row = value["items"][0]
        value["items"] = [{**row, "id": f"fixture-{index}"} for index in range(media.MAX_EXTRA_ITEMS + 1)]
        with self.assertRaises(ValueError):
            media.parse_media(json.dumps(value))
        value["items"] = [{**row, "id": f"fixture-{index}", "preview": {**row["preview"], "bytes": media.MAX_FILE_BYTES}}
                          for index in range(5)]
        with self.assertRaises(ValueError):
            media.parse_media(json.dumps(value))

    def test_empty_kind_and_unknown_routes_remain_explicit(self):
        value, _extra, reader = fixture()
        value["items"][0]["preview"] = None
        self.assertEqual(media.project(value, {"items": []}, reader), ())
        for kind in ("video", "music"):
            with patch.object(media, "public_previews", return_value=()):
                body = gallery_random.body(kind)
            self.assertIn(f"No public {kind} previews are available.", body)
            self.assertIn('"items":[]', body)
            self.assertNotIn("data-asset-card", body)
            self.assertNotIn("data-asset-download", body)
        for address in ("/random/nope", "/random/image/private", "/random/", "/random/IMAGE"):
            self.assertIsNone(gallery_page.rendered(address, "GET", "Baltor"))
        for method in ("POST", "DELETE", "PUT"):
            self.assertIsNone(gallery_page.rendered("/random", method, "Baltor"))

    def test_routes_have_static_export_navigation_and_asset_registration(self):
        addresses = static_addresses(include_model_details=False)
        for path in gallery_random.ROUTES:
            self.assertIn(path, addresses)
            for method in ("GET", "HEAD"):
                body, mime = gallery_page.rendered(path, method, "Baltor")
                self.assertEqual(mime, web_pages.HTML_MEDIA_TYPE)
                self.assertEqual(len(re.findall(r"<h1\b", body.decode())), 1)
                self.assertIn('id="random-title"', body.decode())
                self.assertIn(f'href="https://baltor.ai{path}"', body.decode())
                self.assertIn('href="/random"', body.decode())
        for asset in ("/assets/gallery-random.js", "/assets/gallery-random.css"):
            self.assertIn(asset, addresses)
            self.assertIn(asset, web_pages.CACHEABLE_WEB_ASSETS)

    def test_external_text_is_escaped_in_html_and_script_data(self):
        item = {**media.public_previews()[0], "title": '</script><script>alert("fixture")</script>',
                "summary": "<img onerror='fixture'>"}
        with patch.object(media, "public_previews", return_value=(item,)):
            body = gallery_random.body()
        self.assertNotIn(item["title"], body)
        self.assertNotIn(item["summary"], body)
        self.assertIn("&lt;/script&gt;", body)
        self.assertIn("\\u003c/script>", body)


if __name__ == "__main__":
    unittest.main()

"""Website-example provenance and source-only archive controls, without publication.

Synthetic media bytes test access and archive rules, not playback or ownership.
The original source's mathematical tests run separately through Node.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile
import unittest
import warnings
import zlib
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from loop_engine.core.service_runtime import gallery_media as media, gallery_random
from tools.test_gallery_random import fixture


def example_fixture(*, payload=None, mode=stat.S_IFREG, duplicate=False, suffix="source.mjs"):
    contents = {"README.md": b"Parser test instructions only.\n", "LICENSE": b"MIT License\nTest fixture, not rights evidence.\n",
                suffix: b"export const testOnly = true;\n" if payload is None else payload}
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as bundle:
        for name, data in contents.items():
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((mode if name == suffix else stat.S_IFREG) | 0o644) << 16
            info.compress_type = ZIP_DEFLATED
            bundle.writestr(info, data)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                bundle.writestr(suffix, contents[suffix])
    archive = stream.getvalue()
    digest = hashlib.sha256(archive).hexdigest()
    value, record, preview_reader = fixture()
    source = {"kind": "website_example", "identity": "website-example.fixture", "version": digest, "licence": "MIT",
              "archive": {"file": "fixture-source-" + digest[:12] + ".zip", "sha256": digest, "bytes": len(archive)},
              "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                        for name, data in contents.items()]}
    record["items"][0]["source"] = source
    def reader(name):
        return archive if name.endswith(".zip") else preview_reader(name)
    return value, record, reader, archive


def replace_last_deflate(body, replacement):
    """Synthetic ZIP mutation with consistent headers but an altered raw member stream."""
    value = bytearray(body)
    with ZipFile(io.BytesIO(body)) as archive:
        member = max(archive.infolist(), key=lambda row: row.header_offset)
        old_start = archive.start_dir
    local = member.header_offset
    name_length, extra_length = struct.unpack_from("<HH", value, local + 26)
    start = local + 30 + name_length + extra_length
    altered = replacement(bytes(value[start:old_start]))
    value[start:old_start] = altered
    new_start = start + len(altered)
    struct.pack_into("<I", value, local + 18, len(altered))
    cursor = new_start
    while value[cursor:cursor + 4] == b"PK\x01\x02":
        name, extra, comment = struct.unpack_from("<HHH", value, cursor + 28)
        if struct.unpack_from("<I", value, cursor + 42)[0] == local:
            struct.pack_into("<I", value, cursor + 20, len(altered))
        cursor += 46 + name + extra + comment
    struct.pack_into("<I", value, len(value) - 6, new_start)
    return bytes(value)


class WebsiteExampleTests(unittest.TestCase):
    def test_raw_deflate_cannot_hide_extra_bytes_or_escape_as_an_exception(self):
        _, record, _, body = example_fixture()
        origin = record["items"][0]["source"]
        def hidden_unpacked(raw):
            original = zlib.decompress(raw, -zlib.MAX_WBITS)
            encoder = zlib.compressobj(wbits=-zlib.MAX_WBITS)
            return encoder.compress(original + b"unlisted" * 20000) + encoder.flush()
        changes = (lambda raw: raw + b"UNLISTED-BINARY\x00not-source",
                   lambda raw: b"\xff" + raw[1:], lambda raw: raw[:-1], hidden_unpacked)
        for change in changes:
            altered = replace_last_deflate(body, change)
            source = copy.deepcopy(origin)
            digest = hashlib.sha256(altered).hexdigest()
            source["version"] = digest
            source["archive"] = {"file": "fixture-" + digest[:12] + ".zip", "sha256": digest, "bytes": len(altered)}
            with self.subTest(change=changes.index(change)):
                self.assertFalse(media.valid_source_archive(altered, source))

    def test_media_content_policy_allows_same_origin_only(self):
        from types import SimpleNamespace
        from loop_engine.core.service_runtime.http import ServiceHttpApplication
        from loop_engine.core.service_runtime.static_site_export import page_headers
        policy = ServiceHttpApplication._page_headers(SimpleNamespace(browser_identity=None))["Content-Security-Policy"]
        def permits_only_same_origin(value):
            fields = dict((part.split()[0], part.split()[1:]) for part in value.split(";") if part.strip())
            return fields.get("media-src") == ["'self'"]
        self.assertTrue(permits_only_same_origin(policy))
        self.assertFalse(permits_only_same_origin(policy.replace("media-src 'self';", "")))
        for wrong in ("*", "'self' blob:", "'self' https://outside.invalid"):
            self.assertFalse(permits_only_same_origin(policy.replace("media-src 'self';", "media-src " + wrong + ";")))
        self.assertEqual(page_headers()["Content-Security-Policy"], policy)

    def test_single_final_version_refuses_the_unpublished_prior_shape(self):
        self.assertEqual(media.RECORD_TYPE, "website_gallery_media/v2")
        with self.assertRaises(ValueError):
            media.parse_media('{"record_type":"website_gallery_media/v1","items":[]}')
        _, record, _, _ = example_fixture()
        for mutate in (lambda row: row.update(source_slug="unrelated-catalogue-item"),
                       lambda row: row["source"].update(identity="library.supply.false-claim"),
                       lambda row: row["source"].update(licence="unknown"),
                       lambda row: row.update(preview_licence="unknown")):
            bad = copy.deepcopy(record)
            mutate(bad["items"][0])
            with self.assertRaises(ValueError):
                media.parse_media(json.dumps(bad))

    def test_reviewed_website_source_is_distinct_from_any_catalogue_item(self):
        _value, record, reader, archive = example_fixture()
        parsed = media.parse_media(json.dumps(record))
        source = parsed["items"][0]["source"]
        self.assertTrue(media.valid_source_archive(archive, source))
        result = media.project({"items": []}, parsed, reader)
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item["source_kind"], "website_example")
        self.assertEqual(item["source_identity"], "website-example.fixture")
        self.assertEqual(item["source_version"], hashlib.sha256(archive).hexdigest())
        self.assertTrue(item["source_page"].startswith("/assets/gallery-media/"))
        self.assertTrue(item["source_page"].endswith(".zip"))
        with patch.object(media, "public_previews", return_value=result):
            assets = media.media_assets()
            self.assertEqual(len(assets), 2)
            self.assertEqual(assets[item["source_page"]][1], "application/zip")
            html = gallery_random.body("video")
            self.assertIn("Original website demo, not a library item", html)
            self.assertIn("Download editable source ZIP", html)
            self.assertIn("No account is needed for the source ZIP", html)
            self.assertNotIn("Source files licence", html)
            self.assertNotIn("/api/v1/download", html)

    def test_source_and_preview_are_both_held_until_review_and_exact_bytes(self):
        for status in ("pending", "rejected"):
            _value, record, reader, _archive = example_fixture()
            record["items"][0]["review"]["status"] = status
            self.assertEqual(media.project({"items": []}, media.parse_media(json.dumps(record)), reader), ())
        _value, record, reader, _archive = example_fixture()
        for corrupt in ("zip", "preview"):
            def damaged(name):
                return b"changed" if name.endswith(".zip") == (corrupt == "zip") else reader(name)
            self.assertEqual(media.project({"items": []}, media.parse_media(json.dumps(record)), damaged), ())

    def test_source_archive_rejects_links_duplicate_members_binary_and_secret_content(self):
        cases = ({"mode": stat.S_IFLNK}, {"mode": stat.S_IFIFO}, {"duplicate": True},
                 {"payload": b"binary\x00payload"}, {"payload": b"\xff\xfe"},
                 {"payload": ("sk" + "-" + "x" * 24).encode()},
                 {"payload": b"-----BEGIN " + b"PRIVATE KEY-----\nfixture"})
        for case in cases:
            _, record, reader, archive = example_fixture(**case)
            parsed = media.parse_media(json.dumps(record))
            with self.subTest(case=tuple(case)):
                self.assertFalse(media.valid_source_archive(archive, parsed["items"][0]["source"]))
            self.assertEqual(media.project({"items": []}, parsed, reader), ())

    def test_source_paths_and_inventory_are_strict_and_do_not_accept_dependencies(self):
        for suffix in ("../escape.py", "/absolute.py", "folder\\escape.py", "node_modules/a.js", ".env", "media.mp4", "nested.zip"):
            _, record, _, _ = example_fixture(suffix=suffix)
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                media.parse_media(json.dumps(record))
        _, record, _, _ = example_fixture()
        for mutate in (lambda source: source["archive"].update(bytes=media.MAX_SOURCE_ZIP_BYTES + 1),
                       lambda source: source.update(version="0" * 64),
                       lambda source: source["files"][0].update(bytes=media.MAX_SOURCE_FILE_BYTES + 1),
                       lambda source: source["files"].append(copy.deepcopy(source["files"][0])),
                       lambda source: source.update(files=source["files"][:1])):
            bad = copy.deepcopy(record)
            mutate(bad["items"][0]["source"])
            with self.assertRaises(ValueError):
                media.parse_media(json.dumps(bad))

    def test_archive_prefix_tail_comment_and_mismatched_members_are_refused(self):
        _, record, _reader, archive = example_fixture()
        source = record["items"][0]["source"]
        for body in (b"hidden prefix" + archive, archive + b"hidden tail"):
            bad = copy.deepcopy(source)
            digest = hashlib.sha256(body).hexdigest()
            bad["version"] = digest
            bad["archive"] = {"file": "fixture-" + digest[:12] + ".zip", "sha256": digest, "bytes": len(body)}
            self.assertFalse(media.valid_source_archive(body, bad))
        bad = copy.deepcopy(source)
        bad["files"][0]["sha256"] = "0" * 64
        self.assertFalse(media.valid_source_archive(archive, bad))

    def test_packaged_originals_have_exact_bounded_bytes_and_pending_entries_stay_private(self):
        record = media.media_record()
        examples = [row for row in record["items"] if row["source"]["kind"] == "website_example"]
        self.assertEqual({row["kind"] for row in examples}, {"video", "music"})
        self.assertEqual(len(examples), 2)
        public = media.media_assets()
        for row in examples:
            preview = row["preview"]
            body = media._read_asset(media.FOLDER + "/" + preview["file"])
            self.assertEqual(hashlib.sha256(body).hexdigest(), preview["sha256"])
            self.assertEqual(len(body), preview["bytes"])
            self.assertLessEqual(len(body), 2 * 1024 * 1024)
            self.assertLessEqual(preview["duration_seconds"], 16)
            source = row["source"]
            archive = media._read_source(media.FOLDER + "/" + source["archive"]["file"])
            self.assertTrue(media.valid_source_archive(archive, source))
            if row["review"]["status"] != "approved":
                self.assertNotIn(media.PREFIX + preview["file"], public)
                self.assertNotIn(media.PREFIX + source["archive"]["file"], public)

    def test_source_read_uses_its_smaller_bound(self):
        with patch.object(media, "_read_packaged", return_value=b"test") as reader:
            self.assertEqual(media._read_source("gallery-media/fixture.zip"), b"test")
            reader.assert_called_once_with("gallery-media/fixture.zip", media.MAX_SOURCE_ZIP_BYTES)

    def test_source_archive_is_reproducible_from_the_exact_owned_source(self):
        from tools.build_website_example_sources import build_archive
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "example.zip"
            report = build_archive(output)
            source = media.media_record()["items"][0]["source"]
            self.assertEqual(report["sha256"], source["version"])
            self.assertEqual(report["files"], source["files"])
            self.assertTrue(media.valid_source_archive(output.read_bytes(), source))
            with self.assertRaises(ValueError):
                build_archive(output)

    @unittest.skipUnless(shutil.which("node"), "Original deterministic source tests need Node")
    def test_original_musical_and_visual_source_controls(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([shutil.which("node"), "--test", str(root / "showcase/original-previews/test-originals.mjs")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

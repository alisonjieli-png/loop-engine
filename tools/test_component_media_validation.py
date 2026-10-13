"""Small MP4 qualification controls; native checks require explicit local tools.

Run native controls with Python exposing sealed memfd support:
PYTHONPATH=.:src:tools python tools/test_component_media_validation.py --media-tools CONFIG
No network, provider, model or publication effect occurs.
"""
import argparse
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools.component_qualification import checks
from tools.component_qualification import controls, qualify
from tools.component_qualification import media_validation as media
from tools.supply_lines.packaging import PackageFile, require_review_bounds
from tools.supply_lines.records import SupplyRecordError

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "src/loop_engine/core/service_runtime/web_assets/gallery-media/copper-current-b9b28ecda939.mp4"
TOOLS = None


def component(data, *, manifest=None, extra=None, line="creative_originals"):
    source = b"/* fixture render source */\n"
    payloads = {"clip.mp4": data, "scene.mjs": source, **(extra or {})}
    value = manifest if manifest is not None else {"record_type": media.MANIFEST_VERSION, "resources": [{
        "path": "clip.mp4", "sha256": hashlib.sha256(data).hexdigest(), "role": "original", "original": None,
        "source_files": [{"path": "scene.mjs", "sha256": hashlib.sha256(source).hexdigest()}]}]}
    payloads[media.MANIFEST_NAME] = json.dumps(value).encode()
    files = [SimpleNamespace(path=path, media_type="video/mp4" if path.endswith(".mp4") else "text/plain") for path in payloads]
    return SimpleNamespace(line=line, package=SimpleNamespace(files=files), payloads=payloads,
                           text=lambda path: payloads[path].decode("utf-8") if not path.endswith(".mp4") else None,
                           candidate={})


class StructuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = VIDEO.read_bytes()

    def test_exact_published_original_structure(self):
        result = media.mp4_structure(self.data)
        self.assertEqual(result["tracks"], 1)
        self.assertEqual(result["codecs"], ["avc1"])
        self.assertLess(result["boxes"], media.MAX_BOXES)

    def test_truncation_junk_fragment_and_extended_overflow_refuse(self):
        for wrong in (self.data[:-1], self.data + b"junk", self.data + struct.pack(">I4s", 8, b"moof"),
                      bytes(4) + self.data[4:], struct.pack(">I4sQ", 1, b"ftyp", 2**64 - 1) + self.data[8:]):
            with self.subTest(length=len(wrong)), self.assertRaises(media.MediaValidationError):
                media.mp4_structure(wrong)

    def test_box_count_depth_and_file_bounds_cannot_be_widened_by_input(self):
        for field, value in (("MAX_BOXES", 1), ("MAX_DEPTH", 0), ("MAX_FILE_BYTES", len(self.data) - 1)):
            with self.subTest(field=field), mock.patch.object(media, field, value), self.assertRaises(media.MediaValidationError):
                media.mp4_structure(self.data)

    def test_external_url_or_urn_reference_refused(self):
        offset = self.data.index(b"url ")
        for wrong in (self.data[:offset] + b"urn " + self.data[offset + 4:],
                      self.data[:offset + 4] + bytes(4) + self.data[offset + 8:]):
            with self.assertRaisesRegex(media.MediaValidationError, "external_data_reference"):
                media.mp4_structure(wrong)

    def test_chunk_outside_mdat_refused(self):
        offset = self.data.index(b"stco") + 12
        wrong = self.data[:offset] + bytes(4) + self.data[offset + 4:]
        with self.assertRaisesRegex(media.MediaValidationError, "chunk_outside_media"):
            media.mp4_structure(wrong)

    def test_inflated_sample_length_and_unknown_metadata_refuse(self):
        offset = self.data.index(b"stsz") + 16
        size, = struct.unpack_from(">I", self.data, offset)
        wrong = self.data[:offset] + struct.pack(">I", size + 1) + self.data[offset + 4:]
        with self.assertRaisesRegex(media.MediaValidationError, "unbound_media_bytes"):
            media.mp4_structure(wrong)
        wrong = self.data.replace(b"\xa9nam", b"uuid", 1)
        with self.assertRaisesRegex(media.MediaValidationError, "box_unsupported"):
            media.mp4_structure(wrong)

    def test_atom_profile_is_not_a_blanket_extension_or_mime_permission(self):
        for path, kind in (("clip.jpg", "video/mp4"), ("clip.mp4", "application/octet-stream"),
                           ("clip.webp", "image/webp"), ("clip.glb", "model/gltf-binary")):
            entry = SimpleNamespace(path=path, media_type=kind)
            self.assertEqual(checks._binary_findings(entry, self.data), [("binary_file_unverified", path)])
        self.assertEqual(checks._binary_findings(SimpleNamespace(path="clip.mp4", media_type="video/mp4"), self.data),
                         [("binary_file_unverified", "clip.mp4")])


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.data = b"exact byte fixture"
        self.component = component(self.data)

    def test_original_is_bound_to_exact_render_source_and_resource(self):
        row = media.manifest_binding(self.component, "clip.mp4")
        self.assertEqual(row["role"], "original")

    def test_missing_false_or_duplicate_manifest_refuses(self):
        for value in ({}, {"record_type": "unknown/v1", "resources": []},
                      {"record_type": media.MANIFEST_VERSION, "resources": [{"path": []}]}):
            with self.subTest(value=value), self.assertRaises(media.MediaValidationError):
                media.manifest_binding(component(self.data, manifest=value), "clip.mp4")
        self.component.payloads[media.MANIFEST_NAME] = b'{"record_type":"x","record_type":"y"}'
        with self.assertRaises(media.MediaValidationError):
            media.manifest_binding(self.component, "clip.mp4")

    def test_wrong_source_digest_unlisted_path_and_missing_source_refuse(self):
        original = json.loads(self.component.payloads[media.MANIFEST_NAME])
        for field, value in (("sha256", "a" * 64), ("path", "another.mp4"), ("source_files", []),
                             ("source_files", [{"path": "missing.py", "sha256": "a" * 64}]), ("role", "preview-ish")):
            wrong = copy.deepcopy(original)
            wrong["resources"][0][field] = value
            with self.subTest(field=field), self.assertRaises(media.MediaValidationError):
                media.manifest_binding(component(self.data, manifest=wrong), "clip.mp4")

    def test_derivative_needs_an_exact_original_in_the_package(self):
        original = json.loads(self.component.payloads[media.MANIFEST_NAME])
        preview = b"actual derivative bytes"
        original["resources"].append({"path": "preview.mp4", "sha256": hashlib.sha256(preview).hexdigest(),
            "role": "derivative", "original": {"path": "clip.mp4", "sha256": hashlib.sha256(self.data).hexdigest()},
            "source_files": original["resources"][0]["source_files"]})
        value = component(self.data, manifest=original, extra={"preview.mp4": preview})
        self.assertEqual(media.manifest_binding(value, "preview.mp4")["role"], "derivative")
        original["resources"][1]["original"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(media.MediaValidationError, "binding_mismatch"):
            media.manifest_binding(component(self.data, manifest=original, extra={"preview.mp4": preview}), "preview.mp4")

    def test_wrong_supply_line_cannot_enable_media_profile(self):
        with self.assertRaisesRegex(media.MediaValidationError, "supply_line_unsupported"):
            media.manifest_binding(component(self.data, line="function_extracts"), "clip.mp4")

    def test_binary_and_utf8_container_metadata_are_secret_scanned(self):
        value = component(b"fixture-sensitive")
        context = SimpleNamespace(secret_patterns=(re.compile("fixture-sensitive"),))
        result = checks.SecretsCheck().run(value, context)
        self.assertEqual(result.status, checks.REFUSED)
        self.assertIn("binary strings", result.findings[0][1])
        self.assertNotIn("fixture-sensitive", str(result.findings))


class BoundsAndMetadataTests(unittest.TestCase):
    def test_custom_sandbox_launcher_is_not_a_qualified_profile(self):
        with self.assertRaisesRegex(media.MediaValidationError, "sandbox_launcher_unqualified"):
            media.MediaTools("/safe/ffmpeg", "a" * 64, "/safe/ffprobe", "b" * 64, bwrap="/tmp/fake-bwrap")
    def test_only_manifest_bound_creative_mp4_uses_catalogue_bounds(self):
        data = bytes(300000)
        value = component(data)
        rows = [PackageFile(entry.path, value.payloads[entry.path], "skill_asset", media_type=entry.media_type)
                for entry in value.package.files]
        package = SimpleNamespace(line="creative_originals", name="Test resource")
        require_review_bounds(package, rows)
        for wrong in (SimpleNamespace(line="function_extracts", name="Other line"),):
            with self.assertRaisesRegex(SupplyRecordError, "package_above_review_bound"):
                require_review_bounds(wrong, rows)
        with self.assertRaises(SupplyRecordError):
            require_review_bounds(package, [row for row in rows if row.path != media.MANIFEST_NAME])
        bad = [replace(row, data=bytes(media.MAX_FILE_BYTES + 1)) if row.path == "clip.mp4" else row for row in rows]
        with self.assertRaisesRegex(SupplyRecordError, "package_above_review_bound"):
            require_review_bounds(package, bad)
        for path, kind in (("image.png", "image/png"), ("large.txt", "text/plain")):
            with self.assertRaisesRegex(SupplyRecordError, "package_above_review_bound"):
                require_review_bounds(package, rows + [PackageFile(path, data, "skill_asset", media_type=kind)])
        bad = [replace(row, path="clip.bin") if row.path == "clip.mp4" else row for row in rows]
        with self.assertRaises(SupplyRecordError):
            require_review_bounds(package, bad)

    def test_declared_facts_have_closed_numeric_and_codec_profile(self):
        value = {"format": {"duration": "1"}, "streams": [{"codec_type": "video", "codec_name": "h264",
            "width": 320, "height": 180, "pix_fmt": "yuv420p", "field_order": "progressive",
            "disposition": {"attached_pic": 0}, "avg_frame_rate": "30/1", "nb_frames": "30"}]}
        self.assertEqual(media.metadata(value)["frames"], 30)
        for field, wrong in (("width", 999999), ("height", True), ("codec_name", "hevc"), ("pix_fmt", "yuv444p"),
                             ("avg_frame_rate", "0/0"), ("avg_frame_rate", "1000/1"), ("nb_frames", "0"),
                             ("disposition", {"attached_pic": 1}), ("field_order", "tt")):
            changed = copy.deepcopy(value)
            changed["streams"][0][field] = wrong
            with self.subTest(field=field), self.assertRaises(media.MediaValidationError):
                media.metadata(changed)
        boundary = copy.deepcopy(value)
        boundary["format"]["duration"] = "120"
        boundary["streams"][0]["nb_frames"] = "3600"
        self.assertEqual(media.metadata(boundary)["duration_seconds"], 120)
        for duration in ("NaN", "Infinity", "120.001", "121", "0", "1000000000000000000"):
            changed = copy.deepcopy(value)
            changed["format"]["duration"] = duration
            with self.subTest(duration=duration), self.assertRaises(media.MediaValidationError):
                media.metadata(changed)

    def test_sandbox_has_only_pinned_descriptor_inputs_and_no_network_or_host_mount(self):
        tools = media.MediaTools("/safe/ffmpeg", "a" * 64, "/safe/ffprobe", "b" * 64)
        argv = media.sandbox_command(tools, 7, 8, ["-version"])
        self.assertIn("--unshare-all", argv)
        self.assertIn("--clearenv", argv)
        self.assertNotIn("--share-net", argv)
        self.assertNotIn("--ro-bind", argv)
        self.assertEqual(argv.count("--ro-bind-data"), 2)


class NativeTests(unittest.TestCase):
    def setUp(self):
        if TOOLS is None or not hasattr(os, "memfd_create"):
            self.skipTest("explicit native tools and sealed memfd support required")
        self.tools = TOOLS

    def test_actual_full_decode_with_no_host_or_network_access(self):
        result = media.validate(VIDEO.read_bytes(), self.tools)
        self.assertTrue(result["decode_complete"])
        self.assertEqual(result["frames"], 288)
        self.assertEqual(result["width"], 960)
        self.assertEqual(result["ffmpeg_sha256"], self.tools.ffmpeg_sha256)
        self.assertNotIn("text_metadata", result["structure"])
        self.assertFalse(result["limits"]["cgroup_task_limit_enforced"])
        self.assertNotIn("tasks", result["limits"])
        self.assertEqual(result["limits"]["tmp_bytes"], 8 * 1024 * 1024)

    def test_corrupted_packet_refuses_full_native_decode(self):
        data = VIDEO.read_bytes()
        offset = data.index(b"mdat") + 4
        bad = data[:offset] + b"\x7f\xff\xff\xff" + data[offset + 4:]
        media.mp4_structure(bad)
        with self.assertRaises(media.MediaValidationError):
            media.validate(bad, self.tools)

    def test_symlink_hash_mismatch_and_original_tool_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "decoder"
            target.write_bytes(b"original trusted tool bytes")
            target.chmod(0o700)
            link = root / "link"
            link.symlink_to(target)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            with self.assertRaisesRegex(media.MediaValidationError, "symlink_refused"):
                media.pinned_tool(str(link), digest)
            with self.assertRaisesRegex(media.MediaValidationError, "digest_mismatch"):
                media.pinned_tool(str(target), "0" * 64)
            fd = media.pinned_tool(str(target), digest)
            try:
                target.write_bytes(b"concurrent changed executable")
                self.assertEqual(os.read(fd, 100), b"original trusted tool bytes")
                with self.assertRaises(OSError):
                    os.write(fd, b"change sealed bytes")
            finally:
                os.close(fd)

    def test_unavailable_sandbox_refuses_without_unsandboxed_fallback(self):
        with mock.patch.object(media.subprocess, "Popen", side_effect=FileNotFoundError) as popen:
            with self.assertRaisesRegex(media.MediaValidationError, "unavailable"):
                media.validate(VIDEO.read_bytes(), self.tools)
            self.assertEqual(popen.call_count, 1)

    def test_timeout_and_output_limits_refuse(self):
        for field in ("WALL_SECONDS", "MAX_OUTPUT_BYTES"):
            with self.subTest(field=field), mock.patch.object(media, field, 0), self.assertRaises(media.MediaValidationError):
                media.validate(VIDEO.read_bytes(), self.tools)

    def test_parse_integration_requires_manifest_and_records_exact_decode(self):
        value = component(VIDEO.read_bytes())
        context = SimpleNamespace(media_tools=self.tools)
        row = value.package.files[0]
        notes = []
        self.assertEqual(checks._binary_findings(row, value.payloads[row.path], component=value, context=context, notes=notes), [])
        self.assertTrue(json.loads(notes[0])["decode_complete"])
        value.payloads.pop(media.MANIFEST_NAME)
        self.assertTrue(checks._binary_findings(row, value.payloads[row.path], component=value, context=context))


class ReuseTests(unittest.TestCase):
    def record(self):
        return {"record_version": "v1", "package_digest": "a" * 64,
            "qualifier": {"code_revision": "b" * 40, "uncommitted_changes": False},
            "checks": [{"check_id": "parse", "status": checks.PASSED, "notes": []}]}

    def test_configured_native_record_cannot_be_reused_in_default_or_changed_tool_run(self):
        row = {"record_version": "v1", "package_digest": "a" * 64}
        record = self.record()
        self.assertTrue(qualify.reusable(record, row, "b" * 40, check_ids=("parse",)))
        for digest in ("c" * 64, "d" * 64):
            record["media_decoder"] = {"configured": True, "ffmpeg_sha256": digest}
            self.assertFalse(qualify.reusable(record, row, "b" * 40, check_ids=("parse",)))
        record.pop("media_decoder")
        record["checks"][0]["notes"] = [json.dumps({"record_type": "component_media_decode/v1"})]
        self.assertFalse(qualify.reusable(record, row, "b" * 40, check_ids=("parse",)))

    def test_actual_mp4_package_cannot_skip_parse_even_with_markerless_cached_record(self):
        fixture = controls.code_fixture("b" * 40)
        target = fixture.package.files[0].path
        package = type(fixture.package)(tuple(replace(entry, media_type="video/mp4") if entry.path == target else entry
                                              for entry in fixture.package.files), fixture.package.body_form)
        fixture = replace(fixture, package=package)
        context = checks.QualificationContext.load(ROOT)
        old = {"checks": [{"check_id": "parse", "status": checks.PASSED}], "qualified_at": "old"}
        values = {"context": context, "bodies": None, "reuse": {fixture.identity: old}, "check_ids": ("parse",)}
        with mock.patch.dict(qualify._WORKER, values, clear=True), mock.patch.object(qualify, "_full_row", return_value={}), \
                mock.patch.object(qualify, "component_from_row", return_value=fixture), \
                mock.patch.object(qualify, "_comparison", return_value={}):
            result = qualify._check_one({"record_id": fixture.identity})
        self.assertNotIn("reused_from", result)
        self.assertFalse(result["media_decoder"]["configured"])
        self.assertEqual(result["checks"][0]["status"], checks.REFUSED)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--media-tools", type=Path)
    selected, remaining = parser.parse_known_args()
    TOOLS = media.MediaTools.read(selected.media_tools) if selected.media_tools else None
    unittest.main(argv=[sys.argv[0], *remaining])

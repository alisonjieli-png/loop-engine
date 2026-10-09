"""The creative original framework: PNG codec, record readers, package assembly, evidence binding, the CLIs.

Each guard has a known-wrong control: a corrupted PNG, a malformed record, stale evidence, a failing package test.
No engine runs here; the native verifier in the temporary family is a stand-in that only reads files.
"""
from __future__ import annotations

import io
import json
import shutil
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from pathlib import Path

from tools.creative_originals import assemble, check, media, pngio, records, verify

SHARED_TEST = '''"""The package checks itself against component.json; a broken copy must be refused."""
import json
import unittest
from pathlib import Path
from tally import tally

ROOT = Path(__file__).parent
CARD = json.loads((ROOT / "component.json").read_text())


class PackageTests(unittest.TestCase):
    def test_files_match_card(self):
        import hashlib
        for row in CARD["files"]:
            self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_known_answer(self):
        self.assertEqual(tally(CARD["contract"]["values"]), CARD["contract"]["total"])

    def test_known_wrong(self):
        self.assertNotEqual(tally(CARD["contract"]["values"] + [1]), CARD["contract"]["total"])
'''
TALLY = 'def tally(values):\n    """The sum of a list of integers."""\n    return sum(int(value) for value in values)\n'
NATIVE = '''def verify(context):
    from tools.creative_originals import pngio
    text = (context.item_dir / "shape.txt").read_text()
    ok = text.strip() == "square"
    pixels = bytes([0, 64, 128, 255] * 16)
    return {"engine": {"name": "stand_in", "version": "1"},
            "checks": [{"name": "shape_text", "state": "passed" if ok else "failed", "detail": {"text": text.strip()}}],
            "preview": pngio.encode(4, 4, pixels, 4)}
'''


def make_family(root: Path, *, verifier: bool = True) -> Path:
    family = root / "demo_family"
    (family / "shared").mkdir(parents=True)
    (family / "shared" / "test_package.py").write_text(SHARED_TEST)
    (family / "shared" / "tally.py").write_text(TALLY)
    if verifier:
        (family / "native.py").write_text(NATIVE)
    (family / "family.json").write_text(json.dumps({
        "record_type": records.FAMILY_RECORD, "family": "demo_family", "title": "Demo family",
        "description": "A temporary family for framework tests.", "engine": {"name": "python", "minimum_version": "3.10"},
        "shared_files": [{"path": "test_package.py", "role": "executable_tool"},
                         {"path": "tally.py", "role": "executable_tool"}],
        "native_verifier": "native.py" if verifier else None, "generator_version": "1.0.0",
        "default_dimension": "none"}))
    add_item(family, "square_item", "Square item", [1, 2, 3], 6)
    return family


def add_item(family: Path, identity: str, title: str, values: list, total: int, shape: str = "square") -> Path:
    item = family / "items" / identity
    item.mkdir(parents=True)
    (item / "README.md").write_text(f"# {title}\n\nAdds integers.\n")
    (item / "shape.txt").write_text(shape + "\n")
    (item / "item.json").write_text(json.dumps({
        "record_type": records.ITEM_RECORD, "identity": identity, "title": title,
        "purpose": "Add a list of integers.", "form": "function", "dimension": "none",
        "engine": {"name": "python", "minimum_version": "3.10"}, "tags": ["demo", "sum"],
        "files": [{"path": "README.md", "role": "other"}, {"path": "shape.txt", "role": "skill_asset"}],
        "contract": {"values": values, "total": total}, "limits": "Integers only."}))
    return item


class PngTests(unittest.TestCase):
    def test_round_trip_every_channel_count(self):
        for channels in (1, 2, 3, 4):
            pixels = bytes((x * 37 + y * 11 + c * 5) % 256 for y in range(9) for x in range(7) for c in range(channels))
            data = pngio.encode(7, 9, pixels, channels)
            image = pngio.decode(data)
            self.assertEqual((image["width"], image["height"], image["channels"]), (7, 9, channels))
            self.assertEqual(image["pixels"], pixels)
            self.assertEqual(data, pngio.encode(7, 9, pixels, channels), "the encoder is deterministic")

    def test_sixteen_bit_round_trip(self):
        pixels = b"".join(struct.pack(">H", value) for value in range(0, 65535, 4369))[:2 * 3 * 4]
        pixels = pixels + bytes(2 * 3 * 4 - len(pixels))
        self.assertEqual(pngio.decode(pngio.encode(4, 3, pixels, 1, bit_depth=16))["pixels"], pixels)

    def test_known_wrong_images_are_refused(self):
        good = pngio.encode(4, 4, bytes(range(48)), 3)
        flipped = bytearray(good)
        flipped[-20] ^= 0xFF  # inside the last chunks: a CRC must fail
        cases = {"signature_invalid": b"\x89PNX" + good[4:], "crc_mismatch": bytes(flipped),
                 "trailing_bytes": good + b"x", "chunk_truncated": good[:-6]}
        for reason, data in cases.items():
            with self.subTest(reason=reason), self.assertRaises(pngio.PngError) as caught:
                pngio.decode(data)
            self.assertEqual(caught.exception.reason, reason)

    def test_short_data_stream_is_refused(self):
        header = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
        short = zlib.compress(bytes(1 + 12) * 3)  # three rows where four are declared
        data = (pngio.SIGNATURE + pngio._chunk(b"IHDR", header) + pngio._chunk(b"IDAT", short)
                + pngio._chunk(b"IEND", b""))
        with self.assertRaises(pngio.PngError) as caught:
            pngio.decode(data)
        self.assertEqual(caught.exception.reason, "data_length_wrong")

    def test_bad_filter_and_interlace_are_refused(self):
        header = struct.pack(">IIBBBBB", 2, 1, 8, 0, 0, 0, 0)
        bad_filter = (pngio.SIGNATURE + pngio._chunk(b"IHDR", header) + pngio._chunk(b"IDAT", zlib.compress(b"\x07ab"))
                      + pngio._chunk(b"IEND", b""))
        with self.assertRaises(pngio.PngError) as caught:
            pngio.decode(bad_filter)
        self.assertEqual(caught.exception.reason, "filter_invalid")
        interlaced = struct.pack(">IIBBBBB", 2, 1, 8, 0, 0, 0, 1)
        data = (pngio.SIGNATURE + pngio._chunk(b"IHDR", interlaced) + pngio._chunk(b"IDAT", zlib.compress(b"\x00ab"))
                + pngio._chunk(b"IEND", b""))
        with self.assertRaises(pngio.PngError) as caught:
            pngio.decode(data)
        self.assertEqual(caught.exception.reason, "interlace_unsupported")


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.family = make_family(self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_reads_family_and_item(self):
        family = records.read_family(self.family)
        item = records.read_item(self.family, "square_item", family)
        self.assertEqual(item["title"], "Square item")
        self.assertEqual(records.item_identities(self.family), ["square_item"])

    def test_known_wrong_items_are_refused(self):
        path = self.family / "items" / "square_item" / "item.json"
        original = json.loads(path.read_text())
        cases = {"item_keys_invalid": {**original, "colour": "red"},
                 "form_invalid": {**original, "form": "skill"},
                 "asset_role_required": {**original, "form": "three_d_model"},
                 "dimension_invalid": {**original, "dimension": "5d"},
                 "tags_invalid": {**original, "tags": ["Upper Case", "x"]},
                 "file_missing": {**original, "files": original["files"] + [{"path": "gone.txt", "role": "other"}]},
                 "readme_missing": {**original, "files": [row for row in original["files"] if row["path"] != "README.md"]},
                 "file_path_conflict": {**original, "files": original["files"] + [{"path": "component.json",
                                                                                   "role": "other"}]}}
        for reason, value in cases.items():
            with self.subTest(reason=reason):
                path.write_text(json.dumps(value))
                with self.assertRaises(records.CreativeRecordError) as caught:
                    records.read_item(self.family, "square_item")
                self.assertEqual(caught.exception.reason, reason)
        path.write_text(json.dumps(original))
        (path.parent / "stray.txt").write_text("not declared")
        with self.assertRaises(records.CreativeRecordError) as caught:
            records.read_item(self.family, "square_item")
        self.assertEqual(caught.exception.reason, "file_undeclared")

    def test_duplicate_keys_and_titles_and_paths(self):
        path = self.family / "items" / "square_item" / "item.json"
        path.write_text(path.read_text()[:-1] + ', "title": "Again"}')
        with self.assertRaises(records.CreativeRecordError) as caught:
            records.read_item(self.family, "square_item")
        self.assertEqual(caught.exception.reason, "duplicate_key")
        for bad in ("../x", "/abs", "a\\b", ".git/config"):
            with self.subTest(path=bad), self.assertRaises(records.CreativeRecordError):
                records.safe_relative(bad)

    def test_unsupported_binary_suffix_is_refused(self):
        self.assertEqual(media.media_type("scene.tscn"), "text/x-godot-scene")
        self.assertTrue(media.is_text(media.media_type("model.gltf")))
        for name in ("scene.blend", "model.fbx", "sky.exr", "photo.jpg", "model.glb"):
            with self.subTest(name=name), self.assertRaises(records.CreativeRecordError):
                media.media_type(name)


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.family = make_family(self.root)
        self.evidence = self.root / "evidence"

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_verify(self, *extra):
        with redirect_stdout(io.StringIO()):
            return verify.main(["--family", "demo_family", "--root", str(self.root), "--output", str(self.evidence),
                                *extra])

    def test_verify_then_assemble_then_test(self):
        self.assertEqual(self.run_verify(), 0)
        record = self.evidence / "demo_family" / "square_item.json"
        evidence = record.read_bytes()
        preview = record.with_suffix(".png").read_bytes()
        entries = assemble.package_entries(self.family, "square_item", evidence=evidence, preview=preview)
        paths = [entry.path for entry in entries]
        self.assertEqual(paths, sorted(["README.md", "shape.txt", "test_package.py", "tally.py", "component.json",
                                        "verification/native.json", "preview.png"]))
        card = json.loads(next(entry.data for entry in entries if entry.path == "component.json"))
        self.assertEqual(card["job"], {"family": "demo_family", "identity": "square_item"})
        self.assertEqual(card["verification"]["native"]["state"], "passed")
        result = assemble.assemble_and_test(self.family, "square_item", self.root / "packages", evidence=evidence,
                                            preview=preview, licence=b"MIT\n")
        self.assertEqual(result["state"], "passed", result)
        self.assertEqual(self.run_verify(), 0, "an unchanged item reuses its record")

    def test_stale_or_failed_or_missing_evidence_is_refused(self):
        self.assertEqual(self.run_verify(), 0)
        record = self.evidence / "demo_family" / "square_item.json"
        evidence, preview = record.read_bytes(), record.with_suffix(".png").read_bytes()
        with self.assertRaises(records.CreativeRecordError) as caught:
            assemble.package_entries(self.family, "square_item")
        self.assertEqual(caught.exception.reason, "evidence_missing")
        with self.assertRaises(records.CreativeRecordError) as caught:
            assemble.package_entries(self.family, "square_item", evidence=evidence, preview=preview[:-1] + b"x")
        self.assertEqual(caught.exception.reason, "preview_mismatch")
        (self.family / "items" / "square_item" / "shape.txt").write_text("circle\n")
        with self.assertRaises(records.CreativeRecordError) as caught:
            assemble.package_entries(self.family, "square_item", evidence=evidence, preview=preview)
        self.assertEqual(caught.exception.reason, "evidence_stale")
        self.assertEqual(self.run_verify(), 1, "the native stand-in fails on the changed shape")
        failed = json.loads(record.read_bytes())
        self.assertEqual(failed["state"], "failed")
        self.assertIsNone(failed["preview"])
        with self.assertRaises(records.CreativeRecordError) as caught:
            assemble.package_entries(self.family, "square_item", evidence=record.read_bytes())
        self.assertEqual(caught.exception.reason, "native_check_failed")

    def test_a_changed_verifier_makes_old_evidence_stale(self):
        self.assertEqual(self.run_verify(), 0)
        record = self.evidence / "demo_family" / "square_item.json"
        evidence, preview = record.read_bytes(), record.with_suffix(".png").read_bytes()
        self.assertEqual(json.loads(evidence)["verifier_digest"],
                         assemble.verifier_digest(self.family, records.read_family(self.family)))
        # Known wrong: the verifier changes while the item does not; the old record no longer proves anything.
        native = self.family / "native.py"
        native.write_text(native.read_text() + "\n# a changed verifier\n")
        with self.assertRaises(records.CreativeRecordError) as caught:
            assemble.package_entries(self.family, "square_item", evidence=evidence, preview=preview)
        self.assertEqual(caught.exception.reason, "evidence_stale")
        self.assertEqual(self.run_verify(), 0, "the changed verifier runs again instead of reusing the record")
        fresh = record.read_bytes()
        self.assertNotEqual(json.loads(fresh)["verifier_digest"], json.loads(evidence)["verifier_digest"])
        assemble.package_entries(self.family, "square_item", evidence=fresh, preview=record.with_suffix(".png").read_bytes())
        # A support file beside native.py counts as the verifier too; bytecode does not.
        (self.family / "support").mkdir()
        (self.family / "support" / "fixture.txt").write_text("fixture\n")
        before = assemble.verifier_digest(self.family, records.read_family(self.family))
        self.assertNotEqual(before, json.loads(fresh)["verifier_digest"])
        (self.family / "__pycache__").mkdir(exist_ok=True)
        (self.family / "__pycache__" / "native.cpython-310.pyc").write_bytes(b"cache")
        self.assertEqual(assemble.verifier_digest(self.family, records.read_family(self.family)), before)

    def test_failing_package_test_is_reported(self):
        self.assertEqual(self.run_verify(), 0)
        item = self.family / "items" / "square_item" / "item.json"
        value = json.loads(item.read_text())
        value["contract"]["total"] = 7  # a wrong known answer
        item.write_text(json.dumps(value))
        self.assertEqual(self.run_verify(), 0)
        with redirect_stdout(io.StringIO()):
            status = check.main(["--family", "demo_family", "--root", str(self.root), "--evidence", str(self.evidence),
                                 "--packages", str(self.root / "packages")])
        self.assertEqual(status, 1)

    def test_check_refuses_copied_items(self):
        add_item(self.family, "square_copy", "Square copy", [1, 2, 3], 6)
        self.assertEqual(self.run_verify(), 0)
        output = io.StringIO()
        with redirect_stdout(output):
            status = check.main(["--family", "demo_family", "--root", str(self.root), "--evidence", str(self.evidence),
                                 "--packages", str(self.root / "packages")])
        self.assertEqual(status, 1)
        report = json.loads(output.getvalue()[output.getvalue().index("{\n"):])
        self.assertEqual(report["duplicates"][0]["reason"], "file_bytes_repeated")

    def test_verifier_exception_is_a_failure(self):
        (self.family / "native.py").write_text("def verify(context):\n    raise RuntimeError('broken verifier')\n")
        self.assertEqual(self.run_verify(), 1)
        record = json.loads((self.evidence / "demo_family" / "square_item.json").read_text())
        self.assertEqual(record["checks"][0]["name"], "verifier_error")


if __name__ == "__main__":
    unittest.main()

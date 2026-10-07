"""The Cloudflare edge operator tools, offline: export, sampling, upload payloads and the network guard.

`tools/cloudflare_d1_search.py` and `tools/cloudflare_site_edge.py` talk to a Worker only with
--authorize-network; everything they build before that is checked here against a bundle written by the release
checks' own fixture, with no network and no Cloudflare account.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import cloudflare_d1_search as d1_tool  # noqa: E402
import cloudflare_site_edge as site_tool  # noqa: E402
from loop_engine.core.service_runtime import catalogue_d1_index as d1  # noqa: E402
from loop_engine.core.service_runtime import static_site_export as site  # noqa: E402


class ExportFromABundle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from loop_engine.core.service_runtime.catalogue_d1_index_checks import CHECK_SCHEMA
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        cls.temp = tempfile.TemporaryDirectory(prefix="cloudflare-edge-tools-")
        root = Path(cls.temp.name)
        fixture = Fixture(root / "store")
        lines = [fixture.line(f"tool_item_{n:02d}", f"# item {n}\npython data {n}\n",
                              attributes={"domain": ["data"], "origin_layer": "code_intelligence"},
                              purpose=f"Python data helper number {n}") for n in range(12)]
        cls.bundle = fixture.bundle(lines, schema=CHECK_SCHEMA)
        cls.out = root / "export"
        original = d1_tool.read_live_bundle
        d1_tool.read_live_bundle = lambda _folder: cls.bundle
        try:
            cls.summary = d1_tool.export(cls.bundle.folder, cls.out, sample=5)
        finally:
            d1_tool.read_live_bundle = original

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_a_sample_is_the_same_every_run_and_keeps_the_named_identities(self):
        keep = {"tool_item_07"}
        first = d1_tool.sample_positions(self.bundle, 5, keep)
        self.assertEqual(first, d1_tool.sample_positions(self.bundle, 5, keep))
        self.assertIn("tool_item_07", first)
        self.assertEqual(len(first), 5)
        self.assertEqual(len(d1_tool.sample_positions(self.bundle, None, keep)), 12)

    def test_the_export_writes_a_build_its_entries_and_every_vector_column(self):
        build = json.loads((self.out / "build.json").read_text())
        self.assertEqual(build["record_type"], d1.BUILD_RECORD_TYPE)
        self.assertEqual(build["entries"], 5)
        self.assertTrue(build["release_id"].endswith("+sample5"))
        self.assertEqual(len(list((self.out / "vectors").iterdir())), d1.VECTOR_DIMENSIONS)
        self.assertEqual(self.summary["build_id"], build["build_id"])
        reloaded = d1_tool.load_export(self.out)
        self.assertEqual(reloaded.build_id, build["build_id"])

    def test_changed_vector_columns_are_refused_before_any_upload(self):
        column = self.out / "vectors" / "007.f32"
        original = column.read_bytes()
        try:
            column.write_bytes(original[:-4] + b"\x00\x00\x80\x3f")
            with self.assertRaises(SystemExit):
                d1_tool.load_export(self.out)
        finally:
            column.write_bytes(original)

    def test_an_upload_payload_carries_the_build_every_digest_and_the_columns_in_order(self):
        exported = d1_tool.load_export(self.out)
        payload = d1.vector_upload_payload(exported, [3, 1])
        self.assertEqual(payload[:8], d1.VECTOR_UPLOAD_MAGIC)
        length = int.from_bytes(payload[8:12], "little")
        header = json.loads(payload[12:12 + length])
        self.assertEqual(header["build_id"], exported.build_id)
        self.assertEqual(header["dimensions"], [3, 1])
        self.assertEqual(payload[12 + length:], exported.columns[3] + exported.columns[1])
        with self.assertRaises(Exception):
            d1.vector_upload_payload(exported, [1, 1])


class SiteLoadPayloads(unittest.TestCase):

    def test_a_load_names_each_file_by_its_digest_and_the_manifest_by_the_export(self):
        export = site.SiteExport({"record_type": site.MANIFEST_RECORD_TYPE, "export_id": "e" * 64, "files": {}},
                                 {"a" * 64: b"one", "b" * 64: b"two"})
        entries = site.kv_entries(export)
        self.assertEqual(entries[0][0], "e" * 64 + "/manifest")
        self.assertEqual([key for key, _body in entries[1:]], ["e" * 64 + "/f/" + "a" * 64, "e" * 64 + "/f/" + "b" * 64])
        payload = site.load_payload(export.export_id, entries)
        length = int.from_bytes(payload[8:12], "little")
        header = json.loads(payload[12:12 + length])
        self.assertEqual([row["bytes"] for row in header["files"]], [len(body) for _key, body in entries])


class NetworkGuard(unittest.TestCase):

    def test_site_client_refuses_non_origins_without_opening_a_connection(self):
        with patch.object(site_tool.http.client, "HTTPSConnection") as connection:
            for origin in ("http://origin.invalid", "https://origin.invalid/path", "https://user@origin.invalid",
                           "https://origin.invalid?query", "https://origin.invalid#fragment"):
                with self.assertRaises(ValueError):
                    site_tool.Client(origin)
            connection.assert_not_called()

    def test_site_client_never_replays_an_uncertain_write(self):
        with patch.object(site_tool.http.client, "HTTPSConnection") as connection:
            connection.return_value.request.side_effect = OSError("lost response")
            client = site_tool.Client("https://origin.invalid")
            with self.assertRaises(OSError):
                client.request("POST", "/__edge/admin/files", b"data")
            self.assertEqual(connection.return_value.request.call_count, 1)

    def test_site_client_may_retry_one_failed_read(self):
        with patch.object(site_tool.http.client, "HTTPSConnection") as connection:
            connection.return_value.request.side_effect = OSError("lost response")
            client = site_tool.Client("https://origin.invalid")
            with self.assertRaises(OSError):
                client.request("GET", "/__edge/status")
            self.assertEqual(connection.return_value.request.call_count, 2)

    def test_every_networked_command_refuses_without_the_authorization_flag(self):
        for argv in (["vectors", "--export", "x", "--worker", "https://w", "--admin-key", "k"],
                     ["measure", "--export", "x", "--bundle", "b", "--worker", "https://w", "--search-key", "k",
                      "--out", "o"]):
            with self.assertRaises(SystemExit) as caught:
                d1_tool.main(argv)
            self.assertIn("--authorize-network", str(caught.exception))
        for argv in (["export", "--out", "o", "--origin", "https://o"],
                     ["load", "--export", "x", "--worker", "https://w", "--admin-key", "k"],
                     ["measure", "--export", "x", "--worker", "https://w", "--origin", "https://o", "--out", "o"],
                     ["outage", "--export", "x", "--worker", "https://w", "--out", "o"]):
            with self.assertRaises(SystemExit) as caught:
                site_tool.main(argv)
            self.assertIn("--authorize-network", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

"""Offline tests of this package's pinned manifest and of creative_fetch.py against a local server.

The fetcher downloads fixtures from a server on the loopback address. Known-wrong cases, each refused with nothing
left in place: bytes other than the recorded SHA-256, more bytes than recorded, a placement outside the folder, an
address that is not HTTPS on a listed host, a redirect to an unlisted address, an unknown variant, and an archive
holding a member that was not recorded. The package's own manifest must pin every file by HTTPS address, size and
SHA-256, and a manifest broken in any of those ways must be refused.
"""
from __future__ import annotations

import copy
import hashlib
import http.server
import io
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import creative_fetch as fetch  # noqa: E402

PACKAGE = fetch.load_manifest(HERE / fetch.MANIFEST_NAME)


class _Server:
    """A server on the loopback address: path to bytes, path to redirect target; it records every request."""

    def __init__(self, files, redirects=None):
        self.files, self.redirects, self.requests = dict(files), dict(redirects or {}), []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append(self.path)
                name = self.path.lstrip("/")
                if name in owner.redirects:
                    self.send_response(302)
                    self.send_header("Location", owner.redirects[name])
                    self.end_headers()
                    return
                if name not in owner.files:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = owner.files[name]
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_arguments):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def url(self, name):
        return f"http://127.0.0.1:{self.server.server_port}/{name}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _file(server, name, data, path=None, *, recorded=None, role="fixture"):
    pinned = recorded if recorded is not None else data
    return {"path": path or name, "url": server.url(name), "size_bytes": len(pinned),
            "sha256": hashlib.sha256(pinned).hexdigest(), "role": role}


def _manifest(files, *, identifier="fixture"):
    return {"record_type": fetch.RECORD_TYPE, "job": {"source": "fixture", "identity": "fixture"},
            "asset": {"type": "model", "name": "Fixture"}, "hosts": ["example.org"],
            "variants": [{"id": identifier, "files": files, "total_bytes": sum(row["size_bytes"] for row in files),
                          "main": files[0]["path"]}],
            "default_variant": identifier, "licence": {"spdx": "CC0-1.0"}}


def _archive(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return stream.getvalue()


class PackageManifestTest(unittest.TestCase):
    def test_the_package_pins_every_file_by_https_address_size_and_sha256(self):
        self.assertEqual(fetch.manifest_problems(PACKAGE), [])
        for row in PACKAGE["variants"]:
            self.assertIn(row["id"], fetch.describe(PACKAGE))
            for item in row["files"]:
                self.assertTrue(item["url"].startswith("https://"), item["url"])
                self.assertEqual(fetch.check_address(item["url"], PACKAGE["hosts"]), item["url"])

    def test_known_wrong_manifests_are_refused(self):
        base = copy.deepcopy(PACKAGE) if PACKAGE["variants"] else _manifest(
            [{"path": "a.bin", "url": "https://example.org/a.bin", "size_bytes": 1, "sha256": "0" * 64}])
        self.assertEqual(fetch.manifest_problems(base), [])

        def broken(change):
            value = copy.deepcopy(base)
            change(value)
            return fetch.manifest_problems(value)

        first = lambda value: value["variants"][0]["files"][0]  # noqa: E731
        for change in (lambda value: value.update(record_type="creative_asset_manifest/v2"),
                       lambda value: first(value).update(sha256="z" * 64),
                       lambda value: first(value).update(url="http://example.org/a.bin"),
                       lambda value: first(value).update(url="https://elsewhere.example/a.bin"),
                       lambda value: first(value).update(path="../outside.bin"),
                       lambda value: first(value).update(size_bytes=-1),
                       lambda value: value["variants"][0].update(total_bytes=value["variants"][0]["total_bytes"] + 1),
                       lambda value: value.update(default_variant="not-a-variant")):
            self.assertTrue(broken(change))


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.data = b"pinned bytes\n" * 512
        self.server = _Server({"files/asset.bin": self.data, "files/other.bin": b"other bytes\n"})
        self.folder = tempfile.mkdtemp()
        self.open_url = fetch.opener((), allow_loopback=True, proxies={}).open

    def tearDown(self):
        self.server.close()
        shutil.rmtree(self.folder)

    def _fetch(self, manifest, identifier=None):
        return fetch.fetch(identifier, self.folder, manifest=manifest, allow_loopback=True, open_url=self.open_url)

    def _left(self):
        return sorted(str(path.relative_to(self.folder)) for path in Path(self.folder).rglob("*") if path.is_file())

    def test_a_variant_is_fetched_with_its_recorded_bytes_and_a_second_fetch_downloads_nothing(self):
        manifest = _manifest([_file(self.server, "files/asset.bin", self.data, "textures/asset.bin")])
        [path] = self._fetch(manifest)
        self.assertEqual(path.read_bytes(), self.data)
        self.assertEqual(self._left(), [os.path.join("textures", "asset.bin")])
        asked = len(self.server.requests)
        self._fetch(manifest)
        self.assertEqual(len(self.server.requests), asked)

    def test_known_wrong_other_bytes_are_refused_and_nothing_is_left(self):
        manifest = _manifest([_file(self.server, "files/asset.bin", self.data, recorded=self.data[:-1] + b"?")])
        with self.assertRaises(fetch.FetchError) as caught:
            self._fetch(manifest)
        self.assertEqual(caught.exception.code, "digest_mismatch")
        self.assertEqual(self._left(), [])

    def test_known_wrong_more_or_fewer_bytes_than_recorded_are_refused(self):
        for recorded in (self.data[:100], self.data + b"x"):
            manifest = _manifest([_file(self.server, "files/asset.bin", self.data, recorded=recorded)])
            with self.assertRaises(fetch.FetchError) as caught:
                self._fetch(manifest)
            self.assertEqual(caught.exception.code, "size_mismatch")
            self.assertEqual(self._left(), [])

    def test_known_wrong_an_unsafe_placement_or_an_unlisted_address_sends_nothing(self):
        for path in ("../outside.bin", "/absolute.bin", "a\\b.bin", "a/../../b.bin"):
            manifest = _manifest([_file(self.server, "files/asset.bin", self.data, path)])
            with self.assertRaises(fetch.FetchError):
                self._fetch(manifest)
        plain = _manifest([dict(_file(self.server, "files/asset.bin", self.data),
                                url="http://example.org/files/asset.bin")])
        with self.assertRaises(fetch.FetchError):
            self._fetch(plain)
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch(None, self.folder, manifest=_manifest([_file(self.server, "files/asset.bin", self.data)]),
                        open_url=self.open_url)
        self.assertEqual(caught.exception.code, "manifest_invalid")
        self.assertEqual(self.server.requests, [])
        self.assertEqual(self._left(), [])

    def test_known_wrong_a_redirect_to_an_unlisted_address_is_refused(self):
        self.server.redirects["files/moved.bin"] = "http://example.org/files/asset.bin"
        manifest = _manifest([_file(self.server, "files/moved.bin", self.data)])
        with self.assertRaises(fetch.FetchError) as caught:
            self._fetch(manifest)
        self.assertEqual(caught.exception.code, "address_refused")
        self.server.redirects["files/moved.bin"] = self.server.url("files/asset.bin")
        self.assertEqual(self._fetch(manifest)[0].read_bytes(), self.data)

    def test_known_wrong_an_unknown_variant_is_refused(self):
        manifest = _manifest([_file(self.server, "files/asset.bin", self.data)])
        with self.assertRaises(fetch.FetchError) as caught:
            self._fetch(manifest, "no-such-variant")
        self.assertEqual(caught.exception.code, "variant_unknown")
        self.assertEqual(self.server.requests, [])

    def test_an_archive_is_unpacked_only_with_its_recorded_members(self):
        members = {"maps/color.jpg": b"colour map", "material.tres": b"[gd_resource]\n"}
        archive = _archive(members)
        self.server.files["files/set.zip"] = archive
        row = dict(_file(self.server, "files/set.zip", archive, "set.zip", role="archive"), unpack=True,
                   members=[{"path": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                             "role": name} for name, data in members.items()])
        paths = self._fetch(_manifest([row]))
        self.assertEqual(sorted(path.name for path in paths), ["color.jpg", "material.tres", "set.zip"])
        self.assertEqual((Path(self.folder) / "maps" / "color.jpg").read_bytes(), b"colour map")
        wrong = copy.deepcopy(row)
        wrong["members"][0]["sha256"] = hashlib.sha256(b"another map").hexdigest()
        (Path(self.folder) / "maps" / "color.jpg").unlink()
        with self.assertRaises(fetch.FetchError) as caught:
            self._fetch(_manifest([wrong]))
        self.assertEqual(caught.exception.code, "digest_mismatch")
        self.assertFalse((Path(self.folder) / "maps" / "color.jpg").exists())

    def test_known_wrong_an_archive_with_an_unrecorded_member_is_refused(self):
        archive = _archive({"maps/color.jpg": b"colour map", "../escape.txt": b"outside"})
        self.server.files["files/bad.zip"] = archive
        row = dict(_file(self.server, "files/bad.zip", archive, "bad.zip", role="archive"), unpack=True,
                   members=[{"path": "maps/color.jpg", "size_bytes": 10,
                             "sha256": hashlib.sha256(b"colour map").hexdigest(), "role": "diffuse"}])
        with self.assertRaises(fetch.FetchError) as caught:
            self._fetch(_manifest([row]))
        self.assertEqual(caught.exception.code, "archive_members_differ")
        self.assertFalse((Path(self.folder).parent / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()

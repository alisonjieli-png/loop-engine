"""Negative and positive checks for the read-only research source watcher."""
from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from tools import refresh_research_sources as watch

SOURCE = {
    "id": "example_repo",
    "name": "Example repository",
    "kind": "github_repository",
    "url": "https://github.com/example/project",
    "roadmap_step": "S-6.42",
    "license_state": "unknown",
    "baseline_revision": "a" * 40,
}


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        self.body = BytesIO(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.body.close()

    def read(self, size: int) -> bytes:
        return self.body.read(size)


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


class ManifestChecks(unittest.TestCase):
    def manifest(self, *sources):
        return {"record_type": watch.MANIFEST_TYPE, "sources": list(sources)}

    def test_duplicate_id_and_duplicate_url_are_refused(self):
        other_id = dict(SOURCE, id="another_repo")
        other_url = dict(SOURCE, url="https://github.com/example/another")
        for second in (other_id, other_url):
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, "duplicate"):
                watch.validate_manifest(self.manifest(SOURCE, second))

    def test_malformed_source_and_unknown_contract_are_refused(self):
        for manifest in (
            {"record_type": "unversioned", "sources": [SOURCE]},
            self.manifest(dict(SOURCE, extra_permission=True)),
            self.manifest(dict(SOURCE, roadmap_step="tomorrow")),
            self.manifest(dict(SOURCE, baseline_revision="main")),
            self.manifest(dict(SOURCE, name="")),
        ):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                watch.validate_manifest(manifest)

    def test_unsupported_urls_are_refused_before_network(self):
        for url in (
            "http://github.com/example/project",
            "https://user:secret@github.com/example/project",
            "https://github.com:443/example/project",
            "https://github.com/example/project/tree/main",
            "https://127.0.0.1/example/project",
            "https://metadata.google.internal/example/project",
            "https://github.com/example/project?token=sensitive",
            "https://github.com/example/project#readme",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                watch.validate_manifest(self.manifest(dict(SOURCE, url=url)))
        page = dict(SOURCE, kind="web_page", url="https://example.com/research")
        del page["baseline_revision"]
        with self.assertRaisesRegex(ValueError, "unsupported web page URL"):
            watch.validate_manifest(self.manifest(page))

    def test_starter_manifest_is_valid_and_bounded(self):
        path = Path(__file__).with_name("research_source_watch.json")
        sources = watch.validate_manifest(json.loads(path.read_text("utf-8")))
        self.assertLessEqual(len(sources), watch.MAX_ONLINE_SOURCES)
        self.assertEqual(len(sources), len({row["url"] for row in sources}))


class ObservationChecks(unittest.TestCase):
    def test_offline_mode_never_calls_network_and_keeps_change_unknown(self):
        opener = FakeOpener(error=AssertionError("network should not be called"))
        report = watch.run_watch([SOURCE], online=False, opener=opener)
        self.assertEqual([], opener.requests)
        self.assertEqual("offline_validation", report["mode"])
        self.assertEqual("unknown", report["sources"][0]["change"])
        self.assertIsNone(report["sources"][0]["retrieved_at"])

    def test_changed_and_unchanged_commits_use_exact_revision(self):
        for sha, expected in (("b" * 40, "changed"), ("a" * 40, "unchanged")):
            with self.subTest(expected=expected):
                opener = FakeOpener(response=FakeResponse(json.dumps([{"sha": sha}]).encode()))
                report = watch.run_watch([SOURCE], online=True, opener=opener)
                row = report["sources"][0]
                self.assertEqual(expected, row["change"])
                self.assertEqual(sha, row["observed"]["revision"])
                self.assertEqual("manifest baseline_revision", row["comparison_basis"])
                self.assertEqual("https://api.github.com/repos/example/project/commits?per_page=1",
                                 row["observed"]["request_url"])
                self.assertIsNotNone(row["retrieved_at"])
                self.assertEqual("GET", opener.requests[0][0].get_method())

    def test_prior_success_overrides_old_manifest_baseline(self):
        previous = {(SOURCE["id"], SOURCE["kind"], SOURCE["url"]): ("b" * 40, "previous.json")}
        opener = FakeOpener(response=FakeResponse(json.dumps([{"sha": "b" * 40}]).encode()))
        row = watch.run_watch([SOURCE], online=True, prior=previous, opener=opener)["sources"][0]
        self.assertEqual("unchanged", row["change"])
        self.assertEqual("previous.json", row["comparison_basis"])

    def test_timeout_and_invalid_response_leave_change_unknown(self):
        for opener, expected in (
            (FakeOpener(error=TimeoutError()), "timeout"),
            (FakeOpener(response=FakeResponse(b"{}")), "invalid_response"),
            (FakeOpener(response=FakeResponse(b"x" * 1025)), "invalid_response"),
        ):
            with self.subTest(expected=expected, opener=opener):
                row = watch.run_watch([SOURCE], online=True, opener=opener,
                                      max_bytes=1024)["sources"][0]
                self.assertEqual("unknown", row["change"])
                self.assertEqual(expected, row["failure"]["kind"])
                self.assertIsNone(row["retrieved_at"])

    def test_page_report_records_validators_and_digest_without_body(self):
        page = dict(SOURCE, id="example_page", kind="web_page",
                    url="https://arxiv.org/abs/2609.20519")
        del page["baseline_revision"]
        body = b"private-looking-test-body-that-must-not-be-saved"
        opener = FakeOpener(response=FakeResponse(body, {"ETag": '"revision-2"',
                                                           "Last-Modified": "Tue, 22 Sep 2026 10:00:00 GMT"}))
        report = watch.run_watch([page], online=True, opener=opener)
        row = report["sources"][0]
        self.assertEqual("unknown", row["change"])
        self.assertEqual('"revision-2"', row["observed"]["etag"])
        self.assertEqual(64, len(row["observed"]["content_sha256"]))
        self.assertNotIn(body.decode(), json.dumps(report))

    def test_oversized_validator_header_is_not_persisted(self):
        page = dict(SOURCE, id="example_page", kind="web_page",
                    url="https://arxiv.org/abs/2609.20519")
        del page["baseline_revision"]
        opener = FakeOpener(response=FakeResponse(b"body", {"ETag": "x" * 257}))
        row = watch.run_watch([page], online=True, opener=opener)["sources"][0]
        self.assertIsNone(row["observed"]["etag"])

    def test_online_limit_refuses_work_before_any_request(self):
        opener = FakeOpener(error=AssertionError("network should not be called"))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            watch.run_watch([SOURCE, dict(SOURCE, id="second")], online=True,
                            max_online_sources=1, opener=opener)
        self.assertEqual([], opener.requests)


class ReportChecks(unittest.TestCase):
    def test_exclusive_write_keeps_prior_result_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "RESEARCH-SOURCE-WATCH-2026-09-22.json"
            watch.write_new_report(path, {"result": "first"})
            first = path.read_bytes()
            with self.assertRaises(FileExistsError):
                watch.write_new_report(path, {"result": "second"})
            self.assertEqual(first, path.read_bytes())

    def test_latest_successful_observation_survives_later_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            successful = {"record_type": watch.REPORT_TYPE, "sources": [
                {"id": SOURCE["id"], "kind": SOURCE["kind"], "url": SOURCE["url"],
                 "observed": {"fingerprint": "b" * 40}}]}
            failed = deepcopy(successful)
            failed["sources"][0]["observed"] = None
            watch.write_new_report(root / "RESEARCH-SOURCE-WATCH-2026-09-20.json", successful)
            watch.write_new_report(root / "RESEARCH-SOURCE-WATCH-2026-09-21.json", failed)
            prior = watch.load_prior_observations(root)
            self.assertEqual(("b" * 40, "RESEARCH-SOURCE-WATCH-2026-09-20.json"),
                             prior[(SOURCE["id"], SOURCE["kind"], SOURCE["url"])])


if __name__ == "__main__":
    unittest.main()

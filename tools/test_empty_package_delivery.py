"""A protocol size refusal must never count an item whose files were all omitted."""
from dataclasses import replace
import inspect
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime.catalogue_release_checks import bundle_line
from loop_engine.core.service_runtime.catalogue_releases import publish
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from tools import test_selected_file_delivery as selected


class EmptyPackageDelivery(unittest.TestCase):
    def setUp(self):
        self.fixture = selected.SelectedFileDelivery()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def install_files(self, *, small=False):
        case = self.fixture
        big = selected.BODY * 200
        second = selected.OTHER if small else big
        rows = [(selected.SELECTED, big, "text/markdown", "skill_definition"),
                ("notes.txt", second, "text/plain", "other")]
        bundle = case.case.bundle([bundle_line(selected.IDENTITY, rows)], payloads=tuple(set((big, second))))
        publish(case.case.context, bundle, expected_release=case.view.release_id)
        view = replace(case.case.view(), body_store=case.remote)
        case.package = view.package_of(selected.IDENTITY)
        case.served.provisioning.install_view(view)
        for entry, body in zip(case.package.files, (big, second)):
            case.fake.objects[case.remote.object_key(entry.digest)] = body

    def request(self, client, *, path, openapi):
        case = self.fixture
        if not openapi:
            response, success, body, code = case.request(client, "mcp", path=path)
            record = selected.protocol_message(response).get("result", {}).get("structuredContent", {}).get("result", {})
            return response, success, code, record
        fields = {"identity": selected.IDENTITY, "expected_digest": case.package.served_digest,
                  "request_id": "openapi-size-refusal", "authority_effects": []}
        if path is not None:fields["path"] = path
        response = client.post("/api/v1/connect/read", json=fields,
            headers={"Authorization": "Bearer " + case.case.key.key, "Origin": "https://customer.example"})
        message = response.json()
        return response, response.status_code == 200, message.get("error", {}).get("code"), message.get("result", {})

    def assert_empty_refused(self, *, response_limit=False):
        case = self.fixture
        self.install_files()
        configuration = ({"maximum_response_bytes": 10000} if response_limit else
                         {"maximum_download_bytes": 1024, "maximum_inline_body_bytes": 1024})
        with running_http(case.served, **configuration) as (origin, _app), httpx.Client(base_url=origin, trust_env=False) as client:
            for openapi in (False, True):
                for path in (selected.SELECTED, None):
                    with self.subTest(openapi=openapi, path=path, response_limit=response_limit):
                        response, success, code, _record = self.request(client, path=path, openapi=openapi)
                        self.assertEqual(case.usage(), 0, "An omissions-only answer consumed a paid unit")
                        self.assertFalse(success)
                        self.assertEqual(code, "response_limit_exceeded" if response_limit else "download_limit_exceeded")
                        if openapi:self.assertEqual(response.status_code, 413)
                        self.assertNotIn(selected.BODY, response.content)
        self.assertEqual(case.fake.count("GET"), 0)

    def test_selected_and_all_omitted_pages_refuse_the_download_limit_before_usage(self):
        self.assert_empty_refused()

    def test_selected_and_all_omitted_pages_refuse_the_protocol_limit_before_usage(self):
        self.assert_empty_refused(response_limit=True)

    def test_a_useful_partial_page_delivers_the_small_file_and_counts_once(self):
        case = self.fixture
        self.install_files(small=True)
        with running_http(case.served, maximum_download_bytes=1024, maximum_inline_body_bytes=1024) as (origin, _app), \
                httpx.Client(base_url=origin, trust_env=False) as client:
            for openapi in (False, True):
                response, success, code, record = self.request(client, path=None, openapi=openapi)
                self.assertTrue(success, code)
                self.assertEqual([row["path"] for row in record["files"]], ["notes.txt"])
                self.assertEqual(record["files"][0]["content"].encode(), selected.OTHER)
                self.assertEqual([row["path"] for row in record["omitted"]], [selected.SELECTED])
                self.assertEqual(case.usage(), 1)
        self.assertEqual(case.fake.count("GET"), 2)

    def test_removing_both_empty_delivery_guards_reproduces_the_paid_unit(self):
        import textwrap
        from loop_engine.core.service_runtime import http
        source = textwrap.dedent(inspect.getsource(ServiceHttpApplication._protocol_read))
        original = source
        source = source.replace('    if all(entry.size_bytes > self.configuration.maximum_download_bytes for entry in chosen):\n'
                                '        raise ServiceHttpError("download_limit_exceeded", 413)\n', "")
        source = source.replace('if not record["files"] or _protocol_cost(record) > budget:', 'if _protocol_cost(record) > budget:')
        self.assertNotEqual(source, original)
        namespace = dict(vars(http))
        exec(compile(source, "<known-wrong-empty-delivery>", "exec"), namespace)
        with mock.patch.object(ServiceHttpApplication, "_protocol_read", namespace["_protocol_read"]):
            self.install_files()
            case = self.fixture
            with running_http(case.served, maximum_download_bytes=1024, maximum_inline_body_bytes=1024) as (origin, _app), \
                    httpx.Client(base_url=origin, trust_env=False) as client:
                _response, success, _code, record = self.request(client, path=selected.SELECTED, openapi=False)
            self.assertTrue(success, "The known-wrong source no longer reproduces the faulty success")
            self.assertEqual(record["files"], [])
            self.assertEqual(case.usage(), 1, "The known-wrong source must reproduce the premature paid unit")
            self.assertEqual(case.fake.count("GET"), 0)


if __name__ == "__main__":unittest.main()

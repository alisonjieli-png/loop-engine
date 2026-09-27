"""The supply lines' records, packages, store writes and the protocol server line, offline.

Every guard has a known-wrong case: a licence outside the allowlist or joined by AND to one, a candidate record of
another version or with an extra field, a form a line may not declare, a package whose files hide text, a server
reached only over the network, a package version its registry does not publish, a second server for the same
package, and a supplied candidate that an export reading only imported copies would meet (it never does: the supply
namespace is its own).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from loop_engine.catalog.query import IntelligenceQuery  # noqa: E402
from loop_engine.core.library_ingestion.provenance import (  # noqa: E402
    LICENCE_EVIDENCE_RECORD_TYPE, LINK_ONLY, ORIGIN_HOSTS, REGISTRY_ORIGIN, OutsideSourceProvenance)
from loop_engine.core.library_ingestion.record_rules import canonical_json  # noqa: E402

from licensed_import.storage import NAMESPACE, SUPPLY_NAMESPACE  # noqa: E402
from supply_lines import mcp_registry, records  # noqa: E402
from supply_lines.packaging import LICENCE_NAME, PackageFile, SupplyPackage, build  # noqa: E402
from supply_lines.records import SupplyRecordError, licence_allowed, read_supply_candidate  # noqa: E402

LICENCE = (HERE.parent / "LICENSE").read_bytes()
GENERATOR = {"identity": "tools/supply_lines/test.py", "version": "1.0.0", "code_revision": "a" * 40}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fact():
    return records.fact_source("https://example.org/spec.json", "2026-09-27T00:00:00Z", "b" * 64, 10,
                               "specification", spdx="MIT", basis="test")


def _package(**changes) -> SupplyPackage:
    values = dict(line=records.OPENAPI_OPERATIONS, identity="example:get_thing",
                  key=records.upstream_key(records.OPENAPI_OPERATIONS, "example:get_thing"), kind="code_module",
                  native_format="openapi_operation_client", form="api_operation", name="get_thing",
                  description="Read one thing.",
                  files=[PackageFile("get_thing.py", b"def get_thing():\n    return 1\n", "executable_tool"),
                         PackageFile(LICENCE_NAME, LICENCE, "other", records.LICENCE_TEXT)],
                  licence_expression="MIT",
                  provenance=records.provenance("github_repository", "example/api", "openapi.json", "c" * 40,
                                                [_fact()], GENERATOR),
                  placements=[], effects=[("network", "calls_the_api")], credentials=["EXAMPLE_TOKEN"],
                  tests={"files": [], "result": "passed"}, repository={"name": "example/api", "stars": 1},
                  generated_on="2026-09-27")
    values.update(changes)
    return SupplyPackage(**values)


class RecordsTest(unittest.TestCase):
    def test_licence_expressions_follow_the_owner_allowlist(self):
        for allowed in ("MIT", "Apache-2.0", "MIT OR Apache-2.0", "(MIT OR Apache-2.0)", "MIT OR GPL-3.0-only",
                        "MIT AND BSD-3-Clause", "Unlicense OR MIT", "CC0-1.0"):
            self.assertTrue(licence_allowed(allowed), allowed)
        for refused in ("", "GPL-3.0-only", "MIT AND GPL-3.0-only", "Apache-2.0 WITH LLVM-exception", "MIT OR",
                        "(MIT", "NOASSERTION", "ODbL-1.0", "CC-BY-SA-4.0", "MIT OR AND Apache-2.0"):
            self.assertFalse(licence_allowed(refused), refused)

    def test_a_built_candidate_is_read_back_and_known_wrong_records_are_refused(self):
        payload, bodies = build(_package())
        self.assertEqual(read_supply_candidate(payload), payload)
        self.assertEqual(payload["component_form"]["form"], "api_operation")
        self.assertEqual(payload["licence"]["texts"], ["LICENSE"])
        self.assertIn("ATTRIBUTION.md", {entry["path"] for entry in payload["package"]["files"]})
        self.assertEqual(set(bodies), {entry["digest"] for entry in payload["package"]["files"]})
        attribution = next(data for data in bodies.values() if data.startswith(b"# Attribution"))
        self.assertIn(b"No model wrote any of it.", attribution)
        self.assertIn(b"https://example.org/spec.json", attribution)

        def mutated(change):
            value = copy.deepcopy(payload)
            change(value)
            return value

        wrong = {
            "candidate_version_unsupported": mutated(lambda v: v.update(record_type="library_supply_candidate/v2")),
            "candidate_fields_invalid": mutated(lambda v: v.update(approved=True)),
            "component_form_kind_mismatch": mutated(lambda v: v.update(kind="skill")),
            "line_form_mismatch": mutated(lambda v: v.update(line=records.MCP_REGISTRY)),
            "authoring_invalid": mutated(lambda v: v.update(authoring="imported_verbatim_under_permissive_licence")),
            "lifecycle_invalid": mutated(lambda v: v.update(lifecycle="approved")),
            "licence_not_on_allowlist": mutated(lambda v: v["licence"].update(spdx_expression="GPL-3.0-only")),
            "licence_files_missing": mutated(lambda v: v["licence"].update(texts=["COPYING"])),
            "effects_invalid": mutated(lambda v: v.update(declared_effects=["sends_email"])),
            "credentials_invalid": mutated(lambda v: v.update(credentials=["sk-live-1234"])),
            "record_identity_invalid": mutated(lambda v: v.update(package_digest="d" * 64)),
        }
        for code, value in wrong.items():
            with self.assertRaises(SupplyRecordError, msg=code) as caught:
                read_supply_candidate(value)
            self.assertEqual(caught.exception.code, code)

    def test_a_package_with_hidden_text_or_above_the_review_bound_is_refused(self):
        hidden = "def get_thing():\n    return 1  \U000e0101\n".encode()
        with self.assertRaises(SupplyRecordError) as caught:
            build(_package(files=[PackageFile("get_thing.py", hidden, "executable_tool"),
                                  PackageFile(LICENCE_NAME, LICENCE, "other", records.LICENCE_TEXT)]))
        self.assertEqual(caught.exception.code, "blocked_by_static_check")
        with self.assertRaises(SupplyRecordError) as caught:
            build(_package(files=[PackageFile("big.json", b"[" + b"1," * 200_000 + b"1]", "other"),
                                  PackageFile(LICENCE_NAME, LICENCE, "other", records.LICENCE_TEXT)]))
        self.assertEqual(caught.exception.code, "package_above_review_bound")
        with self.assertRaises(SupplyRecordError) as caught:
            build(_package(licence_expression="MIT AND GPL-3.0-only"))
        self.assertEqual(caught.exception.code, "licence_not_on_allowlist")
        with self.assertRaises(SupplyRecordError) as caught:
            build(_package(files=[PackageFile("get_thing.py", b"x = 1\n", "executable_tool")]))
        self.assertEqual(caught.exception.code, "licence_files_missing")


class StoreTest(unittest.TestCase):
    def test_supplied_candidates_live_in_their_own_namespace_with_versions_and_withdrawals(self):
        from supply_lines.store import SupplyStore
        with tempfile.TemporaryDirectory() as folder:
            first = build(_package())
            other = build(_package(identity="example:list_things", name="list_things",
                                   key=records.upstream_key(records.OPENAPI_OPERATIONS, "example:list_things")))
            with self.assertRaises(PermissionError):
                SupplyStore(folder, writes_authorized=False)
            writer = SupplyStore(folder, writes_authorized=True)
            try:
                self.assertEqual(writer.write(records.OPENAPI_OPERATIONS, [first, other], complete=True)["written"], 2)
                self.assertEqual(writer.write(records.OPENAPI_OPERATIONS, [first, other], complete=True)["unchanged"], 2)
                changed = build(_package(description="Read one thing, second version.",
                                         files=[PackageFile("get_thing.py", b"def get_thing():\n    return 2\n",
                                                            "executable_tool"),
                                                PackageFile(LICENCE_NAME, LICENCE, "other", records.LICENCE_TEXT)]))
                result = writer.write(records.OPENAPI_OPERATIONS, [changed], complete=True)
                self.assertEqual((result["written"], result["superseded"], result["withdrawn"]), (1, 1, 1))
                rows = writer.store.records.query(IntelligenceQuery(namespaces=(SUPPLY_NAMESPACE,)))
                lifecycles = sorted(row["lifecycle"] for row in rows if row["artifact_kind"] == "intelligence_record")
                self.assertEqual(lifecycles, ["candidate", "superseded", "withdrawn"])
                self.assertEqual(writer.store.get(changed[0]["record_id"])["payload"]["version"]["previous_record_id"],
                                 first[0]["record_id"])
                # Known wrong: an export that reads only imported copies never meets a supplied candidate.
                imported = writer.store.records.query(IntelligenceQuery(namespaces=(NAMESPACE,),
                                                                        lifecycle=("candidate",)))
                self.assertEqual(imported, [])
            finally:
                writer.close()


def _entry(name="io.github.example/weather", *, package=None, remotes=None, env=None, version="1.2.3"):
    server = {"name": name, "version": version, "description": "Weather forecasts for agents.",
              "repository": {"url": "https://github.com/example/weather-mcp", "source": "github"}}
    if package is not False:
        server["packages"] = [package or {"registryType": "npm", "identifier": "@example/weather-mcp",
                                          "version": version, "transport": {"type": "stdio"},
                                          "environmentVariables": env if env is not None else [
                                              {"name": "WEATHER_API_KEY", "isSecret": True, "isRequired": True}]}]
    if remotes:
        server["remotes"] = remotes
    return {"server": server, "_meta": {"io.modelcontextprotocol.registry/official": {
        "status": "active", "publishedAt": "2026-09-01T00:00:00Z", "isLatest": True}}}


def _source(entry, spdx="MIT", reason="upstream_repository_licence"):
    data = canonical_json(entry).encode()
    name, version = entry["server"]["name"], entry["server"]["version"]
    evidence = {"record_type": LICENCE_EVIDENCE_RECORD_TYPE, "spdx_expression": spdx, "decision": LINK_ONLY,
                "reason": reason, "detector": "test",
                "repository_licence": {"path": "LICENSE", "sha256": "e" * 64, "github_spdx_id": spdx,
                                       "matched_spdx": spdx, "similarity": 1.0} if spdx != "NOASSERTION" else None,
                "governing_file": None, "file_level_notices": []}
    return OutsideSourceProvenance(REGISTRY_ORIGIN, ORIGIN_HOSTS[REGISTRY_ORIGIN], name,
                                   f"version:{version};published:2026-09-01T00:00:00Z",
                                   f"v0.1/servers/{name.replace('/', '%2F')}/versions/{version}", _digest(data),
                                   len(data), None, "f" * 64, evidence, "2026-09-27T00:00:00Z", "a" * 64)


class _Answer:
    def __init__(self, status, body):
        self.status, self.body = status, body
        self.sha256, self.retrieved_at = _digest(body), "2026-09-27T00:00:00Z"


class _Reader:
    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def get(self, url, cache_errors=False):
        self.asked.append(url)
        status, body = self.answers.get(url, (404, b"{}"))
        return _Answer(status, body)


NPM = "https://registry.npmjs.org/@example%2Fweather-mcp/1.2.3"


class McpRegistryLineTest(unittest.TestCase):
    def _generate(self, entries, answers=None):
        reader = _Reader(answers if answers is not None else {NPM: (200, json.dumps({"license": "MIT"}).encode())})
        return mcp_registry.generate(entries, reader, code_revision="a" * 40, licence_text=LICENCE,
                                     generated_on="2026-09-27")

    def test_a_published_npm_server_becomes_one_connection_package_for_four_harnesses(self):
        entry = _entry()
        built, refusals = self._generate([(entry, _source(entry))])
        self.assertEqual(refusals, [])
        [(payload, bodies)] = built
        files = {entry["path"]: bodies[entry["digest"]] for entry in payload["package"]["files"]}
        self.assertEqual(set(files), {".mcp.json", ".codex/config.toml", "opencode.json", ".cursor/mcp.json",
                                      "baltor-connection.json", "README.md", "LICENSE", "ATTRIBUTION.md"})
        claude = json.loads(files[".mcp.json"])["mcpServers"]["example-weather"]
        self.assertEqual(claude["args"], ["-y", "@example/weather-mcp@1.2.3"])
        self.assertEqual(claude["env"], {"WEATHER_API_KEY": "${WEATHER_API_KEY}"})
        cursor = json.loads(files[".cursor/mcp.json"])["mcpServers"]["example-weather"]
        self.assertEqual(cursor["env"], {"WEATHER_API_KEY": "${env:WEATHER_API_KEY}"})
        self.assertIn(b'env_vars = ["WEATHER_API_KEY"]', files[".codex/config.toml"])
        self.assertEqual(payload["credentials"], ["WEATHER_API_KEY"])
        self.assertEqual(payload["declared_effects"], ["network", "reads_secret", "spawns_process"])
        self.assertEqual((payload["kind"], payload["component_form"]["form"]),
                         ("protocol_server_configuration", "mcp_server"))
        self.assertEqual(payload["provenance"]["origin"], "mcp_official_registry")
        self.assertEqual([fact["role"] for fact in payload["provenance"]["facts"]],
                         ["registry_entry", "licence_text", "package_metadata"])
        # The author's description is never copied into the files.
        self.assertFalse(any(b"Weather forecasts for agents" in data for data in files.values()))

    def test_known_wrong_entries_are_refused_by_name(self):
        cases = {
            "remote_only_server": (_entry(package=False, remotes=[{"type": "streamable-http",
                                                                   "url": "https://example.org/mcp"}]), "MIT"),
            "licence_not_on_allowlist": (_entry(), "GPL-3.0-only"),
            "licence_unknown": (_entry(), "NOASSERTION"),
            "package_type_not_rendered": (_entry(package={"registryType": "npm", "identifier": "@example/weather-mcp",
                                                          "version": "latest", "transport": {"type": "stdio"}}), "MIT"),
            "credential_shaped_value_in_entry": (_entry(env=[{"name": "TOKEN", "value": "ghp_" + "a" * 36}]), "MIT"),
            "no_npm_or_pypi_package": (_entry(package={"registryType": "oci", "identifier": "example/weather",
                                                       "version": "1.2.3", "transport": {"type": "stdio"}}), "MIT"),
        }
        for reason, (entry, spdx) in cases.items():
            built, refusals = self._generate([(entry, _source(entry, spdx))])
            self.assertEqual((len(built), [row["reason"] for row in refusals]), (0, [reason]), reason)
        disagree = _entry()
        _built, refusals = self._generate([(disagree, _source(disagree, "NOASSERTION",
                                                              "upstream_licence_signals_disagree"))])
        self.assertEqual(refusals[0]["reason"], "licence_signals_disagree")

    def test_the_published_package_and_its_licence_are_checked_and_duplicates_kept_once(self):
        entry = _entry()
        _built, refusals = self._generate([(entry, _source(entry))], answers={NPM: (404, b"{}")})
        self.assertEqual(refusals[0]["reason"], "package_version_not_published")
        _built, refusals = self._generate([(entry, _source(entry))], answers={NPM: (503, b"")})
        self.assertEqual(refusals[0]["reason"], "package_version_unknown")
        _built, refusals = self._generate([(entry, _source(entry))],
                                          answers={NPM: (200, json.dumps({"license": "AGPL-3.0-only"}).encode())})
        self.assertEqual(refusals[0]["reason"], "package_licence_not_on_allowlist")
        twin = _entry(name="io.github.example/weather-copy")
        built, refusals = self._generate([(entry, _source(entry)), (twin, _source(twin))])
        self.assertEqual((len(built), [row["reason"] for row in refusals]), (1, ["duplicate_package"]))


SPECIFICATION = {
    "openapi": "3.1.0", "info": {"title": "Example", "version": "2.0"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "security": [{"bearer": []}],
    "components": {
        "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"},
                            "key": {"type": "apiKey", "in": "header", "name": "X-Api-Key"}},
        "schemas": {"Thing": {"type": "object", "required": ["id", "name"],
                              "properties": {"id": {"type": "string", "readOnly": True}, "name": {"type": "string"},
                                             "size": {"type": "integer", "minimum": 3},
                                             "kind": {"type": "string", "enum": ["small", "large"]},
                                             "parent": {"$ref": "#/components/schemas/Thing"}}}}},
    "paths": {
        "/things/{thing_id}": {
            "parameters": [{"name": "thing_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {"operationId": "getThing", "summary": "Read one thing",
                    "parameters": [{"name": "expand", "in": "query", "schema": {"type": "boolean"}}],
                    "responses": {"200": {"description": "The thing", "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/Thing"},
                        "example": {"id": "t1", "name": "first"}}}},
                        "404": {"description": "No such thing"}}},
            "delete": {"operationId": "deleteThing", "security": [{"key": []}],
                       "responses": {"204": {"description": "Deleted"}}}},
        "/things": {
            "post": {"operationId": "createThing", "requestBody": {"required": True, "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/Thing"}}}},
                "responses": {"201": {"description": "Created", "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Thing"}}}}}},
            "put": {"operationId": "uploadThing", "requestBody": {"content": {"multipart/form-data": {}}},
                    "responses": {"200": {"description": "ok"}}}},
        "/remote/{name}": {"get": {"operationId": "remote", "parameters": [
            {"$ref": "other.json#/components/parameters/name"}], "responses": {"200": {"description": "ok"}}}},
        "/cookie": {"get": {"operationId": "withCookie", "parameters": [
            {"name": "session", "in": "cookie", "required": True, "schema": {"type": "string"}}],
            "responses": {"200": {"description": "ok"}}}},
    }}
SOURCE = {"source_id": "example", "repository": "example/api", "branch": "main", "paths": ["openapi.json"],
          "vendor": "example", "credential_variable": "EXAMPLE_TOKEN", "maximum_operations": 50}
SPEC_FACTS = {"title": "Example", "version": "2.0", "repository": "example/api", "commit": "c" * 40,
              "path": "openapi.json", "sha256": "d" * 64, "licence": "MIT", "base_url_variable": "EXAMPLE_BASE_URL"}


class OpenApiLineTest(unittest.TestCase):
    def test_operations_are_read_and_unsupported_ones_refused_by_name(self):
        from supply_lines import openapi_operations as line
        found, refused = line.operations(SPECIFICATION, SOURCE)
        self.assertEqual(sorted(operation.function for operation in found),
                         ["create_thing", "delete_thing", "get_thing"])
        self.assertEqual(sorted(row["reason"] for row in refused),
                         ["operation_body_not_json", "operation_parameters_unsupported",
                          "operation_parameters_unsupported"])
        get = next(operation for operation in found if operation.function == "get_thing")
        self.assertEqual([(row.python, row.location, row.required) for row in get.parameters],
                         [("thing_id", "path", True), ("expand", "query", False)])
        self.assertEqual(get.base_url, "https://api.example.com/v1")
        self.assertEqual(get.auth["placement"], "header")
        self.assertIn("recursive reference", json.dumps(get.response_schema))
        delete = next(operation for operation in found if operation.function == "delete_thing")
        self.assertEqual((delete.auth["name"], delete.response_kind, delete.success_statuses), ("X-Api-Key", "empty",
                                                                                              (204,)))
        create = next(operation for operation in found if operation.function == "create_thing")
        # A read-only field is not required in a request body.
        self.assertEqual(create.body_check["required"], ["name"])

    def test_every_generated_client_passes_its_own_tests_and_a_client_without_checks_fails_them(self):
        from supply_lines import openapi_operations as line
        found, _refused = line.operations(SPECIFICATION, SOURCE)
        with tempfile.TemporaryDirectory() as folder:
            for operation in found:
                call, example = line._example_arguments(operation), line._response_example(operation)
                target = Path(folder) / operation.module
                target.mkdir()
                client = line.client_source(operation, SPEC_FACTS)
                (target / f"{operation.module}.py").write_text(client, encoding="utf-8")
                (target / f"test_{operation.module}.py").write_text(line.test_source(operation, call, example),
                                                                     encoding="utf-8")
                passed, count, output = line.run_tests(target, operation.module)
                self.assertTrue(passed, output)
                self.assertGreaterEqual(count, 3)
                compile(client, operation.module, "exec")
            # Known wrong: a client that skips its argument checks must fail the generated tests.
            create = next(operation for operation in found if operation.function == "create_thing")
            broken = line.client_source(create, SPEC_FACTS).replace("        _check(body, BODY_SCHEMA, \"body\")\n",
                                                                    "        pass\n")
            (Path(folder) / create.module / f"{create.module}.py").write_text(broken, encoding="utf-8")
            passed, _count, _output = line.run_tests(Path(folder) / create.module, create.module)
            self.assertFalse(passed)
            # And a client that sends to a plain HTTP address fails them too.
            get = next(operation for operation in found if operation.function == "get_thing")
            broken = line.client_source(get, SPEC_FACTS).replace('if not root.startswith("https://"):',
                                                                 'if not root.startswith("http"):')
            (Path(folder) / get.module / f"{get.module}.py").write_text(broken, encoding="utf-8")
            self.assertFalse(line.run_tests(Path(folder) / get.module, get.module)[0])

    def test_the_network_is_closed_while_generated_tests_run(self):
        from supply_lines import openapi_operations as line
        import urllib.request
        before = urllib.request.urlopen
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "example_probe"
            target.mkdir()
            (target / "example_probe.py").write_text("", encoding="utf-8")
            (target / "test_example_probe.py").write_text(
                "import unittest, urllib.request\n\nclass T(unittest.TestCase):\n    def test_open(self):\n"
                "        urllib.request.urlopen('https://example.com')\n", encoding="utf-8")
            passed, count, output = line.run_tests(target, "example_probe")
        self.assertEqual((passed, count), (False, 1))
        self.assertIn("network is closed", output)
        self.assertIs(urllib.request.urlopen, before)


if __name__ == "__main__":
    unittest.main()

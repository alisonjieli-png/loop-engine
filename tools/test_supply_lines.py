"""The supply lines' records, packages, store writes and the protocol server line, offline.

Every guard has a known-wrong case: a licence outside the allowlist or joined by AND to one, a candidate record of
another version or with an extra field, a form a line may not declare, a package whose files hide text, a server
reached only over the network, a package version its registry does not publish, a second server for the same
package, and a supplied candidate that an export reading only imported copies would meet (it never does: the supply
namespace is its own).
"""
from __future__ import annotations

import copy
import math
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
        # The reviewer is told that the configuration downloads and runs a package.
        self.assertIn("downloads_and_runs_a_package", {finding["rule"] for finding in payload["findings"]})
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
        # Path keys that are not paths: a fragment that tells operations apart, a fixed query.
        "/things/{thing_id}#rename": {"put": {"operationId": "renameThing", "parameters": [
            {"name": "thing_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "responses": {"200": {"description": "ok"}}}},
        "/things/search?beta=true": {"post": {"operationId": "searchThings", "parameters": [
            {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}}],
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
                         ["create_thing", "delete_thing", "get_thing", "rename_thing", "search_things"])
        rename = next(operation for operation in found if operation.function == "rename_thing")
        self.assertEqual((rename.path, rename.path_key, rename.fixed_query),
                         ("/things/{thing_id}", "/things/{thing_id}#rename", ()))
        search = next(operation for operation in found if operation.function == "search_things")
        self.assertEqual((search.path, search.fixed_query), ("/things/search", (("beta", "true"),)))
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

    def test_a_declared_fallback_applies_only_when_the_specification_declares_no_security(self):
        from supply_lines import openapi_operations as line
        bare = {"openapi": "3.0.3", "info": {"title": "Bare", "version": "1"},
                "servers": [{"url": "https://api.example.com"}],
                "paths": {"/repos": {"get": {"operationId": "listRepos", "responses": {"200": {"description": "ok"}}}}}}
        source = {**SOURCE, "fallback_security": {"type": "http", "scheme": "bearer", "optional": True}}
        [operation], _refused = line.operations(bare, source)
        self.assertEqual((operation.auth["prefix"], operation.auth["variable"], operation.auth_optional),
                         ("Bearer ", "EXAMPLE_TOKEN", True))
        # Known wrong: a specification that declares its own schemes keeps them; the fallback never overrides.
        found, _refused = line.operations(SPECIFICATION, source)
        delete = next(item for item in found if item.function == "delete_thing")
        self.assertEqual(delete.auth["name"], "X-Api-Key")
        # Without a fallback, a bare specification's clients send no credential.
        [plain], _refused = line.operations(bare, SOURCE)
        self.assertIsNone(plain.auth)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / operation.module
            target.mkdir()
            (target / f"{operation.module}.py").write_text(line.client_source(operation, SPEC_FACTS), encoding="utf-8")
            (target / f"test_{operation.module}.py").write_text(
                line.test_source(operation, line._example_arguments(operation), line._response_example(operation)),
                encoding="utf-8")
            passed, _count, output = line.run_tests(target, operation.module)
            self.assertTrue(passed, output)

    def test_a_compacted_schema_keeps_every_property_name_and_drops_prose(self):
        from supply_lines import openapi_operations as line
        schema = {"type": "object", "description": "A thing.", "x-internal": True,
                  "properties": {"description": {"type": "string", "description": "Its text."},
                                 "deep": {"type": "object", "properties": {"a": {"type": "object", "properties": {
                                     "b": {"type": "string"}}}}}}}
        flat = line.compact(schema, None)
        self.assertEqual(flat["properties"]["description"], {"type": "string"})
        self.assertNotIn("description", flat)
        self.assertNotIn("x-internal", flat)
        shallow = line.compact(schema, 3)
        self.assertIn("$comment", json.dumps(shallow))
        self.assertIn("description", shallow["properties"])

    def test_a_package_whose_schema_is_above_the_bound_is_kept_with_a_compacted_schema(self):
        from supply_lines import openapi_operations as line
        from supply_lines.licences import RepositoryLicence
        found, _refused = line.operations(SPECIFICATION, SOURCE)
        create = next(operation for operation in found if operation.function == "create_thing")
        licence = RepositoryLicence("example/api", "c" * 40, "MIT", "agreed", "LICENSE", LICENCE, "MIT", "MIT", 1.0)
        generator = {"identity": "tools/supply_lines/openapi_operations.py", "version": "test",
                     "code_revision": "a" * 40}
        saved = line.MAXIMUM_REVIEW_FILE_BYTES
        line.MAXIMUM_REVIEW_FILE_BYTES = 900
        try:
            with tempfile.TemporaryDirectory() as folder:
                payload, bodies = line._package(create, {**SPEC_FACTS, "size_bytes": 10, "retrieved_at": "2026-09-27T00:00:00Z"},
                                                SOURCE, licence, generator, LICENCE, "2026-09-27", Path(folder), {})
        finally:
            line.MAXIMUM_REVIEW_FILE_BYTES = saved
        schema = next(bodies[entry["digest"]] for entry in payload["package"]["files"] if entry["path"] == "schema.json")
        self.assertIn(b"descriptions and examples are omitted", schema)
        self.assertEqual(payload["component_form"]["form"], "api_operation")

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


FORMULA = {"name": "sample", "desc": "Sample tool", "license": "MIT", "homepage": "https://example.org",
           "deprecated": False, "disabled": False, "versions": {"stable": "1.2.3"},
           "urls": {"stable": {"url": "https://example.org/sample-1.2.3.tar.gz", "checksum": "a" * 64}},
           "bottle": {"stable": {"files": {
               "arm64_sequoia": {"url": "https://ghcr.io/sample/arm", "sha256": "b" * 64},
               "sonoma": {"url": "https://ghcr.io/sample/intel", "sha256": "c" * 64},
               "x86_64_linux": {"url": "https://ghcr.io/sample/linux", "sha256": "d" * 64}}}}}
PROGRAM_ROW = {"formula": "sample", "program": "sample-no-such-program", "version_arguments": ["--version"],
               "repository": "example/sample", "effects": ["writes_fs"], "category": "files"}
RELEASE = {"tagName": "v1.2.3", "releaseAssets": {"nodes": [
    {"name": "sample-linux.tar.gz", "size": 10, "downloadUrl": "https://github.com/example/sample/linux",
     "digest": "sha256:" + "e" * 64},
    {"name": "sample-old.tar.gz", "size": 10, "downloadUrl": "https://github.com/example/sample/old", "digest": None}]}}


class ProgramLineTest(unittest.TestCase):
    def _write(self, folder, row=PROGRAM_ROW, formula=FORMULA, release=RELEASE):
        from supply_lines import program_installs as line
        from supply_lines.openapi_operations import literal, snake
        module = f"{snake(row['program'])}_program"
        plan = line.recipe(row, formula, release)
        wrapper = line.WRAPPER.format(title="t", program=row["program"], version=plan["version"],
                                      formula=formula["name"], description="Sample tool",
                                      version_arguments=literal(tuple(row["version_arguments"])), hint="brew install sample")
        target = Path(folder) / module
        target.mkdir()
        (target / f"{module}.py").write_text(wrapper, encoding="utf-8")
        (target / f"test_{module}.py").write_text(line.TESTS.format(program=row["program"], module=module,
                                                                    class_name="SampleTest"), encoding="utf-8")
        (target / "install.json").write_text(json.dumps(plan), encoding="utf-8")
        return target, module, plan

    def test_the_recipe_pins_each_platform_bottle_and_the_published_release_digests(self):
        from supply_lines import program_installs as line
        plan = line.recipe(PROGRAM_ROW, FORMULA, RELEASE)
        self.assertEqual(sorted(plan["platforms"]), ["linux-x86_64", "macos-arm64", "macos-x86_64"])
        self.assertEqual(plan["platforms"]["macos-arm64"]["bottle"]["sha256"], "b" * 64)
        self.assertEqual(plan["source"], {"url": "https://example.org/sample-1.2.3.tar.gz", "sha256": "a" * 64})
        # An asset without a published digest is left out; a release of another version is left out whole.
        self.assertEqual([asset["name"] for asset in plan["release"]["assets"]], ["sample-linux.tar.gz"])
        self.assertIsNone(line.recipe(PROGRAM_ROW, FORMULA, {**RELEASE, "tagName": "v9.9.9"})["release"])

    def test_the_wrapper_passes_its_own_tests_and_known_wrong_wrappers_fail_them(self):
        from supply_lines.openapi_operations import run_tests
        with tempfile.TemporaryDirectory() as folder:
            target, module, _plan = self._write(folder)
            passed, count, output = run_tests(target, module)
            self.assertTrue(passed, output)
            self.assertEqual(count, 5)  # four checks and the smoke test, skipped: the program is not installed
            source = (target / f"{module}.py").read_text(encoding="utf-8")
            for broken in (source.replace("shell=False", "shell=True"),
                           source.replace('        if "\\x00" in value:\n', '        if False:\n'),
                           source.replace("if isinstance(arguments, (str, bytes)):", "if False:")):
                self.assertNotEqual(broken, source)
                (target / f"{module}.py").write_text(broken, encoding="utf-8")
                self.assertFalse(run_tests(target, module)[0])

    def test_a_recipe_whose_checksum_is_not_published_fails_its_own_test(self):
        from supply_lines.openapi_operations import run_tests
        formula = json.loads(json.dumps(FORMULA))
        with tempfile.TemporaryDirectory() as folder:
            target, module, plan = self._write(folder, formula=formula)
            plan["platforms"]["macos-arm64"]["bottle"]["sha256"] = "not a digest"
            (target / "install.json").write_text(json.dumps(plan), encoding="utf-8")
            self.assertFalse(run_tests(target, module)[0])


class DataTableLineTest(unittest.TestCase):
    def test_each_declared_shape_is_read_as_rows_and_known_wrong_files_are_refused(self):
        from supply_lines import data_tables as line
        self.assertEqual(line.table_rows({"200": "OK", "404": "Not Found"}, "mapping", "code", "message"),
                         [{"code": "200", "message": "OK"}, {"code": "404", "message": "Not Found"}])
        self.assertEqual(line.table_rows({"cm": {"status": "standard"}}, "keyed_records", "unit", None),
                         [{"unit": "cm", "status": "standard"}])
        self.assertEqual(line.table_rows(["a", "b"], "values", "tag", None), [{"tag": "a"}, {"tag": "b"}])
        self.assertEqual(line.table_rows([{"country": "Chad", "code": 235}], "records", "country", None),
                         [{"country": "Chad", "code": 235}])
        wrong = [({"a": 1}, "records", "row_violates_schema"),
                 ([{"country": "Chad"}, {"country": "Chad"}], "records", "row_violates_schema"),
                 ([{"code": 1}], "records", "row_violates_schema"),
                 ({"cm": {"unit": "mm"}}, "keyed_records", "row_violates_schema"),
                 ([{"a": 1}], "values", "row_violates_schema"),
                 ([], "records", "table_empty")]
        for document, shape, reason in wrong:
            with self.assertRaises(line.TableRefused, msg=(document, shape)) as caught:
                line.table_rows(document, shape, "country" if shape == "records" else "unit", None)
            self.assertEqual(caught.exception.reason, reason)
        fields, required = line.infer_schema([{"code": "a", "n": 1}, {"code": "b", "n": 1.5, "x": None}])
        self.assertEqual((fields, required), ({"code": ["string"], "n": ["integer", "number"], "x": ["null"]},
                                              ["code", "n"]))

    def test_the_generated_loader_passes_its_tests_and_one_without_its_checks_fails_them(self):
        from supply_lines import data_tables as line
        from supply_lines.openapi_operations import literal, run_tests
        document = {"100": "Continue", "200": "OK", "404": "Not Found"}
        data = json.dumps(document).encode()
        table = line.table_rows(document, "mapping", "code", "message")
        fields, required = line.infer_schema(table)
        loader = line.LOADER.format(title="Status codes", count=len(table), file_name="codes.json",
                                    repository="example/statuses", commit="c" * 40, path="codes.json", licence="MIT",
                                    sha256=_digest(data), key_field="code", value_line="VALUE_FIELD = 'message'\n",
                                    fields=literal(fields), required=literal(required),
                                    shape_line=line.SHAPE_LINES["mapping"])
        tests = line.TESTS.format(table_id="status_codes", module="status_codes_table", class_name="StatusTest",
                                  first_key="100", missing_key="999", wrong_key=12345)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "status_codes_table"
            (target / "data").mkdir(parents=True)
            (target / "data" / "codes.json").write_bytes(data)
            (target / "status_codes_table.py").write_text(loader, encoding="utf-8")
            (target / "test_status_codes_table.py").write_text(tests, encoding="utf-8")
            passed, count, output = run_tests(target, "status_codes_table")
            self.assertTrue(passed, output)
            self.assertEqual(count, 5)
            for broken in (loader.replace("if hashlib.sha256(data).hexdigest() != DATA_SHA256:", "if False:"),
                           loader.replace("        if kinds is None:\n", "        if False:\n"),
                           loader.replace("    if missing:\n", "    if False:\n")):
                self.assertNotEqual(broken, loader)
                (target / "status_codes_table.py").write_text(broken, encoding="utf-8")
                self.assertFalse(run_tests(target, "status_codes_table")[0])


class VerbatimCodeSourcesTest(unittest.TestCase):
    def test_the_declaration_is_a_valid_import_source_of_code_modules_only(self):
        from licensed_import.harness_kinds import SourceScope, declared_kind
        from licensed_import.sources import read_sources
        record = read_sources(json.loads((HERE / "supply_lines" / "verbatim_code_sources.json").read_text("utf-8")))
        self.assertGreaterEqual(len(record["repositories"]), 5)
        for row in record["repositories"]:
            self.assertEqual(row["kinds"], ["code_module"], row["source_id"])
            self.assertTrue(row["include"], row["source_id"])
        python = next(row for row in record["repositories"] if row["repository"] == "TheAlgorithms/Python")
        scope = SourceScope(tuple(python["kinds"]), tuple(python["include"]), tuple(python["exclude"]))
        self.assertEqual(declared_kind("sorts/quick_sort.py", scope), ("code_module", "code_module"))
        # Known wrong: Project Euler solutions, scrapers, package markers and tests are never a module package.
        for path in ("project_euler/problem_001/sol1.py", "web_programming/fetch_jobs.py", "maths/__init__.py",
                     "sorts/test_quick_sort.py"):
            self.assertIsNone(declared_kind(path, scope), path)


class SupplyReportTest(unittest.TestCase):
    def test_the_projection_stops_when_supply_ends_and_keeps_skills_under_their_cap(self):
        from licensed_import.composition import load_targets
        from supply_lines.report import needs, project
        targets = load_targets()
        library = {"executable_code": 970, "connectors_and_extensions": 818, "skills": 5130,
                   "agents_and_commands": 1563, "instructions_and_rules": 3656, "data_and_contracts": 54}
        skills_only = {"skills": 1_000_000}
        result = project(targets, library, skills_only, 0.75)
        # Skills alone cannot grow a library that already holds more than its cap share of them: nothing is kept.
        self.assertEqual((result["reached"], result["slots_run"]), ({}, 0))
        # Known wrong: caps applied to each slot alone let a skills-only supply carry the library past 25,000
        # with skills far above their cap.
        from licensed_import.composition import slot_quotas
        counts = dict(library)
        while sum(counts.values()) < 25_000:
            counts["skills"] += int(round(slot_quotas(targets, 2000)["skills"] * 0.75))
        self.assertGreater(counts["skills"] / sum(counts.values()), 0.5)
        balanced = {name: 1_000_000 for name in library}
        result = project(targets, library, balanced, 0.75)
        self.assertEqual(sorted(result["reached"]), ["100000", "25000", "50000"])
        final = result["reached"]["100000"]["families"]
        for family in targets.families:
            self.assertAlmostEqual(final[family.name]["share"], family.share, delta=0.02)
        short = project(targets, library, {"skills": 10, "executable_code": 10}, 0.75)
        # The executable supply is drawn and ends; the skills stay undrawn, because the library is over their cap.
        self.assertEqual((short["not_reached"], short["end"]["supply_left"]["executable_code"],
                          short["end"]["supply_left"]["skills"]), (["25000", "50000", "100000"], 0, 10))
        # The export takes at most 15 candidates from one repository a slot: executable supply held by two
        # repositories gives at most 30 a slot, so it lasts many more slots than its quota alone would suggest.
        pools = {"executable_code": {"a/one": 600, "b/two": 600}}
        few = project(targets, library, {"executable_code": 1200}, 0.75, repositories=pools, ceiling=15)
        free = project(targets, library, {"executable_code": 1200}, 0.75)
        self.assertEqual(few["repository_ceiling"], 15)
        self.assertEqual(few["slots_run"], 40)
        self.assertLess(free["slots_run"], few["slots_run"])
        gaps = needs(targets, library, {"executable_code": 1000}, 0.75)
        self.assertEqual(gaps["100000"]["executable_code"]["approved_needed"], 35000 - 970)
        self.assertEqual(gaps["100000"]["executable_code"]["gap"], math.ceil((35000 - 970) / 0.75) - 1000)
        self.assertEqual(gaps["25000"]["skills"]["approved_needed"], 0)


if __name__ == "__main__":
    unittest.main()

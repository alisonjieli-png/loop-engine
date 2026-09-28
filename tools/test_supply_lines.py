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

    def test_a_scoped_mode_keeps_its_own_state_so_the_other_mode_never_withdraws_it(self):
        from supply_lines.store import SupplyStore
        with tempfile.TemporaryDirectory() as folder:
            curated = build(_package())
            directory = build(_package(identity="apis.guru/example:list_things", name="example-list-things",
                                       key=records.upstream_key(records.OPENAPI_OPERATIONS,
                                                                "apis.guru/example:list_things")))
            writer = SupplyStore(folder, writes_authorized=True)
            try:
                writer.write(records.OPENAPI_OPERATIONS, [directory], complete=False, scope="apis_guru_directory")
                result = writer.write(records.OPENAPI_OPERATIONS, [curated], complete=True)
                self.assertEqual((result["written"], result["withdrawn"]), (1, 0))
                self.assertEqual(writer.store.get(directory[0]["record_id"])["lifecycle"], "candidate")
                scoped = writer.store.get(records.state_record_id(records.OPENAPI_OPERATIONS, "apis_guru_directory"))
                self.assertEqual(list(scoped["payload"]["packages"].values()), [directory[0]["record_id"]])
                # Known wrong: one shared state lets the curated mode's complete run withdraw the directory's.
                writer.write(records.OPENAPI_OPERATIONS, [directory], complete=False)
                shared = writer.write(records.OPENAPI_OPERATIONS, [curated], complete=True)
                self.assertEqual(shared["withdrawn"], 1)
            finally:
                writer.close()
        with self.assertRaises(SupplyRecordError):
            records.state_record_id(records.OPENAPI_OPERATIONS, "somewhere_else")

    def test_a_store_write_leaves_the_disk_floor_free(self):
        import build_library_supply as builder
        with tempfile.TemporaryDirectory() as folder:
            args = builder.parser().parse_args(["data-tables", "--run-folder", folder, "--authorize-network-reads",
                                                "--authorize-store-writes", "--store-root", folder,
                                                "--minimum-free-gigabytes", "1000000"])
            result = builder.store(args, records.DATA_TABLES, [build(_package())], {}, complete=True)
            self.assertEqual((result["stored"], result["reason"]), (False, "free_space_below_the_floor"))
            self.assertEqual(list(Path(folder).iterdir()), [])
            self.assertEqual(builder.parser().parse_args(["data-tables", "--run-folder", folder,
                                                          "--authorize-network-reads"]).minimum_free_gigabytes, 15)


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

    def test_a_body_whose_other_shapes_allow_the_field_gets_no_false_known_wrong_test(self):
        from supply_lines import openapi_operations as line
        spec = {"openapi": "3.0.3", "info": {"title": "Shapes", "version": "1"},
                "servers": [{"url": "https://api.example.com"}],
                "paths": {"/items": {"post": {"operationId": "addItem", "requestBody": {"required": True, "content": {
                    "application/json": {"schema": {"type": "object", "required": ["content_id"],
                                                    "properties": {"content_id": {"type": "integer"}},
                                                    "anyOf": [{"required": ["content_id"]},
                                                              {"properties": {"note": {"type": "string"}}}]}}}},
                    "responses": {"201": {"description": "created"}}}}}}
        [operation], _refused = line.operations(spec, SOURCE)
        call = line._example_arguments(operation)
        source = line.test_source(operation, call, line._response_example(operation))
        self.assertNotIn("a_body_without_a_required_field", source)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / operation.module
            target.mkdir()
            (target / f"{operation.module}.py").write_text(line.client_source(operation, SPEC_FACTS), encoding="utf-8")
            (target / f"test_{operation.module}.py").write_text(source, encoding="utf-8")
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

    def test_a_specification_declares_its_own_licence_beside_its_repository(self):
        from supply_lines import declared_licences as declared
        from supply_lines import openapi_operations as line
        from supply_lines.licences import RepositoryLicence
        repository = declared.repository_declaration
        self.assertEqual(repository({"license": {"name": "MIT", "identifier": "MIT"}})[0], "MIT")
        self.assertEqual(repository({"license": {"name": "MIT", "url": "https://code.example.com/api/blob/main/LICENSE"}})[0],
                         "MIT")
        self.assertEqual(repository({"license": {"name": "Apache 2.0",
                                                 "url": "https://www.apache.org/licenses/LICENSE-2.0.html"}})[0],
                         "Apache-2.0")
        self.assertIsNone(repository({"title": "none"}))
        # Known wrong: a name off the table, an address naming another licence, an unaddressed generic name, and an
        # identifier that is not one SPDX identifier.
        for info in ({"license": {"name": "Proprietary"}},
                     {"license": {"name": "MIT", "url": "https://www.gnu.org/licenses/gpl-3.0.html"}},
                     {"license": {"name": "MIT", "url": "https://www.apache.org/licenses/LICENSE-2.0"}},
                     {"license": {"name": "Creative Commons"}},
                     {"license": {"name": "x", "identifier": "MIT OR GPL-3.0"}}):
            self.assertIsNone(repository(info)[0], info)
        # The directory mode also needs the address to confirm the name, word by word ("commit" is not MIT).
        self.assertIsNone(declared.declared_licence({"license": {"name": "MIT",
                                                                 "url": "https://example.org/commit/terms"}})[0])
        self.assertEqual(declared.declared_licence({"license": {"name": "Anything", "identifier": "ISC"}})[0], "ISC")

        class Texts:
            def text(self, spdx):
                return RepositoryLicence("github/choosealicense.com", "c" * 40, spdx, "agreed",
                                         f"_licenses/{spdx.lower()}.txt", b"licence text " + spdx.encode(), spdx, spdx, 1.0)

        mit = RepositoryLicence("example/api", "c" * 40, "MIT", "agreed", "LICENSE", LICENCE, "MIT", "MIT", 1.0)
        self.assertIsNone(line.declared_beside({}, mit, Texts(), "example/api/openapi.json"))
        same = line.declared_beside({"license": {"name": "MIT License"}}, mit, Texts(), "x")
        self.assertEqual((same["spdx"], same["text"]), ("MIT", None))
        other = line.declared_beside({"license": {"name": "Apache 2.0"}}, mit, Texts(), "x")
        self.assertEqual(other["text"].spdx, "Apache-2.0")
        with self.assertRaises(line.OperationRefused) as refused:
            line.declared_beside({"license": {"name": "Proprietary"}}, mit, Texts(), "x")
        self.assertEqual(refused.exception.reason, "licence_not_on_allowlist")
        # A second allowlisted licence travels with the package, and the expression names both.
        found, _refused = line.operations(SPECIFICATION, SOURCE)
        get = next(operation for operation in found if operation.function == "get_thing")
        generator = {"identity": "tools/supply_lines/openapi_operations.py", "version": "test",
                     "code_revision": "a" * 40}
        facts = {**SPEC_FACTS, "size_bytes": 10, "retrieved_at": "2026-09-27T00:00:00Z"}
        with tempfile.TemporaryDirectory() as folder:
            payload, bodies = line._package(get, {**facts, "declared_licence": other}, SOURCE, mit, generator,
                                            LICENCE, "2026-09-27", Path(folder), {})
            alone, _bodies = line._package(get, {**facts, "declared_licence": same}, SOURCE, mit, generator,
                                           LICENCE, "2026-09-27", Path(folder), {})
        self.assertEqual(payload["licence"]["spdx_expression"], "MIT AND Apache-2.0")
        self.assertIn(line.SPECIFICATION_LICENCE_NAME, payload["licence"]["texts"])
        self.assertEqual(alone["licence"]["spdx_expression"], "MIT")
        self.assertNotIn(line.SPECIFICATION_LICENCE_NAME, alone["licence"]["texts"])

    def test_generate_reads_each_specifications_own_licence_beside_the_repository_licence(self):
        from loop_engine.core.library_ingestion.record_rules import git_blob_identity
        from supply_lines import openapi_operations as line
        from supply_lines.declared_licences import licence_text_paths
        paths, _commit = licence_text_paths()
        small = {"openapi": "3.0.3", "info": {"title": "Small", "version": "1"},
                 "servers": [{"url": "https://api.example.com"}],
                 "paths": {"/ping": {"get": {"operationId": "ping", "responses": {"200": {"description": "ok"}}}}}}

        class Reader:
            def __init__(self, document):
                self.body = json.dumps(document).encode()

            def github(self, path):
                if path.endswith("/commits/main"):
                    return _Answer(200, json.dumps({"sha": "c" * 40}).encode())
                return _Answer(200, json.dumps({"sha": git_blob_identity(self.body)}).encode())

            def get(self, url, cache_errors=False):
                return _Answer(200, self.body)

            def licence_text(self, repository, commit):
                return "LICENSE", LICENCE, "MIT"

            def pinned_file(self, repository, commit, path):
                spdx = next(key for key, (where, _digest) in paths.items() if where == path)
                return {"sha256": paths[spdx][1], "commit": commit, "bytes": b"text of " + spdx.encode(),
                        "path": path}

        def run(info):
            document = {**small, "info": {**small["info"], **info}}
            with tempfile.TemporaryDirectory() as folder:
                return line.generate(Reader(document), [SOURCE], code_revision="a" * 40, licence_text=LICENCE,
                                     generated_on="2026-09-27", staging=Path(folder))

        built, refused, _facts, summary = run({"license": {"name": "Apache 2.0",
                                                           "url": "https://www.apache.org/licenses/LICENSE-2.0.html"}})
        self.assertEqual(refused, [])
        self.assertEqual([payload["licence"]["spdx_expression"] for payload, _bodies in built], ["MIT AND Apache-2.0"])
        self.assertEqual((summary[0]["licence"], summary[0]["declared_licence"]), ("MIT", "Apache-2.0"))
        built, refused, _facts, _summary = run({})
        self.assertEqual([payload["licence"]["spdx_expression"] for payload, _bodies in built], ["MIT"])
        # Known wrong: a specification that declares a licence off the allowlist is refused whole, although its
        # repository is MIT.
        built, refused, _facts, _summary = run({"license": {"name": "Proprietary"}})
        self.assertEqual((built, [row["reason"] for row in refused]), ([], ["licence_not_on_allowlist"]))

    def test_form_bodies_are_encoded_by_their_declared_style(self):
        from supply_lines import openapi_operations as line
        stripe = (("expand", "deepObject", True), ("metadata", "deepObject", True))
        self.assertEqual(line.form_pairs({"amount": 5, "expand": ["a", "b"], "metadata": {"k": "v", "n": None},
                                          "live": True, "skip": None}, stripe),
                         [("amount", "5"), ("expand[0]", "a"), ("expand[1]", "b"), ("metadata[k]", "v"),
                          ("live", "true")])
        self.assertEqual(line.form_pairs({"items": [{"price": "p1", "tax": [1, 2]}]}, (("items", "deepObject", True),)),
                         [("items[0][price]", "p1"), ("items[0][tax][0]", "1"), ("items[0][tax][1]", "2")])
        self.assertEqual(line.form_pairs({"Event": ["a", "b"], "Codes": ["x", "y"]}, (("Codes", "form", False),)),
                         [("Event", "a"), ("Event", "b"), ("Codes", "x,y")])
        self.assertEqual(line.form_pairs({"point": {"x": 1, "y": 2}}, ()), [("x", "1"), ("y", "2")])
        self.assertEqual(line.form_encoding({"encoding": {"b": {"style": "deepObject", "explode": True}, "a": {}}}),
                         (("a", "form", True), ("b", "deepObject", True)))
        spec = {"openapi": "3.0.0", "info": {"title": "Pay", "version": "1"},
                "servers": [{"url": "https://api.pay.example/"}],
                "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
                "security": [{"bearer": []}],
                "paths": {"/v1/charges": {"post": {"operationId": "PostCharges", "requestBody": {"required": True,
                    "content": {"application/x-www-form-urlencoded": {
                        "encoding": {"metadata": {"style": "deepObject", "explode": True}},
                        "schema": {"type": "object", "required": ["amount"], "properties": {
                            "amount": {"type": "integer"}, "metadata": {"type": "object", "example": {"order": "7"}},
                            "expand": {"type": "array", "items": {"type": "string"}}}}}}},
                    "responses": {"200": {"description": "ok", "content": {"application/json": {
                        "schema": {"type": "object", "properties": {"id": {"type": "string"}}}}}}}}}}}
        [operation], refused = line.operations(spec, SOURCE)
        self.assertEqual((refused, operation.body_media, operation.body_encoding),
                         ([], "application/x-www-form-urlencoded", (("metadata", "deepObject", True),)))
        # Known wrong: a list of objects in plain form style has no defined encoding, so the operation is refused.
        fields = spec["paths"]["/v1/charges"]["post"]["requestBody"]["content"]["application/x-www-form-urlencoded"]
        listed = copy.deepcopy(spec)
        listed["paths"]["/v1/charges"]["post"]["requestBody"]["content"]["application/x-www-form-urlencoded"] = {
            **fields, "schema": {**fields["schema"], "properties": {
                **fields["schema"]["properties"], "lines": {"type": "array", "items": {"type": "object"}}}}}
        found, refused = line.operations(listed, SOURCE)
        self.assertEqual((found, [row["reason"] for row in refused]), ([], ["operation_body_not_json"]))
        call = {"body": {"amount": 5, "metadata": {"order": "7"}}}
        source = line.test_source(operation, call, line._response_example(operation))
        client = line.client_source(operation, SPEC_FACTS)
        self.assertIn("EXPECTED_FORM = [('amount', '5'), ('metadata[order]', '7')]", source)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / operation.module
            target.mkdir()
            (target / f"{operation.module}.py").write_text(client, encoding="utf-8")
            (target / f"test_{operation.module}.py").write_text(source, encoding="utf-8")
            passed, _count, output = line.run_tests(target, operation.module)
            self.assertTrue(passed, output)
            # Known wrong: an encoder that flattens nested fields instead of bracketing them fails the test.
            broken = client.replace("            pairs += _deep(name, value)\n",
                                    "            pairs.append((name, _text(value)))\n")
            self.assertNotEqual(broken, client)
            (target / f"{operation.module}.py").write_text(broken, encoding="utf-8")
            self.assertFalse(line.run_tests(target, operation.module)[0])

    def test_a_single_scheme_requirement_is_preferred_and_a_combination_alone_is_refused(self):
        from supply_lines import openapi_operations as line
        schemes = {"email": {"type": "apiKey", "in": "header", "name": "X-Auth-Email"},
                   "key": {"type": "apiKey", "in": "header", "name": "X-Auth-Key"},
                   "token": {"type": "http", "scheme": "bearer"}}

        def spec(security):
            return {"openapi": "3.0.0", "info": {"title": "Edge", "version": "1"},
                    "servers": [{"url": "https://api.edge.example"}], "components": {"securitySchemes": schemes},
                    "paths": {"/zones": {"get": {"operationId": "listZones", "security": security,
                                                 "responses": {"200": {"description": "ok"}}}}}}

        [operation], _refused = line.operations(spec([{"email": [], "key": []}, {"token": []}]), SOURCE)
        self.assertEqual((operation.auth["scheme"], operation.auth["prefix"]), ("token", "Bearer "))
        # Known wrong: a requirement that combines schemes needs all of them, which the client does not send.
        found, refused = line.operations(spec([{"email": [], "key": [], "token": []}]), SOURCE)
        self.assertEqual((found, [row["reason"] for row in refused]), ([], ["security_scheme_unsupported"]))

    def test_json_media_types_and_a_self_hosted_address(self):
        from supply_lines import openapi_operations as line
        self.assertEqual(line.request_content({"application/json-patch+json": {"a": 1},
                                               "application/merge-patch+json": {"b": 2}}),
                         ("application/merge-patch+json", {"b": 2}))
        self.assertEqual(line.request_content({"*/*": {"schema": {}}})[0], "application/json")
        self.assertEqual(line.request_content({"application/json": {}, "*/*": {}})[0], "application/json")
        self.assertIsNone(line.request_content({"multipart/form-data": {}, "application/yaml": {}}))
        spec = {"openapi": "3.0.0", "info": {"title": "Cluster", "version": "1"},
                "components": {"securitySchemes": {"token": {"type": "apiKey", "in": "header",
                                                             "name": "authorization"}}},
                "security": [{"token": []}],
                "paths": {"/api/v1/namespaces/{name}": {"patch": {"operationId": "patchNamespace", "parameters": [
                    {"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {"required": True, "content": {
                        "application/json-patch+json": {"schema": {"type": "object"}},
                        "application/merge-patch+json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "ok", "content": {"application/json": {
                        "schema": {"type": "object"}}}}}}}}}
        [operation], refused = line.operations(spec, SOURCE)
        self.assertEqual((refused, operation.base_url, operation.body_media), ([], "", "application/merge-patch+json"))
        call = line._example_arguments(operation)
        source = line.test_source(operation, call, line._response_example(operation))
        client = line.client_source(operation, SPEC_FACTS)
        self.assertIn("test_known_wrong_without_an_address_nothing_is_sent", source)
        self.assertIn("application/merge-patch+json", source)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / operation.module
            target.mkdir()
            (target / f"{operation.module}.py").write_text(client, encoding="utf-8")
            (target / f"test_{operation.module}.py").write_text(source, encoding="utf-8")
            passed, _count, output = line.run_tests(target, operation.module)
            self.assertTrue(passed, output)
            # Known wrong: a client that falls back to a made-up address sends without being told where.
            broken = client.replace("BASE_URL = ''", "BASE_URL = 'https://localhost'")
            self.assertNotEqual(broken, client)
            (target / f"{operation.module}.py").write_text(broken, encoding="utf-8")
            self.assertFalse(line.run_tests(target, operation.module)[0])

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
        smoke = (line.SMOKE_DECLARED if row.get("declared", True) else line.SMOKE_CATALOGUE).format(
            program=row["program"])
        (target / f"test_{module}.py").write_text(line.TESTS.format(program=row["program"], module=module,
                                                                    class_name="SampleTest", smoke=smoke),
                                                  encoding="utf-8")
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

    def test_catalogue_rows_take_every_formula_the_curated_list_does_not_hold(self):
        from supply_lines import program_installs as line
        formulae = [{**FORMULA, "name": "sample", "executables": ["sample"]},
                    {**FORMULA, "name": "multi-tool", "executables": ["mt-b", "mt-a", "bad name;rm"],
                     "homepage": "https://github.com/example/multi-tool"},
                    {**FORMULA, "name": "library-only", "executables": []}]
        rows, skipped = line.catalogue_rows(formulae, {"sample"})
        self.assertEqual([(row["formula"], row["program"], row["executables"]) for row in rows],
                         [("multi-tool", "mt-a", ["mt-a", "mt-b"])])
        self.assertEqual(rows[0]["repository"], "example/multi-tool")
        self.assertEqual((rows[0]["declared"], rows[0]["effects"]), (False, ["network", "writes_fs"]))
        self.assertEqual(skipped, {"curated_or_unnamed": 1, "no_executables": 1})
        self.assertEqual(line.github_project({"homepage": "https://example.org",
                                              "urls": {"stable": {"url": "https://github.com/a/b/archive/v1.tar.gz"}}}),
                         "a/b")
        from supply_lines.openapi_operations import run_tests
        with tempfile.TemporaryDirectory() as folder:
            target, module, plan = self._write(folder, row={**PROGRAM_ROW, **rows[0], "program": "mt-no-such-program"})
            passed, count, output = run_tests(target, module)
            self.assertTrue(passed, output)
            self.assertEqual(plan["verify"]["basis"], "default_version_flag_the_program_may_not_support")
            self.assertEqual(plan["executables"], ["mt-a", "mt-b"])

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


SWAGGER2 = {
    "swagger": "2.0", "info": {"title": "Old", "version": "1"}, "host": "api.example.com", "basePath": "/v2",
    "schemes": ["http", "https"], "consumes": ["application/json"], "produces": ["application/json"],
    "securityDefinitions": {"key": {"type": "apiKey", "name": "api_key", "in": "query"},
                            "login": {"type": "basic"}},
    "security": [{"key": []}],
    "parameters": {"Limit": {"name": "limit", "in": "query", "type": "integer", "minimum": 1}},
    "definitions": {"Pet": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"},
                                                                                  "tag": {"type": "string"}}}},
    "paths": {
        "/pets": {
            "get": {"operationId": "listPets", "parameters": [{"$ref": "#/parameters/Limit"}],
                    "responses": {"200": {"description": "ok", "schema": {"type": "array",
                                                                          "items": {"$ref": "#/definitions/Pet"}}}}},
            "post": {"operationId": "addPet", "security": [{"login": []}],
                     "parameters": [{"name": "pet", "in": "body", "required": True,
                                     "schema": {"$ref": "#/definitions/Pet"}}],
                     "responses": {"201": {"description": "created", "schema": {"$ref": "#/definitions/Pet"}}}}},
        "/pets/{petId}/photo": {
            "post": {"operationId": "uploadPhoto", "consumes": ["multipart/form-data"],
                     "parameters": [{"name": "petId", "in": "path", "required": True, "type": "string"},
                                    {"name": "file", "in": "formData", "type": "file"}],
                     "responses": {"200": {"description": "ok"}}}}}}


class OpenApiDirectoryTest(unittest.TestCase):
    def test_declared_licences_map_only_by_exact_name_and_a_matching_address(self):
        from supply_lines import openapi_directory as line
        self.assertEqual(line.declared_licence({"license": {"name": "Apache 2.0 License",
                                                             "url": "http://www.apache.org/licenses/LICENSE-2.0.html"}}),
                         ("Apache-2.0", "Apache 2.0 License", "http://www.apache.org/licenses/LICENSE-2.0.html"))
        self.assertEqual(line.declared_licence({"license": {"name": "The MIT License (MIT)"}})[0], "MIT")
        self.assertEqual(line.declared_licence({"license": {"name": "Apache 2.0 License",
                                                             "url": "http://www.apache.org/licenses/"}})[0], "Apache-2.0")
        self.assertEqual(line.declared_licence({"license": {"name": "Creative Commons",
                                                             "url": "https://creativecommons.org/licenses/by/4.0/"}})[0],
                         "CC-BY-4.0")
        # Known wrong: a licence named by words the table does not hold, and a name whose address says otherwise.
        for info in ({"license": {"name": "Creative Commons Attribution 3.0"}}, {"license": {"name": "Microsoft"}},
                     {"license": {"name": "Creative Commons"}},
                     {"license": {"name": "Creative Commons", "url": "http://creativecommons.org/licenses/by/3.0/"}},
                     {"license": {"name": "MIT", "url": "https://www.gnu.org/licenses/gpl-3.0.html"}},
                     {"license": {"name": "Apache 2.0", "url": "https://opensource.org/licenses/MIT"}}):
            self.assertIsNone(line.declared_licence(info)[0], info)
        self.assertIsNone(line.declared_licence({"title": "no licence"}))
        self.assertEqual(line.origin_repository({"x-origin": [{"url": "https://raw.githubusercontent.com/Azure/"
                                                                        "azure-rest-api-specs/master/x/compute.json"}]}),
                         "Azure/azure-rest-api-specs")
        self.assertIsNone(line.origin_repository({"x-origin": [{"url": "https://developer.example.com/spec.yaml"}]}))
        listed = {"microsoft.com:graph", "microsoft.com:graph-beta", "azure.com:eventhub-EventHub-preview",
                  "azure.com:eventhub-EventHub", "example.com:beta"}
        self.assertEqual(line.stable_sibling("microsoft.com:graph-beta", listed), "microsoft.com:graph")
        self.assertEqual(line.stable_sibling("azure.com:eventhub-EventHub-preview", listed), "azure.com:eventhub-EventHub")
        # Known wrong: a preview without a listed stable release, and a stable release, are kept.
        self.assertIsNone(line.stable_sibling("example.com:beta", listed))
        self.assertIsNone(line.stable_sibling("microsoft.com:graph", listed))
        names = ["amazonaws.com:ec2", "azure.com:compute", "azure.com:network", "example.com"]
        self.assertEqual(line.selected(names, only=["azure.com"]), ["azure.com:compute", "azure.com:network"])
        self.assertEqual(line.selected(names, excluded=["azure.com", "amazonaws.com"]), ["example.com"])
        self.assertEqual(line.selected(names, only=["azure.com"], excluded=["azure.com:network"]), ["azure.com:compute"])
        self.assertEqual(line.selected(names), names)
        self.assertEqual(line.vendor_of("azure.com:compute"), "azure_compute")
        self.assertEqual(line.vendor_of("1password.local:connect"), "api_1password_connect")

    def test_a_declared_licence_needs_no_repository_and_an_undeclared_one_needs_an_agreed_origin(self):
        from supply_lines import openapi_directory as line
        from supply_lines.licences import RepositoryLicence

        class Texts:
            def text(self, spdx):
                return RepositoryLicence("github/choosealicense.com", "c" * 40, spdx, "agreed", "_licenses/x.txt",
                                         b"text", spdx, spdx, 1.0)

        class Reader:
            def __init__(self, licence):
                self.licence, self.asked = licence, 0

            def repository_facts(self, repositories):
                self.asked += 1
                return {repository.lower(): {"defaultBranchRef": {"target": {"oid": "d" * 40}}}
                        for repository in repositories}

            def licence_text(self, repository, commit):
                return self.licence

        mit = ("LICENSE", LICENCE, "MIT")
        declared = line.decide("a.com", {"license": {"name": "MIT"}}, Reader(None), Texts(), {})
        self.assertEqual((declared["decision"], declared["spdx"], declared["basis"]), ("agreed", "MIT", line.DIRECTORY_BASIS))
        origin = {"x-origin": [{"url": "https://raw.githubusercontent.com/example/specs/main/api.json"}]}
        agreed = line.decide("b.com", origin, Reader(mit), Texts(), {})
        self.assertEqual((agreed["decision"], agreed["spdx"], agreed["basis"]), ("agreed", "MIT", line.ORIGIN_BASIS))
        # Known wrong: a declared licence off the allowlist is refused even when the origin repository is MIT.
        refused = line.decide("c.com", {"license": {"name": "Microsoft"}, **origin}, Reader(mit), Texts(), {})
        self.assertEqual(refused["decision"], "licence_not_on_allowlist")
        self.assertEqual(line.decide("d.com", {"title": "x"}, Reader(mit), Texts(), {})["decision"], "licence_unknown")
        unreadable = line.decide("e.com", origin, Reader(None), Texts(), {})
        self.assertEqual(unreadable["decision"], "licence_unknown")

    def test_a_licence_file_address_is_decided_by_its_repository_and_must_agree_with_the_declared_name(self):
        from supply_lines import openapi_directory as line
        from supply_lines.licences import RepositoryLicence

        class Reader:
            def __init__(self, licence):
                self.licence = licence

            def repository_facts(self, repositories):
                return {repository.lower(): {"defaultBranchRef": {"target": {"oid": "d" * 40}}}
                        for repository in repositories}

            def licence_text(self, repository, commit):
                return self.licence

        class Texts:
            def text(self, spdx):
                raise AssertionError("a licence file address never takes a template text")

        self.assertEqual(line.licence_file_repository("https://github.com/XeroAPI/Xero-OpenAPI/blob/master/LICENSE"),
                         "XeroAPI/Xero-OpenAPI")
        self.assertEqual(line.licence_file_repository(
            "https://raw.githubusercontent.com/appwrite/appwrite/master/LICENSE"), "appwrite/appwrite")
        self.assertEqual(line.licence_file_repository("https://github.com/a/b/blob/main/COPYING.txt"), "a/b")
        for address in ("https://github.com/a/b/blob/main/README.md", "https://docs.example.org/LICENSE.txt",
                        "https://github.com/a/b", "./LICENSE", ""):
            self.assertIsNone(line.licence_file_repository(address), address)
        mit = ("LICENSE", LICENCE, "MIT")
        xero = {"license": {"name": "MIT", "url": "https://github.com/XeroAPI/Xero-OpenAPI/blob/master/LICENSE"}}
        agreed = line.decide("xero.com:xero_assets", xero, Reader(mit), Texts(), {})
        self.assertEqual((agreed["decision"], agreed["spdx"], agreed["basis"], agreed["licence_repository"]),
                         ("agreed", "MIT", line.LICENCE_FILE_BASIS, "XeroAPI/Xero-OpenAPI"))
        self.assertEqual(agreed["licence"].commit, "d" * 40)
        # Known wrong: the declared name and the repository's licence disagree, the name maps to no licence, or
        # the repository does not answer.
        apache = {"license": {"name": "Apache 2.0", "url": "https://github.com/XeroAPI/Xero-OpenAPI/blob/x/LICENSE"}}
        self.assertEqual(line.decide("x.com", apache, Reader(mit), Texts(), {})["decision"], "licence_signals_disagree")
        public = {"license": {"name": "Public Domain", "url": "https://github.com/a/b/blob/main/LICENSE"}}
        self.assertEqual(line.decide("y.com", public, Reader(mit), Texts(), {})["decision"], "licence_not_on_allowlist")
        self.assertEqual(line.decide("z.com", xero, Reader(None), Texts(), {})["decision"], "licence_unknown")

    def test_curated_sources_keep_their_directory_entries_and_one_operation_is_supplied_once(self):
        from supply_lines import openapi_directory as line
        from supply_lines import openapi_operations as generator
        covered = line.curated_coverage(generator.read_sources())
        self.assertEqual(line.covering_source("github.com:ghes-3.8", covered), "github")
        self.assertEqual(line.covering_source("twilio.com:api", covered), "twilio")
        self.assertEqual(line.covering_source("sendgrid.com", covered), "sendgrid")
        self.assertEqual(line.covering_source("openai.com", covered), "openai")
        # Known wrong: a sibling API of a covered one, or a same-named service elsewhere, is not covered.
        for name in ("twilio.com:twilio_chat_v2", "klarna.com:openai", "xero.com:xero_assets", "azure.com:compute"):
            self.assertIsNone(line.covering_source(name, covered), name)

        def one(server):
            document = {"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "servers": [{"url": server}],
                        "paths": {"/users/{id}": {"get": {"operationId": "getUser", "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                            "responses": {"200": {"description": "ok"}}}}}}
            found, _refused = generator.operations(document, {"source_id": "t", "vendor": "t",
                                                              "credential_prefix": "T", "maximum_operations": 5})
            return found[0]

        stable, preview = one("https://graph.example.com/v1.0"), one("https://graph.example.com/v1.0/")
        self.assertEqual(line.operation_key(stable), line.operation_key(preview))
        # Known wrong: APIs that share a host under different base paths are different operations.
        self.assertNotEqual(line.operation_key(stable), line.operation_key(one("https://graph.example.com/beta")))
        self.assertNotEqual(line.operation_key(stable), line.operation_key(one("https://other.example.com/v1.0")))
        # Known wrong: a coverage field that is not a list of names is refused when the sources are read.
        bad = {"record_type": generator.SOURCES_RECORD_TYPE, "specifications": [
            {"source_id": "x", "vendor": "x", "credential_variable": "X_KEY", "directory_names": "x.com"}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sources.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                generator.read_sources(path)

    def test_generate_leaves_covered_apis_to_their_source_and_supplies_one_operation_once(self):
        from supply_lines import openapi_directory as line
        from supply_lines.reading import https_address
        paths, _commit = line.licence_text_paths()
        names = ("example.com:graph", "example.com:graph-mirror", "github.com:ghes-3.8", "example.com:graph-beta")

        def specification(version):
            return {"openapi": "3.0.0", "info": {"title": "Graph", "version": "1", "license": {"name": "MIT"}},
                    "servers": [{"url": f"https://graph.example.com/{version}"}],
                    "paths": {"/users/{id}": {"get": {"operationId": "getUser", "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {"200": {"description": "ok", "content": {"application/json": {
                            "schema": {"type": "object", "properties": {"id": {"type": "string"}}}}}}}}}}}

        address = {name: f"https://{line.DIRECTORY_HOST}/v2/specs/{name.replace(':', '/')}/1/openapi.json"
                   for name in names}
        listing = {name: {"preferred": "1", "versions": {"1": {
            "info": {"title": name, "license": {"name": "MIT"}}, "swaggerUrl": address[name],
            "updated": "2026-09-01T00:00:00Z"}}} for name in names}
        answers = {https_address(line.DIRECTORY_HOST, line.DIRECTORY_LIST): json.dumps(listing).encode(),
                   address[names[0]]: json.dumps(specification("v1.0")).encode(),
                   address[names[1]]: json.dumps(specification("v1.0")).encode(),
                   address[names[2]]: json.dumps(specification("v3")).encode(),
                   address[names[3]]: json.dumps(specification("beta")).encode()}

        class Answer(_Answer):
            def __init__(self, url, status, body):
                super().__init__(status, body)
                self.url = url

        class Reader:
            def __init__(self):
                self.asked = []

            def get(self, url, cache_errors=False):
                self.asked.append(url)
                return Answer(url, 200, answers[url]) if url in answers else Answer(url, 404, b"{}")

            def pinned_file(self, repository, commit, path):
                return {"sha256": paths["MIT"][1], "commit": commit, "bytes": LICENCE, "path": path,
                        "url": f"https://raw.githubusercontent.com/{repository}/{commit}/{path}",
                        "retrieved_at": "2026-09-27T00:00:00Z"}

        reader = Reader()
        with tempfile.TemporaryDirectory() as folder:
            built, refused, _facts, decisions, summary = line.generate(
                reader, code_revision="a" * 40, licence_text=LICENCE, generated_on="2026-09-27",
                staging=Path(folder) / "staging")
        self.assertEqual([payload["provenance"]["repository"] for payload, _bodies in built],
                         ["apis.guru/example.com/graph"])
        self.assertEqual(sorted((row["reason"], row["subject"].split(" ")[0]) for row in refused),
                         [("covered_by_a_curated_source", "github.com:ghes-3.8"),
                          ("duplicate_operation", "example.com:graph-mirror"),
                          ("preview_beside_its_stable_release", "example.com:graph-beta")])
        self.assertEqual((summary["covered_by_a_curated_source"], summary["duplicate_operations"],
                          summary["preview_beside_its_stable_release"]), (1, 1, 1))
        # A covered API and a preview are never read: they are left to the curated source and the stable release.
        self.assertNotIn(address[names[2]], reader.asked)
        self.assertNotIn(address[names[3]], reader.asked)
        self.assertEqual([row["api"] for row in decisions], ["example.com:graph", "example.com:graph-mirror"])

    def test_a_swagger_2_document_becomes_operations_with_body_auth_and_servers(self):
        from supply_lines import openapi_directory as line
        from supply_lines import openapi_operations as generator
        document = line.swagger2_to_openapi3(SWAGGER2)
        source = {"source_id": "old", "vendor": "old", "credential_prefix": "OLD", "maximum_operations": 50}
        found, refused = generator.operations(document, source)
        by_name = {operation.function: operation for operation in found}
        self.assertEqual(sorted(by_name), ["add_pet", "list_pets"])
        self.assertEqual([row["reason"] for row in refused], ["operation_body_not_json"])
        self.assertEqual(by_name["list_pets"].base_url, "https://api.example.com/v2")
        self.assertEqual(by_name["list_pets"].auth, {"scheme": "key", "placement": "query", "name": "api_key",
                                                     "prefix": "", "variable": "OLD_API_KEY"})
        self.assertEqual(by_name["add_pet"].auth["variable"], "OLD_CREDENTIALS")
        self.assertEqual(by_name["add_pet"].body_check["required"], ["name"])
        self.assertEqual(by_name["list_pets"].parameters[0].check, {"type": ["integer"], "minimum": 1})
        with tempfile.TemporaryDirectory() as folder:
            for operation in found:
                target = Path(folder) / operation.module
                target.mkdir()
                (target / f"{operation.module}.py").write_text(generator.client_source(operation, SPEC_FACTS),
                                                               encoding="utf-8")
                (target / f"test_{operation.module}.py").write_text(generator.test_source(
                    operation, generator._example_arguments(operation), generator._response_example(operation)),
                    encoding="utf-8")
                passed, _count, output = generator.run_tests(target, operation.module)
                self.assertTrue(passed, output)

    def test_swagger_2_form_fields_keep_their_names_types_and_collection_formats(self):
        from supply_lines import swagger2
        document = {"swagger": "2.0", "info": {"title": "Chat", "version": "1"}, "host": "chat.example.com",
                    "basePath": "/api", "schemes": ["https"], "consumes": ["application/x-www-form-urlencoded"],
                    "paths": {"/chat.postMessage": {"post": {"operationId": "chat_postMessage", "parameters": [
                        {"name": "channel", "in": "formData", "type": "string", "required": True},
                        {"name": "users", "in": "formData", "type": "array", "items": {"type": "string"},
                         "collectionFormat": "multi"},
                        {"name": "tags", "in": "formData", "type": "array", "items": {"type": "string"}}],
                        "responses": {"200": {"description": "ok"}}}}}}
        converted = swagger2.swagger2_to_openapi3(document)
        body = converted["paths"]["/chat.postMessage"]["post"]["requestBody"]
        entry = body["content"]["application/x-www-form-urlencoded"]
        self.assertEqual((body["required"], entry["schema"]["required"], sorted(entry["schema"]["properties"])),
                         (True, ["channel"], ["channel", "tags", "users"]))
        self.assertEqual(entry["encoding"], {"users": {"style": "form", "explode": True},
                                             "tags": {"style": "form", "explode": False}})
        self.assertTrue(swagger2.is_swagger2(document))
        self.assertFalse(swagger2.is_swagger2(converted))

    def test_aws_operations_are_signed_with_the_sdk_metadata_and_pass_the_published_test_vector(self):
        from supply_lines import openapi_operations as generator
        region = {"default": "us-east-1", "enum": ["us-east-1", "eu-west-1"]}
        document = {
            "openapi": "3.0.0", "info": {"title": "Things", "version": "2020-01-01"},
            "servers": [{"url": "http://things.{region}.amazonaws.com", "variables": {"region": region}},
                        {"url": "https://things.{region}.amazonaws.com", "variables": {"region": region}}],
            "security": [{"hmac": []}],
            "components": {"securitySchemes": {"hmac": {"type": "apiKey", "name": "Authorization", "in": "header",
                                                        "x-amazon-apigateway-authtype": "awsSigv4"}},
                           "parameters": {"X-Amz-Date": {"name": "X-Amz-Date", "in": "header", "schema": {"type": "string"}}}},
            "paths": {
                "/#X-Amz-Target=Things_20200101.GetThing": {
                    "parameters": [{"$ref": "#/components/parameters/X-Amz-Date"}],
                    "post": {"operationId": "GetThing",
                             "parameters": [{"name": "X-Amz-Target", "in": "header", "required": True,
                                             "schema": {"type": "string", "enum": ["Things_20200101.GetThing"]}}],
                             "requestBody": {"required": True, "content": {"application/json": {"schema": {
                                 "type": "object", "required": ["Name"], "properties": {"Name": {"type": "string"}}}}}},
                             "responses": {"200": {"description": "ok", "content": {"application/json": {
                                 "schema": {"type": "object", "properties": {"Arn": {"type": "string"}}}}}}}}},
                "/#Action=ListThings": {
                    "get": {"operationId": "GET_ListThings",
                            "parameters": [{"name": "MaxResults", "in": "query", "schema": {"type": "integer"}},
                                           {"name": "Filter", "in": "query", "schema": {"type": "array",
                                                                                         "items": {"type": "string"}}}],
                            "responses": {"200": {"description": "ok", "content": {"text/xml": {
                                "schema": {"type": "object"}}}}}}}}}
        json_source = {"source_id": "things", "vendor": "things", "credential_prefix": "THINGS", "maximum_operations": 9,
                       "aws": {"protocol": "json", "json_version": "1.1", "signing_name": "things",
                               "api_version": "2020-01-01"}}
        found, refused = generator.operations(document, json_source)
        self.assertEqual(refused, [])
        get_thing = next(operation for operation in found if operation.function == "get_thing")
        self.assertEqual((get_thing.fixed_headers, get_thing.body_media, get_thing.path),
                         ((("X-Amz-Target", "Things_20200101.GetThing"),), "application/x-amz-json-1.1", "/"))
        self.assertEqual([parameter.wire for parameter in get_thing.parameters], [])
        self.assertEqual((get_thing.base_url_template, get_thing.region_default),
                         ("https://things.{region}.amazonaws.com", "us-east-1"))
        self.assertEqual(get_thing.auth["service"], "things")
        list_things = next(operation for operation in found if operation.function == "get_list_things")
        # The query protocol numbers list members; this client leaves an optional list out instead of sending it wrong.
        self.assertEqual([parameter.wire for parameter in list_things.parameters], ["MaxResults"])
        self.assertEqual(list_things.fixed_query, (("Action", "ListThings"), ("Version", "2020-01-01")))
        with tempfile.TemporaryDirectory() as folder:
            for operation in found:
                target = Path(folder) / operation.module
                target.mkdir()
                client = generator.client_source(operation, SPEC_FACTS)
                (target / f"{operation.module}.py").write_text(client, encoding="utf-8")
                source = generator.test_source(operation, generator._example_arguments(operation),
                                               generator._response_example(operation))
                self.assertIn("test_the_signature_matches_the_aws_test_vector", source)
                (target / f"test_{operation.module}.py").write_text(source, encoding="utf-8")
                passed, _count, output = generator.run_tests(target, operation.module)
                self.assertTrue(passed, output)
            # Known wrong: a signer with a wrong key derivation fails the published test vector.
            broken = client.replace('for part in (date, region, service, "aws4_request"):',
                                    'for part in (date, service, region, "aws4_request"):')
            self.assertNotEqual(broken, client)
            (target / f"{operation.module}.py").write_text(broken, encoding="utf-8")
            self.assertFalse(generator.run_tests(target, operation.module)[0])
        # The whole package builds: its README says how the request is signed, and every key is named.
        from supply_lines.licences import RepositoryLicence
        licence = RepositoryLicence("example/api", "c" * 40, "Apache-2.0", "agreed", "LICENSE", b"Apache text",
                                    "Apache-2.0", "Apache-2.0", 1.0)
        generator_record = {"identity": "tools/supply_lines/openapi_directory.py", "version": "test",
                            "code_revision": "a" * 40}
        with tempfile.TemporaryDirectory() as folder:
            payload, bodies = generator._package(get_thing, {**SPEC_FACTS, "size_bytes": 10,
                                                             "retrieved_at": "2026-09-27T00:00:00Z"},
                                                 json_source, licence, generator_record, LICENCE, "2026-09-27",
                                                 Path(folder), {})
        readme = next(bodies[entry["digest"]] for entry in payload["package"]["files"] if entry["path"] == "README.md")
        self.assertIn(b"AWS Signature Version 4", readme)
        self.assertEqual(payload["credentials"], ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"])
        # Without the SDK metadata, or for S3, a signing scheme is still refused.
        _found, refused = generator.operations(document, {**json_source, "aws": {}})
        self.assertEqual({row["reason"] for row in refused}, {"security_scheme_unsupported"})
        _found, refused = generator.operations(document, {**json_source, "aws": {**json_source["aws"],
                                                                                 "signing_name": "s3"}})
        self.assertEqual({row["reason"] for row in refused}, {"security_scheme_unsupported"})

    def test_a_request_signing_scheme_is_refused_by_name(self):
        from supply_lines import openapi_operations as generator
        document = {"openapi": "3.0.0", "info": {"title": "AWS", "version": "1"},
                    "servers": [{"url": "https://service.example.amazonaws.com"}], "security": [{"hmac": []}],
                    "components": {"securitySchemes": {"hmac": {"type": "apiKey", "name": "Authorization",
                                                                "in": "header",
                                                                "x-amazon-apigateway-authtype": "awsSigv4"}}},
                    "paths": {"/": {"get": {"operationId": "listThings", "responses": {"200": {"description": "ok"}}}}}}
        found, refused = generator.operations(document, {"source_id": "aws", "vendor": "aws", "credential_prefix": "AWS",
                                                         "maximum_operations": 5})
        self.assertEqual((found, [row["reason"] for row in refused]), ([], ["security_scheme_unsupported"]))


DISCOVERY = {
    "kind": "discovery#restDescription", "name": "things", "version": "v1", "title": "Things API",
    "rootUrl": "https://things.googleapis.com/", "servicePath": "",
    "parameters": {"alt": {"type": "string", "location": "query"}, "key": {"type": "string", "location": "query"}},
    "auth": {"oauth2": {"scopes": {"https://www.googleapis.com/auth/cloud-platform": {"description": "all"}}}},
    "schemas": {"Thing": {"id": "Thing", "type": "object", "properties": {
        "name": {"type": "string"}, "size": {"type": "string", "format": "int64"},
        "labels": {"type": "object", "additionalProperties": {"type": "string"}}, "extra": {"type": "any"},
        "parts": {"type": "array", "items": {"$ref": "Thing"}}}}},
    "resources": {"projects": {"resources": {"locations": {"resources": {"things": {"methods": {
        "get": {"id": "things.projects.locations.things.get", "path": "v1/{+name}", "httpMethod": "GET",
                "parameters": {"name": {"type": "string", "location": "path", "required": True,
                                        "pattern": "^projects/[^/]+/locations/[^/]+/things/[^/]+$"},
                               "view": {"type": "string", "location": "query", "enum": ["BASIC", "FULL"]}},
                "response": {"$ref": "Thing"}, "scopes": ["https://www.googleapis.com/auth/cloud-platform"]},
        "list": {"id": "things.projects.locations.things.list", "path": "v1/{+parent}/things", "httpMethod": "GET",
                 "parameters": {"parent": {"type": "string", "location": "path", "required": True,
                                           "pattern": "^projects/[^/]+/locations/[^/]+$"},
                                "pageSize": {"type": "integer", "format": "int32", "location": "query",
                                             "minimum": "1", "maximum": "100"},
                                "labels": {"type": "string", "location": "query", "repeated": True}},
                 "scopes": ["https://www.googleapis.com/auth/cloud-platform"]},
        "create": {"id": "things.projects.locations.things.create", "path": "v1/{+parent}/things",
                   "httpMethod": "POST",
                   "parameters": {"parent": {"type": "string", "location": "path", "required": True}},
                   "request": {"$ref": "Thing"}, "response": {"$ref": "Thing"},
                   "scopes": ["https://www.googleapis.com/auth/cloud-platform"]}}}}}}}},
    "methods": {"ping": {"id": "things.ping", "path": "v1/ping", "httpMethod": "GET"}}}


class GoogleDiscoveryTest(unittest.TestCase):
    def test_one_version_per_api_is_chosen_stable_first(self):
        from supply_lines import google_discovery as line
        folder = "googleapiclient/discovery_cache/documents/"
        names = ["drive.v2.json", "drive.v3.json", "compute.alpha.json", "compute.v1.json", "compute.beta.json",
                 "merchantapi.accounts_v1beta.json", "merchantapi.accounts_v1.json",
                 "merchantapi.products_v1beta.json", "aiplatform.v1beta1.json", "aiplatform.v1.json",
                 "labs.v1alpha.json", "labs.v1alpha2.json", "index.json"]
        chosen = [(path.rsplit("/", 1)[-1]) for path, _name, _version in line.choose_documents(folder + name
                                                                                           for name in names)]
        self.assertEqual(chosen, ["aiplatform.v1.json", "compute.v1.json", "drive.v3.json", "labs.v1alpha2.json",
                                  "merchantapi.accounts_v1.json", "merchantapi.products_v1beta.json"])
        self.assertEqual(line.version_rank("v1p1beta1"), ("", (1, 1, 0, 1)))
        self.assertIsNone(line.version_rank("alpha"))
        self.assertEqual(line.vendor_of("merchantapi", "accounts_v1"), "google_merchantapi_accounts_v1")

    def test_a_discovery_document_becomes_tested_clients_with_reserved_names(self):
        from supply_lines import google_discovery as line
        from supply_lines import openapi_operations as generator
        document = line.discovery_to_openapi3(DISCOVERY)
        self.assertEqual(document["servers"], [{"url": "https://things.googleapis.com"}])
        self.assertEqual(document["components"]["schemas"]["Thing"]["properties"]["parts"],
                         {"type": "array", "items": {"$ref": "#/components/schemas/Thing"}})
        self.assertEqual(document["components"]["schemas"]["Thing"]["properties"]["extra"], {})
        source = {"source_id": "google:things:v1", "vendor": "google_things_v1", "credential_variable":
                  line.CREDENTIAL_VARIABLE, "credential_prefix": "GOOGLE", "maximum_operations": 50}
        found, refused = generator.operations(document, source)
        self.assertEqual(refused, [])
        by_name = {operation.function: operation for operation in found}
        self.assertEqual(sorted(by_name), ["ping", "projects_locations_things_create", "projects_locations_things_get",
                                           "projects_locations_things_list"])
        get = by_name["projects_locations_things_get"]
        self.assertEqual((get.path, [row.reserved for row in get.parameters if row.location == "path"]),
                         ("/v1/{name}", [True]))
        self.assertEqual(get.parameters[0].example, "projects/example/locations/example/things/example")
        self.assertEqual(get.auth["variable"], "GOOGLE_ACCESS_TOKEN")
        self.assertIsNone(by_name["ping"].auth)
        listing = by_name["projects_locations_things_list"]
        self.assertEqual({row.wire: row.check.get("type") for row in listing.parameters},
                         {"parent": ["string"], "pageSize": ["integer"], "labels": ["array"]})
        spec = {**SPEC_FACTS, "base_url_variable": "GOOGLE_THINGS_V1_BASE_URL"}
        with tempfile.TemporaryDirectory() as folder:
            for operation in found:
                target = Path(folder) / operation.module
                target.mkdir()
                client = generator.client_source(operation, spec)
                (target / f"{operation.module}.py").write_text(client, encoding="utf-8")
                tests = generator.test_source(operation, generator._example_arguments(operation),
                                              generator._response_example(operation))
                (target / f"test_{operation.module}.py").write_text(tests, encoding="utf-8")
                passed, _count, output = generator.run_tests(target, operation.module)
                self.assertTrue(passed, output)
            # Known wrong: a client that escapes the slashes of a resource name fails its own test.
            client = generator.client_source(get, spec)
            broken = client.replace('safe="/" if wire_name in RESERVED_PATH else ""', 'safe=""')
            self.assertNotEqual(broken, client)
            (Path(folder) / get.module / f"{get.module}.py").write_text(broken, encoding="utf-8")
            self.assertFalse(generator.run_tests(Path(folder) / get.module, get.module)[0])

    def test_generate_reads_each_chosen_document_by_blob_identity_under_the_repository_licence(self):
        from loop_engine.core.library_ingestion.record_rules import git_blob_identity
        from supply_lines import google_discovery as line
        body = json.dumps(DISCOVERY).encode()
        folder = line.DISCOVERY_FOLDER
        tree = {"tree": [{"path": f"{folder}/things.v1.json", "type": "blob", "sha": git_blob_identity(body)},
                         {"path": f"{folder}/things.v1beta.json", "type": "blob", "sha": "0" * 40},
                         {"path": "README.md", "type": "blob", "sha": "1" * 40}]}

        class Reader:
            def __init__(self, bytes_served):
                self.bytes_served, self.asked = bytes_served, []

            def github(self, path):
                if "/commits/" in path:
                    return _Answer(200, json.dumps({"sha": "c" * 40}).encode())
                return _Answer(200, json.dumps(tree).encode())

            def licence_text(self, repository, commit):
                return "LICENSE", LICENCE, "MIT"

            def get(self, url, cache_errors=False):
                self.asked.append(url)
                return _Answer(200, self.bytes_served)

        reader = Reader(body)
        with tempfile.TemporaryDirectory() as staging:
            built, refused, _facts, summary = line.generate(reader, code_revision="a" * 40, licence_text=LICENCE,
                                                            generated_on="2026-09-27", staging=Path(staging))
        self.assertEqual((len(built), refused, summary["documents_chosen"]), (4, [], 1))
        self.assertEqual(reader.asked, [f"https://raw.githubusercontent.com/{line.DISCOVERY_REPOSITORY}/{'c' * 40}/"
                                        f"{folder}/things.v1.json"])
        names = sorted(payload["name"] for payload, _bodies in built)
        self.assertEqual(names[0], "google_things_v1-ping")
        self.assertTrue(all(payload["licence"]["spdx_expression"] == "MIT" for payload, _bodies in built))
        # Known wrong: bytes that are not the listed blob are refused, and nothing is built from them.
        with tempfile.TemporaryDirectory() as staging:
            built, refused, _facts, _summary = line.generate(Reader(body + b" "), code_revision="a" * 40,
                                                             licence_text=LICENCE, generated_on="2026-09-27",
                                                             staging=Path(staging))
        self.assertEqual((built, [row["reason"] for row in refused]), ([], ["specification_unreadable"]))


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

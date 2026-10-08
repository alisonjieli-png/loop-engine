"""Offline operation-contract scope of the existing JSON Schema supply line.

Reuse pinned licensed OpenAPI facts, never call an API. A decoded parameter
bundle, request body or response body is a job; labels and dates are not jobs.
The run owner materializes ordinary library_supply_candidate/v1 packages.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import urllib.parse

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from . import api_schemas, schema_check
from .openapi_operations import (METHODS, OperationRefused, Resolver, SPECIFICATION_LICENCE_NAME,
                                check_schema, clean_example, run_tests, synthesize)
from .packaging import (LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build, notice_files)
from .reading import FactReader, Fetched, GITHUB_HOST, RAW_HOST, github_blob_address, https_address
from .records import (GENERATED_CODE_LICENCE, JSON_SCHEMAS, LICENCE_TEXT, OPENAPI_OPERATIONS, OPERATION_CONTRACT_SCOPE,
                      fact_source, provenance, upstream_key)

GENERATOR_VERSION = "1.2.0"
STATE_SCOPE = OPERATION_CONTRACT_SCOPE
CONTRACT_TYPE = "api_operation_contract_atom/v2"
MAXIMUM_SOURCE_BYTES = 128 * 1024 * 1024
MAXIMUM_SCHEMA_BYTES = 128 * 1024
MAXIMUM_SCHEMA_NODES = 20_000
MAXIMUM_DEPTH = 32
ANNOTATIONS = frozenset({"title", "description", "default", "example", "examples", "$comment", "deprecated",
                         "readOnly", "writeOnly", "externalDocs", "discriminator", "xml"})
MAPS = frozenset({"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"})
SINGLE = frozenset({"items", "additionalProperties", "not", "contains", "propertyNames", "if", "then", "else"})
ARRAYS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
# These are the shared shipped validator's assertion vocabulary, not all JSON Schema.
ASSERTIONS = frozenset({"type", "enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "minLength", "maxLength", "pattern", "format", "minItems", "maxItems", "uniqueItems",
    "minContains", "maxContains", "minProperties", "maxProperties", "required", "dependentRequired"})


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


class CachedFacts(FactReader):
    """The existing fact cache protocol, with no network fallback or cache write."""

    def __init__(self, folder=None, *, cache_directory=None):
        if (folder is None) == (cache_directory is None):
            raise ValueError("one_explicit_cache_location_required")
        self.cache = Path(cache_directory).absolute() if cache_directory is not None else Path(folder).absolute() / "cache"
        if self.cache.resolve() != self.cache or not self.cache.is_dir():
            raise ValueError("fact_cache_not_regular")
        self.cache_hits = 0
        self.receipts = {}
        self.misses = []

    def get(self, url, **_kwargs):
        body_path, meta_path = self._paths(url)
        for path, limit in ((meta_path, 16_384), (body_path, MAXIMUM_SOURCE_BYTES)):
            if path.resolve() != path or not path.is_file() or path.stat().st_size > limit:
                self.misses.append(url)
                raise LookupError("offline_fact_missing_or_out_of_bounds")
        meta = json.loads(meta_path.read_bytes())
        body = body_path.read_bytes()
        if (meta.get("url") != url or meta.get("sha256") != hashlib.sha256(body).hexdigest()
                or meta.get("size_bytes") != len(body) or type(meta.get("status")) is not int
                or not isinstance(meta.get("retrieved_at"), str)):
            raise LookupError("offline_fact_integrity_mismatch")
        self.cache_hits += 1
        self.receipts[url] = {key: meta[key] for key in ("sha256", "status", "size_bytes", "retrieved_at")}
        return Fetched(url, meta["status"], body, meta["sha256"], meta["retrieved_at"], True)

    def github(self, path):
        return self.get(https_address(GITHUB_HOST, path))

    def repository_facts(self, repositories):
        """The native reader's exact GraphQL cache key, with no CLI/network fallback."""
        names = sorted(set(repositories))
        found = self.get("graphql:" + json.dumps(names))
        data = json.loads(found.body).get("data") or {}
        return {name.lower(): data.get("r" + str(index)) for index, name in enumerate(names)}


def normalize_schema(raw, document):
    """Resolve local refs without truncating constraints; unsupported/cyclic forms stay findings."""
    resolver, budget = Resolver(document), [MAXIMUM_SCHEMA_NODES]
    old_dialect = str(document.get("openapi", "")).startswith("3.0.")

    def convert(node, trail=(), depth=0):
        budget[0] -= 1
        if depth > MAXIMUM_DEPTH or budget[0] < 0:
            raise ValueError("schema_expansion_bound")
        if type(node) is bool:
            return node
        if type(node) is not dict:
            raise ValueError("schema_not_object")
        if "$ref" in node:
            ref = node["$ref"]
            if ref in trail:
                raise ValueError("recursive_schema_not_materialized")
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            if old_dialect and set(siblings) - ANNOTATIONS:
                raise ValueError("reference_assertion_siblings_unsupported")
            target = convert(resolver.target(ref), trail + (ref,), depth + 1)
            if not old_dialect and siblings:
                return {"allOf": [target, convert(siblings, trail, depth + 1)]}
            return target
        result = {}
        for key, value in node.items():
            if key in ANNOTATIONS or key.startswith("x-"):
                continue
            if key == "nullable" and old_dialect:
                continue
            if key in MAPS:
                if not isinstance(value, dict):
                    raise ValueError("schema_map_invalid")
                result[key] = {name: convert(child, trail, depth + 1) for name, child in sorted(value.items())}
            elif key in SINGLE:
                result[key] = convert(value, trail, depth + 1)
            elif key in ARRAYS:
                if not isinstance(value, list):
                    raise ValueError("schema_array_invalid")
                result[key] = [convert(child, trail, depth + 1) for child in value]
            elif key in ASSERTIONS:
                result[key] = deepcopy(value)
            else:
                raise ValueError("schema_keyword_unsupported")
        if old_dialect:
            for side in ("Minimum", "Maximum"):
                exclusive, bound = "exclusive" + side, side.lower()
                if type(result.get(exclusive)) is bool:
                    enabled = result.pop(exclusive)
                    if enabled:
                        if bound not in result:
                            raise ValueError("exclusive_bound_missing")
                        result[exclusive] = result.pop(bound)
            if node.get("nullable") is True and isinstance(result.get("type"), str):
                result["type"] = [result["type"], "null"]
        # Set-like assertion arrays have no semantic order. Preserve tuple schemas and examples.
        for name in ("required", "type"):
            if isinstance(result.get(name), list):
                result[name] = sorted(result[name])
        if "enum" in result:
            result["enum"] = sorted(result["enum"], key=lambda item: json.dumps(item, sort_keys=True))
        return result

    schema = convert(raw)
    if len(json_bytes(schema)) > MAXIMUM_SCHEMA_BYTES:
        raise ValueError("schema_byte_bound")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        raise ValueError("invalid_json_schema") from None
    return schema


def semantic_digest(schema):
    """Labels, provenance, dates and file paths cannot manufacture semantic novelty."""
    def walk(node, named=False):
        if isinstance(node, dict):
            result = {}
            for key, value in sorted(node.items()):
                if not named and (key in ANNOTATIONS or key == "$schema" or key.startswith("x-")):
                    continue
                value = walk(value, key in MAPS)
                if not named and key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    value = sorted(value, key=json_bytes)
                    if key != "oneOf":
                        value = list({json_bytes(item): item for item in value}.values())
                result[key] = value
            return result
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node
    return digest(walk(schema))


def pointer(part):
    return str(part).replace("~", "~0").replace("/", "~1")


def atoms(document):
    """Yield real API edges in stable order, not method/persona/word cross products.

    Parameter objects validate decoded values by location. Authentication,
    serialization, server behavior and success semantics remain separate.
    """
    resolver = Resolver(document)
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        yield {"finding": "paths_shape_unsupported", "pointer": "#/paths"}
        return
    for path, raw_path in sorted(paths.items()):
        try:
            path_item = resolver.follow(raw_path)
            if not isinstance(path_item, dict):
                raise ValueError("path_shape_unsupported")
        except (ValueError, LookupError, TypeError):
            yield {"finding": "path_reference_unreadable", "pointer": "#/paths/" + pointer(path)}
            continue
        for method in METHODS:
            if method not in path_item:
                continue
            operation = path_item[method]
            base = "#/paths/" + pointer(path) + "/" + method
            if not isinstance(operation, dict):
                yield {"finding": "operation_shape_unsupported", "pointer": base}
                continue
            context = {"method": method.upper(), "path": path,
                       "operation_id": operation.get("operationId"), "operation_pointer": base}
            try:
                parameters = {}
                for row in list(path_item.get("parameters", [])) + list(operation.get("parameters", [])):
                    row = resolver.follow(row)
                    parameters[(row["in"], row["name"])] = row
                if parameters:
                    locations = {}
                    for (location, name), row in sorted(parameters.items()):
                        if location not in ("path", "query", "header", "cookie") or "schema" not in row:
                            raise ValueError("parameter_shape_unsupported")
                        group = locations.setdefault(location, {"type": "object", "properties": {}, "required": []})
                        group["properties"][name] = row["schema"]
                        if row.get("required") is True or location == "path":
                            group["required"].append(name)
                    schema = {"type": "object", "properties": locations,
                              "required": sorted(key for key, value in locations.items() if value["required"])}
                    yield {**context, "phase": "parameters", "pointer": base + "/parameters", "schema": schema}
            except (ValueError, LookupError, KeyError, TypeError):
                yield {**context, "finding": "parameter_shape_unsupported", "pointer": base + "/parameters"}
            entries = []
            if "requestBody" in operation:
                entries.append(("request", base + "/requestBody", operation["requestBody"]))
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                yield {**context, "finding": "responses_shape_unsupported", "pointer": base + "/responses"}
                responses = {}
            for code, row in sorted(responses.items()):
                if not re.fullmatch(r"[1-5][0-9X]{2}|default", str(code)):
                    yield {**context, "finding": "response_status_unsupported", "pointer": base + "/responses/" + str(code)}
                    continue
                entries.append(("response:" + str(code), base + "/responses/" + pointer(code), row))
            for phase, where, raw in entries:
                try:
                    entry = resolver.follow(raw)
                    if not isinstance(entry, dict) or not isinstance(entry.get("content", {}), dict):
                        raise ValueError("body_shape_unsupported")
                    for media, content in sorted(entry.get("content", {}).items()):
                        if media.split(";", 1)[0] != "application/json" and not media.split(";", 1)[0].endswith("+json"):
                            continue
                        if isinstance(content, dict) and "schema" in content:
                            yield {**context, "phase": phase, "pointer": where + "/content/" + pointer(media) + "/schema",
                                   "media_type": media, "schema": content["schema"], "example": content.get("example")}
                except (ValueError, LookupError, TypeError):
                    yield {**context, "finding": "body_reference_unreadable", "pointer": where}


def cases(raw, schema):
    """Both the shipped validator and an independent JSON Schema implementation must agree."""
    validator = Draft202012Validator(schema)
    good = []
    candidates = [raw.get("example")]
    for every in (False, True):
        try:
            candidates.append(synthesize(check_schema(schema), every_property=every))
        except (ValueError, TypeError, RecursionError, LookupError):
            pass
    for candidate in candidates:
        candidate = clean_example(candidate)
        if validator.is_valid(candidate) and not schema_check.errors(candidate, schema) and candidate not in good:
            good.append(candidate)
    wrong = []
    alternatives = [None, True, 0, "", [], {}]
    for candidate in good:
        if isinstance(candidate, dict):
            alternatives += [{key: item for key, item in candidate.items() if key != required}
                             for required in schema.get("required", []) if required in candidate]
    for candidate in alternatives:
        if not validator.is_valid(candidate) and schema_check.errors(candidate, schema) and candidate not in wrong:
            wrong.append(candidate)
    if not good or not wrong:
        raise ValueError("discriminating_cases_unavailable")
    return {"valid": good[:3], "invalid": wrong[:4], "basis": "synthetic_local_contract_checks_not_provider_execution"}


TEST_TEXT = '''"""Check the decoded-value contract; no API request is made."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema_check

class ContractCases(unittest.TestCase):
    def test_valid(self):
        schema = json.loads((HERE / "contract.schema.json").read_text())
        cases = json.loads((HERE / "cases.json").read_text())
        self.assertTrue(cases["valid"])
        for value in cases["valid"]:
            self.assertEqual(schema_check.errors(value, schema), [])

    def test_invalid(self):
        schema = json.loads((HERE / "contract.schema.json").read_text())
        cases = json.loads((HERE / "cases.json").read_text())
        self.assertTrue(cases["invalid"])
        for value in cases["invalid"]:
            self.assertTrue(schema_check.errors(value, schema))

if __name__ == "__main__":
    unittest.main()
'''


def package(atom, schema, examples, spec, *, revision, generated_on, licence_text, staging):
    """An ordinary JSON Schema supply candidate with exact parent/source bindings."""
    identity = f"{spec['repository']}:{spec['path']}:{atom['pointer']}"
    parent = f"{spec['repository']}:{spec['path']}:{atom['method']} {atom['path']}"
    key = upstream_key(JSON_SCHEMAS, identity)
    # The phase selector is derived: inherited parameters and referenced body
    # objects need not exist at that literal location. Bind an actual Path Item
    # pointer and state the reference-following/selection rule separately.
    selection_pointer = "#/paths/" + urllib.parse.quote(pointer(atom["path"]), safe="~")
    selected = Resolver(spec["document"]).target(selection_pointer)
    if not isinstance(selected, dict):
        raise ValueError("source_selection_pointer_invalid")
    contract = {"record_type": CONTRACT_TYPE, "source_sha256": spec["sha256"], "source_revision": spec["commit"],
                "logical_selector": atom["pointer"], "parent_operation_key": upstream_key(OPENAPI_OPERATIONS, parent),
                "source_selection": {"pointers": [selection_pointer], "method": atom["method"], "phase": atom["phase"],
                    "media_type": atom.get("media_type"),
                    "derivation": "follow_local_refs_then_select_operation_phase/v1",
                    "parameter_merge": "path_item_then_operation_override_by_location_and_name"},
                "source_selection_basis": spec.get("pointer_basis", "pinned_openapi_document"),
                "normalized_source_view_sha256": spec.get("normalized_view_sha256") or digest(spec["document"]),
                "source_conversion": spec.get("conversion", "none"),
                "parent_binding": "upstream_job_reference_not_a_resolved_catalogue_dependency",
                "method": atom["method"], "path": atom["path"], "phase": atom["phase"],
                "operation_id": atom["operation_id"], "semantic_sha256": semantic_digest(schema),
                "network_calls": 0, "provider_behavior_tested": False}
    title = f"{atom['method']} {atom['path']} {atom['phase']}"
    schema = {"$schema": api_schemas.DIALECT, "title": title, "x-baltor-contract": contract, **schema}
    payloads = {"contract.schema.json": json_bytes(schema), "cases.json": json_bytes(examples),
                "schema_check.py": api_schemas.VALIDATOR_TEXT, "test_contract.py": TEST_TEXT.encode()}
    folder = staging / key
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        (folder / name).write_bytes(data)
    passed, count, _ = run_tests(folder, "contract")
    if not passed:
        raise ValueError("generated_contract_tests_failed")
    licence = spec["licence"]
    readme = (f"# {title}\n\nValidate this decoded {atom['phase']} value for {spec['title']} {spec['version']} "
              f"before composing it with another tool. Use `python schema_check.py contract.schema.json value.json`.\n\n"
              "`cases.json` contains synthetic passing and deliberately failing examples; "
              "`python -m unittest test_contract` checks both. No provider request was made. "
              "The parameters contract groups decoded values by path, query, header or cookie; it is not wire serialization. "
              "Formats and readOnly/writeOnly are annotations, not enforced permissions. Authentication, "
              "transport, server behavior and whether an HTTP status means task success require separate checks.\n\n"
              f"Source: `{spec['repository']}` at `{spec['commit']}`, `{spec['path']}`; "
              f"Path Item pointer `{selection_pointer}` in the {contract['source_selection_basis']} view. "
              f"`{atom['pointer']}` is a logical phase selector, not a literal source pointer. Follow local references "
              "before selecting the method, phase and media type. Merge path-item parameters with operation overrides "
              "by location and name; "
              f"conversion `{contract['source_conversion']}`; observed {spec['retrieved_at']}. This is a pinned historical "
              "contract, not a claim about the latest service. The schema's x-baltor-contract binds the "
              "parent operation job and exact source bytes. It does not resolve or authorize that operation.\n")
    files = [PackageFile(name, data, "executable_tool" if name.endswith(".py") else "other")
             for name, data in payloads.items()]
    licence_url = github_blob_address(licence.repository, licence.commit, licence.path)
    files += [PackageFile("README.md", readme.encode(), "other"),
              PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
              PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                          {"url": licence_url, "sha256": licence.sha256})]
    spec_url = spec.get("url") or https_address(RAW_HOST, f"{spec['repository']}/{spec['commit']}/{urllib.parse.quote(spec['path'])}")
    facts = [fact_source(spec_url, spec["retrieved_at"], spec["sha256"], spec["size_bytes"], "specification",
                        spdx=licence.spdx, basis=spec.get("licence_basis", "github_licence_interface_and_text_agree"),
                        evidence_sha256=licence.sha256),
             fact_source(licence_url, spec["retrieved_at"], licence.sha256, len(licence.text), "licence_text",
                         spdx=licence.spdx, basis=spec.get("licence_text_basis", "licence_file_at_the_pinned_commit"))]
    second = (spec.get("declared_licence") or {}).get("text")
    if second is not None:
        address = github_blob_address(second.repository, second.commit, second.path)
        files.append(PackageFile(SPECIFICATION_LICENCE_NAME, second.text, "other", LICENCE_TEXT,
                                 {"url": address, "sha256": second.sha256}))
        facts.append(fact_source(address, spec["retrieved_at"], second.sha256, len(second.text), "licence_text",
                                spdx=second.spdx, basis="specification_declared_licence"))
    notices, notice_facts = notice_files(spec.get("notices"))
    files += notices
    facts += notice_facts
    facts += list(spec.get("extra_facts") or ())
    expression = " AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx] + ([second.spdx] if second else [])))
    return build(SupplyPackage(line=JSON_SCHEMAS, identity=identity, key=key, kind="contract_schema",
        native_format=api_schemas.NATIVE_FORMAT, form="schema", name="api-contract-" + key,
        description=f"Validate {title[:200]} decoded values against a pinned API contract.", files=files,
        licence_expression=expression,
        provenance=provenance(spec.get("origin", "github_repository"), spec["repository"], spec["path"], spec["commit"], facts,
            {"identity": "tools/supply_lines/api_contract_atoms.py", "version": GENERATOR_VERSION, "code_revision": revision}),
        placements=[{"harness": "reference", "path": f"schemas/api-contract-{key}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "reads_schema_and_caller_supplied_value")], credentials=[],
        tests={"files": ["test_contract.py"], "command": "python -m unittest test_contract", "result": "passed",
               "tests_run": count, "network": False, "valid_instances": len(examples["valid"]),
               "known_wrong": len(examples["invalid"])},
        repository={"name": spec["repository"], "specification": spec["path"], "schema": title},
        generated_on=generated_on, comparison_text=identity))

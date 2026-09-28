"""Line json_schemas, API component mode: one JSON Schema per named object of a licensed OpenAPI specification.

```text
the curated sources of the API operation line (openapi_sources.json), read as that line reads them
├── licence: the repository's (interface and text agree) and the specification's own declaration
├── components.schemas (OpenAPI 3) or definitions (Swagger 2): every named object schema with at least two
│   properties or a combination (allOf, anyOf, oneOf)
├── the schema with its local references resolved (recursion cut, depth bounded) and OpenAPI's dialect written
│   as JSON Schema (nullable becomes a null type; examples, discriminators and extensions are left out)
├── tests: the specification's own example and small generated instances that the validator accepts, and two
│   known-wrong values (another type, and a valid instance without its first required field) it must refuse
└── package: <Name>.schema.json, schema_check.py (the same validator as every schema package), the test,
    README.md, LICENSE, UPSTREAM-LICENSE and, when the specification declares a second licence,
    SPECIFICATION-LICENSE; form schema, kind contract_schema, its own line state (scope api_components)
```
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import schema_check
from .declared_licences import LicenceTexts
from .openapi_operations import (
    SPECIFICATION_LICENCE_NAME, OperationRefused, Resolver, check_schema, clean_example, compact, literal,
    read_sources, read_specification, run_tests, synthesize)
from .packaging import LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import RAW_HOST, github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, JSON_SCHEMAS, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
NATIVE_FORMAT = "json_schema"
STATE_SCOPE = "api_components"
VALIDATOR_NAME = "schema_check.py"
VALIDATOR_TEXT = Path(schema_check.__file__).read_bytes()
DIALECT = "https://json-schema.org/draft/2020-12/schema"
#: OpenAPI keywords that describe rather than constrain: left out of the standalone schema.
_ANNOTATIONS = frozenset({"example", "examples", "discriminator", "xml", "externalDocs", "deprecated"})
_SEGMENT = re.compile(r"[^a-z0-9]+")
#: A value of another type than the schema's top-level type, for the known-wrong control.
WRONG_TYPE_VALUES = {"object": [], "array": {}, "string": 0, "number": "0", "integer": "0", "boolean": "true"}


def to_json_schema(node):
    """OpenAPI's schema dialect as JSON Schema: nullable becomes a null type, annotations and extensions go."""
    if isinstance(node, list):
        return [to_json_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    result = {}
    for key, value in node.items():
        if key in _ANNOTATIONS or str(key).startswith("x-") or key == "nullable":
            continue
        if key in ("properties", "patternProperties", "$defs", "definitions") and isinstance(value, dict):
            result[key] = {name: to_json_schema(part) for name, part in value.items()}
        else:
            result[key] = to_json_schema(value)
    if node.get("nullable") is True:
        kind = result.get("type")
        if isinstance(kind, str):
            result["type"] = [kind, "null"]
        elif isinstance(kind, list) and "null" not in kind:
            result["type"] = kind + ["null"]
        elif "enum" in result and None not in result["enum"]:
            result["enum"] = list(result["enum"]) + [None]
    return result


def named_schemas(document: dict) -> dict:
    """Name -> reference of every named schema of a document (OpenAPI 3 components or Swagger 2 definitions)."""
    found = {}
    for name in sorted(((document.get("components") or {}).get("schemas") or {})):
        found[name] = f"#/components/schemas/{name.replace('~', '~0').replace('/', '~1')}"
    for name in sorted(document.get("definitions") or {}):
        found.setdefault(name, f"#/definitions/{name.replace('~', '~0').replace('/', '~1')}")
    return found


def worth_a_package(schema: dict) -> bool:
    """An object with at least two properties, or a combination of shapes; a bare scalar or an empty object is not."""
    if not isinstance(schema, dict):
        return False
    return len(schema.get("properties") or {}) >= 2 or any(key in schema for key in ("allOf", "anyOf", "oneOf"))


def instances(raw: dict, schema: dict) -> list:
    """The valid instances a package tests: the specification's own example, then generated ones, each only when
    the validator accepts it; distinct, at most three."""
    candidates = []
    example = raw.get("example") if isinstance(raw, dict) else None
    if example is None and isinstance(raw, dict) and isinstance(raw.get("examples"), list) and raw["examples"]:
        example = raw["examples"][0]
    if example is not None:
        candidates.append(example)
    checked = check_schema(raw)
    for every in (False, True):
        try:
            candidates.append(synthesize(checked, every_property=every))
        except (TypeError, ValueError, RecursionError):
            continue
    kept = []
    for candidate in (clean_example(candidate) for candidate in candidates):
        try:
            if not schema_check.errors(candidate, schema) and candidate not in kept:
                kept.append(candidate)
        except (LookupError, RecursionError, TypeError, ValueError):
            continue
    return kept[:3]


def wrong_values(schema: dict, valid: list) -> list:
    """Known-wrong values the validator refuses: another top-level type, and a valid object without its first
    required field."""
    wrong = []
    kind = schema.get("type")
    kind = kind[0] if isinstance(kind, list) and kind else kind
    if isinstance(kind, str) and kind in WRONG_TYPE_VALUES and schema_check.errors(WRONG_TYPE_VALUES[kind], schema):
        wrong.append(WRONG_TYPE_VALUES[kind])
    required = schema.get("required") or []
    for instance in valid:
        if isinstance(instance, dict) and required and required[0] in instance:
            missing = {key: value for key, value in instance.items() if key != required[0]}
            if schema_check.errors(missing, schema):
                wrong.append(missing)
                break
    return wrong


def test_text(schema_file: str, valid: list, wrong: list) -> str:
    return ('"""The schema accepts the specification\'s example and generated instances, and refuses known-wrong '
            'values."""\nimport os\nimport sys\nimport unittest\n\n'
            "HERE = os.path.dirname(os.path.abspath(__file__))\nsys.path.insert(0, HERE)\n"
            "import schema_check  # noqa: E402\n\n"
            f"SCHEMA = {schema_file!r}\nVALID = {literal(valid)}\nWRONG = {literal(wrong)}\n\n\n"
            "class SchemaInstancesTest(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.schema = schema_check.load(os.path.join(HERE, SCHEMA))\n\n"
            "    def test_every_valid_instance_passes(self):\n"
            "        for instance in VALID:\n"
            "            self.assertEqual(schema_check.errors(instance, self.schema), [], instance)\n\n"
            "    def test_known_wrong_values_fail(self):\n"
            "        for instance in WRONG:\n"
            "            self.assertNotEqual(schema_check.errors(instance, self.schema), [], instance)\n\n\n"
            'if __name__ == "__main__":\n    unittest.main()\n')


def generate(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             maximum_per_specification: int = 400) -> tuple:
    """(built, refusals, facts, summary): the named object schemas of every curated specification."""
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/api_schemas.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    texts = LicenceTexts(reader)
    seen = set()
    for source in sources:
        for path in source["paths"]:
            try:
                spec = read_specification(reader, source, path, texts)
            except OperationRefused as error:
                refused.append(refusal(JSON_SCHEMAS, "source_unreadable", f"{source['source_id']} {path}",
                                       error.reason))
                continue
            facts[spec["sha256"]] = spec["bytes"]
            document = spec["document"]
            resolver = Resolver(document)
            kept = 0
            for name, reference in named_schemas(document).items():
                if kept >= maximum_per_specification:
                    break
                label = f"{source['source_id']} {name}"
                identity = f"{spec['repository']}:{spec['path']}:{reference}"
                module = (f"{source['vendor']}_" + _SEGMENT.sub("_", name.lower()).strip("_"))[:70]
                if module in seen:
                    refused.append(refusal(JSON_SCHEMAS, "duplicate_schema", label))
                    continue
                try:
                    raw = resolver.schema({"$ref": reference})
                except (OperationRefused, RecursionError):
                    refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", label))
                    continue
                if not worth_a_package(raw):
                    refused.append(refusal(JSON_SCHEMAS, "not_an_object_schema", label))
                    continue
                schema = {"$schema": DIALECT, "title": name, **to_json_schema(raw)}
                text = json.dumps(schema, indent=1, ensure_ascii=False) + "\n"
                for depth in (None, 5, 3):
                    if len(text.encode("utf-8")) <= MAXIMUM_REVIEW_FILE_BYTES:
                        break
                    schema = {"$schema": DIALECT, "title": name, **to_json_schema(compact(raw, depth))}
                    text = json.dumps(schema, indent=1, ensure_ascii=False) + "\n"
                valid = instances(raw, schema)
                if not valid:
                    refused.append(refusal(JSON_SCHEMAS, "valid_example_rejected", label, "no instance the "
                                           "validator accepts"))
                    continue
                wrong = wrong_values(schema, valid)
                try:
                    built.append(_package(name, module, schema, text, valid, wrong, spec, source, identity, generator,
                                          licence_text, generated_on, staging))
                    seen.add(module)
                    kept += 1
                except SupplyRecordError as error:
                    reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) \
                        else GENERATED_TEST_FAILED
                    refused.append(refusal(JSON_SCHEMAS, reason, label, str(error)[:200]))
            summary.append({"source_id": source["source_id"], "path": path, "licence": spec["licence"].spdx,
                            "named_schemas": len(named_schemas(document)), "packaged": kept})
    return built, refused, facts, summary


def _package(name, module, schema, text, valid, wrong, spec, source, identity, generator, licence_text, generated_on,
             staging):
    licence = spec["licence"]
    schema_file = f"{module}.schema.json"
    tests = test_text(schema_file, valid, wrong)
    folder = staging / module
    folder.mkdir(parents=True, exist_ok=True)
    for path, data in ((schema_file, text.encode("utf-8")), (VALIDATOR_NAME, VALIDATOR_TEXT),
                       (f"test_{module}.py", tests.encode("utf-8"))):
        (folder / path).write_bytes(data)
    passed, count, output = run_tests(folder, module)
    shutil.rmtree(folder, ignore_errors=True)
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, output[-300:])
    title = str(schema.get("description") or name).split("\n")[0][:200]
    readme = (f"# {name}\n\n{title}\n\n`{schema_file}` is the `{name}` object of the {spec['title']} OpenAPI "
              f"specification {spec['version']} at `{spec['repository']}` commit `{spec['commit']}` "
              f"(`{spec['path']}`), with its references resolved and written as JSON Schema; licensed "
              f"{licence.spdx}.\n\n`{VALIDATOR_NAME}` checks a document against it: `python {VALIDATOR_NAME} "
              f"{schema_file} document.json`.\n\n`test_{module}.py`: {len(valid)} valid instance"
              f"{'s' if len(valid) != 1 else ''} pass and {len(wrong)} known-wrong value{'s' if len(wrong) != 1 else ''} "
              f"fail ({count} tests).\n")
    upstream_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(schema_file, text.encode("utf-8"), "other"),
             PackageFile(VALIDATOR_NAME, VALIDATOR_TEXT, "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode("utf-8"), "executable_tool"),
             PackageFile("README.md", readme.encode("utf-8"), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": upstream_address, "sha256": licence.sha256})]
    second = (spec.get("declared_licence") or {}).get("text")
    if second is not None:
        files.append(PackageFile(SPECIFICATION_LICENCE_NAME, second.text, "other", LICENCE_TEXT,
                                 {"url": github_blob_address(second.repository, second.commit, second.path),
                                  "sha256": second.sha256}))
    spec_url = https_address(RAW_HOST, f"{spec['repository']}/{spec['commit']}/{spec['path']}")
    facts = [fact_source(spec_url, spec["retrieved_at"], spec["sha256"], spec["size_bytes"], "specification",
                         spdx=licence.spdx, basis="github_licence_interface_and_text_agree",
                         evidence_sha256=licence.sha256),
             fact_source(upstream_address, spec["retrieved_at"], licence.sha256, len(licence.text), "licence_text",
                         spdx=licence.spdx, basis="licence_file_at_the_pinned_commit")]
    expression = " AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx] +
                                            ([second.spdx] if second is not None else [])))
    supply = SupplyPackage(
        line=JSON_SCHEMAS, identity=identity, key=upstream_key(JSON_SCHEMAS, identity), kind="contract_schema",
        native_format=NATIVE_FORMAT, form="schema", name=f"{module.replace('_', '-')}-schema"[:90],
        description=f"JSON Schema of the {spec['title']} {name} object, with a validator and tests.",
        files=files, licence_expression=expression,
        provenance=provenance("github_repository", spec["repository"], spec["path"], spec["commit"], facts, generator),
        placements=[{"harness": "reference", "path": f"schemas/{module}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "reads_the_schema_and_the_document_it_is_given")], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False, "valid_instances": len(valid), "known_wrong": len(wrong)},
        repository={"name": spec["repository"], "specification": spec["path"], "schema": name},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


__all__ = ["STATE_SCOPE", "generate", "instances", "named_schemas", "to_json_schema", "worth_a_package",
           "wrong_values"]

"""Line json_schemas: one JSON Schema of a configuration file with a validator and its own examples as tests.

```text
SchemaStore/schemastore at its head commit (Apache-2.0: GitHub's licence interface and text agree)
├── src/schemas/json/<name>.json, read by git blob identity from the tree
├── one version per family (abc-plan-14.2.0 over abc-plan-1.0.0)
├── tests from the repository itself: src/test/<name>/*.json (must pass) and src/negative_test/<name>/*.json
│   (must fail), copied byte for byte beside the schema
├── schema_check.py: the same small validator in every package (drafts 4 to 2020-12, local references)
└── refused by name: a reference outside the file, no valid JSON example, a valid example the validator
    rejects, an older version of a listed family, a package above the review bound
```

An invalid example the validator accepts is left out of the package and counted;
a package keeps at least one valid example, and a value of the wrong top-level
type must fail (a known-wrong control) whenever the schema names its type.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from . import schema_check
from .licences import repository_licence
from .openapi_operations import run_tests
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import RAW_HOST, github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, JSON_SCHEMAS, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, UPSTREAM_VERBATIM, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

SCHEMA_REPOSITORY = "SchemaStore/schemastore"
SCHEMA_BRANCH = "master"
SCHEMA_FOLDER, VALID_FOLDER, INVALID_FOLDER = "src/schemas/json", "src/test", "src/negative_test"
HOSTS = (RAW_HOST,)
GENERATOR_VERSION = "1.0.0"
NATIVE_FORMAT = "json_schema"
VALIDATOR_NAME = "schema_check.py"
VALIDATOR_TEXT = Path(schema_check.__file__).read_bytes()
#: Examples one package carries at most, each at most this size.
MAXIMUM_EXAMPLES, MAXIMUM_EXAMPLE_BYTES = 20, 64 * 1024
_FAMILY = re.compile(r"^(?P<family>.+?)[-_]v?(?P<version>\d+(?:\.\d+)*)$")
_SEGMENT = re.compile(r"[^a-z0-9]+")
#: A value of another type than the schema's top-level type, for the known-wrong control.
WRONG_TYPE_VALUES = {"object": [], "array": {}, "string": 0, "number": "0", "integer": "0", "boolean": "true"}


def family_of(name: str) -> tuple:
    """(family, version numbers) of a schema name: abc-plan-14.2.0 -> (abc-plan, (14, 2, 0))."""
    match = _FAMILY.match(name)
    if match is None:
        return name, ()
    return match.group("family"), tuple(int(part) for part in match.group("version").split("."))


def choose(names) -> list:
    """The latest version of each family, in name order."""
    best = {}
    for name in sorted(names):
        family, version = family_of(name)
        if family not in best or version > best[family][0]:
            best[family] = (version, name)
    return sorted(name for _version, name in best.values())


def outside_references(node) -> list:
    """The references of a schema that point outside the file."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("$ref", "$recursiveRef", "$dynamicRef") and isinstance(value, str) and not value.startswith("#"):
                found.append(value)
            else:
                found += outside_references(value)
    elif isinstance(node, list):
        for value in node:
            found += outside_references(value)
    return found


def module_name(name: str) -> str:
    return ("schemastore_" + _SEGMENT.sub("_", name.lower()).strip("_"))[:80]


def test_text(schema_file: str, valid: list, invalid: list, wrong) -> str:
    lines = ['"""The schema\'s own examples from SchemaStore: every valid one passes, every invalid one fails."""',
             "import os", "import sys", "import unittest", "",
             "HERE = os.path.dirname(os.path.abspath(__file__))", "sys.path.insert(0, HERE)",
             "import schema_check  # noqa: E402", "", f"SCHEMA = {schema_file!r}", f"VALID = {valid!r}",
             f"INVALID = {invalid!r}", "", "",
             "class SchemaExamplesTest(unittest.TestCase):",
             "    def setUp(self):",
             "        self.schema = schema_check.load(os.path.join(HERE, SCHEMA))", "",
             "    def test_every_valid_example_passes(self):",
             "        for path in VALID:",
             "            instance = schema_check.load(os.path.join(HERE, path))",
             "            self.assertEqual(schema_check.errors(instance, self.schema), [], path)"]
    if invalid:
        lines += ["", "    def test_known_wrong_every_invalid_example_fails(self):",
                  "        for path in INVALID:",
                  "            instance = schema_check.load(os.path.join(HERE, path))",
                  "            self.assertNotEqual(schema_check.errors(instance, self.schema), [], path)"]
    if wrong is not None:
        lines += ["", "    def test_known_wrong_a_value_of_another_type_fails(self):",
                  f"        self.assertNotEqual(schema_check.errors({wrong!r}, self.schema), [])"]
    lines += ["", "", 'if __name__ == "__main__":', "    unittest.main()", ""]
    return "\n".join(lines)


def generate(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path, only=None,
             maximum_schemas: "int | None" = None) -> tuple:
    """(built, refusals, facts, summary) of every chosen SchemaStore schema that has valid JSON examples."""
    head = reader.github(f"repos/{SCHEMA_REPOSITORY}/commits/{SCHEMA_BRANCH}")
    if head.status != 200:
        raise SupplyRecordError("source_unreadable", f"{SCHEMA_REPOSITORY}: no head commit")
    commit = json.loads(head.body)["sha"]
    licence = repository_licence(reader, SCHEMA_REPOSITORY, commit)
    if not licence.allowed:
        raise SupplyRecordError("licence_not_on_allowlist", f"{SCHEMA_REPOSITORY}: {licence.reason}")
    tree = reader.github(f"repos/{SCHEMA_REPOSITORY}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise SupplyRecordError("source_unreadable", f"{SCHEMA_REPOSITORY}: no tree at {commit[:12]}")
    blobs = {entry["path"]: (entry["sha"], entry.get("size", 0)) for entry in json.loads(tree.body).get("tree", [])
             if entry.get("type") == "blob"}
    names = {Path(path).stem for path in blobs if re.fullmatch(rf"{SCHEMA_FOLDER}/[^/]+\.json", path)}
    examples = {}
    for path, (_sha, size) in blobs.items():
        for folder, kind in ((VALID_FOLDER, "valid"), (INVALID_FOLDER, "invalid")):
            if path.startswith(folder + "/") and path.endswith(".json") and path.count("/") == 3 \
                    and size <= MAXIMUM_EXAMPLE_BYTES:
                examples.setdefault(path.split("/")[2], {}).setdefault(kind, []).append(path)
    refused, built, facts = [], [], {}
    candidates = sorted(name for name in names if examples.get(name, {}).get("valid"))
    chosen = choose(candidates)
    for name in sorted(set(candidates) - set(chosen)):
        refused.append(refusal(JSON_SCHEMAS, "older_version_of_a_listed_schema", name, family_of(name)[0]))
    if only:
        chosen = [name for name in chosen if name in set(only)]
    if maximum_schemas:
        chosen = chosen[:maximum_schemas]
    summary = {"schemas_listed": len(names), "with_valid_examples": len(candidates), "chosen": len(chosen),
               "invalid_examples_not_caught": 0, "packaged": 0}
    generator = {"identity": "tools/supply_lines/json_schemas.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}

    def read(path):
        answer = reader.get(https_address(RAW_HOST, f"{SCHEMA_REPOSITORY}/{commit}/{path}"))
        if answer.status != 200 or git_blob_identity(answer.body) != blobs[path][0]:
            raise LookupError(path)
        facts[answer.sha256] = answer.body
        return answer

    for name in chosen:
        schema_path = f"{SCHEMA_FOLDER}/{name}.json"
        try:
            schema_answer = read(schema_path)
            schema = json.loads(schema_answer.body)
            valid = [(path, read(path)) for path in sorted(examples[name].get("valid", []))[:MAXIMUM_EXAMPLES]]
            invalid = [(path, read(path)) for path in sorted(examples[name].get("invalid", []))[:MAXIMUM_EXAMPLES]]
            parsed = {path: json.loads(answer.body) for path, answer in valid + invalid}
        except (LookupError, ValueError) as error:
            refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", name, str(error)[:120]))
            continue
        if not isinstance(schema, dict):
            refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", name, "not a JSON object"))
            continue
        outside = outside_references(schema)
        if outside:
            refused.append(refusal(JSON_SCHEMAS, "needs_an_outside_reference", name, outside[0][:120]))
            continue
        try:
            rejected = [path for path, _answer in valid if schema_check.errors(parsed[path], schema)]
            caught = [(path, answer) for path, answer in invalid if schema_check.errors(parsed[path], schema)]
        except (LookupError, RecursionError, TypeError, ValueError) as error:
            refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", name, f"{type(error).__name__}: {error}"[:120]))
            continue
        if rejected:
            refused.append(refusal(JSON_SCHEMAS, "valid_example_rejected", name, rejected[0]))
            continue
        summary["invalid_examples_not_caught"] += len(invalid) - len(caught)
        kind = schema.get("type")
        wrong = WRONG_TYPE_VALUES.get(kind) if isinstance(kind, str) else None
        if wrong is not None and not schema_check.errors(wrong, schema):
            wrong = None
        try:
            built.append(_package(name, schema_path, schema_answer, valid, caught, wrong, commit, licence, generator,
                                  licence_text, generated_on, staging))
            summary["packaged"] += 1
        except SupplyRecordError as error:
            reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                GENERATED_TEST_FAILED
            refused.append(refusal(JSON_SCHEMAS, reason, name, str(error)[:200]))
    return built, refused, facts, summary


def _package(name, schema_path, schema_answer, valid, invalid, wrong, commit, licence, generator, licence_text,
             generated_on, staging):
    module = module_name(name)
    schema_file = f"{name}.schema.json"
    valid_files = [f"examples/valid/{Path(path).name}" for path, _answer in valid]
    invalid_files = [f"examples/invalid/{Path(path).name}" for path, _answer in invalid]
    tests = test_text(schema_file, valid_files, invalid_files, wrong)
    folder = staging / module
    for path, data in [(schema_file, schema_answer.body), (VALIDATOR_NAME, VALIDATOR_TEXT),
                       (f"test_{module}.py", tests.encode("utf-8"))] + \
            [(target, answer.body) for target, (_path, answer) in zip(valid_files + invalid_files, valid + invalid)]:
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_bytes(data)
    passed, count, output = run_tests(folder, module)
    for leftover in sorted(folder.rglob("*"), reverse=True):
        leftover.unlink() if leftover.is_file() else leftover.rmdir()
    folder.rmdir()
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, output[-300:])
    schema = json.loads(schema_answer.body)
    title = str(schema.get("title") or schema.get("description") or name).split("\n")[0][:200]
    readme = (f"# {name}\n\n{title}\n\n`{schema_file}` is SchemaStore's JSON Schema for {name}, copied byte for byte "
              f"from {SCHEMA_REPOSITORY} at commit `{commit}` ({schema_path}), licensed {licence.spdx}.\n\n"
              f"`{VALIDATOR_NAME}` checks a document against it: `python {VALIDATOR_NAME} {schema_file} document.json` "
              "prints each problem and exits 1 when there is one. It follows the file's own references and does not "
              "check formats.\n\n"
              f"`test_{module}.py` runs SchemaStore's own examples: {len(valid)} valid "
              f"example{'s' if len(valid) != 1 else ''} must pass and {len(invalid)} invalid "
              f"example{'s' if len(invalid) != 1 else ''} must fail ({count} tests).\n")
    upstream_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(schema_file, schema_answer.body, "other", UPSTREAM_VERBATIM,
                         {"url": github_blob_address(SCHEMA_REPOSITORY, commit, schema_path),
                          "sha256": schema_answer.sha256}),
             PackageFile(VALIDATOR_NAME, VALIDATOR_TEXT, "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode("utf-8"), "executable_tool"),
             PackageFile("README.md", readme.encode("utf-8"), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": upstream_address, "sha256": licence.sha256})]
    for target, (path, answer) in zip(valid_files + invalid_files, valid + invalid):
        files.append(PackageFile(target, answer.body, "other", UPSTREAM_VERBATIM,
                                 {"url": github_blob_address(SCHEMA_REPOSITORY, commit, path), "sha256": answer.sha256}))
    facts = [fact_source(https_address(RAW_HOST, f"{SCHEMA_REPOSITORY}/{commit}/{schema_path}"),
                         schema_answer.retrieved_at, schema_answer.sha256, len(schema_answer.body), "data_source",
                         spdx=licence.spdx, basis="github_licence_interface_and_text_agree",
                         evidence_sha256=licence.sha256),
             fact_source(upstream_address, schema_answer.retrieved_at, licence.sha256, len(licence.text),
                         "licence_text", spdx=licence.spdx, basis="licence_file_at_the_pinned_commit")]
    identity = f"{SCHEMA_REPOSITORY}:{schema_path}"
    supply = SupplyPackage(
        line=JSON_SCHEMAS, identity=identity, key=upstream_key(JSON_SCHEMAS, identity), kind="contract_schema",
        native_format=NATIVE_FORMAT, form="schema", name=f"schemastore-{module[len('schemastore_'):].replace('_', '-')}"[:90],
        description=f"JSON Schema for {name}: {title[:180]} With a validator and SchemaStore's own examples as tests.",
        files=files, licence_expression=" AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx])),
        provenance=provenance("github_repository", SCHEMA_REPOSITORY, schema_path, commit, facts, generator),
        placements=[{"harness": "reference", "path": f"schemas/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "reads_the_schema_and_the_document_it_is_given")], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False, "valid_examples": len(valid), "invalid_examples": len(invalid)},
        repository={"name": SCHEMA_REPOSITORY, "schema": schema_path, "family": family_of(name)[0]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


__all__ = ["SCHEMA_REPOSITORY", "choose", "family_of", "generate", "outside_references", "test_text"]

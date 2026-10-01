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

```text
curated mode (generate_curated): the sources of json_schema_sources.json, its own line state (scope curated_schemas)
├── each repository at its branch's head commit, its licence decided the same way (interface and text agree)
├── each declared schema read by git blob identity and copied byte for byte; a reference to a sibling file of
│   the repository or to another address refuses it by name (no bundling)
├── tests: the repository's own examples (listed paths or a pattern over the tree) where it has them, a valid
│   example the validator rejects left out and counted; otherwise the schema's own example and generated
│   instances with two known-wrong values, as API component mode writes them
└── package: <vendor>_<name>.schema.json, schema_check.py, the test, README.md, LICENSE, UPSTREAM-LICENSE
```
"""
from __future__ import annotations

import fnmatch
import json
import math
import re
from pathlib import Path

from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from . import schema_check
from .licences import repository_licence
from .openapi_operations import OperationRefused, Resolver, run_tests
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build, notice_files
from .reading import RAW_HOST, github_blob_address, https_address, repository_notice
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, JSON_SCHEMAS, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, REFUSAL_REASONS, UPSTREAM_VERBATIM, SupplyRecordError, fact_source, provenance,
    refusal, upstream_key)

SCHEMA_REPOSITORY = "SchemaStore/schemastore"
SCHEMA_BRANCH = "master"
SCHEMA_FOLDER, VALID_FOLDER, INVALID_FOLDER = "src/schemas/json", "src/test", "src/negative_test"
HOSTS = (RAW_HOST,)
GENERATOR_VERSION = "1.1.0"
NATIVE_FORMAT = "json_schema"
VALIDATOR_NAME = "schema_check.py"
VALIDATOR_TEXT = Path(schema_check.__file__).read_bytes()
#: Examples one package carries at most, each at most this size.
MAXIMUM_EXAMPLES, MAXIMUM_EXAMPLE_BYTES = 20, 64 * 1024
_FAMILY = re.compile(r"^(?P<family>.+?)[-_]v?(?P<version>\d+(?:\.\d+)*)$")
_SEGMENT = re.compile(r"[^a-z0-9]+")
#: A value of another type than the schema's top-level type, for the known-wrong control.
WRONG_TYPE_VALUES = {"object": [], "array": {}, "string": 0, "number": "0", "integer": "0", "boolean": "true"}
#: A value of each common format, for an instance built from a schema's own keywords.
FORMAT_VALUES = {"date-time": "2026-01-01T00:00:00Z", "date": "2026-01-01", "time": "00:00:00Z",
                 "email": "someone@example.org", "uri": "https://example.org/", "uri-reference": "https://example.org/",
                 "iri": "https://example.org/", "url": "https://example.org/", "hostname": "example.org",
                 "ipv4": "192.0.2.1", "ipv6": "2001:db8::1", "uuid": "00000000-0000-4000-8000-000000000000"}
#: How deep an instance built from a schema's own keywords goes at most.
MAXIMUM_INSTANCE_DEPTH = 16
SOURCES_FILE = Path(__file__).with_name("json_schema_sources.json")
SOURCES_RECORD_TYPE = "library_supply_json_schema_sources/v1"
CURATED_STATE_SCOPE = "curated_schemas"


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


def is_sibling_reference(reference: str) -> bool:
    """A reference to another file of the same repository (a relative path), as opposed to another address."""
    return "://" not in reference and not reference.startswith(("urn:", "//"))


def wrong_type_value(schema: dict):
    """A value of another type than the schema's named top-level type that the validator refuses, or None."""
    kind = schema.get("type")
    wrong = WRONG_TYPE_VALUES.get(kind) if isinstance(kind, str) else None
    if wrong is not None and not schema_check.errors(wrong, schema):
        return None
    return wrong


def _merged(node: dict, part: dict) -> dict:
    """A schema with one more part joined in (allOf): properties and required lists added, other keys kept."""
    merged = {**part, **node}
    merged["properties"] = {**(part.get("properties") or {}), **(node.get("properties") or {})}
    merged["required"] = list(dict.fromkeys(list(node.get("required") or []) + list(part.get("required") or [])))
    return merged


def minimal_instance(node, root: dict, depth: int = 0):
    """The smallest value a schema's own keywords build: the constant, the first enumeration value, the required
    properties, the fewest items (with one that each contains asks for), a format's usual value and the first
    combination branch the validator accepts. Patterns are not followed; the caller checks the result."""
    if node is True or not isinstance(node, dict) or depth > MAXIMUM_INSTANCE_DEPTH:
        return {}
    if "$ref" in node:
        try:
            target = Resolver(root).target(node["$ref"]) if node["$ref"] != "#" else root
        except OperationRefused:
            return {}
        rest = {key: value for key, value in node.items() if key != "$ref"}
        return minimal_instance(_merged(rest, target) if isinstance(target, dict) else rest, root, depth + 1)
    if "const" in node:
        return node["const"]
    if isinstance(node.get("enum"), list) and node["enum"]:
        return node["enum"][0]
    if isinstance(node.get("allOf"), list):
        merged = {key: value for key, value in node.items() if key != "allOf"}
        for part in node["allOf"]:
            if isinstance(part, dict) and "$ref" in part:
                try:
                    part = Resolver(root).target(part["$ref"]) if part["$ref"] != "#" else root
                except OperationRefused:
                    continue
            if isinstance(part, dict):
                merged = _merged(merged, part)
        return minimal_instance(merged, root, depth + 1)
    for key in ("oneOf", "anyOf"):
        if isinstance(node.get(key), list) and node[key]:
            rest = {name: value for name, value in node.items() if name != key}
            first = None
            for branch in node[key]:
                candidate = minimal_instance(_merged(rest, branch) if isinstance(branch, dict) else rest, root,
                                             depth + 1)
                first = candidate if first is None else first
                try:
                    if not schema_check.errors(candidate, {**root, **node}):
                        return candidate
                except (LookupError, RecursionError, TypeError, ValueError):
                    continue
            return first
    kind = node.get("type")
    if isinstance(kind, list):
        kind = next((name for name in kind if name != "null"), "null")
    if kind is None:
        kind = "object" if "properties" in node or "required" in node else "array" if "items" in node else None
    if kind == "object":
        properties = node.get("properties") or {}
        names = list(node.get("required") or [])
        names += [name for name in properties if name not in names][:max(0, int(node.get("minProperties", 0)) - len(names))]
        return {name: minimal_instance(properties.get(name, {}), root, depth + 1) for name in names}
    if kind == "array":
        prefix = node.get("prefixItems") or (node["items"] if isinstance(node.get("items"), list) else [])
        items = node.get("items") if isinstance(node.get("items"), dict) else node.get("additionalItems", {})
        value = [minimal_instance(part, root, depth + 1) for part in prefix]
        if "contains" in node:
            contains = node["contains"]
            value.append(minimal_instance(_merged(contains, items) if isinstance(contains, dict) and
                                          isinstance(items, dict) else contains, root, depth + 1))
        while len(value) < int(node.get("minItems", 0)):
            value.append(minimal_instance(items, root, depth + 1))
        return value
    if kind == "string":
        text = FORMAT_VALUES.get(node.get("format"), "example")
        text = (text * (int(node.get("minLength", 0)) // len(text) + 1))[:max(len(text), int(node.get("minLength", 0)))]
        return text[:node["maxLength"]] if isinstance(node.get("maxLength"), int) else text
    if kind in ("integer", "number"):
        low = node.get("minimum", node.get("exclusiveMinimum") if not isinstance(node.get("exclusiveMinimum"), bool)
                       else None)
        value = 0 if low is None else math.ceil(low) + (1 if "exclusiveMinimum" in node and "minimum" not in node else 0)
        if node.get("exclusiveMinimum") is True:
            value += 1
        return value
    if kind == "boolean":
        return False
    if kind == "null":
        return None
    return {}


def read_sources(path: Path = SOURCES_FILE) -> list:
    """The curated sources, one row per repository: a row listing several repositories (one extension each)
    becomes one row per repository, its schema named after the repository."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    rows = []
    for row in record["sources"]:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", row["vendor"]) or not row.get("schemas"):
            raise ValueError(f"{row.get('source_id')}: a vendor is a lower-case word and a source names schemas")
        several = "repositories" in row
        for repository in row.get("repositories") or [row["repository"]]:
            schemas = []
            for entry in row["schemas"]:
                for kind in ("valid", "invalid"):
                    if f"{kind}_examples" in entry and f"{kind}_examples_glob" in entry:
                        raise ValueError(f"{row['source_id']}: {kind} examples are listed or matched, not both")
                name = entry.get("name") or (repository.split("/")[1] if several else Path(entry["path"]).stem)
                schemas.append({**entry, "name": name})
            rows.append({**{key: value for key, value in row.items() if key != "repositories"},
                         "repository": repository, "schemas": schemas})
    return rows


def example_paths(entry: dict, blobs: dict, kind: str) -> list:
    """The example files of one kind (valid or invalid) a schema entry declares: its listed paths, or the tree's
    files its pattern matches segment for segment; in path order, each within the size bound, at most the
    entry's maximum."""
    paths = entry.get(f"{kind}_examples") or []
    pattern = entry.get(f"{kind}_examples_glob")
    if pattern:
        paths = [path for path in blobs if fnmatch.fnmatchcase(path, pattern) and path.count("/") == pattern.count("/")]
    paths = sorted(path for path in paths if path not in blobs or blobs[path][1] <= MAXIMUM_EXAMPLE_BYTES)
    return paths[:min(int(entry.get("maximum_examples", MAXIMUM_EXAMPLES)), MAXIMUM_EXAMPLES)]


def _read_pinned(reader, repository: str, commit: str, blobs: dict, path: str, facts: dict):
    """One file of a repository at a commit, its bytes proven by the tree's git blob identity; a file the tree
    does not list (a truncated tree) is proven by the contents interface instead. Raises LookupError."""
    if path not in blobs:
        found = reader.pinned_file(repository, commit, path)
        answer = reader.get(found["url"])
    else:
        answer = reader.get(https_address(RAW_HOST, f"{repository}/{commit}/{path}"))
        if answer.status != 200 or git_blob_identity(answer.body) != blobs[path][0]:
            raise LookupError(path)
    facts[answer.sha256] = answer.body
    return answer


def safe_name(name: str) -> str:
    """A file name of letters, digits and ._-, as a package path allows (the original path stays in provenance)."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")[:100] or "example.json"


def module_name(name: str) -> str:
    return ("schemastore_" + _SEGMENT.sub("_", name.lower()).strip("_"))[:80]


def test_text(schema_file: str, valid: list, invalid: list, wrong, origin: str = "SchemaStore") -> str:
    lines = [f'"""The schema\'s own examples from {origin}: every valid one passes, every invalid one fails."""',
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
    notice = repository_notice(reader, SCHEMA_REPOSITORY, commit, licence.spdx)
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
        if path not in blobs:
            raise LookupError(path)
        return _read_pinned(reader, SCHEMA_REPOSITORY, commit, blobs, path, facts)

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
        wrong = wrong_type_value(schema)
        try:
            built.append(_package(name, schema_path, schema_answer, valid, caught, wrong, commit, licence, generator,
                                  licence_text, generated_on, staging, notice))
            summary["packaged"] += 1
        except SupplyRecordError as error:
            reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                GENERATED_TEST_FAILED
            refused.append(refusal(JSON_SCHEMAS, reason, name, str(error)[:200]))
    return built, refused, facts, summary


def generate_curated(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str,
                     staging: Path) -> tuple:
    """(built, refusals, facts, summary) of every declared schema of the curated sources (json_schema_sources.json)."""
    from . import api_schemas
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/json_schemas.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    seen = set()
    for source in sources:
        repository = source["repository"]
        label = f"{source['source_id']} {repository}"
        head = reader.github(f"repos/{repository}/commits/{source['branch']}")
        if head.status != 200:
            refused.append(refusal(JSON_SCHEMAS, "source_unreadable", label, f"no head commit of {source['branch']}"))
            continue
        commit = json.loads(head.body)["sha"]
        licence = repository_licence(reader, repository, commit)
        if not licence.allowed:
            refused.append(refusal(JSON_SCHEMAS, licence.refusal_reason(REFUSAL_REASONS[JSON_SCHEMAS]), label,
                                   licence.github_spdx or ""))
            continue
        notice = repository_notice(reader, repository, commit, licence.spdx)
        tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
        if tree.status != 200:
            refused.append(refusal(JSON_SCHEMAS, "source_unreadable", label, f"no tree at {commit[:12]}"))
            continue
        blobs = {entry["path"]: (entry["sha"], entry.get("size", 0)) for entry in json.loads(tree.body).get("tree", [])
                 if entry.get("type") == "blob"}
        row = {"source_id": source["source_id"], "repository": repository, "commit": commit, "licence": licence.spdx,
               "schemas": len(source["schemas"]), "packaged": 0, "with_examples": 0, "valid_examples_rejected": 0,
               "invalid_examples_not_caught": 0}
        for entry in source["schemas"]:
            name, schema_path = entry["name"], entry["path"]
            module = (f"{source['vendor']}_" + _SEGMENT.sub("_", name.lower()).strip("_"))[:70]
            subject = f"{repository}:{schema_path}"
            if module in seen:
                refused.append(refusal(JSON_SCHEMAS, "duplicate_schema", subject, module))
                continue
            try:
                schema_answer = _read_pinned(reader, repository, commit, blobs, schema_path, facts)
                schema = json.loads(schema_answer.body)
                valid = [(path, _read_pinned(reader, repository, commit, blobs, path, facts))
                         for path in example_paths(entry, blobs, "valid")]
                invalid = [(path, _read_pinned(reader, repository, commit, blobs, path, facts))
                           for path in example_paths(entry, blobs, "invalid")]
                parsed = {path: json.loads(answer.body) for path, answer in valid + invalid}
            except (LookupError, ValueError) as error:
                refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", subject, str(error)[:120]))
                continue
            if not isinstance(schema, dict):
                refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", subject, "not a JSON object"))
                continue
            outside = outside_references(schema)
            if outside:
                # Bundling a sibling file is not done here: the schema is refused by the reason that would name it.
                sibling = next((reference for reference in outside if is_sibling_reference(reference)), None)
                reason = "needs_a_sibling_schema" if sibling is not None else "needs_an_outside_reference"
                refused.append(refusal(JSON_SCHEMAS, reason, subject, (sibling or outside[0])[:120]))
                continue
            generated = None
            try:
                # The repository's own examples where it has them: a valid one the validator rejects is left out
                # and counted, an invalid one it accepts likewise; a schema whose every valid example is rejected
                # disagrees with its own data and is refused.
                accepted = [(path, answer) for path, answer in valid if not schema_check.errors(parsed[path], schema)]
                caught = [(path, answer) for path, answer in invalid if schema_check.errors(parsed[path], schema)]
                if not valid:
                    try:
                        raw = Resolver(schema).schema(schema)
                    except (OperationRefused, RecursionError):
                        raw = {}
                    generated = api_schemas.instances(raw, schema)
                    if not generated:
                        # The specification synthesizer knows no constants or contained items: an instance built
                        # from the schema's own keywords is kept when the validator accepts it.
                        built_instance = minimal_instance(schema, schema)
                        if not schema_check.errors(built_instance, schema):
                            generated = [built_instance]
                wrong = wrong_type_value(schema)
            except (LookupError, RecursionError, TypeError, ValueError) as error:
                refused.append(refusal(JSON_SCHEMAS, "schema_unreadable", subject,
                                       f"{type(error).__name__}: {error}"[:120]))
                continue
            if valid and not accepted:
                refused.append(refusal(JSON_SCHEMAS, "valid_example_rejected", subject, valid[0][0]))
                continue
            if generated is not None and not generated:
                refused.append(refusal(JSON_SCHEMAS, "valid_example_rejected", subject, "no instance the validator "
                                       "accepts"))
                continue
            if generated is not None:
                wrong = api_schemas.wrong_values(schema, generated)
            row["valid_examples_rejected"] += len(valid) - len(accepted)
            row["invalid_examples_not_caught"] += len(invalid) - len(caught)
            try:
                built.append(_package(name, schema_path, schema_answer, accepted, caught, wrong, commit, licence,
                                      generator, licence_text, generated_on, staging, notice, source=source,
                                      module=module, generated=generated))
                seen.add(module)
                row["packaged"] += 1
                row["with_examples"] += generated is None
            except SupplyRecordError as error:
                reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                    GENERATED_TEST_FAILED
                refused.append(refusal(JSON_SCHEMAS, reason, subject, str(error)[:200]))
        summary.append(row)
    return built, refused, facts, summary


def _unique(names) -> list:
    """File names made unique by a counter, when two examples sanitize to one name."""
    seen, unique = {}, []
    for name in names:
        count = seen.get(name, 0)
        seen[name] = count + 1
        unique.append(name if not count else f"{Path(name).stem}_{count}{Path(name).suffix}")
    return unique


def _package(name, schema_path, schema_answer, valid, invalid, wrong, commit, licence, generator, licence_text,
             generated_on, staging, notice=None, *, source=None, module=None, generated=None):
    """One schema package: SchemaStore's by default; a curated source's when source is given, tested by generated
    instances and known-wrong values (a list) when generated is given."""
    from . import api_schemas
    repository = source["repository"] if source else SCHEMA_REPOSITORY
    module = module or module_name(name)
    schema_file = f"{module}.schema.json" if source else f"{name}.schema.json"
    valid_files = [f"examples/valid/{name}" for name in _unique(safe_name(Path(path).name) for path, _answer in valid)]
    invalid_files = [f"examples/invalid/{name}" for name in _unique(safe_name(Path(path).name)
                                                                     for path, _answer in invalid)]
    if generated is not None:
        tests = api_schemas.test_text(schema_file, generated, wrong)
    else:
        tests = test_text(schema_file, valid_files, invalid_files, wrong, repository if source else "SchemaStore")
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
    if source:
        opening = (f"`{schema_file}` is the JSON Schema `{schema_path}` of {repository}, copied byte for byte at "
                   f"commit `{commit}`, licensed {licence.spdx}.")
    else:
        opening = (f"`{schema_file}` is SchemaStore's JSON Schema for {name}, copied byte for byte from "
                   f"{SCHEMA_REPOSITORY} at commit `{commit}` ({schema_path}), licensed {licence.spdx}.")
    if generated is not None:
        testing = (f"`test_{module}.py`: the repository has no examples of this schema, so {len(generated)} "
                   f"instance{'s' if len(generated) != 1 else ''} (the schema's own example or generated) must pass "
                   f"and {len(wrong)} known-wrong value{'s' if len(wrong) != 1 else ''} must fail ({count} tests).\n")
    else:
        testing = (f"`test_{module}.py` runs {'the repository' if source else 'SchemaStore'}'s own examples: "
                   f"{len(valid)} valid example{'s' if len(valid) != 1 else ''} must pass and {len(invalid)} invalid "
                   f"example{'s' if len(invalid) != 1 else ''} must fail ({count} tests).\n")
    readme = (f"# {name}\n\n{title}\n\n{opening}\n\n"
              f"`{VALIDATOR_NAME}` checks a document against it: `python {VALIDATOR_NAME} {schema_file} document.json` "
              "prints each problem and exits 1 when there is one. It follows the file's own references and does not "
              f"check formats.\n\n{testing}")
    upstream_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(schema_file, schema_answer.body, "other", UPSTREAM_VERBATIM,
                         {"url": github_blob_address(repository, commit, schema_path),
                          "sha256": schema_answer.sha256}),
             PackageFile(VALIDATOR_NAME, VALIDATOR_TEXT, "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode("utf-8"), "executable_tool"),
             PackageFile("README.md", readme.encode("utf-8"), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": upstream_address, "sha256": licence.sha256})]
    for target, (path, answer) in zip(valid_files + invalid_files, valid + invalid):
        files.append(PackageFile(target, answer.body, "other", UPSTREAM_VERBATIM,
                                 {"url": github_blob_address(repository, commit, path), "sha256": answer.sha256}))
    facts = [fact_source(https_address(RAW_HOST, f"{repository}/{commit}/{schema_path}"),
                         schema_answer.retrieved_at, schema_answer.sha256, len(schema_answer.body), "data_source",
                         spdx=licence.spdx, basis="github_licence_interface_and_text_agree",
                         evidence_sha256=licence.sha256),
             fact_source(upstream_address, schema_answer.retrieved_at, licence.sha256, len(licence.text),
                         "licence_text", spdx=licence.spdx, basis="licence_file_at_the_pinned_commit")]
    notices, notice_facts = notice_files([notice])
    files += notices
    facts += notice_facts
    identity = f"{repository}:{schema_path}"
    if source:
        package_name = f"{module.replace('_', '-')}-schema"[:90]
        tested_by = "generated instances and known-wrong values" if generated is not None else \
            "the repository's own examples"
        description = f"JSON Schema {name} of {repository}: {title[:160]} With a validator and {tested_by} as tests."
        counts = {"valid_instances": len(generated), "known_wrong": len(wrong)} if generated is not None else \
            {"valid_examples": len(valid), "invalid_examples": len(invalid)}
        upstream = {"name": repository, "schema": schema_path, "source_id": source["source_id"]}
    else:
        package_name = f"schemastore-{module[len('schemastore_'):].replace('_', '-')}"[:90]
        description = f"JSON Schema for {name}: {title[:180]} With a validator and SchemaStore's own examples as tests."
        counts = {"valid_examples": len(valid), "invalid_examples": len(invalid)}
        upstream = {"name": SCHEMA_REPOSITORY, "schema": schema_path, "family": family_of(name)[0]}
    supply = SupplyPackage(
        line=JSON_SCHEMAS, identity=identity, key=upstream_key(JSON_SCHEMAS, identity), kind="contract_schema",
        native_format=NATIVE_FORMAT, form="schema", name=package_name, description=description,
        files=files, licence_expression=" AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx])),
        provenance=provenance("github_repository", repository, schema_path, commit, facts, generator),
        placements=[{"harness": "reference", "path": f"schemas/{module if source else name}/",
                     "basis": "documented_layout", "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "reads_the_schema_and_the_document_it_is_given")], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False, **counts},
        repository=upstream, generated_on=generated_on, comparison_text=identity)
    return build(supply)


__all__ = ["CURATED_STATE_SCOPE", "SCHEMA_REPOSITORY", "choose", "example_paths", "family_of", "generate",
           "generate_curated", "outside_references", "read_sources", "test_text"]

"""Line openapi_operations, discovery mode: every Google API whose discovery document Google publishes in its
Apache-2.0 client repository, one tested Python client per method.

```text
googleapis/google-api-python-client at its head commit (Apache-2.0: GitHub's licence interface and text agree)
├── googleapiclient/discovery_cache/documents/<name>.<version>.json, each read by its git blob identity
├── one version per API: the highest stable version (v1, v2, ...), else the highest beta, else the highest alpha
├── converted to the OpenAPI 3 shape the generator reads
│   ├── server: rootUrl and servicePath; each method's path, {+name} kept as reserved expansion
│   ├── parameters: the method's path and query parameters, a repeated one as a list; the document's
│   │   global parameters (alt, fields, key, prettyPrint, ...) left out
│   ├── request and response bodies: JSON, their schemas as components
│   └── credential: an OAuth 2.0 access token in GOOGLE_ACCESS_TOKEN, sent as a bearer token, for every
│       method that names scopes; a method without scopes sends none
└── every method: the API operation line's generator (client, schema, README, tests run offline), one
    package per host, method and path in the run, in its own line state (scope google_discovery)
```

A discovery document declares no licence of its own. The documents are files
of Google's own client repository, so that repository's licence, decided from
GitHub's licence interface and the licence text at the pinned commit, is the
licence of each document, and its text travels with every package.
"""
from __future__ import annotations

import json
import re
from collections import Counter

from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from .licences import repository_licence
from .openapi_directory import DUPLICATE_OPERATION, operation_key
from .openapi_operations import operations, package_operations
from .reading import RAW_HOST, https_address, repository_notice
from .records import OPENAPI_OPERATIONS, SupplyRecordError, refusal

DISCOVERY_REPOSITORY = "googleapis/google-api-python-client"
DISCOVERY_BRANCH = "main"
DISCOVERY_FOLDER = "googleapiclient/discovery_cache/documents"
HOSTS = (RAW_HOST,)
#: The credential every Google client reads: an OAuth 2.0 access token (for example from gcloud auth
#: print-access-token), sent as a bearer token.
CREDENTIAL_VARIABLE = "GOOGLE_ACCESS_TOKEN"
CREDENTIAL_PREFIX = "GOOGLE"
#: The line state of this mode, so the curated and directory modes never withdraw its packages.
STATE_SCOPE = "google_discovery"
OAUTH_SCHEME = "oauth2"
_FILE = re.compile(r"([A-Za-z0-9]+)\.([A-Za-z0-9_.]+)\.json\Z")
_VERSION = re.compile(r"(?:(?P<family>[A-Za-z0-9_]+)_)?v(?P<major>\d+)(?:\.(?P<minor>\d+))?"
                      r"(?P<stage>(?:p\d+)?(?:alpha|beta)\d*)?\Z")
_SEGMENT = re.compile(r"[^a-z0-9]+")
_STAGE_NUMBER = re.compile(r"(\d+)\Z")
#: How a discovery version's stage ranks: a stable version before a beta before an alpha.
STABLE, BETA, ALPHA = 2, 1, 0


def version_rank(version: str) -> "tuple | None":
    """(family, (stability, major, minor, stage number)) of a discovery version, or None when it is not one."""
    match = _VERSION.match(version)
    if match is None:
        return None
    stage = match.group("stage") or ""
    stability = ALPHA if "alpha" in stage else BETA if "beta" in stage else STABLE
    number = _STAGE_NUMBER.search(stage)
    return match.group("family") or "", (stability, int(match.group("major")), int(match.group("minor") or 0),
                                         int(number.group(1)) if number else 0)


def choose_documents(paths) -> list:
    """The one document per API (name and version family) a run reads: the highest stable version, else the
    highest beta, else the highest alpha. A file whose version is not a discovery version is left out."""
    best = {}
    for path in sorted(paths):
        match = _FILE.search(path.rsplit("/", 1)[-1])
        if match is None:
            continue
        name, version = match.group(1), match.group(2)
        ranked = version_rank(version)
        if ranked is None:
            continue
        family, rank = ranked
        key = (name, family)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, path, name, version)
    return [(path, name, version) for _rank, path, name, version in sorted(best.values(), key=lambda row: row[1])]


def vendor_of(name: str, version: str) -> str:
    """google_<name>_<version>, lower case, for module and package names."""
    vendor = _SEGMENT.sub("_", f"google_{name}_{version}".lower()).strip("_")
    return vendor[:40].rstrip("_")


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def convert_schema(node) -> dict:
    """A discovery schema as a JSON schema: a named reference becomes a component reference, "any" any value."""
    if not isinstance(node, dict):
        return {}
    if isinstance(node.get("$ref"), str):
        return {"$ref": "#/components/schemas/" + node["$ref"]}
    out = {}
    if isinstance(node.get("type"), str) and node["type"] != "any":
        out["type"] = node["type"]
    for key in ("format", "enum", "description", "readOnly", "pattern"):
        if key in node:
            out[key] = node[key]
    for key in ("minimum", "maximum"):
        number = _number(node.get(key))
        if number is not None:
            out[key] = number
    if isinstance(node.get("properties"), dict):
        out["properties"] = {name: convert_schema(value) for name, value in node["properties"].items()}
    if isinstance(node.get("items"), dict):
        out["items"] = convert_schema(node["items"])
    if isinstance(node.get("additionalProperties"), dict):
        out["additionalProperties"] = convert_schema(node["additionalProperties"])
    return out


def _methods(container, found: list) -> list:
    """Every method of a discovery resource tree, depth first, in name order."""
    for _name, method in sorted((container.get("methods") or {}).items()):
        if isinstance(method, dict):
            found.append(method)
    for _name, resource in sorted((container.get("resources") or {}).items()):
        if isinstance(resource, dict):
            _methods(resource, found)
    return found


def discovery_to_openapi3(document: dict) -> dict:
    """The OpenAPI 3 shape of a discovery document, as far as the generator reads it."""
    root = str(document.get("rootUrl") or "") + str(document.get("servicePath") or "")
    name = str(document.get("name") or "")
    paths = {}
    for method in _methods(document, []):
        path, verb = method.get("path"), str(method.get("httpMethod") or "").lower()
        if not isinstance(path, str) or not verb:
            continue
        identity = str(method.get("id") or "")
        operation_id = identity[len(name) + 1:] if name and identity.startswith(name + ".") else identity
        parameters = []
        for parameter_name, parameter in sorted((method.get("parameters") or {}).items()):
            if not isinstance(parameter, dict) or parameter.get("location") not in ("path", "query"):
                continue
            schema = convert_schema({key: value for key, value in parameter.items() if key != "repeated"})
            if parameter.get("repeated"):
                schema = {"type": "array", "items": schema}
            parameters.append({"name": parameter_name, "in": parameter["location"],
                               "required": bool(parameter.get("required")) or parameter["location"] == "path",
                               "description": str(parameter.get("description") or ""), "schema": schema})
        operation = {"operationId": operation_id, "description": str(method.get("description") or ""),
                     "parameters": parameters,
                     "security": [{OAUTH_SCHEME: []}] if method.get("scopes") else []}
        if isinstance(method.get("request"), dict):
            operation["requestBody"] = {"required": True, "content": {"application/json": {
                "schema": convert_schema(method["request"])}}}
        answer = {"description": "Successful response"}
        if isinstance(method.get("response"), dict):
            answer["content"] = {"application/json": {"schema": convert_schema(method["response"])}}
        operation["responses"] = {"200": answer}
        if method.get("deprecated"):
            operation["deprecated"] = True
        paths.setdefault("/" + path.lstrip("/"), {})[verb] = operation
    schemas = {schema_name: convert_schema(schema) for schema_name, schema in (document.get("schemas") or {}).items()}
    return {"openapi": "3.0.0",
            "info": {"title": str(document.get("title") or name), "version": str(document.get("version") or "")},
            "servers": [{"url": root.rstrip("/")}], "paths": paths,
            "components": {"schemas": schemas, "securitySchemes": {OAUTH_SCHEME: {"type": OAUTH_SCHEME, "flows": {}}}}}


def generate(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging, only=None,
             maximum_apis: "int | None" = None, maximum_operations: int = 3000, javascript: bool = True) -> tuple:
    """(built, refusals, facts, summary) of every chosen discovery document, or of the named APIs."""
    head = reader.github(f"repos/{DISCOVERY_REPOSITORY}/commits/{DISCOVERY_BRANCH}")
    if head.status != 200:
        raise SupplyRecordError("specification_unreadable", f"{DISCOVERY_REPOSITORY}: no head commit")
    commit = json.loads(head.body)["sha"]
    licence = repository_licence(reader, DISCOVERY_REPOSITORY, commit)
    if not licence.allowed:
        raise SupplyRecordError("licence_not_on_allowlist", f"{DISCOVERY_REPOSITORY}: {licence.reason}")
    tree = reader.github(f"repos/{DISCOVERY_REPOSITORY}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise SupplyRecordError("specification_unreadable", f"{DISCOVERY_REPOSITORY}: no tree at {commit[:12]}")
    blobs = {entry["path"]: entry["sha"] for entry in json.loads(tree.body).get("tree", [])
             if entry.get("type") == "blob" and entry["path"].startswith(DISCOVERY_FOLDER + "/")}
    notice = repository_notice(reader, DISCOVERY_REPOSITORY, commit, licence.spdx)
    chosen = choose_documents(blobs)
    if only:
        chosen = [row for row in chosen if row[1] in set(only)]
    if maximum_apis:
        chosen = chosen[:maximum_apis]
    generator = {"identity": "tools/supply_lines/google_discovery.py", "version": "1.1.0", "code_revision": code_revision}
    built, refused, facts, summary, supplied = [], [], {}, Counter(), {}
    summary["documents_listed"], summary["documents_chosen"] = len(blobs), len(chosen)
    for path, name, version in chosen:
        raw = reader.get(https_address(RAW_HOST, f"{DISCOVERY_REPOSITORY}/{commit}/{path}"))
        if raw.status != 200 or git_blob_identity(raw.body) != blobs[path]:
            refused.append(refusal(OPENAPI_OPERATIONS, "specification_unreadable", path, "bytes differ from the blob"))
            continue
        try:
            document = json.loads(raw.body)
        except ValueError:
            refused.append(refusal(OPENAPI_OPERATIONS, "specification_unreadable", path, "not JSON"))
            continue
        facts[raw.sha256] = raw.body
        vendor = vendor_of(name, version)
        converted = discovery_to_openapi3(document)
        source = {"source_id": f"google:{name}:{version}", "vendor": vendor, "credential_variable": CREDENTIAL_VARIABLE,
                  "credential_prefix": CREDENTIAL_PREFIX, "maximum_operations": maximum_operations}
        spec = {"document": converted, "origin": "github_repository", "repository": DISCOVERY_REPOSITORY,
                "commit": commit, "path": path, "sha256": raw.sha256, "size_bytes": len(raw.body),
                "retrieved_at": raw.retrieved_at, "licence": licence.spdx,
                "title": re.sub(r"\s+", " ", str(document.get("title") or name))[:80], "version": version[:40],
                "base_url_variable": f"{vendor.upper()}_BASE_URL", "notices": [notice]}
        found, refusals = operations(converted, source)
        refused += refusals
        summary["apis"] += 1
        summary["operations"] += len(found)
        jobs = []
        for operation in found[:maximum_operations]:
            key = operation_key(operation)
            if key in supplied:
                refused.append(refusal(OPENAPI_OPERATIONS, DUPLICATE_OPERATION,
                                       f"{name}:{version} {operation.method} {operation.path}",
                                       f"supplied from {supplied[key]}"))
                continue
            supplied[key] = f"{name}:{version}"
            jobs.append((operation, spec, source, licence, generator, licence_text, generated_on, {},
                         f"{name}:{version} {operation.method} {operation.path}"))
        packaged = package_operations(jobs, staging, refused, summary, javascript=javascript)
        built += packaged
        summary["packaged"] += len(packaged)
    return built, refused, facts, dict(summary)


__all__ = ["CREDENTIAL_VARIABLE", "DISCOVERY_REPOSITORY", "STATE_SCOPE", "choose_documents", "convert_schema",
           "discovery_to_openapi3", "generate", "vendor_of", "version_rank"]

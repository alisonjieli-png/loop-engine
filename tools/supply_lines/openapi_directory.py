"""Line openapi_operations, directory mode: every API of the APIs.guru OpenAPI directory whose licence allows copying.

```text
APIs.guru OpenAPI directory (api.apis.guru/v2/list.json, the directory itself under CC0-1.0)
├── one preferred version per API, its specification served as JSON (OpenAPI 3, or Swagger 2 converted here)
├── licence, decided per API and recorded (licences.jsonl in the run folder)
│   ├── the specification declares info.license: its name must be one of the names mapped below to an
│   │   allowlisted SPDX identifier (and its address, when given, must be that licence's); any other
│   │   declared licence is refused, even when the repository it came from is permissive
│   ├── it declares none and its x-origin is a GitHub repository: that repository's licence at its
│   │   head commit, where GitHub's licence interface and the text agree on an allowlisted licence
│   └── otherwise the licence is unknown and the API is refused
├── licence text: the origin repository's own file, or the licence's text from
│   github/choosealicense.com at the commit the licence matcher already pins (its SHA-256 checked)
└── every operation: the API operation line's generator (client, schema, README, tests run offline)
```

A Swagger 2 specification is converted to the OpenAPI 3 shape the generator
reads: host, base path and schemes become servers, body parameters a JSON
request body, form parameters a form body (refused as not JSON), response
schemas JSON content, and security definitions security schemes. References
stay local pointers into the same document.
"""
from __future__ import annotations

import json
import re
from collections import Counter

from loop_engine.core.library_ingestion.licences import TEMPLATES_FILE

from .licences import (
    AGREED, KNOWN_LICENCE_REFUSALS, LICENCE_NOT_ON_ALLOWLIST, LICENCE_UNKNOWN, RepositoryLicence, repository_licence)
from .openapi_operations import (
    METHODS, OperationRefused, _package, operations, plain)
from .reading import https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_TEST_FAILED, OPENAPI_OPERATIONS, PACKAGE_ABOVE_REVIEW_BOUND, SupplyRecordError,
    fact_source, licence_allowed, refusal)

DIRECTORY_HOST = "api.apis.guru"
DIRECTORY_LIST = "v2/list.json"
DIRECTORY_REPOSITORY = "APIs-guru/openapi-directory"
DIRECTORY_LICENCE = "CC0-1.0"
LICENCE_TEXT_REPOSITORY = "github/choosealicense.com"
HOSTS = (DIRECTORY_HOST, "raw.githubusercontent.com")
#: The licence names the directory's specifications declare, mapped to SPDX identifiers. Only exact names are
#: mapped; a name not listed here is refused, never guessed from its words.
DECLARED_LICENCE_NAMES = {
    "MIT": "MIT", "MIT License": "MIT", "The MIT License (MIT)": "MIT", "Distributed under the MIT license": "MIT",
    "Apache 2.0": "Apache-2.0", "Apache 2.0 License": "Apache-2.0", "Apache-2.0": "Apache-2.0",
    "Apache v2 License": "Apache-2.0", "Apache License 2.0": "Apache-2.0", "Apache License, Version 2.0": "Apache-2.0",
    "BSD-3-Clause": "BSD-3-Clause", "BSD-2-Clause": "BSD-2-Clause", "ISC": "ISC", "CC0 1.0": "CC0-1.0",
    "CC0-1.0": "CC0-1.0", "Unlicense": "Unlicense", "CC-BY-4.0": "CC-BY-4.0"}
#: The address fragments that confirm a declared licence; a declared address naming another licence is refused.
LICENCE_ADDRESS_WORDS = {"MIT": ("mit",), "Apache-2.0": ("apache.org/licenses/license-2.0", "apache-2.0", "apache2"),
                         "BSD-3-Clause": ("bsd-3",), "BSD-2-Clause": ("bsd-2",), "ISC": ("isc",),
                         "CC0-1.0": ("cc0", "publicdomain/zero"), "Unlicense": ("unlicense",),
                         "CC-BY-4.0": ("by/4.0", "cc-by-4.0")}
_ORIGIN = re.compile(r"https://(?:raw\.githubusercontent\.com|github\.com)/([A-Za-z0-9][A-Za-z0-9-]{0,38})/"
                     r"([A-Za-z0-9._-]{1,100})/")
_SEGMENT = re.compile(r"[^a-z0-9]+")
BODY_IN, FORM_IN = "body", "formData"
JSON_MEDIA = "application/json"
FORM_MEDIA = "application/x-www-form-urlencoded"
DIRECTORY_BASIS = "specification_info_license_declaration"
ORIGIN_BASIS = "origin_repository_licence_interface_and_text_agree"
#: AWS specifications of the directory are converted from the AWS SDK for JavaScript's models; the model's
#: metadata (protocol, JSON version, signing name, API version) is read from that repository at a pinned commit.
AWS_PROVIDER = "amazonaws.com"
AWS_SDK_REPOSITORY = "aws/aws-sdk-js"
AWS_SDK_BRANCH = "master"
_AWS_MODEL = re.compile(r"https://raw\.githubusercontent\.com/aws/aws-sdk-js/[^/]+/(apis/[A-Za-z0-9._-]+)\.normal\.json\Z")


# -- licences ------------------------------------------------------------------------------------------------------
def declared_licence(info: dict) -> "tuple | None":
    """(SPDX identifier or None, declared name, declared address) of a specification's info.license, or None."""
    licence = info.get("license") if isinstance(info, dict) else None
    if not isinstance(licence, dict) or not str(licence.get("name") or "").strip():
        return None
    name, address = str(licence["name"]).strip(), str(licence.get("url") or "").strip()
    spdx = DECLARED_LICENCE_NAMES.get(name)
    if spdx and address and not any(word in address.lower() for word in LICENCE_ADDRESS_WORDS[spdx]):
        spdx = None  # the address names another licence than the name does
    return spdx, name, address


def origin_repository(info: dict) -> "str | None":
    origins = info.get("x-origin") if isinstance(info, dict) else None
    for origin in reversed(origins if isinstance(origins, list) else []):
        match = _ORIGIN.match(str((origin or {}).get("url") or "")) if isinstance(origin, dict) else None
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def licence_text_paths() -> tuple:
    """(SPDX identifier to (path, SHA-256) of its text, commit) in github/choosealicense.com, as the licence matcher
    of library ingestion pins them (licence_templates.json)."""
    record = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return {row["spdx"]: (row["path"], row["sha256"]) for row in record["templates"]}, record["source"]["commit"]


class LicenceTexts:
    """Licence texts from github/choosealicense.com at the commit the licence matcher pins, each checked by SHA-256."""

    def __init__(self, reader) -> None:
        self.reader = reader
        self.paths, self.commit = licence_text_paths()
        self.found = {}

    def text(self, spdx: str) -> RepositoryLicence:
        if spdx not in self.found:
            path, digest = self.paths[spdx]
            pinned = self.reader.pinned_file(LICENCE_TEXT_REPOSITORY, self.commit, path)
            if pinned["sha256"] != digest:
                raise SupplyRecordError("licence_text_changed", f"{path} is not the pinned text")
            self.found[spdx] = RepositoryLicence(LICENCE_TEXT_REPOSITORY, pinned["commit"], spdx, AGREED, path,
                                                 pinned["bytes"], spdx, spdx, 1.0)
        return self.found[spdx]


def decide(name: str, info: dict, reader, texts: LicenceTexts, origins: dict) -> dict:
    """The recorded licence decision of one API: spdx, basis, the text to carry, or the refusal reason."""
    declared = declared_licence(info)
    origin = origin_repository(info)
    row = {"api": name, "declared_name": declared[1] if declared else None,
           "declared_address": declared[2] if declared else None, "origin_repository": origin}
    if declared is not None:
        spdx = declared[0]
        if spdx is None or not licence_allowed(spdx):
            return {**row, "decision": LICENCE_NOT_ON_ALLOWLIST, "spdx": None}
        return {**row, "decision": AGREED, "spdx": spdx, "basis": DIRECTORY_BASIS, "licence": texts.text(spdx)}
    if origin is None:
        return {**row, "decision": LICENCE_UNKNOWN, "spdx": None}
    if origin not in origins:
        facts = reader.repository_facts([origin]).get(origin.lower()) or {}
        commit = (((facts.get("defaultBranchRef") or {}).get("target")) or {}).get("oid")
        origins[origin] = repository_licence(reader, origin, commit) if commit else None
    licence = origins[origin]
    if licence is None or not licence.allowed:
        reason = licence.reason if licence is not None else LICENCE_UNKNOWN
        return {**row, "decision": reason, "spdx": licence.github_spdx if licence else None}
    return {**row, "decision": AGREED, "spdx": licence.spdx, "basis": ORIGIN_BASIS, "licence": licence}


# -- Swagger 2 ------------------------------------------------------------------------------------------------------
def _local(document: dict, node):
    """A Swagger 2 parameter or response with its local reference followed (one level of #/... pointers)."""
    seen = 0
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/") and seen < 10:
        target = document
        for part in node["$ref"][2:].split("/"):
            target = target.get(part.replace("~1", "/").replace("~0", "~")) if isinstance(target, dict) else None
        if not isinstance(target, dict):
            return node
        node, seen = target, seen + 1
    return node


def _parameter_schema(parameter: dict) -> dict:
    keys = ("type", "format", "enum", "items", "default", "minimum", "maximum", "pattern", "minLength", "maxLength",
            "collectionFormat")
    return {key: parameter[key] for key in keys if key in parameter}


def swagger2_to_openapi3(document: dict) -> dict:
    """The OpenAPI 3 shape of a Swagger 2 document, as far as the generator reads it."""
    host = document.get("host")
    base = str(document.get("basePath") or "")
    schemes = [scheme for scheme in document.get("schemes") or ["https"] if isinstance(scheme, str)]
    servers = [{"url": f"{scheme}://{host}{base}"} for scheme in schemes if host]
    produces_top = document.get("produces") or [JSON_MEDIA]
    consumes_top = document.get("consumes") or [JSON_MEDIA]
    schemes_out = {}
    for name, definition in (document.get("securityDefinitions") or {}).items():
        if not isinstance(definition, dict):
            continue
        if definition.get("type") == "basic":
            schemes_out[name] = {"type": "http", "scheme": "basic"}
        else:
            schemes_out[name] = dict(definition)
    paths = {}
    for path, item in (document.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        shared = [_local(document, row) for row in item.get("parameters") or ()]
        new_item = {}
        for method in METHODS:
            node = item.get(method)
            if not isinstance(node, dict):
                continue
            by_key = {(row.get("name"), row.get("in")): row for row in shared if isinstance(row, dict)}
            for row in node.get("parameters") or ():
                row = _local(document, row)
                if isinstance(row, dict):
                    by_key[(row.get("name"), row.get("in"))] = row
            parameters, body, form = [], None, []
            for (name, location), row in by_key.items():
                if location == BODY_IN:
                    body = row
                elif location == FORM_IN:
                    form.append(row)
                else:
                    parameters.append({"name": name, "in": location, "required": bool(row.get("required")),
                                       "description": row.get("description", ""), "schema": _parameter_schema(row)})
            operation = {key: node[key] for key in ("operationId", "summary", "description", "deprecated", "security",
                                                    "tags") if key in node}
            operation["parameters"] = parameters
            consumes = node.get("consumes") or consumes_top
            if body is not None:
                media = next((value for value in consumes if "json" in str(value).lower()), consumes[0])
                operation["requestBody"] = {"required": bool(body.get("required")),
                                            "content": {media: {"schema": body.get("schema") or {}}}}
            elif form:
                operation["requestBody"] = {"required": any(row.get("required") for row in form),
                                            "content": {FORM_MEDIA: {"schema": {"type": "object"}}}}
            produces = node.get("produces") or produces_top
            media = next((value for value in produces if "json" in str(value).lower()), produces[0] if produces else
                         JSON_MEDIA)
            responses = {}
            for code, response in (node.get("responses") or {}).items():
                response = _local(document, response)
                if not isinstance(response, dict):
                    continue
                converted = {"description": response.get("description", "")}
                if "schema" in response:
                    content = {"schema": response["schema"]}
                    examples = response.get("examples")
                    if isinstance(examples, dict) and media in examples:
                        content["example"] = examples[media]
                    converted["content"] = {media: content}
                responses[str(code)] = converted
            operation["responses"] = responses
            new_item[method] = operation
        paths[path] = new_item
    converted = {"openapi": "3.0.0", "info": document.get("info") or {}, "servers": servers, "paths": paths,
                 "components": {"securitySchemes": schemes_out}, "definitions": document.get("definitions") or {}}
    if "security" in document:
        converted["security"] = document["security"]
    return converted


# -- the line -------------------------------------------------------------------------------------------------------
def aws_metadata(reader, info: dict, cache: dict) -> "tuple | None":
    """(the AWS SDK model's metadata for signing, its pinned file, the SDK licence) of an AWS specification."""
    origins = info.get("x-origin") if isinstance(info, dict) else None
    model = None
    for origin in origins if isinstance(origins, list) else []:
        match = _AWS_MODEL.match(str((origin or {}).get("url") or "")) if isinstance(origin, dict) else None
        if match:
            model = match.group(1) + ".min.json"
    if model is None:
        return None
    if "licence" not in cache:
        facts = reader.repository_facts([AWS_SDK_REPOSITORY]).get(AWS_SDK_REPOSITORY.lower()) or {}
        commit = (((facts.get("defaultBranchRef") or {}).get("target")) or {}).get("oid")
        cache["commit"] = commit
        cache["licence"] = repository_licence(reader, AWS_SDK_REPOSITORY, commit) if commit else None
    licence = cache["licence"]
    if licence is None or not licence.allowed:
        return None
    try:
        pinned = reader.pinned_file(AWS_SDK_REPOSITORY, cache["commit"], model)
        metadata = json.loads(pinned["bytes"]).get("metadata") or {}
    except (LookupError, ValueError):
        return None
    signing = metadata.get("signingName") or metadata.get("endpointPrefix")
    if not signing or str(metadata.get("signatureVersion", "v4")) not in ("v4", "s3v4"):
        return None
    return ({"protocol": metadata.get("protocol"), "json_version": metadata.get("jsonVersion"),
             "signing_name": signing, "api_version": metadata.get("apiVersion")}, pinned, licence)


def vendor_of(name: str) -> str:
    """A lower-case identifier for one API of the directory, for module and variable names."""
    provider, _, service = name.partition(":")
    words = [provider.split(".")[0]] + ([service] if service else [])
    vendor = _SEGMENT.sub("_", "_".join(words).lower()).strip("_") or "api"
    return ("api_" + vendor if vendor[0].isdigit() else vendor)[:40].rstrip("_")


def read_directory(reader) -> tuple:
    """(the directory list, its fetch) of APIs.guru."""
    answer = reader.get(https_address(DIRECTORY_HOST, DIRECTORY_LIST))
    if answer.status != 200:
        raise SupplyRecordError("specification_unreadable", "the directory list did not answer")
    return json.loads(answer.body), answer


def generate(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging, only=None,
             maximum_apis: "int | None" = None, maximum_operations: int = 5000) -> tuple:
    """(built, refusals, facts, decisions, summary) of every API of the directory, or of the named ones."""
    directory, listing = read_directory(reader)
    facts = {listing.sha256: listing.body}
    texts = LicenceTexts(reader)
    origins, decisions, built, refused, summary, aws_cache = {}, [], [], [], Counter(), {}
    generator = {"identity": "tools/supply_lines/openapi_directory.py", "version": "1.0.0",
                 "code_revision": code_revision}
    names = sorted(directory)
    if only:
        names = [name for name in names if name in set(only) or name.split(":")[0] in set(only)]
    if maximum_apis:
        names = names[:maximum_apis]
    for name in names:
        api = directory[name]
        version = api.get("preferred")
        entry = (api.get("versions") or {}).get(version) or {}
        info = entry.get("info") or {}
        decision = decide(name, info, reader, texts, origins)
        decisions.append({key: value for key, value in decision.items() if key != "licence"})
        summary[f"licence:{decision['decision']}"] += 1
        if decision["decision"] != AGREED:
            reason = decision["decision"] if decision["decision"] in KNOWN_LICENCE_REFUSALS else LICENCE_UNKNOWN
            refused.append(refusal(OPENAPI_OPERATIONS, reason, name, str(decision.get("declared_name") or "")))
            continue
        url = entry.get("swaggerUrl")
        answer = reader.get(url) if url else None
        if answer is None or answer.status != 200:
            refused.append(refusal(OPENAPI_OPERATIONS, "specification_unreadable", name, str(url)))
            continue
        try:
            document = plain(json.loads(answer.body))
        except ValueError:
            refused.append(refusal(OPENAPI_OPERATIONS, "specification_unreadable", name, "not JSON"))
            continue
        facts[answer.sha256] = answer.body
        if str(document.get("swagger", "")).startswith("2"):
            document = swagger2_to_openapi3(document)
        if not str(document.get("openapi", "")).startswith("3"):
            refused.append(refusal(OPENAPI_OPERATIONS, "specification_version_unsupported", name))
            continue
        vendor = vendor_of(name)
        source = {"source_id": name, "vendor": vendor, "credential_prefix": vendor.upper(),
                  "maximum_operations": maximum_operations}
        aws_facts = []
        if name.split(":")[0] == AWS_PROVIDER:
            found_aws = aws_metadata(reader, info, aws_cache)
            if found_aws is not None:
                source["aws"], pinned, sdk_licence = found_aws
                facts[pinned["sha256"]] = pinned["bytes"]
                aws_facts.append(fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"],
                                             len(pinned["bytes"]), "repository_facts", spdx=sdk_licence.spdx,
                                             basis="aws_sdk_model_metadata_at_the_pinned_commit",
                                             evidence_sha256=sdk_licence.sha256))
        licence = decision["licence"]
        origin = decision.get("origin_repository")
        path = url.split(f"{DIRECTORY_HOST}/", 1)[-1]
        spec = {"document": document, "origin": "apis_guru_directory", "repository": "apis.guru/" + name.replace(":", "/"),
                "commit": f"version:{version};updated:{entry.get('updated', '')}", "path": path, "url": url,
                "sha256": answer.sha256, "size_bytes": len(answer.body), "retrieved_at": answer.retrieved_at,
                "licence": licence.spdx, "title": re.sub(r"\s+", " ", str(info.get("title") or name))[:80],
                "version": str(version or "")[:40], "base_url_variable": f"{vendor.upper()}_BASE_URL",
                "licence_basis": decision["basis"],
                "licence_text_basis": ("licence_file_at_the_pinned_commit" if decision["basis"] == ORIGIN_BASIS
                                       else "licence_text_from_choosealicense_at_the_pinned_commit"),
                "extra_facts": [fact_source(listing.url, listing.retrieved_at, listing.sha256, len(listing.body),
                                            "registry_entry", spdx=DIRECTORY_LICENCE,
                                            basis="directory_list_of_apis_guru")] + aws_facts}
        if origin:
            spec["origin_repository"] = origin
        found, refusals = operations(document, source)
        refused += refusals
        summary["apis"] += 1
        summary["operations"] += len(found)
        kept = 0
        for operation in found[:maximum_operations]:
            try:
                built.append(_package(operation, spec, source, licence, generator, licence_text, generated_on,
                                      staging, {}))
                kept += 1
            except OperationRefused as error:
                refused.append(refusal(OPENAPI_OPERATIONS, error.reason, f"{name} {operation.method} {operation.path}",
                                       error.detail))
            except SupplyRecordError as error:
                reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                    GENERATED_TEST_FAILED
                refused.append(refusal(OPENAPI_OPERATIONS, reason, f"{name} {operation.method} {operation.path}",
                                       str(error)))
        summary["packaged"] += kept
    return built, refused, facts, decisions, dict(summary)


__all__ = ["DECLARED_LICENCE_NAMES", "LicenceTexts", "declared_licence", "decide", "generate", "origin_repository",
           "read_directory", "swagger2_to_openapi3", "vendor_of"]

"""Line openapi_operations: one API operation client per operation of a licensed OpenAPI specification.

```text
One specification (declared in openapi_sources.json)
├── pinned: the branch's head commit, the file's git blob identity, its bytes proven by that identity
├── licence: GitHub's licence interface and the licence text at that commit agree on an allowlisted
│   licence (supply_lines/licences.py); the text travels as UPSTREAM-LICENSE
└── every operation (path and method), each its own package
    ├── <vendor>_<operation>.py: one function with keyword arguments for the path, query and header
    │   parameters and the JSON body; it checks types, enumerations and required fields before any
    │   request, reads the credential from a named environment variable, sends one HTTPS request
    │   and raises ApiError with the documented meaning for any status outside the successes
    ├── test_<vendor>_<operation>.py: a local mock built from the specification's examples (or a
    │   minimal value built from the schema), and known-wrong calls: a missing required argument,
    │   a wrong type, an error status, a missing credential; each must send nothing or raise
    ├── schema.json: the operation's input and output schemas, local references resolved
    └── README.md, LICENSE (the generated code, MIT), UPSTREAM-LICENSE, ATTRIBUTION.md
```

The generated tests run in this process before a package is stored, with the
network closed; a package whose own tests fail is refused. Operations that
need a body other than JSON, a cookie, an object in the query string, a
reference into another file or a server that is not HTTPS are refused by name.
"""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import keyword
import math
import pprint
import re
import shutil
import sys
import textwrap
import unittest
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from .declared_licences import LicenceTexts, repository_declaration
from .licences import LICENCE_NOT_ON_ALLOWLIST, repository_licence
from .packaging import (
    LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build)
from .reading import RAW_HOST, github_blob_address, https_address, is_https
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT, OPENAPI_OPERATIONS,
    PACKAGE_ABOVE_REVIEW_BOUND, REFUSAL_REASONS, SupplyRecordError, fact_source, licence_allowed, provenance, refusal,
    upstream_key)

GENERATOR_VERSION = "1.4.0"
#: The text of a second allowlisted licence a specification declares beside its repository's licence.
SPECIFICATION_LICENCE_NAME = "SPECIFICATION-LICENSE"
DECLARED_TEXT_BASIS = "specification_info_license_declaration_text_from_choosealicense_at_the_pinned_commit"
#: What the first success answer holds: JSON, text, other bytes, or nothing.
JSON_ANSWER, TEXT_ANSWER, BINARY_ANSWER, NO_ANSWER = "json", "text", "binary", "empty"
#: Refusal codes a package build may raise that the line keeps as they are; any other means its tests failed.
KEPT_CODES = (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND)
SOURCES_FILE = Path(__file__).with_name("openapi_sources.json")
SOURCES_RECORD_TYPE = "library_supply_openapi_sources/v1"
HOSTS = (RAW_HOST,)
NATIVE_FORMAT = "openapi_operation_python"
METHODS = ("get", "put", "post", "delete", "patch", "head", "options")
#: Keyword arguments every generated function has; a parameter with one of these names is renamed.
RESERVED = ("body", "base_url", "timeout", "transport")
#: Headers the client sets itself; a parameter naming one is left to the client, or refused when required.
MANAGED_HEADERS = ("authorization", "content-type", "accept", "user-agent", "content-length", "host")
CHECK_DEPTH = 3
SCHEMA_DEPTH = 8
MAXIMUM_EXAMPLE_CHARACTERS = 24_000
USER_AGENT = "baltor-api-client/1"


class OperationRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


# -- the sources ---------------------------------------------------------------------------------------------------
def read_sources(path: Path = SOURCES_FILE) -> list:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    rows = []
    for row in record["specifications"]:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", row["vendor"]) or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{1,80}", row["credential_variable"]):
            raise ValueError(f"{row['source_id']}: a vendor is a lower-case word and a credential an upper-case name")
        for field_name in ("directory_names", "directory_providers"):
            entries = row.get(field_name, [])
            if not isinstance(entries, list) or not all(isinstance(entry, str) and entry for entry in entries):
                raise ValueError(f"{row['source_id']}: {field_name} lists APIs.guru directory names")
        rows.append(row)
    return rows


# -- references and schemas ----------------------------------------------------------------------------------------
class Resolver:
    """Local references (#/...) of one document; a reference into another file is refused by name."""

    def __init__(self, document: dict) -> None:
        self.document = document

    def target(self, reference: str):
        if not isinstance(reference, str) or not reference.startswith("#/"):
            raise OperationRefused("operation_parameters_unsupported", f"reference outside the file: {reference}")
        node = self.document
        for part in reference[2:].split("/"):
            part = urllib.parse.unquote(part).replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
                node = node[int(part)]
            else:
                raise OperationRefused("operation_parameters_unsupported", f"unresolved reference {reference}")
        return node

    def follow(self, node, limit: int = 20):
        """A parameter, body or response object with its reference chain followed."""
        seen = 0
        while isinstance(node, dict) and "$ref" in node:
            seen += 1
            if seen > limit:
                raise OperationRefused("operation_parameters_unsupported", "a reference chain does not end")
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            node = {**self.target(node["$ref"]), **siblings}
        return node

    def schema(self, node, depth: int = 0, trail: tuple = ()):
        """The schema with local references resolved, recursion cut and depth bounded, as plain data."""
        if not isinstance(node, dict):
            return node if isinstance(node, (bool, type(None))) else {}
        if "$ref" in node:
            reference = node["$ref"]
            if reference in trail:
                return {"$comment": f"recursive reference to {reference}"}
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            target = self.target(reference)
            return self.schema({**target, **siblings} if isinstance(target, dict) else target, depth,
                               trail + (reference,))
        if depth >= SCHEMA_DEPTH:
            kept = {key: node[key] for key in ("type", "format", "enum", "nullable") if key in node}
            return {**kept, "$comment": "deeper levels are in the specification"}
        result = {}
        for key, value in node.items():
            if key in ("properties", "patternProperties", "$defs", "definitions") and isinstance(value, dict):
                result[key] = {name: self.schema(part, depth + 1, trail) for name, part in value.items()}
            elif key in ("items", "additionalProperties", "not", "contains", "propertyNames") and isinstance(value, dict):
                result[key] = self.schema(value, depth + 1, trail)
            elif key in ("allOf", "anyOf", "oneOf", "prefixItems") and isinstance(value, list):
                result[key] = [self.schema(part, depth + 1, trail) for part in value]
            else:
                result[key] = plain(value)
        return result


def plain(value):
    """JSON data only: dates become text, non-finite numbers become None."""
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)


def _types(schema: dict) -> list:
    value = schema.get("type")
    kinds = [value] if isinstance(value, str) else [kind for kind in value if isinstance(kind, str)] \
        if isinstance(value, list) else []
    if kinds and schema.get("nullable") is True and "null" not in kinds:
        kinds.append("null")
    return kinds


def check_schema(schema, depth: int = 0, *, request: bool = True) -> dict:
    """The part of a schema a client checks before sending: types, enumerations, required fields and nesting."""
    if not isinstance(schema, dict):
        return {}
    result = {}
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged = {key: value for key, value in schema.items() if key != "allOf"}
        properties, required = dict(merged.get("properties") or {}), list(merged.get("required") or [])
        kinds = _types(merged)
        for part in schema["allOf"]:
            if isinstance(part, dict):
                properties.update({key: value for key, value in (part.get("properties") or {}).items()
                                   if key not in properties})
                required += [name for name in part.get("required") or () if isinstance(name, str)]
                kinds = kinds or _types(part)
        schema = {**merged, "properties": properties, "required": required, **({"type": kinds} if kinds else {})}
        if not kinds and properties:
            schema["type"] = ["object"]
    kinds = _types(schema)
    if kinds:
        result["type"] = kinds
    if isinstance(schema.get("format"), str):
        result["format"] = schema["format"]
    if isinstance(schema.get("minimum"), (int, float)) and not isinstance(schema.get("minimum"), bool):
        result["minimum"] = schema["minimum"]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum and len(enum) <= 200 and all(
            isinstance(value, (str, int, float, bool, type(None))) for value in enum):
        result["enum"] = list(enum) + ([None] if "null" in kinds and None not in enum else [])
    for key in ("anyOf", "oneOf"):
        if isinstance(schema.get(key), list) and schema[key] and depth < CHECK_DEPTH:
            result["anyOf"] = [check_schema(part, depth + 1, request=request) for part in schema[key]]
            if any(part == {} for part in result["anyOf"]):
                del result["anyOf"]  # a branch that allows anything allows the value
            break
    if depth < CHECK_DEPTH:
        properties = schema.get("properties")
        if isinstance(properties, dict) and properties:
            result["properties"] = {name: check_schema(part, depth + 1, request=request)
                                    for name, part in properties.items() if isinstance(part, dict)}
        required = [name for name in schema.get("required") or () if isinstance(name, str)]
        if request and isinstance(properties, dict):
            required = [name for name in required if not (properties.get(name) or {}).get("readOnly")]
        if required:
            result["required"] = sorted(set(required), key=required.index)
        if isinstance(schema.get("items"), dict):
            result["items"] = check_schema(schema["items"], depth + 1, request=request)
    return result


#: JSON Schema's instance types (the standard's closed vocabulary), each with the test a value passes.
SCHEMA_TYPE_TESTS = {
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "string": lambda value: isinstance(value, str),
    "array": lambda value: isinstance(value, (list, tuple)),
    "object": lambda value: isinstance(value, dict),
    "null": lambda value: value is None}
NULL_TYPE, OBJECT_TYPE, STRING_TYPE = "null", "object", "string"


def _is(value, kind: str) -> bool:
    """True when the value is of the JSON Schema type; an unknown type allows any value."""
    return SCHEMA_TYPE_TESTS.get(kind, lambda _value: True)(value)


def check_value(value, schema: dict, name: str) -> None:
    """The generated client's own check (written out below as _check), used here to test examples."""
    if not schema:
        return
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            try:
                check_value(value, branch, name)
                return
            except (TypeError, ValueError):
                continue
        raise ValueError(f"{name} matches none of the allowed shapes")
    kinds = schema.get("type") or []
    if kinds and not any(_is(value, kind) for kind in kinds):
        raise TypeError(f"{name} must be {' or '.join(kinds)}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{name} must be one of the allowed values")
    if isinstance(value, dict):
        missing = [key for key in schema.get("required", ()) if key not in value]
        if missing:
            raise ValueError(f"{name} lacks {missing}")
        for key, part in (schema.get("properties") or {}).items():
            if key in value and value[key] is not None:
                check_value(value[key], part, f"{name}.{key}")
    elif isinstance(value, (list, tuple)) and "items" in schema:
        for index, item in enumerate(value):
            check_value(item, schema["items"], f"{name}[{index}]")


_FORMAT_EXAMPLES = {"date-time": "2026-01-01T00:00:00Z", "date": "2026-01-01", "email": "user@example.com",
                    "uri": https_address("example.com", ""), "url": https_address("example.com", ""),
                    "uuid": "00000000-0000-4000-8000-000000000000", "ipv4": "192.0.2.1", "hostname": "example.com",
                    "binary": "", "byte": "ZXhhbXBsZQ=="}


def _number_example(schema: dict, floor: float, whole: bool):
    minimum = schema.get("minimum")
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        return int(floor) if whole else floor
    return max(int(floor), int(math.ceil(minimum))) if whole else max(floor, float(minimum))


def _array_example(schema: dict, depth: int, every_property: bool):
    items = schema.get("items")
    return [synthesize(items, depth + 1, every_property=every_property)] if isinstance(items, dict) and depth < 6 \
        else []


def _object_example(schema: dict, depth: int, every_property: bool):
    properties = schema.get("properties") or {}
    names = list(schema.get("required", ()))
    if every_property and depth < 3:
        names += [name for name in properties if name not in names]
    return {name: synthesize(properties.get(name) or {}, depth + 1, every_property=every_property) for name in names}


#: One small value per JSON Schema type, each a function of the schema, the depth and whether to fill every field.
TYPE_EXAMPLES = {
    "string": lambda schema, depth, every: _FORMAT_EXAMPLES.get(schema.get("format", ""), "example"),
    "integer": lambda schema, depth, every: _number_example(schema, 1, True),
    "number": lambda schema, depth, every: _number_example(schema, 1.5, False),
    "boolean": lambda schema, depth, every: True,
    "array": _array_example,
    "object": _object_example}


def synthesize(schema: dict, depth: int = 0, *, every_property: bool = False):
    """A small value the check accepts: the first enumeration value, formats respected, and the required fields
    of an object (every field when asked, for a mock answer that shows the answer's shape)."""
    if not schema:
        return "example"
    if "enum" in schema:
        values = [value for value in schema["enum"] if value is not None]
        return values[0] if values else None
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            candidate = synthesize(branch, depth + 1, every_property=every_property)
            try:
                check_value(candidate, branch, "value")
                return candidate
            except (TypeError, ValueError):
                continue
    kinds = [kind for kind in schema.get("type") or [] if kind != NULL_TYPE]
    kind = kinds[0] if kinds else (OBJECT_TYPE if isinstance(schema.get("properties"), dict) else STRING_TYPE)
    example = TYPE_EXAMPLES.get(kind)
    return example(schema, depth, every_property) if example is not None else None


# -- operations ----------------------------------------------------------------------------------------------------
@dataclass
class Parameter:
    python: str
    wire: str
    location: str
    required: bool
    schema: dict
    check: dict
    description: str
    example: object = None


@dataclass
class Operation:
    method: str
    path: str
    operation_id: str
    function: str
    module: str
    summary: str
    description: str
    parameters: list
    body_required: bool = False
    body_schema: "dict | None" = None
    body_check: "dict | None" = None
    body_example: object = None
    success_statuses: tuple = (200,)
    response_kind: str = JSON_ANSWER
    response_schema: "dict | None" = None
    response_example: object = None
    errors: dict = field(default_factory=dict)
    base_url: str = ""
    auth: "dict | None" = None
    auth_optional: bool = False
    deprecated: bool = False
    #: Query items a specification writes into the path key itself (/responses?beta=true); sent on every call.
    fixed_query: tuple = ()
    #: The path key as the specification writes it, when it differs from the path sent (a query or a fragment).
    path_key: str = ""
    #: Headers sent on every call (an AWS JSON target), the body's media type, and a server address template
    #: whose region the caller chooses, with the region used when the caller names none.
    fixed_headers: tuple = ()
    body_media: str = "application/json"
    base_url_template: str = ""
    region_default: str = ""


def snake(value: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    text = re.sub(r"_+", "_", text)
    if not text or text[0].isdigit():
        text = "op_" + text
    return text + "_" if keyword.iskeyword(text) else text


def _description(node: dict) -> str:
    text = str(node.get("summary") or node.get("description") or "").strip()
    return re.sub(r"\s+", " ", text)


def _first_example(node: dict):
    if not isinstance(node, dict):
        return None
    if "example" in node:
        return node["example"]
    examples = node.get("examples")
    if isinstance(examples, dict):
        for value in examples.values():
            if isinstance(value, dict) and "value" in value:
                return value["value"]
    if isinstance(examples, list) and examples:
        return examples[0]
    return None


def _json_content(content) -> "tuple | None":
    """(media type, media object) of the JSON entry of a content map, or None."""
    if not isinstance(content, dict):
        return None
    for media, value in content.items():
        base = str(media).split(";")[0].strip().lower()
        if base == "application/json" or base.endswith("+json"):
            return base, value if isinstance(value, dict) else {}
    return None


JSON_MEDIA_TYPE = "application/json"
REGION_VARIABLE = "region"


def _region_template(servers) -> tuple:
    """(address template with {region}, default region) of the first HTTPS server that names a region variable."""
    for server in servers or ():
        if not isinstance(server, dict) or not isinstance(server.get("url"), str) or not is_https(server["url"]):
            continue
        variables = server.get("variables") or {}
        region = variables.get(REGION_VARIABLE) if isinstance(variables, dict) else None
        if isinstance(region, dict) and "default" in region:
            template = server["url"]
            for name, variable in variables.items():
                if name != REGION_VARIABLE and isinstance(variable, dict) and "default" in variable:
                    template = template.replace("{" + name + "}", str(variable["default"]))
            if re.fullmatch(r"[^{}]*\{region\}[^{}]*", template):
                return template.rstrip("/"), str(region["default"])
    return "", ""


def _server(servers) -> str:
    for server in servers or ():
        if not isinstance(server, dict) or not isinstance(server.get("url"), str):
            continue
        url = server["url"]
        for name, variable in (server.get("variables") or {}).items():
            if isinstance(variable, dict) and "default" in variable:
                url = url.replace("{" + name + "}", str(variable["default"]))
        if is_https(url) and "{" not in url:
            return url.rstrip("/")
    return ""


#: OpenAPI's security scheme types this client can send, keyed by (type, HTTP scheme or key location): where the
#: credential goes. Any other scheme (a cookie key, mutual TLS) is refused by name.
HTTP_SCHEME_TYPE, API_KEY_SCHEME_TYPE = "http", "apiKey"
#: The scheme name a client records when the sources declaration, not the specification, names the credential.
DECLARED_SCHEME = "declared_in_openapi_sources"
#: The extension prefix AWS specifications use to mark a request-signing scheme (awsSigv4).
SIGNATURE_EXTENSION_PREFIX = "x-amazon-apigateway-authtype"
#: Where an AWS Signature Version 4 credential goes: nowhere as it is; the client signs each request with it.
SIGV4_PLACEMENT = "aws_sigv4"
#: The standard environment variables of AWS credentials, named once (names, never values).
AWS_CREDENTIAL_VARIABLES = {"variable": "AWS_ACCESS_KEY_ID", "secret_variable": "AWS_SECRET_ACCESS_KEY",
                            "token_variable": "AWS_SESSION_TOKEN"}
#: The request headers an AWS specification declares for signing; the signer sets them, so no caller passes them.
AWS_SIGNING_PARAMETERS = frozenset({"x-amz-content-sha256", "x-amz-date", "x-amz-algorithm", "x-amz-credential",
                                    "x-amz-security-token", "x-amz-signature", "x-amz-signedheaders"})
#: AWS protocols whose requests this client can write, and the signing names it does not sign for (S3 needs a
#: payload hash header and single path encoding).
AWS_PROTOCOLS = ("json", "rest-json", "query", "ec2", "rest-xml")
AWS_UNSIGNABLE_SERVICES = frozenset({"s3", "s3-outposts", "s3-object-lambda", "s3express"})
AWS_TARGET_HEADER = "X-Amz-Target"
AWS_ACTION = "Action"
AWS_VERSION = "Version"
AWS_QUERY_PROTOCOLS = ("query", "ec2")
_BEARER = {"placement": "header", "name": "Authorization", "prefix": "Bearer "}
SCHEME_PLACEMENTS = {
    (HTTP_SCHEME_TYPE, "bearer"): _BEARER, ("oauth2", ""): _BEARER, ("openIdConnect", ""): _BEARER,
    (HTTP_SCHEME_TYPE, "basic"): {"placement": "basic", "name": "Authorization", "prefix": "Basic "},
    (API_KEY_SCHEME_TYPE, "header"): {"placement": "header", "name": "", "prefix": ""},
    (API_KEY_SCHEME_TYPE, "query"): {"placement": "query", "name": "", "prefix": ""}}


#: The suffix of a credential variable named by rule (a directory source names a prefix, not each variable).
CREDENTIAL_SUFFIXES = {API_KEY_SCHEME_TYPE: "_API_KEY", HTTP_SCHEME_TYPE + ":basic": "_CREDENTIALS"}
TOKEN_SUFFIX = "_ACCESS_TOKEN"


def credential_variable(source: dict, key: tuple) -> str:
    """The declared variable, or one named by rule: the prefix and a suffix for the scheme's kind."""
    if source.get("credential_variable"):
        return source["credential_variable"]
    kind, detail = key
    suffix = CREDENTIAL_SUFFIXES.get(kind) or CREDENTIAL_SUFFIXES.get(f"{kind}:{detail}") or TOKEN_SUFFIX
    return source["credential_prefix"] + suffix


def _auth(document: dict, requirements, source: dict) -> tuple:
    """(auth, optional): how the credential travels, from the first security requirement, or (None, True)."""
    if requirements is None:
        requirements = document.get("security") or []
    schemes_declared = bool((document.get("components") or {}).get("securitySchemes"))
    fallback = source.get("fallback_security")
    if not requirements and not schemes_declared and fallback:
        # The specification declares no security at all; the sources declaration names how the API takes a
        # credential (for example GitHub's bearer token), and whether a call may go without one.
        return {"scheme": DECLARED_SCHEME, **_BEARER, "variable": credential_variable(source, ("oauth2", ""))}, \
            bool(fallback.get("optional"))
    if not requirements:
        return None, True
    optional = any(requirement == {} for requirement in requirements)
    schemes = (document.get("components") or {}).get("securitySchemes") or {}
    for requirement in requirements:
        if not isinstance(requirement, dict) or not requirement:
            continue
        name = next(iter(requirement))
        scheme = schemes.get(name)
        if isinstance(scheme, dict) and "$ref" in scheme:
            scheme = Resolver(document).follow(scheme)
        if not isinstance(scheme, dict):
            continue
        kind = scheme.get("type")
        if any(str(field).startswith(SIGNATURE_EXTENSION_PREFIX) for field in scheme):
            # A request-signing scheme (AWS Signature Version 4): the client signs each request when the AWS SDK's
            # published metadata names the service's protocol and signing name; otherwise it is refused.
            aws = source.get("aws") or {}
            if aws.get("protocol") not in AWS_PROTOCOLS or not aws.get("signing_name") or \
                    aws["signing_name"] in AWS_UNSIGNABLE_SERVICES:
                raise OperationRefused("security_scheme_unsupported", f"security scheme {name} signs each request")
            return {"scheme": name, "placement": SIGV4_PLACEMENT, "name": "Authorization", "prefix": "",
                    **AWS_CREDENTIAL_VARIABLES, "service": aws["signing_name"]}, optional
        key = (kind, str(scheme.get("scheme", "")).lower() if kind == HTTP_SCHEME_TYPE else
               str(scheme.get("in", "")) if kind == API_KEY_SCHEME_TYPE else "")
        variable = (source.get("scheme_variables") or {}).get(name) or credential_variable(source, key)
        placement = SCHEME_PLACEMENTS.get(key)
        if placement is None or (kind == API_KEY_SCHEME_TYPE and not isinstance(scheme.get("name"), str)):
            raise OperationRefused("operation_parameters_unsupported", f"security scheme {name} of type {kind}")
        return {"scheme": name, **placement, "name": scheme["name"] if kind == API_KEY_SCHEME_TYPE else placement["name"],
                "variable": variable}, optional
    return None, True


def operations(document: dict, source: dict) -> tuple:
    """(operations, refusals) of one specification document, in path and method order."""
    resolver = Resolver(document)
    found, refused, names = [], [], set()
    top_servers = document.get("servers") or []
    for path in sorted(document.get("paths") or {}):
        item = resolver.follow(document["paths"][path]) if isinstance(document["paths"][path], dict) else {}
        for method in METHODS:
            node = item.get(method)
            if not isinstance(node, dict):
                continue
            label = f"{method.upper()} {path}"
            try:
                operation = _operation(document, resolver, source, path, method, item, node, top_servers)
            except OperationRefused as error:
                refused.append(refusal(OPENAPI_OPERATIONS, error.reason, f"{source['source_id']} {label}", error.detail))
                continue
            if operation.module in names:
                refused.append(refusal(OPENAPI_OPERATIONS, "duplicate_operation", f"{source['source_id']} {label}",
                                       operation.module))
                continue
            names.add(operation.module)
            found.append(operation)
    return found, refused


def _aws_fragment(path: str, aws: dict) -> tuple:
    """(fixed headers, fixed query) an AWS path key's fragment names: #X-Amz-Target=... or #Action=...."""
    fragment = path.partition("#")[2]
    name, _separator, value = fragment.partition("=")
    if not value:
        return (), ()
    if name == AWS_TARGET_HEADER:
        return ((AWS_TARGET_HEADER, value),), ()
    if name == AWS_ACTION and aws.get("api_version"):
        return (), ((AWS_ACTION, value), (AWS_VERSION, aws["api_version"]))
    return (), ()


def _operation(document, resolver, source, path, method, item, node, top_servers) -> Operation:
    operation_id = str(node.get("operationId") or "").strip() or f"{method}_{path}"
    function = snake(operation_id)
    module = f"{source['vendor']}_{function}"[:80]
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", module):
        raise OperationRefused("operation_identity_missing", operation_id)
    auth, auth_optional = _auth(document, node.get("security"), source)
    signs = bool(auth and auth["placement"] == SIGV4_PLACEMENT)
    aws = source.get("aws") or {} if signs else {}
    fixed_headers, aws_query = _aws_fragment(path, aws) if signs else ((), ())
    fixed_names = {name.lower() for name, _value in fixed_headers}
    # The query protocol is the API's (AWS metadata) or the operation's own (its path key names an Action).
    query_protocol = signs and (aws.get("protocol") in AWS_QUERY_PROTOCOLS or bool(aws_query))
    merged = {}
    for raw in list(item.get("parameters") or []) + list(node.get("parameters") or []):
        parameter = resolver.follow(raw)
        if not isinstance(parameter, dict) or not isinstance(parameter.get("name"), str):
            raise OperationRefused("operation_parameters_unsupported", "a parameter without a name")
        lowered = parameter["name"].lower()
        if signs and (lowered in AWS_SIGNING_PARAMETERS or lowered in fixed_names or
                      (parameter.get("in") == "query" and parameter["name"] in (AWS_ACTION, AWS_VERSION) and aws_query)):
            continue  # the signer or the path key's fragment supplies it
        merged[(parameter["name"], parameter.get("in"))] = parameter
    parameters, pythons = [], set(RESERVED)
    for (name, location), parameter in merged.items():
        required = bool(parameter.get("required")) or location == "path"
        if location == "cookie" or (location == "header" and name.lower() in MANAGED_HEADERS):
            if required:
                raise OperationRefused("operation_parameters_unsupported", f"{location} parameter {name}")
            continue
        if location not in ("path", "query", "header"):
            raise OperationRefused("operation_parameters_unsupported", f"parameter {name} in {location}")
        if "content" in parameter and "schema" not in parameter:
            raise OperationRefused("operation_parameters_unsupported", f"parameter {name} with a content map")
        schema = resolver.schema(parameter.get("schema") or {})
        check = check_schema(schema)
        if location == "query" and "object" in check.get("type", []) or (
                query_protocol and location == "query" and "array" in check.get("type", [])):
            # An object in the query, or a list in the AWS query protocol (which numbers each member), is not
            # written by this client: an optional one is left out, a required one refuses the operation.
            if required:
                raise OperationRefused("operation_parameters_unsupported", f"object or list in the query: {name}")
            continue
        python = snake(name)
        while python in pythons:
            python += "_parameter"
        pythons.add(python)
        example = _first_example(parameter)
        if example is None:
            example = _first_example(parameter.get("schema") or {})
        parameters.append(Parameter(python, name, location, required, schema, check,
                                    re.sub(r"\s+", " ", str(parameter.get("description") or ""))[:300], plain(example)))
    # Some specifications tell operations on one path apart by a fragment (/files/{id}#add_shared_link) or write a
    # fixed query into the path key (/responses?beta=true). Neither belongs to the path that is sent: a fragment
    # is never sent, and a fixed query travels as query items on every call.
    sent_path, _separator, fixed_text = path.partition("#")[0].partition("?")
    fixed = urllib.parse.parse_qsl(fixed_text, keep_blank_values=True) + list(aws_query)
    placeholders = re.findall(r"{([^}]+)}", sent_path)
    declared = {parameter.wire for parameter in parameters if parameter.location == "path"}
    if set(placeholders) - declared:
        raise OperationRefused("operation_parameters_unsupported", f"undeclared path parameters {placeholders}")
    parameters.sort(key=lambda row: (not row.required, ("path", "query", "header").index(row.location), row.python))
    operation = Operation(method.upper(), sent_path, operation_id, function, module, _description(node)[:300],
                          re.sub(r"\s+", " ", str(node.get("description") or ""))[:600], parameters,
                          deprecated=bool(node.get("deprecated")), fixed_query=tuple(fixed),
                          path_key=path if path != sent_path else "", fixed_headers=tuple(fixed_headers),
                          body_media=(f"application/x-amz-json-{aws['json_version']}"
                                      if signs and aws.get("protocol") == "json" and aws.get("json_version")
                                      else JSON_MEDIA_TYPE))
    body = node.get("requestBody")
    if body is not None:
        body = resolver.follow(body)
        found = _json_content(body.get("content"))
        if found is None:
            raise OperationRefused("operation_body_not_json", ", ".join(sorted(body.get("content") or {}))[:200])
        _media, media = found
        operation.body_required = bool(body.get("required"))
        operation.body_schema = resolver.schema(media.get("schema") or {})
        operation.body_check = check_schema(operation.body_schema)
        operation.body_example = plain(_first_example(media) or _first_example(media.get("schema") or {}))
    responses = node.get("responses") or {}
    successes = sorted(int(code) for code in responses if str(code).isdigit() and 200 <= int(code) < 300)
    operation.success_statuses = tuple(successes) or (200,)
    first = resolver.follow(responses.get(str(operation.success_statuses[0])) or {})
    content = first.get("content") if isinstance(first, dict) else None
    found = _json_content(content)
    if found is not None:
        _media, media = found
        operation.response_schema = resolver.schema(media.get("schema") or {})
        operation.response_example = plain(_first_example(media) or _first_example(media.get("schema") or {}))
        operation.response_kind = JSON_ANSWER
    elif isinstance(content, dict) and content:
        media = str(next(iter(content))).split(";")[0].lower()
        operation.response_kind = TEXT_ANSWER if media.startswith("text/") else BINARY_ANSWER
    else:
        operation.response_kind = NO_ANSWER
    for code, response in responses.items():
        if str(code).isdigit() and int(code) >= 400:
            response = resolver.follow(response) if isinstance(response, dict) else {}
            operation.errors[int(code)] = re.sub(r"\s+", " ", str(response.get("description") or ""))[:160]
    servers = node.get("servers") or item.get("servers") or top_servers
    operation.base_url = _server(servers)
    if not operation.base_url:
        raise OperationRefused("operation_parameters_unsupported", "no HTTPS server")
    if signs:
        operation.base_url_template, operation.region_default = _region_template(servers)
    operation.auth, operation.auth_optional = auth, auth_optional
    return operation


# -- the generated client and its tests ----------------------------------------------------------------------------
def literal(value, indent: int = 0) -> str:
    text = pprint.pformat(value, width=110 - indent, sort_dicts=False)
    return text.replace("\n", "\n" + " " * indent)


RUNTIME = '''


class ApiError(Exception):
    """An answer outside the documented successes, with its status, its documented meaning and its body."""

    def __init__(self, status, meaning, body):
        super().__init__(f"{OPERATION['method']} {OPERATION['path']} answered {status}: {meaning}")
        self.status, self.meaning, self.body = status, meaning, body


def _is(value, kind):
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, {"boolean": bool, "string": str, "array": (list, tuple), "object": dict,
                              "null": type(None)}.get(kind, object))


def _check(value, schema, name):
    """Refuse a value that breaks the schema: its type, its allowed values, required fields and nesting."""
    if not schema:
        return
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            try:
                _check(value, branch, name)
                return
            except (TypeError, ValueError):
                continue
        raise ValueError(f"{name} matches none of the allowed shapes")
    kinds = schema.get("type") or []
    if kinds and not any(_is(value, kind) for kind in kinds):
        raise TypeError(f"{name} must be {' or '.join(kinds)}, not {type(value).__name__}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{name} must be one of {schema['enum'][:20]}")
    if isinstance(value, dict):
        missing = [key for key in schema.get("required", ()) if key not in value]
        if missing:
            raise ValueError(f"{name} lacks {missing}")
        for key, part in (schema.get("properties") or {}).items():
            if key in value and value[key] is not None:
                _check(value[key], part, f"{name}.{key}")
    elif isinstance(value, (list, tuple)) and "items" in schema:
        for index, item in enumerate(value):
            _check(item, schema["items"], f"{name}[{index}]")


def _text(value):
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def _region():
    """The region the caller names in AWS_REGION (or AWS_DEFAULT_REGION), else the specification's default."""
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or REGION_DEFAULT


def _send(request, timeout):
    """Send the request over HTTPS and return (status, content type, bytes), error answers included."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, answer.headers.get("Content-Type", ""), answer.read()
    except urllib.error.HTTPError as error:
        return error.code, (error.headers.get("Content-Type", "") if error.headers else ""), error.read()


def _decode(content_type, payload):
    if not payload:
        return None
    if "json" in (content_type or "").lower():
        return json.loads(payload.decode("utf-8"))
    if (content_type or "").lower().startswith("text/"):
        return payload.decode("utf-8", "replace")
    return payload


def _call(arguments, body, base_url, timeout, transport):
    path, query = OPERATION["path"], list(FIXED_QUERY)
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT, **dict(FIXED_HEADERS)}
    for python_name, wire_name, location, _required, _schema in PARAMETERS:
        value = arguments[python_name]
        if value is None:
            continue
        if location == "path":
            path = path.replace("{" + wire_name + "}", urllib.parse.quote(_text(value), safe=""))
        elif location == "query":
            items = value if isinstance(value, (list, tuple)) else [value]
            query += [(wire_name, _text(item)) for item in items]
        else:
            headers[wire_name] = _text(value)
    root = (base_url or os.environ.get(BASE_URL_VARIABLE) or
            (BASE_URL_TEMPLATE.format(region=_region()) if BASE_URL_TEMPLATE else BASE_URL)).rstrip("/")
    if not root.startswith("https://"):
        raise ValueError("the API address must be an HTTPS address")
# AUTH
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = BODY_MEDIA
    url = root + path + ("?" + urllib.parse.urlencode(query) if query else "")
# SIGN
    request = urllib.request.Request(url, data=data, method=OPERATION["method"], headers=headers)
    status, content_type, payload = (transport or _send)(request, timeout)
    try:
        answer = _decode(content_type, payload)
    except (ValueError, UnicodeDecodeError):
        answer = payload
    if status not in SUCCESS_STATUSES:
        raise ApiError(status, ERRORS.get(status, "not a documented success"), answer)
    return answer
'''


AUTH_PLACEMENTS = {
    "header": '        headers[AUTH["name"]] = AUTH["prefix"] + credential\n',
    "basic": ('        headers[AUTH["name"]] = AUTH["prefix"] + '
              'base64.b64encode(credential.encode("utf-8")).decode("ascii")\n'),
    "query": '        query.append((AUTH["name"], credential))\n'}
AUTH_BLOCK = ('    credential = os.environ.get(AUTH["variable"], "")\n'
              '    if credential:\n'
              'PLACE'
              '    elif not AUTH_OPTIONAL:\n'
              '        raise PermissionError("set the environment variable " + AUTH["variable"] + " to call "\n'
              '                              + OPERATION["operation_id"])\n')


#: The AWS Signature Version 4 signer written into a client whose operation signs each request. It is checked
#: against AWS's published test vector (get-vanilla) in every generated test.
SIGNER = '''

def _signature_headers(method, url, headers, payload, access_key, secret_key, token, region, service, amz_date):
    """The headers AWS Signature Version 4 adds to one request: X-Amz-Date, the session token and Authorization."""
    parts = urllib.parse.urlsplit(url)
    signed = {name.lower(): " ".join(str(value).split()) for name, value in headers.items()}
    signed["host"] = parts.netloc
    signed["x-amz-date"] = amz_date
    if token:
        signed["x-amz-security-token"] = token
    names = sorted(signed)
    pairs = sorted(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    canonical_query = "&".join(urllib.parse.quote(key, safe="-_.~") + "=" + urllib.parse.quote(value, safe="-_.~")
                               for key, value in pairs)
    canonical = "\\n".join([method, urllib.parse.quote(parts.path or "/", safe="/-_.~"), canonical_query,
                           "".join(name + ":" + signed[name] + "\\n" for name in names), ";".join(names),
                           hashlib.sha256(payload or b"").hexdigest()])
    date = amz_date[:8]
    scope = date + "/" + region + "/" + service + "/aws4_request"
    to_sign = "\\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode("utf-8")).hexdigest()])
    key = ("AWS4" + secret_key).encode("utf-8")
    for part in (date, region, service, "aws4_request"):
        key = hmac.new(key, part.encode("utf-8"), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    added = {"X-Amz-Date": amz_date, "Authorization": "AWS4-HMAC-SHA256 Credential=" + access_key + "/" + scope +
             ", SignedHeaders=" + ";".join(names) + ", Signature=" + signature}
    if token:
        added["X-Amz-Security-Token"] = token
    return added
'''
#: The lines of _call that sign the request, for an operation whose security scheme is AWS Signature Version 4.
SIGN_BLOCK = ('    access_key, secret_key = os.environ.get(AUTH["variable"], ""), os.environ.get(AUTH["secret_variable"], "")\n'
              '    if not access_key or not secret_key:\n'
              '        raise PermissionError("set " + AUTH["variable"] + " and " + AUTH["secret_variable"] + " to call "\n'
              '                              + OPERATION["operation_id"])\n'
              '    headers.update(_signature_headers(OPERATION["method"], url, headers, data, access_key, secret_key,\n'
              '                                      os.environ.get(AUTH["token_variable"], ""), _region(),\n'
              '                                      AUTH["service"], time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())))\n')


def auth_block(auth: "dict | None") -> str:
    """The lines of _call that place the credential, for this operation's one security scheme only."""
    if auth is None or auth["placement"] == SIGV4_PLACEMENT:
        return ""
    return AUTH_BLOCK.replace("PLACE", AUTH_PLACEMENTS[auth["placement"]])


def doc(text: str) -> str:
    """Text safe inside a triple-quoted docstring."""
    return str(text).replace("\\", "\\\\").replace('"""', "'''")


def client_source(operation: Operation, spec: dict) -> str:
    title = spec["title"]
    arguments = []
    for parameter in operation.parameters:
        arguments.append(parameter.python if parameter.required else f"{parameter.python}=None")
    if operation.body_schema is not None:
        arguments.append("body" if operation.body_required else "body=None")
    arguments += ["base_url=None", "timeout=30.0", "transport=None"]
    lines = []
    for parameter in operation.parameters:
        kinds = " or ".join(parameter.check.get("type", [])) or "any value"
        text = f"{parameter.python}: {parameter.location} parameter {parameter.wire}, {kinds}" + (
            " (required)" if parameter.required else " (optional)")
        if parameter.description:
            text += f". {parameter.description[:160]}"
        lines.append(text)
    if operation.body_schema is not None:
        lines.append("body: the JSON request body" + (" (required)" if operation.body_required else " (optional)")
                     + '; its schema is "input.body" in schema.json.')
    lines += [f"base_url: overrides {operation.base_url}; the environment variable {spec['base_url_variable']} "
              "does too.", "timeout: seconds to wait for the answer.",
              "transport: a callable (request, timeout) -> (status, content type, bytes), for tests; the default "
              "sends the request over HTTPS."]
    lines = [textwrap.fill(line, width=100, initial_indent="  ", subsequent_indent="    ") for line in lines]
    credential = ""
    if operation.auth:
        credential = (f", PermissionError when {operation.auth['variable']} is not set" if not operation.auth_optional
                      else "")
    returns = {JSON_ANSWER: f"the parsed JSON answer of status {operation.success_statuses[0]}",
               TEXT_ANSWER: "the text of the answer", BINARY_ANSWER: "the bytes of the answer",
               NO_ANSWER: "None (the answer has no body)"}[operation.response_kind]
    closing = textwrap.fill(f"Returns {returns}. Raises TypeError or ValueError before any request when an argument "
                            f"breaks the specification{credential}, and ApiError for any answer outside the documented "
                            "successes.", width=100)
    docstring = "\n".join([textwrap.fill(operation.summary or f"{operation.method} {operation.path}", width=100), "",
                           f"{operation.method} {operation.path} (operation {operation.operation_id}).", "",
                           "Arguments:", *lines, "", closing])
    values = ", ".join(f'"{parameter.python}": {parameter.python}' for parameter in operation.parameters)
    body_check = ""
    if operation.body_schema is not None:
        body_check = ("    if body is None and BODY_REQUIRED:\n        raise ValueError(\"body is required\")\n"
                      "    if body is not None:\n        _check(body, BODY_SCHEMA, \"body\")\n")
    parameters = [(parameter.python, parameter.wire, parameter.location, parameter.required, parameter.check)
                  for parameter in operation.parameters]
    uses_basic = bool(operation.auth and operation.auth["placement"] == "basic")
    header = doc(textwrap.fill(f"{title} API: {operation.summary or operation.operation_id}", width=110) + "\n\n"
                 + textwrap.fill(f"{operation.method} {operation.path}, operation {operation.operation_id} of {title} "
                                 f"{spec['version']}. Baltor generated this client from the specification at "
                                 f"{spec['repository']}@{spec['commit'][:12]} ({spec['path']}); see README.md and "
                                 "schema.json.", width=110))
    header = '"""' + header + '\n"""\n'
    signs = bool(operation.auth and operation.auth["placement"] == SIGV4_PLACEMENT)
    imports = ["from __future__ import annotations", "", *(["import base64"] if uses_basic else []),
               *(["import hashlib", "import hmac"] if signs else []), "import json", "import os",
               *(["import time"] if signs else []), "import urllib.error", "import urllib.parse", "import urllib.request",
               ""]
    signs = bool(operation.auth and operation.auth["placement"] == SIGV4_PLACEMENT)
    runtime = RUNTIME.replace("# AUTH\n", auth_block(operation.auth)).replace("# SIGN\n", SIGN_BLOCK if signs else "")
    if signs:
        runtime += SIGNER
    constants = [
        f'OPERATION = {literal({"method": operation.method, "path": operation.path, "operation_id": operation.operation_id})}',
        f"BASE_URL = {operation.base_url!r}", f"BASE_URL_VARIABLE = {spec['base_url_variable']!r}",
        "#: Query items the specification writes into this operation's path key; sent on every call.",
        f"FIXED_QUERY = {literal(operation.fixed_query)}",
        f"FIXED_HEADERS = {literal(operation.fixed_headers)}",
        f"BODY_MEDIA = {operation.body_media!r}",
        f"BASE_URL_TEMPLATE = {operation.base_url_template!r}",
        f"REGION_DEFAULT = {operation.region_default!r}",
        f"USER_AGENT = {USER_AGENT!r}",
        f"AUTH = {literal(operation.auth)}", f"AUTH_OPTIONAL = {operation.auth_optional!r}",
        "#: (python name, wire name, location, required, checked schema) of every parameter.",
        f"PARAMETERS = {literal(tuple(parameters))}",
        f"BODY_REQUIRED = {operation.body_required!r}",
        f"BODY_SCHEMA = {literal(operation.body_check)}",
        f"SUCCESS_STATUSES = {operation.success_statuses!r}",
        f"ERRORS = {literal(operation.errors)}"]
    signature = textwrap.fill(f"def {operation.function}(*, {', '.join(arguments)}):", width=110,
                              subsequent_indent=" " * (len(operation.function) + 5), break_long_words=False,
                              break_on_hyphens=False)
    function = (f"\n\n{signature}\n"
                + '    """' + "\n".join(line.rstrip() for line in doc(docstring).replace("\n", "\n    ").split("\n"))
                + '\n    """\n'
                + f"    arguments = {{{values}}}\n"
                + "    for python_name, _wire_name, _location, required, schema in PARAMETERS:\n"
                + "        value = arguments[python_name]\n"
                + "        if value is None:\n"
                + "            if required:\n"
                + "                raise ValueError(f\"{python_name} is required\")\n"
                + "            continue\n"
                + "        _check(value, schema, python_name)\n"
                + body_check
                + f"    return _call(arguments, {'body' if operation.body_schema is not None else 'None'}, base_url, "
                  "timeout, transport)\n")
    return header + "\n".join(imports) + "\n" + "\n".join(constants) + runtime + function


def _example_arguments(operation: Operation) -> dict:
    call = {}
    for parameter in operation.parameters:
        if not parameter.required:
            continue
        value = parameter.example
        try:
            if value is None:
                raise ValueError
            check_value(value, parameter.check, parameter.python)
        except (TypeError, ValueError):
            value = synthesize(parameter.check)
            check_value(value, parameter.check, parameter.python)
        call[parameter.python] = value
    if operation.body_schema is not None:
        body = operation.body_example
        try:
            if body is None or len(json.dumps(body)) > MAXIMUM_EXAMPLE_CHARACTERS:
                raise ValueError
            check_value(body, operation.body_check or {}, "body")
        except (TypeError, ValueError):
            body = synthesize(operation.body_check or {})
            check_value(body, operation.body_check or {}, "body")
        call["body"] = body
    return call


def _response_example(operation: Operation):
    if operation.response_kind != JSON_ANSWER:
        return None
    example = operation.response_example
    if example is None or len(json.dumps(example)) > MAXIMUM_EXAMPLE_CHARACTERS:
        example = synthesize(check_schema(operation.response_schema or {}, request=False), every_property=True) \
            if operation.response_schema else {"ok": True}
    return example if example is not None else {"ok": True}


def _breaks(schema: "dict | None", value) -> bool:
    """True when the client's own check refuses the value."""
    try:
        check_value(value, schema or {}, "body")
    except (TypeError, ValueError):
        return True
    return False


def test_source(operation: Operation, call: dict, example) -> str:
    # The server address may carry a path of its own (https://api.example.com/v1): it precedes the operation's.
    expected_path = urllib.parse.urlsplit(operation.base_url).path.rstrip("/") + operation.path
    for parameter in operation.parameters:
        if parameter.location == "path":
            value = call[parameter.python]
            text = ("true" if value else "false") if isinstance(value, bool) else str(value)
            expected_path = expected_path.replace("{" + parameter.wire + "}", urllib.parse.quote(text, safe=""))
    content_type = {JSON_ANSWER: "application/json", TEXT_ANSWER: "text/plain",
                    BINARY_ANSWER: "application/octet-stream", NO_ANSWER: ""}[operation.response_kind]
    payload = {JSON_ANSWER: "json.dumps(EXAMPLE).encode('utf-8')", TEXT_ANSWER: "b'example text'",
               BINARY_ANSWER: "b'\\x00\\x01'", NO_ANSWER: "b''"}[operation.response_kind]
    expected_answer = {JSON_ANSWER: "EXAMPLE", TEXT_ANSWER: "'example text'", BINARY_ANSWER: "b'\\x00\\x01'",
                       NO_ANSWER: "None"}[operation.response_kind]
    error_status = min(operation.errors) if operation.errors else 500
    required = [parameter for parameter in operation.parameters if parameter.required]
    auth = operation.auth
    tests = [f'''
    def test_the_request_follows_the_specification(self):
        mock = _Mock()
        answer = client.{operation.function}(**CALL, transport=mock)
        self.assertEqual(answer, {expected_answer})
        [request] = mock.requests
        self.assertEqual(request.get_method(), {operation.method!r})
        address = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(address.scheme, "https")
        self.assertEqual(urllib.parse.unquote(address.path), urllib.parse.unquote(EXPECTED_PATH))''']
    if auth and auth["placement"] == "header":
        tests[-1] += f'''
        self.assertEqual(request.headers.get({auth["name"].capitalize()!r}), {auth["prefix"] + "test-credential"!r})'''
    elif auth and auth["placement"] == "basic":
        encoded = auth["prefix"] + base64.b64encode(b"test-credential").decode("ascii")
        tests[-1] += f'''
        self.assertEqual(request.headers.get("Authorization"), {encoded!r})'''
    elif auth and auth["placement"] == "query":
        tests[-1] += f'''
        self.assertIn(({auth["name"]!r}, "test-credential"), urllib.parse.parse_qsl(address.query))'''
    elif auth and auth["placement"] == SIGV4_PLACEMENT:
        tests[-1] += f'''
        authorization = request.headers.get("Authorization")
        self.assertTrue(authorization.startswith("AWS4-HMAC-SHA256 Credential=test-credential/"), authorization)
        self.assertIn("/{auth["service"]}/aws4_request, SignedHeaders=", authorization)
        self.assertRegex(request.headers.get("X-amz-date"), "^[0-9]{{8}}T[0-9]{{6}}Z$")'''
    for name, value in operation.fixed_headers:
        tests[-1] += f'''
        self.assertEqual(request.headers.get({name.capitalize()!r}), {value!r})'''
    for parameter in required:
        if parameter.location == "query":
            tests[-1] += f'''
        self.assertIn({parameter.wire!r}, dict(urllib.parse.parse_qsl(address.query)))'''
    for name, value in operation.fixed_query:
        tests[-1] += f'''
        self.assertIn(({name!r}, {value!r}), urllib.parse.parse_qsl(address.query, keep_blank_values=True))'''
    if "body" in call:
        tests[-1] += '''
        self.assertEqual(json.loads(request.data.decode("utf-8")), CALL["body"])'''
    if required:
        first = required[0].python
        tests.append(f'''
    def test_known_wrong_a_missing_required_argument_sends_nothing(self):
        mock = _Mock()
        arguments = {{key: value for key, value in CALL.items() if key != {first!r}}}
        with self.assertRaises((TypeError, ValueError)):
            client.{operation.function}(**arguments, {first}=None, transport=mock)
        self.assertEqual(mock.requests, [])''')
        typed = next((parameter for parameter in required if parameter.check.get("type")
                      and "object" not in parameter.check["type"] and "array" not in parameter.check["type"]
                      and not ("string" in parameter.check["type"] and "integer" in parameter.check["type"])), None)
        if typed is not None:
            wrong = [1, 2] if "string" in typed.check["type"] else "wrong type"
            tests.append(f'''
    def test_known_wrong_a_wrong_type_sends_nothing(self):
        mock = _Mock()
        with self.assertRaises((TypeError, ValueError)):
            client.{operation.function}(**{{**CALL, {typed.python!r}: {wrong!r}}}, transport=mock)
        self.assertEqual(mock.requests, [])''')
    body_required = (operation.body_check or {}).get("required") or []
    if isinstance(call.get("body"), dict) and body_required and body_required[0] in call["body"] and \
            _breaks(operation.body_check, {key: value for key, value in call["body"].items() if key != body_required[0]}):
        # Written only when the body without that field really breaks the schema: a body whose other allowed
        # shapes (anyOf) do not require the field is no known-wrong case.
        tests.append(f'''
    def test_known_wrong_a_body_without_a_required_field_sends_nothing(self):
        mock = _Mock()
        body = {{key: value for key, value in CALL["body"].items() if key != {body_required[0]!r}}}
        with self.assertRaises((TypeError, ValueError)):
            client.{operation.function}(**{{**CALL, "body": body}}, transport=mock)
        self.assertEqual(mock.requests, [])''')
    tests.append(f'''
    def test_known_wrong_an_error_status_raises_with_its_meaning(self):
        mock = _Mock(status={error_status}, payload=b'{{"error": "example"}}', content_type="application/json")
        with self.assertRaises(client.ApiError) as caught:
            client.{operation.function}(**CALL, transport=mock)
        self.assertEqual(caught.exception.status, {error_status})''')
    if auth and not operation.auth_optional:
        tests.append(f'''
    def test_known_wrong_without_the_credential_nothing_is_sent(self):
        os.environ.pop({auth["variable"]!r}, None)
        mock = _Mock()
        with self.assertRaises(PermissionError):
            client.{operation.function}(**CALL, transport=mock)
        self.assertEqual(mock.requests, [])''')
    tests.append(f'''
    def test_known_wrong_an_address_that_is_not_https_sends_nothing(self):
        mock = _Mock()
        with self.assertRaises(ValueError):
            client.{operation.function}(**CALL, base_url="http://example.com", transport=mock)
        self.assertEqual(mock.requests, [])''')
    variables = ([auth["variable"]] + ([auth["secret_variable"]] if auth.get("secret_variable") else [])) if auth else []
    if auth and auth["placement"] == SIGV4_PLACEMENT:
        tests.append('''
    def test_the_signature_matches_the_aws_test_vector(self):
        headers = client._signature_headers(
            "GET", "https://example.amazonaws.com/", {}, b"", "AKIDEXAMPLE", "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
            "", "us-east-1", "service", "20150830T123600Z")
        self.assertEqual(headers["Authorization"],
                         "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, "
                         "SignedHeaders=host;x-amz-date, "
                         "Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31")''')
    class_name = "".join(part.capitalize() for part in operation.function.split("_") if part)[:60] + "Test"
    return (f'"""Offline tests of {operation.function}.\n\nA local mock of the API answers with the specification\'s '
            'example, and known-wrong calls\nmust send nothing or raise.\n"""\n'
            "from __future__ import annotations\n\nimport json\nimport os\nimport sys\nimport unittest\n"
            "import urllib.parse\n\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            f"import {operation.module} as client  # noqa: E402\n\n"
            f"CALL = {literal(call)}\nEXAMPLE = {literal(example)}\nEXPECTED_PATH = {expected_path!r}\n"
            f"VARIABLES = {variables!r}\n\n\n"
            "class _Mock:\n"
            '    """A local stand-in for the API: it records each request and answers with the example."""\n\n'
            f"    def __init__(self, status={operation.success_statuses[0]}, payload=None, content_type={content_type!r}):\n"
            f"        self.status, self.content_type = status, content_type\n"
            f"        self.payload = {payload} if payload is None else payload\n"
            "        self.requests = []\n\n"
            "    def __call__(self, request, timeout):\n"
            "        self.requests.append(request)\n"
            "        return self.status, self.content_type, self.payload\n\n\n"
            f"class {class_name}(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.saved = {name: os.environ.get(name) for name in VARIABLES + [client.BASE_URL_VARIABLE]}\n"
            "        os.environ.pop(client.BASE_URL_VARIABLE, None)\n"
            "        for name in VARIABLES:\n"
            '            os.environ[name] = "test-credential"\n\n'
            "    def tearDown(self):\n"
            "        for name, value in self.saved.items():\n"
            "            if value is None:\n"
            "                os.environ.pop(name, None)\n"
            "            else:\n"
            "                os.environ[name] = value\n"
            + "\n".join(tests) + "\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n")


def readme_source(operation: Operation, spec: dict, schema_bytes: int) -> str:
    rows = [f"| `{parameter.python}` | {parameter.location} `{parameter.wire}` | "
            f"{' or '.join(parameter.check.get('type', [])) or 'any'} | {'yes' if parameter.required else 'no'} |"
            for parameter in operation.parameters]
    table = "\n".join(["| Argument | Sent as | Type | Required |", "|---|---|---|---|", *rows]) if rows else \
        "The operation takes no parameters."
    auth = operation.auth
    if auth is None:
        credential = "The specification requires no credential for this operation."
    elif auth["placement"] == SIGV4_PLACEMENT:
        credential = (f"The client signs each request with AWS Signature Version 4 for the service "
                      f"`{auth['service']}` (security scheme `{auth['scheme']}`), reading the access key from "
                      f"`{auth['variable']}`, the secret key from `{auth['secret_variable']}` and, when it is set, "
                      f"the session token from `{auth['token_variable']}`. The region is `AWS_REGION` (or "
                      f"`AWS_DEFAULT_REGION`), else the specification's default `{operation.region_default or 'none'}`."
                      f" The keys are never written to a file"
                      + (". The credential is optional for this operation." if operation.auth_optional else "."))
    else:
        where = {"header": f"the `{auth['name']}` header" + (f" (value `{auth['prefix']}<credential>`)"
                                                             if auth["prefix"] else " (the value as set)"),
                 "basic": "the `Authorization` header as Basic credentials (set the variable to `user:password`)",
                 "query": f"the query parameter `{auth['name']}`"}[auth["placement"]]
        origin = ("the specification declares no security scheme, so Baltor's sources declaration names it"
                  if auth["scheme"] == DECLARED_SCHEME else f"security scheme `{auth['scheme']}`")
        credential = (f"The client reads the credential from the environment variable `{auth['variable']}` "
                      f"({origin}) and sends it in {where}. It is never written to a file"
                      + (". The credential is optional for this operation." if operation.auth_optional else "."))
    body = ""
    if operation.body_schema is not None:
        body = (f"\nThe JSON request body is {'required' if operation.body_required else 'optional'}; "
                "its schema is `input.body` in `schema.json`.\n")
    return f"""# {spec['title']}: {operation.summary or operation.operation_id}

`{operation.method} {operation.path}` (operation `{operation.operation_id}`{f', path key `{operation.path_key}`' if operation.path_key else ''}) as one Python function,
`{operation.function}` in `{operation.module}.py`. Baltor generated it and its tests from the
{spec['title']} OpenAPI specification {spec['version']} at `{spec['repository']}` commit
`{spec['commit']}`, file `{spec['path']}` (SHA-256 `{spec['sha256']}`), licensed {spec['licence']}.
{('The specification marks this operation as deprecated.' + chr(10)) if operation.deprecated else ''}
{operation.description or ''}

## Arguments

{table}
{body}
## Credential

{credential}

## What it does and refuses

- Sends one HTTPS request to `{operation.base_url}` (or the address in `{spec['base_url_variable']}`
  or `base_url`) and returns {('the parsed JSON answer' if operation.response_kind == JSON_ANSWER else 'the answer')}.
- Checks types, allowed values and required fields before sending, and raises `TypeError` or
  `ValueError` without sending anything when an argument breaks the specification.
- Raises `ApiError` with the status, the documented meaning and the body for any answer outside the
  documented successes ({', '.join(str(code) for code in operation.success_statuses)}).
- Refuses an address that is not HTTPS. The specification defines no pagination for this operation,
  so the client returns one page as the API answers it.

`schema.json` holds the input and output schemas ({schema_bytes} bytes), with the specification's
local references resolved. `test_{operation.module}.py` runs offline against a local mock:

```bash
python -m unittest test_{operation.module}
```
"""


# -- running the generated tests -----------------------------------------------------------------------------------
def run_tests(folder: Path, module: str) -> tuple:
    """(passed, tests run, tail of the output) of one package's generated tests, in this process, network closed."""
    saved_path, saved_modules = list(sys.path), set(sys.modules)
    saved_open, saved_bytecode = urllib.request.urlopen, sys.dont_write_bytecode
    # No compiled copy is written or reused: a rewritten file of the same size within the same second would
    # otherwise load its earlier compiled copy.
    sys.dont_write_bytecode = True

    def closed(*_arguments, **_options):
        raise RuntimeError("the network is closed while generated tests run")

    urllib.request.urlopen = closed
    stream = io.StringIO()
    try:
        name = f"test_{module}"
        specification = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
        loaded = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(loaded)
        suite = unittest.TestLoader().loadTestsFromModule(loaded)
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        return result.wasSuccessful() and result.testsRun > 0, result.testsRun, stream.getvalue()[-800:]
    except Exception as error:  # noqa: BLE001 - a package whose tests cannot even load is refused, never stored
        return False, 0, f"{type(error).__name__}: {error}"[:800]
    finally:
        urllib.request.urlopen = saved_open
        sys.dont_write_bytecode = saved_bytecode
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_modules:
            del sys.modules[name]


# -- reading a specification ---------------------------------------------------------------------------------------
def declared_beside(info: dict, licence, texts, where: str) -> "dict | None":
    """The specification's own licence declaration read beside its repository's licence: None when it declares
    none; refused when it declares a licence off the allowlist; the text of a second allowlisted licence."""
    declared = repository_declaration(info)
    if declared is None:
        return None
    spdx, written, address = declared
    if spdx is None or not licence_allowed(spdx):
        raise OperationRefused(LICENCE_NOT_ON_ALLOWLIST, f"{where} declares {written[:60]!r} {address[:80]}")
    return {"spdx": spdx, "declared": written[:120], "address": address[:300],
            "text": texts.text(spdx) if spdx != licence.spdx else None}


def read_specification(reader, source: dict, path: str, texts=None) -> dict:
    """The specification's bytes at the branch's head commit, proven by git blob identity, with its licence and
    its own declared licence."""
    repository = source["repository"]
    head = reader.github(f"repos/{repository}/commits/{source['branch']}")
    if head.status != 200:
        raise OperationRefused("specification_unreadable", f"{repository}: no head commit")
    commit = json.loads(head.body)["sha"]
    meta = reader.github(f"repos/{repository}/contents/{urllib.parse.quote(path)}?ref={commit}")
    if meta.status != 200:
        raise OperationRefused("specification_unreadable", f"{repository}/{path}: no file at {commit[:12]}")
    blob = json.loads(meta.body).get("sha")
    raw = reader.get(https_address(RAW_HOST, f"{repository}/{commit}/{urllib.parse.quote(path)}"))
    if raw.status != 200 or git_blob_identity(raw.body) != blob:
        raise OperationRefused("specification_unreadable", f"{repository}/{path}: bytes differ from blob {blob}")
    licence = repository_licence(reader, repository, commit)
    if not licence.allowed:
        reason = licence.refusal_reason(REFUSAL_REASONS[OPENAPI_OPERATIONS])
        raise OperationRefused(reason, f"{repository}: {licence.reason} {licence.github_spdx}")
    try:
        if path.endswith((".yaml", ".yml")):
            import yaml
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            document = yaml.load(raw.body.decode("utf-8"), Loader=loader)  # noqa: S506 - a safe loader
        else:
            document = json.loads(raw.body.decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - an unreadable specification is refused by name
        raise OperationRefused("specification_unreadable", f"{repository}/{path}: {type(error).__name__}") from None
    document = plain(document)  # YAML keys such as 200 become text, and dates become text
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3."):
        raise OperationRefused("specification_version_unsupported",
                               f"{repository}/{path}: {str(document.get('openapi') or document.get('swagger'))[:20]}")
    info = document.get("info") or {}
    declared = declared_beside(info, licence, texts or LicenceTexts(reader), f"{repository}/{path}")
    return {"document": document, "repository": repository, "commit": commit, "path": path, "blob": blob,
            "sha256": raw.sha256, "size_bytes": len(raw.body), "retrieved_at": raw.retrieved_at, "bytes": raw.body,
            "licence": licence, "declared_licence": declared,
            "title": re.sub(r"\s+", " ", str(info.get("title") or source["vendor"]))[:80],
            "version": str(info.get("version") or "")[:40],
            "base_url_variable": f"{source['vendor'].upper()}_BASE_URL"}


def generate(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: "dict | None" = None) -> tuple:
    """(built, refusals, facts, summary): every operation of every declared specification, tested and packaged."""
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/openapi_operations.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    texts = LicenceTexts(reader)
    for source in sources:
        taken = 0
        seen_modules = set()
        for path in source["paths"]:
            try:
                spec = read_specification(reader, source, path, texts)
            except OperationRefused as error:
                refused.append(refusal(OPENAPI_OPERATIONS, error.reason, f"{source['source_id']} {path}", error.detail))
                summary.append({"source_id": source["source_id"], "path": path, "refused": error.reason})
                continue
            facts[spec["sha256"]] = spec["bytes"]
            licence = spec["licence"]
            spec["licence"] = licence.spdx
            found, refusals = operations(spec["document"], source)
            refused += refusals
            kept = 0
            for operation in found:
                if taken >= source["maximum_operations"]:
                    break
                if operation.module in seen_modules:
                    refused.append(refusal(OPENAPI_OPERATIONS, "duplicate_operation",
                                           f"{source['source_id']} {operation.method} {operation.path}", operation.module))
                    continue
                try:
                    payload_bodies = _package(operation, spec, source, licence, generator, licence_text, generated_on,
                                              staging, repository_facts or {})
                except OperationRefused as error:
                    refused.append(refusal(OPENAPI_OPERATIONS, error.reason,
                                           f"{source['source_id']} {operation.method} {operation.path}", error.detail))
                    continue
                except SupplyRecordError as error:
                    reason = error.code if error.code in KEPT_CODES else GENERATED_TEST_FAILED
                    refused.append(refusal(OPENAPI_OPERATIONS, reason,
                                           f"{source['source_id']} {operation.method} {operation.path}", str(error)))
                    continue
                seen_modules.add(operation.module)
                built.append(payload_bodies)
                taken += 1
                kept += 1
            declared = spec.get("declared_licence") or {}
            summary.append({"source_id": source["source_id"], "path": path, "commit": spec["commit"],
                            "sha256": spec["sha256"], "licence": licence.spdx,
                            "declared_licence": declared.get("spdx"), "declared_as": declared.get("declared"),
                            "operations": len(found),
                            "refused_while_reading": len(refusals), "packaged": kept})
    return built, refused, facts, summary


_PROSE_KEYS = frozenset({"description", "example", "examples", "title", "summary", "externalDocs"})
#: Keys whose value maps names to schemas: every name is kept, even one spelled like a prose key.
_NAME_MAPS = frozenset({"properties", "patternProperties", "$defs", "definitions"})


def compact(value, depth_limit: "int | None", depth: int = 0, names: bool = False):
    """A schema without prose, examples or extension keys, and cut below depth_limit when one is given."""
    if isinstance(value, dict):
        if names:
            return {key: compact(item, depth_limit, depth + 1) for key, item in value.items()}
        if depth_limit is not None and depth >= depth_limit:
            kept = {key: value[key] for key in ("type", "format", "enum", "nullable") if key in value}
            return {**kept, "$comment": "deeper levels are in the specification"} if len(value) > len(kept) else kept
        return {key: compact(item, depth_limit, depth + 1, names=key in _NAME_MAPS) for key, item in value.items()
                if key not in _PROSE_KEYS and not str(key).startswith("x-")}
    if isinstance(value, list):
        return [compact(item, depth_limit, depth + 1) for item in value]
    return value


def _package(operation, spec, source, licence, generator, licence_text, generated_on, staging, repository_facts):
    try:
        call = _example_arguments(operation)
        example = _response_example(operation)
    except (TypeError, ValueError) as error:
        raise OperationRefused("example_not_constructible", str(error)[:200]) from None
    schema = {"operation": {"method": operation.method, "path": operation.path, "operation_id": operation.operation_id},
              "input": {"parameters": [{"name": parameter.wire, "in": parameter.location, "required": parameter.required,
                                        "schema": parameter.schema} for parameter in operation.parameters],
                        "body": operation.body_schema, "body_required": operation.body_required},
              "output": {"status": list(operation.success_statuses), "kind": operation.response_kind,
                         "schema": operation.response_schema},
              "errors": {str(code): meaning for code, meaning in sorted(operation.errors.items())}}
    schema_text = json.dumps(schema, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    # A schema above the review bound is written again without its prose and examples, then with fewer levels,
    # before the operation is refused; the full schema stays in the pinned specification.
    for depth in (None, 5, 3):
        if len(schema_text.encode("utf-8")) <= MAXIMUM_REVIEW_FILE_BYTES:
            break
        schema = {**compact(schema, depth), "$comment": "descriptions and examples are omitted to stay within the "
                  "review bound; the pinned specification holds them"}
        schema_text = json.dumps(schema, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    client = client_source(operation, spec)
    tests = test_source(operation, call, example)
    folder = staging / operation.module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{operation.module}.py").write_text(client, encoding="utf-8")
    (folder / f"test_{operation.module}.py").write_text(tests, encoding="utf-8")
    passed, count, output = run_tests(folder, operation.module)
    shutil.rmtree(folder, ignore_errors=True)  # the package keeps the files; the staging copy is not needed
    if not passed:
        raise OperationRefused(GENERATED_TEST_FAILED, output[-300:])
    readme = readme_source(operation, spec, len(schema_text.encode()))
    upstream = licence.text
    licence_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(f"{operation.module}.py", client.encode(), "executable_tool"),
             PackageFile(f"test_{operation.module}.py", tests.encode(), "executable_tool"),
             PackageFile("schema.json", schema_text.encode(), "other"),
             PackageFile("README.md", readme.encode(), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, upstream, "other", LICENCE_TEXT,
                         {"url": licence_address, "sha256": licence.sha256})]
    second = (spec.get("declared_licence") or {}).get("text")
    if second is not None:
        # The specification declares an allowlisted licence other than its repository's: both travel.
        files.append(PackageFile(SPECIFICATION_LICENCE_NAME, second.text, "other", LICENCE_TEXT,
                                 {"url": github_blob_address(second.repository, second.commit, second.path),
                                  "sha256": second.sha256}))
    expression = " AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx] +
                                            ([second.spdx] if second is not None else [])))
    spec_url = spec.get("url") or https_address(
        RAW_HOST, f"{spec['repository']}/{spec['commit']}/{urllib.parse.quote(spec['path'])}")
    facts = [fact_source(spec_url, spec["retrieved_at"], spec["sha256"], spec["size_bytes"], "specification",
                         spdx=licence.spdx, basis=spec.get("licence_basis", "github_licence_interface_and_text_agree"),
                         evidence_sha256=licence.sha256),
             fact_source(licence_address, spec["retrieved_at"], licence.sha256, len(upstream), "licence_text",
                         spdx=licence.spdx, basis=spec.get("licence_text_basis", "licence_file_at_the_pinned_commit"))]
    if second is not None:
        facts.append(fact_source(github_blob_address(second.repository, second.commit, second.path),
                                 spec["retrieved_at"], second.sha256, len(second.text), "licence_text",
                                 spdx=second.spdx, basis=DECLARED_TEXT_BASIS))
    facts += list(spec.get("extra_facts") or ())
    effects = [("network", "sends_one_https_request_to_the_api")]
    credentials = []
    if operation.auth:
        effects.append(("reads_secret", f"reads_{operation.auth['variable']}_from_the_environment"))
        credentials.append(operation.auth["variable"])
        for other in ("secret_variable", "token_variable"):
            if operation.auth.get(other):
                credentials.append(operation.auth[other])
    name = f"{source['vendor']}-{operation.function.replace('_', '-')}"[:90]
    identity = f"{spec['repository']}:{spec['path']}:{operation.method} {operation.path_key or operation.path}"
    stars = ((repository_facts.get(spec["repository"].lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=OPENAPI_OPERATIONS, identity=identity, key=upstream_key(OPENAPI_OPERATIONS, identity), kind="code_module",
        native_format=NATIVE_FORMAT, form="api_operation", name=name,
        description=(f"{spec['title']} API: {operation.summary or operation.operation_id} "
                     f"({operation.method} {operation.path}), one tested Python function."),
        files=files, licence_expression=expression,
        provenance=provenance(spec.get("origin", "github_repository"), spec["repository"], spec["path"], spec["commit"],
                              facts, generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=effects, credentials=credentials,
        tests={"files": [f"test_{operation.module}.py"], "command": f"python -m unittest test_{operation.module}",
               "result": "passed", "tests_run": count, "network": False},
        repository={"name": spec["repository"], "stars": stars, "specification": spec["path"],
                    "specification_version": spec["version"], "operation": f"{operation.method} {operation.path}"},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def counts(refusals) -> dict:
    return dict(Counter(row["reason"] for row in refusals).most_common())

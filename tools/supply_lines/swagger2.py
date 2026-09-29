"""Swagger 2 documents in the OpenAPI 3 shape the API operation generator reads.

Host, base path and schemes become servers; a body parameter becomes a JSON
request body; form parameters become a form body whose schema names each field,
its type and whether it is required; response schemas become JSON content; basic
security becomes an HTTP scheme. References stay local pointers into the same
document (definitions keep their place, so #/definitions/... still resolves).
"""
from __future__ import annotations

from .openapi_operations import METHODS

BODY_IN, FORM_IN = "body", "formData"
JSON_MEDIA = "application/json"
FORM_MEDIA = "application/x-www-form-urlencoded"


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
                # Each form field keeps its name, type and whether it is required; a file field makes the body
                # multipart, which the generator refuses by name.
                fields = {row["name"]: _parameter_schema(row) for row in form if row.get("name")}
                required = [row["name"] for row in form if row.get("required") and row.get("name")]
                media = next((value for value in consumes if "form" in str(value).lower()), FORM_MEDIA)
                schema = {"type": "object", "properties": fields, **({"required": required} if required else {})}
                # Swagger 2 joins a list field with commas unless its collection format is "multi" (one key per
                # item): the OpenAPI 3 form style, exploded only for "multi".
                encoding = {row["name"]: {"style": "form", "explode": row.get("collectionFormat") == "multi"}
                            for row in form if row.get("name") and row.get("type") == "array"}
                entry = {"schema": schema, **({"encoding": encoding} if encoding else {})}
                operation["requestBody"] = {"required": bool(required), "content": {media: entry}}
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


def is_swagger2(document) -> bool:
    return isinstance(document, dict) and str(document.get("swagger", "")).startswith("2")


__all__ = ["BODY_IN", "FORM_IN", "FORM_MEDIA", "JSON_MEDIA", "is_swagger2", "swagger2_to_openapi3"]

"""A JavaScript module with TypeScript declarations beside each generated Python API client, tested as well.

```text
one API operation package
├── <module>.py and test_<module>.py        the Python client and its offline tests (unittest)
├── <module>.mjs                             the same operation as an ES module for Node.js 18 or later
├── <module>.d.ts                            its TypeScript declarations (arguments, options, ApiError)
└── <module>.test.mjs                        its offline tests (node --test): the same example call, the same
                                             expected path, form pairs and answer, and the same known-wrong
                                             calls, with fetch closed so no test reaches the network
```

The JavaScript module and its tests are kept only when its tests pass; a
package whose JavaScript tests fail keeps its Python client alone, and the run
counts it. The machine's Node.js (a distribution build) cannot run TypeScript
source, so the module is JavaScript with a declaration file: TypeScript code
imports it with its types, and plain Node.js runs its tests with no compiler
and no dependency.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .openapi_operations import (
    BINARY_ANSWER, FORM_MEDIA_TYPE, JSON_ANSWER, JSON_MEDIA_TYPE, NO_ANSWER, SELF_HOSTED_TEST_ROOT, SIGV4_PLACEMENT,
    TEXT_ANSWER, USER_AGENT, api_title, form_pairs)

NODE = "node"
#: Test files one node process runs at once; each file runs in its own child process.
TEST_CONCURRENCY = 4
#: Seconds one batch of JavaScript tests may take before it is stopped and counted as failed.
BATCH_TIMEOUT_SECONDS = 1800
JAVASCRIPT_SUFFIX, DECLARATION_SUFFIX, TEST_SUFFIX = ".mjs", ".d.ts", ".test.mjs"
_RESERVED_WORDS = frozenset(
    "break case catch class const continue debugger default delete do else enum export extends false finally for "
    "function if import in instanceof new null return super switch this throw true try typeof var void while with "
    "yield let static implements interface package private protected public await arguments eval".split())
_TAP_RESULT = re.compile(r"^(not )?ok \d+ - (.+?)(?: # .*)?$")


def js(value) -> str:
    """A JavaScript literal of a JSON value (line and paragraph separators escaped, as JSON allows)."""
    return json.dumps(value, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def comment(value) -> str:
    """Text safe inside a block comment: one line, and never the comment's end."""
    return re.sub(r"\s+", " ", str(value)).replace("*/", "* /")[:200]


def function_name(python: str) -> str:
    """The camelCase export of a snake_case Python function name; a reserved word gains a suffix."""
    head, *rest = [part for part in python.split("_") if part] or ["operation"]
    name = head + "".join(part[:1].upper() + part[1:] for part in rest)
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name):
        name = "operation" + re.sub(r"[^A-Za-z0-9_$]", "", name.title())
    return name + "Operation" if name in _RESERVED_WORDS else name


def type_name(python: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in python.split("_") if part)[:80] or "Operation"


#: The TypeScript type of each JSON Schema instance type, built from the checked schema (an array from its items).
_TS_TYPES = {
    "integer": lambda check, depth: "number", "number": lambda check, depth: "number",
    "string": lambda check, depth: "string", "boolean": lambda check, depth: "boolean",
    "null": lambda check, depth: "null", "object": lambda check, depth: "Record<string, unknown>",
    "array": lambda check, depth: f"Array<{ts_type(check.get('items') or {}, depth + 1) if depth < 3 else 'unknown'}>"}


def ts_type(check: dict, depth: int = 0) -> str:
    """A TypeScript type for a checked schema: its kinds, string enumerations as literals, arrays of their items."""
    if not check:
        return "unknown"
    enum = check.get("enum")
    if isinstance(enum, list) and 0 < len(enum) <= 30:
        return " | ".join(js(value) for value in enum)
    kinds = [_TS_TYPES[kind](check, depth) for kind in check.get("type") or [] if kind in _TS_TYPES]
    return " | ".join(dict.fromkeys(kinds)) or "unknown"


RUNTIME = r'''
export class ApiError extends Error {
  constructor(status, meaning, body) {
    super(`${OPERATION.method} ${OPERATION.path} answered ${status}: ${meaning}`);
    this.name = "ApiError";
    this.status = status;
    this.meaning = meaning;
    this.body = body;
  }
}

export class CredentialMissingError extends Error {
  constructor(message) {
    super(message);
    this.name = "CredentialMissingError";
  }
}

function isKind(value, kind) {
  switch (kind) {
    case "integer": return Number.isInteger(value);
    case "number": return typeof value === "number" && Number.isFinite(value);
    case "boolean": return typeof value === "boolean";
    case "string": return typeof value === "string";
    case "array": return Array.isArray(value);
    case "object": return value !== null && typeof value === "object" && !Array.isArray(value);
    case "null": return value === null;
    default: return true;
  }
}

function has(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function check(value, schema, name) {
  if (!schema || Object.keys(schema).length === 0) return;
  if (schema.anyOf) {
    for (const branch of schema.anyOf) {
      try {
        check(value, branch, name);
        return;
      } catch (error) {
        if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      }
    }
    throw new RangeError(`${name} matches none of the allowed shapes`);
  }
  const kinds = schema.type || [];
  if (kinds.length && !kinds.some((kind) => isKind(value, kind))) {
    throw new TypeError(`${name} must be ${kinds.join(" or ")}`);
  }
  if (schema.enum && !schema.enum.some((allowed) => allowed === value)) {
    throw new RangeError(`${name} must be one of ${JSON.stringify(schema.enum.slice(0, 20))}`);
  }
  if (isKind(value, "object")) {
    const missing = (schema.required || []).filter((key) => !has(value, key));
    if (missing.length) throw new RangeError(`${name} lacks ${JSON.stringify(missing)}`);
    for (const [key, part] of Object.entries(schema.properties || {})) {
      if (has(value, key) && value[key] !== null && value[key] !== undefined) check(value[key], part, `${name}.${key}`);
    }
  } else if (Array.isArray(value) && schema.items) {
    value.forEach((item, index) => check(item, schema.items, `${name}[${index}]`));
  }
}

function text(value) {
  return typeof value === "boolean" ? (value ? "true" : "false") : String(value);
}

function region() {
  return process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || REGION_DEFAULT;
}

async function send(request, timeout) {
  const answer = await fetch(request.url, { method: request.method, headers: request.headers,
                                            body: request.body, signal: AbortSignal.timeout(timeout * 1000) });
  return { status: answer.status, contentType: answer.headers.get("content-type") || "",
           body: new Uint8Array(await answer.arrayBuffer()) };
}

function decode(contentType, payload) {
  if (!payload || payload.length === 0) return null;
  const type = (contentType || "").toLowerCase();
  if (type.includes("json")) return JSON.parse(new TextDecoder().decode(payload));
  if (type.startsWith("text/")) return new TextDecoder().decode(payload);
  return payload;
}

function deep(prefix, value) {
  if (isKind(value, "object")) {
    return Object.entries(value).filter(([, item]) => item !== null && item !== undefined)
      .flatMap(([key, item]) => deep(`${prefix}[${key}]`, item));
  }
  if (Array.isArray(value)) return value.flatMap((item, index) => deep(`${prefix}[${index}]`, item));
  return [[prefix, text(value)]];
}

function formPairs(body) {
  const pairs = [];
  for (const [name, value] of Object.entries(body)) {
    if (value === null || value === undefined) continue;
    const [style, explode] = BODY_ENCODING[name] || ["form", true];
    if (style === "deepObject" && (isKind(value, "object") || Array.isArray(value))) {
      pairs.push(...deep(name, value));
    } else if (isKind(value, "object")) {
      const items = Object.entries(value).filter(([, item]) => item !== null && item !== undefined);
      if (explode) pairs.push(...items.map(([key, item]) => [String(key), text(item)]));
      else pairs.push([name, items.map(([key, item]) => `${key},${text(item)}`).join(",")]);
    } else if (Array.isArray(value)) {
      if (explode) pairs.push(...value.map((item) => [name, text(item)]));
      else pairs.push([name, value.map((item) => text(item)).join(",")]);
    } else {
      pairs.push([name, text(value)]);
    }
  }
  return pairs;
}

function encodeRfc3986(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (character) =>
    "%" + character.charCodeAt(0).toString(16).toUpperCase());
}

export function signatureHeaders(method, url, headers, payload, accessKey, secretKey, token, region, service, amzDate) {
  const parts = new URL(url);
  const signed = {};
  for (const [name, value] of Object.entries(headers)) signed[name.toLowerCase()] = String(value).trim().split(/\s+/).join(" ");
  signed.host = parts.host;
  signed["x-amz-date"] = amzDate;
  if (token) signed["x-amz-security-token"] = token;
  const names = Object.keys(signed).sort();
  const pairs = [...new URLSearchParams(parts.search)].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 :
    a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
  const canonicalQuery = pairs.map(([key, value]) => encodeRfc3986(key) + "=" + encodeRfc3986(value)).join("&");
  const canonicalPath = (parts.pathname || "/").split("/").map((segment) => encodeRfc3986(segment)).join("/");
  const canonical = [method, canonicalPath, canonicalQuery, names.map((name) => name + ":" + signed[name] + "\n").join(""),
                     names.join(";"), createHash("sha256").update(payload || "").digest("hex")].join("\n");
  const date = amzDate.slice(0, 8);
  const scope = date + "/" + region + "/" + service + "/aws4_request";
  const toSign = ["AWS4-HMAC-SHA256", amzDate, scope, createHash("sha256").update(canonical).digest("hex")].join("\n");
  let key = Buffer.from("AWS4" + secretKey, "utf8");
  for (const part of [date, region, service, "aws4_request"]) key = createHmac("sha256", key).update(part).digest();
  const signature = createHmac("sha256", key).update(toSign).digest("hex");
  const added = { "X-Amz-Date": amzDate, Authorization: "AWS4-HMAC-SHA256 Credential=" + accessKey + "/" + scope +
                  ", SignedHeaders=" + names.join(";") + ", Signature=" + signature };
  if (token) added["X-Amz-Security-Token"] = token;
  return added;
}

async function call(args, body, options) {
  let path = OPERATION.path;
  const query = FIXED_QUERY.map(([key, value]) => [key, value]);
  const headers = { Accept: "application/json", "User-Agent": USER_AGENT, ...Object.fromEntries(FIXED_HEADERS) };
  for (const [python, wire, location] of PARAMETERS) {
    const value = args[python];
    if (value === null || value === undefined) continue;
    if (location === "path") {
      let encoded = encodeURIComponent(text(value));
      if (RESERVED_PATH.includes(wire)) encoded = encoded.replace(/%2F/gi, "/");
      path = path.replace("{" + wire + "}", encoded);
    } else if (location === "query") {
      for (const item of Array.isArray(value) ? value : [value]) query.push([wire, text(item)]);
    } else {
      headers[wire] = text(value);
    }
  }
  const root = (options.baseUrl || process.env[BASE_URL_VARIABLE] ||
                (BASE_URL_TEMPLATE ? BASE_URL_TEMPLATE.replace("{region}", region()) : BASE_URL)).replace(/\/+$/, "");
  if (!root.startsWith("https://")) throw new RangeError("the API address must be an HTTPS address");
  if (AUTH && AUTH.placement !== "aws_sigv4") {
    const credential = process.env[AUTH.variable] || "";
    if (credential) {
      if (AUTH.placement === "header") headers[AUTH.name] = AUTH.prefix + credential;
      else if (AUTH.placement === "basic") headers[AUTH.name] = AUTH.prefix + Buffer.from(credential, "utf8").toString("base64");
      else if (AUTH.placement === "query") query.push([AUTH.name, credential]);
    } else if (!AUTH_OPTIONAL) {
      throw new CredentialMissingError("set the environment variable " + AUTH.variable + " to call " + OPERATION.operation_id);
    }
  }
  let data = null;
  if (body !== null && body !== undefined) {
    data = BODY_MEDIA === "application/x-www-form-urlencoded" ? new URLSearchParams(formPairs(body)).toString()
      : JSON.stringify(body);
    headers["Content-Type"] = BODY_MEDIA;
  }
  const url = root + path + (query.length ? "?" + new URLSearchParams(query).toString() : "");
  if (AUTH && AUTH.placement === "aws_sigv4") {
    const accessKey = process.env[AUTH.variable] || "";
    const secretKey = process.env[AUTH.secret_variable] || "";
    if (!accessKey || !secretKey) {
      throw new CredentialMissingError("set " + AUTH.variable + " and " + AUTH.secret_variable + " to call " + OPERATION.operation_id);
    }
    const amzDate = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    Object.assign(headers, signatureHeaders(OPERATION.method, url, headers, data, accessKey, secretKey,
                                            process.env[AUTH.token_variable] || "", region(), AUTH.service, amzDate));
  }
  const answer = await (options.transport || send)({ url, method: OPERATION.method, headers, body: data },
                                                    options.timeout ?? 30);
  let decoded;
  try {
    decoded = decode(answer.contentType, answer.body);
  } catch {
    decoded = answer.body;
  }
  if (!SUCCESS_STATUSES.includes(answer.status)) {
    throw new ApiError(answer.status, ERRORS[answer.status] ?? "not a documented success", decoded);
  }
  return decoded;
}
'''


def module_source(operation, spec: dict) -> str:
    """The ES module of one operation: the same checks, address rules, credential and body as the Python client."""
    name = function_name(operation.function)
    parameters = [[parameter.python, parameter.wire, parameter.location, parameter.required, parameter.check]
                  for parameter in operation.parameters]
    header = (f"/**\n * {comment(api_title(spec['title']))}: {comment(operation.summary or operation.operation_id)}\n *\n"
              f" * {operation.method} {comment(operation.path)}, operation {comment(operation.operation_id)} of "
              f"{comment(spec['title'])} {comment(spec['version'])}.\n * Baltor generated this module from the "
              f"specification at {spec['repository']}@{spec['commit'][:12]} ({comment(spec['path'])});\n * see "
              f"README.md, schema.json and {operation.module}{DECLARATION_SUFFIX}. No model wrote it.\n */\n")
    imports = 'import { createHash, createHmac } from "node:crypto";\nimport { Buffer } from "node:buffer";\n'
    constants = [
        f"export const OPERATION = {js({'method': operation.method, 'path': operation.path, 'operation_id': operation.operation_id})};",
        f"export const BASE_URL = {js(operation.base_url)};",
        f"export const BASE_URL_VARIABLE = {js(spec['base_url_variable'])};",
        f"const BASE_URL_TEMPLATE = {js(operation.base_url_template)};",
        f"const REGION_DEFAULT = {js(operation.region_default)};",
        f"const FIXED_QUERY = {js([list(pair) for pair in operation.fixed_query])};",
        f"const FIXED_HEADERS = {js([list(pair) for pair in operation.fixed_headers])};",
        f"const BODY_MEDIA = {js(operation.body_media)};",
        f"const BODY_ENCODING = {js({field: [style, explode] for field, style, explode in operation.body_encoding})};",
        f"const RESERVED_PATH = {js([parameter.wire for parameter in operation.parameters if parameter.reserved])};",
        f"const USER_AGENT = {js(USER_AGENT)};",
        f"const AUTH = {js(operation.auth)};",
        f"const AUTH_OPTIONAL = {js(operation.auth_optional)};",
        "/** [argument name, wire name, location, required, checked schema] of every parameter. */",
        f"const PARAMETERS = {js(parameters)};",
        f"const BODY_REQUIRED = {js(operation.body_required)};",
        f"const BODY_SCHEMA = {js(operation.body_check)};",
        f"const SUCCESS_STATUSES = {js(list(operation.success_statuses))};",
        f"const ERRORS = {js({str(code): meaning for code, meaning in sorted(operation.errors.items())})};"]
    has_body = operation.body_schema is not None
    function = (f"\n/**\n * {operation.method} {comment(operation.path)} (operation {comment(operation.operation_id)}).\n"
                f" * Rejects with TypeError or RangeError before any request when an argument breaks the specification"
                f"{', with CredentialMissingError when the credential is not set' if operation.auth and not operation.auth_optional else ''},"
                f"\n * and with ApiError for any answer outside the documented successes.\n */\n"
                f"export async function {name}(args = {{}}, options = {{}}) {{\n"
                "  for (const [python, , , required, schema] of PARAMETERS) {\n"
                "    const value = args[python];\n"
                "    if (value === null || value === undefined) {\n"
                "      if (required) throw new RangeError(`${python} is required`);\n"
                "      continue;\n"
                "    }\n"
                "    check(value, schema, python);\n"
                "  }\n"
                + ("  if ((args.body === null || args.body === undefined) && BODY_REQUIRED) throw new RangeError(\"body is required\");\n"
                   "  if (args.body !== null && args.body !== undefined) check(args.body, BODY_SCHEMA, \"body\");\n"
                   if has_body else "")
                + f"  return call(args, {'args.body' if has_body else 'null'}, options);\n}}\n")
    return header + imports + "\n" + "\n".join(constants) + "\n" + RUNTIME + function


def declaration_source(operation) -> str:
    """The TypeScript declarations of one operation's module."""
    name, kind = function_name(operation.function), type_name(operation.function)
    lines = [f"/** {operation.method} {comment(operation.path)} (operation {comment(operation.operation_id)}). */",
             f"export interface {kind}Arguments {{"]
    for parameter in operation.parameters:
        optional = "" if parameter.required else "?"
        lines.append(f"  /** {parameter.location} parameter {comment(parameter.wire)} */")
        lines.append(f"  {js(parameter.python)}{optional}: {ts_type(parameter.check)};")
    if operation.body_schema is not None:
        kind_text = "the form fields of the request body" if operation.body_media == FORM_MEDIA_TYPE else "the JSON request body"
        lines.append(f"  /** {kind_text}; its schema is input.body in schema.json */")
        lines.append(f"  body{'' if operation.body_required else '?'}: {ts_type(operation.body_check or {})};")
    lines.append("}")
    required = any(parameter.required for parameter in operation.parameters) or (
        operation.body_schema is not None and operation.body_required)
    answer = {JSON_ANSWER: "unknown", TEXT_ANSWER: "string", BINARY_ANSWER: "Uint8Array", NO_ANSWER: "null"}[
        operation.response_kind]
    lines += [
        "",
        "export interface TransportRequest { url: string; method: string; headers: Record<string, string>; body: string | null; }",
        "export interface TransportAnswer { status: number; contentType: string; body: Uint8Array; }",
        "export type Transport = (request: TransportRequest, timeout: number) => Promise<TransportAnswer>;",
        "export interface CallOptions {",
        "  /** the API's HTTPS address; the environment variable named by BASE_URL_VARIABLE does too */",
        "  baseUrl?: string;",
        "  /** seconds to wait for the answer (30 when not given) */",
        "  timeout?: number;",
        "  /** a stand-in for the network, for tests */",
        "  transport?: Transport;",
        "}",
        "export declare class ApiError extends Error { readonly status: number; readonly meaning: string; readonly body: unknown; }",
        "export declare class CredentialMissingError extends Error {}",
        "export declare const OPERATION: { readonly method: string; readonly path: string; readonly operation_id: string };",
        "export declare const BASE_URL: string;",
        "export declare const BASE_URL_VARIABLE: string;",
        "export declare function signatureHeaders(method: string, url: string, headers: Record<string, string>, "
        "payload: string | null, accessKey: string, secretKey: string, token: string, region: string, service: string, "
        "amzDate: string): Record<string, string>;",
        f"export declare function {name}(args{'' if required else '?'}: {kind}Arguments, options?: CallOptions): "
        f"Promise<{answer}>;",
        ""]
    return "\n".join(lines)


def test_source(operation, call: dict, example, expected_path: str) -> tuple:
    """(the node:test file of one operation, the number of tests it holds)."""
    name = function_name(operation.function)
    auth = operation.auth
    form = operation.body_media == FORM_MEDIA_TYPE
    self_hosted = not operation.base_url and not operation.base_url_template
    content_type = {JSON_ANSWER: "application/json", TEXT_ANSWER: "text/plain",
                    BINARY_ANSWER: "application/octet-stream", NO_ANSWER: ""}[operation.response_kind]
    payload = {JSON_ANSWER: "new TextEncoder().encode(JSON.stringify(EXAMPLE))",
               TEXT_ANSWER: 'new TextEncoder().encode("example text")', BINARY_ANSWER: "new Uint8Array([0, 1])",
               NO_ANSWER: "new Uint8Array([])"}[operation.response_kind]
    expected = {JSON_ANSWER: "EXAMPLE", TEXT_ANSWER: '"example text"', BINARY_ANSWER: "new Uint8Array([0, 1])",
                NO_ANSWER: "null"}[operation.response_kind]
    variables = ([auth["variable"]] + ([auth["secret_variable"]] if auth.get("secret_variable") else [])) if auth else []
    checks = [f"  assert.deepEqual(answer, {expected});",
              "  const [request] = transport.requests;",
              f"  assert.equal(request.method, {js(operation.method)});",
              "  const address = new URL(request.url);",
              '  assert.equal(address.protocol, "https:");',
              "  assert.equal(decodeURIComponent(address.pathname), decodeURIComponent(EXPECTED_PATH));"]
    if any(parameter.reserved for parameter in operation.parameters):
        checks.append("  assert.equal(address.pathname, EXPECTED_PATH);")
    if auth and auth["placement"] == "header":
        checks.append(f"  assert.equal(request.headers[{js(auth['name'])}], {js(auth['prefix'] + 'test-credential')});")
    elif auth and auth["placement"] == "basic":
        import base64
        encoded = auth["prefix"] + base64.b64encode(b"test-credential").decode("ascii")
        checks.append(f"  assert.equal(request.headers.Authorization, {js(encoded)});")
    elif auth and auth["placement"] == "query":
        checks.append(f"  assert.ok([...address.searchParams].some(([key, value]) => key === {js(auth['name'])} && "
                      "value === \"test-credential\"));")
    elif auth and auth["placement"] == SIGV4_PLACEMENT:
        checks += ['  assert.match(request.headers.Authorization, /^AWS4-HMAC-SHA256 Credential=test-credential\\//);',
                   f"  assert.ok(request.headers.Authorization.includes({js('/' + auth['service'] + '/aws4_request, SignedHeaders=')}));",
                   '  assert.match(request.headers["X-Amz-Date"], /^[0-9]{8}T[0-9]{6}Z$/);']
    for header_name, value in operation.fixed_headers:
        checks.append(f"  assert.equal(request.headers[{js(header_name)}], {js(value)});")
    for parameter in operation.parameters:
        if parameter.required and parameter.location == "query":
            checks.append(f"  assert.ok(address.searchParams.has({js(parameter.wire)}));")
    for key, value in operation.fixed_query:
        checks.append(f"  assert.ok([...address.searchParams].some(([key, value]) => key === {js(key)} && value === "
                      f"{js(value)}));")
    if "body" in call and form:
        checks += [f'  assert.equal(request.headers["Content-Type"], {js(FORM_MEDIA_TYPE)});',
                   "  assert.deepEqual([...new URLSearchParams(request.body)], EXPECTED_FORM);"]
    elif "body" in call:
        checks.append('  assert.deepEqual(JSON.parse(request.body), CALL.body);')
        if operation.body_media != JSON_MEDIA_TYPE:
            checks.append(f'  assert.equal(request.headers["Content-Type"], {js(operation.body_media)});')
    tests = ["test(\"the request follows the specification\", async () => {",
             "  const transport = mock();",
             f"  const answer = await client.{name}(CALL, {{ transport }});", *checks, "});"]
    count = 1
    required = [parameter for parameter in operation.parameters if parameter.required]
    if required:
        first = required[0].python
        tests += ["", "test(\"known wrong: a missing required argument sends nothing\", async () => {",
                  "  const transport = mock();",
                  f"  await assert.rejects(client.{name}({{ ...CALL, {js(first)}: undefined }}, {{ transport }}));",
                  "  assert.deepEqual(transport.requests, []);", "});"]
        count += 1
        typed = next((parameter for parameter in required if parameter.check.get("type")
                      and "object" not in parameter.check["type"] and "array" not in parameter.check["type"]
                      and not ("string" in parameter.check["type"] and "integer" in parameter.check["type"])), None)
        if typed is not None:
            wrong = [1, 2] if "string" in typed.check["type"] else "wrong type"
            tests += ["", "test(\"known wrong: a wrong type sends nothing\", async () => {",
                      "  const transport = mock();",
                      f"  await assert.rejects(client.{name}({{ ...CALL, {js(typed.python)}: {js(wrong)} }}, "
                      "{ transport }), TypeError);",
                      "  assert.deepEqual(transport.requests, []);", "});"]
            count += 1
    tests += ["", "test(\"known wrong: an error status rejects with its meaning\", async () => {",
              f"  const transport = mock({min(operation.errors) if operation.errors else 500}, "
              "new TextEncoder().encode('{\"error\": \"example\"}'), \"application/json\");",
              f"  await assert.rejects(client.{name}(CALL, {{ transport }}), (error) => error instanceof client.ApiError "
              f"&& error.status === {min(operation.errors) if operation.errors else 500});", "});"]
    count += 1
    if auth and not operation.auth_optional:
        tests += ["", "test(\"known wrong: without the credential nothing is sent\", async () => {",
                  f"  delete process.env[{js(auth['variable'])}];",
                  "  const transport = mock();",
                  f"  await assert.rejects(client.{name}(CALL, {{ transport }}), client.CredentialMissingError);",
                  "  assert.deepEqual(transport.requests, []);", "});"]
        count += 1
    if self_hosted:
        tests += ["", "test(\"known wrong: without an address nothing is sent\", async () => {",
                  "  delete process.env[client.BASE_URL_VARIABLE];",
                  "  const transport = mock();",
                  f"  await assert.rejects(client.{name}(CALL, {{ transport }}), RangeError);",
                  "  assert.deepEqual(transport.requests, []);", "});"]
        count += 1
    tests += ["", "test(\"known wrong: an address that is not HTTPS sends nothing\", async () => {",
              "  const transport = mock();",
              f"  await assert.rejects(client.{name}(CALL, {{ transport, baseUrl: \"http://example.com\" }}), RangeError);",
              "  assert.deepEqual(transport.requests, []);", "});"]
    count += 1
    if auth and auth["placement"] == SIGV4_PLACEMENT:
        tests += ["", "test(\"the signature matches the AWS test vector\", () => {",
                  '  const headers = client.signatureHeaders("GET", "https://example.amazonaws.com/", {}, "", "AKIDEXAMPLE",',
                  '    "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY", "", "us-east-1", "service", "20150830T123600Z");',
                  "  assert.equal(headers.Authorization, \"AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/"
                  "aws4_request, \" +",
                  "    \"SignedHeaders=host;x-amz-date, Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31\");",
                  "});"]
        count += 1
    constants = [f"const CALL = {js(call)};", f"const EXAMPLE = {js(example)};",
                 f"const EXPECTED_PATH = {js(expected_path)};",
                 *([f"const EXPECTED_FORM = {js([list(pair) for pair in form_pairs(call['body'], operation.body_encoding)])};"]
                   if form and "body" in call else []),
                 *([f"const ROOT = {js(SELF_HOSTED_TEST_ROOT)};"] if self_hosted else []),
                 f"const VARIABLES = {js(variables)};"]
    source = ("// Offline tests of " + name + ": a local stand-in for the API answers with the specification's example,\n"
              "// and known-wrong calls must reject and send nothing. fetch is closed, so no test reaches the network.\n"
              'import { describe, test, beforeEach, afterEach } from "node:test";\n'
              'import assert from "node:assert/strict";\n'
              f'import * as client from "./{operation.module}{JAVASCRIPT_SUFFIX}";\n\n'
              'globalThis.fetch = async () => { throw new Error("the network is closed while generated tests run"); };\n\n'
              + "\n".join(constants) + "\n"
              "const saved = {};\n\n"
              f"function mock(status = {operation.success_statuses[0]}, payload = null, contentType = {js(content_type)}) {{\n"
              "  const requests = [];\n"
              "  const transport = async (request, timeout) => {\n"
              "    requests.push(request);\n"
              f"    return {{ status, contentType, body: payload ?? {payload} }};\n"
              "  };\n"
              "  transport.requests = requests;\n"
              "  return transport;\n"
              "}\n\n"
              # One suite named after the file: a batch run reports each file's result on its own line.
              + f"describe({js(operation.module + TEST_SUFFIX)}, () => {{\n"
              "  beforeEach(() => {\n"
              "    for (const name of [...VARIABLES, client.BASE_URL_VARIABLE]) saved[name] = process.env[name];\n"
              + ("    process.env[client.BASE_URL_VARIABLE] = ROOT;\n" if self_hosted else
                 "    delete process.env[client.BASE_URL_VARIABLE];\n")
              + "    for (const name of VARIABLES) process.env[name] = \"test-credential\";\n"
              "  });\n\n"
              "  afterEach(() => {\n"
              "    for (const [name, value] of Object.entries(saved)) {\n"
              "      if (value === undefined) delete process.env[name];\n"
              "      else process.env[name] = value;\n"
              "    }\n"
              "  });\n\n"
              + "\n".join(("  " + line) if line else line for line in "\n".join(tests).split("\n")) + "\n});\n")
    return source, count


def node_available() -> bool:
    return shutil.which(NODE) is not None


def _run(folder: Path, test_files: list, flags: list) -> dict:
    """Suite name to passed, for one node --test run."""
    environment = {"PATH": os.environ.get("PATH", ""), "HOME": str(folder), "NODE_OPTIONS": "", "NO_COLOR": "1"}
    try:
        finished = subprocess.run([NODE, "--test", "--test-reporter=tap", *flags, *test_files], cwd=folder,
                                  capture_output=True, text=True, timeout=BATCH_TIMEOUT_SECONDS, env=environment,
                                  check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    results = {}
    for line in finished.stdout.splitlines():
        match = _TAP_RESULT.match(line)  # top-level lines only: one suite per test file, named after it
        if match:
            name = match.group(2).strip()
            results[name] = results.get(name, True) and match.group(1) is None
    return results


def run_tests(folder: Path, test_files: list) -> dict:
    """Test file (relative to folder) to passed. One node process runs the whole batch, one file after another
    (the files restore what they change in the environment); a file the batch run does not report is run again in
    its own process, so one broken file cannot fail the others."""
    if not test_files:
        return {}
    results = _run(folder, test_files, ["--experimental-test-isolation=none", "--test-concurrency=1"])
    missing = [path for path in test_files if path.rsplit("/", 1)[-1] not in results]
    if missing:
        results.update(_run(folder, missing, [f"--test-concurrency={TEST_CONCURRENCY}"]))
    return {path: results.get(path.rsplit("/", 1)[-1], False) for path in test_files}


__all__ = ["DECLARATION_SUFFIX", "JAVASCRIPT_SUFFIX", "TEST_SUFFIX", "declaration_source", "function_name",
           "module_source", "node_available", "run_tests", "test_source", "ts_type"]

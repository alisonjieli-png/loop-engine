"""The code of a generated API tool server and of its tests: fixed templates around one table of JSON data.

```text
server.py (one per specification file; Python 3.10 or later, standard library only)
├── the module docstring, SPECIFICATION, SERVER, BASE_URL_VARIABLE and INSTRUCTIONS of the file
├── TABLE: JSON data parsed at import (addresses, credentials, error meanings and the tools, each tool with
│   its MCP definition and how it is called); tools.json holds the same tools without the call details
├── the helpers of the generated API client's template, copied verbatim from openapi_operations at
│   generation time (_is, _check, _text, _send, _decode, _deep, _signature_headers; _form_pairs and _region
│   with their per-operation constant made a parameter)
└── SERVER_RUNTIME, the same for every server: one request function with the client's rules, tools/call,
    tools/list by protocol version, initialize with version negotiation, ping, JSON-RPC errors, a line loop
    over standard input and output with tool calls on a few threads, logging to standard error only

test_server.py (one per server, the same code around one DATA table)
├── a shim that runs server.py with every HTTP request sent to a local mock, the address in a header
├── a mock HTTP server on the loopback interface, and a session that drives the server over its pipes
└── the protocol, the tool list, every tool's request, one read and one body in detail, known-wrong calls
```

Every byte of the code is here or in the client's template; the line (api_tool_servers.py) writes only data.
"""
from __future__ import annotations

import ast
import inspect
import json

#: The keywords a tool's input schema may use: the client's own argument checks (openapi_operations.check_schema),
#: a description per argument, and a closed object at the top. The generated tests hold every schema to them.
SCHEMA_KEYWORDS = ("type", "properties", "required", "items", "anyOf", "enum", "format", "minimum", "description",
                   "additionalProperties")
SCHEMA_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")
#: The client template's helpers the server copies unchanged, by the template constant that holds them.
VERBATIM_HELPERS = (("RUNTIME", ("_is", "_check", "_text", "_send", "_decode")), ("FORM_ENCODER", ("_deep",)),
                    ("SIGNER", ("_signature_headers",)))
#: Helpers whose per-operation constant becomes a parameter, with each exact replacement made.
ADAPTED_HELPERS = (("FORM_ENCODER", "_form_pairs", (("def _form_pairs(body):", "def _form_pairs(body, encoding):"),
                                                    ("BODY_ENCODING.get(name", "encoding.get(name"))),
                   ("RUNTIME", "_region", (("def _region():", "def _region(default):"),
                                           ("or REGION_DEFAULT", "or default"))))


def _functions(text: str) -> dict:
    tree = ast.parse(text)
    return {node.name: ast.get_source_segment(text, node) for node in tree.body if isinstance(node, ast.FunctionDef)}


def client_helpers() -> str:
    """The generated client's own helpers, copied from its template: the server checks arguments, writes values,
    sends, decodes, encodes forms and signs exactly as the client does."""
    from . import openapi_operations as client
    parts = []
    for constant, names in VERBATIM_HELPERS:
        found = _functions(getattr(client, constant))
        parts += [found[name] for name in names]
    for constant, name, replacements in ADAPTED_HELPERS:
        source = _functions(getattr(client, constant))[name]
        for old, new in replacements:
            if source.count(old) != 1:
                raise ValueError(f"the client template's {name} changed: {old!r} is not there once")
            source = source.replace(old, new)
        parts.append(source)
    return "\n\n\n".join(parts)


def render_json(value, indent: int = 0, width: int = 110, lead: int = 0) -> str:
    """Strict JSON (every character outside ASCII escaped) that keeps a value on one line when the line fits the
    width and otherwise puts one member per line, one more space in per level, so no line is long but a long
    string's."""
    flat = json.dumps(value, ensure_ascii=True, separators=(", ", ": "))
    if not isinstance(value, (dict, list)) or not value or indent + lead + len(flat) <= width:
        return flat
    inner = " " * (indent + 1)
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            name = json.dumps(str(key), ensure_ascii=True) + ": "
            rows.append(inner + name + render_json(item, indent + 1, width, len(name)))
        return "{\n" + ",\n".join(rows) + "\n" + " " * indent + "}"
    rows = [inner + render_json(item, indent + 1, width) for item in value]
    return "[\n" + ",\n".join(rows) + "\n" + " " * indent + "]"


def json_constant(name: str, value) -> str:
    """A module constant parsed from JSON text at import. The text is a raw string: JSON escapes every quote
    inside its strings, so three quotes never meet inside it, and it never ends with a backslash."""
    return f'{name} = json.loads(r"""\n{render_json(value)}\n""")\n'


def _schema_problems(schema, where="inputSchema"):
    """What makes a tool's input schema invalid: only the keywords this server writes, each well formed, and at
    the top an object that names its required arguments and refuses any other."""
    if not isinstance(schema, dict):
        return [f"{where} is not an object"]
    problems = [f"{where} uses {key}" for key in schema if key not in SCHEMA_KEYWORDS]
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not isinstance(kinds, list) or ("type" in schema and not kinds) or any(kind not in SCHEMA_TYPES
                                                                              for kind in kinds):
        problems.append(f"{where}.type")
    for key in ("description", "format"):
        if key in schema and not isinstance(schema[key], str):
            problems.append(f"{where}.{key}")
    if "minimum" in schema and (isinstance(schema["minimum"], bool) or not isinstance(schema["minimum"], (int, float))):
        problems.append(f"{where}.minimum")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        problems.append(f"{where}.enum")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        problems.append(f"{where}.additionalProperties")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        problems.append(f"{where}.properties")
        properties = {}
    for name, part in properties.items():
        problems += _schema_problems(part, f"{where}.{name}")
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required) or \
            len(set(required)) != len(required):
        problems.append(f"{where}.required")
        required = []
    if "items" in schema:
        problems += _schema_problems(schema["items"], f"{where}[]")
    if "anyOf" in schema:
        if not isinstance(schema["anyOf"], list) or not schema["anyOf"]:
            problems.append(f"{where}.anyOf")
        else:
            for index, part in enumerate(schema["anyOf"]):
                problems += _schema_problems(part, f"{where}.anyOf[{index}]")
    if where == "inputSchema" and (schema.get("type") != "object" or schema.get("additionalProperties") is not False
                                   or not set(required) <= set(properties)):
        problems.append("inputSchema is not a closed object that names its required arguments")
    return problems


SERVER_IMPORTS = """from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

"""

#: The code every server shares after its data: the client's helpers go where the marker line stands.
SERVER_RUNTIME = r'''
ADDRESSES, AUTHS, MEANINGS, TOOLS = TABLE["addresses"], TABLE["auths"], TABLE["meanings"], TABLE["tools"]
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
#: The protocol versions this server speaks, newest first. A client that asks for another is answered with the
#: newest, and decides itself whether it can use it.
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
USER_AGENT = "baltor-api-tool-server/1"
#: Seconds one request to the API may take before the call ends as an error.
TIMEOUT_SECONDS = 30.0
#: The longest text one tool result carries; a longer answer is cut and says how long it was.
MAXIMUM_TEXT = 400000
#: Tool calls served at the same time; a further call waits for a free slot.
CONCURRENT_CALLS = 4
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = (
    -32700, -32600, -32601, -32602, -32603)
FORM_MEDIA_TYPE = "application/x-www-form-urlencoded"
#: The placement of an AWS Signature Version 4 credential: it is never sent as it is; it signs each request.
SIGNED = "aws_sigv4"
#: The HTTP methods behind each behaviour annotation: a tool's annotations follow from its method alone.
READ_METHODS, DESTRUCTIVE_METHODS = ("GET", "HEAD", "OPTIONS"), ("DELETE", "PUT", "PATCH")
IDEMPOTENT_METHODS = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")
#: What a call record leaves out when it holds nothing there (the table stays small enough to review).
CALL_DEFAULTS = {"reserved": [], "fixed_query": [], "fixed_headers": [], "body": None, "errors": {}, "auth": None,
                 "auth_optional": False, "address": 0}
#: The negotiated version, the tool calls in flight and those of them the client cancelled (by JSON of the id).
STATE = {"version": PROTOCOL_VERSIONS[0], "running": set(), "cancelled": set()}
_OUTPUT, _CANCELLING = threading.Lock(), threading.Lock()


class ApiError(Exception):
    """An answer outside the documented successes, with its status, its documented meaning and its body."""

    def __init__(self, call, status, meaning, body):
        super().__init__(f"{call['method']} {call['path']} answered {status}: {meaning}")
        self.status, self.meaning, self.body = status, meaning, body


class InvalidParams(ValueError):
    """Parameters a method cannot take, answered with the JSON-RPC error -32602."""


# CLIENT HELPERS


def _root(call):
    """The API's address for one call, by the generated client's rule: the variable BASE_URL_VARIABLE when it is
    set, else the specification's server with its region filled in, and an HTTPS address only."""
    place = ADDRESSES[call["address"]]
    root = os.environ.get(BASE_URL_VARIABLE) or (
        place["template"].format(region=_region(place["region"])) if place["template"] else place["base_url"])
    root = root.rstrip("/")
    if not root:
        listed = f" (it lists {place['hint']})" if place["hint"] else ""
        raise ValueError(f"the specification names no public HTTPS address{listed}; set {BASE_URL_VARIABLE} to the "
                         "API's HTTPS address")
    if not root.startswith("https://"):
        raise ValueError("the API address must be an HTTPS address")
    return root


def _request(call, arguments):
    """Send one call with the generated client's rules and return (status, content type, answer) of a documented
    success; raise ApiError for another status, and PermissionError or ValueError before anything is sent."""
    call = {**CALL_DEFAULTS, **call}
    path, query = call["path"], [tuple(item) for item in call["fixed_query"]]
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT, **dict(call["fixed_headers"])}
    for name, wire, location in call["parameters"]:
        value = arguments.get(name)
        if value is None:
            continue
        if location == "path":
            safe = "/" if wire in call["reserved"] else ""
            path = path.replace("{" + wire + "}", urllib.parse.quote(_text(value), safe=safe))
        elif location == "query":
            items = value if isinstance(value, (list, tuple)) else [value]
            query += [(wire, _text(item)) for item in items]
        else:
            headers[wire] = _text(value)
    root = _root(call)
    auth = AUTHS[call["auth"]] if call["auth"] is not None else None
    if auth is not None and auth["placement"] != SIGNED:
        credential = os.environ.get(auth["variable"], "")
        if credential:
            if auth["placement"] == "query":
                query.append((auth["name"], credential))
            elif auth["placement"] == "basic":
                headers[auth["name"]] = auth["prefix"] + base64.b64encode(credential.encode("utf-8")).decode("ascii")
            else:
                headers[auth["name"]] = auth["prefix"] + credential
        elif not call["auth_optional"]:
            raise PermissionError(f"set the environment variable {auth['variable']} to call {call['operation_id']}")
    data, body = None, arguments.get("body")
    if call["body"] is not None and body is not None:
        if call["body"]["media"] == FORM_MEDIA_TYPE:
            data = urllib.parse.urlencode(_form_pairs(body, call["body"]["encoding"])).encode("ascii")
        else:
            data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = call["body"]["media"]
    url = root + path + ("?" + urllib.parse.urlencode(query) if query else "")
    if auth is not None and auth["placement"] == SIGNED:
        access_key, secret_key = os.environ.get(auth["variable"], ""), os.environ.get(auth["secret_variable"], "")
        if not access_key or not secret_key:
            raise PermissionError(f"set {auth['variable']} and {auth['secret_variable']} to call "
                                  f"{call['operation_id']}")
        headers.update(_signature_headers(call["method"], url, headers, data, access_key, secret_key,
                                          os.environ.get(auth["token_variable"], ""),
                                          _region(ADDRESSES[call["address"]]["region"]), auth["service"],
                                          time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())))
    request = urllib.request.Request(url, data=data, method=call["method"], headers=headers)
    status, content_type, payload = _send(request, TIMEOUT_SECONDS)
    _log(f"{call['method']} {call['path']} answered {status}")
    try:
        answer = _decode(content_type, payload)
    except (ValueError, UnicodeDecodeError):
        answer = payload
    if status not in call["success"]:
        meaning = call["errors"].get(str(status))
        raise ApiError(call, status, MEANINGS[meaning] if meaning is not None else "not a documented success", answer)
    return status, content_type, answer


def _shown(status, content_type, answer):
    """The text of a successful answer: JSON as JSON, text as it is, other bytes in base64 with their type."""
    if answer is None or answer == b"":
        return f"The API answered {status} with no body."
    if isinstance(answer, bytes):
        return (f"The API answered {status} with {len(answer)} bytes of {content_type or 'an unnamed type'}, in "
                "base64:\n" + base64.b64encode(answer).decode("ascii"))
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=False)


def _result(text, error=False):
    """A tool result holding one text; a text longer than MAXIMUM_TEXT is cut and says so."""
    if len(text) > MAXIMUM_TEXT:
        text = text[:MAXIMUM_TEXT] + f"\n[cut: the answer holds {len(text)} characters]"
    return {"content": [{"type": "text", "text": text}], "isError": error}


def call_tool(name, arguments):
    """One tool call: its arguments checked as the generated client checks them, then one request.

    Raises InvalidParams for an unknown tool or for arguments the tool cannot take. Every other failure (no
    credential or address, an error status, no answer in time) is a tool result marked as an error."""
    tool = TOOLS_BY_NAME.get(name) if isinstance(name, str) else None
    if tool is None:
        raise InvalidParams(f"Unknown tool: {name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise InvalidParams("arguments must be an object")
    properties = tool["inputSchema"]["properties"]
    unknown = sorted(key for key in arguments if key not in properties)
    if unknown:
        raise InvalidParams(f"{name} takes no argument {unknown[0]}; its arguments are {sorted(properties)}")
    for key in tool["inputSchema"].get("required", ()):
        if arguments.get(key) is None:
            raise InvalidParams(f"{key} is required")
    for key, value in arguments.items():
        if value is not None:
            try:
                _check(value, properties[key], key)
            except (TypeError, ValueError) as error:
                raise InvalidParams(str(error)) from None
    call = tool["call"]
    try:
        status, content_type, answer = _request(call, arguments)
    except ApiError as error:
        body = error.body
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
        elif body is not None and not isinstance(body, str):
            body = json.dumps(body, ensure_ascii=False)
        _log(f"tools/call {name}: {error}")
        return _result(str(error) + ("\n" + body[:4000] if body else ""), error=True)
    except (PermissionError, ValueError) as error:  # no credential, or no HTTPS address: nothing was sent
        _log(f"tools/call {name}: {error}")
        return _result(f"{call['method']} {call['path']} was not sent: {error}", error=True)
    except Exception as error:  # noqa: BLE001 - no answer in time, a refused connection, a broken answer
        _log(f"tools/call {name}: {type(error).__name__}: {error}")
        return _result(f"{call['method']} {call['path']} was not answered: {type(error).__name__}: {error}",
                       error=True)
    return _result(_shown(status, content_type, answer))


def _annotations(method):
    """The behaviour hints of the Model Context Protocol, from the HTTP method alone."""
    return {"readOnlyHint": method in READ_METHODS, "destructiveHint": method in DESTRUCTIVE_METHODS,
            "idempotentHint": method in IDEMPOTENT_METHODS, "openWorldHint": True}


def list_tools(version):
    """The tools as the negotiated protocol version describes them: a title from 2025-06-18, the behaviour
    annotations from 2025-03-26 (where the title sits among them), neither in 2024-11-05."""
    age = PROTOCOL_VERSIONS.index(version) if version in PROTOCOL_VERSIONS else 0
    listed = []
    for tool in TOOLS:
        entry = {"name": tool["name"]}
        if age == 0:
            entry["title"] = tool["title"]
        entry["description"], entry["inputSchema"] = tool["description"], tool["inputSchema"]
        if age == 0:
            entry["annotations"] = _annotations(tool["call"]["method"])
        elif age == 1:
            entry["annotations"] = {"title": tool["title"], **_annotations(tool["call"]["method"])}
        listed.append(entry)
    return listed


def initialize(params):
    """The answer to initialize: the client's protocol version when this server speaks it, else the newest."""
    if not isinstance(params, dict) or not isinstance(params.get("protocolVersion"), str):
        raise InvalidParams("initialize names the client's protocolVersion")
    asked = params["protocolVersion"]
    version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
    STATE["version"] = version
    info = {"name": SERVER["name"], "version": SERVER["version"]}
    if version == PROTOCOL_VERSIONS[0]:
        info["title"] = SERVER["title"]
    return {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": info,
            "instructions": INSTRUCTIONS}


def _failure(identity, code, message):
    return {"jsonrpc": "2.0", "id": identity, "error": {"code": code, "message": message}}


def handle(message):
    """The answer to one JSON-RPC message: a result, an error, or None for a notification or a response."""
    if not isinstance(message, dict):
        return _failure(None, INVALID_REQUEST, "Invalid Request: a message is a JSON object")
    named = "id" in message
    identity = message.get("id")
    if named and (isinstance(identity, bool) or not isinstance(identity, (str, int))):
        return _failure(None, INVALID_REQUEST, "Invalid Request: an id is a string or an integer")
    if message.get("jsonrpc") != "2.0":
        return _failure(identity, INVALID_REQUEST, 'Invalid Request: jsonrpc must be "2.0"')
    method = message.get("method")
    if method is None and ("result" in message or "error" in message):
        return None  # an answer to a request; this server sends none
    if not isinstance(method, str):
        return _failure(identity, INVALID_REQUEST, "Invalid Request: method must be a string")
    params = message.get("params", {})
    if not isinstance(params, (dict, list)):
        return _failure(identity, INVALID_REQUEST, "Invalid Request: params must be an object or an array")
    if not named:
        if method == "notifications/cancelled" and isinstance(params, dict):
            key = json.dumps(params.get("requestId"))
            with _CANCELLING:
                if key in STATE["running"]:  # a call already answered, or never made, is not remembered
                    STATE["cancelled"].add(key)
        return None  # a notification is never answered
    try:
        if isinstance(params, list):
            raise InvalidParams(f"{method} takes named parameters")
        if method == "initialize":
            result = initialize(params)
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": list_tools(STATE["version"])}
        elif method == "tools/call":
            result = call_tool(params.get("name"), params.get("arguments"))
        else:
            return _failure(identity, METHOD_NOT_FOUND, f"Method not found: {method}")
    except InvalidParams as error:
        return _failure(identity, INVALID_PARAMS, f"Invalid params: {error}")
    except Exception as error:  # noqa: BLE001 - one message never stops the server
        _log(f"{method} failed: {type(error).__name__}: {error}")
        return _failure(identity, INTERNAL_ERROR, f"Internal error: {type(error).__name__}")
    return {"jsonrpc": "2.0", "id": identity, "result": result}


def _log(text):
    """One line on standard error, the only place this server writes anything but protocol messages."""
    try:
        sys.stderr.write(f"[{SERVER['name']}] {text}\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def _write(message):
    """One JSON-RPC message on its own line of standard output, ASCII only."""
    data = (json.dumps(message, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
    with _OUTPUT:
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except (OSError, ValueError):
            pass  # the client has gone; its input ends next


def _serve_call(message, slots):
    """Answer one tools/call on its own thread, unless the client cancelled it meanwhile."""
    key = json.dumps(message.get("id"))
    try:
        answer = handle(message)
        with _CANCELLING:
            cancelled = key in STATE["cancelled"]
            STATE["cancelled"].discard(key)
            STATE["running"].discard(key)
        if answer is not None and not cancelled:
            _write(answer)
    finally:
        slots.release()


def main():
    """Serve the tools over standard input and output, one JSON-RPC message per line, until the input ends."""
    _log(f"serving {len(TOOLS)} tools of {SPECIFICATION['title']} {SPECIFICATION['version']}")
    slots, workers = threading.BoundedSemaphore(CONCURRENT_CALLS), []
    try:
        for line in sys.stdin.buffer:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                _write(_failure(None, PARSE_ERROR, "Parse error: each line holds one JSON-RPC message"))
                continue
            if isinstance(message, list):
                answers = [answer for answer in map(handle, message) if answer is not None]
                if not message:
                    _write(_failure(None, INVALID_REQUEST, "Invalid Request: an empty batch"))
                elif answers:
                    _write(answers)
            elif isinstance(message, dict) and message.get("method") == "tools/call" and "id" in message:
                slots.acquire()
                with _CANCELLING:
                    STATE["running"].add(json.dumps(message.get("id")))
                worker = threading.Thread(target=_serve_call, args=(message, slots), daemon=True)
                worker.start()
                workers = [thread for thread in workers if thread.is_alive()] + [worker]
            else:
                answer = handle(message)
                if answer is not None:
                    _write(answer)
    except KeyboardInterrupt:
        pass
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
'''

#: The marker in SERVER_RUNTIME that the client's helpers replace.
HELPERS_MARKER = "# CLIENT HELPERS\n"


def server_source(docstring: str, constants: str, table: dict) -> str:
    """server.py: its docstring, its constants (Python literals), its TABLE and the shared runtime."""
    runtime = SERVER_RUNTIME
    if runtime.count(HELPERS_MARKER) != 1:
        raise ValueError("the server runtime holds the helpers marker once")
    return ('"""' + docstring + '\n"""\n' + SERVER_IMPORTS + constants + json_constant("TABLE", table)
            + runtime.replace(HELPERS_MARKER, client_helpers() + "\n"))


TEST_HEAD = r'''"""Offline tests of server.py: the protocol, the tool list, every tool's request and known-wrong calls.

Each test starts server.py as a subprocess speaking the Model Context Protocol over standard input and output.
A shim in that subprocess sends every HTTP request to a local mock instead of the API, with the address the
server chose in a header, so nothing leaves the machine; the mock records each request and answers as told.
"""
from __future__ import annotations

import http.server
import json
import os
import queue
import re
import subprocess
import sys
import threading
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "server.py")
'''

TEST_BODY = r'''
(SERVER_NAME, BASE_URL_VARIABLE, USER_AGENT, VARIABLES, CLEARED, ROOT, ANSWER, METHODS, CALLS, READ, WRITE, WRONG,
 CREDENTIALED, UNADDRESSED) = (DATA[key] for key in (
    "server_name", "base_url_variable", "user_agent", "variables", "cleared", "root", "answer", "methods", "calls",
    "read", "write", "wrong", "credentialed", "unaddressed"))
VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}")
READ_METHODS, DESTRUCTIVE_METHODS = ("GET", "HEAD", "OPTIONS"), ("DELETE", "PUT", "PATCH")
IDEMPOTENT_METHODS = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")
#: Runs in the server's process before server.py: every request goes to the local mock instead, with the address
#: the server chose in a header, so a test sees that address and nothing leaves the machine.
SHIM = "\n".join([
    "import os, runpy, sys, urllib.parse, urllib.request",
    "_mock = os.environ['TEST_MOCK_ADDRESS']",
    "_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))",
    "def _redirect(request, timeout=None, **options):",
    "    original = request.full_url",
    "    parts = urllib.parse.urlsplit(original)",
    "    request.full_url = _mock + parts.path + ('?' + parts.query if parts.query else '')",
    "    request.add_header('X-original-url', original)",
    "    return _opener.open(request, timeout=timeout)",
    "urllib.request.urlopen = _redirect",
    "sys.argv = sys.argv[1:]",
    "runpy.run_path(sys.argv[0], run_name='__main__')"])


# SCHEMA PROBLEMS


def _answer(status, kind):
    """(status, content type, bytes) the mock answers with, by the kind of answer the operation documents."""
    return {"json": (status, "application/json", json.dumps(ANSWER).encode("utf-8")),
            "text": (status, "text/plain", b"example text"),
            "binary": (status, "application/octet-stream", b"\x00\x01"),
            "empty": (status, "", b"")}[kind]


class _Handler(http.server.BaseHTTPRequestHandler):
    def _respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.server.requests.append({"method": self.command, "path": self.path, "body": body,
                                     "headers": {name.lower(): value for name, value in self.headers.items()}})
        status, content_type, payload = self.server.answer
        if self.command == "HEAD" or status in (204, 304):
            payload = b""
        self.send_response(status)
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    do_GET = do_PUT = do_POST = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _respond

    def log_message(self, *arguments):
        """Quiet: each request is recorded instead."""


class _Mock(http.server.ThreadingHTTPServer):
    """A stand-in for the API on the loopback interface: it records each request and answers as told."""

    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests, self.answer = [], _answer(200, "json")
        threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    @property
    def address(self):
        return "http://127.0.0.1:%d" % self.server_address[1]

    def stop(self):
        self.shutdown()
        self.server_close()


class _Session:
    """server.py in a subprocess behind the shim, its standard output read line by line on a thread."""

    def __init__(self, mock, *, credentials=True, root=ROOT, environment=None):
        env = {name: value for name, value in os.environ.items()
               if name not in CLEARED and not name.lower().endswith("_proxy")}
        env["TEST_MOCK_ADDRESS"] = mock.address
        if credentials:
            env.update({name: "test-credential" for name in VARIABLES})
        if root:
            env[BASE_URL_VARIABLE] = root
        env.update(environment or {})
        self.process = subprocess.Popen([sys.executable, "-E", "-s", "-B", "-c", SHIM, SERVER], cwd=HERE, env=env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.lines, self.log, self.counter = queue.Queue(), [], 0
        self.readers = [threading.Thread(target=self._read, daemon=True),
                        threading.Thread(target=self._drain, daemon=True)]
        for reader in self.readers:
            reader.start()

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _drain(self):
        for line in self.process.stderr:
            self.log.append(line.decode("utf-8", "replace"))

    def send(self, message):
        data = message if isinstance(message, bytes) else json.dumps(message).encode("utf-8")
        self.process.stdin.write(data + b"\n")
        self.process.stdin.flush()

    def receive(self, timeout=30):
        """The next message on standard output, which carries nothing but JSON-RPC 2.0 messages."""
        line = self.lines.get(timeout=timeout)
        if line is None:
            raise AssertionError("the server stopped: " + "".join(self.log)[-1500:])
        message = json.loads(line)
        for item in message if isinstance(message, list) else [message]:
            if not isinstance(item, dict) or item.get("jsonrpc") != "2.0":
                raise AssertionError(f"not a JSON-RPC 2.0 message: {line[:200]!r}")
        return message

    def request(self, method, params=None):
        self.counter += 1
        message = {"jsonrpc": "2.0", "id": self.counter, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        answer = self.receive()
        if answer.get("id") != self.counter:
            raise AssertionError(f"the answer names id {answer.get('id')!r}, the request {self.counter}")
        return answer

    def initialize(self, version=VERSIONS[0]):
        answer = self.request("initialize", {"protocolVersion": version, "capabilities": {},
                                             "clientInfo": {"name": "test_server", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return answer

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        """End the server's input, wait for it to stop and close its pipes; its exit status."""
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            status = self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            status = self.process.wait()
        for reader in self.readers:
            reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        return status


def _address(original):
    parts = urllib.parse.urlsplit(original)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")), \
        sorted(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))


def _problem(answer, sent, method, address, query):
    """What a tool call did wrong, or None: its answer, and the method, address and query it sent."""
    if "error" in answer:
        return f"error {answer['error']}"
    if answer["result"].get("isError"):
        return "tool error: " + answer["result"]["content"][0]["text"][:300]
    if len(sent) != 1:
        return f"{len(sent)} requests sent"
    if sent[0]["method"] != method:
        return f"method {sent[0]['method']}"
    found, items = _address(sent[0]["headers"].get("x-original-url", ""))
    if found != address:
        return f"address {found}"
    if items != sorted(tuple(item) for item in query):
        return f"query {items}"
    return None


def check_calls(calls=None):
    """Call every tool once against the mock: {tool: what went wrong} for each call that did not send the request
    its specification describes. A server that stops is started again for the next call."""
    mock, failures, session = _Mock(), {}, None
    try:
        for name, arguments, method, address, query, status, kind in CALLS if calls is None else calls:
            if session is None:
                session = _Session(mock)
                session.initialize()
            del mock.requests[:]
            mock.answer = _answer(status, kind)
            try:
                problem = _problem(session.call(name, arguments), list(mock.requests), method, address, query)
            except (AssertionError, ValueError, OSError, queue.Empty) as error:
                problem = f"{type(error).__name__}: {error}"[:300]
                session.close()
                session = None
            if problem:
                failures[name] = problem
        return failures
    finally:
        if session is not None:
            session.close()
        mock.stop()


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.mock = _Mock()
        self.addCleanup(self.mock.stop)

    def session(self, **options):
        session = _Session(self.mock, **options)
        self.addCleanup(session.close)
        return session

    def test_initialize_answers_the_clients_version_or_the_newest(self):
        session = self.session()
        for asked, answered in [(version, version) for version in VERSIONS] + [("1999-01-01", VERSIONS[0])]:
            result = session.initialize(asked)["result"]
            self.assertEqual(result["protocolVersion"], answered)
            self.assertEqual(result["capabilities"], {"tools": {"listChanged": False}})
            self.assertEqual(result["serverInfo"]["name"], SERVER_NAME)
        self.assertEqual(session.request("ping")["result"], {})

    def test_the_tools_are_tools_json_with_valid_schemas_and_annotations(self):
        session = self.session()
        session.initialize()
        tools = session.request("tools/list")["result"]["tools"]
        with open(os.path.join(HERE, "tools.json"), encoding="utf-8") as stream:
            self.assertEqual(tools, json.load(stream)["tools"])
        names = [tool["name"] for tool in tools]
        self.assertEqual(names, [name for name, _method in METHODS])
        self.assertEqual(len(set(names)), len(names))
        methods = dict(METHODS)
        for tool in tools:
            self.assertTrue(NAME.fullmatch(tool["name"]), tool["name"])
            self.assertTrue(tool["title"] and tool["description"], tool["name"])
            self.assertEqual(_schema_problems(tool["inputSchema"]), [], tool["name"])
            method = methods[tool["name"]]
            self.assertEqual(tool["annotations"], {"readOnlyHint": method in READ_METHODS,
                                                   "destructiveHint": method in DESTRUCTIVE_METHODS,
                                                   "idempotentHint": method in IDEMPOTENT_METHODS,
                                                   "openWorldHint": True}, tool["name"])
        session.initialize(VERSIONS[1])
        older = session.request("tools/list")["result"]["tools"]
        self.assertEqual(older, [{"name": tool["name"], "description": tool["description"],
                                  "inputSchema": tool["inputSchema"],
                                  "annotations": {"title": tool["title"], **tool["annotations"]}} for tool in tools])
        session.initialize(VERSIONS[2])
        oldest = session.request("tools/list")["result"]["tools"]
        self.assertEqual(oldest, [{"name": tool["name"], "description": tool["description"],
                                   "inputSchema": tool["inputSchema"]} for tool in tools])

    def test_every_tool_sends_the_request_its_specification_describes(self):
        self.assertEqual(check_calls(), {})

    @unittest.skipIf(READ is None, "the specification defines no read operation")
    def test_a_read_sends_its_parameters_and_credential_and_returns_the_answer(self):
        self.mock.answer = _answer(READ["status"], READ["kind"])
        session = self.session()
        session.initialize()
        result = session.call(READ["tool"], READ["arguments"])["result"]
        self.assertFalse(result["isError"], result)
        [sent] = self.mock.requests
        self.assertIsNone(_problem({"result": result}, [sent], READ["method"], READ["address"], READ["query"]))
        for name, value in READ["headers"].items():
            self.assertEqual(sent["headers"].get(name), value, name)
        if READ["signed"]:
            self.assertTrue(sent["headers"]["authorization"].startswith(
                "AWS4-HMAC-SHA256 Credential=test-credential/"), sent["headers"]["authorization"])
            self.assertIn("/" + READ["signed"] + "/aws4_request", sent["headers"]["authorization"])
        self.assertEqual(sent["body"], b"")
        text = result["content"][0]["text"]
        if READ["kind"] == "json":
            self.assertEqual(json.loads(text), ANSWER)
        elif READ["kind"] == "text":
            self.assertEqual(text, "example text")
        elif READ["kind"] == "empty":
            self.assertIn("no body", text)
        else:
            self.assertIn("AAE=", text)

    @unittest.skipIf(WRITE is None, "the specification defines no operation with a request body")
    def test_a_body_is_sent_as_the_specification_declares(self):
        self.mock.answer = _answer(WRITE["status"], WRITE["kind"])
        session = self.session()
        session.initialize()
        result = session.call(WRITE["tool"], WRITE["arguments"])["result"]
        self.assertFalse(result["isError"], result)
        [sent] = self.mock.requests
        self.assertIsNone(_problem({"result": result}, [sent], WRITE["method"], WRITE["address"], WRITE["query"]))
        self.assertEqual(sent["headers"].get("content-type"), WRITE["media"])
        if WRITE["form"] is not None:
            self.assertEqual(urllib.parse.parse_qsl(sent["body"].decode("ascii"), keep_blank_values=True),
                             [tuple(pair) for pair in WRITE["form"]])
        else:
            self.assertEqual(json.loads(sent["body"].decode("utf-8")), WRITE["arguments"]["body"])

    def test_two_calls_at_once_are_both_answered(self):
        name, arguments, _method, _address, _query, status, kind = CALLS[0]
        self.mock.answer = _answer(status, kind)
        session = self.session()
        session.initialize()
        # A cancellation of a call that is not in flight is not remembered against a later call with its id.
        session.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "first"}})
        for identity in ("first", "second"):
            session.send({"jsonrpc": "2.0", "id": identity, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments}})
        answers = [session.receive(), session.receive()]
        self.assertEqual(sorted(answer["id"] for answer in answers), ["first", "second"])
        self.assertFalse(any(answer["result"]["isError"] for answer in answers), answers)

    def test_known_wrong_arguments_are_refused_and_nothing_is_sent(self):
        session = self.session()
        session.initialize()
        arguments = WRONG["arguments"]
        cases = [{**arguments, "no_such_argument": 1}, ["not", "an", "object"]]
        if WRONG["required"]:
            cases.append({key: value for key, value in arguments.items() if key != WRONG["required"]})
        if WRONG["typed"]:
            cases.append({**arguments, WRONG["typed"]: WRONG["wrong_value"]})
        if WRONG["body_without"] is not None:
            cases.append({**arguments, "body": WRONG["body_without"]})
        for case in cases:
            answer = session.call(WRONG["tool"], case)
            self.assertEqual(answer.get("error", {}).get("code"), -32602, (case, answer))
        self.assertEqual(self.mock.requests, [])

    def test_known_wrong_an_unknown_tool_or_method_is_an_error(self):
        session = self.session()
        session.initialize()
        self.assertEqual(session.call("no_such_tool", {})["error"]["code"], -32602)
        self.assertEqual(session.request("tools/call", {"arguments": {}})["error"]["code"], -32602)
        self.assertEqual(session.request("resources/list")["error"]["code"], -32601)
        self.assertEqual(self.mock.requests, [])

    def test_known_wrong_malformed_messages_get_their_json_rpc_errors(self):
        session = self.session()
        cases = [(b"{not json", -32700, None), ({"jsonrpc": "1.0", "id": 1, "method": "ping"}, -32600, 1),
                 ({"jsonrpc": "2.0", "id": 2}, -32600, 2), ({"jsonrpc": "2.0", "id": 3, "method": 7}, -32600, 3),
                 ({"jsonrpc": "2.0", "id": None, "method": "ping"}, -32600, None), ([], -32600, None),
                 ({"jsonrpc": "2.0", "id": 4, "method": "ping", "params": "text"}, -32600, 4),
                 ({"jsonrpc": "2.0", "id": 5, "method": "initialize", "params": {}}, -32602, 5),
                 ({"jsonrpc": "2.0", "id": 6, "method": "initialize", "params": [VERSIONS[0]]}, -32602, 6)]
        for message, code, identity in cases:
            session.send(message)
            answer = session.receive()
            self.assertEqual((answer["error"]["code"], answer["id"]), (code, identity), message)
        # A notification is never answered: the next answer on the stream is the ping's.
        session.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        session.send({"jsonrpc": "2.0", "method": "no/such/notification"})
        self.assertEqual(session.request("ping"), {"jsonrpc": "2.0", "id": 1, "result": {}})
        session.send([{"jsonrpc": "2.0", "id": "x", "method": "ping"},
                      {"jsonrpc": "2.0", "method": "notifications/initialized"},
                      {"jsonrpc": "2.0", "id": "y", "method": "no/such/method"}])
        batch = session.receive()
        self.assertEqual(sorted((item["id"], "result" in item) for item in batch), [("x", True), ("y", False)])
        self.assertEqual(session.close(), 0)

    def test_known_wrong_an_error_status_is_a_tool_error_with_its_meaning(self):
        self.mock.answer = (WRONG["error_status"], "application/json", b'{"error": "example"}')
        session = self.session()
        session.initialize()
        result = session.call(WRONG["tool"], WRONG["arguments"])["result"]
        self.assertTrue(result["isError"], result)
        self.assertIn(f"answered {WRONG['error_status']}: {WRONG['meaning']}", result["content"][0]["text"])
        if WRONG["method"] != "HEAD":  # an answer to HEAD carries no body
            self.assertIn("example", result["content"][0]["text"])

    @unittest.skipIf(CREDENTIALED is None, "no tool needs a credential")
    def test_known_wrong_without_the_credential_nothing_is_sent(self):
        name, arguments, variable = CREDENTIALED
        session = self.session(credentials=False)
        session.initialize()
        result = session.call(name, arguments)["result"]
        self.assertTrue(result["isError"], result)
        self.assertIn(variable, result["content"][0]["text"])
        self.assertEqual(self.mock.requests, [])

    def test_known_wrong_an_address_that_is_not_https_sends_nothing(self):
        name, arguments = CALLS[0][0], CALLS[0][1]
        session = self.session(environment={BASE_URL_VARIABLE: "http://example.com"})
        session.initialize()
        result = session.call(name, arguments)["result"]
        self.assertTrue(result["isError"], result)
        self.assertIn("HTTPS", result["content"][0]["text"])
        self.assertEqual(self.mock.requests, [])

    @unittest.skipIf(UNADDRESSED is None, "the specification names the API's address")
    def test_known_wrong_without_an_address_nothing_is_sent(self):
        name, arguments = UNADDRESSED
        session = self.session(root=None)
        session.initialize()
        result = session.call(name, arguments)["result"]
        self.assertTrue(result["isError"], result)
        self.assertIn(BASE_URL_VARIABLE, result["content"][0]["text"])
        self.assertEqual(self.mock.requests, [])


if __name__ == "__main__":
    unittest.main()
'''

#: The marker in TEST_BODY that the schema check replaces, so the tests and the line check schemas alike.
SCHEMA_MARKER = "# SCHEMA PROBLEMS\n"
#: The schema check's source, read once at import: a file edited during a long run never changes what is copied.
SCHEMA_PROBLEMS_SOURCE = inspect.getsource(_schema_problems)


def test_source(data: dict) -> str:
    """test_server.py: the fixed tests around one DATA table, with the line's own schema check copied in."""
    if TEST_BODY.count(SCHEMA_MARKER) != 1:
        raise ValueError("the test body holds the schema marker once")
    keywords = f"SCHEMA_KEYWORDS = {SCHEMA_KEYWORDS!r}\nSCHEMA_TYPES = {SCHEMA_TYPES!r}\n"
    return (TEST_HEAD + keywords + json_constant("DATA", data)
            + TEST_BODY.replace(SCHEMA_MARKER, SCHEMA_PROBLEMS_SOURCE))


__all__ = ["SCHEMA_KEYWORDS", "SCHEMA_TYPES", "client_helpers", "json_constant", "render_json", "server_source",
           "test_source"]

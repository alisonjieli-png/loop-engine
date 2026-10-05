"""Line api_tool_servers: one Model Context Protocol tool server per licensed OpenAPI specification file.

```text
the curated sources of the API operation line (openapi_sources.json), read as that line reads them
├── the file at the branch's head commit, its repository licence and its own declared licence
│   (read_specification), so a server never carries a licence the operation packages would not
├── its tools: the file's operations the operation line builds, in that line's order and by its rules
│   (operations(), the source's maximum_operations across its files, its duplicate rule, a constructible
│   example); each operation left out is a refusal under that line's reason
├── each tool: a name of at most 64 characters, a title and description from the summary and description,
│   an input schema made of the client's own argument checks, and annotations from the method
├── server.py: one standard-library module speaking MCP over standard input and output; the tools are JSON
│   data and one request function sends with the generated client's rules (tool_server_template.py);
│   tools.json beside it holds the same tool list
├── test_server.py: starts the server as a subprocess against a local mock; every tool is called once in a
│   check before the package is built, and the whole file must pass before the package is kept
├── .mcp.json, .codex/config.toml, opencode.json, .cursor/mcp.json: start python3 with the server and pass
│   each credential variable by name, by the registry line's template
└── README.md, LICENSE, UPSTREAM-LICENSE (and SPECIFICATION-LICENSE), UPSTREAM-NOTICE, ATTRIBUTION.md
```

A server above the review bound is written again with shorter descriptions, then with the first tools that fit;
each tool left out is refused by name. Prose that the publication checks would refuse (a secret shape, an
instruction override, a hidden comment) is replaced by the tool's own name and request, and a tool whose
request itself would be refused is left out.
"""
from __future__ import annotations

import base64
import functools
import hashlib
import importlib.util
import itertools
import json
import re
import shutil
import subprocess
import sys
import textwrap
import unicodedata
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from loop_engine.core.library_ingestion.connection_rendering import stdio_connection_files
from loop_engine.core.library_ingestion.format_connection import ConnectionFileRules
from loop_engine.core.library_ingestion.rendering_types import RenderRefused
from loop_engine.core.model_call_records import default_secret_patterns

from licensed_import.checks import blocking_rules

from . import tool_server_template as template
from .declared_licences import LicenceTexts
from .mcp_registry import CURSOR_PATH, HARNESSES, _cursor_file
from .openapi_operations import (
    DECLARED_TEXT_BASIS, FORM_MEDIA_TYPE, NO_ANSWER, SELF_HOSTED_TEST_ROOT, SIGV4_PLACEMENT,
    SPECIFICATION_LICENCE_NAME, OperationRefused, _example_arguments, _response_example, api_title, check_value,
    clean_example, doc, form_pairs, operations, read_specification, synthesize)
from . import packaging
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, notice_files
from .reading import RAW_HOST, github_blob_address, https_address
from .records import (
    API_TOOL_SERVERS, BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

#: 1.1.0 (October 5, 2026): the credential is an unredirected header and a redirect to another origin is a tool error;
#: every server of 1.0.0 sent its credential header to any host a redirect named.
GENERATOR_VERSION = "1.1.0"
NATIVE_FORMAT = "mcp_stdio_server_python"
KIND, FORM = "protocol_server_configuration", "mcp_server"
SERVER_FILE, TEST_FILE, TOOLS_FILE, README_FILE = "server.py", "test_server.py", "tools.json", "README.md"
#: The command each connection file starts, and the project folder the package is placed in (relative to the
#: project root, where the harnesses start a project's local servers).
COMMAND, PLACEMENT_FOLDER = "python3", "tools"
#: The oldest Python the server and its tests run on: the floor the generated API clients are tested on (the
#: repository's own, pyproject.toml), which the line itself runs the generated tests with.
MINIMUM_PYTHON = "3.10"
USER_AGENT = "baltor-api-tool-server/1"
TOOL_NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}")
MAXIMUM_TOOL_NAME = 64
READ_METHODS, DESTRUCTIVE_METHODS = ("GET", "HEAD", "OPTIONS"), ("DELETE", "PUT", "PATCH")
IDEMPOTENT_METHODS = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")
#: A tool's prose at each level of detail, in JSON-escaped characters: (its description, an argument's); at the
#: last level an argument has no description (its name and type remain) and the body none either.
DETAIL_LEVELS = ((600, 200), (240, 80), (120, 0))
#: What a call record leaves out when it holds nothing there; the server's runtime fills the same defaults in
#: (tool_server_template.SERVER_RUNTIME, CALL_DEFAULTS).
CALL_DEFAULTS = {"reserved": [], "fixed_query": [], "fixed_headers": [], "body": None, "errors": {}, "auth": None,
                 "auth_optional": False, "address": 0}
MAXIMUM_TITLE, MAXIMUM_MEANING, MAXIMUM_HINT = 120, 160, 120
#: The longest escaped string a tool may hold beside its prose (an enumeration value, a path): a longer one would
#: make a line the qualification reads as minified code, so the tool is refused instead.
MAXIMUM_DATA_STRING = 900
#: What ATTRIBUTION.md may add to a package (its facts and its file table), kept free under the package bound.
ATTRIBUTION_ALLOWANCE = 16 * 1024
TEST_TIMEOUT_SECONDS = 600
#: What the mock answers in the generated tests: small, and the same for every server.
ANSWER = {"id": "example", "items": [1, 2, 3], "nested": {"ok": True}}
#: The meaning written for an error whose own description the publication checks would refuse.
WITHHELD_MEANING = "a documented error status"
PANEL = Path(__file__).resolve().parents[1] / "candidate_review" / "resources" / "panel.json"
TEST_CREDENTIAL = "test-credential"


class ServerRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


# -- prose ---------------------------------------------------------------------------------------------------------
_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
#: Unicode categories never kept in prose: controls, format characters (zero-width and direction marks among
#: them), surrogates, private use and unassigned code points.
_DROPPED = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})


def clean_text(value) -> str:
    """Prose fit for a tool: HTML comments and invisible or control characters removed, whitespace collapsed."""
    text = _COMMENT.sub(" ", str(value or ""))
    text = "".join(" " if character in "\t\n\r" or unicodedata.category(character) in ("Zl", "Zp") else character
                   for character in text if character in "\t\n\r" or unicodedata.category(character) not in _DROPPED)
    return re.sub(r"\s+", " ", text).strip()


def escaped_length(text: str) -> int:
    return len(json.dumps(text, ensure_ascii=True)) - 2


def fit(text: str, limit: int) -> str:
    """The text when its escaped form fits the limit, else its longest start that ends at a word and, with an
    ellipsis, does."""
    if escaped_length(text) <= limit:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if escaped_length(text[:middle]) + 3 <= limit:
            low = middle
        else:
            high = middle - 1
    cut = text[:low]
    space = cut.rfind(" ")
    if space > low // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-") + "..."


_SCREEN: dict = {}


#: Texts up to this length are screened once and remembered: a server's error meanings and addresses repeat across
#: its tools and its size attempts. A tool's whole text is screened once and not kept.
REMEMBERED_SCREEN = 1000


def screen(text: str) -> tuple:
    """The rules the qualification's publication checks would refuse this text by: the review panel's safety rules
    and secret shapes, a control or format character, and the licensed import's blocking static rules."""
    return _screen_remembered(text) if len(text) <= REMEMBERED_SCREEN else _screen(text)


@functools.lru_cache(maxsize=1 << 14)
def _screen_remembered(text: str) -> tuple:
    return _screen(text)


def _screen(text: str) -> tuple:
    if not _SCREEN:
        from candidate_review.prechecks.safety_rules import RULES
        panel = json.loads(PANEL.read_text(encoding="utf-8"))
        extra = panel["precheck_engines"]["builtin_secret_patterns"]["extra_patterns"]
        _SCREEN["rules"] = RULES
        _SCREEN["secrets"] = tuple(re.compile(pattern) for pattern in (*default_secret_patterns(), *extra))
    found = {code for code, pattern in _SCREEN["rules"] if pattern.search(text)}
    if any(pattern.search(text) for pattern in _SCREEN["secrets"]):
        found.add("secret_shaped_value")
    if any(unicodedata.category(character) in ("Cc", "Cf") and character not in "\n\t" for character in text):
        found.add("control_or_format_character")
    scanned = packaging.static_checks().scan({"tool": [("tool.json", text.encode("utf-8"))]})["tool"]
    found.update(blocking_rules(scanned))
    return tuple(sorted(found))


# -- one tool ------------------------------------------------------------------------------------------------------
def _text(value) -> str:
    """A value as the generated client writes it into a path, a query or a header."""
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def tool_name(function: str, taken) -> str:
    """The operation's function name, or its start with a digest of the whole when it is longer than 64."""
    name = function
    if len(name) > MAXIMUM_TOOL_NAME:
        name = function[:MAXIMUM_TOOL_NAME - 9].rstrip("_") + "_" + hashlib.sha256(function.encode()).hexdigest()[:8]
    if not TOOL_NAME.fullmatch(name) or name in taken:
        raise OperationRefused("operation_identity_missing", f"no unique tool name for {function[:80]}")
    return name


def annotations(method: str) -> dict:
    """The behaviour hints of the Model Context Protocol, from the HTTP method alone."""
    return {"readOnlyHint": method in READ_METHODS, "destructiveHint": method in DESTRUCTIVE_METHODS,
            "idempotentHint": method in IDEMPOTENT_METHODS, "openWorldHint": True}


def minimal_arguments(operation) -> dict:
    """One call's arguments: each required parameter, and the body when it is required, at the smallest values
    the client's checks accept."""
    arguments = {}
    for parameter in operation.parameters:
        if parameter.required:
            value = synthesize(parameter.check)
            check_value(value, parameter.check, parameter.python)
            arguments[parameter.python] = value
    if operation.body_schema is not None and operation.body_required:
        body = synthesize(operation.body_check or {})
        check_value(body, operation.body_check or {}, "body")
        arguments["body"] = body
    return arguments


def full_arguments(operation) -> dict:
    """The minimal arguments with every optional parameter the checks accept a small value for."""
    arguments = minimal_arguments(operation)
    for parameter in operation.parameters:
        if not parameter.required:
            value = synthesize(parameter.check)
            try:
                check_value(value, parameter.check, parameter.python)
            except (TypeError, ValueError):
                continue
            arguments[parameter.python] = value
    return arguments


@dataclass
class Planned:
    """One operation chosen to be a tool: its name, whether its prose is withheld, and one call's arguments."""

    operation: object
    name: str
    minimal: dict
    bare: bool = False


class Tables:
    """What several tools share, written once in the server: addresses, credentials and error meanings."""

    def __init__(self) -> None:
        self.addresses, self.auths, self.meanings = [], [], []

    @staticmethod
    def _index(rows: list, value) -> int:
        if value not in rows:
            rows.append(value)
        return rows.index(value)

    def address(self, operation) -> int:
        hint = fit(clean_text(operation.server_hint), MAXIMUM_HINT)
        if hint and screen(hint):
            hint = ""
        return self._index(self.addresses, {"base_url": operation.base_url, "template": operation.base_url_template,
                                            "region": operation.region_default, "hint": hint})

    def auth(self, auth: "dict | None") -> "int | None":
        if auth is None:
            return None
        return self._index(self.auths, {key: value for key, value in auth.items() if key != "scheme"})

    def meaning(self, text: str) -> int:
        meaning = fit(clean_text(text), MAXIMUM_MEANING)
        if meaning and screen(meaning):
            meaning = WITHHELD_MEANING
        return self._index(self.meanings, meaning)


def prose(planned: Planned, level: int) -> tuple:
    """(title, description, each argument's description) of a tool at one level of detail. A tool whose prose
    the publication checks would refuse is written from its own name and request only."""
    operation = planned.operation
    request = f"{operation.method} {operation.path_key or operation.path}"
    own = operation.function.replace("_", " ").strip().capitalize() or request
    limit, argument_limit = DETAIL_LEVELS[level]
    summary = "" if planned.bare else clean_text(operation.summary)
    detail = "" if planned.bare else clean_text(operation.description)
    title = fit(summary or own, MAXIMUM_TITLE)
    text = f"{summary or own} ({request})."
    if detail and detail != summary:
        text += " " + detail
    if operation.deprecated:
        text = "Deprecated by the specification. " + text
    arguments = {}
    for parameter in operation.parameters:
        base = f"{parameter.location} parameter {parameter.wire}"
        extra = "" if planned.bare else clean_text(parameter.description)
        arguments[parameter.python] = "" if not argument_limit else fit(f"{base}: {extra}", argument_limit) if (
            extra and escaped_length(base) + 12 < argument_limit) else base
    return title, fit(text, max(limit, MAXIMUM_TITLE)), arguments


def tool_entry(planned: Planned, level: int, tables: Tables) -> dict:
    """One tool of the server's table: its MCP definition and how it is called."""
    operation = planned.operation
    title, description, argument_text = prose(planned, level)
    described = bool(DETAIL_LEVELS[level][1])
    properties, required = {}, []
    for parameter in operation.parameters:
        text = argument_text[parameter.python]
        properties[parameter.python] = {**({"description": text} if text else {}), **parameter.check}
        if parameter.required:
            required.append(parameter.python)
    body = None
    if operation.body_schema is not None:
        form = operation.body_media == FORM_MEDIA_TYPE
        text = "The form fields of the request body, sent URL-encoded" if form else \
            f"The JSON request body, sent as {operation.body_media}"
        properties["body"] = {**({"description": text} if described else {}), **(operation.body_check or {})}
        if operation.body_required:
            required.append("body")
        body = {"media": operation.body_media,
                "encoding": {name: [style, explode] for name, style, explode in operation.body_encoding}}
    schema = {"type": "object", "properties": properties, **({"required": required} if required else {}),
              "additionalProperties": False}
    call = {"method": operation.method, "path": operation.path, "operation_id": operation.operation_id,
            "parameters": [[parameter.python, parameter.wire, parameter.location]
                           for parameter in operation.parameters],
            "reserved": [parameter.wire for parameter in operation.parameters if parameter.reserved],
            "fixed_query": [list(item) for item in operation.fixed_query],
            "fixed_headers": [list(item) for item in operation.fixed_headers], "body": body,
            "success": list(operation.success_statuses),
            "errors": {str(code): tables.meaning(text) for code, text in sorted(operation.errors.items())},
            "auth": tables.auth(operation.auth), "auth_optional": operation.auth_optional,
            "address": tables.address(operation)}
    # The annotations follow from the method, which the server reads from the call: the table holds them once.
    return {"name": planned.name, "title": title, "description": description, "inputSchema": schema,
            "call": {key: value for key, value in call.items() if key not in CALL_DEFAULTS
                     or value != CALL_DEFAULTS[key]}}


def call_of(entry: dict) -> dict:
    """A table entry's call record with the defaults it leaves out filled in, as the server reads it."""
    return {**CALL_DEFAULTS, **entry["call"]}


def listed(entry: dict) -> dict:
    """A tool as tools/list describes it at protocol version 2025-06-18, and as tools.json holds it."""
    return {"name": entry["name"], "title": entry["title"], "description": entry["description"],
            "inputSchema": entry["inputSchema"], "annotations": annotations(entry["call"]["method"])}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def schema_problems(entry: dict) -> list:
    """Why a tool's definition cannot be served: its input schema breaks the keywords the generated tests hold it
    to, or JSON Schema's own meta-schema, or a string in it is longer than a line may be."""
    problems = template._schema_problems(entry["inputSchema"])
    try:
        import jsonschema
        jsonschema.Draft202012Validator.check_schema(entry["inputSchema"])
    except ImportError:
        pass
    except Exception as error:  # noqa: BLE001 - jsonschema.SchemaError and its relatives
        problems.append(f"the input schema breaks JSON Schema: {type(error).__name__}")
    longest = max((escaped_length(text) for text in _strings(entry)), default=0)
    if longest > MAXIMUM_DATA_STRING:
        problems.append(f"a string of {longest} escaped characters")
    return problems


def screened_text(entry: dict, tables: Tables) -> str:
    """Everything of one tool the files will show: its table entry, the shared rows it uses, and its prose as a
    README shows it."""
    call = call_of(entry)
    used = [tables.addresses[call["address"]], tables.auths[call["auth"]] if call["auth"] is not None else None,
            [tables.meanings[index] for index in call["errors"].values()]]
    return "\n".join([template.render_json([entry, used]), entry["title"], entry["description"]])


def plan_tools(chosen, label: str, refused: list) -> list:
    """The tools of a server, each refusal recorded: a name, one call's arguments, and prose the publication checks
    accept (else none), and a definition that can be served."""
    plans, names = [], set()
    for operation in chosen:
        subject = f"{label} {operation.method} {operation.path_key or operation.path}"
        try:
            planned = Planned(operation, tool_name(operation.function, names), minimal_arguments(operation))
        except OperationRefused as error:
            refused.append(refusal(API_TOOL_SERVERS, error.reason, subject, error.detail))
            continue
        except (TypeError, ValueError) as error:
            refused.append(refusal(API_TOOL_SERVERS, "example_not_constructible", subject, str(error)[:200]))
            continue
        tables = Tables()
        entry = tool_entry(planned, 0, tables)
        if screen(screened_text(entry, tables)):
            planned.bare = True
            tables = Tables()
            entry = tool_entry(planned, 0, tables)
            blocked = screen(screened_text(entry, tables))
            if blocked:
                refused.append(refusal(API_TOOL_SERVERS, "tool_text_blocked", subject, ",".join(blocked)))
                continue
        problems = schema_problems(entry)
        if problems:
            refused.append(refusal(API_TOOL_SERVERS, "tool_schema_invalid", subject, "; ".join(problems)[:300]))
            continue
        names.add(planned.name)
        plans.append(planned)
    return plans


# -- the test data -------------------------------------------------------------------------------------------------
def _root_of(address: dict, root: "str | None") -> str:
    if root:
        return root
    return address["template"].format(region=address["region"]) if address["template"] else address["base_url"]


def expected_request(operation, arguments: dict, address: dict, root: "str | None") -> tuple:
    """(address, query items, headers) the server must send for one call, computed here from the operation, not
    from the server's table: a broken table fails the tests."""
    path, query = operation.path, [list(item) for item in operation.fixed_query]
    headers = {"accept": "application/json", "user-agent": USER_AGENT,
               **{name.lower(): value for name, value in operation.fixed_headers}}
    for parameter in operation.parameters:
        value = arguments.get(parameter.python)
        if value is None:
            continue
        if parameter.location == "path":
            path = path.replace("{" + parameter.wire + "}",
                                urllib.parse.quote(_text(value), safe="/" if parameter.reserved else ""))
        elif parameter.location == "query":
            items = value if isinstance(value, (list, tuple)) else [value]
            query += [[parameter.wire, _text(item)] for item in items]
        else:
            headers[parameter.wire.lower()] = _text(value)
    auth = operation.auth
    if auth and auth["placement"] == "query":
        query.append([auth["name"], TEST_CREDENTIAL])
    elif auth and auth["placement"] == "header":
        headers[auth["name"].lower()] = auth["prefix"] + TEST_CREDENTIAL
    elif auth and auth["placement"] == "basic":
        headers[auth["name"].lower()] = auth["prefix"] + base64.b64encode(TEST_CREDENTIAL.encode()).decode("ascii")
    return _root_of(address, root).rstrip("/") + path, query, headers


def _kind(operation) -> str:
    status = operation.success_statuses[0]
    return NO_ANSWER if operation.method == "HEAD" or status in (204, 304) else operation.response_kind


def _refuses(schema, value) -> bool:
    """True when the client's own check refuses the value."""
    try:
        check_value(value, schema or {}, "value")
    except (TypeError, ValueError):
        return True
    return False


def credential_variables(plans) -> tuple:
    """(variables set in tests and passed by the connection files, every credential variable named): an AWS session
    token is named but optional, so neither set nor passed."""
    passed, named = [], []
    for planned in plans:
        auth = planned.operation.auth or {}
        for key in ("variable", "secret_variable"):
            if auth.get(key) and auth[key] not in passed:
                passed.append(auth[key])
        for key in ("variable", "secret_variable", "token_variable"):
            if auth.get(key) and auth[key] not in named:
                named.append(auth[key])
    return passed, named


def test_data(plans, entries, tables: Tables, key: str, base_url_variable: str) -> dict:
    """DATA of test_server.py: what every tool must send, and the calls of the detailed and known-wrong tests."""
    passed, named = credential_variables(plans)
    pairs = list(zip(plans, entries))
    unaddressed = next(((planned, entry) for planned, entry in pairs
                        if not (tables.addresses[call_of(entry)["address"]]["base_url"]
                                or tables.addresses[call_of(entry)["address"]]["template"])), None)
    root = SELF_HOSTED_TEST_ROOT if unaddressed else None

    def request(planned, entry, arguments):
        return expected_request(planned.operation, arguments, tables.addresses[call_of(entry)["address"]], root)

    calls = []
    for planned, entry in pairs:
        address, query, _headers = request(planned, entry, planned.minimal)
        calls.append([planned.name, planned.minimal, planned.operation.method, address, query,
                      planned.operation.success_statuses[0], _kind(planned.operation)])
    read = None
    reads = [(index, planned, entry) for index, (planned, entry) in enumerate(pairs)
             if planned.operation.method in READ_METHODS]
    if reads:
        _index, planned, entry = max(reads, key=lambda row: (_kind(row[1].operation) == "json",
                                                             len(row[1].operation.parameters), -row[0]))
        arguments = full_arguments(planned.operation)
        address, query, headers = request(planned, entry, arguments)
        signed = (planned.operation.auth or {}).get("placement") == SIGV4_PLACEMENT
        read = {"tool": planned.name, "arguments": arguments, "method": planned.operation.method, "address": address,
                "query": query, "headers": headers, "status": planned.operation.success_statuses[0],
                "kind": _kind(planned.operation), "signed": planned.operation.auth["service"] if signed else None}
    write = None
    for planned, entry in pairs:
        operation = planned.operation
        if operation.body_schema is None:
            continue
        arguments = dict(planned.minimal)
        fuller = synthesize(operation.body_check or {}, every_property=True)
        arguments["body"] = fuller if not _refuses(operation.body_check, fuller) else \
            synthesize(operation.body_check or {})
        if _refuses(operation.body_check, arguments["body"]):
            continue
        form = operation.body_media == FORM_MEDIA_TYPE
        if form and not isinstance(arguments["body"], dict):
            continue
        address, query, _headers = request(planned, entry, arguments)
        write = {"tool": planned.name, "arguments": arguments, "method": operation.method, "address": address,
                 "query": query, "media": operation.body_media,
                 "form": [list(pair) for pair in form_pairs(arguments["body"], operation.body_encoding)]
                 if form else None,
                 "status": operation.success_statuses[0], "kind": _kind(operation)}
        break
    choices = [pair for pair in pairs if pair[0].operation.method != "HEAD"] or pairs
    planned, entry = next((pair for pair in choices if pair[0].minimal), choices[0])
    operation = planned.operation
    required = [parameter for parameter in operation.parameters if parameter.required]
    typed, wrong_value = None, None
    for parameter in required:
        candidate = [1, 2] if "string" in parameter.check.get("type", []) else "wrong type"
        if parameter.check.get("type") and _refuses(parameter.check, candidate):
            typed, wrong_value = parameter.python, candidate
            break
    body_without = None
    body = planned.minimal.get("body")
    body_required = (operation.body_check or {}).get("required") or []
    if isinstance(body, dict) and body_required and body_required[0] in body:
        without = {name: value for name, value in body.items() if name != body_required[0]}
        if _refuses(operation.body_check, without):
            body_without = without
    status = min(operation.errors) if operation.errors else 500
    index = call_of(entry)["errors"].get(str(status))
    wrong = {"tool": planned.name, "arguments": planned.minimal, "method": operation.method,
             "required": required[0].python if required else ("body" if "body" in planned.minimal else None),
             "typed": typed, "wrong_value": wrong_value, "body_without": body_without, "error_status": status,
             "meaning": tables.meanings[index] if index is not None else "not a documented success"}
    credentialed = next(([planned.name, planned.minimal, planned.operation.auth["variable"]]
                         for planned in plans if planned.operation.auth and not planned.operation.auth_optional), None)
    # The redirect test's tool: the first that sends a credential, a read before any other method, so a server that
    # followed the redirect (urllib follows a read's every redirect) would carry the credential to the second mock.
    redirected = min(plans, key=lambda planned: (planned.operation.auth is None,
                                                 planned.operation.method not in READ_METHODS))
    cleared = list(dict.fromkeys(named + [base_url_variable, "AWS_REGION", "AWS_DEFAULT_REGION"]))
    return {"server_name": key, "base_url_variable": base_url_variable, "user_agent": USER_AGENT,
            "variables": passed, "cleared": cleared, "root": root, "answer": ANSWER,
            "methods": [[planned.name, planned.operation.method] for planned in plans], "calls": calls, "read": read,
            "write": write, "wrong": wrong, "credentialed": credentialed,
            "unaddressed": [unaddressed[0].name, unaddressed[0].minimal] if unaddressed else None,
            "redirected": [redirected.name, redirected.minimal]}


# -- the files of one server ---------------------------------------------------------------------------------------
def server_key(source: dict, path: str) -> str:
    """The server's key in each harness file: the vendor, and the file's path when the source has several files."""
    base = source["vendor"] if len(source["paths"]) == 1 else \
        f"{source['vendor']}-{PurePosixPath(path).with_suffix('').as_posix()}"
    key = re.sub(r"[^a-z0-9_-]+", "-", base.lower()).strip("-_")
    if len(key) > 64:
        key = key[:55].rstrip("-_") + "-" + hashlib.sha256(base.encode()).hexdigest()[:8]
    return key


@dataclass
class ServerFacts:
    """What every file of one server names: the specification, the key and the variables."""

    spec: dict
    title: str
    key: str
    licence: str
    passed: list = field(default_factory=list)
    named: list = field(default_factory=list)
    unaddressed: bool = False
    operations_found: int = 0
    left_out: dict = field(default_factory=dict)

    @property
    def folder(self) -> str:
        return f"{PLACEMENT_FOLDER}/{self.key}"

    @property
    def base_url_variable(self) -> str:
        return self.spec["base_url_variable"]


def _spec_title(spec: dict, source: dict) -> str:
    title = fit(clean_text(spec["title"]), 80)
    return title if title and not screen(title) else source["vendor"]


def docstring(facts: ServerFacts, count: int) -> str:
    spec = facts.spec
    first = textwrap.fill(f"{api_title(facts.title)} tools: {count} operations of the {facts.title} OpenAPI "
                          f"specification {spec['version']} as Model Context Protocol tools.", width=110)
    rest = textwrap.fill(
        f"Baltor generated this server from the specification at {spec['repository']}@{spec['commit'][:12]} "
        f"({spec['path']}); see README.md and tools.json. It speaks the Model Context Protocol over standard input "
        "and output, one JSON-RPC 2.0 message per line (protocol versions 2025-06-18, 2025-03-26 and 2024-11-05), "
        f"runs on Python {MINIMUM_PYTHON} or later with the standard library only, and logs to standard error only. "
        "Each tool checks its arguments and sends one HTTPS request with the rules of Baltor's generated API "
        "clients, whose helpers it copies.", width=110)
    return doc(first + "\n\n" + rest)


def instructions(facts: ServerFacts, base_url: str) -> str:
    text = (f"Tools for the {api_title(facts.title)} {facts.spec['version']}: each tool sends one HTTPS request to "
            "the API and returns its answer. Tools annotated read-only only read; the others can change or delete "
            "data in the account the credential belongs to.")
    if facts.passed:
        text += f" The credential comes from the environment variable{'s' if len(facts.passed) > 1 else ''} " \
                f"{', '.join(facts.passed)}."
    if facts.unaddressed:
        text += f" Set {facts.base_url_variable} to the API's HTTPS address before calling a tool."
    elif base_url:
        text += f" The address is {base_url} unless {facts.base_url_variable} names another HTTPS address."
    return text


def server_constants(facts: ServerFacts, base_url: str) -> str:
    spec = facts.spec
    specification = {"title": facts.title, "version": spec["version"], "repository": spec["repository"],
                     "path": spec["path"], "commit": spec["commit"], "sha256": spec["sha256"]}
    server = {"name": facts.key, "title": f"{api_title(facts.title)} tools",
              "version": spec["version"] or spec["commit"][:12]}
    return "\n".join([
        "#: The specification this server was generated from: its repository and path name the server's job.",
        f"SPECIFICATION = {json.dumps(specification, ensure_ascii=True)}",
        f"SERVER = {json.dumps(server, ensure_ascii=True)}",
        "#: The environment variable that names another HTTPS address for the API than the specification's.",
        f"BASE_URL_VARIABLE = {json.dumps(facts.base_url_variable)}",
        f"INSTRUCTIONS = {json.dumps(instructions(facts, base_url), ensure_ascii=True)}",
        "#: The tools and how each is called: data, never code. tools.json beside this file holds the same tools as",
        "#: tools/list describes them; README.md lists them.", ""])


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _wrap(text: str, indent: str = "") -> str:
    """One Markdown paragraph wrapped at 110 characters, never inside a word or a code span's address."""
    return textwrap.fill(text, width=110, subsequent_indent=indent, break_long_words=False, break_on_hyphens=False)


#: How each credential placement is named in a README.
_PLACEMENT_WORDS = {"header": "the `{name}` header", "basic": "Basic credentials in the `{name}` header",
                    "query": "the query parameter `{name}`",
                    SIGV4_PLACEMENT: "an AWS Signature Version 4 signature for the service `{service}`"}


def readme(facts: ServerFacts, entries: list, tables: Tables, tests_described: str) -> str:
    """README.md: what the tools are, the third-party API, the credential and address, the effects, where each file
    goes, every tool, what was left out, and how to run the tests."""
    spec = facts.spec
    count = len(entries)
    bases = sorted({_root_of(address, None) for address in tables.addresses if _root_of(address, None)})
    where = f" at `{bases[0]}`" if len(bases) == 1 else (" at " + ", ".join(f"`{base}`" for base in bases[:4])
                                                         if bases else "")
    if facts.passed:
        places = sorted({_PLACEMENT_WORDS[auth["placement"]].format(name=auth.get("name"), service=auth.get("service"))
                         for auth in tables.auths})
        credential = (f"The server reads the credential from the environment variable"
                      f"{'s' if len(facts.passed) > 1 else ''} {', '.join(f'`{name}`' for name in facts.passed)} and "
                      f"sends it as each operation declares, in {' or '.join(places)}. It is never written to a file. "
                      "Each connection file passes the variable on by name, so set it in the environment the "
                      "harness starts from.")
        optional = sum(1 for entry in entries if call_of(entry)["auth"] is not None and call_of(entry)["auth_optional"])
        if optional:
            credential += f" {optional} of the tools also work without it."
    else:
        credential = "The specification requires no credential for these operations."
    hints = sorted({address["hint"] for address in tables.addresses if address["hint"]})
    if facts.unaddressed:
        address = ("The specification names no public HTTPS address" + (f" (it lists `{hints[0]}`)" if hints else "")
                   + f": set `{facts.base_url_variable}` to the API's HTTPS address. The server sends nothing until "
                     "it is set, and each connection file passes it on.")
    else:
        address = (f"Set `{facts.base_url_variable}` to send every call to another HTTPS address instead, such as a "
                   "regional or self-hosted instance, and add it to the connection file's variables when you do.")
    placements = "\n".join(f"| {harness} | `{path}` | {target} |" for harness, path, target in HARNESSES)
    rows = []
    for entry in entries:
        method = entry["call"]["method"]
        change = "no" if method in READ_METHODS else "yes, destructive" if method in DESTRUCTIVE_METHODS else "yes"
        rows.append(f"| `{entry['name']}` | `{_cell(method + ' ' + entry['call']['path'])}` | {change} | "
                    f"{_cell(fit(entry['title'], 100))} |")
    left = ""
    if facts.left_out:
        reasons = ", ".join(f"{reason.replace('_', ' ')} {number}" for reason, number in
                            sorted(facts.left_out.items(), key=lambda item: (-item[1], item[0])))
        left = "\n" + _wrap(f"The file defines {facts.operations_found} operations; {count} are tools here. The "
                            f"others were left out, by reason: {reasons}.") + "\n"
    paragraphs = {
        "intro": _wrap(f"{count} tools, one per operation of the {facts.title} OpenAPI specification "
                       f"{spec['version']}, served by `{SERVER_FILE}`, a Model Context Protocol server that a harness "
                       "starts as a local process. Baltor generated the server, its tests and these files from the "
                       f"specification at `{spec['repository']}` commit `{spec['commit']}`, file `{spec['path']}` "
                       f"(SHA-256 `{spec['sha256']}`), licensed {facts.licence}. It needs Python {MINIMUM_PYTHON} or "
                       "later and nothing beyond the standard library."),
        "third_party": _wrap(f"Every tool call sends one HTTPS request to the {facts.title} API{where}, a service "
                             "that Baltor neither operates nor endorses. The API's own terms, rate limits and charges "
                             "apply to each call made with your credential. A tool that is not read-only can change "
                             "or delete data in that account: each tool's annotations say which (read-only for GET, "
                             "HEAD and OPTIONS; destructive for DELETE, PUT and PATCH; POST neither)."),
        "credential": _wrap(credential), "address": _wrap(address),
        "effects": "\n".join(_wrap(item, "  ") for item in (
            f"- The harness starts `{SERVER_FILE}` with `{COMMAND}` as a local process (it spawns a process).",
            "- Each tool call checks its arguments first and sends nothing when they break the specification; "
            "otherwise it sends one HTTPS request to the API and returns its answer (it uses the network). A "
            "redirect is followed only within the API's origin and never with the credential; a redirect to another "
            "origin is refused.",
            ("- It reads the credential variables named above from its environment (it reads a secret). It "
             if facts.named else "- It reads no credential. It ") + "writes no file, and it logs to standard error "
            "only.")),
        "placement": _wrap(f"Copy this folder to `{facts.folder}/` in your project. Each connection file starts "
                           f"`{COMMAND} {facts.folder}/{SERVER_FILE}` from the project root; merge it into the "
                           "harness's own file."),
        "tests": _wrap(tests_described)}
    return f"""# {api_title(facts.title)} tools for Claude Code, Codex, OpenCode and Cursor

{paragraphs["intro"]}

## Third-party API

{paragraphs["third_party"]}

## Credential and address

{paragraphs["credential"]}

{paragraphs["address"]}

## Effects

{paragraphs["effects"]}

## Where each file goes

{paragraphs["placement"]}

| Harness | File in this package | Merge it into |
|---|---|---|
{placements}

## Tools

| Tool | Request | Changes data | Title |
|---|---|---|---|
{chr(10).join(rows)}
{left}
## Tests

```bash
python -m unittest {TEST_FILE[:-3]}
```

{paragraphs["tests"]}
"""


TESTS_DESCRIBED = ("`test_server.py` starts the server as a subprocess and speaks the protocol to it: version "
                   "negotiation, the tool list against `tools.json` with every input schema and annotation checked, "
                   "one call of every tool against a local mock HTTP server (method, address and query), a read and "
                   "a body in detail, two calls at once, and known-wrong calls (unknown arguments, a missing or "
                   "mistyped argument, an unknown tool or method, malformed messages, an error status, a missing "
                   "credential or address, an address that is not HTTPS, and a redirect to a second mock on another "
                   "port, which must be refused with no credential reaching it). A shim sends every request to the "
                   "mock, so nothing leaves the machine.")


def render(facts: ServerFacts, plans: list, level: int) -> tuple:
    """(files, entries, tables) of a server with these tools at one level of detail."""
    tables = Tables()
    entries = [tool_entry(planned, level, tables) for planned in plans]
    table = {"addresses": tables.addresses, "auths": tables.auths, "meanings": tables.meanings, "tools": entries}
    bases = [_root_of(address, None) for address in tables.addresses if _root_of(address, None)]
    constants = server_constants(facts, bases[0] if len(set(bases)) == 1 else "")
    server = template.server_source(docstring(facts, len(entries)), constants, table)
    tools = template.render_json({"tools": [listed(entry) for entry in entries]}) + "\n"
    tests = template.test_source(test_data(plans, entries, tables, facts.key, facts.base_url_variable))
    files = {SERVER_FILE: server, TOOLS_FILE: tools, TEST_FILE: tests,
             README_FILE: readme(facts, entries, tables, TESTS_DESCRIBED)}
    return {path: text.encode("utf-8") for path, text in files.items()}, entries, tables


def fits(files: dict, fixed_bytes: int) -> bool:
    return all(len(data) <= packaging.MAXIMUM_REVIEW_FILE_BYTES for data in files.values()) and \
        sum(len(data) for data in files.values()) + fixed_bytes + ATTRIBUTION_ALLOWANCE <= \
        packaging.MAXIMUM_REVIEW_PACKAGE_BYTES


def within_bound(facts: ServerFacts, plans: list, fixed_bytes: int, label: str, refused: list) -> tuple:
    """(tools, level): every tool at the first level of detail whose files fit the review bound, else the first
    tools that fit at the last level, each one left out refused by name."""
    for level in range(len(DETAIL_LEVELS)):
        if fits(render(facts, plans, level)[0], fixed_bytes):
            return plans, level
    level = len(DETAIL_LEVELS) - 1
    low, high = 0, len(plans)
    while low < high:
        middle = (low + high + 1) // 2
        if fits(render(facts, plans[:middle], level)[0], fixed_bytes):
            low = middle
        else:
            high = middle - 1
    for planned in plans[low:]:
        operation = planned.operation
        refused.append(refusal(API_TOOL_SERVERS, "tools_beyond_review_bound",
                               f"{label} {operation.method} {operation.path_key or operation.path}",
                               f"the server holds the first {low} tools within {packaging.MAXIMUM_REVIEW_FILE_BYTES} "
                               "bytes per file"))
    return plans[:low], level


# -- running the generated tests -----------------------------------------------------------------------------------
_PRECHECKS = itertools.count()


def stage(folder: Path, files: dict) -> None:
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for path, data in files.items():
        (folder / path).write_bytes(data)


def check_calls(folder: Path) -> dict:
    """{tool: problem} for the staged server: every tool called once through the staged tests' own harness (the
    server in a subprocess behind its shim, a local mock), so one tool that fails is left out, not the server."""
    name = f"_tool_server_check_{next(_PRECHECKS)}"
    loaded = importlib.util.spec_from_file_location(name, folder / TEST_FILE)
    module = importlib.util.module_from_spec(loaded)
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        loaded.loader.exec_module(module)
        return module.check_calls()
    finally:
        sys.dont_write_bytecode = saved


def run_generated_tests(folder: Path) -> tuple:
    """(passed, tests run, tail of the output) of the staged package's own tests, in a process of their own."""
    try:
        done = subprocess.run([sys.executable, "-E", "-s", "-B", "-m", "unittest", "-v", TEST_FILE[:-3]], cwd=folder,
                              capture_output=True, timeout=TEST_TIMEOUT_SECONDS, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, 0, "the generated tests ran past their time limit"
    output = done.stderr.decode("utf-8", "replace")
    ran = re.findall(r"^Ran (\d+) tests? in ", output, re.MULTILINE)
    count = int(ran[-1]) if ran else 0
    passed = done.returncode == 0 and count > 0 and bool(re.search(r"^OK\b", output, re.MULTILINE))
    return passed, count, output[-800:]


# -- the package ---------------------------------------------------------------------------------------------------
def licence_parts(spec: dict, licence, licence_text: bytes) -> tuple:
    """(files, facts, expression): LICENSE, UPSTREAM-LICENSE, SPECIFICATION-LICENSE and UPSTREAM-NOTICE with their
    fact sources and the licence expression, exactly as the API operation line writes them for the same file
    (openapi_operations.prepare_package)."""
    licence_address = github_blob_address(licence.repository, licence.commit, licence.path)
    files = [PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": licence_address, "sha256": licence.sha256})]
    second = (spec.get("declared_licence") or {}).get("text")
    if second is not None:
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
             fact_source(licence_address, spec["retrieved_at"], licence.sha256, len(licence.text), "licence_text",
                         spdx=licence.spdx, basis=spec.get("licence_text_basis", "licence_file_at_the_pinned_commit"))]
    if second is not None:
        facts.append(fact_source(github_blob_address(second.repository, second.commit, second.path),
                                 spec["retrieved_at"], second.sha256, len(second.text), "licence_text",
                                 spdx=second.spdx, basis=DECLARED_TEXT_BASIS))
    notices, notice_facts = notice_files(spec.get("notices"))
    files += notices
    facts += notice_facts
    facts += list(spec.get("extra_facts") or ())
    return files, facts, expression


def connection_files(facts: ServerFacts) -> list:
    """The four harness files that start the server with python3 and pass each credential variable by name, by
    the registry line's template, checked against each harness's documented shape."""
    inputs = [{"name": name, "required": True, "secret": True} for name in facts.passed]
    if facts.unaddressed:
        inputs.append({"name": facts.base_url_variable, "required": True, "secret": False})
    try:
        rendered = stdio_connection_files(facts.key, COMMAND, [f"{facts.folder}/{SERVER_FILE}"], inputs)
    except RenderRefused as error:
        raise ServerRefused("connection_files_invalid", error.detail) from None
    texts = {row["harness"]: row["text"] for row in rendered}
    cursor = _cursor_file(facts.key, {"inputs": inputs}, texts)
    problems = ConnectionFileRules().validate_package({"key": facts.key, "inputs": inputs, "files": [
        *rendered, {"harness": "cursor", "path": CURSOR_PATH, "text": cursor}]})
    if problems:
        raise ServerRefused("connection_files_invalid", "; ".join(problems))
    paths = {row["harness"]: row["path"] for row in rendered}
    return [PackageFile(paths[harness], texts[harness].encode("utf-8"), KIND) for harness in texts] + \
        [PackageFile(CURSOR_PATH, cursor.encode("utf-8"), KIND)]


def build_server(spec: dict, source: dict, licence, chosen: list, *, generator: dict, licence_text: bytes,
                 generated_on: str, staging: Path, repository_facts: dict, refused: list, operations_found: int,
                 left_out: Counter) -> tuple:
    """((payload, bodies), summary) of one specification file's tool server, or raise ServerRefused."""
    label = f"{source['source_id']} {spec['path']}"
    start = len(refused)
    plans = plan_tools(chosen, label, refused)
    if not plans:
        raise ServerRefused("no_tools", "no operation of the file could be a tool")
    passed, named = credential_variables(plans)
    facts = ServerFacts(spec, _spec_title(spec, source), server_key(source, spec["path"]), licence.spdx, passed, named,
                        operations_found=operations_found)
    identity = f"{spec['repository']}:{spec['path']}"
    key = upstream_key(API_TOOL_SERVERS, identity)
    folder = staging / key
    try:
        licence_files, fact_sources, expression = licence_parts(spec, licence, licence_text)
        fixed = sum(len(row.data) for row in licence_files) + 4096
        facts.unaddressed = any(not (planned.operation.base_url or planned.operation.base_url_template)
                                for planned in plans)
        plans, level = within_bound(facts, plans, fixed, label, refused)
        if not plans:
            raise ServerRefused("package_above_review_bound", "not one tool fits the review bound")
        facts.unaddressed = any(not (planned.operation.base_url or planned.operation.base_url_template)
                                for planned in plans)
        connections = connection_files(facts)
        files, _entries, _tables = render(facts, plans, level)
        stage(folder, files)
        try:
            failures = check_calls(folder)
        except Exception as error:  # noqa: BLE001 - a server that cannot even start is refused, never stored
            raise ServerRefused(GENERATED_TEST_FAILED, f"{type(error).__name__}: {error}"[:300]) from None
        if failures:
            for planned in plans:
                if planned.name in failures:
                    refused.append(refusal(API_TOOL_SERVERS, GENERATED_TEST_FAILED,
                                           f"{label} {planned.operation.method} "
                                           f"{planned.operation.path_key or planned.operation.path}",
                                           failures[planned.name]))
            plans = [planned for planned in plans if planned.name not in failures]
            if not plans:
                raise ServerRefused(GENERATED_TEST_FAILED, "every tool failed its call")
            facts.passed, facts.named = credential_variables(plans)
            facts.unaddressed = any(not (planned.operation.base_url or planned.operation.base_url_template)
                                    for planned in plans)
            connections = connection_files(facts)
        facts.left_out = dict(left_out + Counter(row["reason"] for row in refused[start:]))
        files, entries, tables = render(facts, plans, level)
        stage(folder, files)
        passed_tests, count, output = run_generated_tests(folder)
        if not passed_tests:
            raise ServerRefused(GENERATED_TEST_FAILED, output[-300:])
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    effects = [("network", "sends_one_https_request_to_the_api_per_tool_call"),
               ("spawns_process", "the_harness_starts_the_server_with_python3")]
    if facts.named:
        effects.append(("reads_secret", "reads_the_credential_variables_from_the_environment"))
    package_files = [PackageFile(SERVER_FILE, files[SERVER_FILE], "executable_tool"),
                     PackageFile(TEST_FILE, files[TEST_FILE], "executable_tool"),
                     PackageFile(TOOLS_FILE, files[TOOLS_FILE], "other"),
                     PackageFile(README_FILE, files[README_FILE], "other"), *connections, *licence_files]
    stars = ((repository_facts.get(spec["repository"].lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=API_TOOL_SERVERS, identity=identity, key=key, kind=KIND, native_format=NATIVE_FORMAT, form=FORM,
        name=f"{facts.key}-tool-server"[:90],
        description=(f"{api_title(facts.title)}: {len(entries)} tools for Claude Code, Codex, OpenCode and Cursor, "
                     f"one per operation of {spec['path']}, served by one tested Python protocol server (standard "
                     "library only)."),
        files=package_files, licence_expression=expression,
        provenance=provenance(spec.get("origin", "github_repository"), spec["repository"], spec["path"],
                              spec["commit"], fact_sources, generator),
        placements=[{"harness": "reference", "path": f"{facts.folder}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}] + [
            {"harness": harness, "path": path, "basis": "documented_layout", "scope": "project",
             "support": "unverified"} for harness, path, _target in HARNESSES],
        effects=effects, credentials=facts.named,
        tests={"files": [TEST_FILE], "command": f"python -m unittest {TEST_FILE[:-3]}", "result": "passed",
               "tests_run": count, "network": False, "tools_called": len(entries),
               "server": "started_as_a_subprocess_against_a_local_mock"},
        repository={"name": spec["repository"], "stars": stars, "specification": spec["path"],
                    "specification_version": spec["version"], "tools": len(entries)},
        generated_on=generated_on, comparison_text=identity)
    try:
        built = packaging.build(supply)
    except SupplyRecordError as error:
        reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
            GENERATED_TEST_FAILED
        raise ServerRefused(reason, str(error)[:300]) from None
    return built, {"tools": len(entries), "detail_level": level, "tests_run": count,
                   "server_bytes": len(files[SERVER_FILE]), "key": facts.key,
                   "auth_placements": sorted({auth["placement"] for auth in tables.auths}),
                   "unaddressed": facts.unaddressed}


# -- the line ------------------------------------------------------------------------------------------------------
def select(found: list, source: dict, state: dict, label: str, refused: list) -> tuple:
    """(chosen, past): the operations of one file the API operation line would build, in its order and by its
    rules (the source's maximum across its files, one package per module name across them, and an example its
    client can be tested with: openapi_operations.generate and prepare_package), and how many operations lay past
    the maximum, which one refusal row counts."""
    chosen = []
    for index, operation in enumerate(found):
        if state["taken"] + len(chosen) >= source["maximum_operations"]:
            refused.append(refusal(API_TOOL_SERVERS, "beyond_maximum_operations", label,
                                   f"{len(found) - index} operations past the source's maximum of "
                                   f"{source['maximum_operations']}"))
            return chosen, len(found) - index
        subject = f"{label} {operation.method} {operation.path_key or operation.path}"
        if operation.module in state["seen"]:
            refused.append(refusal(API_TOOL_SERVERS, "duplicate_operation", subject, operation.module))
            continue
        state["seen"].add(operation.module)
        try:
            call = clean_example(_example_arguments(operation))
            clean_example(_response_example(operation))
            for name, value in call.items():
                check_value(value, next((row.check for row in operation.parameters if row.python == name),
                                        operation.body_check or {}), name)
        except (TypeError, ValueError) as error:
            refused.append(refusal(API_TOOL_SERVERS, "example_not_constructible", subject, str(error)[:200]))
            continue
        chosen.append(operation)
    return chosen, 0


def generate(reader, sources, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: "dict | None" = None) -> tuple:
    """(built, refusals, facts, summary): one tested tool server per declared specification file."""
    built, refused, facts, summary = [], [], {}, []
    generator = {"identity": "tools/supply_lines/api_tool_servers.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    texts = LicenceTexts(reader)
    for source in sources:
        state = {"taken": 0, "seen": set()}
        for path in source["paths"]:
            label = f"{source['source_id']} {path}"
            try:
                spec = read_specification(reader, source, path, texts)
            except OperationRefused as error:
                refused.append(refusal(API_TOOL_SERVERS, error.reason, label, error.detail))
                summary.append({"source_id": source["source_id"], "path": path, "refused": error.reason})
                continue
            facts[spec["sha256"]] = spec["bytes"]
            licence = spec["licence"]
            found, reading = operations(spec["document"], source)
            before = len(refused)
            refused += [refusal(API_TOOL_SERVERS, row["reason"], row["subject"], row["detail"]) for row in reading]
            chosen, past = select(found, source, state, label, refused)
            # The operations left out so far, by reason; the maximum's one row counts every operation past it.
            left_out = Counter(row["reason"] for row in refused[before:]
                               if row["reason"] != "beyond_maximum_operations")
            if past:
                left_out["beyond_maximum_operations"] = past
            row = {"source_id": source["source_id"], "path": path, "commit": spec["commit"], "sha256": spec["sha256"],
                   "licence": licence.spdx, "declared_licence": (spec.get("declared_licence") or {}).get("spdx"),
                   "operations": len(found), "refused_while_reading": len(reading), "chosen": len(chosen)}
            try:
                package, details = build_server(
                    spec, source, licence, chosen, generator=generator, licence_text=licence_text,
                    generated_on=generated_on, staging=staging, repository_facts=repository_facts or {},
                    refused=refused, operations_found=len(found) + len(reading), left_out=left_out)
            except ServerRefused as error:
                refused.append(refusal(API_TOOL_SERVERS, error.reason, label, error.detail))
                summary.append({**row, "tools": 0, "refused": error.reason})
                continue
            built.append(package)
            state["taken"] += details["tools"]
            summary.append({**row, **details})
    return built, refused, facts, summary


def counts(refusals) -> dict:
    return dict(Counter(row["reason"] for row in refusals).most_common())


__all__ = ["GENERATOR_VERSION", "build_server", "generate", "plan_tools", "screen", "select", "server_key",
           "tool_entry", "tool_name"]

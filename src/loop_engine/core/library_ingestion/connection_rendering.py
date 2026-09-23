"""Render one registry entry into connection files for Claude Code, Codex and OpenCode.

Link mode: every byte here is written from the entry's facts (name, version,
package or endpoint, the names of its inputs) by Baltor's own template. The
author's description, the input descriptions and the server's code are
never copied; topic words from the closed list may become search tags. A
secret input is always a reference to an environment variable in each
harness's own syntax, never a value. An endpoint that is not HTTPS, a
credential-shaped value, a required argument without a value, a templated
address and an unsupported package type are refused by name. The files
follow each harness's documented shape: Claude Code's .mcp.json, a Codex
config.toml table, and OpenCode's opencode.json. The package document beside
them carries the upstream identity (the server's name and version, its code
repository address when the entry gives an HTTPS one) and the licence
evidence of that code repository, so a reviewer reads the rights with the
files; the harness files themselves hold configuration only.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..model_call_records import default_secret_patterns
from .https_transport import HTTPS_SCHEME, split_address
from .rendering_types import RenderedPackage, RenderRefused
from .topics import topic_words

CONNECTION_PACKAGE_RECORD_TYPE = "library_connection_package/v1"
DOCUMENT_PATH = "baltor-connection.json"
CLAUDE_CODE, CODEX, OPENCODE = "claude_code", "codex", "opencode"
HARNESS_PATHS = ((CLAUDE_CODE, ".mcp.json"), (CODEX, ".codex/config.toml"), (OPENCODE, "opencode.json"))
#: The package registries whose packages this renderer can start, and the transports it can reach.
NPM, PYPI, OCI = "npm", "pypi", "oci"
STDIO, STREAMABLE_HTTP, SSE = "stdio", "streamable-http", "sse"
_COMMANDS = {NPM: "npx", PYPI: "uvx", OCI: "docker"}
_REGISTRY_LABELS = {NPM: "npm", PYPI: "PyPI", OCI: "container image"}
_REMOTE_TYPES = {STREAMABLE_HTTP: "http", SSE: "sse"}
_REMOTE_WORDS = {STREAMABLE_HTTP: "streamable HTTP", SSE: "server-sent events"}
#: How a header value reaches the harness: written as given, or read from a variable.
FIXED_VALUE, VARIABLE_VALUE = "fixed", "variable"
_MAXIMUM_ADDRESS_CHARACTERS = 512
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_HEADER_NAME = re.compile(r"[A-Za-z0-9!#$%&'*+.^_`|~-]{1,128}\Z")
_IDENTIFIERS = {NPM: re.compile(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*\Z", re.I),
                PYPI: re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z"),
                OCI: re.compile(r"[a-z0-9][a-z0-9._/:@-]*\Z")}
_VERSION = re.compile(r"(?:sha256:[0-9a-f]{64}|[A-Za-z0-9][A-Za-z0-9.+_-]{0,63})\Z")
#: A tag that moves with every release names no exact package or image.
FLOATING_TAG = "latest"
_TOKEN_QUERY = re.compile(r"(?i)(?:^|&)(?:api[_-]?key|access[_-]?token|token|secret|password|key)=([^&]{8,})")


def config_key(name: str) -> str:
    """A harness-safe key for one server: letters, digits, hyphens and underscores."""
    base = name[len("io.github."):] if name.startswith("io.github.") else name
    key = re.sub(r"[^a-z0-9_-]+", "-", base.lower()).strip("-_")
    if len(key) > 64:
        key = key[:55].rstrip("-_") + "-" + hashlib.sha256(name.encode()).hexdigest()[:8]
    if not key:
        raise RenderRefused("server_name_unusable", "the server name leaves no usable key")
    return key


def credential_shaped(value: str) -> bool:
    """True when a value has the shape of a secret or carries one in its query."""
    if any(re.search(pattern, value) for pattern in default_secret_patterns()):
        return True
    return bool(_TOKEN_QUERY.search(split_address(value).query)) if "?" in value else False


def _arguments(arguments) -> list:
    rendered = []
    for argument in arguments or ():
        if not isinstance(argument, dict):
            raise RenderRefused("required_arguments_not_rendered", "an argument is not an object")
        value = argument.get("value", argument.get("default"))
        if value is None:
            if argument.get("isRequired"):
                raise RenderRefused("required_arguments_not_rendered", "a required argument has no value")
            continue
        value = str(value)
        if credential_shaped(value):
            raise RenderRefused("credential_shaped_value_in_entry", "an argument value looks like a secret")
        if "{" in value or "}" in value:
            raise RenderRefused("required_arguments_not_rendered", "an argument value is a template")
        if argument.get("type") == "named":
            name = str(argument.get("name") or "")
            if not name.startswith("-"):
                raise RenderRefused("required_arguments_not_rendered", "a named argument has no flag")
            rendered += [name, value]
        else:
            rendered.append(value)
    return rendered


def _inputs(variables) -> list:
    rows = []
    for variable in variables or ():
        name = str((variable or {}).get("name") or "") if isinstance(variable, dict) else ""
        if not _ENV_NAME.match(name):
            raise RenderRefused("required_arguments_not_rendered", "an environment variable has no usable name")
        for field in ("value", "default"):
            if variable.get(field) is not None and credential_shaped(str(variable[field])):
                raise RenderRefused("credential_shaped_value_in_entry", f"{name} carries a secret-shaped value")
        rows.append({"name": name, "kind": "environment_variable",
                     "required": bool(variable.get("isRequired")), "secret": bool(variable.get("isSecret"))})
    return rows


def image_reference(identifier: str) -> str:
    """The exact tag or digest a container image identifier names, or empty text when it names none.

    A digest (after @) is exact. A tag is the text after the last colon of the
    last path part, so a registry port (host:5000/name) is not taken for one.
    The floating tag latest names no exact image and yields empty text.
    """
    if "@" in identifier:
        return identifier.rsplit("@", 1)[1]
    last = identifier.rsplit("/", 1)[-1]
    tag = last.rsplit(":", 1)[1] if ":" in last else ""
    return "" if tag == FLOATING_TAG else tag


def _toml_value(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(json.dumps(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(key)} = {json.dumps(item)}" for key, item in value.items()) + " }"
    return json.dumps(value)


def _package_plan(server: dict, key: str) -> dict:
    packages = [row for row in server.get("packages") or () if isinstance(row, dict)]
    stdio = [row for row in packages if (row.get("transport") or {}).get("type") == STDIO
             and row.get("registryType") in _COMMANDS]
    remotes = [row for row in server.get("remotes") or () if isinstance(row, dict)
               and row.get("type") in _REMOTE_TYPES]
    if stdio:
        package = sorted(stdio, key=lambda row: list(_COMMANDS).index(row["registryType"]))[0]
        kind = package["registryType"]
        identifier, version = str(package.get("identifier") or ""), str(package.get("version") or "")
        if kind == OCI and not version:
            version = image_reference(identifier)
        if not _IDENTIFIERS[kind].match(identifier) or not _VERSION.match(version) or version == FLOATING_TAG:
            raise RenderRefused("package_type_not_rendered", "the package identity is not exact")
        runtime, arguments = _arguments(package.get("runtimeArguments")), _arguments(package.get("packageArguments"))
        inputs = _inputs(package.get("environmentVariables"))
        if kind == NPM:
            command, args = _COMMANDS[NPM], ["-y", *runtime, f"{identifier}@{version}", *arguments]
        elif kind == PYPI:
            command, args = _COMMANDS[PYPI], [*runtime, f"{identifier}@{version}", *arguments]
        else:
            image = identifier if image_reference(identifier) else f"{identifier}:{version}"
            flags = [part for row in inputs for part in ("-e", row["name"])]
            command, args = _COMMANDS[OCI], ["run", "-i", "--rm", *flags, *runtime, image, *arguments]
        return {"transport": STDIO, "command": command, "args": args, "inputs": inputs,
                "package": {"registry": kind, "identifier": identifier, "version": version},
                "remote": None, "headers": {}}
    if remotes:
        remote = sorted(remotes, key=lambda row: list(_REMOTE_TYPES).index(row["type"]))[0]
        url = str(remote.get("url") or "")
        parts = split_address(url)
        if parts.scheme != HTTPS_SCHEME or not parts.hostname:
            raise RenderRefused("remote_endpoint_not_https", "the endpoint is not an HTTPS address")
        if credential_shaped(url):
            raise RenderRefused("credential_shaped_value_in_entry", "the endpoint address carries a secret")
        if "{" in url or "}" in url:
            raise RenderRefused("url_template_not_rendered", "the endpoint address is a template")
        headers, inputs = {}, []
        for header in remote.get("headers") or ():
            name = str((header or {}).get("name") or "") if isinstance(header, dict) else ""
            if not _HEADER_NAME.match(name):
                raise RenderRefused("required_arguments_not_rendered", "a header has no usable name")
            value = header.get("value")
            if value is not None and credential_shaped(str(value)):
                raise RenderRefused("credential_shaped_value_in_entry", f"the header {name} carries a secret")
            if value is not None and not header.get("isSecret") and "{" not in str(value):
                headers[name] = (FIXED_VALUE, str(value))
                continue
            variable = re.sub(r"[^A-Z0-9_]", "_", f"{key}_{name}".upper())
            variable = variable if re.match(r"[A-Z_]", variable) else "MCP_" + variable
            headers[name] = (VARIABLE_VALUE, variable)
            inputs.append({"name": variable, "kind": "header", "header": name,
                           "required": bool(header.get("isRequired")), "secret": bool(header.get("isSecret"))})
        return {"transport": remote["type"], "command": None, "args": [], "inputs": inputs, "package": None,
                "remote": {"url": url, "host": parts.hostname}, "headers": headers}
    if server.get("packages"):
        raise RenderRefused("package_type_not_rendered", "no package runs over standard input and output "
                                                         "from npm, PyPI or a container image")
    raise RenderRefused("no_transport_rendered", "the entry names no package and no remote endpoint")


def _harness_files(key: str, plan: dict):
    rendered, skipped = [], []
    if plan["transport"] == STDIO:
        forwarded = [value["name"] for value in plan["inputs"]]
        claude = {"type": STDIO, "command": plan["command"], "args": plan["args"]}
        opencode = {"type": "local", "command": [plan["command"], *plan["args"]], "enabled": True}
        codex = [f"[mcp_servers.{key}]", f"command = {_toml_value(plan['command'])}",
                 f"args = {_toml_value(plan['args'])}"]
        if forwarded:
            claude["env"] = {name: "${" + name + "}" for name in forwarded}
            opencode["environment"] = {name: "{env:" + name + "}" for name in forwarded}
            codex.append(f"env_vars = {_toml_value(forwarded)}")
    else:
        url, headers = plan["remote"]["url"], plan["headers"]
        claude = {"type": _REMOTE_TYPES[plan["transport"]], "url": url}
        opencode = {"type": "remote", "url": url, "enabled": True}
        if headers:
            claude["headers"] = {name: value if how == FIXED_VALUE else "${" + value + "}"
                                 for name, (how, value) in headers.items()}
            opencode["headers"] = {name: value if how == FIXED_VALUE else "{env:" + value + "}"
                                   for name, (how, value) in headers.items()}
        codex = None
        if plan["transport"] == STREAMABLE_HTTP:
            codex = [f"[mcp_servers.{key}]", f"url = {_toml_value(url)}"]
            fixed = {name: value for name, (how, value) in headers.items() if how == FIXED_VALUE}
            referenced = {name: value for name, (how, value) in headers.items() if how == VARIABLE_VALUE}
            if fixed:
                codex.append(f"http_headers = {_toml_value(fixed)}")
            if referenced:
                codex.append(f"env_http_headers = {_toml_value(referenced)}")
        else:
            skipped.append({"harness": CODEX, "reason": "Codex connects to streamable HTTP servers only"})
    texts = {CLAUDE_CODE: json.dumps({"mcpServers": {key: claude}}, indent=2) + "\n",
             OPENCODE: json.dumps({"mcp": {key: opencode}}, indent=2) + "\n"}
    if codex is not None:
        texts[CODEX] = "\n".join(codex) + "\n"
    for harness, path in HARNESS_PATHS:
        if harness in texts:
            data = texts[harness].encode("utf-8")
            rendered.append({"harness": harness, "path": path, "sha256": hashlib.sha256(data).hexdigest(),
                             "text": texts[harness]})
    return rendered, skipped


def _description(name: str, version: str, plan: dict) -> str:
    if plan["transport"] == STDIO:
        package = plan["package"]
        how = (f"It starts on your machine with {plan['command']} from the "
               f"{_REGISTRY_LABELS[package['registry']]} package {package['identifier']}.")
    else:
        how = f"It is reached over {_REMOTE_WORDS[plan['transport']]} at {plan['remote']['host']}."
    needs = ""
    if plan["inputs"]:
        names = [row["name"] + (" (secret)" if row["secret"] else "") for row in plan["inputs"]]
        needs = " It reads these environment variables: " + ", ".join(names) + "."
    return (f"Connection settings for the protocol server {name}, version {version}. {how}{needs} "
            "Baltor wrote these files from the registry entry's facts; the server's code and its "
            "author's text are not included.")


def repository_address(server: dict) -> "str | None":
    """The entry's code repository address, only when it is a plain HTTPS address without a secret."""
    url = str((server.get("repository") or {}).get("url") or "") if isinstance(server.get("repository"), dict) \
        else ""
    if not url or len(url) > _MAXIMUM_ADDRESS_CHARACTERS or "{" in url or "}" in url or credential_shaped(url):
        return None
    try:
        parts = split_address(url)
    except ValueError:
        return None
    if parts.scheme != HTTPS_SCHEME or not parts.hostname or parts.username or parts.password \
            or any(ord(character) < 33 for character in url):
        return None
    return url


def _upstream(name: str, version: str, server: dict, provenance) -> dict:
    """Who the server is and what the licence evidence of its code repository says."""
    evidence = provenance.licence_evidence
    part = evidence.get("repository_licence")
    return {"server_name": name, "server_version": version, "repository_url": repository_address(server),
            "licence_expression": evidence["spdx_expression"], "licence_reason": evidence["reason"],
            "licence_file": {"path": part["path"], "sha256": part["sha256"]} if part else None}


def endpoint_identity(document: dict) -> str:
    """One server's identity for exact duplicates: its package, or else its endpoint address."""
    server = document["server"]
    if server["package"] is not None:
        return f"{server['package']['registry']}:{server['package']['identifier']}".lower()
    parts = split_address(server["endpoint"])
    return f"remote:{parts.scheme}://{(parts.netloc or '').lower()}{parts.path.rstrip('/')}?{parts.query}"


def render_connection(entry: dict, provenance) -> RenderedPackage:
    """The three harness files and one package document for one registry entry."""
    server = entry.get("server") if isinstance(entry, dict) else None
    if not isinstance(server, dict) or not server.get("name") or not server.get("version"):
        raise RenderRefused("entry_unreadable", "the entry has no server name and version")
    name, version = str(server["name"]), str(server["version"])
    key = config_key(name)
    plan = _package_plan(server, key)
    files, skipped = _harness_files(key, plan)
    document = {"record_type": CONNECTION_PACKAGE_RECORD_TYPE,
                "server": {"name": name, "version": version, "transport": plan["transport"],
                           "package": plan["package"],
                           "remote_host": plan["remote"]["host"] if plan["remote"] else None,
                           "endpoint": plan["remote"]["url"] if plan["remote"] else None},
                "upstream": _upstream(name, version, server, provenance),
                "key": key, "description": _description(name, version, plan), "inputs": plan["inputs"],
                "files": files, "harness_files_not_rendered": skipped,
                "topic_words": topic_words(name, str(server.get("description") or ""),
                                           str(server.get("title") or "")),
                "source": {"registry_entry": provenance.repository, "revision": provenance.immutable_revision,
                           "entry_sha256": provenance.source_digest}}
    data = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    all_files = ((DOCUMENT_PATH, data),) + tuple((row["path"], row["text"].encode("utf-8")) for row in files)
    return RenderedPackage(key, DOCUMENT_PATH, all_files, ("generated_from_registry_facts",),
                           f"Connect the {name} protocol server", key, document)

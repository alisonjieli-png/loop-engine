"""Line mcp_registry: one protocol server connection package per server of the official registry.

```text
Official Model Context Protocol registry (registry.modelcontextprotocol.io, latest active entries)
├── read by the library ingestion engine mcp_official_registry (link mode): status active, the latest
│   version, the entry's canonical bytes kept in quarantine with outside_source_provenance/v1
├── upstream licence: GitHub's licence interface and the licence text must agree on an allowlisted
│   licence, read only for entries that name an npm or PyPI package run over standard input and output
├── published package: the exact npm or PyPI version must answer 200 from its public registry, and a
│   licence the package metadata declares must be on the allowlist too
├── connection files written from the entry's facts by the library ingestion renderer (Claude Code
│   .mcp.json, Codex config.toml, OpenCode opencode.json) and here for Cursor (.cursor/mcp.json);
│   the documented shapes are checked by the connection_builtin_rules engine
└── one package: the four files, baltor-connection.json, README.md, LICENSE, ATTRIBUTION.md
```

The author's description and the server's code are never copied: every byte
is written from facts (name, version, package, variable names). A secret is
always a reference to an environment variable, named in `credentials`.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from loop_engine.core.library_ingestion.candidates import REQUEST_RECORD_TYPE
from loop_engine.core.library_ingestion.connection_rendering import render_connection
from loop_engine.core.library_ingestion.effects import declared_effects
from loop_engine.core.library_ingestion.format_connection import ConnectionFileRules
from loop_engine.core.library_ingestion.https_transport import quote_part
from loop_engine.core.library_ingestion.provenance import read_outside_provenance
from loop_engine.core.library_ingestion.quarantine import Quarantine
from loop_engine.core.library_ingestion.record_rules import bytes_digest, now_utc
from loop_engine.core.library_ingestion.rendering_types import RenderRefused
from loop_engine.core.library_ingestion.source_declarations import REGISTRY_ENGINE
from loop_engine.core.library_ingestion.source_mcp_registry import (
    McpOfficialRegistrySource, upstream_github_repository)

from .packaging import LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, CONNECTION_FILES_INVALID, GENERATED_CODE_LICENCE, LICENCE_TEXT, MCP_REGISTRY,
    REFUSAL_REASONS, SupplyRecordError, fact_source, licence_allowed, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.1.0"
REGISTRY_HOST = "registry.modelcontextprotocol.io"
#: The registry engine's reason when GitHub's licence interface and the licence text name different licences.
UPSTREAM_SIGNALS_DISAGREE = "upstream_licence_signals_disagree"
NPM_HOST, PYPI_HOST = "registry.npmjs.org", "pypi.org"
HOSTS = (REGISTRY_HOST, NPM_HOST, PYPI_HOST)
NATIVE_FORMAT = "mcp_connection_bundle"
CURSOR_PATH = ".cursor/mcp.json"
#: What each harness file is and where a person merges it.
HARNESSES = (("claude-code", ".mcp.json", ".mcp.json at the project root"),
             ("codex", ".codex/config.toml", "~/.codex/config.toml or the project's .codex/config.toml"),
             ("opencode", "opencode.json", "opencode.json at the project root"),
             ("cursor", CURSOR_PATH, ".cursor/mcp.json at the project root or ~/.cursor/mcp.json"))
#: Render refusals of the library ingestion renderer this line reports under the same names.
_RENDER_REASONS = {"package_type_not_rendered", "no_transport_rendered", "required_arguments_not_rendered",
                   "credential_shaped_value_in_entry", "url_template_not_rendered", "remote_endpoint_not_https",
                   "server_name_unusable", "entry_unreadable"}
#: PyPI trove classifiers and npm spellings that name an allowlisted licence exactly.
_CLASSIFIERS = {"License :: OSI Approved :: MIT License": "MIT",
                "License :: OSI Approved :: Apache Software License": "Apache-2.0",
                "License :: OSI Approved :: BSD License": "BSD-3-Clause",
                "License :: OSI Approved :: ISC License (ISCL)": "ISC",
                "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication": "CC0-1.0",
                "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense"}


class _CachedGitHub:
    """The registry engine's GitHub reads, through the supply reader's cache and pace."""

    def __init__(self, reader) -> None:
        self.reader = reader

    def get(self, path: str):
        return self.reader.github(path)


def _has_package(server: dict) -> bool:
    return any(isinstance(row, dict) and row.get("registryType") in ("npm", "pypi")
               and (row.get("transport") or {}).get("type") == "stdio" for row in server.get("packages") or ())


class _SupplyRegistrySource(McpOfficialRegistrySource):
    """The registry engine, reading the upstream licence only for entries this line can package."""

    def _link_evidence(self, server: dict) -> "dict | None":
        if not _has_package(server):
            return {"record_type": "outside_licence_evidence/v1", "spdx_expression": "NOASSERTION",
                    "decision": "link_only", "reason": "upstream_licence_not_checked",
                    "detector": "GitHub licence interface for the upstream code repository",
                    "repository_licence": None, "governing_file": None, "file_level_notices": []}
        return super()._link_evidence(server)


def read_registry(reader, quarantine_folder: Path, *, maximum_entries: int, maximum_lookups: int) -> tuple:
    """(candidates with their entries, refusals, complete) of one pass over the registry's latest entries."""
    quarantine = Quarantine(quarantine_folder)
    engine = _SupplyRegistrySource(reader.https, quarantine, github_reader=_CachedGitHub(reader),
                                   maximum_upstream_lookups=maximum_lookups)
    declaration = {"source_id": "mcp_registry_supply", "engine": REGISTRY_ENGINE, "host": REGISTRY_HOST, "use": "link",
                   "maximum_entries": maximum_entries, "exclude_name_prefixes": [],
                   "note": "Supply line of protocol server connections, September 27, 2026."}
    request = {"record_type": REQUEST_RECORD_TYPE, "source_id": "mcp_registry_supply", "cursor": None,
               "maximum_candidates": maximum_entries, "maximum_requests": 2000, "network_reads_authorized": True,
               "requested_at": now_utc()}
    batch = engine.read_candidates(declaration, request)
    found = []
    for candidate in batch["candidates"]:
        source = read_outside_provenance(candidate["provenance"])
        entry = json.loads(quarantine.get(source.source_digest))
        found.append((entry, source))
    refusals = [refusal(MCP_REGISTRY, row["reason"] if row["reason"] in REFUSAL_REASONS[MCP_REGISTRY]
                        else "entry_unreadable", (row.get("source_ref") or {}).get("repository", ""), row["detail"])
                for row in batch["refusals"]]
    return found, refusals, batch["complete"], quarantine


def package_metadata(reader, package: dict) -> dict:
    """What npm or PyPI says of the exact version: published or not, its declared licence and the fact source."""
    registry, identifier, version = package["registry"], package["identifier"], package["version"]
    if registry == "npm":
        url = https_address(NPM_HOST, f"{quote_part(identifier, safe='@')}/{quote_part(version)}")
    else:
        url = https_address(PYPI_HOST, f"pypi/{quote_part(identifier)}/{quote_part(version)}/json")
    answer = reader.get(url, cache_errors=True)
    if answer.status == 404:
        return {"published": False, "url": url}
    if answer.status != 200:
        return {"published": None, "url": url}
    try:
        document = json.loads(answer.body)
    except ValueError:
        return {"published": None, "url": url}
    declared = None
    if registry == "npm":
        value = document.get("license")
        declared = value.get("type") if isinstance(value, dict) else value
    else:
        info = document.get("info") or {}
        declared = info.get("license_expression") or None
        if not declared:
            classifiers = [_CLASSIFIERS[row] for row in info.get("classifiers") or () if row in _CLASSIFIERS]
            declared = classifiers[0] if len(set(classifiers)) == 1 else None
        if not declared and isinstance(info.get("license"), str) and len(info["license"]) <= 64:
            declared = info["license"].strip() or None
    return {"published": True, "url": url, "licence": declared if isinstance(declared, str) else None,
            "sha256": answer.sha256, "size_bytes": len(answer.body), "retrieved_at": answer.retrieved_at}


def _cursor_file(key: str, document: dict, rendered: dict) -> str:
    claude = json.loads(rendered["claude_code"])["mcpServers"][key]
    entry = {"command": claude["command"], "args": claude.get("args", [])}
    names = [row["name"] for row in document["inputs"]]
    if names:
        entry["env"] = {name: "${env:" + name + "}" for name in names}
    return json.dumps({"mcpServers": {key: entry}}, indent=2) + "\n"


def readme(name: str, document: dict, metadata: dict, licence: dict) -> str:
    """README.md, written from facts only: the pinned package, the upstream licence, the settings and placements."""
    server, package = document["server"], document["server"]["package"]
    command = "npx" if package["registry"] == "npm" else "uvx"
    rows = [f"| `{row['name']}` | {'yes' if row['secret'] else 'no'} | {'yes' if row['required'] else 'no'} |"
            for row in document["inputs"]]
    settings = ("\n".join(["| Variable | Secret | Required |", "|---|---|---|", *rows]) if rows
                else "The registry entry names no environment variable.")
    placements = "\n".join(f"| {harness} | `{path}` | {target} |" for harness, path, target in HARNESSES)
    upstream = document["upstream"]
    return f"""# Protocol server connection: {name}

{document['description']}

- Package: {package['registry']} `{package['identifier']}` version `{package['version']}`, pinned.
  The package metadata declares the licence {metadata.get('licence') or 'nothing'}.
- Upstream code: {upstream['repository_url'] or 'not given'} under {licence['spdx']}, decided from
  the licence file `{licence['path']}` (SHA-256 `{licence['sha256']}`) and GitHub's licence
  interface. The code is not included here.
- Registry entry: `{server['name']}` version {server['version']}.

## Settings it reads

{settings}

Set each variable in the environment the harness starts from. A secret is never written into these files;
each file refers to the variable by name.

## Where each file goes

| Harness | File in this package | Merge it into |
|---|---|---|
{placements}

## What running it does

The harness starts the server as a local process with `{command}`, which downloads the pinned
package from {package['registry']} the first time. The registry entry does not declare what the
server itself reads, writes or connects to, so treat it as third-party code that runs with your
permissions.
"""


#: Runtime flags with which an entry names the package or a module itself (uvx --from pkg[extra] command,
#: npx --package pkg, python -m module). The renderer appends the pinned identifier@version after the runtime
#: arguments, so with one of these the package would run unpinned with a stray argument; such an entry is refused.
PACKAGE_NAMING_FLAGS = frozenset({"--from", "--with", "--package", "-p", "-m"})


def names_its_own_package(server: dict) -> bool:
    """Whether a runtime argument of any package of the entry names the package or a module to run."""
    for package in server.get("packages") or ():
        for argument in (package.get("runtimeArguments") or ()) if isinstance(package, dict) else ():
            if isinstance(argument, dict) and ({str(argument.get("name") or ""), str(argument.get("value") or "")}
                                               & PACKAGE_NAMING_FLAGS):
                return True
    return False


def secret_names(document: dict, texts) -> list:
    """The variables a connection passes that are secrets: flagged by the entry, or named like a secret (the
    library ingestion effect rule names_a_secret, read over the variable's name alone)."""
    names = []
    for row in document["inputs"]:
        named = "reads_secret" in declared_effects("protocol_server_configuration", row["name"], {}).effects
        if row["secret"] or named:
            names.append(row["name"])
    return names


def generate(entries, reader, *, code_revision: str, licence_text: bytes, generated_on: str,
             repository_facts: "dict | None" = None) -> tuple:
    """(built, refusals) for the registry entries: one package per server that passes every rule."""
    built, refusals, seen = [], [], {}
    rules = ConnectionFileRules()
    generator = {"identity": "tools/supply_lines/mcp_registry.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    for entry, source in sorted(entries, key=lambda row: row[1].repository):
        server = entry.get("server") or {}
        name = str(server.get("name") or "")
        evidence = source.licence_evidence
        if not _has_package(server):
            reason = "remote_only_server" if server.get("remotes") and not server.get("packages") else \
                "no_npm_or_pypi_package"
            refusals.append(refusal(MCP_REGISTRY, reason, name))
            continue
        repository = upstream_github_repository(server)
        if repository is None:
            refusals.append(refusal(MCP_REGISTRY, "upstream_repository_not_on_github", name))
            continue
        spdx, reason = evidence["spdx_expression"], evidence["reason"]
        if reason == UPSTREAM_SIGNALS_DISAGREE:
            refusals.append(refusal(MCP_REGISTRY, "licence_signals_disagree", name, repository))
            continue
        if spdx in ("NOASSERTION", "NONE"):
            refusals.append(refusal(MCP_REGISTRY, "licence_unknown", name, reason))
            continue
        if not licence_allowed(spdx):
            refusals.append(refusal(MCP_REGISTRY, "licence_not_on_allowlist", name, spdx))
            continue
        part = evidence.get("repository_licence") or {}
        if not part.get("sha256"):
            refusals.append(refusal(MCP_REGISTRY, "licence_unknown", name, "no licence file digest"))
            continue
        if names_its_own_package(server):
            refusals.append(refusal(MCP_REGISTRY, "required_arguments_not_rendered", name,
                                    "a runtime argument names the package or a module; the pinned version would "
                                    "not apply to it"))
            continue
        try:
            rendered = render_connection(entry, source)
        except RenderRefused as error:
            code = error.code if error.code in _RENDER_REASONS else "entry_unreadable"
            refusals.append(refusal(MCP_REGISTRY, code, name, error.detail))
            continue
        document = dict(rendered.document)
        package = document["server"]["package"]
        if package is None or package["registry"] not in ("npm", "pypi"):
            refusals.append(refusal(MCP_REGISTRY, "no_npm_or_pypi_package", name))
            continue
        identity = f"{package['registry']}:{package['identifier']}".lower()
        if identity in seen:
            refusals.append(refusal(MCP_REGISTRY, "duplicate_package", name, f"kept {seen[identity]}"))
            continue
        metadata = package_metadata(reader, package)
        if metadata["published"] is False:
            refusals.append(refusal(MCP_REGISTRY, "package_version_not_published", name, metadata["url"]))
            continue
        if metadata["published"] is None:
            refusals.append(refusal(MCP_REGISTRY, "package_version_unknown", name, metadata["url"]))
            continue
        if metadata.get("licence") and not licence_allowed(metadata["licence"]):
            refusals.append(refusal(MCP_REGISTRY, "package_licence_not_on_allowlist", name, metadata["licence"]))
            continue
        texts = {row["harness"]: row["text"] for row in document["files"]}
        cursor = _cursor_file(rendered.key, document, texts)
        document["files"] = list(document["files"]) + [{"harness": "cursor", "path": CURSOR_PATH,
                                                         "sha256": bytes_digest(cursor.encode()), "text": cursor}]
        problems = rules.validate_package(document)
        if problems:
            refusals.append(refusal(MCP_REGISTRY, "connection_files_invalid", name, "; ".join(problems)))
            continue
        document["package_metadata"] = {"url": metadata["url"], "licence": metadata.get("licence"),
                                        "sha256": metadata["sha256"]}
        document["server_effects"] = "not declared by the registry entry; the server is third-party code"
        licence_view = {"spdx": spdx, "path": part.get("path"), "sha256": part.get("sha256")}
        stars = ((repository_facts or {}).get(repository.lower()) or {}).get("stargazerCount") or 0
        files = [PackageFile(".mcp.json", texts["claude_code"].encode(), "protocol_server_configuration"),
                 PackageFile("opencode.json", texts["opencode"].encode(), "protocol_server_configuration"),
                 PackageFile(CURSOR_PATH, cursor.encode(), "protocol_server_configuration"),
                 PackageFile("baltor-connection.json",
                             (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode(), "other"),
                 PackageFile("README.md", readme(name, document, metadata, licence_view).encode(), "other"),
                 PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT)]
        if "codex" in texts:
            files.append(PackageFile(".codex/config.toml", texts["codex"].encode(), "protocol_server_configuration"))
        facts = [fact_source(https_address(REGISTRY_HOST, source.path), source.fetched_at, source.source_digest,
                             source.source_size_bytes, "registry_entry", spdx="NOASSERTION",
                             basis="link_only_facts_no_text_copied"),
                 fact_source(github_blob_address(repository, "HEAD", part.get("path") or "LICENSE"),
                             source.fetched_at, part["sha256"], 0, "licence_text", spdx=spdx,
                             basis="github_licence_interface_and_text_agree", evidence_sha256=part["sha256"]),
                 fact_source(metadata["url"], metadata["retrieved_at"], metadata["sha256"], metadata["size_bytes"],
                             "package_metadata", spdx=metadata.get("licence") or "NOASSERTION",
                             basis="package_metadata_declaration")]
        effects = [("spawns_process", "starts_a_local_server_process"),
                   ("network", "downloads_the_pinned_package_when_started")]
        secrets = secret_names(document, texts)
        found = declared_effects("protocol_server_configuration", "\n".join(texts.values()), {}, connection=document)
        if secrets or "reads_secret" in found.effects:
            effects.append(("reads_secret", "reads_secret_inputs_from_named_environment_variables"))
        placements = [{"harness": "upstream", "path": source.path, "basis": "registry_entry", "scope": "upstream",
                       "support": "unverified"}] + [
            {"harness": harness, "path": path, "basis": "documented_layout", "scope": "project",
             "support": "unverified"} for harness, path, _target in HARNESSES if path in {row.path for row in files}]
        supply = SupplyPackage(
            line=MCP_REGISTRY, identity=name, key=upstream_key(MCP_REGISTRY, name), kind="protocol_server_configuration",
            native_format=NATIVE_FORMAT, form="mcp_server", name=rendered.key, description=document["description"],
            files=files, licence_expression=GENERATED_CODE_LICENCE,
            provenance=provenance("mcp_official_registry", repository, source.path, source.immutable_revision,
                                  facts, generator),
            placements=placements, effects=effects, credentials=secrets,
            tests={"checks": ["connection_builtin_rules"], "result": "passed", "network": False},
            repository={"name": repository, "stars": stars, "upstream_licence": spdx,
                        "package": f"{package['registry']}:{package['identifier']}@{package['version']}"},
            generated_on=generated_on, comparison_text=identity)
        try:
            built.append(build(supply))
        except SupplyRecordError as error:
            code = error.code if error.code == BLOCKED_BY_STATIC_CHECK else CONNECTION_FILES_INVALID
            refusals.append(refusal(MCP_REGISTRY, code, name, str(error)))
            continue
        seen[identity] = name
    return built, refusals


def counts(refusals) -> dict:
    return dict(Counter(row["reason"] for row in refusals).most_common())

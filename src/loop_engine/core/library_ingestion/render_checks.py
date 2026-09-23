"""Known-wrong checks for rendering outside items into native files and validating them.

The checks require: an imported skill keeps its body byte for byte, carries
its licence, source identity and change note in the Agent Skills fields and
its licence file beside it; a skill whose name, description or frontmatter
breaks the specification is refused by the built-in rules; a connection
file never carries a secret value, only a reference to one; a plain HTTP
endpoint, a credential-shaped value and required arguments without a value
are refused by name; no author text from a registry entry reaches a
rendered file; and each harness file keeps its documented shape.
"""
from __future__ import annotations

import json

from .connection_rendering import render_connection
from .format_builtin import AgentSkillsBuiltinRules
from .format_connection import ConnectionFileRules
from .provenance_checks import fixture_provenance, fixture_registry_provenance
from .provenance import read_outside_provenance
from .rendering_types import RenderRefused
from .skill_rendering import parse_skill, render_instruction, render_skill

UPSTREAM_SKILL = """---
name: Systematic_Debugging
description: Use when a test fails for a reason you do not yet understand.
version: 2.1.0
tags: [debugging, testing]
license: MIT
---

# Systematic debugging

1. Reproduce the failure and write down the exact command.
2. Form one hypothesis at a time and test it with the smallest change.
3. Keep the failing test until the fix makes it pass for the stated reason.
"""


def _entry(**server_overrides) -> dict:
    server = {"name": "io.github.example/weather", "version": "1.2.0",
              "description": "Author words about weather that must never be copied verbatim.",
              "packages": [{"registryType": "npm", "identifier": "@example/weather-mcp",
                            "version": "1.2.0", "transport": {"type": "stdio"},
                            "environmentVariables": [
                                {"name": "WEATHER_API_KEY", "isRequired": True, "isSecret": True,
                                 "description": "Key for the weather service"},
                                {"name": "WEATHER_UNITS", "isRequired": False,
                                 "description": "metric or imperial"}]}]}
    server.update(server_overrides)
    return {"server": server, "_meta": {"io.modelcontextprotocol.registry/official": {
        "status": "active", "publishedAt": "2026-09-01T10:00:00.123456Z", "isLatest": True}}}


def _refused(action) -> str:
    try:
        action()
    except RenderRefused as error:
        return error.code
    return ""


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:300]})

    provenance = read_outside_provenance(fixture_provenance())
    parsed = parse_skill(UPSTREAM_SKILL)
    package = render_skill(parsed, provenance, licence_file=("LICENSE", b"MIT licence text\n"))
    main = package.main_text
    rendered = parse_skill(main)
    check("an_imported_skill_keeps_its_body_byte_for_byte",
          rendered.body == parsed.body and main.endswith(parsed.body), package.changes)
    metadata = rendered.frontmatter["metadata"]
    check("attribution_travels_in_the_allowed_fields_and_the_licence_file_beside_the_skill",
          rendered.frontmatter["license"] == "MIT" and rendered.frontmatter["name"] == "systematic-debugging"
          and set(rendered.frontmatter) <= {"name", "description", "license", "compatibility",
                                            "allowed-tools", "metadata"}
          and metadata["baltor-source-repository"] == "github.com/example-owner/example-skills"
          and metadata["baltor-source-commit"] == provenance.immutable_revision
          and metadata["upstream-version"] == "2.1.0" and "baltor-changes" in metadata
          and dict(package.files)["systematic-debugging/LICENSE"] == b"MIT licence text\n", metadata)

    rules = AgentSkillsBuiltinRules()
    clean = rules.validate_skill(package.folder, main)
    broken = {
        "name_mismatch": rules.validate_skill("another-name", main),
        "bad_name": rules.validate_skill("Bad--Name", main.replace("systematic-debugging", "Bad--Name")),
        "long_description": rules.validate_skill(package.folder, main.replace(
            "Use when a test fails", "Use when " + "a test fails " * 90)),
        "unknown_field": rules.validate_skill(package.folder, main.replace("license: MIT",
                                                                          "license: MIT\nversion: 1.0")),
        "no_frontmatter": rules.validate_skill(package.folder, "# Just a heading\n"),
    }
    check("a_skill_that_breaks_the_specification_is_refused_by_the_built_in_rules",
          clean == [] and all(problems for problems in broken.values()), broken)

    missing = _refused(lambda: render_skill(parse_skill("---\nname: x-y\n---\nbody\n"), provenance,
                                            licence_file=("LICENSE", b"text")))
    no_frontmatter = _refused(lambda: parse_skill("# No frontmatter\n"))
    check("a_skill_without_a_description_or_frontmatter_is_refused_by_name",
          (missing, no_frontmatter) == ("description_missing", "frontmatter_missing"))

    instruction = render_instruction("---\napplyTo: '**/*.py'\n---\nUse type hints.\n", provenance,
                                     "copilot_instructions", "python", ("LICENSE", b"MIT text\n"))
    check("an_instruction_file_is_copied_verbatim_to_its_native_path",
          instruction.main_path == ".github/instructions/python.instructions.md"
          and instruction.main_text == "---\napplyTo: '**/*.py'\n---\nUse type hints.\n")

    registry = read_outside_provenance(fixture_registry_provenance())
    connection = render_connection(_entry(), registry)
    files = {row["harness"]: row for row in connection.document["files"]}
    everything = json.dumps(connection.document)
    claude = json.loads(files["claude_code"]["text"])["mcpServers"]
    opencode = json.loads(files["opencode"]["text"])["mcp"]
    check("a_connection_file_carries_a_reference_to_a_secret_never_a_value",
          claude[connection.key]["env"]["WEATHER_API_KEY"] == "${WEATHER_API_KEY}"
          and opencode[connection.key]["environment"]["WEATHER_API_KEY"] == "{env:WEATHER_API_KEY}"
          and 'env_vars = ["WEATHER_API_KEY", "WEATHER_UNITS"]' in files["codex"]["text"]
          and connection.document["inputs"][0]["secret"] is True, files["codex"]["text"])
    check("no_author_text_from_a_registry_entry_reaches_a_rendered_file",
          "Author words" not in everything and "never be copied" not in everything
          and "Key for the weather service" not in everything)
    check("every_harness_file_keeps_its_documented_shape",
          ConnectionFileRules().validate_package(connection.document) == []
          and claude[connection.key]["args"] == ["-y", "@example/weather-mcp@1.2.0"]
          and opencode[connection.key]["command"][:2] == ["npx", "-y"], connection.key)

    remote = render_connection(_entry(packages=[], remotes=[{
        "type": "streamable-http", "url": "https://weather.example/mcp",
        "headers": [{"name": "Authorization", "isSecret": True, "description": "Bearer token"}]}]), registry)
    remote_files = {row["harness"]: json.loads(row["text"]) if row["harness"] != "codex" else row["text"]
                    for row in remote.document["files"]}
    check("a_secret_header_becomes_an_environment_reference_in_every_harness",
          remote_files["claude_code"]["mcpServers"][remote.key]["headers"]["Authorization"].startswith("${")
          and remote_files["opencode"]["mcp"][remote.key]["headers"]["Authorization"].startswith("{env:")
          and "env_http_headers" in remote_files["codex"])

    evidence = registry.licence_evidence
    linked = render_connection(_entry(repository={"url": "https://github.com/example/weather-mcp",
                                                  "source": "github"}), registry).document
    unlinked = render_connection(_entry(repository={"url": "http://example.invalid/weather"}),
                                 registry).document
    check("a_connection_document_carries_the_upstream_licence_and_identity",
          linked.get("upstream") == {
              "server_name": "io.github.example/weather", "server_version": "1.2.0",
              "repository_url": "https://github.com/example/weather-mcp",
              "licence_expression": evidence["spdx_expression"], "licence_reason": evidence["reason"],
              "licence_file": {"path": evidence["repository_licence"]["path"],
                               "sha256": evidence["repository_licence"]["sha256"]}}
          and (unlinked.get("upstream") or {}).get("repository_url", "missing") is None,
          linked.get("upstream"))

    plain_http = _refused(lambda: render_connection(_entry(packages=[], remotes=[
        {"type": "streamable-http", "url": "http://weather.example/mcp"}]), registry))
    fake_key = "sk-" + "a1b2c3d4e5" * 3
    shaped = _refused(lambda: render_connection(_entry(packages=[], remotes=[
        {"type": "streamable-http", "url": f"https://weather.example/mcp?key={fake_key}"}]), registry))
    required = _refused(lambda: render_connection(_entry(packages=[{
        "registryType": "npm", "identifier": "weather", "version": "1.0.0", "transport": {"type": "stdio"},
        "packageArguments": [{"type": "positional", "isRequired": True, "valueHint": "path"}]}]), registry))
    unsupported = _refused(lambda: render_connection(_entry(packages=[{
        "registryType": "nuget", "identifier": "Weather", "version": "1.0.0",
        "transport": {"type": "stdio"}}]), registry))
    check("unsafe_or_unrenderable_entries_are_refused_by_name",
          (plain_http, shaped, required, unsupported)
          == ("remote_endpoint_not_https", "credential_shaped_value_in_entry",
              "required_arguments_not_rendered", "package_type_not_rendered"),
          (plain_http, shaped, required, unsupported))

    def image(identifier, version=None):
        package = {"registryType": "oci", "identifier": identifier, "transport": {"type": "stdio"}}
        if version is not None:
            package["version"] = version
        return _entry(packages=[package])

    tagged = render_connection(image("docker.io/example/weather:1.4.2"), registry)
    pinned = render_connection(image("ghcr.io/example/weather@sha256:" + "ab" * 32), registry)
    floating = _refused(lambda: render_connection(image("docker.io/example/weather:latest"), registry))
    untagged = _refused(lambda: render_connection(image("docker.io/example/weather"), registry))
    tagged_args = json.loads({row["harness"]: row for row in tagged.document["files"]}["claude_code"]["text"])
    check("a_container_image_named_by_an_exact_tag_or_digest_is_rendered_and_a_floating_one_is_refused",
          tagged_args["mcpServers"][tagged.key]["args"][-1] == "docker.io/example/weather:1.4.2"
          and tagged.document["server"]["package"]["version"] == "1.4.2"
          and pinned.document["server"]["package"]["version"] == "sha256:" + "ab" * 32
          and (floating, untagged) == ("package_type_not_rendered", "package_type_not_rendered"),
          (tagged.document["server"]["package"], floating, untagged))

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "library_render_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}

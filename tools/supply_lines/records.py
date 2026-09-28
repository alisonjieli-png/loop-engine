"""Records of the supply lines, each written name/vN and read strictly.

A supply line turns licensed facts (a registry entry, an API specification,
a package formula, a data file) into packages Baltor writes itself: protocol
server connections, API operation clients, program install recipes and data
tables. The facts are pinned (address, retrieval time, SHA-256, revision) and
each carries its licence evidence; the generated files carry the generator's
identity and version. Nothing here approves anything: every package is a
candidate until an independent review reads its exact bytes.

```text
library_supply_candidate/v1 (one package version)
├── line, kind (a served harness kind), native format, component_form/v1 (declared)
├── package: catalogue_package/v1 with every file's origin (generated, upstream_verbatim,
│   licence_text or attribution)
├── licence: the package's SPDX expression, the licence texts and ATTRIBUTION.md inside it
├── provenance: library_supply_provenance/v1
│   ├── origin, repository (the upstream the package points at), path, immutable revision
│   ├── facts: library_supply_fact_source/v1, each with its address, time, digest and licence
│   └── generator: its module, version and code revision
├── declared effects with the rule behind each, credentials by name only, tests to run
└── authoring generated_from_licensed_facts, lifecycle candidate, evidence states
```
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME
from loop_engine.core.library_ingestion.record_rules import canonical_digest
from loop_engine.core.service_runtime.catalogue_attributes import (
    FORM_DECLARED, ComponentFormError, read_component_form)
from loop_engine.core.facets import EFFECTS

CANDIDATE_RECORD_TYPE = "library_supply_candidate/v1"
PROVENANCE_RECORD_TYPE = "library_supply_provenance/v1"
FACT_SOURCE_RECORD_TYPE = "library_supply_fact_source/v1"
REFUSAL_RECORD_TYPE = "library_supply_refusal/v1"
STATE_RECORD_TYPE = "library_supply_state/v1"
RUN_RECORD_TYPE = "library_supply_run/v1"

#: The supply lines, one per kind of fact source.
MCP_REGISTRY, OPENAPI_OPERATIONS, PROGRAM_INSTALLS, DATA_TABLES, FUNCTION_EXTRACTS = LINES = (
    "mcp_registry", "openapi_operations", "program_installs", "data_tables", "function_extracts")
#: How the text of every supply package was authored, and the review profile it needs. The panel has no such
#: profile yet (tools/candidate_review reads original and imported packages only), so an export holds these.
AUTHORING = "generated_from_licensed_facts"
REVIEW_PROFILE = "generated_from_licensed_facts/v1"
#: Where each file of a package came from.
GENERATED, UPSTREAM_VERBATIM, LICENCE_TEXT, ATTRIBUTION = FILE_ORIGINS = (
    "generated", "upstream_verbatim", "licence_text", "attribution")
#: Where the facts came from; each names the host the facts were read from.
ORIGINS = {"mcp_official_registry": "registry.modelcontextprotocol.io", "github_repository": "github.com",
           "homebrew_formulae": "formulae.brew.sh", "apis_guru_directory": "api.apis.guru"}
#: What one fact source is to the package.
FACT_ROLES = ("registry_entry", "package_metadata", "specification", "formula", "release", "licence_text",
              "data_source", "repository_facts", "analytics")
#: The owner's allowlist of September 24, 2026 (tools/licensed_import/records.py ALLOWED_LICENCES).
ALLOWED_LICENCES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "CC0-1.0", "CC-BY-4.0",
                    "Unlicense")
#: The licence of every file Baltor's generators write (this repository's licence).
GENERATED_CODE_LICENCE = "MIT"
#: Reasons several lines give, named once so code compares against the vocabulary, never a spelled token.
BLOCKED_BY_STATIC_CHECK, GENERATED_TEST_FAILED, PACKAGE_ABOVE_REVIEW_BOUND, CONNECTION_FILES_INVALID = (
    "blocked_by_static_check", "generated_test_failed", "package_above_review_bound", "connection_files_invalid")
#: Why a line leaves a candidate out, per line; a closed vocabulary so a report can count them.
REFUSAL_REASONS = {
    MCP_REGISTRY: ("registry_status_not_active", "registry_entry_not_latest", "entry_unreadable",
                   "excluded_by_declaration", "server_name_unusable", "upstream_repository_unreadable",
                   "upstream_repository_not_on_github", "licence_unknown", "licence_signals_disagree",
                   "licence_not_on_allowlist", "no_npm_or_pypi_package", "package_type_not_rendered",
                   "remote_only_server", "no_transport_rendered", "required_arguments_not_rendered",
                   "credential_shaped_value_in_entry", "url_template_not_rendered", "remote_endpoint_not_https",
                   "package_version_not_published", "package_version_unknown", "package_licence_not_on_allowlist",
                   "duplicate_package", "blocked_by_static_check", "connection_files_invalid"),
    OPENAPI_OPERATIONS: ("specification_unreadable", "specification_version_unsupported", "licence_not_on_allowlist",
                         "licence_signals_disagree", "licence_unknown", "operation_identity_missing",
                         "operation_body_not_json", "operation_parameters_unsupported", "security_scheme_unsupported",
                         "example_not_constructible", "duplicate_operation", "blocked_by_static_check",
                         "generated_test_failed", "package_above_review_bound", "covered_by_a_curated_source",
                         "preview_beside_its_stable_release"),
    PROGRAM_INSTALLS: ("formula_licence_not_on_allowlist", "formula_deprecated_or_disabled", "not_a_command_line_program",
                       "no_published_checksum", "upstream_repository_unreadable", "licence_signals_disagree",
                       "blocked_by_static_check", "generated_test_failed", "duplicate_program"),
    DATA_TABLES: ("source_unreadable", "licence_not_on_allowlist", "licence_signals_disagree", "table_empty",
                  "row_violates_schema", "table_above_review_bound", "blocked_by_static_check",
                  "generated_test_failed"),
    FUNCTION_EXTRACTS: ("source_unreadable", "licence_not_on_allowlist", "licence_signals_disagree", "licence_unknown",
                        "no_examples", "closure_unresolved", "needs_a_dependency", "closure_too_large",
                        "closure_name_conflict", "examples_failed", "examples_do_not_exercise_the_function",
                        "duplicate_function", "blocked_by_static_check", "generated_test_failed",
                        "package_above_review_bound"),
}
#: The forms each line may declare, and the harness kind it serves them as.
LINE_FORMS = {MCP_REGISTRY: {"mcp_server": "protocol_server_configuration"},
              OPENAPI_OPERATIONS: {"api_operation": "code_module"},
              PROGRAM_INSTALLS: {"binary_install": "code_module", "program": "code_module"},
              DATA_TABLES: {"data_table": "code_module"},
              FUNCTION_EXTRACTS: {"function": "code_module"}}
CANDIDATE_FIELDS = ("record_type", "record_id", "upstream_key", "line", "kind", "native_format", "component_form",
                    "name", "description", "package", "package_digest", "files", "licence", "provenance",
                    "placements", "declared_effects", "effect_evidence", "credentials", "tests", "findings",
                    "authoring", "review_profile", "lifecycle", "qualification", "generated_on", "repository",
                    "sources", "merged", "comparison", "version", "evidence")
PROVENANCE_FIELDS = ("record_type", "origin", "origin_host", "repository", "path", "immutable_revision", "facts",
                     "generator")
FACT_FIELDS = ("record_type", "url", "retrieved_at", "sha256", "size_bytes", "role", "licence")
_KEY = re.compile(r"[0-9a-f]{24}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SPDX_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}\Z")


class SupplyRecordError(ValueError):
    """A supply record that cannot be true, with a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def licence_allowed(expression: str) -> bool:
    """True when an SPDX expression lets the package be copied under the owner's allowlist.

    OR needs one allowed branch, AND needs every part allowed; WITH (an exception) and anything unparsed is
    refused rather than guessed."""
    text = str(expression or "").strip()
    if not text or "WITH" in text.split():
        return False
    text = text.replace("(", " ( ").replace(")", " ) ")
    tokens = text.split()

    def parse(position):
        value, position = term(position)
        while position < len(tokens) and tokens[position] == "OR":
            right, position = term(position + 1)
            value = value or right
        return value, position

    def term(position):
        value, position = atom(position)
        while position < len(tokens) and tokens[position] == "AND":
            right, position = atom(position + 1)
            value = value and right
        return value, position

    def atom(position):
        if position >= len(tokens):
            raise SupplyRecordError("licence_expression_invalid", expression)
        if tokens[position] == "(":
            value, position = parse(position + 1)
            if position >= len(tokens) or tokens[position] != ")":
                raise SupplyRecordError("licence_expression_invalid", expression)
            return value, position + 1
        if not _SPDX_ID.match(tokens[position]) or tokens[position] in ("AND", "OR", ")"):
            raise SupplyRecordError("licence_expression_invalid", expression)
        return tokens[position] in ALLOWED_LICENCES, position + 1

    try:
        value, position = parse(0)
    except SupplyRecordError:
        return False
    return bool(value) and position == len(tokens)


def upstream_key(line: str, identity: str) -> str:
    """The stable identity of one supplied component: the same server, operation, program or table."""
    if line not in LINES:
        raise SupplyRecordError("line_unknown", line)
    return canonical_digest({"line": line, "identity": identity})[:24]


def record_id(line: str, key: str, package_digest: str) -> str:
    if line not in LINES or not _KEY.match(key) or not _DIGEST.match(package_digest):
        raise SupplyRecordError("record_identity_invalid", f"{line}/{key}")
    return f"library.supply.{line}.{key}.{package_digest[:16]}"


#: The state scopes of a line. A line written by two modes keeps one state per mode, so a complete run of one
#: mode never withdraws what the other supplies (the curated and the directory mode of the API line).
STATE_SCOPES = ("", "apis_guru_directory", "google_discovery")


def state_record_id(line: str, scope: str = "") -> str:
    if line not in LINES:
        raise SupplyRecordError("line_unknown", line)
    if scope not in STATE_SCOPES:
        raise SupplyRecordError("state_scope_unknown", scope)
    return f"library.supply.state.{line}" + (f".{scope}" if scope else "")


def refusal(line: str, reason: str, subject: str, detail: str = "") -> dict:
    """One left-out candidate with a reason from the line's closed vocabulary."""
    if reason not in REFUSAL_REASONS.get(line, ()):
        raise SupplyRecordError("refusal_reason_unknown", f"{line}: {reason}")
    return {"record_type": REFUSAL_RECORD_TYPE, "line": line, "reason": reason, "subject": str(subject)[:300],
            "detail": str(detail)[:300]}


def fact_source(url: str, retrieved_at: str, sha256: str, size_bytes: int, role: str, *, spdx: str,
                basis: str, evidence_sha256: "str | None" = None) -> dict:
    """One pinned fact source: where the facts were read, when, their digest and the licence they carry."""
    if role not in FACT_ROLES:
        raise SupplyRecordError("fact_role_unknown", role)
    if not _DIGEST.match(str(sha256)) or type(size_bytes) is not int or size_bytes < 0:
        raise SupplyRecordError("fact_digest_invalid", url)
    if urlsplit(str(url)).scheme != HTTPS_SCHEME:
        raise SupplyRecordError("fact_address_invalid", "a fact source is an HTTPS address")
    return {"record_type": FACT_SOURCE_RECORD_TYPE, "url": url, "retrieved_at": retrieved_at, "sha256": sha256,
            "size_bytes": size_bytes, "role": role,
            "licence": {"spdx_expression": spdx, "basis": basis, "evidence_sha256": evidence_sha256}}


def provenance(origin: str, repository: str, path: str, revision: str, facts, generator: dict) -> dict:
    if origin not in ORIGINS:
        raise SupplyRecordError("origin_unknown", origin)
    if not facts:
        raise SupplyRecordError("facts_missing", "a supplied package names the facts it was written from")
    if set(generator) != {"identity", "version", "code_revision"}:
        raise SupplyRecordError("generator_invalid", "a generator names its identity, version and code revision")
    return {"record_type": PROVENANCE_RECORD_TYPE, "origin": origin, "origin_host": ORIGINS[origin],
            "repository": repository, "path": path, "immutable_revision": revision, "facts": list(facts),
            "generator": dict(generator)}


def read_supply_candidate(value) -> dict:
    """The candidate, or a refusal of another version, a missing or unknown field, or a claim that cannot hold."""
    if not isinstance(value, dict) or value.get("record_type") != CANDIDATE_RECORD_TYPE:
        found = value.get("record_type") if isinstance(value, dict) else None
        raise SupplyRecordError("candidate_version_unsupported", f"expected {CANDIDATE_RECORD_TYPE}, found {found!r}")
    if set(value) != set(CANDIDATE_FIELDS):
        raise SupplyRecordError("candidate_fields_invalid",
                                f"unknown {sorted(set(value) - set(CANDIDATE_FIELDS))}, "
                                f"missing {sorted(set(CANDIDATE_FIELDS) - set(value))}")
    line = value["line"]
    if line not in LINES:
        raise SupplyRecordError("line_unknown", str(line))
    try:
        form = read_component_form(value["component_form"], value["kind"])
    except ComponentFormError as error:
        raise SupplyRecordError(error.code, str(error)) from None
    if value["component_form"]["basis"] != FORM_DECLARED or LINE_FORMS[line].get(form) != value["kind"]:
        raise SupplyRecordError("line_form_mismatch", f"the {line} line declares {sorted(LINE_FORMS[line])}")
    if value["authoring"] != AUTHORING or value["review_profile"] != REVIEW_PROFILE:
        raise SupplyRecordError("authoring_invalid", "a supplied package is generated from licensed facts")
    if value["lifecycle"] != "candidate" or value["qualification"] != "not_independently_reviewed":
        raise SupplyRecordError("lifecycle_invalid", "a supply line writes candidates only")
    if not _KEY.match(str(value["upstream_key"])) or value["record_id"] != record_id(
            line, value["upstream_key"], value["package_digest"]):
        raise SupplyRecordError("record_identity_invalid", str(value["record_id"]))
    licence = value["licence"]
    if not licence_allowed(licence.get("spdx_expression", "")):
        raise SupplyRecordError("licence_not_on_allowlist", str(licence.get("spdx_expression")))
    paths = {entry["path"]: entry for entry in value["package"]["files"]}
    if (not licence.get("texts") or any(path not in paths for path in licence["texts"])
            or licence.get("attribution") not in paths):
        raise SupplyRecordError("licence_files_missing", "the licence texts and the attribution are package files")
    origins = {row["path"]: row["origin"] for row in value["files"]}
    if set(origins) != set(paths) or any(origin not in FILE_ORIGINS for origin in origins.values()):
        raise SupplyRecordError("file_origins_invalid", "every package file names where it came from")
    source = value["provenance"]
    if not isinstance(source, dict) or source.get("record_type") != PROVENANCE_RECORD_TYPE \
            or set(source) != set(PROVENANCE_FIELDS) or source["origin"] not in ORIGINS \
            or source["origin_host"] != ORIGINS[source["origin"]]:
        raise SupplyRecordError("provenance_invalid", "the provenance names its origin, host, facts and generator")
    for fact in source["facts"]:
        if not isinstance(fact, dict) or fact.get("record_type") != FACT_SOURCE_RECORD_TYPE \
                or set(fact) != set(FACT_FIELDS) or fact["role"] not in FACT_ROLES:
            raise SupplyRecordError("fact_source_invalid", "every fact names its address, time, digest and licence")
    if any(effect not in EFFECTS for effect in value["declared_effects"]) or not value["declared_effects"]:
        raise SupplyRecordError("effects_invalid", f"effects are drawn from {EFFECTS}")
    if any(not re.fullmatch(r"[A-Z_][A-Z0-9_]{0,127}", str(name)) for name in value["credentials"]):
        raise SupplyRecordError("credentials_invalid", "a credential is named by its environment variable only")
    return value

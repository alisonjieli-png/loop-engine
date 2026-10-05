"""From result rows to candidates: one identity per thing, the licence as reported, and the line it is proposed to.

```text
result row (executor.parse)
├── candidate key        github:owner/repo, github-file:owner/repo/path, hf-model:, hf-dataset:, doi:,
│                        openverse:, gbif-dataset:, europa:, datagov:, npm:, web:<canonical address>
├── licence_reported     exactly what the source said, and which field said it
├── licence_lead         the SPDX identifier that report names, when it names exactly one; allowlisted or not
└── route                a supply line that has a source file today, or a pool for a line that does not exist yet
    ├── openapi_sources      an OpenAPI, Swagger or AsyncAPI file in a public GitHub repository
    ├── json_schema_sources  a JSON Schema file (or a repository that declares itself one)
    ├── data_tables          a CSV, TSV or JSON table file in a public GitHub repository, or a portal dataset
    │                        with a tabular distribution (the line reads GitHub today; portal rows wait for a reader)
    ├── function_sources     a Python library that says it carries doctests
    ├── programs             a command-line program (the line still needs its Homebrew formula and release check)
    └── pools                model_pool, dataset_pool, media_pool, paper_pool, package_pool, harness_file_pool,
                             harness_repository_pool, python_library_pool, code_file_pool, repository_pool,
                             web_lead_pool
```

A route is a proposal, never an admission: every line decides the licence again from the licence text at the
pinned commit when it generates, and a row whose reported licence is off the allowlist is still recorded (as a
lead with its reason) so the count of what the probes found stays complete.
"""
from __future__ import annotations

import re

from supply_lines.records import ALLOWED_LICENCES, licence_allowed

LINES = ("openapi_sources", "json_schema_sources", "data_tables", "function_sources", "programs")
POOLS = ("model_pool", "dataset_pool", "media_pool", "paper_pool", "package_pool", "harness_file_pool",
         "harness_repository_pool", "python_library_pool", "code_file_pool", "repository_pool", "web_lead_pool")
LINE_FILES = {"openapi_sources": "tools/supply_lines/openapi_sources.json",
              "json_schema_sources": "tools/supply_lines/json_schema_sources.json",
              "data_tables": "tools/supply_lines/data_table_sources.json",
              "function_sources": "tools/supply_lines/function_sources.json",
              "programs": "tools/supply_lines/program_sources.json"}
_LOWER = {licence.lower(): licence for licence in ALLOWED_LICENCES}
_ALIASES = {"apache2": "Apache-2.0", "apache 2.0": "Apache-2.0", "apache license 2.0": "Apache-2.0", "mit license": "MIT",
            "cc0": "CC0-1.0", "cc-0": "CC0-1.0", "cc0 1.0": "CC0-1.0", "cc_by_4_0": "CC-BY-4.0", "cc-by 4.0": "CC-BY-4.0",
            "cc by 4.0": "CC-BY-4.0", "bsd-3": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause", "bsd-2": "BSD-2-Clause",
            "the unlicense": "Unlicense", "unlicense": "Unlicense", "isc license": "ISC"}
_URLS = ((re.compile(r"creativecommons\.org/publicdomain/zero/1\.0"), "CC0-1.0"),
         (re.compile(r"creativecommons\.org/licenses/by/4\.0"), "CC-BY-4.0"),
         (re.compile(r"/cc-by/4\.0\b"), "CC-BY-4.0"),
         (re.compile(r"opensource\.org/licenses/mit\b"), "MIT"),
         (re.compile(r"apache\.org/licenses/license-2\.0"), "Apache-2.0"),
         (re.compile(r"\bcc_by_4_0\b"), "CC-BY-4.0"))
#: Reports that name a licence family but not its version: never the allowlisted CC-BY-4.0 by assumption.
_VERSIONLESS = {"cc-by": "CC-BY (version not reported)", "by": "CC-BY (version not reported)"}


def licence_lead(reported) -> tuple:
    """(identifier or label, allowlisted, basis) for one report. A lead, not a licence decision."""
    if not isinstance(reported, str) or not reported.strip():
        return None, False, "not_reported"
    text = reported.strip()
    if " | " in text:
        parts = [licence_lead(part) for part in text.split(" | ")]
        names = {name for name, _, _ in parts}
        if len(names) == 1 and parts[0][1]:
            return parts[0][0], True, "every_distribution_agrees"
        return text[:200], False, "distributions_disagree_or_unlisted"
    if text in ALLOWED_LICENCES:
        return text, True, "spdx_identifier"
    lowered = text.lower()
    if lowered in _LOWER:
        return _LOWER[lowered], True, "spdx_identifier_case"
    if lowered in _ALIASES:
        return _ALIASES[lowered], True, "known_alias"
    if lowered in _VERSIONLESS:
        return _VERSIONLESS[lowered], False, "version_not_reported"
    for pattern, spdx in _URLS:
        if pattern.search(lowered):
            return spdx, True, "licence_address"
    if any(word in text.split() for word in ("OR", "AND")) and licence_allowed(text):
        return text, True, "spdx_expression_allows"
    return text[:200], False, "not_on_allowlist_or_unrecognised"


_HARNESS_NAMES = re.compile(r"(?:^|/)(?:SKILL\.md|AGENTS\.md|CLAUDE\.md|GEMINI\.md|\.cursorrules|mcp\.json|plugin\.json)\Z", re.I)
_SCHEMA_PATH = re.compile(r"(?:\.schema\.json|(?:^|/)schemas?/[^/]+\.json)\Z", re.I)
_OPENAPI_PATH = re.compile(r"(?:openapi|swagger|asyncapi)[^/]*\.(?:ya?ml|json)\Z", re.I)
_TABLE_PATH = re.compile(r"\.(csv|tsv)\Z", re.I)
_MEDIA_PATH = re.compile(r"\.(glb|gltf|blend|obj|stl|fbx|usda?|mid|midi|musicxml|abc|svg|ttf|otf|step|stp|dxf|wav|flac|ogg|mp3)\Z", re.I)
_CLI = re.compile(r"\b(command[- ]line|cli tool|terminal tool|\bcli\b)", re.I)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60] or "source"


def route(candidate: dict) -> tuple:
    """(line or pool, proposed row or None) for one new candidate."""
    kind, extra = candidate["kind"], candidate.get("extra") or {}
    if kind == "file":
        repository, path = extra.get("repository"), extra.get("path") or ""
        owner = (repository or "").split("/")[0]
        pin = {"commit_seen": extra.get("commit"), "blob_sha": extra.get("blob_sha")}
        if _OPENAPI_PATH.search(path):
            return "openapi_sources", {"source_id": _slug(repository + "_" + path), "repository": repository,
                                       "branch": "HEAD", "paths": [path], "vendor": _slug(owner),
                                       "maximum_operations": 400, **pin}
        if _SCHEMA_PATH.search(path):
            return "json_schema_sources", {"source_id": _slug(repository + "_" + path), "title": repository + " " + path,
                                           "repository": repository, "branch": "HEAD", "vendor": _slug(owner),
                                           "schemas": [{"path": path}], **pin}
        match = _TABLE_PATH.search(path)
        if match:
            shape = "csv_records" if match.group(1).lower() == "csv" else "tsv_records"
            return "data_tables", {"row": [_slug(repository + "_" + path), path.rsplit("/", 1)[-1], repository, "HEAD",
                                           path, shape, None, None], **pin}
        if _HARNESS_NAMES.search(path) or "/.cursor/rules/" in "/" + path:
            return "harness_file_pool", None
        if _MEDIA_PATH.search(path):
            return "media_pool", None
        return "code_file_pool", None
    if kind == "repository":
        topics = {topic.lower() for topic in extra.get("topics") or ()}
        description = (candidate.get("description") or "").lower()
        language = (extra.get("language") or "").lower()
        if topics & {"mcp", "mcp-server", "model-context-protocol", "claude-code", "claude-skills", "agent-skills",
                     "cursor-rules", "agents-md", "codex", "claude"}:
            return "harness_repository_pool", None
        if topics & {"openapi", "openapi-specification", "openapi3", "swagger", "asyncapi"}:
            return "openapi_sources", {"source_id": _slug(candidate["title"]), "repository": candidate["title"],
                                       "branch": extra.get("default_branch") or "HEAD", "paths": [],
                                       "vendor": _slug(candidate["title"].split("/")[0]), "maximum_operations": 400,
                                       "needs": "specification paths"}
        if topics & {"json-schema", "jsonschema", "json-schemas"}:
            return "json_schema_sources", {"source_id": _slug(candidate["title"]), "title": candidate["title"],
                                           "repository": candidate["title"], "branch": extra.get("default_branch") or "HEAD",
                                           "schemas": [], "needs": "schema paths"}
        if language == "python" and ("doctest" in description or "doctest" in topics):
            return "function_sources", {"source_id": _slug(candidate["title"]), "title": candidate["title"],
                                        "repository": candidate["title"], "branch": extra.get("default_branch") or "HEAD",
                                        "needs": "package_root and modules"}
        if topics & {"cli", "command-line", "command-line-tool", "terminal", "commandline"} or _CLI.search(description):
            return "programs", {"row": [None, candidate["title"].split("/")[-1], ["--version"], candidate["title"], [], "unclassified"],
                                "needs": "Homebrew formula, release and effects check"}
        if topics & {"dataset", "datasets", "open-data", "opendata", "data"}:
            return "dataset_pool", None
        if language == "python" and ({"python-library", "library", "package", "pypi"} & topics or "library" in description):
            return "python_library_pool", None
        return "repository_pool", None
    if kind == "dataset":
        formats = {str(fmt).upper() for fmt in extra.get("formats") or ()} | {
            str(row.get("format") or "").upper() for row in extra.get("files") or () if isinstance(row, dict)}
        if formats & {"CSV", "TSV", "TEXT/CSV", "TEXT/TAB-SEPARATED-VALUES", "JSON", "XLSX", "PARQUET"} and not candidate["key"].startswith("hf-dataset:"):
            return "data_tables", {"source_kind": "portal_distribution", "dataset": candidate["url"],
                                   "files": (extra.get("files") or [])[:5],
                                   "needs": "a portal reader in the data table line; it reads GitHub repositories today"}
        return "dataset_pool", None
    if kind == "package":
        return npm_route(candidate) or ("package_pool", None)
    return {"model": "model_pool", "media": "media_pool", "paper": "paper_pool",
            "web_page": "web_lead_pool"}.get(kind, "web_lead_pool"), None


def npm_route(candidate: dict) -> "tuple | None":
    """An npm package that says it is a command-line program is also a programs lead."""
    extra = candidate.get("extra") or {}
    words = " ".join(extra.get("keywords") or []) + " " + (candidate.get("description") or "")
    if _CLI.search(words):
        return "programs", {"row": [None, candidate["title"], ["--version"], None, [], "unclassified"],
                            "npm": candidate["title"], "needs": "Homebrew formula, release and effects check"}
    return None

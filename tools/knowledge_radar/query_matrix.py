"""Lazy search hypotheses; never capability or publication identities.

The existing radar source contracts own retrieval. The idea matrix owns
method deduplication. This module only compiles applicability facets into
bounded search pages and a digest-bound cursor; no I/O or model dispatch is
performed by page(). Counts are combinations examined and unique queries,
not useful files, packages, source coverage or accepted work.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlencode

from harness_idea_matrix import DATATYPES, OPERATIONS, USE_CASES, operation_fits_datatype
from loop_engine.core.model_call_records import default_secret_patterns
from .records import SourceContract

MATRIX = "knowledge_radar_query_matrix/v1"
CURSOR = "knowledge_radar_query_cursor/v1"
QUERY = "knowledge_radar_query/v1"
PAGE = "knowledge_radar_query_page/v1"
QUERY_PARAMETERS = MappingProxyType({"per_page": 10, "sort": "updated", "order": "desc", "rank_by": "stars", "limit": 10})
MAX_PAGE = 20  # Keeps a page journal below the existing managed-record envelope.
MAX_SCAN = 10000
TOKEN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
GATES = MappingProxyType({"source_identity": "not_checked", "exact_version": "not_pinned",
         "redistribution_rights": "not_established", "relevance": "not_reviewed",
         "private_data": "not_assessed", "qualification": "not_run",
         "independent_admission": "not_requested", "publication": "not_authorized"})
SECRET_PATTERNS = tuple(re.compile(pattern) for pattern in default_secret_patterns())
SENSITIVE_TERM = re.compile(
    r"@|(?<!\w)(?:~/|/|\.\.?/)|\bbearer\s+[a-z0-9._~-]{12,}"
    r"|\b(?:github_pat_|gh[ousr]_|glpat-|xox[rs]-)[a-z0-9_-]{12,}"
    r"|\bsk[-_]proj[-_][a-z0-9_-]{16,}|(?:^|\s)\.(?:ssh|aws|config)/"
    r"|\b(?:internal confidential|company confidential|internal only|do not disclose|not for publication)\b"
    r"|(?:^|\s)\.env(?:\b|\.)", re.IGNORECASE)


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(part) for key, part in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(part) for part in value]
    return value


def freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(part) for key, part in value.items()})
    if isinstance(value, list):
        return tuple(freeze(part) for part in value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def strict(value, fields, name):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(name + "_fields")


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(name + "_bound")
    return value


def words(value):
    if type(value) is not str or not 1 <= len(value) <= 100:
        raise ValueError("query_term_length")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("query_term_control")
    clean = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    # Terms are quoted, not executable search operators, URLs or instructions.
    if not clean or any(char in clean for char in '\\"<>:{}'):
        raise ValueError("query_term_syntax")
    if SENSITIVE_TERM.search(clean) or any(pattern.search(value) or pattern.search(unicodedata.normalize("NFKC", value)) for pattern in SECRET_PATTERNS):
        raise ValueError("query_term_sensitive_pattern")
    return clean


@dataclass(frozen=True)
class Matrix:
    document: Mapping
    plan_digest: str
    sizes: tuple
    contracts: Mapping
    implementation_digest: str

    @property
    def raw_combinations(self):
        return sum(self.sizes)


def read_matrix(value, contracts: dict[str, SourceContract]) -> Matrix:
    strict(value, ("record_type", "revision", "vocabulary", "routes", "provenance"), "matrix")
    if value["record_type"] != MATRIX or type(value["revision"]) is not str or not re.fullmatch(r"[a-zA-Z0-9._-]{1,40}", value["revision"]):
        raise ValueError("matrix_version")
    vocabulary = value["vocabulary"]
    if type(vocabulary) is not dict or not 1 <= len(vocabulary) <= 20:
        raise ValueError("vocabulary_bound")
    for name, terms in vocabulary.items():
        if type(name) is not str or not TOKEN.fullmatch(name) or type(terms) is not list or not 1 <= len(terms) <= 1000:
            raise ValueError("vocabulary_dimension")
        normalized = [words(term) for term in terms]
        if len(normalized) != len(set(normalized)):
            raise ValueError("vocabulary_normalized_duplicate")
    routes = value["routes"]
    if type(routes) is not list or not 1 <= len(routes) <= 32:
        raise ValueError("routes_bound")
    names, sizes = set(), []
    for route in routes:
        strict(route, ("id", "engine", "dimensions", "purpose"), "route")
        if type(route["id"]) is not str or not TOKEN.fullmatch(route["id"]) or route["id"] in names:
            raise ValueError("route_identity")
        names.add(route["id"])
        if type(route["engine"]) is not str or (route["engine"] and route["engine"] not in contracts):
            raise ValueError("source_contract_missing")
        dimensions = route["dimensions"]
        if type(dimensions) is not list or not 1 <= len(dimensions) <= 8 or any(type(name) is not str or name not in vocabulary for name in dimensions) or len(set(dimensions)) != len(dimensions):
            raise ValueError("route_dimensions")
        if type(route["purpose"]) is not str or not 1 <= len(route["purpose"]) <= 500:
            raise ValueError("route_purpose")
        sizes.append(math.prod(len(vocabulary[name]) for name in dimensions))
    if type(value["provenance"]) is not list or not 1 <= len(value["provenance"]) <= 20 or any(type(item) is not str or len(item) > 1000 for item in value["provenance"]):
        raise ValueError("matrix_provenance")
    if len(json.dumps(value, ensure_ascii=False).encode()) > 512 * 1024:
        raise ValueError("matrix_bytes")
    used = {route["engine"] for route in routes if route["engine"]}
    snapshots = {}
    for name, contract in contracts.items():
        if not isinstance(contract, SourceContract) or contract.engine_id != name:
            raise ValueError("query_source_contract_identity")
        snapshots[name] = replace(contract, hosts=tuple(contract.hosts),
                                  excluded_upstreams=tuple(contract.excluded_upstreams),
                                  excluded_publishers=tuple(contract.excluded_publishers))
    source_contracts = {name: snapshots[name].to_dict() for name in sorted(used)}
    root = Path(__file__).resolve().parents[2]
    implementation = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in (
        "tools/knowledge_radar/query_matrix.py", "tools/knowledge_radar/query_runs.py",
        "tools/knowledge_radar/engines_network.py", "tools/knowledge_radar/engines.py",
        "tools/harness_idea_matrix.py", "src/loop_engine/forbidden_paths.json")}
    return Matrix(freeze(value), digest({"matrix": value, "contracts": source_contracts, "implementation": implementation}),
                  tuple(sizes), MappingProxyType(snapshots), digest(implementation))


def cursor_for(matrix, cursor=None):
    if cursor is None:
        return {"record_type": CURSOR, "plan_digest": matrix.plan_digest,
                "positions": [0] * len(matrix.sizes), "next_route": 0}
    strict(cursor, ("record_type", "plan_digest", "positions", "next_route"), "cursor")
    if cursor["record_type"] != CURSOR or cursor["plan_digest"] != matrix.plan_digest:
        raise ValueError("cursor_binding")
    if type(cursor["positions"]) is not list or len(cursor["positions"]) != len(matrix.sizes):
        raise ValueError("cursor_positions")
    positions = [integer(position, 0, size, "cursor_position") for position, size in zip(cursor["positions"], matrix.sizes)]
    return {**cursor, "positions": positions,
            "next_route": integer(cursor["next_route"], 0, len(matrix.sizes) - 1, "cursor_route")}


def query_at(matrix, route_index, offset):
    route = matrix.document["routes"][route_index]
    dimensions = matrix.document["vocabulary"]
    facets = {}
    # A coprime affine permutation visits every combination exactly once while
    # dispersing all digits, rather than exhausting first-country variants.
    size = matrix.sizes[route_index]
    stride = max(1, size * 6180339887 // 10000000000)
    while math.gcd(stride, size) != 1:
        stride += 1
    phase = int(digest({"route": route["id"]}), 16) % size
    offset = (offset * stride + phase) % size
    for name in route["dimensions"]:
        values = dimensions[name]
        offset, digit = divmod(offset, len(values))
        facets[name] = words(values[digit])
    return compile_query(matrix, route, facets)


def compile_query(matrix, route, facets):
    """One canonical record from an already selected route and lexical facets."""
    if "task" in facets and "data_type" in facets:
        task, datatype = facets["task"].replace(" ", "_"), facets["data_type"].replace(" ", "_")
        if task in OPERATIONS and datatype in DATATYPES and not operation_fits_datatype(datatype, task):
            return None, "incompatible_method"
    terms = search_terms(facets)
    if len(terms) > 256:
        return None, "query_too_long"
    engine = route["engine"]
    query = terms + (" in:readme archived:false is:public" if engine == "github_search" else "")
    if engine == "github_search" and len(urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 10})) > 1500:
        return None, "query_transport_length"
    contract_digest = digest(matrix.contracts[engine].to_dict()) if engine else None
    identity = digest({"engine": engine, "query": query})
    # Stable query identity is independent of labels, enumeration order and plan revision.
    work_id = digest({"query_id": identity, "source_contract_digest": contract_digest,
                      "parameters": QUERY_PARAMETERS, "implementation_digest": matrix.implementation_digest})
    return {"record_type": QUERY, "query_id": identity, "work_id": work_id,
            "plan_digest": matrix.plan_digest, "route": route["id"], "facets": facets,
            "query": query, "engine": engine, "source_contract_digest": contract_digest,
            "dispatch": "supported" if engine == "github_search" else "deferred_adapter",
            "purpose": route["purpose"], "gates": dict(GATES)}, ""


def search_terms(facets):
    # Target numbering is scope evidence, not an exact text phrase likely to
    # occur in an implementation's README. Preserve it in facets, omit it here.
    values = {re.sub(r"^\d{1,2}\.[0-9a-z]+ ", "", term) if name == "sdg_target" else term
              for name, term in facets.items()}
    return " ".join('"' + term + '"' for term in sorted(values))


def page(matrix, cursor=None, *, limit=10, scan_limit=1000, seen=None):
    integer(limit, 1, MAX_PAGE, "page_limit")
    integer(scan_limit, 1, MAX_SCAN, "scan_limit")
    start = cursor_for(matrix, cursor)
    next_cursor = cursor_for(matrix, start)
    rows, local_seen, excluded, coverage = [], set(), {}, {}
    examined = duplicates = 0
    for _ in range(scan_limit):
        available = [index for index in range(len(matrix.sizes)) if next_cursor["positions"][index] < matrix.sizes[index]]
        if not available or len(rows) == limit:
            break
        index = min(available, key=lambda index: (index - next_cursor["next_route"]) % len(matrix.sizes))
        offset = next_cursor["positions"][index]
        next_cursor["positions"][index] += 1
        next_cursor["next_route"] = (index + 1) % len(matrix.sizes)
        examined += 1
        row, reason = query_at(matrix, index, offset)
        if row is None:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        if row["work_id"] in local_seen or (seen and seen(row["work_id"])):
            duplicates += 1
            continue
        local_seen.add(row["work_id"])
        rows.append(row)
        for name, term in row["facets"].items():
            by_term = coverage.setdefault(name, {})
            by_term[term] = by_term.get(term, 0) + 1
    complete = all(position == size for position, size in zip(next_cursor["positions"], matrix.sizes))
    return {"record_type": PAGE, "plan_digest": matrix.plan_digest, "cursor": start,
            "limits": {"page_size": limit, "scan_limit": scan_limit},
            "next_cursor": next_cursor, "queries": rows, "complete": complete,
            "raw_combinations_upper_bound": matrix.raw_combinations,
            "counts": {"combinations_examined": examined, "queries_planned": len(rows),
                       "duplicates": duplicates, "excluded": excluded, "queries_executed": 0,
                       "candidate_packages_created": 0, "files_published": 0},
            "coverage": {"emitted_page_only": coverage,
                         "vocabulary_values": {name: len(values) for name, values in matrix.document["vocabulary"].items()},
                         "complete_source_or_population_coverage": False}}


def read_countries(value):
    """Operator-supplied factual inventory; source rights remain an explicit gate.

    Structural checks do not certify that a declared M49 snapshot is complete.
    No URL is fetched, and no provenance label grants redistribution rights.
    """
    strict(value, ("record_type", "source_url", "source_sha256", "observed_on", "rights_basis", "coverage", "entries"), "countries")
    if value["record_type"] != "knowledge_radar_country_inventory/v1":
        raise ValueError("country_inventory_version")
    from .records import day, https_address
    https_address(value["source_url"], "country source")
    day(value["observed_on"], "country observation")
    if type(value["source_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", value["source_sha256"]):
        raise ValueError("country_source_digest")
    if type(value["rights_basis"]) is not str or not 1 <= len(value["rights_basis"]) <= 600 or value["coverage"] not in ("declared_m49_snapshot", "pilot_subset"):
        raise ValueError("country_provenance")
    rows = value["entries"]
    if type(rows) is not list or not 1 <= len(rows) <= 1000:
        raise ValueError("country_entries")
    codes, names = set(), set()
    for row in rows:
        strict(row, ("m49", "name"), "country")
        if type(row["m49"]) is not str or not re.fullmatch(r"[0-9]{3}", row["m49"]) or row["m49"] in codes:
            raise ValueError("country_code")
        name = words(row["name"])
        if name in names:
            raise ValueError("country_duplicate_name")
        codes.add(row["m49"])
        names.add(name)
    return value


def default_matrix(repository, country_inventory=None):
    """Reuse method/applicability vocabularies; selected countries are not a world taxonomy."""
    root = Path(repository)
    expansion = json.loads((root / "tools/knowledge_radar/expansion-dimensions-v1.json").read_bytes())
    contexts = expansion["contexts"]
    vocabulary = {
        "task": [term.replace("_", " ") for term in OPERATIONS],
        "data_type": [term.replace("_", " ") for term in DATATYPES],
        "use_case": [term.replace("_", " ") for term in USE_CASES],
        "industry": list(dict.fromkeys(row["industry"] for row in contexts)),
        "occupation": list(dict.fromkeys(row["job_title"] for row in contexts)),
        "country_area": ["Argentina", "Australia", "Brazil", "Canada", "Egypt", "France", "Germany", "India", "Indonesia", "Japan", "Kenya", "Mexico", "Nigeria", "South Africa", "United Kingdom", "United States"],
        "language": ["Arabic", "Chinese", "English", "French", "Hindi", "Portuguese", "Spanish", "Swahili"],
        "audience": ["teachers", "students", "community volunteers", "public librarians", "caregivers", "small businesses", "researchers", "public administrators", "farmers", "workers", "designers", "disabled people"],
        "sdg_target": ["1.3 social protection", "2.4 sustainable agriculture", "3.d health emergency preparedness", "4.4 vocational skills", "5.4 unpaid care", "6.4 water efficiency", "7.3 energy efficiency", "8.8 worker rights", "9.1 resilient infrastructure", "10.2 social inclusion", "11.2 public transport", "12.5 waste reduction", "13.1 climate resilience", "14.1 marine pollution", "15.1 ecosystem conservation", "16.6 accountable institutions", "17.18 statistical capacity"],
        "artifact_form": ["Python", "TypeScript", "JSON schema", "reference dataset", "workflow", "SKILL.md", "AGENTS.md", "Open Knowledge Format", "plugin", "parameterized function", "worked example", "editable scene", "decision guide", "benchmark fixture"],
        "harness": ["Claude Code", "Codex", "OpenCode", "Pi", "Baltor", "Goose", "Zed", "Gemini CLI"],
        "source_type": ["official documentation", "open data", "source repository", "hosted service", "MCP server", "SaaS API"],
        "failure_mode": ["duplicate records", "incorrect units", "stale evidence", "incompatible versions", "partial failure", "inaccessible output", "privacy leakage", "missing licence"],
    }
    routes = [
        ("implementations", "github_search", ["task", "data_type", "industry", "country_area"]),
        ("public_good", "github_search", ["sdg_target", "task", "data_type", "country_area"]),
        ("native_workflows", "github_search", ["harness", "task", "use_case", "artifact_form", "language"]),
        ("audience_work", "github_search", ["audience", "task", "occupation", "country_area"]),
        ("service_references", "github_search", ["source_type", "task", "industry", "language"]),
        ("failure_checks", "github_search", ["failure_mode", "task", "artifact_form", "industry"]),
        ("official_reference", "", ["sdg_target", "country_area", "language", "source_type"]),
    ]
    country_provenance = "Country coverage is a 16-name illustrative pilot, not all M49 entries; provide --country-inventory for an exact source-bound inventory."
    country_rights = "Pilot country names are ordinary search terms; no external taxonomy is bundled."
    if country_inventory is not None:
        countries = read_countries(country_inventory)
        vocabulary["country_area"] = [row["name"] for row in sorted(countries["entries"], key=lambda row: row["m49"])]
        country_provenance = ("Country inventory sha256:" + digest(countries) + " source " + countries["source_url"]
                              + " source_sha256:" + countries["source_sha256"] + " observed:" + countries["observed_on"]
                              + " coverage:" + countries["coverage"] + "; declaration, not independently certified coverage.")
        country_rights = "Country inventory rights basis supplied by its preparer: " + countries["rights_basis"]
    sources = ["tools/harness_idea_matrix.py", "tools/knowledge_radar/expansion-dimensions-v1.json"]
    return {"record_type": MATRIX, "revision": "2026-10-01.1", "vocabulary": vocabulary,
            "routes": [{"id": name, "engine": engine, "dimensions": dimensions,
                        "purpose": "Find reusable " + name.replace("_", " ") + "; inspect exact source, rights, usefulness and existing method before proposing material."} for name, engine, dimensions in routes],
            "provenance": [*(path + " sha256:" + hashlib.sha256((root / path).read_bytes()).hexdigest() for path in sources),
                           "SDG target identifiers: https://sdgs.un.org/2030agenda ; selected one per goal, not complete target coverage or endorsement.",
                           "Language, audience, artifact and harness vocabulary: illustrative OpenAI-authored query choices; not exhaustive taxonomies or compatibility claims. Country provenance is separate.",
                           country_provenance, country_rights,
                           "https://docs.github.com/en/rest/search/search ; checked 2026-10-01; search is partial and rate-bounded. Repository licence metadata does not license individual payloads."]}

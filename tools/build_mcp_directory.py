"""Build the public directory of Model Context Protocol servers and agent APIs served at /directory.

Kind: development command. It reads outside listings into a state folder that lives outside the repository,
merges them into one row per offering and writes the packaged files the service serves: the manifest and eight
row files under `src/loop_engine/core/service_runtime/web_assets/directory/`, and the generated regions of
`web_assets/directory.html`. The package `tools/mcp_directory` holds the source engines, the merge and the page
rendering; `tools/mcp_directory/SOURCES.md` records each source and its terms.

Refresh the data (the daily job runs exactly these two commands):

    PYTHONPATH=src:tools python tools/build_mcp_directory.py refresh --state STATE_FOLDER
    PYTHONPATH=src:tools python tools/build_mcp_directory.py build --state STATE_FOLDER

`refresh` reads the official MCP Registry from the saved cursor: a full traversal the first time, then only the
entries updated since the last complete traversal (updated_since, with a one hour overlap). A stopped refresh
resumes where it stopped. It also reads GitHub's MCP directory and the Docker MCP Catalog at the commit its main
branch names, and, with --licences, the licence GitHub reports for each code repository through the gh login.
`build` needs no network. `check` compares the packaged files with each other and with the served address table.

Start a state folder from the recorded research traversal of September 23, 2026 instead of a full read:

    PYTHONPATH=src:tools python tools/build_mcp_directory.py seed --state STATE_FOLDER \\
        --acquisition RESEARCH/acquisition.json --acquisition RESEARCH/acquisition-continuation.json \\
        --requests CACHE/initial-requests.jsonl --requests CACHE/continuation-requests.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport  # noqa: E402
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog  # noqa: E402
from loop_engine.core.service_runtime import commercial_relationship as commercial  # noqa: E402
from mcp_directory import build as directory_build  # noqa: E402
from mcp_directory import page as directory_page  # noqa: E402
from mcp_directory import sources, state as directory_state  # noqa: E402
from mcp_directory.records import REPORT_RECORD_TYPE, Exclusion, Listing  # noqa: E402

WEB_ASSETS = ROOT / "src/loop_engine/core/service_runtime/web_assets"
DATA_FOLDER = WEB_ASSETS / "directory"
PAGE = WEB_ASSETS / "directory.html"
INDEX = WEB_ASSETS / "index.html"
CATEGORY_RULES = ROOT / "tools/resources/mcp-directory-categories.json"
RESEARCH_EXTRACT = ROOT / "tools/resources/mcp-directory-codex-research.json"
PUBLISHER_FILE = ROOT / "tools/resources/mcp-directory-publisher-documentation.json"
COMMERCIAL_FILE = ROOT / "tools/resources/mcp-directory-commercial-relationships.json"
SITE_MAP = ROOT / "src/loop_engine/core/service_runtime/web_site_map.json"
RESEARCH_RECORD_TYPE = "mcp_directory_research_extract/v1"
PUBLISHER_RECORD_TYPE = "mcp_directory_publisher_documentation/v1"
COMMERCIAL_RECORD_TYPE = "mcp_directory_commercial_relationships/v1"
PAGE_ADDRESS = "/directory"
READ_HOSTS = (sources.REGISTRY_HOST, sources.GITHUB_DIRECTORY_HOST, sources.DOCKER_ARCHIVE_HOST,
              directory_state.GITHUB_API_HOST)


def _transport(log_path: Path, maximum_requests: int) -> HttpsGetTransport:
    budget = RequestBudget(maximum_requests=maximum_requests, maximum_pause_seconds=600)
    return HttpsGetTransport(READ_HOSTS, budget, RequestLog(log_path), timeout_seconds=60, maximum_bytes=32 * 1024 * 1024)


def research_listings() -> list:
    """The recorded research selection: licence facts from its package metadata checks, keyed by server name."""
    if not RESEARCH_EXTRACT.exists():
        return []
    record = json.loads(RESEARCH_EXTRACT.read_text(encoding="utf-8"))
    if record.get("record_type") != RESEARCH_RECORD_TYPE:
        raise ValueError(f"{RESEARCH_EXTRACT} is not {RESEARCH_RECORD_TYPE}")
    return [Listing(source="codex", key=item["name"], name=item["name"], licence=item.get("licence", ""),
                    licence_basis="package" if item.get("licence") else "", reference=item["research_id"])
            for item in record["items"]]


def publisher_listings() -> "tuple[list, list]":
    if not PUBLISHER_FILE.exists():
        return [], []
    record = json.loads(PUBLISHER_FILE.read_text(encoding="utf-8"))
    if record.get("record_type") != PUBLISHER_RECORD_TYPE:
        raise ValueError(f"{PUBLISHER_FILE} is not {PUBLISHER_RECORD_TYPE}")
    found = [sources.publisher_listing(item) for item in record.get("offerings") or ()]
    return ([item for item in found if not isinstance(item, Exclusion)],
            [item for item in found if isinstance(item, Exclusion)])


def reviewed_relationships() -> dict:
    """The commercial relationship of each row identity, from the reviewed file; rows it does not name have none."""
    if not COMMERCIAL_FILE.exists():
        return {}
    record = json.loads(COMMERCIAL_FILE.read_text(encoding="utf-8"))
    if record.get("record_type") != COMMERCIAL_RECORD_TYPE or record.get("schema") != commercial.SCHEMA:
        raise ValueError(f"{COMMERCIAL_FILE} is not {COMMERCIAL_RECORD_TYPE} with {commercial.SCHEMA}")
    return {str(item["row"]): commercial.from_record(item["commercial_relationship"]) for item in record.get("rows") or ()}


def collect_listings(state: directory_state.DirectoryState) -> "tuple[list, list, dict]":
    """Every listing of every source the state holds, the exclusions, and each source's checked date."""
    listings, exclusions, checked = [], [], {}
    for entry in state.entries.values():
        found = sources.registry_listing(entry)
        (exclusions if isinstance(found, Exclusion) else listings).append(found)
    checked["registry"] = (state.sync.get("last_complete_at") or "")[:10]
    research = research_listings()
    listings.extend(research)
    if research:
        checked["codex"] = "2026-09-23"
    published, refused = publisher_listings()
    listings.extend(published)
    exclusions.extend(refused)
    if published:
        record = json.loads(PUBLISHER_FILE.read_text(encoding="utf-8"))
        checked["docs"] = str(record.get("reviewed_on") or "")
    github = state.snapshot("github")
    if github:
        for entry in github.get("items") or ():
            found = sources.github_listing(entry)
            (exclusions if isinstance(found, Exclusion) else listings).append(found)
        checked["github"] = github["checked_at"][:10]
    docker = state.snapshot("docker")
    if docker:
        import yaml
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        archive = state.quarantine.get(docker["archive_sha256"])
        found, refused = sources.docker_archive_listings(archive, docker["commit"], lambda text: yaml.load(text, Loader=loader))
        listings.extend(found)
        exclusions.extend(refused)
        checked["docker"] = docker["checked_at"][:10]
    return listings, exclusions, checked


def with_licences(offerings, licences: dict) -> list:
    """Fill a licence nobody reported from the licence GitHub reports for the offering's repository."""
    from dataclasses import replace
    folded = {key.lower(): value for key, value in licences.items()}
    filled = []
    for item in offerings:
        found = folded.get(item.repository.lower())
        if found:
            item = replace(item, repository_state="archived" if found.get("archived") else "found" if found.get("found") else "missing")
        if not item.licence and found and found.get("spdx"):
            item = replace(item, licence=found["spdx"], licence_basis="repository")
        filled.append(item)
    return filled


def build_offerings(listings, rules, relationships: dict, licences: dict) -> "tuple[list, list]":
    offerings, exclusions = [], []
    for group in directory_build.merge_listings(listings):
        found = directory_build.offering_of(group, rules)
        (exclusions if isinstance(found, Exclusion) else offerings).append(found)
    offerings = with_licences(offerings, licences)
    offerings = directory_build.with_relationships(offerings, relationships)
    return directory_build.default_order(offerings), exclusions


def secret_shaped(offerings) -> list:
    """Rows with a field that has the shape of a credential; they are held back, never published."""
    import re
    patterns = [re.compile(pattern) for pattern in json.loads(
        (ROOT / "src/loop_engine/forbidden_paths.json").read_text(encoding="utf-8"))["secret_patterns"]]
    patterns.append(re.compile(r"(?i)(?:bearer\s+[a-z0-9._-]{12,}|(?<![a-z0-9_])sk-[a-z0-9_-]{12,}|-----BEGIN [A-Z ]+PRIVATE KEY-----)"))
    held = []
    for item in offerings:
        text = json.dumps([item.identity, item.name, item.description, item.publisher, item.docs, item.repository,
                           [location.value for location in item.locations], list(item.aliases)], ensure_ascii=False)
        if any(pattern.search(text) for pattern in patterns):
            held.append(item.identity)
    return held


def write_packaged(offerings, rules, checked: dict, generated_at: str) -> dict:
    manifest, parts = directory_build.encode(offerings, rules, {"generated_at": generated_at, "checked": checked})
    manifest["labels"] = directory_page.LABELS
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    for index, part in enumerate(parts):
        text = directory_build.serialized_part(part)
        (DATA_FOLDER / f"rows-{index}.json").write_text(text, encoding="utf-8")
        manifest["parts"][index]["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        manifest["parts"][index]["bytes"] = len(text.encode("utf-8"))
    (DATA_FOLDER / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    first = [directory_page.decode_row(row, manifest) for row in _first_rows(offerings, manifest, parts)]
    canonical = directory_page.SECURE + json.loads(SITE_MAP.read_text(encoding="utf-8"))["canonical_hostname"] + PAGE_ADDRESS
    html = PAGE.read_text(encoding="utf-8")
    header, footer = directory_page.chrome_from_index(INDEX.read_text(encoding="utf-8"))
    html = directory_page.replace_region(html, "header", header)
    html = directory_page.replace_region(html, "footer", footer)
    html = directory_page.replace_region(html, "facts", directory_page.facts_html(manifest))
    html = directory_page.replace_region(html, "chips", directory_page.chips_html(manifest))
    html = directory_page.replace_region(html, "rows", "".join(directory_page.row_html(row, manifest) for row in first))
    html = directory_page.replace_region(html, "structured-data", '<script type="application/ld+json">'
                                         + directory_page.structured_data(manifest, first, canonical) + "</script>")
    PAGE.write_text(html, encoding="utf-8")
    return manifest


def _first_rows(offerings, manifest: dict, parts: list) -> list:
    wanted = [item.identity for item in offerings[:directory_page.FIRST_ROWS]]
    by_id = {row[0]: row for part in parts for row in part["rows"]}
    return [by_id[identity] for identity in wanted]


def report(offerings, exclusions, held, manifest: dict, listings) -> dict:
    by_source = {entry["id"]: entry["rows"] for entry in manifest["sources"]}
    by_category = {entry["label"]: entry["rows"] for entry in manifest["categories"]}
    sizes = {"manifest.json": (DATA_FOLDER / "manifest.json").stat().st_size}
    sizes.update({f"rows-{index}.json": entry["bytes"] for index, entry in enumerate(manifest["parts"])})
    return {"record_type": REPORT_RECORD_TYPE, "generated_at": manifest["generated_at"], "rows": manifest["row_count"],
            "listings_read": dict(Counter(item.source for item in listings)), "rows_by_source": by_source,
            "rows_by_category": by_category,
            "rows_by_origin": dict(Counter(item.origin for item in offerings)),
            "rows_with_licence": sum(1 for item in offerings if item.licence),
            "rows_listed_in_more_than_one_source": sum(1 for item in offerings if bin(item.source_bits).count("1") > 1),
            "aliases_merged": sum(len(item.aliases) for item in offerings),
            "exclusions_by_rule": dict(Counter(item.rule for item in exclusions)),
            "held_back_secret_shaped": held, "commercial_relationships_other_than_none": sum(
                1 for item in offerings if item.commercial_relationship != commercial.NONE),
            "bytes": sizes, "bytes_total": sum(sizes.values())}


def command_build(arguments) -> int:
    state = directory_state.DirectoryState(Path(arguments.state))
    rules = directory_build.CategoryRules.from_file(CATEGORY_RULES)
    listings, exclusions, checked = collect_listings(state)
    offerings, merged_out = build_offerings(listings, rules, reviewed_relationships(), directory_state.licence_cache(state))
    exclusions.extend(merged_out)
    held = secret_shaped(offerings)
    offerings = [item for item in offerings if item.identity not in set(held)]
    generated_at = arguments.generated_at or directory_state.utc_now()
    manifest = write_packaged(offerings, rules, checked, generated_at)
    summary = report(offerings, exclusions, held, manifest, listings)
    (Path(arguments.state) / "build-report.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("rows", "rows_by_source", "exclusions_by_rule", "bytes_total")}))
    return 0


def command_refresh(arguments) -> int:
    state = directory_state.DirectoryState(Path(arguments.state))
    transport = _transport(Path(arguments.state) / "requests.jsonl", arguments.maximum_requests)
    wanted = set(arguments.sources.split(","))
    results = {"pruned_pages": directory_state.prune_quarantine(state)}
    if "registry" in wanted:
        results["registry"] = directory_state.sync_registry(state, transport)
    if "github" in wanted:
        results["github"] = directory_state.read_github_directory(state, transport)
    if "docker" in wanted:
        results["docker"] = directory_state.read_docker_catalog(state, transport)
    if arguments.licences:
        listings, _exclusions, _checked = collect_listings(state)
        repositories = {listing.repository for listing in listings if listing.repository}
        results["licences"] = directory_state.github_licences(state, repositories, maximum=arguments.licences)
    print(json.dumps(results, default=str))
    complete = results.get("registry", {}).get("complete", True)
    return 0 if complete else 3


def command_seed(arguments) -> int:
    state = directory_state.DirectoryState(Path(arguments.state))
    print(json.dumps(directory_state.seed_from_research(state, arguments.acquisition, arguments.requests)))
    return 0


def command_import_research(arguments) -> int:
    """Write the committed extract of the research selection: names, research ids and reported licences."""
    source = Path(arguments.ranked)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    items = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        licence = str(row.get("license_reported") or "")
        items.append({"name": row["name"], "research_id": row["research_id"], "rank": row["rank"],
                      "licence": "" if licence in ("", "unknown") or " " in licence else licence})
    record = {"record_type": RESEARCH_RECORD_TYPE, "source": "artifacts/harness-source-research-2026-09-23/tools-ranked.jsonl",
              "source_sha256": digest, "decided_on": "2026-09-24",
              "note": "Licences are as the npm or PyPI package metadata reported them; no licence was verified.",
              "items": sorted(items, key=lambda item: item["rank"])}
    head = json.dumps({key: value for key, value in record.items() if key != "items"}, indent=1)[:-2]
    lines = ",\n".join(json.dumps(item, separators=(",", ":")) for item in record["items"])
    RESEARCH_EXTRACT.write_text(head + ',\n "items": [\n' + lines + "\n ]\n}\n", encoding="utf-8")
    print(json.dumps({"items": len(items), "with_licence": sum(1 for item in items if item["licence"])}))
    return 0


def check_packaged() -> list:
    """Problems with the packaged directory files, read without the network."""
    from loop_engine.core.service_runtime.web_pages import WEB_ASSETS
    problems = []
    manifest = json.loads((DATA_FOLDER / "manifest.json").read_text(encoding="utf-8"))
    served = sorted(path for path in WEB_ASSETS if path.startswith("/assets/directory/rows-"))
    listed = sorted(entry["address"] for entry in manifest["parts"])
    if served != listed or len(listed) != directory_build.PART_COUNT:
        problems.append(f"the served row files {served} are not the manifest's parts {listed}")
    identities, total = set(), 0
    for index, entry in enumerate(manifest["parts"]):
        text = (DATA_FOLDER / f"rows-{index}.json").read_text(encoding="utf-8")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != entry.get("sha256"):
            problems.append(f"rows-{index}.json does not hold the bytes the manifest names")
        part = json.loads(text)
        total += len(part["rows"])
        for row in part["rows"]:
            if len(row) != len(manifest["columns"]):
                problems.append(f"a row of rows-{index}.json has {len(row)} columns")
                break
            if row[0] in identities:
                problems.append(f"the row {row[0]} is listed twice")
            identities.add(row[0])
            if not row[manifest["columns"].index("locations")] and not row[manifest["columns"].index("repository")]:
                problems.append(f"the row {row[0]} names no place to get it")
            if directory_build.part_of(row[0]) != index:
                problems.append(f"the row {row[0]} is in the wrong part")
    if total != manifest["row_count"]:
        problems.append(f"the parts hold {total} rows and the manifest says {manifest['row_count']}")
    for record in manifest["commercial_relationships"]:
        commercial.from_record(record)
    html = PAGE.read_text(encoding="utf-8")
    for name in ("header", "footer", "facts", "chips", "rows", "structured-data"):
        directory_page.region(html, name)
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("refresh", help="read the sources into the state folder")
    refresh.add_argument("--state", required=True)
    refresh.add_argument("--sources", default="registry,github,docker")
    refresh.add_argument("--licences", type=int, default=0, help="look up at most this many repository licences")
    refresh.add_argument("--maximum-requests", type=int, default=3000)
    build = commands.add_parser("build", help="write the packaged data files and the page regions")
    build.add_argument("--state", required=True)
    build.add_argument("--generated-at", default="")
    seed = commands.add_parser("seed", help="start an empty state folder from the recorded research traversal")
    seed.add_argument("--state", required=True)
    seed.add_argument("--acquisition", action="append", required=True)
    seed.add_argument("--requests", action="append", required=True)
    research = commands.add_parser("import-research", help="write the committed extract of the research selection")
    research.add_argument("--ranked", required=True)
    commands.add_parser("check", help="compare the packaged files with each other and with the served table")
    arguments = parser.parse_args(argv)
    if arguments.command == "check":
        problems = check_packaged()
        print(json.dumps({"problems": problems}))
        return 1 if problems else 0
    return {"refresh": command_refresh, "build": command_build, "seed": command_seed,
            "import-research": command_import_research}[arguments.command](arguments)


if __name__ == "__main__":
    sys.exit(main())

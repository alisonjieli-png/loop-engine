"""Build the multiplier's CC0 geography and language tables from Wikidata, with their provenance.

Wikidata's structured data is CC0-1.0, which is on the owner's allowlist, so the derived tables may live in this
repository. Each table records the SPARQL text, the endpoint, the retrieval time and the SHA-256 of the exact
response it was built from. The build is a read: one GET per table to query.wikidata.org, no credential, no
redirect, bounded bytes. Nothing here certifies that a country list is complete or names a legal status: the
entries are search terms with codes, and a country or area name is not a jurisdiction or sovereignty claim.

```text
geography-wikidata-v1.json
├── countries_or_areas   ISO 3166-1 alpha-2 (P297) items without a dissolution date (P576) that carry an
│                        alpha-3 code (P298) or an M49 code (P2082); one row per alpha-2 code, the row with an
│                        M49 code preferred; label = Wikidata's English label
└── regions              items with an M49 code and no alpha-2 code: the UN M49 regions and sub-regions, minus
                         the world (001, which the null value already covers) and former atolls
languages-wikidata-v1.json
└── languages            ISO 639-1 (P218) with Wikidata's English label and native labels (P1705), so a query
                         can use the endonym and not only the English name
```

Command (writes the two tables beside this module; network read only)::

    PYTHONPATH=src:tools python -m query_multiplier.reference_tables --authorize-network-reads
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ENDPOINT_HOST = "query.wikidata.org"
ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "loop-engine query-multiplier/1.0 (read-only reference tables; https://github.com/alisonjieli-png/loop-engine)"
MAXIMUM_BYTES = 4 * 1024 * 1024
DATA = Path(__file__).resolve().parent / "data"
GEOGRAPHY_FILE, LANGUAGES_FILE = "geography-wikidata-v1.json", "languages-wikidata-v1.json"
LICENCE = "CC0-1.0"
LICENCE_EVIDENCE = "https://www.wikidata.org/wiki/Wikidata:Licensing (structured data in the main namespace: CC0-1.0)"

COUNTRIES_QUERY = (
    'SELECT ?item ?iso2 ?iso3 ?m49 ?label WHERE { ?item wdt:P297 ?iso2 . FILTER NOT EXISTS { ?item wdt:P576 ?end } '
    'OPTIONAL { ?item wdt:P298 ?iso3 } OPTIONAL { ?item wdt:P2082 ?m49 } '
    '?item rdfs:label ?label FILTER(LANG(?label) = "en") } ORDER BY ?iso2')
REGIONS_QUERY = (
    'SELECT ?item ?m49 ?label WHERE { ?item wdt:P2082 ?m49 . FILTER NOT EXISTS { ?item wdt:P297 ?iso2 } '
    '?item rdfs:label ?label FILTER(LANG(?label) = "en") } ORDER BY ?m49')
LANGUAGES_QUERY = (
    'SELECT ?lang ?code ?en (GROUP_CONCAT(DISTINCT ?nat; separator="|") AS ?natives) WHERE { ?lang wdt:P218 ?code . '
    '?lang rdfs:label ?en FILTER(LANG(?en) = "en") OPTIONAL { ?lang wdt:P1705 ?nat } } '
    'GROUP BY ?lang ?code ?en ORDER BY ?code')
#: M49 codes with no alpha-2 code that are not regions to search by: the world (the null value already means
#: "no geography"), two former atolls, and the Netherlands, whose M49 code sits on a second item.
EXCLUDED_REGION_CODES = {"001": "the null value already means no geography",
                         "396": "former atoll, no current population", "488": "former atoll, no current population",
                         "528": "a country whose M49 code sits on a second Wikidata item; the country row covers it"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(query: str) -> tuple[bytes, str]:
    """One bounded GET of the public SPARQL endpoint; the response bytes and the time they were read."""
    target = ENDPOINT + "?" + urlencode({"query": query})
    request = urllib.request.Request(target, method="GET", headers={
        "User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=120) as answer:
        if answer.status != 200:
            raise RuntimeError(f"wikidata answered {answer.status}")
        body = answer.read(MAXIMUM_BYTES + 1)
    if len(body) > MAXIMUM_BYTES:
        raise RuntimeError("wikidata response above the declared bound")
    return body, datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _rows(body: bytes) -> list:
    return json.loads(body)["results"]["bindings"]


def _value(row: dict, name: str):
    cell = row.get(name)
    return cell.get("value") if isinstance(cell, dict) and cell.get("value") else None


def _qid(row: dict, name: str) -> str:
    return (_value(row, name) or "").rsplit("/", 1)[-1]


def _provenance(query: str, body: bytes, retrieved: str) -> dict:
    return {"endpoint": ENDPOINT, "query": query, "retrieved_at": retrieved,
            "response_sha256": hashlib.sha256(body).hexdigest(), "response_bytes": len(body),
            "licence": LICENCE, "licence_evidence": LICENCE_EVIDENCE}


def geography_table(countries_body: bytes, countries_at: str, regions_body: bytes, regions_at: str) -> dict:
    by_code: dict = {}
    for row in _rows(countries_body):
        iso2, iso3, m49 = _value(row, "iso2"), _value(row, "iso3"), _value(row, "m49")
        if not iso2 or not (iso3 or m49):
            continue
        entry = {"iso2": iso2, "iso3": iso3, "m49": m49, "label": _value(row, "label"), "wikidata": _qid(row, "item")}
        held = by_code.get(iso2)
        # One row per alpha-2 code: the item with an M49 code wins, then the lower item number.
        if held is None or (bool(m49), -int(entry["wikidata"][1:] or 0)) > (bool(held["m49"]), -int(held["wikidata"][1:] or 0)):
            by_code[iso2] = entry
    regions, excluded = {}, []
    for row in _rows(regions_body):
        code = _value(row, "m49")
        if not code or len(code) != 3 or not code.isdigit():
            continue
        if code in EXCLUDED_REGION_CODES:
            excluded.append({"m49": code, "label": _value(row, "label"), "reason": EXCLUDED_REGION_CODES[code]})
            continue
        regions.setdefault(code, {"m49": code, "label": _value(row, "label"), "wikidata": _qid(row, "item")})
    return {"record_type": "research_reference_geography/v1", "licence": LICENCE,
            "scope": "Search terms with codes; a country or area name is not a jurisdiction or sovereignty claim, "
                     "and this list is not certified complete.",
            "sources": {"countries_or_areas": _provenance(COUNTRIES_QUERY, countries_body, countries_at),
                        "regions": _provenance(REGIONS_QUERY, regions_body, regions_at)},
            "countries_or_areas": [by_code[code] for code in sorted(by_code)],
            "regions": [regions[code] for code in sorted(regions)],
            "excluded_regions": sorted(excluded, key=lambda row: row["m49"])}


def languages_table(body: bytes, retrieved: str) -> dict:
    rows = {}
    for row in _rows(body):
        code = _value(row, "code")
        if not code or len(code) != 2 or code in rows:
            continue
        natives = sorted({part.strip() for part in (_value(row, "natives") or "").split("|") if part.strip()})
        rows[code] = {"iso639_1": code, "label": _value(row, "en"), "native_labels": natives,
                      "wikidata": _qid(row, "lang")}
    return {"record_type": "research_reference_languages/v1", "licence": LICENCE,
            "scope": "ISO 639-1 codes with English and native labels as search terms; not a translation service.",
            "sources": {"languages": _provenance(LANGUAGES_QUERY, body, retrieved)},
            "languages": [rows[code] for code in sorted(rows)]}


def write(path: Path, value: dict) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--output", type=Path, default=DATA)
    options = parser.parse_args(argv)
    if not options.authorize_network_reads:
        print(json.dumps({"status": "plan", "reads": [ENDPOINT] * 3, "writes": [GEOGRAPHY_FILE, LANGUAGES_FILE]}))
        return 0
    try:
        countries, countries_at = fetch(COUNTRIES_QUERY)
        time.sleep(2)
        regions, regions_at = fetch(REGIONS_QUERY)
        time.sleep(2)
        languages, languages_at = fetch(LANGUAGES_QUERY)
    except (urllib.error.URLError, OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "error_class": type(error).__name__}))
        return 2
    geography = geography_table(countries, countries_at, regions, regions_at)
    table = languages_table(languages, languages_at)
    options.output.mkdir(parents=True, exist_ok=True)
    write(options.output / GEOGRAPHY_FILE, geography)
    write(options.output / LANGUAGES_FILE, table)
    print(json.dumps({"status": "written", "countries_or_areas": len(geography["countries_or_areas"]),
                      "regions": len(geography["regions"]), "languages": len(table["languages"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

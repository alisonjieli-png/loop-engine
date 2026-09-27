"""Read-only discovery adapters. Outputs are research observations, not admission.

Reuse collector.py for the bounded transport, record cleaning and common feeds.
The daily exports deliberately omit source abstracts and repository descriptions.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit

import collector as base

TYPE = "source_discovery_extension_configuration/v1"
FAMILIES = {"papers", "skills", "plugins", "protocol_servers", "services", "repositories", "packages", "news"}
ROUTES = {
    "daily_papers": ("huggingface.co", "/api/daily_papers"),
    "mcp_registry": ("registry.modelcontextprotocol.io", "/v0.1/servers"),
    "npm_search": ("registry.npmjs.org", "/-/v1/search"),
    "skills_directory": ("www.skills.sh", "/"),
    "github_search": ("api.github.com", "/search/repositories"),
    "github_trending": ("github.com", "/trending"),
}


def validate(value):
    if type(value) is not dict or set(value) != {"record_type", "sources", "maximum_requests", "timeout_seconds"} or value["record_type"] != TYPE:
        raise ValueError("invalid_configuration")
    if type(value["maximum_requests"]) is not int or not 1 <= value["maximum_requests"] <= 20:
        raise ValueError("invalid_request_bound")
    if type(value["timeout_seconds"]) is not int or not 1 <= value["timeout_seconds"] <= 20:
        raise ValueError("invalid_timeout")
    if type(value["sources"]) is not list or not 1 <= len(value["sources"]) <= value["maximum_requests"]:
        raise ValueError("invalid_sources")
    ids = set()
    for s in value["sources"]:
        if type(s) is not dict or set(s) != {"id", "family", "kind", "host", "path", "query", "maximum_entries"}:
            raise ValueError("invalid_source")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,60}", s["id"]) or s["id"] in ids:
            raise ValueError("invalid_source_identity")
        ids.add(s["id"])
        if s["family"] not in FAMILIES or type(s["maximum_entries"]) is not int or not 1 <= s["maximum_entries"] <= 100:
            raise ValueError("invalid_source_scope")
        if s["kind"] == "feed":
            base.public_url("https://" + s["host"] + s["path"])
            if not re.fullmatch(r"[a-z0-9.-]+", s["host"]) or not s["path"].startswith("/") or s["query"]:
                raise ValueError("invalid_feed")
        elif (s["host"], s["path"]) != ROUTES.get(s["kind"]):
            raise ValueError("unsupported_source_route")
        if type(s["query"]) is not dict or any(type(k) is not str or type(v) not in (str, int) for k, v in s["query"].items()):
            raise ValueError("invalid_query")
        allowed = {"daily_papers": {"limit", "sort", "date"}, "mcp_registry": {"limit", "version", "cursor", "updated_since"},
                   "npm_search": {"text", "size", "from"}, "github_search": {"q", "sort", "order", "per_page"},
                   "github_trending": {"since", "spoken_language_code"}, "skills_directory": set(), "feed": set()}[s["kind"]]
        if not set(s["query"]) <= allowed:
            raise ValueError("unsupported_query")
        for key in ("limit", "size", "per_page"):
            if key in s["query"] and (type(s["query"][key]) is not int or not 1 <= s["query"][key] <= s["maximum_entries"]):
                raise ValueError("invalid_page_bound")
        if any(re.search(p, json.dumps(s)) for p in base.default_secret_patterns()):
            raise ValueError("secret_shaped_configuration")
    return value


def entry(key, title, url, *, source, version=None, licence=None, updated=None, facts=None):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing_title")
    return {"key": key, "family": source["family"], "source_id": source["id"],
            "title": base.clean(title, 200), "url": base.public_url(url), "version": version,
            "declared_licence": licence, "licence_verified": False, "updated_at": base.timestamp(updated),
            "facts": facts or {}, "verification": "discovery_only", "source_body_read": False,
            "summary": None, "summary_state": "not_authored", "component_admission": "not_requested"}


class DirectoryLinks(HTMLParser):
    """Select known directory link shapes; ignore embedded scripts and navigation."""

    def __init__(self, kind):
        super().__init__(convert_charrefs=True)
        self.kind, self.links, self.tags = kind, [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        href = dict(attrs).get("href", "")
        if tag != "a":
            return
        parts = urlsplit(href)
        if parts.scheme or parts.netloc or parts.query or parts.fragment:
            return
        segments = parts.path.strip("/").split("/")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", p) or p in (".", "..") for p in segments):
            return
        if self.kind == "skills_directory" and len(segments) == 3:
            self.links.append(parts.path)
        if self.kind == "github_trending" and len(segments) == 2 and "article" in self.tags and "h2" in self.tags:
            self.links.append(parts.path)

    def handle_endtag(self, tag):
        if tag in self.tags:
            index = len(self.tags) - 1 - self.tags[::-1].index(tag)
            self.tags = self.tags[:index]


def parse(raw, source):
    kind, cap = source["kind"], source["maximum_entries"]
    rows, omitted = [], []
    coverage = {"complete_source": False, "selection": "bounded_first_page", "available_entries": None, "next_cursor": None}
    if source['query'].get('cursor'):
        coverage['selection'] = 'bounded_cursor_page'
    if kind in {"skills_directory", "github_trending"}:
        parser = DirectoryLinks(kind)
        parser.feed(raw.decode("utf-8"))
        links = list(dict.fromkeys(parser.links))
        if not links:
            raise ValueError("directory_shape_not_observed")
        for path in links[:cap]:
            title = path.strip("/")
            rows.append(entry(kind + ":" + title, title, "https://" + source["host"] + path,
                              source=source, facts={"directory_position": len(rows) + 1}))
        coverage.update(selection="visible_html_links", available_entries=len(links))
        return rows, omitted, coverage
    if kind == "feed":
        for row in base.parse_feed(raw, source["id"], cap):
            rows.append(entry(row["key"], row["title"], row["url"], source=source, updated=row["updated_at"]))
        coverage["selection"] = "feed_entries_up_to_bound"
        return rows, omitted, coverage
    data = json.loads(raw)
    if kind != 'daily_papers' and type(data) is not dict:
        raise ValueError('response_object_shape')
    if kind == "daily_papers":
        if type(data) is not list:
            raise ValueError("paper_list_shape")
        candidates = data
    elif kind == "mcp_registry":
        candidates = data["servers"]
        metadata = data.get('metadata', {})
        if type(metadata) is not dict:
            raise ValueError('registry_metadata_shape')
        coverage["next_cursor"] = metadata.get("nextCursor")
    elif kind == "npm_search":
        candidates = data["objects"]
        coverage["available_entries"] = data.get("total")
    else:
        candidates = data["items"]
        coverage.update(available_entries=data.get("total_count"), incomplete_results=data.get("incomplete_results"))
    if type(candidates) is not list:
        raise ValueError("entry_list_shape")
    coverage["page_entries"] = len(candidates)
    if len(candidates) > cap:
        omitted.append({'entry_index': cap, 'omitted_entries': len(candidates) - cap,
                        'reason': 'source_page_exceeds_bound'})
    for index, item in enumerate(candidates[:cap]):
        try:
            if type(item) is not dict:
                raise ValueError('entry_object_shape')
            if kind == "daily_papers":
                p = item["paper"]
                identity = p["id"]
                if not re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?", identity):
                    raise ValueError("paper_identity_shape")
                row = entry("paper:" + identity, p["title"], "https://huggingface.co/papers/" + identity,
                            source=source, updated=p.get("publishedAt"))
            elif kind == "mcp_registry":
                p = item["server"]
                m = item["_meta"]["io.modelcontextprotocol.registry/official"]
                if type(p) is not dict or type(m) is not dict:
                    raise ValueError('registry_entry_metadata_shape')
                identity, version = p["name"], p["version"]
                if not isinstance(identity, str) or not isinstance(version, str) or not identity or not version:
                    raise ValueError("registry_identity_shape")
                path = "/v0.1/servers/" + quote(identity, safe="") + "/versions/" + quote(version, safe="")
                row = entry("mcp:" + identity + "@" + version, identity, "https://" + source["host"] + path,
                            source=source, version=version, updated=m.get("updatedAt") or m.get("publishedAt"),
                            facts={"registry_status": m.get("status"), "is_latest": m.get("isLatest"),
                                   "packages_listed": len(p.get("packages") or []), "remotes_listed": len(p.get("remotes") or [])})
            elif kind == "npm_search":
                p = item["package"]
                identity, version = p["name"], p["version"]
                if not isinstance(identity, str) or not re.fullmatch(r"(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+", identity) or not isinstance(version, str):
                    raise ValueError("npm_identity_shape")
                row = entry("npm:" + identity + "@" + version, identity, "https://www.npmjs.com/package/" + identity,
                            source=source, version=version, licence=p.get("license"), updated=p.get("date"))
            else:
                p = base.repository(item, source["id"])
                row = entry(p["key"], p["title"], p["url"], source=source, licence=p["declared_licence"],
                            updated=p["updated_at"], facts={"archived": p["archived"], "stars": p["metrics"]["stargazers_count"]})
            row["source_entry_sha256"] = base.sha(base.canonical(item))
            rows.append(row)
        except (KeyError, TypeError, ValueError) as error:
            omitted.append({"entry_index": index, "error_type": type(error).__name__})
    return rows, omitted, coverage


def distill(observations, outcomes, observed_at):
    """One reproducible metadata record per family, with all discovery origins."""
    records = []
    for family in sorted({o["family"] for o in outcomes}):
        selected = [r for r in observations if r["family"] == family]
        identities = {}
        for row in selected:
            identities.setdefault(row["key"], []).append(row)
        sources = [s for s in outcomes if s["family"] == family]
        records.append({"record_type": "source_family_distillation/v1", "family": family,
                        "observed_at": observed_at, "status": "complete" if all(s["outcome"] == "ok" for s in sources) else "partial",
                        "selection_complete": False, "summary_mode": "metadata_only", "model_calls": 0,
                        "observations": len(selected), "distinct_source_identities": len(identities), "sources": sources,
                        "entries": [{"key": k, "observations": v} for k, v in sorted(identities.items())],
                        "new_components": 0, "approved_components": 0})
    return records


def run(config, output):
    config = validate(config)
    output = output.absolute()
    if output.parent.resolve() != output.parent:
        raise ValueError("output_parent_not_plain")
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    log = base.RequestLog(output / "requests.jsonl")
    budget = base.RequestBudget(config["maximum_requests"], maximum_pause_seconds=0, reserve=0)
    transport = base.HttpsGetTransport({s["host"] for s in config["sources"]}, budget, log,
                                      timeout_seconds=config["timeout_seconds"], maximum_bytes=2 * 1024 * 1024)
    observed_at, observations, outcomes = base.now(), [], []
    since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    for source in config["sources"]:
        query = {k: v.replace("{since_14d}", since) if isinstance(v, str) else v for k, v in source["query"].items()}
        result = {"source_id": source["id"], "family": source["family"], "outcome": "failed", "observations": 0,
                  "request_query": query}
        try:
            response = transport.get(source["host"], source["path"], query)
            result.update(http_status=response.status, response_sha256=base.sha(response.body), response_bytes=len(response.body))
            if response.status != 200:
                raise ValueError("source_http_failure")
            # Private snapshots permit exact replay; not a public content republication.
            (output / (source["id"] + ".response")).write_bytes(response.body)
            rows, omitted, coverage = parse(response.body, source)
            for row in rows:
                row.update(observed_at=observed_at, response_sha256=result["response_sha256"])
            observations.extend(rows)
            result.update(outcome="ok" if not omitted else "partial", observations=len(rows), exclusions=omitted, coverage=coverage)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            result["error_type"] = type(error).__name__
        outcomes.append(result)
    records = distill(observations, outcomes, observed_at)
    for record in records:
        base.write_json(output / (record["family"] + ".json"), record)
    report = {"record_type": "source_discovery_extension_run/v1", "observed_at": observed_at, "finished_at": base.now(),
              "configuration_sha256": base.sha(base.canonical(config)), "adapter_sha256": base.sha(Path(__file__).read_bytes()),
              "collector_sha256": base.sha(Path(base.__file__).read_bytes()), "sources": outcomes,
              "requests": budget.used, "observations": len(observations), "families": dict(Counter(r["family"] for r in observations)),
              "status": "complete" if all(s["outcome"] == "ok" for s in outcomes) else "partial",
              "model_calls": 0, "source_programs_executed": 0, "new_components": 0, "approved_components": 0}
    base.write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--configuration", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--authorize-network-reads", action="store_true")
    p.add_argument("--authorize-local-writes", action="store_true")
    a = p.parse_args()
    config = validate(json.loads(a.configuration.read_bytes()))
    if a.authorize_network_reads and a.authorize_local_writes:
        print(json.dumps(run(config, a.output)))
    else:
        print(json.dumps({"preview": True, "sources": len(config["sources"]), "maximum_requests": config["maximum_requests"]}))

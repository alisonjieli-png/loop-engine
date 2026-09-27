"""Local engines of the radar's source edge: they read files and never the network.

`collector_state` reads the source discovery collector's latest private
exports (read-only; another process owns and writes them). `model_directory`
and `mcp_directory` read the directory data this repository packages for its
public pages. `curated_seed` turns the official links a person declared in
the question registry into observations that stay unverified until the
vetting stage checks each link.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .engines import (
    FAILED,
    OK,
    PARTIAL,
    EngineAnswer,
    RadarEngineError,
    ReadContext,
    clean_title,
    iso_time,
    limit_of,
    number,
    observation,
    parameter,
    ranked,
    text_fact,
)
from .records import https_address

MODEL_DIRECTORY = Path("src/loop_engine/core/service_runtime/web_assets/model-directory")
MCP_DIRECTORY = Path("src/loop_engine/core/service_runtime/web_assets/directory")
MAXIMUM_FILE_BYTES = 64 * 1024 * 1024
FAMILIES = ("papers", "skills", "plugins", "protocol_servers", "services", "repositories", "packages", "news")
INDEXES = {"Artificial Analysis Intelligence Index": "intelligence_index",
           "Artificial Analysis Coding Index": "coding_index",
           "Artificial Analysis Agentic Index": "agentic_index"}


def _plain_file(root: Path, relative: Path) -> Path:
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RadarEngineError("radar_local_file_invalid", f"{relative} passes through a link")
    if not path.is_file() or path.stat().st_size > MAXIMUM_FILE_BYTES:
        raise RadarEngineError("radar_local_file_missing", f"{relative} is missing or too large")
    return path


def _json(root: Path, relative) -> dict:
    try:
        return json.loads(_plain_file(Path(root), Path(relative)).read_bytes())
    except (OSError, ValueError) as error:
        raise RadarEngineError("radar_local_file_unreadable", f"{relative}: {type(error).__name__}") from None


def _origin(key: str, title: str, url: str) -> str:
    kind, _, rest = key.partition(":")
    if kind == "paper":
        return "arxiv:" + rest.split("v")[0]
    if kind == "github-repository":
        return "github:" + title.lower()
    if kind in ("mcp", "npm"):
        return kind + ":" + rest.rsplit("@", 1)[0].lower()
    if kind == "skills_directory":
        return "skills.sh:" + rest.lower()
    return "web:" + url


class CollectorState:
    """The source discovery collector's newest distillation of one family of public listings."""

    engine_id, engine_version = "collector_state", "1.0.0"
    material_facts = ("licence", "archived", "registry_status")

    def read(self, context: ReadContext) -> EngineAnswer:
        if context.collector_state is None:
            return EngineAnswer(FAILED, "the run names no collector state folder")
        state = Path(context.collector_state)
        family = parameter(context, "family", kind=str, choices=FAMILIES)
        source_id = parameter(context, "source_id", "", kind=str)
        try:
            latest = _json(state, "combined-latest.json")
            report = Path(str(latest.get("extended_report", "")))
            folder = report.parent
            if folder.parent.parent != state or folder.parent.name != "extended-runs":
                return EngineAnswer(FAILED, "the collector's latest report is outside its state folder")
            distilled = _json(folder, f"{family}.json")
        except RadarEngineError as error:
            return EngineAnswer(FAILED, str(error))
        if distilled.get("record_type") != "source_family_distillation/v1" or distilled.get("family") != family:
            return EngineAnswer(FAILED, "the collector export is not a source_family_distillation/v1 record")
        rows, excluded = [], []
        for entry in distilled.get("entries", []):
            seen = [row for row in entry.get("observations", []) if not source_id or row.get("source_id") == source_id]
            if not seen:
                continue
            row = seen[0]
            title, reason = clean_title(row.get("title"))
            if reason:
                excluded.append((str(entry.get("key")), reason))
                continue
            try:
                url = https_address(row.get("url"), "collector url")
            except ValueError:
                excluded.append((str(entry.get("key")), "the listing gave no public https address"))
                continue
            facts = row.get("facts") if isinstance(row.get("facts"), dict) else {}
            rows.append(observation(
                context, self, key=str(entry["key"]), origin=_origin(str(entry["key"]), title, url), title=title,
                url=url, source_address=f"collector export {folder.name}/{family}.json ({row.get('source_id')})",
                facts={"stars": number(facts.get("stars")), "archived": facts.get("archived"),
                       "directory_position": number(facts.get("directory_position")),
                       "registry_status": text_fact(facts.get("registry_status")),
                       "listing": text_fact(row.get("source_id")), "version": text_fact(row.get("version"))},
                licence=text_fact(row.get("declared_licence"), 80),
                licence_basis="declared by the listing, not verified" if row.get("declared_licence") else
                "not stated by the listing",
                source_published_at=iso_time(row.get("updated_at")),
                observed_at=iso_time(row.get("observed_at")) or context.observed_at))
        rank_by = parameter(context, "rank_by", "source_published_at", kind=str)
        chosen = ranked(rows, rank_by, descending=not parameter(context, "ascending", False, kind=bool))
        status = OK if distilled.get("status") == "complete" and latest.get("status") == "complete" else PARTIAL
        reason = "" if status == OK else "the collector marked its latest run or this family partial"
        return EngineAnswer(status, reason, tuple(chosen[:limit_of(context)]), 0, (), tuple(excluded))


def _first(values, name="value", allowed=None):
    """The first value of a fact that a permitted source gave; a fact from an excluded source counts as unknown."""
    entries = values if isinstance(values, list) else [values] if isinstance(values, dict) else []
    for item in entries:
        if isinstance(item, dict) and name in item and (allowed is None or allowed(item)):
            return item[name]
    return None


def source_filter(row: dict, contract) -> "tuple":
    """A predicate that keeps a value only when its source is not excluded by the contract, and whether any source is."""
    excluded = {name.lower() for name in contract.excluded_upstreams}
    identities = [str(source.get("id", "")).lower() for source in row.get("sources", []) if isinstance(source, dict)]

    def allowed(entry) -> bool:
        index = entry.get("source") if isinstance(entry, dict) else None
        if type(index) is not int or not 0 <= index < len(identities):
            return False
        return identities[index] not in excluded
    return allowed, any(name not in excluded for name in identities)


def model_facts(row: dict, allowed=None, excluded_publishers=(), excluded_routes=()) -> dict:
    """The plain, sourced facts of one model directory row, with unknown and excluded values left out."""
    keep = allowed or (lambda entry: True)
    publishers = {name.lower() for name in excluded_publishers}
    routes = {name.lower() for name in excluded_routes}
    facts = row.get("facts", {})
    prices = [price for price in row.get("prices", []) if number(price.get("output")) is not None and keep(price)
              and str(price.get("route", "")).lower() not in routes]
    cheapest = min(prices, key=lambda price: (price["output"], price.get("input") or 0, price.get("provider", "")),
                   default=None)
    indexes = {INDEXES[item["name"]]: number(item.get("value")) for item in row.get("benchmarks", [])
               if item.get("name") in INDEXES and keep(item)
               and str(item.get("publisher", "")).lower() not in publishers}
    quants = [item for item in row.get("quantizations", []) if number(item.get("bytes")) and keep(item)]
    smallest = min(quants, key=lambda item: (item["bytes"], item.get("name", "")), default=None)
    uses = sorted({item.get("value") for item in row.get("use_cases", []) if isinstance(item.get("value"), str)
                   and keep(item)})
    released = _first(facts.get("released"), allowed=keep)
    output = cheapest["output"] if cheapest else None
    intelligence = indexes.get("intelligence_index")
    popularity = row.get("popularity") if isinstance(row.get("popularity"), dict) and keep(row.get("popularity")) else {}
    return {
        "maker": text_fact(row.get("maker")),
        "parameters": number(_first(facts.get("parameters"), allowed=keep)),
        "active_parameters": number(_first(facts.get("active_parameters"), allowed=keep)),
        "context": number(_first(facts.get("context"), allowed=keep)),
        "max_output": number(_first(facts.get("max_output"), allowed=keep)),
        "open_weights": _first(facts.get("open_weights"), allowed=keep),
        "tool_calling": _first(facts.get("tool_calling"), allowed=keep),
        "structured_output": _first(facts.get("structured_output"), allowed=keep),
        "reasoning": _first(facts.get("reasoning"), allowed=keep),
        "released": released if isinstance(released, str) else None,
        "downloads": number(popularity.get("downloads")),
        "likes": number(popularity.get("likes")),
        "intelligence_index": intelligence,
        "coding_index": indexes.get("coding_index"),
        "agentic_index": indexes.get("agentic_index"),
        "input_price": number(cheapest.get("input")) if cheapest else None,
        "output_price": output,
        "price_provider": text_fact(cheapest.get("provider")) if cheapest else None,
        "price_as_of": cheapest.get("as_of") if cheapest else None,
        "price_per_intelligence_point": round(output / intelligence, 4) if output and intelligence else None,
        "smallest_quant_bytes": smallest["bytes"] if smallest else None,
        "smallest_quant": text_fact(smallest.get("name")) if smallest else None,
        "uses": ", ".join(uses) if uses else None,
    }


def _model_url(row: dict):
    ids = row.get("ids") or {}
    if isinstance(ids.get("huggingface"), str):
        return "https://huggingface.co/" + ids["huggingface"]
    return None


class ModelDirectory:
    """The packaged model directory: makers, licences, sizes, listed prices and published index values."""

    engine_id, engine_version = "model_directory", "1.0.0"
    material_facts = ("licence", "output_price", "input_price", "intelligence_index", "coding_index",
                      "open_weights", "tool_calling", "structured_output")

    def read(self, context: ReadContext) -> EngineAnswer:
        try:
            data = _json(context.repository, MODEL_DIRECTORY / "models.json")
            manifest = _json(context.repository, MODEL_DIRECTORY / "manifest.json")
        except RadarEngineError as error:
            return EngineAnswer(FAILED, str(error))
        use_case = parameter(context, "use_case", "", kind=str)
        require = parameter(context, "require", [], kind=list)
        names = [str(name).lower() for name in parameter(context, "name_contains", [], kind=list)]
        maximum = parameter(context, "max_parameters", None, kind=int)
        minimum = parameter(context, "min_parameters", None, kind=int)
        maximum_quant = parameter(context, "max_quant_bytes", None, kind=int)
        needs = [str(name) for name in parameter(context, "needs_facts", [], kind=list)]
        built = str(manifest.get("built_at", ""))[:10]
        rows = []
        for row in data.get("models", []):
            allowed, permitted = source_filter(row, context.contract)
            if not permitted:
                continue
            facts = model_facts(row, allowed, context.contract.excluded_publishers, context.contract.excluded_upstreams)
            uses = facts["uses"] or ""
            if use_case and use_case not in uses.split(", "):
                continue
            if any(facts.get(flag) is not True for flag in require):
                continue
            if names and not any(name in (str(row.get("name", "")) + " " + str(row.get("slug", ""))).lower()
                                 for name in names):
                continue
            if maximum is not None and (facts["parameters"] is None or facts["parameters"] > maximum):
                continue
            if minimum is not None and (facts["parameters"] is None or facts["parameters"] < minimum):
                continue
            if maximum_quant is not None and (facts["smallest_quant_bytes"] is None
                                              or facts["smallest_quant_bytes"] > maximum_quant):
                continue
            if any(facts.get(name) is None for name in needs):
                continue
            title, reason = clean_title(row.get("name"))
            url = _model_url(row)
            if reason or not url:
                continue
            read_days = sorted(source.get("read") for index, source in enumerate(row.get("sources", []))
                               if isinstance(source.get("read"), str) and allowed({"source": index}))
            licence = _first(row.get("facts", {}).get("licence"), allowed=allowed)
            rows.append(observation(
                context, self, key="model:" + str(row.get("slug")), origin="model:" + str(row.get("slug")),
                title=title, url=url, source_address=f"https://baltor.ai/models (directory built {built})",
                facts=facts, licence=licence if isinstance(licence, str) else None,
                licence_basis="the licence the model card declares" if isinstance(licence, str) else
                "no licence stated by the listed sources",
                event_at=facts["released"], observed_at=(read_days[-1] if read_days else built) or context.today))
        rank_by = parameter(context, "rank_by", "downloads", kind=str)
        ascending = parameter(context, "ascending", False, kind=bool)
        chosen = ranked(rows, rank_by, descending=not ascending)
        if not rows:
            return EngineAnswer(OK, "no model matched the declared filter", (), 0)
        return EngineAnswer(OK, "", tuple(chosen[:limit_of(context)]), 0)


class McpDirectory:
    """The packaged directory of protocol servers and agent interfaces, by category."""

    engine_id, engine_version = "mcp_directory", "1.0.0"
    material_facts = ("licence", "repository_state")

    def read(self, context: ReadContext) -> EngineAnswer:
        try:
            manifest = _json(context.repository, MCP_DIRECTORY / "manifest.json")
            parts = [_json(context.repository, MCP_DIRECTORY / Path(part["address"]).name)
                     for part in manifest.get("parts", [])]
        except (RadarEngineError, KeyError, TypeError) as error:
            return EngineAnswer(FAILED, str(error))
        columns = manifest.get("columns", [])
        categories = manifest.get("categories", [])
        labels = manifest.get("labels", {})
        day_zero = date.fromisoformat(manifest.get("day_zero", "1970-01-01"))
        generated = iso_time(manifest.get("generated_at")) or context.observed_at
        mode = parameter(context, "mode", "rows", kind=str, choices=("rows", "category_counts"))
        if mode == "category_counts":
            rows = [observation(
                context, self, key="mcp-category:" + str(item.get("id")), origin="mcp-category:" + str(item.get("id")),
                title=str(item.get("label")), url="https://baltor.ai/directory",
                source_address="https://baltor.ai/directory (packaged manifest)", facts={"servers": number(item.get("rows"))},
                observed_at=generated) for item in categories if isinstance(item, dict)]
            return EngineAnswer(OK, "", tuple(ranked(rows, "servers")[:limit_of(context)]), 0)
        wanted = parameter(context, "category", kind=str)
        category_ids = [item.get("id") for item in categories]
        if wanted not in category_ids:
            raise RadarEngineError("radar_parameter_invalid", f"mcp_directory category {wanted!r} is not in the manifest")
        position = {name: index for index, name in enumerate(columns)}
        needs_licence = parameter(context, "licence_required", True, kind=bool)
        rows, guards = [], []
        offering_bits = manifest.get("offering_bits", {})
        transport_bits = manifest.get("transport_bits", {})
        auth_bits = manifest.get("auth_bits", {})
        for part in parts:
            for values in part.get("rows", []):
                try:
                    row = {name: values[index] for name, index in position.items()}
                except (IndexError, TypeError):
                    continue
                index = row.get("category")
                if not isinstance(index, int) or not 0 <= index < len(category_ids) or category_ids[index] != wanted:
                    continue
                licence = manifest["licences"][row["licence"]] if isinstance(row.get("licence"), int) else ""
                if needs_licence and not licence:
                    continue
                repository = row.get("repository") or ""
                website = row.get("website") or ""
                address = ("https://" + repository) if repository else ("https://" + website) if website else ""
                try:
                    address = https_address(address, "directory address")
                except ValueError:
                    continue
                title, reason = clean_title(row.get("name"))
                if reason:
                    continue
                if isinstance(row.get("description"), str):
                    guards.append(row["description"])
                updated = (day_zero + timedelta(days=row["updated"])).isoformat() if isinstance(row.get("updated"), int) \
                    and row["updated"] > 0 else None
                origin = ("github:" + repository.split("github.com/", 1)[1].lower().rstrip("/")
                          if repository.startswith("github.com/") else "mcp:" + str(row.get("id")).lower())
                state = manifest["repository_states"][row["repository_state"]] if isinstance(
                    row.get("repository_state"), int) else None
                rows.append(observation(
                    context, self, key="mcp:" + str(row.get("id")), origin=origin, title=title, url=address,
                    source_address="https://baltor.ai/directory (packaged rows)",
                    facts={"publisher": text_fact(row.get("publisher")),
                           "offering": _bits(row.get("offering"), offering_bits, labels.get("offering", {})),
                           "transports": _bits(row.get("transports"), transport_bits, labels.get("transports", {})),
                           "authentication": _bits(row.get("auth"), auth_bits, labels.get("auth", {})),
                           "repository_state": state, "updated": updated},
                    licence=licence or None,
                    licence_basis=("from the " + manifest["licence_bases"][row["licence_basis"]]
                                   if isinstance(row.get("licence_basis"), int) and row["licence_basis"] else
                                   "not stated") if licence else "not stated",
                    source_published_at=updated, observed_at=generated))
        chosen = ranked(rows, parameter(context, "rank_by", "updated", kind=str))
        selected = tuple(chosen[:limit_of(context)])
        chosen_keys = {item.key for item in selected}
        return EngineAnswer(OK, "", selected, 0, tuple(guards[:400]) if chosen_keys else ())


def _bits(value, bits: dict, labels: dict):
    if not isinstance(value, int):
        return None
    names = [labels.get(name, name) for name, bit in sorted(bits.items(), key=lambda item: item[1]) if value & bit]
    return ", ".join(names) if names else None


class CuratedSeed:
    """Official links a person declared for a question. Unverified until the vetting stage checks them."""

    engine_id, engine_version = "curated_seed", "1.0.0"
    material_facts = ()

    def read(self, context: ReadContext) -> EngineAnswer:
        kind = parameter(context, "kind", "", kind=str)
        rows = []
        for seed in context.question.seeds:
            if kind and seed.kind != kind:
                continue
            facts = {"kind": seed.kind.replace("_", " ")}
            facts.update({"link_" + name: link for name, link in seed.links.items()})
            rows.append(observation(
                context, self, key="seed:" + seed.name.lower(), origin="seed:" + seed.url.lower().rstrip("/"),
                title=seed.name, url=seed.url, source_address="question registry seed",
                facts=facts, last_verified_at=None))
        if not rows:
            return EngineAnswer(FAILED, f"no seed of kind {kind!r} is declared for this question")
        return EngineAnswer(OK, "", tuple(rows[:limit_of(context)]), 0)


def _address(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return https_address(value if value.startswith("https://") else "https://" + value, "endpoint address")
    except ValueError:
        return None


class EndpointDirectory:
    """The packaged directory of hosted model endpoints and local runtimes, with their documentation pages."""

    engine_id, engine_version = "endpoint_directory", "1.0.0"
    material_facts = ("tool_calling", "structured_output", "api_styles")

    def read(self, context: ReadContext) -> EngineAnswer:
        try:
            data = _json(context.repository, MODEL_DIRECTORY / "endpoints.json")
        except RadarEngineError as error:
            return EngineAnswer(FAILED, str(error))
        kind = parameter(context, "kind", "", kind=str)
        needs = [str(name) for name in parameter(context, "needs_facts", [], kind=list)]
        rows = []
        for row in data.get("endpoints", []):
            if not isinstance(row, dict) or (kind and row.get("kind") != kind):
                continue
            allowed, permitted = source_filter(row, context.contract)
            if not permitted:
                continue
            raw = row.get("facts") if isinstance(row.get("facts"), dict) else {}
            facts = {name: value for name, value in raw.items() if isinstance(value, dict) and allowed(value)}
            documentation = _address((facts.get("documentation") or {}).get("address"))
            if documentation is None:
                # A local runtime has no hosted documentation fact; its first recorded source page is its documentation.
                documentation = next((_address(source.get("address")) for index, source in enumerate(row.get("sources", []))
                                      if isinstance(source, dict) and allowed({"source": index})
                                      and _address(source.get("address"))), None)
            title, reason = clean_title(row.get("name"))
            if reason or not documentation:
                continue
            styles = sorted({api.get("style") for api in row.get("apis", []) if isinstance(api, dict) and allowed(api)
                             and isinstance(api.get("style"), str)})
            values = {
                "kind": text_fact(row.get("kind")),
                "api_styles": ", ".join(styles) if styles else None,
                "local_address": next((api.get("base") for api in row.get("apis", []) if isinstance(api, dict)
                                       and allowed(api) and str(api.get("base", "")).startswith("localhost:")), None),
                "tool_calling": (facts.get("tool_calling") or {}).get("value"),
                "structured_output": (facts.get("structured_output") or {}).get("value"),
                "models_listed": sum(1 for model in row.get("models", []) if allowed(model)) or None,
                "pricing_page": _address((facts.get("pricing") or {}).get("address")),
                "rate_limits_page": _address((facts.get("rate_limits") or {}).get("address")),
                "data_policy_page": _address((facts.get("data_policy") or {}).get("address")),
            }
            if any(values.get(name) is None for name in needs):
                continue
            read_days = sorted(source.get("read") for index, source in enumerate(row.get("sources", []))
                               if isinstance(source, dict) and isinstance(source.get("read"), str)
                               and allowed({"source": index}))
            host = documentation.split("/")[2]
            rows.append(observation(
                context, self, key="endpoint:" + str(row.get("slug")), origin="site:" + host, title=title,
                url=documentation, source_address="https://baltor.ai/endpoints (packaged endpoint rows)",
                facts=values, licence_basis="a hosted service or runtime; its terms are on its own pages",
                observed_at=read_days[-1] if read_days else context.today))
        chosen = ranked(rows, parameter(context, "rank_by", "models_listed", kind=str))
        return EngineAnswer(OK, "" if rows else "no endpoint matched the declared filter",
                            tuple(chosen[:limit_of(context)]), 0)


ENGINES = (CollectorState(), ModelDirectory(), McpDirectory(), EndpointDirectory(), CuratedSeed())

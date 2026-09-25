"""Endpoint rows: hosted model services and local runtimes, with the harness setup facts.

Kind: development tool module. A reviewed endpoint takes its API styles, authentication, rate-limit,
pricing and data-policy facts from `provider_documentation.json`, each with the page it came from
and the day a person read it, and its model list and prices from models.dev. Any other models.dev
provider that publishes an OpenAI-compatible address becomes a row with only what models.dev says.
A local runtime takes everything from the reviewed record.
"""
from __future__ import annotations

from loop_engine.core.service_runtime import model_directory as records

from .rows import RowSources, no_relationship, record_day, slug_of, variable_parts

MODELSDEV_ADDRESS = "models.dev/api.json"
BALTOR_REPOSITORY = "github.com/alisonjieli-png/loop-engine/blob/main/"


def _documented_sources(entry: dict, sources_of: RowSources) -> dict:
    return {key: sources_of.add("provider_documentation", address, day) for key, (address, day) in entry["sources"].items()}


def _models_list(provider: dict, md_answer, sources_of: RowSources, model_slugs: dict) -> list:
    if not provider or not md_answer.usable:
        return []
    source = sources_of.add("modelsdev", MODELSDEV_ADDRESS, md_answer.read_on)
    listed = []
    for model_id, model in sorted((provider.get("models") or {}).items()):
        cost = model.get("cost") or {}
        limit = model.get("limit") or {}
        as_of = record_day(model.get("last_updated"), md_answer.read_on)
        item = {"id": model_id, "name": str(model.get("name") or model_id), "source": source, "as_of": as_of}
        if isinstance(cost.get("input"), (int, float)) and isinstance(cost.get("output"), (int, float)):
            item["input"], item["output"] = float(cost["input"]), float(cost["output"])
        if isinstance(limit.get("context"), int) and limit["context"] > 0:
            item["context"] = limit["context"]
        if isinstance(model.get("tool_call"), bool):
            item["tool_calling"] = model["tool_call"]
        slug = model_slugs.get(model_id.lower())
        if slug:
            item["model_slug"] = slug
        listed.append(item)
    return listed


def _hosted_row(entry: dict, md: dict, md_answer, model_slugs: dict, baltor: list) -> dict:
    sources_of = RowSources()
    keys = _documented_sources(entry, sources_of)
    apis = []
    for api in entry["apis"]:
        item = {"style": api["style"], "base": api["base"], "source": keys[api["source"]]}
        if api.get("note"):
            item["note"] = api["note"]
        apis.append(item)
    auth = entry.get("auth")
    facts = {}
    for name, fact in entry.get("facts", {}).items():
        item = {"source": keys[fact["source"]]}
        for key in ("value", "note", "address"):
            if key in fact:
                item[key] = fact[key]
        facts[name] = item
    models = _models_list(md.get(entry.get("modelsdev") or "") or {}, md_answer, sources_of, model_slugs)
    observed = [item for item in baltor if item["provider"] == entry["slug"]]
    if observed:
        source = sources_of.add("baltor_records", BALTOR_REPOSITORY + observed[0]["path"], observed[0]["observed_at"])
        facts["observed_output_limits"] = {"source": source, "value": len(observed),
                                           "note": "Baltor's own provider client declares an output limit for "
                                           + ", ".join(f"{item['model']} ({item['maximum_output_tokens']:,} tokens, {item['observed_at']})" for item in observed[:12])
                                           + (" and more" if len(observed) > 12 else "") + "."}
    return {"slug": entry["slug"], "name": entry["name"], "kind": records.ENDPOINT_HOSTED, "sources": sources_of.items,
            "apis": apis, "auth": None if not auth else {"header": auth["header"], "variable": list(auth["variable"]), "source": keys[auth["source"]]},
            "facts": facts, "setup": {}, "models": models, "openrouter_provider": entry.get("openrouter_provider") or "",
            "commercial_relationship": no_relationship()}


def _listed_row(provider_id: str, provider: dict, md_answer, model_slugs: dict, taken: set) -> "dict | None":
    base = provider.get("api")
    if not isinstance(base, str) or not base.startswith(records.SCHEME + "://") or "@ai-sdk/openai-compatible" != provider.get("npm"):
        return None
    slug = slug_of(provider_id)
    if not slug or slug in taken:
        return None
    sources_of = RowSources()
    source = sources_of.add("modelsdev", MODELSDEV_ADDRESS, md_answer.read_on)
    address = base[len(records.SCHEME) + 3:].rstrip("/")
    if not records._ADDRESS.match(address):
        return None
    facts = {}
    doc = provider.get("doc")
    if isinstance(doc, str) and doc.startswith(records.SCHEME + "://") and records._ADDRESS.match(doc[len(records.SCHEME) + 3:]):
        facts["documentation"] = {"source": source, "address": doc[len(records.SCHEME) + 3:]}
    models = _models_list(provider, md_answer, sources_of, model_slugs)
    with_tools = [item for item in models if item.get("tool_calling") is True]
    if models:
        facts["tool_calling"] = {"source": source, "value": f"{len(with_tools)} of {len(models)} listed models",
                                 "note": "The share of this provider's models that models.dev records with tool calling."}
    variables = [name for name in provider.get("env") or () if isinstance(name, str)]
    auth = {"header": "Authorization: Bearer", "variable": variable_parts(variables[0]), "source": source,
            "note": "The key goes in a bearer header, the convention of OpenAI-compatible addresses; models.dev names the variable."} if variables else None
    return {"slug": slug, "name": str(provider.get("name") or provider_id), "kind": records.ENDPOINT_HOSTED,
            "sources": sources_of.items, "apis": [{"style": records.API_OPENAI_CHAT, "base": address, "source": source}],
            "auth": auth, "facts": facts, "setup": {}, "models": models, "openrouter_provider": "",
            "commercial_relationship": no_relationship()}


def _local_row(entry: dict) -> dict:
    sources_of = RowSources()
    keys = _documented_sources(entry, sources_of)
    apis = [{"style": api["style"], "scheme": api["scheme"], "base": api["base"], "source": keys[api["source"]]} for api in entry["apis"]]
    setup = {}
    for name, value in entry.get("setup", {}).items():
        setup[name] = {**{key: item for key, item in value.items() if key != "source"}, "source": keys[value["source"]]}
    setup["formats"] = list(entry.get("formats") or ())
    return {"slug": entry["slug"], "name": entry["name"], "kind": records.ENDPOINT_LOCAL, "sources": sources_of.items,
            "apis": apis, "auth": None, "facts": {}, "setup": setup, "models": [], "openrouter_provider": "",
            "commercial_relationship": no_relationship()}


def harness_records(documentation: dict) -> list:
    """The harness setup facts the pages turn into configuration, each with its dated source."""
    harnesses = []
    for entry in documentation.get("harnesses") or ():
        address, day = entry["sources"][entry["source"]]
        harnesses.append({"slug": entry["slug"], "name": entry["name"], "styles": list(entry["styles"]), "file": entry["file"],
                          "note": entry.get("note", ""), "api_names": dict(entry.get("api_names") or {}),
                          "oss_providers": list(entry.get("oss_providers") or ()), "oss_names": dict(entry.get("oss_names") or {}),
                          "sources": [{"id": "harness_documentation", "address": item[0], "read": item[1]} for item in entry["sources"].values()],
                          "source_address": address, "source_read": day})
    return harnesses


def assemble_endpoints(documentation: dict, md_answer, model_rows: list, baltor: list) -> list:
    """Every endpoint row: the reviewed hosted services, the other models.dev providers, the local runtimes."""
    md = md_answer.value if isinstance(md_answer.value, dict) else {}
    model_slugs = {}
    for row in model_rows:
        for key in ("huggingface", "openrouter", "modelsdev"):
            identifier = row["ids"].get(key)
            if isinstance(identifier, str):
                model_slugs.setdefault(identifier.lower(), row["slug"])
                model_slugs.setdefault(identifier.split("/", 1)[-1].lower(), row["slug"])
    rows = [_hosted_row(entry, md, md_answer, model_slugs, baltor) for entry in documentation.get("hosted") or ()]
    taken = {row["slug"] for row in rows} | {entry["slug"] for entry in documentation.get("local") or ()}
    reviewed = {entry.get("modelsdev") for entry in documentation.get("hosted") or ()}
    for provider_id, provider in sorted(md.items()):
        if provider_id in reviewed:
            continue
        row = _listed_row(provider_id, provider, md_answer, model_slugs, taken)
        if row is not None:
            rows.append(row)
            taken.add(row["slug"])
    rows.extend(_local_row(entry) for entry in documentation.get("local") or ())
    return rows

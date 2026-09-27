"""Model rows: one per model, from Hugging Face, models.dev, LiteLLM and LMArena, joined on exact identifiers.

Kind: development tool module. An open model is a row from its Hugging Face repository. A hosted model is a row from
the models.dev list of its maker's own API, for the makers the reviewed record names. Another source joins a row only on
an exact identifier:

- a models.dev offer or a LiteLLM entry joins an open row when its model identifier equals the Hugging Face repository,
  ignoring case, and brings that provider's price only;
- the maker's own LiteLLM entry joins a hosted row when it names exactly the model identifier of the maker's models.dev
  list, and brings its limits, capability flags and price;
- an LMArena score joins a hosted row when the arena names that maker and exactly the same model identifier.

Nothing is joined on a similar name, so a row never borrows another model's facts. Every fact names its source and
basis. Unknown facts are left out. Estimates say so. Nothing is read from OpenRouter or Artificial Analysis: their terms
forbid republishing their data, so the pages link to them instead.
"""
from __future__ import annotations

import re

from loop_engine.core.service_runtime import model_directory as records
from loop_engine.core.service_runtime import model_directory_fit as fit

from . import sources
from .rows import RowSources, no_relationship, per_million, record_day, scheme_free, slug_of

MODELSDEV_ADDRESS = "models.dev/api.json"
#: The name, publisher and page of the one LMArena result the directory republishes, with the licence LMArena gives it.
ARENA_RESULT = "Arena text score"
ARENA_PUBLISHER = "LMArena"
ARENA_PAGE_ADDRESS = "arena.ai/leaderboard"
_CODE_NAME = re.compile(r"(?i)(?:coder|codestral|devstral|starcoder|codellama|codegemma|codegen|(?<![a-z])code(?![a-z]))")
_MODALITY_BY_TASK = {"text-generation": (["text"], ["text"]), "image-text-to-text": (["text", "image"], ["text"]),
                     "feature-extraction": (["text"], ["embeddings"]), "sentence-similarity": (["text"], ["embeddings"]),
                     "text-ranking": (["text"], ["scores"])}
_USE_BY_TASK = {"feature-extraction": "embeddings", "sentence-similarity": "embeddings", "text-ranking": "rerank",
                "image-text-to-text": "vision"}


def _licence(record: dict) -> "tuple[str, str]":
    card = record.get("cardData") or {}
    licence = card.get("license")
    if isinstance(licence, list):
        licence = licence[0] if licence else None
    if not isinstance(licence, str) or not licence.strip():
        licence = next((str(tag)[8:] for tag in record.get("tags") or () if str(tag).startswith("license:")), "")
    link = card.get("license_link") if isinstance(card.get("license_link"), str) else ""
    if link.startswith("LICENSE") or link.startswith("./"):
        link = "huggingface.co/" + record["id"] + "/blob/main/" + link.lstrip("./")
    return licence.strip(), scheme_free(link) if "://" in link else link


def _chat_template(record: dict) -> str:
    tokenizer = ((record.get("config") or {}).get("tokenizer_config") or {})
    template = tokenizer.get("chat_template")
    if isinstance(template, list):
        template = " ".join(str(item.get("template", "")) for item in template if isinstance(item, dict))
    return template if isinstance(template, str) else ""


def _use(row: dict, value: str, source: int, basis: str) -> None:
    if all(item["value"] != value for item in row["use_cases"]):
        row["use_cases"].append({"value": value, "source": source, "basis": basis})


def sources_slug(name: str) -> str:
    return slug_of(name) or "provider"


def _modelsdev_offer(row: dict, add, provider_id: str, provider: dict, model: dict, read_on: str, maker_api: bool) -> None:
    source = add("modelsdev", MODELSDEV_ADDRESS, read_on)
    cost = model.get("cost") or {}
    as_of = record_day(model.get("last_updated"), read_on)
    if isinstance(cost.get("input"), (int, float)) and isinstance(cost.get("output"), (int, float)):
        price = {"provider": provider.get("name") or provider_id, "provider_slug": sources_slug(provider_id),
                 "route": records.ROUTE_DIRECT, "model_id": model["id"], "input": float(cost["input"]),
                 "output": float(cost["output"]), "as_of": as_of, "source": source}
        if isinstance(cost.get("cache_read"), (int, float)):
            price["cache_read"] = float(cost["cache_read"])
        limit = model.get("limit") or {}
        if isinstance(limit.get("context"), int) and limit["context"] > 0:
            price["context"] = limit["context"]
        if isinstance(limit.get("output"), int) and limit["output"] > 0:
            price["max_output"] = limit["output"]
        row["prices"].append(price)
    if not maker_api:
        return
    facts = row["facts"]
    limit = model.get("limit") or {}
    if isinstance(limit.get("context"), int) and limit["context"] > 0:
        facts.setdefault("context", []).append({"value": limit["context"], "source": source, "basis": "the context limit models.dev records for the maker's own API"})
    if isinstance(limit.get("output"), int) and limit["output"] > 0:
        facts.setdefault("max_output", []).append({"value": limit["output"], "source": source, "basis": "the output limit models.dev records for the maker's own API"})
    for key, name in (("tool_call", "tool_calling"), ("structured_output", "structured_output"), ("reasoning", "reasoning")):
        if isinstance(model.get(key), bool):
            facts.setdefault(name, []).append({"value": model[key], "source": source, "basis": f"models.dev records {key} as {str(model[key]).lower()}"})
    if isinstance(model.get("open_weights"), bool):
        facts["open_weights"] = {"value": model["open_weights"], "source": source, "basis": "models.dev records whether the weights are open"}
    if record_day(model.get("release_date"), ""):
        facts["released"] = {"value": model["release_date"], "source": source, "basis": "the release date models.dev records"}
    if isinstance(model.get("knowledge"), str) and re.match(r"^\d{4}-\d{2}(-\d{2})?$", model["knowledge"]):
        facts.setdefault("knowledge_cutoff", {"value": model["knowledge"], "source": source, "basis": "the knowledge cutoff models.dev records"})
    modalities = model.get("modalities") or {}
    if modalities.get("input") and "modalities" not in facts:
        facts["modalities"] = {"input": list(modalities["input"]), "output": list(modalities.get("output") or []), "source": source}
    if "image" in (modalities.get("input") or ()):
        _use(row, "vision", source, "models.dev lists images among its inputs")
    if model.get("reasoning") is True:
        _use(row, "reasoning", source, "models.dev records it as a reasoning model")


def _empty_row(identifier_kind: str, identifier: str, name: str, maker: str) -> dict:
    return {"slug": "", "name": name, "maker": maker, "ids": {identifier_kind: identifier}, "sources": [],
            "facts": {}, "quantizations": [], "prices": [], "use_cases": [], "benchmarks": [], "popularity": None,
            "commercial_relationship": no_relationship()}


def _hugging_face_row(record: dict, answer, config_answer, config_address: str, gguf: tuple, today: str) -> tuple:
    """A row from one Hugging Face repository, its configuration and its GGUF copy."""
    identifier = record["id"]
    row = _empty_row("huggingface", identifier, identifier.split("/", 1)[-1], str(record.get("author") or identifier.split("/")[0]))
    sources_of = RowSources()
    add = sources_of.add
    source = add("huggingface", "huggingface.co/api/models/" + identifier, answer.read_on)
    facts = row["facts"]
    created = str(record.get("createdAt") or "")[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", created):
        facts["released"] = {"value": created, "source": source, "basis": "the day the repository was first published on Hugging Face"}
    licence, link = _licence(record)
    if licence:
        facts["licence"] = {"value": licence, "source": source, "basis": "the licence the model card declares"}
        if link and records._ADDRESS.match(link):
            facts["licence"]["link"] = link
    total = (record.get("safetensors") or {}).get("total")
    if isinstance(total, int) and total > 0:
        facts["parameters"] = {"value": total, "source": source, "basis": "counted from the safetensors weight files"}
    facts["open_weights"] = {"value": True, "source": source, "basis": "the weights are published in this Hugging Face repository"
                             + (", behind the maker's access form" if record.get("gated") else "")}
    task = record.get("pipeline_tag") or ""
    if task in _MODALITY_BY_TASK:
        inputs, outputs = _MODALITY_BY_TASK[task]
        facts["modalities"] = {"input": list(inputs), "output": list(outputs), "source": source}
    if task in _USE_BY_TASK:
        _use(row, _USE_BY_TASK[task], source, f"Hugging Face files it under {task}")
    if _CODE_NAME.search(identifier.split("/", 1)[-1]):
        _use(row, "coding", source, "the maker's name for the model marks it for code")
    template = _chat_template(record)
    if template:
        accepts = "tools" in template
        facts["tool_calling"] = [{"value": accepts, "source": source, "basis": "the chat template in the tokenizer configuration "
                                  + ("accepts tool definitions" if accepts else "has no place for tool definitions")}]
    if config_answer is not None and config_answer.usable and isinstance(config_answer.value, dict):
        config = config_answer.value
        config_source = add("huggingface_config", config_address, config_answer.read_on)
        architecture = fit.architecture_from_config(config)
        if architecture.layers or architecture.max_context:
            fact = {"source": config_source, "layers": architecture.layers, "kv_heads": architecture.kv_heads,
                    "head_dim": architecture.head_dim, "attention": architecture.attention,
                    "latent_width": architecture.latent_width, "max_context": architecture.max_context}
            sliding = fit.sliding_layers(config)
            if sliding:
                fact["sliding"] = list(sliding)
            if config_address.split("/")[1] != identifier.split("/")[0]:
                fact["basis"] = "read from the public copy " + "/".join(config_address.split("/")[1:3]) + ", because the original repository is gated"
            facts["architecture"] = fact
        if architecture.max_context:
            facts.setdefault("context", []).append({"value": architecture.max_context, "source": config_source,
                                                    "basis": "the maximum position embeddings in the model configuration"})
        if isinstance(total, int) and total > 0:
            active = fit.active_parameters_from_config(config, total)
            if active:
                facts["active_parameters"] = {"value": active, "source": config_source, "estimate": True,
                                              "basis": "estimated from the expert counts and sizes in the configuration"}
    repository, quantized, tree_answer = gguf
    if repository and quantized:
        gguf_source = add("huggingface_gguf", "huggingface.co/api/models/" + repository + "/tree/main", tree_answer.read_on)
        for name, (size, files) in sorted(quantized.items(), key=lambda item: item[1][0]):
            row["quantizations"].append({"name": name, "format": "gguf", "bytes": size, "repository": repository,
                                         "files": files[:6], "source": gguf_source})
    downloads, likes = record.get("downloads"), record.get("likes")
    if isinstance(downloads, int) and isinstance(likes, int):
        row["popularity"] = {"downloads": downloads, "likes": likes, "source": source}
    row["benchmarks"].append({"name": "Results the maker published on the model card", "publisher": row["maker"],
                              "address": "huggingface.co/" + identifier, "source": source})
    return row, sources_of


def _whole(value) -> "int | None":
    """A positive whole number from a source that may write it as a float, or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 or int(value) != value:
        return None
    return int(value)


#: The LiteLLM capability flags the directory reads, and the fact each one states for the maker's own API.
_LITELLM_FLAGS = {"supports_function_calling": "tool_calling", "supports_response_schema": "structured_output",
                  "supports_reasoning": "reasoning"}


def _provider_key(name: str) -> str:
    return name.lower().replace("-", "_")


def litellm_index(answer, providers: dict) -> dict:
    """LiteLLM's text, embedding and ranking entries by lowercase model identifier.

    A key that starts with its provider's name and a slash names the model after the slash, which is the identifier the
    provider itself uses. Each entry keeps the models.dev provider the reviewed record maps its provider to, or None.
    """
    index: dict = {}
    for key, entry in sorted((answer.value or {}).items() if isinstance(answer.value, dict) else ()):
        if not isinstance(entry, dict) or entry.get("mode") not in sources.LITELLM_MODES:
            continue
        provider = entry.get("litellm_provider")
        if not isinstance(provider, str) or not provider or not isinstance(key, str):
            continue
        head, slash, rest = key.partition("/")
        model_id = rest if slash and rest and _provider_key(head) == _provider_key(provider) else key
        index.setdefault(model_id.lower(), []).append({"key": key, "model_id": model_id, "provider": provider,
                                                       "modelsdev": providers.get(provider), "entry": entry})
    return index


def _litellm_offer(row: dict, add, item: dict, read_on: str, md: dict, maker_api: bool) -> None:
    """One LiteLLM entry on a row: its price unless a models.dev price of the same provider is there, and, for the
    maker's own API, its limits and capability flags."""
    entry, mapped = item["entry"], item["modelsdev"]
    slug = sources_slug(mapped) if mapped else slug_of(item["provider"]) or "provider"
    name = str((md.get(mapped) or {}).get("name") or mapped) if mapped else item["provider"]
    prompt, completion = per_million(entry.get("input_cost_per_token")), per_million(entry.get("output_cost_per_token"))
    priced = prompt is not None and completion is not None and all(price["provider_slug"] != slug for price in row["prices"])
    described = maker_api and (bool(_whole(entry.get("max_input_tokens")) or _whole(entry.get("max_output_tokens")))
                               or any(isinstance(entry.get(key), bool) for key in _LITELLM_FLAGS)
                               or entry.get("supports_vision") is True)
    if not priced and not described:
        return
    source = add("litellm", sources.LITELLM_ADDRESS, read_on)
    if priced:
        price = {"provider": name, "provider_slug": slug, "route": records.ROUTE_DIRECT, "model_id": item["model_id"],
                 "input": prompt, "output": completion, "as_of": read_on, "source": source}
        cache = per_million(entry.get("cache_read_input_token_cost"))
        if cache is not None:
            price["cache_read"] = cache
        for key, field in (("max_input_tokens", "context"), ("max_output_tokens", "max_output")):
            if _whole(entry.get(key)):
                price[field] = _whole(entry.get(key))
        row["prices"].append(price)
    if not maker_api:
        return
    facts = row["facts"]
    if _whole(entry.get("max_input_tokens")):
        facts.setdefault("context", []).append({"value": _whole(entry["max_input_tokens"]), "source": source,
                                                "basis": "the input limit LiteLLM records for the maker's own API"})
    if _whole(entry.get("max_output_tokens")):
        facts.setdefault("max_output", []).append({"value": _whole(entry["max_output_tokens"]), "source": source,
                                                   "basis": "the output limit LiteLLM records for the maker's own API"})
    for key, fact in _LITELLM_FLAGS.items():
        if isinstance(entry.get(key), bool):
            facts.setdefault(fact, []).append({"value": entry[key], "source": source,
                                               "basis": f"LiteLLM records {key} as {str(entry[key]).lower()} for the maker's own API"})
    if entry.get("supports_vision") is True:
        _use(row, "vision", source, "LiteLLM records vision support for the maker's own API")
    if entry.get("supports_reasoning") is True:
        _use(row, "reasoning", source, "LiteLLM records reasoning support for the maker's own API")


def join_arena(rows: list, answer, organizations: dict) -> dict:
    """Add the arena score to each hosted row whose maker the arena names, for exactly the same model identifier.

    The arena's organization field decides the maker; a row with no organization, or one the reviewed record does not
    map, joins nothing. The score is rounded to a whole number, a change the pages state beside the licence.
    """
    report = {"state": answer.state, "read": answer.read_on, "rows": 0, "joined": 0}
    if not answer.usable:
        return report
    hosted: dict = {}
    for row, sources_of in rows:
        identifier = row["ids"].get("modelsdev")
        if isinstance(identifier, str) and "huggingface" not in row["ids"]:
            provider, _, model = identifier.partition("/")
            hosted.setdefault((provider, model.lower()), []).append((row, sources_of))
    for item in answer.value:
        name, rating = item.get("model_name"), item.get("rating")
        published = record_day(item.get("leaderboard_publish_date"), "")
        if not isinstance(name, str) or not name.strip() or isinstance(rating, bool) or not isinstance(rating, (int, float)):
            continue
        report["rows"] += 1
        organization = str(item.get("organization") or "").strip().lower()
        for provider in organizations.get(organization, ()):
            for row, sources_of in hosted.get((provider, name.strip().lower()), ()):
                if any(result["name"] == ARENA_RESULT for result in row["benchmarks"]):
                    continue
                result = {"name": ARENA_RESULT, "value": round(rating), "publisher": ARENA_PUBLISHER,
                          "address": ARENA_PAGE_ADDRESS, "source": sources_of.add("lmarena", sources.ARENA_ADDRESS, answer.read_on)}
                if published:
                    result["as_of"] = published
                row["benchmarks"].append(result)
                report["joined"] += 1
    return report


def assemble_models(reader, documentation: dict, root, today: str, gguf_limit: int, progress=print) -> tuple:
    """Every model row, and a report of what was read, reused, kept and refused."""
    makers = sorted(set(documentation["maker_providers"]["providers"]))
    report = {"lists": [], "refused": [], "gguf_repositories": 0, "configurations": 0, "served_copies": 0,
              "served_repositories": 0, "hosted_repositories": 0}
    hf: dict = {}
    copies: dict = {}
    for task, sort, limit in sources.HF_LISTS:
        answer = sources.hf_list(reader, task, sort, limit)
        kept = 0
        for record in answer.value or ():
            if not isinstance(record, dict) or not isinstance(record.get("id"), str) or record["id"] in hf:
                continue
            if sources.is_copy(record):
                copies.setdefault(record["id"].lower(), (record, answer))
                continue
            hf[record["id"]] = (record, answer)
            kept += 1
        report["lists"].append({"task": task, "sort": sort, "limit": limit, "state": answer.state, "read": answer.read_on, "added": kept})
    md_answer = sources.modelsdev(reader)
    md = md_answer.value if isinstance(md_answer.value, dict) else {}
    ll_answer = sources.litellm_prices(reader)
    litellm = litellm_index(ll_answer, documentation["litellm_providers"]["map"])
    # A repository a provider serves under its exact name is the model itself, even when Hugging Face tags it like a
    # quantized copy: a model published in 8-bit or FP8 weights carries those tags. Such a repository from the lists
    # above gets its row back when models.dev or LiteLLM names a provider that serves it by that name.
    served = {model_id.lower() for provider in md.values() for model_id in (provider.get("models") or {}) if model_id.count("/") == 1}
    served |= {model_id for model_id in litellm if model_id.count("/") == 1}
    for model_id in sorted(served & set(copies)):
        record, answer = copies[model_id]
        if record["id"] not in hf:
            hf[record["id"]] = (record, answer)
            report["served_copies"] += 1
    # A served repository outside the lists is found in its author's own list, one request for each author who already
    # has a row, and gets its row when the name matches exactly.
    authors = {identifier.split("/", 1)[0].lower(): identifier.split("/", 1)[0] for identifier in hf}
    known = {identifier.lower() for identifier in hf}
    wanted: dict = {}
    for model_id in sorted(served - known):
        if model_id.split("/", 1)[0] in authors:
            wanted.setdefault(authors[model_id.split("/", 1)[0]], set()).add(model_id)
    for author, names in sorted(wanted.items()):
        answer = sources.hf_author_models(reader, author)
        for record in answer.value or ():
            if isinstance(record, dict) and isinstance(record.get("id"), str) and record["id"].lower() in names and record["id"] not in hf:
                hf[record["id"]] = (record, answer)
                report["served_repositories"] += 1
    # A repository that Hugging Face's own inference router serves gets its row even outside the lists. models.dev's list
    # of that router names each one by its repository.
    known = {identifier.lower() for identifier in hf}
    for model_id in sorted((md.get(sources.HF_ROUTER_PROVIDER) or {}).get("models") or ()):
        if model_id.count("/") == 1 and model_id.lower() not in known:
            answer = sources.hf_model(reader, model_id)
            if answer.usable and isinstance(answer.value, dict) and answer.value.get("id") == model_id:
                hf[model_id] = (answer.value, answer)
                report["hosted_repositories"] += 1
    by_hf_id: dict = {}
    for provider_id, provider in md.items():
        for model_id, model in (provider.get("models") or {}).items():
            by_hf_id.setdefault(model_id.lower(), []).append((provider_id, provider, {**model, "id": model_id}))
    rows, used_md = [], set()
    ordered = sorted(hf, key=lambda key: (-(hf[key][0].get("downloads") or 0), key))
    for position, identifier in enumerate(ordered):
        record, answer = hf[identifier]
        config_answer, config_address, gguf = None, "", ("", {}, None)
        task = record.get("pipeline_tag") or ""
        wants_files = task in ("text-generation", "image-text-to-text") and position < gguf_limit
        if wants_files:
            config_address = "huggingface.co/" + identifier + "/raw/main/config.json"
            config_answer = sources.hf_config(reader, identifier) if not record.get("gated") else None
            if (config_answer is None or not config_answer.usable) and record.get("gated"):
                copy = "unsloth/" + identifier.split("/", 1)[1]
                mirror = sources.hf_config(reader, copy)
                expected = (record.get("config") or {}).get("model_type")
                if mirror.usable and isinstance(mirror.value, dict) and expected and mirror.value.get("model_type") == expected:
                    config_answer, config_address = mirror, "huggingface.co/" + copy + "/raw/main/config.json"
            report["configurations"] += int(bool(config_answer and config_answer.usable))
            listing = sources.hf_quantized(reader, identifier, "gguf")
            candidates = [item for item in listing.value or () if isinstance(item, dict) and not item.get("gated") and isinstance(item.get("id"), str)]
            same_maker = [item for item in candidates if item.get("author") == record.get("author")]
            chosen = (same_maker or candidates or [None])[0]
            if chosen is not None:
                tree = sources.hf_tree(reader, chosen["id"])
                total = (record.get("safetensors") or {}).get("total")
                quantized = sources.gguf_quantizations(tree.value if isinstance(tree.value, list) else [], total)
                if quantized:
                    gguf = (chosen["id"], quantized, tree)
                    report["gguf_repositories"] += 1
        row, sources_of = _hugging_face_row(record, answer, config_answer, config_address, gguf, today)
        for provider_id, provider, offer in by_hf_id.get(identifier.lower(), ()):
            _modelsdev_offer(row, sources_of.add, provider_id, provider, offer, md_answer.read_on, False)
            used_md.add((provider_id, offer["id"]))
        for item in litellm.get(identifier.lower(), ()):
            _litellm_offer(row, sources_of.add, item, ll_answer.read_on, md, False)
        rows.append((row, sources_of))
        if position % 100 == 0:
            progress(f"models: {position} of {len(ordered)} open models assembled; {reader.summary()['answers']}")
    for provider_id in makers:
        provider = md.get(provider_id) or {}
        for model_id, offer in sorted((provider.get("models") or {}).items()):
            if (provider_id, model_id) in used_md:
                continue
            row = _empty_row("modelsdev", provider_id + "/" + model_id, str(offer.get("name") or model_id), str(provider.get("name") or provider_id))
            sources_of = RowSources()
            _modelsdev_offer(row, sources_of.add, provider_id, provider, {**offer, "id": model_id}, md_answer.read_on, True)
            # The maker's own LiteLLM entry, the first by key when LiteLLM keeps the model under two keys.
            own = next((item for item in litellm.get(model_id.lower(), ()) if item["modelsdev"] == provider_id), None)
            if own is not None:
                _litellm_offer(row, sources_of.add, own, ll_answer.read_on, md, True)
            rows.append((row, sources_of))
    arena_answer = sources.arena_text_leaderboard(reader)
    report["arena"] = join_arena(rows, arena_answer, documentation["arena_organizations"]["map"])
    report["litellm"] = {"state": ll_answer.state, "read": ll_answer.read_on, "entries": sum(len(items) for items in litellm.values())}
    return rows, report, {"modelsdev": md_answer, "litellm": ll_answer, "arena": arena_answer}

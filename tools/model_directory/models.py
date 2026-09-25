"""Model rows: one per model, from Hugging Face, OpenRouter and models.dev, joined on exact identifiers.

Kind: development tool module. A Hugging Face repository and an OpenRouter model are one row only
when OpenRouter names that repository in its hugging_face_id field. A models.dev offer joins a row
only when its model identifier equals the row's Hugging Face identifier, or when the maker's own
models.dev provider lists exactly the model identifier OpenRouter uses. Nothing is joined on a
similar name, so a row never borrows another model's facts.

Every fact names its source and basis. Unknown facts are left out. Estimates say so.
"""
from __future__ import annotations

import re

from loop_engine.core.service_runtime import model_directory as records
from loop_engine.core.service_runtime import model_directory_fit as fit

from . import sources
from .rows import RowSources, day_of_epoch, no_relationship, per_million, record_day, scheme_free, split_openrouter_name

MODELSDEV_ADDRESS = "models.dev/api.json"
OPENROUTER_ADDRESS = "openrouter.ai/api/v1/models"
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


def _openrouter_facts(model: dict, row: dict, add, source: int) -> None:
    facts = row["facts"]
    if isinstance(model.get("context_length"), int) and model["context_length"] > 0:
        facts.setdefault("context", []).append({"value": model["context_length"], "source": source,
                                                "basis": "the context length OpenRouter lists"})
    top = model.get("top_provider") or {}
    if isinstance(top.get("max_completion_tokens"), int) and top["max_completion_tokens"] > 0:
        facts.setdefault("max_output", []).append({"value": top["max_completion_tokens"], "source": source,
                                                   "basis": "the largest output OpenRouter's first provider allows"})
    architecture = model.get("architecture") or {}
    if architecture.get("input_modalities") and "modalities" not in facts:
        facts["modalities"] = {"input": list(architecture["input_modalities"]),
                               "output": list(architecture.get("output_modalities") or []), "source": source}
    supported = set(model.get("supported_parameters") or ())
    facts.setdefault("tool_calling", []).append({"value": "tools" in supported, "source": source,
                                                 "basis": "OpenRouter lists tools among the supported parameters" if "tools" in supported
                                                 else "OpenRouter does not list tools among the supported parameters"})
    structured = bool(supported & {"structured_outputs", "response_format"})
    facts.setdefault("structured_output", []).append({
        "value": structured, "source": source,
        "basis": ("OpenRouter lists structured outputs among the supported parameters" if "structured_outputs" in supported
                  else "OpenRouter lists response_format, a JSON mode, among the supported parameters" if structured
                  else "OpenRouter lists no structured output parameter")})
    reasoning = model.get("reasoning") if isinstance(model.get("reasoning"), dict) else None
    if reasoning or "reasoning" in supported:
        efforts = ", ".join((reasoning or {}).get("supported_efforts") or ())
        facts.setdefault("reasoning", []).append({"value": True, "source": source,
                                                  "basis": "OpenRouter lists reasoning controls" + (f", with the efforts {efforts}" if efforts else "")})
        _use(row, "reasoning", source, "OpenRouter lists reasoning controls for it")
    if isinstance(model.get("knowledge_cutoff"), str) and re.match(r"^\d{4}-\d{2}(-\d{2})?$", model["knowledge_cutoff"]):
        facts.setdefault("knowledge_cutoff", {"value": model["knowledge_cutoff"], "source": source,
                                              "basis": "the knowledge cutoff OpenRouter lists"})
    if "image" in (architecture.get("input_modalities") or ()):
        _use(row, "vision", source, "OpenRouter lists images among its inputs")
    analysis = (model.get("benchmarks") or {}).get("artificial_analysis") or {}
    for key, label in (("intelligence_index", "Artificial Analysis Intelligence Index"),
                       ("coding_index", "Artificial Analysis Coding Index"), ("agentic_index", "Artificial Analysis Agentic Index")):
        if isinstance(analysis.get(key), (int, float)) and not isinstance(analysis.get(key), bool):
            row["benchmarks"].append({"name": label, "value": analysis[key], "publisher": "Artificial Analysis",
                                      "address": "artificialanalysis.ai/methodology/intelligence-benchmarking", "source": source})


def _use(row: dict, value: str, source: int, basis: str) -> None:
    if all(item["value"] != value for item in row["use_cases"]):
        row["use_cases"].append({"value": value, "source": source, "basis": basis})


def _openrouter_prices(row: dict, details, add, model: dict) -> None:
    if details is None or not details.usable:
        return
    source = add("openrouter_endpoints", "openrouter.ai" + (model.get("links") or {}).get("details", ""), details.read_on)
    for endpoint in ((details.value or {}).get("data") or {}).get("endpoints") or ():
        pricing = endpoint.get("pricing") or {}
        prompt, completion = per_million(pricing.get("prompt")), per_million(pricing.get("completion"))
        provider = str(endpoint.get("provider_name") or "").strip()
        if prompt is None or completion is None or not provider:
            continue
        price = {"provider": provider, "provider_slug": sources_slug(provider), "route": records.ROUTE_OPENROUTER,
                 "model_id": model["id"], "input": prompt, "output": completion, "as_of": details.read_on, "source": source}
        cache = per_million(pricing.get("input_cache_read"))
        if cache is not None:
            price["cache_read"] = cache
        for key, name in (("context_length", "context"), ("max_completion_tokens", "max_output")):
            if isinstance(endpoint.get(key), int) and endpoint[key] > 0:
                price[name] = endpoint[key]
        if isinstance(endpoint.get("quantization"), str) and endpoint["quantization"] not in ("", "unknown"):
            price["quantization"] = endpoint["quantization"]
        row["prices"].append(price)


def sources_slug(name: str) -> str:
    from .rows import slug_of
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


def assemble_models(reader, documentation: dict, root, today: str, gguf_limit: int, progress=print) -> tuple:
    """Every model row, and a report of what was read, reused, kept and refused."""
    excluded = set(documentation.get("excluded_openrouter_vendors") or ())
    makers = {key: value for key, value in (documentation.get("openrouter_makers") or {}).items() if key != "note"}
    report = {"lists": [], "refused": [], "gguf_repositories": 0, "configurations": 0}
    or_answer = sources.openrouter_models(reader)
    or_models = [model for model in ((or_answer.value or {}).get("data") or ())
                 if isinstance(model.get("id"), str) and not model["id"].startswith("~")
                 and model["id"].split("/", 1)[0] not in excluded]
    hf: dict = {}
    for task, sort, limit in sources.HF_LISTS:
        answer = sources.hf_list(reader, task, sort, limit)
        kept = 0
        for record in answer.value or ():
            if isinstance(record, dict) and isinstance(record.get("id"), str) and not sources.is_copy(record) and record["id"] not in hf:
                hf[record["id"]] = (record, answer)
                kept += 1
        report["lists"].append({"task": task, "sort": sort, "limit": limit, "state": answer.state, "read": answer.read_on, "added": kept})
    groups: dict = {}
    for model in or_models:
        groups.setdefault(model["id"].split(":", 1)[0], []).append(model)
    for base, group in groups.items():
        group.sort(key=lambda item: (item["id"] != base, item["id"]))
    linked = {}
    for group in groups.values():
        repository = next((model.get("hugging_face_id") for model in group if isinstance(model.get("hugging_face_id"), str)
                           and model["hugging_face_id"].count("/") == 1), None)
        if repository is None:
            continue
        linked.setdefault(repository, []).extend(group)
        if repository not in hf:
            answer = sources.hf_model(reader, repository)
            if answer.usable and isinstance(answer.value, dict) and answer.value.get("id") == repository:
                hf[repository] = (answer.value, answer)
    md_answer = sources.modelsdev(reader)
    md = md_answer.value if isinstance(md_answer.value, dict) else {}
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
        for index, model in enumerate(linked.get(identifier, ())):
            _join_openrouter(row, sources_of, model, or_answer, reader, with_facts=index == 0)
        for provider_id, provider, offer in by_hf_id.get(identifier.lower(), ()):
            _modelsdev_offer(row, sources_of.add, provider_id, provider, offer, md_answer.read_on, False)
            used_md.add((provider_id, offer["id"]))
        rows.append((row, sources_of))
        if position % 100 == 0:
            progress(f"models: {position} of {len(ordered)} open models assembled; {reader.summary()['answers']}")
    joined = {id(model) for group in linked.values() for model in group}
    for base, group in sorted(groups.items()):
        if any(id(model) in joined for model in group):
            continue
        model = group[0]
        maker, name = split_openrouter_name(str(model.get("name") or model["id"]))
        row = _empty_row("openrouter", model["id"], name or model["id"], maker or model["id"].split("/")[0])
        sources_of = RowSources()
        for index, variant in enumerate(group):
            _join_openrouter(row, sources_of, variant, or_answer, reader, with_facts=index == 0)
        vendor, _, model_part = base.partition("/")
        provider_id = makers.get(vendor)
        offer = ((md.get(provider_id) or {}).get("models") or {}).get(model_part) if provider_id else None
        if offer is not None:
            _modelsdev_offer(row, sources_of.add, provider_id, md[provider_id], {**offer, "id": model_part}, md_answer.read_on, True)
            used_md.add((provider_id, model_part))
        rows.append((row, sources_of))
    for provider_id in sorted(set(makers.values())):
        provider = md.get(provider_id) or {}
        for model_id, offer in sorted((provider.get("models") or {}).items()):
            if (provider_id, model_id) in used_md:
                continue
            row = _empty_row("modelsdev", provider_id + "/" + model_id, str(offer.get("name") or model_id), str(provider.get("name") or provider_id))
            sources_of = RowSources()
            _modelsdev_offer(row, sources_of.add, provider_id, provider, {**offer, "id": model_id}, md_answer.read_on, True)
            rows.append((row, sources_of))
    return rows, report, {"openrouter": or_answer, "modelsdev": md_answer}


def _join_openrouter(row: dict, sources_of: RowSources, model: dict, or_answer, reader, with_facts: bool = True) -> None:
    """Join one OpenRouter model: its facts for the first model of a group, its prices for every one."""
    add = sources_of.add
    details = (model.get("links") or {}).get("details")
    if isinstance(details, str) and details.startswith("/api/v1/models/"):
        _openrouter_prices(row, sources.openrouter_endpoints(reader, details), add, model)
    if not with_facts:
        return
    source = add("openrouter", OPENROUTER_ADDRESS, or_answer.read_on)
    row["ids"]["openrouter"] = model["id"]
    maker, name = split_openrouter_name(str(model.get("name") or ""))
    if name:
        row["name"] = name
    if maker:
        row["maker"] = maker
    if "released" not in row["facts"]:
        day = day_of_epoch(model.get("created"))
        if day:
            row["facts"]["released"] = {"value": day, "source": source, "basis": "the day OpenRouter added the model"}
    _openrouter_facts(model, row, add, source)
